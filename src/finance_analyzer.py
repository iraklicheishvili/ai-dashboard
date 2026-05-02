"""
Finance analyzer for Page 3 of the AI Intelligence Dashboard.

Pulls real-world AI funding/valuation/M&A data via Anthropic's native
web search tool, then uses Haiku for categorization and Sonnet for
synthesis (the "money flow" insights and fintech strategic angle).

Designed to run WEEKLY (Mondays) — the result is cached to
output/finance-cache.json and re-used by the daily pipeline on other days.

Cost per weekly run (~$0.18-0.25):
  - 6-8 web searches @ $10/1000 = ~$0.08
  - Haiku categorization: ~$0.02
  - Sonnet synthesis: ~$0.10

Output schema matches what render.py already expects on Page 3:
  - funding_summary (4 metric cards)
  - funding_rounds (sortable table)
  - private_ai (valuation leaderboard)
  - arms_race (quarterly bar chart)
  - vc_league (top investors)
  - money_flow (directional signal insights)
  - ma_tracker (M&A timeline)
  - fintech_spotlight (Mastercard/payments angle)

Note: ETF pulse and public_ai are pulled separately by stocks.py
(yfinance) and don't go through this analyzer.
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from anthropic import Anthropic


# Models
HAIKU_MODEL = "claude-haiku-4-5"
SONNET_MODEL = "claude-sonnet-4-6"

# Web search tool spec (Feb 2026 version)
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 3}


# ============================================================
# Web search helpers
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
    
    Throttled with a 40-second sleep BEFORE each call to stay under the
    30K tokens/min free-tier rate limit (each web search call ingests
    ~15-20K tokens of search result content).
    """
    print(f"    (waiting 40s for rate limit window...)")
    time.sleep(40)
    tool = {**WEB_SEARCH_TOOL, "max_uses": max_uses}
    resp = client.messages.create(
        model=SONNET_MODEL,
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
        tools=[tool],
    )
    return _extract_text(resp)


# ============================================================
# JSON extraction helpers
# ============================================================

def _extract_json(text: str) -> Optional[Any]:
    """Extract a JSON object/array from a model response."""
    if not text:
        return None
    # Try fenced ```json blocks first
    m = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Try first { ... } or [ ... ]
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
# Data fetchers (one per Page 3 component)
# ============================================================

def fetch_funding_rounds(client: Anthropic) -> List[Dict]:
    """Pull recent (last 14 days) AI funding rounds via web search."""
    prompt = """Search the web for AI startup funding rounds announced in the past 2 weeks. Look at TechCrunch, The Information, Reuters, Bloomberg.

Find 8-12 notable rounds and return ONLY a JSON array (no prose, no markdown fences) with this exact schema for each round:

[
  {
    "company": "Company name",
    "category": "Foundation Model" | "AI Infra" | "Agents" | "Vertical SaaS" | "Fintech AI" | "Robotics" | "AI Health" | "Dev Tools",
    "amount": "$XB" or "$XXXM",
    "valuation": "$XB" or "—" if undisclosed,
    "stage": "Seed" | "Series A" | "Series B" | "Series C" | "Series D" | "Series E" | "Growth" | "Strategic",
    "lead_investor": "Lead investor name(s)",
    "date": "Mon DD" (e.g. "May 02"),
    "url": "Source URL"
  }
]

Return ONLY the JSON array. No explanations."""
    text = _ws_search(client, prompt, max_uses=4)
    data = _extract_json(text)
    return data if isinstance(data, list) else []


def fetch_private_valuations(client: Anthropic) -> List[Dict]:
    """Pull current top private AI company valuations."""
    prompt = """Search the web for the current valuations of the top private AI companies as of this week. Cross-reference TechCrunch, The Information, Bloomberg, Forbes.

Return ONLY a JSON array (no prose) of the top 12 private AI companies sorted by valuation desc:

[
  {
    "name": "OpenAI",
    "valuation_billions": 500,
    "last_round": "40B",
    "last_round_date": "Oct 2024"
  }
]

Use the most recent confirmed valuation (post-money). Include: OpenAI, Anthropic, xAI, Mistral, Perplexity, Cohere, Scale AI, Databricks, Cognition, Sakana, Character.AI, Imbue, Anysphere/Cursor, Runway, ElevenLabs — pick the top 12 by current valuation.

Return ONLY the JSON array."""
    text = _ws_search(client, prompt, max_uses=3)
    data = _extract_json(text)
    return data if isinstance(data, list) else []


