import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

import scrapers.reddit as reddit

FEED_URL_RE = re.compile(r"^https://www\.reddit\.com/r/")


# ---------------------------------------------------------------------------
# _clean
# ---------------------------------------------------------------------------

def test_clean_strips_tags_and_unescapes_entities():
    assert reddit._clean("Some &lt;b&gt;bold&lt;/b&gt;   text.") == "Some bold text."


def test_clean_handles_none_and_empty():
    assert reddit._clean(None) == ""
    assert reddit._clean("") == ""


# ---------------------------------------------------------------------------
# _retry_wait
# ---------------------------------------------------------------------------

def test_retry_wait_prefers_retry_after_over_ratelimit_reset():
    wait = reddit._retry_wait({"retry-after": "10", "x-ratelimit-reset": "999"}, default=5)
    assert wait == 11  # +1s buffer


def test_retry_wait_falls_back_to_ratelimit_reset():
    wait = reddit._retry_wait({"x-ratelimit-reset": "20"}, default=5)
    assert wait == 21


def test_retry_wait_caps_at_max_rate_limit_wait():
    wait = reddit._retry_wait({"retry-after": "10000"}, default=5)
    assert wait == reddit.MAX_RATE_LIMIT_WAIT


def test_retry_wait_falls_back_to_default_when_headers_missing():
    assert reddit._retry_wait({}, default=7) == 7


def test_retry_wait_falls_back_to_default_on_unparseable_header():
    wait = reddit._retry_wait({"retry-after": "not-a-number"}, default=7)
    assert wait == 7


# ---------------------------------------------------------------------------
# _fetch
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def no_real_sleeps(monkeypatch):
    monkeypatch.setattr(reddit.time, "sleep", lambda *a: None)


def test_fetch_returns_text_on_200(requests_mock):
    requests_mock.get(FEED_URL_RE, text="<feed></feed>")

    assert reddit._fetch("https://www.reddit.com/r/fake/hot/.rss", {}, log=lambda *a: None) == "<feed></feed>"


def test_fetch_retries_on_network_error_then_succeeds(requests_mock):
    requests_mock.get(FEED_URL_RE, [
        {"exc": requests.exceptions.ConnectionError},
        {"text": "<feed>ok</feed>"},
    ])

    result = reddit._fetch("https://www.reddit.com/r/fake/hot/.rss", {}, log=lambda *a: None)

    assert result == "<feed>ok</feed>"


def test_fetch_gives_up_after_exhausting_tries(requests_mock):
    requests_mock.get(FEED_URL_RE, exc=requests.exceptions.ConnectionError)

    result = reddit._fetch("https://www.reddit.com/r/fake/hot/.rss", {}, log=lambda *a: None, tries=3)

    assert result is None
    assert len(requests_mock.request_history) == 3


def test_fetch_retries_on_429_then_succeeds(requests_mock):
    requests_mock.get(FEED_URL_RE, [
        {"status_code": 429, "headers": {"retry-after": "1"}},
        {"text": "<feed>ok</feed>"},
    ])

    result = reddit._fetch("https://www.reddit.com/r/fake/hot/.rss", {}, log=lambda *a: None)

    assert result == "<feed>ok</feed>"


def test_fetch_returns_none_immediately_on_403_without_retrying(requests_mock):
    requests_mock.get(FEED_URL_RE, status_code=403)

    result = reddit._fetch("https://www.reddit.com/r/fake/hot/.rss", {}, log=lambda *a: None)

    assert result is None
    assert len(requests_mock.request_history) == 1  # no retry on 403


def test_fetch_returns_none_immediately_on_404_without_retrying(requests_mock):
    requests_mock.get(FEED_URL_RE, status_code=404)

    result = reddit._fetch("https://www.reddit.com/r/fake/hot/.rss", {}, log=lambda *a: None)

    assert result is None
    assert len(requests_mock.request_history) == 1


def test_fetch_retries_on_other_status_then_gives_up(requests_mock):
    requests_mock.get(FEED_URL_RE, status_code=500)

    result = reddit._fetch("https://www.reddit.com/r/fake/hot/.rss", {}, log=lambda *a: None, tries=2)

    assert result is None
    assert len(requests_mock.request_history) == 2


