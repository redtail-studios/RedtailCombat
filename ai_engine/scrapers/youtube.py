"""
YouTube scraper — game-video comments via the YouTube Data API v3.
Needs a free key: console.cloud.google.com → enable "YouTube Data API v3" →
create API key → put it in .env as YOUTUBE_API_KEY. Skips cleanly without one.
"""
import requests

from config import (YOUTUBE_API_KEY, YT_QUERIES, YT_VIDEOS_PER_Q,
                    YT_COMMENTS_PER, get_year_dir)
from scrapers import score, save

BASE = "https://www.googleapis.com/youtube/v3"


def _search_videos(q: str, year: int | None) -> list:
    params = {"part": "snippet", "q": q, "type": "video",
              "maxResults": YT_VIDEOS_PER_Q, "key": YOUTUBE_API_KEY, "relevanceLanguage": "en"}
    if year:
        params["publishedAfter"] = f"{year}-01-01T00:00:00Z"
        params["publishedBefore"] = f"{year}-12-31T23:59:59Z"
    try:
        r = requests.get(f"{BASE}/search", params=params, timeout=15)
        r.raise_for_status()
        return [(i["id"]["videoId"], i["snippet"]["title"]) for i in r.json().get("items", [])
                if i.get("id", {}).get("videoId")]
    except Exception:
        return []


def _comments(video_id: str) -> list:
    try:
        r = requests.get(f"{BASE}/commentThreads", timeout=15, params={
            "part": "snippet", "videoId": video_id, "maxResults": YT_COMMENTS_PER,
            "order": "relevance", "textFormat": "plainText", "key": YOUTUBE_API_KEY})
        if r.status_code != 200:
            return []
        out = []
        for it in r.json().get("items", []):
            t = it["snippet"]["topLevelComment"]["snippet"].get("textDisplay", "").strip()
            if len(t) > 10:
                out.append({"body": t[:600], "sentiment": score(t)})
        return out
    except Exception:
        return []


def run(year: int | None = None, log=print) -> list:
    if not YOUTUBE_API_KEY:
        log("  [youtube] skipped — set YOUTUBE_API_KEY in .env (free: YouTube Data API v3)")
        return save([], get_year_dir(year), "youtube", log)
    log(f"[youtube] {len(YT_QUERIES)} queries (year={year})")
    records = []
    for q in YT_QUERIES:
        for vid, title in _search_videos(q, year):
            comments = _comments(vid)
            records.append({
                "source": "youtube", "query": q, "video_id": vid,
                "title": title, "text": title,
                "url": f"https://youtube.com/watch?v={vid}",
                "sentiment": score(title), "comments": comments,
            })
        log(f"  [youtube] '{q}': done")
    return save(records, get_year_dir(year), "youtube", log)


if __name__ == "__main__":
    run()
