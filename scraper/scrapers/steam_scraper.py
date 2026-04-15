"""
steam_scraper.py
Scrapes Steam game data via:
  - SteamSpy API (free, no auth, game stats + tags)
  - Steam Store Reviews API (free, no auth)
No API key required for either.
"""
import json, time, os, requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from tqdm import tqdm
from config import STEAM_GENRE_TAG, STEAM_APP_IDS, STEAM_REVIEWS_PER_APP, DATA_DIR

STEAMSPY_BASE  = "https://steamspy.com/api.php"
STEAM_REVIEW_BASE = "https://store.steampowered.com/appreviews"


def get_genre_top_games(tag: str = "Fighting", n: int = 20) -> dict:
    """Get top games for a genre tag from SteamSpy."""
    print(f"  [steam] Fetching top '{tag}' games from SteamSpy...")
    resp = requests.get(STEAMSPY_BASE, params={"request": "tag", "tag": tag}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    # SteamSpy returns a dict of appid -> game info
    top = dict(list(data.items())[:n])
    return top


def get_app_details(app_id: str) -> dict:
    """Get detailed stats for one app from SteamSpy."""
    try:
        resp = requests.get(STEAMSPY_BASE, params={"request": "appdetails", "appid": app_id}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [steam] SteamSpy detail error for {app_id}: {e}")
        return {}


def get_reviews(app_id: str, count: int = 100) -> list:
    """Pull recent English reviews for a Steam app. No auth needed."""
    url = f"{STEAM_REVIEW_BASE}/{app_id}"
    params = {
        "json":         1,
        "num_per_page": min(count, 100),
        "filter":       "recent",
        "language":     "english",
        "review_type":  "all",
        "purchase_type":"all",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("reviews", [])
    except Exception as e:
        print(f"  [steam] Review fetch error for {app_id}: {e}")
        return []


def run(output_path: str = None) -> list:
    """Main entry point. Returns list of scraped records and saves to JSON."""
    sia = SentimentIntensityAnalyzer()
    results = []

    # 1. Genre top games
    top_games = get_genre_top_games(STEAM_GENRE_TAG)
    print(f"  [steam] Found {len(top_games)} top games in genre '{STEAM_GENRE_TAG}'")

    # Combine genre top games + specific app IDs
    all_ids = list(top_games.keys())[:10] + STEAM_APP_IDS
    all_ids = list(dict.fromkeys(all_ids))  # deduplicate

    for app_id in tqdm(all_ids, desc="Steam apps"):
        details = get_app_details(app_id)
        reviews = get_reviews(app_id, STEAM_REVIEWS_PER_APP)

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
            "average_playtime": details.get("average_forever", 0),
            "price":           details.get("price", 0),
            "tags":            list(details.get("tags", {}).keys())[:15],
            "reviews":         scored_reviews,
        })

        time.sleep(1.5)  # SteamSpy rate limit: be polite

    print(f"  [steam] Collected {sum(len(r['reviews']) for r in results)} reviews across {len(results)} apps")

    os.makedirs(DATA_DIR, exist_ok=True)
    path = output_path or os.path.join(DATA_DIR, "steam_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  → Saved to {path}")

    return results


if __name__ == "__main__":
    run()
