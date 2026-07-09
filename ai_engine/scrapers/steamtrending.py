"""Steam trending scraper — SteamSpy top-100-by-players (last 2 weeks). No key."""
import requests

from config import STEAM_TRENDING_N, get_year_dir
from scrapers import score, save

URL = "https://steamspy.com/api.php"


def run(year: int | None = None, log=print) -> list:
    # Live snapshot of what's being played now — tagged to the run year.
    log(f"[steamtrending] SteamSpy top-100-in-2-weeks (tagged {year})")
    try:
        r = requests.get(URL, params={"request": "top100in2weeks"}, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log(f"  [steamtrending] error: {e}")
        return save([], get_year_dir(year), "steamtrending", log)

    records = []
    for rank, (appid, g) in enumerate(list(data.items())[:STEAM_TRENDING_N], 1):
        name = g.get("name", str(appid))
        tags = list((g.get("tags") or {}).keys())[:8]
        owners = g.get("owners", "")
        text = (f"#{rank} trending on Steam (2-week players): '{name}' "
                f"— owners {owners}; tags: {', '.join(tags) or 'n/a'}.")
        records.append({
            "source": "steamtrending", "rank": rank, "app_id": appid,
            "title": f"#{rank} Steam trending: {name}", "text": text,
            "name": name, "owners": owners, "tags": tags,
            "ccu": g.get("ccu", 0), "sentiment": score(text),
        })
    log(f"  [steamtrending] {len(records)} trending games")
    return save(records, get_year_dir(year), "steamtrending", log)


if __name__ == "__main__":
    run()
