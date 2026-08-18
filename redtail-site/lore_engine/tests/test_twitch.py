import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

import scrapers.twitch as twitch

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
GAMES_URL = "https://api.twitch.tv/helix/games/top"


@pytest.fixture
def creds(monkeypatch):
    monkeypatch.setattr(twitch, "TWITCH_CLIENT_ID", "cid")
    monkeypatch.setattr(twitch, "TWITCH_CLIENT_SECRET", "secret")
    monkeypatch.setattr(twitch, "TWITCH_TOP_GAMES", 5)
    monkeypatch.setattr(twitch, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(twitch, "save", lambda records, data_dir, name, log: records)


def test_missing_credentials_skips_without_calling_out(monkeypatch, requests_mock):
    monkeypatch.setattr(twitch, "TWITCH_CLIENT_ID", "")
    monkeypatch.setattr(twitch, "TWITCH_CLIENT_SECRET", "")
    monkeypatch.setattr(twitch, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(twitch, "save", lambda records, data_dir, name, log: records)
    requests_mock.post(TOKEN_URL, exc=AssertionError("should never be called"))

    assert twitch.run(log=lambda *a: None) == []


def test_token_request_error_skips_without_crashing(creds, requests_mock):
    requests_mock.post(TOKEN_URL, exc=requests.exceptions.ConnectionError)

    assert twitch.run(log=lambda *a: None) == []


def test_token_http_error_skips_without_crashing(creds, requests_mock):
    requests_mock.post(TOKEN_URL, status_code=401, json={"message": "invalid client"})

    assert twitch.run(log=lambda *a: None) == []


def test_games_request_error_returns_empty_without_crashing(creds, requests_mock):
    requests_mock.post(TOKEN_URL, json={"access_token": "tok"})
    requests_mock.get(GAMES_URL, exc=requests.exceptions.ConnectionError)

    assert twitch.run(log=lambda *a: None) == []


def test_empty_games_page_stops_without_records(creds, requests_mock):
    requests_mock.post(TOKEN_URL, json={"access_token": "tok"})
    requests_mock.get(GAMES_URL, json={"data": []})

    assert twitch.run(log=lambda *a: None) == []


def test_happy_path_single_page_no_cursor(creds, requests_mock):
    requests_mock.post(TOKEN_URL, json={"access_token": "tok"})
    requests_mock.get(GAMES_URL, json={"data": [
        {"name": "Game A"}, {"name": "Game B"},
    ], "pagination": {}})

    records = twitch.run(log=lambda *a: None)

    assert [r["rank"] for r in records] == [1, 2]
    assert [r["name"] for r in records] == ["Game A", "Game B"]


def test_pagination_across_two_pages(creds, requests_mock):
    requests_mock.post(TOKEN_URL, json={"access_token": "tok"})

    def cb(request, context):
        if "after" not in request.qs:
            return {"data": [{"name": "Game A"}, {"name": "Game B"}, {"name": "Game C"}],
                    "pagination": {"cursor": "page2"}}
        return {"data": [{"name": "Game D"}, {"name": "Game E"}], "pagination": {}}
    requests_mock.get(GAMES_URL, json=cb)

    records = twitch.run(log=lambda *a: None)

    assert len(records) == 5  # TWITCH_TOP_GAMES=5, stops once reached
    assert [r["rank"] for r in records] == [1, 2, 3, 4, 5]
    assert [r["name"] for r in records] == ["Game A", "Game B", "Game C", "Game D", "Game E"]
