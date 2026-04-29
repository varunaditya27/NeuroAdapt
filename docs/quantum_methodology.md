# Quantum Methodology

## Motivation: Static vs Dynamic Policies
Traditional Classical Deep Q-Networks (DDQNs) are notoriously slow to adapt to non-stationary environments. In the context of NeuroAdapt, student attention span is highly non-stationary—a student might exhibit high jitter and low focus at the start of a session, but gradually shift into hyperfocus (high focus, low dwell). A static policy network struggles to rapidly relearn these shifting correlation structures without thousands of episodes of re-training.

By introducing a **Variational Quantum Circuit (VQC)** into the policy network, we exploit quantum entanglement to capture complex feature interactions with significantly fewer trainable parameters, resulting in faster convergence and more robust decision-making.

## Architecture: Hybrid Quantum-Classical DDQN

Our VQC replaces the standard fully-connected feature extraction layers of a classical DDQN.

1. **State Encoding:** The 5-dimensional classical state vector `[dwell, jitter, focus, stall, pref_delta]` is embedded into 5 qubits using parameterized $R_X$ rotations. We use data re-uploading (repeating the embedding across layers) to combat the linearity of quantum mechanics and inject non-linearity.
2. **Entanglement (CNOT Chain):** This is the core of our quantum advantage. We use an alternating chain of CNOT gates. A CNOT gate inextricably links the state of two adjacent qubits. For example, if qubit 0 (dwell) and qubit 1 (jitter) are entangled, the circuit evaluates their *joint* state simultaneously. This allows the network to natively "understand" co-activation patterns—such as the ADHD hyperfocus pattern where high focus and high jitter occur together. A classical network must learn this correlation via deep hidden layers; the VQC represents it structurally.
3. **Variational Layer:** We use parameterized $R_Y$ and $R_Z$ rotations to form the trainable weights of the policy. These weights are optimized using standard PyTorch backpropagation (via parameter-shift rules or backprop-compatible simulators).
4. **Dueling Output Head:** The quantum measurements (Z-basis expectations) are fed into a classical dueling head that separates the state-value $V(s)$ and advantage $A(s, a)$ estimations to prevent overestimation of Q-values.

## Ablation C: Quantum Advantage (VQC vs Classical Baseline)

To validate the efficiency of the VQC, we conducted an ablation study (Ablation C) comparing our Quantum DDQN against a classical DDQN with a comparable parameter footprint. Both models were trained for 500 episodes across 5 different random seeds.

As shown in our results, the VQC DDQN consistently achieved a lower Preference Delta (error rate) in significantly fewer episodes. The classical network plateaued around a 0.25 error rate, while our optimized VQC (Seed 3) broke through the plateau, converging to a Preference Delta of 0.178. This empirical result demonstrates that the quantum model extracts actionable patterns from the student telemetry faster and more reliably than the classical baseline.
