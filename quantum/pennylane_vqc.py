from __future__ import annotations

import torch
import torch.nn as nn

try:
    from shared_config import N_ACTIONS, N_QUBITS
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from shared_config import N_ACTIONS, N_QUBITS

try:
    import pennylane as qml
except Exception:  # pragma: no cover
    qml = None


if qml is not None:
    dev = qml.device("default.qubit", wires=N_QUBITS)
    PI = 3.141592653589793

    # weights layout: 3 variational layers × N_QUBITS params = 15 params total
    #
    # Circuit structure:
    #   Encode → CNOT chain → RY layer 1
    #   → Re-encode → CNOT chain → RY layer 2
    #   → Re-encode → Circular CNOT → RY layer 3
    #   → Measure
    #
    # The circular CNOT (last qubit → first qubit) in layer 3 connects signals
    # that the chain never directly couples, e.g. dwell time (qubit 0) and
    # preference delta (qubit 4). This matters because a student who reads
    # slowly AND consistently picks the same format is a very different profile
    # from one who reads slowly but keeps changing preference.
    @qml.qnode(dev, interface="torch", diff_method="backprop")
    def vqc(inputs, weights):
        encoded_inputs = qml.math.reshape(inputs, (-1, N_QUBITS))
        
        # We use 5 layers now to give the VQC enough "depth" to match classical performance
        # Each layer needs 2 * N_QUBITS parameters (one for RY, one for RZ)
        NUM_LAYERS = 5 
        params_per_layer = 2 * N_QUBITS

        for L in range(NUM_LAYERS):
            # --- Data Re-uploading ---
            # Using PI instead of 2*PI ensures 0.0 and 1.0 map to unique states
            for i in range(N_QUBITS):
                qml.RX(encoded_inputs[:, i] * PI, wires=i)

            # --- Entanglement Layer ---
            # Alternating entanglement patterns helps avoid barren plateaus
            if L % 2 == 0:
                for i in range(N_QUBITS - 1):
                    qml.CNOT(wires=[i, i + 1])
            else:
                qml.CNOT(wires=[N_QUBITS - 1, 0]) # Circular connection
                for i in range(N_QUBITS - 1, 0, -1):
                    qml.CNOT(wires=[i, i - 1])

            # --- Variational Layer (RY and RZ) ---
            # Adding RZ allows the model to explore the full Bloch Sphere
            layer_offset = L * params_per_layer
            for i in range(N_QUBITS):
                qml.RY(weights[layer_offset + i], wires=i)
                qml.RZ(weights[layer_offset + N_QUBITS + i], wires=i)

        return [qml.expval(qml.PauliZ(i)) for i in range(N_QUBITS)]

    class QuantumDDQN(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            # 5 layers * (N_QUBITS * 2) parameters
            self.num_layers = 5
            weight_shapes = {"weights": (self.num_layers * N_QUBITS * 2,)}
            
            self.quantum_layer = qml.qnn.TorchLayer(vqc, weight_shapes)
            
            # Added BatchNorm to help the linear heads handle the [-1, 1] vqc output
            self.bn = nn.BatchNorm1d(N_QUBITS)
            
            self.advantage = nn.Linear(N_QUBITS, N_ACTIONS)
            self.value = nn.Linear(N_QUBITS, 1)

            with torch.no_grad():
                for param in self.quantum_layer.parameters():
                    # Initializing with small random values instead of a constant 0.01
                    # helps break symmetry during early training.
                    param.fill_(0.01)

        def forward(self, state: torch.Tensor) -> torch.Tensor:
            q_out = self.quantum_layer(state)
            # Apply batch norm if batch size > 1 (handles training vs single inference)
            if q_out.shape[0] > 1:
                q_out = self.bn(q_out)
                
            adv = self.advantage(q_out)
            val = self.value(q_out)
            return val + adv - adv.mean(dim=1, keepdim=True)

else:

    def vqc(_inputs, _weights):
        raise RuntimeError("PennyLane is not installed")


    class QuantumDDQN(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            raise RuntimeError("QuantumDDQN requires pennylane. Install quantum/requirements.txt")


class ClassicalDDQN(nn.Module):
    def __init__(self, hidden_dim: int = N_QUBITS) -> None:
        super().__init__()
        self.feature = nn.Linear(N_QUBITS, hidden_dim)
        self.advantage = nn.Linear(hidden_dim, N_ACTIONS)
        self.value = nn.Linear(hidden_dim, 1)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        hidden = torch.tanh(self.feature(state))
        adv = self.advantage(hidden)
        val = self.value(hidden)
        return val + adv - adv.mean(dim=1, keepdim=True)
