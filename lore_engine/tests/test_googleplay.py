import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import scrapers.googleplay as googleplay


@pytest.fixture
def one_genre(monkeypatch):
    """googleplay.py imports google_play_scraper's functions *inside*
    _scrape_query() on every call, so patching the attributes on the real
    google_play_scraper module (rather than on scrapers.googleplay) is what
    actually takes effect."""
    monkeypatch.setattr(googleplay, "GENRES", {"action": {"google_play_query": "action games"}})
    monkeypatch.setattr(googleplay, "ACTIVE_GENRES", ["action"])
    monkeypatch.setattr(googleplay, "GOOGLE_PLAY_N_APPS", 5)
    monkeypatch.setattr(googleplay, "GOOGLE_PLAY_REVIEWS", 5)
    monkeypatch.setattr(googleplay, "get_year_dir", lambda year: "/tmp/unused")
    monkeypatch.setattr(googleplay, "save", lambda records, data_dir, name, log: records)
    monkeypatch.setattr(googleplay.time, "sleep", lambda *a: None)


def _review(review_id, content, score, at):
    return {"reviewId": review_id, "content": content, "score": score, "at": at}


def test_search_error_returns_no_records(one_genre, monkeypatch):
    def fake_search(query, n_hits, lang, country):
        raise RuntimeError("network down")
    monkeypatch.setattr("google_play_scraper.search", fake_search)

    assert googleplay.run(log=lambda *a: None) == []


def test_missing_app_id_is_skipped(one_genre, monkeypatch):
    monkeypatch.setattr("google_play_scraper.search", lambda *a, **k: [{"title": "No ID App"}])

    assert googleplay.run(log=lambda *a: None) == []


def test_app_details_error_falls_back_to_search_hit(one_genre, monkeypatch):
    monkeypatch.setattr("google_play_scraper.search",
                        lambda *a, **k: [{"appId": "com.fake.app", "title": "Hit Title"}])
    monkeypatch.setattr("google_play_scraper.app",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("not found")))
    monkeypatch.setattr("google_play_scraper.reviews", lambda *a, **k: ([], None))

    records = googleplay.run(log=lambda *a: None)

    assert len(records) == 1
    assert records[0]["name"] == "Hit Title"  # fell back to the search hit dict


def test_reviews_error_still_creates_record_with_no_reviews(one_genre, monkeypatch):
    monkeypatch.setattr("google_play_scraper.search",
                        lambda *a, **k: [{"appId": "com.fake.app"}])
    monkeypatch.setattr("google_play_scraper.app",
                        lambda *a, **k: {"title": "Fake App"})
    monkeypatch.setattr("google_play_scraper.reviews",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("blocked")))

    records = googleplay.run(log=lambda *a: None)

    assert len(records) == 1
    assert records[0]["reviews"] == []


def test_short_review_text_is_filtered(one_genre, monkeypatch):
    monkeypatch.setattr("google_play_scraper.search",
                        lambda *a, **k: [{"appId": "com.fake.app"}])
    monkeypatch.setattr("google_play_scraper.app", lambda *a, **k: {"title": "Fake App"})
    monkeypatch.setattr("google_play_scraper.reviews", lambda *a, **k: (
        [_review("r1", "ok", 3, datetime(2024, 1, 1))], None))

    records = googleplay.run(log=lambda *a: None)

    assert records[0]["reviews"] == []


def test_year_filter_breaks_on_older_review(one_genre, monkeypatch):
    # Reviews come back newest-first, so once one predates `year` the loop
    # `break`s instead of `continue`s — nothing after it should be kept
    # even if (hypothetically) newer again.
    monkeypatch.setattr("google_play_scraper.search",
                        lambda *a, **k: [{"appId": "com.fake.app"}])
    monkeypatch.setattr("google_play_scraper.app", lambda *a, **k: {"title": "Fake App"})
    monkeypatch.setattr("google_play_scraper.reviews", lambda *a, **k: ([
        _review("r1", "a review from the right year here", 5, datetime(2024, 6, 1)),
        _review("r2", "a review from last year that predates it", 4, datetime(2023, 6, 1)),
        _review("r3", "a review that would be kept if not for the break", 5, datetime(2024, 1, 1)),
    ], None))

    records = googleplay.run(year=2024, log=lambda *a: None)

    reviews = records[0]["reviews"]
    assert len(reviews) == 1
    assert reviews[0]["review_id"] == "r1"


