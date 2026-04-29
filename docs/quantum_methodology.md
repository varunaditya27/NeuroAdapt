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

## Ablation C: Quantum Advantage (VQC vs Classical Baseline)

To validate the efficiency of the VQC, Ablation C compares the Quantum DDQN against a classical DDQN with a comparable parameter footprint, trained on the same synthetic archetype dataset and evaluation set.

**Status:** Pending final run. Insert the final convergence plot and numeric comparison after the ablation run.

- **Result placeholder:** VQC converged in **X** episodes vs **Y** for the classical baseline.
- **Metric:** Preference Delta (lower is better), reported on a fixed evaluation set.

## Artifacts (to attach)

- VQC circuit diagram PNG from `quantum/visualise_circuit.py`
- Ablation C convergence plot (e.g. `quantum/ablation_thesis_final_run.png`)
- W&B export or CSV summary for multi-seed runs
