"""
arXiv API scraper for the AI dashboard pipeline.

Pulls recent papers from cs.AI, cs.LG, cs.CL categories using arXiv's free Atom API.
No authentication required. Polite throttling per arXiv guidelines (1 req every ~3s).
"""

import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

# arXiv categories most relevant to AI/ML research
DEFAULT_CATEGORIES = [
    "cs.AI",   # Artificial Intelligence
    "cs.LG",   # Machine Learning
    "cs.CL",   # Computation and Language (NLP)
    "cs.CV",   # Computer Vision
    "cs.MA",   # Multi-agent systems
]

# Mapping arXiv category codes to display tags
CATEGORY_TAGS = {
    "cs.AI": "AI",
    "cs.LG": "Machine Learning",
    "cs.CL": "NLP",
    "cs.CV": "Computer Vision",
    "cs.MA": "Multi-agent",
    "cs.NE": "Neural Networks",
    "cs.RO": "Robotics",
    "cs.IR": "Info Retrieval",
    "stat.ML": "Statistical ML",
}

ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

USER_AGENT = "ai-dashboard/1.0 (https://github.com/iraklicheishvili/ai-dashboard)"


def _fetch_arxiv(query: str, max_results: int = 50) -> str:
    """Make a single request to the arXiv API. Returns the raw Atom XML."""
    params = {
        "search_query": query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    }
    url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def _parse_entry(entry):
    """Extract a paper dict from a single arXiv entry element."""
    def _text(tag):
        el = entry.find(f"atom:{tag}", ATOM_NS)
        return el.text.strip() if el is not None and el.text else ""

    title = " ".join(_text("title").split())
    summary = " ".join(_text("summary").split())
    arxiv_url = _text("id")
    arxiv_id = arxiv_url.rsplit("/abs/", 1)[-1] if "/abs/" in arxiv_url else arxiv_url
    published_raw = _text("published")
    try:
        published_dt = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
    except Exception:
        published_dt = datetime.now(timezone.utc)

    authors = []
    for a in entry.findall("atom:author", ATOM_NS):
        name = a.find("atom:name", ATOM_NS)
        if name is not None and name.text:
            authors.append(name.text.strip())

    categories = [c.attrib.get("term", "") for c in entry.findall("atom:category", ATOM_NS)]
    primary_cat = ""
    pc = entry.find("arxiv:primary_category", ATOM_NS)
    if pc is not None:
        primary_cat = pc.attrib.get("term", "")

    pdf_url = ""
    for link in entry.findall("atom:link", ATOM_NS):
        if link.attrib.get("title") == "pdf":
            pdf_url = link.attrib.get("href", "")
            break

    return {
        "arxiv_id": arxiv_id,
        "title": title,
        "summary": summary,
        "authors": authors,
        "categories": categories,
        "primary_category": primary_cat,
        "published": published_dt.isoformat(),
        "published_dt": published_dt,
        "url": arxiv_url,
        "pdf_url": pdf_url,
    }


def fetch_recent_papers(categories=None, days_back: int = 7, max_per_cat: int = 50) -> list:
    """
    Pull recent papers from each requested arXiv category.
    Returns a deduplicated list of paper dicts published within `days_back` days.
    """
    if categories is None:
        categories = DEFAULT_CATEGORIES

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    seen_ids = set()
    papers = []

    for cat in categories:
        try:
            xml_data = _fetch_arxiv(f"cat:{cat}", max_results=max_per_cat)
        except Exception as e:
            print(f"  arXiv fetch failed for {cat}: {e}")
            continue

        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError as e:
            print(f"  arXiv parse failed for {cat}: {e}")
            continue

        entries = root.findall("atom:entry", ATOM_NS)
        kept = 0
        for e in entries:
            paper = _parse_entry(e)
            if paper["published_dt"] < cutoff:
                continue
            if paper["arxiv_id"] in seen_ids:
                continue
            seen_ids.add(paper["arxiv_id"])
            papers.append(paper)
            kept += 1
        print(f"  {cat}: {kept} papers within {days_back} days")

        # Polite throttle per arXiv guidelines
        time.sleep(3)

    # Sort by submission date, newest first
    papers.sort(key=lambda p: p["published_dt"], reverse=True)
    return papers


def format_authors(authors: list, max_show: int = 2) -> str:
    """Format author list for display: 'Smith et al.' or 'Smith, Jones'."""
    if not authors:
        return "Unknown"
    if len(authors) == 1:
        return authors[0]
    if len(authors) <= max_show:
        return ", ".join(authors)
    last_name = authors[0].split()[-1] if authors[0] else "Unknown"
    return f"{last_name} et al. · {len(authors)} authors"


def categorize_for_display(primary_cat: str, all_cats: list) -> list:
    """Convert arXiv categories to display tags."""
    tags = []
    for cat in [primary_cat] + all_cats:
        if cat in CATEGORY_TAGS and CATEGORY_TAGS[cat] not in tags:
            tags.append(CATEGORY_TAGS[cat])
        if len(tags) >= 2:
            break
    return tags or ["Research"]


if __name__ == "__main__":
    # Quick sanity test
    papers = fetch_recent_papers(days_back=3, max_per_cat=10)
    print(f"\nGot {len(papers)} unique papers")
    for p in papers[:5]:
        print(f"  - [{p['primary_category']}] {p['title'][:80]}")
        print(f"    {format_authors(p['authors'])} · {p['arxiv_id']}")
