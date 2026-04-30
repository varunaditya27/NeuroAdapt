import argparse
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
PYTHON_EXE = sys.executable


def remap_dataset_for_3_actions(original_dir: Path, target_dir: Path, seed: int = 0) -> None:
    """Copy dataset to target_dir with action indices rescaled to [0, 2].

    Uses floor-based balanced bucketing:
        new_action = old_action * 3 // 6   (equivalent to old_action // 2)
    Mapping: {0,1}→0, {2,3}→1, {4,5}→2 — exactly 2 original actions per bucket.

    Transitions within each file are shuffled to prevent the model learning
    a majority-class ordering bias inherited from the original dataset layout.
    """
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True)

    rng = random.Random(seed)
    action_counts = [0, 0, 0]

    for file in original_dir.glob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)

        transitions = data.get("transitions", [])
        for transition in transitions:
            old_action = int(transition.get("action", 0))
            new_action = old_action * 3 // 6  # floor-based: perfectly balanced
            transition["action"] = new_action
            action_counts[new_action] += 1

        # Shuffle to break any ordering bias from the original dataset
        rng.shuffle(transitions)
        data["transitions"] = transitions

        target_file = target_dir / file.name
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

    total = sum(action_counts)
    print(f"Remapped dataset written to {target_dir}")
    print(
        "Action balance: "
        + ", ".join(
            f"action {i}: {c} ({100 * c / total:.1f}%)"
            for i, c in enumerate(action_counts)
        )
    )


def _save_plot(history_3_actions: list, history_6_actions: list, output_path: Path) -> None:
    try:
        import matplotlib.pyplot as plt

        Y_MIN, Y_MAX = 0.15, 0.65

        def ma20(x: list, w: int = 20) -> list:
            out: list = []
            s = 0.0
            for i, v in enumerate(x):
                s += v
                if i >= w:
                    s -= x[i - w]
                out.append(s / min(i + 1, w))
            return out

        plt.figure(figsize=(10, 5))
        if history_6_actions:
            plt.plot(
                ma20(history_6_actions),
                label="6 Actions (Baseline MA20)",
                color="#1f63ff",
                linewidth=2.2,
            )
        if history_3_actions:
            plt.plot(
                ma20(history_3_actions),
                label="3 Actions (Ablation B MA20)",
                color="#d9531e",
                linewidth=2.2,
            )

        plt.title("Ablation B: Action Space Reduction (3 vs 6 Actions)")
        plt.xlabel("Episode")
        plt.ylabel("Preference Delta (lower is better)")
        plt.ylim(Y_MIN, Y_MAX)
        plt.legend()
        plt.grid(alpha=0.25)
        plt.tight_layout()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150)
        plt.close()
    except Exception as e:
        print(f"Plotting failed: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Ablation B: Action Space Reduction")
    parser.add_argument("--episodes", type=int, default=300)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    train_script = repo_root / "quantum" / "train.py"
    original_data_dir = repo_root / "quantum" / "data"
    remapped_data_dir = repo_root / "quantum" / "tmp_ablation_b_data"

    print("--- Remapping dataset actions to 3-action space ---")
    remap_dataset_for_3_actions(original_data_dir, remapped_data_dir, seed=args.seed)

    print("--- Running training with 3 actions (via --actions flag, no file patching) ---")
    cmd = [
        PYTHON_EXE, str(train_script),
        "--episodes", str(args.episodes),
        "--model", "quantum",
        "--checkpoint-prefix", "ablation_b_3actions",
        "--seed", str(args.seed),
        "--data-dir", str(remapped_data_dir),
        "--steps-per-episode", "20",
        "--epsilon-decay-episodes", "40",
        "--actions", "3",  # cleanly overrides output head size, no disk patching needed
    ]
    subprocess.run(cmd, check=True)

    # Cleanup remapped dataset
    if remapped_data_dir.exists():
        shutil.rmtree(remapped_data_dir)
        print("--- Cleaned up temporary remapped dataset ---")

    # Load histories for comparison plot
    baseline_history: list = []
    baseline_path = repo_root / f"quantum/checkpoints/ablation_quantum_seed{args.seed}_history.json"
    if baseline_path.exists():
        with open(baseline_path, "r", encoding="utf-8") as f:
            baseline_history = json.load(f).get("preference_delta_history", [])
    else:
        print(f"Warning: baseline history not found at {baseline_path}")

    ablation_history: list = []
    ablation_path = repo_root / "quantum/checkpoints/ablation_b_3actions_history.json"
    if ablation_path.exists():
        with open(ablation_path, "r", encoding="utf-8") as f:
            ablation_history = json.load(f).get("preference_delta_history", [])

    output_png = repo_root / "quantum/ablation_b_action_space.png"
    _save_plot(ablation_history, baseline_history, output_png)
    print(f"\nSaved comparison plot to {output_png}")


if __name__ == "__main__":
    main()
