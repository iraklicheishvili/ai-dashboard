# AI Intelligence Dashboard — Build Plan

**Status as of:** May 3, 2026
**Project repo:** `github.com/iraklicheishvili/ai-dashboard`
**Live URL:** `https://iraklicheishvili.github.io/ai-dashboard/latest.html`
**Owner:** Irakli Cheishvili

This document is the single source of truth for the next development session. It captures the current state of the project, every design decision we've made, and the exact build sequence for Pages 1 and 2 plus the polish work for Pages 3 and 4.

---

## 1. Current State

### What works today
- Pipeline runs daily on GitHub Actions (manual trigger only — cron disabled)
- Page 4 (Research & Papers): fully populated from arXiv, daily refresh
- Page 3 (AI Finance): partially populated, weekly Monday refresh via web search
- Page 1 (AI Intelligence): scaffolded with mock Reddit data
- Page 2 (Model Tracker): scaffolded but Page 2 deep-dive sections are empty
- ETF + market cap data via yfinance (live, daily)
- Live deploy to GitHub Pages on every workflow run
- Finance cache committed to repo — survives across runs

### What's blocked
- Reddit API approval (~1 week wait, no ETA from Reddit)
- ETF "Trend" sparkline column on Page 3 — `stocks.py` doesn't generate `sparkline` / `sparkline_points` data the template expects

### What's missing
- All of Pages 1 and 2 deep components (real data sources beyond mocks)
- Source aggregation layer (HN, GitHub Trending, arXiv-as-stories)
- Per-model deep-dive data (MAU, market share, key people quotes)
- Disclaimers on Pages 3 and 4
- Clickable links across multiple components on Pages 3 and 4
- `index.html` redirect for the bare GitHub Pages URL
- Health check + footer status indicator
- ETF sparkline (separate stocks.py work)

---

## 2. Strategic Direction

### Reddit-skip strategy
We're moving forward without Reddit API approval. Pages 1 and 2 will be powered by:
- **Hacker News** (free public API, no auth)
- **GitHub Trending** (free public API, scrape)
- **arXiv** (already integrated)
- **Web search** (Anthropic native tool, weekly only)

When Reddit API approval comes through, integration is a config-only change — no code rewrite needed. The `sources/reddit.py` module slots into the same aggregation pattern as the others.

### Cost optimization is the primary driver
Current target: ~$10/month total Anthropic spend.

| Cadence | What runs | Approx cost per run |
|---|---|---|
| Daily | Source fetches, story scoring, daily synthesis, model sentiment, arXiv | ~$0.20 |
| Weekly (Mondays) | Page 3 finance pull + Page 2 model deep-dive (MAU/market share/key people) | ~$0.30 added |
| Monthly (1st) | Page 2 strengths/weaknesses synthesis | ~$0.03 |

Monthly total: **~$8–10**.

---

## 3. Architecture (Target State)

### File layout
```
ai-dashboard/
├── src/
│   ├── main.py                  # Orchestrator
│   ├── scraper.py               # Source aggregator (renamed from Reddit-only)
│   ├── analyzer.py              # Story scoring + daily synthesis
│   ├── render.py                # HTML renderer (refactored)
│   ├── stocks.py                # yfinance ETFs + sparklines
│   ├── storage.py               # JSON read/write + path constants
│   ├── arxiv_scraper.py         # arXiv API
│   ├── arxiv_analyzer.py        # arXiv synthesis
│   ├── finance_analyzer.py      # Page 3 finance (already built)
│   ├── model_tracker.py         # NEW — Page 2 weekly deep-dive
│   ├── health.py                # NEW — pipeline health check
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── json_extract.py      # NEW — shared JSON parser used by all analyzers
│   │   ├── throttle.py          # NEW — rate-limit-safe Sonnet caller
│   │   └── wikipedia.py         # NEW — fetch person photos (Page 2 key people)
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── reddit.py            # Existing logic, MOVED here (mock for now)
│   │   ├── hn.py                # NEW — Hacker News API
│   │   ├── github_trending.py   # NEW — GitHub Trending repos + ecosystem stars
│   │   └── arxiv_stories.py     # NEW — surface arXiv papers as Page 1 stories
│   └── mock_data.py             # Reddit mock fallback (kept)
├── prompts/
│   ├── score_story.txt          # Updated to be source-agnostic
│   ├── synthesize.txt           # Includes trending_topics + drivers
│   ├── model_sentiment.txt      # HN-aware
│   └── (Page 2/3-specific prompts inlined in analyzer files)
├── templates/                   # NEW (optional, see render refactor)
├── output/                      # All committed to repo
│   ├── daily-data/              # 30-day rolling JSON snapshots
│   ├── finance-cache.json       # Mondays
│   ├── model-deep-cache.json    # NEW — Mondays
│   ├── model-events-history.json # NEW — daily appends
│   ├── model-strengths-cache.json # NEW — monthly
│   ├── model-sentiment-history.json # NEW — daily
│   ├── github-stars-history.json # NEW — daily
│   ├── health.json              # NEW — daily status
│   └── dashboard/
│       ├── latest.html
│       └── index.html           # NEW — redirect
├── config.py                    # All paths + tracked entities
├── requirements.txt
├── .env (gitignored)
├── .gitignore
├── .github/workflows/daily.yml
└── PLAN.md (this file)
```

