"""
HTML dashboard renderer (Phase 2 refactor).

Architecture (PLAN.md sec.3 and sec.4.11):
    SHELL_HEAD       — head + body open + page header + tabs
    PAGE_N_BODY      — content-only string for each of the 4 pages
    SHELL_TAIL       — closing footer + tab JS + body close
    render_dashboard — concatenates SHELL_HEAD + page wrappers + bodies + SHELL_TAIL
                       then validates structure and runs Jinja once.

Page bodies are content only — they DO NOT contain their own
`<div id="pN" class="page">` wrapper. The shell adds those wrappers
when assembling the final HTML, which makes page-bleed structurally
impossible: a component cannot accidentally close its parent page
because the page wrapper is added programmatically AFTER the body
content is concatenated.

The structural validator (validate_html_structure) runs before Jinja
processes the assembled string. It catches:
  - Unbalanced page open/close pairs
  - Missing or duplicate page IDs
  - Truncated `{%` / `{{` Jinja markers
  - Negative div nesting depth

Universal Phase 2 polish applied to Pages 3 and 4 ONLY:
  - .disclaimer line on every component card (PLAN sec.4.1, sec.7.1)
  - .empty-state pattern for missing data (PLAN sec.4.2)
  - .linkable hover treatment for clickable items (PLAN sec.4.3, sec.7.2)
  - 3-line professional footer replaces the debug-style footer (PLAN sec.4.4)

Pages 1 and 2 bodies are preserved byte-for-byte from the previous
version. Phase 2B will rebuild them with the new component designs.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Dict

from jinja2 import Template

# config is imported here even though not directly referenced in this file
# yet — Phase 3 will use config.DASHBOARD_LAUNCH_DATE for the volume chart
# starting point.
import config  # noqa: F401


# ============================================================
# Pre-render structural validator (PLAN sec.4.11)
# ============================================================

class HTMLStructureError(Exception):
    """Raised when the assembled HTML fails structural validation."""


def validate_html_structure(html: str) -> None:
    """Validate the assembled HTML before Jinja render.

    Checks (PLAN sec.4.11):
      1. Each `<div id="pN" class="page...">` has exactly one open + one close.
      2. No truncated Jinja markers (`{%` without matching `%}`, etc.).
      3. No duplicate `id="pN"` page IDs.
      4. Overall div open/close counts match.

    Raises HTMLStructureError with a clear message if anything is broken.
    """
    # 1. Page IDs — every id="pN" should appear exactly once
    page_id_opens = re.findall(r'<div\s+id="(p[1-4])"\s+class="page', html)
    seen: Dict[str, int] = {}
    for pid in page_id_opens:
        seen[pid] = seen.get(pid, 0) + 1
    duplicates = [pid for pid, n in seen.items() if n > 1]
    if duplicates:
        raise HTMLStructureError(
            "Duplicate page IDs in shell: " + str(duplicates) +
            ". Each id=\"pN\" must appear exactly once."
        )
    missing = [f"p{n}" for n in (1, 2, 3, 4) if f"p{n}" not in seen]
    if missing:
        raise HTMLStructureError(
            "Missing page IDs in assembled HTML: " + str(missing) +
            ". Shell must wrap every page body."
        )

    # 2. Truncated Jinja markers — only flag when there are MORE opens than
    # closes (which clearly indicates truncation). Excess `}}` can come from
    # CSS keyframe blocks like `{0%,100%{filter:brightness(1);}}` — those are
    # legal CSS, not Jinja, and Jinja parses them correctly.
    open_block = html.count("{%")
    close_block = html.count("%}")
    if open_block > close_block:
        raise HTMLStructureError(
            "Truncated Jinja block: " + str(open_block) +
            " '{%' opens vs " + str(close_block) +
            " '%}' closes. Likely a copy-paste truncation."
        )
    open_var = html.count("{{")
    close_var = html.count("}}")
    if open_var > close_var:
        raise HTMLStructureError(
            "Truncated Jinja variable: " + str(open_var) +
            " '{{' opens vs " + str(close_var) + " '}}' closes."
        )

    # 3. Overall div nesting — should land at zero
    div_opens = len(re.findall(r"<div\b", html))
    div_closes = len(re.findall(r"</div\s*>", html))
    if div_opens != div_closes:
        raise HTMLStructureError(
            "Unbalanced <div> count: " + str(div_opens) + " opens vs " +
            str(div_closes) + " closes. Page-bleed risk — likely a missing "
            "or stray </div>."
        )


# ========================================================# Shell + Page bodies# ========================================================

SHELL_HEAD = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"> 
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Intelligence Dashboard — {{ today }}</title>

<!-- SEO -->
<meta name="description" content="Daily AI intelligence dashboard — curated stories, model tracking, finance, and research, with a fintech and payments lens.">
<meta name="author" content="Irakli Cheishvili">
<link rel="canonical" href="https://siiixseveen.com/">

<!-- Open Graph (LinkedIn, Facebook, Slack, WhatsApp) -->
<meta property="og:title" content="AI Intelligence Dashboard">
<meta property="og:description" content="Daily AI intelligence — curated by Claude. Stories, model tracker, finance, research.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://siiixseveen.com/">
<meta property="og:site_name" content="AI Intelligence Dashboard">
<meta property="og:image" content="https://siiixseveen.com/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="AI Intelligence Dashboard preview showing daily curated AI news, model tracker, finance, and research.">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="AI Intelligence Dashboard">
<meta name="twitter:description" content="Daily AI intelligence — curated by Claude. Stories, model tracker, finance, research.">
<meta name="twitter:image" content="https://siiixseveen.com/og.png">
<meta name="twitter:image:alt" content="AI Intelligence Dashboard preview showing daily curated AI news, model tracker, finance, and research.">

<style>
  :root {
    --bg-primary: #ffffff;
    --bg-secondary: #f5f4f0;
    --bg-tertiary: #fafaf8;
    --text-primary: #1a1a18;
    --text-secondary: #5f5e5a;
    --text-tertiary: #888780;
    --text-info: #185fa5;
    --border: rgba(26,26,24,0.12);
    --border-strong: rgba(26,26,24,0.25);
    --radius-md: 8px;
    --radius-lg: 12px;
    --bg-info: #e6f1fb;
    --border-info: #378add;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg-primary: #1f1f1d;
      --bg-secondary: #2a2a27;
      --bg-tertiary: #181816;
      --text-primary: #f0efe8;
      --text-secondary: #b4b2a9;
      --text-tertiary: #888780;
      --text-info: #85b7eb;
      --border: rgba(240,239,232,0.12);
      --border-strong: rgba(240,239,232,0.25);
      --bg-info: #0c447c;
    }
  }
  *{box-sizing:border-box;margin:0;padding:0;}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg-tertiary);color:var(--text-primary);font-size:14px;line-height:1.5;}
  .container{max-width:1100px;margin:0 auto;padding:1.5rem 1rem;}
  .head{display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:14px;}
  .h-title{font-size:20px;font-weight:500;}
  .h-sub{font-size:12px;color:var(--text-secondary);margin-top:2px;}
  .nav-label{font-size:10px;font-weight:500;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:.08em;margin:0 0 6px 4px;}
  .tabs{display:flex;gap:6px;background:var(--bg-secondary);padding:6px;border-radius:var(--radius-md);margin-bottom:18px;position:sticky;top:0;z-index:5;flex-wrap:wrap;border:0.5px solid var(--border);}
  .tab{flex:1;min-width:140px;padding:10px 14px;font-size:13px;border-radius:calc(var(--radius-md) - 2px);border:none;background:transparent;color:var(--text-secondary);cursor:pointer;text-align:left;transition:background 0.18s, color 0.18s;font-family:inherit;display:flex;align-items:center;gap:10px;position:relative;}
  .tab .tab-icon{width:16px;height:16px;flex-shrink:0;opacity:0.65;transition:opacity 0.18s;}
  .tab .tab-label{flex:1;}
  .tab:hover{color:var(--text-primary);background:rgba(255,255,255,0.03);}
  .tab:hover .tab-icon{opacity:1;}
  .tab.active{background:var(--bg-primary);color:var(--text-primary);font-weight:500;box-shadow:0 1px 2px rgba(0,0,0,0.3), 0 0 0 0.5px var(--border);}
  .tab.active .tab-icon{opacity:1;}
  .tab.active::before{content:"";position:absolute;left:6px;top:14px;bottom:14px;width:2px;border-radius:2px;}
  .tab.active.tab-p1::before{background:#7F77DD;}
  .tab.active.tab-p1{color:#7F77DD;}
  .tab.active.tab-p2::before{background:#1D9E75;}
  .tab.active.tab-p2{color:#1D9E75;}
  .tab.active.tab-p3::before{background:#EF9F27;}
  .tab.active.tab-p3{color:#EF9F27;}
  .tab.active.tab-p4::before{background:#378ADD;}
  .tab.active.tab-p4{color:#378ADD;}
  .tab.active{padding-left:18px;}
  .page{display:none;}
  .page.active{display:block;}
  .card{background:var(--bg-primary);border:0.5px solid var(--border);border-radius:var(--radius-lg);padding:1.25rem;margin-bottom:12px;}
  .card-info{border:2px solid var(--border-info);}
  .sec-title{font-size:13px;font-weight:500;margin-bottom:4px;}
  .sec-sub{font-size:11px;color:var(--text-secondary);margin-bottom:12px;}
  .sec-row{display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;margin-bottom:8px;}
  .mcard{background:var(--bg-secondary);border-radius:var(--radius-md);padding:12px;}
  .mlabel{font-size:11px;color:var(--text-secondary);margin-bottom:4px;}
  .mvalue{font-size:20px;font-weight:500;}
  .up{color:#3b6d11;}
  .down{color:#a32d2d;}
  .neu{color:var(--text-secondary);}
  .pill{font-size:11px;padding:2px 9px;border-radius:99px;font-weight:500;display:inline-block;}
  .sent-pos{background:#eaf3de;color:#3b6d11;}
  .sent-neu{background:#f1efe8;color:#5f5e5a;}
  @media (prefers-color-scheme: dark) {
    .sent-pos{background:#27500a;color:#c0dd97;}
    .sent-neu{background:#444441;color:#d3d1c7;}
  }
  .cat-tag{font-size:10px;padding:2px 7px;border-radius:99px;border:0.5px solid var(--border);color:var(--text-secondary);white-space:nowrap;}
  .score-pill{font-size:10px;padding:2px 7px;border-radius:99px;background:#eeedfe;color:#3c3489;font-weight:500;}
  @media (prefers-color-scheme: dark) {
    .score-pill{background:#3c3489;color:#cecbf6;}
  }
  .linkrow{display:block;text-decoration:none;color:inherit;padding:10px 8px;border-bottom:0.5px solid var(--border);transition:background 0.15s;border-radius:var(--radius-md);}
  .linkrow:hover{background:var(--bg-secondary);}
  .linkrow:last-child{border-bottom:none;}
  .story-title{font-size:13px;font-weight:500;line-height:1.4;}
  .story-meta{font-size:11px;color:var(--text-secondary);margin-top:4px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;}
  .pattern-tag{display:inline-flex;align-items:center;gap:6px;font-size:11px;padding:6px 10px;border-radius:var(--radius-md);margin:3px 4px 3px 0;}
  .pat-up{background:#eaf3de;color:#3b6d11;}
  .pat-down{background:#fcebeb;color:#a32d2d;}
  .pat-neu{background:#e6f1fb;color:#0c447c;}
  .pat-warn{background:#faeeda;color:#854f0b;}
  @media (prefers-color-scheme: dark) {
    .pat-up{background:#27500a;color:#c0dd97;}
    .pat-down{background:#791f1f;color:#f7c1c1;}
    .pat-neu{background:#0c447c;color:#b5d4f4;}
    .pat-warn{background:#633806;color:#fac775;}
  }
  .ins-up::before{content:"\25B2";color:#3b6d11;font-size:9px;margin-right:5px;}
  .ins-down::before{content:"\25BC";color:#a32d2d;font-size:9px;margin-right:5px;}
  .ins-neu::before{content:"\25CF";color:#888780;font-size:7px;margin-right:5px;}
  .ins-warning::before{content:"\26A0";color:#854f0b;font-size:10px;margin-right:5px;}
  .ins-row{font-size:12px;padding:5px 0;line-height:1.4;border-bottom:0.5px solid var(--border);}
  .ins-row:last-child{border-bottom:none;}
  .signal-row{font-size:13px;line-height:1.55;padding:11px 14px 11px 16px;background:var(--bg-secondary);border-radius:var(--radius-md);color:var(--text-primary);border-left:3px solid transparent;}
  .signal-row::before{font-weight:500;margin-right:9px;display:inline-block;width:12px;}
  .signal-row.signal-up{border-left-color:#1D9E75;}
  .signal-row.signal-down{border-left-color:#E24B4A;}
  .signal-row.signal-warning{border-left-color:#EF9F27;}
  .signal-row.signal-neu{border-left-color:#7F77DD;}
  .signal-row.signal-up::before{content:"\25B2";color:#1D9E75;}
  .signal-row.signal-down::before{content:"\25BC";color:#E24B4A;}
  .signal-row.signal-warning::before{content:"\26A0";color:#EF9F27;}
  .signal-row.signal-neu::before{content:"\25CF";color:#7F77DD;font-size:10px;}
  .col-hdr{font-size:10px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.04em;}
  .stat-card{background:var(--bg-secondary);border-radius:var(--radius-md);padding:12px;}
  .stat-label{font-size:11px;color:var(--text-secondary);margin-bottom:4px;}
  .stat-value{font-size:20px;font-weight:500;}
  .dot-g{width:6px;height:6px;border-radius:50%;background:#639922;flex-shrink:0;margin-top:4px;}
  .dot-r{width:6px;height:6px;border-radius:50%;background:#e24b4a;flex-shrink:0;margin-top:4px;}
  .cap-item{display:flex;align-items:flex-start;gap:6px;font-size:12px;margin-bottom:5px;line-height:1.4;}
  .person-chip{display:flex;align-items:flex-start;gap:8px;background:var(--bg-secondary);border-radius:var(--radius-md);padding:10px 12px;margin-bottom:8px;}
  .avatar{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:500;flex-shrink:0;margin-top:1px;}
  .quote-text{font-size:11px;color:var(--text-secondary);margin-top:5px;line-height:1.4;font-style:italic;border-left:2px solid var(--border-strong);padding-left:7px;}
  .quote-meta{font-size:10px;color:var(--text-tertiary);margin-top:3px;}
  .wc-cloud{display:flex;flex-wrap:wrap;justify-content:center;align-items:center;align-content:center;gap:4px 14px;padding:14px 8px;min-height:200px;}
  .wc-word{display:inline-block;padding:3px 6px;line-height:1.25;letter-spacing:-0.01em;opacity:0;transform:translateY(6px) scale(0.92);animation:wcFadeIn 0.55s cubic-bezier(.22,.61,.36,1) forwards;transition:transform 0.2s ease, filter 0.2s ease;cursor:default;}
  .wc-word:hover{transform:translateY(-1px) scale(1.04);filter:brightness(1.15);}
  @keyframes wcFadeIn{to{opacity:var(--wc-opacity,1);transform:translateY(0) scale(1);}}
  @keyframes wcPulse{0%,100%{filter:brightness(1);}50%{filter:brightness(1.18);}}
  .wc-tier-xl{font-size:30px;font-weight:500;letter-spacing:-0.02em;animation:wcFadeIn 0.55s cubic-bezier(.22,.61,.36,1) forwards, wcPulse 4s ease-in-out 1.5s infinite;}
  .wc-tier-lg{font-size:24px;font-weight:500;}
  .wc-tier-md{font-size:18px;font-weight:500;}
  .wc-tier-sm{font-size:14px;font-weight:400;}
  .wc-tier-xs{font-size:12px;font-weight:400;}
  .wc-word.wc-model_release,.wc-word.wc-model{color:#5BA3E8;}
  .wc-word.wc-research_paper,.wc-word.wc-research{color:#9B93E8;}
  .wc-word.wc-funding{color:#3DC48A;}
  .wc-word.wc-regulation{color:#F0A830;}
  .wc-word.wc-open_source{color:#E87070;}
  .wc-word.wc-other{color:var(--text-primary);}
  .wc-tag.wc-model_release,.wc-tag.wc-model{background:transparent;color:#5BA3E8;border:none;}
.wc-tag.wc-funding{background:transparent;color:#3DC48A;border:none;}
.wc-tag.wc-regulation{background:transparent;color:#F0A830;border:none;}
.wc-tag.wc-open_source{background:transparent;color:#E87070;border:none;}
.wc-tag.wc-other{background:transparent;color:var(--text-secondary);border:none;}
.wc-tag.wc-other{background:var(--bg-secondary);color:var(--text-secondary);border:0.5px solid var(--border);}
  .foot{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;padding:14px 4px 0;margin-top:6px;border-top:0.5px solid var(--border);font-size:11px;color:var(--text-secondary);}
  a{color:var(--text-info);}
  select{font-family:inherit;font-size:13px;padding:6px 12px;border-radius:var(--radius-md);border:0.5px solid var(--border-strong);background:var(--bg-primary);color:var(--text-primary);cursor:pointer;}

  .mini-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;}
  .source-chip{font-size:10px;color:var(--text-secondary);background:var(--bg-secondary);border-radius:99px;padding:2px 7px;display:inline-block;}
  .bar-track{height:8px;background:var(--bg-secondary);border-radius:99px;overflow:hidden;}
  .bar-fill{height:100%;border-radius:99px;background:#7F77DD;transition:filter 150ms ease, transform 150ms ease;position:relative;}
  .bar-track:hover .bar-fill{filter:brightness(1.15);}
  .split-card-grid{display:grid;grid-template-columns:1fr 1fr;min-height:260px;}
  .split-panel{padding:16px 18px;display:flex;flex-direction:column;}
  .split-panel + .split-panel{border-left:0.5px solid var(--border);}
  .split-body{flex:1;display:flex;flex-direction:column;justify-content:center;}
  @media (max-width:760px){.split-card-grid{grid-template-columns:1fr}.split-panel + .split-panel{border-left:none;border-top:0.5px solid var(--border);}}
  .toggle-row{display:inline-flex;gap:4px;background:var(--bg-secondary);border-radius:var(--radius-md);padding:4px;border:0.5px solid var(--border);}
  .toggle-btn{font-family:inherit;font-size:11px;border:none;border-radius:calc(var(--radius-md) - 2px);padding:6px 10px;background:transparent;color:var(--text-secondary);cursor:pointer;}
  .toggle-btn.active{background:var(--bg-primary);color:var(--text-primary);box-shadow:0 1px 2px rgba(0,0,0,0.15);}
  .model-card{background:var(--bg-secondary);border:0.5px solid var(--border);border-radius:var(--radius-lg);padding:13px 14px;}
  .model-snapshot-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:10px;}
  @media (max-width:1050px){.model-snapshot-grid{grid-template-columns:repeat(4,minmax(0,1fr));}.model-snapshot-grid .model-card:nth-last-child(-n+3){grid-column:auto;}}
  @media (max-width:760px){.model-snapshot-grid{grid-template-columns:repeat(3,minmax(0,1fr));}}
  @media (max-width:520px){.model-snapshot-grid{grid-template-columns:1fr;}}
  .driver-row{display:block;text-decoration:none;color:inherit;font-size:12px;line-height:1.45;padding:6px 0;border-bottom:0.5px solid var(--border);}
  .driver-row:last-child{border-bottom:none;}
  .timeline-row{display:flex;gap:10px;padding:7px 0;border-bottom:0.5px solid var(--border);font-size:12px;}
  .timeline-row:last-child{border-bottom:none;}


  /* ============================================================
     Phase 2 universal additions (PLAN 4.1, 4.2, 4.3, 4.4)
     ============================================================ */
  .disclaimer{font-size:10px;color:var(--text-tertiary);margin-top:10px;padding-top:8px;border-top:0.5px dashed var(--border);font-style:italic;line-height:1.45;}
  .empty-state{padding:18px 0;font-size:12px;color:var(--text-tertiary);text-align:center;font-style:italic;}
  .linkable{cursor:pointer;border-bottom:1px solid transparent;transition:border-color 150ms ease, color 150ms ease;color:inherit;text-decoration:none;}
  .linkable:hover{border-bottom:1px dashed var(--text-tertiary);color:var(--text-primary);}
  .linkable:hover::after{content:" \2197";font-size:0.85em;color:var(--text-tertiary);margin-left:2px;display:inline;}
  .linked-title{display:inline;border-bottom:1px solid transparent;transition:border-color 150ms ease, color 150ms ease;}
  .linkrow:hover .linked-title,.link-card:hover .linked-title{border-bottom:1px dashed var(--text-tertiary);color:var(--text-primary);}
  .linkrow:hover .linked-title::after,.link-card:hover .linked-title::after{content:" \2197";font-size:0.85em;color:var(--text-tertiary);margin-left:2px;}
  .link-card{display:block;text-decoration:none;color:inherit;border-radius:var(--radius-md);transition:background 150ms ease;}
  .link-card:hover{background:var(--bg-secondary);}
  .signal-icon{display:inline-flex;align-items:center;justify-content:center;width:16px;margin-right:6px;font-size:10px;font-weight:600;}
  .signal-icon.up{color:#1D9E75;}
  .signal-icon.down{color:#E24B4A;}
  .signal-icon.neutral{color:#7F77DD;}
  .deep-metric .mvalue{font-size:15px!important;line-height:1.25;word-break:break-word;}
  .deep-metric .metric-note{font-size:10px;color:var(--text-secondary);margin-top:3px;line-height:1.25;}
  .trait-panel{border-left:3px solid transparent;}
  .trait-panel.trait-strength{border-left-color:#1D9E75;}
  .trait-panel.trait-weakness{border-left-color:#E24B4A;}
  .trait-panel .cap-item{padding-left:0;}
  .pro-foot{margin-top:20px;padding:18px 4px 8px;border-top:0.5px solid var(--border);text-align:center;font-size:11px;color:var(--text-secondary);line-height:1.7;}
  .pro-foot .pf-line1{font-weight:500;color:var(--text-primary);}
  .pro-foot .pf-line2{color:var(--text-secondary);}
  .pro-foot .pf-line3{color:var(--text-tertiary);font-style:italic;}
  .health-indicator{display:inline-flex;align-items:center;gap:5px;font-size:11px;margin-left:8px;}
  .health-indicator .health-dot{width:6px;height:6px;border-radius:50%;display:inline-block;}
</style>
</head>
<body>
<div class="container">

<div class="head">
  <div>
    <div class="h-title">AI intelligence dashboard</div>
    <div class="h-sub">Daily digest from Hacker News, arXiv, GitHub Trending, Yahoo Finance, and web search — {{ today }}</div>
  </div>
</div>

<div class="nav-label">Dashboard sections</div>
<div class="tabs" role="tablist">
  <button class="tab tab-p1 active" data-page="p1">
    <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h3l2-7 4 14 2-9 2 5h5"/></svg>
    <span class="tab-label">AI intelligence</span>
  </button>
  <button class="tab tab-p2" data-page="p2">
    <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
    <span class="tab-label">Model tracker</span>
  </button>
  <button class="tab tab-p3" data-page="p3">
    <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="20" x2="4" y2="12"/><line x1="10" y1="20" x2="10" y2="6"/><line x1="16" y1="20" x2="16" y2="14"/><line x1="22" y1="20" x2="22" y2="9"/></svg>
    <span class="tab-label">AI finance</span>
  </button>
  <button class="tab tab-p4" data-page="p4">
    <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/></svg>
    <span class="tab-label">Research & papers</span>
  </button>
</div>

"""
PAGE_1_BODY = r"""

{% if top_story %}
<div class="card card-info">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
    <span style="font-size:10px;font-weight:500;color:#185fa5;text-transform:uppercase;letter-spacing:.06em;">Top story today</span>
    <span class="score-pill" style="font-size:11px;padding:3px 10px;">{{ "%.1f"|format(top_story.combined_score | default(top_story.relevance_score | default(0))) }}</span>
  </div>
  <a class="link-card" href="{{ top_story.external_url or top_story.url }}" target="_blank" style="padding:8px 10px;margin:-8px -10px 6px;">
    <div style="font-size:16px;font-weight:500;line-height:1.4;"><span class="linked-title">{{ top_story.title }}</span></div>
  </a>
  <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px;">{{ top_story.source or top_story.subreddit }} · {{ top_story.score }} pts · {{ top_story.num_comments | default(0) }} comments</div>
  <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;">
    {% for tag in top_story.category_tags or [] %}<span class="cat-tag">{{ tag }}</span>{% endfor %}
  </div>
  {% if synthesis.top_story and synthesis.top_story.why_top %}
  <div style="font-size:12px;line-height:1.5;color:var(--text-primary);">{{ synthesis.top_story.why_top }}</div>
  {% elif top_story.summary %}
  <div style="font-size:12px;line-height:1.5;color:var(--text-primary);">{{ top_story.summary }}</div>
  {% endif %}
  <div class="disclaimer">Sources: Hacker News, arXiv, GitHub Trending · Top story selected by combined content and engagement score · Updated daily</div>
</div>
{% endif %}

<div class="card">
  <div class="sec-title">Today at a glance</div>
  <div class="sec-sub">Source-agnostic story intelligence across AI, models, research, and fintech</div>
  <div class="mini-grid">
    <div class="mcard"><div class="mlabel">Total stories</div><div class="mvalue">{{ metrics.total_stories | default(top_stories | length) }}</div><div style="font-size:11px;color:var(--text-secondary);">Curated today</div></div>
    <div class="mcard"><div class="mlabel">Fintech stories</div><div class="mvalue">{{ metrics.fintech_count | default(fintech_stories | length) }}</div><div style="font-size:11px;color:var(--text-secondary);">Payments, fraud, banking, lending</div></div>
    <div class="mcard"><div class="mlabel">Top source</div><div class="mvalue" style="font-size:15px;">{{ metrics.top_source | default('—') }}</div><div class="neu" style="font-size:11px;">{{ metrics.top_source_count | default(0) }} stories</div></div>
    <div class="mcard"><div class="mlabel">Most active category</div><div class="mvalue" style="font-size:15px;">{{ metrics.most_active_category | default('—') }}</div><div class="neu" style="font-size:11px;">{{ metrics.top_category_count | default(0) }} stories</div></div>
  </div>
  <div class="disclaimer">Sources: Hacker News, arXiv, GitHub Trending · Metrics computed from curated stories · Updated daily</div>
</div>

<div class="card">
  <div class="sec-title">Story volume — last 30 days</div>
  <div class="sec-sub">Curated stories per source · sparse until the dashboard accumulates more history</div>
  {% if volume_history %}
  <div style="position:relative;height:190px;width:100%"><canvas id="volumeChart"></canvas></div>
  {% else %}
  <div class="empty-state">No story volume history yet</div>
  {% endif %}
  <div class="disclaimer">Sources: Hacker News, arXiv, GitHub Trending · Dashboard launched {{ launch_date }} · Backfills automatically as daily history accumulates</div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>
(function(){
  var history = {{ volume_history | tojson }};
  if(!history || history.length === 0 || typeof Chart === 'undefined') return;
  var labels = history.map(function(d){ return String(d.date || '').slice(5); });
  var sources = ['Hacker News','GitHub Trending','arXiv'];
  var palette = ['#378ADD','#1D9E75','#7F77DD'];
  var datasets = sources.map(function(src, idx){ return {label: src, data: history.map(function(d){return (d.sources || {})[src] || 0;}), backgroundColor: palette[idx], borderRadius: 3}; });
  var ctx = document.getElementById('volumeChart');
  if(!ctx) return;
  new Chart(ctx, {type:'bar', data:{labels:labels, datasets:datasets}, options:{responsive:true, maintainAspectRatio:false, plugins:{legend:{position:'top', align:'start', labels:{font:{size:11}, color:'#888', boxWidth:10, padding:12}}}, scales:{x:{stacked:false, grid:{display:false}, ticks:{font:{size:10}, color:'#888', maxTicksLimit:10}}, y:{stacked:false, beginAtZero:true, grid:{color:'rgba(128,128,128,0.1)'}, ticks:{font:{size:10}, color:'#888', precision:0}}}}});
})();
</script>

<div class="card">
  <div class="sec-title">Top stories</div>
  <div class="sec-sub">15 curated stories — ranked by Claude content score plus normalized source engagement</div>
  {% if top_stories %}
    {% for s in top_stories[:15] %}
    <a class="linkrow" href="{{ s.external_url or s.url }}" target="_blank">
      <div class="story-title"><span class="linked-title">{{ s.title }}</span></div>
      {% if s.summary %}<div style="font-size:12px;color:var(--text-secondary);line-height:1.45;margin-top:4px;">{{ s.summary }}</div>{% endif %}
      <div class="story-meta">
        <span>{{ s.source or s.subreddit }}</span>
        {% if s.source == 'Hacker News' %}<span>{{ s.score }} pts · {{ s.num_comments | default(0) }} comments</span>{% elif s.source == 'GitHub Trending' %}<span>{{ s.github_stars_total | default(s.score) }} stars</span>{% elif s.source == 'arXiv' %}<span>{{ s.arxiv_category | default('paper') }}</span>{% endif %}
        {% for tag in s.category_tags or [] %}<span class="cat-tag">{{ tag }}</span>{% endfor %}
        <span class="score-pill">{{ "%.1f"|format(s.combined_score | default(s.relevance_score | default(0))) }}</span>
      </div>
    </a>
    {% endfor %}
  {% else %}
    <div class="empty-state">No major AI stories today</div>
  {% endif %}
  <div class="disclaimer">Sources: Hacker News, arXiv, GitHub Trending · Stories ranked by Claude content score and normalized engagement · Updated daily</div>
</div>

<div class="card" style="padding:0">
  <div class="split-card-grid">
    <div class="split-panel">
      <div class="sec-title">Category breakdown</div>
      <div class="sec-sub">Today's curated stories by primary tag</div>
      {% if category_breakdown %}
      <div class="split-body">
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;position:relative;min-height:190px;">
          <canvas id="catDonut" width="160" height="160" style="flex-shrink:0;width:160px;height:160px"></canvas>
          <div id="catLegend" style="display:flex;flex-wrap:wrap;justify-content:center;gap:6px 14px;font-size:12px;max-width:100%"></div>
        </div>
      </div>
      {% else %}<div class="empty-state">No category mix today</div>{% endif %}
      <div class="disclaimer">Sources: Hacker News, arXiv, GitHub Trending · Categories assigned by Claude during scoring</div>
    </div>
    <div class="split-panel">
      <div class="sec-title">Trending topics</div>
      <div class="sec-sub">Themes emerging from today's curated stories</div>
      {% set sorted_topics = synthesis.trending_topics | default([]) | sort(attribute='weight', reverse=true) %}
      {% if sorted_topics %}
        {% for term in sorted_topics[:10] %}
        {% set w = term.weight | int %}
        <div style="margin:9px 0;">
          <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;"><span>{{ term.term }}</span><span class="source-chip">{{ term.category | default('theme') }}</span></div>
          <div class="bar-track" title="{{ w }} discussions / weighted mentions"><div class="bar-fill" style="width:{{ [w * 10, 100] | min }}%;"></div></div>
        </div>
        {% endfor %}
      {% else %}<div class="empty-state">No major trending topics today</div>{% endif %}
      <div class="disclaimer">Sources: Hacker News, arXiv, GitHub Trending · Themes synthesized by Claude</div>
    </div>
  </div>
</div>
<script>
(function(){
  var breakdown = {{ category_breakdown | tojson }};
  var labels = Object.keys(breakdown || {});
  var values = labels.map(function(k){return breakdown[k];});
  var canvas = document.getElementById('catDonut');
  if(!canvas || labels.length === 0 || typeof Chart === 'undefined') return;
  var colors = ['#378ADD','#7F77DD','#1D9E75','#EF9F27','#E24B4A','#D4537E','#BA7517','#4267B2','#888780','#3DC48A'];
  new Chart(canvas, {
    type: 'doughnut',
    data: {labels: labels, datasets: [{data: values, backgroundColor: colors.slice(0, labels.length), borderWidth: 2, borderColor: getComputedStyle(document.body).getPropertyValue('--bg-primary') || '#fff'}]},
    options: {responsive:false, cutout:'58%', plugins:{legend:{display:false}, tooltip:{callbacks:{label:function(ctx){return ctx.label + ': ' + ctx.parsed + ' articles';}}}}}
  });
  var legend=document.getElementById('catLegend');
  labels.forEach(function(k,i){ var row=document.createElement('div'); row.style.cssText='display:flex;align-items:center;gap:5px'; var dot=document.createElement('span'); dot.style.cssText='width:8px;height:8px;border-radius:50%;background:'+colors[i%colors.length]; var txt=document.createElement('span'); txt.style.color='var(--text-secondary)'; txt.textContent=k+' ('+values[i]+')'; row.appendChild(dot); row.appendChild(txt); legend.appendChild(row); });
})();
</script>

<div class="card">
  <div class="sec-row">
    <div><div class="sec-title">Source hot topics</div><div class="sec-sub">Top items from each source today — switch via dropdown</div></div>
    <select id="sourceSelect" onchange="filterSource(this.value)">
      {% for source, items in source_hot_topics.items() %}<option value="{{ source }}">{{ source }} · {{ items | length }}</option>{% endfor %}
    </select>
  </div>
  {% if source_hot_topics %}
  <div id="sourceStories">
    {% for source, items in source_hot_topics.items() %}
    <div class="source-group" data-source="{{ source }}"{% if not loop.first %} style="display:none"{% endif %}>
      {% for s in items[:7] %}
      <a class="linkrow" href="{{ s.external_url or s.url }}" target="_blank">
        <div class="story-title"><span class="linked-title">{{ s.title }}</span></div>
        <div class="story-meta"><span>{{ s.source or s.subreddit }}</span><span class="score-pill">{{ "%.1f"|format(s.combined_score | default(s.relevance_score | default(0))) }}</span>{% for tag in s.category_tags or [] %}<span class="cat-tag">{{ tag }}</span>{% endfor %}</div>
      </a>
      {% endfor %}
    </div>
    {% endfor %}
  </div>
  {% else %}<div class="empty-state">No major source stories today</div>{% endif %}
  <div class="disclaimer">Sources: Hacker News, arXiv, GitHub Trending · Reuses today's curated story pool · Updated daily</div>
</div>
<script>
function filterSource(val){document.querySelectorAll('.source-group').forEach(function(g){g.style.display = g.dataset.source === val ? '' : 'none';});}
</script>

<div class="card">
  <div class="sec-title">Fintech & payments spotlight</div>
  <div class="sec-sub">AI news in payments, lending, fraud, banking — with strategic implications for card networks</div>
  {% if fintech_stories %}
    {% for s in fintech_stories[:5] %}
    <a class="linkrow" href="{{ s.external_url or s.url }}" target="_blank" style="background:var(--bg-secondary);border-radius:var(--radius-md);padding:11px 13px;margin-bottom:8px;border-bottom:none;">
      <div class="story-title"><span class="linked-title">{{ s.title }}</span></div>
      {% if s.summary %}<div style="font-size:12px;color:var(--text-secondary);line-height:1.45;margin-top:4px;">{{ s.summary }}</div>{% endif %}
      <div class="story-meta"><span>{{ s.source or s.subreddit }}</span>{% for tag in s.category_tags or [] %}<span class="cat-tag">{{ tag }}</span>{% endfor %}</div>
    </a>
    {% endfor %}
    {% if synthesis.fintech_implications %}<div style="margin-top:10px;font-size:12px;color:var(--text-primary);line-height:1.5;border-top:0.5px solid var(--border);padding-top:10px;"><strong style="font-weight:500;">Strategic read:</strong> {{ synthesis.fintech_implications | replace('Mastercard', 'international payment schemes') | replace('mastercard', 'international payment schemes') | replace('card networks like Visa/Mastercard', 'international payment schemes') }}</div>{% endif %}
  {% else %}<div class="empty-state">No major fintech AI stories today</div>{% endif %}
  <div class="disclaimer">Sources: Hacker News, arXiv, GitHub Trending · Strategic implications synthesized by Claude Sonnet · Updated daily</div>
</div>

"""
PAGE_2_BODY = r"""

<div class="card">
  <div class="sec-title">All models — snapshot</div>
  <div class="sec-sub">Live sentiment + buzz from Hacker News discussion threads (last 3 days)</div>
  <div class="model-snapshot-grid">
    {% for m in model_sentiments %}
    <div class="model-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:5px;">
        <div><div style="font-size:14px;font-weight:500;">{{ m.model_config.name }}</div><div style="font-size:11px;color:var(--text-secondary);">{{ m.model_config.maker }}</div></div>
        {% if m.story_count or m.comment_count %}<span class="pill {{ 'sent-pos' if m.sentiment_score >= 6 else 'sent-neu' }}">{{ "%.1f"|format(m.sentiment_score | default(0)) }}</span>{% else %}<span class="pill sent-neu">—</span>{% endif %}
      </div>
      <div class="bar-track" style="height:4px;margin:8px 0 6px;"><div style="height:4px;border-radius:99px;background:{{ m.model_config.color }};width:{{ m.buzz_volume | default(0) }}%;"></div></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;font-size:11px;color:var(--text-secondary);">
        <span>Buzz <strong style="color:var(--text-primary);font-weight:500;">{{ m.buzz_volume | default(0) }}%</strong></span>
        <span>Mentions <strong style="color:var(--text-primary);font-weight:500;">{{ m.comment_count | default(m.story_count | default(0)) }}</strong></span>
        {% if m.wow_delta_pct %}<span class="{{ 'up' if m.wow_delta_pct.startswith('+') else 'down' }}" style="font-weight:500;">{{ m.wow_delta_pct }} WoW</span>{% else %}<span class="neu">No prior WoW</span>{% endif %}
      </div>
      {% if not (m.story_count or m.comment_count) %}<div style="font-size:11px;color:var(--text-tertiary);margin-top:6px;">No discussion today</div>{% endif %}
    </div>
    {% endfor %}
  </div>
  <div class="disclaimer">Sources: Hacker News comments · Sentiment classified by Claude Haiku · Updated daily</div>
</div>

<div class="card">
  <div class="sec-row">
    <div><div class="sec-title">Sentiment trends — last 30 days</div><div class="sec-sub">Toggle between Hacker News sentiment and GitHub ecosystem star activity</div></div>
    <div class="toggle-row"><button class="toggle-btn active" id="hnToggle" onclick="setTrendMode('hn')">Hacker News</button><button class="toggle-btn" id="ghToggle" onclick="setTrendMode('github')">GitHub</button></div>
  </div>
  {% if sentiment_history and sentiment_history.labels %}
  <div style="position:relative;height:250px;width:100%;margin-top:8px"><canvas id="sentimentChart"></canvas></div>
  <div id="hnDisclaimer" class="disclaimer">Source: Hacker News comments · Sentiment scored by Claude Haiku · Each line shows average sentiment score (1–10). Backfills automatically as daily history accumulates.</div>
  <div id="ghDisclaimer" class="disclaimer" style="display:none;">Source: GitHub stars on official ecosystem repos · Each line shows daily new stars across primary repos. Backfills automatically as daily history accumulates.</div>
  {% else %}
  <div class="empty-state">No model trend history yet</div>
  <div class="disclaimer">Sources: Hacker News comments + GitHub stars · Backfills automatically as daily history accumulates</div>
  {% endif %}
</div>
<script>
var trendChart = null;
var trendHistory = {{ sentiment_history | tojson }};
function buildTrendDatasets(mode){
  if(!trendHistory || !trendHistory.models) return [];
  return trendHistory.models.map(function(m){return {label:m.name, data:(mode==='github' ? (m.github_stars || []) : (m.scores || [])), borderColor:m.color, backgroundColor:'transparent', borderWidth:2, pointRadius:0, tension:0.3};});
}
function setTrendMode(mode){
  if(!trendChart) return;
  document.getElementById('hnToggle').classList.toggle('active', mode==='hn');
  document.getElementById('ghToggle').classList.toggle('active', mode==='github');
  document.getElementById('hnDisclaimer').style.display = mode==='hn' ? '' : 'none';
  document.getElementById('ghDisclaimer').style.display = mode==='github' ? '' : 'none';
  trendChart.data.datasets = buildTrendDatasets(mode);
  trendChart.options.scales.y.min = mode==='hn' ? 1 : 0;
  trendChart.options.scales.y.max = mode==='hn' ? 10 : undefined;
  trendChart.options.scales.y.ticks.stepSize = mode==='hn' ? 1 : undefined;
  trendChart.update();
}
(function(){
  if(!trendHistory || !trendHistory.labels || trendHistory.labels.length === 0 || typeof Chart === 'undefined') return;
  var ctx = document.getElementById('sentimentChart'); if(!ctx) return;
  trendChart = new Chart(ctx,{type:'line',data:{labels:trendHistory.labels,datasets:buildTrendDatasets('hn')},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{position:'top',align:'start',labels:{font:{size:11},color:'#888',usePointStyle:true,pointStyle:'line',boxWidth:24,padding:12}}},scales:{x:{grid:{display:false},ticks:{font:{size:10},color:'#888',maxTicksLimit:8}},y:{min:1,max:10,grid:{color:'rgba(128,128,128,0.1)'},ticks:{font:{size:10},color:'#888',stepSize:1}}}}});
})();
</script>

<div class="card">
  <div class="sec-title">What's driving each model's trend</div>
  <div class="sec-sub">Why each model's sentiment moved this week — synthesized from discussion threads and curated stories</div>
  {% for m in model_sentiments %}
  <div style="padding:12px 0;{% if not loop.last %}border-bottom:0.5px solid var(--border);{% endif %}">
    <div style="font-size:13px;font-weight:500;color:{{ m.model_config.color }};margin-bottom:6px;">{{ m.model_config.name }} <span style="font-size:11px;font-weight:400;color:var(--text-secondary);">{{ "%.1f"|format(m.sentiment_score | default(0)) }}/10{% if m.wow_delta_pct %} · {{ m.wow_delta_pct }} WoW{% endif %}</span></div>
    {% if m.trend_drivers %}
      {% for d in m.trend_drivers[:3] %}
      {% set dir = d.direction | default('neutral') %}
      <a class="driver-row link-card" href="{{ d.url | default('#') }}"{% if d.url %} target="_blank"{% endif %}>{% if dir in ['up','positive'] %}<span class="signal-icon up">▲</span>{% elif dir in ['down','negative'] %}<span class="signal-icon down">▼</span>{% else %}<span class="signal-icon neutral">●</span>{% endif %}<span class="linked-title">{{ d.text }}</span></a>
      {% endfor %}
    {% else %}<div class="empty-state">Not enough discussion this week to identify drivers.</div>{% endif %}
  </div>
  {% endfor %}
  <div class="disclaimer">Sources: Hacker News comments + curated stories from HN/arXiv/GitHub · Drivers synthesized by Claude Sonnet</div>
</div>

<div class="card">
  <div class="sec-title">Model deep dive</div>
  <div class="sec-sub">MAU, market share, mention sentiment, recent changes, and key people activity</div>
  <select id="modelSelect" onchange="filterModel(this.value)" style="width:100%;margin:6px 0 14px;">
    {% for m in model_sentiments %}<option value="{{ m.model_config.name }}">{{ m.model_config.name }} ({{ m.model_config.maker }})</option>{% endfor %}
  </select>
  {% for m in model_sentiments %}
  {% set deep = m.deep or {} %}
  {% set model_id = m.model_config.id %}
  <div class="model-deep" data-model="{{ m.model_config.name }}"{% if not loop.first %} style="display:none"{% endif %}>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:10px;margin-bottom:14px;">
      <div class="mcard"><div class="mlabel">Sentiment</div><div class="mvalue" style="color:{{ m.model_config.color }};">{{ "%.1f"|format(m.sentiment_score | default(0)) }}</div><div style="font-size:10px;color:var(--text-secondary);">out of 10</div></div>
      <div class="mcard deep-metric"><div class="mlabel">{% if model_id == 'llama' %}Downloads{% else %}MAU{% endif %}</div><div class="mvalue">{{ deep.mau | default('Not disclosed') }}</div><div class="metric-note">{% if deep.last_updated %}as of {{ deep.last_updated }}{% else %}weekly cache{% endif %}</div></div>
      <div class="mcard deep-metric"><div class="mlabel">{% if model_id == 'llama' %}Derivatives{% else %}Market share{% endif %}</div><div class="mvalue">{{ deep.market_share | default('—') }}</div><div class="metric-note">{% if deep.last_updated %}as of {{ deep.last_updated }}{% else %}weekly cache{% endif %}</div></div>
      <div class="mcard deep-metric"><div class="mlabel">Buzz volume</div><div class="mvalue">{{ m.buzz_volume | default(0) }}%</div><div class="metric-note">HN discussion</div></div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;">
      <div class="stat-card trait-panel trait-strength"><div style="font-size:11px;font-weight:500;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px;">Strengths</div>{% if deep.strengths %}{% for s in deep.strengths %}<div class="cap-item"><div>{{ s }}</div></div>{% endfor %}{% else %}<div class="empty-state">Not enough discussion this month to synthesize.</div>{% endif %}</div>
      <div class="stat-card trait-panel trait-weakness"><div style="font-size:11px;font-weight:500;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px;">Weaknesses</div>{% if deep.weaknesses %}{% for w in deep.weaknesses %}<div class="cap-item"><div>{{ w }}</div></div>{% endfor %}{% else %}<div class="empty-state">Not enough discussion this month to synthesize.</div>{% endif %}</div>
    </div>

    <div style="margin-bottom:14px;">
      <div class="sec-title">Mention sentiment — current vs prior 30 days</div>
      <div class="sec-sub">Positive vs negative HN mentions · prior bars appear after 60+ days of history</div>
      {% set br = m.mentions_breakdown or {} %}
      {% set pos = br.positive | default(0) %}{% set neg = br.negative | default(0) %}{% set neu = br.neutral | default(0) %}{% set total = pos + neg + neu %}
      {% if total >= 5 %}
      <div style="display:grid;gap:8px;margin-top:8px;">
        <div><div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px;"><span>Positive</span><span>{{ pos }}</span></div><div class="bar-track"><div style="height:100%;background:#3b6d11;border-radius:99px;width:{{ (pos / total * 100) | round(0) }}%;"></div></div></div>
        <div><div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px;"><span>Negative</span><span>{{ neg }}</span></div><div class="bar-track"><div style="height:100%;background:#a32d2d;border-radius:99px;width:{{ (neg / total * 100) | round(0) }}%;"></div></div></div>
        <div><div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px;"><span>Neutral</span><span>{{ neu }}</span></div><div class="bar-track"><div style="height:100%;background:#888780;border-radius:99px;width:{{ (neu / total * 100) | round(0) }}%;"></div></div></div>
      </div>
      {% else %}<div class="empty-state">Low sample — fewer than 5 classified mentions today</div>{% endif %}
    </div>

    <div style="margin-bottom:14px;">
      <div class="sec-title">Recent changes</div>
      <div class="sec-sub">Releases, announcements, and major news from the last 90 days</div>
      {% if deep.recent_changes %}{% for c in deep.recent_changes[:7] %}<a class="timeline-row link-card" href="{{ c.url | default('#') }}"{% if c.url %} target="_blank"{% endif %}><div style="width:58px;color:var(--text-secondary);flex-shrink:0;">{{ c.date }}</div><div><span class="linked-title">{{ c.text }}</span></div></a>{% endfor %}{% else %}<div class="empty-state">No major releases or announcements in the last 90 days.</div>{% endif %}
    </div>

    <div>
      <div class="sec-title">Key people quotes</div>
      <div class="sec-sub">Recent posts from leadership and key researchers</div>
      {% if deep.key_people %}{% for p in deep.key_people %}<a class="person-chip link-card" href="{{ p.source_url | default('#') }}"{% if p.source_url %} target="_blank"{% endif %} style="text-decoration:none;color:inherit;">{% if p.photo_url %}<img class="avatar" src="{{ p.photo_url }}" alt="{{ p.name }}" style="object-fit:cover;">{% else %}<div class="avatar" style="background:{{ m.model_config.color }}33;color:{{ m.model_config.color }};">{{ p.initials | default(p.name[:2]) }}</div>{% endif %}<div style="flex:1;min-width:0;"><div style="font-size:13px;font-weight:500;">{{ p.name }} <span style="color:var(--text-secondary);font-weight:400;font-size:11px;">{{ p.role | default('') }}</span></div><div class="quote-text">{{ p.quote }}</div><div class="quote-meta">{{ p.date }} · {{ p.platform | default('X') }}</div></div></a>{% endfor %}{% else %}<div class="empty-state">No recent public posts from this model's leadership in the last 60 days.</div>{% endif %}
    </div>
    <div class="disclaimer">Sources: Web search of analyst reports, press releases, public posts, and curated HN/arXiv/GitHub stories · Phase 3 weekly/monthly caches will populate unavailable fields</div>
  </div>
  {% endfor %}
</div>
<script>
function filterModel(val){document.querySelectorAll('.model-deep').forEach(function(g){g.style.display = g.dataset.model === val ? '' : 'none';});}
</script>

"""
PAGE_3_BODY = r"""
<div style="margin-bottom:14px;">
  <div style="font-size:18px;font-weight:500;">AI finance</div>
  <div style="font-size:12px;color:var(--text-secondary);margin-top:2px;">Funding, valuations, market pulse, and competitive capital intelligence — {{ today }}</div>
</div>

<!-- COMP 1: This week in AI funding -->
<div class="card">
  <div class="sec-title">This week in AI funding</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-top:10px;">
    <div class="mcard">
      <div class="mlabel">Total raised</div>
      <div class="mvalue">{% if funding_summary.total_raised and funding_summary.total_raised != 'N/A' %}${{ funding_summary.total_raised }}{% else %}N/A{% endif %}</div>
      <div style="font-size:11px;color:var(--text-secondary);">{% if funding_summary.total_raised_change %}{{ funding_summary.total_raised_change }} vs last week{% else %}{{ funding_summary.deals_closed | default(0) }} deals tracked{% endif %}</div>
    </div>
    <div class="mcard">
      <div class="mlabel">Deals closed</div>
      <div class="mvalue">{{ funding_summary.deals_closed | default('N/A') }}</div>
      <div style="font-size:11px;color:var(--text-secondary);">{% if funding_summary.deals_change %}{{ funding_summary.deals_change }} vs last week{% else %}past 2 weeks{% endif %}</div>
    </div>
    <div class="mcard">
      <div class="mlabel">Largest round</div>
      <div class="mvalue">{% if funding_summary.largest_round and funding_summary.largest_round != 'N/A' %}${{ funding_summary.largest_round }}{% else %}N/A{% endif %}</div>
      <div style="font-size:11px;color:var(--text-secondary);">{{ funding_summary.largest_round_company | default('—') }}</div>
    </div>
    <div class="mcard">
      <div class="mlabel">Median valuation</div>
      <div class="mvalue">{% if funding_summary.median_premoney and funding_summary.median_premoney != 'N/A' %}${{ funding_summary.median_premoney }}{% else %}N/A{% endif %}</div>
      <div style="font-size:11px;color:var(--text-secondary);">{% if funding_summary.median_premoney == 'N/A' %}most undisclosed{% elif funding_summary.median_trend == 'up' %}Trending up{% elif funding_summary.median_trend == 'down' %}Trending down{% else %}across disclosed rounds{% endif %}</div>
    </div>
  </div>
  <div class="disclaimer">Sources: TechCrunch, The Information, Reuters, Bloomberg, PitchBook &middot; Aggregated by Claude Sonnet via web search &middot; Refreshed Mondays</div>
</div>

<!-- COMP 2: AI ETF market pulse + bubble chart -->
<div class="card">
  <div class="sec-title">AI ETF market pulse</div>
  <div class="sec-sub">US-listed AI ETFs — prices as of {{ today }}</div>
  <div style="display:flex;gap:0;padding:0 0 6px;border-bottom:0.5px solid var(--border-strong);margin-bottom:2px;">
    <div class="col-hdr" style="width:52px;">Ticker</div>
    <div class="col-hdr" style="flex:1;">Name</div>
    <div class="col-hdr" style="width:80px;">Trend</div>
    <div class="col-hdr" style="width:60px;text-align:right;">Price</div>
    <div class="col-hdr" style="width:60px;text-align:right;">DoD</div>
    <div class="col-hdr" style="width:50px;text-align:right;">1-yr</div>
    <div class="col-hdr" style="width:60px;text-align:right;">AUM</div>
  </div>
  {% for e in etfs %}
  <div style="display:flex;align-items:center;gap:0;padding:9px 0;border-bottom:0.5px solid var(--border);">
    <a class="linkable" href="https://finance.yahoo.com/quote/{{ e.ticker }}" target="_blank" style="font-size:13px;font-weight:500;color:var(--text-info);width:52px;text-decoration:none;">{{ e.ticker }}</a>
    <div style="font-size:11px;color:var(--text-secondary);flex:1;min-width:0;padding-right:6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ e.name }}</div>
    <div style="width:80px;height:18px;">
      {% if e.sparkline %}
      <svg width="80" height="18" viewBox="0 0 80 18" preserveAspectRatio="none">
        <polyline points="{{ e.sparkline_points }}" fill="none" stroke="{% if (e.dod_pct | default(0)) >= 0 %}#3b6d11{% else %}#a32d2d{% endif %}" stroke-width="1.2"/>
      </svg>
      {% endif %}
    </div>
    <div style="font-size:13px;font-weight:500;width:60px;text-align:right;">${{ "%.2f"|format(e.price | default(0)) }}</div>
    <div style="font-size:12px;font-weight:500;width:60px;text-align:right;{% if (e.dod_pct | default(0)) >= 0 %}color:#3b6d11{% else %}color:#a32d2d{% endif %};">{% if (e.dod_pct | default(0)) >= 0 %}+{% endif %}{{ "%.2f"|format(e.dod_pct | default(0)) }}%</div>
    <div style="font-size:12px;width:50px;text-align:right;{% if (e.year_return_pct | default(0)) >= 0 %}color:#3b6d11{% else %}color:#a32d2d{% endif %};">{% if (e.year_return_pct | default(0)) >= 0 %}+{% endif %}{{ "%.0f"|format(e.year_return_pct | default(0)) }}%</div>
    <div style="font-size:11px;color:var(--text-secondary);width:60px;text-align:right;">{{ e.aum | default("n/a") }}</div>
  </div>
  {% endfor %}
  <div style="position:relative;height:280px;width:100%;margin-top:18px;">
    <canvas id="etfBubbleChart"></canvas>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:14px;margin-top:8px;font-size:11px;color:var(--text-secondary);">
    {% for e in etfs %}
    <span style="display:flex;align-items:center;gap:5px;"><span style="width:8px;height:8px;border-radius:50%;background:{{ e.color | default('#888') }};"></span>{{ e.ticker }}</span>
    {% endfor %}
    <span style="margin-left:auto;font-style:italic;">· Bubble size = AUM</span>
  </div>
  <div class="disclaimer">Sources: Yahoo Finance &middot; Live ETF prices and 90-day sparkline &middot; Updated daily</div>
</div>

<!-- COMP 3: Recent funding rounds -->
<div class="card">
  <div class="sec-title">Recent funding rounds</div>
  <div class="sec-sub">Sorted by round size — past 2 weeks</div>
  <div style="display:flex;gap:0;padding:0 0 6px;border-bottom:0.5px solid var(--border-strong);margin-bottom:2px;margin-top:8px;">
    <div class="col-hdr" style="flex:2;">Company</div>
    <div class="col-hdr" style="width:60px;text-align:right;">Date</div>
    <div class="col-hdr" style="width:80px;text-align:right;">Amount</div>
    <div class="col-hdr" style="width:80px;text-align:right;">Valuation</div>
    <div class="col-hdr" style="width:80px;text-align:center;">Stage</div>
    <div class="col-hdr" style="width:120px;text-align:right;">Lead investor</div>
  </div>
  {% if funding_rounds %}
{% for r in funding_rounds %}
  <div style="display:flex;align-items:flex-start;gap:0;padding:10px 0;border-bottom:0.5px solid var(--border);">
    <div style="flex:2;min-width:0;">
      <div style="font-size:13px;font-weight:500;">{% if r.url %}<a class="linkable" href="{{ r.url }}" target="_blank" style="color:var(--text-primary);text-decoration:none;">{{ r.company }}</a>{% else %}{{ r.company }}{% endif %} <span style="font-size:10px;color:var(--text-tertiary);font-weight:400;">{{ r.country | default('') }}</span></div>
      <div style="font-size:11px;color:var(--text-secondary);">{{ r.category | default('') }}</div>
    </div>
    <div style="width:60px;text-align:right;font-size:12px;color:var(--text-secondary);">{{ r.date | default('—') }}</div>
    <div style="width:80px;text-align:right;font-size:13px;font-weight:500;">{% if r.amount and r.amount != 'N/A' %}${{ r.amount }}{% else %}N/A{% endif %}</div>
    <div style="width:80px;text-align:right;font-size:13px;font-weight:500;">{% if r.valuation and r.valuation != 'N/A' %}${{ r.valuation }}{% else %}<span style="color:var(--text-tertiary);font-weight:400;">N/A</span>{% endif %}</div>
    <div style="width:80px;text-align:center;"><span class="pill" style="background:#e6f1fb;color:#0c447c;">{{ r.stage }}</span></div>
    <div style="width:120px;text-align:right;font-size:12px;{% if r.lead_investor == 'N/A' %}color:var(--text-tertiary){% else %}color:var(--text-secondary){% endif %};">{{ r.lead_investor }}</div>
  </div>
  {% endfor %}
{% else %}
<div class="empty-state">No major AI funding rounds tracked in the past 2 weeks.</div>
{% endif %}

  <div class="disclaimer">Sources: TechCrunch, The Information, Reuters, Bloomberg, PitchBook &middot; Rounds verified via primary press releases &middot; Refreshed Mondays</div>
</div>

<!-- COMP 4: Private + Public AI valuation leaderboards -->
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
  <div class="card" style="margin-bottom:0;">
    <div class="sec-title">Private AI companies by valuation</div>
    <div class="sec-sub">Estimated valuations · last known round</div>
    {% set max_priv = (private_ai[0].valuation_billions | default(1)) if private_ai else 1 %}
    {% for p in private_ai %}
    <div style="padding:8px 0;border-bottom:0.5px solid var(--border);">
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:3px;">
        <div style="font-size:12px;font-weight:{% if loop.index <= 3 %}500{% else %}400{% endif %};">{{ loop.index }}. {{ p.name }}</div>
        <div style="font-size:12px;font-weight:500;color:#7F77DD;">${{ p.valuation_billions }}B</div>
      </div>
      <div style="font-size:10px;color:var(--text-tertiary);margin-bottom:4px;">Last round: ${{ p.last_round | default('—') }} · {{ p.last_round_date | default('—') }}</div>
      <div style="height:3px;background:var(--bg-secondary);border-radius:2px;"><div style="height:3px;border-radius:2px;background:#7F77DD;width:{{ ((p.valuation_billions / max_priv) * 100) | round | int }}%;"></div></div>
    </div>
    {% endfor %}
    <div class="disclaimer">Sources: Web search of analyst reports + PitchBook estimates &middot; Estimated valuations from public sources &middot; Refreshed Mondays</div>
</div>
  <div class="card" style="margin-bottom:0;">
    <div class="sec-title">Public AI — top 10 by market cap</div>
    <div class="sec-sub">Market cap in $B · {{ today }} close</div>
    {% if public_ai %}
    {% set max_cap = public_ai[0].market_cap_billions %}
    {% for p in public_ai %}
    <a class="linkrow" href="https://finance.yahoo.com/quote/{{ p.ticker }}" target="_blank" style="padding:7px 8px;">
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:3px;">
        <div style="font-size:12px;font-weight:{% if loop.index <= 3 %}500{% else %}400{% endif %};">{{ loop.index }}. {{ p.name }} <span style="font-weight:400;color:var(--text-secondary);font-size:10px;">{{ p.ticker }}</span></div>
        <div style="display:flex;align-items:center;gap:6px;">
          <span style="font-size:11px;{% if p.dod_pct >= 0 %}color:#3b6d11{% else %}color:#a32d2d{% endif %};">{% if p.dod_pct >= 0 %}+{% endif %}{{ "%.2f"|format(p.dod_pct) }}%</span>
          <span style="font-size:12px;font-weight:500;">${{ p.market_cap_billions }}B</span>
        </div>
      </div>
      <div style="height:3px;background:var(--bg-secondary);border-radius:2px;"><div style="height:3px;border-radius:2px;background:#1d9e75;width:{{ ((p.market_cap_billions / max_cap) * 100) | round | int }}%;"></div></div>
    </a>
    {% endfor %}
    {% endif %}
    <div class="disclaimer">Sources: Yahoo Finance &middot; Live market caps in USD billions &middot; Updated daily</div>
</div>
</div>

<!-- COMP 5: The arms race -->
<div class="card">
  <div class="sec-title">The arms race — quarterly funding by player</div>
  <div class="sec-sub">External capital raised per quarter, Q1 2025 — Q2 2026 · $B</div>
  <div style="position:relative;height:240px;width:100%;margin-top:8px;">
    <canvas id="armsRaceChart"></canvas>
  </div>
  <div style="font-size:10px;color:var(--text-tertiary);text-align:right;margin-top:4px;font-style:italic;">* Q2 2026 in progress</div>
  <div class="disclaimer">Sources: TechCrunch, The Information, PitchBook &middot; Quarterly external capital aggregated by Claude Sonnet &middot; Refreshed Mondays</div>
</div>

<!-- COMP 6: VC league table -->
<div class="card">
  <div class="sec-title">VC league table — top AI investors this quarter</div>
  <div class="sec-sub">Ranked by deals closed · current quarter or latest available prior quarter</div>
  {% if vc_league %}
  <div style="display:flex;gap:0;padding:0 0 6px;border-bottom:0.5px solid var(--border-strong);margin-bottom:2px;margin-top:8px;">
    <div class="col-hdr" style="width:24px;">#</div>
    <div class="col-hdr" style="flex:1;">Firm</div>
    <div class="col-hdr" style="width:60px;text-align:right;">Deals</div>
    <div class="col-hdr" style="width:80px;text-align:right;">Deployed</div>
    <div class="col-hdr" style="width:160px;text-align:right;">Focus</div>
  </div>
  {% for v in vc_league %}
  <div style="display:flex;align-items:center;gap:0;padding:8px 0;border-bottom:0.5px solid var(--border);">
    <div style="width:24px;font-size:12px;color:var(--text-secondary);">{{ loop.index }}</div>
    <div style="flex:1;font-size:13px;font-weight:500;">{{ v.firm }}</div>
    <div style="width:60px;text-align:right;font-size:13px;font-weight:500;">{{ v.deals }}</div>
    <div style="width:80px;text-align:right;font-size:13px;font-weight:500;">{% if v.deployed and v.deployed != 'N/A' %}${{ v.deployed }}{% else %}N/A{% endif %}</div>
    <div style="width:160px;text-align:right;font-size:11px;color:var(--text-secondary);">{{ v.focus }}</div>
  </div>
  {% endfor %}
  {% else %}
  <div style="padding:18px 0;font-size:12px;color:var(--text-tertiary);text-align:center;font-style:italic;">VC league data unavailable for this quarter — quarterly aggregates publish with delay.</div>
  {% endif %}
  <div class="disclaimer">Sources: PitchBook, Crunchbase, TechCrunch &middot; Deal counts verified via firm press releases &middot; Refreshed Mondays</div>
</div>

<!-- COMP 7: Money flow analysis -->
<div class="card">
  <div class="sec-title">Money flow analysis</div>
  <div class="sec-sub">Signal-driven directional insights from this week's capital movements</div>
  <div style="margin-top:10px;display:flex;flex-direction:column;gap:8px;">
    {% if money_flow %}
{% for f in money_flow %}
    <div class="signal-row signal-{% if f.direction in ['up','positive'] %}up{% elif f.direction in ['down','negative'] %}down{% elif f.direction in ['warning'] %}warning{% else %}neu{% endif %}">{{ f.text }}</div>
    {% endfor %}
{% else %}
<div class="empty-state">No directional signals identified this week.</div>
{% endif %}

  </div>
  <div class="disclaimer">Sources: This week's funding rounds, M&amp;A, and fintech deals &middot; Synthesized by Claude Sonnet &middot; Refreshed Mondays</div>
</div>

<!-- COMP 8: M&A & exits tracker -->
<div class="card">
  <div class="sec-title">M&A & exits tracker</div>
  <div class="sec-sub">Acquisitions, strategic investments, IPO filings, acqui-hires</div>
  {% if ma_tracker %}
  <div style="margin-top:10px;">
    {% for m in ma_tracker %}
    <div style="display:flex;gap:14px;padding:10px 0;border-bottom:0.5px solid var(--border);">
      <div style="width:48px;color:var(--text-secondary);font-size:11px;flex-shrink:0;padding-top:2px;">{{ m.date }}</div>
      <div style="flex:1;min-width:0;">
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
          <span style="font-size:13px;font-weight:500;">{% if m.url %}<a class="linkable" href="{{ m.url }}" target="_blank" style="color:var(--text-primary);text-decoration:none;">{{ m.title }}</a>{% else %}{{ m.title }}{% endif %}</span>
          <span class="pill" style="background:{% if m.type == 'Acquisition' %}#eaf3de;color:#3b6d11{% elif m.type == 'IPO filing' %}#e6f1fb;color:#0c447c{% elif m.type == 'Investment' %}#eeedfe;color:#3c3489{% else %}#f1efe8;color:#5f5e5a{% endif %};">{{ m.type }}</span>
        </div>
        <div style="font-size:11px;color:var(--text-secondary);margin-top:3px;">{{ m.detail }}</div>
      </div>
    </div>
    {% endfor %}
  </div>
  {% else %}
  <div style="padding:18px 0;font-size:12px;color:var(--text-tertiary);text-align:center;font-style:italic;">No major M&A activity tracked in the past 30 days.</div>
  {% endif %}
  <div class="disclaimer">Sources: TechCrunch, Reuters, Bloomberg, SEC filings &middot; Verified against primary filings where applicable &middot; Refreshed Mondays</div>
</div>

<!-- COMP 9: Fintech & payments AI spotlight -->
<div class="card">
  <div class="sec-title">Fintech & payments AI spotlight</div>
  <div class="sec-sub">AI deals in payments, lending, fraud, embedded finance, and banking infrastructure — with strategic implications for card networks and issuers</div>
  <div style="margin-top:10px;display:flex;flex-direction:column;gap:10px;">
    {% if fintech_spotlight %}
{% for f in fintech_spotlight %}
    <div style="background:var(--bg-secondary);border-radius:var(--radius-md);padding:14px 16px;">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px;">
        <span style="font-size:14px;font-weight:500;">{% if f.url %}<a class="linkable" href="{{ f.url }}" target="_blank" style="color:var(--text-primary);text-decoration:none;">{{ f.company }}</a>{% else %}{{ f.company }}{% endif %}</span>
        <span style="font-size:11px;color:var(--text-info);">{{ f.deal_type }}</span>
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;">
        {% for tag in f.tags %}<span class="cat-tag">{{ tag }}</span>{% endfor %}
      </div>
      <div style="font-size:12px;color:var(--text-primary);line-height:1.5;margin-bottom:10px;">{{ f.description }}</div>
      {% if f.strategic %}
      <div style="font-size:10px;font-weight:500;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px;">Strategic implication</div>
      <div style="font-size:12px;color:var(--text-primary);line-height:1.5;border-top:0.5px solid var(--border);padding-top:8px;">{{ f.strategic }}</div>
      {% endif %}
      {% if f.url %}
      <div style="margin-top:8px;font-size:11px;"><a href="{{ f.url }}" target="_blank" style="color:var(--text-info);text-decoration:none;">Read source →</a></div>
      {% endif %}
    </div>
    {% endfor %}
{% else %}
<div class="empty-state">No major fintech AI deals this week.</div>
{% endif %}

  </div>
  <div class="disclaimer">Sources: TechCrunch, The Information, Reuters, Bloomberg &middot; Strategic implications by Claude Sonnet &middot; Refreshed Mondays</div>
</div>

<script>
(function(){
  // Bubble chart for ETFs
  var etfData = {{ etfs | tojson }};
  if(!etfData || etfData.length === 0) return;
  var ctx = document.getElementById('etfBubbleChart');
  if(!ctx) return;
  // Parse AUM strings like "$1.1B" or "$711M" into billions for bubble size
  function parseAum(a){
    if(!a) return 0;
    var m = String(a).match(/([0-9.]+)\s*([BMK]?)/i);
    if(!m) return 0;
    var v = parseFloat(m[1]);
    var unit = (m[2]||'B').toUpperCase();
    if(unit === 'M') v = v/1000;
    if(unit === 'K') v = v/1000000;
    return v;
  }
  var datasets = etfData.map(function(e){
    var aum = parseAum(e.aum);
    return {
      label: e.ticker,
      data: [{x: e.year_return_pct || 0, y: e.price || 0, r: Math.max(8, Math.sqrt(aum) * 14)}],
      backgroundColor: (e.color || '#888') + 'cc',
      borderColor: e.color || '#888',
      borderWidth: 1
    };
  });
  new Chart(ctx, {
    type: 'bubble',
    data: { datasets: datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: function(c){ var d = etfData[c.datasetIndex]; return d.ticker + ': $' + (d.price||0).toFixed(2) + ', ' + (d.year_return_pct>=0?'+':'') + (d.year_return_pct||0).toFixed(0) + '% 1y, AUM ' + (d.aum||'—'); } } }
      },
      scales: {
        x: { title: { display: true, text: '1-year return (%)', color: '#888', font: {size:11} }, grid: { color: 'rgba(128,128,128,0.1)' }, ticks: { font: { size: 10 }, color: '#888', callback: function(v){return (v>=0?'+':'')+v+'%';} } },
        y: { title: { display: true, text: 'Current price ($)', color: '#888', font: {size:11} }, grid: { color: 'rgba(128,128,128,0.1)' }, ticks: { font: { size: 10 }, color: '#888', callback: function(v){return '$'+v;} } }
      }
    }
  });
})();
(function(){
  // Arms race chart
  var arms = {{ arms_race | tojson }};
  if(!arms || !arms.quarters || arms.quarters.length === 0) return;
  var ctx = document.getElementById('armsRaceChart');
  if(!ctx) return;
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: arms.quarters,
      datasets: arms.players.map(function(p){
        return {
          label: p.name,
          data: p.data,
          backgroundColor: p.color + 'cc',
          borderColor: p.color,
          borderWidth: 1,
          borderRadius: 2
        };
      })
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top', align: 'start', labels: { font: { size: 11 }, color: '#888', usePointStyle: true, pointStyle: 'rectRounded', boxWidth: 10, padding: 10 } }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 11 }, color: '#888' } },
        y: { grid: { color: 'rgba(128,128,128,0.1)' }, ticks: { font: { size: 11 }, color: '#888', callback: function(v){return '$'+v+'B';} }, title: { display: true, text: 'Capital raised ($B)', color: '#888', font: {size:11} } }
      }
    }
  });
})();
</script>


"""
PAGE_4_BODY = r"""
<div style="margin-bottom:14px;">
  <div style="font-size:18px;font-weight:500;">Research & papers</div>
  <div style="font-size:12px;color:var(--text-secondary);margin-top:2px;">AI research frontier — week of {{ today }} · sourced from arXiv, Semantic Scholar, and institutional preprints</div>
</div>

<!-- COMP 1: This week in AI research -->
<div class="card">
  <div class="sec-title">This week in AI research</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-top:10px;">
    <div class="mcard">
      <div class="mlabel">Papers published</div>
      <div class="mvalue">{{ research_summary.papers_published | default('—') }}</div>
      <div style="font-size:11px;{% if research_summary.papers_change and research_summary.papers_change.startswith('+') %}color:#3b6d11{% else %}color:var(--text-secondary){% endif %};">{{ research_summary.papers_change | default('') }} vs last week</div>
    </div>
    <div class="mcard">
      <div class="mlabel">Breakthrough flagged</div>
      <div class="mvalue">{{ research_summary.breakthroughs | default('—') }}</div>
      <div style="font-size:11px;color:var(--text-secondary);">{{ research_summary.breakthrough_note | default('') }}</div>
    </div>
    <div class="mcard">
      <div class="mlabel">Top institution</div>
      <div class="mvalue" style="font-size:18px;">{{ research_summary.top_institution | default('—') }}</div>
      <div style="font-size:11px;color:var(--text-secondary);">{{ research_summary.top_institution_papers | default('') }} papers this week</div>
    </div>
    <div class="mcard">
      <div class="mlabel">Hottest topic</div>
      <div class="mvalue" style="font-size:18px;">{{ research_summary.hottest_topic | default('—') }}</div>
      <div style="font-size:11px;{% if research_summary.hottest_topic_change and research_summary.hottest_topic_change.startswith('+') %}color:#3b6d11{% else %}color:var(--text-secondary){% endif %};">{{ research_summary.hottest_topic_change | default('') }} paper volume</div>
    </div>
  </div>
  <div class="disclaimer">Sources: arXiv (cs.AI, cs.LG, cs.CL, cs.CV, cs.MA) &middot; Aggregated by Claude during paper scoring &middot; Updated daily</div>
</div>

<!-- COMP 2: Paper of the week -->
{% if paper_of_week %}
<div class="card card-info">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
    <span style="font-size:10px;font-weight:500;color:#185fa5;text-transform:uppercase;letter-spacing:.06em;">Paper of the week</span>
    <span class="score-pill" style="font-size:11px;padding:3px 10px;">{{ "%.1f"|format(paper_of_week.score) }} / 10</span>
  </div>
  <a class="link-card" href="{{ paper_of_week.url }}" target="_blank" style="padding:8px 10px;margin:-8px -10px 6px;"><div style="font-size:16px;font-weight:500;line-height:1.4;"><span class="linked-title">{{ paper_of_week.title }}</span></div></a>
  <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px;">{{ paper_of_week.institution }} · {{ paper_of_week.team }} · arXiv:{{ paper_of_week.arxiv_id }} · {{ paper_of_week.date }}</div>
  <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;">
    {% for tag in paper_of_week.tags %}<span class="cat-tag">{{ tag }}</span>{% endfor %}
  </div>
  <div style="background:var(--bg-secondary);border-radius:var(--radius-md);padding:12px 14px;margin-bottom:10px;">
    <div style="font-size:10px;font-weight:500;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px;">Plain-english summary</div>
    <div style="font-size:13px;line-height:1.5;color:var(--text-primary);font-weight:500;">{{ paper_of_week.plain_summary }}</div>
  </div>
  <div style="font-size:12px;color:var(--text-primary);line-height:1.5;margin-bottom:10px;"><strong style="font-weight:500;">Why it matters:</strong> {{ paper_of_week.why_matters }}</div>
  <div class="disclaimer">Sources: arXiv &middot; Selected and summarized by Claude Sonnet &middot; Updated daily</div>
</div>
{% endif %}

<!-- COMP 3: Top papers this week -->
<div class="card">
  <div class="sec-title">Top papers this week</div>
  <div class="sec-sub">Scored by relevance, novelty, and likely real-world impact · 8.0+ threshold</div>
  <div style="margin-top:10px;">
    {% if top_papers %}
{% for p in top_papers %}
    <a class="linkrow" href="{{ p.url }}" target="_blank" style="padding:14px 8px;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:4px;">
        <div style="font-size:13px;font-weight:500;line-height:1.4;flex:1;"><span class="linked-title">{{ p.title }}</span></div>
        <span class="score-pill" style="flex-shrink:0;">{{ "%.1f"|format(p.score) }}</span>
      </div>
      <div style="font-size:11px;color:var(--text-secondary);margin-bottom:6px;">{{ p.authors }} · {{ p.institution }}</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px;">
        {% for tag in p.tags %}<span class="cat-tag">{{ tag }}</span>{% endfor %}
      </div>
      <div style="font-size:12px;color:var(--text-secondary);line-height:1.5;">{{ p.summary }}</div>
    </a>
    {% endfor %}
{% else %}
<div class="empty-state">No papers above the relevance threshold this week.</div>
{% endif %}

  </div>
  <div class="disclaimer">Sources: arXiv &middot; Scored by Claude Haiku, summarized by Sonnet &middot; Updated daily</div>
</div>

<!-- COMP 4: Research by category + 30-day volume -->
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
  <div class="card" style="margin-bottom:0;">
    <div class="sec-title">Research by category</div>
    <div class="sec-sub">Paper count this week vs last week</div>
    <div style="position:relative;height:260px;width:100%;margin-top:10px;">
      <canvas id="researchCategoryChart"></canvas>
    </div>
    <div class="disclaimer">Sources: arXiv categories &middot; Paper counts: this week vs last week &middot; Updated daily</div>
</div>
  <div class="card" style="margin-bottom:0;">
    <div class="sec-title">30-day research volume</div>
    <div class="sec-sub">Papers per category — daily rolling average</div>
    <div style="position:relative;height:260px;width:100%;margin-top:10px;">
      <canvas id="researchVolumeChart"></canvas>
    </div>
    <div class="disclaimer">Sources: arXiv categories &middot; Daily paper volume per category &middot; Backfills as daily history accumulates</div>
</div>
</div>

<!-- COMP 5: Hot institutions this week -->
<div class="card">
  <div class="sec-title">Hot institutions this week</div>
  <div class="sec-sub">Ranked by paper output × citation velocity · rising = above 4-week average</div>
  {% if hot_institutions %}
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px 24px;margin-top:12px;">
    {% for i in hot_institutions %}
    <div style="padding:8px 0;border-bottom:0.5px solid var(--border);">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:3px;">
        <div style="font-size:13px;font-weight:500;">{{ loop.index }}. {{ i.name }}</div>
        <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">
          {% if i.rising %}<span class="pill sent-pos" style="font-size:10px;">rising</span>{% endif %}
          <span style="font-size:13px;font-weight:500;">{{ i.papers }}</span>
        </div>
      </div>
      <div style="font-size:11px;color:var(--text-secondary);">{{ i.focus }}</div>
    </div>
    {% endfor %}
  </div>
  {% else %}<div class="empty-state">No hot institution concentration detected this week.</div>{% endif %}
  <div class="disclaimer">Sources: arXiv author affiliations &middot; Ranked by paper output and citation velocity &middot; Updated daily</div>
</div>

<!-- COMP 6: Author spotlight -->
<div class="card">
  <div class="sec-title">Author spotlight</div>
  <div class="sec-sub">Researchers who published notable work this week</div>
  <div style="margin-top:12px;display:flex;flex-direction:column;gap:10px;">
    {% set author_items = author_spotlight if author_spotlight else [] %}
    {% if author_items %}
    {% for a in author_items %}
    <a class="link-card" href="{{ a.url | default(a.author_url | default('#')) }}"{% if a.url or a.author_url %} target="_blank"{% endif %} style="display:flex;gap:12px;background:var(--bg-secondary);border-radius:var(--radius-md);padding:12px 14px;">
      <div class="avatar" style="background:{{ a.color | default('#7F77DD') }}33;color:{{ a.color | default('#7F77DD') }};width:36px;height:36px;font-size:12px;flex-shrink:0;">{{ a.initials }}</div>
      <div style="flex:1;min-width:0;">
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px;">
          <span style="font-size:13px;font-weight:500;">{{ a.name }}</span>
          <span style="font-size:11px;color:var(--text-secondary);">{{ a.affiliation }}</span>
          <span style="font-size:11px;color:var(--text-info);">{{ a.handle | default('') }}</span>
        </div>
        <div style="font-size:13px;font-weight:500;line-height:1.4;margin-bottom:4px;">{{ a.paper_title }}</div>
        <div style="font-size:12px;color:var(--text-secondary);line-height:1.5;font-style:italic;">{{ a.note }}</div>
      </div>
    </a>
    {% endfor %}
    {% else %}
      {% if top_papers %}
        {% for p in top_papers[:3] %}
        <a class="link-card" href="{{ p.url | default('#') }}"{% if p.url %} target="_blank"{% endif %} style="display:flex;gap:12px;background:var(--bg-secondary);border-radius:var(--radius-md);padding:12px 14px;">
          <div class="avatar" style="background:#7F77DD33;color:#7F77DD;width:36px;height:36px;font-size:12px;flex-shrink:0;">{{ (p.authors | default('AI'))[:2] }}</div>
          <div style="flex:1;min-width:0;">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px;">
              <span style="font-size:13px;font-weight:500;">{{ p.authors | default('Research team') }}</span>
              <span style="font-size:11px;color:var(--text-secondary);">{{ p.institution | default('arXiv') }}</span>
            </div>
            <div style="font-size:13px;font-weight:500;line-height:1.4;margin-bottom:4px;"><span class="linked-title">{{ p.title }}</span></div>
            <div style="font-size:12px;color:var(--text-secondary);line-height:1.5;font-style:italic;">Notable paper selected from this week's top arXiv results.</div>
          </div>
        </a>
        {% endfor %}
      {% else %}<div class="empty-state">No author spotlight generated this week.</div>{% endif %}
    {% endif %}
  </div>
  <div class="disclaimer">Sources: arXiv author tracking &middot; Synthesized by Claude Sonnet &middot; Updated daily</div>
</div>

<!-- COMP 7: Breakthrough radar -->
<div class="card">
  <div class="sec-title">Breakthrough radar</div>
  <div class="sec-sub">Papers plotted by time-to-impact vs potential significance · hover for paper details</div>
  <div style="position:relative;height:340px;width:100%;margin-top:12px;">
    <canvas id="breakthroughRadarChart"></canvas>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px;">
    <div style="background:var(--bg-secondary);border-radius:var(--radius-md);padding:12px 14px;border-left:3px solid #1D9E75;">
      <div style="font-size:11px;font-weight:500;color:#1D9E75;text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px;">Deploy Now</div>
      <div style="font-size:12px;color:var(--text-secondary);">Near-term · high impact</div>
    </div>
    <div style="background:var(--bg-secondary);border-radius:var(--radius-md);padding:12px 14px;border-left:3px solid #E24B4A;">
      <div style="font-size:11px;font-weight:500;color:#E24B4A;text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px;">Watch Closely</div>
      <div style="font-size:12px;color:var(--text-secondary);">Long-term · paradigm shift</div>
    </div>
    <div style="background:var(--bg-secondary);border-radius:var(--radius-md);padding:12px 14px;border-left:3px solid #378ADD;">
      <div style="font-size:11px;font-weight:500;color:#378ADD;text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px;">Incremental Gains</div>
      <div style="font-size:12px;color:var(--text-secondary);">Near-term · smaller scope</div>
    </div>
    <div style="background:var(--bg-secondary);border-radius:var(--radius-md);padding:12px 14px;border-left:3px solid #EF9F27;">
      <div style="font-size:11px;font-weight:500;color:#EF9F27;text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px;">Long Bet</div>
      <div style="font-size:12px;color:var(--text-secondary);">Long-term · uncertain impact</div>
    </div>
  </div>
  <div class="disclaimer">Sources: arXiv &middot; Breakthroughs flagged by Claude Sonnet at score 8.0+ &middot; Updated daily</div>
</div>

<!-- COMP 8: Research signal analysis -->
<div class="card">
  <div class="sec-title">Research signal analysis</div>
  <div class="sec-sub">What this week's paper volume and topics tell us about where the field is heading</div>
  <div style="margin-top:10px;display:flex;flex-direction:column;gap:8px;">
    {% if research_signals %}
{% for s in research_signals %}
    <div class="signal-row signal-{% if s.direction in ['up','positive'] %}up{% elif s.direction in ['down','negative'] %}down{% elif s.direction in ['warning'] %}warning{% else %}neu{% endif %}">{{ s.text }}</div>
    {% endfor %}
{% else %}
<div class="empty-state">No directional research signals this week.</div>
{% endif %}

  </div>
  <div class="disclaimer">Sources: This week's arXiv papers &middot; Synthesized by Claude Sonnet &middot; Updated daily</div>
</div>

<!-- COMP 9: Fintech & payments research corner -->
<div class="card">
  <div class="sec-title">Fintech & payments research corner</div>
  <div class="sec-sub">AI papers in fraud detection, credit scoring, AML, payment routing, and financial forecasting — with strategic implications for card networks and issuers</div>
  <div style="margin-top:10px;display:flex;flex-direction:column;gap:10px;">
    {% if fintech_research %}
{% for f in fintech_research %}
    <div style="background:var(--bg-secondary);border-radius:var(--radius-md);padding:14px 16px;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:6px;">
        {% if f.url %}<a class="linkable" href="{{ f.url }}" target="_blank" style="font-size:14px;font-weight:500;line-height:1.4;flex:1;color:var(--text-primary);text-decoration:none;">{{ f.title }}</a>{% else %}<div style="font-size:14px;font-weight:500;line-height:1.4;flex:1;">{{ f.title }}</div>{% endif %}
        <span class="score-pill" style="flex-shrink:0;">{{ "%.1f"|format(f.score) }}</span>
      </div>
      <div style="font-size:11px;color:var(--text-secondary);margin-bottom:8px;">{{ f.authors }} · arXiv:{{ f.arxiv_id }}</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;">
        {% for tag in f.tags %}<span class="cat-tag">{{ tag }}</span>{% endfor %}
      </div>
      <div style="font-size:12px;color:var(--text-primary);line-height:1.5;margin-bottom:10px;">{{ f.summary }}</div>
      <div style="font-size:10px;font-weight:500;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px;">Strategic implication</div>
      <div style="font-size:12px;color:var(--text-primary);line-height:1.5;border-top:0.5px solid var(--border);padding-top:8px;">{{ f.strategic }}</div>
    </div>
    {% endfor %}
{% else %}
<div class="empty-state">No fintech-relevant arXiv papers this week.</div>
{% endif %}

  </div>
  <div class="disclaimer">Sources: arXiv (filtered for payments, fintech, fraud topics) &middot; Strategic implications by Claude Sonnet &middot; Updated daily</div>
</div>

<script>
(function(){
  // Research by category - horizontal bar chart with this-week vs last-week
  var data = {{ research_categories | tojson }};
  if(!data || !data.labels || data.labels.length === 0) return;
  var ctx = document.getElementById('researchCategoryChart');
  if(!ctx) return;
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: [
        {label:'This week', data: data.this_week, backgroundColor:'#7F77DD', borderRadius:2},
        {label:'Last week', data: data.last_week, backgroundColor:'rgba(207,207,207,0.5)', borderRadius:2}
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false, indexAxis: 'y',
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(128,128,128,0.1)' }, ticks: { font: { size: 10 }, color: '#888' } },
        y: { grid: { display: false }, ticks: { font: { size: 11 }, color: '#888' } }
      }
    }
  });
})();
(function(){
  // 30-day research volume - line chart per category
  var data = {{ research_volume | tojson }};
  if(!data || !data.labels || data.labels.length === 0) return;
  var ctx = document.getElementById('researchVolumeChart');
  if(!ctx) return;
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.labels,
      datasets: data.categories.map(function(c){
        return {
          label: c.name,
          data: c.values,
          borderColor: c.color,
          backgroundColor: 'transparent',
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.3
        };
      })
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      layout: { padding: { top: 8, bottom: 4 } },
      plugins: {
        legend: { position: 'top', align: 'start', labels: { font: { size: 11 }, color: '#888', usePointStyle: true, pointStyle: 'line', boxWidth: 22, boxHeight: 2, padding: 12 } }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#888', maxTicksLimit: 8 } },
        y: { grid: { color: 'rgba(128,128,128,0.1)' }, ticks: { font: { size: 10 }, color: '#888' } }
      }
    }
  });
})();
(function(){
  // Breakthrough radar - bubble chart with x=time-to-impact, y=significance
  var data = {{ breakthrough_radar | tojson }};
  if(!data || data.length === 0) return;
  var ctx = document.getElementById('breakthroughRadarChart');
  if(!ctx) return;
  var quadColors = {'deploy_now':'#1D9E75','watch_closely':'#E24B4A','incremental':'#378ADD','long_bet':'#EF9F27','paradigm':'#E24B4A'};
  var datasets = data.map(function(p){
    return {
      label: p.title,
      data: [{x: p.time_to_impact, y: p.significance, r: 8 + (p.score - 7) * 4}],
      backgroundColor: (quadColors[p.quadrant] || '#888') + 'cc',
      borderColor: quadColors[p.quadrant] || '#888',
      borderWidth: 1
    };
  });
  new Chart(ctx, {
    type: 'bubble',
    data: { datasets: datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: function(c){ var p = data[c.datasetIndex]; var ttiLabel = p.time_to_impact >= 6 ? 'long-term' : (p.time_to_impact >= 4 ? 'mid-term' : 'near-term'); var sigLabel = p.significance >= 7 ? 'paradigm shift' : (p.significance >= 4 ? 'significant' : 'incremental'); return [p.title, 'Score: ' + p.score.toFixed(1) + '  ·  ' + ttiLabel + '  ·  ' + sigLabel]; } } }
      },
      scales: {
        x: { min: 0, max: 10, title: { display: true, text: 'Time to Impact   ←  Near-term      Long-term  →', color: 'rgba(255,255,255,0.7)', font: {size:12, weight: '500'} }, grid: { color: 'rgba(128,128,128,0.1)' }, ticks: { display: false } },
        y: { min: 0, max: 10, title: { display: true, text: 'Significance   ↓  Incremental      Paradigm shift  ↑', color: 'rgba(255,255,255,0.7)', font: {size:12, weight: '500'} }, grid: { color: 'rgba(128,128,128,0.1)' }, ticks: { display: false } }
      }
    }
  });
})();
</script>


"""
SHELL_TAIL = r"""

<div class="pro-foot">
  <div class="pf-line1">AI Intelligence Dashboard &middot; Updated daily &middot; Last refresh: {{ today }}</div>
  <div class="pf-line2">Sources: Hacker News &middot; arXiv &middot; GitHub Trending &middot; Yahoo Finance &middot; Web search</div>
  <div class="pf-line3">Curated and synthesized by Claude (Anthropic)</div>
  <div class="health-indicator">{% if health.status == "healthy" %}<span class="health-dot" style="background:#3b6d11;"></span>All systems healthy{% elif health.status == "degraded" %}<span class="health-dot" style="background:#e3a01a;"></span>{{ health.warnings | length }} checks degraded{% else %}<span class="health-dot" style="background:#a32d2d;"></span>Pipeline issues — see logs{% endif %}</div>
</div>

</div>

<script>
document.querySelectorAll(".tab").forEach(t => {
  t.addEventListener("click", () => {
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
    document.getElementById(t.dataset.page).classList.add("active");
    t.classList.add("active");
  });
});
</script>
</body>
</html>

"""


