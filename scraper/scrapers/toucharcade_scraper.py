"""
toucharcade_scraper.py — year-aware
Scrapes TouchArcade reviews. When year is given, uses the WordPress
monthly archive URLs (toucharcade.com/YYYY/MM/) for accurate historical data.
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
}

CURRENT_PAGES = [
    "https://toucharcade.com/category/reviews/",
    "https://toucharcade.com/category/reviews/page/2/",
    "https://toucharcade.com/?s=fighting+game",
    "https://toucharcade.com/?s=mobile+pvp",
]


def _archive_urls(year: int) -> list[str]:
    """Return monthly archive URLs for a given year."""
    return [f"https://toucharcade.com/{year}/{month:02d}/" for month in range(1, 13)]


def _scrape_page(url: str, sia: SentimentIntensityAnalyzer) -> list:
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 404:
            return []
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        articles = (
            soup.select("article")
            or soup.select(".post")
            or soup.select(".entry")
        )

        for art in articles[:25]:
            title_el   = art.select_one("h1, h2, h3, .entry-title, .post-title")
            excerpt_el = art.select_one(".entry-summary, .excerpt, p.summary, p")
            rating_el  = art.select_one("[class*='rating'], [class*='star']")

            title   = title_el.get_text(strip=True)   if title_el   else ""
            excerpt = excerpt_el.get_text(strip=True)  if excerpt_el else ""
            rating  = rating_el.get_text(strip=True)   if rating_el  else ""

            if not title or len(title) < 6:
                continue

            combined  = f"{title}. {excerpt} {rating}".strip()
            sentiment = sia.polarity_scores(combined)
            results.append({
                "source":    "toucharcade",
                "title":     title,
                "text":      excerpt,
                "sentiment": sentiment,
            })

    except Exception as e:
        pass  # silently skip failed pages

    return results


def run(year: int = None, output_path: str = None) -> list:
    sia     = SentimentIntensityAnalyzer()
    results = []

    year_label = f" [{year}]" if year else ""
    print(f"\n[toucharcade]{year_label} Scraping TouchArcade...")

    pages = _archive_urls(year) if year else CURRENT_PAGES

    for url in pages:
        page_results = _scrape_page(url, sia)
        results.extend(page_results)
        if page_results:
            print(f"  [toucharcade] {url.rstrip('/').split('/')[-1] or 'page'}: {len(page_results)} items")
        time.sleep(1.2)

    # De-duplicate
    seen, dedup = set(), []
    for r in results:
        if r["title"] not in seen:
            seen.add(r["title"])
            dedup.append(r)
    results = dedup

    print(f"  [toucharcade] Total unique articles: {len(results)}")

    out_dir = get_year_dir(year) if year else DATA_DIR
    os.makedirs(out_dir, exist_ok=True)
    path = output_path or os.path.join(out_dir, "toucharcade_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  → Saved to {path}")

    return results


if __name__ == "__main__":
    run()
