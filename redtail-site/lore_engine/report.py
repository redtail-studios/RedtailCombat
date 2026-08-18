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

PART 1 (before the separator): a plain-text digest, 2-3 sentences, of this genre's single biggest opportunity and how under-served it is — no HTML. This feeds a cross-genre executive summary, so make it a strong, specific standalone claim.

PART 2 (after the separator): the HTML section for this genre, in this structure:
<div class="card">
<h3>{label}</h3>
<p>[2-3 sentences: demand signal strength and sentiment split, with real numbers]</p>
<h4>Market Gap</h4>
<p>[the top 1-2 unmet needs: name each gap, cite the signal score + hit count, include at least one real player quote with its ID in brackets e.g. [Q7], and explain why no current competitor fills it. A real gap = high demand AND low satisfaction with what exists. Be honest if the sample is thin or the gap is weak. Do not invent quotes or IDs.]</p>
<h4>Trends &amp; Competitors</h4>
<p>[how signals evolved across {bt}{" (and how the " + bt + " signals held up against " + val + " reality)" if has_val else ""}, and where named competitors are failing players in this genre]</p>
</div>

Be specific. Cite exact numbers. Use real quotes. No platitudes — a founding team makes real decisions from this."""


def _synthesis_prompt(digests: dict, genres: list, backtest_years: list,
                      validation_years: list, has_val: bool) -> str:
    """The cross-genre wrapper sections (exec summary, ranking, recs, data
    quality) need to see all genres at once, but only need each genre's short
    digest to do that — not the raw scraped data — so this call stays small
    and fast even though it runs after (and depends on) every genre call."""
    bt = ", ".join(str(y) for y in sorted(backtest_years))
    genre_list = ", ".join(GENRES[g]["label"] for g in genres)
    digest_text = "\n".join(f"- {GENRES[g]['label']}: {digests[g]}" for g in genres)

    return f"""You are running in non-interactive report-generation mode. Output ONLY the two parts described below — no <!DOCTYPE>/<html>/<head>/<body> wrapper, no markdown fences, no commentary.

You are a senior market-intelligence analyst synthesizing a multi-genre report covering: {genre_list}. Each genre's detailed section has already been written by a separate analyst; you are writing only the parts that need a view across all of them.

## PER-GENRE DIGESTS ({bt})
{digest_text}

## OUTPUT
Output exactly two parts, separated by a line containing only: ===MID-END===

PART 1 — the report opening, as HTML:
<h1>Mobile Gaming Market Gaps Intelligence Report</h1>
<div class="card"><h2>Executive Summary</h2><p>[2-3 tight paragraphs: the single biggest finding across all genres and the size of the opportunity]</p></div>
<div class="card"><h2>Cross-Genre Comparison</h2><p>[rank the genres by opportunity — demand signal strength vs. how weakly current competitors serve it. Call out which genre has the most under-served demand and which is already crowded/well-served.]</p></div>

PART 2 — the report closing, as HTML:
<div class="card"><h2>Strategic Recommendations</h2><p>[top 3 product bets across all genres, top 2 things to avoid, and one contrarian insight — 2-3 sentences each, not a full paragraph per item]</p></div>
<div class="card"><h2>Data Quality</h2><p>[state overall confidence across genres and flag any genre whose sample is notably thin, in 2-3 sentences]</p></div>

The Data Quality section is required — do not run out of room before writing it.

Be specific. No platitudes — a founding team makes real decisions from this."""


DESIGN_SPEC = """
Use this exact dark, premium design system:

body { background:#0a0a0a; color:#e8e8e8; font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif; line-height:1.6; max-width:1000px; margin:0 auto; padding:40px 24px; }
h1 { color:#ff6b2b; font-size:34px; letter-spacing:-0.02em; }
h2 { color:#e8e8e8; border-bottom:2px solid #ff6b2b; padding-bottom:8px; margin-top:40px; }
h3 { color:#ff6b2b; }
.card { background:#141414; border:1px solid #222; border-radius:12px; padding:24px; margin:16px 0; }
.bar-track { background:#222; border-radius:4px; height:18px; overflow:hidden; }
.bar-fill { background:#ff6b2b; height:100%; border-radius:4px; }
table { width:100%; border-collapse:collapse; }
th,td { text-align:left; padding:8px 10px; border-bottom:1px solid #222; }
th { color:#ff6b2b; font-size:13px; text-transform:uppercase; letter-spacing:0.05em; }
blockquote { border-left:3px solid #ff6b2b; padding-left:16px; color:#ccc; font-style:italic; margin:12px 0; }
.badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; }
.badge-high { background:rgba(74,222,128,0.15); color:#4ade80; }
.badge-med  { background:rgba(251,191,36,0.15); color:#fbbf24; }
.badge-low  { background:rgba(248,113,113,0.15); color:#f87171; }

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

    for m in re.finditer(r'<h4[^>]*>\s*Market Gap\s*</h4>(.*?)(?=<h4|</div>|\Z)',
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
{DESIGN_SPEC}
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


def build_game_prompt(years: list, analysis_by_year: dict,
                      game_text: str, game_label: str) -> tuple:
    ids = count(1)
    registry = {}
    yrs = ", ".join(str(y) for y in sorted(years))
    data = "".join(_year_block(y, analysis_by_year[str(y)], ids, registry)
                   for y in sorted(years))

    prompt = f"""You are running in non-interactive report-generation mode. Output ONLY a complete, self-contained HTML document (<!DOCTYPE html> ... </html>). No tool calls, no markdown fences, no commentary — just the HTML.

You are a senior market-intelligence analyst. A studio has uploaded their own game's design document and wants to know how it stacks up against real scraped player-market data (Reddit, Steam reviews, Google Play, Hacker News, gaming-news outlets, Steam trending, Wikipedia interest) from {yrs}.

## THE GAME — "{game_label}"
{game_text[:6000]}

## MARKET DATA ({yrs})
{data}

## REPORT REQUIREMENTS
Produce a premium HTML intelligence report analysing THIS SPECIFIC GAME against the market data, with these sections:

1. Executive Summary — how well this game's current design lines up with what the market data shows players want, in 2-3 tight paragraphs.
2. Market Fit — which real market gaps/demand signals this game ALREADY serves well, citing signal scores + hit counts + real player quotes.
3. Exposed Gaps — which unmet player needs from the data this game currently does NOT address, and how big a miss that is.
4. Competitive Position — how this game compares to the named competitors given what's failing them with players.
5. Strategic Recommendations — top 3 concrete changes this specific game should make, grounded in the data, plus one contrarian insight.
6. Data Quality — rate coverage per platform (A-F) and state overall confidence. Flag where the sample is thin.

Be specific. Cite exact numbers and real quotes. No platitudes — this feeds a real product decision for this exact game.

## DESIGN
{DESIGN_SPEC}
"""
    return prompt, registry


def generate_game_report(years: list, game_text: str, game_label: str = "your game") -> str:
    """Run analysis (aggregated across every active genre) for the needed
    years, then ask Claude to analyse the uploaded game against it."""
    analysis_by_year = {str(y): analyse(y) for y in set(years)}
    prompt, registry = build_game_prompt(years, analysis_by_year, game_text, game_label)
    html = llm.generate_html(prompt, max_tokens=32000)

    result = validate_citations(html, registry)
    if not result["valid"]:
        print(f"[report.generate_game_report] citation validation failed — "
              f"hallucinated_ids={result['hallucinated_ids']} "
              f"uncited_gaps={result['uncited_gaps']}")

    return html