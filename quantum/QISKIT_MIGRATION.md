# Qiskit Migration Guide

## Device Switch

Current simulator setup:

```python
import pennylane as qml

dev = qml.device("default.qubit", wires=5)
```

Target IBM backend setup:

```python
import pennylane as qml

dev = qml.device(
    "qiskit.ibmq",
    wires=5,
    backend="ibm_osaka",  # choose an available backend
    ibmqx_token="${IBMQ_API_TOKEN}",
)
```

Use environment variables for credentials and never commit tokens.

## Expected NISQ Noise Differences

- Gate errors and readout noise will reduce confidence calibration compared to simulator output.
- Decoherence introduces stochastic variance across identical forward passes.
- Circuit depth has to stay shallow to preserve signal fidelity.

Practical mitigation steps:

- Keep qubit count fixed at 5 and minimize entangling depth.
- Use repeated circuit evaluations and aggregate logits (mean of multiple shots).
- Re-tune confidence gate threshold using hardware calibration runs.

## Why 5 Qubits Is Safe

NeuroAdapt uses 5 qubits, which is comfortably below the smallest widely accessible IBMQ devices (7+ qubits). This keeps routing constraints and transpilation overhead manageable for early hardware pilots.
