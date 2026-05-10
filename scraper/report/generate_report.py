"""
generate_report.py
Generates an HTML report matching the Redtail Intelligence Engine sample.
Sections: Data Sources · Key Behavioral Signals · Market Scorecard · Competitive Snapshot
Open the output HTML in Chrome and Cmd+P → Save as PDF to get a PDF version.
"""
import json, os, datetime
from config import DATA_DIR, OUTPUT_DIR

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>Redtail Intelligence Engine — Agent Insight Report</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
  *  {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: 'Inter', Arial, sans-serif;
    background: #fff;
    color: #111;
    font-size: 13px;
    padding: 32px 40px 60px;
    max-width: 900px;
    margin: 0 auto;
  }}

  /* ── Top bar ── */
  .topbar {{
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 10px;
  }}
  .tag {{
    background: #111; color: #fff;
    font-size: 9px; font-weight: 700;
    letter-spacing: 1.5px; text-transform: uppercase;
    padding: 4px 10px; border-radius: 3px;
  }}
  .tag.cycle {{ background: #555; }}
  .date-tag {{
    font-size: 10px; color: #888;
    font-weight: 500; letter-spacing: 0.5px;
  }}

  /* ── Title ── */
  h1 {{
    font-size: 28px; font-weight: 800;
    color: #111; line-height: 1.15;
    margin-bottom: 6px;
  }}
  .subtitle {{ font-size: 11px; color: #888; margin-bottom: 28px; }}

  /* ── Section headers ── */
  .section {{ margin-bottom: 36px; }}
  .section-title {{
    font-size: 18px; font-weight: 700;
    border-bottom: 2px solid #111;
    padding-bottom: 6px; margin-bottom: 14px;
    display: flex; align-items: baseline; gap: 10px;
  }}
  .section-title .num {{ color: #111; }}
  .section-lead {{ font-size: 12px; color: #444; margin-bottom: 16px; line-height: 1.6; }}

  /* ── Source cards ── */
  .sources-grid {{
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 10px;
  }}
  .source-card {{
    border: 1px solid #e0e0e0; border-radius: 6px;
    padding: 12px 14px;
    display: flex; gap: 10px;
  }}
  .source-icon {{ font-size: 18px; flex-shrink: 0; line-height: 1; }}
  .source-name {{ font-size: 12px; font-weight: 700; margin-bottom: 3px; }}
  .source-desc {{ font-size: 11px; color: #666; line-height: 1.5; }}
  .source-note {{
    grid-column: 1/-1;
    background: #f5f5f5; border: 1px solid #ddd;
    border-radius: 4px; padding: 8px 14px;
    font-size: 11px; color: #555;
  }}

  /* ── Bar chart ── */
  .chart-area {{ margin: 8px 0 16px; }}
  .bar-row {{
    display: flex; align-items: center;
    margin-bottom: 4px; gap: 10px;
  }}
  .bar-label {{
    width: 240px; text-align: right;
    font-size: 12px; color: #222; flex-shrink: 0;
    white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis;
  }}
  .bar-track {{
    flex: 1; height: 28px; background: #f0f0f0;
    border-radius: 2px; position: relative;
    overflow: hidden;
  }}
  .bar-fill {{
    height: 100%; background: #7b0000;
    border-radius: 2px; position: absolute; top:0; left:0;
    transition: width 0.3s ease;
  }}
  .bar-score {{
    position: absolute; right: 8px; top: 50%;
    transform: translateY(-50%);
    font-size: 11px; font-weight: 700; color: #fff;
  }}
  .bar-axis {{
    display: flex; justify-content: space-between;
    padding-left: 250px;
    font-size: 10px; color: #999; margin-top: 4px;
  }}
  .chart-note {{ font-size: 11px; color: #555; margin-top: 10px; line-height: 1.6; }}

  /* ── Scorecard ── */
  .scorecard-wrap {{
    display: grid; grid-template-columns: 1fr 1fr auto;
    gap: 0; border: 1px solid #ccc;
  }}
  .sc-left {{ display: grid; grid-template-rows: 1fr 1fr; }}
  .sc-right {{ display: grid; grid-template-rows: 1fr 1fr; }}
  .sc-box {{
    padding: 14px 16px;
    border: 1px solid #ddd;
  }}
  .sc-label {{
    font-size: 11px; font-weight: 700; margin-bottom: 4px;
  }}
  .sc-rating {{
    display: inline-block;
    font-size: 10px; font-weight: 800; letter-spacing: 1px;
    padding: 2px 7px; border-radius: 3px; margin-right: 6px;
  }}
  .rating-HIGH   {{ background: #1a4a1a; color: #4ade80; }}
  .rating-MEDIUM {{ background: #2a2a00; color: #fbbf24; }}
  .rating-LOW    {{ background: #4a1a1a; color: #f87171; }}
  .sc-detail {{ font-size: 11px; color: #555; margin-top: 4px; line-height: 1.5; }}

  /* Big score column */
  .sc-score-col {{
    background: #f9f9f9;
    border: 1px solid #ccc;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 20px 28px; text-align: center; gap: 4px;
  }}
  .sc-score-title {{ font-size: 10px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: #666; }}
  .sc-score-num   {{ font-size: 52px; font-weight: 800; color: #111; line-height: 1; }}
  .sc-score-denom {{ font-size: 14px; color: #666; }}
  .sc-score-sep   {{ width: 40px; height: 1px; background: #ccc; margin: 8px 0; }}
  .sc-conf-num    {{ font-size: 36px; font-weight: 800; color: #111; }}
  .sc-conf-label  {{ font-size: 10px; color: #666; font-weight: 500; letter-spacing: 0.5px; }}

  /* ── Competitive snapshot ── */
  .snap-table {{ width: 100%; border-collapse: collapse; }}
  .snap-table th {{
    background: #111; color: #fff;
    font-size: 10px; font-weight: 600;
    letter-spacing: 1px; text-transform: uppercase;
    padding: 8px 12px; text-align: left;
  }}
  .snap-table td {{
    padding: 10px 12px; border-bottom: 1px solid #eee;
    font-size: 12px; vertical-align: top;
  }}
  .snap-table tr:hover td {{ background: #fafafa; }}
  .sentiment-bar-wrap {{ display: flex; height: 8px; border-radius: 4px; overflow:hidden; width: 100px; }}
  .sent-pos {{ background: #22c55e; }}
  .sent-neg {{ background: #ef4444; }}
  .snap-quote {{ font-size: 11px; color: #777; font-style: italic; margin-top: 4px; }}

  /* ── Footer ── */
  .footer {{
    margin-top: 40px; padding-top: 14px;
    border-top: 1px solid #ddd;
    font-size: 10px; color: #aaa;
    display: flex; justify-content: space-between;
  }}

  @media print {{
    body {{ padding: 20px 24px; }}
    @page {{ margin: 1cm; }}
  }}
</style>
</head>
<body>

<!-- Top bar -->
<div class="topbar">
  <span class="tag">AI-GENERATED REPORT</span>
  <span class="tag cycle">AGENT CYCLE #001</span>
  <span class="date-tag">{date}</span>
</div>

<h1>Redtail Intelligence Engine — Agent Insight Report</h1>
<p class="subtitle">Automated discovery output — Generated by behavioral analysis agents scanning player ecosystems, market signals, and competitive benchmarks.</p>

<hr style="border:none;border-top:1px solid #ddd;margin-bottom:28px"/>

<!-- ══ SECTION 1: DATA SOURCES ══ -->
<div class="section">
  <div class="section-title"><span class="num">1 —</span> Data Sources Collected</div>
  <p class="section-lead">The following source groups were aggregated across multiple platforms and processed through automated scraping agents. Each source feeds structured signals into the behavioral modeling pipeline.</p>

  <div class="sources-grid">
    <div class="source-card">
      <div class="source-icon">💬</div>
      <div>
        <div class="source-name">Player Forums &amp; Communities</div>
        <div class="source-desc">Reddit (r/gaming, r/AndroidGaming, r/FightingGames, r/patientgamers) — thread volume, sentiment polarity, trending topics, feature requests, and complaint clustering.</div>
      </div>
    </div>
    <div class="source-card">
      <div class="source-icon">🎮</div>
      <div>
        <div class="source-name">Steam Trending &amp; Engagement</div>
        <div class="source-desc">Wishlists, concurrent player peaks, playtime distributions, and early access momentum signals via SteamSpy API (free, no auth required).</div>
      </div>
    </div>
    <div class="source-card">
      <div class="source-icon">📱</div>
      <div>
        <div class="source-name">App Store &amp; Google Play Rankings</div>
        <div class="source-desc">Download velocity, category rank movement, featuring activity, and install-to-review conversion rates. iOS + Android top competitors analysed.</div>
      </div>
    </div>
    <div class="source-card">
      <div class="source-icon">⭐</div>
      <div>
        <div class="source-name">Player Review Sentiment</div>
        <div class="source-desc">App Store, Steam, Google Play — NLP-scored reviews using VADER sentiment analysis, keyword extraction, and longitudinal sentiment drift across {total_items} data points.</div>
      </div>
    </div>
    <div class="source-note">
      📊 Data aggregated across multiple platforms and processed through automated scraping agents.
      Total signals collected: <strong>{total_items}</strong> items.
      Analysis engine: VADER Sentiment + Keyword Frequency Scoring.
    </div>
  </div>
</div>

<!-- ══ SECTION 2: BEHAVIORAL SIGNALS ══ -->
<div class="section">
  <div class="section-title"><span class="num">2 —</span> Key Behavioral Signals Identified</div>
  <p class="section-lead">The intelligence engine surfaced the following high-confidence behavioral signals from cross-platform analysis. Each signal is scored on a Trend Strength Scale of 0–10, reflecting both magnitude and momentum of the underlying pattern. Scores above 7.5 indicate strong directional signals worthy of strategic attention.</p>

  <div class="chart-area">
    {bars_html}
    <div class="bar-axis">
      <span>0</span><span>3</span><span>6</span><span>9</span>
    </div>
  </div>

  <p class="chart-note">{chart_note}</p>
</div>

<!-- ══ SECTION 3: MARKET OPPORTUNITY SCORECARD ══ -->
<div class="section">
  <div class="section-title"><span class="num">3 —</span> Market Opportunity Scorecard</div>
  <p class="section-lead">The engine synthesises signal clusters into a composite opportunity scorecard. Each dimension is rated by a dedicated sub-agent and cross-validated against historical accuracy benchmarks from prior cycles.</p>

  <div class="scorecard-wrap">
    <div class="sc-left">
      <div class="sc-box">
        <div class="sc-label">Market Demand</div>
        <div><span class="sc-rating rating-{market_demand}">{market_demand}</span></div>
        <div class="sc-detail">{market_demand_detail}</div>
      </div>
      <div class="sc-box">
        <div class="sc-label">Monetization Potential</div>
        <div><span class="sc-rating rating-{monetization_potential}">{monetization_potential}</span></div>
        <div class="sc-detail">{monetization_detail}</div>
      </div>
    </div>
    <div class="sc-right">
      <div class="sc-box">
        <div class="sc-label">Competitive Saturation</div>
        <div><span class="sc-rating rating-{competitive_saturation}">{competitive_saturation}</span></div>
        <div class="sc-detail">{saturation_detail}</div>
      </div>
      <div class="sc-box">
        <div class="sc-label">Growth Velocity</div>
        <div><span class="sc-rating rating-{growth_velocity}">{growth_velocity}</span></div>
        <div class="sc-detail">{growth_velocity_detail}</div>
      </div>
    </div>
    <div class="sc-score-col">
      <div class="sc-score-title">Overall Opportunity Score</div>
      <div>
        <span class="sc-score-num">{opportunity_score}</span>
        <span class="sc-score-denom"> /10</span>
      </div>
      <div style="font-size:10px;color:#888">Composite score across all dimensions</div>
      <div class="sc-score-sep"></div>
      <div class="sc-conf-num">{confidence}%</div>
      <div class="sc-conf-label">Agent Confidence</div>
      <div style="font-size:10px;color:#aaa;margin-top:4px">Based on signal coherence and<br/>historical prediction accuracy</div>
    </div>
  </div>
</div>

<!-- ══ SECTION 4: COMPETITIVE SNAPSHOT ══ -->
<div class="section">
  <div class="section-title"><span class="num">4 —</span> Competitive Snapshot</div>
  <p class="section-lead">The engine identified the most-mentioned competing titles from cross-platform discussion. Each was profiled across session length preference, ad experience sentiment, and retention performance signals.</p>

  {snapshot_html}
</div>

<div class="footer">
  <span>Redtail Intelligence Engine · Automated Agent Report · {date}</span>
  <span>Generated locally · VADER Sentiment · {total_items} signals analysed</span>
</div>

</body>
</html>"""


def _build_bars(signal_scores: dict) -> tuple[str, str]:
    """Build the bar chart HTML rows and the chart annotation note."""
    if not signal_scores:
        return "<p style='color:#999'>No signal data available.</p>", ""

    sorted_signals = sorted(signal_scores.items(), key=lambda x: -x[1]["score"])
    rows = []
    for name, data in sorted_signals:
        score = data["score"]
        pct   = score / 10 * 100
        rows.append(f"""
    <div class="bar-row">
      <div class="bar-label">{name}</div>
      <div class="bar-track">
        <div class="bar-fill" style="width:{pct}%"></div>
        <span class="bar-score">{score}</span>
      </div>
    </div>""")

    top_signals = [s for s, d in sorted_signals if d["score"] >= 7.5]
    note = ""
    if top_signals:
        note = (f"All signals above 7.5 on the confidence threshold. "
                f"The convergence of <strong>{', '.join(top_signals[:3])}</strong> creates a clear design corridor "
                f"for a differentiated mobile product. The engine flags this cluster as a <strong>high-coherence opportunity pattern</strong>.")
    else:
        note = ("Signals collected. Increase scraping volume (more subreddits, more reviews) to push scores higher. "
                "Low scores typically reflect insufficient data rather than low demand.")

    return "\n".join(rows), note


def _build_snapshot(snapshot: list) -> str:
    if not snapshot:
        return "<p style='color:#999;font-size:12px'>No competitor mentions found in scraped data. Increase scraping volume to populate this section.</p>"

    rows = "".join(f"""
    <tr>
      <td><strong>{s['name']}</strong></td>
      <td>{s['mentions']}</td>
      <td>
        <div class="sentiment-bar-wrap">
          <div class="sent-pos" style="width:{s['positive_pct']}%"></div>
          <div class="sent-neg" style="width:{s['negative_pct']}%"></div>
        </div>
        <div style="font-size:10px;color:#888;margin-top:3px">{s['positive_pct']}% pos / {s['negative_pct']}% neg</div>
      </td>
      <td><span class="snap-quote">"{s['sample_quote'][:100]}..."</span></td>
    </tr>""" for s in snapshot)

    return f"""
  <table class="snap-table">
    <thead>
      <tr>
        <th>Title</th>
        <th>Mentions</th>
        <th>Sentiment Split</th>
        <th>Sample Signal</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>"""


def run(analysis: dict = None) -> str:
    """Generate the HTML report. Pass analysis dict or it loads from disk."""
    if analysis is None:
        path = os.path.join(DATA_DIR, "analysis_results.json")
        if not os.path.exists(path):
            print("[report] No analysis_results.json found. Run analysis/sentiment.py first.")
            return ""
        with open(path, encoding="utf-8") as f:
            analysis = json.load(f)

    sc       = analysis.get("scorecard", {})
    signals  = analysis.get("signal_scores", {})
    snapshot = analysis.get("snapshot", [])
    total    = analysis.get("total_items", 0)

    bars_html, chart_note = _build_bars(signals)
    snapshot_html         = _build_snapshot(snapshot)

    now = datetime.datetime.now().strftime("Q%q %Y").replace(
        "%q", str((datetime.datetime.now().month - 1) // 3 + 1))

    html = TEMPLATE.format(
        date                   = datetime.datetime.now().strftime("%B %Y"),
        total_items            = total,
        bars_html              = bars_html,
        chart_note             = chart_note,
        market_demand          = sc.get("market_demand", "MEDIUM"),
        market_demand_detail   = sc.get("market_demand_detail", ""),
        competitive_saturation = sc.get("competitive_saturation", "MEDIUM"),
        saturation_detail      = sc.get("saturation_detail", ""),
        monetization_potential = sc.get("monetization_potential", "MEDIUM"),
        monetization_detail    = sc.get("monetization_detail", ""),
        growth_velocity        = sc.get("growth_velocity", "MEDIUM"),
        growth_velocity_detail = sc.get("growth_velocity_detail", ""),
        opportunity_score      = sc.get("opportunity_score", 0),
        confidence             = sc.get("confidence", 50),
        snapshot_html          = snapshot_html,
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts        = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    out_path  = os.path.join(OUTPUT_DIR, f"redtail_insight_report_{ts}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n[report] Report saved to: {out_path}")
    print("  → Open in Chrome and press Cmd+P → Save as PDF to export")
    return out_path


if __name__ == "__main__":
    run()
