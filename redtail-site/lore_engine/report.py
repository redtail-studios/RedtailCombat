"""
report.py — turn the cheap analysis into a Claude-written HTML intelligence report.

Supports two modes:
  • analyse   — analyse one or more years and find market gaps
  • backtest  — analyse historical years as predictions, then score them against
                later "validation" years (what actually happened)
"""
import re
from concurrent.futures import ThreadPoolExecutor
from itertools import count

import llm
from analysis import analyse
from config import GENRES, ACTIVE_GENRES


def _fmt_signals(sigs: dict) -> str:
    if not sigs:
        return "  (no signal data)"
    rows = sorted(sigs.items(), key=lambda x: -x[1]["score"])
    return "\n".join(
        f"  - {name}: {d['score']}/10  ({d['hits']} hits, {d['pct']}% of content)"
        for name, d in rows
    )


def _fmt_competitors(comps: list) -> str:
    if not comps:
        return "  (no competitor mentions)"
    lines = []
    for c in comps:
        lines.append(f"  - {c['name']}: {c['mentions']} mentions "
                     f"({c['positive_pct']}% pos / {c['negative_pct']}% neg)")
        if c["quote"]:
            lines.append(f'      e.g. "{c["quote"]}"')
    return "\n".join(lines)


def _fmt_quotes(quotes: list, ids, registry: dict, seen: set | None = None) -> str:
    if not quotes:
        return "  (no quotes)"
    # seen is shared across genre sections for a year (see _year_block_multi) so
    # a general-tagged quote that legitimately scores in every genre only gets
    # printed once, instead of appearing verbatim under every genre heading.
    # ids/registry are shared across the whole prompt (see build_prompt*) so
    # every quote gets a globally-unique [Qn] id Claude can cite and we can
    # later verify against.
    seen = set() if seen is None else seen
    lines = []
    for q in quotes[:20]:
        if q in seen:
            continue
        seen.add(q)
        qid = f"Q{next(ids)}"
        registry[qid] = q
        lines.append(f'  - [{qid}] "{q}"')
    return "\n".join(lines) if lines else "  (no new quotes — already shown above for this year)"


def _year_block(year: int, a: dict, ids, registry: dict) -> str:
    sc = a.get("scorecard", {})
    return f"""
### {year}
Data points: {a.get('total_items', 0)}
Sentiment: {sc.get('positive_pct', 0)}% positive / {sc.get('negative_pct', 0)}% negative
Demand signals (0-10, normalised within the year):
{_fmt_signals(a.get('signals', {}))}
Competitor mentions:
{_fmt_competitors(a.get('competitors', []))}
High-signal player quotes:
{_fmt_quotes(a.get('quotes', []), ids, registry)}
"""


def _genre_block(genre: str, a: dict, ids, registry: dict, seen: set) -> str:
    sc = a.get("scorecard", {})
    return f"""
#### {GENRES[genre]['label']}
Data points: {a.get('total_items', 0)}
Sentiment: {sc.get('positive_pct', 0)}% positive / {sc.get('negative_pct', 0)}% negative
Demand signals (0-10, normalised within this genre's data):
{_fmt_signals(a.get('signals', {}))}
Competitor mentions:
{_fmt_competitors(a.get('competitors', []))}
High-signal player quotes:
{_fmt_quotes(a.get('quotes', []), ids, registry, seen)}
"""


def _prep_multi_genre_blocks(backtest_years: list, validation_years: list,
                             analysis_by_year_genre: dict, genres: list) -> tuple:
    """Pre-formats every genre's per-year data block once, up front — assigning
    globally-unique quote IDs and deduping general-tagged quotes across
    genres within a year, exactly as the old single-call build_prompt_multi
    did. Doing this synchronously before any LLM call means the actual
    per-genre report calls (see _genre_section_prompt) can run concurrently
    without needing to coordinate with each other over IDs or dedup state.

    Returns (blocks, registry) where blocks[genre][year] is a formatted str.
    """
    ids = count(1)
    registry = {}
    years = sorted(set(backtest_years) | set(validation_years))
    blocks = {g: {} for g in genres}
    for y in years:
        seen: set = set()  # shared across genres for this year only, same as before
        for g in genres:
            blocks[g][y] = _genre_block(g, analysis_by_year_genre[str(y)][g], ids, registry, seen)
    return blocks, registry


