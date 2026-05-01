"""
Mock Reddit data for testing the pipeline without real Reddit API credentials.
Used automatically when REDDIT_CLIENT_ID is still set to the placeholder value.
"""

from datetime import datetime, timezone, timedelta


def _ts(hours_ago: int) -> tuple:
    dt = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return dt.timestamp(), dt.isoformat()


def get_mock_posts() -> list:
    """Return a realistic set of pretend Reddit posts for testing."""
    now = datetime.now(timezone.utc)
    posts = [
        {
            "id": "mock001", "title": "DeepSeek R2 tops MATH benchmark — beats o1 across 5 categories",
            "subreddit": "r/LocalLLaMA", "url": "https://reddit.com/r/LocalLLaMA/mock001",
            "external_url": "https://github.com/deepseek-ai", "score": 8120, "num_comments": 1420,
            "author": "deepseek_fan", "selftext": "DeepSeek just released R2 with significant gains across the MATH benchmark suite. Outperforms OpenAI o1 across 5 of 8 categories. Open weights, MIT license. Inference cost about 1/10th of comparable closed models.",
            "is_video": False,
        },
        {
            "id": "mock002", "title": "Anthropic releases Claude Sonnet 4.6 with improved instruction following",
            "subreddit": "r/Anthropic", "url": "https://reddit.com/r/Anthropic/mock002",
            "external_url": "https://anthropic.com/news/sonnet-4-6", "score": 4250, "num_comments": 612,
            "author": "claude_user", "selftext": "Sonnet 4.6 ships with notable improvements to multi-step instruction following and fewer refusals on borderline-but-safe requests. API and Claude.ai available now.",
            "is_video": False,
        },
        {
            "id": "mock003", "title": "OpenAI ships GPT-4.5 turbo — 30% latency reduction across all endpoints",
            "subreddit": "r/OpenAI", "url": "https://reddit.com/r/OpenAI/mock003",
            "external_url": "https://openai.com/blog/gpt-4-5-turbo", "score": 3890, "num_comments": 545,
            "author": "openai_dev", "selftext": "GPT-4.5 turbo is now generally available with substantially faster inference. Pricing held flat. Operator program also expanded to 40 new partners this week.",
            "is_video": False,
        },
        {
            "id": "mock004", "title": "Mistral raises $1.2B Series C at $14B valuation, plans European AI cloud",
            "subreddit": "r/artificial", "url": "https://reddit.com/r/artificial/mock004",
            "external_url": "https://techcrunch.com/mistral-1-2b", "score": 3210, "num_comments": 388,
            "author": "vc_watcher", "selftext": "Mistral closes Series C led by a16z. Plans to launch a sovereign European AI cloud to compete with hyperscalers. France and Germany are anchor enterprise customers.",
            "is_video": False,
        },
        {
            "id": "mock005", "title": "EU AI Act enforcement begins — first fines target generative model providers",
            "subreddit": "r/technology", "url": "https://reddit.com/r/technology/mock005",
            "external_url": "https://reuters.com/eu-ai-act", "score": 2890, "num_comments": 421,
            "author": "policy_observer", "selftext": "European Commission has issued the first fines under the AI Act, targeting generative model providers for inadequate transparency on training data sources. Fines totaled €45M.",
            "is_video": False,
        },
        {
            "id": "mock006", "title": "Stripe integrates Anthropic computer-use for autonomous merchant onboarding",
            "subreddit": "r/fintech", "url": "https://reddit.com/r/fintech/mock006",
            "external_url": "https://stripe.com/blog/anthropic-integration", "score": 1840, "num_comments": 215,
            "author": "payments_pro", "selftext": "Stripe announces integration with Anthropic's computer-use API to fully automate merchant onboarding workflows. Eliminates manual KYB review for low-risk merchants. Rollout starts next month.",
            "is_video": False,
        },
        {
            "id": "mock007", "title": "Mastercard pilots agent-driven B2B payments with three Fortune 100 partners",
            "subreddit": "r/fintech", "url": "https://reddit.com/r/fintech/mock007",
            "external_url": "https://mastercard.com/news/agent-b2b", "score": 1620, "num_comments": 178,
            "author": "fintech_analyst", "selftext": "Mastercard launches a B2B payments pilot using AI agents to handle invoice-to-pay cycles autonomously. Three unnamed Fortune 100 companies are participating.",
            "is_video": False,
        },
        {
            "id": "mock008", "title": "Gemini 2.5 Pro hits #1 on coding benchmarks",
            "subreddit": "r/MachineLearning", "url": "https://reddit.com/r/MachineLearning/mock008",
            "external_url": "https://blog.google/gemini-2-5-pro", "score": 2340, "num_comments": 312,
            "author": "ml_researcher", "selftext": "Gemini 2.5 Pro now sits at the top of HumanEval+, SWE-Bench, and LiveCodeBench. Significant gains over the previous Gemini 2.0 across all coding-focused evals.",
            "is_video": False,
        },
        {
            "id": "mock009", "title": "Plaid + OpenAI partnership: real-time financial data for ChatGPT enterprise",
            "subreddit": "r/fintech", "url": "https://reddit.com/r/fintech/mock009",
            "external_url": "https://plaid.com/news/openai", "score": 1450, "num_comments": 168,
            "author": "embedded_finance", "selftext": "Plaid and OpenAI announce partnership giving ChatGPT Enterprise users access to real-time bank account data through Plaid's API layer. Available to compliant enterprise customers in Q3.",
            "is_video": False,
        },
        {
            "id": "mock010", "title": "vLLM v0.7 ships — 2x throughput on H100s with new scheduler",
            "subreddit": "r/LocalLLaMA", "url": "https://reddit.com/r/LocalLLaMA/mock010",
            "external_url": "https://github.com/vllm-project/vllm/releases", "score": 2120, "num_comments": 245,
            "author": "infra_eng", "selftext": "vLLM 0.7 brings a new continuous batching scheduler that doubles throughput on H100 deployments. Major improvements to chunked prefill and prefix caching as well.",
            "is_video": False,
        },
        {
            "id": "mock011", "title": "Llama 4 leak: 600B MoE architecture details surface on GitHub",
            "subreddit": "r/LocalLLaMA", "url": "https://reddit.com/r/LocalLLaMA/mock011",
            "external_url": "https://github.com/meta-llama-leak", "score": 5430, "num_comments": 892,
            "author": "open_source_advocate", "selftext": "Configuration files appearing to be from Meta's Llama 4 surfaced briefly on a GitHub gist. Suggest a 600B parameter MoE architecture with 8 active experts. Meta has not commented.",
            "is_video": False,
        },
        {
            "id": "mock012", "title": "xAI raises $6B Series C at $50B valuation",
            "subreddit": "r/artificial", "url": "https://reddit.com/r/artificial/mock012",
            "external_url": "https://x.ai/news/series-c", "score": 2640, "num_comments": 412,
            "author": "tech_investor", "selftext": "xAI closes $6B Series C at a $50B post-money valuation, doubling from last raise. Founders Fund leads. Capital earmarked for Grok 4 training and Memphis data center expansion.",
            "is_video": False,
        },
        {
            "id": "mock013", "title": "Constitutional AI at Scale: Alignment Without Human Feedback at 1T Parameters",
            "subreddit": "r/MachineLearning", "url": "https://reddit.com/r/MachineLearning/mock013",
            "external_url": "https://arxiv.org/abs/2504.16988", "score": 1890, "num_comments": 234,
            "author": "alignment_researcher", "selftext": "New Anthropic paper shows Constitutional AI methods scale to trillion-parameter models with no degradation in alignment quality. Suggests RLHF may be optional at scale. Strong empirical results across 47 evals.",
            "is_video": False,
        },
        {
            "id": "mock014", "title": "Cohere raises $450M Series D, doubles down on enterprise",
            "subreddit": "r/artificial", "url": "https://reddit.com/r/artificial/mock014",
            "external_url": "https://cohere.com/blog/series-d", "score": 1340, "num_comments": 156,
            "author": "enterprise_ai", "selftext": "Cohere closes $450M led by PSP Investments at a $5.5B valuation. Doubling down on enterprise-only positioning, away from consumer chatbots. Major customers include Oracle and Notion.",
            "is_video": False,
        },
        {
            "id": "mock015", "title": "Best 7B model for code right now? Community benchmarks April 2026",
            "subreddit": "r/LocalLLaMA", "url": "https://reddit.com/r/LocalLLaMA/mock015",
            "external_url": None, "score": 1240, "num_comments": 312,
            "author": "local_dev", "selftext": "Crowdsourced benchmark comparison of the top 7B coding models as of April 2026. Qwen3-Coder-7B and DeepSeek-Coder-V3-7B trade wins across HumanEval, BigCodeBench, and SWE-Bench Lite.",
            "is_video": False,
        },
        {
            "id": "mock016", "title": "Microsoft acquires Inflection AI talent team for $650M",
            "subreddit": "r/technology", "url": "https://reddit.com/r/technology/mock016",
            "external_url": "https://blogs.microsoft.com/inflection-acq", "score": 2180, "num_comments": 278,
            "author": "ma_watcher", "selftext": "Microsoft completes acqui-hire of Inflection AI's research team. ~40 researchers join the Copilot org. Deal structure avoids HSR antitrust filing. Mustafa Suleyman remains as Microsoft AI CEO.",
            "is_video": False,
        },
        {
            "id": "mock017", "title": "Perplexity AI files confidential S-1, IPO expected Q3 2026",
            "subreddit": "r/stocks", "url": "https://reddit.com/r/stocks/mock017",
            "external_url": "https://sec.gov/perplexity-s1", "score": 1750, "num_comments": 198,
            "author": "ipo_tracker", "selftext": "Perplexity files confidential S-1 with the SEC. Goldman Sachs and Morgan Stanley leading. Last private valuation was $9B. Would be the first major AI-native search company to go public.",
            "is_video": False,
        },
        {
            "id": "mock018", "title": "Boston Dynamics Atlas humanoid now operational on factory floor at Hyundai",
            "subreddit": "r/robotics", "url": "https://reddit.com/r/robotics/mock018",
            "external_url": "https://bostondynamics.com/atlas-hyundai", "score": 3120, "num_comments": 445,
            "author": "robotics_eng", "selftext": "Boston Dynamics announces Atlas humanoid robots are now operational on Hyundai's factory floor in real production tasks. First major humanoid deployment in industrial setting.",
            "is_video": False,
        },
        {
            "id": "mock019", "title": "Apple ships on-device 7B MoE model in iOS 19 beta",
            "subreddit": "r/MachineLearning", "url": "https://reddit.com/r/MachineLearning/mock019",
            "external_url": "https://apple.com/newsroom/ai-ios-19", "score": 2890, "num_comments": 524,
            "author": "apple_dev", "selftext": "iOS 19 beta includes a 7B parameter MoE model running fully on-device with 40ms latency on iPhone 16 Pro. Replaces server-side calls for most Siri and Writing Tools features.",
            "is_video": False,
        },
        {
            "id": "mock020", "title": "Ramp adds AI-powered spend intelligence, raises $150M extension",
            "subreddit": "r/fintech", "url": "https://reddit.com/r/fintech/mock020",
            "external_url": "https://ramp.com/blog/series-e-extension", "score": 980, "num_comments": 112,
            "author": "corp_card_user", "selftext": "Ramp closes $150M Series E extension on the back of new AI-powered autonomous approval workflows. Targeting commercial card share against incumbents Chase, Amex, and Citi.",
            "is_video": False,
        },
        {
            "id": "mock021", "title": "OpenAI Operator now available to ChatGPT Pro users",
            "subreddit": "r/ChatGPT", "url": "https://reddit.com/r/ChatGPT/mock021",
            "external_url": "https://openai.com/operator-rollout", "score": 4120, "num_comments": 632,
            "author": "agents_enthusiast", "selftext": "Operator browser-agent product opened to all ChatGPT Pro subscribers today. Use cases include online ordering, form filling, and research workflows. Limited to 500 tasks per month per user.",
            "is_video": False,
        },
        {
            "id": "mock022", "title": "Local Sonnet 4.6 alternative — Qwen3 14B fine-tune comparison",
            "subreddit": "r/LocalLLaMA", "url": "https://reddit.com/r/LocalLLaMA/mock022",
            "external_url": None, "score": 890, "num_comments": 156,
            "author": "fine_tuner", "selftext": "Comparison of Qwen3-14B fine-tunes attempting to approximate Claude Sonnet 4.6's instruction-following ability. Best fine-tune reaches ~70% of Sonnet quality on internal evals at 1/100th the cost.",
            "is_video": False,
        },
        {
            "id": "mock023", "title": "DeepSeek API pricing cut 60% — triggers market-wide repricing",
            "subreddit": "r/DeepSeek", "url": "https://reddit.com/r/DeepSeek/mock023",
            "external_url": "https://api-docs.deepseek.com/pricing", "score": 3450, "num_comments": 412,
            "author": "api_user", "selftext": "DeepSeek cuts API pricing across all tiers by 60%. Within 48 hours OpenAI and Anthropic announced their own pricing adjustments. Open weights pressure is now visibly affecting closed lab margins.",
            "is_video": False,
        },
        {
            "id": "mock024", "title": "Visa Research publishes FraudRadar GNN paper — 23% fewer false positives",
            "subreddit": "r/MachineLearning", "url": "https://reddit.com/r/MachineLearning/mock024",
            "external_url": "https://arxiv.org/abs/2504.14102", "score": 1240, "num_comments": 134,
            "author": "graph_ml", "selftext": "Visa Research releases FraudRadar, a temporal graph neural network for real-time card fraud detection. Tested on 2.1B real transactions, 23% reduction in false positives vs incumbent FICO models.",
            "is_video": False,
        },
        {
            "id": "mock025", "title": "GitHub Copilot adds multi-file editing and workspace context",
            "subreddit": "r/Copilot", "url": "https://reddit.com/r/Copilot/mock025",
            "external_url": "https://github.blog/copilot-multifile", "score": 1680, "num_comments": 234,
            "author": "github_user", "selftext": "GitHub Copilot now supports coordinated multi-file edits and full workspace context awareness. Direct competitive response to Cursor and Windsurf gaining developer mindshare.",
            "is_video": False,
        },
    ]

    # Add timestamp data to each post (staggered over the past 24 hours)
    for i, post in enumerate(posts):
        ts, iso = _ts(hours_ago=(i + 1) * 1)
        post["created_utc"] = ts
        post["created_iso"] = iso

    return posts