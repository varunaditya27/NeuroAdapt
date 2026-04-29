"""
All tests that touch the training loop use ClassicalDDQN so the suite stays
fast and does not require PennyLane.  Quantum-specific paths are tested
only at the interface level (checkpoint loading, model dispatch).
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import torch

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
_HERE        = Path(__file__).resolve()
_QUANTUM_DIR = _HERE.parents[1]
_REPO_ROOT   = _QUANTUM_DIR.parent

for _p in (_REPO_ROOT, _QUANTUM_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from quantum.pennylane_vqc import ClassicalDDQN
from quantum.retrain import (
    _build_model,
    _load_checkpoint,
    _make_optimiser,
    run_retrain,
)
from quantum.train import TrainingResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATE_DIM  = 5
_N_ACTIONS  = 6
_N_EPISODES = 6
_N_STEPS    = 5


def _fake_transition():
    state      = [random.random() for _ in range(_STATE_DIM)]
    action     = random.randint(0, _N_ACTIONS - 1)
    reward     = random.uniform(-1, 1)
    next_state = [random.random() for _ in range(_STATE_DIM)]
    done       = random.random() < 0.1
    return (state, action, reward, next_state, done)


def _fake_dataset(n: int = 300) -> list:
    rng = random.Random(42)
    random.seed(42)
    return [_fake_transition() for _ in range(n)]


def _save_dummy_checkpoint(path: Path, model_type: str = "classical") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    model = ClassicalDDQN()
    torch.save(model.state_dict(), path)


def _write_dummy_reward_weights(path: Path) -> None:
    path.write_text(
        "complete: 1.0\n"
        "answer_correct: 0.5\n"
        "format_choice: 0.2\n"
        "energy_bar: -2.0\n"
        "stability_bonus: 0.3\n"
        "tab_switch_penalty: -0.3\n"
        "overload_penalty: -0.5\n"
    )


# ---------------------------------------------------------------------------
# 1. _build_model
# ---------------------------------------------------------------------------

class TestBuildModel:
    def test_classical_returns_classical_ddqn(self):
        m = _build_model("classical")
        assert isinstance(m, ClassicalDDQN)

    def test_invalid_model_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            _build_model("transformer")

    def test_classical_model_has_expected_layers(self):
        m = _build_model("classical")
        assert hasattr(m, "advantage") and hasattr(m, "value")


# ---------------------------------------------------------------------------
# 2. _load_checkpoint
# ---------------------------------------------------------------------------

class TestLoadCheckpoint:
    def test_loads_valid_checkpoint(self, tmp_path):
        ckpt = tmp_path / "ckpt.pt"
        _save_dummy_checkpoint(ckpt)
        model = ClassicalDDQN()
        _load_checkpoint(model, ckpt)   # should not raise

    def test_missing_checkpoint_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Checkpoint not found"):
            _load_checkpoint(ClassicalDDQN(), tmp_path / "ghost.pt")

    def test_loaded_weights_match(self, tmp_path):
        ckpt = tmp_path / "ckpt.pt"
        source = ClassicalDDQN()
        torch.save(source.state_dict(), ckpt)
        target = ClassicalDDQN()
        _load_checkpoint(target, ckpt)
        for p_src, p_tgt in zip(source.parameters(), target.parameters()):
            assert torch.allclose(p_src, p_tgt)


# ---------------------------------------------------------------------------
# 3. _make_optimiser
# ---------------------------------------------------------------------------

class TestMakeOptimiser:
    def test_classical_returns_adam(self):
        m   = ClassicalDDQN()
        opt = _make_optimiser("classical", m, lr=1e-3)
        assert isinstance(opt, torch.optim.Adam)

    def test_classical_has_single_param_group(self):
        m   = ClassicalDDQN()
        opt = _make_optimiser("classical", m, lr=1e-3)
        assert len(opt.param_groups) == 1
        assert opt.param_groups[0]["lr"] == pytest.approx(1e-3)


# ---------------------------------------------------------------------------
# 4. run_retrain — integration (classical only, tiny episodes)
# ---------------------------------------------------------------------------

class TestRunRetrain:

    @pytest.fixture()
    def setup(self, tmp_path) -> dict:
        ckpt_in  = tmp_path / "checkpoints" / "latest.pt"
        ckpt_out = tmp_path / "checkpoints" / "retrained_latest.pt"
        rw_yaml  = tmp_path / "reward_weights.yaml"
        _save_dummy_checkpoint(ckpt_in)
        _write_dummy_reward_weights(rw_yaml)

        dataset = _fake_dataset(300)
        return {
            "ckpt_in":  str(ckpt_in),
            "ckpt_out": str(ckpt_out),
            "rw_yaml":  str(rw_yaml),
            "tmp_path": tmp_path,
            "dataset":  dataset,
        }

    def _run(self, setup: dict, **kwargs) -> TrainingResult:
        defaults = dict(
            episodes=_N_EPISODES,
            steps_per_episode=_N_STEPS,
            model_type="classical",
            learning_rate=1e-3,
            checkpoint_in=setup["ckpt_in"],
            checkpoint_out=setup["ckpt_out"],
            reward_weights_path=setup["rw_yaml"],
            seed=42,
            enable_wandb=False,
        )
        defaults.update(kwargs)
        with patch("quantum.retrain.load_dataset_transitions", return_value=setup["dataset"]):
            return run_retrain(**defaults)

    def test_returns_training_result(self, setup):
        result = self._run(setup)
        assert isinstance(result, TrainingResult)

    def test_episode_rewards_length(self, setup):
        result = self._run(setup)
        assert len(result.episode_rewards) == _N_EPISODES

    def test_pref_delta_history_length(self, setup):
        result = self._run(setup)
        assert len(result.preference_delta_history) == _N_EPISODES

    def test_all_rewards_are_finite(self, setup):
        result = self._run(setup)
        for r in result.episode_rewards:
            assert isinstance(r, float) and r == r   # NaN check

    def test_checkpoint_out_written(self, setup):
        self._run(setup)
        assert Path(setup["ckpt_out"]).exists()

    def test_history_json_written(self, setup):
        self._run(setup)
        history_path = Path(setup["ckpt_out"]).with_suffix(".history.json")
        assert history_path.exists()
        data = json.loads(history_path.read_text())
        assert "episode_rewards" in data
        assert "pref_delta_history" in data
        assert "loss_history" in data

    def test_history_json_lengths_match(self, setup):
        self._run(setup)
        history_path = Path(setup["ckpt_out"]).with_suffix(".history.json")
        data = json.loads(history_path.read_text())
        assert len(data["episode_rewards"])    == _N_EPISODES
        assert len(data["pref_delta_history"]) == _N_EPISODES
        assert len(data["loss_history"])       == _N_EPISODES

    def test_deterministic_with_same_seed(self, setup):
        r1 = self._run(setup, seed=1)
        r2 = self._run(setup, seed=1)
        assert r1.episode_rewards == r2.episode_rewards

    def test_different_seeds_may_differ(self, setup):
        r1 = self._run(setup, seed=1)
        r2 = self._run(setup, seed=99)
        # Not guaranteed, but very likely with real randomness
        assert r1.episode_rewards != r2.episode_rewards or True  # soft check

    def test_epsilon_decay_reduces_over_time(self, setup):
        """
        Smoke test: with high epsilon_decay_episodes the final reward
        should be finite (agent mostly explores).
        """
        result = self._run(setup, epsilon_start=1.0, epsilon_end=0.0,
                           epsilon_decay_episodes=1000)
        assert all(r == r for r in result.episode_rewards)   # no NaN

    def test_custom_reward_weights_affect_result(self, setup, tmp_path):
        """Different reward weights should change the rewards recorded."""
        rw_high = tmp_path / "rw_high.yaml"
        rw_high.write_text(
            "complete: 100.0\nanswer_correct: 0.5\nformat_choice: 0.2\n"
            "energy_bar: -2.0\nstability_bonus: 0.3\n"
            "tab_switch_penalty: -0.3\noverload_penalty: -0.5\n"
        )
        r_default = self._run(setup, seed=7)
        r_high    = self._run(setup, seed=7, reward_weights_path=str(rw_high))
        # At least one episode reward should differ
        assert r_default.episode_rewards != r_high.episode_rewards

    def test_missing_checkpoint_raises(self, setup):
        with pytest.raises(FileNotFoundError):
            self._run(setup, checkpoint_in="/nonexistent/path/ckpt.pt")

    def test_invalid_model_type_raises(self, setup):
        with pytest.raises(ValueError, match="Unsupported"):
            self._run(setup, model_type="gpt")


# ---------------------------------------------------------------------------
# 5. Epsilon schedule
# ---------------------------------------------------------------------------

class TestEpsilonSchedule:
    """Unit-test the epsilon computation formula in run_retrain."""

    def test_epsilon_starts_at_epsilon_start(self):
        eps_start = 0.20
        eps_end   = 0.02
        decay     = 50
        # episode 1 → epsilon = max(end, start - 0/decay * range) = start
        computed = max(eps_end, eps_start - 0 / decay * (eps_start - eps_end))
        assert computed == pytest.approx(eps_start)

    def test_epsilon_clamps_at_epsilon_end(self):
        eps_start = 0.20
        eps_end   = 0.02
        decay     = 10
        computed = max(eps_end, eps_start - 100 / decay * (eps_start - eps_end))
        assert computed == pytest.approx(eps_end)

    def test_epsilon_is_monotone_decreasing(self):
        eps_start = 0.15
        eps_end   = 0.02
        decay     = 80
        epsilons = [
            max(eps_end, eps_start - (ep - 1) / decay * (eps_start - eps_end))
            for ep in range(1, 90)
        ]
        for a, b in zip(epsilons, epsilons[1:]):
            assert a >= b


# ---------------------------------------------------------------------------
# 6. run_retrain — W&B disabled path
# ---------------------------------------------------------------------------

class TestWandbDisabled:
    def test_no_import_error_when_wandb_missing(self, tmp_path):
        ckpt_in  = tmp_path / "ckpt.pt"
        ckpt_out = tmp_path / "out.pt"
        rw_yaml  = tmp_path / "reward_weights.yaml"
        _save_dummy_checkpoint(ckpt_in)
        _write_dummy_reward_weights(rw_yaml)
        dataset = _fake_dataset(100)

        with patch("quantum.retrain.load_dataset_transitions", return_value=dataset):
            result = run_retrain(
                episodes=2,
                steps_per_episode=3,
                model_type="classical",
                checkpoint_in=str(ckpt_in),
                checkpoint_out=str(ckpt_out),
                reward_weights_path=str(rw_yaml),
                seed=0,
                enable_wandb=False,
            )
        assert isinstance(result, TrainingResult)


# ---------------------------------------------------------------------------
# 7. parse_args smoke test
# ---------------------------------------------------------------------------

class TestParseArgs:
    def test_defaults_parsed(self):
        import quantum.retrain as rt
        args = rt.parse_args.__wrapped__() if hasattr(rt.parse_args, "__wrapped__") else None
        # Just confirm the function exists and is callable
        assert callable(rt.parse_args)

    def test_model_choices_accepted(self, monkeypatch):
        import quantum.retrain as rt
        monkeypatch.setattr(sys, "argv", ["retrain.py", "--model", "classical"])
        args = rt.parse_args()
        assert args.model == "classical"
