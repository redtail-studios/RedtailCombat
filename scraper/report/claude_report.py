"""
claude_report.py
Calls the Claude API to generate a rich HTML intelligence report
from multi-year scraped + VADER-analysed data.
"""
import os
from config import SUPPORTED_YEARS


def _fmt_signals(signal_scores: dict) -> str:
    if not signal_scores:
        return "  (no signal data)\n"
    lines = []
    for sig, d in sorted(signal_scores.items(), key=lambda x: -x[1]["score"]):
        lines.append(f"  • {sig}: {d['score']}/10  ({d['hits']} hits, {d['pct']}% of content)")
    return "\n".join(lines)


def _fmt_competitors(snapshot: list) -> str:
    if not snapshot:
        return "  (no competitor data)\n"
    lines = []
    for c in snapshot:
        lines.append(
            f"  • {c['name']}: {c['mentions']} mentions — "
            f"{c['positive_pct']}% positive / {c['negative_pct']}% negative"
        )
        if c.get("sample_quote"):
            lines.append(f'    Quote: "{c["sample_quote"][:120]}"')
    return "\n".join(lines)


def _fmt_quotes(quotes: list) -> str:
    if not quotes:
        return "  (no quotes)\n"
    return "\n".join(f'  • "{q[:160]}"' for q in quotes[:25])


