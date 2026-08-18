import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

import scrapers.steam as steam

STEAMSPY_URL = "https://steamspy.com/api.php"
REVIEWS_URL_RE = re.compile(r"^https://store\.steampowered\.com/appreviews/")


@pytest.fixture
def one_genre(monkeypatch):
    monkeypatch.setattr(steam, "GENRES", {
        "action": {"steam_tag": "Action", "steam_app_ids": []},
    })
    monkeypatch.setattr(steam, "ACTIVE_GENRES", ["action"])
    monkeypatch.setattr(steam, "STEAM_REVIEWS_PER_APP", 5)
    monkeypatch.setattr(steam, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(steam, "save", lambda records, data_dir, name, log: records)
    monkeypatch.setattr(steam.time, "sleep", lambda *a: None)


def _steamspy_cb(tag_response, details_response):
    def cb(request, context):
        req_type = request.qs.get("request", [None])[0]
        if req_type == "tag":
            return tag_response
        if req_type == "appdetails":
            return details_response
        return {}
    return cb


def _review(rec_id, text, voted_up, ts):
    return {"recommendationid": rec_id, "review": text, "voted_up": voted_up,
            "timestamp_created": ts}


def _ts(y, m=1, d=1):
    return int(datetime(y, m, d, tzinfo=timezone.utc).timestamp())


def test_steam_tag_none_skips_genre_without_http_call(monkeypatch, requests_mock):
    monkeypatch.setattr(steam, "GENRES", {"idle": {"steam_tag": None, "steam_app_ids": []}})
    monkeypatch.setattr(steam, "ACTIVE_GENRES", ["idle"])
    monkeypatch.setattr(steam, "STEAM_REVIEWS_PER_APP", 5)
    monkeypatch.setattr(steam, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(steam, "save", lambda records, data_dir, name, log: records)
    monkeypatch.setattr(steam.time, "sleep", lambda *a: None)
    requests_mock.get(STEAMSPY_URL, exc=AssertionError("should never be called"))

    assert steam.run(log=lambda *a: None) == []


def test_top_games_error_falls_back_to_configured_app_ids(monkeypatch, requests_mock):
    monkeypatch.setattr(steam, "GENRES", {"action": {"steam_tag": "Action", "steam_app_ids": ["777"]}})
    monkeypatch.setattr(steam, "ACTIVE_GENRES", ["action"])
    monkeypatch.setattr(steam, "STEAM_REVIEWS_PER_APP", 5)
    monkeypatch.setattr(steam, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(steam, "save", lambda records, data_dir, name, log: records)
    monkeypatch.setattr(steam.time, "sleep", lambda *a: None)

    def cb(request, context):
        if request.qs.get("request", [None])[0] == "tag":
            raise requests.exceptions.ConnectionError()
        return {"name": "Fallback Game"}
    requests_mock.get(STEAMSPY_URL, json=cb)
    requests_mock.get(REVIEWS_URL_RE, json={"reviews": [], "cursor": ""})

    records = steam.run(log=lambda *a: None)

    assert len(records) == 1
    assert records[0]["app_id"] == "777"
    assert records[0]["name"] == "Fallback Game"


def test_dedup_appid_across_genres_keeps_first_genre(monkeypatch, requests_mock):
    monkeypatch.setattr(steam, "GENRES", {
        "action": {"steam_tag": "Action", "steam_app_ids": []},
        "adventure": {"steam_tag": "Adventure", "steam_app_ids": []},
    })
    monkeypatch.setattr(steam, "ACTIVE_GENRES", ["action", "adventure"])
    monkeypatch.setattr(steam, "STEAM_REVIEWS_PER_APP", 5)
    monkeypatch.setattr(steam, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(steam, "save", lambda records, data_dir, name, log: records)
    monkeypatch.setattr(steam.time, "sleep", lambda *a: None)
    requests_mock.get(STEAMSPY_URL, json=_steamspy_cb({"999": {}}, {"name": "Shared Game"}))
    requests_mock.get(REVIEWS_URL_RE, json={"reviews": [], "cursor": ""})

    records = steam.run(log=lambda *a: None)

    assert len(records) == 1  # same app_id "999" claimed by both genres' tag lookups
    assert records[0]["genre"] == "action"


def test_details_error_defaults_name_to_app_id(one_genre, requests_mock):
    def cb(request, context):
        if request.qs.get("request", [None])[0] == "tag":
            return {"999": {}}
        raise requests.exceptions.ConnectionError()
    requests_mock.get(STEAMSPY_URL, json=cb)
    requests_mock.get(REVIEWS_URL_RE, json={"reviews": [], "cursor": ""})

    records = steam.run(log=lambda *a: None)

    assert records[0]["name"] == "999"


def test_reviews_pagination_stops_on_missing_cursor(one_genre, requests_mock):
    requests_mock.get(STEAMSPY_URL, json=_steamspy_cb({"999": {}}, {"name": "Fake Game"}))
    requests_mock.get(REVIEWS_URL_RE, json={
        "reviews": [_review("r1", "a perfectly fine review here", True, _ts(2024))],
        "cursor": "",  # no next cursor -> stop after this page
    })

    records = steam.run(log=lambda *a: None)

    assert len(records[0]["reviews"]) == 1


def test_reviews_pagination_stops_on_empty_batch(one_genre, requests_mock):
    requests_mock.get(STEAMSPY_URL, json=_steamspy_cb({"999": {}}, {"name": "Fake Game"}))
    requests_mock.get(REVIEWS_URL_RE, json={"reviews": [], "cursor": "*next*"})

    records = steam.run(log=lambda *a: None)

    assert records[0]["reviews"] == []


def test_reviews_pagination_stops_when_oldest_predates_year(one_genre, requests_mock):
    requests_mock.get(STEAMSPY_URL, json=_steamspy_cb({"999": {}}, {"name": "Fake Game"}))
    requests_mock.get(REVIEWS_URL_RE, [
        {"json": {"reviews": [_review("r1", "a review from the requested year 2024", True, _ts(2024))],
                   "cursor": "page2"}},
        {"json": {"reviews": [_review("r2", "a review from way before the requested year", True, _ts(2020))],
                   "cursor": "page3"}},
    ])

    records = steam.run(year=2024, log=lambda *a: None)

    ids = [r["id"] for r in records[0]["reviews"]]
    assert ids == ["r1"]  # page 2's old review triggers the break, its own text is post-filtered too


def test_reviews_pagination_stops_when_oldest_predates_since(one_genre, requests_mock):
    requests_mock.get(STEAMSPY_URL, json=_steamspy_cb({"999": {}}, {"name": "Fake Game"}))
    requests_mock.get(REVIEWS_URL_RE, [
        {"json": {"reviews": [_review("r1", "a review that is after the since cutoff", True, _ts(2024, 6))],
                   "cursor": "page2"}},
        {"json": {"reviews": [_review("r2", "a review that predates the since cutoff", True, _ts(2024, 1))],
                   "cursor": "page3"}},
    ])
    since = datetime(2024, 3, 1, tzinfo=timezone.utc)

    records = steam.run(since=since, log=lambda *a: None)

    ids = [r["id"] for r in records[0]["reviews"]]
    assert ids == ["r1"]


def test_reviews_pagination_stops_on_request_error(one_genre, requests_mock):
    requests_mock.get(STEAMSPY_URL, json=_steamspy_cb({"999": {}}, {"name": "Fake Game"}))
    requests_mock.get(REVIEWS_URL_RE, [
        {"json": {"reviews": [_review("r1", "a review from before the network dies", True, _ts(2024))],
                   "cursor": "page2"}},
        {"exc": requests.exceptions.ConnectionError},
    ])

    records = steam.run(log=lambda *a: None)

    assert [r["id"] for r in records[0]["reviews"]] == ["r1"]


def test_reviews_post_filtered_by_year(one_genre, requests_mock):
    # Even though pagination tries to stop early, the results are filtered
    # by `year` again afterward (steam.py:63-65) — simulate the loop
    # over-collecting (single page holds both years) to exercise that.
    requests_mock.get(STEAMSPY_URL, json=_steamspy_cb({"999": {}}, {"name": "Fake Game"}))
    requests_mock.get(REVIEWS_URL_RE, json={
        "reviews": [
            _review("r1", "a review from the correct requested year", True, _ts(2024)),
            _review("r2", "a review from a totally different year", True, _ts(2023)),
        ],
        "cursor": "",
    })

    records = steam.run(year=2024, log=lambda *a: None)

    ids = [r["id"] for r in records[0]["reviews"]]
    assert ids == ["r1"]


def test_short_review_text_is_filtered(one_genre, requests_mock):
    requests_mock.get(STEAMSPY_URL, json=_steamspy_cb({"999": {}}, {"name": "Fake Game"}))
    requests_mock.get(REVIEWS_URL_RE, json={
        "reviews": [_review("r1", "meh", True, _ts(2024))],
        "cursor": "",
    })

    records = steam.run(log=lambda *a: None)

    assert records[0]["reviews"] == []


def test_reviews_capped_at_steam_reviews_per_app(one_genre, requests_mock):
    reviews_data = [_review(f"r{i}", f"a perfectly normal review body number {i}", True, _ts(2024))
                    for i in range(10)]
    requests_mock.get(STEAMSPY_URL, json=_steamspy_cb({"999": {}}, {"name": "Fake Game"}))
    requests_mock.get(REVIEWS_URL_RE, json={"reviews": reviews_data, "cursor": ""})

    records = steam.run(log=lambda *a: None)

    assert len(records[0]["reviews"]) == 5  # STEAM_REVIEWS_PER_APP=5


def test_happy_path_record_fields(one_genre, requests_mock):
    requests_mock.get(STEAMSPY_URL, json=_steamspy_cb({"999": {}}, {
        "name": "Cool Game", "developer": "Cool Studio", "owners": "1,000,000",
        "tags": {f"Tag{i}": 1 for i in range(15)},
        "positive": 800, "negative": 200,
        "average_forever": 300, "average_2weeks": 60,
        "median_forever": 150, "median_2weeks": 30,
    }))
    requests_mock.get(REVIEWS_URL_RE, json={
        "reviews": [_review("r1", "This game is great fun with friends.", True, _ts(2024))],
        "cursor": "",
    })

    records = steam.run(log=lambda *a: None)

    assert len(records) == 1
    r = records[0]
    assert r["name"] == "Cool Game"
    assert r["developer"] == "Cool Studio"
    assert r["positive"] == 800
    assert r["negative"] == 200
    assert len(r["tags"]) == 12  # truncated to 12
    assert r["reviews"][0]["id"] == "r1"
    assert r["reviews"][0]["voted_up"] is True
    assert "sentiment" in r["reviews"][0]
