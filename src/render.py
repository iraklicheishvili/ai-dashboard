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
  .tabs{display:flex;gap:4px;background:var(--bg-secondary);padding:4px;border-radius:var(--radius-md);margin-bottom:14px;position:sticky;top:0;z-index:5;flex-wrap:wrap;}
  .tab{flex:1;min-width:120px;padding:8px 12px;font-size:13px;border-radius:var(--radius-md);border:none;background:transparent;color:var(--text-secondary);cursor:pointer;text-align:center;transition:all 0.15s;font-family:inherit;}
  .tab:hover{color:var(--text-primary);}
  .tab.active{background:var(--bg-primary);color:var(--text-primary);font-weight:500;box-shadow:0 0 0 0.5px var(--border);}
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

<div class="tabs" role="tablist">
  <button class="tab active" data-page="p1">AI intelligence</button>
  <button class="tab" data-page="p2">Model tracker</button>
  <button class="tab" data-page="p3">AI finance</button>
  <button class="tab" data-page="p4">Research & papers</button>
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
          label: 'Stor
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
      <div style="display:flex;align-items:center;gap:16px;margin-top:10px;position:relative">
        <canvas id="catDonut" width="160" height="160" style="flex-shrink:0;width:160px;height:160px"></canvas>
<div id="donutTooltip" style="display:none;position:absolute;background:var(--bg-secondary);border:0.5px solid var(--border);border-radius:var(--radius-md);padding:6px 10px;font-size:12px;color:var(--text-primary);pointer-events:none;z-index:10"></div>
        <div id="catLegend" style="display:flex;flex-direction:column;gap:5px;font-size:12px"></div>
      </div>
    </div>
    <div style="padding:16px 18px">
      <div class="sec-title">Trending topics</div>
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:10px">
      {% for term in synthesis.trending_topics %}
        <span class="wc-tag wc-{{ term.category | default('other') | lower | replace('/', '_') | replace(' ', '_') }}" style="font-size:{{ [10 + (term.weight | int) * 1.5, 20] | min | int }}px;{% if term.weight >= 8 %}font-weight:500;{% endif %}">{{ term.term }}</span>
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
<div class="card">
  <div class="sec-title">Subreddit hot topics this week</div>
  <select id="subSelect" onchange="filterSub(this.value)" style="width:100%;margin:10px 0 14px;">
    {% for sub, sub_stories in stories_by_subreddit.items() %}
    <option value="{{ sub }}">{{ sub }} · {{ sub_stories | length }} stories</option>
    {% endfor %}
  </select>
  <div id="subStories">
    {% for sub, sub_stories in stories_by_subreddit.items() %}
    <div class="sub-group" data-sub="{{ sub }}" style="{% if not loop.first %}display:none{% endif %}">
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
  <div class="model-deep" data-model="{{ m.model_config.name }}" style="{% if not loop.first %}display:none{% endif %}">

    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px;">
      <div class="mcard">
        <div class="mlabel">Sentiment</div>
        <div class="mvalue" style="color:{{ m.model_config.color }};">{{ "%.1f"|format(m.sentiment_score) }}</div>
        <div style="font-size:10px;color:var(--text-secondary);">out of 10</div>
      </div>
      <div class="mcard">
        <div class="mlabel">MAU</div>
        <div class="mvalue" style="font-size:18px;">{{ m.deep.mau | default('—') }}</div>
        <div style="font-size:10px;color:var(--text-secondary);">estimated</div>
      </div>
      <div class="mcard">
        <div class="mlabel">Market share</div>
        <div class="mvalue" style="font-size:18px;">{{ m.deep.market_share | default('—') }}</div>
        <div style="font-size:10px;{% if m.deep.market_share_change and m.deep.market_share_change.startswith('+') %}color:#3b6d11{% else %}color:var(--text-secondary){% endif %};">{{ m.deep.market_share_change | default('') }} WoW</div>
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
        {% for s in (m.deep.strengths or []) %}
        <div class="cap-item"><div class="dot-g"></div><div>{{ s }}</div></div>
        {% endfor %}
      </div>
      <div class="stat-card">
        <div style="font-size:11px;font-weight:500;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px;">Weaknesses</div>
        {% for w in (m.deep.weaknesses or []) %}
        <div class="cap-item"><div class="dot-r"></div><div>{{ w }}</div></div>
        {% endfor %}
      </div>
    </div>

    {% if m.deep.mention_chart %}
    <div style="margin-bottom:14px;">
      <div class="sec-title">Reddit mention sentiment — strengths vs weaknesses</div>
      <div class="sec-sub">Positive / negative Reddit mentions — current 30 days vs prior 30 days</div>
      <div style="position:relative;height:280px;width:100%;margin-top:8px;">
        <canvas id="mentionChart-{{ loop.index }}"></canvas>
      </div>
      <div style="font-size:10px;color:var(--text-tertiary);text-align:center;margin-top:4px;">← negative mentions  |  positive mentions →</div>
    </div>
    {% endif %}

    {% if m.deep.recent_changes %}
    <div style="margin-bottom:14px;">
      <div class="sec-title">Recent changes</div>
      {% for c in m.deep.recent_changes %}
      <div style="display:flex;gap:10px;padding:6px 0;border-bottom:0.5px solid var(--border);font-size:12px;">
        <div style="width:48px;color:var(--text-secondary);flex-shrink:0;">{{ c.date }}</div>
        <div style="color:var(--text-info);">{{ c.text }}</div>
      </div>
      {% endfor %}
    </div>
    {% endif %}

    {% if m.deep.key_people %}
    <div>
      <div class="sec-title">Key people — latest activity</div>
      {% for p in m.deep.key_people %}
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
{% if m.deep.mention_chart %}
(function(){
  var ctx = document.getElementById('mentionChart-{{ loop.index }}');
  if(!ctx) return;
  var data = {{ m.deep.mention_chart | tojson }};
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


<!-- ==================== PAGE 3: AI FINANCE ==================== -->
<div id="p3" class="page">

<div class="card">
  <div class="sec-title">AI ETF market pulse</div>
  <div class="sec-sub">US-listed AI ETFs — prices as of {{ today }}</div>
  <div style="display:flex;gap:0;padding:0 0 6px;border-bottom:0.5px solid var(--border-strong);margin-bottom:2px;">
    <div class="col-hdr" style="width:52px;">Ticker</div>
    <div class="col-hdr" style="flex:1;">Name</div>
    <div class="col-hdr" style="width:60px;text-align:right;">Price</div>
    <div class="col-hdr" style="width:60px;text-align:right;">DoD</div>
    <div class="col-hdr" style="width:50px;text-align:right;">1-yr</div>
    <div class="col-hdr" style="width:50px;text-align:right;">AUM</div>
  </div>
  {% for e in etfs %}
  <div style="display:flex;align-items:center;gap:0;padding:9px 0;border-bottom:0.5px solid var(--border);">
    <a href="https://finance.yahoo.com/quote/{{ e.ticker }}" target="_blank" style="font-size:13px;font-weight:500;color:var(--text-info);width:52px;text-decoration:none;">{{ e.ticker }}</a>
    <div style="font-size:11px;color:var(--text-secondary);flex:1;min-width:0;padding-right:6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ e.name }}</div>
    <div style="font-size:13px;font-weight:500;width:60px;text-align:right;">${{ "%.2f"|format(e.price | default(0)) }}</div>
    <div style="font-size:12px;font-weight:500;width:60px;text-align:right;{% if (e.dod_pct | default(0)) >= 0 %}color:#3b6d11{% else %}color:#a32d2d{% endif %};">{% if (e.dod_pct | default(0)) >= 0 %}+{% endif %}{{ "%.2f"|format(e.dod_pct | default(0)) }}%</div>
    <div style="font-size:12px;width:50px;text-align:right;">{% if (e.year_return_pct | default(0)) >= 0 %}+{% endif %}{{ "%.0f"|format(e.year_return_pct | default(0)) }}%</div>
    <div style="font-size:11px;color:var(--text-secondary);width:50px;text-align:right;">{{ e.aum | default("n/a") }}</div>
  </div>
  {% endfor %}
</div>

{% if public_ai %}
<div class="card">
  <div class="sec-title">Public AI — top 10 by market cap</div>
  <div class="sec-sub">Market cap in $B</div>
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
</div>
{% endif %}

<div class="card">
  <div class="sec-title">Coming next</div>
  <div class="sec-sub">VC league table, arms race chart, and detailed funding rounds will populate from web search in v2 of the pipeline.</div>
</div>

</div>

<!-- ==================== PAGE 4: RESEARCH & PAPERS ==================== -->
<div id="p4" class="page">

<div class="card">
  <div class="sec-title">Research & papers</div>
  <div class="sec-sub">arXiv integration is the next milestone after pipeline v1 ships. Currently this page surfaces research-tagged stories from Reddit.</div>
</div>

{% if research_stories %}
<div class="card">
  <div class="sec-title">Research-tagged stories from today's Reddit pull</div>
  {% for s in research_stories[:10] %}
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
{% endif %}

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
)
