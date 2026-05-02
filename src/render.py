"""
HTML dashboard renderer.
Takes the structured daily JSON and produces the 4-page interactive dashboard
matching the design spec we agreed on in chat.
"""

import json
from datetime import date
from pathlib import Path
from typing import Dict
from jinja2 import Template

import config


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Intelligence Dashboard — {{ today }}</title>
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
  .linkrow{display:block;text-decoration:none;color:inherit;padding:10px 0;border-bottom:0.5px solid var(--border);transition:background 0.15s;}
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
</style>
</head>
<body>
<div class="container">

<div class="head">
  <div>
    <div class="h-title">AI intelligence dashboard</div>
    <div class="h-sub">Daily digest from 24 subreddits and the open web — {{ today }}</div>
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

<!-- ==================== PAGE 1: AI INTELLIGENCE ==================== -->
<div id="p1" class="page active">

{% if top_story %}
<div class="card card-info">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
    <span style="font-size:10px;font-weight:500;color:#185fa5;text-transform:uppercase;letter-spacing:.06em;">Top story today</span>
    <span class="score-pill" style="font-size:11px;padding:3px 10px;">{{ "%.1f"|format(top_story.relevance_score) }}</span>
  </div>
  <a href="{{ top_story.url }}" target="_blank" style="text-decoration:none;color:inherit;">
    <div style="font-size:16px;font-weight:500;line-height:1.4;margin-bottom:6px;">{{ top_story.title }}</div>
  </a>
  <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px;">{{ top_story.subreddit }} · {{ top_story.score }} upvotes · {{ top_story.num_comments }} comments</div>
  <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;">
    {% for tag in top_story.category_tags %}<span class="cat-tag">{{ tag }}</span>{% endfor %}
  </div>
  {% if synthesis.top_story and synthesis.top_story.why_top %}
  <div style="font-size:12px;line-height:1.5;color:var(--text-primary);">{{ synthesis.top_story.why_top }}</div>
  {% endif %}
</div>
{% endif %}

<div class="card">
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;">
    <div class="mcard"><div class="mlabel">Stories today</div><div class="mvalue">{{ metrics.total_stories }}</div><div style="font-size:11px;color:var(--text-secondary);">Pulled {{ metrics.posts_pulled }} · curated {{ metrics.total_stories }}</div></div>
    <div class="mcard"><div class="mlabel">Top subreddit</div><div class="mvalue" style="font-size:15px;">{{ synthesis.metrics.top_subreddit }}</div><div class="neu" style="font-size:11px;">{{ metrics.top_subreddit_count }} stories</div></div>
    <div class="mcard"><div class="mlabel">Most active category</div><div class="mvalue" style="font-size:15px;">{{ synthesis.metrics.most_active_category }}</div><div class="neu" style="font-size:11px;">{{ metrics.top_category_count }} stories</div></div>
    <div class="mcard"><div class="mlabel">Trending model</div><div class="mvalue" style="font-size:15px;">{{ synthesis.metrics.trending_model or "—" }}</div><div class="up" style="font-size:11px;">{{ synthesis.metrics.trending_model_buzz_change or "" }}</div></div>
  </div>
    <div class="sec-title">Story volume — last 30 days</div>
  <div style="font-size:11px;color:var(--text-secondary);margin-top:2px;margin-bottom:12px;">Daily story count vs 7-day rolling average</div>
  <div style="position:relative;height:160px;width:100%">
    <canvas id="volumeChart"></canvas>
  </div>
  {% if synthesis.pattern_insights %}
  <div style="margin-top:14px;padding-top:4px;display:flex;flex-wrap:wrap;gap:8px;">
    {% for ins in synthesis.pattern_insights %}
    <span class="pattern-tag pat-{{ ins.direction if ins.direction in ['up','down','neu','warn'] else 'neu' }}">
      {% if ins.direction == 'up' %}▲{% elif ins.direction == 'down' %}▼{% elif ins.direction == 'warning' or ins.direction == 'warn' %}⚠{% else %}●{% endif %}
      {{ ins.text }}
    </span>
    {% endfor %}
  </div>
  {% endif %}
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>
(function(){
  var history = {{ volume_history | tojson }};
  if(!history || history.length === 0) return;
  var labels = history.map(function(d){ return d.date.slice(5); });
  var counts = history.map(function(d){ return d.count; });
  var rolling = counts.map(function(v,i){
    var slice = counts.slice(Math.max(0,i-6),i+1);
    return Math.round(slice.reduce(function(a,b){return a+b;},0)/slice.length);
  });
  var ctx = document.getElementById('volumeChart');
  if(!ctx) return;
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Stories',
          data: counts,
          backgroundColor: 'rgba(127,119,221,0.7)',
          borderRadius: 3,
          order: 2
        },
        {
          label: '7-day avg',
          data: rolling,
          type: 'line',
          borderColor: '#EF9F27',
          borderWidth: 2,
          pointRadius: 0,
          fill: false,
          order: 1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#888', maxTicksLimit: 10 } },
        y: { grid: { color: 'rgba(128,128,128,0.1)' }, ticks: { font: { size: 10 }, color: '#888' }, beginAtZero: true }
      }
    }
  });
})();
</script>

