"""
RAWG scraper — the RAWG video-game database (ratings, genres, popularity).
Needs a FREE key: rawg.io/apidocs → sign up → copy key into .env as RAWG_API_KEY.
Skips cleanly without one. Year-filterable (real release dates).
"""
import requests

from config import RAWG_API_KEY, RAWG_PAGE_SIZE, get_year_dir
from scrapers import score, save

API = "https://api.rawg.io/api/games"


def run(year: int | None = None, log=print) -> list:
    if not RAWG_API_KEY:
        log("  [rawg] skipped — set RAWG_API_KEY in .env (free: rawg.io/apidocs)")
        return save([], get_year_dir(year), "rawg", log)
    y = year or 2026
    log(f"[rawg] top games by popularity for {y}")
    params = {"key": RAWG_API_KEY, "dates": f"{y}-01-01,{y}-12-31",
              "ordering": "-added", "page_size": RAWG_PAGE_SIZE}
    try:
        results = requests.get(API, params=params, timeout=20).json().get("results", [])
    except Exception as e:
        log(f"  [rawg] error: {e}")
        return save([], get_year_dir(year), "rawg", log)

    records = []
    for g in results:
        name = g.get("name", "")
        genres = [gg.get("name") for gg in g.get("genres", [])][:5]
        rating = g.get("rating", 0)
        added = g.get("added", 0)
        text = (f"'{name}' ({g.get('released', '?')}) — rating {rating}/5 "
                f"from {g.get('ratings_count', 0)} users; {added} users tracked it; "
                f"genres: {', '.join(genres) or 'n/a'}.")
        records.append({
            "source": "rawg", "name": name, "title": f"{name} — RAWG {y}",
            "text": text, "rating": rating, "added": added, "genres": genres,
            "released": g.get("released"), "sentiment": score(text),
        })
    log(f"  [rawg] {len(records)} games")
    return save(records, get_year_dir(year), "rawg", log)


if __name__ == "__main__":
    run()
