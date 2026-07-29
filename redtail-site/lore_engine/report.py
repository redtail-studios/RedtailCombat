"""
report.py — turn the cheap analysis into a Claude-written HTML intelligence report.

Supports two modes:
  • analyse   — analyse one or more years and find market gaps
  • backtest  — analyse historical years as predictions, then score them against
                later "validation" years (what actually happened)
"""
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


def _fmt_quotes(quotes: list, seen: set | None = None) -> str:
    """seen, when passed, is a cross-genre-section dedup set (see
    _year_block_multi) — general/untagged records count toward every genre's
    analyse() call by design, so the same quote can otherwise repeat verbatim
    in every genre's section of one multi-genre report."""
    if seen is not None:
        quotes = [q for q in quotes if q not in seen]
        for q in quotes[:20]:
            seen.add(q)
    if not quotes:
        return "  (no quotes)"
    return "\n".join(f'  - "{q}"' for q in quotes[:20])


def _year_block(year: int, a: dict) -> str:
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
{_fmt_quotes(a.get('quotes', []))}
"""


def _genre_block(genre: str, a: dict, seen: set) -> str:
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
{_fmt_quotes(a.get('quotes', []), seen)}
"""


def _year_block_multi(year: int, per_genre: dict) -> str:
    # Fresh dedup set per year: a quote already shown under one genre this
    # year is skipped in later genres' sections, but the same quote is fair
    # game again for a different year.
    seen: set = set()
    body = "".join(_genre_block(g, per_genre[g], seen) for g in per_genre)
    return f"\n### {year}\n{body}"


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
                 analysis_by_year: dict, genre: str | None = None) -> str:
    bt  = ", ".join(str(y) for y in sorted(backtest_years))
    val = ", ".join(str(y) for y in sorted(validation_years))
    has_val = bool(validation_years)
    scope_note = (f"\nScope: this data covers only the {GENRES[genre]['label']} genre — "
                  f"frame gaps and competitors within that genre, not mobile games broadly.\n"
                  if genre else "")

    bt_data = "".join(_year_block(y, analysis_by_year[str(y)])
                      for y in sorted(backtest_years))

    val_data = ""
    if has_val:
        val_data = "\n## VALIDATION DATA — what actually happened (" + val + ")\n"
        val_data += "".join(_year_block(y, analysis_by_year[str(y)])
                            for y in sorted(validation_years))

    n = 5 if has_val else 4
    backtest_note = (
        f"\nYou are running a MARKET BACKTEST: analyse {bt} as if predicting at "
        f"that time, then use the {val} validation data to score how accurate "
        f"those signals turned out to be.\n" if has_val else ""
    )

    return f"""You are running in non-interactive report-generation mode. Output ONLY a complete, self-contained HTML document (<!DOCTYPE html> ... </html>). No tool calls, no markdown fences, no commentary — just the HTML.

You are a senior market-intelligence analyst. From real scraped data across Reddit, Steam reviews, Google Play, Hacker News, gaming-news outlets (IGN/Polygon/Eurogamer/etc.), Steam's most-played trending list, and Wikipedia interest trends, find genuine GAPS in the market — unmet player needs that no current product serves well. Use the news/trending/Wikipedia signals for *what's rising*, and the reviews/discussion for *what players are frustrated by*.
{scope_note}{backtest_note}
## DATA ({bt})
{bt_data}
{val_data}

## REPORT REQUIREMENTS
Produce a premium HTML intelligence report with these sections:

1. Executive Summary — the single biggest finding and the size of the opportunity, in 2-3 tight paragraphs.
2. Market Gap Analysis — the top 3-5 unmet needs. For each: name the gap, cite the signal score + hit count, include at least one real player quote, and explain why no current competitor fills it. A real gap = high demand AND low satisfaction with what exists. Be honest if a "gap" is weak.
3. Year-over-Year Trends ({bt}) — how signals evolved. Use specific numbers, not vague narrative.
4. Competitive Landscape — where the named competitors are failing their players, mapped to the gaps.
{"5. Backtesting Accuracy — compare the " + bt + " signals against " + val + " reality. Which gaps were real? Score the predictive accuracy honestly." if has_val else ""}
{n+1}. Strategic Recommendations — top 3 product bets the data supports, top 2 things to avoid, and one contrarian insight.
{n+2}. Data Quality — rate coverage per platform (A-F) and state overall confidence. Flag where the sample is thin.

Be specific. Cite exact numbers. Use real quotes. No platitudes — a founding team makes real decisions from this.

## DESIGN
{DESIGN_SPEC}
"""


