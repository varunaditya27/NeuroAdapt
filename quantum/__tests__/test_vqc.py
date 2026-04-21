import pytest
import torch

from shared_config import N_ACTIONS, N_QUBITS


def test_quantum_ddqn_forward_supports_batched_inputs() -> None:
    pytest.importorskip("pennylane")

    from quantum.pennylane_vqc import QuantumDDQN

    model = QuantumDDQN()
    batch_state = torch.rand(8, N_QUBITS, dtype=torch.float32)

    with torch.no_grad():
        q_values = model(batch_state)

    assert q_values.shape == (8, N_ACTIONS)
    assert torch.isfinite(q_values).all()
