"""
Inject dummy Page 3 data into today's JSON for testing the AI Finance dashboard.
Run this once to populate funding/valuation/M&A data, then re-render the dashboard.
"""

import json
import sys

JSON_PATH = 'output/daily-data/2026-05-02.json'

def make_sparkline_points(start_y, end_y, n=8, w=80, h=18):
    """Generate SVG polyline points for a sparkline."""
    import random
    random.seed(int(start_y * 100 + end_y * 7))
    pts = []
    for i in range(n):
        x = (w / (n - 1)) * i
        # Interpolate from start to end with noise
        t = i / (n - 1)
        base = start_y + (end_y - start_y) * t
        noise = random.uniform(-2, 2)
        y = max(2, min(h - 2, base + noise))
        pts.append(f'{x:.0f},{y:.0f}')
    return ' '.join(pts)


def main():
    with open(JSON_PATH, encoding='utf-8') as f:
        d = json.load(f)

    # ETF colors and sparkline data
    etf_color_map = {
        'CHAT': '#EF9F27', 'ARTY': '#378ADD', 'AIQ': '#1D9E75',
        'IGPT': '#7F77DD', 'BOTZ': '#E24B4A', 'AGIX': '#D4537E',
    }
    for e in d.get('etfs', []):
        ticker = e.get('ticker', '')
        e['color'] = etf_color_map.get(ticker, '#888780')
        e['sparkline'] = True
        # Direction follows DoD pct
        if e.get('dod_pct', 0) >= 0:
            e['sparkline_points'] = make_sparkline_points(14, 4)
        else:
            e['sparkline_points'] = make_sparkline_points(4, 14)

    # Comp 1: Funding summary metrics
    d['funding_summary'] = {
        'total_raised': '4.8B',
        'total_raised_change': '+22%',
        'deals_closed': 31,
        'deals_change': '+7',
        'largest_round': '1.2B',
        'largest_round_company': 'Mistral Series C',
        'median_premoney': '340M',
        'median_trend': 'up',
    }

    # Comp 3: Recent funding rounds
    d['funding_rounds'] = [
        {'company': 'Mistral AI', 'country': 'FR', 'category': 'Foundation model', 'amount': '1.2B', 'valuation': '14B', 'stage': 'Series D', 'lead_investor': 'Andreessen Horowitz'},
        {'company': 'xAI (Grok)', 'country': 'US', 'category': 'Foundation model', 'amount': '6.0B', 'valuation': '50B', 'stage': 'Series D', 'lead_investor': 'Founders Fund'},
        {'company': 'Perplexity AI', 'country': 'US', 'category': 'AI Search', 'amount': '500M', 'valuation': '9B', 'stage': 'Series E', 'lead_investor': 'IVP'},
        {'company': 'Cohere', 'country': 'CA', 'category': 'Enterprise AI', 'amount': '450M', 'valuation': '5.5B', 'stage': 'Series D', 'lead_investor': 'PSP Investments'},
        {'company': 'Poolside AI', 'country': 'US', 'category': 'Code generation', 'amount': '300M', 'valuation': '3B', 'stage': 'Series B', 'lead_investor': 'Bain Capital'},
        {'company': 'Cognition (Devin)', 'country': 'US', 'category': 'AI agents', 'amount': '175M', 'valuation': '2B', 'stage': 'Series B', 'lead_investor': 'Founders Fund'},
    ]

    # Comp 4: Private AI top 10 by valuation
    d['private_ai'] = [
        {'name': 'OpenAI', 'valuation_billions': 157, 'last_round': '40B', 'last_round_date': 'Mar 2026'},
        {'name': 'xAI', 'valuation_billions': 50, 'last_round': '6B', 'last_round_date': 'Apr 2026'},
        {'name': 'Anthropic', 'valuation_billions': 61, 'last_round': '3.5B', 'last_round_date': 'Jan 2026'},
        {'name': 'Mistral AI', 'valuation_billions': 14, 'last_round': '1.2B', 'last_round_date': 'Apr 2026'},
        {'name': 'Perplexity', 'valuation_billions': 9, 'last_round': '500M', 'last_round_date': 'Apr 2026'},
        {'name': 'Cohere', 'valuation_billions': 5.5, 'last_round': '450M', 'last_round_date': 'Apr 2026'},
        {'name': 'Poolside AI', 'valuation_billions': 3, 'last_round': '300M', 'last_round_date': 'Apr 2026'},
        {'name': 'Cognition', 'valuation_billions': 2, 'last_round': '175M', 'last_round_date': 'Apr 2026'},
        {'name': 'Sakana AI', 'valuation_billions': 1.8, 'last_round': '214M', 'last_round_date': 'Jan 2026'},
        {'name': 'Imbue', 'valuation_billions': 1.2, 'last_round': '200M', 'last_round_date': '2024'},
    ]

    # Comp 5: Arms race chart - quarterly funding by player ($B)
    d['arms_race'] = {
        'quarters': ['Q1 25', 'Q2 25', 'Q3 25', 'Q4 25', 'Q1 26', 'Q2 26*'],
        'players': [
            {'name': 'OpenAI', 'color': '#378ADD', 'data': [5, 3, 40, 0, 3, 1]},
            {'name': 'Anthropic', 'color': '#EF9F27', 'data': [0.5, 2, 0, 0, 3.5, 0]},
            {'name': 'xAI', 'color': '#E24B4A', 'data': [0, 4, 0, 0, 5, 6]},
            {'name': 'Mistral', 'color': '#7F77DD', 'data': [0, 0.5, 0, 0.5, 0, 1.2]},
            {'name': 'Cohere', 'color': '#1D9E75', 'data': [0, 0, 0, 0, 0, 0.45]},
        ],
    }

    # Comp 6: VC league table
    d['vc_league'] = [
        {'firm': 'Andreessen Horowitz', 'deals': 14, 'deployed': '2.1B', 'focus': 'Foundation models, infra'},
        {'firm': 'Sequoia Capital', 'deals': 11, 'deployed': '1.8B', 'focus': 'Agents, enterprise AI'},
        {'firm': 'Founders Fund', 'deals': 9, 'deployed': '1.4B', 'focus': 'Foundation, defense AI'},
        {'firm': 'Khosla Ventures', 'deals': 8, 'deployed': '0.9B', 'focus': 'AI health, robotics'},
        {'firm': 'Lightspeed Venture', 'deals': 7, 'deployed': '0.7B', 'focus': 'AI SaaS, developer tools'},
        {'firm': 'Google Ventures', 'deals': 7, 'deployed': '0.6B', 'focus': 'AI infra, multimodal'},
        {'firm': 'Coatue Management', 'deals': 6, 'deployed': '0.8B', 'focus': 'Gen AI, fintech-AI'},
        {'firm': 'Tiger Global', 'deals': 5, 'deployed': '0.5B', 'focus': 'AI productivity, B2B'},
    ]

    # Comp 7: Money flow analysis
    d['money_flow'] = [
        {'direction': 'up', 'text': 'Foundation model funding surged to $47.2B cumulative — OpenAI\'s $40B Series F alone represents more capital than the entire AI industry raised in all of 2022'},
        {'direction': 'down', 'text': 'Infrastructure and GPU cloud VC deals down 18% QoQ as hyperscaler capex crowds out venture-scale infrastructure plays — GPUs are a commodity bet now'},
        {'direction': 'up', 'text': 'European AI funding hit $2.1B this week — first time matching a US weekly total in 18 months, driven by Mistral\'s $1.2B and UK sovereign AI fund commitments'},
        {'direction': 'up', 'text': 'Fintech-AI deal count up 3x YoY as enterprise adoption inflects — 9 of 31 deals this week had payments, lending, or fraud as primary use case'},
        {'direction': 'up', 'text': 'Median Series B valuation now $340M vs $180M in Q1 2025 — valuation inflation is back, driven by competition among a16z, Sequoia, and Founders Fund for the same 20 deals'},
        {'direction': 'down', 'text': 'Chinese AI companies raising zero dollars in US-visible rounds for third consecutive quarter — geopolitical capital bifurcation is now structural, not temporary'},
    ]

    # Comp 8: M&A & exits tracker
    d['ma_tracker'] = [
        {'date': 'Apr 28', 'title': 'Microsoft acquires Inflection AI talent team', 'type': 'Acquisition', 'detail': '~40 researchers joining Copilot org · deal structure avoids HSR filing · est. $650M'},
        {'date': 'Apr 24', 'title': 'Google acquires CoreWeave data center leases', 'type': 'Acquisition', 'detail': '3 facilities, 12,000 H100 GPUs · $1.9B · expands TPU-alternative compute access'},
        {'date': 'Apr 20', 'title': 'Salesforce strategic investment in Cohere', 'type': 'Investment', 'detail': '$100M for preferred access to enterprise LLM API · part of $450M round'},
        {'date': 'Apr 15', 'title': 'Perplexity AI files confidential S-1', 'type': 'IPO filing', 'detail': 'IPO expected Q3 2026 · Goldman Sachs, Morgan Stanley leading · last val $9B'},
        {'date': 'Apr 10', 'title': 'Databricks acquires MosaicML integration assets', 'type': 'Acquisition', 'detail': 'Follow-on to 2023 acquisition · absorbing remaining open-source team · $45M'},
        {'date': 'Apr 5', 'title': 'Adobe strategic investment in Runway ML', 'type': 'Investment', 'detail': '$50M minority stake · video generation for Creative Cloud integration roadmap'},
    ]

    # Comp 9: Fintech & payments AI spotlight
    d['fintech_spotlight'] = [
        {
            'company': 'Stripe',
            'deal_type': 'Partnership',
            'tags': ['Agents/automation', 'Onboarding'],
            'description': 'Integrates Anthropic computer-use for autonomous merchant onboarding — end-to-end KYB without human review',
            'strategic': 'Threatens traditional KYB/KYC vendors (Jumio, Onfido). Card networks benefit from faster merchant activation; reduces fraud surface at onboarding stage. Mastercard\'s own identity verification products face direct competitive pressure.'
        },
        {
            'company': 'Mastercard (internal)',
            'deal_type': '$600M capex',
            'tags': ['Agents/automation', 'B2B payments'],
            'description': 'Pilots agent-driven B2B payments with three Fortune 100 partners — autonomous invoice-to-payment cycle',
            'strategic': 'Positive for Mastercard\'s B2B track positioning. Validates the agent-payments thesis. First-mover on autonomous B2B could lock in commercial card revenue before fintechs get there.'
        },
        {
            'company': 'Plaid + OpenAI',
            'deal_type': 'Partnership',
            'tags': ['Data infrastructure', 'Open banking'],
            'description': 'Real-time financial data API for ChatGPT Enterprise users — AI-native bank data access layer',
            'strategic': 'Plaid becomes the default financial data layer for AI agents. Long-term threat to banks\' data moats. Visa/MC benefit if agent-initiated transactions flow over card rails vs ACH/RTP alternatives.'
        },
        {
            'company': 'Ramp',
            'deal_type': '$150M',
            'tags': ['Fintech', 'Corporate cards'],
            'description': 'Series E extension — AI-powered spend intelligence and autonomous approval workflows',
            'strategic': 'Ramp\'s AI layer further differentiates corporate card from banks\' expense tools. Commercial issuers (Chase, Amex, Citi) need to accelerate their own AI spend management or lose corporate card share.'
        },
    ]

    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

    print(f'Injected Page 3 dummy data into {JSON_PATH}')
    print(f'Components populated: funding_summary, funding_rounds, private_ai, arms_race, vc_league, money_flow, ma_tracker, fintech_spotlight')


if __name__ == '__main__':
    main()