<div class="card">
  <div class="sec-title">Top stories</div>
  {% for s in top_stories[:10] %}
  <a class="linkrow" href="{{ s.url }}" target="_blank">
    <div class="story-title">{{ s.title }}</div>
    <div class="story-meta">
      <span>{{ s.subreddit }}</span>
      {% for tag in s.category_tags %}<span class="cat-tag">{{ tag }}</span>{% endfor %}
      <span class="score-pill">{{ "%.1f"|format(s.relevance_score) }}</span>
    </div>
  </a>
  {% endfor %}
</div>

<div class="card" style="padding:0">
  <div style="display:grid;grid-template-columns:1fr 1fr;min-height:220px">
    <div style="padding:16px 18px;border-right:0.5px solid var(--border)">
      <div class="sec-title">Category breakdown</div>
      <div style="display:flex;flex-direction:column;align-items:center;gap:14px;margin-top:14px;position:relative">
        <canvas id="catDonut" width="160" height="160" style="flex-shrink:0;width:160px;height:160px"></canvas>
<div id="donutTooltip" style="display:none;position:absolute;background:var(--bg-secondary);border:0.5px solid var(--border);border-radius:var(--radius-md);padding:6px 10px;font-size:12px;color:var(--text-primary);pointer-events:none;z-index:10"></div>
        <div id="catLegend" style="display:flex;flex-wrap:wrap;justify-content:center;gap:6px 14px;font-size:12px;max-width:100%"></div>
      </div>
    </div>
    <div style="padding:16px 18px">
      <div class="sec-title">Trending topics</div>
      <div class="wc-cloud">
      {% set sorted_topics = synthesis.trending_topics | sort(attribute='weight', reverse=true) %}
      {% for term in sorted_topics %}
        {% set w = term.weight | int %}
        {% if w >= 9 %}{% set tier = 'xl' %}{% set op = '1' %}
        {% elif w >= 7 %}{% set tier = 'lg' %}{% set op = '0.95' %}
        {% elif w >= 5 %}{% set tier = 'md' %}{% set op = '0.85' %}
        {% elif w >= 3 %}{% set tier = 'sm' %}{% set op = '0.7' %}
        {% else %}{% set tier = 'xs' %}{% set op = '0.55' %}{% endif %}
        <span class="wc-word wc-tier-{{ tier }} wc-{{ term.category | default('other') | lower | replace('/', '_') | replace(' ', '_') }}" style="--wc-opacity:{{ op }};animation-delay:{{ loop.index0 * 0.06 }}s;">{{ term.term }}</span>
      {% endfor %}
      </div>
    </div>
  </div>
</div>
<script>
(function(){
  var breakdown = {{ category_breakdown | tojson }};
  var colors = {"Model release":"#378ADD","Model_release":"#378ADD","Research/paper":"#7F77DD","Research_paper":"#7F77DD","Funding":"#1D9E75","Regulation":"#EF9F27","Open source":"#E24B4A","Open_source":"#E24B4A","Other":"#888780"};
  var defaultColors = ["#378ADD","#7F77DD","#1D9E75","#EF9F27","#E24B4A","#D4537E","#888780"];
  var labels = Object.keys(breakdown);
  var values = labels.map(function(k){return breakdown[k];});
  var bgColors = labels.map(function(k,i){return colors[k]||defaultColors[i%defaultColors.length];});
  var canvas = document.getElementById("catDonut");
  if(!canvas) return;
  var ctx = canvas.getContext("2d");
  var total = values.reduce(function(a,b){return a+b;},0);
  if(total===0) return;
  var startAngle = -Math.PI/2;
  var cx=80,cy=80,outerR=75,innerR=45;
  values.forEach(function(v,i){
    var slice = (v/total)*2*Math.PI;
    ctx.beginPath();
    ctx.moveTo(cx,cy);
    ctx.arc(cx,cy,outerR,startAngle,startAngle+slice);
    ctx.closePath();
    ctx.fillStyle=bgColors[i];
    ctx.fill();
    startAngle+=slice;
  });
  ctx.beginPath();
  ctx.arc(cx,cy,innerR,0,2*Math.PI);
  ctx.fillStyle=getComputedStyle(document.body).getPropertyValue('--bg-primary')||'#1a1a2e';
  ctx.fill();
  var legend = document.getElementById("catLegend");
  labels.forEach(function(k,i){
    var row = document.createElement("div");
    row.style.cssText="display:flex;align-items:center;gap:5px";
    var dot = document.createElement("span");
    dot.style.cssText="width:8px;height:8px;border-radius:50%;flex-shrink:0;background:"+bgColors[i];
    var txt = document.createElement("span");
    txt.style.color="var(--text-secondary)";
    txt.textContent=k+" ("+values[i]+")";
    row.appendChild(dot);row.appendChild(txt);
    legend.appendChild(row);
  });
  canvas.addEventListener('mousemove', function(e){
    var rect = canvas.getBoundingClientRect();
    var x = e.clientX - rect.left - cx;
    var y = e.clientY - rect.top - cy;
    var dist = Math.sqrt(x*x+y*y);
    var tip = document.getElementById('donutTooltip');
    if(dist > innerR && dist < outerR){
      var angle = Math.atan2(y,x) + Math.PI/2;
      var norm = ((angle % (2*Math.PI)) + 2*Math.PI) % (2*Math.PI);
      var cumulative = 0;
      for(var i=0;i<values.length;i++){
        cumulative += (values[i]/total)*2*Math.PI;
        if(norm < cumulative){
          var pct = Math.round(values[i]/total*100);
          tip.innerHTML = '<strong>'+labels[i]+'</strong><br>'+values[i]+' stories · '+pct+'%';
          tip.style.display='block';
          tip.style.left=(e.offsetX+10)+'px';
          tip.style.top=(e.offsetY-10)+'px';
          break;
        }
      }
    } else {
      tip.style.display='none';
    }
  });
})();
</script>


