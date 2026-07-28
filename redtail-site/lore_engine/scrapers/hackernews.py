"""Hacker News scraper — Algolia search API. No key needed."""
import time
from datetime import datetime, timezone

import requests

from config import (GENRES, ACTIVE_GENRES, HN_QUERIES_COMMON, HN_HITS_PER_Q,
                    HN_COMMENTS_PER, get_year_dir)
from scrapers import score, save

SEARCH = "https://hn.algolia.com/api/v1/search_by_date"
ITEM   = "https://hn.algolia.com/api/v1/items/{id}"


def _year_bounds(year: int | None):
    if not year:
        return None, None
    start = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp())
    end   = int(datetime(year + 1, 1, 1, tzinfo=timezone.utc).timestamp())
    return start, end


def run(year: int | None = None, log=print) -> list:
    # (query, genre tag) pairs — common queries tag "general", each active
    # genre additionally contributes its own query tagged with that genre.
    queries = [(q, "general") for q in HN_QUERIES_COMMON]
    queries += [(GENRES[g]["hn_query"], g) for g in ACTIVE_GENRES]

    log(f"[hackernews] scraping {len(queries)} queries (year={year})")
    start, end = _year_bounds(year)
    records, seen = [], set()
    for q, genre in queries:
        params = {"query": q, "tags": "story", "hitsPerPage": HN_HITS_PER_Q}
        if start:
            params["numericFilters"] = f"created_at_i>={start},created_at_i<{end}"
        try:
            hits = requests.get(SEARCH, params=params, timeout=15).json().get("hits", [])
        except Exception as e:
            log(f"  [hackernews] query '{q}' failed: {e}")
            continue
        for h in hits:
            oid = h.get("objectID")
            if not oid or oid in seen:
                continue
            seen.add(oid)
            title = h.get("title") or h.get("story_title") or ""
            text  = h.get("story_text") or ""
            comments = []
            try:
                item = requests.get(ITEM.format(id=oid), timeout=15).json()
                for c in (item.get("children") or [])[:HN_COMMENTS_PER]:
                    body = (c.get("text") or "").strip()
                    if len(body) > 10:
                        comments.append({"body": body[:600], "sentiment": score(body)})
            except Exception:
                pass
            records.append({
                "source": "hackernews", "id": oid, "title": title, "genre": genre,
                "text": text[:600], "points": h.get("points", 0),
                "sentiment": score(f"{title} {text}"),
                "comments": comments,
            })
            time.sleep(0.2)
    return save(records, get_year_dir(year), "hackernews", log)


if __name__ == "__main__":
    run()
