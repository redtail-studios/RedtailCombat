"""
App Store charts scraper — per-genre top-free/top-grossing charts via the
legacy iTunes RSS endpoint. No key.

This is the "orphaned" platform: APPCHARTS_COUNTRY/APPCHARTS_LIMIT sat in
config.py with no scraper reading them until now. Apple's newer
rss.marketingtools.apple.com generator dropped genre-level filtering (only
whole-store top charts), but the older itunes.apple.com RSS generator still
accepts a genre id and returns real, correctly-bucketed results — verified
live against genre=7012 (Puzzle) returning Royal Match / Candy Crush Saga,
and genre=7014 (Role Playing) returning Pokémon GO / Dragon Ball Legends.
"""
import time

import requests

from config import GENRES, ACTIVE_GENRES, APPCHARTS_COUNTRY, APPCHARTS_LIMIT, get_year_dir
from scrapers import score, save

RSS = ("https://itunes.apple.com/{country}/rss/{chart}/limit={limit}/genre={genre}/json")
CHARTS = [("topfreeapplications", "top free"), ("topgrossingapplications", "top grossing")]


def _fetch(chart: str, genre_id: str, log) -> list:
    url = RSS.format(country=APPCHARTS_COUNTRY, chart=chart, limit=APPCHARTS_LIMIT, genre=genre_id)
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return r.json().get("feed", {}).get("entry", [])
    except Exception as e:
        log(f"  [appcharts] {chart} genre={genre_id} error: {e}")
        return []


def run(year: int | None = None, log=print) -> list:
    genres_with_charts = [g for g in ACTIVE_GENRES if GENRES[g].get("apple_chart_genre")]
    log(f"[appcharts] scraping {len(CHARTS)} charts x {len(genres_with_charts)} genres "
        f"(country={APPCHARTS_COUNTRY}, tagged {year})")
    records = []
    for g in genres_with_charts:
        genre_id = GENRES[g]["apple_chart_genre"]
        for chart, label in CHARTS:
            entries = _fetch(chart, genre_id, log)
            for rank, e in enumerate(entries, 1):
                name = e.get("im:name", {}).get("label", "")
                if not name:
                    continue
                app_id = e.get("id", {}).get("attributes", {}).get("im:id", "")
                summary = (e.get("summary", {}).get("label") or "").strip()[:300]
                text = (f"#{rank} App Store {label} ({GENRES[g]['label']}): '{name}'. "
                        f"{summary}")
                records.append({
                    "source": "appcharts", "genre": g, "chart": label, "rank": rank,
                    "app_id": app_id, "name": name,
                    "title": f"#{rank} {label} ({GENRES[g]['label']}): {name}",
                    "text": text, "sentiment": score(text),
                })
            log(f"  [appcharts] genre={g} {label}: {len(entries)} apps")
            time.sleep(0.3)
    return save(records, get_year_dir(year), "appcharts", log)


if __name__ == "__main__":
    run()
