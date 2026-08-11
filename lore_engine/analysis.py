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
from collections import defaultdict, deque

from config import DEPLOYED, SIGNAL_KEYWORDS, COMPETITORS, PLATFORM_IDS, SOURCE_WEIGHTS, get_year_dir
import storage
import re
from difflib import SequenceMatcher



# ── Loading ──────────────────────────────────────────────────────────────────
def _iter_records(year: int, genre: str | None = None):
    for pid in PLATFORM_IDS:
        if DEPLOYED:
            records = storage.get_cached_records(year, pid)
            if records is None:  # miss or stale — same silent-skip as before
                continue
        else:
            fpath = os.path.join(get_year_dir(year), f"{pid}_data.json")
            if not os.path.exists(fpath):
                continue
            try:
                with open(fpath, encoding="utf-8") as f:
                    records = json.load(f)
            except Exception:
                continue
        for record in records:
            # Records without a "genre" tag (whole-market signals: news,
            # GitHub, itch.io, Steam charts, Twitch, ...) or tagged "general"
            # always count, regardless of which genre is being filtered for.
            if genre and record.get("genre", "general") not in (genre, "general"):
                continue
            yield pid, record


def load_items(year: int, genre: str | None = None) -> list:
    """Flatten every text fragment (titles, reviews, comments) into items."""
    items = []
    for source, record in _iter_records(year, genre):
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
    return dedupe_items(items)


def top_quotes(year: int, n: int = 25, genre: str | None = None) -> list:
    """Return the n most signal-rich quotes (keyword hits + strong sentiment)."""
    all_kw = {k.lower() for kws in SIGNAL_KEYWORDS.values() for k in kws}
    cands = []
    for source, record in _iter_records(year, genre):
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
                cands.append((hits * 2 + comp * 5, text[:220], source))
    cands.sort(key=lambda x: -x[0])
    # feed candidates through dedupe_items in score order (highest first) so
    # near-duplicate/reworded quotes collapse to their best-scoring phrasing,
    # then the exact-match set below is just a cheap final safety net
    cand_items = [{"source": src, "text": text, "sentiment": {}} for _score, text, src in cands]
    deduped = dedupe_items(cand_items)
    seen, out = set(), []
    for item in deduped:
        text = item["text"]
        if text not in seen:
            seen.add(text)
            out.append(text)
        if len(out) >= n:
            break
    return out


def dedupe_items(items: list, sim_ratio: float = 0.85) -> list:
    """
    Removes duplicate items in terms of context
    """
    queue = deque(maxlen=50) # compare against a bounded window, not the full list pairwise — O(N) not O(N^2) once lore_data/ has thousands of items
    keep = []
    for item in items:
        # normalize text
        text = item["text"]
        text = re.sub(r'[.,!?]', " ", text).lower() # lowercase everything and strip punctuation
        text = re.sub(r'\s+', ' ', text).strip() # removes extraneous whitespace
        # compare for duplicates
        i = 0
        duplicate = None
        while i < len(queue):
            ratio = SequenceMatcher(None, queue[i]["norm"], text).ratio()
            if ratio > sim_ratio:
                # found a duplicate
                duplicate = queue[i]
                break
            i += 1
        if duplicate is not None:
            # found a duplicate, appending new sources
            if item["source"] not in duplicate["sources"]:
                duplicate["sources"].append(item["source"])
        else:
            # found something unique
            elem = {**item, "norm" : text, "sources" : [item["source"]]}
            keep.append(elem)
            queue.append(elem)

    for item in keep:
        # remove norm from final result
        del item["norm"]

    return keep
        


# ── Scoring ──────────────────────────────────────────────────────────────────
def signal_scores(items: list) -> dict:
    total = len(items)
    if not total:
        return {}
    counts = defaultdict(float)
    for it in items:
        source = it["source"]
        low = it["text"].lower()
        for signal, kws in SIGNAL_KEYWORDS.items():
            if any(kw.lower() in low for kw in kws):
                counts[signal] += SOURCE_WEIGHTS.get(source, 1.0)
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
    #pos = sum(1 for i in items if i["sentiment"].get("compound", 0) > 0.05)
    #neg = sum(1 for i in items if i["sentiment"].get("compound", 0) < -0.05)

    pos = 0
    neg = 0
    for i in items:
        source = i["source"]
        if i["sentiment"].get("compound", 0) > 0.05:
            pos += SOURCE_WEIGHTS.get(source, 1.0)
        elif i["sentiment"].get("compound", 0) < -0.05:
            neg += SOURCE_WEIGHTS.get(source, 1.0)
    
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
        source = it["source"]
        low = it["text"].lower()
        for name, subs in COMPETITORS.items():
            if any(s in low for s in subs):
                s = it["sentiment"].get("compound", 0)
                agg[name]["mentions"] += SOURCE_WEIGHTS.get(source, 1.0)
                if s > 0.05:
                    agg[name]["pos"] += SOURCE_WEIGHTS.get(source, 1.0)
                elif s < -0.05:
                    agg[name]["neg"] += SOURCE_WEIGHTS.get(source, 1.0)
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


def analyse(year: int, genre: str | None = None) -> dict:
    """Full cheap analysis for one year. genre=None aggregates across every
    genre scraped for that year (today's original behavior, unchanged)."""
    items = load_items(year, genre)
    sigs  = signal_scores(items)
    return {
        "total_items": len(items),
        "signals":     sigs,
        "scorecard":   scorecard(items, sigs),
        "competitors": competitors(items),
        "quotes":      top_quotes(year, n=25, genre=genre),
    }