# ============================================================
# Page wrappers — opening + closing tags injected by shell, NOT
# by page bodies. This is the structural fix that makes page-bleed
# impossible.
# ============================================================

def _wrap_page(page_id: str, body: str, active: bool = False) -> str:
    klass = "page active" if active else "page"
    return (
        '\n<!-- ==================== PAGE ' + page_id[1:].upper()
        + ' ==================== -->\n'
        + '<div id="' + page_id + '" class="' + klass + '">\n'
        + body
        + '\n</div>\n'
    )


def _build_template_text() -> str:
    """Concatenate the shell + 4 page wrappers + shell tail.

    This is the only place where page wrappers are added. By construction,
    each page body is wrapped exactly once, so HTML structure is provably
    balanced (the structural validator double-checks this).
    """
    return (
        SHELL_HEAD
        + _wrap_page("p1", PAGE_1_BODY, active=True)
        + _wrap_page("p2", PAGE_2_BODY)
        + _wrap_page("p3", PAGE_3_BODY)
        + _wrap_page("p4", PAGE_4_BODY)
        + SHELL_TAIL
    )



def _source_label(story: Dict) -> str:
    """Return the source label used by Page 1 source components."""
    return story.get("source") or story.get("subreddit") or "Unknown"


def _build_source_hot_topics(stories: list) -> Dict[str, list]:
    """Group curated stories by source, ordered by combined/relevance score."""
    grouped: Dict[str, list] = {}
    for story in stories:
        grouped.setdefault(_source_label(story), []).append(story)
    for source, items in grouped.items():
        grouped[source] = sorted(
            items,
            key=lambda s: float(s.get("combined_score") or s.get("relevance_score") or 0),
            reverse=True,
        )
    return dict(sorted(grouped.items(), key=lambda item: -len(item[1])))


