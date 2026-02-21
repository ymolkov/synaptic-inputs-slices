import sys
import numpy as np
import matplotlib.pyplot as plt

def find_peaks(vm, threshold=-20.0, min_distance=50):
    peaks = []
    last_peak = -min_distance
    for i in range(1, len(vm) - 1):
        if vm[i] > threshold and vm[i] > vm[i-1] and vm[i] >= vm[i+1]:
            if i - last_peak >= min_distance:
                peaks.append(i)
                last_peak = i
    return np.array(peaks)

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
    dt = (t[-1] - t[0]) / len(t)
    if dt == 0: dt = 0.0001
    min_dist_pts = int(0.005 / dt) # 5ms min distance

    peaks_idx = find_peaks(vm, threshold=-20.0, min_distance=min_dist_pts)
    
    if len(peaks_idx) == 0:
        print("No spikes found.")
        return

    # Infer true heights using quadratic interpolation
    inferred_peaks = []
    for idx in peaks_idx:
        # We need 3 points: idx-1, idx, idx+1
        t_pts = t[idx-1:idx+2]
        v_pts = vm[idx-1:idx+2]
        
        # Fit parabola: V = a*x^2 + b*x + c, using indices [-1, 0, 1]
        x_centered = np.array([-1.0, 0.0, 1.0])
        coeffs = np.polyfit(x_centered, v_pts, 2)
        
        a, b, c = coeffs
        if a < 0: # It's a proper peak
            x_max = -b / (2*a)
            # if the inferred peak is too far outside the 3 points, fallback to raw
            if abs(x_max) > 1.0:
                inferred_peaks.append(v_pts[1])
            else:
                v_max = a*(x_max**2) + b*x_max + c
                inferred_peaks.append(max(v_pts[1], v_max)) # It should always be >= raw
        else:
            inferred_peaks.append(v_pts[1])
            
    # Target peak can be the 90th percentile of inferred
    target_peak = np.percentile(inferred_peaks, 90)
    print(f'Average raw peak: {np.mean(vm[peaks_idx]):.2f} mV')
    print(f'Average inferred peak: {np.mean(inferred_peaks):.2f} mV')
    print(f'Target peak for normalization: {target_peak:.2f} mV')

    # Normalize data
    v_norm = np.copy(vm)
    threshold_base = -30.0 # Scaling happens above this voltage

    for i, idx in enumerate(peaks_idx):
        inferred = inferred_peaks[i]
        
        # Find spike bounds above threshold
        left = idx
        while left > 0 and vm[left] > threshold_base:
            left -= 1
            
        right = idx
        while right < len(vm)-1 and vm[right] > threshold_base:
            right += 1
            
        segment = vm[left:right+1]
        
        if vm[idx] > threshold_base:
            scale_factor = (target_peak - threshold_base) / (vm[idx] - threshold_base)
            
            # Linearly stretch the voltage above threshold
            # v_new = threshold + (v_old - threshold) * scale
            v_norm[left:right+1] = threshold_base + (segment - threshold_base) * scale_factor

    # Plot
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(t, vm, color='gray', lw=0.8, alpha=0.5, label='Raw Undersampled')
    ax.plot(t, v_norm, color='blue', lw=0.8, alpha=0.8, label='Normalized Peaks')

    norm_peaks_idx = find_peaks(v_norm, threshold=-20.0, min_distance=min_dist_pts)
    ax.scatter(t[norm_peaks_idx], v_norm[norm_peaks_idx], color='red', s=10, zorder=5, label='Scaled Peaks')

    ax.axhline(target_peak, color='red', linestyle='--', lw=0.5, alpha=0.5, label=f'Target ({target_peak:.1f} mV)')

    ax.set_title(f'Normalized Spikes using Quadratic Interpolation\nVGAT-E-Cell4-C ({t_start}-{t_end}s)')
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
