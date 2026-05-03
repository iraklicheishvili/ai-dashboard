# AI Intelligence Dashboard — PLAN v2

**Status as of:** May 4, 2026  
**Project repo:** `github.com/iraklicheishvili/ai-dashboard`  
**Live URL:** `https://iraklicheishvili.github.io/ai-dashboard/latest.html`  
**Owner:** Irakli Cheishvili  

This document replaces the prior Phase 3 planning notes. It combines the planned Phase 3 build with all identified dashboard bugs, visual fixes, data gaps, and production-readiness improvements into one coordinated completion phase.

---

## 1. Phase 3 Objective

Phase 3 turns the dashboard from a working multi-page prototype into a production-ready intelligence product.

The phase includes:

- Completing Page 2 model intelligence with weekly web-search-backed deep dives.
- Adding model events history, strengths/weaknesses, and key people quotes.
- Adding GitHub stars history for the Page 2 trend toggle.
- Adding pipeline health checks and footer status.
- Fixing all current UI inconsistencies across Pages 1–4.
- Improving Page 1 visual components.
- Stabilizing Page 3 finance refresh behavior and filling missing finance components.
- Investigating sparse Page 4 research components.
- Final local validation, GitHub workflow validation, and production deployment.

---

## 2. Global UI System Fixes

### 2.1 Unified Linked Item Hover System

All clickable items across all pages must behave consistently.

**Blueprint:** Page 1 → Top Stories list.

Required behavior:

- Hover background highlight on the clickable row/card.
- Title gets a dashed underline on hover.
- External-link arrow `↗` appears inline next to the title, not below it.
- Cursor becomes pointer.
- Smooth 150ms transition.
- Click opens in a new tab with `target="_blank"` and `rel="noopener noreferrer"`.
- No fabricated URLs.

Components to standardize:

- Page 1:
  - Top story today
  - Top stories
  - Source hot topics
  - Fintech & payments spotlight
- Page 2:
  - Trend drivers
  - Recent changes timeline
  - Key people quote cards
- Page 3:
  - Funding rounds
  - Private AI companies
  - VC league table firms
  - Money flow signals
  - M&A tracker
  - Fintech spotlight
- Page 4:
  - Paper of the week
  - Top papers
  - Research categories
  - Author spotlight
  - Breakthrough radar
  - Research signal analysis
  - Fintech research papers

Known bugs to fix:

- Page 1 top story arrow appears below the title instead of inline.
- Page 4 paper of the week has no proper hover state and only shows “View on arXiv”.
- Page 4 top papers react inconsistently, with arrows appearing under the entire article instead of next to the title.
- Some linked rows behave as full-card links while others only underline title text.
- Some items have no visible hover feedback at all.

Implementation direction:

- Add a reusable linked-row pattern.
- Keep the full row/card clickable when appropriate.
- Scope the visual underline and arrow to the title element only.
- Avoid applying `.linkable::after` to large block containers.

---

## 3. Page 1 — AI Intelligence Fixes

### 3.1 Story Volume Component Rebuild

Current issues:

- The component still shows dummy Reddit/mock data in some cases.
- Legend includes both subreddit-style labels and source labels.
- Current stacked bar chart looks visually unclear.

Required fix:

- Remove all subreddit framing from the component.
- Show sources only:
  - Hacker News
  - GitHub Trending
  - arXiv
  - Reddit only when live or mock data actually exists, but never as “subreddits”.
- Replace stacked bars with grouped daily bars:
  - One date group per day.
  - One bar per source inside each date group.
  - Clear source-only legend.
- Build from `output/daily-data/*.json`.
- Keep honest sparse history until enough daily files accumulate.

Expected result:

- The chart should visually communicate source mix over time without confusing subreddits and sources.

---

### 3.2 Category Breakdown Donut Fix

Current issues:

- Hover interaction does not show category and article count.
- Some categories appear to share the same color.
- Some categories look visually grouped together.

Required fix:

- Use unique colors for each category slice.
- Add hover tooltip showing:
  - Category name
  - Number of articles/stories
- Ensure the displayed total equals the curated story count.
- Use primary category only for counting, as agreed in the original plan.

Expected result:

- Category breakdown should be readable, interactive, and visually distinct.

---

### 3.3 Strategic Read Wording

Current issue:

- The component says signals matter for Mastercard.

Required fix:

- Make the wording audience-neutral.
- Replace Mastercard-specific language with:
  - “international payment schemes”
  - or “IPSs (international payment schemes)”

