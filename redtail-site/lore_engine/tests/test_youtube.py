import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

import scrapers.youtube as youtube

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
COMMENTS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"


@pytest.fixture
def one_query(monkeypatch):
    monkeypatch.setattr(youtube, "YOUTUBE_API_KEY", "fake-key")
    monkeypatch.setattr(youtube, "GENRES", {})
    monkeypatch.setattr(youtube, "ACTIVE_GENRES", [])
    monkeypatch.setattr(youtube, "YT_QUERIES_COMMON", ["fake query"])
    monkeypatch.setattr(youtube, "YT_VIDEOS_PER_Q", 10)
    monkeypatch.setattr(youtube, "YT_COMMENTS_PER", 10)
    monkeypatch.setattr(youtube, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(youtube, "save", lambda records, data_dir, name, log: records)


def test_missing_api_key_skips_without_calling_out(monkeypatch, requests_mock):
    monkeypatch.setattr(youtube, "YOUTUBE_API_KEY", "")
    monkeypatch.setattr(youtube, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(youtube, "save", lambda records, data_dir, name, log: records)
    requests_mock.get(SEARCH_URL, exc=AssertionError("should never be called"))

    assert youtube.run(log=lambda *a: None) == []


def test_search_error_returns_empty_without_crashing(one_query, requests_mock):
    requests_mock.get(SEARCH_URL, exc=requests.exceptions.ConnectionError)

    assert youtube.run(log=lambda *a: None) == []


def test_video_missing_video_id_is_skipped(one_query, requests_mock):
    requests_mock.get(SEARCH_URL, json={"items": [
        {"id": {}, "snippet": {"title": "No ID Video"}},
    ]})

    assert youtube.run(log=lambda *a: None) == []


def test_comments_non_200_returns_no_comments(one_query, requests_mock):
    requests_mock.get(SEARCH_URL, json={"items": [
        {"id": {"videoId": "vid1"}, "snippet": {"title": "A Video"}},
    ]})
    requests_mock.get(COMMENTS_URL, status_code=403, json={})

    records = youtube.run(log=lambda *a: None)

    assert len(records) == 1
    assert records[0]["comments"] == []


def test_comments_request_error_returns_no_comments(one_query, requests_mock):
    requests_mock.get(SEARCH_URL, json={"items": [
        {"id": {"videoId": "vid1"}, "snippet": {"title": "A Video"}},
    ]})
    requests_mock.get(COMMENTS_URL, exc=requests.exceptions.ConnectionError)

    records = youtube.run(log=lambda *a: None)

    assert records[0]["comments"] == []


def test_short_comments_are_filtered_out(one_query, requests_mock):
    requests_mock.get(SEARCH_URL, json={"items": [
        {"id": {"videoId": "vid1"}, "snippet": {"title": "A Video"}},
    ]})
    requests_mock.get(COMMENTS_URL, json={"items": [
        {"snippet": {"topLevelComment": {"snippet": {"textDisplay": "short"}}}},
        {"snippet": {"topLevelComment": {"snippet": {"textDisplay": "a long enough comment"}}}},
    ]})

    records = youtube.run(log=lambda *a: None)

    assert len(records[0]["comments"]) == 1
    assert records[0]["comments"][0]["body"] == "a long enough comment"


def test_happy_path_record_fields(one_query, requests_mock):
    requests_mock.get(SEARCH_URL, json={"items": [
        {"id": {"videoId": "vid1"}, "snippet": {"title": "Great Game Review"}},
    ]})
    requests_mock.get(COMMENTS_URL, json={"items": []})

    records = youtube.run(log=lambda *a: None)

    assert len(records) == 1
    r = records[0]
    assert r["video_id"] == "vid1"
    assert r["title"] == "Great Game Review"
    assert r["url"] == "https://youtube.com/watch?v=vid1"
    assert r["query"] == "fake query"
    assert r["genre"] == "general"


def test_year_filter_adds_published_bounds(one_query, requests_mock):
    requests_mock.get(SEARCH_URL, json={"items": []})

    youtube.run(year=2023, log=lambda *a: None)

    req = requests_mock.request_history[0]
    assert req.qs["publishedafter"] == ["2023-01-01t00:00:00z"]
    assert req.qs["publishedbefore"] == ["2023-12-31t23:59:59z"]
