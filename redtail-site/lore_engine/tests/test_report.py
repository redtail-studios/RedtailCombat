import os
import sys
from itertools import count

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import report
from report import (build_prompt, _fmt_quotes, _fmt_signals,
                    _fmt_competitors, validate_citations)


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


def test_prep_multi_genre_blocks_general_quote_shown_once_across_genres():
    shared_quote = "Everyone is talking about the new engine update."
    analysis_by_year_genre = {
        "2025": {
            "fighting": _analyse_stub([shared_quote, "Fighting specific quote."]),
            "puzzle":   _analyse_stub([shared_quote, "Puzzle specific quote."]),
        }
    }
    blocks, registry = report._prep_multi_genre_blocks(
        [2025], [], analysis_by_year_genre, ["fighting", "puzzle"])
    combined = blocks["fighting"][2025] + blocks["puzzle"][2025]

    assert combined.count(shared_quote) == 1
    assert combined.count("Fighting specific quote.") == 1
    assert combined.count("Puzzle specific quote.") == 1
    # ids stay unique across genre sections in the same report
    assert sorted(registry.values()) == sorted(
        [shared_quote, "Fighting specific quote.", "Puzzle specific quote."])
    assert len(set(registry.keys())) == len(registry)


def test_prep_multi_genre_blocks_numeric_outputs_unaffected_by_quote_dedup():
    analysis_by_year_genre = {
        "2025": {
            "fighting": {"total_items": 42, "signals": {}, "scorecard": {},
                         "competitors": [], "quotes": ["shared quote", "fighting quote"]},
            "puzzle":   {"total_items": 17, "signals": {}, "scorecard": {},
                         "competitors": [], "quotes": ["shared quote", "puzzle quote"]},
        }
    }
    blocks, _registry = report._prep_multi_genre_blocks(
        [2025], [], analysis_by_year_genre, ["fighting", "puzzle"])

    # Task 1b only changes quote rendering — total_items must still reflect
    # the real per-genre count, unaffected by cross-genre quote deduplication.
    assert "Data points: 42" in blocks["fighting"][2025]
    assert "Data points: 17" in blocks["puzzle"][2025]


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


def test_validate_citations_multi_genre_shape_valid_citation_passes():
    registry = {"Q1": "some quote"}
    html = """
    <div class="card"><h3>Fighting</h3>
    <h4>Market Gap</h4><p>Players want more depth [Q1].</p></div>
    """
    result = validate_citations(html, registry)
    assert result["valid"] is True
    assert result["uncited_gaps"] == []


def test_validate_citations_multi_genre_shape_flags_uncited_gap():
    registry = {"Q1": "some quote"}
    html = """
    <div class="card"><h3>Fighting</h3>
    <h4>Market Gap</h4><p>Players want more depth [Q1].</p></div>
    <div class="card"><h3>Puzzle</h3>
    <h4>Market Gap</h4><p>No citation in this one.</p></div>
    """
    result = validate_citations(html, registry)
    assert result["valid"] is False
    assert result["uncited_gaps"] == ["Puzzle — Market Gap"]


# ---------------------------------------------------------------------------
# _fmt_signals / _fmt_competitors
# ---------------------------------------------------------------------------

def test_fmt_signals_sorted_by_score_descending():
    sigs = {
        "SignalA": {"score": 3.0, "hits": 2, "pct": 10.0},
        "SignalB": {"score": 8.0, "hits": 5, "pct": 40.0},
    }
    out = _fmt_signals(sigs)

    assert out.index("SignalB") < out.index("SignalA")


def test_fmt_competitors_includes_example_quote():
    comps = [{"name": "CompA", "mentions": 5, "positive_pct": 60, "negative_pct": 20,
             "quote": "great game overall"}]

    out = _fmt_competitors(comps)

    assert "CompA: 5 mentions (60% pos / 20% neg)" in out
    assert 'e.g. "great game overall"' in out


def test_fmt_competitors_without_quote_omits_example_line():
    comps = [{"name": "CompA", "mentions": 5, "positive_pct": 60, "negative_pct": 20, "quote": ""}]

    out = _fmt_competitors(comps)

    assert "e.g." not in out