Expected result:

- The dashboard remains relevant to payments and banking without being tied to one employer or internal audience.

---

## 4. Page 2 — Model Tracker Completion

### 4.1 All Models Snapshot Grid Fix

Current issue:

- Seven cards can wrap awkwardly, leaving one model alone on the last row.

Required fix:

- Improve responsive grid behavior.
- Preferred layouts:
  - Wide desktop: all 7 cards in one row if space allows.
  - Medium screens: balanced 4 + 3.
  - Smaller screens: balanced wrapping such as 3 + 2 + 2.
- Avoid a layout where one model card sits alone on a row unless the viewport is very narrow.

Expected result:

- Page 2 top section should feel intentional and balanced.

---

### 4.2 Sentiment Trends — GitHub Mode Population

Current issue:

- GitHub trend mode is not populated yet.

Required fix:

- Create and maintain `output/github-stars-history.json`.
- Fetch daily GitHub star deltas for tracked model ecosystem repos.
- Use existing `config.TRACKED_MODELS[*].github_repos`.
- Feed this data into the Page 2 GitHub toggle.

Tracked repos currently defined in config include:

- ChatGPT / OpenAI repos
- Claude / Anthropic repos
- Gemini / Google repo
- DeepSeek repo
- Grok repo
- Copilot repo
- Llama repo

Expected result:

- HN toggle shows sentiment.
- GitHub toggle shows daily star gains by model ecosystem.
- Empty GitHub days show 0, not missing/broken data.

---

### 4.3 Trend Drivers — Signal Indicators

Current issue:

- “What’s driving each model’s trend” lacks the agreed positive/neutral/negative signal treatment.

Required fix:

Each driver should render with a signal indicator:

| Signal | Icon | Visual style |
|---|---|---|
| Positive | ▲ | Green |
| Neutral | ● or → | Muted gray / neutral |
| Negative | ▼ | Red |

Implementation direction:

- Match the visual language used in Page 3 Money Flow Analysis and Page 4 Research Signal Analysis.
- Ensure every driver has an indicator.
- If analyzer output is missing `direction`, default to neutral.

Expected result:

- Users can scan whether a model’s narrative is improving, worsening, or stable.

---

### 4.4 Model Deep Dive via `model_tracker.py`

Current issue:

- Model deep-dive fields are placeholders or partially empty.
- MAU, market share, buzz volume, strengths, weaknesses, key people quotes, and recent changes still need Phase 3 data support.

Required build:

Create `src/model_tracker.py`.

It should mirror the resilience pattern already used by `finance_analyzer.py`:

- Weekly run on Mondays.
- Web-search-backed model deep dive.
- Date anchor in every prompt.
- Progress file after each major step.
- Cache file committed to repo.
- Graceful fallback to cache on rate limit or failure.
- Throttled Sonnet web-search calls.

Primary cache:

- `output/model-deep-cache.json`

Deep-dive fields per model:

- Sentiment score
- MAU or equivalent
- Market share or equivalent
- Buzz volume
- Last updated date
- Sources used

Special handling for Llama:

- Llama is not a consumer product.
- Replace MAU with “Downloads”.
- Replace market share with “Derivatives”.
- Prefer Hugging Face download counts and derivative/fine-tune counts where available.

Expected result:

- Page 2 deep-dive card becomes a real intelligence section, not a placeholder section.

---

### 4.5 Strengths & Weaknesses

Required build:

- Create monthly strengths/weaknesses synthesis.
- Runs only on the 1st of the month.
- Uses last 30 days of:
  - HN model comments
  - curated stories
  - relevant releases / events
- Writes to:
  - `output/model-strengths-cache.json`

Required output per model:

- 3–5 strengths
- 3–5 weaknesses
- Evidence-aware wording, not generic claims

Rendering requirements:

- Strengths and weaknesses side-by-side.
- Strengths use green dots.
- Weaknesses use red dots.
- If cache is missing, show clean empty state.

Expected result:

- Page 2 explains what each model is perceived to be good or weak at, based on recent evidence.

---

### 4.6 Recent Changes Timeline

Required build:

Create and maintain:

- `output/model-events-history.json`

Sources:

- Daily: curated stories where `model_mentioned` is present.
- Weekly: model web-search top-up from `model_tracker.py`.

Rules:

- Keep last 90 days.
- Deduplicate by model + title + URL.
- Each event has:
  - model
  - date
  - title
  - short description
  - source URL
  - event type if available

Rendering requirements:

