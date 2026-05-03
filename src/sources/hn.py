"""
Hacker News source fetcher for Pages 1 and 2.

Uses HN's free Firebase API (https://github.com/HackerNews/API):
  - /v0/topstories.json    → top story IDs
  - /v0/item/{id}.json     → individual story or comment

No authentication required. We pull recent items, filter for AI/ML
keywords, and return them in the same dict shape as the existing
Reddit scraper so the analyzer doesn't need to change.

Functions:
  fetch_ai_stories()   → list of curated AI/ML stories (Page 1 feed)
  fetch_model_mentions(model_keywords, hours_back) → stories+comments
                                                     mentioning a model
                                                     (Page 2 sentiment)
"""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Optional

USER_AGENT = "ai-dashboard/1.0 (https://github.com/iraklicheishvili/ai-dashboard)"
HN_BASE = "https://hacker-news.firebaseio.com/v0"
HN_ITEM_URL = "https://news.ycombinator.com/item?id={id}"
TIMEOUT_SECONDS = 10

# Words that strongly suggest an AI/ML story
AI_KEYWORDS = [
    # General
    "ai", "a.i.", "llm", "ml", "machine learning", "artificial intelligence",
    "neural", "transformer", "deep learning",
    # Models & makers
    "gpt", "chatgpt", "claude", "anthropic", "openai", "gemini", "deepmind",
    "deepseek", "grok", "xai", "llama", "meta ai", "mistral", "copilot",
    "perplexity", "cohere",
    # Concepts
    "agent", "agentic", "rag", "fine-tune", "fine tuning", "embedding",
    "diffusion", "multimodal", "reasoning model", "alignment", "safety",
    # Tooling
    "huggingface", "hugging face", "ollama", "lmsys", "lm studio",
    "langchain", "llamaindex",
]


