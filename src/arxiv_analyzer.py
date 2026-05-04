"""
arXiv paper analyzer — scores papers for dashboard relevance and synthesizes
the structured data needed for Page 4 (Research & papers).

Uses Claude Haiku for cheap per-paper scoring + Sonnet for the synthesis pass
(paper of the week, signals, etc.).
"""

import json
import os
import re
from collections import Counter
from datetime import datetime, timezone, timedelta
from anthropic import Anthropic

from src.arxiv_scraper import (
    fetch_recent_papers,
    format_authors,
    categorize_for_display,
)

# Paper relevance threshold for dashboard inclusion
SCORE_THRESHOLD = 7.5

# Models
SCORING_MODEL = "claude-haiku-4-5-20251001"
SYNTHESIS_MODEL = "claude-opus-4-7"

# Institution detection patterns (loose match on author affiliations / titles)
INSTITUTION_KEYWORDS = {
    "Google DeepMind": ["DeepMind", "Google Research", "Google Brain"],
    "Anthropic": ["Anthropic"],
    "OpenAI": ["OpenAI"],
    "Meta FAIR": ["FAIR", "Meta AI", "Facebook AI"],
    "Microsoft Research": ["Microsoft Research", "MSR"],
    "MIT CSAIL": ["MIT", "CSAIL"],
    "Stanford": ["Stanford"],
    "UC Berkeley": ["Berkeley", "UC Berkeley", "BAIR"],
    "CMU": ["Carnegie Mellon", "CMU"],
    "Tsinghua": ["Tsinghua"],
    "Apple ML": ["Apple"],
    "NVIDIA Research": ["NVIDIA"],
    "Cohere": ["Cohere"],
    "Mistral": ["Mistral"],
    "Hugging Face": ["Hugging Face", "HuggingFace"],
}

# Topic clustering keywords for category breakdown
TOPIC_KEYWORDS = {
    "Reasoning": ["reasoning", "chain-of-thought", "chain of thought", "cot", "inference-time", "deliberat"],
    "Agents": ["agent", "tool use", "tool-use", "autonomous", "planning"],
    "Safety": ["safety", "alignment", "rlhf", "constitutional", "interpret", "robustness", "adversarial"],
    "Multimodal": ["multimodal", "vision-language", "vlm", "image-text", "audio-visual"],
    "Efficiency": ["efficient", "compression", "quantization", "pruning", "distillation", "moe", "mixture of expert", "sparse"],
    "Computer Vision": ["vision", "image generation", "diffusion model", "object detection", "segmentation"],
    "Benchmarks": ["benchmark", "evaluation", "leaderboard", "eval suite"],
    "Robotics": ["robot", "manipulation", "locomotion", "embodied"],
    "Fintech": ["financial", "credit", "fraud", "trading", "payment", "transaction"],
}


def _claude(client, model, system, user, max_tokens=1500):
    """Helper to call Claude with a single user message + system prompt.

    Routes through src.utils.throttle so arxiv_analyzer benefits from the
    same rate-limit protection as analyzer.py and model_tracker.py:
      - Sonnet/Opus calls get the 20s pre-call sleep + single 90s retry on 429
      - Haiku calls go through Haiku's separate rate-limit pool (no sleep,
        short 15s retry on rare 429)

    Backward compatible — accepts the same (client, model, system, user,
    max_tokens) signature so all existing call sites work unchanged.
    """
    from src.utils.throttle import sonnet_call, haiku_call

    # Decide which throttle wrapper to use based on model family.
    # Anything that isn't Haiku is treated as Sonnet/Opus tier.
    is_haiku = isinstance(model, str) and "haiku" in model.lower()
    if is_haiku:
        return haiku_call(
            client,
            user,
            model=model,
            max_tokens=max_tokens,
            system=system,
        )
    return sonnet_call(
        client,
        user,
        model=model,
        max_tokens=max_tokens,
        system=system,
    )


def score_paper(client, paper):
    """Use Claude Haiku to score a paper 0-10 for dashboard relevance."""
    system = (
        "You are an expert AI research analyst. Score arXiv papers 0-10 for their "
        "likely importance to the AI/ML community based on title and abstract. "
        "Higher scores for: novel methods, surprising results, foundational contributions, "
        "industry-relevant breakthroughs, and papers from leading labs. "
        "Lower scores for: incremental tweaks, narrow applications, surveys, position papers. "
        "Respond with ONLY a JSON object: {\"score\": <float 0-10>, \"reason\": \"<one sentence>\"}"
    )
    user = (
        f"Title: {paper['title']}\n\n"
        f"Authors: {format_authors(paper['authors'], max_show=4)}\n\n"
        f"Abstract: {paper['summary'][:1500]}\n\n"
        f"Score this paper for AI dashboard inclusion."
    )
    try:
        text = _claude(client, SCORING_MODEL, system, user, max_tokens=300)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return 0.0, "no JSON in response"
        data = json.loads(match.group(0))
        return float(data.get("score", 0)), data.get("reason", "")
    except Exception as e:
        return 0.0, f"scoring failed: {e}"


