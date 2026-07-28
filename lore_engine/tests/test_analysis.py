import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analysis
from analysis import dedupe_items, signal_scores, competitors


def _item(text, source, compound=0.0):
    return {"source": source, "text": text, "sentiment": {"compound": compound}}


def test_dedupe_identical_text_different_source_merges():
    items = [
        _item("Players say the matchmaking is too slow.", "reddit"),
        _item("Players say the matchmaking is too slow.", "hackernews"),
    ]
    out = dedupe_items(items)
    assert len(out) == 1
    assert out[0]["sources"] == ["reddit", "hackernews"]


def test_dedupe_reworded_text_merges():
    items = [
        _item("The matchmaking in this game is way too slow for ranked play.", "reddit"),
        _item("Matchmaking in this game is way too slow for ranked play!", "gamenews"),
    ]
    out = dedupe_items(items)
    assert len(out) == 1
    assert out[0]["sources"] == ["reddit", "gamenews"]


def test_dedupe_different_text_both_kept():
    items = [
        _item("Players say the matchmaking is too slow.", "reddit"),
        _item("The new battle pass cosmetics are gorgeous this season.", "hackernews"),
    ]
    out = dedupe_items(items)
    assert len(out) == 2


def test_dedupe_repeat_source_not_double_added():
    items = [
        _item("Players say the matchmaking is too slow.", "reddit"),
        _item("Players say the matchmaking is too slow.", "reddit"),
    ]
    out = dedupe_items(items)
    assert len(out) == 1
    assert out[0]["sources"] == ["reddit"]


def test_dedupe_removes_duplicate_before_signal_scores_and_competitors():
    items = [
        _item("This pvp ranked mode is amazing, best 1v1 experience.", "reddit"),
        _item("This pvp ranked mode is amazing, best 1v1 experience!", "gamenews"),
    ]
    deduped = dedupe_items(items)
    sigs = signal_scores(deduped)
    assert sigs["Competitive / PvP demand"]["hits"] == 1

    comp_items = [
        _item("Brawlhalla just added a new legend, great patch.", "reddit"),
        _item("brawlhalla just added a new legend great patch", "hackernews"),
    ]
    deduped_comp = dedupe_items(comp_items)
    comps = competitors(deduped_comp)
    brawlhalla = next((c for c in comps if c["name"] == "Brawlhalla"), None)
    assert brawlhalla is not None
    assert brawlhalla["mentions"] == 1


def test_load_items_dedupes_across_platforms(tmp_path, monkeypatch):
    year_dir = tmp_path / "2025"
    year_dir.mkdir()
    reddit_data = [{"title": "Ranked matchmaking is way too slow right now.",
                    "sentiment": {"compound": -0.5}}]
    hn_data = [{"title": "Ranked matchmaking is way too slow right now!",
                "sentiment": {"compound": -0.5}}]
    (year_dir / "reddit_data.json").write_text(json.dumps(reddit_data))
    (year_dir / "hackernews_data.json").write_text(json.dumps(hn_data))

    monkeypatch.setattr(analysis, "PLATFORM_IDS", ["reddit", "hackernews"])
    monkeypatch.setattr(analysis, "get_year_dir", lambda year: str(year_dir))
    monkeypatch.setattr(analysis, "DEPLOYED", False)

    items = analysis.load_items(2025)
    assert len(items) == 1
    assert set(items[0]["sources"]) == {"reddit", "hackernews"}


def test_top_quotes_dedupes_across_platforms(tmp_path, monkeypatch):
    year_dir = tmp_path / "2025"
    year_dir.mkdir()
    reddit_data = [{"title": "Ranked matchmaking is way too slow right now.",
                    "sentiment": {"compound": -0.5}}]
    hn_data = [{"title": "Ranked matchmaking is way too slow right now!",
                "sentiment": {"compound": -0.5}}]
    (year_dir / "reddit_data.json").write_text(json.dumps(reddit_data))
    (year_dir / "hackernews_data.json").write_text(json.dumps(hn_data))

    monkeypatch.setattr(analysis, "PLATFORM_IDS", ["reddit", "hackernews"])
    monkeypatch.setattr(analysis, "get_year_dir", lambda year: str(year_dir))
    monkeypatch.setattr(analysis, "DEPLOYED", False)

    quotes = analysis.top_quotes(2025, n=25)
    assert len(quotes) == 1
