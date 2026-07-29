"""scheduler.py — EventBridge Scheduler entry point for the weekly scrape.
Runs on a cron schedule (see SCRAPING_ARCHITECTURE.md), independent of the
Vercel API process entirely. Enqueues a fresh scrape of every platform for
the current calendar year — the schedule itself is the freshness mechanism
now, so this always forces a re-scrape regardless of the S3 TTL check that
the manual ops endpoint (server.py) still respects.

Deployed as its own Lambda function, separate from the SQS-triggered scrape
worker (lore_engine/worker.py) — this only needs config.py + storage.py
(boto3, already in the Lambda runtime), never scrapers/*, so its deployment
package stays tiny and its IAM role stays narrow (S3 head/put + SQS send
only, no S3 get/list, no SQS receive/delete).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # so `import config`/`storage` resolve
                                                 # regardless of packaging layout

import storage  # noqa: E402


def handler(event, context):
    year = storage.current_year()
    queued = storage.enqueue_missing_platforms(year, force=True)
    print(f"[scheduler] enqueued {len(queued)} platform(s) for {year}: {queued}")
    return {"year": year, "queued": queued}
