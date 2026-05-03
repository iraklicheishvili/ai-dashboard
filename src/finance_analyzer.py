"""
Finance analyzer for Page 3 of the AI Intelligence Dashboard.

Pulls real-world AI funding/valuation/M&A data via Anthropic's native
web search tool, then uses Sonnet for synthesis (the "money flow" insights
and fintech strategic angle).

Designed to run WEEKLY (Mondays) — the result is cached to
output/finance-cache.json and re-used by the daily pipeline on other days.

Cost per weekly run (~$0.20):
  - 6 web searches @ $10/1000 = ~$0.06
  - Sonnet synthesis: ~$0.14

Throttled with 60s sleeps between every Sonnet call to stay under the
30K tokens/min free-tier rate limit. Total runtime: ~7 min.

Resumable: progress is saved to output/finance-progress.json after every
step, so a rate-limit failure mid-run can be retried without re-paying for
completed steps. The progress file is deleted on successful completion.
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from anthropic import Anthropic


# Models
SONNET_MODEL = "claude-sonnet-4-6"

# Web search tool spec
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 3}

# Throttle (seconds) before each Sonnet call to stay under 30K input tokens/min
THROTTLE_SECONDS = 60


# ============================================================
# Date context — anchor model on actual current date
# ============================================================

def _date_context() -> str:
    """Returns a date anchor block to prepend to every prompt.

    Without this, the model often defaults to its training-cutoff dates
    (e.g. 2025) when web searching, returning stale archived content
    instead of current news.
    """
    today = date.today()
    two_weeks_ago = today - timedelta(days=14)
    one_month_ago = today - timedelta(days=30)
    return f"""IMPORTANT DATE CONTEXT:
- Today's date is {today.strftime('%B %d, %Y')} ({today.isoformat()}).
- The current year is {today.year}.
- "This week" means {today - timedelta(days=7):%B %d} to {today:%B %d, %Y}.
- "Past 2 weeks" means after {two_weeks_ago:%B %d, %Y}.
- "Past 30 days" means after {one_month_ago:%B %d, %Y}.

When you search the web, only return results from these recent date ranges.
Reject any older content that appears in search results — those are stale.
All dates in your output should be in {today.year} (or late {today.year - 1} if explicitly within range).

"""


# ============================================================
# Web search & response helpers
# ============================================================

def _extract_text(response) -> str:
    """Pull the final text answer from a Claude response with web search."""
    out = []
    for block in response.content:
        if hasattr(block, "type") and block.type == "text":
            out.append(block.text)
    return "\n".join(out).strip()


def _ws_search(client: Anthropic, prompt: str, max_uses: int = 3) -> str:
    """Run a single web-search-enabled Claude call and return text.

    Throttled before each call to stay under the 30K tokens/min rate limit.
    """
    print(f"    (waiting {THROTTLE_SECONDS}s for rate limit window...)")
    time.sleep(THROTTLE_SECONDS)
    tool = {**WEB_SEARCH_TOOL, "max_uses": max_uses}
    resp = client.messages.create(
        model=SONNET_MODEL,
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
        tools=[tool],
    )
    return _extract_text(resp)


def _extract_json(text: str) -> Optional[Any]:
    """Extract a JSON object/array from a model response."""
    if not text:
        return None
    m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    for opener, closer in [("{", "}"), ("[", "]")]:
        s = text.find(opener)
        e = text.rfind(closer)
        if s >= 0 and e > s:
            try:
                return json.loads(text[s:e+1])
            except json.JSONDecodeError:
                pass
    return None


# ============================================================
# Helpers for data normalization
# ============================================================

def _na(value: Any) -> str:
    """Normalize empty/missing values to 'N/A'."""
    if value is None:
        return "N/A"
    s = str(value).strip()
    if not s or s in ("-", "—", "Undisclosed", "undisclosed", "null", "None", "TBD", "tbd"):
        return "N/A"
    return s


def _strip_dollar(value: str) -> str:
    """Strip leading $ from values that come back already prefixed.

    Render template prepends $, so we should not double it.
    """
    if value is None:
        return ""
    s = str(value).strip()
    if s.startswith("$"):
        s = s[1:].strip()
    return s


def _parse_amount_billions(value: str) -> float:
    """Parse '$2B', '500M', '$1.2B' etc. to billions."""
    if not value:
        return 0.0
    s = str(value).strip().lstrip("$").upper().replace(",", "")
    m = re.match(r"([\d.]+)\s*([BM])", s)
    if not m:
        return 0.0
    val = float(m.group(1))
    return val if m.group(2) == "B" else val / 1000


# ============================================================
# Data fetchers (one per Page 3 component)
# ============================================================

def fetch_funding_rounds(client: Anthropic) -> List[Dict]:
    """Pull recent (last 14 days) AI funding rounds via web search."""
    prompt = _date_context() + """Search the web for AI startup funding rounds announced in the past 2 weeks. Focus on TechCrunch, The Information, Reuters, Bloomberg, PitchBook.

