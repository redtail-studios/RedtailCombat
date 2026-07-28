"""
Reddit scraper — PUBLIC RSS feeds. No API key, no OAuth, works from any IP.

Reddit shut down keyless access to its JSON API (/r/<sub>/hot.json now 403s for
everyone, authenticated-only), but it still serves the RSS/Atom feeds openly:
    https://www.reddit.com/r/<sub>/hot/.rss
We pull that, parse with the standard library, strip HTML, score sentiment.

Only "hot" is fetched (not "top") to keep the per-subreddit request count to
one — this scraper runs on a background worker with a wall-clock budget, and
doubling requests per subreddit for "top" wasn't worth it: t=year means "top
of the last 365 days", not "top of a given historical year", so it mostly
duplicated "hot" for the current year anyway. Polite delays + 429 backoff
keep Reddit happy.

Consequence worth knowing: "hot" only reflects what's active right now, so
scraping any year other than the current one (see NOW_YEAR below) reliably
comes back with zero records — run()'s year filter has nothing years-old to
keep, since "hot" almost never surfaces a post that old. There's no fix for
this without a different endpoint (Reddit's RSS has no date-range query;
only the OAuth search API does) — see SCRAPING_ARCHITECTURE.md §5.
"""
import html
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import requests

from config import (SUBREDDITS_COMMON, SUBREDDITS_BROAD, REDDIT_KEYWORDS_COMMON,
                    GENRES, ACTIVE_GENRES, REDDIT_POST_LIMIT, REDDIT_USER_AGENT,
                    get_year_dir)
from scrapers import score, save

ATOM = "{http://www.w3.org/2005/Atom}"
UA = REDDIT_USER_AGENT or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/124 Safari/537.36"
NOW_YEAR = datetime.now(timezone.utc).year
_TAGS = re.compile(r"<[^>]+>")
MAX_RATE_LIMIT_WAIT = 65  # cap a single 429 wait — Reddit's window is ~60s; guards against a bad/huge header