def _genre_section_prompt(genre: str, blocks_for_genre: dict,
                          backtest_years: list, validation_years: list, has_val: bool) -> str:
    """One genre's slice of the multi-genre report, as its own small prompt —
    small enough that running one of these per genre, concurrently, is much
    faster wall-clock than one prompt asking Claude to write all genres at
    once (which is what pushed generation time to Vercel's 300s ceiling on
    data-heavy years). Each call gets a real per-genre token budget rather
    than a shared one split five ways, so depth doesn't have to be sacrificed
    for speed — the speedup comes from parallelism, not from asking for less."""
    label = GENRES[genre]["label"]
    bt = ", ".join(str(y) for y in sorted(backtest_years))
    val = ", ".join(str(y) for y in sorted(validation_years))

    bt_data = "".join(f"\n### {y}\n{blocks_for_genre[y]}" for y in sorted(backtest_years))
    val_data = ""
    if has_val:
        val_data = "\n## VALIDATION DATA — what actually happened (" + val + ")\n"
        val_data += "".join(f"\n### {y}\n{blocks_for_genre[y]}" for y in sorted(validation_years))
    backtest_note = (
        f"\nYou are running a MARKET BACKTEST: analyse {bt} as if predicting at "
        f"that time, then use the {val} validation data to score how accurate "
        f"those signals turned out to be.\n" if has_val else ""
    )

    return f"""You are running in non-interactive report-generation mode. Output ONLY the two parts described below — no <!DOCTYPE>/<html>/<head>/<body> wrapper, no markdown fences, no commentary.

You are a senior market-intelligence analyst writing one genre's section of a larger multi-genre report: {label}. Find genuine GAPS in the market for this genre specifically — unmet player needs that no current product serves well.
{backtest_note}
## DATA — {label} ({bt})
{bt_data}
{val_data}

## OUTPUT
Output exactly two parts, separated by a line containing only: ===DIGEST-END===

PART 1 (before the separator): plain text, no HTML, in exactly this format — real numbers pulled from the DATA above, not invented:
Top Signal: <the highest-scoring demand signal name>, <its score>/10
Sentiment: <positive>% positive / <negative>% negative
Data Coverage: <A-F, your judgment of how thin or solid this genre's sample is, one letter only>
Digest: <2-3 sentences on this genre's single biggest opportunity and how under-served it is>
This feeds a cross-genre ranking table and a data-quality table, so the three data lines above must be real values from the DATA section, and the Digest must be a strong, specific standalone claim.

PART 2 (after the separator): the HTML section for this genre. This fragment gets embedded into a page with its own stylesheet you do not see — do not add any color, background, or background-color styles anywhere, inline or otherwise, and do not add your own <style> tag. The only inline styles you should use are the layout ones shown in the bar-chart example below (width/flex/gap/margin). Follow this structure and markup exactly — this is a visual intelligence report, not a text summary, so signal scores render as bar charts and competitors render as a table, never as prose describing the numbers:
<div class="card">
<h3>{label}</h3>
<p>[2-3 sentences: demand signal strength and sentiment split, with real numbers]</p>
<h4>Demand Signals</h4>
[one row per signal from the data above, strongest first, using this exact pattern with the REAL score for each — e.g. for a signal scoring 8.5/10:]
<div style="display:flex;align-items:center;gap:10px;margin:6px 0"><span style="width:160px">Signal Name</span><div class="bar-track" style="flex:1"><div class="bar-fill" style="width:85%"></div></div><span>8.5/10</span></div>
[repeat for every signal in the data above — do not skip any, do not invent scores]
<h4>Market Gap</h4>
<p>[the top 1-2 unmet needs: name each gap, cite the signal score + hit count, and explain why no current competitor fills it. A real gap = high demand AND low satisfaction with what exists. Be honest if the sample is thin or the gap is weak.]</p>
[for each gap, one real player quote as a blockquote, e.g.:]
<blockquote>"the actual quote text" [Q7]</blockquote>
[Do not invent quotes or IDs — every blockquote must be a real quote from the data above with its real [Qn] id.]
<h4>Competitors</h4>
[a table of every named competitor from the data above — do not skip any, do not invent competitors:]
<table><tr><th>Competitor</th><th>Mentions</th><th>Sentiment</th></tr>
<tr><td>Name</td><td>N mentions</td><td>X% pos / Y% neg</td></tr>
[one row per competitor]</table>
<h4>Trends</h4>
<p>[how signals evolved across {bt}{" (and how the " + bt + " signals held up against " + val + " reality)" if has_val else ""}]</p>
</div>

Be specific. Cite exact numbers. Use real quotes. No platitudes — a founding team makes real decisions from this. Every number in your HTML must come from the DATA section above — never invent a score, a mention count, or a percentage."""


