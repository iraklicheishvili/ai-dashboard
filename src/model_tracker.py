"""Phase 3 model intelligence for Page 2.

Runs weekly/monthly, writes persistent cache files in output/ so GitHub
Actions can carry state forward between runs.

Design goals:
- Web-search calls are batched to reduce rate-limit pressure.
- Every step is resumable and cache-first.
- Missing web-search output degrades to empty fields, never a dashboard crash.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anthropic import Anthropic
from dotenv import load_dotenv

import config
from src.utils.json_extract import extract_json
from src.utils.wikipedia import fetch_person_photo, initials

load_dotenv()

_client = None


def get_client():
    """Lazy Anthropic client."""
    global _client
    if _client is None:
        from anthropic import Anthropic
        _client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _client


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


def _date_context() -> str:
    today = date.today()
    return f"""IMPORTANT DATE CONTEXT:
- Today's date is {today.strftime('%B %d, %Y')} ({today.isoformat()}).
- The current year is {today.year}.
- Treat current public-company/product metrics as fresh only if they are from the past 6 months.
- Treat public posts/quotes as recent only if they are from the last 60 days.
- If a metric is not publicly disclosed, return \"Not disclosed\" rather than guessing.
"""


def _model_brief() -> str:
    rows = []
    for m in config.TRACKED_MODELS:
        rows.append({
            "id": m["id"],
            "name": m["name"],
            "maker": m["maker"],
            "keywords": m.get("keywords", [])[:8],
        })
    return json.dumps(rows, indent=2)


def load_model_deep_cache() -> Dict[str, Any]:
    return _read_json(Path(config.MODEL_DEEP_CACHE_PATH), {"_updated": "", "models": {}})


def load_model_strengths_cache() -> Dict[str, Any]:
    return _read_json(Path(config.MODEL_STRENGTHS_CACHE_PATH), {"_updated": "", "models": {}})


def load_model_events_history() -> Dict[str, List[Dict]]:
    return _read_json(Path(config.MODEL_EVENTS_HISTORY_PATH), {})


def append_daily_model_events(curated_stories: List[Dict]) -> Dict[str, List[Dict]]:
    """Append model-related curated stories to the 90-day events history."""
    history: Dict[str, List[Dict]] = load_model_events_history()
    model_name_to_id = {m["name"].lower(): m["id"] for m in config.TRACKED_MODELS}
    model_id_set = {m["id"] for m in config.TRACKED_MODELS}
    today_iso = date.today().isoformat()
    cutoff = date.today() - timedelta(days=90)

    for story in curated_stories:
        mentioned = story.get("model_mentioned")
        if not mentioned:
            continue
        mid = str(mentioned).strip().lower()
        model_id = model_name_to_id.get(mid) or (mid if mid in model_id_set else None)
        if not model_id:
            continue
        url = story.get("external_url") or story.get("url") or ""
        title = story.get("title") or story.get("summary") or "Model-related story"
        event = {
            "date": (story.get("created_iso") or today_iso)[:10],
            "text": title[:180],
            "url": url,
            "source": story.get("source") or story.get("subreddit") or "Curated story",
        }
        bucket = history.setdefault(model_id, [])
        if not any(e.get("url") == url and e.get("text") == event["text"] for e in bucket):
            bucket.append(event)

    for mid, events in list(history.items()):
        cleaned = []
        for e in events:
            try:
                d = date.fromisoformat(str(e.get("date", ""))[:10])
            except ValueError:
                d = date.today()
            if d >= cutoff:
                cleaned.append(e)
        history[mid] = sorted(cleaned, key=lambda e: e.get("date", ""), reverse=True)[:30]

    _write_json(Path(config.MODEL_EVENTS_HISTORY_PATH), history)
    return history


def refresh_model_deep_cache(existing_events: Optional[Dict[str, List[Dict]]] = None) -> Dict[str, Any]:
    """Weekly web-search refresh for MAU/market share/key people/recent changes."""
    print("\nModel tracker — weekly deep-dive web search")
    prompt = _date_context() + f"""
You are building a factual model-tracker dashboard.

Tracked models:
{_model_brief()}

For EACH model, return current public intelligence. Use web search. Be conservative.
Return ONLY valid JSON with this shape:
{{
  "models": {{
    "chatgpt": {{
      "mau": "string or Not disclosed",
      "market_share": "string or —",
      "buzz_volume_note": "brief public signal, or —",
      "recent_changes": [{{"date":"YYYY-MM-DD", "text":"short release/news item", "url":"https://..."}}],
      "key_people": [{{"name":"Full Name", "role":"Role", "quote":"short paraphrase or quote under 25 words", "date":"YYYY-MM-DD", "platform":"X/LinkedIn/Threads/blog", "source_url":"https://..."}}]
    }}
  }}
}}