# ---------------------------------------------------------------------------
# build_prompt (single-genre) / build_prompt_multi with validation years
# ---------------------------------------------------------------------------

def test_build_prompt_single_genre_no_validation(monkeypatch):
    monkeypatch.setattr(report, "GENRES", {"fighting": {"label": "Fighting"}})
    analysis_by_year = {"2024": _analyse_stub(["A fighting-specific quote here."])}

    prompt, registry = build_prompt([2024], [], analysis_by_year, genre="fighting")

    assert "the Fighting genre" in prompt
    assert "VALIDATION DATA" not in prompt
    assert "MARKET BACKTEST" not in prompt
    assert "A fighting-specific quote here." in prompt


def test_build_prompt_single_genre_with_validation_years(monkeypatch):
    monkeypatch.setattr(report, "GENRES", {"fighting": {"label": "Fighting"}})
    analysis_by_year = {
        "2023": _analyse_stub(["A backtest-year quote."]),
        "2024": _analyse_stub(["A validation-year quote."]),
    }

    prompt, registry = build_prompt([2023], [2024], analysis_by_year, genre="fighting")

    assert "VALIDATION DATA" in prompt
    assert "MARKET BACKTEST" in prompt
    assert "A validation-year quote." in prompt


def test_build_prompt_no_scope_note_when_genre_is_none():
    prompt, _registry = build_prompt([2024], [], {"2024": _analyse_stub([])}, genre=None)

    assert "Scope: this data covers only" not in prompt


def test_prep_multi_genre_blocks_with_validation_years(monkeypatch):
    monkeypatch.setattr(report, "GENRES", {"fighting": {"label": "Fighting"},
                                            "puzzle": {"label": "Puzzle"}})
    analysis_by_year_genre = {
        "2023": {"fighting": _analyse_stub(["bt fighting quote"]),
                 "puzzle": _analyse_stub(["bt puzzle quote"])},
        "2024": {"fighting": _analyse_stub(["val fighting quote"]),
                 "puzzle": _analyse_stub(["val puzzle quote"])},
    }

    blocks, registry = report._prep_multi_genre_blocks(
        [2023], [2024], analysis_by_year_genre, ["fighting", "puzzle"])

    assert "val fighting quote" in blocks["fighting"][2024]
    assert "val puzzle quote" in blocks["puzzle"][2024]
    assert "bt fighting quote" in blocks["fighting"][2023]


# ---------------------------------------------------------------------------
# _genre_section_prompt / _synthesis_prompt
# ---------------------------------------------------------------------------

def test_genre_section_prompt_basic(monkeypatch):
    monkeypatch.setattr(report, "GENRES", {"fighting": {"label": "Fighting"}})
    blocks_for_genre = {2024: "### 2024\nData points: 5"}

    prompt = report._genre_section_prompt("fighting", blocks_for_genre, [2024], [], False)

    assert "one genre's section of a larger multi-genre report: Fighting." in prompt
    assert "Data points: 5" in prompt
    assert "===DIGEST-END===" in prompt
    assert "MARKET BACKTEST" not in prompt
    assert "VALIDATION DATA" not in prompt


def test_genre_section_prompt_includes_backtest_note_when_has_val(monkeypatch):
    monkeypatch.setattr(report, "GENRES", {"fighting": {"label": "Fighting"}})
    blocks_for_genre = {2023: "bt block", 2024: "val block"}

    prompt = report._genre_section_prompt("fighting", blocks_for_genre, [2023], [2024], True)

    assert "MARKET BACKTEST" in prompt
    assert "VALIDATION DATA" in prompt
    assert "val block" in prompt


def test_synthesis_prompt_includes_digests_and_separator(monkeypatch):
    monkeypatch.setattr(report, "GENRES", {"fighting": {"label": "Fighting"},
                                            "puzzle": {"label": "Puzzle"}})
    digests = {"fighting": "Fighting is under-served.", "puzzle": "Puzzle is saturated."}

    prompt = report._synthesis_prompt(digests, ["fighting", "puzzle"], [2024], [], False)

    assert "Fighting is under-served." in prompt
    assert "Puzzle is saturated." in prompt
    assert "===MID-END===" in prompt


