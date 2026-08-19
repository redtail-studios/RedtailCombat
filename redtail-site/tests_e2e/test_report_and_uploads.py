"""E2E: the file-upload routes (/api/lore/game-report, /api/lore/snapshot).

Both send a real multipart upload through FastAPI's real UploadFile handling,
into snapshot.py's real prep_upload()/load_game_text() (only the LLM/image
boundary is mocked) — proving the upload -> text-extraction -> analysis ->
report/brief chain holds end-to-end. This is also regression coverage for the
game-report endpoint, which called two functions (snapshot.prep_upload,
report.generate_game_report) that did not exist anywhere in this branch until
this same change added them back (see SCRAPING_ARCHITECTURE.md history) —
without a test driving the real route, 288 passing unit tests never caught it.
"""
import time
from pathlib import Path

import server
import snapshot

YEAR = 2026
PASSWORD = server.LORE_PASSWORD
FIXTURE = Path(__file__).parent / "fixtures" / "sample_game_design.txt"


def _seed_scraped_data(client, reset_scrape_job):
    """Run the real local scrape pipeline first so analyse() has real
    (fake-scraper-sourced) data to work with, instead of an empty year."""
    reset_scrape_job(YEAR)
    client.post("/api/lore/scrape", json={"year": YEAR, "password": PASSWORD})
    deadline = time.time() + 10.0
    while time.time() < deadline:
        status = client.get("/api/lore/scrape/status", params={"year": YEAR}).json()
        if status["status"] in ("done", "error"):
            assert status["status"] == "done"
            return
        time.sleep(0.05)
    raise AssertionError("seed scrape did not finish in time")


def test_game_report_upload(client, fake_scrapers, local_data_dir, mock_llm, reset_scrape_job):
    _seed_scraped_data(client, reset_scrape_job)

    with open(FIXTURE, "rb") as f:
        resp = client.post(
            "/api/lore/game-report",
            files={"file": ("sample_game_design.txt", f, "text/plain")},
            data={"years": str(YEAR), "password": PASSWORD},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["game"] == "sample_game_design"
    assert "Market Gap Analysis" in body["html"]


def test_snapshot_upload(client, fake_scrapers, local_data_dir, reset_scrape_job, monkeypatch):
    _seed_scraped_data(client, reset_scrape_job)

    fake_brief = (
        '{"headline": "test headline", "modifications": ['
        '{"finding": "players want short matches", "change": "add a quick-match mode", '
        '"why": "matches the finding", "image_prompt": "a quick-match menu card"}]}'
    )
    monkeypatch.setattr(snapshot.llm, "generate", lambda prompt, max_tokens=4000: fake_brief)
    monkeypatch.setattr(snapshot, "_render_image", lambda prompt: b"\x89PNGfakebytes")

    with open(FIXTURE, "rb") as f:
        resp = client.post(
            "/api/lore/snapshot",
            files={"file": ("sample_game_design.txt", f, "text/plain")},
            data={"year": str(YEAR), "password": PASSWORD},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["game"] == "sample_game_design"
    assert body["headline"] == "test headline"
    assert len(body["modifications"]) == 1
    assert "image_b64" in body["modifications"][0]