Rules:
- Include all 7 model IDs: chatgpt, claude, gemini, deepseek, grok, copilot, llama.
- For Llama, use "Downloads" style info in mau and "Derivatives" style info in market_share.
- Key people must be current public-facing leaders/researchers/engineers tied to the model.
- Only include verifiable links. If unsure, leave arrays empty.
"""
    try:
        from src.utils.throttle import sonnet_web_search
        text = sonnet_web_search(get_client(), prompt, model=config.SONNET_MODEL, max_tokens=4500, max_uses=5)
        data = extract_json(text) or {}
    except Exception as exc:
        print(f"  model deep refresh failed: {exc}")
        return load_model_deep_cache()

    raw_models = data.get("models") if isinstance(data, dict) else {}
    if not isinstance(raw_models, dict):
        raw_models = {}

    today_iso = date.today().isoformat()
    out = {"_updated": today_iso, "models": {}}
    existing_events = existing_events or load_model_events_history()

    for m in config.TRACKED_MODELS:
        mid = m["id"]
        raw = raw_models.get(mid) if isinstance(raw_models.get(mid), dict) else {}
        people = []
        for p in list(raw.get("key_people") or [])[:8]:
            name = str(p.get("name") or "").strip()
            if not name:
                continue
            people.append({
                "name": name,
                "role": p.get("role") or "",
                "quote": p.get("quote") or "",
                "date": p.get("date") or "",
                "platform": p.get("platform") or "",
                "source_url": p.get("source_url") or p.get("url") or "",
                "photo_url": fetch_person_photo(name),
                "initials": initials(name),
            })
        recent_changes = list(raw.get("recent_changes") or [])[:10]
        # Merge weekly web-search events with daily curated story events.
        merged = []
        for e in recent_changes + list(existing_events.get(mid, [])):
            if not isinstance(e, dict):
                continue
            text_val = e.get("text") or e.get("title") or ""
            if not text_val:
                continue
            item = {"date": e.get("date") or today_iso, "text": text_val, "url": e.get("url") or e.get("source_url") or ""}
            if not any(x.get("text") == item["text"] and x.get("url") == item["url"] for x in merged):
                merged.append(item)
        out["models"][mid] = {
            "last_updated": today_iso,
            "mau": raw.get("mau") or "Not disclosed",
            "market_share": raw.get("market_share") or "—",
            "buzz_volume_note": raw.get("buzz_volume_note") or "—",
            "recent_changes": sorted(merged, key=lambda e: e.get("date", ""), reverse=True)[:10],
            "key_people": people,
        }

    _write_json(Path(config.MODEL_DEEP_CACHE_PATH), out)
    print(f"  model deep cache updated: {config.MODEL_DEEP_CACHE_PATH}")
    return out


def refresh_model_strengths_cache(history_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Monthly strengths/weaknesses synthesis."""
    print("\nModel tracker — monthly strengths/weaknesses synthesis")
    prompt = _date_context() + f"""
You are summarizing structural strengths and weaknesses of the main AI models.

Tracked models:
{_model_brief()}

Recent model sentiment/history JSON:
{json.dumps(history_payload, indent=2)[:18000]}

Return ONLY valid JSON:
{{
  "models": {{
    "chatgpt": {{"strengths": ["3-5 evidence-based bullets"], "weaknesses": ["3-5 evidence-based bullets"]}}
  }}
}}

Rules:
- Include all seven model IDs.
- No generic claims. Tie bullets to observable signals such as releases, HN discussion, ecosystem activity, benchmarks, or public company moves.
- Keep each bullet under 100 characters.
"""
    try:
        from src.utils.throttle import sonnet_call
        text = sonnet_call(get_client(), prompt, model=config.SONNET_MODEL, max_tokens=3500)
        data = extract_json(text) or {}
    except Exception as exc:
        print(f"  strengths refresh failed: {exc}")
        return load_model_strengths_cache()

    raw_models = data.get("models") if isinstance(data, dict) else {}
    if not isinstance(raw_models, dict):
        raw_models = {}

    out = {"_updated": date.today().isoformat(), "models": {}}
    for m in config.TRACKED_MODELS:
        mid = m["id"]
        raw = raw_models.get(mid) if isinstance(raw_models.get(mid), dict) else {}
        out["models"][mid] = {
            "strengths": list(raw.get("strengths") or [])[:5],
            "weaknesses": list(raw.get("weaknesses") or [])[:5],
        }
    _write_json(Path(config.MODEL_STRENGTHS_CACHE_PATH), out)
    print(f"  model strengths cache updated: {config.MODEL_STRENGTHS_CACHE_PATH}")
    return out


def attach_model_intelligence(
    model_sentiments: List[Dict],
    *,
    deep_cache: Optional[Dict[str, Any]] = None,
    strengths_cache: Optional[Dict[str, Any]] = None,
    events_history: Optional[Dict[str, List[Dict]]] = None,
) -> List[Dict]:
    """Attach cache-backed deep fields to model sentiment rows for render.py."""
    deep_cache = deep_cache or load_model_deep_cache()
    strengths_cache = strengths_cache or load_model_strengths_cache()
    events_history = events_history or load_model_events_history()
    deep_models = deep_cache.get("models", {}) if isinstance(deep_cache, dict) else {}
    strength_models = strengths_cache.get("models", {}) if isinstance(strengths_cache, dict) else {}

    enriched = []
    for row in model_sentiments:
        row2 = dict(row)
        cfg = row2.get("model_config") or {}
        mid = row2.get("model_id") or cfg.get("id")
        deep = dict(deep_models.get(mid) or {})
        strengths = strength_models.get(mid) or {}
        if strengths.get("strengths"):
            deep["strengths"] = strengths.get("strengths")
        if strengths.get("weaknesses"):
            deep["weaknesses"] = strengths.get("weaknesses")
        if not deep.get("recent_changes") and events_history.get(mid):
            deep["recent_changes"] = events_history.get(mid, [])[:10]
        row2["deep"] = deep
        enriched.append(row2)
    return enriched
