# Pitch Deck Notes (Slides 4-6)

## Slide 4: Why Quantum Helps

- Problem: static policy networks adapt too slowly to non-stationary attention signals.
- Claim: VQC captures joint signal interactions with fewer parameters.
- Visual: 5-signal state vector -> VQC -> action distribution.
- One-line takeaway: faster early convergence in the first 20-40 episodes.

## Slide 5: VQC Circuit Intuition

- Show circuit diagram (from visualise_circuit.py).
- Emphasize CNOT entanglement across focus and stall.
- Explain: co-activation patterns encode hyperfocus vs paralysis.
- One-line takeaway: entanglement represents joint states structurally.

## Slide 6: Ablation C Result

- Plot: VQC vs classical baseline preference delta.
- Highlight: episode count to reach target delta.
- Provide numeric callout: VQC X episodes vs classical Y episodes.
- One-line takeaway: VQC learns faster under the same data budget.
