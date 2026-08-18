import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

import scrapers.hackernews as hackernews

SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
ITEM_URL_RE = re.compile(r"^https://hn\.algolia\.com/api/v1/items/")


@pytest.fixture
def one_query(monkeypatch):
    """Point hackernews.run() at a single fake query instead of the real,
    config-driven query list, and stub out disk writes via save()."""
    monkeypatch.setattr(hackernews, "GENRES", {})
    monkeypatch.setattr(hackernews, "ACTIVE_GENRES", [])
    monkeypatch.setattr(hackernews, "HN_QUERIES_COMMON", ["fake query"])
    monkeypatch.setattr(hackernews, "HN_HITS_PER_Q", 10)
    monkeypatch.setattr(hackernews, "HN_COMMENTS_PER", 5)
    monkeypatch.setattr(hackernews, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(hackernews, "save", lambda records, data_dir, name, log: records)


def test_search_request_error_skips_query_without_crashing(one_query, requests_mock):
    requests_mock.get(SEARCH_URL, exc=requests.exceptions.ConnectionError)

    assert hackernews.run(log=lambda *a: None) == []


def test_dedup_across_queries_by_object_id(monkeypatch, requests_mock):
    # Two distinct queries (a common one + a genre one) both surface the
    # same story — the module-level `seen` set should keep only one copy.
    monkeypatch.setattr(hackernews, "GENRES", {"action": {"hn_query": "second query"}})
    monkeypatch.setattr(hackernews, "ACTIVE_GENRES", ["action"])
    monkeypatch.setattr(hackernews, "HN_QUERIES_COMMON", ["first query"])
    monkeypatch.setattr(hackernews, "HN_HITS_PER_Q", 10)
    monkeypatch.setattr(hackernews, "HN_COMMENTS_PER", 5)
    monkeypatch.setattr(hackernews, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(hackernews, "save", lambda records, data_dir, name, log: records)

    requests_mock.get(SEARCH_URL, json={"hits": [{"objectID": "123", "title": "Same Story"}]})
    requests_mock.get(ITEM_URL_RE, json={"children": []})

    records = hackernews.run(log=lambda *a: None)

    assert len(records) == 1
    assert records[0]["id"] == "123"


def test_item_fetch_failure_keeps_story_with_no_comments(one_query, requests_mock):
    requests_mock.get(SEARCH_URL, json={"hits": [{"objectID": "1", "title": "Story"}]})
    requests_mock.get(ITEM_URL_RE, exc=requests.exceptions.ConnectionError)

    records = hackernews.run(log=lambda *a: None)

    assert len(records) == 1
    assert records[0]["comments"] == []


def test_title_falls_back_to_story_title(one_query, requests_mock):
    requests_mock.get(ITEM_URL_RE, json={"children": []})
    requests_mock.get(SEARCH_URL, json={"hits": [{"objectID": "1", "story_title": "Fallback Title"}]})

    records = hackernews.run(log=lambda *a: None)

    assert records[0]["title"] == "Fallback Title"


def test_comments_sliced_before_length_filter(one_query, requests_mock):
    # hackernews.py:59 slices to HN_COMMENTS_PER *before* filtering out
    # short bodies, not after. So a short comment among the first
    # HN_COMMENTS_PER children wastes a slot instead of being skipped in
    # favor of a later long one — this pins down that (surprising) order.
    requests_mock.get(SEARCH_URL, json={"hits": [{"objectID": "1", "title": "Story"}]})
    children = [{"text": "short"}] + [
        {"text": f"a sufficiently long comment body, number {i}"} for i in range(6)
    ]
    requests_mock.get(ITEM_URL_RE, json={"children": children})

    records = hackernews.run(log=lambda *a: None)

    # HN_COMMENTS_PER=5 -> only the first 5 children are considered at all;
    # the short one among them is then dropped, leaving 4, not 5.
    assert len(records[0]["comments"]) == 4


def test_numeric_filters_built_for_year(one_query, requests_mock):
    requests_mock.get(SEARCH_URL, json={"hits": []})
    start = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())
    end = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp())

    hackernews.run(year=2023, log=lambda *a: None)

    req = requests_mock.request_history[0]
    assert req.qs["numericfilters"] == [f"created_at_i>={start},created_at_i<{end}"]


def test_since_raises_lower_bound_without_year(one_query, requests_mock):
    requests_mock.get(SEARCH_URL, json={"hits": []})
    since = datetime(2024, 6, 1, tzinfo=timezone.utc)

    hackernews.run(since=since, log=lambda *a: None)

    req = requests_mock.request_history[0]
    assert req.qs["numericfilters"] == [f"created_at_i>={int(since.timestamp())}"]