### render.py architectural split (CRITICAL FIX)

The page-bleed problem we fought yesterday was caused by a 1300-line monolithic template string. New approach:

```python
# render.py structure (target)

# Shell — provides outer wrapping ONCE per page
SHELL_TEMPLATE = """<!DOCTYPE html>...
{% for page in pages %}
<div id="{{ page.id }}" class="page{% if loop.first %} active{% endif %}">
{{ page.body }}
</div>
{% endfor %}
..."""

# Per-page bodies — content only, no <div id="pN"> wrapper
PAGE_1_BODY = (
    COMPONENT_PAGE1_HEADER_METRICS +
    COMPONENT_PAGE1_VOLUME_CHART +
    COMPONENT_PAGE1_TOP_STORIES +
    # ... etc
)

# Per-component templates — self-contained strings
COMPONENT_PAGE1_HEADER_METRICS = """<div class="card">..."""
```

**Outcome:** Page 1 content cannot leak into Page 2 because the shell is responsible for opening/closing each page div, not the bodies themselves.

---

## 4. Universal Standards (apply to every component, every page)

### 4.1 Disclaimer format
Every component card has a disclaimer line at the bottom:
```
Sources: [list] · [methodology note] · [refresh cadence]
```

Examples:
- `Sources: Hacker News, arXiv, GitHub Trending · Stories ranked by Claude content score · Updated daily`
- `Sources: TechCrunch, Bloomberg, PitchBook · Strategic implications by Claude Sonnet · Refreshed Mondays`

Disclaimer styling:
- Font size: 10px
- Color: `var(--text-tertiary)` (muted gray)
- Italic acceptable for distinction
- Position: bottom of card

### 4.2 Empty-state pattern
For any component with no data on a given day:
```
"No major [component purpose] today"
```

Examples: "No major fintech AI stories today", "No major AI M&A activity today", "No HN discussion this period"

### 4.3 Linkable items
Every linkable item (stories, papers, deals, quotes, etc.) must:
- Use the `.linkable` CSS class
- Cursor changes to `pointer` on hover
- Dashed underline appears on hover
- Tiny `↗` icon appears on hover (via `::after` pseudo-element)
- 150ms transition for smooth feel
- `target="_blank"` always
- Real URLs only — never fabricated

```css
.linkable {
  cursor: default;
  border-bottom: 1px solid transparent;
  transition: border-color 150ms ease, color 150ms ease;
}
.linkable:hover {
  cursor: pointer;
  border-bottom: 1px dashed var(--text-tertiary);
}
.linkable:hover::after {
  content: " ↗";
  font-size: 0.85em;
  color: var(--text-tertiary);
  margin-left: 2px;
}
```

### 4.4 Footer (every page)
```
AI Intelligence Dashboard · Updated daily · Last refresh: [date]
Sources: Hacker News · arXiv · GitHub Trending · Yahoo Finance · Web search
Curated and synthesized by Claude (Anthropic)
```
- 3 lines, centered, muted color
- "Last refresh" pulls dynamically from `{{ today }}`
- Sources list updates dynamically when Reddit comes online

### 4.5 Conditional HTML attribute pattern
**Wrong** (produces empty `style=""`):
```html
<div style="{% if not loop.first %}display:none{% endif %}">
```

**Right** (entire attribute conditional):
```html
<div{% if not loop.first %} style="display:none"{% endif %}>
```

