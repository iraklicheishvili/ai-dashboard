"""
Central configuration for the AI Intelligence Dashboard.
Edit this file to change tracked sources, models, ETFs, paths, or thresholds.
"""

from pathlib import Path

# ============================================================
# Project paths — single source of truth, used everywhere
# ============================================================

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
DAILY_DATA_DIR = OUTPUT_DIR / "daily-data"
WEEKLY_STATS_DIR = OUTPUT_DIR / "weekly-stats"
DASHBOARD_DIR = OUTPUT_DIR / "dashboard"

# Persistent cache files (committed to repo so they survive across runs)
FINANCE_CACHE_PATH = OUTPUT_DIR / "finance-cache.json"
MODEL_DEEP_CACHE_PATH = OUTPUT_DIR / "model-deep-cache.json"
MODEL_EVENTS_HISTORY_PATH = OUTPUT_DIR / "model-events-history.json"
MODEL_STRENGTHS_CACHE_PATH = OUTPUT_DIR / "model-strengths-cache.json"
MODEL_SENTIMENT_HISTORY_PATH = OUTPUT_DIR / "model-sentiment-history.json"
GITHUB_STARS_HISTORY_PATH = OUTPUT_DIR / "github-stars-history.json"
HEALTH_PATH = OUTPUT_DIR / "health.json"

DASHBOARD_HTML_PATH = DASHBOARD_DIR / "latest.html"
DASHBOARD_INDEX_PATH = DASHBOARD_DIR / "index.html"

# Dashboard launch date (used in disclaimers + chart starting points)
DASHBOARD_LAUNCH_DATE = "2026-05-01"

# ============================================================
# Reddit (mock until API approval; auto-activates when real creds set)
# ============================================================

# 24 tracked subreddits, organized by theme
SUBREDDITS = {
    "core_ai_news": [
        "artificial",
        "singularity",
        "ArtificialIntelligence",
        "ChatGPT",
    ],
    "research_technical": [
        "MachineLearning",
        "LocalLLaMA",
        "LanguageTechnology",
        "LLMDevs",
        "ComputerVision",
    ],
    "safety_alignment": [
        "ControlProblem",
        "AIAlignment",
    ],
    "agents_applied": [
        "AutoGPT",
    ],
    "company_specific": [
        "OpenAI",
        "Anthropic",
        "GoogleGemini",
        "DeepSeek",
        "Copilot",
    ],
    "robotics": [
        "robotics",
    ],
    "finance_investing": [
        "investing",
        "stocks",
        "fintech",
    ],
    "tech_news": [
        "technology",
        "technews",
        "futurology",
    ],
}

ALL_SUBREDDITS = [sub for cat in SUBREDDITS.values() for sub in cat]

POSTS_PER_SUBREDDIT = 25
POST_TIME_FILTER = "day"
MIN_REDDIT_SCORE = 10

# ============================================================
# Tracked AI models for Page 2
# Llama added in this release.
# Each model has GitHub ecosystem repos used for daily star tracking
# (Component 2.2's GitHub toggle on the trend chart).
# ============================================================

TRACKED_MODELS = [
    {
        "id": "chatgpt",
        "name": "ChatGPT",
        "maker": "OpenAI",
        "color": "#378ADD",
        "keywords": ["chatgpt", "gpt-4", "gpt-5", "gpt-4o", "gpt-4.5", "openai", "o1", "o3"],
        "github_repos": ["openai/openai-python", "openai/openai-cookbook"],
    },
    {
        "id": "claude",
        "name": "Claude",
        "maker": "Anthropic",
        "color": "#D85A30",
        "keywords": ["claude", "anthropic", "sonnet", "opus", "haiku"],
        "github_repos": ["anthropics/anthropic-sdk-python", "anthropics/courses"],
    },
    {
        "id": "gemini",
        "name": "Gemini",
        "maker": "Google DeepMind",
        "color": "#1D9E75",
        "keywords": ["gemini", "google deepmind", "bard"],
        "github_repos": ["google/generative-ai-python", "google-gemini/cookbook"],
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "maker": "DeepSeek AI",
        "color": "#7F77DD",
        "keywords": ["deepseek", "deepseek-r1", "deepseek-r2", "deepseek-v3"],
        "github_repos": ["deepseek-ai/DeepSeek-V3", "deepseek-ai/DeepSeek-R1"],
    },
    {
        "id": "grok",
        "name": "Grok",
        "maker": "xAI",
        "color": "#E24B4A",
        "keywords": ["grok", "xai", "x.ai", "elon musk ai"],
        "github_repos": ["xai-org/grok-1"],
    },
    {
        "id": "copilot",
        "name": "Copilot",
        "maker": "Microsoft",
        "color": "#888780",
        "keywords": ["copilot", "github copilot", "microsoft copilot", "copilot studio"],
        "github_repos": ["github/copilot-cli"],
    },
    {
        "id": "llama",
        "name": "Llama",
        "maker": "Meta",
        "color": "#4267B2",
        "keywords": ["llama", "llama-3", "llama 3", "meta ai", "llama-recipes"],
        "github_repos": ["meta-llama/llama-recipes", "meta-llama/llama-models"],
    },
]