- Timeline list per model.
- 5–7 most recent events.
- Clickable rows using universal hover behavior.
- Clean empty state when no events exist.

Expected result:

- Users can quickly see what recently changed for each major model.

---

### 4.7 Key People Quotes with Wikipedia Avatars

Required build:

Part of `model_tracker.py` weekly Monday run.

For each tracked model/company:

- Identify public-facing leaders, researchers, or engineers.
- Find recent public quote/post from the last 60 days.
- Return up to 8 people per model where verifiable.

Each quote item should include:

- Name
- Role
- Company/model association
- Quote
- Date
- Platform
- Source URL
- Optional handles
- Avatar URL if found

Avatar strategy:

- Use `src/utils/wikipedia.py` / Wikipedia summary API.
- If photo exists, render avatar image.
- If not, use branded initials fallback.

Rendering requirements:

- Quote cards clickable to original source.
- Universal hover behavior.
- Avatar + name + role + quote + date/platform.

Expected result:

- Page 2 becomes more human and executive-readable.

---

## 5. Page 3 — AI Finance Fixes

### 5.1 Finance Rate-Limit Stability

Current issue:

- Finance refresh can hit Anthropic 429 rate limits.
- Current fallback works, but Phase 3 should improve the chance of completing fresh finance refreshes.

Required fix:

- Increase web-search throttling for finance from 40s to 60s where needed.
- Add additional spacing between heavy Sonnet web-search calls.
- Preserve cache fallback.
- Preserve progress file behavior.
- Avoid retry loops that burn tokens.
- Ensure a failed finance refresh never prevents dashboard render.

Expected result:

- Monday finance refresh is more likely to complete.
- If it fails, dashboard still uses the latest finance cache.

---

### 5.2 Private AI Companies Table Title

Current issue:

- Component title says “Private AI Top 10” but table can contain 12 companies.

Required fix:

Choose one of the following and apply consistently:

- Rename to “Private AI Companies” or “Top Private AI Companies”.
- Or strictly limit to 10 companies.

Preferred direction:

- Rename title to avoid inaccurate count.

Expected result:

- Title matches actual content.

---

### 5.3 Private Valuation Readability

Current issue:

- Under each company name, the last known round appears but is not clearly labeled.
- Estimated valuation badge is fine but needs clearer separation from round detail.

Required fix:

- Under company name, display:
  - `Last round: Series X` or equivalent.
- Keep estimated valuation in the indigo/colored badge next to the company name.
- Ensure users can immediately distinguish:
  - company name
  - estimated valuation
  - last known round
  - category/stage if present

Expected result:

- Private valuation table is easier for external users to read.

---

### 5.4 VC League Table Population

Current issue:

- VC league table is not populated.

Required fix:

- Populate from finance analyzer output.
- If current week has no sufficient data, use prior quarter or most recent available quarter.
- Add fallback logic:
  - Current week data
  - Current quarter data
  - Prior quarter data
  - Empty state only if no credible source data exists

Each VC row should include:

- Firm name
- Number of AI deals
- Total disclosed amount where available
- Notable companies
- Source URL or firm URL where available

Expected result:

- VC league table should not remain empty when credible prior-period data exists.

---

### 5.5 Money Flow Indicator Fix

Current issue:

- Only some positive signals show green indicators.
- Neutral and negative signals appear without indicators in some rows.

Required fix:

- Ensure every money flow signal has a direction/type.
- Supported values:
  - positive / up
  - neutral / stable
  - negative / down
  - warning
- Normalize direction strings before render.
- Render matching icon and left border for all signal types.

Expected result:

- Money Flow Analysis behaves like Page 4 Research Signal Analysis, where signal styling already works.

---

## 6. Page 4 — Research Fixes

### 6.1 Research Link Hover Consistency

Apply the global linked-item hover system to:

- Paper of the week
- Top papers
- Research by category
- Hot institutions if clickable
- Author spotlight
- Breakthrough radar
- Research signal analysis
- Fintech research corner

Known fixes:

- Paper of the week should not rely only on a “View on arXiv” text link.
- Top paper hover should underline title and show inline arrow next to title.
- Avoid arrows appearing under the entire article/card.

Expected result:

- Page 4 interactions feel consistent with Page 1 Top Stories.

---

### 6.2 Hot Institutions Investigation and Fix

Current issue:

- Hot Institutions is sparsely populated.

Required investigation:

Determine whether sparsity is caused by:

- genuinely limited data
- missing affiliation extraction
- overly strict threshold
- analyzer output shape mismatch
- render expecting different fields

