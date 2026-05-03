"""
Main orchestrator. Runs the full pipeline:
  1. arXiv pull (free) — also feeds Page 1 stories
  2. Multi-source aggregation: HN + arXiv + GitHub Trending + Reddit (mock)
  3. Score every story via Haiku (source-agnostic content rubric)
  4. Synthesize narrative + insights via Sonnet/Opus
  5. Per-model sentiment from HN comments (Haiku)
  6. ETF + market cap data via yfinance
  7. Weekly finance refresh on Mondays (cached otherwise)
  8. Save daily JSON
  9. Render HTML dashboard

Run with:
  python -m src.main
"""

from __future__ import annotations

import json
import os
import time
from collections import Counter
from datetime import date
from typing import Dict, List

from dotenv import load_dotenv

import config
from src import scraper, analyzer, stocks, storage, render
from src.arxiv_analyzer import analyze_arxiv_papers
from src.finance_analyzer import analyze_finance

load_dotenv()


def compute_metrics(curated_stories: List[Dict], posts_pulled: int) -> Dict:
    """Compute summary metrics for the dashboard header (Component 1.1)."""
    if not curated_stories:
        return {
            "total_stories": 0,
            "posts_pulled": posts_pulled,
            "fintech_count": 0,
            "top_source": "—",
            "top_source_count": 0,
            "most_active_category": "—",
            "top_category_count": 0,
            "top_subreddit": "—",
            "top_subreddit_count": 0,
        }

    source_counts: Counter = Counter()
    for s in curated_stories:
        src = s.get("source") or s.get("subreddit") or "Unknown"
        source_counts[src] += 1
    top_source, top_source_count = source_counts.most_common(1)[0]

    cat_counts: Counter = Counter()
    for s in curated_stories:
        tags = s.get("category_tags") or []
        if tags:
            cat_counts[tags[0]] += 1
    if cat_counts:
        top_cat, top_cat_count = cat_counts.most_common(1)[0]
    else:
        top_cat, top_cat_count = "—", 0

    fintech_count = sum(1 for s in curated_stories if s.get("is_fintech"))

    return {
        "total_stories": len(curated_stories),
        "posts_pulled": posts_pulled,
        "fintech_count": fintech_count,
        "top_source": top_source,
        "top_source_count": top_source_count,
        "most_active_category": top_cat,
        "top_category_count": top_cat_count,
        "top_subreddit": top_source,
        "top_subreddit_count": top_source_count,
    }


def compute_category_breakdown(curated_stories: List[Dict]) -> Dict[str, int]:
    """Count stories per primary category for the donut chart (Component 1.4)."""
    breakdown: Dict[str, int] = {}
    for story in curated_stories:
        tags = story.get("category_tags") or []
        if tags:
            primary = tags[0]
            breakdown[primary] = breakdown.get(primary, 0) + 1
    return breakdown


def _empty_synthesis() -> Dict:
    """Default synthesis dict when curated list is empty."""
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