### 4.6 Cross-platform robustness
- Use `pathlib.Path()` and `os.path.join()` — never raw path strings with `\` or `/`
- Always pass `encoding='utf-8'` to every `open()` call (avoids Windows cp1252/cp1251 crash on emoji/arrow chars)
- Use `datetime.now(timezone.utc)` not `datetime.now()` (timezone-aware)
- Always use context managers (`with open() as f:`)

### 4.7 Schema contracts
Every analyzer's output is documented with a TypedDict at the top of the file. Render.py also documents what shape it expects. When either side changes, both update in the same commit.

### 4.8 Resumable progress files
Every multi-step analyzer (`finance_analyzer`, `model_tracker`, `arxiv_analyzer`) saves intermediate results to `output/<name>-progress.json` after each step. On restart after failure, picks up where it left off. Deletes progress file on successful completion.

### 4.9 Rate-limit throttling
- 40s sleep before every Sonnet web-search call
- 20s sleep before plain Sonnet synthesis calls
- No throttle needed between Haiku calls (separate rate-limit pool)
- 60s buffer between major sections (arXiv → Page 1 → Page 2)
- Date anchor injected into every web-search prompt to prevent stale (training-cutoff) data

### 4.10 Zero terminal warnings
- No deprecation warnings (use modern APIs)
- No file-handle warnings (always use context managers)
- No encoding warnings (always specify utf-8)
- Progress logs sectioned, not spammy ("[1/8] HN..." not 80 lines of "...10/80")
- Every file passes `ast.parse` and `flake8` core checks before commit

### 4.11 Pre-render structural validator
Before sending HTML, render.py runs a validator that checks:
- All `<div id="pN" class="page">` open/close pairs are balanced
- No truncated string literals in component code
- No duplicate component definitions
- Nesting depth never goes negative

Raises `HTMLStructureError` with clear message pointing to offending component if anything is broken.

### 4.12 Universal `safe` access in templates
Wrap any nested object access:
```jinja
{% set safe = m.deep or {} %}
{{ safe.field | default('—') }}
```

Never raw `m.deep.field` access — that crashes when `deep` is missing.

---

## 5. Page 1 — AI Intelligence (FULL DESIGN)

### 1.1 Header metrics (4 cards)
- **Cards:** Total stories | Fintech stories | Top source | Most active category
- **Source:** Computed from aggregated stories
- **Frequency:** Daily
- **Cost:** $0
- **Disclaimer:** "Sources: Hacker News, arXiv, GitHub Trending"
- **Notes:** Dropped "Posts pulled" in favor of "Fintech stories" (more useful). Renamed "Top subreddit" → "Top source".

### 1.2 Story volume chart (30 days)
- **Display:** Stacked bar chart, colored by source
- **Source:** Daily JSON history (auto-aggregates from `output/daily-data/*.json`)
- **Frequency:** Daily
- **Cost:** $0
- **Subtitle:** "Curated stories per source"
- **Disclaimer:** "Sources: Hacker News, arXiv, GitHub Trending · Dashboard launched May 1, 2026"
- **Notes:** Sparse for first ~30 days; fills in over time. Honest representation chosen over synthetic backfill.

### 1.3 Top stories feed
- **Display:** 15 curated stories — title, source label, score, category tags, summary, "why it matters", clickable link
- **Sources:** HN (~70%), arXiv (~20%), GitHub Trending (~10%); Reddit additive when API approves
- **Frequency:** Daily
- **Cost:** ~$0.05 (Haiku scoring + Sonnet "why it matters")
- **Selection:** Adaptive top-15 by combined score (no fixed threshold — always shows 15 even on slow days)
- **Subtitle:** "Curated from Hacker News, arXiv, and GitHub Trending — scored by Claude"

#### Source-agnostic relevance scoring
**Step 1 — Content score (Haiku, 1-10):**
Evaluates newsworthiness, strategic significance, technical depth, specificity, fintech bonus. Source ID is metadata only — not used for scoring. Same rubric across all sources (no HN-bias).

**Step 2 — Per-source engagement normalization:**
| Source | Raw signal | Normalized 0–1 |
|---|---|---|
| HN | Points | `min(points / 1000, 1.0)` |
| arXiv | Citations + discussion | `0.7` (papers don't have viral signals) |
| GitHub | Stars-today | `min(stars / 500, 1.0)` |
| Reddit | Upvotes | `min(upvotes / 1500, 1.0)` |

**Step 3 — Combined score:**
```
final_score = (content_score * 0.85) + (engagement_normalized * 1.5)
```

**Per-story labels:**
- HN: `Hacker News · 842 pts · 234 comments` + two links (HN thread + source article)
- arXiv: `arXiv · cs.CL · 9.2 score` + arXiv abstract link
- GitHub: `GitHub · 2.1k stars today` + repo link

### 1.4 Category breakdown (donut)
- **Display:** Donut chart, top 6-7 categories
- **Source:** Primary tag of each curated story (Haiku tags during scoring)
- **Frequency:** Daily
- **Cost:** $0
- **Subtitle:** "Today's curated stories by topic"
- **Disclaimer:** "Sources: Hacker News, arXiv, GitHub Trending · Categories assigned by Claude during scoring"
- **Decision:** Use only first tag per story (clean totals match story count)

### 1.5 Trending topics
- **Display:** Ranked list with horizontal weight bars, 8-10 topics
- **Source:** Bundled into Component 1.3's Sonnet synthesis call (extracts emergent themes)
- **Frequency:** Daily
- **Cost:** $0 marginal
- **Subtitle:** "Themes emerging from today's curated stories"
- **Disclaimer:** "Sources: Hacker News, arXiv, GitHub Trending · Themes synthesized by Claude"

### 1.6 Source hot topics
- **Display:** Dropdown selector (Hacker News default | arXiv | GitHub Trending) + 7 items per source
- **Per-source metrics:** HN points / arXiv relevance score / GitHub stars-today
- **All items clickable** to source
- **Source:** Reuses Component 1.3 fetched data (kept separate per source)
- **Frequency:** Daily
- **Cost:** $0
- **Title:** "Source hot topics" (renamed from "Subreddit hot topics")
- **Subtitle:** "Top items from each source today — switch via dropdown"
- **Empty state:** "No major HN/arXiv/GitHub stories today"

### 1.7 Fintech & payments spotlight
- **Display:** 3-5 fintech-tagged stories with strategic implications
- **Each shows:** Company, tags, description, strategic implication, source link
- **Source:** Filter from Component 1.3 where `is_fintech: true` + Sonnet adds strategic implications
- **Frequency:** Daily
- **Cost:** ~$0.02–0.04
- **Subtitle:** "AI news in payments, lending, fraud, banking — with strategic implications for card networks"
- **Empty state:** "No major fintech AI stories today"

**Page 1 daily cost: ~$0.07–0.09**

---

## 6. Page 2 — Model Tracker (FULL DESIGN)

### Tracked models (7)
ChatGPT (OpenAI), Claude (Anthropic), Gemini (Google), DeepSeek, Grok (xAI), Copilot (Microsoft), **Llama (Meta)** — added in this redesign. Llama brand color: `#4267B2`.

### 2.1 All models snapshot (7 cards)
- **Cards:** Sentiment score | Buzz volume | WoW delta per model
- **Source:** HN comments (last 3 days) scored by Haiku
- **Frequency:** Daily
- **Cost:** ~$0.035 (7 small Haiku calls, one per model)
- **Subtitle:** "Live sentiment + buzz from Hacker News discussion threads (last 3 days)"
- **Layout:** CSS grid `repeat(auto-fit, minmax(155px, 1fr))` — 7 cards on wide screens, wraps gracefully on narrow
- **Empty state per card:** "No discussion today" + "—" for sentiment

### 2.2 Sentiment trends (30-day chart)
- **Display:** Line chart, 7 model lines, X-axis 30 days
- **Toggle:** `[Hacker News]` (default) vs `[GitHub]`
  - HN view: Y-axis = sentiment 1-10
  - GitHub view: Y-axis = stars gained per day (across model's official ecosystem repos)
- **Source:** Daily JSON history (HN sentiment from 2.1, GitHub stars fetched daily)
- **Frequency:** Daily
- **Cost:** $0 (GitHub API free, sentiment already computed)
- **Per-model GitHub repo signature:** stored in `config.py`
  - ChatGPT: `openai/openai-python`, `openai/openai-cookbook`
  - Claude: `anthropics/anthropic-sdk-python`, `anthropics/courses`
  - Gemini: `google/generative-ai-python`
  - DeepSeek: `deepseek-ai/DeepSeek-V3`
  - Grok: `xai-org/grok-1`
  - Copilot: `github/copilot-cli`
  - Llama: `meta-llama/llama-recipes`
- **Empty state HN:** Carry forward prior score (line stays continuous)
- **Empty state GitHub:** Show 0 (accurate — no new stars)

#### Dynamic disclaimers (toggle-based)

**HN selected:**
> Source: Hacker News comments · Sentiment scored by Claude Haiku
> Each line shows the average sentiment score (1–10) of HN comments mentioning the model that day. Higher = more positive discussion. Spikes often follow major releases or controversies. Sparse on slow news days.

**GitHub selected:**
> Source: GitHub stars on official ecosystem repos
> Each line shows daily new stars across the model's primary repos. Higher = more developer adoption that day. Smoother than sentiment — measures *how many* are building, not *how they feel*.

**Both modes share at bottom:**
> Backfills automatically as daily history accumulates.

### 2.3 What's driving each model's trend
- **Display:** Per-model section with 3 driver bullets, each tagged ↑/↓/→
- **Each driver clickable** → links to source HN thread or curated story
- **Source:** Single batched Sonnet call for all 7 models (cost-efficient)
- **Frequency:** Daily
- **Cost:** ~$0.02
- **Subtitle:** "Why each model's sentiment moved this week — synthesized from discussion threads and curated stories"
- **Disclaimer:** "Sources: Hacker News comments + curated stories from HN/arXiv/GitHub · Drivers synthesized by Claude Sonnet"
- **Empty state:** "Not enough discussion this week to identify drivers." (per-model)

### 2.4 Deep-dive: MAU + market share
- **Display:** 4 cards in deep-dive header — Sentiment | MAU | Market share | Buzz volume
- **Always show all 4 cards** with "Not disclosed" or "—" for missing
- **Source:** Web search (analyst reports, earnings calls, press releases)
- **Frequency:** Weekly (Mondays only)
- **Cost:** ~$0.06 (7 web searches × ~$0.008 each, throttled)
- **Cache file:** `output/model-deep-cache.json`
- **Subtitle on each card:** "as of [Monday date]" instead of WoW deltas

#### Llama special handling
Llama is not a consumer product. Replace metric labels:
- MAU → "Downloads" (Hugging Face counts)
- Market share → "Derivatives" (count of fine-tuned models)

#### Per-model expectation matrix
| Model | MAU public? | Market share data? |
|---|---|---|
| ChatGPT | ✅ | ✅ |
| Claude | ❌ Not disclosed | ⚠️ Estimates |
| Gemini | ✅ | ✅ |
| DeepSeek | ⚠️ Self-reported | ⚠️ Estimates |
| Grok | ⚠️ Sometimes announced | ❌ |
| Copilot | ✅ | ✅ Coding-AI specific |
| Llama | (Downloads instead) | (Derivatives instead) |

- **Disclaimer:** "Sources: Web search of analyst reports, earnings calls, press releases · Refreshed Mondays · Last updated: [date]"

### 2.5 Strengths & weaknesses
- **Display:** Two side-by-side panels per model: Strengths (green dots) | Weaknesses (red dots), 3-5 bullets each
- **Not clickable** — clean visual presentation
- **Source:** Bundled Sonnet call analyzing **last 30 days** of HN comments + curated stories
- **Frequency:** **Monthly** (1st of month only) — these are structural traits, not transient
- **Cost:** ~$0.03/month
- **Cache file:** `output/model-strengths-cache.json`
- **Subtitle:** "Based on 30-day discussion analysis · refreshed monthly"
- **Disclaimer:** "Sources: Hacker News comments + curated stories from HN/arXiv/GitHub · Synthesized by Claude Sonnet · Last updated: [date]"
- **Empty state:** "Not enough discussion this month to synthesize." (per-model)
- **Quality safeguards:** Each bullet must reference observable evidence (specific thread, benchmark, release note). No generic statements.

### 2.6 Mention chart (positive/negative)
- **Display:** Horizontal bar chart per model — pos_current, pos_prior, neg_current, neg_prior
- **Auto-scale per chart** + absolute numbers shown next to each bar (e.g. "320 ↑", "41 ↓")
- **Negatives render to left of zero** by negating values
- **Source:** Daily JSON history (from Component 2.1's HN sentiment classifications)
- **Frequency:** Daily (auto-rebuilds from history)
- **Cost:** $0
- **Title:** "Mention sentiment — current vs prior 30 days"
- **Subtitle:** "Positive vs negative HN mentions · stacked comparison"
- **Disclaimer:** "Sources: Hacker News comments classified by Claude Haiku · Backfills automatically as daily history accumulates"
- **Logic:** Hide "prior" bars until 60+ days of history; warn "Low sample" when total mentions <5

### 2.7 Recent changes per model
- **Display:** Timeline list, 5-7 most recent events per model from **last 90 days**
- **Each row clickable** → links to source
- **Source:** Hybrid
  - **Daily:** auto-appends from Component 1.3 curated stories with `model_mentioned`
  - **Weekly Mondays:** web search top-up bundled with 2.4 deep-dive run
- **Frequency:** Daily updates + Monday comprehensive refresh
- **Cost:** ~$0.04 added to Monday's run
- **Persistent file:** `output/model-events-history.json` (committed to repo, prunes >90 days)
- **Subtitle:** "Releases, announcements, and major news for the selected model"
- **Disclaimer:** "Sources: Curated HN/arXiv/GitHub stories + weekly web search of press releases · Updated daily; comprehensive refresh Mondays"
- **Empty state:** "No major releases or announcements in the last 90 days."

### 2.8 Key people quotes
- **Display:** Per-person card — avatar (Wikipedia or initials fallback), name, role, social handle icons (X/LinkedIn/Threads), recent quote, date+platform
- **All cards clickable** → opens original post
- **Adaptive count** — show all key people we can find (no cap; could be 2-8 per model)
- **Quote freshness:** last 60 days
- **Avatar strategy:** Wikipedia API first → fall back to colored initials in branded circle
  - Wikipedia API: `https://en.wikipedia.org/api/rest_v1/page/summary/{name}` → check `thumbnail.source`
  - Free, no auth, hotlink-friendly, copyright-clean
- **Source:** Web search per model (CEO, lead researchers, public-facing engineers)
- **Frequency:** Weekly (Mondays, bundled with 2.4 deep-dive run)
- **Cost:** ~$0.05/Monday
- **Subtitle:** "Recent posts from leadership and key researchers"
- **Disclaimer:** "Sources: Web search of public X/LinkedIn/Threads posts · Avatars from Wikipedia (where available) · Refreshed Mondays · Last updated: [date]"
- **Empty state:** "No recent public posts from this model's leadership in the last 60 days."

#### Sonnet prompt approach
> "Find all current public-facing leaders, researchers, and engineers tied to [model]. For each, find their most recent public post (X / LinkedIn / Threads) within the last 60 days. Return up to 8 people; only include those with verifiable recent activity."

Each returned item: `{name, role, handles: [...], quote, date, platform, source_url}`. Renderer wraps card in `<a href="source_url">`. Wikipedia photo lookup happens after Sonnet returns.

**Page 2 cost:**
- Daily: ~$0.06
- Monday extra: ~$0.15
- Monthly extra: ~$0.03

---

## 7. Pages 3 & 4 Polish (no full redesign)

### 7.1 Add disclaimers to every component

**Page 3:**
| Component | Disclaimer |
|---|---|
| 3.1 This week in AI funding | Sources: TechCrunch, The Information, Reuters, Bloomberg, PitchBook · Refreshed Mondays |
| 3.2 AI ETF market pulse | Source: Yahoo Finance · Updated daily |
| 3.3 Recent funding rounds | Sources: TechCrunch, The Information, Reuters, Bloomberg, PitchBook · Refreshed Mondays |
| 3.4 Private + Public AI valuations | Sources: Web search of analyst reports + Yahoo Finance · Refreshed Mondays (private), daily (public) |
| 3.5 The arms race chart | Sources: TechCrunch, The Information, PitchBook · Quarterly aggregates · Refreshed Mondays |
| 3.6 VC league table | Sources: PitchBook, Crunchbase, TechCrunch · Refreshed Mondays |
| 3.7 Money flow analysis | Synthesized by Claude Sonnet from this week's funding/M&A activity · Refreshed Mondays |
| 3.8 M&A & exits tracker | Sources: TechCrunch, Reuters, Bloomberg, SEC filings · Refreshed Mondays |
| 3.9 Fintech & payments AI spotlight | Sources: TechCrunch, The Information, Reuters, Bloomberg · Strategic implications by Claude Sonnet · Refreshed Mondays |

**Page 4:**
| Component | Disclaimer |
|---|---|
| 4.1 This week in AI research | Source: arXiv (cs.AI, cs.LG, cs.CL, cs.CV, cs.MA) · Updated daily |
| 4.2 Paper of the week | Source: arXiv · Selected and summarized by Claude Sonnet · Updated daily |
| 4.3 Top papers this week | Source: arXiv · Scored by Claude Haiku, summarized by Sonnet · Updated daily |
| 4.4 Research by category + 30-day volume | Source: arXiv categories · Backfills automatically as daily history accumulates |
| 4.5 Hot institutions this week | Source: arXiv author affiliations · Updated daily |
| 4.6 Author spotlight | Source: arXiv author tracking · Synthesized by Claude Sonnet · Updated daily |
| 4.7 Breakthrough radar | Source: arXiv · Breakthroughs flagged by Claude Sonnet at score 8.0+ · Updated daily |
| 4.8 Research signal analysis | Synthesized by Claude Sonnet from this week's papers · Updated daily |
| 4.9 Fintech & payments research corner | Source: arXiv (filtered for payments/fintech/fraud topics) · Updated daily |

### 7.2 Linkable items audit (Pages 3 & 4)

**Page 3:**
- 3.1 Largest round → link to source article (analyzer addition: include source URL with largest round)
- 3.4 Private AI companies → each company's last round article (analyzer addition: `last_round_url`)
- 3.6 VC firms → firm's website or PitchBook profile (analyzer addition: `firm_url`)
- 3.7 Money flow signals → cited source per signal (analyzer addition: `source_url` per signal)

**Page 4:**
- 4.3 Paper titles → arXiv URL
- 4.4 Categories → arXiv listing for that category
- 4.6 Author names → arXiv author page
- 4.7 Breakthrough items → linked paper
- 4.8 Research signals → cited papers (analyzer addition: `cited_paper_urls`)
- 4.9 Fintech research papers → arXiv URL

### 7.3 ETF Trend sparkline (Page 3 only remaining bug)
`stocks.py` already fetches 90-day price history but doesn't generate `sparkline` boolean and `sparkline_points` SVG polyline string. Add a helper:

```python
def build_sparkline_points(prices_90d: List[float], width: int = 80, height: int = 18) -> str:
    """Convert price history to SVG polyline points string."""
    if not prices_90d or len(prices_90d) < 2:
        return ""
    lo, hi = min(prices_90d), max(prices_90d)
    rng = hi - lo or 1
    n = len(prices_90d)
    pts = []
    for i, p in enumerate(prices_90d):
        x = (i / (n - 1)) * width
        y = height - ((p - lo) / rng) * height
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)
```

Then in `fetch_etf_data()`:
```python
result["sparkline"] = True
result["sparkline_points"] = build_sparkline_points(spark)
```

---

## 8. Failure Visibility — Health Check (NEW)

### 8.1 What it monitors
Pipeline runs `health.py` at the end. Saves `output/health.json`:
```json
{
  "timestamp": "2026-05-04T08:23:11Z",
  "status": "healthy" | "degraded" | "broken",
  "checks": {
    "hn_items": {"value": 24, "expected_min": 5, "ok": true},
    "arxiv_papers": {"value": 199, "expected_min": 30, "ok": true},
    "github_repos": {"value": 8, "expected_min": 3, "ok": true},
    "synthesis_count": {"value": 8, "expected_min": 3, "ok": true},
    "daily_json_size_kb": {"value": 287, "expected_min": 10, "ok": true},
    "finance_cache_age_days": {"value": 2, "expected_max": 9, "ok": true}
  },
  "warnings": []
}
```

### 8.2 Dashboard footer status indicator
Below the existing footer:

```html
<div class="health-indicator">
  {% if health.status == "healthy" %}
    <span style="color:#3b6d11;">●</span> All systems healthy
  {% elif health.status == "degraded" %}
    <span style="color:#e3a01a;">●</span> {{ health.warnings | length }} sources returned low data
  {% else %}
    <span style="color:#a32d2d;">●</span> Pipeline issues — see logs
  {% endif %}
</div>
```

---

## 9. Local Development Workflow

### 9.1 `--render-only` flag
For fast iteration on visual tweaks without burning API budget:
```bash
python -m src.main --render-only
```
Skips all data fetching, reads existing `output/daily-data/<today>.json` + caches, re-renders dashboard. ~3 seconds, $0.

### 9.2 Standard local dev cycle
```bash
# Activate venv
.\venv\Scripts\Activate.ps1

# .env auto-loads (after build adds dotenv.load_dotenv() calls)
python -m src.main           # full run
python -m src.main --render-only  # render only
python -m src.finance_analyzer    # standalone finance test
python -m src.model_tracker       # standalone model deep-dive test
```

### 9.3 Cost transparency
Every daily payload includes `cost_estimate` field. Footer shows: "Today's compute: $0.18".

---

## 10. Reddit On-Ramp (When Approved)

### When Reddit API approval comes through:

1. Update GitHub Secrets:
   - `REDDIT_CLIENT_ID`
   - `REDDIT_CLIENT_SECRET`
   - `REDDIT_USER_AGENT`
2. Set `REDDIT_MODE=live` (replaces brittle string-prefix check from current `_is_mock_mode()`)
3. **No code changes needed.**
4. Reddit posts get added to the aggregate stream alongside HN/arXiv/GitHub
5. Reddit comments feed into the same per-model sentiment pipeline as HN
6. Disclaimers update automatically: "Sources: HN, arXiv, GitHub" → "Sources: HN, Reddit, arXiv, GitHub"

### Architecture commitments to enable this:
- `sources/reddit.py` returns same dict shape as `sources/hn.py`
- Aggregator in `scraper.py` treats Reddit as just another source
- No special-casing, no Reddit-only code paths

---

## 11. Build Sequence (FRESH SESSION)

### Phase 0 — Setup
1. Create `.env` permanent setup (add `dotenv.load_dotenv()` calls everywhere needed)
2. Create `src/utils/` directory with shared helpers:
   - `json_extract.py` — single `_extract_json()` used by all analyzers
   - `throttle.py` — `_ws_search_throttled()` and `_sonnet_call_throttled()`
   - `wikipedia.py` — `fetch_person_photo(name)`

### Phase 1 — Source layer
3. `src/sources/__init__.py`
4. `src/sources/hn.py` — Hacker News fetcher (top stories + comment fetching)
5. `src/sources/github_trending.py` — Trending repos + per-model ecosystem stars
6. `src/sources/arxiv_stories.py` — Surface top arXiv papers as Page 1 stories (thin wrapper)
7. `src/sources/reddit.py` — Move existing Reddit logic here (mock mode preserved)

### Phase 2 — Update orchestrator
8. Update `src/scraper.py` → renamed/refactored aggregator
9. Update `src/analyzer.py` → source-agnostic story scoring (prompt rewrite)

### Phase 3 — Page 2 deep-dive
10. `src/model_tracker.py` — Mondays-only Page 2 deep-dive (mirrors `finance_analyzer.py` pattern)
11. Update `src/main.py` to wire it in (Monday check, monthly check)

### Phase 4 — Render refactor
12. Refactor `src/render.py`:
    - Split monolithic template into shell + per-page bodies + per-component strings
    - Add structural validator
    - Add `index.html` redirect generator
    - Update Pages 3 & 4 with disclaimers + linkable items
    - Add footer + health indicator
    - Apply `.linkable` hover pattern across all 4 pages
13. Update `src/storage.py` to write both `latest.html` and `index.html`

### Phase 5 — Health & polish
14. `src/health.py` — pipeline health check
15. `src/stocks.py` → add sparkline generation (Page 3 ETF Trend column fix)
16. Update analyzer outputs to include URL fields (Pages 3 & 4 linkable items)
17. Update `config.py` with: path constants, GitHub repo signatures per model, `DASHBOARD_LAUNCH_DATE`

### Phase 6 — Workflow & deploy
18. Update `.gitignore` for new persistent files
19. Update `daily.yml` to commit all cache files (not just finance)
20. Test locally with `--render-only` (fastest iteration)
21. Test locally with full pipeline (real data validation)
22. Push and trigger workflow
23. Verify GitHub == local

### Phase 7 — Post-build cleanup (your TODO)
24. Consolidate Anthropic API keys into single `ai-dashboard-prod`
25. Update GitHub secret + local `.env`
26. Revoke all old keys
27. Add SEO/Open Graph meta tags for LinkedIn shareability
28. Re-enable cron in `daily.yml` for daily auto-runs
29. Post on LinkedIn

---

## 12. Five-Phase Validation Before Push

Before any push to GitHub, code must pass:

1. **Syntax & lint** — `ast.parse` + `flake8 --max-line-length=120 --ignore=E501`
2. **Mock-empty test** — Run pipeline with all sources artificially returning `[]`. Dashboard must render cleanly with empty-state messages everywhere.
3. **Real-data test (local)** — Run full pipeline locally. Verify every component renders with real data. Click every link.
4. **Push and watch** — Trigger GitHub workflow live. Monitor for failures.
5. **GitHub == local check** — Compare local `latest.html` with deployed version. Differences should only be date stamps and live data freshness, never structural.

---

## 13. Cost Budget (Hard Targets)

| Cadence | Target | Hard Cap |
|---|---|---|
| Daily run | $0.20 | $0.30 |
| Monday extra | $0.30 | $0.50 |
| Monthly | $0.03 | $0.10 |
| **Monthly total** | **$10** | **$13** |

If a build day exceeds hard cap, revisit design and trim before continuing.

---

## 14. Issues Encountered (and how we're preventing them)

Documented for future debugging:

| Issue | Root cause | Prevention |
|---|---|---|
| Page bleed (Page 1 components on Pages 2/3/4) | Monolithic 1300-line template, manual `</div>` editing | Architectural split into shell + components, structural validator |
| `KeyError` on Claude code-fenced JSON | Naive code-fence stripping | Single shared `_extract_json()` in `utils/` |
| Empty `style=""` HTML attributes | Conditional inside attribute value | Wrap entire attribute conditionally |
| UnicodeEncodeError on Windows (cp1252) | Default encoding when writing files | Always pass `encoding='utf-8'` |
| Duplicate code from copy-paste | Manual editing in Notepad/VS Code | Pre-render structural validator catches truncated strings, duplicates |
| Rate limit cascades | No throttling between Sonnet calls | 40s sleeps + resumable progress files |
| 2025 dates in fresh web search | Model defaults to training cutoff | Date anchor block in every web-search prompt |
| Schema mismatch (analyzer vs render) | No explicit contracts | TypedDict schemas + same-commit updates |
| Cache file missing on GitHub Actions | Ephemeral runner, no persistent storage | All caches committed to repo |
| Path separators (`\` vs `/`) | Raw strings | `pathlib.Path` everywhere |
| PowerShell env var loss on restart | Session-scoped variables | `.env` + `dotenv.load_dotenv()` |
| Multiple API keys floating around | Ad-hoc generation during debugging | Naming convention: `ai-dashboard-prod` only |
| Reddit mock detection brittle | String prefix check | `REDDIT_MODE=live\|mock` env var |
| YAML parse errors with empty cron | YAML doesn't allow empty schedule blocks | Use clean reference template |
| Duplicate broken script blocks | Failed copy-paste | Structural validator |
| `m.deep` AttributeError | Template assumes nested object exists | `{% set safe = obj or {} %}` pattern |

---

## 15. What This Document Is Not

- Not a step-by-step tutorial (we'll do that in chat)
- Not pretending Pages 1/2 are built — they're designed but not coded
- Not the final visual spec (mockups in earlier chats are still authoritative for layout details)
- Not committed to specific HN/GitHub query patterns yet — those firm up at implementation

This document IS:
- The contract for what gets built next session
- The reference for "how do we handle X" questions
- The recovery point if a session gets interrupted mid-build

---

## 16. Open Questions for Next Session

(None right now — design is complete.)