def _fallback_volume_history(stories: list, today: str) -> list:
    """Render-only fallback when main.py has not attached history yet."""
    if not stories:
        return []
    counts: Dict[str, int] = {}
    for story in stories:
        source = _source_label(story)
        counts[source] = counts.get(source, 0) + 1
    return [{"date": today, "count": len(stories), "sources": counts}]


def _fallback_sentiment_history(model_sentiments: list, today: str) -> Dict:
    """Render-only fallback for a single-day model trend chart."""
    if not model_sentiments:
        return {"labels": [], "models": []}
    return {
        "labels": [today[5:] if len(today) >= 10 else today],
        "models": [
            {
                "id": (m.get("model_config") or {}).get("id") or m.get("model_id"),
                "name": (m.get("model_config") or {}).get("name") or m.get("model_id", "Model"),
                "color": (m.get("model_config") or {}).get("color") or "#888780",
                "scores": [float(m.get("sentiment_score") or 0)],
                "github_stars": [0],
            }
            for m in model_sentiments
        ],
    }


# ============================================================
# Model trend-driver normalization (render-safe fallback)
# ============================================================

def _classify_trend_driver_direction(text: str, fallback_score: float = 0.0) -> str:
    """Classify trend-driver text into positive/negative/neutral for Page 2 icons.

    Keep this intentionally conservative. If the text does not clearly contain
    a directional signal, return neutral. Do not infer direction from the
    model's overall sentiment score, otherwise almost every row becomes
    non-neutral.
    """
    text_l = str(text or "").lower()

    negative_keywords = [
        "weakest", "poorly", "poor", "worse", "struggle", "struggles",
        "fails", "failure", "issue", "issues", "concern", "concerns",
        "criticism", "criticized", "delay", "drop", "decline", "risk",
        "problem", "controversy", "regression", "hallucination",
    ]
    positive_keywords = [
        "improved", "improvement", "growth", "increase", "adoption",
        "launch", "launched", "release", "released", "upgrade",
        "breakthrough", "outperform", "outperformed", "beat", "beats",
        "partnership", "record", "milestone",
    ]

    neg_hit = any(k in text_l for k in negative_keywords)
    pos_hit = any(k in text_l for k in positive_keywords)

    if neg_hit and not pos_hit:
        return "negative"
    if pos_hit and not neg_hit:
        return "positive"
    return "neutral"