def _fetch_json(url: str, timeout: int = TIMEOUT_SECONDS) -> Optional[dict]:
    """GET a URL and parse JSON. Returns None on any failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, Exception):
        return None


def _fetch_item(item_id: int) -> Optional[dict]:
    """Fetch a single HN item (story or comment) by ID."""
    return _fetch_json(f"{HN_BASE}/item/{item_id}.json")


def _looks_like_ai(title: str, text: str = "") -> bool:
    """Heuristic check whether a story is AI/ML-related."""
    if not title:
        return False
    haystack = (title + " " + (text or "")).lower()
    return any(kw in haystack for kw in AI_KEYWORDS)


def _hn_to_post(item: dict) -> Optional[Dict]:
    """Convert an HN item dict to the shared post schema used by analyzer.

    The shared schema mirrors what scraper.py returns for Reddit posts so
    the existing analyzer.score_story() works unchanged.
    """
    if not item or item.get("type") != "story" or item.get("dead") or item.get("deleted"):
        return None

    title = item.get("title") or ""
    if not title:
        return None

    item_id = item.get("id")
    score = int(item.get("score") or 0)
    descendants = int(item.get("descendants") or 0)  # comment count
    created_ts = float(item.get("time") or 0)
    author = item.get("by") or "[unknown]"

    # HN stories may be link-posts (url) or text-posts (text)
    external_url = item.get("url") or None
    selftext = item.get("text") or ""
    # Strip basic HTML — HN text posts include some HTML tags
    if selftext:
        selftext = (
            selftext.replace("<p>", "\n")
            .replace("</p>", "")
            .replace("&#x27;", "'")
            .replace("&quot;", '"')
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
        )

    created_iso = (
        datetime.fromtimestamp(created_ts, tz=timezone.utc).isoformat()
        if created_ts
        else ""
    )

    return {
        "id": f"hn_{item_id}",
        "source": "Hacker News",
        "title": title,
        "subreddit": "Hacker News",  # Kept for analyzer.py backward compat
        "url": HN_ITEM_URL.format(id=item_id),  # HN discussion thread
        "external_url": external_url,           # Original article (if link post)
        "score": score,
        "num_comments": descendants,
        "created_utc": created_ts,
        "created_iso": created_iso,
        "author": author,
        "selftext": selftext[:2000] if selftext else "",
        "is_video": False,
    }


def fetch_ai_stories(max_stories: int = 30, scan_top_n: int = 200) -> List[Dict]:
    """Fetch recent AI/ML stories from HN top stories.

    Args:
        max_stories: cap on returned stories (default 30 — analyzer scores them all)
        scan_top_n: how many top story IDs to inspect (default 200 — wide funnel)

    Returns: list of post dicts in the shared schema, sorted by score desc.
    """
    print(f"  Fetching HN top story IDs (scanning top {scan_top_n})...")
    top_ids = _fetch_json(f"{HN_BASE}/topstories.json")
    if not top_ids or not isinstance(top_ids, list):
        print("    HN top stories fetch failed — returning empty")
        return []

    candidates = top_ids[:scan_top_n]
    posts: List[Dict] = []
    inspected = 0

    for item_id in candidates:
        if len(posts) >= max_stories:
            break
        inspected += 1

        item = _fetch_item(item_id)
        if not item:
            continue

        title = item.get("title", "")
        text = item.get("text", "")
        if not _looks_like_ai(title, text):
            continue

        post = _hn_to_post(item)
        if post:
            posts.append(post)

        # Polite throttle — HN API is generous but no need to hammer
        if inspected % 25 == 0:
            time.sleep(0.5)

    posts.sort(key=lambda p: p["score"], reverse=True)
    print(f"    {len(posts)} AI/ML stories from {inspected} inspected")
    return posts


def _fetch_comment_tree(item_id: int, max_comments: int = 30) -> List[str]:
    """Fetch up to max_comments top-level comment texts from a story.

    Used for per-model sentiment analysis on Page 2.
    Strips deleted/dead comments and basic HTML.
    """
    item = _fetch_item(item_id)
    if not item:
        return []

    kid_ids = item.get("kids") or []
    comments: List[str] = []

    for kid_id in kid_ids[:max_comments]:
        kid = _fetch_item(kid_id)
        if not kid or kid.get("dead") or kid.get("deleted"):
            continue
        text = kid.get("text") or ""
        if not text or len(text) < 30:
            continue
        # Strip basic HTML
        text = (
            text.replace("<p>", "\n")
            .replace("</p>", "")
            .replace("&#x27;", "'")
            .replace("&quot;", '"')
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
        )
        comments.append(text[:1000])

    return comments


def fetch_model_mentions(
    model_keywords: List[str],
    hours_back: int = 72,
    max_stories: int = 10,
) -> Dict:
    """Fetch HN stories+comments mentioning a specific model (last N hours).

    Used for Page 2 per-model sentiment scoring (Component 2.1).
    The default 72-hour window matches the "last 3 days" sentiment design.

    Returns: dict with 'stories' (list of post dicts with 'comments' attached)
             and 'comment_count' (total comments harvested across all stories).
    """
    if not model_keywords:
        return {"stories": [], "comment_count": 0}

    keywords_lower = [k.lower() for k in model_keywords]
    cutoff_ts = time.time() - (hours_back * 3600)

    top_ids = _fetch_json(f"{HN_BASE}/topstories.json") or []
    new_ids = _fetch_json(f"{HN_BASE}/newstories.json") or []
    # De-duplicate while preserving order
    candidate_ids = list(dict.fromkeys(list(top_ids[:300]) + list(new_ids[:100])))

    matching: List[Dict] = []
    inspected = 0

    for item_id in candidate_ids:
        if len(matching) >= max_stories:
            break
        inspected += 1

        item = _fetch_item(item_id)
        if not item:
            continue
        if item.get("type") != "story":
            continue
        if (item.get("time") or 0) < cutoff_ts:
            continue

        title = (item.get("title") or "").lower()
        text = (item.get("text") or "").lower()
        haystack = title + " " + text

        if not any(kw in haystack for kw in keywords_lower):
            continue

        post = _hn_to_post(item)
        if not post:
            continue

        # Pull top comments for sentiment scoring
        post["comments"] = _fetch_comment_tree(item_id, max_comments=20)
        matching.append(post)

        if inspected % 25 == 0:
            time.sleep(0.5)

    total_comments = sum(len(s.get("comments", [])) for s in matching)
    return {"stories": matching, "comment_count": total_comments}


if __name__ == "__main__":
    # Manual sanity check
    stories = fetch_ai_stories(max_stories=5, scan_top_n=50)
    print(f"\nGot {len(stories)} AI/ML stories")
    for s in stories[:3]:
        print(f"  [{s['score']} pts | {s['num_comments']} comments] {s['title'][:80]}")
