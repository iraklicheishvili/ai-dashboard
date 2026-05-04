"""Main orchestrator for the AI Intelligence Dashboard.

Modes:
  python -m src.main                 # full pipeline (manual/local)
  python -m src.main --daily         # lightweight daily run; skips weekly/monthly web-search caches if fresh
  python -m src.main --finance-only  # refresh finance cache only, then re-render from saved data
  python -m src.main --model-only    # refresh model deep/event cache only, then re-render from saved data
  python -m src.main --monthly-only  # refresh monthly strengths/weaknesses only, then re-render
  python -m src.main --render-only   # $0 local render from saved JSON/caches

Phase 3 additions:
  - Persistent model sentiment and GitHub stars histories
  - Weekly model deep-dive cache (MAU, market share, key people, recent changes)
  - Monthly strengths/weaknesses cache
  - Daily model events history
  - Health check output
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

import config
from src import storage, render

load_dotenv()


# ============================================================
# Basic derived structures
# ============================================================

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


def _source_label(story: Dict) -> str:
    """Shared source label used for Page 1 history and source hot topics."""
    source = story.get("source") or story.get("subreddit") or "Unknown"
    # Phase 3: keep mock Reddit out of the source-volume story unless it is live.
    if source.startswith("r/"):
        return "Reddit"
    return source


def build_source_hot_topics(curated_stories: List[Dict]) -> Dict[str, List[Dict]]:
    """Group today's curated stories by source for Page 1 Component 1.6."""
    grouped: Dict[str, List[Dict]] = {}
    for story in curated_stories:
        grouped.setdefault(_source_label(story), []).append(story)
    for source, items in grouped.items():
        grouped[source] = sorted(
            items,
            key=lambda s: float(s.get("combined_score") or s.get("relevance_score") or 0),
            reverse=True,
        )[:7]
    # Prefer live sources first, then any remaining source.
    preferred = ["Hacker News", "GitHub Trending", "arXiv", "Reddit"]
    ordered: Dict[str, List[Dict]] = {}
    for src in preferred:
        if src in grouped:
            ordered[src] = grouped[src]
    for src in sorted(grouped.keys()):
        if src not in ordered:
            ordered[src] = grouped[src]
    return ordered


# ============================================================
# Persistent history helpers
# ============================================================

def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def _parse_iso_date(value: Any) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def cache_age_days(path: Path, date_keys: Optional[List[str]] = None) -> Optional[int]:
    """Return cache age in days using explicit date fields first, then file mtime."""
    if not path.exists():
        return None
    payload = _read_json(path, {})
    if isinstance(payload, dict):
        for key in (date_keys or []):
            parsed = _parse_iso_date(payload.get(key))
            if parsed:
                return max((date.today() - parsed).days, 0)
        parsed = _parse_iso_date(payload.get("last_updated") or payload.get("updated_at") or payload.get("date"))
        if parsed:
            return max((date.today() - parsed).days, 0)
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime).date()
        return max((date.today() - mtime).days, 0)
    except OSError:
        return None


def cache_is_fresh(path: Path, max_age_days: int, date_keys: Optional[List[str]] = None) -> bool:
    age = cache_age_days(path, date_keys=date_keys)
    return age is not None and age < max_age_days


def merge_finance_cache(payload: Dict) -> Dict:
    """Overlay latest finance cache onto a render payload.

    This lets --finance-only update output/finance-cache.json and then re-render
    without re-running the full daily pipeline.
    """
    finance = _read_json(Path(config.FINANCE_CACHE_PATH), {})
    if not isinstance(finance, dict) or not finance:
        return payload
    merged = dict(payload)
    for key in [
        "_finance_updated", "funding_summary", "funding_rounds", "private_ai",
        "arms_race", "vc_league", "money_flow", "ma_tracker", "fintech_spotlight",
    ]:
        if key in finance:
            merged[key] = finance.get(key)
    return merged


