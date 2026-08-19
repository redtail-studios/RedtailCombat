"""
appstore_scraper.py — year-aware
Scrapes Apple App Store reviews, filtering by year when provided.
"""
import json, time, os
from datetime import datetime
from app_store_scraper import AppStore
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from tqdm import tqdm
from config import APP_STORE_APPS, APP_STORE_REVIEWS, DATA_DIR, get_year_dir


def _parse_year(date_val) -> int | None:
    if date_val is None:
        return None
    if isinstance(date_val, datetime):
        return date_val.year
    try:
        return datetime.fromisoformat(str(date_val)).year
    except Exception:
        pass
    try:
        return int(str(date_val)[:4])
    except Exception:
        return None


def run(year: int = None, output_path: str = None) -> list:
    sia     = SentimentIntensityAnalyzer()
    results = []

    year_label = f" [{year}]" if year else ""
    fetch_count = APP_STORE_REVIEWS * (5 if year else 1)

    print(f"\n[appstore]{year_label} Scraping {len(APP_STORE_APPS)} iOS apps...")

    for app_cfg in tqdm(APP_STORE_APPS, desc=f"AppStore{year_label}"):
        name   = app_cfg["name"]
        app_id = app_cfg["app_id"]

        try:
            store = AppStore(country="us", app_name=name, app_id=app_id)
            store.review(how_many=fetch_count)
            raw_reviews = store.reviews or []
        except Exception as e:
            print(f"  [appstore] Error for {name}: {e}")
            raw_reviews = []

        scored_reviews = []
        for r in raw_reviews:
            if year:
                rev_year = _parse_year(r.get("date"))
                if rev_year is None or rev_year != year:
                    continue

            text = (r.get("review") or "").strip()
            if len(text) < 10:
                continue
            sentiment = sia.polarity_scores(text[:600])
            scored_reviews.append({
                "text":      text[:600],
                "rating":    r.get("rating", 0),
                "title":     r.get("title", ""),
                "date":      str(r.get("date", "")),
                "sentiment": sentiment,
            })
            if len(scored_reviews) >= APP_STORE_REVIEWS:
                break

        results.append({
            "source":  "app_store",
            "app_id":  app_id,
            "name":    name,
            "reviews": scored_reviews,
        })
        time.sleep(2)

    total = sum(len(r["reviews"]) for r in results)
    print(f"  [appstore] Collected {total} reviews")

    out_dir = get_year_dir(year) if year else DATA_DIR
    os.makedirs(out_dir, exist_ok=True)
    path = output_path or os.path.join(out_dir, "appstore_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  → Saved to {path}")

    return results


if __name__ == "__main__":
    run()
