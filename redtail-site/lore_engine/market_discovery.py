"""Small public welcome feed. Reads existing market data; never runs a scraper or AI."""
import json
import re
import threading
import time

from fastapi.responses import JSONResponse

import storage

# Steam's trending feed can contain desktop software, which is not a game.
NON_GAME_APPS = {'431960', '629520'}  # Wallpaper Engine, Soundpad


def ranked_games(records, limit=20):
    candidates = []
    for row in records if isinstance(records, list) else []:
        if not isinstance(row, dict):
            continue
        name = row.get('name')
        app_id = str(row.get('app_id', ''))
        rank = row.get('rank')
        if not isinstance(name, str) or not name.strip() or not re.fullmatch(r'[0-9]+', app_id):
            continue
        if isinstance(rank, bool) or not isinstance(rank, int) or rank < 1 or app_id in NON_GAME_APPS:
            continue
        candidates.append({'id': app_id, 'name': name.strip(), 'rank': rank, 'sourceUrl': f'https://store.steampowered.com/app/{app_id}/'})
    seen_ids, seen_names, games = set(), set(), []
    for item in sorted(candidates, key=lambda game: (game['rank'], game['name'])):
        name = item['name'].casefold()
        if item['id'] in seen_ids or name in seen_names:
            continue
        seen_ids.add(item['id']); seen_names.add(name); games.append(item)
        if len(games) == limit:
            break
    return games


def install(app, year):
    cache = {}
    lock = threading.Lock()

    @app.get('/api/lore/discover-games')
    def discover_games():
        with lock:
            if cache and time.monotonic() - cache['at'] < 300:
                return cache['payload']
            try:
                obj = storage._s3_client().get_object(Bucket=storage.BUCKET, Key=storage._data_key(year, 'steamtrending'))
                records = json.loads(obj['Body'].read())
                games = ranked_games(records)
                if not games:
                    return JSONResponse({'error': 'Trending games are not available yet. You can still add your game.'}, status_code=503)
                payload = {'games': games, 'source': 'SteamSpy', 'feed': 'Steam trending · two-week players', 'sourceUrl': 'https://steamspy.com/', 'snapshotAt': obj['LastModified'].isoformat(), 'year': year}
                cache.update(at=time.monotonic(), payload=payload)
                return payload
            except Exception:
                return JSONResponse({'error': 'Trending games could not load. You can still add your game.'}, status_code=503)
    return discover_games