def test_since_filter_breaks_past_cutoff(one_genre, monkeypatch):
    monkeypatch.setattr("google_play_scraper.search",
                        lambda *a, **k: [{"appId": "com.fake.app"}])
    monkeypatch.setattr("google_play_scraper.app", lambda *a, **k: {"title": "Fake App"})
    monkeypatch.setattr("google_play_scraper.reviews", lambda *a, **k: ([
        _review("r1", "a review after the since cutoff date", 5,
                 datetime(2024, 6, 1, tzinfo=timezone.utc)),
        _review("r2", "a review right at the since cutoff itself", 5,
                 datetime(2024, 1, 1, tzinfo=timezone.utc)),
    ], None))
    since = datetime(2024, 1, 1, tzinfo=timezone.utc)

    records = googleplay.run(since=since, log=lambda *a: None)

    reviews = records[0]["reviews"]
    assert len(reviews) == 1
    assert reviews[0]["review_id"] == "r1"


def test_year_filter_skips_review_with_no_usable_date(one_genre, monkeypatch):
    monkeypatch.setattr("google_play_scraper.search",
                        lambda *a, **k: [{"appId": "com.fake.app"}])
    monkeypatch.setattr("google_play_scraper.app", lambda *a, **k: {"title": "Fake App"})
    monkeypatch.setattr("google_play_scraper.reviews", lambda *a, **k: ([
        _review("r1", "a review with no usable date attached to it", 5, at=None),
        _review("r2", "a review with a proper date in the right year", 5,
                 datetime(2024, 3, 1)),
    ], None))

    records = googleplay.run(year=2024, log=lambda *a: None)

    reviews = records[0]["reviews"]
    assert len(reviews) == 1
    assert reviews[0]["review_id"] == "r2"


def test_year_filter_skips_review_from_a_different_year(one_genre, monkeypatch):
    monkeypatch.setattr("google_play_scraper.search",
                        lambda *a, **k: [{"appId": "com.fake.app"}])
    monkeypatch.setattr("google_play_scraper.app", lambda *a, **k: {"title": "Fake App"})
    monkeypatch.setattr("google_play_scraper.reviews", lambda *a, **k: ([
        _review("r1", "a review dated after the requested year somehow", 5,
                 datetime(2025, 1, 1)),
        _review("r2", "a review dated in the correct requested year", 5,
                 datetime(2024, 6, 1)),
    ], None))

    records = googleplay.run(year=2024, log=lambda *a: None)

    reviews = records[0]["reviews"]
    assert len(reviews) == 1
    assert reviews[0]["review_id"] == "r2"


def test_review_count_capped_at_google_play_reviews(one_genre, monkeypatch):
    reviews_data = [_review(f"r{i}", f"a perfectly normal review body number {i}", 5,
                             datetime(2024, 1, 1)) for i in range(10)]
    monkeypatch.setattr("google_play_scraper.search",
                        lambda *a, **k: [{"appId": "com.fake.app"}])
    monkeypatch.setattr("google_play_scraper.app", lambda *a, **k: {"title": "Fake App"})
    monkeypatch.setattr("google_play_scraper.reviews",
                        lambda *a, **k: (reviews_data, None))

    records = googleplay.run(log=lambda *a: None)

    assert len(records[0]["reviews"]) == 5  # GOOGLE_PLAY_REVIEWS=5


def test_fetch_count_quadruples_when_year_is_set(one_genre, monkeypatch):
    captured = {}
    monkeypatch.setattr("google_play_scraper.search",
                        lambda *a, **k: [{"appId": "com.fake.app"}])
    monkeypatch.setattr("google_play_scraper.app", lambda *a, **k: {"title": "Fake App"})

    def fake_reviews(app_id, lang, country, sort, count):
        captured["count"] = count
        return [], None
    monkeypatch.setattr("google_play_scraper.reviews", fake_reviews)

    googleplay.run(year=2024, log=lambda *a: None)

    assert captured["count"] == 20  # GOOGLE_PLAY_REVIEWS(5) * 4


def test_happy_path_record_fields(one_genre, monkeypatch):
    monkeypatch.setattr("google_play_scraper.search",
                        lambda *a, **k: [{"appId": "com.fake.app"}])
    monkeypatch.setattr("google_play_scraper.app", lambda *a, **k: {
        "title": "Fake App", "developer": "Fake Studio", "installs": "1,000,000+",
        "genre": "Action",
    })
    monkeypatch.setattr("google_play_scraper.reviews", lambda *a, **k: (
        [_review("r1", "This game is a lot of fun to play with friends.", 5,
                 datetime(2024, 1, 1))], None))

    records = googleplay.run(log=lambda *a: None)

    assert len(records) == 1
    r = records[0]
    assert r["name"] == "Fake App"
    assert r["developer"] == "Fake Studio"
    assert r["genre"] == "action"
    assert r["reviews"][0]["review_id"] == "r1"
    assert "sentiment" in r["reviews"][0]