def fetch_ma_activity(client: Anthropic) -> List[Dict]:
    """Pull recent M&A and exits in AI."""
    prompt = """Search the web for AI-related acquisitions, IPO filings, and major strategic deals in the past 30 days.

Return ONLY a JSON array (no prose) with 6-8 most notable items:

[
  {
    "type": "Acquisition" | "IPO Filing" | "Strategic Investment" | "Acqui-hire",
    "acquirer": "Acquirer name",
    "target": "Target name",
    "value": "$XB" or "Undisclosed",
    "date": "Mon DD",
    "description": "One-line description of strategic rationale",
    "url": "Source URL"
  }
]

Return ONLY the JSON array."""
    text = _ws_search(client, prompt, max_uses=3)
    data = _extract_json(text)
    return data if isinstance(data, list) else []


def fetch_vc_activity(client: Anthropic) -> List[Dict]:
    """Pull top AI VCs by deal count this quarter."""
    prompt = """Search the web for the most active AI venture capital firms in the current quarter. Look at PitchBook, Crunchbase, TechCrunch.

Return ONLY a JSON array (no prose) of the top 8 VCs by AI deal count this quarter:

[
  {
    "firm": "Andreessen Horowitz",
    "deals": 14,
    "deployed": "2.1B",
    "focus": "Foundation models, infra"
  }
]

Sort by deal count desc. Return ONLY the JSON array."""
    text = _ws_search(client, prompt, max_uses=2)
    data = _extract_json(text)
    return data if isinstance(data, list) else []


def fetch_fintech_ai_deals(client: Anthropic) -> List[Dict]:
    """Pull recent fintech/payments AI deals — the strategic Mastercard angle."""
    prompt = """Search the web for AI deals, partnerships, and product launches specifically in fintech, payments, lending, fraud detection, or banking infrastructure in the past 30 days. Focus on companies like Stripe, Plaid, Ramp, Brex, Mercury, Mastercard, Visa, plus AI-native fintech entrants.

Return ONLY a JSON array (no prose) of 4-6 most strategic items:

[
  {
    "company": "Stripe x Anthropic",
    "deal_type": "Partnership" | "Series E" | "Acquisition" | "Product Launch",
    "tags": ["Payments AI", "Embedded finance"],
    "description": "One-line description of what happened",
    "url": "Source URL"
  }
]

Return ONLY the JSON array."""
    text = _ws_search(client, prompt, max_uses=3)
    data = _extract_json(text)
    return data if isinstance(data, list) else []


# ============================================================
# Synthesis (Sonnet) — the IQ layer
# ============================================================

