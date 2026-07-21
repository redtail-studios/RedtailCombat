"""Google Play scraper — google-play-scraper library. No key needed."""
import time
from datetime import datetime

from config import GENRES, ACTIVE_GENRES, GOOGLE_PLAY_N_APPS, GOOGLE_PLAY_REVIEWS, get_year_dir
from scrapers import score, save


def _scrape_query(query: str, genre_tag: str, year, log) -> list:
    from google_play_scraper import search, app, reviews, Sort
    try:
        hits = search(query, n_hits=GOOGLE_PLAY_N_APPS, lang="en", country="us")
    except Exception as e:
        log(f"  [googleplay] search '{query}' failed: {e}")
        return []

    fetch = GOOGLE_PLAY_REVIEWS * (4 if year else 1)
    records = []
    for h in hits:
        app_id = h.get("appId")
        if not app_id:
            continue
        try:
            d = app(app_id, lang="en", country="us")
        except Exception:
            d = h
        try:
            revs_raw, _ = reviews(app_id, lang="en", country="us",
                                  sort=Sort.NEWEST, count=fetch)
        except Exception:
            revs_raw = []
        revs = []
        for r in revs_raw:
            if year:
                at = r.get("at")
                ry = at.year if isinstance(at, datetime) else None
                if ry is None:
                    continue
                if ry < year:
                    break
                if ry != year:
                    continue
            text = (r.get("content") or "").strip()[:600]
            if len(text) < 10:
                continue
            revs.append({"text": text, "score": r.get("score", 0),
                         "date": str(r.get("at", "")), "sentiment": score(text)})
            if len(revs) >= GOOGLE_PLAY_REVIEWS:
                break
        records.append({"source": "googleplay", "app_id": app_id, "genre": genre_tag,
                        "name": d.get("title", app_id),
                        "developer": d.get("developer", ""),
                        "installs": d.get("installs", ""),
                        "play_store_genre": d.get("genre", ""),
                        "reviews": revs})
        time.sleep(1.5)
    return records


def run(year: int | None = None, log=print) -> list:
    log(f"[googleplay] searching {len(ACTIVE_GENRES)} genre queries (year={year})")
    records = []
    for g in ACTIVE_GENRES:
        query = GENRES[g]["google_play_query"]
        log(f"  [googleplay] genre={g} query='{query}'")
        records.extend(_scrape_query(query, g, year, log))
    return save(records, get_year_dir(year), "googleplay", log)


if __name__ == "__main__":
    run()
