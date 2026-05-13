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
    import pennylane as qml # type: ignore
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
        
        # Increase depth for research-grade complexity
        NUM_LAYERS = 5
        params_per_layer = 2 * N_QUBITS
 
        for L in range(NUM_LAYERS):
            if L < DATA_REUPLOAD_LAYERS:
                for i in range(N_QUBITS):
                    # RY encoding is more stable for real-plane tabular input
                    qml.RY(encoded_inputs[:, i] * PI * input_scales[L, i], wires=i)
            
            qml.BasicEntanglerLayers(weights[L:L+1], wires=range(N_QUBITS))
 
        # Standardized measurements + Entangling terms (7 outputs)
        return [qml.expval(qml.PauliZ(i)) for i in range(N_QUBITS)]

    class QuantumDDQN(nn.Module):
        def __init__(self, n_actions: int = N_ACTIONS) -> None:
            super().__init__()
            # 5 layers for deeper feature extraction
            self.num_layers = 5
            self.data_reupload_layers = DATA_REUPLOAD_LAYERS
            # Weights for BasicEntanglerLayers are (layers, wires)
            weight_shapes = {
                "weights": (self.num_layers, N_QUBITS),
                "input_scales": (self.data_reupload_layers, N_QUBITS),
            }
            
            self.quantum_layer = qml.qnn.TorchLayer(vqc, weight_shapes)
            # Output from VQC is 5 raw measurements
            
            self.bottleneck = nn.Sequential(
                nn.Linear(5, 64),
                nn.ReLU()
            )
            
            self.advantage = nn.Linear(64, n_actions)
            self.value = nn.Linear(64, 1)

            with torch.no_grad():
                for name, param in self.quantum_layer.named_parameters():
                    if "input_scales" in name:
                        nn.init.uniform_(param, a=0.1, b=0.5)
                    else:
                        # Start broad so the circuit is not trapped in near-identity behavior.
                        nn.init.uniform_(param, a=-0.1, b=0.1)

                nn.init.xavier_uniform_(self.bottleneck[0].weight)
                nn.init.zeros_(self.bottleneck[0].bias)

                nn.init.xavier_uniform_(self.advantage.weight)
                nn.init.zeros_(self.advantage.bias)
                nn.init.xavier_uniform_(self.value.weight)
                nn.init.zeros_(self.value.bias)

        def forward(self, state: torch.Tensor) -> torch.Tensor:
            state = state * 3.14159
            q_out = self.quantum_layer(state)
            
            bottleneck_out = self.bottleneck(q_out)
                
            adv = self.advantage(bottleneck_out)
            val = self.value(bottleneck_out)
            return val + adv - adv.mean(dim=1, keepdim=True)

else:

    def vqc(_inputs, _weights):
        raise RuntimeError("PennyLane is not installed")


    class QuantumDDQN(nn.Module):
        def __init__(self, n_actions: int = N_ACTIONS) -> None:
            super().__init__()
            raise RuntimeError("QuantumDDQN requires pennylane. Install quantum/requirements.txt")


class ClassicalDDQN(nn.Module):
    def __init__(self, hidden_dim: int = 64, n_actions: int = N_ACTIONS) -> None:
        super().__init__()
        self.feature = nn.Linear(N_QUBITS, hidden_dim)
        self.advantage = nn.Linear(hidden_dim, n_actions)
        self.value = nn.Linear(hidden_dim, 1)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        state = (state - 0.5) * 2.0
        hidden = torch.tanh(self.feature(state))
        adv = self.advantage(hidden)
        val = self.value(hidden)
        return val + adv - adv.mean(dim=1, keepdim=True)
