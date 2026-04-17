import sys
import numpy as np
import matplotlib.pyplot as plt
from spike_repair import find_spike_peaks, repair_undersampled_spikes

def normalize_episode(data_file, out_file, t_start=1606, t_end=1610):
    data = []
    with open(data_file, 'r') as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 3:
                t = float(parts[0])
                if t >= t_start and t <= t_end:
                    vm = float(parts[2])
                    data.append((t, vm))
                elif t > t_end:
                    break

    data = np.array(data)
    if len(data) == 0:
        print("No data in this time range.")
        return

    t = data[:, 0]
    vm = data[:, 1]
    dt_candidates = np.diff(t)
    dt_candidates = dt_candidates[dt_candidates > 0]
    dt = np.median(dt_candidates) if len(dt_candidates) > 0 else 0.0001
    min_dist_pts = max(1, int(round(0.005 / dt))) # 5ms min distance

    peaks_idx = find_spike_peaks(vm, threshold=-30.0, min_distance=min_dist_pts)
    
    if len(peaks_idx) == 0:
        print("No spikes found.")
        return

    v_norm, repair_diag = repair_undersampled_spikes(
        vm, dt, peak_threshold=-30.0, base_threshold=-45.0
    )
    print(f'Average raw peak: {np.mean(vm[peaks_idx]):.2f} mV')
    print(f"Repaired peaks: {repair_diag.get('num_peaks', 0)}")
    print(f"Mean inferred lift: {repair_diag.get('mean_peak_lift', 0.0):.2f} mV")

    # Plot
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(t, vm, color='gray', lw=0.8, alpha=0.5, label='Raw Undersampled')
    ax.plot(t, v_norm, color='blue', lw=0.8, alpha=0.8, label='Normalized Peaks')

    norm_peaks_idx = find_spike_peaks(v_norm, threshold=-30.0, min_distance=min_dist_pts)
    ax.scatter(t[norm_peaks_idx], v_norm[norm_peaks_idx], color='red', s=10, zorder=5, label='Scaled Peaks')

    ax.set_title(f'Normalized Spikes using Template-Based Peak Repair\n{data_file} ({t_start}-{t_end}s)')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Vm (mV)')
    ax.legend(loc='lower left')
    plt.tight_layout()
    plt.savefig(out_file, dpi=300)
    print(f'Saved plot to {out_file}')
    
if __name__ == "__main__":
    if len(sys.argv) > 1:
        data_file = sys.argv[1]
        out_file = sys.argv[2]
        t_start = float(sys.argv[3]) if len(sys.argv) > 3 else 1606
        t_end = float(sys.argv[4]) if len(sys.argv) > 4 else 1610
        normalize_episode(data_file, out_file, t_start, t_end)
    else:
        normalize_episode('data/VGAT-E-Cell4-C', 'results/normalized_episode.png', 1606, 1610)