def _synthesis_prompt(digests: dict, genres: list, backtest_years: list,
                      validation_years: list, has_val: bool) -> str:
    """The cross-genre wrapper sections (exec summary, ranking, recs, data
    quality) need to see all genres at once, but only need each genre's short
    digest to do that — not the raw scraped data — so this call stays small
    and fast even though it runs after (and depends on) every genre call.
    Each digest now carries a Top Signal score, sentiment split, and a data
    coverage letter grade (see _genre_section_prompt's PART 1 format) so this
    call has real numbers to rank and grade with, not just prose to guess a
    ranking from."""
    bt = ", ".join(str(y) for y in sorted(backtest_years))
    genre_list = ", ".join(GENRES[g]["label"] for g in genres)
    digest_text = "\n\n".join(f"### {GENRES[g]['label']}\n{digests[g]}" for g in genres)

    return f"""You are running in non-interactive report-generation mode. Output ONLY the two parts described below — no <!DOCTYPE>/<html>/<head>/<body> wrapper, no markdown fences, no commentary.

You are a senior market-intelligence analyst synthesizing a multi-genre report covering: {genre_list}. Each genre's detailed section has already been written by a separate analyst; you are writing only the parts that need a view across all of them. This is a visual intelligence report — the comparison and data-quality sections render as tables, never as prose describing the same numbers.

## PER-GENRE DIGESTS ({bt})
{digest_text}

## OUTPUT
Output exactly two parts, separated by a line containing only: ===MID-END===

These fragments get embedded into a page with its own stylesheet you do not see — do not add any color, background, or background-color styles anywhere, inline or otherwise, and do not add your own <style> tag.

PART 1 — the report opening, as HTML:
<h1>Mobile Gaming Market Gaps Intelligence Report</h1>
<div class="card"><h2>Executive Summary</h2><p>[2-3 tight paragraphs: the single biggest finding across all genres and the size of the opportunity]</p></div>
<div class="card"><h2>Cross-Genre Comparison</h2>
<table><tr><th>Rank</th><th>Genre</th><th>Top Signal</th><th>Score</th><th>Sentiment</th><th>Opportunity</th></tr>
[one row per genre, ranked 1 = most under-served opportunity first, using each genre's real Top Signal/Score/Sentiment from the digests above. Opportunity column: one short phrase, e.g. "high demand, weak supply" or "crowded, low differentiation".]
</table>
<p>[1-2 sentences calling out the single most under-served genre and the most crowded one]</p></div>

PART 2 — the report closing, as HTML:
<div class="card"><h2>Strategic Recommendations</h2><p>[top 3 product bets across all genres, top 2 things to avoid, and one contrarian insight — 2-3 sentences each, not a full paragraph per item]</p></div>
<div class="card"><h2>Data Quality</h2>
<table><tr><th>Genre</th><th>Coverage</th></tr>
[one row per genre: <td>Genre name</td><td><span class="badge badge-{{high|med|low}}">A-F grade</span></td> — use each genre's real Data Coverage letter from the digests above; badge-high for A/B, badge-med for C, badge-low for D/F]
</table>
<p>[1-2 sentences on overall confidence and any genre whose sample is notably thin]</p></div>

The Data Quality section is required — do not run out of room before writing it.

Be specific. No platitudes — a founding team makes real decisions from this. Every score, percentage, and grade must be one already given in the digests above — never invent one."""


# Pure CSS only — this constant gets dropped verbatim into a real <style> tag
# by _run_multi_genre/_run_multi_year_game, so it must never contain prose
# (a stray sentence there is invalid CSS and can silently invalidate the
# whole first rule it gets glued onto — that's how the shared body{} layout
# rule went missing in production even though it reads fine here as a string).
DESIGN_CSS = """
body { background:#ffffff; color:#1a1a1a; font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif; line-height:1.6; max-width:1000px; margin:0 auto; padding:40px 24px; }
h1 { color:#ff6b2b; font-size:34px; letter-spacing:-0.02em; }
h2 { color:#1a1a1a; border-bottom:2px solid #ff6b2b; padding-bottom:8px; margin-top:40px; }
h3 { color:#ff6b2b; }
.card { background:#f7f7f7; border:1px solid #e5e5e5; border-radius:12px; padding:24px; margin:16px 0; }
.bar-track { background:#e5e5e5; border-radius:4px; height:18px; overflow:hidden; }
.bar-fill { background:#ff6b2b; height:100%; border-radius:4px; }
table { width:100%; border-collapse:collapse; }
th,td { text-align:left; padding:8px 10px; border-bottom:1px solid #e5e5e5; }
th { color:#ff6b2b; font-size:13px; text-transform:uppercase; letter-spacing:0.05em; }
blockquote { border-left:3px solid #ff6b2b; padding-left:16px; color:#444; font-style:italic; margin:12px 0; }
/* safety net: this report is assembled from several separately-generated
   fragments; forcing dark text here means even a fragment that adds its
   own stray color still reads fine against the white page. */
p, li, td { color:#1a1a1a !important; }
.badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; }
.badge-high { background:rgba(34,153,84,0.12); color:#1a7a42; }
.badge-med  { background:rgba(217,164,6,0.12); color:#9c6b05; }
.badge-low  { background:rgba(220,38,38,0.12); color:#b91c1c; }
"""

