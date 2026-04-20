from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__ is None or __package__ == "":
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

try:
    from quantum.train import run_training
except ModuleNotFoundError:
    from train import run_training


def _save_plot_or_csv(quantum_history: list[float], classical_history: list[float], output: Path) -> None:
    try:
        import matplotlib.pyplot as plt

        plt.figure(figsize=(10, 5))
        plt.plot(quantum_history, label="VQC DDQN", linewidth=2)
        plt.plot(classical_history, label="Classical DDQN", linewidth=2)
        plt.title("Ablation C: Preference Delta Convergence")
        plt.xlabel("Episode")
        plt.ylabel("Preference Delta (lower is better)")
        plt.legend()
        plt.grid(alpha=0.25)
        plt.tight_layout()
        plt.savefig(output)
        plt.close()
    except Exception:
        fallback = output.with_suffix(".json")
        fallback.write_text(
            json.dumps(
                {
                    "quantum_preference_delta": quantum_history,
                    "classical_preference_delta": classical_history,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Ablation C: VQC vs Classical")
    parser.add_argument("--episodes", type=int, default=300)
    parser.add_argument("--steps-per-episode", type=int, default=20)
    parser.add_argument("--output", type=str, default="quantum/ablation_c_convergence.png")
    parser.add_argument("--seed", type=int, default=7)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    quantum_result = run_training(
        episodes=args.episodes,
        model_type="quantum",
        steps_per_episode=args.steps_per_episode,
        checkpoint_every=max(1, args.episodes),
        checkpoint_prefix="ablation_quantum",
        learning_rate=1e-3,
        enable_wandb=False,
        wandb_project="neuroadapt-ablation-c",
        write_latest=False,
        seed=args.seed,
    )

    classical_result = run_training(
        episodes=args.episodes,
        model_type="classical",
        steps_per_episode=args.steps_per_episode,
        checkpoint_every=max(1, args.episodes),
        checkpoint_prefix="ablation_classical",
        learning_rate=1e-3,
        enable_wandb=False,
        wandb_project="neuroadapt-ablation-c",
        write_latest=False,
        seed=args.seed,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    _save_plot_or_csv(
        quantum_result.preference_delta_history,
        classical_result.preference_delta_history,
        output_path,
    )


if __name__ == "__main__":
    main()
