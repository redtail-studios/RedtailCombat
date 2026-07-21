"""Steam charts scraper — Steam store featuredcategories (no key)."""
import requests

from config import STEAM_CHARTS_PER_LIST, get_year_dir
from scrapers import score, save

URL = "https://store.steampowered.com/api/featuredcategories"
LISTS = [("top_sellers", "top seller"), ("new_releases", "new release"),
         ("specials", "discounted")]


def run(year: int | None = None, log=print) -> list:
    # Live commercial snapshot (no historical feed) — tagged to the run year.
    log(f"[steamcharts] Steam top sellers / new / specials (tagged {year})")
    try:
        data = requests.get(URL, params={"cc": "us", "l": "en"}, timeout=20).json()
    except Exception as e:
        log(f"  [steamcharts] error: {e}")
        return save([], get_year_dir(year), "steamcharts", log)

    records = []
    for key, label in LISTS:
        items = (data.get(key) or {}).get("items", []) or []
        for rank, it in enumerate(items[:STEAM_CHARTS_PER_LIST], 1):
            name = it.get("name", "")
            if not name:
                continue
            text = f"#{rank} Steam {label}: '{name}'."
            records.append({
                "source": "steamcharts", "chart": label, "rank": rank,
                "app_id": it.get("id"), "title": f"#{rank} {label}: {name}",
                "text": text, "name": name, "sentiment": score(text),
            })
        log(f"  [steamcharts] {label}: {min(len(items), STEAM_CHARTS_PER_LIST)} games")
    return save(records, get_year_dir(year), "steamcharts", log)


if __name__ == "__main__":
    run()
