"""Steam scraper — SteamSpy genre list + Steam reviews API. No key needed."""
import time
from datetime import datetime, timezone

import requests

from config import STEAM_GENRE_TAG, STEAM_APP_IDS, STEAM_REVIEWS_PER_APP, get_year_dir
from scrapers import score, save

STEAMSPY = "https://steamspy.com/api.php"
REVIEWS  = "https://store.steampowered.com/appreviews"


def _top_games(tag: str, n: int = 10) -> dict:
    try:
        r = requests.get(STEAMSPY, params={"request": "tag", "tag": tag}, timeout=15)
        r.raise_for_status()
        return dict(list(r.json().items())[:n])
    except Exception:
        return {}


def _details(app_id: str) -> dict:
    try:
        r = requests.get(STEAMSPY, params={"request": "appdetails", "appid": app_id}, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def _reviews(app_id: str, count: int, year: int | None) -> list:
    cursor, out, pages = "*", [], 0
    want = count * 3 if year else count
    while pages < 10 and len(out) < want:
        try:
            r = requests.get(f"{REVIEWS}/{app_id}", timeout=15, params={
                "json": 1, "num_per_page": 100, "filter": "recent",
                "language": "english", "review_type": "all",
                "purchase_type": "all", "cursor": cursor})
            r.raise_for_status()
            data = r.json()
            batch = data.get("reviews", [])
            if not batch:
                break
            out.extend(batch)
            cursor = data.get("cursor", "")
            pages += 1
            if not cursor:
                break
            if year:
                oldest = min(rv.get("timestamp_created", 9e9) for rv in batch)
                if datetime.fromtimestamp(oldest, timezone.utc).year < year:
                    break
            time.sleep(0.4)
        except Exception:
            break
    if year:
        out = [rv for rv in out
               if datetime.fromtimestamp(rv.get("timestamp_created", 0), timezone.utc).year == year]
    return out[:count]


def run(year: int | None = None, log=print) -> list:
    log(f"[steam] scraping (year={year})")
    ids = list(_top_games(STEAM_GENRE_TAG)) + STEAM_APP_IDS
    ids = list(dict.fromkeys(ids))
    records = []
    for app_id in ids:
        d = _details(app_id)
        revs = []
        for rv in _reviews(app_id, STEAM_REVIEWS_PER_APP, year):
            text = (rv.get("review") or "")[:800]
            if len(text) < 10:
                continue
            revs.append({"text": text, "voted_up": rv.get("voted_up", False),
                         "timestamp": rv.get("timestamp_created", 0),
                         "sentiment": score(text)})
        records.append({"source": "steam", "app_id": app_id,
                        "name": d.get("name", app_id),
                        "developer": d.get("developer", ""),
                        "owners": d.get("owners", ""),
                        "tags": list(d.get("tags", {}).keys())[:12],
                        "reviews": revs})
        time.sleep(1.0)
    return save(records, get_year_dir(year), "steam", log)


if __name__ == "__main__":
    run()
