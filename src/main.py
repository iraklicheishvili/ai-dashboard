"""
Main orchestrator. Runs the full pipeline:
  1. Scrape Reddit (24 subs)
  2. Score every post via Haiku
  3. Synthesize narrative + insights via Opus
  4. Per-model sentiment analysis (Haiku)
  5. Pull ETF / market data (yfinance)
  6. Save daily JSON
  7. Render HTML dashboard

Run with:
  python -m src.main
"""

from collections import Counter
from datetime import date
from typing import Dict

from src import scraper, analyzer, stocks, storage, render


def compute_metrics(curated_stories: list, posts_pulled: int) -> Dict:
    """Compute basic metrics for the dashboard header."""
    if not curated_stories:
        return {
            "total_stories": 0,
            "posts_pulled": posts_pulled,
            "top_subreddit_count": 0,
            "top_category_count": 0,
        }

    sub_counts = Counter(s["subreddit"] for s in curated_stories)
    cat_counts = Counter()
    for s in curated_stories:
        for tag in s.get("category_tags", []):
            cat_counts[tag] += 1

    top_sub = sub_counts.most_common(1)[0] if sub_counts else ("", 0)
    top_cat = cat_counts.most_common(1)[0] if cat_counts else ("", 0)

    return {
        "total_stories": len(curated_stories),
        "posts_pulled": posts_pulled,
        "top_subreddit": top_sub[0],
        "top_subreddit_count": top_sub[1],
        "most_active_category": top_cat[0],
        "top_category_count": top_cat[1],
        "fintech_count": sum(1 for s in curated_stories if s.get("is_fintech")),
    }


def compute_category_breakdown(curated_stories: list) -> dict:
    """Count stories per category for the donut chart."""
    breakdown = {}
    for story in curated_stories:
        tags = story.get("category_tags") or []
        for tag in tags[:1]:
            breakdown[tag] = breakdown.get(tag, 0) + 1
    return breakdown


def run_pipeline():
    """Full pipeline. Returns the saved JSON path and dashboard HTML path."""
    print("=" * 60)
    print("AI Intelligence Dashboard — daily pipeline")
    print(f"Date: {date.today().isoformat()}")
    print("=" * 60 + "\n")

    # 1. Scrape Reddit
    posts = scraper.scrape_all_subreddits()

    # 2. Score every post (Haiku) and curate
    curated = analyzer.score_all_stories(posts)

    # 3. Synthesize narrative + insights (Opus)
    synthesis = analyzer.synthesize_daily(curated) if curated else {"metrics": {"top_subreddit": "—", "most_active_category": "—", "trending_model": "—", "trending_model_buzz_change": ""}, "narrative": "", "pattern_insights": [], "fintech_spotlight": []}

    # 4. Per-model sentiment (Haiku, one call per model)
    model_sentiments = analyzer.analyze_all_model_sentiments(curated)

    # 5. Market data
    etfs = stocks.fetch_all_etfs()
    public_ai = stocks.fetch_public_ai_market_caps()

    # 6. Compute summary metrics
    metrics = compute_metrics(curated, len(posts))

    # 7. Assemble JSON payload
    payload = {
        "stories": curated,
        "metrics": metrics,
        "synthesis": synthesis,
        "model_sentiments": model_sentiments,
        "etfs": etfs,
        "public_ai": public_ai,
    }

    json_path = storage.save_daily_data(payload)

    # 8. Render dashboard
    print("Rendering dashboard HTML...")
    html = render.render_dashboard(payload)
    html_path = storage.save_dashboard(html)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print(f"  JSON:      {json_path}")
    print(f"  Dashboard: {html_path}")
    print(f"  Stories:   {len(curated)} curated from {len(posts)} pulled")
    print("=" * 60)


if __name__ == "__main__":
    run_pipeline()