# Instructional wrapper for build_prompt()'s single-genre path, where Claude
# writes its own <style> tag from these instructions rather than us splicing
# raw CSS into the page — safe to include prose here since none of it is
# ever output verbatim.
DESIGN_SPEC = f"""
Use this exact clean, light design system:
{DESIGN_CSS}
Include a CSS-only bar chart for the signal scores and a styled table for competitors.
"""


def build_prompt(backtest_years: list, validation_years: list,
                 analysis_by_year: dict, genre: str | None = None) -> tuple:
    ids = count(1)
    registry = {}

    bt  = ", ".join(str(y) for y in sorted(backtest_years))
    val = ", ".join(str(y) for y in sorted(validation_years))
    has_val = bool(validation_years)
    scope_note = (f"\nScope: this data covers only the {GENRES[genre]['label']} genre — "
                  f"frame gaps and competitors within that genre, not mobile games broadly.\n"
                  if genre else "")

    bt_data = "".join(_year_block(y, analysis_by_year[str(y)], ids, registry)
                      for y in sorted(backtest_years))

    val_data = ""
    if has_val:
        val_data = "\n## VALIDATION DATA — what actually happened (" + val + ")\n"
        val_data += "".join(_year_block(y, analysis_by_year[str(y)], ids, registry)
                            for y in sorted(validation_years))

    n = 5 if has_val else 4
    backtest_note = (
        f"\nYou are running a MARKET BACKTEST: analyse {bt} as if predicting at "
        f"that time, then use the {val} validation data to score how accurate "
        f"those signals turned out to be.\n" if has_val else ""
    )

    prompt = f"""You are running in non-interactive report-generation mode. Output ONLY a complete, self-contained HTML document (<!DOCTYPE html> ... </html>). No tool calls, no markdown fences, no commentary — just the HTML.

You are a senior market-intelligence analyst. From real scraped data across Reddit, Steam reviews, Google Play, Hacker News, gaming-news outlets (IGN/Polygon/Eurogamer/etc.), Steam's most-played trending list, and Wikipedia interest trends, find genuine GAPS in the market — unmet player needs that no current product serves well. Use the news/trending/Wikipedia signals for *what's rising*, and the reviews/discussion for *what players are frustrated by*.
{scope_note}{backtest_note}
## DATA ({bt})
{bt_data}
{val_data}

## REPORT REQUIREMENTS
Produce a premium HTML intelligence report with these sections:

1. Executive Summary — the single biggest finding and the size of the opportunity, in 2-3 tight paragraphs.
2. Market Gap Analysis — the top 3-5 unmet needs. For each: name the gap, cite the signal score + hit count, include at least one real player quote, and explain why no current competitor fills it. A real gap = high demand AND low satisfaction with what exists. Be honest if a "gap" is weak. Every gap you name must include at least one quote ID in brackets, e.g. [Q7], pulled from the quotes list above. Do not invent quotes or IDs — if you don't have a real quote for a gap, say so instead of fabricating one.
3. Year-over-Year Trends ({bt}) — how signals evolved. Use specific numbers, not vague narrative.
4. Competitive Landscape — where the named competitors are failing their players, mapped to the gaps.
{"5. Backtesting Accuracy — compare the " + bt + " signals against " + val + " reality. Which gaps were real? Score the predictive accuracy honestly." if has_val else ""}
{n+1}. Strategic Recommendations — top 3 product bets the data supports, top 2 things to avoid, and one contrarian insight.
{n+2}. Data Quality — rate coverage per platform (A-F) and state overall confidence. Flag where the sample is thin.

Be specific. Cite exact numbers. Use real quotes. No platitudes — a founding team makes real decisions from this.

## DESIGN
{DESIGN_SPEC}
"""
    return prompt, registry


_QUOTE_ID_RE = re.compile(r'\[Q(\d+)\]')


