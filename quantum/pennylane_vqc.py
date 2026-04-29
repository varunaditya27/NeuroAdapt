from __future__ import annotations

import math
import torch
import torch.nn as nn

try:
    from backend.shared_config import N_ACTIONS, N_QUBITS
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.shared_config import N_ACTIONS, N_QUBITS

try:
    import pennylane as qml
except Exception:  # pragma: no cover
    qml = None


if qml is not None:
    dev = qml.device("default.qubit", wires=N_QUBITS)
    PI = 3.141592653589793

    # weights layout: 5 variational layers × 2 gates × N_QUBITS params.
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
    DATA_REUPLOAD_LAYERS = 2

    @qml.qnode(dev, interface="torch", diff_method="backprop")
    def vqc(inputs, weights, input_scales):
        encoded_inputs = qml.math.reshape(inputs, (-1, N_QUBITS))
        
        # We use 5 layers now to give the VQC enough "depth" to match classical performance
        # Each layer needs 2 * N_QUBITS parameters (one for RY, one for RZ)
        NUM_LAYERS = 5 
        params_per_layer = 2 * N_QUBITS

        for L in range(NUM_LAYERS):
            # --- Data Re-uploading ---
            # Re-upload only in early layers to limit excessive periodic collapse.
            if L < DATA_REUPLOAD_LAYERS:
                for i in range(N_QUBITS):
                    qml.RX(encoded_inputs[:, i] * PI * input_scales[L, i], wires=i)

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

        # Final global entanglement to ensure all features are correlated
        for i in range(N_QUBITS):
            qml.CNOT(wires=[i, (i + 1) % N_QUBITS])

        return [qml.expval(qml.PauliZ(i) if i % 2 == 0 else qml.PauliX(i)) for i in range(N_QUBITS)]

    class QuantumDDQN(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            # 5 layers * (N_QUBITS * 2) parameters
            self.num_layers = 5
            self.data_reupload_layers = DATA_REUPLOAD_LAYERS
            weight_shapes = {
                "weights": (self.num_layers * N_QUBITS * 2,),
                "input_scales": (self.data_reupload_layers, N_QUBITS),
            }
            
            self.quantum_layer = qml.qnn.TorchLayer(vqc, weight_shapes)

            # LayerNorm is stable for both batch and single-sample inference.
            self.norm = nn.LayerNorm(N_QUBITS)
            # Backward-compatible alias used by existing optimizer code.
            self.bn = self.norm
            
            self.advantage = nn.Linear(N_QUBITS, N_ACTIONS)
            self.value = nn.Linear(N_QUBITS, 1)

            with torch.no_grad():
                for name, param in self.quantum_layer.named_parameters():
                    if "input_scales" in name:
                        nn.init.uniform_(param, a=0.1, b=0.5)
                    else:
                        # Start broad so the circuit is not trapped in near-identity behavior.
                        nn.init.uniform_(param, a=-math.pi, b=math.pi)

                nn.init.xavier_uniform_(self.advantage.weight)
                nn.init.zeros_(self.advantage.bias)
                nn.init.xavier_uniform_(self.value.weight)
                nn.init.zeros_(self.value.bias)

        def forward(self, state: torch.Tensor) -> torch.Tensor:
            q_out = self.quantum_layer(state)
            q_out = self.norm(q_out)
                
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
    def __init__(self, hidden_dim: int = 64) -> None:
        super().__init__()
        self.feature = nn.Linear(N_QUBITS, hidden_dim)
        self.advantage = nn.Linear(hidden_dim, N_ACTIONS)
        self.value = nn.Linear(hidden_dim, 1)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        hidden = torch.tanh(self.feature(state))
        adv = self.advantage(hidden)
        val = self.value(hidden)
        return val + adv - adv.mean(dim=1, keepdim=True)
