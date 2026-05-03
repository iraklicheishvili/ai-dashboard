"""
Thin wrapper that surfaces arXiv papers as Page 1 stories.

The arXiv pipeline (arxiv_scraper.py + arxiv_analyzer.py) already pulls
recent papers and scores them for Page 4. This module reuses those
results so high-relevance papers also appear on the Page 1 main feed
without paying for a second pass.

Strategy:
  - On Page 1's daily run, after arXiv has been analyzed
  - Take the top N papers (default 5) by Haiku score
  - Convert to the shared post schema so analyzer.score_story() can
    re-score them in the unified Page 1 ranking pass
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional


def papers_to_stories(top_papers: List[Dict], max_stories: int = 5) -> List[Dict]:
    """Convert arXiv 'top_papers' entries into Page 1 post dicts.

    `top_papers` is the list arxiv_analyzer.analyze_arxiv_papers() builds
    for Page 4 — each item already has title, plain_summary, score, url, etc.
    We map those onto the shared scraper schema.

    Returns at most `max_stories` posts, sorted by arXiv score desc.
    """
    if not top_papers:
        return []

    # Defensive sort by score (the Page 4 list is usually already sorted,
    # but we don't want to rely on it)
    sorted_papers = sorted(
        top_papers,
        key=lambda p: float(p.get("score") or 0),
        reverse=True,
    )

    posts: List[Dict] = []
    for paper in sorted_papers[:max_stories]:
        post = _paper_to_post(paper)
        if post:
            posts.append(post)

    return posts


def _paper_to_post(paper: Dict) -> Optional[Dict]:
    """Convert one arXiv paper dict to the shared post schema."""
    title = paper.get("title", "")
    if not title:
        return None

    arxiv_id = paper.get("arxiv_id") or ""
    score_raw = paper.get("score") or 0
    try:
        arxiv_score = float(score_raw)
    except (TypeError, ValueError):
        arxiv_score = 0.0

    url = paper.get("url") or ""
    summary = paper.get("plain_summary") or paper.get("summary") or ""
    institution = paper.get("institution") or ""
    team = paper.get("team") or ""

    # Build a date string for created_iso — best-effort
    date_str = paper.get("date") or ""  # e.g. "Apr 30, 2026"
    created_iso = ""
    try:
        if date_str:
            dt = datetime.strptime(date_str, "%b %d, %Y")
            created_iso = dt.replace(tzinfo=timezone.utc).isoformat()
    except (ValueError, TypeError):
        pass

    # Map arXiv score (1-10) to a Reddit-like "score" (upvotes equivalent)
    # so the unified ranking treats it sensibly. arXiv 8.5 → ~85 upvotes.
    pseudo_upvotes = int(arxiv_score * 10)

    # Build a meaningful subtitle: institution / authors
    selftext_parts = []
    if institution:
        selftext_parts.append(f"Institution: {institution}")
    if team:
        selftext_parts.append(f"Authors: {team}")
    selftext_parts.append(summary)
    selftext = "\n".join(selftext_parts)

    return {
        "id": f"arxiv_{arxiv_id}" if arxiv_id else f"arxiv_{hash(title) & 0xffffffff:x}",
        "source": "arXiv",
        "title": title,
        "subreddit": "arXiv",  # backward compat for analyzer
        "url": url,
        "external_url": url,
        "score": pseudo_upvotes,
        "num_comments": 0,
        "created_utc": 0,
        "created_iso": created_iso,
        "author": team or "arXiv contributors",
        "selftext": selftext[:2000],
        "is_video": False,
        # arXiv-specific extras for richer rendering on Page 1
        "arxiv_score": arxiv_score,
        "arxiv_id": arxiv_id,
        "arxiv_institution": institution,
    }
