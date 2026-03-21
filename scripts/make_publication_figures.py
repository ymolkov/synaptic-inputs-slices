#!/usr/bin/env python3
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import csv
from figure_utils import run_analysis, load_params, TMP_DIR, RESULTS_DIR, PROJECT_ROOT
from spike_repair import repair_undersampled_spikes

PUBLICATION_DIR = os.path.join(PROJECT_ROOT, "publication")
FIG_DIR = os.path.join(PUBLICATION_DIR, "figures")
CAPTIONS_FILE = os.path.join(PUBLICATION_DIR, "captions.md")

os.makedirs(FIG_DIR, exist_ok=True)

def robust_polyfit(x, y, deg=1, iterations=1):
    """Linear regression with outlier detection based on residuals."""
    if len(x) < 3:
        return np.polyfit(x, y, deg)
    
    # First pass
    coeffs = np.polyfit(x, y, deg)
    p = np.poly1d(coeffs)
    residuals = y - p(x)
    sigma = np.std(residuals)
    
    # Second pass: exclude outliers
    threshold = 2.5 * sigma
    mask = np.abs(residuals) <= threshold
    
    if np.sum(mask) < 3: # Fallback if too many outliers
        return coeffs
        
    return np.polyfit(x[mask], y[mask], deg)

def figure_1_method_illustration():
    """Figure 1: Method Illustration using VgluT2-I-Cell2-C."""
    print("Generating Figure 1: Method Illustration...")
    basename = "VgluT2-I-Cell2-C"
    dat_path, ph_path, par_path = run_analysis(basename)
    
    dat = np.loadtxt(dat_path)
    ph = np.loadtxt(ph_path)
    params = load_params(par_path)
    
    plt.rcParams.update({
        "axes.labelsize": 16,
        "xtick.labelsize": 13,
        "ytick.labelsize": 13,
        "legend.fontsize": 13
    })
    fig = plt.figure(figsize=(13, 10))
    gs = gridspec.GridSpec(2, 2, wspace=0.28, hspace=0.32)
    
    # Filter valid bins
    ph_valid = ph[ph[:, 3] > 0]
    
    import matplotlib.ticker as ticker
    
    # --- Panel A: Linear Regressions ---
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.yaxis.set_major_locator(ticker.MaxNLocator(nbins=4, integer=True))
    target_phases = [0.0, 0.5]
    colors = ['red', 'blue']
    window = 0.001 
    
    for phi, color in zip(target_phases, colors):
        mask = (dat[:, 2] >= phi) & (dat[:, 2] < phi + window)
        pts = dat[mask]
        if len(pts) == 0: continue
            
        I_pts = pts[:, 3]
        V_pts = pts[:, 4]
        ax1.scatter(V_pts, I_pts, s=10, alpha=0.5, color=color, label=rf"$\phi \approx {phi}$", edgecolors='none')
        
        slope_py, intercept_py = robust_polyfit(V_pts, I_pts, 1)
        v_line = np.array([V_pts.min(), V_pts.max()])
        i_line = slope_py * v_line + intercept_py
        ax1.plot(v_line, i_line, color=color, linewidth=2, linestyle='--')

    ax1.set_xlabel("V (mV)")
    ax1.set_ylabel("I (nA)")
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    # --- Panel B: Wedge Plot ---
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.yaxis.set_major_locator(ticker.MaxNLocator(nbins=4, integer=True))
    G_vals = ph_valid[:, 0] * 1000.0 # uS -> nS
    I0_vals = ph_valid[:, 1]         # nA
    
    G_traj = np.concatenate([G_vals, [G_vals[0]]])
    I0_traj = np.concatenate([I0_vals, [I0_vals[0]]])
    ax2.plot(G_traj, I0_traj, color='black', linewidth=1, alpha=0.6)
    ax2.scatter(G_vals, I0_vals, color='black', s=5, alpha=0.6)
    
    Ei, Ee = params.get('Ei', -80.0), params.get('Ee', 0.0)
    g_start, E_leak = params.get('g', 0.0), params.get('E', -60.0)
    
    x_data_min, x_data_max = G_vals.min(), G_vals.max()
    y_data_min, y_data_max = I0_vals.min(), I0_vals.max()
    x_pad = 0.08 * (x_data_max - x_data_min if x_data_max > x_data_min else 1.0)
    y_pad = 0.08 * (y_data_max - y_data_min if y_data_max > y_data_min else 1.0)

    # Keep the upper limits driven by the measured wedge points, but extend the
    # lower-left corner enough to include the leak-point intersection.
    if Ei != Ee:
        g_intersection = 1000.0 * g_start
        offset_i = g_start * (Ei - E_leak)
        i0_intersection = (-Ei / 1000.0) * g_intersection + offset_i
        x_min = min(x_data_min, g_intersection) - x_pad
        y_min = min(y_data_min, i0_intersection) - y_pad
    else:
        offset_i = g_start * (Ei - E_leak)
        x_min = x_data_min - x_pad
        y_min = y_data_min - y_pad
    x_max = x_data_max + x_pad
    y_max = y_data_max + y_pad

    g_line = np.array([x_min, x_max])
    y_inh_line = (-Ei/1000.0)*g_line + offset_i
    ax2.plot(g_line, y_inh_line, color='blue', linestyle='--', label='Pure Inhibition')
    
    offset_e = g_start * (Ee - E_leak)
    y_exc_line = (-Ee/1000.0)*g_line + offset_e
    ax2.plot(g_line, y_exc_line, color='red', linestyle='--', label='Pure Excitation')

    ax2.set_xlim(x_min, x_max)
    ax2.set_ylim(y_min, y_max)
    ax2.set_xlabel("$G_{tot}$ (nS)")
    ax2.set_ylabel("$I_0$ (nA)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # --- Panel C: Reconstructed Conductances ---
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.yaxis.set_major_locator(ticker.MaxNLocator(nbins=4, integer=True))
    g_ns_factor = params.get('g', 1.0) * 1000.0
    phs = ph_valid[:, 6] / 1000.0
    gi = ph_valid[:, 4] * g_ns_factor
    ge = ph_valid[:, 5] * g_ns_factor
    sem = (ph_valid[:, 2] / np.sqrt(ph_valid[:, 3])) * 1000.0
    
    phs2 = np.concatenate([phs, phs + 1.0])
    gi2, ge2, sem2 = np.tile(gi, 2), np.tile(ge, 2), np.tile(sem, 2)
    
    ax3.fill_between(phs2, ge2, 0, color='red', alpha=0.5, label='$G_{exc}$', linewidth=0)
    ax3.fill_between(phs2, gi2, 0, color='blue', alpha=0.5, label='$G_{inh}$', linewidth=0)
    ax3.plot(phs2, sem2, color='black', linewidth=1, label='Error')
    
    ax3.set_xticks(np.arange(0, 2.1, 0.5))
    ax3.set_xlabel("Phase (2 cycles)")
    ax3.set_ylabel("Conductance (nS)")
    ax3.grid(True, alpha=0.3)

    # --- Panel D: Polar Conductance Plot ---
    ax4 = fig.add_subplot(gs[1, 1], projection='polar')
    theta = 2.0 * np.pi * phs
    theta_closed = np.concatenate([theta, [theta[0]]])
    ge_closed = np.concatenate([ge, [ge[0]]])
    gi_closed = np.concatenate([gi, [gi[0]]])
    sem_closed = np.concatenate([sem, [sem[0]]])
    max_cond = max(np.max(ge), np.max(gi)) if len(ge) > 0 else 1.0

    h_ge = ax4.fill(theta_closed, ge_closed, color='red', alpha=0.5, linewidth=0, label='$G_{exc}$')[0]
    h_gi = ax4.fill(theta_closed, gi_closed, color='blue', alpha=0.5, linewidth=0, label='$G_{inh}$')[0]
    h_err, = ax4.plot(theta_closed, sem_closed, color='black', linewidth=1.0, label='Error')
    ax4.set_ylim(0, max_cond * 1.1)
    ax4.set_theta_zero_location('E')
    ax4.set_theta_direction(1)
    ax4.set_xticks(np.deg2rad([0, 90, 180, 270]))
    ax4.set_xticklabels(['0', '0.25', '0.5', '0.75'])
    ax4.set_yticklabels([])
    ax4.grid(True, alpha=0.3)
    # Shared legend for panels C and D.
    fig.legend(
        handles=[h_ge, h_gi, h_err],
        labels=['$G_{exc}$', '$G_{inh}$', 'Error'],
        loc='center left',
        bbox_to_anchor=(0.505, 0.31),
        ncol=1,
        frameon=True,
        fontsize=12
    )
    
    fig.subplots_adjust(left=0.06, right=0.98, top=0.96, bottom=0.08, wspace=0.28, hspace=0.32)
    # Figure-level panel labels for strict row/column alignment.
    pos_a = ax1.get_position()
    pos_b = ax2.get_position()
    pos_c = ax3.get_position()
    pos_d = ax4.get_position()
    x_left = min(pos_a.x0, pos_c.x0) - 0.04
    x_right = min(pos_b.x0, pos_d.x0) - 0.042
    y_top = max(pos_a.y1, pos_b.y1) + 0.01
    y_bottom = max(pos_c.y1, pos_d.y1) + 0.01
    fig.text(x_left, y_top, "A", fontsize=18, fontweight='bold', va='top', ha='right')
    fig.text(x_right, y_top, "B", fontsize=18, fontweight='bold', va='top', ha='right')
    fig.text(x_left, y_bottom, "C", fontsize=18, fontweight='bold', va='top', ha='right')
    fig.text(x_right, y_bottom, "D", fontsize=18, fontweight='bold', va='top', ha='right')
    plt.savefig(os.path.join(FIG_DIR, "figure1_method.png"), dpi=300, bbox_inches='tight', pad_inches=0.02)
    plt.close()

def figure_3_selected_conductances():
    """Figure 3: Selected Conductances from various cell types."""
    print("Generating Figure 3: Selected Conductances...")
    cells = ["VgluT2-I-Cell2", "VgluT2-E-Cell1", "VGAT-I-Cell9", "VGAT-E-Cell8"]
    fig, axes = plt.subplots(4, 2, figsize=(12, 10), sharex=True)
    
    import matplotlib.ticker as ticker
    for i, cell in enumerate(cells):
        max_g = 0
        row_data = []
        for j, suffix in enumerate(["-C", "-V"]):
            basename = cell + suffix
            ax = axes[i, j]
            ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=4, integer=True))
            try:
                # Add specific overrides as in original script
                extra = ""
                if basename == "VgluT2-E-Cell1-V": extra = "-l 100000"
                if basename == "VgluT2-I-Cell2-V": extra = "-x 100000"
                if basename == "VGAT-I-Cell9-C": extra = "-l 500000"
                
                _, ph_path, par_path = run_analysis(basename, extra)
                data = np.loadtxt(ph_path)
                params = load_params(par_path)
                g_ns = params.get('g', 1.0) * 1000.0
                row_data.append((basename, data, g_ns))
                max_g = max(max_g, np.max(data[:, 4]*g_ns), np.max(data[:, 5]*g_ns))
            except Exception as e:
                print(f"Error processing {basename}: {e}")
                row_data.append((basename, None, None))
        
        for j, (basename, data, g_ns) in enumerate(row_data):
            ax = axes[i, j]
            if data is not None:
                n = data.shape[0]
                phase = np.linspace(0, 2, 2*n)
                gi = np.tile(data[:, 4] * g_ns, 2)
                ge = np.tile(data[:, 5] * g_ns, 2)
                err = np.tile((data[:, 2] / np.sqrt(data[:, 3])) * 1000.0, 2)
                
                ax.fill_between(phase, 0, gi, color='blue', alpha=0.5, label='Inh' if i==0 and j==0 else "", linewidth=0)
                ax.fill_between(phase, 0, ge, color='red', alpha=0.5, label='Exc' if i==0 and j==0 else "", linewidth=0)
                ax.plot(phase, err, color='black', linewidth=0.5)
                ax.set_ylim(0, max_g * 1.1)
                ax.set_title(basename, fontsize=10)
            if j == 0: ax.set_ylabel("Cond. (nS)")
            if i == 3: 
                ax.set_xlabel("Phase (2 cycles)")
                ax.set_xticks(np.arange(0, 2.1, 0.5))
            if i == 0 and j == 0: ax.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "figure3_selected.png"), dpi=300)
    plt.close()