def _normalize_model_trend_drivers(model_sentiments: list) -> list:
    """Ensure every trend driver is a dict with text, direction, and optional url."""
    out = []
    for row in model_sentiments or []:
        row2 = dict(row)
        try:
            fallback_score = float(row2.get("sentiment_score") or 0)
        except (TypeError, ValueError):
            fallback_score = 0.0

        normalized = []
        for d in row2.get("trend_drivers") or []:
            if isinstance(d, str):
                text = d.strip()
                if text:
                    normalized.append({
                        "text": text,
                        "direction": _classify_trend_driver_direction(text, fallback_score),
                    })
            elif isinstance(d, dict):
                text = str(d.get("text") or d.get("title") or "").strip()
                if not text:
                    continue
                existing = str(d.get("direction") or d.get("signal") or d.get("sentiment") or "").lower()
                if existing in {"up", "positive", "bullish"}:
                    direction = "positive"
                elif existing in {"down", "negative", "bearish"}:
                    direction = "negative"
                elif existing in {"neutral", "neu", "mixed"}:
                    direction = "neutral"
                else:
                    direction = _classify_trend_driver_direction(text, fallback_score)
                item = dict(d)
                item["text"] = text
                item["direction"] = direction
                normalized.append(item)
        row2["trend_drivers"] = normalized
        out.append(row2)
    return out

