import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

import scrapers.wikipedia as wikipedia

WIKI_URL_RE = re.compile(r"^https://wikimedia\.org/api/rest_v1/metrics/pageviews/")


@pytest.fixture
def one_article(monkeypatch):
    monkeypatch.setattr(wikipedia, "WIKI_ARTICLES_COMMON", ["Fake_Article"])
    monkeypatch.setattr(wikipedia, "GENRES", {})
    monkeypatch.setattr(wikipedia, "ACTIVE_GENRES", [])
    monkeypatch.setattr(wikipedia, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(wikipedia, "save", lambda records, data_dir, name, log: records)
    monkeypatch.setattr(wikipedia.time, "sleep", lambda *a: None)


def _views(*counts):
    return {"items": [{"views": c} for c in counts]}


def test_network_error_skips_article_without_crashing(one_article, requests_mock):
    requests_mock.get(WIKI_URL_RE, exc=requests.exceptions.ConnectionError)

    assert wikipedia.run(log=lambda *a: None) == []


def test_non_200_status_skips_article_without_crashing(one_article, requests_mock):
    requests_mock.get(WIKI_URL_RE, status_code=404, json={})

    assert wikipedia.run(log=lambda *a: None) == []


def test_malformed_json_skips_article_without_crashing(one_article, requests_mock):
    requests_mock.get(WIKI_URL_RE, text="not json")

    assert wikipedia.run(log=lambda *a: None) == []


def test_empty_items_produces_no_record(one_article, requests_mock):
    requests_mock.get(WIKI_URL_RE, json={"items": []})

    assert wikipedia.run(log=lambda *a: None) == []


def test_rising_trend(one_article, requests_mock):
    requests_mock.get(WIKI_URL_RE, json=_views(100, 100, 200))  # last > first*1.15

    records = wikipedia.run(log=lambda *a: None)

    assert records[0]["trend"] == "rising"
    assert records[0]["views_total"] == 400


def test_falling_trend(one_article, requests_mock):
    requests_mock.get(WIKI_URL_RE, json=_views(200, 100, 50))  # last < first*0.85

    records = wikipedia.run(log=lambda *a: None)

    assert records[0]["trend"] == "falling"


def test_steady_trend(one_article, requests_mock):
    requests_mock.get(WIKI_URL_RE, json=_views(100, 100, 100))

    records = wikipedia.run(log=lambda *a: None)

    assert records[0]["trend"] == "steady"


def test_genre_tagging(monkeypatch, requests_mock):
    monkeypatch.setattr(wikipedia, "WIKI_ARTICLES_COMMON", [])
    monkeypatch.setattr(wikipedia, "GENRES", {
        "action": {"wiki_article": "Action_Game"},
        "idle": {"wiki_article": None},  # no analog for this genre — should be skipped
    })
    monkeypatch.setattr(wikipedia, "ACTIVE_GENRES", ["action", "idle"])
    monkeypatch.setattr(wikipedia, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(wikipedia, "save", lambda records, data_dir, name, log: records)
    monkeypatch.setattr(wikipedia.time, "sleep", lambda *a: None)
    requests_mock.get(WIKI_URL_RE, json=_views(100, 100))

    records = wikipedia.run(log=lambda *a: None)

    assert len(records) == 1
    assert records[0]["genre"] == "action"
    assert records[0]["article"] == "Action Game"
