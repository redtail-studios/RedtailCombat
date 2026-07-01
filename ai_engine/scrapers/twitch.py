"""
Twitch scraper — top games by live viewers (a strong demand signal).
Needs a free app: dev.twitch.tv/console/apps → create app → copy Client ID +
Secret into .env as TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET. Skips without them.
"""
import requests

from config import (TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET, TWITCH_TOP_GAMES,
                    get_year_dir)
from scrapers import score, save


def _token() -> str | None:
    try:
        r = requests.post("https://id.twitch.tv/oauth2/token", timeout=15, params={
            "client_id": TWITCH_CLIENT_ID, "client_secret": TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials"})
        r.raise_for_status()
        return r.json().get("access_token")
    except Exception:
        return None


def run(year: int | None = None, log=print) -> list:
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        log("  [twitch] skipped — set TWITCH_CLIENT_ID/SECRET in .env (free: dev.twitch.tv)")
        return save([], get_year_dir(year), "twitch", log)
    token = _token()
    if not token:
        log("  [twitch] auth failed — check TWITCH_CLIENT_ID/SECRET")
        return save([], get_year_dir(year), "twitch", log)

    # Live snapshot of top games by viewers — tagged to the run year.
    log(f"[twitch] top {TWITCH_TOP_GAMES} games by viewers (tagged {year})")
    headers = {"Client-Id": TWITCH_CLIENT_ID, "Authorization": f"Bearer {token}"}
    records, cursor, rank = [], None, 0
    while len(records) < TWITCH_TOP_GAMES:
        params = {"first": min(100, TWITCH_TOP_GAMES - len(records))}
        if cursor:
            params["after"] = cursor
        try:
            r = requests.get("https://api.twitch.tv/helix/games/top",
                             headers=headers, params=params, timeout=15)
            r.raise_for_status()
            body = r.json()
        except Exception as e:
            log(f"  [twitch] error: {e}")
            break
        games = body.get("data", [])
        if not games:
            break
        for g in games:
            rank += 1
            name = g.get("name", "")
            text = f"#{rank} most-watched game on Twitch right now: '{name}'."
            records.append({
                "source": "twitch", "rank": rank, "title": f"#{rank} on Twitch: {name}",
                "text": text, "name": name, "sentiment": score(text),
            })
        cursor = body.get("pagination", {}).get("cursor")
        if not cursor:
            break
    log(f"  [twitch] {len(records)} games")
    return save(records, get_year_dir(year), "twitch", log)


if __name__ == "__main__":
    run()
