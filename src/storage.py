"""
Storage layer — read and write daily JSON files.
For now everything is local. Easy to swap in GCS or Drive later.
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Optional

import config


def ensure_dirs():
    """Create output directories if missing."""
    for d in [config.OUTPUT_DIR, config.DAILY_DATA_DIR,
              config.WEEKLY_STATS_DIR, config.DASHBOARD_DIR]:
        Path(d).mkdir(parents=True, exist_ok=True)


def save_daily_data(payload: Dict, target_date: Optional[date] = None) -> str:
    """Save the day's structured analysis to daily-data/YYYY-MM-DD.json."""
    ensure_dirs()
    d = target_date or date.today()
    path = Path(config.DAILY_DATA_DIR) / f"{d.isoformat()}.json"
    payload = {**payload, "_saved_at": datetime.now().isoformat(), "_date": d.isoformat()}
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"Daily data saved: {path}")
    return str(path)


def load_daily_data(target_date: date) -> Optional[Dict]:
    """Load a specific day's JSON file, returns None if not present."""
    path = Path(config.DAILY_DATA_DIR) / f"{target_date.isoformat()}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_recent_dates(n: int = 30) -> list:
    """List up to N most recent date files we have on disk."""
    p = Path(config.DAILY_DATA_DIR)
    if not p.exists():
        return []
    files = sorted(p.glob("*.json"), reverse=True)
    return [f.stem for f in files[:n]]


def save_dashboard(html: str, filename: str = "latest.html") -> str:
    """Write the rendered HTML dashboard.

    Phase 2 (PLAN sec.3, sec.11.13): also writes index.html as a meta-refresh
    redirect to latest.html, so the bare GitHub Pages URL works.
    """
    ensure_dirs()
    path = Path(config.DASHBOARD_DIR) / filename
    path.write_text(html, encoding="utf-8")
    print(f"Dashboard saved: {path}")

    # Also write index.html — small redirect that points at latest.html.
    # We import lazily to avoid a circular import (render imports config too).
    if filename == "latest.html":
        try:
            from src.render import render_index_redirect
            index_path = Path(config.DASHBOARD_DIR) / "index.html"
            index_path.write_text(render_index_redirect(), encoding="utf-8")
            print(f"Index redirect saved: {index_path}")
        except Exception as exc:
            # Don't fail the pipeline if redirect generation hiccups; the
            # dashboard itself has been saved successfully.
            print(f"  (index.html redirect skipped: {exc})")

    return str(path)
