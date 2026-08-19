"""E2E: the local (non-DEPLOYED) scrape pipeline, driven through real HTTP
routes. POST /api/lore/scrape spawns a real background thread that iterates
real scraper modules (faked at their own run() boundary only), writes through
manifest.rebuild() to local disk, and GET /api/lore/status reads it back —
proving the wiring between server.py, the scraper loop, and manifest.py
actually holds, not just each piece in isolation.
"""
import time

import config
import server

YEAR = 2026
PASSWORD = server.LORE_PASSWORD


def _wait_for_scrape_done(client, year, timeout=10.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = client.get("/api/lore/scrape/status", params={"year": year}).json()
        if last["status"] in ("done", "error"):
            return last
        time.sleep(0.05)
    raise AssertionError(f"scrape for {year} did not finish within {timeout}s; last poll: {last}")


def test_local_scrape_then_status_then_report(
    client, fake_scrapers, local_data_dir, mock_llm, reset_scrape_job,
):
    reset_scrape_job(YEAR)

    resp = client.post("/api/lore/scrape", json={"year": YEAR, "password": PASSWORD})
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"

    final = _wait_for_scrape_done(client, YEAR)
    assert final["status"] == "done"
    assert all(v == "done" for v in final["platforms"].values())

    status = client.get("/api/lore/status").json()
    year_block = status["years"][str(YEAR)]
    # every real platform actually made it into the manifest with the right count
    assert set(year_block["sources"]) == set(config.PLATFORM_IDS)
    assert year_block["sources"]["reddit"] == len(fake_scrapers["reddit"])
    assert year_block["sources"]["steam"] == len(fake_scrapers["steam"])
    assert year_block["total"] == sum(len(v) for v in fake_scrapers.values())

    report_resp = client.post("/api/lore/report", json={
        "backtest_years": [YEAR], "password": PASSWORD,
    })
    assert report_resp.status_code == 200
    html = report_resp.json()["html"]
    assert "<html>" in html
    assert "Market Gap Analysis" in html


def test_scrape_rejects_unsupported_year(client, reset_scrape_job):
    resp = client.post("/api/lore/scrape", json={"year": 1999, "password": PASSWORD})
    assert resp.status_code == 400


def test_scrape_while_running_returns_409(client, reset_scrape_job):
    # Drive the guard deterministically rather than racing a real background
    # thread (fake scrapers return instantly, so timing a real overlap would
    # be flaky) — pre-seed the exact "already running" state the guard checks.
    reset_scrape_job(YEAR)
    with server._scrape_lock:
        server._scrape[str(YEAR)]["status"] = "running"

    resp = client.post("/api/lore/scrape", json={"year": YEAR, "password": PASSWORD})
    assert resp.status_code == 409