Required fix:

- If data exists but is not rendering, fix render/schema mismatch.
- If analyzer is too strict, adjust extraction/grouping logic.
- If data is genuinely sparse, render a clear explanation and avoid looking broken.

Expected result:

- Hot Institutions either displays credible institution data or a clean, honest empty state.

---

### 6.3 Author Spotlight Investigation and Fix

Current issue:

- Author Spotlight is not populated.

Required investigation:

Determine whether issue is caused by:

- analyzer not producing author spotlight
- missing author metadata
- render expecting wrong keys
- threshold too high

Required fix:

- Ensure analyzer output includes the expected author spotlight structure.
- Ensure render reads that structure safely.
- Add fallback empty state if no credible author can be identified.

Expected result:

- Author Spotlight displays when data supports it, otherwise cleanly explains absence.

---

## 7. New Persistent Data Files

Phase 3 must create and maintain these committed output files:

```text
output/model-deep-cache.json
output/model-events-history.json
output/model-strengths-cache.json
output/model-sentiment-history.json
output/github-stars-history.json
output/health.json
```

Rules:

- Files must be committed to repo so GitHub Actions runners can reuse them.
- Missing files should not crash local render-only runs.
- Render should show clean empty states when files are missing.
- Full pipeline should create/update them.

---

## 8. `main.py` Pipeline Enhancements

Required additions:

### 8.1 Render-only preservation

`python -m src.main --render-only` must remain safe and cost $0.

It must not call:

- Anthropic
- yfinance
- HN API
- GitHub API
- arXiv API
- finance analyzer
- model tracker

It should only read existing JSON/cache files and render HTML.

### 8.2 Daily history updates

On full pipeline run:

- Append/update model sentiment history.
- Append/update GitHub stars history.
- Append/update model events history from curated stories.

### 8.3 Weekly model tracker

On Mondays:

- Run model deep-dive web search.
- Refresh key people quotes.
- Refresh recent model events from web search.
- Write `model-deep-cache.json` and update `model-events-history.json`.

### 8.4 Monthly strengths/weaknesses

On the 1st of each month:

- Run strengths/weaknesses synthesis.
- Write `model-strengths-cache.json`.

### 8.5 Finance stability

On Mondays:

- Run finance refresh with improved spacing.
- On 429/failure, load latest finance cache and continue.

### 8.6 Health check

At the end of full pipeline:

- Run health check.
- Save `output/health.json`.
- Pass health object into render.

---

## 9. `health.py` Build

Create `src/health.py`.

It should inspect pipeline output and produce:

```json
{
  "timestamp": "2026-05-04T08:23:11Z",
  "status": "healthy",
  "checks": {
    "hn_items": {"value": 24, "expected_min": 5, "ok": true},
    "arxiv_papers": {"value": 199, "expected_min": 30, "ok": true},
    "github_repos": {"value": 8, "expected_min": 3, "ok": true},
    "daily_json_size_kb": {"value": 287, "expected_min": 10, "ok": true},
    "finance_cache_age_days": {"value": 2, "expected_max": 9, "ok": true}
  },
  "warnings": []
}
```

Statuses:

- `healthy`: all core checks pass.
- `degraded`: dashboard rendered but one or more sources returned low data.
- `broken`: major output missing or render/data integrity failed.

Footer rendering:

- Healthy: green dot + “All systems healthy”.
- Degraded: amber dot + warning count.
- Broken: red dot + “Pipeline issues — see logs”.

---

## 10. `render.py` Requirements

Maintain the Phase 2 architecture:

- Shell owns page wrappers.
- Page bodies do not define their own `<div id="pN" class="page">` wrappers.
- Structural validator runs before Jinja render.
- Safe access pattern for nested data.
- No page bleed.

Required render updates:

- Universal hover/link system.
- Page 1 chart and donut fixes.
- Page 2 completed deep-dive components.
- Page 2 GitHub trend mode populated from history.
- Page 3 finance visual fixes.
- Page 4 hover and sparse-data fixes.
- Footer health indicator.

---

## 11. `finance_analyzer.py` Requirements

Required updates:

- Improve delay spacing around web-search calls.
- Ensure fallback to cache remains robust.
- Add/repair VC league table output.
- Add prior-quarter fallback for VC league table.
- Normalize money flow signal directions.
- Ensure private valuation fields support clearer rendering.

Output schema should include:

