import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analysis
from analysis import dedupe_items, signal_scores, scorecard, competitors, analyse
from config import SOURCE_WEIGHTS


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
    # both items dedupe to the one that appeared first ("reddit") — its
    # SOURCE_WEIGHTS entry, not a hardcoded 1.0, is what should come through
    assert sigs["Competitive / PvP demand"]["hits"] == SOURCE_WEIGHTS["reddit"]

    comp_items = [
        _item("Brawlhalla just added a new legend, great patch.", "reddit"),
        _item("brawlhalla just added a new legend great patch", "hackernews"),
    ]
    deduped_comp = dedupe_items(comp_items)
    comps = competitors(deduped_comp)
    brawlhalla = next((c for c in comps if c["name"] == "Brawlhalla"), None)
    assert brawlhalla is not None
    assert brawlhalla["mentions"] == SOURCE_WEIGHTS["reddit"]


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


# ---------------------------------------------------------------------------
# _iter_records / load_items — file loading edge cases
# ---------------------------------------------------------------------------

def test_load_items_skips_missing_data_file(tmp_path, monkeypatch):
    year_dir = tmp_path / "2025"
    year_dir.mkdir()
    (year_dir / "reddit_data.json").write_text(json.dumps(
        [{"title": "A perfectly normal reddit post here.", "sentiment": {"compound": 0.0}}]))
    # "ghost" is in PLATFORM_IDS but never wrote a data file.

    monkeypatch.setattr(analysis, "PLATFORM_IDS", ["reddit", "ghost"])
    monkeypatch.setattr(analysis, "get_year_dir", lambda year: str(year_dir))
    monkeypatch.setattr(analysis, "DEPLOYED", False)

    items = analysis.load_items(2025)

    assert len(items) == 1


def test_load_items_skips_malformed_json_file(tmp_path, monkeypatch):
    year_dir = tmp_path / "2025"
    year_dir.mkdir()
    (year_dir / "reddit_data.json").write_text(json.dumps(
        [{"title": "A perfectly normal reddit post here.", "sentiment": {"compound": 0.0}}]))
    (year_dir / "broken_data.json").write_text("not valid json {{{")

    monkeypatch.setattr(analysis, "PLATFORM_IDS", ["reddit", "broken"])
    monkeypatch.setattr(analysis, "get_year_dir", lambda year: str(year_dir))
    monkeypatch.setattr(analysis, "DEPLOYED", False)

    items = analysis.load_items(2025)

    assert len(items) == 1


def test_load_items_genre_filter(tmp_path, monkeypatch):
    year_dir = tmp_path / "2025"
    year_dir.mkdir()
    (year_dir / "reddit_data.json").write_text(json.dumps([
        {"title": "An action genre specific post here.", "genre": "action",
         "sentiment": {"compound": 0.0}},
        {"title": "A general post with no genre tag set.",
         "sentiment": {"compound": 0.0}},
    ]))

    monkeypatch.setattr(analysis, "PLATFORM_IDS", ["reddit"])
    monkeypatch.setattr(analysis, "get_year_dir", lambda year: str(year_dir))
    monkeypatch.setattr(analysis, "DEPLOYED", False)

    puzzle_items = analysis.load_items(2025, genre="puzzle")
    assert len(puzzle_items) == 1
    assert "general post" in puzzle_items[0]["text"]

    action_items = analysis.load_items(2025, genre="action")
    assert len(action_items) == 2  # action-tagged + general-tagged both count


def test_load_items_deployed_mode_reads_from_storage(monkeypatch):
    monkeypatch.setattr(analysis, "PLATFORM_IDS", ["reddit", "hackernews"])
    monkeypatch.setattr(analysis, "DEPLOYED", True)

    def fake_get_cached_records(year, pid):
        if pid == "reddit":
            return [{"title": "A cached reddit post from S3 storage.",
                     "sentiment": {"compound": 0.0}}]
        return None  # cache miss/stale for hackernews
    monkeypatch.setattr(analysis.storage, "get_cached_records", fake_get_cached_records)

    items = analysis.load_items(2025)

    assert len(items) == 1
    assert items[0]["sources"] == ["reddit"]


