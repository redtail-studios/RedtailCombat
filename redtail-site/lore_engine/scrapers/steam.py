"""Steam scraper — SteamSpy genre list + Steam reviews API. No key needed."""
import time
from datetime import datetime, timezone

import requests

from config import GENRES, ACTIVE_GENRES, STEAM_REVIEWS_PER_APP, get_year_dir
from scrapers import score, save

STEAMSPY = "https://steamspy.com/api.php"
REVIEWS  = "https://store.steampowered.com/appreviews"
TIME_BUDGET_SECONDS = 720  # stop starting new apps past this; the worker Lambda's hard
                            # timeout is 900s and a killed invocation returns nothing and
                            # never gets deleted off SQS, so leaving no margin here is what
                            # caused reddit.py to retry forever once (see SCRAPING_ARCHITECTURE.md
                            # §5) — same risk here now that discovery can return far more apps.


def _top_games(tag: str, n: int | None = None) -> dict:
    """SteamSpy's tag-browse endpoint already returns its FULL result in one
    response (confirmed live) — `n`, when given, is a pure in-memory slice
    applied after that complete data is already downloaded, not a smaller
    request. Defaulting to no slice costs zero extra network traffic and
    avoids silently excluding a real match that just doesn't rank in the
    top N by whatever order SteamSpy happens to return (popularity) —
    important once results feed an intersection, where narrowing is
    supposed to happen via the intersection itself, not pre-truncation."""
    try:
        r = requests.get(STEAMSPY, params={"request": "tag", "tag": tag}, timeout=15)
        r.raise_for_status()
        items = list(r.json().items())
        return dict(items[:n] if n else items)
    except Exception:
        return {}


def _niche_discovery(combos: list) -> dict:
    """app_id -> sorted list of which combo's tags matched. Each combo is a
    list of tags that must ALL match (set intersection); an app can satisfy
    more than one combo. Intersects over each tag's FULL result (see
    _top_games) — narrowing happens via the intersection, never via
    pre-truncating an individual tag's list first. A courtesy sleep between
    SteamSpy calls — this is only ever called from the weekly cron, never
    from a live request."""
    matched = {}
    for combo in combos:
        app_sets = []
        for tag in combo:
            app_sets.append(set(_top_games(tag)))
            time.sleep(0.3)
        if not app_sets:
            continue
        hits = set.intersection(*app_sets)
        for app_id in hits:
            matched.setdefault(app_id, set()).update(combo)
    return {app_id: sorted(tags) for app_id, tags in matched.items()}