Find 8-12 notable rounds. CRITICAL — only include rounds announced in the past 2 weeks. Skip anything older.

Return ONLY a JSON array (no prose, no markdown fences) with this exact schema:

[
  {
    "company": "Company name",
    "category": "Foundation Model" | "AI Infra" | "Agents" | "Vertical SaaS" | "Fintech AI" | "Robotics" | "AI Health" | "Dev Tools",
    "amount": "2B" or "500M" (NO leading $),
    "valuation": "5B" or "N/A" (NO leading $; use N/A if undisclosed),
    "stage": "Seed" | "Series A" | "Series B" | "Series C" | "Series D" | "Series E" | "Growth" | "Strategic",
    "lead_investor": "Lead investor name(s)" or "N/A" if undisclosed,
    "date": "Mon DD" (e.g. "Apr 28") — must be from the past 2 weeks,
    "url": "Source URL"
  }
]

Use "N/A" string (not dashes, not empty) for any undisclosed field. Do NOT include a leading $ in amount/valuation values.

Return ONLY the JSON array. No explanations."""
    text = _ws_search(client, prompt, max_uses=4)
    data = _extract_json(text)
    if not isinstance(data, list):
        return []
    cleaned = []
    for r in data:
        cleaned.append({
            "company": _na(r.get("company")),
            "category": _na(r.get("category")),
            "amount": _strip_dollar(_na(r.get("amount"))),
            "valuation": _strip_dollar(_na(r.get("valuation"))),
            "stage": _na(r.get("stage")),
            "lead_investor": _na(r.get("lead_investor")),
            "date": _na(r.get("date")),
            "url": r.get("url", ""),
        })
    return cleaned


def fetch_private_valuations(client: Anthropic) -> List[Dict]:
    """Pull current top private AI company valuations."""
    prompt = _date_context() + """Search the web for the current valuations of the top private AI companies as of this week. Cross-reference TechCrunch, The Information, Bloomberg, Forbes, PitchBook.

Return ONLY a JSON array (no prose) of the top 12 private AI companies sorted by valuation desc:

[
  {
    "name": "OpenAI",
    "valuation_billions": 500,
    "last_round": "40B" (NO leading $),
    "last_round_date": "Oct 2024"
  }
]

Use the most recent confirmed post-money valuation. Candidates to evaluate: OpenAI, Anthropic, xAI, Mistral, Perplexity, Cohere, Scale AI, Databricks, Cognition, Sakana, Character.AI, Imbue, Anysphere/Cursor, Runway, ElevenLabs, Glean. Pick the top 12 by current valuation.

valuation_billions must be a number (not a string). Return ONLY the JSON array."""
    text = _ws_search(client, prompt, max_uses=3)
    data = _extract_json(text)
    if not isinstance(data, list):
        return []
    cleaned = []
    for p in data:
        try:
            val_b = float(p.get("valuation_billions", 0))
        except (TypeError, ValueError):
            val_b = 0.0
        cleaned.append({
            "name": _na(p.get("name")),
            "valuation_billions": val_b,
            "last_round": _strip_dollar(_na(p.get("last_round"))),
            "last_round_date": _na(p.get("last_round_date")),
        })
    cleaned.sort(key=lambda x: x["valuation_billions"], reverse=True)
    return cleaned[:12]


def fetch_ma_activity(client: Anthropic) -> List[Dict]:
    """Pull recent M&A and exits in AI."""
    prompt = _date_context() + """Search the web for AI-related acquisitions, IPO filings, and major strategic deals announced in the past 30 days. Skip anything older than 30 days from today.