<div class="card">
  <div class="sec-title">Subreddit hot topics this week</div>
  <select id="subSelect" onchange="filterSub(this.value)" style="width:100%;margin:10px 0 14px;">
    {% for sub, sub_stories in stories_by_subreddit.items() %}
    <option value="{{ sub }}">{{ sub }} · {{ sub_stories | length }} stories</option>
    {% endfor %}
  </select>
  <div id="subStories">
    {% for sub, sub_stories in stories_by_subreddit.items() %}
    <div class="sub-group" data-sub="{{ sub }}"{% if not loop.first %} style="display:none"{% endif %}>
      {% for s in sub_stories[:5] %}
      <a class="linkrow" href="{{ s.url }}" target="_blank">
        <div class="story-title">{{ s.title }}</div>
        <div class="story-meta">
          {% for tag in s.category_tags %}<span class="cat-tag">{{ tag }}</span>{% endfor %}
        </div>
      </a>
      {% endfor %}
    </div>
    {% endfor %}
  </div>
</div>
<script>
function filterSub(val){
  document.querySelectorAll('.sub-group').forEach(function(g){
    g.style.display = g.dataset.sub === val ? '' : 'none';
  });
}
</script>
{% if fintech_stories %}
<div class="card">
  <div class="sec-title">Fintech & payments spotlight</div>
  {% for s in fintech_stories[:3] %}
  <a class="linkrow" href="{{ s.url }}" target="_blank" style="background:var(--bg-secondary);border-radius:var(--radius-md);padding:11px 13px;margin-bottom:8px;border-bottom:none;">
    <div class="story-title">{{ s.title }}</div>
    <div class="story-meta"><span>{{ s.subreddit }}</span><span class="score-pill">{{ "%.1f"|format(s.relevance_score) }}</span></div>
  </a>
  {% endfor %}
  {% if synthesis.fintech_implications %}
  <div style="margin-top:10px;font-size:12px;color:var(--text-primary);line-height:1.5;border-top:0.5px solid var(--border);padding-top:10px;">
    <strong style="font-weight:500;">Strategic read:</strong> {{ synthesis.fintech_implications }}
  </div>
  {% endif %}
</div>
{% endif %}
</div>


<!-- ==================== PAGE 2: MODEL TRACKER ==================== -->
<div id="p2" class="page">

<div class="card">
  <div class="sec-title">All models — snapshot</div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;">
    {% for m in model_sentiments %}
    <div style="background:var(--bg-primary);border:0.5px solid var(--border);border-radius:var(--radius-lg);padding:14px 16px;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;">
        <div>
          <div style="font-size:14px;font-weight:500;">{{ m.model_config.name }}</div>
          <div style="font-size:11px;color:var(--text-secondary);">{{ m.model_config.maker }}</div>
        </div>
        <span class="pill {{ 'sent-pos' if m.sentiment_label == 'positive' else 'sent-neu' }}">{{ "%.1f"|format(m.sentiment_score) }}</span>
      </div>
      <div style="height:3px;background:var(--bg-secondary);border-radius:2px;margin:8px 0 6px;"><div style="height:3px;border-radius:2px;background:{{ m.model_config.color }};width:{{ m.buzz_volume }}%;"></div></div>
      <div style="display:flex;gap:10px;flex-wrap:wrap;">
        <span style="font-size:11px;color:var(--text-secondary);">Stories <span style="color:var(--text-primary);font-weight:500;">{{ m.story_count }}</span></span>
        <span style="font-size:11px;color:var(--text-secondary);">Buzz <span style="color:var(--text-primary);font-weight:500;">{{ m.buzz_volume }}%</span></span>
        <span style="font-size:11px;font-weight:500;{% if m.wow_delta_pct.startswith('+') %}color:#3b6d11{% else %}color:#a32d2d{% endif %};">{{ m.wow_delta_pct }} WoW</span>
      </div>
    </div>
    {% endfor %}
  </div>
