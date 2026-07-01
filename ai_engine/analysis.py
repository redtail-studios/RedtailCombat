"""
analysis.py — cheap pre-aggregation over scraped data.

Reads the JSON files produced by the scrapers (which already carry per-item
VADER sentiment) and computes signal scores, a market scorecard, competitor
mentions, and the most signal-rich quotes. This is the structured summary that
gets handed to Claude for the deep gap analysis — it is intentionally fast and
dependency-light (no model calls here), so it runs fine on Vercel.
"""
import json
import os
from collections import defaultdict

from config import DATA_DIR, SIGNAL_KEYWORDS, COMPETITORS, PLATFORM_IDS

DATA_FILES = [f"{pid}_data.json" for pid in PLATFORM_IDS]


# ── Loading ──────────────────────────────────────────────────────────────────
def _iter_records(data_dir: str):
    for fname in DATA_FILES:
        fpath = os.path.join(data_dir, fname)
        if not os.path.exists(fpath):
            continue
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        source = fname.replace("_data.json", "")
        for record in data:
            yield source, record


def load_items(data_dir: str) -> list:
    """Flatten every text fragment (titles, reviews, comments) into items."""
    items = []
    for source, record in _iter_records(data_dir):
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
        for c in record.get("comments", []):
            t = (c.get("body") or c.get("text") or "").strip()
            if len(t) > 10:
                items.append({"source": source, "text": t,
                              "sentiment": c.get("sentiment", {})})
    return items


def top_quotes(data_dir: str, n: int = 25) -> list:
    """Return the n most signal-rich quotes (keyword hits + strong sentiment)."""
    all_kw = {k.lower() for kws in SIGNAL_KEYWORDS.values() for k in kws}
    cands = []
    for _source, record in _iter_records(data_dir):
        texts = []
        for rev in record.get("reviews", []):
            t = (rev.get("text") or rev.get("body") or "").strip()
            if len(t) > 30:
                texts.append((t, rev.get("sentiment", {})))
        for c in record.get("comments", []):
            t = (c.get("body") or c.get("text") or "").strip()
            if len(t) > 30:
                texts.append((t, c.get("sentiment", {})))
        for field in ("title", "text"):
            t = (record.get(field) or "").strip()
            if len(t) > 30:
                texts.append((t, record.get("sentiment", {})))
        for text, sent in texts:
            low = text.lower()
            hits = sum(1 for kw in all_kw if kw in low)
            comp = abs(sent.get("compound", 0))
            if hits > 0 or comp > 0.4:
                cands.append((hits * 2 + comp * 5, text[:220]))
    cands.sort(key=lambda x: -x[0])
    seen, out = set(), []
    for _score, text in cands:
        if text not in seen:
            seen.add(text)
            out.append(text)
        if len(out) >= n:
            break
    return out


# ── Scoring ──────────────────────────────────────────────────────────────────
def signal_scores(items: list) -> dict:
    total = len(items)
    if not total:
        return {}
    counts = defaultdict(int)
    for it in items:
        low = it["text"].lower()
        for signal, kws in SIGNAL_KEYWORDS.items():
            if any(kw.lower() in low for kw in kws):
                counts[signal] += 1
    max_pct = max((counts[s] / total for s in counts), default=0.01)
    out = {}
    for signal in SIGNAL_KEYWORDS:
        hits = counts[signal]
        pct = hits / total
        score = round(min((pct / max(max_pct, 0.001)) * 9.5, 9.9), 1)
        out[signal] = {"score": score, "hits": hits, "pct": round(pct * 100, 1)}
    return out


def scorecard(items: list, sigs: dict) -> dict:
    total = len(items)
    if not total:
        return {}
    pos = sum(1 for i in items if i["sentiment"].get("compound", 0) > 0.05)
    neg = sum(1 for i in items if i["sentiment"].get("compound", 0) < -0.05)
    return {
        "total_items":  total,
        "positive_pct": round(pos / total * 100, 1),
        "negative_pct": round(neg / total * 100, 1),
        "neutral_pct":  round((total - pos - neg) / total * 100, 1),
        "top_signal":   max(sigs, key=lambda s: sigs[s]["score"]) if sigs else None,
    }


def competitors(items: list) -> list:
    agg = defaultdict(lambda: {"mentions": 0, "pos": 0, "neg": 0, "quote": ""})
    for it in items:
        low = it["text"].lower()
        for name, subs in COMPETITORS.items():
            if any(s in low for s in subs):
                s = it["sentiment"].get("compound", 0)
                agg[name]["mentions"] += 1
                if s > 0.05:
                    agg[name]["pos"] += 1
                elif s < -0.05:
                    agg[name]["neg"] += 1
                if not agg[name]["quote"]:
                    agg[name]["quote"] = it["text"][:160]
    out = []
    for name, d in sorted(agg.items(), key=lambda x: -x[1]["mentions"]):
        m = d["mentions"]
        if not m:
            continue
        out.append({
            "name": name, "mentions": m,
            "positive_pct": round(d["pos"] / m * 100),
            "negative_pct": round(d["neg"] / m * 100),
            "quote": d["quote"],
        })
    return out[:6]


def analyse(data_dir: str) -> dict:
    """Full cheap analysis for one data directory (one year)."""
    items = load_items(data_dir)
    sigs  = signal_scores(items)
    return {
        "total_items": len(items),
        "signals":     sigs,
        "scorecard":   scorecard(items, sigs),
        "competitors": competitors(items),
        "quotes":      top_quotes(data_dir, n=25),
    }
