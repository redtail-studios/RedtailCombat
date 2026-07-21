"""worker.py — SQS-triggered Lambda handler for the scrape queue. One SQS
message = one (year, platform) job. Reuses the existing scrapers.<id>.run()
unchanged; the only new work is uploading its return value to S3 and writing
status markers, since the worker has no memory shared with the API process.
"""
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # so `import config`/`scrapers` resolve
                                                  # regardless of packaging layout

import storage  # noqa: E402


def _process_one(year: int, platform: str) -> None:
    try:
        storage.put_status(year, platform, "running")
        mod = importlib.import_module(f"scrapers.{platform}")
        records = mod.run(year=year, log=print)
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
