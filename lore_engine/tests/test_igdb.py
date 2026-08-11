import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

import scrapers.igdb as igdb

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
GAMES_URL = "https://api.igdb.com/v4/games"


@pytest.fixture
def one_genre(monkeypatch):
    monkeypatch.setattr(igdb, "TWITCH_CLIENT_ID", "cid")
    monkeypatch.setattr(igdb, "TWITCH_CLIENT_SECRET", "secret")
    monkeypatch.setattr(igdb, "IGDB_TOP_N", 10)
    monkeypatch.setattr(igdb, "GENRES", {"action": {"igdb_genre": 5}})
    monkeypatch.setattr(igdb, "ACTIVE_GENRES", ["action"])
    monkeypatch.setattr(igdb, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(igdb, "save", lambda records, data_dir, name, log: records)
    monkeypatch.setattr(igdb.time, "sleep", lambda *a: None)


def test_missing_credentials_skips_without_calling_out(monkeypatch, requests_mock):
    monkeypatch.setattr(igdb, "TWITCH_CLIENT_ID", "")
    monkeypatch.setattr(igdb, "TWITCH_CLIENT_SECRET", "")
    monkeypatch.setattr(igdb, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(igdb, "save", lambda records, data_dir, name, log: records)
    requests_mock.post(TOKEN_URL, exc=AssertionError("should never be called"))

    assert igdb.run(log=lambda *a: None) == []


def test_token_request_error_skips_without_crashing(one_genre, requests_mock):
    requests_mock.post(TOKEN_URL, exc=requests.exceptions.ConnectionError)

    assert igdb.run(log=lambda *a: None) == []


def test_token_http_error_skips_without_crashing(one_genre, requests_mock):
    requests_mock.post(TOKEN_URL, status_code=401, json={"message": "invalid client"})

    assert igdb.run(log=lambda *a: None) == []


def test_genre_without_igdb_analog_makes_no_request(monkeypatch, requests_mock):
    monkeypatch.setattr(igdb, "TWITCH_CLIENT_ID", "cid")
    monkeypatch.setattr(igdb, "TWITCH_CLIENT_SECRET", "secret")
    monkeypatch.setattr(igdb, "IGDB_TOP_N", 10)
    monkeypatch.setattr(igdb, "GENRES", {"idle": {"igdb_genre": None}})
    monkeypatch.setattr(igdb, "ACTIVE_GENRES", ["idle"])
    monkeypatch.setattr(igdb, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(igdb, "save", lambda records, data_dir, name, log: records)
    monkeypatch.setattr(igdb.time, "sleep", lambda *a: None)
    requests_mock.post(TOKEN_URL, json={"access_token": "tok"})
    requests_mock.post(GAMES_URL, exc=AssertionError("should never be called"))

    assert igdb.run(log=lambda *a: None) == []


def test_fetch_error_for_one_genre_does_not_crash(one_genre, requests_mock):
    requests_mock.post(TOKEN_URL, json={"access_token": "tok"})
    requests_mock.post(GAMES_URL, exc=requests.exceptions.ConnectionError)

    assert igdb.run(log=lambda *a: None) == []


def test_happy_path_record_fields(one_genre, requests_mock):
    requests_mock.post(TOKEN_URL, json={"access_token": "tok"})
    requests_mock.post(GAMES_URL, json=[{
        "name": "Upcoming Game", "hypes": 42, "rating": 87.654, "rating_count": 12,
        "first_release_date": 1700000000,
        "involved_companies": [
            {"company": {"name": "Studio A"}},
            {"company": {}},  # missing name -> filtered out
            {},                # missing company entirely -> filtered out
        ],
    }])

    records = igdb.run(log=lambda *a: None)

    assert len(records) == 1
    r = records[0]
    assert r["name"] == "Upcoming Game"
    assert r["hypes"] == 42
    assert r["rating"] == 87.7  # rounded to 1 decimal
    assert r["companies"] == ["Studio A"]
    assert r["genre"] == "action"
