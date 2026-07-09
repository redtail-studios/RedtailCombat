"""
Reddit scraper — PUBLIC RSS feeds. No API key, no OAuth, works from any IP.

Reddit shut down keyless access to its JSON API (/r/<sub>/hot.json now 403s for
everyone, authenticated-only), but it still serves the RSS/Atom feeds openly:
    https://www.reddit.com/r/<sub>/hot/.rss
    https://www.reddit.com/r/<sub>/top/.rss?t=year
We pull those, parse with the standard library, strip HTML, score sentiment.

Each RSS feed returns ~25 of the freshest items, so per subreddit we combine
hot + top-of-year and dedupe. Polite delays + 429 backoff keep Reddit happy.
"""
import html
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import requests

from config import (SUBREDDITS, REDDIT_BROAD, REDDIT_KEYWORDS, REDDIT_TOP_TIME,
                    REDDIT_POST_LIMIT, REDDIT_USER_AGENT, get_year_dir)
from scrapers import score, save

ATOM = "{http://www.w3.org/2005/Atom}"
UA = REDDIT_USER_AGENT or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/124 Safari/537.36"
NOW_YEAR = datetime.now(timezone.utc).year
_TAGS = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", _TAGS.sub(" ", html.unescape(text))).strip()


def _fetch(url: str, params: dict, log, tries: int = 4) -> str | None:
    for i in range(tries):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, params=params, timeout=15)
        except Exception as e:
            log(f"    request error: {e}")
            time.sleep(2 * (i + 1))
            continue
        if r.status_code == 200:
            return r.text
        if r.status_code == 429:
            time.sleep(5 * (i + 1))  # rate-limited — back off
            continue
        if r.status_code in (403, 404):
            return None
        time.sleep(2 * (i + 1))
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
    log(f"[reddit] scraping {len(SUBREDDITS)} subreddits via public RSS feeds "
        f"(no key) (year={year})")
    kws = [k.lower() for k in REDDIT_KEYWORDS]
    records, blocked = [], 0

    for sub in SUBREDDITS:
        posts, seen = [], set()
        for kind, params in (("hot", {}), ("top", {"t": REDDIT_TOP_TIME})):
            xml = _fetch(f"https://www.reddit.com/r/{sub}/{kind}/.rss", params, log)
            time.sleep(1.5)  # be polite — RSS rate-limits if hammered
            if not xml:
                continue
            for p in _parse(xml):
                if p["id"] and p["id"] not in seen:
                    seen.add(p["id"])
                    posts.append(p)
            if len(posts) >= REDDIT_POST_LIMIT:
                break
        if not posts:
            blocked += 1
            continue

        broad = sub in REDDIT_BROAD
        kept = 0
        for p in posts[:REDDIT_POST_LIMIT]:
            # Year filter only for past years (RSS is freshest-first; current year ok).
            if year and year < NOW_YEAR and p["year"] and p["year"] != year:
                continue
            if broad and not any(k in f"{p['title']} {p['text']}".lower() for k in kws):
                continue
            records.append({
                "source": "reddit", "subreddit": sub,
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