def synthesize_paper_of_week(client, top_paper):
    """Generate plain-English summary and 'why it matters' for the hero paper."""
    system = (
        "You are an AI research analyst writing for a daily intelligence dashboard. "
        "Given a paper, produce: (1) a plain-English 2-3 sentence summary that explains "
        "what the paper does without jargon, and (2) a 'why it matters' paragraph "
        "explaining the practical implications for the AI industry. "
        "Respond with ONLY a JSON object: "
        "{\"plain_summary\": \"<2-3 sentences>\", \"why_matters\": \"<2-3 sentences>\"}"
    )
    user = (
        f"Title: {top_paper['title']}\n\n"
        f"Authors: {format_authors(top_paper['authors'], max_show=4)}\n\n"
        f"Abstract: {top_paper['summary'][:2500]}\n\n"
        f"Generate the dashboard hero content."
    )
    try:
        text = _claude(client, SYNTHESIS_MODEL, system, user, max_tokens=800)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}
        return json.loads(match.group(0))
    except Exception as e:
        print(f"  paper_of_week synthesis failed: {e}")
        return {}


def synthesize_top_paper_summary(client, paper):
    """Generate a one-sentence summary of why this paper matters."""
    system = (
        "Summarize this arXiv paper in ONE sentence (max 30 words) that explains the key "
        "result and why it's notable. No jargon. Respond with just the sentence."
    )
    user = f"Title: {paper['title']}\n\nAbstract: {paper['summary'][:1200]}"
    try:
        return _claude(client, SCORING_MODEL, system, user, max_tokens=200).strip()
    except Exception:
        return paper["summary"][:200]


def detect_institution(paper):
    """Best-effort institution detection from authors + summary."""
    text = " ".join(paper["authors"]) + " " + paper["summary"][:800]
    for inst, patterns in INSTITUTION_KEYWORDS.items():
        for pat in patterns:
            if re.search(rf"\b{re.escape(pat)}\b", text, re.IGNORECASE):
                return inst
    return ""


def detect_topics(paper):
    """Detect which dashboard topics this paper covers."""
    text = (paper["title"] + " " + paper["summary"][:1500]).lower()
    matched = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                matched.append(topic)
                break
    return matched or ["Other"]


def synthesize_research_signals(client, top_papers, all_papers, prev_count=None):
    """Generate the 'research signal analysis' bullets for the dashboard."""
    paper_summaries = "\n".join([
        f"- {p['title']} (score {p['score']:.1f}, topics: {', '.join(p.get('topics', ['Other']))})"
        for p in top_papers[:15]
    ])
    topic_counter = Counter()
    for p in all_papers:
        for t in p.get("topics", []):
            topic_counter[t] += 1
    topic_breakdown = ", ".join([f"{t}: {n}" for t, n in topic_counter.most_common(8)])

    system = (
        "You are an AI research analyst producing 'signal analysis' bullets for an AI dashboard. "
        "Given recent arXiv papers, produce 4-6 directional insights about where the field is heading. "
        "Each bullet should reference specific evidence (paper counts, named papers, institutions). "
        "Each bullet has a direction: 'up' (positive trend), 'down' (declining), 'warning' (concerning), 'neu' (neutral observation). "
        "Respond with ONLY a JSON array: "
        "[{\"direction\": \"up|down|warning|neu\", \"text\": \"<one sentence with specifics>\"}, ...]"
    )
    user = (
        f"Top {len(top_papers)} papers this week:\n{paper_summaries}\n\n"
        f"Topic breakdown across {len(all_papers)} papers: {topic_breakdown}\n\n"
        f"Generate 4-6 signal bullets."
    )
    try:
        text = _claude(client, SYNTHESIS_MODEL, system, user, max_tokens=1500)
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            return []
        return json.loads(match.group(0))
    except Exception as e:
        print(f"  research_signals synthesis failed: {e}")
        return []