</div>

<div class="card">
  <div class="sec-title">Sentiment trends — last 30 days</div>
  <div class="sec-sub">Daily Reddit sentiment score across 24 subreddits</div>
  <div style="position:relative;height:240px;width:100%;margin-top:8px">
    <canvas id="sentimentChart"></canvas>
  </div>
</div>
<script>
(function(){
  var history = {{ sentiment_history | tojson }};
  if(!history || !history.labels || history.labels.length === 0) return;
  var ctx = document.getElementById('sentimentChart');
  if(!ctx) return;
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: history.labels,
      datasets: history.models.map(function(m){
        return {
          label: m.name,
          data: m.scores,
          borderColor: m.color,
          backgroundColor: 'transparent',
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.3
        };
      })
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      layout: { padding: { top: 8, bottom: 4 } },
      plugins: {
        legend: { position: 'top', align: 'start', labels: { font: { size: 12 }, color: '#888', usePointStyle: true, pointStyle: 'line', boxWidth: 28, boxHeight: 2, padding: 16 } }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#888', maxTicksLimit: 8 } },
        y: { grid: { color: 'rgba(128,128,128,0.1)' }, ticks: { font: { size: 10 }, color: '#888', stepSize: 0.5 }, min: 4, max: 9 }
      }
    }
  });
})();
</script>

<div class="card">
  <div class="sec-title">What's driving each model's trend</div>
  <div class="sec-sub">Signal analysis from Reddit volume, benchmark events, and news triggers</div>
  {% for m in model_sentiments %}
  <div style="padding:12px 0;{% if not loop.last %}border-bottom:0.5px solid var(--border);{% endif %}">
    <div style="font-size:13px;font-weight:500;color:{{ m.model_config.color }};margin-bottom:6px;">
      {{ m.model_config.name }} <span style="font-size:11px;font-weight:400;color:var(--text-secondary);">{{ "%.1f"|format(m.sentiment_score) }}/10 · {{ m.wow_delta_pct }} WoW</span>
    </div>
    {% for d in m.trend_drivers %}
    <div class="ins-row ins-{{ d.direction }}" style="padding:3px 0;">{{ d.text }}</div>
    {% endfor %}
  </div>
  {% endfor %}
</div>


<div class="card">
  <div class="sec-title">Model deep dive</div>
  <div class="sec-sub">Strengths, weaknesses, Reddit mention analysis, recent changes, key people</div>
  <select id="modelSelect" onchange="filterModel(this.value)" style="width:100%;margin:6px 0 14px;">
    {% for m in model_sentiments %}
    <option value="{{ m.model_config.name }}">{{ m.model_config.name }} ({{ m.model_config.maker }})</option>
    {% endfor %}
  </select>

  {% for m in model_sentiments %}
  {% set dd = m.deep or {} %}
  <div class="model-deep" data-model="{{ m.model_config.name }}"{% if not loop.first %} style="display:none"{% endif %}>

    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px;">
      <div class="mcard">
        <div class="mlabel">Sentiment</div>
        <div class="mvalue" style="color:{{ m.model_config.color }};">{{ "%.1f"|format(m.sentiment_score) }}</div>
        <div style="font-size:10px;color:var(--text-secondary);">out of 10</div>
      </div>
      <div class="mcard">
        <div class="mlabel">MAU</div>
        <div class="mvalue" style="font-size:18px;">{{ dd.mau | default('—') }}</div>
        <div style="font-size:10px;color:var(--text-secondary);">estimated</div>
      </div>
      <div class="mcard">
        <div class="mlabel">Market share</div>
        <div class="mvalue" style="font-size:18px;">{{ dd.market_share | default('—') }}</div>
        <div style="font-size:10px;{% if dd.market_share_change and dd.market_share_change.startswith('+') %}color:#3b6d11{% else %}color:var(--text-secondary){% endif %};">{{ dd.market_share_change | default('') }} WoW</div>
      </div>
      <div class="mcard">
        <div class="mlabel">Buzz volume</div>
        <div class="mvalue" style="font-size:18px;">{{ m.buzz_volume }}%</div>
        <div style="font-size:10px;color:var(--text-secondary);">of peak</div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;">
      <div class="stat-card">
        <div style="font-size:11px;font-weight:500;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px;">Strengths</div>
        {% for s in (dd.strengths or []) %}
        <div class="cap-item"><div class="dot-g"></div><div>{{ s }}</div></div>
        {% endfor %}
      </div>
      <div class="stat-card">
        <div style="font-size:11px;font-weight:500;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px;">Weaknesses</div>
        {% for w in (dd.weaknesses or []) %}
        <div class="cap-item"><div class="dot-r"></div><div>{{ w }}</div></div>
        {% endfor %}
      </div>
    </div>

    {% if dd.mention_chart %}
    <div style="margin-bottom:14px;">
      <div class="sec-title">Reddit mention sentiment — strengths vs weaknesses</div>
      <div class="sec-sub">Positive / negative Reddit mentions — current 30 days vs prior 30 days</div>
      <div style="position:relative;height:280px;width:100%;margin-top:8px;">
        <canvas id="mentionChart-{{ loop.index }}"></canvas>
      </div>
      <div style="font-size:10px;color:var(--text-tertiary);text-align:center;margin-top:4px;">← negative mentions  |  positive mentions →</div>
    </div>
    {% endif %}

    {% if dd.recent_changes %}
    <div style="margin-bottom:14px;">
      <div class="sec-title">Recent changes</div>
      {% for c in dd.recent_changes %}
      <div style="display:flex;gap:10px;padding:6px 0;border-bottom:0.5px solid var(--border);font-size:12px;">
        <div style="width:48px;color:var(--text-secondary);flex-shrink:0;">{{ c.date }}</div>
        <div style="color:var(--text-info);">{{ c.text }}</div>
      </div>
      {% endfor %}
    </div>
    {% endif %}

    {% if dd.key_people %}
    <div>
      <div class="sec-title">Key people — latest activity</div>
      {% for p in dd.key_people %}
      <div class="person-chip">
        <div class="avatar" style="background:{{ m.model_config.color }}33;color:{{ m.model_config.color }};">{{ p.initials }}</div>
        <div style="flex:1;min-width:0;">
          <div style="font-size:13px;font-weight:500;">{{ p.name }} <span style="color:var(--text-secondary);font-weight:400;font-size:11px;">{{ p.handle }}</span></div>
          <div class="quote-text">{{ p.quote }}</div>
          <div class="quote-meta">{{ p.date }} · {{ p.platform | default('X') }}</div>
        </div>
      </div>
      {% endfor %}
    </div>
    {% endif %}

  </div>
  {% endfor %}
