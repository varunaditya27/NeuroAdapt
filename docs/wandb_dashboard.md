# W&B Dashboard Setup

## Recommended Projects

- neuroadapt-ddqn (main training runs)
- neuroadapt-ablation-a (signal importance)
- neuroadapt-ablation-b (action space reduction)
- neuroadapt-ablation-c (quantum vs classical)

## Core Panels

1) Preference Delta vs Episode
- Line chart of pref_delta
- Add mean line and per-seed runs if available

2) Episode Reward vs Episode
- Line chart of episode_reward
- Add smoothing window 20

3) Action Distribution
- Histogram or bar chart of action counts
- Use policy_action_entropy as a secondary trend line

4) Confidence Distribution
- Histogram of confidence values (if logged)

5) Quantum Diagnostics
- Line chart of quantum_grad_norm
- Optional: loss and learning rate on secondary axis

## Suggested Run Tags

- model: quantum | classical
- dataset: synthetic | real
- ablation: A | B | C
- seed: integer

## Logging Notes

- Main training supports `--wandb` and `--wandb-project` in train.py.
- Ablation A/B scripts do not log to W&B by default. To log runs:
  - run train.py directly with `--wandb`, or
  - set `enable_wandb=True` in the ablation scripts before the run.

## Export Targets

- Export ablation plots to research/ablation_results/ for report inclusion.
- Store W&B run links in report notes for quick retrieval.
