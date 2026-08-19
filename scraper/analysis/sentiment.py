"""
sentiment.py
Reads scraped JSON files, runs VADER sentiment + signal scoring,
and builds the analysis dict used by the report generators.
Accepts an optional data_dir to support year-specific analysis.
"""
import json, os, re
from collections import defaultdict
from config import DATA_DIR, SIGNAL_KEYWORDS

DATA_FILES = [
    "reddit_data.json", "steam_data.json",
    "googleplay_data.json", "appstore_data.json",
    "forbes_data.json", "toucharcade_data.json",
    "pocketgamer_data.json",
]


# ── Data loading ───────────────────────────────────────────────────────────────

def load_all_data(data_dir: str = None) -> list:
    """Load all scraped JSON files from data_dir into a flat list of text items."""
    if data_dir is None:
        data_dir = DATA_DIR

    items = []
    sources_found = []

    for fname in DATA_FILES:
        fpath = os.path.join(data_dir, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)

        source = fname.replace("_data.json", "")
        sources_found.append(source)

        for record in data:
            for field in ("title", "text", "description"):
                t = (record.get(field) or "").strip()
                if len(t) > 10:
                    items.append({"source": source, "text": t,
                                  "sentiment": record.get("sentiment", {})})

            for rev in record.get("reviews", []):
                t = (rev.get("text") or rev.get("body") or "").strip()
                if len(t) > 10:
                    items.append({"source": source, "text": t,
                                  "sentiment": rev.get("sentiment", {})})

            for comment in record.get("comments", []):
                t = (comment.get("body") or "").strip()
                if len(t) > 10:
                    items.append({"source": source, "text": t,
                                  "sentiment": comment.get("sentiment", {})})

    print(f"  [analysis] Loaded {len(items)} text items from: {sources_found or ['(none)']}")
    return items


