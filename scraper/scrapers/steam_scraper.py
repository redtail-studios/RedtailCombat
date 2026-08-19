"""
steam_scraper.py — year-aware
Scrapes Steam via SteamSpy + Steam Reviews API.
Filters reviews by year when year param is provided.
"""
import json, time, os, requests
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from tqdm import tqdm
from config import STEAM_GENRE_TAG, STEAM_APP_IDS, STEAM_REVIEWS_PER_APP, DATA_DIR, get_year_dir

STEAMSPY_BASE     = "https://steamspy.com/api.php"
STEAM_REVIEW_BASE = "https://store.steampowered.com/appreviews"


def get_genre_top_games(tag: str = "Fighting", n: int = 20) -> dict:
    print(f"  [steam] Fetching top '{tag}' games from SteamSpy...")
    try:
        resp = requests.get(STEAMSPY_BASE, params={"request": "tag", "tag": tag}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return dict(list(data.items())[:n])
    except Exception as e:
        print(f"  [steam] SteamSpy genre error: {e}")
        return {}


def get_app_details(app_id: str) -> dict:
    try:
        resp = requests.get(STEAMSPY_BASE, params={"request": "appdetails", "appid": app_id}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [steam] SteamSpy detail error for {app_id}: {e}")
        return {}


def get_reviews(app_id: str, count: int = 100, year: int = None) -> list:
    """Fetch reviews, paginating until we have enough or exhaust the year range."""
    url    = f"{STEAM_REVIEW_BASE}/{app_id}"
    cursor = "*"
    all_reviews = []
    pages_checked = 0
    max_pages = 10  # avoid infinite loops

    while pages_checked < max_pages and len(all_reviews) < (count * 3 if year else count):
        params = {
            "json":         1,
            "num_per_page": 100,
            "filter":       "recent",
            "language":     "english",
            "review_type":  "all",
            "purchase_type":"all",
            "cursor":       cursor,
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data     = resp.json()
            batch    = data.get("reviews", [])
            if not batch:
                break
            all_reviews.extend(batch)
            cursor = data.get("cursor", "")
            pages_checked += 1
            if not cursor:
                break
            # If year filter: stop if oldest review in batch is before target year
            if year and batch:
                oldest_ts = min(r.get("timestamp_created", 9999999999) for r in batch)
                oldest_year = datetime.utcfromtimestamp(oldest_ts).year
                if oldest_year < year:
                    break
            time.sleep(0.5)
        except Exception as e:
            print(f"  [steam] Review fetch error for {app_id}: {e}")
            break

    # Filter by year if requested
    if year:
        all_reviews = [
            r for r in all_reviews
            if datetime.utcfromtimestamp(r.get("timestamp_created", 0)).year == year
        ]

    return all_reviews[:count]


def run(year: int = None, output_path: str = None) -> list:
    sia     = SentimentIntensityAnalyzer()
    results = []

    year_label = f" [{year}]" if year else ""
    print(f"\n[steam]{year_label} Scraping Steam reviews...")

    top_games = get_genre_top_games(STEAM_GENRE_TAG)
    all_ids   = list(top_games.keys())[:10] + STEAM_APP_IDS
    all_ids   = list(dict.fromkeys(all_ids))

    for app_id in tqdm(all_ids, desc=f"Steam{year_label}"):
        details = get_app_details(app_id)
        reviews = get_reviews(app_id, STEAM_REVIEWS_PER_APP, year=year)

        scored_reviews = []
        for r in reviews:
            text = r.get("review", "")[:800]
            if len(text) < 10:
                continue
            sentiment = sia.polarity_scores(text)
            scored_reviews.append({
                "text":           text,
                "voted_up":       r.get("voted_up", False),
                "votes_helpful":  r.get("votes_helpful", 0),
                "timestamp":      r.get("timestamp_created", 0),
                "sentiment":      sentiment,
                "playtime_hours": round(r.get("author", {}).get("playtime_forever", 0) / 60, 1),
            })

        results.append({
            "source":          "steam",
            "app_id":          app_id,
            "name":            details.get("name", top_games.get(app_id, {}).get("name", app_id)),
            "developer":       details.get("developer", ""),
            "owners":          details.get("owners", ""),
            "positive":        details.get("positive", 0),
            "negative":        details.get("negative", 0),
            "average_playtime":details.get("average_forever", 0),
            "price":           details.get("price", 0),
            "tags":            list(details.get("tags", {}).keys())[:15],
            "reviews":         scored_reviews,
        })
        time.sleep(1.5)

    print(f"  [steam] Collected {sum(len(r['reviews']) for r in results)} reviews")

    out_dir = get_year_dir(year) if year else DATA_DIR
    os.makedirs(out_dir, exist_ok=True)
    path = output_path or os.path.join(out_dir, "steam_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  → Saved to {path}")

    return results


if __name__ == "__main__":
    run()
