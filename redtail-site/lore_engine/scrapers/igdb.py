"""
IGDB scraper — pre-release hype/buzz signal (Twitch-owned game database).
Reuses TWITCH_CLIENT_ID/SECRET already set for twitch.py (dev.twitch.tv) —
no separate key needed. Skips cleanly without them. Not year-filtered: this
tracks what's hyped *right now*, since upcoming titles often have a future
or null release date (a hard year window would exclude exactly the games
this scraper exists to surface) — same "live snapshot, tagged to the run
year" approach as twitch.py/steamtrending.py.
"""
import time

import requests

from config import GENRES, ACTIVE_GENRES, TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET, IGDB_TOP_N, get_year_dir
from scrapers import score, save

GAMES = "https://api.igdb.com/v4/games"


def _token() -> str | None:
    try:
        r = requests.post("https://id.twitch.tv/oauth2/token", timeout=15, params={
            "client_id": TWITCH_CLIENT_ID, "client_secret": TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials"})
        r.raise_for_status()
        return r.json().get("access_token")
    except Exception:
        return None


def _top_hyped(igdb_genre_id: int, headers: dict, log) -> list:
    # "follows" was checked live and returns null/omitted even for hugely
    # popular titles (Cyberpunk 2077 included) — deprecated on IGDB's side,
    # so it's deliberately left out; hypes/rating/rating_count are the live
    # buzz signal that actually returns data.
    query = (f"fields name,genres.name,first_release_date,rating,rating_count,"
             f"hypes,involved_companies.company.name; "
             f"where genres = ({igdb_genre_id}); sort hypes desc; limit {IGDB_TOP_N};")
    try:
        r = requests.post(GAMES, headers=headers, data=query, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log(f"  [igdb] error (genre_id={igdb_genre_id}): {e}")
        return []


def run(year: int | None = None, log=print) -> list:
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        log("  [igdb] skipped — set TWITCH_CLIENT_ID/SECRET in .env (free: dev.twitch.tv)")
        return save([], get_year_dir(year), "igdb", log)
    token = _token()
    if not token:
        log("  [igdb] auth failed — check TWITCH_CLIENT_ID/SECRET")
        return save([], get_year_dir(year), "igdb", log)
    headers = {"Client-ID": TWITCH_CLIENT_ID, "Authorization": f"Bearer {token}"}

    records = []
    for g in ACTIVE_GENRES:
        igdb_genre_id = GENRES[g].get("igdb_genre")
        if igdb_genre_id is None:
            continue  # no IGDB genre analog for this genre (e.g. idle, hybrid_casual)
        log(f"[igdb] top {IGDB_TOP_N} hyped games for genre={g} (igdb_genre={igdb_genre_id}, tagged {year})")
        games = _top_hyped(igdb_genre_id, headers, log)
        for game in games:
            name = game.get("name", "")
            hypes = game.get("hypes", 0)
            rating = round(game.get("rating", 0), 1)
            rating_count = game.get("rating_count", 0)
            companies = [c.get("company", {}).get("name") for c in game.get("involved_companies", [])]
            companies = [c for c in companies if c]
            text = (f"'{name}' has {hypes} hypes on IGDB ahead of release "
                    f"(rating {rating}/100 from {rating_count} users).")
            records.append({
                "source": "igdb", "name": name, "genre": g,
                "title": f"{name} — IGDB pre-release hype",
                "text": text, "hypes": hypes, "rating": rating,
                "rating_count": rating_count,
                "first_release_date": game.get("first_release_date"),
                "companies": companies, "sentiment": score(text),
            })
        log(f"  [igdb] genre={g}: {len(games)} games")
        time.sleep(0.3)
    return save(records, get_year_dir(year), "igdb", log)


if __name__ == "__main__":
    run()