</div>
<script>
function filterModel(val){
  document.querySelectorAll('.model-deep').forEach(function(g){
    g.style.display = g.dataset.model === val ? '' : 'none';
  });
}
{% for m in model_sentiments %}
{% set dd = m.deep or {} %}
{% if dd.mention_chart %}
(function(){
  var ctx = document.getElementById('mentionChart-{{ loop.index }}');
  if(!ctx) return;
  var data = {{ dd.mention_chart | tojson }};
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: [
        {label:'Positive (current)', data: data.pos_current, backgroundColor:'#3b6d11', borderRadius:2},
        {label:'Positive (prior 30d)', data: data.pos_prior, backgroundColor:'rgba(99,153,34,0.55)', borderRadius:2},
        {label:'Negative (current)', data: data.neg_current.map(function(v){return -Math.abs(v);}), backgroundColor:'#a32d2d', borderRadius:2},
        {label:'Negative (prior 30d)', data: data.neg_prior.map(function(v){return -Math.abs(v);}), backgroundColor:'rgba(226,75,74,0.55)', borderRadius:2}
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false, indexAxis: 'y',
      plugins: {
        legend: { position: 'top', align: 'start', labels: { font:{size:11}, color:'#888', usePointStyle: true, pointStyle: 'rectRounded', boxWidth: 10, padding: 12 } }
      },
      scales: {
        x: { stacked: false, grid: { color: 'rgba(128,128,128,0.1)' }, ticks: { font: { size: 10 }, color: '#888', callback: function(v){return Math.abs(v);} } },
        y: { stacked: false, grid: { display: false }, ticks: { font: { size: 11 }, color: '#888' } }
      }
    }
  });
})();
{% endif %}
{% endfor %}
</script>

</div>

<!-- ==================== PAGE 3: AI FINANCE ==================== -->
<div id="p3" class="page">

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
      <div class="mvalue">${{ funding_summary.total_raised | default('—') }}</div>
      <div style="font-size:11px;{% if funding_summary.total_raised_change and funding_summary.total_raised_change.startswith('+') %}color:#3b6d11{% else %}color:var(--text-secondary){% endif %};">{{ funding_summary.total_raised_change | default('') }} vs last week</div>
    </div>
    <div class="mcard">
      <div class="mlabel">Deals closed</div>
      <div class="mvalue">{{ funding_summary.deals_closed | default('—') }}</div>
      <div style="font-size:11px;{% if funding_summary.deals_change and funding_summary.deals_change.startswith('+') %}color:#3b6d11{% else %}color:var(--text-secondary){% endif %};">{{ funding_summary.deals_change | default('') }} vs last week</div>
    </div>
    <div class="mcard">
      <div class="mlabel">Largest round</div>
      <div class="mvalue">${{ funding_summary.largest_round | default('—') }}</div>
      <div style="font-size:11px;color:var(--text-secondary);">{{ funding_summary.largest_round_company | default('') }}</div>
    </div>
    <div class="mcard">
      <div class="mlabel">Median pre-money</div>
      <div class="mvalue">${{ funding_summary.median_premoney | default('—') }}</div>
      <div style="font-size:11px;{% if funding_summary.median_trend == 'up' %}color:#3b6d11{% elif funding_summary.median_trend == 'down' %}color:#a32d2d{% else %}color:var(--text-secondary){% endif %};">{% if funding_summary.median_trend == 'up' %}Trending up{% elif funding_summary.median_trend == 'down' %}Trending down{% else %}Stable{% endif %}</div>
    </div>
  </div>
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
    <a href="https://finance.yahoo.com/quote/{{ e.ticker }}" target="_blank" style="font-size:13px;font-weight:500;color:var(--text-info);width:52px;text-decoration:none;">{{ e.ticker }}</a>
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
</div>

