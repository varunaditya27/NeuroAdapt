# VQC Experiment Log

This file tracks the architectural and hyperparameter variations tried during the optimization of the NeuroAdapt Quantum DDQN.

## Variation 1: The Baseline Stabilizer
- **Goal**: Resolve immediate numerical instability and loss explosion.
- **Configuration**:
    - **Architecture**: 2-layer VQC, 5 measurements (PauliZ per qubit).
    - **Loss**: `F.smooth_l1_loss` (Reverted from MSE).
    - **Clipping**: `GRAD_CLIP_NORM = 0.5`.
    - **Clamping**: Q-Values clamped to `[-10.0, 10.0]`.
    - **LR**: `1e-4` for all parameters.
    - **Target Sync**: `TAU = 0.0001`, `TARGET_UPDATE_FREQ = 200`.
- **Observations**: 
    - Loss stabilized, but the model showed "lazy" behavior.
    - Convergence plateaued early around 0.45 preference delta.
    - Information bottleneck identified: 5 measurements too low for 6 actions.

## Variation 2: Resolution & Entropy Push
- **Goal**: Break the 0.45 plateau by increasing signal resolution and exploration pressure.
- **Configuration**:
    - **Architecture**: 9 measurements (PauliX/Y/Z on Q0-Q1, PauliZ on Q2-Q4).
    - **Entanglement**: Switched to `qml.StronglyEntanglingLayers`.
    - **Exploration**: Added **Entropy Penalty** (`-0.01 * policy_entropy`) to the loss.
    - **Scheduler**: Introduced `CosineAnnealingWarmRestarts(T_0=50)` for "kicks."
    - **Target Sync**: Increased `TAU` to 0.005 for more responsiveness.
- **Observations**: 
    - Model started exploring diverse actions.
    - **U-Shaped Loss** emerged: scheduler kicks were too frequent/aggressive for the VQC to settle.
    - Identified "Classical Dominance": The 64-unit bottleneck allowed the MLP to learn the task without the VQC.

## Variation 3: The "Emergency Brake" Refinement
- **Goal**: Dampen the U-shaped loss while maintaining the higher resolution.
- **Configuration**:
    - **Architecture**: Retained 9 measurements and strongly entangling layers.
    - **Target Sync**: Dropped `TAU` back to **0.001** and locked `TARGET_UPDATE_FREQ` at 150.
    - **Epsilon**: Accelerated decay to **200 episodes** to force earlier reliance on learned weights.
    - **Data**: Sharpened archetype contrasts (Dyslexia stall 0.95).
- **Observations**: 
    - Smoother loss curve, but still trailing the classical model in early-run speed.
    - Confirmed "Feature Washout": The 64-dim bottleneck was still too wide.

## Variation 4: The Intelligence Overhaul (Active)
- **Goal**: Force VQC dominance and achieve "Quantum Lead" in convergence speed.
- **Configuration**:
    - **Architecture**: 
        - Increased depth to **5 layers**.
        - Switched to **RY encoding** (stable real-plane rotations).
        - Standardized **7 measurements** (5 PauliZ + 2 Entangling pairs).
    - **Bottleneck**: Shrunk hidden dimension from 64 to **16 units** (Forced dependency).
    - **Optimization**:
        - **LR Flip**: Quantum Core `1e-3` / Classical Head `1e-4`.
        - **Clipping**: Increased to `1.0` to allow quantum gradient spikes.
        - **Scheduler**: Smoothed to `T_0 = 150`.
    - **Stabilization**: `TAU = 0.0005`, `EPSILON_DECAY_EP = 300`.
    - **Pre-fill**: Increased to **5,000** for high-diversity initial gradients.
- **Hypothesis**: The combination of a deeper VQC, a restrictive classical bottleneck, and higher quantum learning authority will force the model to utilize the Bloch sphere's expressive capacity to distinguish archetypes faster than the classical model.
- **Date**: 2026-05-04