Find 6-10 notable items. Return ONLY a JSON array (no prose) with this EXACT schema:

[
  {
    "type": "Acquisition" | "IPO filing" | "Investment" | "Acqui-hire",
    "title": "Acquirer acquires Target" or "Company files for IPO" or "Acquirer invests in Target" — short headline format,
    "detail": "One sentence describing the strategic rationale, deal value if known, and any other key context.",
    "date": "Mon DD" (e.g. "Apr 28") — must be from the past 30 days,
    "url": "Source URL"
  }
]

The "title" field should be a short headline like "Salesforce acquires Cloudera" or "Cohere files for IPO" — NOT a description.
The "detail" field has the full context.

Return ONLY the JSON array."""
    text = _ws_search(client, prompt, max_uses=3)
    data = _extract_json(text)
    if not isinstance(data, list):
        return []
    cleaned = []
    for m in data:
        cleaned.append({
            "type": _na(m.get("type")),
            "title": _na(m.get("title")),
            "detail": _na(m.get("detail")),
            "date": _na(m.get("date")),
            "url": m.get("url", ""),
        })
    return cleaned


def fetch_vc_activity(client: Anthropic) -> List[Dict]:
    """Pull top AI VCs by deal count this quarter."""
    prompt = _date_context() + """Search the web for the most active AI venture capital firms in the current quarter (this quarter of the current year). Look at PitchBook, Crunchbase, TechCrunch, Bloomberg.

Find 6-10 firms. CRITICAL — return data ONLY for firms where you found verifiable activity in the current quarter. Do NOT guess or fabricate.

Return ONLY a JSON array (no prose) of the top 8 VCs by AI deal count this quarter:

[
  {
    "firm": "Andreessen Horowitz",
    "deals": 14,
    "deployed": "2.1B" (NO leading $; use a number with B or M suffix),
    "focus": "Foundation models, infra"
  }
]

Sort by deal count desc. The "deals" field must be a number. Return ONLY the JSON array.

If you cannot find verifiable data for any AI VC, return an empty array []."""
    text = _ws_search(client, prompt, max_uses=3)
    data = _extract_json(text)
    if not isinstance(data, list):
        return []
    cleaned = []
    for v in data:
        try:
            deals = int(v.get("deals", 0))
        except (TypeError, ValueError):
            deals = 0
        cleaned.append({
            "firm": _na(v.get("firm")),
            "deals": deals,
            "deployed": _strip_dollar(_na(v.get("deployed"))),
            "focus": _na(v.get("focus")),
        })
    cleaned.sort(key=lambda x: x["deals"], reverse=True)
    return cleaned[:8]


def fetch_fintech_ai_deals(client: Anthropic) -> List[Dict]:
    """Pull recent fintech/payments AI deals — the strategic Mastercard angle."""
    prompt = _date_context() + """Search the web for AI deals, partnerships, and product launches in fintech, payments, lending, fraud detection, or banking infrastructure announced in the past 30 days. Focus on Stripe, Plaid, Ramp, Brex, Mercury, Mastercard, Visa, Adyen, Block, Klarna, Affirm, plus AI-native fintech entrants.

CRITICAL — only include deals from the past 30 days. Skip anything older.

Return ONLY a JSON array (no prose) of 4-6 most strategic items:

[
  {
    "company": "Stripe x Anthropic",
    "deal_type": "Partnership" | "Series E" | "Acquisition" | "Product Launch",
    "tags": ["Payments AI", "Embedded finance"],
    "description": "One-line description of what happened, including the date the deal was announced (e.g. 'Stripe announced on Apr 28 that...')",
    "url": "Source URL — full article link"
  }
]

