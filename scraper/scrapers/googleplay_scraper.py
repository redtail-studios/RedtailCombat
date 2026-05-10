"""
googleplay_scraper.py — year-aware
Scrapes Google Play reviews, filtering by year when provided.
"""
import json, time, os
from datetime import datetime
from google_play_scraper import search, app, reviews, Sort
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from tqdm import tqdm
from config import GOOGLE_PLAY_QUERY, GOOGLE_PLAY_N_APPS, GOOGLE_PLAY_REVIEWS, DATA_DIR, get_year_dir


def run(year: int = None, output_path: str = None) -> list:
    sia     = SentimentIntensityAnalyzer()
    results = []

    year_label = f" [{year}]" if year else ""
    print(f"\n[googleplay]{year_label} Searching for: '{GOOGLE_PLAY_QUERY}'")

    try:
        search_results = search(GOOGLE_PLAY_QUERY, n_hits=GOOGLE_PLAY_N_APPS, lang="en", country="us")
    except Exception as e:
        print(f"  [googleplay] Search failed: {e}")
        return []

    print(f"  → Found {len(search_results)} apps")

    # Fetch more reviews than needed when year-filtering so we have enough after filtering
    fetch_count = GOOGLE_PLAY_REVIEWS * (4 if year else 1)

    for sr in tqdm(search_results, desc=f"Play{year_label}"):
        app_id = sr.get("appId")
        if not app_id:
            continue

        try:
            details = app(app_id, lang="en", country="us")
        except Exception:
            details = sr

        try:
            app_reviews, _ = reviews(
                app_id,
                lang="en",
                country="us",
                sort=Sort.NEWEST,      # newest first for better year filtering
                count=fetch_count,
            )
        except Exception as e:
            print(f"  [googleplay] Reviews error for {app_id}: {e}")
            app_reviews = []

        scored_reviews = []
        for r in app_reviews:
            # Year filter
            if year:
                rev_date = r.get("at")
                if rev_date is None:
                    continue
                rev_year = rev_date.year if isinstance(rev_date, datetime) else int(str(rev_date)[:4])
                if rev_year != year:
                    if rev_year < year:
                        break  # sorted newest first, so stop when too old
                    continue

            text = (r.get("content") or "").strip()
            if len(text) < 10:
                continue
            sentiment = sia.polarity_scores(text[:600])
            scored_reviews.append({
                "text":      text[:600],
                "score":     r.get("score", 0),
                "thumbs_up": r.get("thumbsUpCount", 0),
                "date":      str(r.get("at", "")),
                "sentiment": sentiment,
            })
            if len(scored_reviews) >= GOOGLE_PLAY_REVIEWS:
                break

        results.append({
            "source":      "google_play",
            "app_id":      app_id,
            "name":        details.get("title", app_id),
            "developer":   details.get("developer", ""),
            "rating":      details.get("score", 0),
            "installs":    details.get("installs", ""),
            "genre":       details.get("genre", ""),
            "description": (details.get("description") or "")[:500],
            "reviews":     scored_reviews,
        })
        time.sleep(2)

    total = sum(len(r["reviews"]) for r in results)
    print(f"  [googleplay] Collected {total} reviews")

    out_dir = get_year_dir(year) if year else DATA_DIR
    os.makedirs(out_dir, exist_ok=True)
    path = output_path or os.path.join(out_dir, "googleplay_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  → Saved to {path}")

    return results


if __name__ == "__main__":
    run()
