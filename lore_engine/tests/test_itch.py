import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import requests

import scrapers.itch as itch

FEED_URL = "http://fake.test/itch-feed"


@pytest.fixture
def feed(monkeypatch):
    monkeypatch.setattr(itch, "ITCH_FEED", FEED_URL)
    monkeypatch.setattr(itch, "ITCH_LIMIT", 10)
    monkeypatch.setattr(itch, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(itch, "save", lambda records, data_dir, name, log: records)


def test_network_error_returns_empty_without_crashing(feed, requests_mock):
    requests_mock.get(FEED_URL, exc=requests.exceptions.ConnectionError)

    assert itch.run(log=lambda *a: None) == []


def test_non_200_status_returns_empty_without_crashing(feed, requests_mock):
    requests_mock.get(FEED_URL, status_code=503, text="")

    assert itch.run(log=lambda *a: None) == []


def test_malformed_xml_returns_empty_without_crashing(feed, requests_mock):
    requests_mock.get(FEED_URL, text="not xml at all <<<")

    assert itch.run(log=lambda *a: None) == []


def test_happy_path_parses_rss_item(feed, requests_mock):
    rss = """<rss><channel>
    <item><title>Cool Indie Game</title>
    <description>A &lt;b&gt;great&lt;/b&gt; little game.</description>
    <link>http://itch.io/game/1</link></item>
    </channel></rss>"""
    requests_mock.get(FEED_URL, text=rss)

    records = itch.run(log=lambda *a: None)

    assert len(records) == 1
    assert records[0]["title"] == "Cool Indie Game"
    assert records[0]["text"] == "A great little game."
    assert records[0]["url"] == "http://itch.io/game/1"


def test_happy_path_parses_atom_entry(feed, requests_mock):
    atom = """<feed xmlns="http://www.w3.org/2005/Atom">
    <entry><title>Atom Indie Game</title><summary>Neat little Atom game.</summary>
    <link href="http://itch.io/game/2"/></entry>
    </feed>"""
    requests_mock.get(FEED_URL, text=atom)

    records = itch.run(log=lambda *a: None)

    assert len(records) == 1
    assert records[0]["title"] == "Atom Indie Game"
    assert records[0]["url"] == "http://itch.io/game/2"


def test_limit_slices_before_short_title_filter(monkeypatch, requests_mock):
    # itch.py:43 slices to ITCH_LIMIT *before* dropping short titles, so a
    # too-short title inside the window wastes a slot instead of the next
    # valid item outside the window taking its place.
    monkeypatch.setattr(itch, "ITCH_FEED", FEED_URL)
    monkeypatch.setattr(itch, "ITCH_LIMIT", 2)
    monkeypatch.setattr(itch, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(itch, "save", lambda records, data_dir, name, log: records)
    rss = """<rss><channel>
    <item><title>A</title><description>too short a title</description><link>1</link></item>
    <item><title>Valid Game One</title><description>desc</description><link>2</link></item>
    <item><title>Valid Game Two</title><description>desc</description><link>3</link></item>
    </channel></rss>"""
    requests_mock.get(FEED_URL, text=rss)

    records = itch.run(log=lambda *a: None)

    assert len(records) == 1
    assert records[0]["title"] == "Valid Game One"