<!-- COMP 3: Recent funding rounds -->
<div class="card">
  <div class="sec-title">Recent funding rounds</div>
  <div class="sec-sub">Sorted by round size — this week</div>
  <div style="display:flex;gap:0;padding:0 0 6px;border-bottom:0.5px solid var(--border-strong);margin-bottom:2px;margin-top:8px;">
    <div class="col-hdr" style="flex:2;">Company</div>
    <div class="col-hdr" style="width:80px;text-align:right;">Amount</div>
    <div class="col-hdr" style="width:80px;text-align:right;">Valuation</div>
    <div class="col-hdr" style="width:80px;text-align:center;">Stage</div>
    <div class="col-hdr" style="width:120px;text-align:right;">Lead investor</div>
  </div>
  {% for r in funding_rounds %}
  <div style="display:flex;align-items:flex-start;gap:0;padding:10px 0;border-bottom:0.5px solid var(--border);">
    <div style="flex:2;min-width:0;">
      <div style="font-size:13px;font-weight:500;">{{ r.company }} <span style="font-size:10px;color:var(--text-tertiary);font-weight:400;">{{ r.country | default('') }}</span></div>
      <div style="font-size:11px;color:var(--text-secondary);">{{ r.category | default('') }}</div>
    </div>
    <div style="width:80px;text-align:right;font-size:13px;font-weight:500;">${{ r.amount }}</div>
    <div style="width:80px;text-align:right;font-size:13px;font-weight:500;">${{ r.valuation }}</div>
    <div style="width:80px;text-align:center;"><span class="pill" style="background:#e6f1fb;color:#0c447c;">{{ r.stage }}</span></div>
    <div style="width:120px;text-align:right;font-size:12px;color:var(--text-secondary);">{{ r.lead_investor }}</div>
  </div>
  {% endfor %}
</div>

<!-- COMP 4: Private + Public AI valuation leaderboards -->
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
  <div class="card" style="margin-bottom:0;">
    <div class="sec-title">Private AI — top 10 by valuation</div>
    <div class="sec-sub">Estimated valuations · last known round</div>
    {% set max_priv = (private_ai[0].valuation_billions | default(1)) if private_ai else 1 %}
    {% for p in private_ai %}
    <div style="padding:8px 0;border-bottom:0.5px solid var(--border);">
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:3px;">
        <div style="font-size:12px;font-weight:{% if loop.index <= 3 %}500{% else %}400{% endif %};">{{ loop.index }}. {{ p.name }}</div>
        <div style="font-size:12px;font-weight:500;color:#7F77DD;">${{ p.valuation_billions }}B</div>
      </div>
      <div style="font-size:10px;color:var(--text-tertiary);margin-bottom:4px;">${{ p.last_round | default('—') }} · {{ p.last_round_date | default('—') }}</div>
      <div style="height:3px;background:var(--bg-secondary);border-radius:2px;"><div style="height:3px;border-radius:2px;background:#7F77DD;width:{{ ((p.valuation_billions / max_priv) * 100) | round | int }}%;"></div></div>
    </div>
    {% endfor %}
  </div>
  <div class="card" style="margin-bottom:0;">
    <div class="sec-title">Public AI — top 10 by market cap</div>
    <div class="sec-sub">Market cap in $B · {{ today }} close</div>
    {% if public_ai %}
    {% set max_cap = public_ai[0].market_cap_billions %}
    {% for p in public_ai %}
    <a href="https://finance.yahoo.com/quote/{{ p.ticker }}" target="_blank" style="display:block;text-decoration:none;color:inherit;padding:7px 0;border-bottom:0.5px solid var(--border);">
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
</div>

<!-- COMP 6: VC league table -->
<div class="card">
  <div class="sec-title">VC league table — top AI investors this quarter</div>
  <div class="sec-sub">Ranked by deals closed · Q1 2026</div>
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
    <div style="width:80px;text-align:right;font-size:13px;font-weight:500;">${{ v.deployed }}</div>
    <div style="width:160px;text-align:right;font-size:11px;color:var(--text-secondary);">{{ v.focus }}</div>
  </div>
  {% endfor %}
</div>

<!-- COMP 7: Money flow analysis -->
<div class="card">
  <div class="sec-title">Money flow analysis</div>
  <div class="sec-sub">Signal-driven directional insights from this week's capital movements</div>
  <div style="margin-top:10px;display:flex;flex-direction:column;gap:8px;">
    {% for f in money_flow %}
    <div class="signal-row signal-{{ f.direction }}">{{ f.text }}</div>
    {% endfor %}
  </div>
