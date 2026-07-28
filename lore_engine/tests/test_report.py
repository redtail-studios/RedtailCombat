import os
import sys
from itertools import count

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from report import build_prompt_multi, _fmt_quotes, validate_citations


def _analyse_stub(quotes):
    return {"total_items": len(quotes), "signals": {}, "scorecard": {},
            "competitors": [], "quotes": quotes}


def test_fmt_quotes_dedupes_against_shared_seen_set():
    ids, registry, seen = count(1), {}, set()
    first = _fmt_quotes(["Wikipedia interest is spiking.", "Fighting-only quote."], ids, registry, seen)
    second = _fmt_quotes(["Wikipedia interest is spiking.", "Puzzle-only quote."], ids, registry, seen)
    assert '"Wikipedia interest is spiking."' in first
    assert '"Wikipedia interest is spiking."' not in second
    assert '"Puzzle-only quote."' in second


def test_fmt_quotes_independent_when_no_seen_set_shared():
    first = _fmt_quotes(["Same quote in both."], count(1), {})
    second = _fmt_quotes(["Same quote in both."], count(1), {})
    assert '"Same quote in both."' in first
    assert '"Same quote in both."' in second


def test_fmt_quotes_assigns_sequential_ids_across_shared_counter():
    # Simulates two genre sections in one report sharing the same ids/registry.
    ids, registry = count(1), {}
    first = _fmt_quotes(["Alpha quote.", "Beta quote."], ids, registry)
    second = _fmt_quotes(["Gamma quote."], ids, registry)

    assert '[Q1] "Alpha quote."' in first
    assert '[Q2] "Beta quote."' in first
    assert '[Q3] "Gamma quote."' in second
    assert registry == {"Q1": "Alpha quote.", "Q2": "Beta quote.", "Q3": "Gamma quote."}


def test_build_prompt_multi_general_quote_shown_once_across_genres():
    shared_quote = "Everyone is talking about the new engine update."
    analysis_by_year_genre = {
        "2025": {
            "fighting": _analyse_stub([shared_quote, "Fighting specific quote."]),
            "puzzle":   _analyse_stub([shared_quote, "Puzzle specific quote."]),
        }
    }
    prompt, registry = build_prompt_multi([2025], [], analysis_by_year_genre, ["fighting", "puzzle"])

    assert prompt.count(shared_quote) == 1
    assert prompt.count("Fighting specific quote.") == 1
    assert prompt.count("Puzzle specific quote.") == 1
    # ids stay unique across genre sections in the same report
    assert sorted(registry.values()) == sorted(
        [shared_quote, "Fighting specific quote.", "Puzzle specific quote."])
    assert len(set(registry.keys())) == len(registry)


def test_build_prompt_multi_numeric_outputs_unaffected_by_quote_dedup():
    analysis_by_year_genre = {
        "2025": {
            "fighting": {"total_items": 42, "signals": {}, "scorecard": {},
                         "competitors": [], "quotes": ["shared quote", "fighting quote"]},
            "puzzle":   {"total_items": 17, "signals": {}, "scorecard": {},
                         "competitors": [], "quotes": ["shared quote", "puzzle quote"]},
        }
    }
    prompt, _registry = build_prompt_multi([2025], [], analysis_by_year_genre, ["fighting", "puzzle"])

    # Task 1b only changes quote rendering — total_items must still reflect
    # the real per-genre count, unaffected by cross-genre quote deduplication.
    assert "Data points: 42" in prompt
    assert "Data points: 17" in prompt


def test_validate_citations_valid_citation_passes():
    registry = {"Q1": "Players say ranked matchmaking takes forever."}
    html = """
    <h2>2. Market Gap Analysis</h2>
    <h3>Slow Matchmaking</h3>
    <p>Players are frustrated [Q1].</p>
    """
    result = validate_citations(html, registry)
    assert result["valid"] is True
    assert result["hallucinated_ids"] == []
    assert result["uncited_gaps"] == []


def test_validate_citations_flags_hallucinated_id():
    registry = {"Q1": "Players say ranked matchmaking takes forever."}
    html = """
    <h2>2. Market Gap Analysis</h2>
    <h3>Slow Matchmaking</h3>
    <p>Players are frustrated [Q1] and also [Q99].</p>
    """
    result = validate_citations(html, registry)
    assert result["valid"] is False
    assert result["hallucinated_ids"] == ["Q99"]
    assert result["uncited_gaps"] == []


def test_validate_citations_flags_uncited_gap():
    registry = {"Q1": "Players say ranked matchmaking takes forever."}
    html = """
    <h2>2. Market Gap Analysis</h2>
    <h3>Slow Matchmaking</h3>
    <p>Players are frustrated [Q1].</p>
    <h3>No Cosmetic Variety</h3>
    <p>This gap has no citation at all.</p>
    """
    result = validate_citations(html, registry)
    assert result["valid"] is False
    assert result["hallucinated_ids"] == []
    assert result["uncited_gaps"] == ["No Cosmetic Variety"]
