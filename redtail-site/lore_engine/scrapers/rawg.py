"""
RAWG scraper — the RAWG video-game database (ratings, genres, popularity).
Needs a FREE key: rawg.io/apidocs → sign up → copy key into .env as RAWG_API_KEY.
Skips cleanly without one. Year-filterable (real release dates).
"""
import requests

from config import GENRES, ACTIVE_GENRES, RAWG_API_KEY, RAWG_PAGE_SIZE, get_year_dir
from scrapers import score, save

API = "https://api.rawg.io/api/games"


def _fetch(genre_slug: str | None, y: int, log) -> list:
    params = {"key": RAWG_API_KEY, "dates": f"{y}-01-01,{y}-12-31",
              "ordering": "-added", "page_size": RAWG_PAGE_SIZE}
    if genre_slug:
        params["genres"] = genre_slug
    try:
        return requests.get(API, params=params, timeout=20).json().get("results", [])
    except Exception as e:
        log(f"  [rawg] error (genre={genre_slug}): {e}")
        return []


def run(year: int | None = None, log=print) -> list:
    if not RAWG_API_KEY:
        log("  [rawg] skipped — set RAWG_API_KEY in .env (free: rawg.io/apidocs)")
        return save([], get_year_dir(year), "rawg", log)
    y = year or 2026

    # game id -> first genre (RAWG slug) that claimed it, so a game matching
    # two active genres' slugs (e.g. "casual" shared by idle + hybrid_casual)
    # is only fetched/recorded once.
    seen, ordered = {}, []
    for g in ACTIVE_GENRES:
        slug = GENRES[g]["rawg_genre"]
        log(f"[rawg] top games by popularity for {y}, genre={g} (slug={slug})")
        for game in _fetch(slug, y, log):
            gid = game.get("id")
            if gid is None or gid in seen:
                continue
            seen[gid] = g
            ordered.append(game)

    records = []
    for game in ordered:
        name = game.get("name", "")
        genres = [gg.get("name") for gg in game.get("genres", [])][:5]
        rating = game.get("rating", 0)
        added = game.get("added", 0)
        text = (f"'{name}' ({game.get('released', '?')}) — rating {rating}/5 "
                f"from {game.get('ratings_count', 0)} users; {added} users tracked it; "
                f"genres: {', '.join(genres) or 'n/a'}.")
        records.append({
            "source": "rawg", "name": name, "genre": seen[game.get("id")],
            "title": f"{name} — RAWG {y}",
            "text": text, "rating": rating, "added": added, "rawg_genres": genres,
            "released": game.get("released"), "sentiment": score(text),
        })
    log(f"  [rawg] {len(records)} games")
    return save(records, get_year_dir(year), "rawg", log)


if __name__ == "__main__":
    run()