def figure_4_combined_summary():
    """Figure 4: Population summary of conductances."""
    print("Generating Figure 4: Combined Summary...")
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.titlesize": 19,
        "axes.labelsize": 18,
        "xtick.labelsize": 16,
        "ytick.labelsize": 16
    })
    groups = ["VGAT-I", "VgluT2-I", "VGAT-E", "VgluT2-E"]
    fig, axes = plt.subplots(2, 2, figsize=(10, 11), sharey=True)
    phase_ticks = [0.5, 2.5]
    phase_labels = ['Expiration', 'Inspiration']
    # Use the same colors for Exp and Insp within each modality.
    colors = ['#D62728', '#56B4E9', '#D62728', '#56B4E9']
    
    for i, group in enumerate(groups):
        ax = axes[i // 2, i % 2]
        csv_path = os.path.join(RESULTS_DIR, f"{group.replace('-', '_')}_conductances.csv")
        if not os.path.exists(csv_path):
            ax.text(0.5, 0.5, f"Missing {group} data", ha='center')
            continue
            
        data = []
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append([float(row['Mean_gExc_Stat']), float(row['Mean_gInh_Stat']), 
                             float(row['gExc_Phase0']), float(row['gInh_Phase0'])])
        
        data = np.array(data)
        means, sems, inliers, outliers = [], [], [], []
        for j in range(4):
            m = data[:, j]
            q1, q3 = np.percentile(m, [25, 75])
            iqr = q3 - q1
            mask = (m >= q1 - 1.5*iqr) & (m <= q3 + 1.5*iqr)
            clean = m[mask]
            outs = m[~mask]
            means.append(np.mean(clean) if len(clean)>0 else 0)
            sems.append(np.std(clean, ddof=1)/np.sqrt(len(clean)) if len(clean)>1 else 0)
            inliers.append(clean)
            outliers.append(outs)
            
        x = np.arange(4)
        ax.bar(
            x, means, yerr=sems, alpha=0.9, color=colors, capsize=4, width=0.8,
            ecolor='#1A1A1A', error_kw={"elinewidth": 1.5, "capthick": 1.5}
        )
        
        n_inliers = 0
        rng = np.random.default_rng(100 + i)
        for j in range(4):
            n_inliers = max(n_inliers, len(inliers[j])) # Use max number of inliers across metrics
            # Plot inliers
            ax.scatter(
                rng.normal(j, 0.04, len(inliers[j])), inliers[j],
                color='#2E2E2E', alpha=0.45, s=16, linewidth=0
            )
            # Plot outliers
            if len(outliers[j]) > 0:
                ax.scatter(
                    rng.normal(j, 0.04, len(outliers[j])), outliers[j],
                    color='magenta', marker='x', s=28, linewidth=1.25
                )
            
        ax.set_title(f"{group} (N={n_inliers})", fontsize=19)
        ax.set_xticks(phase_ticks)
        ax.set_xticklabels(phase_labels, fontsize=16)
        ax.set_xlim(-0.6, 3.6)
        ax.set_ylim(0, 0.5)
        ax.grid(axis='y', alpha=0.22, linestyle='-', linewidth=0.8)
        ax.set_axisbelow(True)
        
        # Labels for outer edges
        if i % 2 == 0: 
            ax.set_ylabel("Synaptic / Leak Conductance", fontsize=18)
            ax.tick_params(axis='y', labelsize=16)
        
        if i == 0:
            legend_handles = [
                plt.Rectangle((0, 0), 1, 1, color='#D62728', alpha=0.9, label='Excitation'),
                plt.Rectangle((0, 0), 1, 1, color='#56B4E9', alpha=0.9, label='Inhibition')
            ]
            ax.legend(handles=legend_handles, loc='upper left', frameon=False, fontsize=16)

    fig.subplots_adjust(wspace=0.15, hspace=0.28, bottom=0.08, left=0.10, right=0.97, top=0.94)
    plt.savefig(os.path.join(FIG_DIR, "figure4_summary.png"), dpi=300)
    plt.close()

def _load_recording_window(basename, t_start, t_end):
    path = os.path.join(PROJECT_ROOT, "data", basename)
    data = []
    with open(path, 'r') as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 4:
                try:
                    t = float(parts[0])
                    if t_start is not None and t < t_start:
                        continue
                    if t_end is not None and t > t_end:
                        break
                    inj = float(parts[1])
                    vm = float(parts[2])
                    ref = float(parts[3])
                    data.append((t, inj, vm, ref))
                except ValueError:
                    pass

    if not data:
        return None

    return np.array(data)

def _current_stability_metrics(t, inj):
    if len(t) < 2:
        return np.inf, np.inf
    span_95_5 = np.percentile(inj, 95) - np.percentile(inj, 5)
    slope = np.polyfit(t - t[0], inj, 1)[0]
    return span_95_5, slope

def _median_filter_with_edge_padding(x, window_pts):
    """Median filter with edge padding (avoids boundary dips and suppresses outliers)."""
    x = np.asarray(x)
    if len(x) == 0:
        return x

    w = max(1, int(window_pts))
    w = min(w, len(x))
    if w % 2 == 0:
        w = w - 1 if w > 1 else 1
    if w <= 1:
        return x.copy()

    pad = w // 2
    x_pad = np.pad(x, (pad, pad), mode='edge')
    out = np.empty_like(x, dtype=float)
    for i in range(len(x)):
        out[i] = np.median(x_pad[i:i + w])
    return out

def figure_2_four_populations():
    """Figure 2: Four Population Episodes."""
    print("Generating Figure 2: Four Population Episodes...")
    episodes = [
        ('VGAT-E', 'VGAT-E-Cell4-C', 1575.8, 1600.8),
        ('VGAT-I', 'VGAT-I-Cell9-C', 3313.8, 3338.8),
        ('VgluT2-I', 'VgluT2-I-Cell10-C-1', 3003.6, 3028.6), 
        ('VgluT2-E', 'VgluT2-E-Cell1-C', 278.1, 303.1)
    ]

    plt.rcParams.update({
        "axes.labelsize": 16,
        "axes.titlesize": 16,
        "xtick.labelsize": 14,
        "ytick.labelsize": 14,
        "legend.fontsize": 14,
        "font.family": "DejaVu Sans"
    })
    
    fig, axes = plt.subplots(4, 1, figsize=(15, 12), sharex=True)

    for i, (name, basename, start, end) in enumerate(episodes):
        rec = _load_recording_window(basename, start, end)
        if rec is None or len(rec) < 3:
            print(f'Failed to load {basename}')
            continue
        t = rec[:, 0]
        inj = rec[:, 1]
        vm = rec[:, 2]
        ref = rec[:, 3]

        dt_candidates = np.diff(t)
        dt_candidates = dt_candidates[dt_candidates > 0]
        dt = np.median(dt_candidates) if len(dt_candidates) > 0 else 0.0001
        v_norm, repair_diag = repair_undersampled_spikes(
            vm, dt, peak_threshold=-30.0, base_threshold=-45.0
        )

        i_span, i_slope = _current_stability_metrics(t, inj)
        if i_span > 0.20 or abs(i_slope) > 0.0025:
            print(
                f"Warning: {basename} has non-steady injected current in plotted window "
                f"(span95-5={i_span:.4f}, slope={i_slope:.6f}/s)."
            )

        t_aligned = t - t[0]

        med_window = max(1, int(round(0.1 / dt)))  # 100 ms median denoise
        ref_smooth = _median_filter_with_edge_padding(ref, med_window)
            
        # Scale green signal to be strictly below the blue signal
        vm_min = np.min(v_norm)
        # Give it a 25mV amplitude to make the bumps more prominent, ending 5mV below the minimum of Vm
        ref_max = vm_min - 5
        ref_min = ref_max - 25
        
        ref_norm = (ref_smooth - np.min(ref_smooth)) / (np.max(ref_smooth) - np.min(ref_smooth) + 1e-6)
        ref_mapped = ref_norm * (ref_max - ref_min) + ref_min
        
        ax = axes[i]
        
        # Hide the borders for a cleaner aesthetic
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        
        if i < 3:
            ax.xaxis.set_visible(False)
            
        ax.plot(t_aligned, ref_mapped, color='#2ca02c', lw=2, alpha=0.8, label=r'$\int$ HNA' if i==0 else "")
        ax.plot(t_aligned, v_norm, color='#1f77b4', lw=1, alpha=0.9, label='Membrane Potential' if i==0 else "")

        if i == 0:
            print(
                f"Spike repair summary ({basename}): "
                f"n_peaks={repair_diag.get('num_peaks', 0)}, "
                f"mean_lift={repair_diag.get('mean_peak_lift', 0.0):.3f} mV"
            )
        
        # Use simple titles, shift inside the plot area for cleaner look
        ax.text(0.01, 0.95, name, transform=ax.transAxes, fontsize=18, fontweight='bold', 
                va='top', ha='left', bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=2))
                
        # Set y limits based on the traces
        ax.set_ylim(ref_min - 5, 40)
        ax.set_xlim(0, 25)
        
        # Set custom y-ticks starting from -60
        # Determine max Vm to see how high ticks should go
        vm_max = np.max(v_norm)
        ytick_max = 20 if vm_max < 30 else 40
        ax.set_yticks(np.arange(-60, ytick_max + 1, 20))
        
        if i == 0:
            ax.legend(loc='upper right', frameon=False, ncol=2)
            
        # Draw a horizontal line at 0 mV as a visual reference
        ax.axhline(0, color='gray', linestyle='--', lw=0.5, alpha=0.5)

    axes[-1].spines['bottom'].set_visible(True)
    axes[-1].set_xlabel('Time (s)')
    plt.tight_layout()
    plt.subplots_adjust(hspace=0.1) # compress space between
    plt.savefig(os.path.join(FIG_DIR, "figure2_four_populations.png"), dpi=300)
    plt.close()

