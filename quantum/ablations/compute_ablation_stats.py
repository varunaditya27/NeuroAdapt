"""Compute summary statistics for Ablation A and B results."""
import json
import statistics
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
ckpt = repo_root / "quantum" / "checkpoints"

WINDOW = 20  # MA window


def ma(series, w=WINDOW):
    out, s = [], 0.0
    for i, v in enumerate(series):
        s += v
        if i >= w:
            s -= series[i - w]
        out.append(s / min(i + 1, w))
    return out


def final_mean(series, last_n=50):
    tail = series[-last_n:]
    return statistics.mean(tail)


# Ablation A
SIGNAL_NAMES = ["dwell", "jitter", "focus", "stall", "pref_delta"]
print("=" * 60)
print("ABLATION A - Observer Signal Importance (Preference Delta lower=better)")
print("=" * 60)

a_results = {}
for sig in SIGNAL_NAMES:
    path = ckpt / f"ablation_a_{sig}_history.json"
    if not path.exists():
        print(f"  {sig}: MISSING")
        continue
    data = json.loads(path.read_text())
    hist = data.get("preference_delta_history", [])
    if len(hist) < 10:
        print(f"  {sig}: only {len(hist)} ep - skipping (still running?)")
        continue
    smoothed = ma(hist)
    init = statistics.mean(hist[:20])
    final = final_mean(smoothed)
    a_results[sig] = {"init": init, "final": final, "n": len(hist)}
    print(f"  {sig:12s}: init={init:.4f}  final(MA20 last50)={final:.4f}  n={len(hist)}")

if a_results:
    worst = max(a_results, key=lambda k: a_results[k]["final"])
    best = min(a_results, key=lambda k: a_results[k]["final"])
    print(f"\n  >> Zeroing '{worst}' causes highest residual delta ({a_results[worst]['final']:.4f}) -> most critical signal")
    print(f"  >> Zeroing '{best}' has least impact ({a_results[best]['final']:.4f}) -> least critical signal")

# Ablation B
print()
print("=" * 60)
print("ABLATION B - Action Space Reduction (3 vs 6 Actions)")
print("=" * 60)

path_b = ckpt / "ablation_b_3actions_history.json"
path_baseline = ckpt / "ablation_quantum_seed7_history.json"

final_b = None
final_6 = None

if path_b.exists():
    hist_b = json.loads(path_b.read_text())["preference_delta_history"]
    smoothed_b = ma(hist_b)
    init_b = statistics.mean(hist_b[:20])
    final_b = final_mean(smoothed_b)
    print(f"  3-action: init={init_b:.4f}  final(MA20 last50)={final_b:.4f}  n={len(hist_b)}")

if path_baseline.exists():
    hist_6 = json.loads(path_baseline.read_text())["preference_delta_history"]
    smoothed_6 = ma(hist_6)
    init_6 = statistics.mean(hist_6[:20])
    final_6 = final_mean(smoothed_6)
    print(f"  6-action: init={init_6:.4f}  final(MA20 last50)={final_6:.4f}  n={len(hist_6)}")
    if final_b is not None:
        delta_gap = final_b - final_6
        print(f"\n  >> Action space reduction cost: +{delta_gap:.4f} preference delta")
        print(f"  >> 3-action final / 6-action final = {final_b/final_6:.2f}x")

print()
