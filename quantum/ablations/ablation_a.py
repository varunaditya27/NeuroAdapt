import argparse
import json
import shutil
import statistics
from pathlib import Path

if __package__ is None or __package__ == "":
    import sys
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from quantum.train import run_training

SIGNAL_NAMES = ["dwell", "jitter", "focus", "stall", "pref_delta"]

def create_zeroed_dataset(original_dir: Path, target_dir: Path, signal_index: int) -> None:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True)
    
    for file in original_dir.glob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        for transition in data.get("transitions", []):
            transition["state"][signal_index] = 0.0
            transition["next_state"][signal_index] = 0.0
            
        target_file = target_dir / file.name
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

def _mean_and_std(series_list: list[list[float]]) -> tuple[list[float], list[float]]:
    means: list[float] = []
    stds: list[float] = []
    for index in range(len(series_list[0])):
        values = [series[index] for series in series_list]
        means.append(float(statistics.mean(values)))
        stds.append(float(statistics.pstdev(values)))
    return means, stds

def _save_plot(histories: dict[str, list[float]], output: Path) -> None:
    try:
        import matplotlib.pyplot as plt
        
        plt.figure(figsize=(10, 5))
        for signal_name, history in histories.items():
            plt.plot(history, label=f"Zeroed: {signal_name}")
            
        plt.title("Ablation A: Observer Signal Importance")
        plt.xlabel("Episode")
        plt.ylabel("Preference Delta (lower is better)")
        plt.legend()
        plt.grid(alpha=0.25)
        plt.tight_layout()
        
        output.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output)
        plt.close()
    except Exception as e:
        print(f"Plotting failed: {e}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Run Ablation A: Observer Signal Importance")
    parser.add_argument("--episodes", type=int, default=300)
    parser.add_argument("--steps-per-episode", type=int, default=20)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--data-dir", type=str, default="quantum/data")
    parser.add_argument("--output", type=str, default="quantum/ablation_a_signals.png")
    args = parser.parse_args()

    original_data_dir = Path(args.data_dir)
    tmp_data_dir = Path("quantum/tmp_ablation_a_data")
    
    results = {}

    for i, signal_name in enumerate(SIGNAL_NAMES):
        print(f"\n--- Running Ablation A: Zeroing out '{signal_name}' ---")
        create_zeroed_dataset(original_data_dir, tmp_data_dir, i)
        
        result = run_training(
            episodes=args.episodes,
            model_type="quantum",
            steps_per_episode=args.steps_per_episode,
            checkpoint_every=args.episodes,
            checkpoint_prefix=f"ablation_a_{signal_name}",
            learning_rate=1e-4,
            enable_wandb=False,
            wandb_project="neuroadapt-ablation-a",
            write_latest=False,
            seed=args.seed,
            data_dir=str(tmp_data_dir),
            epsilon_decay_episodes=40,
        )
        
        results[signal_name] = result.preference_delta_history

    if tmp_data_dir.exists():
        shutil.rmtree(tmp_data_dir)

    # Calculate moving average for plotting
    def ma20(x, w=20):
        out = []
        s = 0.0
        for i, v in enumerate(x):
            s += v
            if i >= w: s -= x[i - w]
            out.append(s / min(i + 1, w))
        return out
        
    smoothed_results = {k: ma20(v) for k, v in results.items()}
    _save_plot(smoothed_results, Path(args.output))
    print(f"\nSaved plot to {args.output}")

if __name__ == "__main__":
    main()
