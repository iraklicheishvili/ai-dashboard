"""
Central configuration for the AI Intelligence Dashboard.
Edit this file to change tracked subreddits, models, ETFs, or categories.
"""

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

# Flat list of all subreddits for iteration
ALL_SUBREDDITS = [sub for category in SUBREDDITS.values() for sub in category]

# Posts per subreddit per pull
POSTS_PER_SUBREDDIT = 25

# Time filter for posts: "day" / "week" / "month"
POST_TIME_FILTER = "day"

# Minimum score to even consider a post (Reddit upvotes)
MIN_REDDIT_SCORE = 10

# Models tracked on Page 2
TRACKED_MODELS = [
    {
        "id": "chatgpt",
        "name": "ChatGPT",
        "maker": "OpenAI",
        "color": "#378ADD",
        "keywords": ["chatgpt", "gpt-4", "gpt-5", "gpt-4o", "gpt-4.5", "openai", "o1", "o3"],
    },
    {
        "id": "claude",
        "name": "Claude",
        "maker": "Anthropic",
        "color": "#D85A30",
        "keywords": ["claude", "anthropic", "sonnet", "opus", "haiku"],
    },
    {
        "id": "gemini",
        "name": "Gemini",
        "maker": "Google DeepMind",
        "color": "#1D9E75",
        "keywords": ["gemini", "google deepmind", "bard"],
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "maker": "DeepSeek AI",
        "color": "#7F77DD",
        "keywords": ["deepseek", "deepseek-r1", "deepseek-r2", "deepseek-v3"],
    },
    {
        "id": "grok",
        "name": "Grok",
        "maker": "xAI",
        "color": "#D4537E",
        "keywords": ["grok", "xai", "x.ai", "elon musk ai"],
    },
    {
        "id": "copilot",
        "name": "Copilot",
        "maker": "Microsoft",
        "color": "#888780",
        "keywords": ["copilot", "github copilot", "microsoft copilot", "copilot studio"],
    },
]

# AI ETFs tracked on Page 3
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

# Public AI companies tracked for market cap leaderboard
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

# Category tags assigned to each story (from spec)
CATEGORY_TAGS = [
    # Model & Product
    "Model Release",
    "Model Update",
    "Product Launch",
    "Benchmark/Evaluation",
    # Technical
    "Research/Paper",
    "Open Source",
    "Infrastructure/Hardware",
    # Industry
    "Funding/Investment",
    "Acquisition/Partnership",
    "Regulation/Policy",
    "Leadership/People",
    # Applications
    "Fintech/Payments",
    "Agents/Automation",
    "Robotics",
    "Computer Vision",
    # Community
    "Tutorial/Guide",
    "Discussion/Opinion",
    "Controversy",
]

# Curation criteria
RELEVANCE_THRESHOLD = 7.0  # Only include stories scoring >= this

# Claude models
HAIKU_MODEL = "claude-haiku-4-5-20251001"
OPUS_MODEL = "claude-opus-4-7"  # Synthesis layer

# Output paths
OUTPUT_DIR = "output"
DAILY_DATA_DIR = f"{OUTPUT_DIR}/daily-data"
WEEKLY_STATS_DIR = f"{OUTPUT_DIR}/weekly-stats"
DASHBOARD_DIR = f"{OUTPUT_DIR}/dashboard"
