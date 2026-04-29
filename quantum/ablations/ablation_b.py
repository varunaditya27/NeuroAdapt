import argparse
import json
import shutil
import subprocess
from pathlib import Path
import atexit

repo_root = Path(__file__).resolve().parents[2]

SHARED_CONFIG_PATH = repo_root / "shared_config.py"
TRAIN_PATH = repo_root / "quantum" / "train.py"

SHARED_CONFIG_BAK = SHARED_CONFIG_PATH.with_suffix(".py.bak")
TRAIN_BAK = TRAIN_PATH.with_suffix(".py.bak")

def backup_files():
    if not SHARED_CONFIG_BAK.exists():
        shutil.copy2(SHARED_CONFIG_PATH, SHARED_CONFIG_BAK)
    if not TRAIN_BAK.exists():
        shutil.copy2(TRAIN_PATH, TRAIN_BAK)

def restore_files():
    if SHARED_CONFIG_BAK.exists():
        shutil.copy2(SHARED_CONFIG_BAK, SHARED_CONFIG_PATH)
        SHARED_CONFIG_BAK.unlink()
    if TRAIN_BAK.exists():
        shutil.copy2(TRAIN_BAK, TRAIN_PATH)
        TRAIN_BAK.unlink()

atexit.register(restore_files)

def patch_for_ablation_b():
    # 1. Patch shared_config.py
    config_content = SHARED_CONFIG_PATH.read_text(encoding="utf-8")
    config_content = config_content.replace("ACTION_SPACE = 6", "ACTION_SPACE = 3")
    SHARED_CONFIG_PATH.write_text(config_content, encoding="utf-8")

    # 2. Patch train.py heuristic_action
    train_content = TRAIN_PATH.read_text(encoding="utf-8")
    
    original_heuristic = """def heuristic_action(state: list[float]) -> int:
    dwell, jitter, focus, stall, pref_delta = state

    if max(stall, jitter) > 0.75:
        return 5
    if dwell > 0.70:
        return 2
    if pref_delta > 0.70:
        return 3
    if stall > 0.55:
        return 4
    if focus < 0.25:
        return 1
    return 0"""

    patched_heuristic = """def heuristic_action(state: list[float]) -> int:
    dwell, jitter, focus, stall, pref_delta = state

    if max(stall, jitter) > 0.75:
        return 2 # mapped to break
    if dwell > 0.70:
        return 1 # mapped to simplify
    if pref_delta > 0.70:
        return 1 # mapped to simplify
    if stall > 0.55:
        return 2 # mapped to break
    if focus < 0.25:
        return 1 # mapped to simplify
    return 0"""
    
    if original_heuristic in train_content:
        train_content = train_content.replace(original_heuristic, patched_heuristic)
        TRAIN_PATH.write_text(train_content, encoding="utf-8")
    else:
        print("Warning: Could not find heuristic_action to patch in train.py")

def _save_plot(history_3_actions, history_6_actions, output_path: Path):
    try:
        import matplotlib.pyplot as plt
        
        def ma20(x, w=20):
            out = []
            s = 0.0
            for i, v in enumerate(x):
                s += v
                if i >= w: s -= x[i - w]
                out.append(s / min(i + 1, w))
            return out

        plt.figure(figsize=(10, 5))
        if history_6_actions:
            plt.plot(ma20(history_6_actions), label="6 Actions (Baseline MA20)", color='#1f63ff', linewidth=2.2)
        if history_3_actions:
            plt.plot(ma20(history_3_actions), label="3 Actions (Ablation B MA20)", color='#d9531e', linewidth=2.2)
            
        plt.title("Ablation B: Action Space Reduction (3 vs 6 Actions)")
        plt.xlabel("Episode")
        plt.ylabel("Preference Delta (lower is better)")
        plt.legend()
        plt.grid(alpha=0.25)
        plt.tight_layout()
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path)
        plt.close()
    except Exception as e:
        print(f"Plotting failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Run Ablation B: Action Space Reduction")
    parser.add_argument("--episodes", type=int, default=300)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    print("--- Backing up files ---")
    backup_files()

    print("--- Patching files for 3-action space ---")
    patch_for_ablation_b()

    print("--- Running training with 3 actions ---")
    # Run in subprocess to ensure fresh module imports
    cmd = [
        "python", str(TRAIN_PATH),
        "--episodes", str(args.episodes),
        "--model", "quantum",
        "--checkpoint-prefix", "ablation_b_3actions",
        "--seed", str(args.seed),
    ]
    subprocess.run(cmd, check=True)

    print("--- Restoring original files ---")
    restore_files()

    # Try to load baseline (6 actions) for comparison
    baseline_history = []
    baseline_path = repo_root / f"quantum/checkpoints/ablation_quantum_seed{args.seed}_history.json"
    if baseline_path.exists():
        with open(baseline_path, "r", encoding="utf-8") as f:
            baseline_history = json.load(f).get("preference_delta_history", [])

    ablation_history = []
    ablation_path = repo_root / "quantum/checkpoints/ablation_b_3actions_history.json"
    if ablation_path.exists():
        with open(ablation_path, "r", encoding="utf-8") as f:
            ablation_history = json.load(f).get("preference_delta_history", [])

    output_png = repo_root / "quantum/ablation_b_action_space.png"
    _save_plot(ablation_history, baseline_history, output_png)
    print(f"\nSaved comparison plot to {output_png}")

if __name__ == "__main__":
    main()