def build_prompt_multi(backtest_years: list, validation_years: list,
                       analysis_by_year_genre: dict, genres: list) -> str:
    """Like build_prompt, but data is broken out per active genre instead of
    pooled — Claude sees each genre's signals/competitors/quotes as its own
    labeled section and is asked to compare across them, rather than getting
    one undifferentiated cross-genre blend."""
    bt  = ", ".join(str(y) for y in sorted(backtest_years))
    val = ", ".join(str(y) for y in sorted(validation_years))
    has_val = bool(validation_years)
    genre_list = ", ".join(GENRES[g]["label"] for g in genres)

    bt_data = "".join(_year_block_multi(y, analysis_by_year_genre[str(y)])
                      for y in sorted(backtest_years))

    val_data = ""
    if has_val:
        val_data = "\n## VALIDATION DATA — what actually happened (" + val + ")\n"
        val_data += "".join(_year_block_multi(y, analysis_by_year_genre[str(y)])
                            for y in sorted(validation_years))

    n = 6 if has_val else 5
    backtest_note = (
        f"\nYou are running a MARKET BACKTEST: analyse {bt} as if predicting at "
        f"that time, then use the {val} validation data to score how accurate "
        f"those signals turned out to be.\n" if has_val else ""
    )

    return f"""You are running in non-interactive report-generation mode. Output ONLY a complete, self-contained HTML document (<!DOCTYPE html> ... </html>). No tool calls, no markdown fences, no commentary — just the HTML.

You are a senior market-intelligence analyst covering multiple mobile game genres: {genre_list}. From real scraped data across Reddit, Steam reviews, Google Play, Hacker News, gaming-news outlets (IGN/Polygon/Eurogamer/etc.), Steam's most-played trending list, and Wikipedia interest trends — broken out per genre below — find genuine GAPS in the market, both within each genre and by comparing across genres. Use the news/trending/Wikipedia signals for *what's rising*, and the reviews/discussion for *what players are frustrated by*.
{backtest_note}
## DATA BY YEAR, THEN GENRE ({bt})
{bt_data}
{val_data}

## REPORT REQUIREMENTS
Produce a premium HTML intelligence report with these sections. Keep every
per-genre write-up tight — this covers {len(genres)} genres in one report, so
verbosity per genre multiplies fast; be concise rather than exhaustive.

1. Executive Summary — the single biggest finding across all genres and the size of the opportunity, in 2-3 tight paragraphs.
2. Cross-Genre Comparison — rank the genres by opportunity (demand signal strength vs. how weakly current competitors serve it). Call out which genre has the most under-served demand and which is already crowded/well-served.
3. Market Gap Analysis (per genre) — for each genre with meaningful data, the top 1-2 unmet needs (not 3): name the gap, cite the signal score + hit count, include at least one real player quote, and explain in 1-2 sentences why no current competitor fills it. A real gap = high demand AND low satisfaction with what exists. If a genre's sample is thin or its "gap" is weak, say so in one line rather than padding it out.
4. Year-over-Year Trends ({bt}) — 2-3 sentences per genre on how signals evolved, only where the data actually supports a trend claim.
5. Competitive Landscape — 1-2 sentences per genre on where named competitors are failing their players.
{"6. Backtesting Accuracy — compare the " + bt + " signals against " + val + " reality, per genre, briefly. Which gaps were real? Score the predictive accuracy honestly." if has_val else ""}
{n+1}. Strategic Recommendations — top 3 product bets across all genres, top 2 things to avoid, and one contrarian insight.
{n+2}. Data Quality — rate coverage per platform AND per genre (A-F) and state overall confidence, briefly. Flag where any genre's sample is thin.

Be specific. Cite exact numbers. Use real quotes. No platitudes — a founding team makes real decisions from this. Concise beats exhaustive throughout.

## DESIGN
{DESIGN_SPEC}
"""


def generate(backtest_years: list, validation_years: list | None = None,
             genre: str | None = None) -> str:
    """Run analysis for the needed years, then ask Claude to write the report.

    genre=<key> scopes everything to one genre (unchanged single-genre path).
    genre=None (default) now runs analysis once per active genre per year and
    asks Claude to compare across genres, rather than pooling every genre's
    data into one undifferentiated blend.

    The multi-genre path uses a lower max_tokens than the single-genre path
    (20000 vs 32000): asking Claude to write ~5 genres' worth of report in
    one call is what was pushing wall-clock generation time past Vercel's
    300s function timeout (intermittently, depending on generation speed).
    Combined with the tighter per-genre wording in build_prompt_multi, this
    keeps the requested content comfortably inside the smaller budget rather
    than truncating what would otherwise be a longer, verbose report."""
    validation_years = validation_years or []
    years = set(backtest_years) | set(validation_years)

    if genre:
        analysis_by_year = {str(y): analyse(y, genre) for y in years}
        prompt = build_prompt(backtest_years, validation_years, analysis_by_year, genre)
        return llm.generate_html(prompt, max_tokens=32000)
    else:
        analysis_by_year_genre = {str(y): {g: analyse(y, g) for g in ACTIVE_GENRES}
                                  for y in years}
        prompt = build_prompt_multi(backtest_years, validation_years,
                                    analysis_by_year_genre, ACTIVE_GENRES)
        return llm.generate_html(prompt, max_tokens=20000)


def build_game_prompt(years: list, analysis_by_year: dict,
                      game_text: str, game_label: str) -> str:
    yrs = ", ".join(str(y) for y in sorted(years))
    data = "".join(_year_block(y, analysis_by_year[str(y)]) for y in sorted(years))

    return f"""You are running in non-interactive report-generation mode. Output ONLY a complete, self-contained HTML document (<!DOCTYPE html> ... </html>). No tool calls, no markdown fences, no commentary — just the HTML.

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


def generate_game_report(years: list, game_text: str, game_label: str = "your game") -> str:
    """Run analysis (aggregated across every active genre) for the needed
    years, then ask Claude to analyse the uploaded game against it."""
    analysis_by_year = {str(y): analyse(y) for y in set(years)}
    prompt = build_game_prompt(years, analysis_by_year, game_text, game_label)
    return llm.generate_html(prompt, max_tokens=32000)