# ---------------------------------------------------------------------------
# _parse
# ---------------------------------------------------------------------------

def _atom(entries_xml: str) -> str:
    return f'<feed xmlns="http://www.w3.org/2005/Atom">{entries_xml}</feed>'


def test_parse_malformed_xml_returns_empty():
    assert reddit._parse("not xml at all <<<") == []


def test_parse_atom_entry_fields():
    xml = _atom(
        '<entry><id>t3_abc</id><title>Cool Post</title>'
        '<content>Some &lt;b&gt;content&lt;/b&gt;.</content>'
        '<link href="https://reddit.com/r/fake/abc"/>'
        '<author><name>u/someone</name></author>'
        '<published>2024-06-01T12:00:00Z</published></entry>'
    )

    posts = reddit._parse(xml)

    assert len(posts) == 1
    p = posts[0]
    assert p["id"] == "t3_abc"
    assert p["title"] == "Cool Post"
    assert p["text"] == "Some content ."  # tag-stripping leaves a space before the period
    assert p["link"] == "https://reddit.com/r/fake/abc"
    assert p["author"] == "u/someone"
    assert p["year"] == 2024


def test_parse_falls_back_to_updated_when_published_missing():
    xml = _atom('<entry><id>t3_abc</id><updated>2023-01-01T00:00:00Z</updated></entry>')

    posts = reddit._parse(xml)

    assert posts[0]["year"] == 2023


def test_parse_missing_link_and_author_default_to_empty():
    xml = _atom('<entry><id>t3_abc</id><title>No Link Or Author</title></entry>')

    posts = reddit._parse(xml)

    assert posts[0]["link"] == ""
    assert posts[0]["author"] == ""
    assert posts[0]["year"] is None


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------

def _feed_url(sub):
    return f"https://www.reddit.com/r/{sub}/hot/.rss"


def _entry(post_id, title, content="", published="2024-06-01T12:00:00Z"):
    return (f'<entry><id>{post_id}</id><title>{title}</title><content>{content}</content>'
            f'<link href="https://reddit.com/r/x/{post_id}"/><published>{published}</published></entry>')