The url field MUST be a real article URL, not a publication homepage. Return ONLY the JSON array."""
    text = _ws_search(client, prompt, max_uses=3)
    data = _extract_json(text)
    if not isinstance(data, list):
        return []
    cleaned = []
    for f in data:
        cleaned.append({
            "company": _na(f.get("company")),
            "deal_type": _na(f.get("deal_type")),
            "tags": f.get("tags") or [],
            "description": _na(f.get("description")),
            "url": f.get("url", ""),
        })
    return cleaned


def build_arms_race(client: Anthropic) -> Dict:
    """Build quarterly funding chart for top 5 AI labs over the last 6 quarters."""
    prompt = _date_context() + """Search the web for total capital raised per quarter by these 5 AI companies over the past 6 quarters: OpenAI, Anthropic, xAI, Mistral, Cohere.

Use the 6 most recent quarters ending with the current quarter. Values in $B. Use 0 for quarters where they didn't raise.

Return ONLY a JSON object (no prose):

{
  "quarters": ["Q4 24", "Q1 25", "Q2 25", "Q3 25", "Q4 25", "Q1 26"],
  "players": [
    {"name": "OpenAI",    "color": "#378ADD", "data": [0, 6.6, 0, 0, 0, 40]},
    {"name": "Anthropic", "color": "#EF9F27", "data": [0, 0, 0, 3.5, 0, 0]},
    {"name": "xAI",       "color": "#E24B4A", "data": [0, 6, 0, 5, 10, 0]},
    {"name": "Mistral",   "color": "#7F77DD", "data": [0.5, 0, 0, 0, 0, 0]},
    {"name": "Cohere",    "color": "#1D9E75", "data": [0, 0, 0.45, 0, 0, 0]}
  ]
}

