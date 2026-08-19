"""
pocketgamer_scraper.py — year-aware
Scrapes Pocket Gamer mobile game reviews.
"""
import json, os, re, time, requests
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from config import DATA_DIR, get_year_dir

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}

CURRENT_PAGES = [
    "https://www.pocketgamer.com/reviews/",
    "https://www.pocketgamer.com/tag/fighting/",
    "https://www.pocketgamer.com/tag/action/",
    "https://www.pocketgamer.com/tag/multiplayer/",
]


def _archive_url(year: int) -> list[str]:
    return [
        f"https://www.pocketgamer.com/reviews/?year={year}",
        f"https://www.pocketgamer.com/tag/fighting/?year={year}",
    ]


def _parse_year_from_text(text: str) -> int | None:
    m = re.search(r"\b(202[0-9])\b", text)
    return int(m.group(1)) if m else None


def _star_words(rating_text: str) -> str:
    m = re.search(r"(\d+(?:\.\d+)?)", rating_text)
    if not m:
        return ""
    s = float(m.group(1))
    if s >= 8:   return "excellent game highly recommended outstanding"
    if s >= 6:   return "good game worth playing solid"
    if s >= 4:   return "average game mixed mediocre"
    return "disappointing poor not recommended avoid"


def _scrape_page(url: str, year: int, sia: SentimentIntensityAnalyzer) -> list:
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []

        soup     = BeautifulSoup(resp.text, "html.parser")
        articles = (soup.select("article")
                    or soup.select(".article-list-item")
                    or soup.select(".game-card")
                    or soup.select(".review-item"))

        for art in articles[:30]:
            title_el  = art.select_one("h1, h2, h3, h4, [class*='title']")
            desc_el   = art.select_one("p, [class*='summary'], [class*='excerpt']")
            rating_el = art.select_one("[class*='rating'], [class*='score'], [class*='star']")
            date_el   = art.select_one("time, [class*='date'], [datetime]")

            title  = title_el.get_text(strip=True)  if title_el  else ""
            desc   = desc_el.get_text(strip=True)   if desc_el   else ""
            rating = rating_el.get_text(strip=True) if rating_el else ""
            stars  = _star_words(rating)

            if year and date_el:
                date_str  = date_el.get("datetime", "") or date_el.get_text()
                art_year  = _parse_year_from_text(date_str)
                if art_year and art_year != year:
                    continue

            if not title or len(title) < 5:
                continue

            combined  = f"{title}. {desc} {stars}".strip()
            sentiment = sia.polarity_scores(combined)
            results.append({
                "source":    "pocketgamer",
                "title":     title,
                "text":      f"{desc} {stars}".strip(),
                "rating":    rating,
                "sentiment": sentiment,
            })

    except Exception:
        pass

    return results


def run(year: int = None, output_path: str = None) -> list:
    sia     = SentimentIntensityAnalyzer()
    results = []

    year_label = f" [{year}]" if year else ""
    print(f"\n[pocketgamer]{year_label} Scraping Pocket Gamer...")

    pages = _archive_url(year) if year else CURRENT_PAGES

    for url in pages:
        page_results = _scrape_page(url, year, sia)
        results.extend(page_results)
        print(f"  [pocketgamer] {url.rstrip('/').split('/')[-1] or 'reviews'}: {len(page_results)} items")
        time.sleep(1.2)

    seen, dedup = set(), []
    for r in results:
        if r["title"] not in seen:
            seen.add(r["title"])
            dedup.append(r)
    results = dedup

    print(f"  [pocketgamer] Total unique reviews: {len(results)}")

    out_dir = get_year_dir(year) if year else DATA_DIR
    os.makedirs(out_dir, exist_ok=True)
    path = output_path or os.path.join(out_dir, "pocketgamer_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  → Saved to {path}")

    return results


if __name__ == "__main__":
    run()
