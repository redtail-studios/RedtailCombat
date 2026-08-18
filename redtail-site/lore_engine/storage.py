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
from botocore.config import Config
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

# boto3's default urllib3 pool is 10 connections. A single report request can
# now make up to len(PLATFORM_IDS) * len(ACTIVE_GENRES) sequential S3 reads
# (18 platforms x 5 genres = 90), and compute_manifest()/get_all_statuses()
# fan out up to 16 concurrent HEAD/GET calls via ThreadPoolExecutor on top of
# that — comfortably exceeding a pool of 10, which forced boto3 to keep
# discarding and reopening connections ("Connection pool is full, discarding
# connection") and pushed a chunk of every request into raw TCP/TLS handshake
# time instead of reusing a warm connection. 50 gives real headroom over the
# largest concurrent burst (16 threads) without being wastefully large.
_S3_CONFIG = Config(max_pool_connections=50)

_s3 = None
_sqs = None


def _s3_client():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3", region_name=REGION, config=_S3_CONFIG)
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


# ── Incremental-scrape support (a handful of platforms only — see worker.py's
#    INCREMENTAL_MERGE_KEYS) ──────────────────────────────────────────────────
def get_last_scraped(year: int, platform: str):
    """Returns the existing data object's LastModified, or None if it doesn't
    exist yet. Used as the 'since' cursor a scraper fetches forward from —
    None means "no prior data, fetch the full year" (first run behavior,
    unchanged)."""
    try:
        resp = _s3_client().head_object(Bucket=BUCKET, Key=_data_key(year, platform))
    except ClientError as e:
        if _not_found(e):
            return None
        raise
    return resp["LastModified"]


def get_raw_records(year: int, platform: str):
    """Like get_cached_records(), but skips the freshness/TTL check — the
    incremental-merge path needs to see existing data even when it's
    technically 'stale' by the current-year TTL, since that staleness is
    exactly why a re-scrape was triggered. Returns None only on a genuine
    cache miss."""
    try:
        resp = _s3_client().get_object(Bucket=BUCKET, Key=_data_key(year, platform))
    except ClientError as e:
        if _not_found(e):
            return None
        raise
    return json.loads(resp["Body"].read())


def merge_by_key(existing: list, new: list, key: str) -> list:
    """Append-only merge for platforms whose records are immutable once
    captured (news articles, forum stories) — a key collision means we
    already have this item, so existing wins and duplicates are dropped;
    genuinely new keys get appended. Not a fit for platforms whose records
    carry live metrics that change after capture (review/owner counts,
    hype scores) — those stay on the full-overwrite path."""
    seen = {r[key] for r in existing if r.get(key) is not None}
    merged = list(existing)
    for r in new:
        k = r.get(key)
        if k is not None and k not in seen:
            merged.append(r)
            seen.add(k)
    return merged


def merge_nested_by_key(existing: list, new: list, record_key: str,
                         nested_field: str, nested_key: str) -> list:
    """For platforms whose top-level records mix live metrics (review/owner
    counts, install counts) with an append-only nested list (reviews):
    matches records by `record_key` (e.g. app_id), takes the NEW run's
    top-level fields as-is (they're the fresh live metrics), but merges the
    `nested_field` list (e.g. "reviews") by `nested_key` via merge_by_key()
    instead of replacing it. A record that existed before but is absent from
    `new` (e.g. an app that dropped out of this week's top-10-by-tag) keeps
    its accumulated history rather than vanishing."""
    by_key = {r[record_key]: r for r in existing if r.get(record_key) is not None}
    merged = []
    for rec in new:
        old = by_key.pop(rec.get(record_key), None)
        if old is not None:
            rec[nested_field] = merge_by_key(
                old.get(nested_field, []), rec.get(nested_field, []), nested_key)
        merged.append(rec)
    merged.extend(by_key.values())  # untouched-this-run records, kept as-is
    return merged


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
    parallel (15 small GETs) so a status poll every 1.5s stays fast.

    For past years (never expiring — see _is_fresh), a platform reported
    "idle" here just means no scrape *job* was ever run through this app's
    status-marker system, not that the platform's data is missing — a lot
    of historical data was backfilled directly into S3 without going
    through a job. So for past years only, "idle" gets upgraded to "done"
    when real cached data actually exists, instead of misleadingly showing
    the Step 1 grid as "needs scraping" for years that are already loaded.
    The current year is left exactly as before: real job status, since
    that's what "does this actually need a re-scrape" depends on there."""
    with ThreadPoolExecutor(max_workers=8) as ex:
        pairs = list(ex.map(
            lambda pid: (pid, get_status(year, pid).get("status", "idle")),
            PLATFORM_IDS,
        ))
    statuses = dict(pairs)

    if year != current_year():
        idle_pids = [pid for pid, s in statuses.items() if s == "idle"]
        if idle_pids:
            with ThreadPoolExecutor(max_workers=8) as ex:
                present = list(ex.map(lambda pid: (pid, is_cached_fresh(year, pid)), idle_pids))
            for pid, has_data in present:
                if has_data:
                    statuses[pid] = "done"

    return statuses


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
