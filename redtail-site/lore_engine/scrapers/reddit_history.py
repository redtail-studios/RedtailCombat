"""
Reddit scraper for PAST years — Arctic Shift archive API. No key needed.

reddit.py can only see what's hot right now (its RSS feeds have no date
range), so asking it for an old year returns nothing. Arctic Shift is a
community-run archive of Reddit that can query a subreddit by date range:
    https://arctic-shift.photon-reddit.com/api/posts/search
reddit.run() hands any year before the current one to this module.

Splitting: a full year is ~25 subreddits x ~40s, far past one Lambda's time
budget, so the worker runs it as a chain of parts of GROUP_SIZE subreddits each
(worker.py enqueues part N+1 when part N finishes and merges results by url).
run(part=N) does only group N; num_parts() says how many there are.

How it samples: for each subreddit, one request per month (oldest 100 posts
that month, so a busy sub's month is a sample, not complete), then keeps the
REDDIT_POST_LIMIT highest-scoring posts for the year — same cap as the live
scraper. That's ~12 requests per subreddit; subs are walked niche-first and
the loop stops at TIME_BUDGET_SECONDS, so the broad subs are what get cut if
time runs out.

Known limits, found by testing on 2026-10-14:
  - Coverage has holes. r/FightingGames has nothing archived for 2021-2024
    (2019-2020 and 2025 are fine). A sub with no posts in any month is logged
    as "no archive coverage" so a gap doesn't look like a quiet year.
  - Heavy queries sometimes fail with HTTP 422 "Timeout. Maybe slow down a
    bit" — transient, so we retry with backoff.
  - Volunteer-run service: be polite (delay between requests, honour
    X-RateLimit-Reset on 429). For bulk volume use the monthly dumps instead.
  - The text is user content under Reddit's terms; check licensing before
    showing archived posts verbatim to customers.
"""
import time
from datetime import datetime, timezone

import requests

from config import (SUBREDDITS_COMMON, SUBREDDITS_BROAD, REDDIT_KEYWORDS_COMMON,
                    GENRES, ACTIVE_GENRES, REDDIT_POST_LIMIT, get_year_dir)
from scrapers import score, save

API = "https://arctic-shift.photon-reddit.com/api/posts/search"
UA = "redtail-lore/1.0 (market research scraper)"
# The API rejects unknown fields with HTTP 400 (e.g. "permalink" is not valid), so keep
# this list to fields confirmed against the live API.
FIELDS = "id,created_utc,subreddit,title,selftext,score,num_comments,author"
GROUP_SIZE = 5  # subreddits per part: ~200s typical, well inside TIME_BUDGET_SECONDS
PAGE_LIMIT = 100  # API max for a plain integer limit
REQUEST_DELAY = 1.0
MAX_RATE_LIMIT_WAIT = 65
TIME_BUDGET_SECONDS = 720  # worker Lambda's hard timeout is 900s — same margin as reddit.py
_REMOVED = {"[removed]", "[deleted]"}


class BudgetExceeded(RuntimeError):
    """A part ran out of time before finishing its subreddits. Raised (rather
    than returning a short list) so the job shows as an error and retries
    instead of looking complete."""


def _all_subs() -> tuple:
    """(ordered subreddit list, {sub: genre}) — niche subs first, broad last."""
    niche_genre = {sub: "general" for sub in SUBREDDITS_COMMON}
    for g in ACTIVE_GENRES:
        for sub in GENRES[g]["subreddits"]:
            niche_genre[sub] = g
    return list(niche_genre) + list(SUBREDDITS_BROAD), niche_genre