- `vc_league`
- `money_flow_signals[*].direction`
- `private_valuations[*].last_round`
- `private_valuations[*].valuation`
- source URLs where available

---

## 12. `arxiv_analyzer.py` / Page 4 Data Requirements

Required updates:

- Verify hot institution extraction.
- Verify author spotlight extraction.
- Ensure output keys match render expectations.
- Add clean empty states when data is genuinely unavailable.
- Preserve arXiv daily behavior and current Page 4 strengths.

---

## 13. `config.py` Requirements

Ensure config includes:

- `TRACKED_MODELS` with seven models.
- GitHub repo signatures per model.
- Cache paths:
  - model deep cache
  - model events history
  - model strengths cache
  - model sentiment history
  - GitHub stars history
  - health path
- Dashboard launch date.
- Source display names.

---

## 14. Workflow Requirements

Update `.github/workflows/daily.yml` when Phase 3 is ready.

Requirements:

- Commit all persistent caches and histories.
- Keep manual trigger available.
- Re-enable cron only after local and workflow validation.
- Avoid missing cache files in GitHub Actions.

Persistent files to include:

```text
output/finance-cache.json
output/model-deep-cache.json
output/model-events-history.json
output/model-strengths-cache.json
output/model-sentiment-history.json
output/github-stars-history.json
output/health.json
output/daily-data/*.json
output/dashboard/latest.html
output/dashboard/index.html
```

---

## 15. Local Validation Plan

### 15.1 Replace files locally

Use full-file replacement for large files where safer:

- `src/render.py`
- `src/main.py`
- `src/model_tracker.py`
- `src/health.py`
- modified analyzers as needed

### 15.2 Syntax validation

Run:

```powershell
python -m py_compile src\render.py src\main.py src\model_tracker.py src\health.py
```

Also run compile on modified analyzers.

### 15.3 Lint validation

Run:

```powershell
flake8 src --max-line-length=120 --ignore=E501
```

### 15.4 Render-only validation

Run:

```powershell
python -m src.main --render-only
```

Expected:

- No source fetches.
- No Anthropic calls.
- No yfinance calls.
- Dashboard renders successfully.

### 15.5 Full local pipeline validation

Run:

```powershell
python -m src.main
```

Expected:

- Full data refresh.
- Caches update.
- Dashboard renders.
- Finance fallback works if rate limited.
- Model tracker fallback works if rate limited.

### 15.6 Manual dashboard QA

Check all pages:

Page 1:

- Source volume chart uses sources only.
- Grouped bars look clean.
- Donut hover works.
- Strategic read says IPSs, not Mastercard.
- Link hover behavior consistent.

Page 2:

- Seven model cards balanced.
- HN/GitHub toggle works.
- Trend drivers have indicators.
- Deep-dive populated from cache/web search.
- Strengths/weaknesses render.
- Recent changes render.
- Key people quotes render with avatars or initials.

Page 3:

- Finance page remains strongest page.
- Private AI table title fixed.
- Last round label is readable.
- VC league table populated or credible fallback shown.
- Money flow indicators render for all directions.

Page 4:

- Paper links behave consistently.
- Hot Institutions no longer looks broken.
- Author Spotlight populated or cleanly empty.

Footer:

- Health indicator visible and accurate.

---

## 16. Git Validation and Deployment

After local validation:

```powershell
git status
git diff
```

Then commit:

```powershell
git add src config.py output .github/workflows/daily.yml
git commit -m "Phase 3: complete model intelligence, health checks, finance stability, and dashboard polish"
```

Push:

```powershell
git push origin main
```

Then manually trigger GitHub workflow.

Validation after workflow:

- Check workflow logs.
- Confirm no crash.
- Confirm caches committed back if workflow is designed to do so.
- Compare deployed `latest.html` with local output.
- Confirm differences are only data freshness/date-related.

---

## 17. Final Acceptance Criteria

Phase 3 is complete when:

- `--render-only` works with $0 cost.
- Full local pipeline completes or falls back safely on cached sections.
- GitHub workflow completes successfully.
- All four pages render without broken components.
- Linked item hover behavior is consistent across all pages.
- Page 1 charts no longer show confusing Reddit/subreddit residue.
- Page 2 model tracker has real deep-dive data or cache-backed graceful states.
- Page 3 finance page has stable fallback, readable private valuations, populated VC table, and fixed signal indicators.
- Page 4 research sparse components are either populated or honestly empty.
- Health indicator appears in footer.
- All persistent cache/history files are created and committed.
- Dashboard is production-ready for daily automated publishing.
