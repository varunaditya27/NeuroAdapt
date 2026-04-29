"""Circuit Visualization Module

Generates PNG circuit diagrams for the Variational Quantum Circuit (VQC).
Used for documentation, reporting, and debugging quantum circuit structure.

Owner: Prarthana (W&B dashboard integration, report generation)
"""

from __future__ import annotations

import math
from pathlib import Path

try:
    from shared_config import N_QUBITS
except ModuleNotFoundError:
    import sys
    from pathlib import Path as PathlibPath

    repo_root = PathlibPath(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from shared_config import N_QUBITS

try:
    import pennylane as qml
    import numpy as np
except ImportError as e:
    raise ImportError(
        "visualise_circuit.py requires pennylane and numpy. "
        "Install quantum/requirements.txt: pip install -r quantum/requirements.txt"
    ) from e


def visualise_vqc_circuit(
    output_path: str = "quantum/circuit_diagram.png",
    include_measurements: bool = True,
    width: int = 1024,
) -> str:
    """
    Generate a PNG diagram of the Variational Quantum Circuit (VQC).

    The circuit structure:
      Layer 0-1: Data Re-uploading (RX gates with input scaling)
      Layer 0-4: Entanglement patterns (alternating CNOT chains)
      Layer 0-4: Variational gates (RY + RZ per qubit)
      Final: Global entanglement (circular CNOT)
      Measurements: PauliZ (even qubits) / PauliX (odd qubits)

    Parameters
    ----------
    output_path : str
        Path where PNG diagram will be saved (relative to repo root).
        Default: "quantum/circuit_diagram.png"
    include_measurements : bool
        Whether to include measurement gates in the diagram.
        Default: True
    width : int
        Width of the output PNG in pixels. Larger values = more readable.
        Default: 1024

    Returns
    -------
    str
        Absolute path to the generated PNG file.

    Raises
    ------
    ImportError
        If PennyLane is not installed.
    """
    # Validate output path
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Create a device for circuit construction
    dev = qml.device("default.qubit", wires=N_QUBITS)

    # Build circuit with dummy parameters for visualization
    # The circuit structure must match the VQC in pennylane_vqc.py
    @qml.qnode(dev)
    def vqc_viz_circuit(inputs, weights, input_scales):
        """VQC circuit with visualization annotations."""
        NUM_LAYERS = 5
        DATA_REUPLOAD_LAYERS = 2
        PI = 3.141592653589793
        params_per_layer = 2 * N_QUBITS

        encoded_inputs = qml.math.reshape(inputs, (-1, N_QUBITS))

        for L in range(NUM_LAYERS):
            # --- Data Re-uploading (layers 0-1) ---
            if L < DATA_REUPLOAD_LAYERS:
                for i in range(N_QUBITS):
                    qml.RX(
                        encoded_inputs[:, i] * PI * input_scales[L, i],
                        wires=i,
                    )

            # --- Entanglement Layer ---
            # Alternating patterns: chain vs. circular
            if L % 2 == 0:
                for i in range(N_QUBITS - 1):
                    qml.CNOT(wires=[i, i + 1])
            else:
                qml.CNOT(wires=[N_QUBITS - 1, 0])  # Circular
                for i in range(N_QUBITS - 1, 0, -1):
                    qml.CNOT(wires=[i, i - 1])

            # --- Variational Layer (RY + RZ) ---
            layer_offset = L * params_per_layer
            for i in range(N_QUBITS):
                qml.RY(weights[layer_offset + i], wires=i)
                qml.RZ(weights[layer_offset + N_QUBITS + i], wires=i)

        # Final global entanglement
        for i in range(N_QUBITS):
            qml.CNOT(wires=[i, (i + 1) % N_QUBITS])

        # Measurements
        if include_measurements:
            return [
                qml.expval(qml.PauliZ(i) if i % 2 == 0 else qml.PauliX(i))
                for i in range(N_QUBITS)
            ]
        return []

    # Create dummy parameters
    dummy_inputs = np.random.rand(N_QUBITS)
    dummy_weights = np.random.uniform(-math.pi, math.pi, (5 * N_QUBITS * 2,))
    dummy_input_scales = np.random.uniform(0.1, 0.5, (2, N_QUBITS))

    # Draw circuit
    try:
        circuit_drawer = qml.draw(vqc_viz_circuit, decimals=2)
        circuit_text = circuit_drawer(dummy_inputs, dummy_weights, dummy_input_scales)
        print(circuit_text)
    except Exception as e:
        print(f"Warning: Could not generate text circuit diagram: {e}")

    # Save as PNG using matplotlib (if available)
    try:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(12, 8))
        ax.text(
            0.5,
            0.5,
            "VQC Circuit Diagram\n\n"
            f"Configuration:\n"
            f"  Qubits: {N_QUBITS}\n"
            f"  Layers: 5\n"
            f"  Parameters: {5 * N_QUBITS * 2} (weights + input scales)\n"
            f"  Data Re-upload Layers: 2\n\n"
            f"Structure:\n"
            f"  1. Data Encoding (RX)\n"
            f"  2. Entanglement (alternating CNOT patterns)\n"
            f"  3. Variational (RY + RZ per qubit)\n"
            f"  4. Final Global Entanglement (circular CNOT)\n"
            f"  5. Measurements (PauliZ/PauliX)\n",
            ha="center",
            va="center",
            fontsize=11,
            family="monospace",
        )
        ax.axis("off")
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches="tight")
        plt.close()

        abs_path = output_file.resolve()
        print(f"[visualise_circuit] Circuit diagram saved to {abs_path}")
        return str(abs_path)

    except ImportError:
        print(
            "Warning: matplotlib not available. Skipping PNG generation. "
            "Install: pip install matplotlib"
        )
        return ""
    except Exception as e:
        print(f"Error saving circuit diagram: {e}")
        raise


