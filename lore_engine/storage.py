"""storage.py — S3-backed cache for scraped platform data + per-platform job
status, and an SQS enqueue helper for the scrape worker. Used in place of the
local lore_data/ + manifest.json flow when DEPLOYED (or when running as the
Lambda scrape worker).
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from config import PLATFORM_IDS, SUPPORTED_YEARS

REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET = os.getenv("AWS_BUCKET")
QUEUE_URL = os.getenv("LORE_SCRAPE_QUEUE_URL")  # only needed on the enqueue (API) side
TTL_SECONDS = int(os.getenv("LORE_CACHE_TTL_SECONDS", str(7 * 24 * 3600)))  # 7 days

_ROOT_PREFIX = os.getenv("LORE_S3_PREFIX", "lore")  # override in test deployments so a
                                                     # test project's data can never
                                                     # collide with production's keyspace
DATA_PREFIX = f"{_ROOT_PREFIX}/data"      # <prefix>/data/<year>/<platform>.json   -> records list
STATUS_PREFIX = f"{_ROOT_PREFIX}/status"  # <prefix>/status/<year>/<platform>.json -> status marker

_s3 = None
_sqs = None


def _s3_client():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3", region_name=REGION)
    return _s3


def _sqs_client():
    global _sqs
    if _sqs is None:
        _sqs = boto3.client("sqs", region_name=REGION)
    return _sqs


def _data_key(year, platform):
    return f"{DATA_PREFIX}/{year}/{platform}.json"


def _status_key(year, platform):
    return f"{STATUS_PREFIX}/{year}/{platform}.json"


def _not_found(e: ClientError) -> bool:
    return e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey")


def current_year() -> int:
    return datetime.now(timezone.utc).year


def _is_fresh(year: int, last_modified: datetime) -> bool:
    """Past years never expire; only the current calendar year has a TTL."""
    if year != current_year():
        return True
    age = datetime.now(timezone.utc) - last_modified
    return age.total_seconds() < TTL_SECONDS


# ── Data cache ───────────────────────────────────────────────────────────────
def is_cached_fresh(year: int, platform: str) -> bool:
    """Cheap HEAD-only freshness check (no body download) — used by the
    producer to decide whether a platform needs to be (re-)enqueued."""
    try:
        resp = _s3_client().head_object(Bucket=BUCKET, Key=_data_key(year, platform))
    except ClientError as e:
        if _not_found(e):
            return False
        raise
    return _is_fresh(year, resp["LastModified"])


def get_cached_records(year: int, platform: str):
    """Read-path used by analysis.py. Returns None on cache miss OR stale
    cache (same "silently skip" semantics as today's missing-local-file case).
    """
    try:
        resp = _s3_client().get_object(Bucket=BUCKET, Key=_data_key(year, platform))
    except ClientError as e:
        if _not_found(e):
            return None
        raise
    if not _is_fresh(year, resp["LastModified"]):
        return None
    return json.loads(resp["Body"].read())


def put_records(year: int, platform: str, records: list) -> None:
    """Write-path used only by the worker. Stashes the record count in S3
    object metadata so compute_manifest() can read counts via HEAD (no body
    download) instead of downloading+parsing every JSON body."""
    body = json.dumps(records, ensure_ascii=False).encode("utf-8")
    _s3_client().put_object(
        Bucket=BUCKET, Key=_data_key(year, platform), Body=body,
        ContentType="application/json",
        Metadata={"count": str(len(records))},
    )


# ── Status markers ───────────────────────────────────────────────────────────
def put_status(year: int, platform: str, status: str, error: str = None) -> None:
    doc = {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}
    if error:
        doc["error"] = str(error)[:500]
    _s3_client().put_object(
        Bucket=BUCKET, Key=_status_key(year, platform),
        Body=json.dumps(doc).encode("utf-8"), ContentType="application/json",
    )


def get_status(year: int, platform: str) -> dict:
    try:
        resp = _s3_client().get_object(Bucket=BUCKET, Key=_status_key(year, platform))
    except ClientError as e:
        if _not_found(e):
            return {"status": "idle"}
        raise
    return json.loads(resp["Body"].read())


def get_all_statuses(year: int) -> dict:
    """{platform_id: status_str} for every known platform, fanned out in
    parallel (15 small GETs) so a status poll every 1.5s stays fast."""
    with ThreadPoolExecutor(max_workers=8) as ex:
        pairs = list(ex.map(
            lambda pid: (pid, get_status(year, pid).get("status", "idle")),
            PLATFORM_IDS,
        ))
    return dict(pairs)


# ── Live manifest (replaces lore_data/manifest.json when DEPLOYED) ──────────
def compute_manifest() -> dict:
    """Rebuilds the manifest.json shape by listing S3 + reading cheap HEAD
    metadata — no separately-maintained manifest.json in S3, so there is no
    read-modify-write race between concurrent worker invocations scraping
    different platforms of the same year."""
    keys = set()
    paginator = _s3_client().get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=f"{DATA_PREFIX}/"):
        for obj in page.get("Contents", []):
            keys.add(obj["Key"])

    def _head(year, pid):
        key = _data_key(year, pid)
        if key not in keys:
            return None
        try:
            resp = _s3_client().head_object(Bucket=BUCKET, Key=key)
        except ClientError:
            return None
        count = int(resp.get("Metadata", {}).get("count", "0"))
        return pid, count, resp["LastModified"]

    targets = [(y, pid) for y in SUPPORTED_YEARS for pid in PLATFORM_IDS]
    with ThreadPoolExecutor(max_workers=16) as ex:
        results = list(ex.map(lambda t: _head(*t), targets))

    by_year = {}
    latest = None
    for (y, _pid), r in zip(targets, results):
        if r is None:
            continue
        pid, count, lm = r
        if not count:
            continue
        by_year.setdefault(y, {})[pid] = count
        if latest is None or lm > latest:
            latest = lm

    years = {}
    for y, sources in by_year.items():
        years[str(y)] = {"sources": sources, "total": sum(sources.values())}

    scraped_at = latest.strftime("%Y-%m-%d %H:%M UTC") if latest else "unknown"
    return {"scraped_at": scraped_at, "years": years}


def scrape_status_snapshot(year: int) -> dict:
    """{status, year, log, platforms} — same shape server.py's in-memory
    _scrape dict returns, so GET /api/lore/scrape/status is a drop-in when
    DEPLOYED. `log` is always [] (no cross-invocation log aggregation; the
    frontend never reads it today)."""
    platforms = get_all_statuses(year)
    vals = set(platforms.values())
    terminal = {"done", "empty", "error"}
    if vals and vals <= {"idle"}:
        overall = "idle"
    elif any(v not in terminal for v in vals):  # queued / running
        overall = "running"
    else:
        manifest = compute_manifest()
        overall = "done" if str(year) in manifest.get("years", {}) else "error"
    out = {"status": overall, "year": year, "log": [], "platforms": platforms}
    if overall == "error":
        out["error"] = "Scrape finished with no usable data"
    return out


# ── SQS enqueue (producer side; the worker is invoked by the SQS trigger
#    itself, so there is no matching dequeue function here) ─────────────────
def enqueue_scrape(year: int, platform: str) -> None:
    _sqs_client().send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps({"year": year, "platform": platform}),
    )


def enqueue_missing_platforms(year: int, force: bool = False) -> list:
    """Enqueue every platform that needs (re-)scraping for `year`. Shared by
    the manual ops endpoint (server.py, force=False — skip platforms whose
    cache is still fresh) and the weekly scheduler Lambda (scheduler.py,
    force=True — the schedule itself is now the freshness mechanism, so every
    platform gets re-enqueued regardless of the TTL)."""
    queued = []
    for pid in PLATFORM_IDS:
        if not force and is_cached_fresh(year, pid):
            continue
        put_status(year, pid, "queued")
        enqueue_scrape(year, pid)
        queued.append(pid)
    return queued
