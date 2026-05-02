"""
Fix breakthrough radar data so that:
- time_to_impact: LOW = near-term, HIGH = long-term (matches new x-axis)
- significance: LOW = incremental, HIGH = paradigm shift
- Each item placed in its correct quadrant
"""

import json

JSON_PATH = 'output/daily-data/2026-05-02.json'

# New data with corrected semantics (low x = near, high x = long)
fixed_data = [
    # Deploy Now (near-term, high significance) — LEFT TOP
    {'title': 'AgentBench-2026', 'time_to_impact': 1.5, 'significance': 6.5, 'score': 9.1, 'quadrant': 'deploy_now'},
    {'title': 'Apple MoE on-device', 'time_to_impact': 2.0, 'significance': 7.0, 'score': 8.7, 'quadrant': 'deploy_now'},
    {'title': 'Long-context compression', 'time_to_impact': 3.0, 'significance': 5.5, 'score': 8.1, 'quadrant': 'deploy_now'},
    {'title': 'Financial multimodal', 'time_to_impact': 3.5, 'significance': 6.5, 'score': 8.5, 'quadrant': 'deploy_now'},

    # Watch Closely (long-term, high significance / paradigm shift) — RIGHT TOP
    {'title': 'DeepMind RL reasoning paper', 'time_to_impact': 8.5, 'significance': 9.2, 'score': 9.6, 'quadrant': 'paradigm'},
    {'title': 'Constitutional AI at 1T scale', 'time_to_impact': 7.0, 'significance': 8.5, 'score': 9.0, 'quadrant': 'watch_closely'},
    {'title': 'Emergent goals (SSI)', 'time_to_impact': 7.5, 'significance': 7.8, 'score': 8.8, 'quadrant': 'watch_closely'},

    # Incremental Gains (near-term, smaller scope) — LEFT BOTTOM
    {'title': 'Adversarial VLM robustness', 'time_to_impact': 2.5, 'significance': 3.5, 'score': 8.3, 'quadrant': 'incremental'},
    {'title': 'Meta-learning robotics', 'time_to_impact': 3.5, 'significance': 4.0, 'score': 8.4, 'quadrant': 'incremental'},

    # Long Bet (long-term, uncertain — mid-low significance) — RIGHT BOTTOM
    {'title': 'Humanoid locomotion', 'time_to_impact': 7.5, 'significance': 4.0, 'score': 8.2, 'quadrant': 'long_bet'},
]


def main():
    with open(JSON_PATH, encoding='utf-8') as f:
        d = json.load(f)
    d['breakthrough_radar'] = fixed_data
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    print(f'Fixed breakthrough_radar data in {JSON_PATH}')
    print(f'Items: {len(fixed_data)} (4 deploy-now, 3 watch-closely, 2 incremental, 1 long-bet)')


if __name__ == '__main__':
    main()
