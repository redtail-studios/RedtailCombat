import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

import scrapers.appstore as appstore

ITUNES_URL = re.compile(r"^https://itunes\.apple\.com/")


@pytest.fixture
def one_app(monkeypatch):
    """Point appstore.run() at a single fake app instead of the real,
    config-driven app list, and stub out disk writes via save()."""
    monkeypatch.setattr(appstore, "GENRES", {
        "action": {"app_store_apps": [{"app_id": "999", "name": "Fake Game"}]},
    })
    monkeypatch.setattr(appstore, "ACTIVE_GENRES", ["action"])
    monkeypatch.setattr(appstore, "APP_STORE_REVIEWS", 1)
    monkeypatch.setattr(appstore, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(appstore, "save", lambda records, data_dir, name, log: records)


def test_network_error_returns_empty_reviews_without_crashing(one_app, requests_mock):
    requests_mock.get(ITUNES_URL, exc=requests.exceptions.ConnectionError)

    records = appstore.run(log=lambda *a: None)

    assert records == [{"source": "appstore", "app_id": "999", "genre": "action",
                        "name": "Fake Game", "reviews": []}]


def test_malformed_response_returns_empty_reviews_without_crashing(one_app, requests_mock):
    requests_mock.get(ITUNES_URL, text="not json")

    records = appstore.run(log=lambda *a: None)

    assert records[0]["reviews"] == []


def test_happy_path_parses_one_review(one_app, requests_mock):
    # Page 1's first entry is app metadata, not a review — it has no
    # "im:rating" key, which is exactly what appstore.py checks for to
    # strip it (see appstore.py:24).
    feed = {"feed": {"entry": [
        {"im:name": {"label": "Fake Game"}},
        {"id": {"label": "review-1"},
         "title": {"label": "Great!"},
         "content": {"label": "Love the combat, would recommend."},
         "im:rating": {"label": "5"}},
    ]}}
    requests_mock.get(ITUNES_URL, json=feed)

    records = appstore.run(log=lambda *a: None)

    reviews = records[0]["reviews"]
    assert len(reviews) == 1
    assert reviews[0]["id"] == "review-1"
    assert reviews[0]["rating"] == 5
    assert reviews[0]["text"] == "Love the combat, would recommend."
    assert "sentiment" in reviews[0]
