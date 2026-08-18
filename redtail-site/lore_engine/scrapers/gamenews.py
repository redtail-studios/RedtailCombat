"""Gaming news scraper — public RSS feeds from major outlets. No key."""
import html
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

import requests

from config import GAMENEWS_FEEDS, GAMENEWS_PER_FEED, get_year_dir
from scrapers import score, save

ATOM = "{http://www.w3.org/2005/Atom}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/124 Safari/537.36"
_TAGS = re.compile(r"<[^>]+>")


def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", _TAGS.sub(" ", html.unescape(t or ""))).strip()


def _parse_date(s: str):
    if not s:
        return None
    try:
        if "T" in s and s[:4].isdigit():  # Atom ISO
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        return parsedate_to_datetime(s)  # RSS RFC822
    except Exception:
        return None


def _year_of(s: str) -> int | None:
    dt = _parse_date(s)
    return dt.year if dt else None


def _items(xml_text: str) -> list:
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return []
    out = []
    # RSS 2.0
    for it in root.iter("item"):
        out.append({
            "title": it.findtext("title") or "",
            "text": _clean(it.findtext("description") or ""),
            "link": it.findtext("link") or "",
            "date": it.findtext("pubDate") or "",
        })
    # Atom
    for e in root.findall(ATOM + "entry"):
        link_el = e.find(ATOM + "link")
        out.append({
            "title": e.findtext(ATOM + "title") or "",
            "text": _clean(e.findtext(ATOM + "summary") or e.findtext(ATOM + "content") or ""),
            "link": link_el.get("href") if link_el is not None else "",
            "date": e.findtext(ATOM + "published") or e.findtext(ATOM + "updated") or "",
        })
    return out


def run(year: int | None = None, log=print, since=None) -> list:
    # Feeds themselves have no date-range query — they're always a full pull
    # of their latest N items — so `since` only trims what gets kept, not the
    # request itself. That's still worth it: fewer records built + logged,
    # and worker.py's merge-by-url dedupes the rest regardless.
    log(f"[gamenews] scraping {len(GAMENEWS_FEEDS)} news feeds (year={year}, since={since})")
    records = []
    for name, url in GAMENEWS_FEEDS:
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=15)
            if r.status_code != 200:
                log(f"  [gamenews] {name} HTTP {r.status_code}")
                continue
            items = _items(r.text)[:GAMENEWS_PER_FEED]
        except Exception as e:
            log(f"  [gamenews] {name} error: {e}")
            continue
        kept = 0
        for it in items:
            dt = _parse_date(it["date"])
            if year and (dt.year if dt else None) not in (None, year):
                continue
            if since is not None and dt is not None:
                try:
                    if dt <= since:
                        continue
                except TypeError:
                    pass  # naive/aware mismatch — keep the item rather than guess
            title = it["title"].strip()
            if len(title) < 5:
                continue
            records.append({
                "source": "gamenews", "site": name,
                "title": title, "text": it["text"][:600],
                "url": it["link"], "date": it["date"],
                "sentiment": score(f"{title} {it['text']}"),
            })
            kept += 1
        log(f"  [gamenews] {name}: {kept} articles")
        time.sleep(0.5)
    return save(records, get_year_dir(year), "gamenews", log)


if __name__ == "__main__":
    run()
