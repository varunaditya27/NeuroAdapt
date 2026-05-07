"""
Online fine-tuning of a pre-trained NeuroAdapt DDQN policy.

Loads a checkpoint produced by train.py and runs additional training episodes
using *live* (or mock) learner transitions.  Key differences from train.py:

* Uses the signal-based reward from reward.py (not the proxy exp-distance).
* Much lower initial epsilon (agent is already partially trained).
* Smaller learning rate by default (fine-tuning, not cold-start).
* Supports loading a checkpoint from a path or defaulting to
  ``quantum/checkpoints/latest.pt``.
* Writes a new checkpoint to ``quantum/checkpoints/retrained_latest.pt``
  (configurable via --checkpoint-out).

Usage
-----
    python -m quantum.retrain --model classical --episodes 100
    python -m quantum.retrain --checkpoint quantum/checkpoints/policy_ep_300.pt
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Optional

import torch
from torch import optim

# ---------------------------------------------------------------------------
# Path bootstrap — works whether run as ``python quantum/retrain.py`` or
# ``python -m quantum.retrain`` from repo root.
# ---------------------------------------------------------------------------
if __package__ is None or __package__ == "":
    import sys
    _repo_root = Path(__file__).resolve().parents[1]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))

try:
    from quantum.pennylane_vqc import ClassicalDDQN, QuantumDDQN
    from quantum.reward import compute_reward, reload_weights
except ModuleNotFoundError:
    from pennylane_vqc import ClassicalDDQN, QuantumDDQN
    from reward import compute_reward, reload_weights

from backend.shared_config import (
    BATCH_SIZE,
    REPLAY_CAPACITY,
    TAU,
)
from quantum.train import (  # type: ignore[import]
    ReplayBuffer,
    TrainingResult,
    load_dataset_transitions,
    soft_update,
    train_step,
    evaluate_policy_pref_delta,
    evaluate_policy_action_entropy,
)

# ---------------------------------------------------------------------------
# Retrain-specific defaults
# ---------------------------------------------------------------------------
DEFAULT_EPSILON_START = 0.15   # already-trained agent; mostly greedy
DEFAULT_EPSILON_END   = 0.02
DEFAULT_EPSILON_DECAY = 80     # episodes over which epsilon decays
DEFAULT_LR            = 1e-4   # lower than cold-start
DEFAULT_EPISODES      = 100
DEFAULT_STEPS         = 20
DEFAULT_CHECKPOINT_IN  = "quantum/checkpoints/latest.pt"
DEFAULT_CHECKPOINT_OUT = "quantum/checkpoints/retrained_latest.pt"
DEFAULT_DATA_DIR       = "quantum/data"
MIN_REPLAY_FOR_TRAIN   = 256   # smaller than cold-start; buffer pre-filled


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_model(model_type: str) -> torch.nn.Module:
    if model_type == "quantum":
        return QuantumDDQN()
    if model_type == "classical":
        return ClassicalDDQN()
    raise ValueError(f"Unsupported model_type: {model_type!r}")


def _load_checkpoint(model: torch.nn.Module, checkpoint_path: Path) -> None:
    if not checkpoint_path.exists():
        raise FileNotFoundError(
            f"Checkpoint not found: {checkpoint_path}. "
            "Run train.py first or supply --checkpoint."
        )
    state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)


def _make_optimiser(model_type: str, model: torch.nn.Module, lr: float) -> optim.Optimizer:
    if model_type == "quantum":
        return optim.Adam(
            [
                {"params": model.quantum_layer.parameters(), "lr": lr * 5.0},
                {"params": model.bn.parameters(),        "lr": lr},
                {"params": model.advantage.parameters(), "lr": lr},
                {"params": model.value.parameters(),     "lr": lr},
            ]
        )
    return optim.Adam(model.parameters(), lr=lr)


# ---------------------------------------------------------------------------
# Core retrain loop
# ---------------------------------------------------------------------------

def run_retrain(
    *,
    episodes: int = DEFAULT_EPISODES,
    steps_per_episode: int = DEFAULT_STEPS,
    model_type: str = "classical",
    learning_rate: float = DEFAULT_LR,
    checkpoint_in: str = DEFAULT_CHECKPOINT_IN,
    checkpoint_out: str = DEFAULT_CHECKPOINT_OUT,
    data_dir: str = DEFAULT_DATA_DIR,
    epsilon_start: float = DEFAULT_EPSILON_START,
    epsilon_end: float = DEFAULT_EPSILON_END,
    epsilon_decay_episodes: int = DEFAULT_EPSILON_DECAY,
    seed: Optional[int] = None,
    reward_weights_path: Optional[str] = None,
    enable_wandb: bool = False,
    wandb_project: str = "neuroadapt-retrain",
) -> TrainingResult:
    """
    Fine-tune an existing checkpoint.

    Returns a TrainingResult with per-episode reward and preference-delta lists
    so callers (and tests) can introspect training dynamics.
    """
    # ── Reproducibility ─────────────────────────────────────────────────────
    if seed is not None:
        random.seed(seed)
        torch.manual_seed(seed)
    rng = random.Random(seed or 0)

    # ── Reward weights ───────────────────────────────────────────────────────
    if reward_weights_path is not None:
        reload_weights(Path(reward_weights_path))

    # ── Dataset ─────────────────────────────────────────────────────────────
    dataset_transitions = list(load_dataset_transitions(data_dir))  # Copy to avoid mutating fixture
    rng.shuffle(dataset_transitions)

    # ── Models ───────────────────────────────────────────────────────────────
    online_net = _build_model(model_type)
    target_net = _build_model(model_type)

    _load_checkpoint(online_net, Path(checkpoint_in))
    target_net.load_state_dict(online_net.state_dict())

    optimiser = _make_optimiser(model_type, online_net, learning_rate)

    # ── Replay buffer — pre-fill with dataset ────────────────────────────────
    replay = ReplayBuffer(capacity=REPLAY_CAPACITY)
    for trans in dataset_transitions[:min(len(dataset_transitions), REPLAY_CAPACITY // 2)]:
        replay.push(*trans)

    # ── Eval set (fixed) ─────────────────────────────────────────────────────
    eval_rng  = random.Random((seed or 0) + 42)
    eval_size = min(512, len(dataset_transitions))
    eval_transitions = eval_rng.sample(dataset_transitions, k=eval_size)

    # ── W&B (optional) ───────────────────────────────────────────────────────
    wandb = None
    if enable_wandb:
        try:
            import wandb as wb
            wb.init(project=wandb_project, config={"model_type": model_type, "episodes": episodes})
            wandb = wb
        except Exception:
            pass

    # ── Output directory ─────────────────────────────────────────────────────
    out_path = Path(checkpoint_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Training loop ─────────────────────────────────────────────────────────
    episode_rewards:      list[float] = []
    pref_delta_history:   list[float] = []
    loss_history:         list[float] = []
    decay_eps = max(1, epsilon_decay_episodes)

    for episode in range(1, episodes + 1):
        episode_reward = 0.0
        losses: list[float] = []

        epsilon = max(
            epsilon_end,
            epsilon_start - (episode - 1) / decay_eps * (epsilon_start - epsilon_end),
        )

        for _ in range(steps_per_episode):
            state, action, _dataset_reward, next_state, done = rng.choice(dataset_transitions)

            # ── Live reward from signal-based function ────────────────────────
            reward = compute_reward(
                state, action, next_state, done,
                rng=rng,
                quiz_correct_p=0.6,
            )

            replay.push(state, action, reward, next_state, done)

            if len(replay) >= MIN_REPLAY_FOR_TRAIN:
                batch = replay.sample(BATCH_SIZE)
                loss, _ = train_step(batch, online_net, target_net, optimiser)
                losses.append(loss)
                soft_update(online_net, target_net, tau=TAU)

            episode_reward += reward

        mean_loss = sum(losses) / len(losses) if losses else 0.0
        mean_pref_delta = evaluate_policy_pref_delta(online_net, eval_transitions, sample_count=32)
        action_entropy  = evaluate_policy_action_entropy(online_net, eval_transitions, sample_count=64)

        episode_rewards.append(episode_reward)
        pref_delta_history.append(mean_pref_delta)
        loss_history.append(mean_loss)

        if wandb is not None:
            wandb.log({
                "episode":        episode,
                "episode_reward": episode_reward,
                "epsilon":        epsilon,
                "loss":           mean_loss,
                "pref_delta":     mean_pref_delta,
                "action_entropy": action_entropy,
            })

    # ── Persist checkpoint ────────────────────────────────────────────────────
    torch.save(online_net.state_dict(), out_path)

    # ── Write history JSON (mirrors train.py convention) ────────────────────
    history_path = out_path.with_suffix(".history.json")
    history_path.write_text(
        json.dumps(
            {
                "episode_rewards":    episode_rewards,
                "pref_delta_history": pref_delta_history,
                "loss_history":       loss_history,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if wandb is not None:
        wandb.finish()

    return TrainingResult(
        episode_rewards=episode_rewards,
        preference_delta_history=pref_delta_history,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fine-tune a pre-trained NeuroAdapt DDQN checkpoint",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--episodes",       type=int,   default=DEFAULT_EPISODES)
    p.add_argument("--steps",          type=int,   default=DEFAULT_STEPS)
    p.add_argument("--model",          choices=["quantum", "classical"], default="classical")
    p.add_argument("--learning-rate",  type=float, default=DEFAULT_LR)
    p.add_argument("--checkpoint",     type=str,   default=DEFAULT_CHECKPOINT_IN,
                   dest="checkpoint_in")
    p.add_argument("--checkpoint-out", type=str,   default=DEFAULT_CHECKPOINT_OUT)
    p.add_argument("--data-dir",       type=str,   default=DEFAULT_DATA_DIR)
    p.add_argument("--epsilon-start",  type=float, default=DEFAULT_EPSILON_START)
    p.add_argument("--epsilon-end",    type=float, default=DEFAULT_EPSILON_END)
    p.add_argument("--epsilon-decay",  type=int,   default=DEFAULT_EPSILON_DECAY,
                   dest="epsilon_decay_episodes")
    p.add_argument("--seed",           type=int,   default=42)
    p.add_argument("--reward-weights", type=str,   default=None,
                   dest="reward_weights_path",
                   help="Path to a custom reward_weights.yaml")
    p.add_argument("--wandb",          action="store_true")
    p.add_argument("--wandb-project",  type=str,   default="neuroadapt-retrain")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    result = run_retrain(
        episodes=args.episodes,
        steps_per_episode=args.steps,
        model_type=args.model,
        learning_rate=args.learning_rate,
        checkpoint_in=args.checkpoint_in,
        checkpoint_out=args.checkpoint_out,
        data_dir=args.data_dir,
        epsilon_start=args.epsilon_start,
        epsilon_end=args.epsilon_end,
        epsilon_decay_episodes=args.epsilon_decay_episodes,
        seed=args.seed,
        reward_weights_path=args.reward_weights_path,
        enable_wandb=args.wandb,
        wandb_project=args.wandb_project,
    )
    final_reward = result.episode_rewards[-1] if result.episode_rewards else 0.0
    final_delta  = result.preference_delta_history[-1] if result.preference_delta_history else 0.0
    print(f"[retrain] Done. final_reward={final_reward:.4f}  pref_delta={final_delta:.4f}")


if __name__ == "__main__":
    main()