def run_pipeline() -> None:
    """Run the full daily pipeline."""
    print("=" * 60)
    print("AI Intelligence Dashboard — daily pipeline")
    print(f"Date: {date.today().isoformat()}")
    print("=" * 60)

    # ---------- 1. arXiv (independent, runs first) ----------
    print("\n[1/8] arXiv pipeline")
    try:
        arxiv_payload = analyze_arxiv_papers(days_back=7)
    except Exception as exc:
        print(f"  arXiv pipeline failed: {exc}")
        arxiv_payload = {}

    arxiv_top_papers = arxiv_payload.get("top_papers") or []

    # ---------- 2. Multi-source aggregation ----------
    print("\n[2/8] Multi-source aggregation (HN + GitHub + arXiv + Reddit)")
    posts = scraper.scrape_all_sources(arxiv_top_papers=arxiv_top_papers)

    # ---------- 3. Score every story (Haiku) ----------
    print("\n[3/8] Story scoring (Haiku, source-agnostic)")
    curated = analyzer.score_all_stories(posts)

    # ---------- 4. Daily synthesis (Sonnet/Opus) ----------
    print("\n[4/8] Daily synthesis (Sonnet/Opus)")
    if curated:
        synthesis = analyzer.synthesize_daily(curated)
    else:
        synthesis = _empty_synthesis()

    # ---------- 5. Per-model sentiment (HN comments) ----------
    print("\n[5/8] Per-model sentiment (HN comments → Haiku)")
    model_sentiments = analyzer.analyze_all_model_sentiments()

    # ---------- 6. yfinance market data ----------
    print("\n[6/8] yfinance — ETFs + market caps")
    etfs = stocks.fetch_all_etfs()
    public_ai = stocks.fetch_public_ai_market_caps()

    # ---------- 7. Compute summary metrics ----------
    metrics = compute_metrics(curated, len(posts))
    category_breakdown = compute_category_breakdown(curated)

    # ---------- 8. Weekly finance refresh (Mondays only) ----------
    print("\n[7/8] Finance pipeline (weekly cache)")
    finance_cache_path = config.FINANCE_CACHE_PATH
    is_monday = date.today().weekday() == 0
    finance_payload: Dict = {}

    if is_monday:
        print("  Cooling off 60s before finance pull (rate-limit safety)...")
        time.sleep(60)
        print("  Monday — refreshing finance data via web search...")
        try:
            finance_payload = analyze_finance()
            os.makedirs(config.OUTPUT_DIR, exist_ok=True)
            with open(finance_cache_path, "w", encoding="utf-8") as f:
                json.dump(finance_payload, f, indent=2, ensure_ascii=False, default=str)
            print(f"  finance cache updated: {finance_cache_path}")
        except Exception as exc:
            print(f"  finance refresh failed: {exc}")
            finance_payload = {}

    if not finance_payload and finance_cache_path.exists():
        try:
            with open(finance_cache_path, "r", encoding="utf-8") as f:
                finance_payload = json.load(f)
            print(f"  finance cache loaded from {finance_payload.get('_finance_updated', 'unknown')}")
        except Exception as exc:
            print(f"  finance cache read failed: {exc}")
            finance_payload = {}

    # ---------- Assemble payload ----------
    payload: Dict = {
        "stories": curated,
        "metrics": metrics,
        "category_breakdown": category_breakdown,
        "synthesis": synthesis,
        "model_sentiments": model_sentiments,
        "etfs": etfs,
        "public_ai": public_ai,
    }

    payload.update({
        "research_summary":   arxiv_payload.get("research_summary", {}),
        "paper_of_week":      arxiv_payload.get("paper_of_week"),
        "top_papers":         arxiv_payload.get("top_papers", []),
        "research_categories": arxiv_payload.get("research_categories", {}),
        "research_volume":    arxiv_payload.get("research_volume", {}),
        "hot_institutions":   arxiv_payload.get("hot_institutions", []),
        "author_spotlight":   arxiv_payload.get("author_spotlight", []),
        "breakthrough_radar": arxiv_payload.get("breakthrough_radar", []),
        "research_signals":   arxiv_payload.get("research_signals", []),
        "fintech_research":   arxiv_payload.get("fintech_research", []),
    })

    payload.update({
        "_finance_updated":   finance_payload.get("_finance_updated", ""),
        "funding_summary":    finance_payload.get("funding_summary", {}),
        "funding_rounds":     finance_payload.get("funding_rounds", []),
        "private_ai":         finance_payload.get("private_ai", []),
        "arms_race":          finance_payload.get("arms_race", {}),
        "vc_league":          finance_payload.get("vc_league", []),
        "money_flow":         finance_payload.get("money_flow", []),
        "ma_tracker":         finance_payload.get("ma_tracker", []),
        "fintech_spotlight":  finance_payload.get("fintech_spotlight", []),
    })

    print("\n[8/8] Save + render")
    json_path = storage.save_daily_data(payload)
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