def supplemental_figure_1_sensitivity():
    """Supplemental Figure 1: Sensitivity to Ei and Ee variations."""
    print("Generating Supplemental Figure 1: Sensitivity Analysis...")
    basename = "VgluT2-I-Cell2-C"
    
    # Use baseline Ei = -70 and Ee = -10 as requested
    Ei_def = -70.0
    Ee_def = -10.0
    
    # Get g_scale for normalization
    _, _, par_path_def = run_analysis(basename, Ei=Ei_def, Ee=Ee_def)
    params_def = load_params(par_path_def)
    g_ns_factor = params_def.get('g', 1.0) * 1000.0
    
    Ei_vals = [Ei_def - 10, Ei_def, Ei_def + 10]
    Ee_vals = [Ee_def - 10, Ee_def, Ee_def + 10]
    
    fig, axes = plt.subplots(3, 3, figsize=(15, 12), sharex=True, sharey=True)
    import matplotlib.ticker as ticker

    for i, ee in enumerate(Ee_vals):
        for j, ei in enumerate(Ei_vals):
            ax = axes[i, j]
            ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=4, integer=True))
            
            # Run analysis for this specific combination
            _, ph_path, _ = run_analysis(basename, Ee=ee, Ei=ei)
            ph = np.loadtxt(ph_path)
            ph_valid = ph[ph[:, 3] > 0]
            
            phs = ph_valid[:, 6] / 1000.0
            gi = ph_valid[:, 4] * g_ns_factor
            ge = ph_valid[:, 5] * g_ns_factor
            
            phs2 = np.concatenate([phs, phs + 1.0])
            gi2, ge2 = np.tile(gi, 2), np.tile(ge, 2)
            
            ax.fill_between(phs2, ge2, 0, color='red', alpha=0.5, label='$G_{exc}$', linewidth=0)
            ax.fill_between(phs2, gi2, 0, color='blue', alpha=0.5, label='$G_{inh}$', linewidth=0)
            
            ax.set_title(f"$E_e={ee}, E_i={ei}$", fontsize=12)
            if i == 2: 
                ax.set_xlabel("Phase")
                ax.set_xticks(np.arange(0, 2.1, 0.5))
            if j == 0: ax.set_ylabel("Cond. (nS)")
            if i == 0 and j == 2: ax.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "supp_figure1_sensitivity.png"), dpi=300)
    plt.close()