def synthesize_funding_summary(client: Anthropic, rounds: List[Dict]) -> Dict:
    """Build the 4 metric cards at the top of Page 3."""
    if not rounds:
        return {
            "total_raised": "—",
            "total_change": "",
            "deals_closed": 0,
            "deals_change": "",
            "largest_round": {"company": "—", "amount": "—"},
            "median_pre_money": "—",
            "median_change": "",
        }

    # Calculate from rounds data
    def parse_amount(s: str) -> float:
        """Parse '$2B', '$500M', etc. to $B."""
        s = s.strip().lstrip("$").upper()
        m = re.match(r"([\d.]+)([BM])", s)
        if not m:
            return 0
        val = float(m.group(1))
        return val if m.group(2) == "B" else val / 1000

    amounts_b = [parse_amount(r.get("amount", "")) for r in rounds]
    amounts_b = [a for a in amounts_b if a > 0]
    total_b = sum(amounts_b)
    largest = max(rounds, key=lambda r: parse_amount(r.get("amount", "")), default={})

    # Median valuation (parse '$XB' from valuation field, skip undisclosed)
    vals = []
    for r in rounds:
        v = r.get("valuation", "")
        if v and v != "—":
            v_b = parse_amount(v)
            if v_b > 0:
                vals.append(v_b)
    median_val = sorted(vals)[len(vals)//2] if vals else 0

    return {
        "total_raised": f"${total_b:.1f}B" if total_b >= 1 else f"${total_b*1000:.0f}M",
        "total_change": "",  # Filled by synthesis if comparing to prior week
        "deals_closed": len(rounds),
        "deals_change": "",
        "largest_round": {
            "company": largest.get("company", "—"),
            "amount": largest.get("amount", "—"),
        },
        "median_pre_money": f"${median_val:.1f}B" if median_val >= 1 else f"${median_val*1000:.0f}M",
        "median_change": "",
    }


def synthesize_money_flow(client: Anthropic, rounds: List[Dict], ma: List[Dict],
                          fintech: List[Dict]) -> List[Dict]:
    """Use Sonnet to generate 5-6 directional signal insights."""
    context = {
        "rounds": rounds[:15],
        "ma": ma[:8],
        "fintech": fintech[:6],
    }
    prompt = f"""You are an AI market analyst writing for a strategic operator with a Mastercard/payments background.

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
    print(f"    (waiting 40s for rate limit window...)")
    time.sleep(40)
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

    prompt = f"""You are writing for someone with a Mastercard/payments background. For each AI deal in fintech below, add a one-paragraph "strategic implication" that focuses on what this means for card networks (Visa/Mastercard), issuers, acquirers, or the broader payments stack.

Be specific and sharp — avoid generic statements. Connect the deal to real network/issuer/processor dynamics.

Deals:
{json.dumps(fintech, indent=2)}

Return ONLY a JSON array with the same items, but each item now has an extra "strategic" field:
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
    print(f"    (waiting 40s for rate limit window...)")
    time.sleep(40)
    resp = client.messages.create(
        model=SONNET_MODEL,
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = _extract_text(resp)
    data = _extract_json(text)
    return data if isinstance(data, list) else fintech


# ============================================================
# Arms race chart builder
# ============================================================

def build_arms_race(client: Anthropic) -> Dict:
    """Build quarterly funding chart for top 5 AI labs.
    
    Uses web search to refresh quarterly totals for OpenAI/Anthropic/xAI/Mistral/Cohere
    over the last 6 quarters."""
    prompt = """Search the web for total capital raised per quarter by these 5 AI companies over the past 6 quarters: OpenAI, Anthropic, xAI, Mistral, Cohere.

Return ONLY a JSON object (no prose) with this structure. Use 0 for quarters where they didn't raise:

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

Values in $B. Use the 6 most recent quarters ending with the current quarter. Return ONLY the JSON object."""
    text = _ws_search(client, prompt, max_uses=3)
    data = _extract_json(text)
    if isinstance(data, dict) and "quarters" in data and "players" in data:
        return data
    # Fallback to safe default
    return {
        "quarters": ["Q1 25", "Q2 25", "Q3 25", "Q4 25", "Q1 26", "Q2 26"],
        "players": [
            {"name": "OpenAI",    "color": "#378ADD", "data": [0, 0, 0, 0, 0, 0]},
            {"name": "Anthropic", "color": "#EF9F27", "data": [0, 0, 0, 0, 0, 0]},
            {"name": "xAI",       "color": "#E24B4A", "data": [0, 0, 0, 0, 0, 0]},
            {"name": "Mistral",   "color": "#7F77DD", "data": [0, 0, 0, 0, 0, 0]},
            {"name": "Cohere",    "color": "#1D9E75", "data": [0, 0, 0, 0, 0, 0]},
        ],
    }


# ============================================================
# Main orchestrator
# ============================================================

def analyze_finance() -> Dict:
    """Run full Page 3 finance refresh.
    
    Returns dict with all Page 3 component data, ready to merge into payload.
    
    Uses an intermediate cache (output/finance-progress.json) so that if any
    step fails (e.g. rate limit), restarting picks up from where it left off
    without re-paying for completed steps.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    client = Anthropic(api_key=api_key)

    progress_path = "output/finance-progress.json"
    os.makedirs("output", exist_ok=True)

    # Load any existing progress
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
        progress["money_flow"] = synthesize_money_flow(client, progress["rounds"], progress["ma"], progress["fintech_raw"])
        save_progress()
        print(f"  Got {len(progress['money_flow'])} signals")
    else:
        print(f"\n[Synthesis] [cached] {len(progress['money_flow'])} signals")

    if "fintech_spotlight" not in progress:
        print("\n[Synthesis] Fintech strategic implications (Sonnet)...")
        progress["fintech_spotlight"] = synthesize_fintech_implications(client, progress["fintech_raw"])
        save_progress()
        print(f"  Enriched {len(progress['fintech_spotlight'])} fintech deals")
    else:
        print(f"\n[Synthesis] [cached] {len(progress['fintech_spotlight'])} fintech deals")

    print("\n[Compute] Funding summary metrics...")
    funding_summary = synthesize_funding_summary(client, progress["rounds"])

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

    # Clear progress cache on successful completion
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
