# AI Intelligence Dashboard

Automated daily AI intelligence pipeline. Scrapes 24 subreddits + web search,
analyzes content with Claude, stores structured JSON history, and renders an
interactive HTML dashboard.

## Pipeline

```
Reddit (24 subs) + Web search
        ↓
Haiku 4.5  → score, tag, summarize each story
        ↓
Opus 4.7   → synthesize daily narrative + insights
        ↓
yfinance   → ETF / market data
        ↓
JSON       → daily-data/YYYY-MM-DD.json
HTML       → dashboard/latest.html
```

## Setup

### 1. Install Python 3.10+ and dependencies

```bash
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Get API credentials

You need three sets of keys:

**Reddit API** (https://www.reddit.com/prefs/apps)
- Click "create app" at the bottom, choose "script"
- name: `ai-dashboard`
- redirect uri: `http://localhost:8080`
- Copy the client_id (under app name) and client_secret

**Anthropic API** (https://console.anthropic.com)
- Settings → API Keys → Create Key
- Free tier includes $5 of credits

### 3. Configure

Copy `.env.example` to `.env` and fill in:

```
REDDIT_CLIENT_ID=your_id
REDDIT_CLIENT_SECRET=your_secret
REDDIT_USER_AGENT=ai-dashboard/1.0 by your_username

ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Run it

```bash
python -m src.main
```

This runs the full pipeline once and writes:
- `output/daily-data/2026-04-30.json` — structured analysis
- `output/dashboard/latest.html` — rendered dashboard

Open the HTML file in your browser.

## Project structure

```
ai-dashboard/
├── src/
│   ├── main.py        # Orchestrator
│   ├── scraper.py     # Reddit data collection (PRAW)
│   ├── analyzer.py    # Claude API: scoring + synthesis
│   ├── stocks.py      # ETF data via yfinance
│   ├── storage.py     # JSON read/write
│   └── render.py      # HTML dashboard renderer
├── prompts/
│   ├── score_story.txt    # Per-story analysis
│   ├── synthesize.txt     # Daily synthesis
│   ├── model_sentiment.txt # Per-model sentiment analysis
│   └── insights.txt       # Pattern insights
├── config.py          # Subreddits, models, ETFs, categories
├── .env               # API keys (gitignored)
├── output/            # Generated files (gitignored)
└── requirements.txt
```

## Cost estimate

Per-day: ~$0.15-0.25 in Anthropic API costs
Per-month: ~$5-8

Reddit, yfinance, hosting are all free.

## Next steps after local works

- Schedule daily run via GitHub Actions or cron
- Host dashboard on GitHub Pages or GCS
- Add email summary via SendGrid free tier
- Add X/Twitter scraping for key people quotes
