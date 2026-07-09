"""Wikipedia pageviews scraper — Wikimedia REST API. No key. Popularity trend proxy."""
import time

import requests

from config import WIKI_ARTICLES, get_year_dir
from scrapers import score, save

API = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
       "en.wikipedia/all-access/all-agents/{article}/monthly/{start}/{end}")
UA = "redtail-market-intel/1.0 (market research)"  # Wikimedia requires a UA


def run(year: int | None = None, log=print) -> list:
    y = year or 2026
    start, end = f"{y}010100", f"{y}120100"
    log(f"[wikipedia] pageviews for {len(WIKI_ARTICLES)} articles ({y})")
    records = []
    for article in WIKI_ARTICLES:
        try:
            r = requests.get(API.format(article=article, start=start, end=end),
                             headers={"User-Agent": UA}, timeout=15)
            if r.status_code != 200:
                log(f"  [wikipedia] {article} HTTP {r.status_code}")
                continue
            items = r.json().get("items", [])
        except Exception as e:
            log(f"  [wikipedia] {article} error: {e}")
            continue
        if not items:
            continue
        total = sum(i.get("views", 0) for i in items)
        first = items[0].get("views", 0)
        last = items[-1].get("views", 0)
        trend = "rising" if last > first * 1.15 else "falling" if last < first * 0.85 else "steady"
        name = article.replace("_", " ")
        text = (f"Wikipedia interest in '{name}' during {y}: {total:,} total pageviews "
                f"across {len(items)} months, trend {trend} "
                f"({first:,}/mo → {last:,}/mo).")
        records.append({
            "source": "wikipedia", "article": name, "title": f"{name} — Wikipedia interest {y}",
            "text": text, "views_total": total, "trend": trend,
            "sentiment": score(text),
        })
        log(f"  [wikipedia] {name}: {total:,} views ({trend})")
        time.sleep(0.3)
    return save(records, get_year_dir(year), "wikipedia", log)


if __name__ == "__main__":
    run()
