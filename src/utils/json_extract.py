"""
Shared JSON extraction utility used by every analyzer.

Handles the various shapes Claude can return:
  - Plain JSON object/array
  - JSON wrapped in ```json ... ``` fences
  - JSON with prose preamble before/after
  - JSON with trailing commentary

Falls back gracefully — returns None for unparseable input rather than raising.
Callers decide how to handle None (typically: empty list/dict default).
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional


def extract_json(text: str) -> Optional[Any]:
    """Extract a JSON object or array from a model response.

    Tries in order:
      1. Fenced ```json ... ``` blocks
      2. First balanced { ... } object
      3. First balanced [ ... ] array

    Returns the parsed value, or None if no valid JSON found.
    Never raises — callers should treat None as "no data".
    """
    if not text or not isinstance(text, str):
        return None

    text = text.strip()
    if not text:
        return None

    # 1. Try fenced ```json ... ``` or ``` ... ``` blocks
    fence_match = re.search(
        r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```",
        text,
        re.DOTALL,
    )
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass  # Fall through to next strategy

    # 2/3. Try balanced { ... } or [ ... ] — whichever appears first
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start >= 0 and end > start:
            candidate = text[start:end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

    return None


def extract_text_from_response(response) -> str:
    """Pull the final text answer from an Anthropic Messages response.

    Handles both plain text responses and responses containing tool use
    (e.g. web search) by concatenating all text blocks.
    """
    if response is None or not hasattr(response, "content"):
        return ""
    parts = []
    for block in response.content:
        if hasattr(block, "type") and block.type == "text":
            parts.append(block.text)
    return "\n".join(parts).strip()
