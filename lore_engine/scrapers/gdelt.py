"""
GDELT scraper — global news search via GDELT's DOC 2.0 API. No key. Adds
100+-language, worldwide article coverage that complements GAMENEWS_FEEDS'
curated list of major English-language outlets. GDELT has no documented rate
limit in its own docs; its error response says "one every 5 seconds," but
live testing showed even that gets a 429 back-to-back in practice — so this
sleeps well past that between queries and treats any failure (429, or the
rate-limit notice coming back as plain text instead of JSON) as a
skip-and-log case, not a crash. Expect some queries in a run to come back
empty on a bad day; that's this API being flaky, not a bug here.
"""
import time
from datetime import datetime, timezone

import requests

from config import GENRES, ACTIVE_GENRES, GDELT_QUERIES_COMMON, GDELT_HITS_PER_Q, get_year_dir
from scrapers import score, save

URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def _parse_seendate(seendate: str):
    try:  # GDELT seendate is "YYYYMMDDTHHMMSSZ"
        return datetime.strptime(seendate, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _year_of(seendate: str) -> int | None:
    dt = _parse_seendate(seendate)
    return dt.year if dt else None


def _search(query: str, log, startdatetime: str | None = None) -> list:
    # Unquoted multi-word queries match each word independently (verified
    # live — "mobile game" pulled in unrelated "game conference" and
    # "mobile phone" articles) rather than the phrase; quote it for an exact
    # phrase match, GDELT's documented convention for multi-word terms.
    gdelt_query = f'"{query}"' if " " in query else query
    params = {"query": gdelt_query, "mode": "artlist", "format": "json",
              "maxrecords": GDELT_HITS_PER_Q, "sort": "datedesc"}
    if startdatetime:
        params["startdatetime"] = startdatetime  # real server-side filtering, format YYYYMMDDHHMMSS
    try:
        r = requests.get(URL, timeout=50, params=params)
        r.raise_for_status()
        return r.json().get("articles", [])
    except ValueError:
        # GDELT returns its rate-limit notice as plain text (HTTP 200), which
        # .json() can't parse — treat exactly like any other transient error.
        log(f"  [gdelt] query '{query}' rate-limited or non-JSON response, skipping")
        return []
    except Exception as e:
        log(f"  [gdelt] query '{query}' failed: {e}")
        return []


def run(year: int | None = None, log=print, since=None) -> list:
    queries = [(q, "general") for q in GDELT_QUERIES_COMMON]
    queries += [(GENRES[g]["hn_query"], g) for g in ACTIVE_GENRES]

    startdatetime = since.strftime("%Y%m%d%H%M%S") if since else None
    log(f"[gdelt] scraping {len(queries)} queries (year={year}, since={since})")
    records = []
    for q, genre in queries:
        articles = _search(q, log, startdatetime=startdatetime)
        kept = 0
        for a in articles:
            if year and (_year_of(a.get("seendate", "")) != year):
                continue
            if since is not None:
                dt = _parse_seendate(a.get("seendate", ""))
                if dt is not None and dt <= since:
                    continue  # defensive — startdatetime should've already excluded this
            title = (a.get("title") or "").strip()
            if len(title) < 5:
                continue
            domain = a.get("domain", "")
            sourcecountry = a.get("sourcecountry", "")
            language = a.get("language", "")
            text = f"'{title}' — {domain} ({sourcecountry}, {language})."
            records.append({
                "source": "gdelt", "title": title, "genre": genre,
                "text": text, "url": a.get("url", ""), "date": a.get("seendate", ""),
                "domain": domain, "sourcecountry": sourcecountry, "language": language,
                "sentiment": score(title),
            })
            kept += 1
        log(f"  [gdelt] '{q}': {kept} articles")
        time.sleep(10)  # GDELT's stated "one every 5 seconds" 429'd anyway in live testing
    return save(records, get_year_dir(year), "gdelt", log)


if __name__ == "__main__":
    run()
