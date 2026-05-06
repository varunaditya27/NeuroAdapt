"""
Synthetic learner archetype data generator for NeuroAdapt DDQN pre-training.

Generates 3 archetype datasets × N episodes of (state, action, reward,
next_state, done) replay tuples in JSON format, ready for train.py.

Archetypes are grounded in peer-reviewed behavioural research:

  adhd_hyperfocus:
    - Low mouse entropy + near-zero idle during hyperfocus [Kumar et al., IUI 2026]
    - Attention lapses follow ~12s oscillatory cycles, not random spikes
      [Castellanos et al., 2011, PMID 21596371]
    - Higher max acceleration / stopping distance during lapse states
      [Leontyev & Yamauchi, 2019, PLoS ONE, PMC6880625]

  dyslexia_reader:
    - Total reading time ~1.6x longer; fixation duration 30% above controls
      [arXiv:2510.24647; Rayner et al. via Hebbian Fixation study PMC10605338]
    - More frequent backward saccades → elevated stall + instability mid-read
      [ERIC systematic review, EJ1425898]
    - Consistent format preference: prefers audio/simplified text
      [AttentionGuard cross-validation, HYPERAKTIV dataset]

  neurotypical:
    - Low deviation from personal baseline across all signals
      [Kumar et al., IUI 2026 — top OULAD feature: click rate deviation 22%]
    - Stable, predictable trajectories; low pref_delta

Signal vector: [dwell, jitter, focus, stall, pref_delta], all in [0, 1]
  dwell       = Semantic Dwell Ratio (timeOnSlide / expected read time)
  jitter      = Interaction Jitter (rolling std-dev of mouse velocity)
  focus       = Focus Persistence (1 - tab_switch_rate)
  stall       = Stall Duration (normalised idle time)
  pref_delta  = Preference Delta (format preference shift magnitude)

Usage:
  python quantum/mock_data.py                      # defaults: 500 eps, 20 steps
  python quantum/mock_data.py --episodes 300 --steps 20 --out quantum/data
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import sys

# ---------------------------------------------------------------------------
# Path bootstrap — works whether run from repo root or quantum/ directory
# ---------------------------------------------------------------------------
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from shared_config import N_ACTIONS, ACTION_NAMES, STATE_VECTOR_DIM

# Import the oracle from train.py — MUST be identical to what the trainer uses.
# If the import fails (e.g. PennyLane not installed in this env), we inline a
# copy of the function with an explicit warning so generation still works.
try:
    from quantum.train import heuristic_action
except Exception:
    import warnings
    warnings.warn(
        "Could not import heuristic_action from quantum.train — "
        "using inline fallback. Ensure this matches train.py exactly.",
        stacklevel=2,
    )

    def heuristic_action(state: list[float]) -> int:  # type: ignore[misc]
        dwell, jitter, focus, stall, pref_delta = state
        if max(stall, jitter) > 0.75:
            return 5  # Sensory Break
        if dwell > 0.70:
            return 2  # Simplify Text
        if pref_delta > 0.70:
            return 3  # Switch to Video
        if stall > 0.55:
            return 4  # Inject Gamified Task
        if focus < 0.25:
            return 1  # Soft Nudge
        return 0       # Hold Course


# ---------------------------------------------------------------------------
# Reward weights — mirrors reward_weights.yaml exactly
# ---------------------------------------------------------------------------
REWARD_WEIGHTS: dict[str, float] = {
    "complete":        1.0,
    "answer_correct":  0.5,
    "format_choice":   0.2,
    "energy_bar":     -5.0,
    "stability_bonus": 0.7,
    "tab_switch":     -1.0,
    "overload":       -2.0,
}

# ---------------------------------------------------------------------------
# Archetype definitions
# ---------------------------------------------------------------------------
# Each archetype has:
#   base_profile   : list of (mean, std) per signal for the "resting" state
#   lapse_profile  : list of (mean, std) per signal during an attention lapse
#   lapse_cycle_s  : seconds between lapse peaks (oscillatory, not random)
#   lapse_duration : how many 30s ticks a lapse persists
#   done_prob      : per-step probability that the episode ends (lesson complete)
#   quiz_correct_p : probability of correct quiz answer (shapes reward)
#
# Signal order: [dwell, jitter, focus, stall, pref_delta]

@dataclass
class ArchetypeConfig:
    name: str
    base_profile: list[tuple[float, float]]
    lapse_profile: list[tuple[float, float]]
    # Oscillatory lapse cycle in number of 30-second steps
    # ADHD: ~12s-period oscillation → every ~0.4 steps; we model macro-cycles
    # of ~4 steps (≈ 2 min) based on the sustained-attention literature
    lapse_period_steps: float
    lapse_duration_steps: int
    done_prob: float
    quiz_correct_p: float
    # Momentum controls temporal autocorrelation (higher = smoother signal)
    momentum: float


ARCHETYPES: dict[str, ArchetypeConfig] = {

    # ------------------------------------------------------------------
    # ADHD Hyperfocus
    # Hyperfocus state: near-zero idle, low entropy mouse movement,
    # high sustained dwell. [Kumar et al., IUI 2026; ADD.org clinical desc.]
    # Lapse state: sudden high jitter (max acceleration spike per Leontyev
    # & Yamauchi 2019), stall elevation, focus drops.
    # Lapse rhythm: ~12s micro-oscillation maps to ~1 lapse per 4-step macro
    # window in our 30s-tick resolution. [Castellanos et al., 2011]
    # ------------------------------------------------------------------
    "adhd_hyperfocus": ArchetypeConfig(
        name="adhd_hyperfocus",
        base_profile=[
            (0.78, 0.08),  # dwell      — high: locked in, time-blind [ADD.org]
            (0.18, 0.10),  # jitter     — low in focus state [Leontyev 2019]
            (0.82, 0.08),  # focus      — rarely tabs away during hyperfocus
            (0.02, 0.08),  # stall      — near-zero idle [Kumar IUI 2026]
            (0.42, 0.12),  # pref_delta — moderate; format curiosity shifts
        ],
        lapse_profile=[
            (0.55, 0.12),  # dwell      — drops as attention crashes
            (0.82, 0.10),  # jitter     — high acceleration spike [Leontyev 2019]
            (0.28, 0.14),  # focus      — starts tab-switching
            (0.78, 0.10),  # stall      — freezes after spike
            (0.72, 0.12),  # pref_delta — strong format shift signal
        ],
        lapse_period_steps=4.0,   # ~1 lapse per 4 steps ≈ 2-minute macro cycle
        lapse_duration_steps=2,   # lapse lasts ~2 steps (1 minute)
        done_prob=0.85 / 20,      # high lesson completion when not lapsing
        quiz_correct_p=0.72,      # good comprehension when focused
        momentum=0.25,            # moderate: some volatility between states
    ),

    # ------------------------------------------------------------------
    # Dyslexia Slow-Reader
    # Reading time ~1.6× longer → very high persistent dwell.
    # [arXiv:2510.24647; PMC10605338]
    # Fixation duration 30% above controls → elevated stall throughout.
    # Frequent backward saccades → periodic focus dips (rereading).
    # [EJ1425898 systematic review]
    # Stable format preference: strongly prefers simplified/audio.
    # ------------------------------------------------------------------
    "dyslexia_reader": ArchetypeConfig(
        name="dyslexia_reader",
        base_profile=[
            (0.65, 0.15),  # dwell  — moderate-high with wide spread; re-reads cause oscillation [PMC5147795]
            (0.28, 0.10),  # jitter — unchanged
            (0.50, 0.12),  # focus  — slightly lower; regressive saccades = periodic focus drops [PMC5147795]
            (0.85, 0.10),  # stall  — PRIMARY dyslexia signal; fixation duration 30-50% longer [Frontiers 2026]
            (0.28, 0.08),  # pref_delta — unchanged
        ],
        lapse_profile=[
            (0.90, 0.06),  # dwell      — even higher: completely stuck on word
            (0.52, 0.12),  # jitter     — frustrated movement, higher variance
            (0.02, 0.04),  # focus — full regression: near-zero attention on current line [PMC5147795]
            (0.82, 0.08),  # stall      — frozen mid-sentence
            (0.92, 0.06),  # pref_delta — strong shift to audio/simplified when stuck
        ],
        lapse_period_steps=5.0,   # regression lapses every ~5 steps (2.5 min)
        lapse_duration_steps=2,
        done_prob=0.70 / 20,      # lower completion rate per step
        quiz_correct_p=0.55,      # comprehension reduced by decoding load
        momentum=0.25,            # high: gradual drift, less volatile than ADHD
    ),

    # ------------------------------------------------------------------
    # Neurotypical Control
    # Low deviation from personal baseline — top discriminating feature
    # in AttentionGuard OULAD validation (click rate deviation: 22% importance).
    # [Kumar et al., IUI 2026]
    # Stable, predictable trajectories with low pref_delta.
    # ------------------------------------------------------------------
    "neurotypical": ArchetypeConfig(
        name="neurotypical",
        base_profile=[
            (0.48, 0.10),  # dwell      — moderate; reads at expected pace
            (0.33, 0.12),  # jitter     — moderate; purposeful movement
            (0.70, 0.08),  # focus      — good; occasional brief switches
            (0.28, 0.10),  # stall      — low; consistent interaction
            (0.22, 0.08),  # pref_delta — stable; format preferences don't shift
        ],
        lapse_profile=[
            (0.55, 0.10),  # dwell   — slight uptick
            (0.78, 0.10),  # jitter  — crosses >0.75 occasionally during lapse [Kumar IUI 2026]
            (0.02, 0.04),  # focus — full tab-switch; needs 2 lapse steps to reach <0.25
            (0.68, 0.08),  # stall   — crosses >0.55 during lapse → triggers action 4
            (0.92, 0.06),  # pref_delta — needs 3 lapse steps to cross 0.70 [simulated]
        ],
        lapse_period_steps=7.0,   # ~3 lapses per 20-step episode [naturalistic attention lit]
        lapse_duration_steps=3,
        done_prob=0.90 / 20,
        quiz_correct_p=0.82,
        momentum=0.25,
    ),
}


# ---------------------------------------------------------------------------
# State evolution
# ---------------------------------------------------------------------------

def _clip(v: float) -> float:
    return max(0.0, min(1.0, v))


def _sample_from_profile(
    profile: list[tuple[float, float]],
    rng: random.Random,
) -> list[float]:
    """Sample a state vector from Gaussian profile, clipped to [0, 1]."""
    return [_clip(rng.gauss(mu, sigma + 0.05)) for mu, sigma in profile]


def _evolve_state(
    current: list[float],
    target_profile: list[tuple[float, float]],
    rng: random.Random,
    momentum: float,
) -> list[float]:
    """
    Temporal momentum model: each signal is a weighted blend of the current
    value and a fresh sample from the target profile, plus micro-noise.

    This produces autocorrelated time-series that resemble real behavioural
    signals — gradual drift rather than white noise.

    new_i = momentum * current_i + (1 - momentum) * fresh_i + ε
    where ε ~ Uniform(-0.02, 0.02)
    """
    fresh = _sample_from_profile(target_profile, rng)
    return [
        _clip(momentum * c + (1.0 - momentum) * f + rng.uniform(-0.04, 0.04))
        for c, f in zip(current, fresh)
    ]


def _is_in_lapse(step: int, cfg: ArchetypeConfig) -> bool:
    """
    Deterministic oscillatory lapse schedule based on step index.
    Models the ~12s attention oscillation documented in ADHD literature
    (Castellanos et al., 2011) at 30s-tick resolution.

    A lapse begins at steps: lapse_period, 2*lapse_period, ...
    and lasts lapse_duration_steps ticks.
    """
    period = cfg.lapse_period_steps
    if period <= 0:
        return False
    phase = step % period
    return phase < cfg.lapse_duration_steps


# ---------------------------------------------------------------------------
# Signal-based reward
# Implements the semantics from reward_weights.yaml.
# This is the real reward function the live system will use (via reward.py).
# Different from train.py's distance-based proxy which exists only for
# training stability during synthetic pre-training.
# ---------------------------------------------------------------------------

def compute_signal_reward(
    state: list[float],
    action: int,
    next_state: list[float],
    done: bool,
    rng: random.Random,
    quiz_correct_p: float,
) -> float:
    dwell, jitter, focus, stall, pref_delta = state
    _, next_jitter, _, next_stall, _ = next_state

    reward = 0.0

    # Lesson complete
    if done:
        reward += REWARD_WEIGHTS["complete"]
    else:
        reward -= 0.05

    # Overload: high stall AND high jitter simultaneously
    # Corresponds to ADHD paralysis state (Neuroperforma, 2026)
    if stall > 0.70 and jitter > 0.70:
        reward += REWARD_WEIGHTS["overload"]

    # Tab switching: low focus
    if focus < 0.10:
        reward += REWARD_WEIGHTS["tab_switch"]

    # Stability bonus: intervention worked — signals calming down
    # next_state both less stressed than current
    if next_stall < stall - 0.10 and next_jitter < jitter - 0.10:
        reward += REWARD_WEIGHTS["stability_bonus"]

    # Energy Bar: break forced by learner under severe overload
    # Penalise only when the learner was genuinely overloaded (stall + jitter high)
    # — distinguishes "learner needed a break" from "policy chose break correctly"
    if action == 5 and stall > 0.75 and jitter > 0.75 and focus >= 0.25:
        reward += REWARD_WEIGHTS["energy_bar"]

    # Format preference match
    # High pref_delta (>0.65) means the learner wants a format change.
    # Action 2 (simplify) or 3 (video) honours that.
    if pref_delta > 0.65 and action in (2, 3):
        reward += REWARD_WEIGHTS["format_choice"]

    # Quiz correct answer
    # Action 4 (quiz) with low stall → learner was engaged enough to answer.
    # Probability reflects archetype-specific comprehension level.
    if action == 4 and stall < 0.40:
        if rng.random() < quiz_correct_p:
            reward += REWARD_WEIGHTS["answer_correct"]

    return round(reward, 4)


# ---------------------------------------------------------------------------
# Episode generator
# ---------------------------------------------------------------------------

def generate_episode(
    cfg: ArchetypeConfig,
    steps: int,
    rng: random.Random,
) -> list[dict]:
    """
    Generate one episode of replay transitions.

    Lapse schedule is deterministic (oscillatory) so that the DDQN sees
    predictable within-archetype patterns — matching the clinical literature
    on ADHD attention cycles — rather than purely stochastic noise.
    """
    state = _sample_from_profile(cfg.base_profile, rng)
    transitions: list[dict] = []

    for step in range(steps):
        in_lapse = _is_in_lapse(step, cfg)
        active_profile = cfg.lapse_profile if in_lapse else cfg.base_profile

        next_state = _evolve_state(state, active_profile, rng, cfg.momentum)

        if rng.random() < 0.15:
            action = rng.randint(0, N_ACTIONS - 1)
        else:
            action = heuristic_action(state)

        is_last = (step == steps - 1)
        done = is_last or (rng.random() < cfg.done_prob)

        reward = compute_signal_reward(
            state, action, next_state, done, rng, cfg.quiz_correct_p
        )

        transitions.append({
            "state":      [round(v, 4) for v in state],
            "action":     action,
            "reward":     reward,
            "next_state": [round(v, 4) for v in next_state],
            "done":       done,
        })

        if done:
            break

        state = next_state

    return transitions


# ---------------------------------------------------------------------------
# Dataset generator
# ---------------------------------------------------------------------------

def generate_dataset(
    episodes: int,
    steps_per_episode: int,
    seed: int,
    out_dir: Path,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    output_paths: dict[str, Path] = {}

    for key, cfg in ARCHETYPES.items():
        rng = random.Random(seed)
        all_episodes: list[list[dict]] = []

        for _ in range(episodes):
            transitions = generate_episode(cfg, steps_per_episode, rng)
            all_episodes.append(transitions)

        flat = [t for ep in all_episodes for t in ep]

        total_reward   = round(sum(t["reward"] for t in flat), 2)
        action_counts  = {i: 0 for i in range(N_ACTIONS)}
        done_count     = sum(1 for t in flat if t["done"])
        for t in flat:
            action_counts[t["action"]] += 1

        payload = {
            "archetype":           key,
            "references": [
                "Kumar et al. (IUI 2026) — AttentionGuard: behavioral signal detection",
                "Leontyev & Yamauchi (PLoS ONE 2019, PMC6880625) — ADHD mouse movement",
                "Castellanos et al. (2011, PMC3102245) — ADHD attention oscillation ~12s",
                "arXiv:2510.24647 — dyslexic reading time 1.6x; fixation +30%",
                "ERIC EJ1425898 — dyslexia backward saccades / regression frequency",
            ],
            "generation_config": {
                "episodes":          episodes,
                "steps_per_episode": steps_per_episode,
                "seed":              seed,
                "lapse_period_steps": cfg.lapse_period_steps,
                "lapse_duration_steps": cfg.lapse_duration_steps,
                "momentum":          cfg.momentum,
            },
            "statistics": {
                "total_transitions": len(flat),
                "episodes_done": done_count,
                "total_reward": total_reward,
                "mean_reward": round(total_reward / len(flat), 4),
                "action_distribution": {
                    ACTION_NAMES[a]: c
                    for a, c in sorted(action_counts.items())
                },
            },
            "state_fields":  ["dwell", "jitter", "focus", "stall", "pref_delta"],
            "transitions":   flat,
        }

        out_path = out_dir / f"{key}_2.json"
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        output_paths[key] = out_path

        action_str = "  ".join(
            f"a{a}={c}" for a, c in sorted(action_counts.items())
        )
        print(
            f"[mock_data] {key:22s} | "
            f"{episodes} eps | "
            f"{len(flat):5d} transitions | "
            f"reward {total_reward:+8.2f} | "
            f"done {done_count:4d} | "
            f"{action_str}"
        )
        print(f"            → {out_path}")

    return output_paths


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="NeuroAdapt synthetic learner data generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--episodes", type=int,  default=500,           help="Episodes per archetype")
    p.add_argument("--steps",    type=int,  default=20,            help="Max steps per episode")
    p.add_argument("--seed",     type=int,  default=42,            help="Random seed (reproducible)")
    p.add_argument("--out",      type=str,  default="quantum/data",help="Output directory")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out)

    print(f"\n[mock_data] Generating synthetic pre-training data")
    print(f"            episodes={args.episodes}  steps={args.steps}  seed={args.seed}")
    print(f"            output → {out_dir}\n")

    paths = generate_dataset(
        episodes=args.episodes,
        steps_per_episode=args.steps,
        seed=args.seed,
        out_dir=out_dir,
    )

    print(f"\n[mock_data] Complete. {len(paths)} archetype files written.\n")


if __name__ == "__main__":
    main()