@pytest.fixture
def config(monkeypatch):
    monkeypatch.setattr(reddit, "SUBREDDITS_COMMON", ["commonsub"])
    monkeypatch.setattr(reddit, "SUBREDDITS_BROAD", ["broadsub"])
    monkeypatch.setattr(reddit, "REDDIT_KEYWORDS_COMMON", ["indie"])
    monkeypatch.setattr(reddit, "GENRES", {"action": {"subreddits": ["actionsub"],
                                                        "reddit_keywords": ["shooter"]}})
    monkeypatch.setattr(reddit, "ACTIVE_GENRES", ["action"])
    monkeypatch.setattr(reddit, "REDDIT_POST_LIMIT", 10)
    monkeypatch.setattr(reddit, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(reddit, "save", lambda records, data_dir, name, log: records)


def test_dedup_posts_within_subreddit_by_id(config, requests_mock):
    xml = _atom(_entry("t3_dup", "First Copy") + _entry("t3_dup", "Second Copy"))
    requests_mock.get(FEED_URL_RE, status_code=403)  # everything else: blocked
    requests_mock.get(_feed_url("commonsub"), text=xml)

    records = reddit.run(log=lambda *a: None)

    commonsub_records = [r for r in records if r["subreddit"] == "commonsub"]
    assert len(commonsub_records) == 1


def test_niche_subreddit_keeps_posts_regardless_of_content(config, requests_mock):
    xml = _atom(_entry("t3_a", "Nothing to do with any genre keyword"))
    requests_mock.get(FEED_URL_RE, status_code=403)
    requests_mock.get(_feed_url("actionsub"), text=xml)

    records = reddit.run(log=lambda *a: None)

    action_records = [r for r in records if r["subreddit"] == "actionsub"]
    assert len(action_records) == 1
    assert action_records[0]["genre"] == "action"


def test_broad_subreddit_matches_genre_keyword(config, requests_mock):
    xml = _atom(_entry("t3_a", "A great new shooter just dropped"))
    requests_mock.get(FEED_URL_RE, status_code=403)
    requests_mock.get(_feed_url("broadsub"), text=xml)

    records = reddit.run(log=lambda *a: None)

    broad_records = [r for r in records if r["subreddit"] == "broadsub"]
    assert len(broad_records) == 1
    assert broad_records[0]["genre"] == "action"


def test_broad_subreddit_matches_common_keyword_as_general(config, requests_mock):
    xml = _atom(_entry("t3_a", "Cool indie project I found"))
    requests_mock.get(FEED_URL_RE, status_code=403)
    requests_mock.get(_feed_url("broadsub"), text=xml)

    records = reddit.run(log=lambda *a: None)

    broad_records = [r for r in records if r["subreddit"] == "broadsub"]
    assert len(broad_records) == 1
    assert broad_records[0]["genre"] == "general"


def test_broad_subreddit_drops_posts_matching_no_keywords(config, requests_mock):
    xml = _atom(_entry("t3_a", "Completely unrelated off-topic post"))
    requests_mock.get(FEED_URL_RE, status_code=403)
    requests_mock.get(_feed_url("broadsub"), text=xml)

    records = reddit.run(log=lambda *a: None)

    assert [r for r in records if r["subreddit"] == "broadsub"] == []


def test_all_feeds_blocked_logs_specific_message(config, requests_mock):
    requests_mock.get(FEED_URL_RE, status_code=403)
    logs = []

    records = reddit.run(log=logs.append)

    assert records == []
    assert any("all feeds empty/blocked" in msg for msg in logs)


def test_time_budget_already_exceeded_skips_every_subreddit(config, monkeypatch, requests_mock):
    monkeypatch.setattr(reddit, "TIME_BUDGET_SECONDS", -1)  # guarantees immediate trip
    requests_mock.get(FEED_URL_RE, exc=AssertionError("should never be called"))

    assert reddit.run(log=lambda *a: None) == []


def test_post_limit_truncates_before_any_filtering(config, monkeypatch, requests_mock):
    monkeypatch.setattr(reddit, "REDDIT_POST_LIMIT", 1)
    xml = _atom(_entry("t3_a", "First Post") + _entry("t3_b", "Second Post"))
    requests_mock.get(FEED_URL_RE, status_code=403)
    requests_mock.get(_feed_url("actionsub"), text=xml)

    records = reddit.run(log=lambda *a: None)

    action_records = [r for r in records if r["subreddit"] == "actionsub"]
    assert len(action_records) == 1
    assert action_records[0]["title"] == "First Post"


def test_year_filter_only_applies_to_past_years(config, requests_mock):
    old_year = reddit.NOW_YEAR - 3
    xml = _atom(_entry("t3_a", "An old post", published=f"{old_year}-01-01T00:00:00Z"))
    requests_mock.get(FEED_URL_RE, status_code=403)
    requests_mock.get(_feed_url("actionsub"), text=xml)

    # Requesting the current year (or None) never filters on post year.
    records = reddit.run(year=reddit.NOW_YEAR, log=lambda *a: None)
    assert len([r for r in records if r["subreddit"] == "actionsub"]) == 1

    # Requesting a specific past year that doesn't match the post's year drops it.
    records = reddit.run(year=old_year - 1, log=lambda *a: None)
    assert [r for r in records if r["subreddit"] == "actionsub"] == []


def test_year_filter_keeps_posts_with_unparseable_year(config, requests_mock):
    xml = _atom('<entry><id>t3_a</id><title>No Date Post</title></entry>')  # no published/updated -> year=None
    requests_mock.get(FEED_URL_RE, status_code=403)
    requests_mock.get(_feed_url("actionsub"), text=xml)

    records = reddit.run(year=reddit.NOW_YEAR - 5, log=lambda *a: None)

    assert len([r for r in records if r["subreddit"] == "actionsub"]) == 1
