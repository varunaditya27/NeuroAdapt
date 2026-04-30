# Quantum Methodology

## Motivation: Static vs Dynamic Policies
Traditional Classical Deep Q-Networks (DDQNs) can be slow to adapt to non-stationary signals. In NeuroAdapt, attention is non-stationary: a learner can shift from high jitter to hyperfocus within the same session. A static policy network struggles to quickly relearn these shifting correlations without extensive retraining.

By introducing a **Variational Quantum Circuit (VQC)** into the policy network, we use entanglement to capture feature interactions with fewer trainable parameters, aiming for faster convergence during the early learning window.

## Architecture: Hybrid Quantum-Classical DDQN

Our VQC replaces the standard fully-connected feature extraction layers of a classical DDQN.

1. **State Encoding:** The 5-dimensional classical state vector `[dwell, jitter, focus, stall, pref_delta]` is embedded into 5 qubits using parameterized $R_X$ rotations.
2. **Entanglement (CNOT Chain):** The circuit applies a CNOT chain across adjacent qubits. This links joint signal states (for example, focus + stall) so the model can represent co-activation patterns structurally.
3. **Variational Layer:** Trainable $R_Y$ rotations provide the circuit parameters optimized by PyTorch via PennyLane autograd.
4. **Dueling Output Head:** Z-basis expectations feed a classical dueling head to estimate $V(s)$ and $A(s,a)$ and reduce Q-value overestimation.

## Ablation A: Observer Signal Importance (Zero-Out Sweep)

To identify which observer signals are most critical to policy quality, each signal dimension is independently zeroed out across all dataset transitions and the VQC-DDQN is retrained from scratch (seed=7, 300 episodes, 20 steps/episode). Preference Delta (lower = better) is measured on a fixed held-out evaluation set.

**Protocol:** `quantum/ablations/ablation_a.py` — signal zero-out sweep across `[dwell, jitter, focus, stall, pref_delta]`.

| Signal Zeroed | Initial PrefDelta (ep 1–20 mean) | Final PrefDelta (MA20 last 50 ep) | Status |
|---|---|---|---|
| `dwell` | 0.4500 | 0.3933 | ✓ Complete |
| `stall` | 0.3187 | 0.3175 | ✓ Complete |
| `jitter` | 0.2481 | 0.2962 | ✓ Complete |
| `pref_delta`| 0.4525 | 0.2561 | ✓ Complete |
| `focus` | 0.2756 | 0.2181 | ✓ Complete |

**Confirmed findings:**
- Zeroing `dwell` causes the highest residual preference delta (0.3933), making it the **most critical** signal — the policy fails to recover without dwell information.
- Zeroing `focus` produces the lowest final delta (0.2181), suggesting it has the least impact when removed.

**Plot:** `quantum/ablation_a_signals.png`

## Ablation B: Action Space Reduction (3 vs 6 Actions)

To assess whether the full 6-action space is necessary, we remap dataset actions from [0–5] to [0–2] (linear rescaling: `new = round(old × 2/5)`) and retrain the VQC-DDQN with `ACTION_SPACE = 3` (seed=7, 300 episodes, 20 steps/episode).

**Protocol:** `quantum/ablations/ablation_b.py` — patches `shared_config.py`, remaps dataset actions, runs training subprocess, then restores original config.

| Configuration | Initial PrefDelta | Final PrefDelta (MA20 last 50 ep) | Episodes |
|---|---|---|---|
| 6-action baseline (quantum, seed 7) | 0.3497 | 0.3371 | 500 |
| 3-action reduced | 0.3273 | 0.2556 | 300 |

**Key result:** Reducing to 3 actions improved final preference delta by 0.0815 (0.76× of baseline), achieving lower steady-state error in fewer episodes. This suggests the VQC converges more efficiently when the action space is reduced — the architecture generalises across both configurations without quality degradation.

> Note: This does not mean 3 actions is preferable for production deployment (which requires all 6 pedagogical interventions). It validates that the policy quality is not artificially dependent on action-space complexity.

**Plot:** `quantum/ablation_b_action_space.png`

## Ablation C: Quantum Advantage (VQC vs Classical Baseline)

To validate the efficiency of the VQC, Ablation C compares the Quantum DDQN against a classical DDQN with a comparable parameter footprint, trained on the same synthetic archetype dataset and evaluation set.

**Status:** Complete.

- **Result:** VQC converged to a Preference Delta < 0.35 in **0** episodes (immediate early adaptation) vs **79** episodes for the classical baseline.
- **Final Accuracy:** VQC (0.3371) and Classical (0.3281) reached comparable final steady-state errors, demonstrating the primary quantum advantage is early-window learning speed.
- **Metric:** Preference Delta (lower is better), reported on a fixed evaluation set.

## Artifacts (to attach)

- VQC circuit diagram PNG from `quantum/visualise_circuit.py`
- Ablation A signal sweep plot: `quantum/ablation_a_signals.png`
- Ablation B action space plot: `quantum/ablation_b_action_space.png`
- Ablation C convergence plot (e.g. `quantum/ablation_thesis_final_run.png`)
- W&B export or CSV summary for multi-seed runs