Quarters should match the 6 most recent including the CURRENT quarter (which is the quarter containing today's date).
Return ONLY the JSON object."""
    text = _ws_search(client, prompt, max_uses=3)
    data = _extract_json(text)
    if isinstance(data, dict) and "quarters" in data and "players" in data:
        return data
    today = date.today()
    cur_q = (today.month - 1) // 3 + 1
    quarters = []
    yr = today.year
    q = cur_q
    for _ in range(6):
        quarters.append(f"Q{q} {yr % 100:02d}")
        q -= 1
        if q == 0:
            q = 4
            yr -= 1
    quarters.reverse()
    return {
        "quarters": quarters,
        "players": [
            {"name": "OpenAI",    "color": "#378ADD", "data": [0]*6},
            {"name": "Anthropic", "color": "#EF9F27", "data": [0]*6},
            {"name": "xAI",       "color": "#E24B4A", "data": [0]*6},
            {"name": "Mistral",   "color": "#7F77DD", "data": [0]*6},
            {"name": "Cohere",    "color": "#1D9E75", "data": [0]*6},
        ],
    }


# ============================================================
# Synthesis — Sonnet
# ============================================================

def synthesize_funding_summary(rounds: List[Dict]) -> Dict:
    """Build the 4 metric cards at the top of Page 3.

    Returns dict with field names matching what render.py expects:
      total_raised, total_raised_change,
      deals_closed, deals_change,
      largest_round, largest_round_company,
      median_premoney, median_trend
    """
    if not rounds:
        return {
            "total_raised": "N/A",
            "total_raised_change": "",
            "deals_closed": 0,
            "deals_change": "",
            "largest_round": "N/A",
            "largest_round_company": "",
            "median_premoney": "N/A",
            "median_trend": "flat",
        }

    amounts_b = [_parse_amount_billions(r.get("amount", "")) for r in rounds]
    amounts_b = [a for a in amounts_b if a > 0]
    total_b = sum(amounts_b)

    largest = max(rounds, key=lambda r: _parse_amount_billions(r.get("amount", "")), default={})
    largest_amount = largest.get("amount", "N/A") or "N/A"

    vals = []
    for r in rounds:
        v = r.get("valuation", "")
        if v and v != "N/A":
            v_b = _parse_amount_billions(v)
            if v_b > 0:
                vals.append(v_b)
    if vals:
        sorted_vals = sorted(vals)
        median_val = sorted_vals[len(sorted_vals)//2]
        median_str = f"{median_val:.1f}B" if median_val >= 1 else f"{int(median_val*1000)}M"
    else:
        median_str = "N/A"

    if total_b >= 1:
        total_str = f"{total_b:.1f}B"
    elif total_b > 0:
        total_str = f"{int(total_b*1000)}M"
    else:
        total_str = "N/A"

    return {
        "total_raised": total_str,
        "total_raised_change": "",
        "deals_closed": len(rounds),
        "deals_change": "",
        "largest_round": largest_amount,
        "largest_round_company": largest.get("company", ""),
        "median_premoney": median_str,
        "median_trend": "flat",
    }


def synthesize_money_flow(client: Anthropic, rounds: List[Dict], ma: List[Dict],
                          fintech: List[Dict]) -> List[Dict]:
    """Use Sonnet to generate 5-6 directional signal insights."""
    context = {
        "rounds": rounds[:15],
        "ma": ma[:8],
        "fintech": fintech[:6],
    }
    prompt = _date_context() + f"""You are an AI market analyst writing for a strategic operator with a Mastercard/payments background.

Below is recent AI capital markets activity. Generate 5-6 directional signal insights about where money is flowing, what's heating up, what's cooling.

Each signal should be:
- 1-2 sentences, sharp and specific (not generic)
- Backed by the data below (cite specific companies/rounds when relevant)
- Forward-looking — "what does this mean" not just "what happened"

Format each insight with a direction tag: "up" (heating), "down" (cooling), "flat" (neutral signal), or "alert" (anomaly worth watching).

Recent activity:
{json.dumps(context, indent=2, default=str)}

Return ONLY a JSON array, no prose:
[
  {{"direction": "up", "text": "Foundation model funding hit $X this week, up X% WoW, driven by..."}},
  ...
]"""
    print(f"    (waiting {THROTTLE_SECONDS}s for rate limit window...)")
    time.sleep(THROTTLE_SECONDS)
    resp = client.messages.create(
        model=SONNET_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = _extract_text(resp)
    data = _extract_json(text)
    return data if isinstance(data, list) else []


def synthesize_fintech_implications(client: Anthropic, fintech: List[Dict]) -> List[Dict]:
    """Add Mastercard/payments strategic angle to each fintech deal."""
    if not fintech:
        return []

    prompt = _date_context() + f"""You are writing for someone with a Mastercard/payments background. For each AI deal in fintech below, add a one-paragraph "strategic implication" that focuses on what this means for card networks (Visa/Mastercard), issuers, acquirers, or the broader payments stack.

Be specific and sharp — avoid generic statements. Connect the deal to real network/issuer/processor dynamics.

Deals:
{json.dumps(fintech, indent=2)}

Return ONLY a JSON array with the same items, but each item now has an extra "strategic" field. Preserve the "url" field exactly as provided:
[
  {{
    "company": "...",
    "deal_type": "...",
    "tags": [...],
    "description": "...",
    "strategic": "Your sharp 1-paragraph payments-industry strategic angle here.",
    "url": "..."
  }}
]"""
    print(f"    (waiting {THROTTLE_SECONDS}s for rate limit window...)")
    time.sleep(THROTTLE_SECONDS)
    resp = client.messages.create(
        model=SONNET_MODEL,
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = _extract_text(resp)
    data = _extract_json(text)
    if not isinstance(data, list):
        return [{**f, "strategic": ""} for f in fintech]
    by_company = {f.get("company"): f for f in fintech}
    for item in data:
        if not item.get("url"):
            orig = by_company.get(item.get("company"))
            if orig:
                item["url"] = orig.get("url", "")
    return data


# ============================================================
# Main orchestrator with progress caching
# ============================================================

def analyze_finance() -> Dict:
    """Run full Page 3 finance refresh. Resumable on failure."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    client = Anthropic(api_key=api_key)

    progress_path = "output/finance-progress.json"
    os.makedirs("output", exist_ok=True)

    progress = {}
    if os.path.exists(progress_path):
        try:
            with open(progress_path, "r", encoding="utf-8") as f:
                progress = json.load(f)
            print(f"Resuming from progress file: {list(progress.keys())}")
        except Exception:
            progress = {}

    def save_progress():
        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump(progress, f, indent=2, ensure_ascii=False, default=str)

    print("=" * 60)
    print("Finance analyzer — weekly refresh")
    print(f"Date anchor: {date.today().isoformat()}")
    print("=" * 60)

    if "rounds" not in progress:
        print("\n[1/6] Fetching recent AI funding rounds...")
        progress["rounds"] = fetch_funding_rounds(client)
        save_progress()
        print(f"  Got {len(progress['rounds'])} rounds")
    else:
        print(f"\n[1/6] [cached] {len(progress['rounds'])} rounds")

    if "private_ai" not in progress:
        print("\n[2/6] Fetching private AI valuations...")
        progress["private_ai"] = fetch_private_valuations(client)
        save_progress()
        print(f"  Got {len(progress['private_ai'])} private companies")
    else:
        print(f"\n[2/6] [cached] {len(progress['private_ai'])} private companies")

    if "ma" not in progress:
        print("\n[3/6] Fetching M&A activity...")
        progress["ma"] = fetch_ma_activity(client)
        save_progress()
        print(f"  Got {len(progress['ma'])} M&A items")
    else:
        print(f"\n[3/6] [cached] {len(progress['ma'])} M&A items")

    if "vc_league" not in progress:
        print("\n[4/6] Fetching VC league activity...")
        progress["vc_league"] = fetch_vc_activity(client)
        save_progress()
        print(f"  Got {len(progress['vc_league'])} VCs")
    else:
        print(f"\n[4/6] [cached] {len(progress['vc_league'])} VCs")

    if "fintech_raw" not in progress:
        print("\n[5/6] Fetching fintech AI deals...")
        progress["fintech_raw"] = fetch_fintech_ai_deals(client)
        save_progress()
        print(f"  Got {len(progress['fintech_raw'])} fintech deals")
    else:
        print(f"\n[5/6] [cached] {len(progress['fintech_raw'])} fintech deals")

    if "arms_race" not in progress:
        print("\n[6/6] Building arms race chart...")
        progress["arms_race"] = build_arms_race(client)
        save_progress()
        print(f"  Got {len(progress['arms_race'].get('quarters', []))} quarters")
    else:
        print(f"\n[6/6] [cached] arms race")

    if "money_flow" not in progress:
        print("\n[Synthesis] Money flow analysis (Sonnet)...")
        progress["money_flow"] = synthesize_money_flow(
            client, progress["rounds"], progress["ma"], progress["fintech_raw"]
        )
        save_progress()
        print(f"  Got {len(progress['money_flow'])} signals")
    else:
        print(f"\n[Synthesis] [cached] {len(progress['money_flow'])} signals")

    if "fintech_spotlight" not in progress:
        print("\n[Synthesis] Fintech strategic implications (Sonnet)...")
        progress["fintech_spotlight"] = synthesize_fintech_implications(
            client, progress["fintech_raw"]
        )
        save_progress()
        print(f"  Enriched {len(progress['fintech_spotlight'])} fintech deals")
    else:
        print(f"\n[Synthesis] [cached] {len(progress['fintech_spotlight'])} fintech deals")

    print("\n[Compute] Funding summary metrics...")
    funding_summary = synthesize_funding_summary(progress["rounds"])

    payload = {
        "_finance_updated": date.today().isoformat(),
        "funding_summary": funding_summary,
        "funding_rounds": progress["rounds"],
        "private_ai": progress["private_ai"],
        "arms_race": progress["arms_race"],
        "vc_league": progress["vc_league"],
        "money_flow": progress["money_flow"],
        "ma_tracker": progress["ma"],
        "fintech_spotlight": progress["fintech_spotlight"],
    }

    try:
        os.remove(progress_path)
    except OSError:
        pass

    print("\n" + "=" * 60)
    print("Finance analyzer complete")
    print("=" * 60)
    return payload


if __name__ == "__main__":
    payload = analyze_finance()
    print("\n=== Payload preview ===")
    print(json.dumps(payload, indent=2, default=str)[:3000])
