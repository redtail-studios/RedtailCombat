import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

import scrapers.gdelt as gdelt

URL = "https://api.gdeltproject.org/api/v2/doc/doc"


@pytest.fixture
def one_query(monkeypatch):
    monkeypatch.setattr(gdelt, "GENRES", {})
    monkeypatch.setattr(gdelt, "ACTIVE_GENRES", [])
    monkeypatch.setattr(gdelt, "GDELT_QUERIES_COMMON", ["fake query"])
    monkeypatch.setattr(gdelt, "GDELT_HITS_PER_Q", 10)
    monkeypatch.setattr(gdelt, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(gdelt, "save", lambda records, data_dir, name, log: records)
    monkeypatch.setattr(gdelt.time, "sleep", lambda *a: None)


def test_network_error_returns_empty_without_crashing(one_query, requests_mock):
    requests_mock.get(URL, exc=requests.exceptions.ConnectionError)

    assert gdelt.run(log=lambda *a: None) == []


def test_rate_limit_plain_text_response_returns_empty(one_query, requests_mock):
    # GDELT returns its rate-limit notice as plain text with a 200 status,
    # so r.json() raises ValueError rather than an HTTP error being raised.
    requests_mock.get(URL, text="rate limit exceeded, please wait 5 seconds")

    assert gdelt.run(log=lambda *a: None) == []


def test_multi_word_query_gets_quoted(one_query, monkeypatch, requests_mock):
    monkeypatch.setattr(gdelt, "GDELT_QUERIES_COMMON", ["mobile game"])
    requests_mock.get(URL, json={"articles": []})

    gdelt.run(log=lambda *a: None)

    req = requests_mock.request_history[0]
    assert req.qs["query"] == ['"mobile game"']


def test_single_word_query_is_not_quoted(one_query, monkeypatch, requests_mock):
    monkeypatch.setattr(gdelt, "GDELT_QUERIES_COMMON", ["roguelike"])
    requests_mock.get(URL, json={"articles": []})

    gdelt.run(log=lambda *a: None)

    req = requests_mock.request_history[0]
    assert req.qs["query"] == ["roguelike"]


def test_year_filter_drops_wrong_year(one_query, requests_mock):
    requests_mock.get(URL, json={"articles": [
        {"title": "Old game news article here", "seendate": "20220101T120000Z"},
    ]})

    assert gdelt.run(year=2024, log=lambda *a: None) == []


def test_since_filter_drops_articles_at_or_before_since(one_query, requests_mock):
    # Defensive client-side re-check even though `startdatetime` should
    # already have excluded this server-side (gdelt.py:72-75).
    requests_mock.get(URL, json={"articles": [
        {"title": "Stale article about a game", "seendate": "20240101T120000Z"},
    ]})
    since = datetime(2024, 6, 1, tzinfo=timezone.utc)

    assert gdelt.run(since=since, log=lambda *a: None) == []


def test_since_sets_startdatetime_param(one_query, requests_mock):
    requests_mock.get(URL, json={"articles": []})
    since = datetime(2024, 6, 1, 12, 30, 0, tzinfo=timezone.utc)

    gdelt.run(since=since, log=lambda *a: None)

    req = requests_mock.request_history[0]
    assert req.qs["startdatetime"] == ["20240601123000"]


def test_short_title_is_filtered_out(one_query, requests_mock):
    requests_mock.get(URL, json={"articles": [
        {"title": "Hi", "seendate": "20240101T120000Z"},
    ]})

    assert gdelt.run(log=lambda *a: None) == []


def test_happy_path_record_fields(one_query, requests_mock):
    requests_mock.get(URL, json={"articles": [
        {"title": "Big new mobile game launches today", "seendate": "20240601T120000Z",
         "url": "http://example.com/1", "domain": "example.com",
         "sourcecountry": "United States", "language": "English"},
    ]})

    records = gdelt.run(log=lambda *a: None)

    assert len(records) == 1
    r = records[0]
    assert r["title"] == "Big new mobile game launches today"
    assert r["domain"] == "example.com"
    assert r["sourcecountry"] == "United States"
    assert r["language"] == "English"
    assert r["genre"] == "general"
    assert "sentiment" in r
