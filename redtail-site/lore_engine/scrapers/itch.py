"""itch.io scraper — featured indie games via public RSS. No key."""
import html
import re
import xml.etree.ElementTree as ET

import requests

from config import ITCH_FEED, ITCH_LIMIT, get_year_dir
from scrapers import score, save

ATOM = "{http://www.w3.org/2005/Atom}"
UA = "Mozilla/5.0 Chrome/124"
_TAGS = re.compile(r"<[^>]+>")


def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", _TAGS.sub(" ", html.unescape(t or ""))).strip()


def run(year: int | None = None, log=print) -> list:
    log(f"[itch] featured indie games (tagged {year})")
    try:
        r = requests.get(ITCH_FEED, headers={"User-Agent": UA}, timeout=15)
        if r.status_code != 200:
            log(f"  [itch] HTTP {r.status_code}")
            return save([], get_year_dir(year), "itch", log)
        root = ET.fromstring(r.text)
    except Exception as e:
        log(f"  [itch] error: {e}")
        return save([], get_year_dir(year), "itch", log)

    items = []
    for it in root.iter("item"):  # RSS 2.0
        items.append((it.findtext("title") or "", _clean(it.findtext("description") or ""),
                      it.findtext("link") or ""))
    for e in root.findall(ATOM + "entry"):  # Atom fallback
        link_el = e.find(ATOM + "link")
        items.append((e.findtext(ATOM + "title") or "",
                      _clean(e.findtext(ATOM + "summary") or e.findtext(ATOM + "content") or ""),
                      link_el.get("href") if link_el is not None else ""))

    records = []
    for title, text, link in items[:ITCH_LIMIT]:
        if len(title) < 2:
            continue
        records.append({
            "source": "itch", "title": title.strip(), "text": text[:600],
            "url": link, "sentiment": score(f"{title} {text}"),
        })
    log(f"  [itch] {len(records)} featured games")
    return save(records, get_year_dir(year), "itch", log)


if __name__ == "__main__":
    run()