def _clean(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", _TAGS.sub(" ", html.unescape(text))).strip()


def _retry_wait(headers, default: float) -> float:
    """How long to sleep before retrying a 429. Reddit tells us exactly when
    quota refills (retry-after, or its own x-ratelimit-reset) — prefer that
    over guessing with a fixed backoff, since a fixed schedule that's shorter
    than the real reset window just burns all our tries on guaranteed 429s."""
    for name in ("retry-after", "x-ratelimit-reset"):
        raw = headers.get(name)
        if raw is None:
            continue
        try:
            return min(float(raw) + 1, MAX_RATE_LIMIT_WAIT)  # +1s buffer past the exact reset
        except ValueError:
            continue
    return default


def _fetch(url: str, params: dict, log, tries: int = 5) -> str | None:
    for i in range(tries):
        t0 = time.monotonic()
        try:
            r = requests.get(url, headers={"User-Agent": UA}, params=params, timeout=50)
        except Exception as e:
            log(f"    [DIAG] {url} attempt {i+1}: request error after "
                f"{time.monotonic()-t0:.1f}s: {e}")
            time.sleep(4 * (i + 1))
            continue
        log(f"    [DIAG] {url} attempt {i+1}: status={r.status_code} "
            f"in {time.monotonic()-t0:.1f}s "
            f"retry-after={r.headers.get('retry-after')} "
            f"x-ratelimit-remaining={r.headers.get('x-ratelimit-remaining')} "
            f"x-ratelimit-reset={r.headers.get('x-ratelimit-reset')}"
            )
        if r.status_code == 200:
            return r.text
        if r.status_code == 429:
            wait = _retry_wait(r.headers, default=5 * (i + 1))
            log(f"    [DIAG] {url} attempt {i+1}: rate-limited, waiting {wait:.0f}s for quota to refill")
            time.sleep(wait)
            continue
        if r.status_code in (403, 404):
            return None
        time.sleep(4 * (i + 1))
    return None


def _parse(xml_text: str) -> list:
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return []
    out = []
    for e in root.findall(ATOM + "entry"):
        link_el = e.find(ATOM + "link")
        auth = e.find(ATOM + "author")
        pub = e.findtext(ATOM + "published") or e.findtext(ATOM + "updated") or ""
        year = None
        if pub[:4].isdigit():
            year = int(pub[:4])
        out.append({
            "id": e.findtext(ATOM + "id") or "",
            "title": e.findtext(ATOM + "title") or "",
            "text": _clean(e.findtext(ATOM + "content") or ""),
            "link": link_el.get("href") if link_el is not None else "",
            "author": auth.findtext(ATOM + "name") if auth is not None else "",
            "year": year,
        })
    return out


def run(year: int | None = None, log=print) -> list:
    # Niche subs: common ones (genre="general") plus each active genre's own
    # subreddits (genre=<that genre>). A sub only ever belongs to one genre
    # here — later entries in ACTIVE_GENRES win on the rare overlap.
    niche_genre = {sub: "general" for sub in SUBREDDITS_COMMON}
    for g in ACTIVE_GENRES:
        for sub in GENRES[g]["subreddits"]:
            niche_genre[sub] = g

    # Broad subs are huge/off-topic — a post only survives if it matches some
    # genre's keyword list (tagged with that genre) or the common keyword
    # list (tagged "general"); everything else is dropped, same as before.
    genre_kws = {g: [k.lower() for k in GENRES[g]["reddit_keywords"]] for g in ACTIVE_GENRES}
    common_kws = [k.lower() for k in REDDIT_KEYWORDS_COMMON]

    all_subs = list(niche_genre) + list(SUBREDDITS_BROAD)
    log(f"[reddit] scraping {len(all_subs)} subreddits via public RSS feeds "
        f"(no key) (year={year}, genres={ACTIVE_GENRES})")
    records, blocked = [], 0

    for sub in all_subs:
        posts, seen = [], set()
        # Only "hot" — "top" doubled every subreddit's request count for
        # marginal gain (t=year means "top of the last 365 days", not "top of
        # a given historical year", so it mostly duplicated "hot" anyway for
        # the current year and was of dubious value for past years).
        xml = _fetch(f"https://www.reddit.com/r/{sub}/hot/.rss", {}, log)
        time.sleep(1.5)  # be polite — RSS rate-limits if hammered
        if xml:
            for p in _parse(xml):
                if p["id"] and p["id"] not in seen:
                    seen.add(p["id"])
                    posts.append(p)
        if not posts:
            blocked += 1
            continue

        broad = sub in SUBREDDITS_BROAD
        kept = 0
        for p in posts[:REDDIT_POST_LIMIT]:
            # Year filter only for past years (RSS is freshest-first; current year ok).
            # For any year < NOW_YEAR this drops nearly everything, by design
            # of what "hot" is — see the module docstring above.
            if year and year < NOW_YEAR and p["year"] and p["year"] != year:
                continue
            text_low = f"{p['title']} {p['text']}".lower()
            if broad:
                genre = next((g for g, kws in genre_kws.items()
                             if any(k in text_low for k in kws)), None)
                if genre is None and any(k in text_low for k in common_kws):
                    genre = "general"
                if genre is None:
                    continue
            else:
                genre = niche_genre[sub]
            records.append({
                "source": "reddit", "subreddit": sub, "genre": genre,
                "title": p["title"], "text": p["text"][:600],
                "author": p["author"], "url": p["link"],
                "sentiment": score(f"{p['title']} {p['text']}"),
                "comments": [],
            })
            kept += 1
        log(f"  [reddit] r/{sub}: kept {kept} posts")

    if blocked and not records:
        log("  [reddit] all feeds empty/blocked — unusual for RSS; try again later "
            "(likely a temporary 429 rate-limit).")
    return save(records, get_year_dir(year), "reddit", log)


if __name__ == "__main__":
    run()