def render_dashboard(daily_data: Dict) -> str:
    """Render the dashboard HTML from a daily-data JSON payload.

    Phase 2 changes:
      - Page bodies assembled in Python (no monolithic template)
      - Structural validator runs on assembled template before Jinja
      - HTMLStructureError raised on broken structure (helpful messages)
    """
    template_text = _build_template_text()
    validate_html_structure(template_text)

    template = Template(template_text)

    stories = daily_data.get("stories", [])
    fintech_stories = [s for s in stories if s.get("is_fintech")]
    research_stories = [
        s for s in stories
        if any(
            tag in (s.get("category_tags") or [])
            for tag in ["Research/Paper", "Open Source", "Benchmark/Evaluation"]
        )
    ]

    stories_by_subreddit = {}
    for s in stories:
        sub = s.get("subreddit") or s.get("source") or "unknown"
        stories_by_subreddit.setdefault(sub, []).append(s)
    stories_by_subreddit = dict(
        sorted(stories_by_subreddit.items(), key=lambda x: -len(x[1]))
    )

    today_str = daily_data.get("_date", date.today().isoformat())
    volume_history = daily_data.get("volume_history") or _fallback_volume_history(stories, today_str)
    sentiment_history = daily_data.get("sentiment_history") or _fallback_sentiment_history(
        daily_data.get("model_sentiments", []), today_str
    )

    return template.render(
        volume_history=volume_history,
        today=today_str,
        launch_date=getattr(config, "DASHBOARD_LAUNCH_DATE", "2026-05-01"),
        top_story=stories[0] if stories else None,
        top_stories=stories,
        fintech_stories=fintech_stories,
        research_stories=research_stories,
        synthesis=daily_data.get("synthesis", {}),
        metrics=daily_data.get("metrics", {}),
        model_sentiments=_normalize_model_trend_drivers(daily_data.get("model_sentiments", [])),
        etfs=daily_data.get("etfs", []),
        public_ai=daily_data.get("public_ai", []),
        category_breakdown=daily_data.get("category_breakdown", {}),
        sentiment_history=sentiment_history,
        stories_by_subreddit=stories_by_subreddit,
        source_hot_topics=daily_data.get("source_hot_topics") or _build_source_hot_topics(stories),
        funding_summary=daily_data.get("funding_summary", {}),
        funding_rounds=daily_data.get("funding_rounds", []),
        private_ai=daily_data.get("private_ai", []),
        arms_race=daily_data.get("arms_race", {}),
        vc_league=daily_data.get("vc_league", []),
        money_flow=daily_data.get("money_flow", []),
        ma_tracker=daily_data.get("ma_tracker", []),
        fintech_spotlight=daily_data.get("fintech_spotlight", []),
        research_summary=daily_data.get("research_summary", {}),
        paper_of_week=daily_data.get("paper_of_week", None),
        top_papers=daily_data.get("top_papers", []),
        research_categories=daily_data.get("research_categories", {}),
        research_volume=daily_data.get("research_volume", {}),
        hot_institutions=daily_data.get("hot_institutions", []),
        author_spotlight=daily_data.get("author_spotlight", []),
        breakthrough_radar=daily_data.get("breakthrough_radar", []),
        research_signals=daily_data.get("research_signals", []),
        fintech_research=daily_data.get("fintech_research", []),
        health=daily_data.get("health", {"status": "degraded", "warnings": ["health missing"]}),
    )


def render_index_redirect() -> str:
    """Generate index.html — a tiny meta-refresh redirect to latest.html.

    PLAN sec.3, sec.11.13: bare GitHub Pages URL should land on the dashboard.
    """
    return (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        '<meta http-equiv="refresh" content="0; url=latest.html">\n'
        '<title>AI Intelligence Dashboard</title>\n'
        '<link rel="canonical" href="latest.html">\n'
        '</head>\n'
        '<body>\n'
        '<p>Redirecting to <a href="latest.html">latest dashboard</a>&hellip;</p>\n'
        '<script>window.location.replace("latest.html");</script>\n'
        '</body>\n'
        '</html>\n'
    )
