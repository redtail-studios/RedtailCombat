import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

import scrapers.rawg as rawg

API_URL = "https://api.rawg.io/api/games"


@pytest.fixture
def two_genres(monkeypatch):
    monkeypatch.setattr(rawg, "RAWG_API_KEY", "fake-key")
    monkeypatch.setattr(rawg, "RAWG_PAGE_SIZE", 20)
    monkeypatch.setattr(rawg, "GENRES", {
        "action": {"rawg_genre": "action-slug"},
        "puzzle": {"rawg_genre": "puzzle-slug"},
    })
    monkeypatch.setattr(rawg, "ACTIVE_GENRES", ["action", "puzzle"])
    monkeypatch.setattr(rawg, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(rawg, "save", lambda records, data_dir, name, log: records)


def test_missing_api_key_skips_without_calling_out(monkeypatch, requests_mock):
    monkeypatch.setattr(rawg, "RAWG_API_KEY", "")
    monkeypatch.setattr(rawg, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(rawg, "save", lambda records, data_dir, name, log: records)
    requests_mock.get(API_URL, exc=AssertionError("should never be called"))

    assert rawg.run(log=lambda *a: None) == []


def test_fetch_error_for_one_genre_does_not_block_the_other(two_genres, requests_mock):
    def cb(request, context):
        genre = request.qs.get("genres", [None])[0]
        if genre == "puzzle-slug":
            raise requests.exceptions.ConnectionError()
        return {"results": [{"id": 1, "name": "Action Game"}]}
    requests_mock.get(API_URL, json=cb)

    records = rawg.run(log=lambda *a: None)

    assert len(records) == 1
    assert records[0]["name"] == "Action Game"


def test_dedup_across_genres_keeps_first_genre(two_genres, requests_mock):
    def cb(request, context):
        genre = request.qs.get("genres", [None])[0]
        if genre == "action-slug":
            return {"results": [{"id": 1, "name": "Shared Game"}]}
        return {"results": [{"id": 1, "name": "Shared Game"}, {"id": 2, "name": "Puzzle Only"}]}
    requests_mock.get(API_URL, json=cb)

    records = rawg.run(log=lambda *a: None)

    assert len(records) == 2
    shared = next(r for r in records if r["name"] == "Shared Game")
    assert shared["genre"] == "action"  # first genre to claim id=1 wins


def test_happy_path_record_fields(two_genres, requests_mock):
    def cb(request, context):
        genre = request.qs.get("genres", [None])[0]
        if genre == "action-slug":
            return {"results": [{
                "id": 1, "name": "Cool Game", "released": "2024-03-01",
                "rating": 4.2, "ratings_count": 500, "added": 1000,
                "genres": [{"name": g} for g in
                           ["Action", "Adventure", "RPG", "Shooter", "Indie", "Extra"]],
            }]}
        return {"results": []}
    requests_mock.get(API_URL, json=cb)

    records = rawg.run(year=2024, log=lambda *a: None)

    assert len(records) == 1
    r = records[0]
    assert r["name"] == "Cool Game"
    assert r["rating"] == 4.2
    assert r["added"] == 1000
    assert len(r["rawg_genres"]) == 5  # truncated to 5
    assert "sentiment" in r
