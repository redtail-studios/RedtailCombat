"""Scraper package. Each module exposes run(year=None, log=print) -> list."""
import json
import os

_sia = None


def score(text: str) -> dict:
    """VADER sentiment for one text (lazy import so the web app needn't load it)."""
    global _sia
    if _sia is None:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        _sia = SentimentIntensityAnalyzer()
    return _sia.polarity_scores((text or "")[:1000])


def save(records: list, data_dir: str, name: str, log=print) -> list:
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, f"{name}_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    log(f"  [{name}] saved {len(records)} records -> {path}")
    return records