def validate_citations(html: str, registry: dict) -> dict:
    """Loose, heuristic check that Claude's HTML actually grounds its named
    gaps in real quotes — not a real HTML parser (regex + a "did this gap
    block cite anything" pass is enough for this). Handles two shapes:
    the single-genre report's one <h2>Market Gap Analysis</h2> section with
    a <h3> per gap, and the multi-genre report's one <h4>Market Gap</h4>
    block per per-genre <div class="card">.
    """
    cited_ids = {f"Q{n}" for n in _QUOTE_ID_RE.findall(html)}
    hallucinated_ids = sorted(qid for qid in cited_ids if qid not in registry)

    uncited_gaps = []

    gap_section = re.search(
        r'<h2[^>]*>\s*(?:\d+\.\s*)?Market Gap Analysis.*?</h2>(.*?)(?=<h2|\Z)',
        html, re.IGNORECASE | re.DOTALL)
    if gap_section:
        # each gap is expected to render as its own <h3> block within the section
        for block in re.split(r'(?=<h3[^>]*>)', gap_section.group(1)):
            heading = re.search(r'<h3[^>]*>(.*?)</h3>', block, re.IGNORECASE | re.DOTALL)
            if not heading:
                continue
            if not _QUOTE_ID_RE.search(block):
                uncited_gaps.append(re.sub(r'<[^>]+>', '', heading.group(1)).strip())

    for m in re.finditer(r'<h4[^>]*>\s*(?:Market Gap|Exposed Gaps)\s*</h4>(.*?)(?=<h4|</div>|\Z)',
                        html, re.IGNORECASE | re.DOTALL):
        if not _QUOTE_ID_RE.search(m.group(0)):
            preceding_h3s = re.findall(r'<h3[^>]*>(.*?)</h3>', html[:m.start()],
                                       re.IGNORECASE | re.DOTALL)
            label = re.sub(r'<[^>]+>', '', preceding_h3s[-1]).strip() if preceding_h3s else "unknown genre"
            uncited_gaps.append(f"{label} — Market Gap")

    return {
        "valid": not hallucinated_ids and not uncited_gaps,
        "hallucinated_ids": hallucinated_ids,
        "uncited_gaps": uncited_gaps,
    }


