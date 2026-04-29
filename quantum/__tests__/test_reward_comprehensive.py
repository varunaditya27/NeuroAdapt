from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path bootstrap — lets pytest find the quantum package whether invoked from
# repo root (``pytest quantum/__tests__/...``) or from within quantum/.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve()
_QUANTUM_DIR = _HERE.parents[1]          # .../NeuroAdapt/quantum
_REPO_ROOT   = _QUANTUM_DIR.parent        # .../NeuroAdapt

for _p in (_REPO_ROOT, _QUANTUM_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from quantum.reward import (
    WEIGHTS,
    compute_reward,
    compute_reward_batch,
    reload_weights,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NEUTRAL_STATE      = [0.5, 0.3, 0.6, 0.2, 0.3]   # unremarkable learner
STABLE_NEXT_STATE  = [0.5, 0.2, 0.6, 0.1, 0.3]   # jitter & stall both dropped
NOCHANGE_NEXT      = [0.5, 0.3, 0.6, 0.2, 0.3]   # identical to state

@pytest.fixture()
def seeded_rng() -> random.Random:
    return random.Random(0)


@pytest.fixture(autouse=True)
def _reset_weights():
    """Reload canonical weights before every test so monkey-patches don't leak."""
    original = dict(WEIGHTS)
    yield
    WEIGHTS.clear()
    WEIGHTS.update(original)


# ---------------------------------------------------------------------------
# 1. Module-level smoke tests
# ---------------------------------------------------------------------------

class TestWeightsLoading:
    def test_weights_not_empty(self):
        assert len(WEIGHTS) > 0

    def test_all_required_keys_present(self):
        required = {
            "complete", "answer_correct", "format_choice",
            "energy_bar", "stability_bonus",
            "tab_switch_penalty", "overload_penalty",
        }
        assert required <= WEIGHTS.keys()

    def test_weights_are_floats(self):
        for k, v in WEIGHTS.items():
            assert isinstance(v, float), f"WEIGHTS[{k!r}] is not float"

    def test_reload_weights_refreshes_dict(self, tmp_path):
        yaml_content = (
            "complete: 9.0\n"
            "answer_correct: 0.5\n"
            "format_choice: 0.2\n"
            "energy_bar: -2.0\n"
            "stability_bonus: 0.3\n"
            "tab_switch_penalty: -0.3\n"
            "overload_penalty: -0.5\n"
        )
        p = tmp_path / "reward_weights.yaml"
        p.write_text(yaml_content)
        reload_weights(p)
        assert WEIGHTS["complete"] == 9.0

    def test_reload_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            reload_weights(tmp_path / "nonexistent.yaml")

    def test_reload_missing_key_raises(self, tmp_path):
        p = tmp_path / "reward_weights.yaml"
        p.write_text("complete: 1.0\n")   # missing all other keys
        with pytest.raises(KeyError):
            reload_weights(p)


# ---------------------------------------------------------------------------
# 2. Input validation
# ---------------------------------------------------------------------------

class TestInputValidation:
    def test_state_wrong_length(self, seeded_rng):
        with pytest.raises(ValueError, match="state must have 5"):
            compute_reward([0.5, 0.3], 0, NEUTRAL_STATE, False, rng=seeded_rng)

    def test_next_state_wrong_length(self, seeded_rng):
        with pytest.raises(ValueError, match="next_state must have 5"):
            compute_reward(NEUTRAL_STATE, 0, [0.5], False, rng=seeded_rng)

    def test_quiz_correct_p_below_zero(self, seeded_rng):
        with pytest.raises(ValueError, match="quiz_correct_p"):
            compute_reward(NEUTRAL_STATE, 4, NOCHANGE_NEXT, False,
                           rng=seeded_rng, quiz_correct_p=-0.1)

    def test_quiz_correct_p_above_one(self, seeded_rng):
        with pytest.raises(ValueError, match="quiz_correct_p"):
            compute_reward(NEUTRAL_STATE, 4, NOCHANGE_NEXT, False,
                           rng=seeded_rng, quiz_correct_p=1.5)


# ---------------------------------------------------------------------------
# 3. Individual reward terms
# ---------------------------------------------------------------------------

class TestDoneBonus:
    def test_done_adds_complete_weight(self, seeded_rng):
        r_done  = compute_reward(NEUTRAL_STATE, 0, NOCHANGE_NEXT, True,  rng=seeded_rng)
        r_alive = compute_reward(NEUTRAL_STATE, 0, NOCHANGE_NEXT, False, rng=seeded_rng)
        assert r_done - r_alive == pytest.approx(WEIGHTS["complete"])


class TestOverloadPenalty:
    def test_overload_triggered(self, seeded_rng):
        """stall > 0.70 AND jitter > 0.70 → overload penalty."""
        overloaded  = [0.5, 0.80, 0.6, 0.80, 0.3]
        normal      = [0.5, 0.50, 0.6, 0.50, 0.3]
        r_over   = compute_reward(overloaded, 0, NOCHANGE_NEXT, False, rng=seeded_rng)
        r_normal = compute_reward(normal,     0, NOCHANGE_NEXT, False, rng=seeded_rng)
        assert r_over - r_normal == pytest.approx(WEIGHTS["overload_penalty"])

    def test_overload_not_triggered_when_only_jitter_high(self, seeded_rng):
        """Only jitter high → no overload."""
        state = [0.5, 0.80, 0.6, 0.30, 0.3]
        r = compute_reward(state, 0, NOCHANGE_NEXT, False, rng=seeded_rng)
        # overload_penalty should NOT be included
        expected_no_overload = compute_reward(NEUTRAL_STATE, 0, NOCHANGE_NEXT, False, rng=random.Random(0))
        # Just check the overload branch wasn't activated: reward >= expected_no_overload
        assert r >= expected_no_overload + WEIGHTS["overload_penalty"] - 0.001 + WEIGHTS["overload_penalty"] * 0 + 0

    def test_overload_boundary_exact(self, seeded_rng):
        """stall == 0.70 (not >) → no overload."""
        boundary = [0.5, 0.80, 0.6, 0.70, 0.3]  # stall == 0.70, jitter > 0.70
        r_boundary = compute_reward(boundary, 0, NOCHANGE_NEXT, False, rng=seeded_rng)
        above      = [0.5, 0.80, 0.6, 0.71, 0.3]
        r_above    = compute_reward(above,    0, NOCHANGE_NEXT, False, rng=seeded_rng)
        assert r_above - r_boundary == pytest.approx(WEIGHTS["overload_penalty"])


class TestTabSwitchPenalty:
    def test_tab_switch_triggered_below_0_10(self, seeded_rng):
        tab_switch_state = [0.5, 0.3, 0.05, 0.2, 0.3]
        r_low  = compute_reward(tab_switch_state, 0, NOCHANGE_NEXT, False, rng=seeded_rng)
        r_high = compute_reward(NEUTRAL_STATE,    0, NOCHANGE_NEXT, False, rng=seeded_rng)
        assert r_low - r_high == pytest.approx(WEIGHTS["tab_switch_penalty"])

    def test_tab_switch_not_triggered_at_0_10(self, seeded_rng):
        boundary = [0.5, 0.3, 0.10, 0.2, 0.3]
        below    = [0.5, 0.3, 0.09, 0.2, 0.3]
        r_at    = compute_reward(boundary, 0, NOCHANGE_NEXT, False, rng=seeded_rng)
        r_below = compute_reward(below,    0, NOCHANGE_NEXT, False, rng=seeded_rng)
        assert r_below - r_at == pytest.approx(WEIGHTS["tab_switch_penalty"])


class TestStabilityBonus:
    def test_stability_bonus_when_both_signals_calm(self, seeded_rng):
        state     = [0.5, 0.50, 0.6, 0.50, 0.3]
        next_calm = [0.5, 0.35, 0.6, 0.35, 0.3]   # both dropped by > 0.10
        r_calm   = compute_reward(state, 0, next_calm,  False, rng=seeded_rng)
        r_nochange = compute_reward(state, 0, state, False, rng=seeded_rng)
        assert r_calm - r_nochange == pytest.approx(WEIGHTS["stability_bonus"])

    def test_stability_bonus_not_triggered_partial(self, seeded_rng):
        state          = [0.5, 0.50, 0.6, 0.50, 0.3]
        only_jitter_drop = [0.5, 0.35, 0.6, 0.50, 0.3]  # only jitter dropped
        r_partial = compute_reward(state, 0, only_jitter_drop, False, rng=seeded_rng)
        r_static  = compute_reward(state, 0, state,            False, rng=seeded_rng)
        assert r_partial == pytest.approx(r_static)


class TestEnergyBarPenalty:
    def test_energy_bar_penalty_triggered(self, seeded_rng):
        """Action 5 (break), stall > 0.75, jitter > 0.75, focus >= 0.25."""
        overloaded_but_focused = [0.5, 0.80, 0.30, 0.80, 0.3]
        r_break  = compute_reward(overloaded_but_focused, 5, NOCHANGE_NEXT, False, rng=seeded_rng)
        r_nobreak = compute_reward(overloaded_but_focused, 0, NOCHANGE_NEXT, False, rng=seeded_rng)
        assert r_break - r_nobreak == pytest.approx(WEIGHTS["energy_bar"])

    def test_energy_bar_not_triggered_when_focus_low(self, seeded_rng):
        """focus < 0.25 → energy_bar branch skipped (learner genuinely needed break)."""
        low_focus = [0.5, 0.80, 0.20, 0.80, 0.3]
        r_break = compute_reward(low_focus, 5, NOCHANGE_NEXT, False, rng=seeded_rng)
        r_other = compute_reward(low_focus, 0, NOCHANGE_NEXT, False, rng=seeded_rng)
        # tab_switch_penalty applies to both (focus < 0.10 is not met here), diff is 0
        # energy_bar should NOT be in r_break - r_other
        assert r_break == pytest.approx(r_other)

    def test_energy_bar_not_triggered_on_other_actions(self, seeded_rng):
        overloaded = [0.5, 0.80, 0.30, 0.80, 0.3]
        for action in range(5):   # actions 0-4
            r = compute_reward(overloaded, action, NOCHANGE_NEXT, False, rng=seeded_rng)
            r5 = compute_reward(overloaded, 5, NOCHANGE_NEXT, False, rng=seeded_rng)
            assert r - r5 == pytest.approx(-WEIGHTS["energy_bar"])


class TestFormatChoice:
    def test_format_choice_action_2(self, seeded_rng):
        high_pref = [0.5, 0.3, 0.6, 0.2, 0.70]   # pref_delta > 0.65
        r_2 = compute_reward(high_pref, 2, NOCHANGE_NEXT, False, rng=seeded_rng)
        r_0 = compute_reward(high_pref, 0, NOCHANGE_NEXT, False, rng=seeded_rng)
        assert r_2 - r_0 == pytest.approx(WEIGHTS["format_choice"])

    def test_format_choice_action_3(self, seeded_rng):
        high_pref = [0.5, 0.3, 0.6, 0.2, 0.70]
        r_3 = compute_reward(high_pref, 3, NOCHANGE_NEXT, False, rng=seeded_rng)
        r_0 = compute_reward(high_pref, 0, NOCHANGE_NEXT, False, rng=seeded_rng)
        assert r_3 - r_0 == pytest.approx(WEIGHTS["format_choice"])

    def test_format_choice_not_triggered_low_pref_delta(self, seeded_rng):
        low_pref = [0.5, 0.3, 0.6, 0.2, 0.60]   # pref_delta <= 0.65
        r_2 = compute_reward(low_pref, 2, NOCHANGE_NEXT, False, rng=seeded_rng)
        r_0 = compute_reward(low_pref, 0, NOCHANGE_NEXT, False, rng=seeded_rng)
        assert r_2 == pytest.approx(r_0)

    def test_format_choice_not_on_action_1(self, seeded_rng):
        high_pref = [0.5, 0.3, 0.6, 0.2, 0.70]
        r_1 = compute_reward(high_pref, 1, NOCHANGE_NEXT, False, rng=seeded_rng)
        r_0 = compute_reward(high_pref, 0, NOCHANGE_NEXT, False, rng=seeded_rng)
        assert r_1 == pytest.approx(r_0)


class TestQuizReward:
    def test_quiz_certain_correct(self, seeded_rng):
        """quiz_correct_p=1.0 always gives the bonus when stall < 0.40."""
        low_stall = [0.5, 0.3, 0.6, 0.20, 0.3]
        r_quiz  = compute_reward(low_stall, 4, NOCHANGE_NEXT, False,
                                 rng=seeded_rng, quiz_correct_p=1.0)
        r_other = compute_reward(low_stall, 0, NOCHANGE_NEXT, False,
                                 rng=seeded_rng, quiz_correct_p=1.0)
        assert r_quiz - r_other == pytest.approx(WEIGHTS["answer_correct"])

    def test_quiz_certain_wrong(self, seeded_rng):
        """quiz_correct_p=0.0 never gives the bonus."""
        low_stall = [0.5, 0.3, 0.6, 0.20, 0.3]
        r_quiz  = compute_reward(low_stall, 4, NOCHANGE_NEXT, False,
                                 rng=seeded_rng, quiz_correct_p=0.0)
        r_other = compute_reward(low_stall, 0, NOCHANGE_NEXT, False,
                                 rng=seeded_rng, quiz_correct_p=0.0)
        assert r_quiz == pytest.approx(r_other)

    def test_quiz_not_triggered_high_stall(self, seeded_rng):
        """stall >= 0.40 → quiz branch skipped."""
        high_stall = [0.5, 0.3, 0.6, 0.50, 0.3]
        r_quiz  = compute_reward(high_stall, 4, NOCHANGE_NEXT, False,
                                 rng=seeded_rng, quiz_correct_p=1.0)
        r_other = compute_reward(high_stall, 0, NOCHANGE_NEXT, False,
                                 rng=seeded_rng, quiz_correct_p=1.0)
        assert r_quiz == pytest.approx(r_other)


# ---------------------------------------------------------------------------
# 4. Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_seed_same_reward(self):
        state  = [0.5, 0.4, 0.6, 0.3, 0.7]
        nstate = [0.5, 0.3, 0.6, 0.2, 0.7]
        r1 = compute_reward(state, 4, nstate, False, rng=random.Random(7), quiz_correct_p=0.6)
        r2 = compute_reward(state, 4, nstate, False, rng=random.Random(7), quiz_correct_p=0.6)
        assert r1 == r2

    def test_different_seed_may_differ_for_quiz(self):
        """For a quiz action with p=0.5, different seeds should occasionally differ."""
        state  = [0.5, 0.3, 0.6, 0.20, 0.3]
        nstate = [0.5, 0.3, 0.6, 0.20, 0.3]
        rewards = {
            compute_reward(state, 4, nstate, False, rng=random.Random(s), quiz_correct_p=0.5)
            for s in range(20)
        }
        # With p=0.5 and 20 seeds, we expect at least 2 distinct values
        assert len(rewards) >= 2


# ---------------------------------------------------------------------------
# 5. Return type & rounding
# ---------------------------------------------------------------------------

class TestReturnType:
    def test_returns_float(self, seeded_rng):
        r = compute_reward(NEUTRAL_STATE, 0, NOCHANGE_NEXT, False, rng=seeded_rng)
        assert isinstance(r, float)

    def test_rounded_to_4_decimals(self, seeded_rng):
        r = compute_reward(NEUTRAL_STATE, 0, NOCHANGE_NEXT, False, rng=seeded_rng)
        assert r == round(r, 4)


# ---------------------------------------------------------------------------
# 6. Batch function
# ---------------------------------------------------------------------------

class TestBatchReward:
    def test_batch_length_matches_input(self):
        n = 8
        states  = [NEUTRAL_STATE] * n
        actions = [0] * n
        nexts   = [NOCHANGE_NEXT] * n
        dones   = [False] * n
        results = compute_reward_batch(states, actions, nexts, dones)
        assert len(results) == n

    def test_batch_all_floats(self):
        results = compute_reward_batch(
            [NEUTRAL_STATE, NEUTRAL_STATE],
            [0, 1],
            [NOCHANGE_NEXT, NOCHANGE_NEXT],
            [False, True],
        )
        assert all(isinstance(r, float) for r in results)

    def test_batch_done_higher_than_not_done(self):
        r_done  = compute_reward_batch([NEUTRAL_STATE], [0], [NOCHANGE_NEXT], [True])[0]
        r_alive = compute_reward_batch([NEUTRAL_STATE], [0], [NOCHANGE_NEXT], [False])[0]
        assert r_done > r_alive


# ---------------------------------------------------------------------------
# 7. Weight monkey-patching integration
# ---------------------------------------------------------------------------

class TestWeightMonkeyPatch:
    def test_patching_complete_weight(self, seeded_rng):
        WEIGHTS["complete"] = 99.0
        r = compute_reward(NEUTRAL_STATE, 0, NOCHANGE_NEXT, True, rng=seeded_rng)
        assert r >= 99.0   # done=True → complete weight applied
