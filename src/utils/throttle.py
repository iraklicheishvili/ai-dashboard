"""
Rate-limit-safe wrapper around Anthropic Messages API.

Free tier: 30,000 input tokens/min for Sonnet. Web search calls ingest
~15-20K tokens of search result content, so two consecutive calls without
a pause will trigger a 429.

This module provides:
  - sonnet_call(): standard Sonnet synthesis (20s pre-call sleep)
  - sonnet_web_search(): Sonnet with web_search tool (40s pre-call sleep)
  - haiku_call(): Haiku scoring/classification (no sleep — separate rate-limit pool)

Sleep happens BEFORE the call so the very first call in a fresh session
also gets protection. If you know you've been quiet for >60s, you can skip
the sleep with `skip_sleep=True`.

On rate-limit failure (429), the call retries once after a 90s sleep.
On second failure, the exception propagates so the caller can save progress.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from anthropic import RateLimitError

from src.utils.json_extract import extract_text_from_response


# Sleep durations in seconds — tuned for free-tier 30K tokens/min limit
WEB_SEARCH_SLEEP = 40
SONNET_SLEEP = 20

# Web search tool spec (Anthropic native, March 2025 version still works)
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
}


def _sleep_with_message(seconds: int, label: str) -> None:
    """Sleep with a brief log line so terminal output explains the pause."""
    if seconds > 0:
        print(f"    (waiting {seconds}s for rate limit window — {label})")
        time.sleep(seconds)


def sonnet_call(
    client: Anthropic,
    prompt: str,
    *,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 1500,
    skip_sleep: bool = False,
) -> str:
    """Plain Sonnet synthesis call with rate-limit safety.

    Returns the model's text response. Returns empty string on failure.
    """
    if not skip_sleep:
        _sleep_with_message(SONNET_SLEEP, "sonnet")

    try:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return extract_text_from_response(resp)
    except RateLimitError:
        # Single retry after extended cool-off
        print("    rate limit hit — retrying after 90s")
        time.sleep(90)
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return extract_text_from_response(resp)
        except Exception as exc:
            print(f"    sonnet_call retry failed: {exc}")
            raise


def sonnet_web_search(
    client: Anthropic,
    prompt: str,
    *,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 2500,
    max_uses: int = 3,
    skip_sleep: bool = False,
) -> str:
    """Sonnet call with web_search tool enabled.

    Each call typically ingests 15-20K tokens of search results, so the
    pre-call sleep is longer (40s) than for plain synthesis.
    """
    if not skip_sleep:
        _sleep_with_message(WEB_SEARCH_SLEEP, "web search")

    tool = {**WEB_SEARCH_TOOL, "max_uses": max_uses}

    try:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            tools=[tool],
        )
        return extract_text_from_response(resp)
    except RateLimitError:
        print("    rate limit hit on web search — retrying after 90s")
        time.sleep(90)
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                tools=[tool],
            )
            return extract_text_from_response(resp)
        except Exception as exc:
            print(f"    sonnet_web_search retry failed: {exc}")
            raise


def haiku_call(
    client: Anthropic,
    prompt: str,
    *,
    model: str = "claude-haiku-4-5",
    max_tokens: int = 800,
) -> str:
    """Haiku call for scoring/classification.

    No sleep — Haiku has a separate rate-limit pool that's much higher,
    and Haiku calls are short. Single retry on rate limit just in case.
    """
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return extract_text_from_response(resp)
    except RateLimitError:
        time.sleep(15)
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return extract_text_from_response(resp)
        except Exception as exc:
            print(f"    haiku_call retry failed: {exc}")
            return ""