def _details(app_id: str) -> dict:
    try:
        r = requests.get(STEAMSPY, params={"request": "appdetails", "appid": app_id}, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def _reviews(app_id: str, count: int, year: int | None, since=None) -> list:
    cursor, out, pages = "*", [], 0
    want = count * 3 if year else count
    since_ts = since.timestamp() if since else None
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
            oldest = min(rv.get("timestamp_created", 9e9) for rv in batch)
            if year and datetime.fromtimestamp(oldest, timezone.utc).year < year:
                break
            # "filter": "recent" means each page is strictly older than the
            # last, so once a whole page predates `since` there's nothing
            # newer left to find on later pages either.
            if since_ts is not None and oldest <= since_ts:
                break
            time.sleep(0.4)
        except Exception:
            break
    if year:
        out = [rv for rv in out
               if datetime.fromtimestamp(rv.get("timestamp_created", 0), timezone.utc).year == year]
    if since_ts is not None:
        out = [rv for rv in out if rv.get("timestamp_created", 0) > since_ts]
    return out[:count]


def discover_apps() -> tuple:
    """(app_genre, matched_tags) — app_genre maps app_id -> first genre that
    claimed it; matched_tags maps app_id -> which specific niche tags
    matched (empty for apps found via the plain single steam_tag or a
    static steam_app_ids entry). Shared by this scraper and
    steamplayertrend.py, so the latter automatically gets any future
    discovery upgrade made here.

    A genre with steam_tag_combos configured uses ONLY those (unioned
    across combos) instead of the single broad steam_tag — see fighting's
    config comment for why: a single broad tag included an unrelated game
    (Guacamelee) that a verified niche-tag intersection correctly excludes.
    Combining the combos with the old broad tag would just let it back in."""
    app_genre, matched_tags = {}, {}
    for g in ACTIVE_GENRES:
        cfg = GENRES[g]
        combos = cfg.get("steam_tag_combos")
        if combos:
            niche = _niche_discovery(combos)
            ids = list(niche) + cfg["steam_app_ids"]
            for app_id in dict.fromkeys(ids):
                app_genre.setdefault(app_id, g)
                if app_id in niche:
                    matched_tags.setdefault(app_id, niche[app_id])
        elif cfg["steam_tag"]:
            # Not every genre has a meaningful Steam/PC analog (e.g. gacha,
            # hybrid-casual are mobile-only monetization models) — those set
            # steam_tag=None and are skipped here, same as
            # twitch.py/youtube.py skip cleanly without a key.
            ids = list(_top_games(cfg["steam_tag"])) + cfg["steam_app_ids"]
            for app_id in dict.fromkeys(ids):
                app_genre.setdefault(app_id, g)
    return app_genre, matched_tags


def run(year: int | None = None, log=print, since=None) -> list:
    app_genre, matched_tags = discover_apps()
    log(f"[steam] scraping {len(app_genre)} apps across genres={ACTIVE_GENRES} "
        f"(year={year}, since={since})")

    # Removing _top_games'/_niche_discovery's old pre-truncation (see their
    # docstrings) means a genuinely accurate intersection can legitimately
    # discover hundreds more real apps than before (verified live: the
    # fighting genre alone went from 53 to 692) — a real correctness win,
    # but each one still costs a real per-app review-fetch below. Apps that
    # matched more niche tags are a stronger, free-to-compute fit signal, so
    # they're processed first; if the time budget below ever cuts a run
    # short, it's the long tail of weaker/unmatched candidates that's
    # dropped, not the apps most likely to matter.
    ordered = sorted(app_genre.items(), key=lambda kv: -len(matched_tags.get(kv[0], [])))
    start = time.monotonic()
    records = []
    for app_id, genre in ordered:
        if time.monotonic() - start > TIME_BUDGET_SECONDS:
            log(f"  [steam] time budget ({TIME_BUDGET_SECONDS}s) reached — "
                f"returning {len(records)} records collected so far instead of "
                f"risking the Lambda timeout")
            break
        d = _details(app_id)
        revs = []
        for rv in _reviews(app_id, STEAM_REVIEWS_PER_APP, year, since=since):
            text = (rv.get("review") or "")[:800]
            if len(text) < 10:
                continue
            revs.append({"id": rv.get("recommendationid"), "text": text,
                         "voted_up": rv.get("voted_up", False),
                         "timestamp": rv.get("timestamp_created", 0),
                         "sentiment": score(text)})
        records.append({"source": "steam", "app_id": app_id, "genre": genre,
                        "name": d.get("name", app_id),
                        "developer": d.get("developer", ""),
                        "owners": d.get("owners", ""),
                        "ccu": d.get("ccu", 0),
                        "tags": list(d.get("tags", {}).keys())[:12],
                        "matchedNicheTags": matched_tags.get(app_id, []),
                        "positive": d.get("positive", 0), "negative": d.get("negative", 0),
                        "avg_playtime_forever": d.get("average_forever", 0),
                        "avg_playtime_2weeks": d.get("average_2weeks", 0),
                        "median_playtime_forever": d.get("median_forever", 0),
                        "median_playtime_2weeks": d.get("median_2weeks", 0),
                        "reviews": revs})
        time.sleep(1.0)
    return save(records, get_year_dir(year), "steam", log)


if __name__ == "__main__":
    run()