# ============================================================
# AI ETFs tracked on Page 3
# ============================================================

TRACKED_ETFS = [
    {
        "ticker": "CHAT",
        "name": "Roundhill Generative AI & Technology",
        "exchange": "NYSE Arca",
        "color": "#D85A30",
        "description": "World's first generative AI ETF. Actively managed with a 50% revenue-purity screen. Rotates toward new gen-AI entrants as the space evolves.",
        "stats": ["Exp: 0.75%", "49 holdings", "Active mgmt", "Est. May 2023"],
    },
    {
        "ticker": "ARTY",
        "name": "iShares Future AI & Technology ETF",
        "exchange": "NYSE",
        "color": "#378ADD",
        "description": "BlackRock's AI flagship. Tracks Morningstar Global AI Select Index. ~50 stocks across gen AI, infra, services. Best 1-yr performer in the category.",
        "stats": ["Exp: 0.47%", "50 holdings", "Passive", "BlackRock"],
    },
    {
        "ticker": "AIQ",
        "name": "Global X AI & Technology ETF",
        "exchange": "NASDAQ",
        "color": "#1D9E75",
        "description": "Largest AI ETF by AUM. Tracks Indxx AI & Big Data Index across 86 companies. The S&P 500 of AI ETFs.",
        "stats": ["Exp: 0.68%", "86 holdings", "Passive", "Est. 2018"],
    },
    {
        "ticker": "IGPT",
        "name": "Invesco AI & Next Gen Software ETF",
        "exchange": "NYSE Arca",
        "color": "#7F77DD",
        "description": "Infrastructure & semiconductor tilt. Heavy Micron, SK Hynix, Nvidia exposure. Oldest fund on the list, modernised mandate.",
        "stats": ["Exp: 0.56%", "100 holdings", "Passive", "Est. 2005"],
    },
    {
        "ticker": "BOTZ",
        "name": "Global X Robotics & AI ETF",
        "exchange": "NASDAQ",
        "color": "#BA7517",
        "description": "Applied AI and industrial robotics focus. Tracks Indxx Global Robotics & AI Thematic Index. Heavy industrials, healthcare, Japanese automation.",
        "stats": ["Exp: 0.68%", "50 holdings", "Passive", "~30% Japan"],
    },
    {
        "ticker": "AGIX",
        "name": "KraneShares AGI ETF",
        "exchange": "NYSE Arca",
        "color": "#D4537E",
        "description": "Unique private-company exposure via SEC Rule 22e-4. Holds 2.5% Anthropic stake and 3.2% SpaceX (indirect xAI). Only retail proxy for private AI giants.",
        "stats": ["Exp: 0.99%", "Private stakes", "Anthropic+xAI", "Illiquid premium"],
    },
]

TRACKED_PUBLIC_AI = [
    {"ticker": "NVDA", "name": "Nvidia"},
    {"ticker": "MSFT", "name": "Microsoft"},
    {"ticker": "GOOGL", "name": "Alphabet"},
    {"ticker": "META", "name": "Meta"},
    {"ticker": "AMZN", "name": "Amazon"},
    {"ticker": "TSM", "name": "TSMC"},
    {"ticker": "AVGO", "name": "Broadcom"},
    {"ticker": "ORCL", "name": "Oracle"},
    {"ticker": "AMD", "name": "AMD"},
    {"ticker": "PLTR", "name": "Palantir"},
]

# ============================================================
# Story curation
# ============================================================

CATEGORY_TAGS = [
    "Model Release",
    "Model Update",
    "Product Launch",
    "Benchmark/Evaluation",
    "Research/Paper",
    "Open Source",
    "Infrastructure/Hardware",
    "Funding/Investment",
    "Acquisition/Partnership",
    "Regulation/Policy",
    "Leadership/People",
    "Fintech/Payments",
    "Agents/Automation",
    "Robotics",
    "Computer Vision",
    "Tutorial/Guide",
    "Discussion/Opinion",
    "Controversy",
]

# Adaptive top-15 selection — threshold is reported in logs / health
# but the feed always shows the top 15 regardless.
RELEVANCE_THRESHOLD = 7.0

# ============================================================
# Claude models
# ============================================================

HAIKU_MODEL = "claude-haiku-4-5"
SONNET_MODEL = "claude-sonnet-4-6"
OPUS_MODEL = "claude-opus-4-7"

# ============================================================
# Backward-compat string paths (legacy code expects strings)
# ============================================================

OUTPUT_DIR_STR = str(OUTPUT_DIR)
DAILY_DATA_DIR_STR = str(DAILY_DATA_DIR)
WEEKLY_STATS_DIR_STR = str(WEEKLY_STATS_DIR)
DASHBOARD_DIR_STR = str(DASHBOARD_DIR)