def supplemental_figure_2_linearity():
    """Supplemental Figure 2: Linearity of I-V regressions for all cells in Figure 2."""
    print("Generating Supplemental Figure 2: Linearity Analysis...")
    cells = ["VgluT2-I-Cell2", "VgluT2-E-Cell1", "VGAT-I-Cell9", "VGAT-E-Cell8"]
    fig, axes = plt.subplots(4, 2, figsize=(12, 14))
    import matplotlib.ticker as ticker

    target_phases = [0.0, 0.5]
    colors = ['red', 'blue']
    window = 0.001 

    for i, cell in enumerate(cells):
        v_min, v_max = np.inf, -np.inf
        i_min, i_max = np.inf, -np.inf
        
        # First pass to find scales
        cell_results = []
        for j, suffix in enumerate(["-C", "-V"]):
            basename = cell + suffix
            try:
                extra = ""
                if basename == "VgluT2-E-Cell1-V": extra = "-l 100000"
                if basename == "VgluT2-I-Cell2-V": extra = "-x 100000"
                if basename == "VGAT-I-Cell9-C": extra = "-l 500000"
                
                dat_path, _, _ = run_analysis(basename, extra)
                dat = np.loadtxt(dat_path)
                cell_results.append(dat)
                
                v_min = min(v_min, dat[:, 4].min())
                v_max = max(v_max, dat[:, 4].max())
                i_min = min(i_min, dat[:, 3].min())
                i_max = max(i_max, dat[:, 3].max())
            except:
                cell_results.append(None)

        # Second pass to plot
        for j, dat in enumerate(cell_results):
            basename = cell + (["-C", "-V"][j])
            ax = axes[i, j]
            ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=4, integer=True))
            
            if dat is not None:
                for phi, color in zip(target_phases, colors):
                    mask = (dat[:, 2] >= phi) & (dat[:, 2] < phi + window)
                    pts = dat[mask]
                    if len(pts) == 0: continue
                    
                    I_pts = pts[:, 3]
                    V_pts = pts[:, 4]
                    ax.scatter(V_pts, I_pts, s=15, alpha=0.4, color=color, edgecolors='none', label=rf"$\phi \approx {phi}$")
                    
                    slope_py, intercept_py = robust_polyfit(V_pts, I_pts, 1)
                    # Use shared range for lines
                    v_line = np.array([v_min, v_max])
                    i_line = slope_py * v_line + intercept_py
                    ax.plot(v_line, i_line, color=color, linewidth=1.5, linestyle='--')
                
                ax.set_xlim(v_min - 5, v_max + 5)
                ax.set_ylim(i_min - 0.1*(i_max-i_min), i_max + 0.1*(i_max-i_min))
                ax.set_title(basename, fontsize=14)
                if i == 3: ax.set_xlabel("V (mV)", fontsize=14)
                if j == 0: ax.set_ylabel("I (nA)", fontsize=14)
                if i == 0 and j == 0: ax.legend(loc='upper left', fontsize=12)
                ax.tick_params(axis='both', which='major', labelsize=12)
                ax.grid(True, alpha=0.2)
            else:
                ax.text(0.5, 0.5, "Error", ha='center')

    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "supp_figure2_linearity.png"), dpi=300)
    plt.close()

