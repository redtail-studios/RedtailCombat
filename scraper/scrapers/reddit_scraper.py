"""
reddit_scraper.py
Scrapes posts and comments from gaming subreddits using PRAW.
Requires free Reddit API credentials in .env
"""
import json, time, os
import praw
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from tqdm import tqdm
from config import (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT,
                    SUBREDDITS, REDDIT_KEYWORDS, REDDIT_POST_LIMIT,
                    REDDIT_COMMENT_LIMIT, DATA_DIR)


def get_reddit_client():
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )


def scrape_subreddit(reddit, subreddit_name: str, sia: SentimentIntensityAnalyzer) -> list:
    """Scrape hot + top posts from one subreddit."""
    posts = []
    sub = reddit.subreddit(subreddit_name)

    # Pull from both hot and top (week) to get breadth
    streams = [
        sub.hot(limit=REDDIT_POST_LIMIT // 2),
        sub.top("week", limit=REDDIT_POST_LIMIT // 2),
    ]

    for stream in streams:
        try:
            for post in stream:
                # Skip non-text or very short posts
                body = (post.selftext or "").strip()
                full_text = post.title + " " + body

                sentiment = sia.polarity_scores(full_text[:1000])

                # Grab top N comments
                post.comments.replace_more(limit=0)
                comments = []
                for comment in post.comments[:REDDIT_COMMENT_LIMIT]:
                    if hasattr(comment, "body") and len(comment.body) > 20:
                        c_sentiment = sia.polarity_scores(comment.body[:500])
                        comments.append({
                            "body": comment.body[:500],
                            "score": comment.score,
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
                })
        except Exception as e:
            print(f"  [reddit] Error on r/{subreddit_name}: {e}")

    return posts


def run(output_path: str = None) -> list:
    """Main entry point. Returns list of posts and saves to JSON."""
    if not REDDIT_CLIENT_ID or REDDIT_CLIENT_ID == "your_client_id_here":
        print("[reddit] No API credentials found — skipping Reddit scrape.")
        print("  → Get free credentials at: reddit.com/prefs/apps")
        return []

    print(f"\n[reddit] Scraping {len(SUBREDDITS)} subreddits...")
    reddit = get_reddit_client()
    sia    = SentimentIntensityAnalyzer()
    all_posts = []

    for sub in tqdm(SUBREDDITS, desc="Subreddits"):
        posts = scrape_subreddit(reddit, sub, sia)
        all_posts.extend(posts)
        time.sleep(1)  # Be polite to Reddit's servers

    print(f"  → Collected {len(all_posts)} posts total")

    # Save
    os.makedirs(DATA_DIR, exist_ok=True)
    path = output_path or os.path.join(DATA_DIR, "reddit_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, indent=2, ensure_ascii=False)
    print(f"  → Saved to {path}")

    return all_posts


if __name__ == "__main__":
    run()
