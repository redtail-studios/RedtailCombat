import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

import scrapers.steamtrending as steamtrending

URL = "https://steamspy.com/api.php"


@pytest.fixture
def trending(monkeypatch):
    monkeypatch.setattr(steamtrending, "STEAM_TRENDING_N", 10)
    monkeypatch.setattr(steamtrending, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(steamtrending, "save", lambda records, data_dir, name, log: records)


def test_network_error_returns_empty_without_crashing(trending, requests_mock):
    requests_mock.get(URL, exc=requests.exceptions.ConnectionError)

    assert steamtrending.run(log=lambda *a: None) == []


def test_non_200_status_returns_empty_without_crashing(trending, requests_mock):
    requests_mock.get(URL, status_code=503, text="")

    assert steamtrending.run(log=lambda *a: None) == []


def test_malformed_json_returns_empty_without_crashing(trending, requests_mock):
    requests_mock.get(URL, text="not json")

    assert steamtrending.run(log=lambda *a: None) == []


def test_happy_path_parses_game(trending, requests_mock):
    requests_mock.get(URL, json={
        "123": {"name": "Cool Game", "owners": "1,000,000", "ccu": 5000,
                "tags": {"Action": 1, "Indie": 1}},
    })

    records = steamtrending.run(log=lambda *a: None)

    assert len(records) == 1
    r = records[0]
    assert r["rank"] == 1
    assert r["app_id"] == "123"
    assert r["name"] == "Cool Game"
    assert r["owners"] == "1,000,000"
    assert r["ccu"] == 5000
    assert r["tags"] == ["Action", "Indie"]


def test_name_falls_back_to_appid_when_missing(trending, requests_mock):
    requests_mock.get(URL, json={"456": {"owners": "500", "ccu": 10}})

    records = steamtrending.run(log=lambda *a: None)

    assert records[0]["name"] == "456"


def test_null_tags_default_to_empty(trending, requests_mock):
    requests_mock.get(URL, json={"789": {"name": "Tagless Game", "tags": None}})

    records = steamtrending.run(log=lambda *a: None)

    assert records[0]["tags"] == []


def test_trending_n_limit_is_applied(monkeypatch, requests_mock):
    monkeypatch.setattr(steamtrending, "STEAM_TRENDING_N", 2)
    monkeypatch.setattr(steamtrending, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(steamtrending, "save", lambda records, data_dir, name, log: records)
    requests_mock.get(URL, json={str(i): {"name": f"Game {i}"} for i in range(5)})

    records = steamtrending.run(log=lambda *a: None)

    assert len(records) == 2
