"""
NeuroAdapt signal-based reward function.

Loads weights from reward_weights.yaml and exposes a single public entry
point: compute_reward(state, action, next_state, done, *, rng, quiz_correct_p).

Design contract
---------------
* Weights are loaded once at import time from the YAML that lives alongside
  this file (``quantum/reward_weights.yaml``).  All keys are accessed through
  the module-level WEIGHTS dict so the test suite can monkey-patch individual
  values without touching the file system.
* The function is pure-ish: the only source of randomness is the caller-
  supplied ``rng`` (a ``random.Random`` instance), making it fully
  deterministic in tests when you pass ``random.Random(seed)``.
* Key names in the YAML match the reward_weights-4.yaml exactly:
      complete, answer_correct, format_choice,
      energy_bar, stability_bonus, tab_switch_penalty, overload_penalty
"""

from __future__ import annotations

import random
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Weight loading
# ---------------------------------------------------------------------------

_YAML_CANDIDATES = [
    Path(__file__).with_name("reward_weights.yaml"),
    Path(__file__).with_name("configs") / "reward_weights.yaml",
]


def _resolve_yaml_path(path: Path | None = None) -> Path:
    """Return the first existing reward weight YAML path.

    The repository has used both `quantum/reward_weights.yaml` and
    `quantum/configs/reward_weights.yaml` across different stages. We keep the
    module import-safe by accepting either layout, while still preserving a
    concrete path for tests to monkey-patch.
    """
    if path is not None:
        return path

    for candidate in _YAML_CANDIDATES:
        if candidate.exists():
            return candidate

    return _YAML_CANDIDATES[0]

# Allow tests / callers to override individual keys without touching the file.
WEIGHTS: dict[str, float] = {}


def _load_weights(path: Path | None = None) -> dict[str, float]:
    """Read reward_weights.yaml and return a validated float dict."""
    path = _resolve_yaml_path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"reward_weights.yaml not found at {path}. "
            "Place it in quantum/configs/ or beside reward.py."
        )
    raw: dict = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    required = {
        "complete",
        "answer_correct",
        "format_choice",
        "energy_bar",
        "stability_bonus",
        "tab_switch_penalty",
        "overload_penalty",
    }
    missing = required - raw.keys()
    if missing:
        raise KeyError(f"reward_weights.yaml is missing keys: {missing}")
    return {k: float(v) for k, v in raw.items()}


def reload_weights(path: Path | None = None) -> None:
    """Re-read the YAML and refresh the module-level WEIGHTS dict in place."""
    WEIGHTS.clear()
    WEIGHTS.update(_load_weights(path))


# Populate on import — reload_weights() lets callers refresh at runtime.
reload_weights()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_reward(
    state: list[float],
    action: int,
    next_state: list[float],
    done: bool,
    *,
    rng: random.Random,
    quiz_correct_p: float = 0.6,
) -> float:
    """
    Compute the scalar reward for one (state, action, next_state, done) tuple.

    Parameters
    ----------
    state          : [dwell, jitter, focus, stall, pref_delta] all in [0, 1]
    action         : chosen action index (0-5)
    next_state     : next [dwell, jitter, focus, stall, pref_delta]
    done           : whether this transition ends the episode
    rng            : caller-owned Random instance (keeps function deterministic)
    quiz_correct_p : archetype-specific probability of correct quiz answer

    Returns
    -------
    float — scalar reward, rounded to 4 decimal places
    """
    if len(state) != 5:
        raise ValueError(f"state must have 5 elements, got {len(state)}")
    if len(next_state) != 5:
        raise ValueError(f"next_state must have 5 elements, got {len(next_state)}")
    if not (0.0 <= quiz_correct_p <= 1.0):
        raise ValueError(f"quiz_correct_p must be in [0, 1], got {quiz_correct_p}")

    dwell, jitter, focus, stall, pref_delta = state
    _, next_jitter, _, next_stall, _ = next_state

    reward = 0.0

    # ── Lesson complete ──────────────────────────────────────────────────────
    if done:
        reward += WEIGHTS["complete"]

    # ── Cognitive overload: both stall AND jitter simultaneously high ────────
    # Models ADHD paralysis state (Neuroperforma 2026).
    if stall > 0.70 and jitter > 0.70:
        reward += WEIGHTS["overload_penalty"]

    # ── Tab switching: focus near zero ───────────────────────────────────────
    if focus < 0.10:
        reward += WEIGHTS["tab_switch_penalty"]

    # ── Stability bonus: intervention worked — signals calming ───────────────
    if next_stall < stall - 0.10 and next_jitter < jitter - 0.10:
        reward += WEIGHTS["stability_bonus"]

    # ── Energy bar penalty: break forced under severe overload ───────────────
    # Only penalise when learner was genuinely overloaded (both signals > 0.75)
    # AND still had enough focus to continue (focus >= 0.25).
    # Distinguishes "policy chose break correctly" from "break was avoidable".
    if action == 5 and stall > 0.75 and jitter > 0.75 and focus >= 0.25:
        reward += WEIGHTS["energy_bar"]

    # ── Format preference match ───────────────────────────────────────────────
    # High pref_delta (>0.65) signals the learner wants a content format change.
    # Action 2 (Simplify Text) or 3 (Switch to Video) honours that preference.
    if pref_delta > 0.65 and action in (2, 3):
        reward += WEIGHTS["format_choice"]

    # ── Quiz correct answer ───────────────────────────────────────────────────
    # Action 4 (Inject Gamified Task / quiz) with low stall → learner engaged.
    if action == 4 and stall < 0.40:
        if rng.random() < quiz_correct_p:
            reward += WEIGHTS["answer_correct"]

    return round(reward, 4)


# ---------------------------------------------------------------------------
# Convenience: vectorised batch version (no randomness — quiz ignored)
# ---------------------------------------------------------------------------

def compute_reward_batch(
    states: list[list[float]],
    actions: list[int],
    next_states: list[list[float]],
    dones: list[bool],
) -> list[float]:
    """
    Deterministic batch reward: omits quiz term (stochastic) for bulk evals.
    Useful for plotting reward landscapes or ablation studies.
    """
    _rng = random.Random(0)
    return [
        compute_reward(s, a, ns, d, rng=_rng, quiz_correct_p=0.0)
        for s, a, ns, d in zip(states, actions, next_states, dones)
    ]
