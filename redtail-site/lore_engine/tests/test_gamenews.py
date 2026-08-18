import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

import scrapers.gamenews as gamenews

FEED_URL = "http://fake.test/rss"

RSS_FEED = """<rss><channel>
<item>
  <title>Big Game News Title</title>
  <description>Some &lt;b&gt;bold&lt;/b&gt; text.</description>
  <link>http://example.com/1</link>
  <pubDate>{pubdate}</pubDate>
</item>
</channel></rss>"""

ATOM_FEED = """<feed xmlns="http://www.w3.org/2005/Atom">
<entry>
  <title>Atom Entry Title</title>
  <summary>Atom summary text.</summary>
  <link href="http://example.com/2"/>
  <published>{published}</published>
</entry>
</feed>"""


@pytest.fixture
def one_feed(monkeypatch):
    """Point gamenews.run() at a single fake feed instead of the real,
    config-driven feed list, and stub out disk writes via save()."""
    monkeypatch.setattr(gamenews, "GAMENEWS_FEEDS", [("Fake Outlet", FEED_URL)])
    monkeypatch.setattr(gamenews, "GAMENEWS_PER_FEED", 10)
    monkeypatch.setattr(gamenews, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(gamenews, "save", lambda records, data_dir, name, log: records)


def test_network_error_returns_empty_without_crashing(one_feed, requests_mock):
    requests_mock.get(FEED_URL, exc=requests.exceptions.ConnectionError)

    assert gamenews.run(log=lambda *a: None) == []


def test_non_200_status_returns_empty_without_crashing(one_feed, requests_mock):
    requests_mock.get(FEED_URL, status_code=503, text="")

    assert gamenews.run(log=lambda *a: None) == []


def test_malformed_xml_returns_empty_without_crashing(one_feed, requests_mock):
    requests_mock.get(FEED_URL, text="not xml at all <<<")

    assert gamenews.run(log=lambda *a: None) == []


def test_happy_path_parses_rss_item(one_feed, requests_mock):
    requests_mock.get(FEED_URL, text=RSS_FEED.format(pubdate="Mon, 01 Jan 2024 12:00:00 GMT"))

    records = gamenews.run(log=lambda *a: None)

    assert len(records) == 1
    r = records[0]
    assert r["title"] == "Big Game News Title"
    assert r["text"] == "Some bold text."  # entities unescaped, tags stripped
    assert r["url"] == "http://example.com/1"
    assert "sentiment" in r


def test_happy_path_parses_atom_entry(one_feed, requests_mock):
    requests_mock.get(FEED_URL, text=ATOM_FEED.format(published="2024-06-01T12:00:00Z"))

    records = gamenews.run(log=lambda *a: None)

    assert len(records) == 1
    assert records[0]["title"] == "Atom Entry Title"
    assert records[0]["text"] == "Atom summary text."
    assert records[0]["url"] == "http://example.com/2"


def test_short_title_is_filtered_out(one_feed, requests_mock):
    feed = RSS_FEED.format(pubdate="Mon, 01 Jan 2024 12:00:00 GMT").replace(
        "Big Game News Title", "Hi")
    requests_mock.get(FEED_URL, text=feed)

    assert gamenews.run(log=lambda *a: None) == []


def test_year_filter_drops_wrong_year_but_keeps_unparseable_dates(one_feed, requests_mock):
    # gamenews.py:85 treats an unparseable date as "not excludable" rather
    # than dropping it — a feed item with no usable date still gets kept
    # even when a specific year is requested.
    feed = RSS_FEED.format(pubdate="not a real date")
    requests_mock.get(FEED_URL, text=feed)

    records = gamenews.run(year=2024, log=lambda *a: None)

    assert len(records) == 1

    wrong_year_feed = RSS_FEED.format(pubdate="Mon, 01 Jan 2023 12:00:00 GMT")
    requests_mock.get(FEED_URL, text=wrong_year_feed)

    assert gamenews.run(year=2024, log=lambda *a: None) == []


def test_since_filter_keeps_item_on_naive_aware_mismatch(one_feed, requests_mock):
    # No timezone suffix -> parsedate_to_datetime returns a naive datetime.
    # Comparing that against an aware `since` raises TypeError, which
    # gamenews.py:88-92 catches and treats as "keep it" rather than crash.
    feed = RSS_FEED.format(pubdate="Mon, 01 Jan 2024 12:00:00")
    requests_mock.get(FEED_URL, text=feed)
    since = datetime(2023, 1, 1, tzinfo=timezone.utc)

    records = gamenews.run(since=since, log=lambda *a: None)

    assert len(records) == 1


def test_since_filter_drops_items_not_newer_than_since(one_feed, requests_mock):
    feed = RSS_FEED.format(pubdate="Mon, 01 Jan 2024 12:00:00 GMT")
    requests_mock.get(FEED_URL, text=feed)
    since = datetime(2024, 6, 1, tzinfo=timezone.utc)

    assert gamenews.run(since=since, log=lambda *a: None) == []
