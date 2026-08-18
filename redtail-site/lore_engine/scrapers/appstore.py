"""App Store scraper — iTunes RSS customer-reviews JSON. No key, no extra deps."""
import time

import requests

from config import GENRES, ACTIVE_GENRES, APP_STORE_REVIEWS, get_year_dir
from scrapers import score, save

RSS = ("https://itunes.apple.com/us/rss/customerreviews/page={page}/id={app_id}/"
       "sortby=mostrecent/json")


def _reviews(app_id: str, want: int) -> list:
    out, page = [], 1
    while len(out) < want and page <= 10:
        try:
            r = requests.get(RSS.format(page=page, app_id=app_id), timeout=15,
                             headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            entries = r.json().get("feed", {}).get("entry", [])
        except Exception:
            break
        # The first entry on page 1 is app metadata, not a review.
        if entries and "im:rating" not in entries[0]:
            entries = entries[1:]
        if not entries:
            break
        for e in entries:
            text = (e.get("content", {}).get("label") or "").strip()[:600]
            if len(text) < 10:
                continue
            out.append({
                # iTunes RSS carries no review date, so there's no "since" fetch
                # optimization possible here (see run()) — but the feed entry's
                # own id still lets accumulation dedupe instead of piling up
                # literal repeats every time the same "most recent" page is refetched.
                "id": e.get("id", {}).get("label", ""),
                "text": text,
                "title": e.get("title", {}).get("label", ""),
                "rating": int(e.get("im:rating", {}).get("label", 0) or 0),
                "sentiment": score(text),
            })
        page += 1
        time.sleep(0.5)
    return out[:want]


def run(year: int | None = None, log=print, since=None) -> list:
    apps = [(ap, g) for g in ACTIVE_GENRES for ap in GENRES[g]["app_store_apps"]]
    log(f"[appstore] scraping {len(apps)} apps across genres={ACTIVE_GENRES} (year={year})")
    # iTunes RSS carries no review date, so year filtering — and the `since`
    # cursor other incremental platforms use to shrink their fetch — isn't
    # possible here; reviews are always 'most recent'. `since` is accepted
    # for interface consistency with worker.py but otherwise unused: the id
    # captured above is what makes accumulation safe, not a smaller fetch.
    records = []
    for ap, genre in apps:
        revs = _reviews(ap["app_id"], APP_STORE_REVIEWS)
        records.append({"source": "appstore", "app_id": ap["app_id"], "genre": genre,
                        "name": ap["name"], "reviews": revs})
        time.sleep(0.5)
    return save(records, get_year_dir(year), "appstore", log)


if __name__ == "__main__":
    run()