# ---------------------------------------------------------------------------
# generate()
# ---------------------------------------------------------------------------

def test_generate_single_genre_path(monkeypatch):
    monkeypatch.setattr(report, "GENRES", {"fighting": {"label": "Fighting"}})
    monkeypatch.setattr(report, "analyse", lambda year, genre=None: _analyse_stub(["a quote"]))
    captured = {}

    def fake_generate_html(prompt, max_tokens=32000):
        captured["prompt"] = prompt
        return "<html>report</html>"
    monkeypatch.setattr(report.llm, "generate_html", fake_generate_html)

    html = report.generate([2024], genre="fighting")

    assert html == "<html>report</html>"
    assert "Fighting" in captured["prompt"]


def test_generate_multi_genre_default_path(monkeypatch):
    monkeypatch.setattr(report, "GENRES", {"fighting": {"label": "Fighting"},
                                            "puzzle": {"label": "Puzzle"}})
    monkeypatch.setattr(report, "ACTIVE_GENRES", ["fighting", "puzzle"])
    monkeypatch.setattr(report, "analyse",
                        lambda year, genre=None: _analyse_stub([f"{genre} quote"]))

    def fake_generate_html(prompt, max_tokens=32000):
        if "multi-genre report: Fighting." in prompt:
            return 'Fighting is under-served.===DIGEST-END===<div class="card"><h3>Fighting</h3></div>'
        if "multi-genre report: Puzzle." in prompt:
            return 'Puzzle is saturated.===DIGEST-END===<div class="card"><h3>Puzzle</h3></div>'
        # synthesis call — only one left once both genre calls are accounted for
        assert "Fighting is under-served." in prompt
        assert "Puzzle is saturated." in prompt
        return ('<h1>Report</h1>===MID-END==='
               '<div class="card"><h2>Strategic Recommendations</h2></div>')

    monkeypatch.setattr(report.llm, "generate_html", fake_generate_html)

    html = report.generate([2024])

    # both genre sections and the synthesis wrapper made it into the final document
    assert "<h3>Fighting</h3>" in html
    assert "<h3>Puzzle</h3>" in html
    assert "<h1>Report</h1>" in html
    assert "<h2>Strategic Recommendations</h2>" in html
    assert html.startswith("<!DOCTYPE html>")


def test_generate_multi_genre_runs_genre_calls_concurrently(monkeypatch):
    """Each genre call should run in its own thread (not blocked on the
    others) — the whole point of the parallel-calls redesign."""
    import threading
    monkeypatch.setattr(report, "GENRES", {"fighting": {"label": "Fighting"},
                                            "puzzle": {"label": "Puzzle"}})
    monkeypatch.setattr(report, "ACTIVE_GENRES", ["fighting", "puzzle"])
    monkeypatch.setattr(report, "analyse",
                        lambda year, genre=None: _analyse_stub([f"{genre} quote"]))

    seen_threads = set()

    def fake_generate_html(prompt, max_tokens=32000):
        if "one genre's section" in prompt:
            seen_threads.add(threading.get_ident())
            return 'digest===DIGEST-END===<div class="card"></div>'
        return '<h1>Report</h1>===MID-END===<div class="card"></div>'

    monkeypatch.setattr(report.llm, "generate_html", fake_generate_html)
    report.generate([2024])

    # genre calls ran via the ThreadPoolExecutor, not on the main thread
    assert threading.get_ident() not in seen_threads


def test_generate_prints_warning_when_citations_invalid(monkeypatch, capsys):
    monkeypatch.setattr(report, "GENRES", {"fighting": {"label": "Fighting"}})
    monkeypatch.setattr(report, "analyse", lambda year, genre=None: _analyse_stub(["a quote"]))
    # References a quote id that will never exist in the registry.
    monkeypatch.setattr(report.llm, "generate_html", lambda prompt, max_tokens=32000:
                        "<h2>2. Market Gap Analysis</h2><h3>Gap</h3><p>[Q99]</p>")

    report.generate([2024], genre="fighting")

    out = capsys.readouterr().out
    assert "citation validation failed" in out