def num_parts() -> int:
    subs, _ = _all_subs()
    return -(-len(subs) // GROUP_SIZE)  # ceil


def _month_windows(year: int) -> list:
    """[(after, before)] as ISO dates, one per month of `year`."""
    out = []
    for m in range(1, 13):
        end = (year + 1, 1) if m == 12 else (year, m + 1)
        out.append((f"{year}-{m:02d}-01", f"{end[0]}-{end[1]:02d}-01"))
    return out


def _fetch(params: dict, log, tries: int = 5):
    """Return the API's post list, or None if every try failed."""
    for i in range(tries):
        try:
            r = requests.get(API, params=params, headers={"User-Agent": UA}, timeout=60)
        except Exception as e:
            log(f"    [arctic] request error: {e}")
            time.sleep(4 * (i + 1))
            continue
        if r.status_code == 200:
            return r.json().get("data") or []
        if r.status_code == 429:
            try:
                wait = min(float(r.headers.get("x-ratelimit-reset", 5 * (i + 1))) + 1,
                           MAX_RATE_LIMIT_WAIT)
            except ValueError:
                wait = 5 * (i + 1)
            log(f"    [arctic] rate-limited, waiting {wait:.0f}s")
            time.sleep(wait)
            continue
        if r.status_code in (400, 403, 404):
            log(f"    [arctic] HTTP {r.status_code}: {r.text[:120]} — not retrying")
            return None
        # 422 "Timeout. Maybe slow down a bit" and 5xx are transient.
        log(f"    [arctic] HTTP {r.status_code}, retrying")
        time.sleep(5 * (i + 1))
    return None


def _sub_posts(sub: str, year: int, log) -> tuple:
    """(posts for the year, failed_windows, empty_windows) for one subreddit."""
    posts, failed, empty = [], 0, 0
    for after, before in _month_windows(year):
        data = _fetch({"subreddit": sub, "after": after, "before": before,
                       "sort": "asc", "limit": PAGE_LIMIT, "fields": FIELDS}, log)
        time.sleep(REQUEST_DELAY)
        if data is None:
            failed += 1
        elif not data:
            empty += 1
        else:
            posts.extend(data)
    return posts, failed, empty


def run(year: int | None = None, log=print, part: int | None = None) -> list:
    """part=None: every subreddit in one go, stopping quietly at the time
    budget (direct/manual use). part=N: only group N, and raise BudgetExceeded
    if time runs out before it's done."""
    if year is None:
        raise ValueError("reddit_history needs a specific past year")

    all_subs, niche_genre = _all_subs()
    genre_kws = {g: [k.lower() for k in GENRES[g]["reddit_keywords"]] for g in ACTIVE_GENRES}
    common_kws = [k.lower() for k in REDDIT_KEYWORDS_COMMON]

    if part is not None:
        all_subs = all_subs[part * GROUP_SIZE:(part + 1) * GROUP_SIZE]
    log(f"[reddit] {year}: querying Arctic Shift archive for {len(all_subs)} subreddits"
        + (f" (part {part + 1}/{num_parts()})" if part is not None else ""))
    records, no_coverage = [], []
    start = time.monotonic()

    for sub in all_subs:
        if time.monotonic() - start > TIME_BUDGET_SECONDS:
            if part is not None:
                raise BudgetExceeded(f"part {part} of {year} ran out of time at r/{sub}")
            log(f"  [reddit] time budget ({TIME_BUDGET_SECONDS}s) reached — "
                f"returning {len(records)} records collected so far")
            break
        posts, failed, empty = _sub_posts(sub, year, log)
        if not posts:
            if failed == 0:
                no_coverage.append(sub)
                log(f"  [reddit] r/{sub}: no archive coverage for {year}")
            else:
                log(f"  [reddit] r/{sub}: all {failed} failed windows — no data")
            continue

        broad = sub in SUBREDDITS_BROAD
        candidates, seen = [], set()
        for p in posts:
            if p["id"] in seen or (p.get("selftext") or "").strip() in _REMOVED:
                continue
            seen.add(p["id"])
            text = (p.get("selftext") or "")
            text_low = f"{p.get('title', '')} {text}".lower()
            if broad:
                genre = next((g for g, kws in genre_kws.items()
                              if any(k in text_low for k in kws)), None)
                if genre is None and any(k in text_low for k in common_kws):
                    genre = "general"
                if genre is None:
                    continue
            else:
                genre = niche_genre[sub]
            candidates.append((p, genre))

        candidates.sort(key=lambda pg: pg[0].get("score") or 0, reverse=True)
        for p, genre in candidates[:REDDIT_POST_LIMIT]:
            text = (p.get("selftext") or "")[:600]
            records.append({
                "source": "reddit", "subreddit": sub, "genre": genre,
                "title": p.get("title", ""), "text": text,
                "author": p.get("author", ""),
                "url": f"https://www.reddit.com/comments/{p['id']}/",
                "sentiment": score(f"{p.get('title', '')} {text}"),
                "comments": [],
                "score": p.get("score") or 0,
                "created": datetime.fromtimestamp(p["created_utc"], timezone.utc).date().isoformat(),
            })
        log(f"  [reddit] r/{sub}: {len(posts)} sampled, kept {min(len(candidates), REDDIT_POST_LIMIT)} "
            f"({failed} windows failed, {empty} empty)")

    if no_coverage:
        log(f"  [reddit] {year}: no archive coverage for: {', '.join(no_coverage)}")
    return save(records, get_year_dir(year), "reddit", log)
