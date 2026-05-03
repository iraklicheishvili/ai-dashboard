"""
Reddit source — strict mode policy.

Default behavior: Reddit contributes NOTHING (returns empty list).
This prevents mock data from ever leaking into the live dashboard.

Activation modes (set REDDIT_MODE in .env):
  - REDDIT_MODE=live   → Real Reddit via PRAW (requires valid credentials)
  - REDDIT_MODE=mock   → Mock data (local testing only, never on production)
  - (unset / anything else) → Returns []  ← THE DEFAULT

When Reddit API approval comes through, set REDDIT_MODE=live in GitHub
Secrets and on local .env. No code changes needed — Reddit will start
contributing posts automatically and the footer disclaimer will update
to include "Reddit" in the source list.

Output schema mirrors hn.py and github_trending.py so the aggregator
in scraper.py treats Reddit as just another source when it's active.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, List

import praw
from dotenv import load_dotenv

import config

load_dotenv()


def get_mode() -> str:
    """Return the current Reddit mode: 'live', 'mock', or 'off'.

    'off' is the default and means Reddit contributes nothing.
    """
    mode = os.environ.get("REDDIT_MODE", "").strip().lower()
    if mode == "live":
        return "live"
    if mode == "mock":
        return "mock"
    return "off"


def is_live_mode() -> bool:
    """Backward-compat helper — true only when explicitly REDDIT_MODE=live."""
    return get_mode() == "live"


def _get_client() -> praw.Reddit:
    """Build authenticated PRAW client."""
    return praw.Reddit(
        client_id=os.environ.get("REDDIT_CLIENT_ID"),
        client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
        user_agent=os.environ.get("REDDIT_USER_AGENT", "ai-dashboard/1.0"),
    )


def _submission_to_post(submission, subreddit_name: str) -> Dict:
    """Convert a PRAW submission to the shared post schema."""
    return {
        "id": f"rd_{submission.id}",
        "source": "Reddit",
        "title": submission.title,
        "subreddit": f"r/{subreddit_name}",
        "url": f"https://reddit.com{submission.permalink}",
        "external_url": submission.url if not submission.is_self else None,
        "score": int(submission.score or 0),
        "num_comments": int(submission.num_comments or 0),
        "created_utc": float(submission.created_utc or 0),
        "created_iso": (
            datetime.fromtimestamp(submission.created_utc, tz=timezone.utc).isoformat()
            if submission.created_utc
            else ""
        ),
        "author": str(submission.author) if submission.author else "[deleted]",
        "selftext": submission.selftext[:2000] if submission.is_self else "",
        "is_video": bool(submission.is_video),
    }


def fetch_subreddit_posts(reddit: praw.Reddit, subreddit_name: str) -> List[Dict]:
    """Fetch top posts from one subreddit within configured time window."""
    posts: List[Dict] = []
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
            posts.append(_submission_to_post(submission, subreddit_name))
    except Exception as exc:
        print(f"    error fetching r/{subreddit_name}: {exc}")
    return posts


def fetch_all_reddit_posts() -> List[Dict]:
    """Aggregate posts based on the configured Reddit mode.

    Default behavior (no env var or anything other than 'live'/'mock'):
    returns empty list. This ensures mock data NEVER reaches the live
    dashboard by accident.
    """
    mode = get_mode()

    if mode == "off":
        print("  Reddit: disabled (set REDDIT_MODE=live when API is approved)")
        return []

    if mode == "mock":
        print("  Reddit: mock mode (LOCAL TESTING ONLY — should not be used in production)")
        from src.mock_data import get_mock_posts
        posts = get_mock_posts()
        # Normalize mock data to the shared schema format
        for p in posts:
            if "source" not in p:
                p["source"] = "Reddit"
            if "id" in p and not p["id"].startswith("rd_"):
                p["id"] = f"rd_{p['id']}"
        print(f"    {len(posts)} mock posts loaded")
        return posts

    # live mode
    print(f"  Reddit: live mode — scraping {len(config.ALL_SUBREDDITS)} subreddits")
    try:
        reddit = _get_client()
    except Exception as exc:
        print(f"    Reddit client init failed: {exc}")
        return []

    seen_ids: set = set()
    all_posts: List[Dict] = []

    for sub in config.ALL_SUBREDDITS:
        posts = fetch_subreddit_posts(reddit, sub)
        new_posts = [p for p in posts if p["id"] not in seen_ids]
        seen_ids.update(p["id"] for p in new_posts)
        all_posts.extend(new_posts)

    print(f"    {len(all_posts)} unique posts across all subreddits")
    return all_posts