def test_load_items_includes_review_and_comment_text(tmp_path, monkeypatch):
    year_dir = tmp_path / "2025"
    year_dir.mkdir()
    (year_dir / "steam_data.json").write_text(json.dumps([{
        "title": "The base game title text right here.",
        "sentiment": {"compound": 0.0},
        "reviews": [{"text": "This review text is long enough to count.",
                     "sentiment": {"compound": 0.5}}],
        "comments": [{"body": "This comment body is long enough to count.",
                      "sentiment": {"compound": -0.2}}],
    }]))

    monkeypatch.setattr(analysis, "PLATFORM_IDS", ["steam"])
    monkeypatch.setattr(analysis, "get_year_dir", lambda year: str(year_dir))
    monkeypatch.setattr(analysis, "DEPLOYED", False)

    items = analysis.load_items(2025)

    assert len(items) == 3  # title + review + comment, each its own item


# ---------------------------------------------------------------------------
# top_quotes
# ---------------------------------------------------------------------------

def test_top_quotes_includes_review_and_comment_text(tmp_path, monkeypatch):
    year_dir = tmp_path / "2025"
    year_dir.mkdir()
    (year_dir / "steam_data.json").write_text(json.dumps([{
        "title": "irrelevant base title",
        "sentiment": {"compound": 0.0},
        "reviews": [{"text": "A signal-rich review mentioning pvp ranked play here.",
                     "sentiment": {"compound": 0.0}}],
        "comments": [{"body": "A signal-rich comment mentioning pvp ranked play too.",
                      "sentiment": {"compound": 0.0}}],
    }]))

    monkeypatch.setattr(analysis, "PLATFORM_IDS", ["steam"])
    monkeypatch.setattr(analysis, "get_year_dir", lambda year: str(year_dir))
    monkeypatch.setattr(analysis, "DEPLOYED", False)
    monkeypatch.setattr(analysis, "SIGNAL_KEYWORDS", {"PvP": ["pvp"]})

    quotes = analysis.top_quotes(2025, n=25)

    assert any("review" in q for q in quotes)
    assert any("comment" in q for q in quotes)


def test_top_quotes_respects_n_limit(tmp_path, monkeypatch):
    year_dir = tmp_path / "2025"
    year_dir.mkdir()
    # Genuinely distinct sentences (not just a changed digit) so dedupe_items'
    # fuzzy similarity check doesn't collapse them into one quote.
    titles = [
        "Ranked pvp queue times are way too long lately.",
        "The new pvp map rotation feels stale after a while.",
        "Cross-platform pvp matchmaking would fix a lot of issues.",
        "Pvp balance changes really hurt melee builds this patch.",
        "Solo queue pvp is rough without a premade team.",
    ]
    records = [{"title": t, "sentiment": {"compound": 0.0}} for t in titles]
    (year_dir / "steam_data.json").write_text(json.dumps(records))

    monkeypatch.setattr(analysis, "PLATFORM_IDS", ["steam"])
    monkeypatch.setattr(analysis, "get_year_dir", lambda year: str(year_dir))
    monkeypatch.setattr(analysis, "DEPLOYED", False)
    monkeypatch.setattr(analysis, "SIGNAL_KEYWORDS", {"PvP": ["pvp"]})

    quotes = analysis.top_quotes(2025, n=3)

    assert len(quotes) == 3


# ---------------------------------------------------------------------------
# signal_scores / scorecard
# ---------------------------------------------------------------------------

def test_signal_scores_empty_items_returns_empty_dict():
    assert signal_scores([]) == {}


def test_scorecard_empty_items_returns_empty_dict():
    assert scorecard([], {}) == {}


def test_scorecard_computes_sentiment_percentages_with_source_weights(monkeypatch):
    items = [
        {"source": "reddit", "text": "great pvp mode", "sentiment": {"compound": 0.6}},
        {"source": "steam", "text": "terrible bugs everywhere", "sentiment": {"compound": -0.6}},
        {"source": "reddit", "text": "it is fine i guess", "sentiment": {"compound": 0.0}},
    ]
    monkeypatch.setattr(analysis, "SOURCE_WEIGHTS", {"reddit": 1.0, "steam": 2.0})

    sc = scorecard(items, {})

    assert sc["total_items"] == 3
    assert sc["positive_pct"] == round(1.0 / 3 * 100, 1)
    assert sc["negative_pct"] == round(2.0 / 3 * 100, 1)
    assert sc["neutral_pct"] == 0.0
    assert sc["top_signal"] is None  # sigs was empty


