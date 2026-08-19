"""
reddit_scraper.py — year-aware
Scrapes gaming subreddits via PRAW, filtering by year when provided.
Note: Reddit's public API limits access to ~1,000 most recent posts per
subreddit; historical data (2022–2023) may be sparse without Pushshift access.
"""
import json, time, os
from datetime import datetime
import praw
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from tqdm import tqdm
from config import (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT,
                    SUBREDDITS, REDDIT_KEYWORDS, REDDIT_POST_LIMIT,
                    REDDIT_COMMENT_LIMIT, DATA_DIR, get_year_dir)


def get_reddit_client():
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        raise ValueError(
            "Reddit API credentials missing. Add REDDIT_CLIENT_ID and "
            "REDDIT_CLIENT_SECRET to scraper/.env"
        )
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )


def scrape_subreddit(reddit, subreddit_name: str, sia: SentimentIntensityAnalyzer,
                     year: int = None) -> list:
    posts = []
    sub   = reddit.subreddit(subreddit_name)

    # For year-specific scraping, search with date keywords + filter by timestamp
    if year:
        streams = [
            sub.search(" ".join(REDDIT_KEYWORDS[:3]), sort="new", limit=500),
            sub.top("year", limit=REDDIT_POST_LIMIT),
        ]
    else:
        streams = [
            sub.hot(limit=REDDIT_POST_LIMIT // 2),
            sub.top("week", limit=REDDIT_POST_LIMIT // 2),
        ]

    for stream in streams:
        try:
            for post in stream:
                # Year filter
                if year:
                    post_year = datetime.utcfromtimestamp(post.created_utc).year
                    if post_year != year:
                        if post_year < year:
                            break  # going backward in time
                        continue

                body      = (post.selftext or "").strip()
                full_text = post.title + " " + body
                sentiment = sia.polarity_scores(full_text[:1000])

                post.comments.replace_more(limit=0)
                comments = []
                for comment in post.comments[:REDDIT_COMMENT_LIMIT]:
                    if hasattr(comment, "body") and len(comment.body) > 20:
                        c_sentiment = sia.polarity_scores(comment.body[:500])
                        comments.append({
                            "body":      comment.body[:500],
                            "score":     comment.score,
                            "sentiment": c_sentiment,
                        })

                posts.append({
                    "source":       f"reddit/r/{subreddit_name}",
                    "title":        post.title,
                    "text":         body[:1500],
                    "score":        post.score,
                    "num_comments": post.num_comments,
                    "sentiment":    sentiment,
                    "comments":     comments,
                    "url":          f"https://reddit.com{post.permalink}",
                    "created_utc":  post.created_utc,
                    "year":         datetime.utcfromtimestamp(post.created_utc).year,
                })
        except Exception as e:
            print(f"  [reddit] Error on r/{subreddit_name}: {e}")

    return posts


def run(year: int = None, output_path: str = None) -> list:
    if not REDDIT_CLIENT_ID or REDDIT_CLIENT_ID == "your_client_id_here":
        print("[reddit] No API credentials — skipping.")
        return []

    year_label = f" [{year}]" if year else ""
    print(f"\n[reddit]{year_label} Scraping {len(SUBREDDITS)} subreddits...")

    reddit    = get_reddit_client()
    sia       = SentimentIntensityAnalyzer()
    all_posts = []

    for sub in tqdm(SUBREDDITS, desc=f"Reddit{year_label}"):
        posts = scrape_subreddit(reddit, sub, sia, year=year)
        all_posts.extend(posts)
        time.sleep(1)

    print(f"  → Collected {len(all_posts)} posts{' for ' + str(year) if year else ''}")

    out_dir = get_year_dir(year) if year else DATA_DIR
    os.makedirs(out_dir, exist_ok=True)
    path = output_path or os.path.join(out_dir, "reddit_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, indent=2, ensure_ascii=False)
    print(f"  → Saved to {path}")

    return all_posts


if __name__ == "__main__":
    run()