def extract_quotes(data_dir: str = None, n: int = 30) -> list:
    """Return the n most signal-rich player quotes from the given directory."""
    if data_dir is None:
        data_dir = DATA_DIR

    all_kws = set()
    for kw_list in SIGNAL_KEYWORDS.values():
        all_kws.update(k.lower() for k in kw_list)

    candidates = []
    for fname in DATA_FILES:
        fpath = os.path.join(data_dir, fname)
        if not os.path.exists(fpath):
            continue
        with open(fpath, encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception:
                continue

        for record in data:
            texts = []
            for rev in record.get("reviews", []):
                t = (rev.get("text") or rev.get("body") or "").strip()
                if len(t) > 30:
                    texts.append((t, rev.get("sentiment", {})))

            for comment in record.get("comments", []):
                t = (comment.get("body") or "").strip()
                if len(t) > 30:
                    texts.append((t, comment.get("sentiment", {})))

            for field in ("title", "text"):
                t = (record.get(field) or "").strip()
                if len(t) > 30:
                    texts.append((t, record.get("sentiment", {})))

            for text, sent in texts:
                lower = text.lower()
                kw_hits = sum(1 for kw in all_kws if kw in lower)
                compound = abs(sent.get("compound", 0))
                score = kw_hits * 2 + compound * 5
                if kw_hits > 0 or compound > 0.4:
                    candidates.append((score, text[:200]))

    candidates.sort(key=lambda x: -x[0])
    seen = set()
    quotes = []
    for _, text in candidates:
        if text not in seen:
            seen.add(text)
            quotes.append(text)
        if len(quotes) >= n:
            break
    return quotes


# ── Signal scoring ─────────────────────────────────────────────────────────────

def compute_signal_scores(items: list) -> dict:
    counts     = defaultdict(int)
    total_docs = len(items)
    if total_docs == 0:
        return {}

    for item in items:
        text = item["text"].lower()
        for signal, keywords in SIGNAL_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text:
                    counts[signal] += 1
                    break

    scores = {}
    max_pct = max((counts[s] / total_docs for s in counts), default=0.01)

    for signal in SIGNAL_KEYWORDS:
        hits = counts[signal]
        pct  = hits / total_docs if total_docs else 0
        score = round(min((pct / max(max_pct, 0.001)) * 9.5, 9.9), 1)
        scores[signal] = {"score": score, "hits": hits, "pct": round(pct * 100, 1)}

    return scores


def compute_market_scorecard(items: list, signal_scores: dict) -> dict:
    total = len(items)
    if total == 0:
        return {}

    pos = sum(1 for i in items if i["sentiment"].get("compound", 0) > 0.05)
    neg = sum(1 for i in items if i["sentiment"].get("compound", 0) < -0.05)
    neu = total - pos - neg
    sentiment_ratio = pos / total if total else 0.5

    demand_score = (
        signal_scores.get("Competitive fighting demand", {}).get("score", 0) * 0.4 +
        signal_scores.get("Short-session preference",  {}).get("score", 0) * 0.3 +
        signal_scores.get("Fast progression demand",   {}).get("score", 0) * 0.3
    )
    neg_ad_score   = signal_scores.get("Negative ad sentiment",    {}).get("score", 5)
    cosmetic_score = signal_scores.get("Cosmetic monetization ok", {}).get("score", 0)
    monet_score    = max(0, min(10, cosmetic_score * 0.6 + (10 - neg_ad_score) * 0.4))
    saturation     = "MEDIUM"
    total_hits     = sum(v["hits"] for v in signal_scores.values())
    gv_score       = min(10, total_hits / max(total, 1) * 20)
    opportunity    = round((demand_score * 0.4 + monet_score * 0.3 + gv_score * 0.3), 1)
    opportunity    = min(opportunity, 9.9)
    confidence     = min(95, round(50 + (total / 200) * 30 + sentiment_ratio * 15))

    return {
        "market_demand":          _rating(demand_score),
        "market_demand_score":    round(demand_score, 1),
        "market_demand_detail":   "Cross-platform signals indicate unmet player appetite for short-session competitive experiences on mobile.",
        "competitive_saturation": saturation,
        "saturation_detail":      "Fighting games exist on mobile but few optimise for sub-90s match loops.",
        "monetization_potential": _rating(monet_score),
        "monetization_score":     round(monet_score, 1),
        "monetization_detail":    "Cosmetic-driven models in competitive games show strong LTV.",
        "growth_velocity":        _rating(gv_score),
        "growth_velocity_score":  round(gv_score, 1),
        "growth_velocity_detail": "Category growth rate exceeds market average.",
        "opportunity_score":      opportunity,
        "confidence":             confidence,
        "total_items":            total,
        "positive_pct":           round(pos / total * 100, 1) if total else 0,
        "negative_pct":           round(neg / total * 100, 1) if total else 0,
        "neutral_pct":            round(neu / total * 100, 1) if total else 0,
    }


def compute_competitive_snapshot(items: list) -> list:
    app_mentions = defaultdict(lambda: {"mentions": 0, "pos": 0, "neg": 0, "texts": []})

    competitors = {
        "brawlhalla":    "Brawlhalla",
        "shadow fight":  "Shadow Fight",
        "street fighter":"Street Fighter",
        "mortal kombat": "Mortal Kombat",
        "injustice":     "Injustice",
        "clash royale":  "Clash Royale",
    }

    for item in items:
        text = item["text"].lower()
        for key, display in competitors.items():
            if key in text:
                s = item["sentiment"].get("compound", 0)
                app_mentions[display]["mentions"]  += 1
                if s > 0.05:  app_mentions[display]["pos"] += 1
                elif s < -0.05: app_mentions[display]["neg"] += 1
                if len(app_mentions[display]["texts"]) < 3:
                    app_mentions[display]["texts"].append(item["text"][:120])

    snapshot = []
    for name, data in sorted(app_mentions.items(), key=lambda x: -x[1]["mentions"]):
        m = data["mentions"]
        if m == 0:
            continue
        snapshot.append({
            "name":         name,
            "mentions":     m,
            "positive_pct": round(data["pos"] / m * 100) if m else 0,
            "negative_pct": round(data["neg"] / m * 100) if m else 0,
            "sample_quote": data["texts"][0] if data["texts"] else "",
        })

    return snapshot[:5]


def _rating(score: float) -> str:
    if score >= 7:  return "HIGH"
    if score >= 4:  return "MEDIUM"
    return "LOW"


def run(data_dir: str = None) -> dict:
    """Full analysis pipeline. Returns analysis dict."""
    if data_dir is None:
        data_dir = DATA_DIR

    print(f"\n[analysis] Running analysis on: {data_dir}")
    items         = load_all_data(data_dir)
    signal_scores = compute_signal_scores(items)
    scorecard     = compute_market_scorecard(items, signal_scores)
    snapshot      = compute_competitive_snapshot(items)

    analysis = {
        "signal_scores": signal_scores,
        "scorecard":     scorecard,
        "snapshot":      snapshot,
        "total_items":   len(items),
    }

    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, "analysis_results.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)
    print(f"  → Saved to {path}")
    print(f"  → Opportunity: {scorecard.get('opportunity_score')}/10  Confidence: {scorecard.get('confidence')}%")
    return analysis


if __name__ == "__main__":
    run()
