"""worker.py — SQS-triggered Lambda handler for the scrape queue. One SQS
message = one (year, platform) job. Reuses the existing scrapers.<id>.run()
unchanged for most platforms; the only new work is uploading its return value
to S3 and writing status markers, since the worker has no memory shared with
the API process.

Two shapes of platforms get a 'since' cursor — the existing data's
last-modified time — instead of always re-fetching the whole year:

- INCREMENTAL_MERGE_KEYS: records are immutable once captured (news
  articles, forum stories) and safe to append-and-dedupe by a stable key.
- INCREMENTAL_NESTED_MERGE_KEYS: records mix live metrics (review/owner
  counts, install counts) with an append-only nested reviews list — the
  live fields are taken fresh from the new fetch, only the nested list gets
  merged (see storage.merge_nested_by_key()).

This is deliberately NOT the default: most platforms' records carry live
metrics (review/owner counts, hype scores, chart rank) that change after
capture, so re-fetching the full current state is correct for them — see
SCRAPING_ARCHITECTURE.md.
"""
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # so `import config`/`scrapers` resolve
                                                  # regardless of packaging layout

import storage  # noqa: E402

# platform id -> the field that uniquely identifies one of its records, used
# to merge freshly-fetched records into what's already stored instead of
# overwriting it outright.
INCREMENTAL_MERGE_KEYS = {
    "hackernews": "id",
    "gamenews": "url",
    "gdelt": "url",
}

# platform id -> (record_key, nested_field, nested_key) — see
# storage.merge_nested_by_key(). record_key identifies one app/game across
# runs; nested_field is the append-only list inside it; nested_key
# identifies one item within that list.
INCREMENTAL_NESTED_MERGE_KEYS = {
    "steam":      ("app_id", "reviews", "id"),
    "appstore":   ("app_id", "reviews", "id"),
    "googleplay": ("app_id", "reviews", "review_id"),
}


def _process_one(year: int, platform: str) -> None:
    try:
        storage.put_status(year, platform, "running")
        mod = importlib.import_module(f"scrapers.{platform}")
        merge_key = INCREMENTAL_MERGE_KEYS.get(platform)
        nested = INCREMENTAL_NESTED_MERGE_KEYS.get(platform)
        kwargs = {}
        if merge_key or nested:
            since = storage.get_last_scraped(year, platform)
            if since:
                kwargs["since"] = since
        records = mod.run(year=year, log=print, **kwargs)
        if merge_key:
            existing = storage.get_raw_records(year, platform) or []
            records = storage.merge_by_key(existing, records, merge_key)
        elif nested:
            record_key, nested_field, nested_key = nested
            existing = storage.get_raw_records(year, platform) or []
            records = storage.merge_nested_by_key(
                existing, records, record_key, nested_field, nested_key)
        storage.put_records(year, platform, records)
        storage.put_status(year, platform, "done" if records else "empty")
    except Exception as e:
        # put_status("running") is inside this try too — if a config/permissions
        # problem breaks every S3 write, this second call will also fail and
        # propagate, but if the first failure was transient (or something else
        # in the block threw), the job is now recorded as "error" instead of
        # silently vanishing back to a permanent "queued".
        storage.put_status(year, platform, "error", error=f"{type(e).__name__}: {e}")
        raise  # let SQS retry (maxReceiveCount) / DLQ handle it — don't swallow


def handler(event, context):
    for rec in event.get("Records", []):
        body = json.loads(rec["body"])
        _process_one(int(body["year"]), body["platform"])