def generate_captions():
    print("Generating captions...")
    with open(CAPTIONS_FILE, "w") as f:
        f.write("# Figure Captions\n\n")
        f.write("## Figure 1: Method Illustration\n")
        f.write("A) Linear regressions of I-V curves at different phases. B) Wedge plot showing the trajectory of G_tot vs I_0. C) Reconstructed excitatory (red) and inhibitory (blue) conductances over two cycles. D) Polar representation of excitatory and inhibitory conductance profiles over one normalized cycle.\n\n")
        f.write("## Figure 2: Four Population Episodes\n")
        f.write(r"Representative 25-second rhythmic episodes highlighting the firing patterns of typical neurons in the VgluT2-I, VgluT2-E, VGAT-I, and VGAT-E populations. The blue trace illustrates the membrane potential ($V_m$) exhibiting distinct bursting dynamics time-aligned with the network rhythm. The green trace represents the integrated Hypoglossal Nerve Activity ($\int$ HNA), providing a global reference for the inspiratory phase. Action potential peaks are repaired spike-by-spike using a data-derived typical spike-top template fit to existing sampled points, increasing peak height and reducing undersampling-driven peak variability; episodes are selected from steady-current segments." + "\n\n")
        f.write("## Figure 3: Selected Conductances\n")
        f.write("Example traces of reconstructed conductances for selected cells from different populations (VgluT2-I, VgluT2-E, VGAT-I, VGAT-E).\n\n")
        f.write("## Figure 4: Combined Summary\n")
        f.write("Population-level summary of excitatory and inhibitory conductances during expiration and inspiration for the four main groups. Bars represent mean ± SEM of inliers (outliers removed via IQR method), with conductances normalized by leak conductance.\n\n")
        f.write("## Figure 5: Weighted Circuit Diagram\n")
        f.write("Inferred preBotC population circuit with edge widths scaled to the same CSV-derived mean normalized conductances summarized in Table 1. Red arrows indicate excitatory drive from the inspiratory VgluT2 population, blue lines with terminal circles indicate inhibitory drive from the inspiratory and expiratory VGAT populations, and only connections exceeding the display threshold are shown. Connections below 0.05 are clipped from the diagram.\n\n")
        f.write("## Supplemental Figure 1: Sensitivity Analysis\n")
        f.write("Sensitivity of reconstructed conductances to variations in reversal potentials ($E_e$ and $E_i$). The grid shows results for variations of ±10 mV from default values.\n\n")
        f.write("## Supplemental Figure 2: Linearity Analysis\n")
        f.write(r"I-V regressions for all cells and recording modes presented in Figure 2. Scatter points represent data from specific phase bins ($\phi \approx 0.0$ in red, $\phi \approx 0.5$ in blue), with dashed lines indicating the corresponding linear fits." + "\n\n")
        f.write("## Supplemental Figure 3: Ectopic Bursting in Inhibitory Neurons\n")
        f.write("Representative 25-second inhibitory episodes highlighting ectopic bursting behavior. Each panel displays the membrane potential (blue) and the synchronized rhythmic reference signal (green). Action potential peaks have been accurately restored using parabolic interpolation to mitigate 1000 Hz undersampling. Episodes were selected for having clear ectopic bursts (>=3 spikes), a rhythmic network context (>=2 main bursts), and a steady holding current.\n\n")
        f.write("## Supplemental Figure 4: Pre-Inspiratory Initiator Activity\n")
        f.write("High-resolution comparison of pre-inspiratory action potential firing and underlying synaptic drive. **(Left column)** Current-clamp (CC) episodes show pre-inspiratory spiking (blue) preceding each network burst in the reference signal (green). **(Right column)** Corresponding voltage-clamp (VC) episodes from the same cells show the pre-inspiratory inward current (blue) preceding the same reference bursts (green). Each panel contains two adjacent reference bursts; pink shading marks the pre-inspiratory lead interval for each burst. Horizontal scale bars indicate 1 s, and VC panels include vertical current scale bars in native units.\n")
        f.write("\n## Supplemental Figure 5: Pre-Inspiratory Inhibition of Expiratory Cells\n")
        f.write("Examples of expiratory cells that stop firing before inspiratory onset and matched voltage-clamp recordings from the same cells showing a pre-inspiratory outward current. **(Left column)** Current-clamp (CC) episodes show expiratory spiking (blue) terminating before each inspiratory burst in the reference signal (green). **(Right column)** Corresponding voltage-clamp (VC) episodes show an outward synaptic current (blue) preceding the same inspiratory reference bursts (green). Each panel contains two adjacent reference bursts; pink shading marks the pre-inspiratory silent interval in CC and the pre-inspiratory outward-current interval in VC. Horizontal scale bars indicate 1 s, and VC panels include vertical current scale bars in native units.\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate publication figures and captions.")
    parser.add_argument('--fig1', action='store_true', help="Generate Figure 1 (Method)")
    parser.add_argument('--fig2', action='store_true', help="Generate Figure 2 (Four Populations)")
    parser.add_argument('--fig3', action='store_true', help="Generate Figure 3 (Selected Conductances)")
    parser.add_argument('--fig4', action='store_true', help="Generate Figure 4 (Summary)")
    parser.add_argument('--supp1', action='store_true', help="Generate Supplemental Figure 1 (Sensitivity)")
    parser.add_argument('--supp2', action='store_true', help="Generate Supplemental Figure 2 (Linearity)")
    parser.add_argument('--captions', action='store_true', help="Generate captions.md")
    args = parser.parse_args()

    # If no flags are provided, run all
    if not any([args.fig1, args.fig2, args.fig3, args.fig4, args.supp1, args.supp2, args.captions]):
        args.fig1 = args.fig2 = args.fig3 = args.fig4 = args.supp1 = args.supp2 = args.captions = True

    if args.fig1: figure_1_method_illustration()
    if args.fig2: figure_2_four_populations()
    if args.fig3: figure_3_selected_conductances()
    if args.fig4: figure_4_combined_summary()
    if args.supp1: supplemental_figure_1_sensitivity()
    if args.supp2: supplemental_figure_2_linearity()
    if args.captions: generate_captions()
    
    print(f"Done! Output in {PUBLICATION_DIR}")
