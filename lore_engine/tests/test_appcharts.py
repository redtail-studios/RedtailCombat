import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

import scrapers.appcharts as appcharts

ITUNES_URL = re.compile(r"^https://itunes\.apple\.com/")


@pytest.fixture
def one_genre(monkeypatch):
    """Point appcharts.run() at a single fake genre instead of the real,
    config-driven genre list, and stub out disk writes via save()."""
    monkeypatch.setattr(appcharts, "GENRES", {
        "action": {"apple_chart_genre": "7003", "label": "Action"},
    })
    monkeypatch.setattr(appcharts, "ACTIVE_GENRES", ["action"])
    monkeypatch.setattr(appcharts, "APPCHARTS_COUNTRY", "us")
    monkeypatch.setattr(appcharts, "APPCHARTS_LIMIT", 10)
    monkeypatch.setattr(appcharts, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(appcharts, "save", lambda records, data_dir, name, log: records)


def test_network_error_returns_empty_without_crashing(one_genre, requests_mock):
    requests_mock.get(ITUNES_URL, exc=requests.exceptions.ConnectionError)

    assert appcharts.run(log=lambda *a: None) == []


def test_malformed_response_returns_empty_without_crashing(one_genre, requests_mock):
    requests_mock.get(ITUNES_URL, text="not json")

    assert appcharts.run(log=lambda *a: None) == []


def test_genre_without_chart_mapping_is_skipped(monkeypatch, requests_mock):
    monkeypatch.setattr(appcharts, "GENRES", {"puzzle": {"apple_chart_genre": None, "label": "Puzzle"}})
    monkeypatch.setattr(appcharts, "ACTIVE_GENRES", ["puzzle"])
    monkeypatch.setattr(appcharts, "APPCHARTS_COUNTRY", "us")
    monkeypatch.setattr(appcharts, "APPCHARTS_LIMIT", 10)
    monkeypatch.setattr(appcharts, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(appcharts, "save", lambda records, data_dir, name, log: records)
    # If run() ever calls out for a genre with no chart mapping, fail loudly
    # instead of silently returning [] for the wrong reason.
    requests_mock.get(ITUNES_URL, exc=AssertionError("should never be called"))

    assert appcharts.run(log=lambda *a: None) == []


def test_one_chart_failing_does_not_block_the_other(one_genre, requests_mock):
    good_feed = {"feed": {"entry": [
        {"im:name": {"label": "Puzzle King"}, "id": {"attributes": {"im:id": "12345"}},
         "summary": {"label": "Fun puzzle game"}},
    ]}}
    requests_mock.get(re.compile(r"topfreeapplications"), json=good_feed)
    requests_mock.get(re.compile(r"topgrossingapplications"), exc=requests.exceptions.ConnectionError)

    records = appcharts.run(log=lambda *a: None)

    assert len(records) == 1
    assert records[0]["chart"] == "top free"


def test_happy_path_ranks_and_skips_missing_name(one_genre, requests_mock):
    # Middle entry has no "im:name" and should be dropped — but rank comes
    # from enumerate() over the raw entry list, so the surviving entries
    # keep ranks 1 and 3, not 1 and 2 (appcharts.py:44-47).
    feed = {"feed": {"entry": [
        {"im:name": {"label": "Puzzle King"}, "id": {"attributes": {"im:id": "12345"}},
         "summary": {"label": "A" * 400}},
        {"id": {"attributes": {"im:id": "999"}}, "summary": {"label": "no name here"}},
        {"im:name": {"label": "Second App"}, "id": {"attributes": {"im:id": "67890"}},
         "summary": {"label": "Great app"}},
    ]}}
    requests_mock.get(ITUNES_URL, json=feed)

    records = appcharts.run(log=lambda *a: None)

    # Two charts (top free + top grossing) each parse the same 3 entries,
    # keeping the 2 with a name — 4 records total.
    assert len(records) == 4
    free_ranks = sorted(r["rank"] for r in records if r["chart"] == "top free")
    assert free_ranks == [1, 3]

    first = next(r for r in records if r["name"] == "Puzzle King" and r["chart"] == "top free")
    assert first["app_id"] == "12345"
    assert "A" * 300 in first["text"]
    assert "A" * 301 not in first["text"]  # summary truncated to 300 chars
