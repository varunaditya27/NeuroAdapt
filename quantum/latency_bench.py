from __future__ import annotations

import argparse
import statistics
import time
from pathlib import Path

import torch

if __package__ is None or __package__ == "":
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

try:
    from quantum.pennylane_vqc import QuantumDDQN
except ModuleNotFoundError:
    from pennylane_vqc import QuantumDDQN
from backend.shared_config import N_QUBITS


def benchmark(iterations: int, checkpoint: str) -> tuple[float, float]:
    model = QuantumDDQN()

    checkpoint_path = Path(checkpoint)
    if checkpoint_path.exists():
        state_dict = torch.load(checkpoint_path, map_location="cpu")
        model.load_state_dict(state_dict)

    model.eval()

    timings = []
    with torch.no_grad():
        for _ in range(5):
            model(torch.rand(1, N_QUBITS))

        for _ in range(iterations):
            sample = torch.rand(1, N_QUBITS)
            start = time.perf_counter()
            model(sample)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            timings.append(elapsed_ms)

    p50 = statistics.median(timings)
    p99 = sorted(timings)[max(0, int(len(timings) * 0.99) - 1)]
    return p50, p99


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark quantum inference latency")
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--checkpoint", type=str, default="quantum/checkpoints/latest.pt")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    p50, p99 = benchmark(args.iterations, args.checkpoint)
    print(f"iterations={args.iterations}")
    print(f"p50_ms={p50:.3f}")
    print(f"p99_ms={p99:.3f}")


if __name__ == "__main__":
    main()
