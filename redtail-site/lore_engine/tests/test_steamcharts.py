import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

import scrapers.steamcharts as steamcharts

URL = "https://store.steampowered.com/api/featuredcategories"


@pytest.fixture
def charts(monkeypatch):
    monkeypatch.setattr(steamcharts, "STEAM_CHARTS_PER_LIST", 10)
    monkeypatch.setattr(steamcharts, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(steamcharts, "save", lambda records, data_dir, name, log: records)


def test_network_error_returns_empty_without_crashing(charts, requests_mock):
    requests_mock.get(URL, exc=requests.exceptions.ConnectionError)

    assert steamcharts.run(log=lambda *a: None) == []


def test_malformed_json_returns_empty_without_crashing(charts, requests_mock):
    requests_mock.get(URL, text="not json")

    assert steamcharts.run(log=lambda *a: None) == []


def test_missing_list_key_defaults_to_empty(charts, requests_mock):
    # Only "top_sellers" present — "new_releases"/"specials" absent entirely,
    # not just empty, should be handled by the `or {}` default.
    requests_mock.get(URL, json={"top_sellers": {"items": [{"id": 1, "name": "Game A"}]}})

    records = steamcharts.run(log=lambda *a: None)

    assert len(records) == 1
    assert records[0]["chart"] == "top seller"


def test_items_missing_name_are_skipped(charts, requests_mock):
    requests_mock.get(URL, json={
        "top_sellers": {"items": [{"id": 1}, {"id": 2, "name": "Game B"}]},
    })

    records = steamcharts.run(log=lambda *a: None)

    assert len(records) == 1
    assert records[0]["name"] == "Game B"


def test_happy_path_ranks_independently_per_list(charts, requests_mock):
    requests_mock.get(URL, json={
        "top_sellers": {"items": [{"id": 1, "name": "Game A"}, {"id": 2, "name": "Game B"}]},
        "new_releases": {"items": [{"id": 3, "name": "Game C"}]},
        "specials": {"items": []},
    })

    records = steamcharts.run(log=lambda *a: None)

    assert len(records) == 3
    sellers = [r for r in records if r["chart"] == "top seller"]
    assert [r["rank"] for r in sellers] == [1, 2]
    releases = next(r for r in records if r["chart"] == "new release")
    assert releases["rank"] == 1
    assert releases["name"] == "Game C"


def test_per_list_limit_is_applied(charts, monkeypatch, requests_mock):
    monkeypatch.setattr(steamcharts, "STEAM_CHARTS_PER_LIST", 2)
    requests_mock.get(URL, json={
        "top_sellers": {"items": [{"id": i, "name": f"Game {i}"} for i in range(5)]},
    })

    records = steamcharts.run(log=lambda *a: None)

    assert len(records) == 2
