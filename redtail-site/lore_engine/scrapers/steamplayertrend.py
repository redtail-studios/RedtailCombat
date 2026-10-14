"""Steam player-count snapshot scraper. SteamSpy's owners/ccu fields are a
point-in-time snapshot, not a history — there is no way to backfill "player
count over the last N months." This scraper exists purely to start
recording one snapshot per app per week, going forward, via the existing
weekly cron, so a real player-count-over-time chart becomes possible after
an accrual period. Reuses steam.py's app discovery; skips review fetching
entirely since only owners/ccu are needed here. No key needed.
"""
import time
from datetime import datetime, timedelta, timezone

from config import get_year_dir
from scrapers import save
from scrapers.steam import discover_apps, _details


def _week_of() -> str:
    now = datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    return monday.strftime("%Y-%m-%d")


def run(year: int | None = None, log=print, since=None) -> list:
    app_genre, _ = discover_apps()
    week_of = _week_of()
    log(f"[steamplayertrend] snapshotting {len(app_genre)} apps for week of {week_of}")
    records = []
    for app_id, genre in app_genre.items():
        d = _details(app_id)
        records.append({
            "source": "steamplayertrend", "snapshotId": f"{app_id}:{week_of}",
            "app_id": app_id, "genre": genre, "name": d.get("name", app_id),
            "weekOf": week_of, "ccu": d.get("ccu", 0), "owners": d.get("owners", ""),
        })
        time.sleep(0.5)
    log(f"  [steamplayertrend] {len(records)} snapshots")
    return save(records, get_year_dir(year), "steamplayertrend", log)


if __name__ == "__main__":
    run()
