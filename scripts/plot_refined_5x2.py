import os
import numpy as np
import matplotlib.pyplot as plt

def load_window(path, t_start, t_end, chan=2):
    data = []
    with open(path, 'r') as f:
        for i, line in enumerate(f):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    t = float(parts[0])
                    if t < t_start: continue
                    if t > t_end: break
                    sig = float(parts[chan])
                    ref = float(parts[3])
                    data.append((t, sig, ref))
                except ValueError: pass
    return np.array(data)

def median_filter(data, window_size):
    if window_size < 2: return data
    half = window_size // 2
    padded = np.pad(data, (half, half), mode='edge')
    return np.array([np.median(padded[i:i+window_size]) for i in range(len(data))])

def plot_final_grid_tight():
    # cell: (cc_basename, cc_t, vc_basename, vc_t)
    cell_data = [
        ("VgluT2-I-Cell10-C-1", 2932.4, "VgluT2-I-Cell10-V", 2560.8),
        ("VGAT-I-Cell2-C", 244.1, "VGAT-I-Cell2-V", 63.4),
        ("VGAT-I-Cell9-C", 3334.2, "VGAT-I-Cell9-V", 2540.4),
        ("VgluT2-I-Cell2-C", 876.2, "VgluT2-I-Cell2-V", 180.5),
        ("VGAT-I-Cell8-C", 1787.0, "VGAT-I-Cell8-V", 74.0)
    ]
    
    num_cells = len(cell_data)
    fig, axes = plt.subplots(num_cells, 2, figsize=(16, 4 * num_cells), sharex=True)
    
    window_pre = 1.0
    window_post = 1.5
    
    for row, (cc_name, cc_t, vc_name, vc_t) in enumerate(cell_data):
        # --- Column 1: Current Clamp ---
        ax = axes[row, 0]
        # Load slightly more to ensure filtering doesn't hit edges
        rec = load_window(f"data/{cc_name}", cc_t - 1.5, cc_t + 2.0, chan=2)
        if len(rec) > 0:
            t, vm, ref = rec[:, 0], rec[:, 1], rec[:, 2]
            dt = np.median(np.diff(t)) if len(t) > 1 else 0.001
            if dt <= 0: dt = 0.001
            ref_smooth = median_filter(ref, int(0.1/dt))
            
            lp, lb = np.max(ref_smooth), np.min(ref_smooth)
            lt = lb + 0.20 * (lp - lb)
            lpi = np.argmax(ref_smooth)
            loi = 0
            for j in range(lpi, 0, -1):
                if ref_smooth[j] < lt:
                    loi = j + 1
                    break
            t_onset = t[loi]
            
            spike_indices = np.where((vm[:-1] <= -10) & (vm[1:] > -10))[0]
            t_spikes = t[spike_indices]
            bursts = []
            if len(t_spikes) > 0:
                cur = [t_spikes[0]]
                for k in range(1, len(t_spikes)):
                    if t_spikes[k] - t_spikes[k-1] <= 0.1: cur.append(t_spikes[k])
                    else:
                        if len(cur) >= 2: bursts.append(cur)
                        cur = [t_spikes[k]]
                if len(cur) >= 2: bursts.append(cur)
            
            coinciding = None
            for b in bursts:
                if b[0] < t_onset and b[-1] > t_onset:
                    coinciding = b
                    break
            if coinciding is None and len(bursts) > 0:
                coinciding = bursts[np.argmin([abs(b[0] - t_onset) for b in bursts])]
            
            tz = t - t_onset
            ax.plot(tz, vm, color='blue', lw=0.8)
            ref_norm = (ref_smooth - lb) / (lp - lb + 1e-9)
            ax.plot(tz, ref_norm * 35.0 - 90.0, color='green', lw=2, alpha=0.7)
            ax.axvline(0, color='green', linestyle='--', lw=2)
            
            if coinciding:
                t_start = coinciding[0] - t_onset
                # Only shade if within visible window [-1, 0]
                shade_start = max(-1.0, t_start)
                if shade_start < 0:
                    ax.axvspan(shade_start, 0, color='red', alpha=0.15)
                    ax.axvline(t_start, color='red', linestyle=':', lw=2)
                    lead_ms = -t_start * 1000
                    ax.annotate(f"Lead: {lead_ms:.0f} ms",
                                xy=(t_start, 0), xytext=(-40, 30), textcoords='offset points',
                                arrowprops=dict(arrowstyle="->", color='red'),
                                color='red', fontweight='bold', fontsize=9)

            ax.set_ylabel(f"{cc_name}\nVm (mV)", fontsize=10)
            if row == 0: ax.set_title("Current Clamp", fontsize=12)
            ax.set_ylim(-105, 50)
            ax.grid(alpha=0.2)

        # --- Column 2: Voltage Clamp ---
        ax = axes[row, 1]
        rec = load_window(f"data/{vc_name}", vc_t - 1.5, vc_t + 2.0, chan=1)
        if len(rec) > 0:
            t, inj, ref = rec[:, 0], rec[:, 1], rec[:, 2]
            dt = np.median(np.diff(t)) if len(t) > 1 else 0.001
            if dt <= 0: dt = 0.001
            ref_smooth = median_filter(ref, int(0.1/dt))
            inj_smooth = median_filter(inj, int(0.05/dt))
            
            lp, lb = np.max(ref_smooth), np.min(ref_smooth)
            lt = lb + 0.20 * (lp - lb)
            lpi = np.argmax(ref_smooth)
            loi = 0
            for j in range(lpi, 0, -1):
                if ref_smooth[j] < lt:
                    loi = j + 1
                    break
            t_onset = t[loi]
            
            base_inj = np.median(inj_smooth[:int(0.5/dt)])
            std_inj = np.std(inj_smooth[:int(0.5/dt)]) + 1e-9
            thresh_inj = base_inj - max(3 * std_inj, 0.02)
            idx_peak_vc = np.argmin(inj_smooth)
            idx_onset_vc = 0
            for j in range(idx_peak_vc, 0, -1):
                if inj_smooth[j] > thresh_inj:
                    idx_onset_vc = j + 1
                    break
            t_vc_onset = t[idx_onset_vc]
            
            tz = t - t_onset
            ax.plot(tz, inj, color='blue', lw=0.5, alpha=0.3)
            ax.plot(tz, inj_smooth, color='blue', lw=1.2)
            
            y_min, y_max = np.min(inj_smooth), np.max(inj_smooth)
            ref_norm = (ref_smooth - lb) / (lp - lb + 1e-9)
            ref_mapped = ref_norm * (y_max - y_min) * 0.5 + y_min
            ax.plot(tz, ref_mapped, color='green', lw=2, alpha=0.8)
            ax.axvline(0, color='green', linestyle='--', lw=2)
            
            t_lead_vc = t_vc_onset - t_onset
            shade_start_vc = max(-1.0, t_lead_vc)
            if shade_start_vc < 0:
                ax.axvspan(shade_start_vc, 0, color='red', alpha=0.1)
                ax.axvline(t_lead_vc, color='red', linestyle=':', lw=2)
                ax.annotate(f"I-Lead: {-t_lead_vc*1000:.0f} ms",
                            xy=(t_lead_vc, y_max), xytext=(-40, 10), textcoords='offset points',
                            arrowprops=dict(arrowstyle="->", color='red'),
                            color='red', fontweight='bold', fontsize=9)

            ax.set_ylabel("I (nA)", fontsize=10)
            if row == 0: ax.set_title("Voltage Clamp", fontsize=12)
            ax.grid(alpha=0.2)

    for col in range(2):
        axes[-1, col].set_xlabel("Time from HNA Onset (s)")
        axes[-1, col].set_xlim(-1.0, 1.5)

    plt.tight_layout()
    out_path = os.path.join("publication", "figures", "supp_figure4_pre_i_recruitment.png")
    plt.savefig(out_path, dpi=300)
    print(f"Saved plot to {out_path}")

if __name__ == "__main__":
    plot_final_grid_tight()