</div>

<!-- COMP 8: M&A & exits tracker -->
<div class="card">
  <div class="sec-title">M&A & exits tracker</div>
  <div class="sec-sub">Acquisitions, strategic investments, IPO filings, acqui-hires</div>
  <div style="margin-top:10px;">
    {% for m in ma_tracker %}
    <div style="display:flex;gap:14px;padding:10px 0;border-bottom:0.5px solid var(--border);">
      <div style="width:48px;color:var(--text-secondary);font-size:11px;flex-shrink:0;padding-top:2px;">{{ m.date }}</div>
      <div style="flex:1;min-width:0;">
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
          <span style="font-size:13px;font-weight:500;">{{ m.title }}</span>
          <span class="pill" style="background:{% if m.type == 'Acquisition' %}#eaf3de;color:#3b6d11{% elif m.type == 'IPO filing' %}#e6f1fb;color:#0c447c{% elif m.type == 'Investment' %}#eeedfe;color:#3c3489{% else %}#f1efe8;color:#5f5e5a{% endif %};">{{ m.type }}</span>
        </div>
        <div style="font-size:11px;color:var(--text-secondary);margin-top:3px;">{{ m.detail }}</div>
      </div>
    </div>
    {% endfor %}
  </div>
</div>

<!-- COMP 9: Fintech & payments AI spotlight -->
<div class="card">
  <div class="sec-title">Fintech & payments AI spotlight</div>
  <div class="sec-sub">AI deals in payments, lending, fraud, embedded finance, and banking infrastructure — with strategic implications for card networks and issuers</div>
  <div style="margin-top:10px;display:flex;flex-direction:column;gap:10px;">
    {% for f in fintech_spotlight %}
    <div style="background:var(--bg-secondary);border-radius:var(--radius-md);padding:14px 16px;">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px;">
        <span style="font-size:14px;font-weight:500;">{{ f.company }}</span>
        <span style="font-size:11px;color:var(--text-info);">{{ f.deal_type }}</span>
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;">
        {% for tag in f.tags %}<span class="cat-tag">{{ tag }}</span>{% endfor %}
      </div>
      <div style="font-size:12px;color:var(--text-primary);line-height:1.5;margin-bottom:10px;">{{ f.description }}</div>
      <div style="font-size:10px;font-weight:500;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px;">Strategic implication</div>
      <div style="font-size:12px;color:var(--text-primary);line-height:1.5;border-top:0.5px solid var(--border);padding-top:8px;">{{ f.strategic }}</div>
    </div>
    {% endfor %}
  </div>
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

</div>

<!-- ==================== PAGE 4: RESEARCH & PAPERS ==================== -->
<div id="p4" class="page">

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
</div>

<!-- COMP 2: Paper of the week -->
{% if paper_of_week %}
<div class="card card-info">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
    <span style="font-size:10px;font-weight:500;color:#185fa5;text-transform:uppercase;letter-spacing:.06em;">Paper of the week</span>
    <span class="score-pill" style="font-size:11px;padding:3px 10px;">{{ "%.1f"|format(paper_of_week.score) }} / 10</span>
  </div>
  <div style="font-size:16px;font-weight:500;line-height:1.4;margin-bottom:6px;">{{ paper_of_week.title }}</div>
  <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px;">{{ paper_of_week.institution }} · {{ paper_of_week.team }} · arXiv:{{ paper_of_week.arxiv_id }} · {{ paper_of_week.date }}</div>
  <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;">
    {% for tag in paper_of_week.tags %}<span class="cat-tag">{{ tag }}</span>{% endfor %}
  </div>
  <div style="background:var(--bg-secondary);border-radius:var(--radius-md);padding:12px 14px;margin-bottom:10px;">
    <div style="font-size:10px;font-weight:500;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px;">Plain-english summary</div>
    <div style="font-size:13px;line-height:1.5;color:var(--text-primary);font-weight:500;">{{ paper_of_week.plain_summary }}</div>
  </div>
  <div style="font-size:12px;color:var(--text-primary);line-height:1.5;margin-bottom:10px;"><strong style="font-weight:500;">Why it matters:</strong> {{ paper_of_week.why_matters }}</div>
  <a href="{{ paper_of_week.url }}" target="_blank" style="font-size:13px;color:var(--text-info);text-decoration:none;">View on arXiv →</a>
</div>
{% endif %}

