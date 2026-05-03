"""
GitHub source for Pages 1 and 2.

Two distinct uses:

  1. Page 1 — fetch_trending_repos()
     Trending AI/ML repos as Page 1 stories. Since GitHub deprecated
     their public trending API, we use a workaround: search recently
     pushed repos with AI/ML topic tags, ranked by stars.

  2. Page 2 — fetch_model_stars_today()
     Per-model star counts (added today) across each model's official
     ecosystem repos. Feeds the Page 2 "GitHub" toggle on the sentiment
     trend chart (Component 2.2).

Both use GitHub's public REST API (free, no auth needed for low volume,
but anonymous requests share a 60/hour rate limit per IP).

If the user later sets a GITHUB_TOKEN env var, we use it automatically
to bump the rate limit to 5000/hour. Optional, not required.
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

USER_AGENT = "ai-dashboard/1.0 (https://github.com/iraklicheishvili/ai-dashboard)"
GITHUB_API = "https://api.github.com"
TIMEOUT_SECONDS = 12

# AI/ML topic tags to search for trending repos
AI_TOPICS = [
    "llm",
    "large-language-models",
    "ai-agents",
    "generative-ai",
    "machine-learning",
    "deep-learning",
    "transformers",
]


def _build_headers() -> Dict[str, str]:
    """Build request headers — include token if available for higher rate limit."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_json(url: str) -> Optional[dict]:
    """GET a URL and parse JSON. Returns None on any failure."""
    try:
        req = urllib.request.Request(url, headers=_build_headers())
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            print(f"    GitHub rate limit hit (403) — set GITHUB_TOKEN to bump to 5000/hour")
        elif exc.code == 404:
            pass  # Repo doesn't exist; benign
        else:
            print(f"    GitHub API error {exc.code} on {url[:60]}")
        return None
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, Exception):
        return None


def _repo_to_post(repo: dict, stars_today: int = 0) -> Dict:
    """Convert a GitHub repo dict to the shared post schema.

    Same shape as scraper.py / hn.py — analyzer.score_story() works unchanged.
    """
    full_name = repo.get("full_name", "")
    description = repo.get("description") or ""
    stars = int(repo.get("stargazers_count") or 0)
    pushed_at = repo.get("pushed_at", "")
    html_url = repo.get("html_url", "")
    language = repo.get("language") or "—"

    # Use stars-today if available (proxy for "score"), else total stars / 100
    score = stars_today if stars_today else max(1, stars // 100)

    return {
        "id": f"gh_{full_name.replace('/', '_')}",
        "source": "GitHub Trending",
        "title": full_name,
        "subreddit": "GitHub Trending",  # backward compat
        "url": html_url,
        "external_url": html_url,
        "score": score,
        "num_comments": 0,  # GitHub doesn't have a comment count we use
        "created_utc": 0,
        "created_iso": pushed_at,
        "author": repo.get("owner", {}).get("login", "[unknown]"),
        "selftext": f"{description}\n\nLanguage: {language} · Stars: {stars}",
        "is_video": False,
        # GitHub-specific extras for richer rendering on Page 1
        "github_stars_total": stars,
        "github_stars_today": stars_today,
        "github_language": language,
    }


def fetch_trending_repos(max_repos: int = 8) -> List[Dict]:
    """Fetch trending AI/ML repos from GitHub.

    Strategy: GitHub's search API doesn't support OR across topic: filters,
    so we run one search per topic and merge results, deduplicating by repo
    full_name. Each topic search returns highest-starred repos pushed in
    the last 7 days, sorted by stars desc.

    Returns: list of post dicts in shared schema.
    """
    print(f"  Fetching GitHub trending AI/ML repos...")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

    # Per-topic search; merge + dedupe
    seen_repos: set = set()
    all_repos: List[Dict] = []
    per_topic_cap = max(max_repos, 5)

    for topic in AI_TOPICS:
        query = f"topic:{topic} pushed:>{cutoff}"
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": per_topic_cap,
        }
        url = f"{GITHUB_API}/search/repositories?{urllib.parse.urlencode(params)}"

        data = _fetch_json(url)
        if not data:
            continue

        items = data.get("items") or []
        for repo in items:
            full_name = repo.get("full_name", "")
            if not full_name or full_name in seen_repos:
                continue
            if repo.get("fork"):
                continue
            if int(repo.get("stargazers_count") or 0) < 50:
                continue
            seen_repos.add(full_name)
            all_repos.append(repo)

        # Polite pause between searches (anonymous GH search rate limit
        # is 10 requests/minute — 7 topics × ~0.5s = ~3.5s, well under)
        time.sleep(0.3)

    # Sort the merged result globally by stars desc, then take top N
    all_repos.sort(
        key=lambda r: int(r.get("stargazers_count") or 0),
        reverse=True,
    )

    posts: List[Dict] = []
    for repo in all_repos[:max_repos]:
        post = _repo_to_post(repo)
        posts.append(post)

    print(f"    {len(posts)} trending AI/ML repos (from {len(all_repos)} unique candidates)")
    return posts


def fetch_repo_stars(repo_full_name: str) -> Optional[int]:
    """Fetch current total star count for a single repo.

    Used by Page 2 — we call this for each model's ecosystem repos and
    diff against the prior day's count to compute "stars added today".
    """
    if not repo_full_name or "/" not in repo_full_name:
        return None
    url = f"{GITHUB_API}/repos/{urllib.parse.quote(repo_full_name)}"
    data = _fetch_json(url)
    if not data:
        return None
    return int(data.get("stargazers_count") or 0)


def fetch_model_stars_today(
    model_repos: Dict[str, List[str]],
    prior_day_stars: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    """Fetch combined star counts across each model's ecosystem repos.

    Args:
        model_repos: {"Claude": ["anthropics/anthropic-sdk-python", ...], ...}
        prior_day_stars: Yesterday's total per model — used to compute delta.
                         Pass None on first day; result will be all zeros.

    Returns: {"Claude": 245, "ChatGPT": 187, ...} — stars added since yesterday.

    On rate limit or failure, returns 0 for the affected model rather than
    raising — keeps the daily pipeline from breaking on a transient issue.
    """
    print(f"  Fetching GitHub star totals for {len(model_repos)} models...")
    prior = prior_day_stars or {}
    today_totals: Dict[str, int] = {}
    today_deltas: Dict[str, int] = {}

    for model_name, repos in model_repos.items():
        if not repos:
            today_totals[model_name] = 0
            today_deltas[model_name] = 0
            continue

        total = 0
        ok_count = 0
        for repo in repos:
            stars = fetch_repo_stars(repo)
            if stars is not None:
                total += stars
                ok_count += 1
            time.sleep(0.3)  # polite — keep under rate limit

        today_totals[model_name] = total
        prior_total = int(prior.get(model_name) or 0)
        delta = max(0, total - prior_total) if prior_total else 0
        today_deltas[model_name] = delta

        print(f"    {model_name}: {total} total stars ({ok_count}/{len(repos)} repos OK, +{delta} today)")

    # Return both — caller decides which to persist
    return {"totals": today_totals, "deltas": today_deltas}


if __name__ == "__main__":
    # Manual sanity check
    repos = fetch_trending_repos(max_repos=5)
    print(f"\nGot {len(repos)} trending repos")
    for r in repos[:3]:
        print(f"  [{r['github_stars_total']} stars | {r['github_language']}] {r['title']}")
