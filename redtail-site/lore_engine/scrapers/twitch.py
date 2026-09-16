"""
Twitch scraper — top games by live viewers (a strong demand signal), with
real concurrent-viewer counts (not just rank) and genre tagging for
recognized competitor titles.
Needs a free app: dev.twitch.tv/console/apps → create app → copy Client ID +
Secret into .env as TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET. Skips without them.
"""
import requests

from config import (TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET, TWITCH_TOP_GAMES,
                    GENRES, get_year_dir)
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


def _genre_keyword_index() -> dict:
    """keyword -> genre, built from each genre's own competitor list (the
    same real, hand-verified titles used for competitor detection in
    analysis.py) — lets a Twitch top-game get tagged with a genre when it's
    a title we actually track (e.g. "Brawlhalla" -> fighting), while the
    many big untracked games (Fortnite, Just Chatting, GTA V, ...) stay
    untagged/"general", same as before."""
    idx = {}
    for g, meta in GENRES.items():
        for kws in meta["competitors"].values():
            for kw in kws:
                idx[kw.lower()] = g
    return idx


def _match_genre(name: str, idx: dict) -> str | None:
    low = name.lower()
    for kw, g in idx.items():
        if kw in low:
            return g
    return None


STREAMS_PER_GAME = 30  # individual live streams captured per top game (see run())


def _fetch_streams(game_id: str, headers: dict, log) -> list:
    """Up to 100 live streams for this game, most-watched first. Twitch has
    no single "total concurrent viewers for a game" endpoint, so this same
    page also backs the game's aggregate viewer_count (summed below) — one
    real API call, two uses, instead of fetching it and throwing the actual
    per-stream data away."""
    try:
        r = requests.get("https://api.twitch.tv/helix/streams", headers=headers,
                         params={"game_id": game_id, "first": 100}, timeout=15)
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception as e:
        log(f"  [twitch] stream fetch failed for game_id={game_id}: {e}")
        return []


def run(year: int | None = None, log=print) -> list:
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        log("  [twitch] skipped — set TWITCH_CLIENT_ID/SECRET in .env (free: dev.twitch.tv)")
        return save([], get_year_dir(year), "twitch", log)
    token = _token()
    if not token:
        log("  [twitch] auth failed — check TWITCH_CLIENT_ID/SECRET")
        return save([], get_year_dir(year), "twitch", log)

    genre_idx = _genre_keyword_index()
    log(f"[twitch] top {TWITCH_TOP_GAMES} games by viewers, each with up to "
        f"{STREAMS_PER_GAME} real individual live streams + genre tagging (tagged {year})")
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
            streams = _fetch_streams(g.get("id", ""), headers, log)
            viewers = sum(s.get("viewer_count", 0) for s in streams)
            genre = _match_genre(name, genre_idx)

            # One aggregate record for the game itself (unchanged shape).
            text = f"#{rank} most-watched game on Twitch right now: '{name}' ({viewers:,} concurrent viewers)."
            record = {
                "source": "twitch", "rank": rank, "title": f"#{rank} on Twitch: {name}",
                "text": text, "name": name, "viewer_count": viewers, "sentiment": score(text),
            }
            if genre:
                record["genre"] = genre
            records.append(record)

            # Plus one record per individual live stream — real stream
            # titles are genuine player/creator text (tournament callouts,
            # patch reactions, event hype, ...), the same kind of
            # keyword/sentiment surface reviews and comments provide
            # elsewhere, and this is the actual data the sum above was
            # already computed from.
            for s in streams[:STREAMS_PER_GAME]:
                title = (s.get("title") or "").strip()
                if not title:
                    continue
                stream_record = {
                    "source": "twitch", "rank": rank, "game": name,
                    "streamer": s.get("user_name", ""), "title": title,
                    "text": title, "viewer_count": s.get("viewer_count", 0),
                    "sentiment": score(title),
                }
                if genre:
                    stream_record["genre"] = genre
                records.append(stream_record)
        cursor = body.get("pagination", {}).get("cursor")
        if not cursor:
            break
    log(f"  [twitch] {len(records)} records ({rank} games)")
    return save(records, get_year_dir(year), "twitch", log)


if __name__ == "__main__":
    run()