def build_prompt(
    backtest_years: list[int],
    validation_years: list[int],
    analysis_by_year: dict,
    quotes_by_year: dict,
) -> str:
    bt_str  = ", ".join(str(y) for y in sorted(backtest_years))
    val_str = ", ".join(str(y) for y in sorted(validation_years)) if validation_years else ""
    has_val = bool(validation_years)

    # ── Backtest period data ────────────────────────────────────────────────────
    bt_data = ""
    for year in sorted(backtest_years):
        a = analysis_by_year.get(str(year), {})
        sc = a.get("scorecard", {})
        bt_data += f"\n### {year}\n"
        bt_data += f"Total data points: {a.get('total_items', 0)}\n"
        if sc:
            bt_data += (
                f"Opportunity Score: {sc.get('opportunity_score','?')}/10  |  "
                f"Confidence: {sc.get('confidence','?')}%  |  "
                f"Sentiment: {sc.get('positive_pct',0)}% pos / {sc.get('negative_pct',0)}% neg\n"
            )
        bt_data += "Signal Strengths (0–10 trend scale):\n"
        bt_data += _fmt_signals(a.get("signal_scores", {}))
        bt_data += "\nTop Competitor Mentions:\n"
        bt_data += _fmt_competitors(a.get("snapshot", []))
        bt_data += "\nHigh-Signal Player Quotes:\n"
        bt_data += _fmt_quotes(quotes_by_year.get(str(year), []))
        bt_data += "\n"

    # ── Validation period data ──────────────────────────────────────────────────
    val_data = ""
    if has_val:
        val_data = f"\n## VALIDATION DATA — What Actually Happened ({val_str})\n"
        val_data += "Use this to evaluate whether the backtest predictions were accurate.\n"
        for year in sorted(validation_years):
            a = analysis_by_year.get(str(year), {})
            sc = a.get("scorecard", {})
            val_data += f"\n### {year} Reality\n"
            val_data += f"Total data points: {a.get('total_items', 0)}\n"
            if sc:
                val_data += (
                    f"Opportunity Score: {sc.get('opportunity_score','?')}/10  |  "
                    f"Sentiment: {sc.get('positive_pct',0)}% pos / {sc.get('negative_pct',0)}% neg\n"
                )
            val_data += "Signal Strengths:\n"
            val_data += _fmt_signals(a.get("signal_scores", {}))

    # ── Backtesting note ────────────────────────────────────────────────────────
    backtest_note = ""
    if has_val:
        backtest_note = f"""
## Backtesting Mode
You are performing a **market backtest**: analysing historical data from {bt_str} as if you were making predictions at that time. You also have {val_str} validation data showing what actually happened afterward, so you can score the predictive accuracy of the signals.
"""

    # ── Section numbering ───────────────────────────────────────────────────────
    n = 5 if has_val else 4

    return f"""IMPORTANT SYSTEM INSTRUCTION: You are running in non-interactive report-generation mode. You MUST output ONLY the raw HTML document below — no tool calls, no web searches, no file reads, no bash commands. Just generate the HTML directly from the data provided. Do not use any external tools.

---

You are a senior market intelligence analyst for Redtail Studios — a mobile game startup building a competitive mobile fighting game with sub-90-second matches and cosmetic-only monetization.

## Your Task
Analyse gaming market data from **{bt_str}** and generate a comprehensive HTML intelligence report identifying market gaps, emerging trends, and strategic opportunities for Redtail.
{backtest_note}
## Backtest Data ({bt_str})
{bt_data}
{val_data}

---

## Report Requirements

Generate a **complete, self-contained HTML document** (including <!DOCTYPE html>, <html>, <head>, <body>) with these sections:

**1. Executive Summary**
2–3 punchy paragraphs. What is the single biggest finding? What is the market opportunity size? What should Redtail do with this information?

**2. Market Gap Analysis**
Identify the top 3–5 unmet player needs backed by signal data. For each gap:
- Name the gap
- Cite the signal score and hit count
- Include at least one direct player quote
- Explain why no current competitor is filling it

**3. Year-over-Year Signal Trends ({bt_str})**
How did each signal evolve across the years? What was a weak early signal that became mainstream? What declined? Use the data — specific numbers, not vague narratives.

**4. Competitive Landscape**
Where are Brawlhalla, Shadow Fight, Street Fighter, Clash Royale failing their players? Map competitor weaknesses to Redtail's positioning.

{"**5. Backtesting Accuracy Assessment**" if has_val else ""}
{("Compare predictions from " + bt_str + " data against " + val_str + " reality. Score each signal's predictive accuracy. Were the gaps real?") if has_val else ""}

**{n+1}. Strategic Recommendations for Redtail**
Given: competitive mobile fighting game, sub-90s matches, cosmetic monetization, 2026 launch target.
- Top 3 product bets the data validates
- Top 2 things to avoid based on negative signals
- Recommended launch window and platform priority
- One contrarian insight the data reveals

**{n+2}. Risk Factors**
What market conditions or player signals should concern Redtail's leadership?

**{n+3}. Data Quality Assessment**
Rate the dataset quality (A–F per platform), note coverage gaps, and state the confidence level of the overall analysis.

---

## HTML Design Specification
Use this exact design system — dark, premium, VC-deck quality:

```css
body {{ background: #0a0a0a; color: #e8e8e8; font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif; }}
h1 {{ color: #ff6b2b; }}
h2 {{ color: #e8e8e8; border-bottom: 2px solid #ff6b2b; padding-bottom: 8px; }}
h3 {{ color: #ff6b2b; }}
.card {{ background: #141414; border: 1px solid #222; border-radius: 12px; padding: 24px; margin: 16px 0; }}
.signal-bar {{ background: #222; border-radius: 4px; height: 20px; }}
.signal-fill {{ background: #ff6b2b; border-radius: 4px; height: 100%; }}
.positive {{ color: #4ade80; }}
.negative {{ color: #f87171; }}
.neutral {{ color: #999; }}
blockquote {{ border-left: 3px solid #ff6b2b; padding-left: 16px; color: #ccc; font-style: italic; }}
.badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; }}
.badge-high {{ background: rgba(74,222,128,0.15); color: #4ade80; }}
.badge-med {{ background: rgba(251,191,36,0.15); color: #fbbf24; }}
.badge-low {{ background: rgba(248,113,113,0.15); color: #f87171; }}
```

Include a CSS-only bar chart for the signal scores section. Include a styled table for competitor data. Make the report look like a premium strategy document.

**Important**: Be specific. Cite exact numbers. Include real player quotes. Make concrete, actionable recommendations — not generic platitudes. This report goes directly to a founding team making real product decisions with real capital.
"""


def test_claude_cli() -> bool:
    """Quick smoke-test: can the claude CLI respond to a short prompt?"""
    import subprocess, shutil
    if not shutil.which("claude"):
        print("  [test] FAIL — claude not on PATH")
        return False
    try:
        r = subprocess.run(
            ["claude", "--dangerously-skip-permissions", "-p", "Say the single word: HELLO"],
            capture_output=True, text=True, timeout=60, cwd="/tmp",
        )
        print(f"  [test] returncode={r.returncode}")
        print(f"  [test] stdout={repr(r.stdout[:300])}")
        print(f"  [test] stderr={repr(r.stderr[:300])}")
        return bool(r.stdout.strip())
    except subprocess.TimeoutExpired:
        print("  [test] FAIL — timed out after 60s")
        return False
    except Exception as e:
        print(f"  [test] FAIL — {e}")
        return False