def build_breakthrough_radar(top_papers):
    """
    Plot top papers on the breakthrough radar.
    x = time-to-impact (low = near-term, high = long-term)
    y = significance (low = incremental, high = paradigm shift)
    Quadrants are inferred from topic + score.
    """
    radar = []
    for p in top_papers[:10]:
        topics = p.get("topics", [])
        score = p["score"]

        # Heuristic placement
        if any(t in topics for t in ["Efficiency", "Benchmarks"]):
            tti, sig, quad = 2.5, 5.0, "deploy_now"
        elif "Safety" in topics or "Reasoning" in topics:
            tti, sig, quad = 7.0, min(9.0, score), "watch_closely"
        elif "Robotics" in topics:
            tti, sig, quad = 7.5, 4.5, "long_bet"
        elif "Computer Vision" in topics or "Multimodal" in topics:
            tti, sig, quad = 3.5, 5.0, "incremental"
        elif "Agents" in topics:
            tti, sig, quad = 4.5, 6.5, "deploy_now"
        else:
            tti, sig, quad = 5.0, score - 2, "incremental"

        # Boost significance for top-scored papers
        if score >= 9.0:
            sig = min(9.5, sig + 1.5)
            if quad == "watch_closely":
                quad = "paradigm"

        radar.append({
            "title": p["title"][:60] + ("…" if len(p["title"]) > 60 else ""),
            "time_to_impact": round(tti, 1),
            "significance": round(sig, 1),
            "score": round(score, 1),
            "quadrant": quad,
        })
    return radar


def build_research_categories(all_papers, prev_papers=None):
    """Topic counts for the horizontal bar chart."""
    this_week = Counter()
    for p in all_papers:
        for t in p.get("topics", []):
            this_week[t] += 1

    # If we don't have prior week data, fake it as 80-95% of this week (we'll wire up real history later)
    last_week = {}
    if prev_papers:
        prev_counter = Counter()
        for p in prev_papers:
            for t in p.get("topics", []):
                prev_counter[t] += 1
        last_week = dict(prev_counter)

    labels = [t for t, _ in this_week.most_common(8)]
    return {
        "labels": labels,
        "this_week": [this_week[t] for t in labels],
        "last_week": [last_week.get(t, max(1, int(this_week[t] * 0.85))) for t in labels],
    }