def visualise_vqc_architecture(
    output_path: str = "quantum/vqc_architecture.png",
) -> str:
    """
    Generate a high-level architecture diagram showing VQC → DDQN flow.

    Useful for understanding the full model pipeline:
      State Vector (5D) → VQC (feature extractor) → DDQN (Q-values) → Actions

    Parameters
    ----------
    output_path : str
        Path where PNG diagram will be saved.
        Default: "quantum/vqc_architecture.png"

    Returns
    -------
    str
        Absolute path to the generated PNG file.
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 6)
        ax.axis("off")

        # Title
        ax.text(
            5, 5.5, "NeuroAdapt: VQC → DDQN Pipeline", ha="center", fontsize=14, weight="bold"
        )

        # State Vector box
        state_box = FancyBboxPatch(
            (0.5, 3.5),
            1.5,
            1.2,
            boxstyle="round,pad=0.1",
            edgecolor="blue",
            facecolor="lightblue",
            linewidth=2,
        )
        ax.add_patch(state_box)
        ax.text(1.25, 4.1, "State Vector\n(5D)", ha="center", va="center", fontsize=9, weight="bold")
        ax.text(
            1.25,
            3.7,
            "dwell, jitter,\nfocus, stall,\npref_delta",
            ha="center",
            va="center",
            fontsize=7,
        )

        # VQC box
        vqc_box = FancyBboxPatch(
            (2.75, 3.5),
            2,
            1.2,
            boxstyle="round,pad=0.1",
            edgecolor="green",
            facecolor="lightgreen",
            linewidth=2,
        )
        ax.add_patch(vqc_box)
        ax.text(3.75, 4.3, "VQC Circuit", ha="center", va="center", fontsize=9, weight="bold")
        ax.text(
            3.75,
            3.85,
            "5 qubits × 5 layers\n50 parameters",
            ha="center",
            va="center",
            fontsize=7,
        )

        # DDQN box
        ddqn_box = FancyBboxPatch(
            (5.25, 3.5),
            2,
            1.2,
            boxstyle="round,pad=0.1",
            edgecolor="purple",
            facecolor="plum",
            linewidth=2,
        )
        ax.add_patch(ddqn_box)
        ax.text(6.25, 4.3, "DDQN", ha="center", va="center", fontsize=9, weight="bold")
        ax.text(
            6.25,
            3.85,
            "Dueling streams\n6 actions",
            ha="center",
            va="center",
            fontsize=7,
        )

        # Action box
        action_box = FancyBboxPatch(
            (7.75, 3.5),
            1.5,
            1.2,
            boxstyle="round,pad=0.1",
            edgecolor="red",
            facecolor="lightcoral",
            linewidth=2,
        )
        ax.add_patch(action_box)
        ax.text(8.5, 4.1, "Action ID", ha="center", va="center", fontsize=9, weight="bold")
        ax.text(
            8.5,
            3.7,
            "Gated by\nconfidence\n(0.60)",
            ha="center",
            va="center",
            fontsize=7,
        )

        # Arrows
        arrow1 = FancyArrowPatch(
            (2.0, 4.1),
            (2.75, 4.1),
            arrowstyle="->",
            mutation_scale=20,
            linewidth=2,
            color="black",
        )
        ax.add_patch(arrow1)

        arrow2 = FancyArrowPatch(
            (4.75, 4.1),
            (5.25, 4.1),
            arrowstyle="->",
            mutation_scale=20,
            linewidth=2,
            color="black",
        )
        ax.add_patch(arrow2)

        arrow3 = FancyArrowPatch(
            (7.25, 4.1),
            (7.75, 4.1),
            arrowstyle="->",
            mutation_scale=20,
            linewidth=2,
            color="black",
        )
        ax.add_patch(arrow3)

        # Info box
        info_text = (
            "Observer polls state → Redis → /api/action → VQC inference → ContentRenderer\n"
            "Telemetry: 30s interval | Action polling: 5s interval (configurable)\n"
            "Confidence gate prevents low-confidence actions from influencing content"
        )
        ax.text(
            5,
            1.5,
            info_text,
            ha="center",
            va="center",
            fontsize=8,
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
        )

        plt.tight_layout()
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_file, dpi=150, bbox_inches="tight")
        plt.close()

        abs_path = output_file.resolve()
        print(f"[visualise_circuit] Architecture diagram saved to {abs_path}")
        return str(abs_path)

    except ImportError:
        print(
            "Warning: matplotlib not available. Skipping architecture diagram. "
            "Install: pip install matplotlib"
        )
        return ""
    except Exception as e:
        print(f"Error saving architecture diagram: {e}")
        raise


if __name__ == "__main__":
    # Generate circuit and architecture diagrams
    print("[visualise_circuit] Generating circuit diagrams...")
    circuit_path = visualise_vqc_circuit()
    arch_path = visualise_vqc_architecture()

    if circuit_path:
        print(f"✓ Circuit diagram: {circuit_path}")
    if arch_path:
        print(f"✓ Architecture diagram: {arch_path}")
