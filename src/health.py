"""Pipeline health checks for the AI Intelligence Dashboard."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import config


def _age_days(path: Path) -> int:
    if not path.exists():
        return 999
    now = datetime.now(timezone.utc).timestamp()
    return int((now - path.stat().st_mtime) / 86400)


def build_health(payload: Dict[str, Any]) -> Dict[str, Any]:
    stories = payload.get("stories") or []
    top_papers = payload.get("top_papers") or []
    model_sentiments = payload.get("model_sentiments") or []
    warnings: List[str] = []

    checks = {
        "curated_stories": {"value": len(stories), "expected_min": 5, "ok": len(stories) >= 5},
        "top_papers": {"value": len(top_papers), "expected_min": 3, "ok": len(top_papers) >= 3},
        "model_sentiments": {"value": len(model_sentiments), "expected_min": 7, "ok": len(model_sentiments) >= 7},
        "finance_cache_age_days": {
            "value": _age_days(Path(config.FINANCE_CACHE_PATH)),
            "expected_max": 9,
            "ok": _age_days(Path(config.FINANCE_CACHE_PATH)) <= 9,
        },
        "github_stars_history": {
            "value": 1 if Path(config.GITHUB_STARS_HISTORY_PATH).exists() else 0,
            "expected_min": 1,
            "ok": Path(config.GITHUB_STARS_HISTORY_PATH).exists(),
        },
        "model_deep_cache": {
            "value": 1 if Path(config.MODEL_DEEP_CACHE_PATH).exists() else 0,
            "expected_min": 1,
            "ok": Path(config.MODEL_DEEP_CACHE_PATH).exists(),
        },
    }

    for name, check in checks.items():
        if not check.get("ok"):
            warnings.append(name)

    if not warnings:
        status = "healthy"
    elif len(warnings) <= 2:
        status = "degraded"
    else:
        status = "broken"

    return {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status,
        "checks": checks,
        "warnings": warnings,
    }


def save_health(payload: Dict[str, Any]) -> Dict[str, Any]:
    health = build_health(payload)
    Path(config.HEALTH_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(config.HEALTH_PATH).write_text(json.dumps(health, indent=2), encoding="utf-8")
    print(f"Health saved: {config.HEALTH_PATH} ({health['status']})")
    return health


def load_health() -> Dict[str, Any]:
    path = Path(config.HEALTH_PATH)
    if not path.exists():
        return {"status": "degraded", "warnings": ["health file missing"], "checks": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "degraded", "warnings": ["health file unreadable"], "checks": {}}
