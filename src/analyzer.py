"""
Claude API analyzer.

Two-pass approach:
  Pass 1: Haiku 4.5 scores and tags every story (cheap, fast, scalable).
  Pass 2: Opus 4.7 synthesizes the curated set into narrative + insights.

Per-model sentiment is a separate Haiku call per tracked model.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from anthropic import Anthropic
from dotenv import load_dotenv

import config

load_dotenv()

# Single shared client
_client: Optional[Anthropic] = None


def get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def load_prompt(name: str) -> str:
    """Load a prompt template from prompts/ directory."""
    path = Path(__file__).parent.parent / "prompts" / f"{name}.txt"
    return path.read_text(encoding="utf-8")


def extract_json(text: str) -> dict:
    """
    Extract a JSON object from a Claude response.
    Handles ```json fences, stray preamble, and trailing commentary.
    """
    text = text.strip()

    # Find first { and last } — the actual JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in response: {text[:200]}")

    candidate = text[start:end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        # If parse fails, surface the response for debugging
        raise ValueError(f"Failed to parse JSON from Claude response: {e}\nResponse was: {text[:500]}")

# ---------------- PASS 1: per-story scoring (Haiku) ----------------

def score_story(post: Dict) -> Optional[Dict]:
    """
    Send a single Reddit post to Haiku for scoring + tagging.
    Returns the merged post + analysis dict, or None if scoring fails.
    """
    template = load_prompt("score_story")
    selftext = post.get("selftext", "")[:1500] or "(link post, no body text)"
    external_url = post.get("external_url") or "(none)"

    prompt = (template
        .replace("{title}", str(post["title"]))
        .replace("{subreddit}", str(post["subreddit"]))
        .replace("{score}", str(post["score"]))
        .replace("{num_comments}", str(post["num_comments"]))
        .replace("{selftext}", selftext)
        .replace("{external_url}", external_url))

    try:
        response = get_client().messages.create(
            model=config.HAIKU_MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        analysis = extract_json(response.content[0].text)

        return {
            **post,
            "relevance_score": float(analysis.get("relevance_score", 0)),
            "category_tags": analysis.get("category_tags", []),
            "model_mentioned": analysis.get("model_mentioned"),
            "is_fintech": bool(analysis.get("is_fintech", False)),
            "summary": analysis.get("summary", ""),
            "reasoning": analysis.get("reasoning", ""),
        }
    except Exception as e:
        print(f"  ! Score failed for '{post['title'][:60]}...': {e}")
        return None

def score_all_stories(posts: List[Dict]) -> List[Dict]:
    """
    Score every post via Haiku.
    Returns only stories meeting the relevance threshold, sorted descending.
    """
    print(f"Scoring {len(posts)} posts with Haiku 4.5...")
    scored = []
    for i, post in enumerate(posts, 1):
        result = score_story(post)
        if result:
            scored.append(result)
        if i % 25 == 0:
            print(f"  ...{i}/{len(posts)} scored")

    # Filter by relevance threshold
    curated = [s for s in scored if s["relevance_score"] >= config.RELEVANCE_THRESHOLD]
    curated.sort(key=lambda s: s["relevance_score"], reverse=True)
    print(f"Curated {len(curated)} stories at >= {config.RELEVANCE_THRESHOLD} relevance.\n")
    return curated


# ---------------- PASS 2: daily synthesis (Opus) ----------------

def synthesize_daily(curated: List[Dict]) -> Dict:
    """
    Send the curated story list to Opus for high-level synthesis.
    Returns the synthesis dict (top story, narrative, insights, etc.).
    """
    print(f"Synthesizing daily narrative with Opus 4.7...")

    # Slim the stories before sending — we don't need full bodies
    slim = [{
        "index": i,
        "title": s["title"],
        "subreddit": s["subreddit"],
        "url": s["url"],
        "score": s["score"],
        "category_tags": s["category_tags"],
        "model_mentioned": s.get("model_mentioned"),
        "is_fintech": s.get("is_fintech", False),
        "summary": s["summary"],
        "relevance_score": s["relevance_score"],
    } for i, s in enumerate(curated[:30])]  # cap at top 30

    template = load_prompt("synthesize")
    prompt = template.replace("{stories_json}", json.dumps(slim, indent=2))

    response = get_client().messages.create(
        model=config.OPUS_MODEL,
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )
    synthesis = extract_json(response.content[0].text)
    print("Synthesis complete.\n")
    return synthesis


# ---------------- Per-model sentiment (Haiku) ----------------

def analyze_model_sentiment(model_cfg: Dict, all_scored_stories: List[Dict]) -> Dict:
    """
    For one tracked model, identify stories mentioning it and ask Haiku to
    produce a sentiment dict.
    """
    keywords = [k.lower() for k in model_cfg["keywords"]]

    matching = []
    for s in all_scored_stories:
        haystack = (s["title"] + " " + s.get("selftext", "")).lower()
        if any(kw in haystack for kw in keywords):
            matching.append(s)

    if not matching:
        return {
            "model_id": model_cfg["id"],
            "sentiment_score": 6.5,
            "sentiment_label": "neutral",
            "buzz_volume": 0,
            "wow_delta_pct": "0.0%",
            "strengths_mentioned": [],
            "weaknesses_mentioned": [],
            "trend_drivers": [{"direction": "neutral", "text": "No notable mentions in today's pull."}],
            "story_count": 0,
        }

    template = load_prompt("model_sentiment")
    slim = [{"title": s["title"], "summary": s.get("summary", ""), "score": s["score"]} for s in matching[:20]]
    prompt = (template
        .replace("{model_name}", model_cfg["name"])
        .replace("{model_maker}", model_cfg["maker"])
        .replace("{model_keywords}", ", ".join(model_cfg["keywords"]))
        .replace("{stories_json}", json.dumps(slim, indent=2)))

    try:
        response = get_client().messages.create(
            model=config.HAIKU_MODEL,
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        sentiment = extract_json(response.content[0].text)
        sentiment["story_count"] = len(matching)
        return sentiment
    except Exception as e:
        print(f"  ! Sentiment failed for {model_cfg['name']}: {e}")
        return {
            "model_id": model_cfg["id"],
            "sentiment_score": 6.5,
            "sentiment_label": "neutral",
            "buzz_volume": 0,
            "wow_delta_pct": "0.0%",
            "strengths_mentioned": [],
            "weaknesses_mentioned": [],
            "trend_drivers": [{"direction": "neutral", "text": f"Analysis error: {e}"}],
            "story_count": len(matching),
        }


def analyze_all_model_sentiments(all_scored_stories: List[Dict]) -> List[Dict]:
    """Run sentiment analysis for every tracked model."""
    print(f"Analyzing sentiment for {len(config.TRACKED_MODELS)} models...")
    results = []
    for model_cfg in config.TRACKED_MODELS:
        result = analyze_model_sentiment(model_cfg, all_scored_stories)
        result["model_config"] = model_cfg
        results.append(result)
        print(f"  {model_cfg['name']}: {result['sentiment_score']:.1f}/10 ({result['story_count']} stories)")
    print()
    return results
