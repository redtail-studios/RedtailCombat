"""scheduler.py — EventBridge Scheduler entry point for the weekly scrape.
Runs on a cron schedule (see SCRAPING_ARCHITECTURE.md), independent of the
Vercel API process entirely.

Only the current calendar year gets enqueued, unconditionally (force=True) —
the schedule itself is the freshness mechanism for it, regardless of the S3
TTL check that the manual ops endpoint (server.py) still respects.

Past years are deliberately NOT touched here. An earlier version also did a
backfill-only pass (force=False) over every other supported year, on the
theory that past years are frozen snapshots so re-checking them weekly was
harmless. That's true for most platforms, but not for reddit: its scraper
hits Reddit's `/hot/.rss` listing, which only reflects *currently* trending
posts — asking it for "2025" once 2026 is under way returns close to nothing
no matter how long you let it run (confirmed: a full run against 2025 spent
12 minutes and returned 1 record). So a weekly backfill pass would burn a
worker invocation's entire time budget on every past year, every week,
for no real data. If a genuine past-year gap ever needs to be plugged
(e.g. a new platform added after that year was last scraped), do it as a
one-off manual `/api/lore/scrape` call or a direct worker invoke, not as a
standing weekly job.

Deployed as its own Lambda function, separate from the SQS-triggered scrape
worker (lore_engine/worker.py) — this only needs storage.py (boto3, already
in the Lambda runtime), never scrapers/* or config.py, so its deployment
package stays tiny. Its IAM role needs sqs:SendMessage and a DynamoDB
PutItem on the status table — no S3 access at all now that the past-year
freshness check is gone.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # so `import storage` resolves
                                                 # regardless of packaging layout

import storage  # noqa: E402


def handler(event, context):
    year = storage.current_year()
    queued = storage.enqueue_missing_platforms(year, force=True)
    print(f"[scheduler] enqueued {len(queued)} platform(s) for {year}: {queued}")
    return {"queued_by_year": {year: queued}}
