"""E2E: cheap, infra-free route-contract tests — no scraping, no AWS, no LLM
calls. Every password-gated route's auth gate, the guest-password expiry
window, and basic request-validation error paths, all driven through real
HTTP requests into server.app.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import server

PASSWORD = server.LORE_PASSWORD
FIXTURE = Path(__file__).parent / "fixtures" / "sample_game_design.txt"


def _future():
    return datetime.now(timezone.utc) + timedelta(days=1)


def _past():
    return datetime.now(timezone.utc) - timedelta(days=1)


@pytest.mark.parametrize("method,path,kwargs", [
    ("post", "/api/lore/scrape", dict(json={"year": 2026, "password": "wrong"})),
    ("post", "/api/lore/report", dict(json={"backtest_years": [2026], "password": "wrong"})),
])
def test_json_routes_reject_bad_password(client, method, path, kwargs):
    resp = getattr(client, method)(path, **kwargs)
    assert resp.status_code == 401


def test_game_report_rejects_bad_password(client):
    with open(FIXTURE, "rb") as f:
        resp = client.post(
            "/api/lore/game-report",
            files={"file": ("sample_game_design.txt", f, "text/plain")},
            data={"years": "2026", "password": "wrong"},
        )
    assert resp.status_code == 401


def test_snapshot_rejects_bad_password(client):
    with open(FIXTURE, "rb") as f:
        resp = client.post(
            "/api/lore/snapshot",
            files={"file": ("sample_game_design.txt", f, "text/plain")},
            data={"year": "2026", "password": "wrong"},
        )
    assert resp.status_code == 401


def test_guest_password_works_before_expiry(client, monkeypatch):
    monkeypatch.setattr(server, "GUEST_EXPIRES", _future())
    # unsupported year -> proves auth passed (401 would mean auth failed first)
    resp = client.post("/api/lore/scrape", json={"year": 1999, "password": server.GUEST_PASSWORD})
    assert resp.status_code == 400


def test_guest_password_rejected_after_expiry(client, monkeypatch):
    monkeypatch.setattr(server, "GUEST_EXPIRES", _past())
    resp = client.post("/api/lore/scrape", json={"year": 1999, "password": server.GUEST_PASSWORD})
    assert resp.status_code == 401


def test_report_requires_at_least_one_backtest_year(client):
    resp = client.post("/api/lore/report", json={"backtest_years": [], "password": PASSWORD})
    assert resp.status_code == 400


def test_report_rejects_unknown_genre(client):
    resp = client.post("/api/lore/report", json={
        "backtest_years": [2026], "genre": "not-a-real-genre", "password": PASSWORD,
    })
    assert resp.status_code == 400
