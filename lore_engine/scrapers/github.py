"""GitHub scraper — trending game repos/engines/tools. Public API, no key (low rate)."""
import time

import requests

from config import GITHUB_QUERIES, GITHUB_PER_Q, get_year_dir
from scrapers import score, save

API = "https://api.github.com/search/repositories"
UA = "redtail-lore/1.0"


def run(year: int | None = None, log=print) -> list:
    log(f"[github] trending game projects, {len(GITHUB_QUERIES)} queries (year={year})")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": UA}
    records, seen = [], set()
    for q in GITHUB_QUERIES:
        # Recently-pushed, reasonably-starred repos = currently-active game dev.
        params = {"q": f"{q} stars:>30 pushed:>{(year or 2026)}-01-01",
                  "sort": "updated", "order": "desc", "per_page": GITHUB_PER_Q}
        try:
            r = requests.get(API, headers=headers, params=params, timeout=15)
            if r.status_code != 200:
                log(f"  [github] '{q}' HTTP {r.status_code}")
                time.sleep(5)
                continue
            items = r.json().get("items", [])
        except Exception as e:
            log(f"  [github] '{q}' error: {e}")
            continue
        kept = 0
        for repo in items:
            full = repo.get("full_name", "")
            if not full or full in seen:
                continue
            seen.add(full)
            desc = repo.get("description") or ""
            stars = repo.get("stargazers_count", 0)
            topics = repo.get("topics", [])[:8]
            text = (f"GitHub game project '{full}' ({stars}★, {repo.get('language') or 'n/a'}): "
                    f"{desc} Topics: {', '.join(topics) or 'none'}.")
            records.append({
                "source": "github", "query": q, "repo": full,
                "title": f"{full} ({stars}★)", "text": text[:600],
                "stars": stars, "topics": topics, "url": repo.get("html_url", ""),
                "sentiment": score(f"{full} {desc}"),
            })
            kept += 1
        log(f"  [github] '{q}': {kept} repos")
        time.sleep(6)  # unauth search rate limit is ~10/min
    return save(records, get_year_dir(year), "github", log)


if __name__ == "__main__":
    run()
