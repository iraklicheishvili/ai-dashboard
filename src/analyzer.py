"""
Claude API analyzer for Pages 1 and 2.

Two-pass approach (unchanged from original design):
  Pass 1: Haiku 4.5 scores and tags every story (cheap, fast, scalable).
  Pass 2: Opus / Sonnet synthesizes the curated set into narrative + insights.

Source-agnostic scoring (NEW):
  - Haiku scores ONLY content quality on a 1-10 scale (rubric in prompt)
  - Per-source engagement signals are normalized to [0, 1]
  - Combined ranking: final = (content * 0.85) + (engagement_norm * 1.5)
  - This prevents HN's larger raw vote counts from drowning out arXiv papers
    or GitHub repos in the top-15 selection

Per-model sentiment (UPDATED):
  - Pulls HN comments via sources/hn.fetch_model_mentions()
  - Haiku classifies each comment as positive/negative/neutral
  - Aggregates into the existing sentiment dict shape so render.py
    works unchanged
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from anthropic import Anthropic
from dotenv import load_dotenv

import config
from src.sources import hn as hn_source
from src.utils.json_extract import extract_json
from src.utils.throttle import haiku_call, sonnet_call

load_dotenv()

_client: Optional[Anthropic] = None


def get_client() -> Anthropic:
    """Lazy-initialise the shared Anthropic client."""
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _client


def load_prompt(name: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    path = Path(__file__).parent.parent / "prompts" / f"{name}.txt"
    return path.read_text(encoding="utf-8")


# ============================================================
# Engagement normalization — per-source scaling
# ============================================================

def _normalize_engagement(post: Dict) -> float:
    """Normalize a post's engagement signal to [0, 1] within its source.

    Different sources have wildly different raw scales:
      - HN top stories: 50-2000 points
      - GitHub trending: 50-50000 stars
      - arXiv: no engagement signal (use a fixed 0.7 — they're all peer-like)
      - Reddit: 50-3000 upvotes

    This prevents the combined ranking from being biased toward whichever
    source produces the largest raw numbers.
    """
    source = post.get("source", "")
    score = float(post.get("score") or 0)

    if source == "Hacker News":
        return min(score / 1000.0, 1.0)
    if source == "GitHub Trending":
        # Use total stars (more stable signal than raw "score")
        total = float(post.get("github_stars_total") or score * 100)
        return min(total / 50000.0, 1.0)
    if source == "arXiv":
        # No engagement signal; trust the relevance threshold filter
        return 0.7
    if source == "Reddit":
        return min(score / 1500.0, 1.0)
    # Unknown source — assume mid-tier signal
    return 0.5


def _combined_score(content_score: float, engagement_norm: float) -> float:
    """Weighted combination: content dominates, engagement nudges ties."""
    return (content_score * 0.85) + (engagement_norm * 1.5)


# ============================================================
# Pass 1 — per-story content scoring (Haiku)
# ============================================================

def score_story(post: Dict) -> Optional[Dict]:
    """Score one story for content relevance via Haiku.

    Returns the merged post + analysis dict, or None on failure.
    Adds: relevance_score, category_tags, model_mentioned, is_fintech,
          summary, reasoning, engagement_norm, combined_score.
    """
    template = load_prompt("score_story")
    selftext = (post.get("selftext") or "")[:1500] or "(no body text)"
    external_url = post.get("external_url") or "(none)"

    prompt = (
        template
        .replace("{title}", str(post.get("title", "")))
        .replace("{source}", str(post.get("source", "Unknown")))
        .replace("{subreddit}", str(post.get("subreddit", "")))  # backward compat
        .replace("{score}", str(post.get("score", 0)))
        .replace("{num_comments}", str(post.get("num_comments", 0)))
        .replace("{selftext}", selftext)
        .replace("{external_url}", external_url)
    )

    try:
        text = haiku_call(get_client(), prompt, model=config.HAIKU_MODEL, max_tokens=400)
        analysis = extract_json(text) or {}
    except Exception as exc:
        print(f"    score failed for '{post.get('title','')[:60]}': {exc}")
        return None

    if not isinstance(analysis, dict):
        return None

    content_score = float(analysis.get("relevance_score") or 0)
    engagement_norm = _normalize_engagement(post)
    combined = _combined_score(content_score, engagement_norm)

    return {
        **post,
        "relevance_score": content_score,
        "engagement_norm": round(engagement_norm, 3),
        "combined_score": round(combined, 3),
        "category_tags": analysis.get("category_tags") or [],
        "model_mentioned": analysis.get("model_mentioned"),
        "is_fintech": bool(analysis.get("is_fintech")),
        "summary": analysis.get("summary") or "",
        "reasoning": analysis.get("reasoning") or "",
    }


def score_all_stories(posts: List[Dict]) -> List[Dict]:
    """Score every post via Haiku, then return adaptive top-15.

    Adaptive top-15: returns the highest-ranked 15 stories regardless of
    threshold so the Page 1 feed is always full. We log how many crossed
    the relevance threshold separately for visibility.
    """
    if not posts:
        print("Story scoring — no posts to score")
        return []

    print(f"Story scoring — {len(posts)} candidates via Haiku")
    scored: List[Dict] = []
    for i, post in enumerate(posts, start=1):
        result = score_story(post)
        if result:
            scored.append(result)
        # Light progress every 25
        if i % 25 == 0:
            print(f"    ...{i}/{len(posts)} scored")

    # Sort by combined score desc
    scored.sort(key=lambda s: s.get("combined_score", 0), reverse=True)

    # Track how many crossed the threshold (for the health check)
    above_threshold = sum(
        1 for s in scored if s.get("relevance_score", 0) >= config.RELEVANCE_THRESHOLD
    )

    # Adaptive top 15
    top_count = min(15, len(scored))
    curated = scored[:top_count]

    print(
        f"  {len(scored)} scored · {above_threshold} above threshold "
        f"({config.RELEVANCE_THRESHOLD}) · top {top_count} selected\n"
    )
    return curated


# ============================================================
# Pass 2 — daily synthesis (Sonnet/Opus)
# ============================================================

def synthesize_daily(curated: List[Dict]) -> Dict:
    """Send the curated story list to Sonnet/Opus for high-level synthesis."""
    if not curated:
        return {
            "metrics": {
                "top_subreddit": "—",
                "most_active_category": "—",
                "trending_model": "—",
                "trending_model_buzz_change": "",
            },
            "narrative": "",
            "pattern_insights": [],
            "fintech_implications": None,
            "trending_topics": [],
            "category_breakdown": {},
            "top_story": None,
        }

    print("Daily synthesis (Sonnet/Opus)...")

    # Slim for token efficiency
    slim = []
    for i, s in enumerate(curated[:30]):
        slim.append({
            "index": i,
            "title": s.get("title", ""),
            "source": s.get("source", ""),
            "subreddit": s.get("subreddit", ""),
            "url": s.get("url", ""),
            "score": s.get("score", 0),
            "category_tags": s.get("category_tags", []),
            "model_mentioned": s.get("model_mentioned"),
            "is_fintech": s.get("is_fintech", False),
            "summary": s.get("summary", ""),
            "relevance_score": s.get("relevance_score", 0),
        })

    template = load_prompt("synthesize")
    prompt = template.replace("{stories_json}", json.dumps(slim, indent=2))

    try:
        text = sonnet_call(
            get_client(),
            prompt,
            model=config.OPUS_MODEL,
            max_tokens=2500,
        )
    except Exception as exc:
        print(f"    synthesis call failed: {exc}")
        return {
            "metrics": {},
            "narrative": "",
            "pattern_insights": [],
            "fintech_implications": None,
            "trending_topics": [],
            "category_breakdown": {},
            "top_story": None,
        }

    synthesis = extract_json(text) or {}
    if not isinstance(synthesis, dict):
        synthesis = {}

    # Defensive defaults for any missing keys
    synthesis.setdefault("metrics", {})
    synthesis.setdefault("narrative", "")
    synthesis.setdefault("pattern_insights", [])
    synthesis.setdefault("fintech_implications", None)
    synthesis.setdefault("trending_topics", [])
    synthesis.setdefault("category_breakdown", {})
    synthesis.setdefault("top_story", None)

    print("  synthesis complete\n")
    return synthesis


# ============================================================
# Per-model sentiment (HN comments → Haiku classification)
# ============================================================

def _classify_comments_batch(model_name: str, comments: List[str]) -> Dict:
    """Classify a batch of comments for one model via a single Haiku call.

    Returns: {"positive": int, "negative": int, "neutral": int,
              "sentiment_score": float (1-10), "label": str,
              "drivers": List[str]}

    The drivers list captures specific opinion fragments — used for the
    "what people are saying" angle on Page 2.
    """
    if not comments:
        return {
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "sentiment_score": 6.5,
            "label": "neutral",
            "drivers": [],
        }

    # Build a numbered list, capped per comment to keep tokens reasonable
    numbered = "\n".join(
        f"[{i+1}] {c[:600]}" for i, c in enumerate(comments[:25])
    )

    prompt = f"""You are scoring sentiment of Hacker News comments about an AI model: {model_name}.

For the comments below, classify each as positive, negative, or neutral toward {model_name}.
Then output an aggregate sentiment score (1-10), a label, and 2-3 specific opinion fragments
that capture what people are saying (verbatim phrases or sharp paraphrases, 6-12 words each).

Comments:
{numbered}

Return ONLY a JSON object:
{{
  "positive": <count of positive comments>,
  "negative": <count of negative comments>,
  "neutral": <count of neutral comments>,
  "sentiment_score": <1-10 float; 6.5 = neutral, 8+ = strongly positive>,
  "label": "positive" | "neutral" | "negative",
  "drivers": [
    {{"text": "short opinion 1", "direction": "positive"}},
    {{"text": "short opinion 2", "direction": "negative"}},
    {{"text": "short opinion 3", "direction": "neutral"}}
  ]
}}

Driver direction rules:
- positive = the fragment is clearly favorable toward {model_name}
- negative = the fragment is clearly critical of {model_name}
- neutral = factual, mixed, unclear, or comparative without a clear sentiment
- Use ONLY: positive, negative, neutral"""

    try:
        text = haiku_call(get_client(), prompt, model=config.HAIKU_MODEL, max_tokens=600)
        data = extract_json(text)
    except Exception as exc:
        print(f"    sentiment classify failed for {model_name}: {exc}")
        data = None

    if not isinstance(data, dict):
        return {
            "positive": 0,
            "negative": 0,
            "neutral": len(comments),
            "sentiment_score": 6.5,
            "label": "neutral",
            "drivers": [],
        }

    # Coerce types defensively
    raw_drivers = data.get("drivers") or []
    drivers = []
    for d in raw_drivers[:3]:
        if isinstance(d, dict):
            driver_text = str(d.get("text") or "").strip()
            direction = str(d.get("direction") or "neutral").strip().lower()
            if direction not in {"positive", "negative", "neutral"}:
                direction = "neutral"
            if driver_text:
                drivers.append({"text": driver_text, "direction": direction})
        elif isinstance(d, str):
            driver_text = d.strip()
            if driver_text:
                drivers.append({"text": driver_text, "direction": "neutral"})

    return {
        "positive": int(data.get("positive") or 0),
        "negative": int(data.get("negative") or 0),
        "neutral": int(data.get("neutral") or 0),
        "sentiment_score": float(data.get("sentiment_score") or 6.5),
        "label": str(data.get("label") or "neutral"),
        "drivers": drivers,
    }


def analyze_model_sentiment_hn(model_cfg: Dict, hours_back: int = 72) -> Dict:
    """Compute per-model sentiment from HN comments over the last N hours.

    Returns the dict shape render.py expects on Page 2.
    """
    keywords = model_cfg.get("keywords", [])
    result = hn_source.fetch_model_mentions(
        keywords,
        hours_back=hours_back,
        max_stories=10,
    )
    stories = result.get("stories", [])
    all_comments: List[str] = []
    for s in stories:
        all_comments.extend(s.get("comments", []))

    classified = _classify_comments_batch(model_cfg.get("name", ""), all_comments)

    pos = classified["positive"]
    neg = classified["negative"]
    neu = classified["neutral"]
    total = pos + neg + neu

    # Buzz volume — proportional to mention count, capped at 100
    # (Will be tuned vs each model's 30-day peak once history exists)
    buzz_volume = min(total * 4, 100) if total else 0

    return {
        "model_id": model_cfg.get("id", ""),
        "model_config": model_cfg,
        "sentiment_score": round(classified["sentiment_score"], 1),
        "sentiment_label": classified["label"],
        "buzz_volume": buzz_volume,
        "story_count": len(stories),
        "comment_count": total,
        "wow_delta_pct": "",  # filled later from history
        "trend_drivers": classified["drivers"],
        "mentions_breakdown": {
            "positive": pos,
            "negative": neg,
            "neutral": neu,
        },
    }


def analyze_all_model_sentiments(_unused_curated: Optional[List[Dict]] = None) -> List[Dict]:
    """Run sentiment analysis for every tracked model via HN comments.

    Signature kept compatible with existing main.py for now (the curated
    arg is no longer used — we pull HN comments directly per model).
    """
    print(f"Per-model sentiment (HN comments, last 3 days) — {len(config.TRACKED_MODELS)} models")
    results: List[Dict] = []
    for model_cfg in config.TRACKED_MODELS:
        result = analyze_model_sentiment_hn(model_cfg, hours_back=72)
        results.append(result)
        print(
            f"  {model_cfg.get('name','?')}: "
            f"{result['sentiment_score']:.1f}/10 "
            f"({result['comment_count']} comments across {result['story_count']} stories)"
        )
    print()
    return results