<!-- COMP 3: Top papers this week -->
<div class="card">
  <div class="sec-title">Top papers this week</div>
  <div class="sec-sub">Scored by relevance, novelty, and likely real-world impact · 8.0+ threshold</div>
  <div style="margin-top:10px;">
    {% for p in top_papers %}
    <a href="{{ p.url }}" target="_blank" style="display:block;text-decoration:none;color:inherit;padding:14px 0;border-bottom:0.5px solid var(--border);">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:4px;">
        <div style="font-size:13px;font-weight:500;line-height:1.4;flex:1;">{{ p.title }}</div>
        <span class="score-pill" style="flex-shrink:0;">{{ "%.1f"|format(p.score) }}</span>
      </div>
      <div style="font-size:11px;color:var(--text-secondary);margin-bottom:6px;">{{ p.authors }} · {{ p.institution }}</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px;">
        {% for tag in p.tags %}<span class="cat-tag">{{ tag }}</span>{% endfor %}
      </div>
      <div style="font-size:12px;color:var(--text-secondary);line-height:1.5;">{{ p.summary }}</div>
    </a>
    {% endfor %}
  </div>
</div>

<!-- COMP 4: Research by category + 30-day volume -->
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
  <div class="card" style="margin-bottom:0;">
    <div class="sec-title">Research by category</div>
    <div class="sec-sub">Paper count this week vs last week</div>
    <div style="position:relative;height:260px;width:100%;margin-top:10px;">
      <canvas id="researchCategoryChart"></canvas>
    </div>
  </div>
  <div class="card" style="margin-bottom:0;">
    <div class="sec-title">30-day research volume</div>
    <div class="sec-sub">Papers per category — daily rolling average</div>
    <div style="position:relative;height:260px;width:100%;margin-top:10px;">
      <canvas id="researchVolumeChart"></canvas>
    </div>
  </div>
</div>

<!-- COMP 5: Hot institutions this week -->
<div class="card">
  <div class="sec-title">Hot institutions this week</div>
  <div class="sec-sub">Ranked by paper output × citation velocity · rising = above 4-week average</div>
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
</div>

<!-- COMP 6: Author spotlight -->
<div class="card">
  <div class="sec-title">Author spotlight</div>
  <div class="sec-sub">Researchers who published notable work this week</div>
  <div style="margin-top:12px;display:flex;flex-direction:column;gap:10px;">
    {% for a in author_spotlight %}
    <div style="display:flex;gap:12px;background:var(--bg-secondary);border-radius:var(--radius-md);padding:12px 14px;">
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
    </div>
    {% endfor %}
  </div>
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
</div>

<!-- COMP 8: Research signal analysis -->
<div class="card">
  <div class="sec-title">Research signal analysis</div>
  <div class="sec-sub">What this week's paper volume and topics tell us about where the field is heading</div>
  <div style="margin-top:10px;display:flex;flex-direction:column;gap:8px;">
    {% for s in research_signals %}
    <div class="signal-row signal-{{ s.direction }}">{{ s.text }}</div>
    {% endfor %}
  </div>
</div>

<!-- COMP 9: Fintech & payments research corner -->
<div class="card">
  <div class="sec-title">Fintech & payments research corner</div>
  <div class="sec-sub">AI papers in fraud detection, credit scoring, AML, payment routing, and financial forecasting — with strategic implications for card networks and issuers</div>
  <div style="margin-top:10px;display:flex;flex-direction:column;gap:10px;">
    {% for f in fintech_research %}
    <div style="background:var(--bg-secondary);border-radius:var(--radius-md);padding:14px 16px;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:6px;">
        <div style="font-size:14px;font-weight:500;line-height:1.4;flex:1;">{{ f.title }}</div>
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
  </div>
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

</div>

<div class="foot">
  <div>Auto-generated by Claude · last update {{ today }} · {{ metrics.total_stories }} stories curated from {{ metrics.posts_pulled }} posts</div>
  <div>Pipeline v1.0</div>
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


def render_dashboard(daily_data: Dict) -> str:
    """Render the dashboard HTML from a daily-data JSON payload."""
    template = Template(HTML_TEMPLATE)

    stories = daily_data.get("stories", [])
    fintech_stories = [s for s in stories if s.get("is_fintech")]
    research_stories = [
        s for s in stories
        if any(tag in (s.get("category_tags") or []) for tag in ["Research/Paper", "Open Source", "Benchmark/Evaluation"])
    ]

    stories_by_subreddit = {}
    for s in stories:
        sub = s.get("subreddit", "unknown")
        if sub not in stories_by_subreddit:
            stories_by_subreddit[sub] = []
        stories_by_subreddit[sub].append(s)
    stories_by_subreddit = dict(sorted(stories_by_subreddit.items(), key=lambda x: -len(x[1])))
    return template.render(
    volume_history=daily_data.get("volume_history", []),
    today=daily_data.get("_date", date.today().isoformat()),
    top_story=stories[0] if stories else None,
    top_stories=stories,
    fintech_stories=fintech_stories,
    research_stories=research_stories,
    synthesis=daily_data.get("synthesis", {}),
    metrics=daily_data.get("metrics", {}),
    model_sentiments=daily_data.get("model_sentiments", []),
    etfs=daily_data.get("etfs", []),
    public_ai=daily_data.get("public_ai", []),
    category_breakdown=daily_data.get("category_breakdown", {}),
    sentiment_history=daily_data.get("sentiment_history", {}),
    stories_by_subreddit=stories_by_subreddit,
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
)
