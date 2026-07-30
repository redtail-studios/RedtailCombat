"""scheduler.py — EventBridge Scheduler entry point for the weekly scrape.
Runs on a cron schedule (see SCRAPING_ARCHITECTURE.md), independent of the
Vercel API process entirely. Two things happen on every run:

1. The current calendar year gets force-enqueued unconditionally — the
   schedule itself is the freshness mechanism for the current year now,
   regardless of the S3 TTL check that the manual ops endpoint (server.py)
   still respects.
2. Every *past* supported year gets a backfill-only enqueue (force=False) —
   past years are frozen annual snapshots (see storage._is_fresh: once a
   platform has any data for a past year, it's "fresh" forever), so this
   never overwrites existing historical data. It only catches genuine gaps:
   a platform that errored out every time (like appcharts/igdb/gdelt did
   before a worker bug was fixed) or one added after that year was last
   scraped. Safe to run every week — once nothing is missing for a past
   year, this enqueues nothing for it.

Deployed as its own Lambda function, separate from the SQS-triggered scrape
worker (lore_engine/worker.py) — this only needs config.py + storage.py
(boto3, already in the Lambda runtime), never scrapers/*, so its deployment
package stays tiny. Its IAM role needs s3:HeadObject (the force=False
freshness check on past years), s3:PutObject, and sqs:SendMessage — no S3
get/list, no SQS receive/delete.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # so `import config`/`storage` resolve
                                                 # regardless of packaging layout

import config   # noqa: E402
import storage  # noqa: E402


def handler(event, context):
    year = storage.current_year()
    result = {year: storage.enqueue_missing_platforms(year, force=True)}
    for y in config.SUPPORTED_YEARS:
        if y != year:
            result[y] = storage.enqueue_missing_platforms(y, force=False)

    for y, queued in result.items():
        print(f"[scheduler] enqueued {len(queued)} platform(s) for {y}: {queued}")
    return {"queued_by_year": result}
