"""
Inject dummy Page 4 (Research & papers) data into today's JSON for testing.
Run after inject_page3_data.py, then re-render the dashboard.
"""

import json
import random

JSON_PATH = 'output/daily-data/2026-05-02.json'


def main():
    with open(JSON_PATH, encoding='utf-8') as f:
        d = json.load(f)

    # Comp 1: Research summary metrics
    d['research_summary'] = {
        'papers_published': '1,847',
        'papers_change': '+214',
        'breakthroughs': 12,
        'breakthrough_note': 'Score 8.0+ · +4 vs avg',
        'top_institution': 'DeepMind',
        'top_institution_papers': 31,
        'hottest_topic': 'Reasoning',
        'hottest_topic_change': '+38%',
    }

    # Comp 2: Paper of the week
    d['paper_of_week'] = {
        'title': 'Scaling Reasoning with Reinforcement Learning: How Chain-of-Thought Emerges from Pure RL Without Supervision',
        'institution': 'DeepMind',
        'team': 'Gemma team',
        'arxiv_id': '2504.18841',
        'date': 'Apr 28, 2026',
        'score': 9.6,
        'tags': ['Reasoning', 'Reinforcement learning', 'Foundation models'],
        'plain_summary': 'Models trained purely with reinforcement learning — with no human-labeled chain-of-thought examples — spontaneously develop step-by-step reasoning. This suggests sophisticated reasoning is an emergent property of RL optimization, not something that needs to be explicitly taught.',
        'why_matters': 'This is the most significant reasoning paper since OpenAI\'s o1 release. It suggests the path to better reasoning doesn\'t require expensive human labeling pipelines — just more compute and better RL reward design. Every major lab will be replicating this within weeks. Could accelerate the reasoning arms race by 6-12 months.',
        'url': 'https://arxiv.org/abs/2504.18841',
    }

    # Comp 3: Top papers this week
    d['top_papers'] = [
        {
            'title': 'AgentBench-2026: A Comprehensive Benchmark for Real-World Agent Tasks',
            'authors': 'Chen et al.',
            'institution': 'Tsinghua / MIT',
            'tags': ['Agents', 'Benchmarks'],
            'score': 9.1,
            'summary': 'New benchmark covering 42 real-world agent tasks across coding, web, finance, and science. Current best models score 61% — significant headroom remains.',
            'url': 'https://arxiv.org/abs/2504.18901',
        },
        {
            'title': 'Constitutional AI at Scale: Alignment Without Human Feedback at 1T Parameters',
            'authors': 'Askell et al.',
            'institution': 'Anthropic',
            'tags': ['Safety', 'Foundation models'],
            'score': 9.0,
            'summary': 'Shows Constitutional AI methods scale to trillion-parameter models with no degradation in alignment quality — potentially making RLHF optional at large scale.',
            'url': 'https://arxiv.org/abs/2504.18876',
        },
        {
            'title': 'MoE at the Edge: Sparse Mixture-of-Experts for On-Device Inference',
            'authors': 'Apple ML Research · 12 authors',
            'institution': '',
            'tags': ['Efficiency', 'Infrastructure'],
            'score': 8.7,
            'summary': 'MoE architecture runs efficiently on mobile chips. 7B parameter model achieves GPT-3.5 quality at 40ms latency on iPhone 16. On-device AI becomes real.',
            'url': 'https://arxiv.org/abs/2504.18812',
        },
        {
            'title': 'Multimodal Financial Reasoning: LLMs as Analysts for Earnings Reports',
            'authors': 'FinAI Lab',
            'institution': 'Stanford GSB',
            'tags': ['Multimodal', 'Fintech'],
            'score': 8.5,
            'summary': 'LLMs analyzing earnings reports + charts outperform human analysts on forward revenue prediction by 12%. First robust evidence of LLM alpha in financial analysis.',
            'url': 'https://arxiv.org/abs/2504.18799',
        },
        {
            'title': 'Adversarial Robustness in Vision-Language Models: A Systematic Study',
            'authors': 'Szegedy et al.',
            'institution': 'Google DeepMind',
            'tags': ['Safety', 'Computer Vision'],
            'score': 8.3,
            'summary': 'VLMs are 3x more vulnerable to adversarial attacks than text-only models. New defense method cuts attack success rate from 78% to 9% with minimal performance cost.',
            'url': 'https://arxiv.org/abs/2504.18745',
        },
        {
            'title': 'Humanoid Locomotion via Whole-Body Diffusion Policy',
            'authors': 'Berkeley Robotics · 8 authors',
            'institution': '',
            'tags': ['Robotics', 'Agents'],
            'score': 8.2,
            'summary': 'Diffusion-based control policy enables humanoid robots to traverse unstructured outdoor terrain reliably. First policy that transfers from sim to real without fine-tuning.',
            'url': 'https://arxiv.org/abs/2504.18712',
        },
        {
            'title': 'Long-Context Compression: 1M Tokens at 1/10th the Compute',
            'authors': 'Gu et al.',
            'institution': 'CMU / Together AI',
            'tags': ['Efficiency', 'Infrastructure'],
            'score': 8.1,
            'summary': 'New attention approximation handles 1M token contexts using 90% less compute than standard attention. Makes long-context models economically viable at scale.',
            'url': 'https://arxiv.org/abs/2504.18689',
        },
    ]

    # Comp 4a: Research by category (this week vs last week)
    d['research_categories'] = {
        'labels': ['Reasoning', 'Agents', 'Safety', 'Multimodal', 'Efficiency', 'Computer Vision', 'Benchmarks', 'Robotics'],
        'this_week': [310, 240, 195, 175, 155, 130, 110, 95],
        'last_week': [225, 215, 180, 165, 140, 125, 105, 90],
    }

    # Comp 4b: 30-day research volume per category
    base_volumes = {
        'Reasoning': (35, 58, '#E24B4A'),
        'Agents': (25, 38, '#378ADD'),
        'Safety': (22, 32, '#7F77DD'),
        'Efficiency': (18, 27, '#1D9E75'),
    }
    days = 30
    labels = [f'{((4 if i < 30 else 5))}/{((i % 30) + 1)}' for i in range(days)]
    cats = []
    random.seed(7)
    for name, (lo, hi, color) in base_volumes.items():
        values = []
        v = lo
        for i in range(days):
            t = i / (days - 1)
            target = lo + (hi - lo) * t
            v = target + random.uniform(-1.5, 1.5)
            values.append(round(v, 1))
        cats.append({'name': name, 'color': color, 'values': values})
    d['research_volume'] = {'labels': labels, 'categories': cats}

    # Comp 5: Hot institutions
    d['hot_institutions'] = [
        {'name': 'Google DeepMind', 'papers': 31, 'rising': True, 'focus': 'Reasoning, safety, multimodal'},
        {'name': 'Anthropic', 'papers': 18, 'rising': True, 'focus': 'Alignment, constitutional AI'},
        {'name': 'MIT CSAIL', 'papers': 16, 'rising': False, 'focus': 'Agents, robotics, theory'},
        {'name': 'Stanford HAI', 'papers': 14, 'rising': True, 'focus': 'Multimodal, fintech AI'},
        {'name': 'UC Berkeley', 'papers': 13, 'rising': True, 'focus': 'Robotics, RL, agents'},
        {'name': 'CMU LTI', 'papers': 12, 'rising': False, 'focus': 'NLP, efficiency, compression'},
        {'name': 'Meta FAIR', 'papers': 11, 'rising': False, 'focus': 'Open models, computer vision'},
        {'name': 'Microsoft Research', 'papers': 10, 'rising': False, 'focus': 'Copilot research, agents'},
        {'name': 'Tsinghua THUNLP', 'papers': 9, 'rising': True, 'focus': 'Reasoning, multilingual'},
        {'name': 'OpenAI Research', 'papers': 8, 'rising': False, 'focus': 'RL, safety, evals'},
    ]

    # Comp 6: Author spotlight
    d['author_spotlight'] = [
        {
            'initials': 'IS',
            'name': 'Ilya Sutskever',
            'affiliation': 'Safe Superintelligence',
            'handle': '@ilyasut',
            'color': '#7F77DD',
            'paper_title': 'Emergent Goal Representations in Large-Scale RL Training',
            'note': 'First paper from SSI since founding. Suggests Sutskever\'s team is working on goal-specification as a core alignment primitive — a significant research direction signal.',
        },
        {
            'initials': 'OV',
            'name': 'Oriol Vinyals',
            'affiliation': 'Google DeepMind',
            'handle': '@OriolVinyals',
            'color': '#378ADD',
            'paper_title': 'Game-Theoretic Foundations of Multi-Agent Reasoning',
            'note': 'Bridges AlphaGo-era game theory research with modern LLM agent design. Practical implications for multi-agent systems and adversarial robustness.',
        },
        {
            'initials': 'CF',
            'name': 'Chelsea Finn',
            'affiliation': 'Stanford / Google',
            'handle': '@chelseabfinn',
            'color': '#1D9E75',
            'paper_title': 'Meta-Learning Generalizes Across Robot Morphologies Without Re-Training',
            'note': 'Robotics transfer learning breakthrough. One policy works across 12 different robot body types — massive implication for manufacturing deployment costs.',
        },
        {
            'initials': 'PL',
            'name': 'Percy Liang',
            'affiliation': 'Stanford CRFM',
            'handle': '@percyliang',
            'color': '#E24B4A',
            'paper_title': 'HELM-3: Holistic Evaluation of 140 Language Models',
            'note': 'The most comprehensive LLM benchmark update in two years. New dimensions include long-context fidelity, instruction refusal calibration, and agentic task completion.',
        },
    ]

    # Comp 7: Breakthrough radar (x = time-to-impact 0-10, y = significance 0-10)
    d['breakthrough_radar'] = [
        {'title': 'DeepMind RL reasoning paper', 'time_to_impact': 8.5, 'significance': 9.2, 'score': 9.6, 'quadrant': 'paradigm'},
        {'title': 'Constitutional AI at 1T scale', 'time_to_impact': 3.5, 'significance': 8.0, 'score': 9.0, 'quadrant': 'watch_closely'},
        {'title': 'Emergent goals (SSI)', 'time_to_impact': 2.5, 'significance': 7.5, 'score': 8.8, 'quadrant': 'watch_closely'},
        {'title': 'Apple MoE on-device', 'time_to_impact': 8.0, 'significance': 6.5, 'score': 8.7, 'quadrant': 'deploy_now'},
        {'title': 'AgentBench-2026', 'time_to_impact': 7.5, 'significance': 5.5, 'score': 9.1, 'quadrant': 'deploy_now'},
        {'title': 'Long-context compression', 'time_to_impact': 7.0, 'significance': 5.0, 'score': 8.1, 'quadrant': 'deploy_now'},
        {'title': 'Adversarial VLM robustness', 'time_to_impact': 6.0, 'significance': 4.5, 'score': 8.3, 'quadrant': 'incremental'},
        {'title': 'Humanoid locomotion', 'time_to_impact': 4.0, 'significance': 3.5, 'score': 8.2, 'quadrant': 'long_bet'},
        {'title': 'Financial multimodal', 'time_to_impact': 6.5, 'significance': 5.8, 'score': 8.5, 'quadrant': 'deploy_now'},
        {'title': 'Meta-learning robotics', 'time_to_impact': 5.5, 'significance': 6.5, 'score': 8.4, 'quadrant': 'incremental'},
    ]

    # Comp 8: Research signal analysis
    d['research_signals'] = [
        {'direction': 'up', 'text': 'Reasoning paper volume up 38% WoW — the DeepMind RL paper triggered a wave of follow-on submissions. Expect 20-30 replication and extension papers in the next 10 days'},
        {'direction': 'up', 'text': 'Safety research quietly accelerating — 188 papers this week vs 144 four weeks ago. Constitutional AI and interpretability are the dominant sub-themes, not just red-teaming'},
        {'direction': 'up', 'text': 'On-device AI is having a moment — Apple\'s MoE paper plus 6 other efficiency papers point to a coordinated push toward inference without cloud dependency'},
        {'direction': 'warning', 'text': 'Benchmark inflation concern — 12 new benchmarks published this week, 9 of which show the authors\' own model at #1. Community pushback building on arXiv comments'},
        {'direction': 'down', 'text': 'Purely theoretical ML papers down 22% — the field is in an applied phase. Foundational math contributions are being crowded out by engineering papers'},
        {'direction': 'up', 'text': 'Fintech AI research tripled YoY — fraud, credit, and AML papers now represent 8% of weekly arXiv CS.AI submissions, up from 2.6% in Q1 2025'},
    ]

    # Comp 9: Fintech & payments research corner
    d['fintech_research'] = [
        {
            'title': 'FraudRadar: Real-Time Transaction Anomaly Detection with Temporal Graph Neural Networks',
            'authors': 'Visa Research · 6 authors',
            'arxiv_id': '2504.14102',
            'tags': ['Fraud detection', 'Graph ML'],
            'score': 8.4,
            'summary': 'New GNN architecture detects card fraud 340ms faster than current FICO models with 23% fewer false positives. Tested on 2.1B real transactions.',
            'strategic': 'Direct threat to legacy fraud scoring vendors. Card networks running their own fraud models (Visa Advanced Authorization, Mastercard Decision Intelligence) should evaluate immediate integration. 23% false positive reduction translates to ~$180M annually in unnecessary decline friction for a network at Mastercard\'s scale.',
        },
        {
            'title': 'LLM-Powered AML: Narrative-Aware Suspicious Activity Report Generation',
            'authors': 'JPMorgan AI Research · FinCEN Lab',
            'arxiv_id': '2504.13987',
            'tags': ['AML', 'Regulatory AI'],
            'score': 8.1,
            'summary': 'LLMs generate SAR narratives 8x faster than compliance analysts with equivalent regulatory acceptance rates. Validated against 50,000 real SARs.',
            'strategic': 'Compliance cost reduction story for banks and payment processors. For acquirers processing high-risk merchant categories, automated SAR generation reduces BSA officer headcount needs. Mastercard\'s compliance-as-a-service offerings (RiskRecon, etc.) could integrate this.',
        },
        {
            'title': 'Neural Credit Scoring Beyond FICO: Causal AI for Thin-File Borrowers',
            'authors': 'MIT Media Lab · Experian Research',
            'arxiv_id': '2504.13845',
            'tags': ['Credit scoring', 'Causal AI'],
            'score': 7.9,
            'summary': 'Causal ML model extends credit to 40M previously unscorable US adults with lower default rates than FICO scores for traditional borrowers. Regulatory-explainable by design.',
            'strategic': 'Massive fintech opportunity — 40M thin-file adults represent $200B+ in untapped credit demand. Issuing banks and BNPL players that adopt this first gain addressable market expansion. Mastercard\'s identity and data assets could power a proprietary version of this scoring approach.',
        },
    ]

    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

    print(f'Injected Page 4 dummy data into {JSON_PATH}')
    print('Components populated: research_summary, paper_of_week, top_papers, research_categories, research_volume, hot_institutions, author_spotlight, breakthrough_radar, research_signals, fintech_research')


if __name__ == '__main__':
    main()
