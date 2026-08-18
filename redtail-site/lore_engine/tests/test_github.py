import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

import scrapers.github as github

API_URL = "https://api.github.com/search/repositories"


@pytest.fixture
def one_query(monkeypatch):
    """Point github.run() at a single fake query instead of the real,
    config-driven query list, stub out disk writes via save(), and skip the
    real rate-limit sleeps (5s/6s per query) so tests run instantly."""
    monkeypatch.setattr(github, "GITHUB_QUERIES", ["fake query"])
    monkeypatch.setattr(github, "GITHUB_PER_Q", 10)
    monkeypatch.setattr(github, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(github, "save", lambda records, data_dir, name, log: records)
    monkeypatch.setattr(github.time, "sleep", lambda *a: None)


def test_network_error_skips_query_without_crashing(one_query, requests_mock):
    requests_mock.get(API_URL, exc=requests.exceptions.ConnectionError)

    assert github.run(log=lambda *a: None) == []


def test_non_200_status_skips_query_without_crashing(one_query, requests_mock):
    requests_mock.get(API_URL, status_code=403, json={"message": "rate limited"})

    assert github.run(log=lambda *a: None) == []


def test_dedup_by_full_name_across_queries(monkeypatch, requests_mock):
    monkeypatch.setattr(github, "GITHUB_QUERIES", ["query one", "query two"])
    monkeypatch.setattr(github, "GITHUB_PER_Q", 10)
    monkeypatch.setattr(github, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(github, "save", lambda records, data_dir, name, log: records)
    monkeypatch.setattr(github.time, "sleep", lambda *a: None)
    requests_mock.get(API_URL, json={"items": [
        {"full_name": "acme/game-engine", "stargazers_count": 42, "language": "Rust"},
    ]})

    records = github.run(log=lambda *a: None)

    assert len(records) == 1
    assert records[0]["repo"] == "acme/game-engine"


def test_topics_truncated_to_eight(one_query, requests_mock):
    requests_mock.get(API_URL, json={"items": [
        {"full_name": "acme/game-engine", "stargazers_count": 1,
         "topics": [f"topic{i}" for i in range(12)]},
    ]})

    records = github.run(log=lambda *a: None)

    assert len(records[0]["topics"]) == 8
    assert records[0]["topics"] == [f"topic{i}" for i in range(8)]


def test_repo_missing_full_name_is_skipped(one_query, requests_mock):
    requests_mock.get(API_URL, json={"items": [{"stargazers_count": 5}]})

    assert github.run(log=lambda *a: None) == []