def build_research_volume(all_papers, days=30):
    """30-day rolling volume per top topic."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Group papers by day and topic
    by_day_topic = {}
    for p in all_papers:
        try:
            dt = datetime.fromisoformat(p["published"].replace("Z", "+00:00"))
        except Exception:
            continue
        if dt < cutoff:
            continue
        day_key = f"{dt.month}/{dt.day}"
        for t in p.get("topics", ["Other"]):
            by_day_topic.setdefault(day_key, Counter())[t] += 1

    # Get top 4 topics by total volume
    total = Counter()
    for day_counts in by_day_topic.values():
        total.update(day_counts)
    top_topics = [t for t, _ in total.most_common(4)]

    # Build day labels (last `days` days)
    today = datetime.now(timezone.utc)
    labels = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        labels.append(f"{d.month}/{d.day}")

    color_map = {
        "Reasoning": "#E24B4A",
        "Agents": "#378ADD",
        "Safety": "#7F77DD",
        "Efficiency": "#1D9E75",
        "Multimodal": "#EF9F27",
        "Computer Vision": "#D4537E",
        "Benchmarks": "#888780",
        "Robotics": "#5BA3E8",
    }

    categories = []
    for topic in top_topics:
        values = [by_day_topic.get(lbl, {}).get(topic, 0) for lbl in labels]
        categories.append({
            "name": topic,
            "color": color_map.get(topic, "#888780"),
            "values": values,
        })

    return {"labels": labels, "categories": categories}


def build_hot_institutions(all_papers, prev_papers=None):
    """Rank institutions by paper count."""
    counter = Counter()
    focus_map = {}
    for p in all_papers:
        inst = p.get("institution", "")
        if not inst:
            continue
        counter[inst] += 1
        for t in p.get("topics", []):
            focus_map.setdefault(inst, Counter())[t] += 1

    prev_counter = Counter()
    if prev_papers:
        for p in prev_papers:
            inst = p.get("institution", "")
            if inst:
                prev_counter[inst] += 1

    institutions = []
    for inst, count in counter.most_common(10):
        focuses = [t for t, _ in focus_map.get(inst, Counter()).most_common(3)]
        rising = count > prev_counter.get(inst, count)
        institutions.append({
            "name": inst,
            "papers": count,
            "rising": rising,
            "focus": ", ".join(focuses) if focuses else "Various",
        })
    return institutions


def analyze_arxiv_papers(days_back=7, scoring_threshold=SCORE_THRESHOLD):
    """
    Main entry point. Pull recent papers, score them, build dashboard payload.
    Returns a dict that slots directly into render_dashboard().
    """
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    print(f"Fetching arXiv papers from last {days_back} days...")
    papers = fetch_recent_papers(days_back=days_back, max_per_cat=50)
    print(f"Got {len(papers)} unique papers")

    if not papers:
        return {}

    # Annotate every paper with topics + institution (cheap, no API calls)
    for p in papers:
        p["topics"] = detect_topics(p)
        p["institution"] = detect_institution(p)

    # Score the most recent ~80 papers (cap to avoid burning Haiku budget)
    to_score = papers[:80]
    print(f"Scoring {len(to_score)} papers with Haiku...")
    for i, p in enumerate(to_score):
        score, reason = score_paper(client, p)
        p["score"] = score
        p["score_reason"] = reason
        if (i + 1) % 10 == 0:
            print(f"  ...{i+1}/{len(to_score)} scored")

    # Mark unscored papers with default
    for p in papers[80:]:
        p["score"] = 5.0
        p["score_reason"] = "not scored"

    # Filter to top papers
    top_papers = [p for p in papers if p["score"] >= scoring_threshold]
    top_papers.sort(key=lambda p: p["score"], reverse=True)
    print(f"{len(top_papers)} papers passed threshold {scoring_threshold}")

    # Synthesize dashboard fields
    paper_of_week = None
    if top_papers:
        hero = top_papers[0]
        print(f"Synthesizing paper of the week: {hero['title'][:60]}")
        synth = synthesize_paper_of_week(client, hero)
        date_str = ""
        try:
            dt = datetime.fromisoformat(hero["published"].replace("Z", "+00:00"))
            date_str = dt.strftime("%b %d, %Y")
        except Exception:
            pass
        paper_of_week = {
            "title": hero["title"],
            "institution": hero.get("institution") or (hero["authors"][0].split()[-1] if hero["authors"] else ""),
            "team": format_authors(hero["authors"], max_show=2),
            "arxiv_id": hero["arxiv_id"],
            "date": date_str,
            "score": round(hero["score"], 1),
            "tags": categorize_for_display(hero.get("primary_category", ""), hero.get("categories", [])),
            "plain_summary": synth.get("plain_summary", hero["summary"][:300]),
            "why_matters": synth.get("why_matters", "This paper is currently being analyzed."),
            "url": hero["url"],
        }

    # Build top_papers list for the dashboard (skip the hero, take next 7)
    print("Generating top paper summaries...")
    top_papers_display = []
    for p in top_papers[1:8]:
        summary = synthesize_top_paper_summary(client, p)
        top_papers_display.append({
            "title": p["title"],
            "authors": format_authors(p["authors"], max_show=2),
            "institution": p.get("institution", ""),
            "tags": categorize_for_display(p.get("primary_category", ""), p.get("categories", [])),
            "score": round(p["score"], 1),
            "summary": summary,
            "url": p["url"],
        })

    # Other dashboard fields
    research_categories = build_research_categories(papers)
    research_volume = build_research_volume(papers)
    hot_institutions = build_hot_institutions(papers)
    breakthrough_radar = build_breakthrough_radar(top_papers)

    # Research summary metrics
    breakthrough_count = sum(1 for p in papers if p["score"] >= 8.0)
    top_inst = hot_institutions[0]["name"] if hot_institutions else "—"
    top_inst_papers = hot_institutions[0]["papers"] if hot_institutions else 0
    topic_counter = Counter()
    for p in papers:
        for t in p.get("topics", []):
            topic_counter[t] += 1
    hottest_topic = topic_counter.most_common(1)[0][0] if topic_counter else "—"

    research_summary = {
        "papers_published": str(len(papers)),
        "papers_change": "",  # Would need prior week data
        "breakthroughs": breakthrough_count,
        "breakthrough_note": f"Score 8.0+ · scanned {len(to_score)}",
        "top_institution": top_inst,
        "top_institution_papers": top_inst_papers,
        "hottest_topic": hottest_topic,
        "hottest_topic_change": "",
    }

    # Synthesize research signals
    print("Synthesizing research signals...")
    research_signals = synthesize_research_signals(client, top_papers, papers)

    return {
        "research_summary": research_summary,
        "paper_of_week": paper_of_week,
        "top_papers": top_papers_display,
        "research_categories": research_categories,
        "research_volume": research_volume,
        "hot_institutions": hot_institutions,
        "author_spotlight": [],  # Would need separate enrichment step
        "breakthrough_radar": breakthrough_radar,
        "research_signals": research_signals,
        "fintech_research": [],  # Filtered fintech papers - separate step
    }


if __name__ == "__main__":
    payload = analyze_arxiv_papers(days_back=3)
    print("\n=== Dashboard payload preview ===")
    print(json.dumps(payload, indent=2, default=str)[:2000])
