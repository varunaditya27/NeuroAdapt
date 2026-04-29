from __future__ import annotations

import argparse
import json
import statistics
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


def _mean_and_std(series_list: list[list[float]]) -> tuple[list[float], list[float]]:
    means: list[float] = []
    stds: list[float] = []
    for index in range(len(series_list[0])):
        values = [series[index] for series in series_list]
        means.append(float(statistics.mean(values)))
        stds.append(float(statistics.pstdev(values)))
    return means, stds


def _save_plot_or_csv(
    quantum_mean: list[float],
    classical_mean: list[float],
    output: Path,
    quantum_std: list[float] | None = None,
    classical_std: list[float] | None = None,
) -> None:
    try:
        import matplotlib.pyplot as plt
        import numpy as np

        x = np.arange(len(quantum_mean))

        plt.figure(figsize=(10, 5))
        plt.plot(quantum_mean, label="VQC DDQN", linewidth=2)
        plt.plot(classical_mean, label="Classical DDQN", linewidth=2)

        if quantum_std is not None and classical_std is not None:
            q_std_arr = np.array(quantum_std)
            c_std_arr = np.array(classical_std)
            plt.fill_between(x, np.array(quantum_mean) - q_std_arr, np.array(quantum_mean) + q_std_arr, alpha=0.2)
            plt.fill_between(x, np.array(classical_mean) - c_std_arr, np.array(classical_mean) + c_std_arr, alpha=0.2)

        plt.title("Ablation C Long Run: Raw")
        plt.xlabel("Episode")
        plt.ylabel("Preference Delta (lower is better)")
        plt.legend()
        plt.grid(alpha=0.25)
        plt.tight_layout()
        plt.savefig(output)
        plt.close()

        def ma20(x, w=20):
            out = []
            s = 0.0
            for i, v in enumerate(x):
                s += v
                if i >= w: s -= x[i - w]
                out.append(s / min(i + 1, w))
            return out

        plt.figure(figsize=(10, 5))
        plt.plot(ma20(quantum_mean), label="VQC DDQN (MA20)", color='#1f63ff', linewidth=2.2)
        plt.plot(ma20(classical_mean), label="Classical DDQN (MA20)", color='#d9531e', linewidth=2.2)

        if quantum_std is not None and classical_std is not None:
            plt.fill_between(x, np.array(ma20(quantum_mean)) - np.array(ma20(quantum_std)), np.array(ma20(quantum_mean)) + np.array(ma20(quantum_std)), color='#1f63ff', alpha=0.15)
            plt.fill_between(x, np.array(ma20(classical_mean)) - np.array(ma20(classical_std)), np.array(ma20(classical_mean)) + np.array(ma20(classical_std)), color='#d9531e', alpha=0.15)

        plt.title("Ablation C Long Run: MA20 Smoothed")
        plt.xlabel("Episode")
        plt.ylabel("Preference Delta (lower is better)")
        plt.legend()
        plt.grid(alpha=0.25)
        plt.tight_layout()
        
        smoothed_out = Path(str(output).replace(".png", "_smoothed.png"))
        plt.savefig(smoothed_out)
        plt.close()
    except Exception:
        fallback = output.with_suffix(".json")
        fallback.write_text(
            json.dumps(
                {
                    "quantum_preference_delta_mean": quantum_mean,
                    "classical_preference_delta_mean": classical_mean,
                    "quantum_preference_delta_std": quantum_std,
                    "classical_preference_delta_std": classical_std,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


def _parse_seeds(raw: str) -> list[int]:
    return [int(token.strip()) for token in raw.split(",") if token.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Ablation C: VQC vs Classical")
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--steps-per-episode", type=int, default=20)
    parser.add_argument("--output", type=str, default="quantum/ablation_c_convergence.png")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--seeds", type=str, default="7")
    parser.add_argument("--quantum-lr", type=float, default=1e-4)
    parser.add_argument("--classical-lr", type=float, default=1e-4)
    parser.add_argument("--epsilon-decay-episodes", type=int, default=40)
    parser.add_argument("--quantum-layer-lr", type=float, default=2e-4)
    parser.add_argument("--quantum-head-lr", type=float, default=1e-4)
    parser.add_argument("--classical-hidden-dim", type=int, default=64)
    parser.add_argument("--reward-mode", choices=["dataset", "exp-distance"], default="exp-distance")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    seeds = _parse_seeds(args.seeds)
    if not seeds:
        seeds = [args.seed]

    quantum_histories: list[list[float]] = []
    classical_histories: list[list[float]] = []

    for seed in seeds:
        quantum_result = run_training(
            episodes=args.episodes,
            model_type="quantum",
            steps_per_episode=args.steps_per_episode,
            checkpoint_every=max(1, args.episodes),
            checkpoint_prefix=f"ablation_quantum_seed{seed}",
            learning_rate=args.quantum_head_lr,
            enable_wandb=False,
            wandb_project="neuroadapt-ablation-c",
            write_latest=False,
            seed=seed,
            epsilon_decay_episodes=args.epsilon_decay_episodes,
            classical_hidden_dim=args.classical_hidden_dim,
            quantum_layer_lr=args.quantum_layer_lr,
            quantum_head_lr=args.quantum_head_lr,
            reward_mode=args.reward_mode,
        )

        classical_result = run_training(
            episodes=args.episodes,
            model_type="classical",
            steps_per_episode=args.steps_per_episode,
            checkpoint_every=max(1, args.episodes),
            checkpoint_prefix=f"ablation_classical_seed{seed}",
            learning_rate=args.classical_lr,
            enable_wandb=False,
            wandb_project="neuroadapt-ablation-c",
            write_latest=False,
            seed=seed,
            epsilon_decay_episodes=args.epsilon_decay_episodes,
            classical_hidden_dim=args.classical_hidden_dim,
            reward_mode=args.reward_mode,
        )

        quantum_histories.append(quantum_result.preference_delta_history)
        classical_histories.append(classical_result.preference_delta_history)

    quantum_mean, quantum_std = _mean_and_std(quantum_histories)
    classical_mean, classical_std = _mean_and_std(classical_histories)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    _save_plot_or_csv(
        quantum_mean,
        classical_mean,
        output_path,
        quantum_std=quantum_std if len(seeds) > 1 else None,
        classical_std=classical_std if len(seeds) > 1 else None,
    )


if __name__ == "__main__":
    main()
