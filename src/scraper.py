"""
Reddit scraper using PRAW.
Pulls top posts from each tracked subreddit within the configured time window.

Falls back to mock data if Reddit credentials are still placeholders
(useful while waiting for Reddit API approval).
"""

import os
from datetime import datetime, timezone
from typing import List, Dict
import praw
from dotenv import load_dotenv

import config

load_dotenv()


def _is_mock_mode() -> bool:
    """Check whether Reddit credentials are still placeholder values."""
    client_id = os.getenv("REDDIT_CLIENT_ID", "")
    return client_id in ("", "your_reddit_client_id") or client_id.startswith("your_")


def get_reddit_client() -> praw.Reddit:
    """Create authenticated Reddit client from env vars."""
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "ai-dashboard/1.0"),
    )


def fetch_subreddit_posts(reddit: praw.Reddit, subreddit_name: str) -> List[Dict]:
    """
    Fetch top posts from a subreddit within the time filter.
    Returns a list of post dicts ready for analysis.
    """
    posts = []
    try:
        subreddit = reddit.subreddit(subreddit_name)
        for submission in subreddit.top(
            time_filter=config.POST_TIME_FILTER,
            limit=config.POSTS_PER_SUBREDDIT,
        ):
            if submission.score < config.MIN_REDDIT_SCORE:
                continue
            if submission.stickied:
                continue

            posts.append({
                "id": submission.id,
                "title": submission.title,
                "subreddit": f"r/{subreddit_name}",
                "url": f"https://reddit.com{submission.permalink}",
                "external_url": submission.url if not submission.is_self else None,
                "score": submission.score,
                "num_comments": submission.num_comments,
                "created_utc": submission.created_utc,
                "created_iso": datetime.fromtimestamp(
                    submission.created_utc, tz=timezone.utc
                ).isoformat(),
                "author": str(submission.author) if submission.author else "[deleted]",
                "selftext": submission.selftext[:2000] if submission.is_self else "",
                "is_video": submission.is_video,
            })
    except Exception as e:
        print(f"  ! Error fetching r/{subreddit_name}: {e}")

    return posts


def scrape_all_subreddits() -> List[Dict]:
    """
    Iterate every tracked subreddit and aggregate posts.
    Deduplicates by post ID.

    If Reddit credentials are placeholders, returns mock data instead.
    """
    if _is_mock_mode():
        print("Reddit credentials are placeholder values — using mock data.")
        print("(Once your Reddit app is approved, fill in .env and real scraping will resume automatically.)\n")
        from src.mock_data import get_mock_posts
        posts = get_mock_posts()
        print(f"Loaded {len(posts)} mock posts.\n")
        return posts

    print(f"Scraping {len(config.ALL_SUBREDDITS)} subreddits...")
    reddit = get_reddit_client()

    all_posts = []
    seen_ids = set()

    for sub in config.ALL_SUBREDDITS:
        posts = fetch_subreddit_posts(reddit, sub)
        new_posts = [p for p in posts if p["id"] not in seen_ids]
        seen_ids.update(p["id"] for p in new_posts)
        all_posts.extend(new_posts)
        print(f"  r/{sub}: {len(new_posts)} posts")

    print(f"Total unique posts collected: {len(all_posts)}\n")
    return all_posts


if __name__ == "__main__":
    posts = scrape_all_subreddits()
    print(f"\nSample post:")
    if posts:
        print(f"  Title: {posts[0]['title']}")
        print(f"  Subreddit: {posts[0]['subreddit']}")
        print(f"  Score: {posts[0]['score']}")