def _normalize_github_history(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {"daily_totals": {}, "daily_deltas": {}}
    if "daily_totals" in raw or "daily_deltas" in raw:
        raw.setdefault("daily_totals", {})
        raw.setdefault("daily_deltas", {})
        return raw
    # Backward-compatible old shape: {date: {model_id: delta}}
    return {"daily_totals": {}, "daily_deltas": raw}


def load_github_stars_history() -> Dict[str, Any]:
    return _normalize_github_history(_read_json(Path(config.GITHUB_STARS_HISTORY_PATH), {}))


def load_model_sentiment_history() -> Dict[str, Any]:
    raw = _read_json(Path(config.MODEL_SENTIMENT_HISTORY_PATH), {})
    return raw if isinstance(raw, dict) else {}


def append_model_sentiment_history(model_sentiments: List[Dict], target_date: Optional[str] = None) -> Dict[str, Any]:
    """Persist daily model sentiment aggregates for trends and mention charts."""
    d = target_date or date.today().isoformat()
    history = load_model_sentiment_history()
    row: Dict[str, Dict] = {}
    for item in model_sentiments:
        cfg = item.get("model_config") or {}
        mid = item.get("model_id") or cfg.get("id")
        if not mid:
            continue
        breakdown = item.get("mentions_breakdown") or {}
        row[mid] = {
            "sentiment_score": float(item.get("sentiment_score") or 0),
            "buzz_volume": int(item.get("buzz_volume") or 0),
            "positive": int(breakdown.get("positive") or 0),
            "negative": int(breakdown.get("negative") or 0),
            "neutral": int(breakdown.get("neutral") or 0),
            "comment_count": int(item.get("comment_count") or 0),
            "story_count": int(item.get("story_count") or 0),
        }
    history[d] = row
    # Keep one year; cheap and enough for prior/current comparisons.
    history = dict(sorted(history.items())[-370:])
    _write_json(Path(config.MODEL_SENTIMENT_HISTORY_PATH), history)
    print(f"Model sentiment history saved: {config.MODEL_SENTIMENT_HISTORY_PATH}")
    return history


def append_github_stars_history() -> Dict[str, Any]:
    """Fetch daily GitHub star deltas for Page 2 GitHub mode."""
    from src.sources import github_trending

    d = date.today().isoformat()
    history = load_github_stars_history()
    prior_totals: Dict[str, int] = {}
    for old_date in sorted(history.get("daily_totals", {}).keys(), reverse=True):
        if old_date < d:
            prior_totals = history["daily_totals"].get(old_date) or {}
            break

    model_repos = {m["id"]: m.get("github_repos", []) for m in config.TRACKED_MODELS}
    result = github_trending.fetch_model_stars_today(model_repos, prior_day_stars=prior_totals)
    history.setdefault("daily_totals", {})[d] = result.get("totals", {})
    history.setdefault("daily_deltas", {})[d] = result.get("deltas", {})
    history["daily_totals"] = dict(sorted(history["daily_totals"].items())[-370:])
    history["daily_deltas"] = dict(sorted(history["daily_deltas"].items())[-370:])
    _write_json(Path(config.GITHUB_STARS_HISTORY_PATH), history)
    print(f"GitHub stars history saved: {config.GITHUB_STARS_HISTORY_PATH}")
    return history


def backfill_missing_history_files() -> None:
    """Create history files from existing daily JSONs if they do not exist yet."""
    sentiment_path = Path(config.MODEL_SENTIMENT_HISTORY_PATH)
    if not sentiment_path.exists():
        history: Dict[str, Any] = {}
        for path in sorted(Path(config.DAILY_DATA_DIR).glob("*.json")):
            payload = _read_json(path, {})
            row: Dict[str, Any] = {}
            for item in payload.get("model_sentiments") or []:
                cfg = item.get("model_config") or {}
                mid = item.get("model_id") or cfg.get("id")
                if not mid:
                    continue
                br = item.get("mentions_breakdown") or {}
                row[mid] = {
                    "sentiment_score": float(item.get("sentiment_score") or 0),
                    "buzz_volume": int(item.get("buzz_volume") or 0),
                    "positive": int(br.get("positive") or 0),
                    "negative": int(br.get("negative") or 0),
                    "neutral": int(br.get("neutral") or 0),
                    "comment_count": int(item.get("comment_count") or 0),
                    "story_count": int(item.get("story_count") or 0),
                }
            if row:
                history[payload.get("_date") or path.stem] = row
        _write_json(sentiment_path, history)
        print(f"Backfilled model sentiment history: {sentiment_path}")

    gh_path = Path(config.GITHUB_STARS_HISTORY_PATH)
    if not gh_path.exists():
        _write_json(gh_path, {"daily_totals": {}, "daily_deltas": {}})
        print(f"Created empty GitHub stars history: {gh_path}")


def build_volume_history(current_payload: Optional[Dict] = None, days: int = 30) -> List[Dict]:
    """Build Page 1 source history from saved daily JSON files."""
    rows: List[Dict] = []
    seen_dates = set()
    data_dir = Path(config.DAILY_DATA_DIR)
    live_sources = ["Hacker News", "GitHub Trending", "arXiv"]

    if data_dir.exists():
        for path in sorted(data_dir.glob("*.json"))[-days:]:
            payload = _read_json(path, {})
            stories = payload.get("stories") or []
            sources: Dict[str, int] = {src: 0 for src in live_sources}
            for story in stories:
                source = _source_label(story)
                if source in sources:
                    sources[source] += 1
            row_date = payload.get("_date") or path.stem
            rows.append({"date": row_date, "count": sum(sources.values()), "sources": sources})
            seen_dates.add(row_date)

    if current_payload:
        current_date = current_payload.get("_date") or date.today().isoformat()
        if current_date not in seen_dates:
            stories = current_payload.get("stories") or []
            sources = {src: 0 for src in live_sources}
            for story in stories:
                source = _source_label(story)
                if source in sources:
                    sources[source] += 1
            rows.append({"date": current_date, "count": sum(sources.values()), "sources": sources})

    return sorted(rows, key=lambda r: r.get("date", ""))[-days:]


def build_sentiment_history(current_payload: Optional[Dict] = None, days: int = 30) -> Dict:
    """Build Page 2 trend data from persistent histories + daily JSON fallback."""
    model_meta = {m["id"]: m for m in config.TRACKED_MODELS}
    sentiment_hist = load_model_sentiment_history()

    # Backward fill from daily JSONs if the persistent file is still empty.
    if not sentiment_hist:
        data_dir = Path(config.DAILY_DATA_DIR)
        if data_dir.exists():
            for path in sorted(data_dir.glob("*.json"))[-days:]:
                payload = _read_json(path, {})
                row_date = payload.get("_date") or path.stem
                sentiment_hist[row_date] = {}
                for item in payload.get("model_sentiments") or []:
                    mid = item.get("model_id") or (item.get("model_config") or {}).get("id")
                    if mid:
                        sentiment_hist[row_date][mid] = {"sentiment_score": float(item.get("sentiment_score") or 0)}

    if current_payload:
        current_date = current_payload.get("_date") or date.today().isoformat()
        sentiment_hist.setdefault(current_date, {})
        for item in current_payload.get("model_sentiments") or []:
            mid = item.get("model_id") or (item.get("model_config") or {}).get("id")
            if mid:
                sentiment_hist[current_date][mid] = {"sentiment_score": float(item.get("sentiment_score") or 0)}

    labels_full = sorted(sentiment_hist.keys())[-days:]
    github_history = load_github_stars_history()
    gh_deltas = github_history.get("daily_deltas", {}) if isinstance(github_history, dict) else {}

    models = []
    for mid, meta in model_meta.items():
        carried = None
        scores = []
        github_stars = []
        for d in labels_full:
            val_raw = sentiment_hist.get(d, {}).get(mid)
            val = None
            if isinstance(val_raw, dict):
                val = val_raw.get("sentiment_score")
            elif val_raw is not None:
                val = val_raw
            if val is not None and float(val) > 0:
                carried = float(val)
            scores.append(carried if carried is not None else None)
            github_stars.append(int((gh_deltas.get(d) or {}).get(mid) or 0))
        models.append({
            "id": mid,
            "name": meta.get("name", mid),
            "color": meta.get("color", "#888780"),
            "scores": scores,
            "github_stars": github_stars,
        })

    return {"labels": [d[5:] if len(d) >= 10 else d for d in labels_full], "models": models}


def enrich_payload_for_render(payload: Dict) -> Dict:
    """Attach render-only derived structures and cached Phase 3 data."""
    from src import model_tracker, health

    enriched = merge_finance_cache(dict(payload))
    backfill_missing_history_files()
    events_history = model_tracker.load_model_events_history()
    deep_cache = model_tracker.load_model_deep_cache()
    strengths_cache = model_tracker.load_model_strengths_cache()
    enriched["model_sentiments"] = model_tracker.attach_model_intelligence(
        enriched.get("model_sentiments") or [],
        deep_cache=deep_cache,
        strengths_cache=strengths_cache,
        events_history=events_history,
    )
    enriched.setdefault("source_hot_topics", build_source_hot_topics(enriched.get("stories") or []))
    enriched["volume_history"] = build_volume_history(enriched)
    enriched["sentiment_history"] = build_sentiment_history(enriched)
    enriched["health"] = enriched.get("health") or health.load_health()
    return enriched


def load_latest_daily_payload() -> Dict:
    """Load the most recent daily JSON snapshot for --render-only."""
    dates = storage.list_recent_dates(1)
    if not dates:
        raise FileNotFoundError(
            f"No daily JSON files found in {config.DAILY_DATA_DIR}. Run the full pipeline once first."
        )
    latest_date = date.fromisoformat(dates[0])
    payload = storage.load_daily_data(latest_date)
    if payload is None:
        raise FileNotFoundError(f"Daily JSON not found for {latest_date.isoformat()}")
    return payload


def render_only() -> None:
    """Render latest.html from saved JSON only. Intended for $0 local UI testing."""
    print("=" * 60)
    print("AI Intelligence Dashboard — render-only")
    print("No source fetches, no Anthropic calls, no yfinance calls.")
    print("=" * 60)
    payload = enrich_payload_for_render(load_latest_daily_payload())
    html = render.render_dashboard(payload)
    html_path = storage.save_dashboard(html)
    print(f"Render-only dashboard saved: {html_path}")


# ============================================================
# Full pipeline
# ============================================================

def run_pipeline(mode: str = "full", force: bool = False) -> None:
    """Run the daily/full pipeline.

    mode="daily" keeps the scheduled daily job lightweight by using existing
    weekly/monthly caches unless forced. mode="full" is for manual local runs.
    """
    from src import scraper, analyzer, stocks, model_tracker, health
    from src.arxiv_analyzer import analyze_arxiv_papers
    from src.finance_analyzer import analyze_finance

    print("=" * 60)
    print(f"AI Intelligence Dashboard — {mode} pipeline")
    print(f"Date: {date.today().isoformat()}")
    print("=" * 60)

    # ---------- 1. arXiv ----------
    print("\n[1/10] arXiv pipeline")
    try:
        arxiv_payload = analyze_arxiv_papers(days_back=7)
    except Exception as exc:
        print(f"  arXiv pipeline failed: {exc}")
        arxiv_payload = {}
    arxiv_top_papers = arxiv_payload.get("top_papers") or []

    # ---------- 2. Multi-source aggregation ----------
    print("\n[2/10] Multi-source aggregation (HN + GitHub + arXiv + Reddit)")
    posts = scraper.scrape_all_sources(arxiv_top_papers=arxiv_top_papers)

    # ---------- 3. Score stories ----------
    print("\n[3/10] Story scoring (Haiku, source-agnostic)")
    curated = analyzer.score_all_stories(posts)

    # ---------- 4. Daily synthesis ----------
    print("\n[4/10] Daily synthesis (Sonnet/Opus)")
    synthesis = analyzer.synthesize_daily(curated) if curated else _empty_synthesis()

    # ---------- 5. Per-model sentiment ----------
    print("\n[5/10] Per-model sentiment (HN comments → Haiku)")
    model_sentiments = analyzer.analyze_all_model_sentiments()
    sentiment_history = append_model_sentiment_history(model_sentiments)

    # ---------- 6. GitHub stars history ----------
    print("\n[6/10] GitHub model ecosystem stars")
    try:
        append_github_stars_history()
    except Exception as exc:
        print(f"  GitHub stars history update failed: {exc}")

    # ---------- 7. yfinance market data ----------
    print("\n[7/10] yfinance — ETFs + market caps")
    etfs = stocks.fetch_all_etfs()
    public_ai = stocks.fetch_public_ai_market_caps()

    # ---------- 8. Weekly/monthly Phase 3 model intelligence ----------
    print("\n[8/10] Model intelligence caches")
    events_history = model_tracker.append_daily_model_events(curated)
    is_monday = date.today().weekday() == 0
    is_monthly = date.today().day == 1

    model_cache_path = Path(config.MODEL_DEEP_CACHE_PATH)
    model_cache_fresh = cache_is_fresh(model_cache_path, 7, date_keys=["_updated", "last_updated", "_model_updated"])
    should_refresh_model = force or (is_monday and mode == "full" and not model_cache_fresh)
    if should_refresh_model:
        print("  Cooling off 60s before model deep-dive pull (rate-limit safety)...")
        time.sleep(60)
        deep_cache = model_tracker.refresh_model_deep_cache(events_history)
    else:
        deep_cache = model_tracker.load_model_deep_cache()
        if model_cache_fresh:
            print("  Model deep-dive cache fresh (<7 days) — skipping web search")
        else:
            print("  Model deep-dive cache loaded")

    strengths_cache_path = Path(config.MODEL_STRENGTHS_CACHE_PATH)
    strengths_fresh = cache_is_fresh(strengths_cache_path, 28, date_keys=["_updated", "last_updated", "_strengths_updated"])
    should_refresh_strengths = force or (is_monthly and mode == "full" and not strengths_fresh)
    if should_refresh_strengths:
        print("  Cooling off 60s before monthly strengths synthesis...")
        time.sleep(60)
        strengths_cache = model_tracker.refresh_model_strengths_cache(sentiment_history)
    else:
        strengths_cache = model_tracker.load_model_strengths_cache()
        if strengths_fresh:
            print("  Model strengths cache fresh — skipping monthly synthesis")
        else:
            print("  Model strengths cache loaded")

    model_sentiments = model_tracker.attach_model_intelligence(
        model_sentiments,
        deep_cache=deep_cache,
        strengths_cache=strengths_cache,
        events_history=events_history,
    )

    # ---------- 9. Weekly finance refresh ----------
    print("\n[9/10] Finance pipeline (weekly cache)")
    finance_cache_path = Path(config.FINANCE_CACHE_PATH)
    finance_payload: Dict = {}

    finance_fresh = cache_is_fresh(finance_cache_path, 7, date_keys=["_finance_updated", "last_updated"])
    should_refresh_finance = force or (is_monday and mode == "full" and not finance_fresh)
    if should_refresh_finance:
        print("  Cooling off 90s before finance pull (rate-limit safety after model intelligence)...")
        time.sleep(90)
        print("  Monday — refreshing finance data via web search...")
        try:
            finance_payload = analyze_finance()
            Path(config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
            finance_cache_path.write_text(
                json.dumps(finance_payload, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
            print(f"  finance cache updated: {finance_cache_path}")
        except Exception as exc:
            print(f"  finance refresh failed: {exc}")
            finance_payload = {}
    elif finance_fresh:
        print("  Finance cache fresh (<7 days) — skipping web search")

    if not finance_payload and finance_cache_path.exists():
        try:
            finance_payload = json.loads(finance_cache_path.read_text(encoding="utf-8"))
            print(f"  finance cache loaded from {finance_payload.get('_finance_updated', 'unknown')}")
        except Exception as exc:
            print(f"  finance cache read failed: {exc}")
            finance_payload = {}

    # ---------- Assemble payload ----------
    metrics = compute_metrics(curated, len(posts))
    category_breakdown = compute_category_breakdown(curated)

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
        "research_summary": arxiv_payload.get("research_summary", {}),
        "paper_of_week": arxiv_payload.get("paper_of_week"),
        "top_papers": arxiv_payload.get("top_papers", []),
        "research_categories": arxiv_payload.get("research_categories", {}),
        "research_volume": arxiv_payload.get("research_volume", {}),
        "hot_institutions": arxiv_payload.get("hot_institutions", []),
        "author_spotlight": arxiv_payload.get("author_spotlight", []),
        "breakthrough_radar": arxiv_payload.get("breakthrough_radar", []),
        "research_signals": arxiv_payload.get("research_signals", []),
        "fintech_research": arxiv_payload.get("fintech_research", []),
    })

    payload.update({
        "_finance_updated": finance_payload.get("_finance_updated", ""),
        "funding_summary": finance_payload.get("funding_summary", {}),
        "funding_rounds": finance_payload.get("funding_rounds", []),
        "private_ai": finance_payload.get("private_ai", []),
        "arms_race": finance_payload.get("arms_race", {}),
        "vc_league": finance_payload.get("vc_league", []),
        "money_flow": finance_payload.get("money_flow", []),
        "ma_tracker": finance_payload.get("ma_tracker", []),
        "fintech_spotlight": finance_payload.get("fintech_spotlight", []),
    })

    payload = enrich_payload_for_render(payload)
    payload["health"] = health.save_health(payload)

    print("\n[10/10] Save + render")
    json_path = storage.save_daily_data(payload)
    html = render.render_dashboard(payload)
    html_path = storage.save_dashboard(html)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print(f"  JSON:      {json_path}")
    print(f"  Dashboard: {html_path}")
    print(f"  Stories:   {len(curated)} curated from {len(posts)} pulled")
    print("=" * 60)


def run_finance_only(force: bool = False) -> None:
    """Refresh finance cache only, then re-render dashboard from saved JSON/caches."""
    path = Path(config.FINANCE_CACHE_PATH)
    if not force and cache_is_fresh(path, 7, date_keys=["_finance_updated", "last_updated"]):
        print("Finance cache fresh (<7 days) — skipping web search")
        render_only()
        return
    from src.finance_analyzer import analyze_finance

    print("Finance-only refresh — cooling off 90s before web search...")
    time.sleep(90)
    try:
        payload = analyze_finance()
        _write_json(path, payload)
        print(f"Finance cache updated: {path}")
    except Exception as exc:
        print(f"Finance-only refresh failed: {exc}")
        print("Keeping existing finance cache and re-rendering.")
    render_only()


def run_model_only(force: bool = False) -> None:
    """Refresh model deep cache only, then re-render dashboard from saved JSON/caches."""
    backfill_missing_history_files()
    path = Path(config.MODEL_DEEP_CACHE_PATH)
    if not force and cache_is_fresh(path, 7, date_keys=["_updated", "last_updated", "_model_updated"]):
        print("Model deep cache fresh (<7 days) — skipping web search")
        render_only()
        return

    from src import model_tracker

    latest = load_latest_daily_payload()
    events = model_tracker.append_daily_model_events(latest.get("stories") or [])
    print("Model-only refresh — cooling off 60s before web search...")
    time.sleep(60)
    try:
        model_tracker.refresh_model_deep_cache(events)
    except Exception as exc:
        print(f"Model-only refresh failed: {exc}")
        print("Keeping existing model cache and re-rendering.")
    render_only()


def run_monthly_only(force: bool = False) -> None:
    """Refresh monthly strengths/weaknesses only, then re-render dashboard."""
    backfill_missing_history_files()
    history = load_model_sentiment_history()
    path = Path(config.MODEL_STRENGTHS_CACHE_PATH)
    if not force and cache_is_fresh(path, 28, date_keys=["_updated", "last_updated", "_strengths_updated"]):
        print("Model strengths cache fresh — skipping monthly synthesis")
        render_only()
        return

    from src import model_tracker

    print("Monthly-only refresh — cooling off 60s before synthesis...")
    time.sleep(60)
    try:
        model_tracker.refresh_model_strengths_cache(history)
    except Exception as exc:
        print(f"Monthly-only refresh failed: {exc}")
        print("Keeping existing strengths cache and re-rendering.")
    render_only()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Intelligence Dashboard pipeline")
    parser.add_argument("--render-only", action="store_true", help="Re-render from saved JSON without any API calls")
    parser.add_argument("--daily", action="store_true", help="Run lightweight daily pipeline using existing weekly/monthly caches")
    parser.add_argument("--finance-only", action="store_true", help="Refresh finance cache only, then re-render")
    parser.add_argument("--model-only", action="store_true", help="Refresh model deep cache only, then re-render")
    parser.add_argument("--monthly-only", action="store_true", help="Refresh monthly strengths/weaknesses only, then re-render")
    parser.add_argument("--force", action="store_true", help="Bypass cache freshness guards for one-off manual backfills")
    args = parser.parse_args()
    if args.render_only:
        render_only()
    elif args.finance_only:
        run_finance_only(force=args.force)
    elif args.model_only:
        run_model_only(force=args.force)
    elif args.monthly_only:
        run_monthly_only(force=args.force)
    elif args.daily:
        run_pipeline(mode="daily", force=args.force)
    else:
        run_pipeline(mode="full", force=args.force)
