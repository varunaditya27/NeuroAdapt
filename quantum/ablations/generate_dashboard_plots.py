import json
import statistics
from pathlib import Path

def ma(series, w=20):
    if not series: return []
    out = []
    s = 0.0
    for i, v in enumerate(series):
        s += v
        if i >= w:
            s -= series[i - w]
        out.append(s / min(i + 1, w))
    return out

def get_mean_series(paths, key):
    series_list = []
    for p in paths:
        if p.exists():
            try:
                data = json.loads(p.read_text())
                if key in data:
                    series_list.append(data[key])
            except Exception as e:
                print(f"Failed to load {p}: {e}")
    if not series_list:
        return []
    
    min_len = min(len(s) for s in series_list)
    mean_series = []
    for i in range(min_len):
        vals = [s[i] for s in series_list]
        mean_series.append(statistics.mean(vals))
    return mean_series

def main():
    repo_root = Path(__file__).resolve().parents[2]
    ckpt = repo_root / "quantum" / "checkpoints"
    
    seeds = [3]
    
    qc_paths = [ckpt / f"ablation_quantum_seed{s}_history.json" for s in seeds]
    cl_paths = [ckpt / f"ablation_classical_seed{s}_history.json" for s in seeds]
    
    qc_pref = get_mean_series(qc_paths, "preference_delta_history")
    cl_pref = get_mean_series(cl_paths, "preference_delta_history")
    
    qc_rew = get_mean_series(qc_paths, "episode_rewards")
    cl_rew = get_mean_series(cl_paths, "episode_rewards")
    
    qc_ent = get_mean_series(qc_paths, "policy_action_entropy_history")
    cl_ent = get_mean_series(cl_paths, "policy_action_entropy_history")
    
    qc_loss = get_mean_series(qc_paths, "loss_history")
    cl_loss = get_mean_series(cl_paths, "loss_history")
    
    if not qc_pref or not cl_pref:
        print("Missing history JSONs for seeds.")
        return
        
    try:
        import matplotlib.pyplot as plt
        
        plt.style.use("bmh")
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle("NeuroAdapt Dashboard: Quantum vs Classical Baseline (Ablation C, Seed 3)", fontsize=16, fontweight='bold')
        
        episodes_qc = list(range(len(qc_pref)))
        episodes_cl = list(range(len(cl_pref)))
        
        # 1. Preference Delta
        ax = axes[0, 0]
        ax.plot(episodes_qc, ma(qc_pref), label="VQC-DDQN", color="#e6194b", linewidth=2)
        ax.plot(episodes_cl, ma(cl_pref), label="Classical DDQN", color="#4363d8", linestyle="--", linewidth=2)
        ax.set_title("Preference Delta (Lower is Better)")
        ax.set_xlabel("Episode")
        ax.set_ylabel("Delta")
        ax.legend()
        
        # 2. Episode Rewards
        ax = axes[0, 1]
        ax.plot(episodes_qc, ma(qc_rew), label="VQC-DDQN", color="#e6194b", linewidth=2)
        ax.plot(episodes_cl, ma(cl_rew), label="Classical DDQN", color="#4363d8", linestyle="--", linewidth=2)
        ax.set_title("Episode Rewards (Higher is Better)")
        ax.set_xlabel("Episode")
        ax.set_ylabel("Reward")
        ax.legend()
        
        # 3. Policy Action Entropy
        ax = axes[1, 0]
        ax.plot(episodes_qc, ma(qc_ent), label="VQC-DDQN", color="#e6194b", linewidth=2)
        ax.plot(episodes_cl, ma(cl_ent), label="Classical DDQN", color="#4363d8", linestyle="--", linewidth=2)
        ax.set_title("Policy Action Entropy (Action Distribution Spread)")
        ax.set_xlabel("Episode")
        ax.set_ylabel("Entropy")
        ax.legend()
        
        # 4. Loss
        ax = axes[1, 1]
        ax.plot(episodes_qc, ma(qc_loss), label="VQC-DDQN", color="#e6194b", linewidth=2)
        ax.plot(episodes_cl, ma(cl_loss), label="Classical DDQN", color="#4363d8", linestyle="--", linewidth=2)
        ax.set_title("Training Loss")
        ax.set_xlabel("Episode")
        ax.set_ylabel("Loss")
        ax.legend()
        
        plt.tight_layout()
        out_path = repo_root / "quantum" / "dashboard_plots_Seed3.png"
        plt.savefig(out_path, dpi=150)
        print(f"Saved dashboard plots to {out_path}")
        
    except ImportError:
        print("matplotlib not installed. Run 'pip install matplotlib'")
    except Exception as e:
        print(f"Plotting failed: {e}")

if __name__ == "__main__":
    main()
