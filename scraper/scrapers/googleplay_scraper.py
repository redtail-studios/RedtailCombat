"""
googleplay_scraper.py
Scrapes Google Play app reviews using google-play-scraper.
No API key required — completely free.
"""
import json, time, os
from google_play_scraper import search, app, reviews, Sort
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from tqdm import tqdm
from config import GOOGLE_PLAY_QUERY, GOOGLE_PLAY_N_APPS, GOOGLE_PLAY_REVIEWS, DATA_DIR


def run(output_path: str = None) -> list:
    sia     = SentimentIntensityAnalyzer()
    results = []

    # 1. Search for relevant apps
    print(f"\n[googleplay] Searching for: '{GOOGLE_PLAY_QUERY}'")
    try:
        search_results = search(
            GOOGLE_PLAY_QUERY,
            n_hits=GOOGLE_PLAY_N_APPS,
            lang="en",
            country="us",
        )
    except Exception as e:
        print(f"  [googleplay] Search failed: {e}")
        return []

    print(f"  → Found {len(search_results)} apps")

    for sr in tqdm(search_results, desc="Play Store apps"):
        app_id = sr.get("appId")
        if not app_id:
            continue

        # 2. Get full app details
        try:
            details = app(app_id, lang="en", country="us")
        except Exception as e:
            print(f"  [googleplay] Detail error for {app_id}: {e}")
            details = sr

        # 3. Get reviews — most relevant first
        try:
            app_reviews, _ = reviews(
                app_id,
                lang="en",
                country="us",
                sort=Sort.MOST_RELEVANT,
                count=GOOGLE_PLAY_REVIEWS,
            )
        except Exception as e:
            print(f"  [googleplay] Reviews error for {app_id}: {e}")
            app_reviews = []

        scored_reviews = []
        for r in app_reviews:
            text = (r.get("content") or "").strip()
            if len(text) < 10:
                continue
            sentiment = sia.polarity_scores(text[:600])
            scored_reviews.append({
                "text":      text[:600],
                "score":     r.get("score", 0),       # 1–5 stars
                "thumbs_up": r.get("thumbsUpCount", 0),
                "sentiment": sentiment,
            })

        results.append({
            "source":       "google_play",
            "app_id":       app_id,
            "name":         details.get("title", app_id),
            "developer":    details.get("developer", ""),
            "rating":       details.get("score", 0),
            "installs":     details.get("installs", ""),
            "price":        details.get("price", 0),
            "genre":        details.get("genre", ""),
            "description":  (details.get("description") or "")[:500],
            "reviews":      scored_reviews,
        })

        time.sleep(2)  # Be polite

    total_reviews = sum(len(r["reviews"]) for r in results)
    print(f"  [googleplay] Collected {total_reviews} reviews across {len(results)} apps")

    os.makedirs(DATA_DIR, exist_ok=True)
    path = output_path or os.path.join(DATA_DIR, "googleplay_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  → Saved to {path}")

    return results


if __name__ == "__main__":
    run()
