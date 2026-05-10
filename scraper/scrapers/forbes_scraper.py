"""
forbes_scraper.py — year-aware
Scrapes Forbes Gaming + VentureBeat GamesBeat + GamesIndustry.biz.
Filters articles by year when provided.
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
    "Accept-Language": "en-US,en;q=0.9",
}

MONTH_NAMES = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
               "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}


def _parse_year_from_text(text: str) -> int | None:
    """Try to extract a year (2020-2025) from any date string in the text."""
    m = re.search(r"\b(202[0-9])\b", text)
    return int(m.group(1)) if m else None


SOURCES = [
    {
        "name": "Forbes Gaming",
        "url":  "https://www.forbes.com/gaming/",
        "arts": ["article", ".stream-item", ".article-card"],
        "title":["h2", "h3", ".article-title"],
        "desc": ["p", ".article-description", ".deck"],
        "date": [".article-date", "time", "[class*='date']"],
    },
    {
        "name": "VentureBeat Games",
        "url":  "https://venturebeat.com/category/games/",
        "arts": ["article", ".ArticleListing"],
        "title":["h2", "h3"],
        "desc": ["p.ArticleListing__excerpt", "p.excerpt"],
        "date": ["time", ".ArticleListing__date", "[class*='date']"],
    },
    {
        "name": "GamesIndustry.biz",
        "url":  "https://www.gamesindustry.biz/mobile",
        "arts": ["article", "li.article"],
        "title":["h2", "h3", ".article__title"],
        "desc": ["p", ".article__summary"],
        "date": ["time", ".article__date", "[datetime]"],
    },
]


def _scrape_source(source: dict, year: int, sia: SentimentIntensityAnalyzer) -> list:
    results = []
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"  [forbes] HTTP {resp.status_code} from {source['name']}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        articles = []
        for sel in source["arts"]:
            articles = soup.select(sel)
            if articles:
                break

        for art in articles[:40]:
            title = next((el.get_text(strip=True) for s in source["title"]
                         if (el := art.select_one(s))), "")
            desc  = next((el.get_text(strip=True) for s in source["desc"]
                         if (el := art.select_one(s))), "")

            # Date filtering
            if year:
                date_text = ""
                for ds in source["date"]:
                    el = art.select_one(ds)
                    if el:
                        date_text = el.get("datetime", "") or el.get_text(strip=True)
                        break
                art_year = _parse_year_from_text(date_text or art.get_text())
                if art_year and art_year != year:
                    continue

            if not title or len(title) < 8:
                continue

            combined  = f"{title}. {desc}".strip()
            sentiment = sia.polarity_scores(combined)
            results.append({
                "source":    "forbes",
                "title":     title,
                "text":      desc,
                "sentiment": sentiment,
            })

        print(f"  [forbes] {source['name']}: {len(results)} articles")

    except Exception as e:
        print(f"  [forbes] Error scraping {source['name']}: {e}")

    return results


def run(year: int = None, output_path: str = None) -> list:
    sia     = SentimentIntensityAnalyzer()
    results = []

    year_label = f" [{year}]" if year else ""
    print(f"\n[forbes]{year_label} Scraping gaming industry news...")

    for source in SOURCES:
        results.extend(_scrape_source(source, year, sia))
        time.sleep(1.5)

    print(f"  [forbes] Total articles: {len(results)}")

    out_dir = get_year_dir(year) if year else DATA_DIR
    os.makedirs(out_dir, exist_ok=True)
    path = output_path or os.path.join(out_dir, "forbes_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  → Saved to {path}")

    return results


if __name__ == "__main__":
    run()
