"""
Source aggregator for Pages 1 and 2.

Replaces the Reddit-only scraper with a multi-source pipeline.
Pulls from:
  - Hacker News (always live, free public API)
  - GitHub Trending AI/ML repos (always live, free public API)
  - arXiv top papers (already pulled by arxiv_analyzer for Page 4 — we
    surface the top 5 here as Page 1 stories)
  - Reddit (mock until API approved; auto-activates with REDDIT_MODE=live)

The aggregator returns a deduplicated list in the SAME shape as the
old scraper.py returned, so analyzer.score_story() works unchanged.

Backward-compatible API:
  scrape_all_subreddits() → kept as alias for scrape_all_sources()
                            so existing main.py imports don't break.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from src.sources import hn, github_trending, arxiv_stories, reddit


def scrape_all_sources(arxiv_top_papers: Optional[List[Dict]] = None) -> List[Dict]:
    """Aggregate posts from every active source.

    Args:
        arxiv_top_papers: pre-computed top-papers list from arxiv_analyzer.
                          If provided, top 5 surface as Page 1 stories.
                          If None, arXiv contributes nothing here.

    Returns: deduplicated list of post dicts in shared schema.
    """
    print("\nAggregating sources for Pages 1 & 2...")

    posts: List[Dict] = []
    seen_ids: set = set()
    counts: Dict[str, int] = {}

    def _add_posts(source_name: str, source_posts: List[Dict]) -> None:
        added = 0
        for p in source_posts:
            pid = p.get("id")
            if not pid or pid in seen_ids:
                continue
            seen_ids.add(pid)
            posts.append(p)
            added += 1
        counts[source_name] = added

    # 1. Hacker News
    try:
        hn_posts = hn.fetch_ai_stories(max_stories=30, scan_top_n=200)
        _add_posts("Hacker News", hn_posts)
    except Exception as exc:
        print(f"    HN fetch failed: {exc}")
        counts["Hacker News"] = 0

    # 2. GitHub Trending
    try:
        gh_posts = github_trending.fetch_trending_repos(max_repos=8)
        _add_posts("GitHub Trending", gh_posts)
    except Exception as exc:
        print(f"    GitHub fetch failed: {exc}")
        counts["GitHub Trending"] = 0

    # 3. arXiv (surface top papers)
    if arxiv_top_papers:
        try:
            ax_posts = arxiv_stories.papers_to_stories(arxiv_top_papers, max_stories=5)
            _add_posts("arXiv", ax_posts)
        except Exception as exc:
            print(f"    arXiv stories conversion failed: {exc}")
            counts["arXiv"] = 0
    else:
        counts["arXiv"] = 0

    # 4. Reddit (mock for now, live when API approved)
    try:
        rd_posts = reddit.fetch_all_reddit_posts()
        _add_posts("Reddit", rd_posts)
    except Exception as exc:
        print(f"    Reddit fetch failed: {exc}")
        counts["Reddit"] = 0

    summary = " · ".join(f"{name}: {n}" for name, n in counts.items())
    print(f"  Aggregated {len(posts)} unique posts ({summary})\n")
    return posts


# Backward-compat alias so existing main.py continues to work
def scrape_all_subreddits() -> List[Dict]:
    """Deprecated alias for scrape_all_sources() — kept for backward compat.

    main.py will be updated to call scrape_all_sources() directly with
    the arxiv_top_papers argument so arXiv content surfaces on Page 1.
    """
    return scrape_all_sources(arxiv_top_papers=None)


if __name__ == "__main__":
    posts = scrape_all_sources()
    print(f"\nTotal: {len(posts)} posts")
    if posts:
        print(f"Sample: {posts[0]['title']} ({posts[0]['source']})")
