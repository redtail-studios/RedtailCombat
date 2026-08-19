"""Shared fixtures for the E2E integration suite.

These tests import `server` (the real FastAPI app) and drive its actual HTTP
routes through real business logic (lore_engine.{manifest,storage,analysis,
report,snapshot}) rather than mocking our own module boundaries — see
/Users/dchen/.claude/plans/hazy-wondering-gizmo.md for the rationale. Only two
things are ever mocked: each scraper's own external-HTTP calls (same pattern
as lore_engine/tests/) and the LLM/image-generation boundary (llm.py).
"""
import os
import re
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root -> `import server`

import pytest
from fastapi.testclient import TestClient

import server  # noqa: E402  (inserts lore_engine/ onto sys.path as a side effect)
import config  # noqa: E402
import manifest  # noqa: E402
import storage  # noqa: E402
import analysis  # noqa: E402
import llm  # noqa: E402
import report  # noqa: E402
import scrapers  # noqa: E402  (lore_engine/scrapers/__init__.py — real save(), untouched by per-platform fakes)


@pytest.fixture
def client():
    return TestClient(server.app)


# ── Fake scraper data ─────────────────────────────────────────────────────────
# Three platforms get content rich enough (real signal keywords, a real
# COMPETITORS name, sentiment) to make analysis.py's signals/competitors/quotes
# non-trivial. The rest get a minimal-but-valid record each — plenty to prove
# the manifest/status wiring, without hand-authoring 18 rich fixtures.
_RICH_RECORDS = {
    "reddit": [
        {"genre": "fighting", "title": "Ranked ladder feedback",
         "text": "I love the fast progression and competitive ranked pvp ladder, very fun",
         "sentiment": {"compound": 0.7}},
        {"genre": "fighting", "title": "Monetization complaint",
         "text": "This game is way too pay to win, and it is frustrating to deal with",
         "sentiment": {"compound": -0.6}},
    ],
    "steam": [
        {"genre": "gacha", "title": "Genshin comparison",
         "text": "Genshin Impact handles gacha banners and pity so much better than this game",
         "sentiment": {"compound": -0.3}},
    ],
    "googleplay": [
        {"genre": "idle", "title": "Co-op praise",
         "text": "Great co-op play with friends, the guild clan system keeps me coming back",
         "sentiment": {"compound": 0.5}},
    ],
}


# worker.py's INCREMENTAL_MERGE_KEYS platforms (plain merge_by_key, not the
# nested variant) drop any record missing this key on the very first merge —
# real scrapers always set it; a generic record needs it too or the worker
# ends up storing zero records and reporting status "empty" instead of "done".
_MERGE_KEY_FIELDS = {"hackernews": "id", "gamenews": "url", "gdelt": "url"}


def _generic_records(pid):
    rec = {"genre": "general", "title": f"{pid} sample item",
           "text": f"Synthetic {pid} record generated for the E2E pipeline test.",
           "sentiment": {"compound": 0.1}}
    key_field = _MERGE_KEY_FIELDS.get(pid)
    if key_field:
        rec[key_field] = f"{pid}-1"
    return [rec]


def _install_fake_scraper(monkeypatch, platform, run_fn):
    mod = types.ModuleType(f"scrapers.{platform}")
    mod.run = run_fn
    monkeypatch.setitem(sys.modules, f"scrapers.{platform}", mod)


@pytest.fixture
def fake_scrapers(monkeypatch, tmp_path):
    """Installs a fast synthetic scrapers.<platform>.run() for every real
    platform id, so the scrape pipeline runs end-to-end without any real
    network calls. Returns {platform_id: [records]} for assertions.

    Also redirects config.DATA_DIR to a throwaway tmp_path and has each fake
    run() persist through the real scrapers.save() helper, matching what a
    real scraper does as a side effect — local-mode's manifest.rebuild() reads
    scraped data back off disk, so a run() that only returns records (without
    ever writing the <platform>_data.json file a real scraper writes) would
    leave the manifest empty. This also guarantees the deployed-mode test's
    incidental local-disk writes land in tmp_path, never the real repo.
    """
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    installed = {}
    for pid in config.PLATFORM_IDS:
        records = _RICH_RECORDS.get(pid, _generic_records(pid))
        installed[pid] = records

        def make_run(recs, platform_id):
            def run(year=None, log=print, **kwargs):
                scrapers.save(recs, config.get_year_dir(year), platform_id, log)
                return recs
            return run

        _install_fake_scraper(monkeypatch, pid, make_run(records, pid))
    return installed


@pytest.fixture
def mock_llm(monkeypatch):
    """Patches the LLM boundary (llm.generate_html) so report generation never
    makes a real Claude/OpenAI call. Echoes back a real [Qn] citation pulled
    from the prompt itself (report.py embeds citation ids directly in the
    prompt text via _fmt_quotes) so report.validate_citations() genuinely
    passes rather than trivially no-oping on empty input."""
    def fake_generate_html(prompt, max_tokens=32000):
        ids = re.findall(r"\[Q\d+\]", prompt)
        cite = ids[0] if ids else ""
        return (
            "<html><body>"
            "<h1>Test Report</h1>"
            "<h2>Market Gap Analysis</h2>"
            f"<h3>Fake Gap</h3><p>Players want more of this {cite}</p>"
            "</body></html>"
        )
    monkeypatch.setattr(llm, "generate_html", fake_generate_html)
    return fake_generate_html


@pytest.fixture
def local_data_dir(tmp_path, monkeypatch):
    """Redirects local-mode scrape/manifest storage to a throwaway directory.
    DATA_DIR is read directly off `config` by get_year_dir()/server.status(),
    but manifest.py binds its own copy at import time (`from config import
    DATA_DIR`) so it needs patching separately — see the plan's DEPLOYED-import
    gotcha; DATA_DIR has the identical import-time-binding issue."""
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(manifest, "DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def moto_aws(monkeypatch):
    """Stands up a moto-mocked S3 bucket + SQS queue and points storage.py's
    real boto3 calls at them, and flips config.DEPLOYED everywhere it's bound
    (server.py and analysis.py each capture their own copy at import time —
    patching config.DEPLOYED alone would not affect either)."""
    from moto import mock_aws
    import boto3

    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-lore-bucket")
        sqs = boto3.client("sqs", region_name="us-east-1")
        queue_url = sqs.create_queue(QueueName="test-lore-queue")["QueueUrl"]

        # Force storage.py's lazily-cached boto3 clients to be (re)created
        # inside this moto context rather than reusing any pre-existing ones.
        monkeypatch.setattr(storage, "_s3", None)
        monkeypatch.setattr(storage, "_sqs", None)
        monkeypatch.setattr(storage, "BUCKET", "test-lore-bucket")
        monkeypatch.setattr(storage, "QUEUE_URL", queue_url)

        monkeypatch.setattr(server, "DEPLOYED", True)
        monkeypatch.setattr(analysis, "DEPLOYED", True)

        yield {"bucket": "test-lore-bucket", "queue_url": queue_url,
               "s3": s3, "sqs": sqs}


@pytest.fixture
def reset_scrape_job(monkeypatch):
    """server._scrape is a module-level dict built once at import time and
    mutated in place by real requests — reset the slot a test is about to use
    so tests don't inherit "running"/"done" state left by an earlier test."""
    def _reset(year):
        server._scrape[str(year)] = server._blank_scrape(year)
    return _reset