def _run_multi_genre(backtest_years: list, validation_years: list, has_val: bool,
                     analysis_by_year_genre: dict, genres: list) -> tuple:
    """Runs one Claude call per genre, concurrently, then a final small
    synthesis call for the cross-genre wrapper sections — instead of the one
    giant call across all genres that used to push generation time past
    Vercel's 300s ceiling on data-heavy years. Wall-clock time is roughly
    one genre call's duration (they run in parallel, not len(genres) times
    that) plus one synthesis call, instead of len(genres) calls' worth of
    content squeezed into a single sequential call.

    Returns (html, registry) — registry merges every genre's quote IDs plus
    the synthesis call doesn't mint any new ones, so validate_citations still
    works the same way against the final assembled document."""
    blocks, registry = _prep_multi_genre_blocks(
        backtest_years, validation_years, analysis_by_year_genre, genres)

    def _run_genre(g):
        prompt = _genre_section_prompt(g, blocks[g], backtest_years, validation_years, has_val)
        raw = llm.generate_html(prompt, max_tokens=2500)
        digest, _, section_html = raw.partition("===DIGEST-END===")
        return g, digest.strip(), section_html.strip()

    with ThreadPoolExecutor(max_workers=len(genres)) as ex:
        results = list(ex.map(_run_genre, genres))

    digests = {g: d for g, d, _ in results}
    sections_html = "\n".join(s for _, _, s in results if s)

    synth_prompt = _synthesis_prompt(digests, genres, backtest_years, validation_years, has_val)
    synth_raw = llm.generate_html(synth_prompt, max_tokens=3500)
    opening_html, _, closing_html = synth_raw.partition("===MID-END===")

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{DESIGN_CSS}
</style>
</head>
<body>
{opening_html.strip()}
{sections_html}
{closing_html.strip()}
</body>
</html>"""
    return html, registry


def generate(backtest_years: list, validation_years: list | None = None,
             genre: str | None = None) -> str:
    """Run analysis for the needed years, then ask Claude to write the report.

    genre=<key> scopes everything to one genre (unchanged single-genre path,
    one call, max_tokens=32000).

    genre=None (default) runs analysis once per active genre per year, then
    generates the report as one smaller Claude call per genre (run
    concurrently via _run_multi_genre) plus a final small synthesis call for
    the cross-genre sections — replacing the single mega-call across all
    genres that used to push generation time past Vercel's 300s ceiling on
    data-heavy years (e.g. 2022 after a full re-scrape, ~1,265 items — the
    same scale as 2026's original bloat). This buys speed through
    parallelism rather than through asking for a thinner report."""
    validation_years = validation_years or []
    years = set(backtest_years) | set(validation_years)
    has_val = bool(validation_years)

    if genre:
        analysis_by_year = {str(y): analyse(y, genre) for y in years}
        prompt, registry = build_prompt(backtest_years, validation_years, analysis_by_year, genre)
        html = llm.generate_html(prompt, max_tokens=32000)
    else:
        analysis_by_year_genre = {str(y): {g: analyse(y, g) for g in ACTIVE_GENRES}
                                  for y in years}
        html, registry = _run_multi_genre(backtest_years, validation_years, has_val,
                                          analysis_by_year_genre, ACTIVE_GENRES)

    result = validate_citations(html, registry)
    if not result["valid"]:
        print(f"[report.generate] citation validation failed — "
              f"hallucinated_ids={result['hallucinated_ids']} "
              f"uncited_gaps={result['uncited_gaps']}")

    return html


def _prep_game_year_blocks(years: list, analysis_by_year: dict) -> tuple:
    """Pre-formats each year's data block once, up front, assigning globally
    unique quote IDs — same reasoning as _prep_multi_genre_blocks: doing this
    synchronously before any LLM call means the per-year game calls (see
    _game_year_fit_prompt/_game_year_competitive_prompt) can run concurrently
    without coordinating over IDs.

    Returns (blocks, registry) where blocks[year] is a formatted str."""
    ids = count(1)
    registry = {}
    blocks = {y: _year_block(y, analysis_by_year[str(y)], ids, registry)
              for y in sorted(years)}
    return blocks, registry


def _game_year_fit_prompt(year: int, block: str, game_text: str, game_label: str) -> str:
    """Half of one year's slice of the game-fit report — signals + fit + gaps
    only. Split from competitive analysis (see _game_year_competitive_prompt)
    into its own call so the two run concurrently instead of one call doing
    both: wall-clock for the per-year stage is the slowest single call, and
    trimming prose length alone didn't meaningfully cut that call's duration
    (the cost is the cross-referencing reasoning, not the word count) — so
    this halves the reasoning load per call instead."""
    return f"""You are running in non-interactive report-generation mode. Output ONLY the two parts described below — no <!DOCTYPE>/<html>/<head>/<body> wrapper, no markdown fences, no commentary.

You are a senior market-intelligence analyst comparing a studio's uploaded game design against real scraped player-market data (Reddit, Steam reviews, Google Play, Hacker News, gaming-news outlets, Steam trending, Wikipedia interest) for {year} only.

## THE GAME — "{game_label}"
{game_text[:4000]}

## MARKET DATA ({year})
{block}

## OUTPUT
Output exactly two parts, separated by a line containing only: ===DIGEST-END===

PART 1 (before the separator): plain text, no HTML, in exactly this format — real values pulled from the DATA above, not invented:
Market Fit: <one sentence — the strongest way this game already matches {year} demand, citing a real signal score + hit count>
Biggest Gap: <one sentence — the single unmet {year} player need this game does NOT currently address, citing a real signal score + hit count>
Sentiment: <positive>% positive / <negative>% negative
Data Coverage: <A-F, your judgment of how thin or solid this year's sample is, one letter only, plus a 3-6 word reason (e.g. "thin sample outside core platforms")>
This feeds a final executive summary and a data-quality table, so all four lines must be real values from the DATA section above.

PART 2 (after the separator): the HTML section for this year. This fragment gets embedded into a page with its own stylesheet you do not see — do not add any color, background, or background-color styles anywhere, inline or otherwise, and do not add your own <style> tag. The only inline styles you should use are the layout ones shown in the bar-chart example below (width/flex/gap/margin). This is a visual intelligence report, not a text summary — go deep, the way a paid analyst deliverable would: cite every relevant number and don't settle for one sentence where the data supports three.
<div class="card">
<h3>{year} — Market Fit &amp; Gaps</h3>
<h4>Market Fit</h4>
[one row per signal from the data above, strongest first — the chart IS the market-fit analysis, not a reference for prose below it. Each row must carry a fit-quality badge classifying how well the game's design (from THE GAME section above) serves that signal. Use this exact pattern — e.g. for a signal scoring 8.5/10 that the game serves well:]
<div style="display:flex;align-items:center;gap:10px;margin:6px 0"><span style="width:230px">Signal Name <span class="badge badge-high">STRONG FIT</span></span><div class="bar-track" style="flex:1"><div class="bar-fill" style="width:85%"></div></div><span>8.5/10</span></div>
[repeat for every signal in the data above — do not skip any, do not invent scores. Badge per row: badge-high "STRONG FIT" (design clearly serves this) or "AVOIDED" (a negative signal, like ad-fatigue, that the design correctly sidesteps); badge-med "PARTIAL FIT" (served incompletely); badge-low "MISS" (not addressed at all).]
<p>[2-3 sentences: the single clearest takeaway from the chart above — which STRONG FIT row matters most and why, citing its real score + hit count and the specific part of the game's design that earns it]</p>

<h4>Exposed Gaps</h4>
[a ranked table of every signal this game does NOT currently serve well, worst first — do not skip any real gap, do not invent one:]
<table><tr><th>Gap</th><th>Signal Score</th><th>Hits</th><th>Severity</th></tr>
<tr><td>Gap name</td><td>X/10</td><td>N hits</td><td><span class="badge badge-low">CRITICAL</span></td></tr>
[one row per real gap — badge-low for CRITICAL (top-ranked unaddressed signal), badge-med for SIGNIFICANT, badge-high for MINOR]
</table>
<p>[for the single most critical gap in the table above: 2-3 sentences on why it matters and how the game's existing mechanics (from THE GAME section) could plausibly be extended to address it — be concrete, not generic]</p>
<blockquote>"[a real player quote backing the top gap]" [Qn]</blockquote>
[Do not invent the quote or its ID — it must be a real [Qn] from the data above.]
</div>

Be specific. Cite exact numbers. Use real quotes. No platitudes — this feeds a real product decision for this exact game. Every number in your HTML must come from the DATA section above — never invent a score, a mention count, or a percentage."""


def _game_year_competitive_prompt(year: int, block: str, game_text: str, game_label: str) -> str:
    """The other half of one year's slice — competitive analysis only, no
    digest needed since the synthesis call doesn't reference it. Runs
    concurrently with _game_year_fit_prompt for the same year."""
    return f"""You are running in non-interactive report-generation mode. Output ONLY the HTML fragment described below — no <!DOCTYPE>/<html>/<head>/<body> wrapper, no markdown fences, no commentary, no digest text.

You are a senior market-intelligence analyst comparing a studio's uploaded game design against real scraped player-market data (Reddit, Steam reviews, Google Play, Hacker News, gaming-news outlets, Steam trending, Wikipedia interest) for {year} only.

## THE GAME — "{game_label}"
{game_text[:4000]}

## MARKET DATA ({year})
{block}

## OUTPUT
This fragment gets embedded into a page with its own stylesheet you do not see — do not add any color, background, or background-color styles anywhere, inline or otherwise, and do not add your own <style> tag.
<div class="card">
<h3>{year} — Competitive Landscape</h3>
<h4>Competitors</h4>
[a table of the top 4 named competitors by mention count from the data above — do not invent competitors:]
<table><tr><th>Competitor</th><th>Mentions</th><th>Sentiment</th><th>Contrast</th></tr>
<tr><td>Name</td><td>N mentions</td><td>X% pos / Y% neg</td><td>[one short phrase: what's failing this competitor with players, and whether this game's design avoids or shares that failure]</td></tr>
[one row per competitor, top 4 only]</table>
<h4>Competitive Position</h4>
<p>[2-3 sentences: synthesize the table above into the single most useful competitive insight for {year} — e.g. a shared failure mode across several competitors this game structurally avoids, or a sentiment number that cuts against the obvious read]</p>
</div>

Be specific. Cite exact numbers. No platitudes — this feeds a real product decision for this exact game. Every number in your HTML must come from the DATA section above — never invent a mention count or a percentage."""


def _game_synthesis_prompt(digests: dict, years: list, game_text: str, game_label: str) -> str:
    """The cross-year wrapper sections (exec summary, recommendations, data
    quality) only need each year's short digest, not the raw scraped data, so
    this call stays small and fast even though it runs after every per-year
    call. Keeps a short slice of the game text too, since recommendations
    need to be grounded in the actual design, not just the digests."""
    yrs = ", ".join(str(y) for y in sorted(years))
    digest_text = "\n\n".join(f"### {y}\n{digests[y]}" for y in sorted(years))

    return f"""You are running in non-interactive report-generation mode. Output ONLY the two parts described below — no <!DOCTYPE>/<html>/<head>/<body> wrapper, no markdown fences, no commentary.

You are a senior market-intelligence analyst writing the opening and closing sections of a market-fit report for "{game_label}". Each year's detailed section has already been written by a separate analyst; you are writing only the parts that need a view across all of them.

## THE GAME — "{game_label}"
{game_text[:2000]}

## PER-YEAR DIGESTS ({yrs})
{digest_text}

## OUTPUT
Output exactly two parts, separated by a line containing only: ===MID-END===

These fragments get embedded into a page with its own stylesheet you do not see — do not add any color, background, or background-color styles anywhere, inline or otherwise, and do not add your own <style> tag.

PART 1 — the report opening, as HTML:
<h1>{game_label} — Market Fit Report</h1>
<div class="card"><h2>Executive Summary</h2><p>[3-4 tight paragraphs, in this order: (1) the game's strongest genuine market fit, naming the specific design elements that earn it, with real numbers; (2) the single most damaging exposed gap across {yrs}, with real numbers and why it's structurally hard to ignore; (3) how the game's competitive position nets out against the named competitors; (4) a closing read on overall opportunity size and the biggest risk to it. Use real numbers from the digests above throughout — this should read like a paid analyst deliverable, not a summary.]</p></div>

PART 2 — the report closing, as HTML:
<div class="card"><h2>Strategic Recommendations</h2>
<h3>Recommendation 1</h3><p>[a concrete change grounded in the digests above, with an implementation note on how it fits the game's existing mechanics]</p>
<h3>Recommendation 2</h3><p>[a concrete change grounded in the digests above, with an implementation note on how it fits the game's existing mechanics]</p>
<h3>Recommendation 3</h3><p>[a concrete change grounded in the digests above, with an implementation note on how it fits the game's existing mechanics]</p>
<h3>Contrarian Insight</h3><p>[one counterintuitive take the data supports — a reason NOT to chase the top-scoring signal, or a reframe of a perceived weakness as a positioning asset]</p>
</div>
<div class="card"><h2>Data Quality</h2>
<table><tr><th>Year</th><th>Coverage</th><th>Notes</th></tr>
[one row per year: <td>Year</td><td><span class="badge badge-{{high|med|low}}">A-F grade</span></td><td>the real reason string from that year's Data Coverage line in the digests above</td> — badge-high for A/B, badge-med for C, badge-low for D/F]
</table>
<p>[2-3 sentences on overall confidence across {yrs}, which year's sample is thinnest, and what that means for how much weight to put on the findings above]</p></div>

Be specific. No platitudes — this feeds a real product decision for this exact game. Every grade and reason must be one already given in the digests above — never invent one."""


def _run_multi_year_game(years: list, analysis_by_year: dict,
                         game_text: str, game_label: str) -> tuple:
    """Runs two Claude calls per year (fit+gaps, competitive), concurrently
    across every year, then a final small synthesis call — the same fix
    applied to the multi-genre market report, applied here since this path
    had the same single-mega-call shape (one call across every selected year,
    max_tokens=32000) that pushed generation time past Vercel's 300s ceiling
    when a studio picked several years. Splitting further into two calls per
    year (rather than one) exists because trimming prose length alone didn't
    meaningfully cut a single combined call's duration — the cost is the
    cross-referencing reasoning (matching game mechanics to gap data,
    assessing competitor contrast), not the token count, so halving the
    reasoning load per call is what actually buys wall-clock headroom."""
    years = sorted(years)
    blocks, registry = _prep_game_year_blocks(years, analysis_by_year)

    def _run_fit(y):
        prompt = _game_year_fit_prompt(y, blocks[y], game_text, game_label)
        raw = llm.generate_html(prompt, max_tokens=2000)
        digest, _, section_html = raw.partition("===DIGEST-END===")
        return digest.strip(), section_html.strip()

    def _run_competitive(y):
        prompt = _game_year_competitive_prompt(y, blocks[y], game_text, game_label)
        return llm.generate_html(prompt, max_tokens=1600).strip()

    with ThreadPoolExecutor(max_workers=len(years) * 2) as ex:
        fit_futures = {y: ex.submit(_run_fit, y) for y in years}
        comp_futures = {y: ex.submit(_run_competitive, y) for y in years}
        digests = {}
        cards_by_year = {}
        for y in years:
            digest, fit_html = fit_futures[y].result()
            comp_html = comp_futures[y].result()
            digests[y] = digest
            cards_by_year[y] = f"{fit_html}\n{comp_html}"

    sections_html = "\n".join(cards_by_year[y] for y in years if cards_by_year[y])

    synth_prompt = _game_synthesis_prompt(digests, years, game_text, game_label)
    synth_raw = llm.generate_html(synth_prompt, max_tokens=3200)
    opening_html, _, closing_html = synth_raw.partition("===MID-END===")

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{DESIGN_CSS}
</style>
</head>
<body>
{opening_html.strip()}
{sections_html}
{closing_html.strip()}
</body>
</html>"""
    return html, registry


def generate_game_report(years: list, game_text: str, game_label: str = "your game") -> str:
    """Run analysis (aggregated across every active genre) for the needed
    years, then ask Claude to analyse the uploaded game against it — one
    smaller call per year, run concurrently, plus a synthesis call, instead
    of one mega-call across every selected year."""
    years = sorted(set(years))
    analysis_by_year = {str(y): analyse(y) for y in years}
    html, registry = _run_multi_year_game(years, analysis_by_year, game_text, game_label)

    result = validate_citations(html, registry)
    if not result["valid"]:
        print(f"[report.generate_game_report] citation validation failed — "
              f"hallucinated_ids={result['hallucinated_ids']} "
              f"uncited_gaps={result['uncited_gaps']}")

    return html