import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import scrapers.reddit_history as rh

API_RE = rh.API


def _post(pid, title="A post", score=1, created=1672617600, selftext="body"):  # 2023-01-02
    return {"id": pid, "title": title, "selftext": selftext, "score": score,
            "created_utc": created, "author": "u",
            "num_comments": 0}


@pytest.fixture(autouse=True)
def config(monkeypatch):
    monkeypatch.setattr(rh, "SUBREDDITS_COMMON", [])
    monkeypatch.setattr(rh, "SUBREDDITS_BROAD", ["broadsub"])
    monkeypatch.setattr(rh, "REDDIT_KEYWORDS_COMMON", ["indie"])
    monkeypatch.setattr(rh, "GENRES", {"action": {"subreddits": ["actionsub"],
                                                    "reddit_keywords": ["shooter"]}})
    monkeypatch.setattr(rh, "ACTIVE_GENRES", ["action"])
    monkeypatch.setattr(rh, "REDDIT_POST_LIMIT", 2)
    monkeypatch.setattr(rh, "REQUEST_DELAY", 0)
    monkeypatch.setattr(rh, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(rh, "save", lambda records, data_dir, name, log: records)
    monkeypatch.setattr(rh.time, "sleep", lambda s: None)


def test_month_windows_cover_the_year():
    w = rh._month_windows(2023)
    assert len(w) == 12
    assert w[0] == ("2023-01-01", "2023-02-01")
    assert w[-1] == ("2023-12-01", "2024-01-01")


def test_fetch_returns_data(requests_mock):
    requests_mock.get(API_RE, json={"data": [_post("a")]})
    assert [p["id"] for p in rh._fetch({}, print)] == ["a"]


def test_fetch_retries_transient_422_then_succeeds(requests_mock):
    requests_mock.get(API_RE, [{"status_code": 422, "json": {"data": None, "error": "Timeout"}},
                               {"status_code": 200, "json": {"data": [_post("a")]}}])
    assert len(rh._fetch({}, lambda *a: None)) == 1


def test_fetch_returns_none_when_every_try_fails(requests_mock):
    requests_mock.get(API_RE, status_code=422, json={"data": None})
    assert rh._fetch({}, lambda *a: None, tries=3) is None


def test_fetch_waits_for_ratelimit_reset(requests_mock, monkeypatch):
    waits = []
    monkeypatch.setattr(rh.time, "sleep", waits.append)
    requests_mock.get(API_RE, [{"status_code": 429, "headers": {"x-ratelimit-reset": "9"}},
                               {"status_code": 200, "json": {"data": []}}])
    rh._fetch({}, lambda *a: None)
    assert waits == [10]


def test_run_requires_a_year():
    with pytest.raises(ValueError):
        rh.run(year=None)


def test_run_keeps_top_scoring_posts_and_drops_removed(requests_mock):
    def respond(request, context):
        sub = request.qs["subreddit"][0]
        if sub != "actionsub":
            return {"data": []}
        if request.qs["after"][0] != "2023-01-01":
            return {"data": []}
        return {"data": [_post("a", score=5), _post("b", score=50), _post("c", score=20),
                         _post("d", score=99, selftext="[removed]"), _post("a", score=5)]}
    requests_mock.get(API_RE, json=respond)

    records = rh.run(year=2023, log=lambda *a: None)

    assert [r["title"] for r in records] == ["A post", "A post"]
    assert [r["score"] for r in records] == [50, 20]  # top 2 by score; removed + dup dropped
    assert records[0]["genre"] == "action"
    assert records[0]["created"] == "2023-01-02"
    assert records[0]["url"] == "https://www.reddit.com/comments/b/"


def test_run_filters_broad_subs_by_keyword(requests_mock):
    def respond(request, context):
        if request.qs["subreddit"][0] != "broadsub" or request.qs["after"][0] != "2023-01-01":
            return {"data": []}
        return {"data": [_post("a", title="best shooter ever"),
                         _post("b", title="an indie darling"),
                         _post("c", title="unrelated chatter")]}
    requests_mock.get(API_RE, json=respond)

    records = rh.run(year=2023, log=lambda *a: None)

    assert {(r["title"], r["genre"]) for r in records} == {
        ("best shooter ever", "action"), ("an indie darling", "general")}


def test_run_logs_subs_with_no_archive_coverage(requests_mock):
    requests_mock.get(API_RE, json={"data": []})
    logs = []

    records = rh.run(year=2023, log=logs.append)

    assert records == []
    assert any("no archive coverage for: actionsub, broadsub" in m for m in logs)


def test_fetch_does_not_retry_client_errors(requests_mock):
    requests_mock.get(API_RE, status_code=400, json={"data": None, "error": "bad field"})
    assert rh._fetch({}, lambda *a: None) is None
    assert requests_mock.call_count == 1


def test_requested_fields_exclude_ones_the_api_rejects():
    assert "permalink" not in rh.FIELDS.split(",")


def test_num_parts_groups_subreddits(monkeypatch):
    monkeypatch.setattr(rh, "GROUP_SIZE", 1)
    assert rh.num_parts() == 2  # actionsub + broadsub
    monkeypatch.setattr(rh, "GROUP_SIZE", 5)
    assert rh.num_parts() == 1


def test_run_part_only_queries_its_group(requests_mock, monkeypatch):
    monkeypatch.setattr(rh, "GROUP_SIZE", 1)
    seen = set()
    def respond(request, context):
        seen.add(request.qs["subreddit"][0])
        return {"data": []}
    requests_mock.get(API_RE, json=respond)

    rh.run(year=2023, log=lambda *a: None, part=1)

    assert seen == {"broadsub"}  # part 0 would be actionsub


def test_run_part_raises_when_out_of_time(requests_mock, monkeypatch):
    monkeypatch.setattr(rh, "TIME_BUDGET_SECONDS", -1)
    requests_mock.get(API_RE, json={"data": []})

    with pytest.raises(rh.BudgetExceeded):
        rh.run(year=2023, log=lambda *a: None, part=0)


def test_run_without_part_stops_quietly_at_budget(requests_mock, monkeypatch):
    monkeypatch.setattr(rh, "TIME_BUDGET_SECONDS", -1)
    requests_mock.get(API_RE, json={"data": []})

    assert rh.run(year=2023, log=lambda *a: None) == []