def _strip_code_fence(html: str) -> str:
    """Strip markdown code fences if Claude wrapped the response in one."""
    html = html.strip()
    if html.startswith("```html"):
        html = html[7:]
    elif html.startswith("```"):
        html = html[3:]
    if html.endswith("```"):
        html = html[:-3]
    return html.strip()


def _via_claude_cli(prompt: str) -> str:
    """
    Use the local `claude -p <prompt>` CLI (Claude Code) — no API key needed.

    --allowedTools "" disables the agentic tool loop so claude does a plain
    text completion rather than spending 8+ minutes browsing/writing files.
    """
    import subprocess, threading, shutil

    claude_path = shutil.which("claude")
    if not claude_path:
        raise RuntimeError("claude CLI not found on PATH.")

    print(f"  [claude] {claude_path}")
    print(f"  [claude] Prompt: {len(prompt):,} chars")
    print("  [claude] Running: --tools '' disables all tools → pure completion, no agentic loop")

    proc = subprocess.Popen(
        [
            "claude",
            "--dangerously-skip-permissions",
            "--tools", "",            # disable ALL tools → direct LLM completion only
            "--no-session-persistence",
            "-p", prompt,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd="/tmp",
    )

    print(f"  [claude] PID {proc.pid}")

    stderr_lines: list[str] = []

    def _drain_stderr():
        for line in proc.stderr:
            line = line.rstrip()
            if line:
                stderr_lines.append(line)
                print(f"  [claude stderr] {line}")

    def _heartbeat():
        import time
        start = time.time()
        while proc.poll() is None:
            time.sleep(15)
            print(f"  [claude] {int(time.time()-start)}s elapsed...")

    threading.Thread(target=_drain_stderr, daemon=True).start()
    threading.Thread(target=_heartbeat, daemon=True).start()

    try:
        stdout, _ = proc.communicate(timeout=180)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise RuntimeError(
            "claude CLI timed out after 180s.\n"
            "Stderr: " + "\n".join(stderr_lines[-5:])
        )

    # Always log stdout so we can debug unexpected content
    print(f"  [claude] Exit code={proc.returncode} stdout={len(stdout):,}chars stderr_lines={len(stderr_lines)}")
    if stdout.strip():
        print(f"  [claude] stdout preview: {repr(stdout.strip()[:200])}")
    if stderr_lines:
        print("  [claude] stderr:\n  " + "\n  ".join(stderr_lines[-10:]))

    if proc.returncode != 0:
        raise RuntimeError(
            f"claude CLI exited {proc.returncode}.\n"
            f"stdout: {stdout.strip()[:300]}\n"
            "stderr: " + "\n".join(stderr_lines[-10:])
        )

    output = stdout.strip()
    if not output:
        raise RuntimeError(
            "claude CLI returned empty output.\n"
            "stderr: " + "\n".join(stderr_lines[-10:])
        )

    print(f"  [claude] CLI done — {len(output):,} chars")
    return output


def _get_api_key() -> str:
    key = os.getenv("XAI_API_KEY")
    if key:
        return key
    raise ValueError(
        "XAI_API_KEY not set. Add it to your .env file:\n"
        "  XAI_API_KEY=xai-..."
    )


def _via_api(prompt: str) -> str:
    """Use xAI's Grok API (OpenAI-compatible endpoint)."""
    from openai import OpenAI
    api_key = _get_api_key()
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
    model = "grok-3"
    print(f"  [api] Calling xAI Grok API ({model}, max_tokens=12000)...")
    response = client.chat.completions.create(
        model=model,
        max_tokens=12000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.choices[0].message.content
    print(f"  [api] Done — {len(text):,} chars")
    return text


def generate_report_html(
    backtest_years: list[int],
    validation_years: list[int],
    analysis_by_year: dict,
    quotes_by_year: dict,
) -> str:
    """Generate the HTML report via the Anthropic API (ANTHROPIC_API_KEY from .env)."""
    prompt = build_prompt(backtest_years, validation_years, analysis_by_year, quotes_by_year)
    print(f"  [report] Prompt: {len(prompt):,} chars | years: {backtest_years}")

    import time
    last_err = None
    for attempt in range(3):
        try:
            html = _via_api(prompt)
            return _strip_code_fence(html)
        except Exception as e:
            last_err = e
            if "429" in str(e) or "rate_limit" in str(e):
                wait = 60 * (attempt + 1)
                print(f"  [report] Rate-limited, retrying in {wait}s (attempt {attempt+1}/3)...")
                time.sleep(wait)
            else:
                raise

    raise RuntimeError(f"Report generation failed. Last error: {last_err}")
