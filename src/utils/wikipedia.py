"""
Wikipedia photo lookup for Page 2 key people quotes.

Uses Wikipedia's free REST API to find a public-domain or CC-licensed
thumbnail photo for a person. Falls back to None gracefully when no
photo exists, so callers can use a colored-initial fallback.

No authentication required. Reasonable rate (no formal limit, but we
cache results in memory for the duration of a run).
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Optional

USER_AGENT = "ai-dashboard/1.0 (https://github.com/iraklicheishvili/ai-dashboard)"
WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
TIMEOUT_SECONDS = 8

# Per-run cache to avoid duplicate lookups for same name
_photo_cache: dict = {}


def fetch_person_photo(name: str) -> Optional[str]:
    """Look up a person's Wikipedia thumbnail URL.

    Returns the thumbnail URL if found, None otherwise.
    Cached per session — multiple calls for same name hit cache.

    Wikipedia thumbnails are hotlink-friendly and copyright-clean.
    """
    if not name or not isinstance(name, str):
        return None

    name_clean = name.strip()
    if not name_clean:
        return None

    # Cache hit
    if name_clean in _photo_cache:
        return _photo_cache[name_clean]

    # Wikipedia uses underscores for spaces and URL-encodes the rest
    title = urllib.parse.quote(name_clean.replace(" ", "_"))
    url = WIKI_SUMMARY_URL.format(title=title)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        # 404, timeout, network error — all benign, fall through to None
        _photo_cache[name_clean] = None
        return None

    # Wikipedia returns 'thumbnail' for pages with images
    thumbnail = data.get("thumbnail") or {}
    photo_url = thumbnail.get("source")

    # Sanity check — must be an image URL
    if not photo_url or not isinstance(photo_url, str):
        _photo_cache[name_clean] = None
        return None

    if not photo_url.startswith("https://"):
        _photo_cache[name_clean] = None
        return None

    _photo_cache[name_clean] = photo_url
    return photo_url


def initials(name: str) -> str:
    """Generate fallback initials from a name (for the colored-circle avatar)."""
    if not name:
        return "?"
    parts = name.strip().split()
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()