def test_scorecard_top_signal_picks_highest_score():
    items = [{"source": "reddit", "text": "irrelevant", "sentiment": {"compound": 0.0}}]
    sigs = {"SignalA": {"score": 5.0, "hits": 1, "pct": 10.0},
            "SignalB": {"score": 8.0, "hits": 1, "pct": 20.0}}

    sc = scorecard(items, sigs)

    assert sc["top_signal"] == "SignalB"


# ---------------------------------------------------------------------------
# competitors
# ---------------------------------------------------------------------------

def test_competitors_quote_set_only_on_first_mention(monkeypatch):
    monkeypatch.setattr(analysis, "COMPETITORS", {"CompA": ["compa"]})
    monkeypatch.setattr(analysis, "SOURCE_WEIGHTS", {"reddit": 1.0})
    items = [
        {"source": "reddit", "text": "compa is great, first mention here", "sentiment": {"compound": 0.6}},
        {"source": "reddit", "text": "compa mentioned again, second time", "sentiment": {"compound": 0.6}},
    ]

    comps = competitors(items)

    assert len(comps) == 1
    assert comps[0]["mentions"] == 2
    assert comps[0]["quote"] == "compa is great, first mention here"


def test_competitors_negative_sentiment_counted(monkeypatch):
    monkeypatch.setattr(analysis, "COMPETITORS", {"CompA": ["compa"]})
    monkeypatch.setattr(analysis, "SOURCE_WEIGHTS", {"reddit": 1.0})
    items = [{"source": "reddit", "text": "compa is terrible and buggy",
             "sentiment": {"compound": -0.6}}]

    comps = competitors(items)

    assert comps[0]["negative_pct"] == 100
    assert comps[0]["positive_pct"] == 0


def test_competitors_skips_entries_with_zero_effective_mentions(monkeypatch):
    # A source with a zero weight can match a competitor keyword yet still
    # contribute nothing to `mentions` — that entry must not appear in the
    # output (analysis.py:213-214).
    monkeypatch.setattr(analysis, "COMPETITORS", {"CompA": ["compa"], "CompB": ["compb"]})
    monkeypatch.setattr(analysis, "SOURCE_WEIGHTS", {"reddit": 1.0, "muted": 0.0})
    items = [
        {"source": "muted", "text": "compa mentioned but from a zero-weight source",
         "sentiment": {"compound": 0.0}},
        {"source": "reddit", "text": "compb mentioned from a normal-weight source",
         "sentiment": {"compound": 0.0}},
    ]

    comps = competitors(items)

    assert [c["name"] for c in comps] == ["CompB"]


def test_competitors_caps_at_six(monkeypatch):
    monkeypatch.setattr(analysis, "COMPETITORS", {f"Comp{i}": [f"comp{i}"] for i in range(8)})
    monkeypatch.setattr(analysis, "SOURCE_WEIGHTS", {"reddit": 1.0})
    items = [{"source": "reddit", "text": f"comp{i} mentioned here", "sentiment": {"compound": 0.0}}
             for i in range(8)]

    comps = competitors(items)

    assert len(comps) == 6


# ---------------------------------------------------------------------------
# analyse — end to end
# ---------------------------------------------------------------------------

def test_analyse_end_to_end(tmp_path, monkeypatch):
    year_dir = tmp_path / "2025"
    year_dir.mkdir()
    (year_dir / "reddit_data.json").write_text(json.dumps([
        {"title": "Players really want more pvp ranked content please.",
         "sentiment": {"compound": 0.6}},
    ]))

    monkeypatch.setattr(analysis, "PLATFORM_IDS", ["reddit"])
    monkeypatch.setattr(analysis, "get_year_dir", lambda year: str(year_dir))
    monkeypatch.setattr(analysis, "DEPLOYED", False)

    result = analyse(2025)

    assert result["total_items"] == 1
    assert result["scorecard"]["total_items"] == 1
    assert isinstance(result["signals"], dict)
    assert isinstance(result["competitors"], list)
    assert isinstance(result["quotes"], list)
