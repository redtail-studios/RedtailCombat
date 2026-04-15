"""
appstore_scraper.py
Scrapes Apple App Store reviews using app-store-scraper.
No API key required — completely free.
"""
import json, time, os
from app_store_scraper import AppStore
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from tqdm import tqdm
from config import APP_STORE_APPS, APP_STORE_REVIEWS, DATA_DIR


def run(output_path: str = None) -> list:
    sia     = SentimentIntensityAnalyzer()
    results = []

    print(f"\n[appstore] Scraping {len(APP_STORE_APPS)} iOS apps...")

    for app_cfg in tqdm(APP_STORE_APPS, desc="App Store apps"):
        name   = app_cfg["name"]
        app_id = app_cfg["app_id"]

        try:
            store = AppStore(country="us", app_name=name, app_id=app_id)
            store.review(how_many=APP_STORE_REVIEWS)
            raw_reviews = store.reviews or []
        except Exception as e:
            print(f"  [appstore] Error for {name}: {e}")
            raw_reviews = []

        scored_reviews = []
        for r in raw_reviews:
            text = (r.get("review") or "").strip()
            if len(text) < 10:
                continue
            sentiment = sia.polarity_scores(text[:600])
            scored_reviews.append({
                "text":      text[:600],
                "rating":    r.get("rating", 0),      # 1–5 stars
                "title":     r.get("title", ""),
                "sentiment": sentiment,
            })

        results.append({
            "source":   "app_store",
            "app_id":   app_id,
            "name":     name,
            "reviews":  scored_reviews,
        })

        time.sleep(2)

    total_reviews = sum(len(r["reviews"]) for r in results)
    print(f"  [appstore] Collected {total_reviews} reviews across {len(results)} apps")

    os.makedirs(DATA_DIR, exist_ok=True)
    path = output_path or os.path.join(DATA_DIR, "appstore_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  → Saved to {path}")

    return results


if __name__ == "__main__":
    run()
