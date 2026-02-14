#!/usr/bin/env python3
import os
import subprocess
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.cm import viridis

# Configuration
BASENAME = "VgluT2-I-Cell2-C"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(PROJECT_ROOT, "data", BASENAME)
BIN_PATH = os.path.join(PROJECT_ROOT, "bin", "trace_analyzer")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
TMP_PH = os.path.join(PROJECT_ROOT, "tmp", "method_illust.ph")
TMP_DAT = os.path.join(PROJECT_ROOT, "tmp", "method_illust.dat")
TMP_PAR = os.path.join(PROJECT_ROOT, "tmp", "method_illust.par")
TMP_TRIG = os.path.join(PROJECT_ROOT, "tmp", "method_illust.trig")

def run_analysis():
    print("Running trace_analyzer...")
    cmd = [
        BIN_PATH,
        "-f", "25",
        "-l", "300000",
        "-par", TMP_PAR,
        "-trig", TMP_TRIG
    ]
    
    with open(DATA_PATH, 'rb') as fin, \
         open(TMP_DAT, 'wb') as fout, \
         open(TMP_PH, 'wb') as ferr:
        subprocess.run(cmd, stdin=fin, stdout=fout, stderr=ferr, check=True)

def load_data():
    # Load processed traces (dat file)
    # Columns: t(0), pp(1), phase(2), I(3), V(4)? 
    # Wait, previous check: Ch0 is Col 3, Ch1 is Col 4.
    # In this file: Col 3 is -0.35 (I), Col 4 is -60 (V).
    # So dat[:, 3] is I, dat[:, 4] is V.
    print("Loading traces...")
    dat = np.loadtxt(TMP_DAT)
    
    # Load regression stats (ph file)
    # Columns: slope(0), intercept(1), error(2), count(3), G_inh(4), G_exc(5), bin(6)
    print("Loading stats...")
    ph = np.loadtxt(TMP_PH)
    
    return dat, ph

def load_params():
    params = {}
    try:
        with open(TMP_PAR, 'r') as f:
            for line in f:
                if '=' in line:
                    key, val = line.strip().split('=')
                    params[key] = float(val)
    except Exception as e:
        print(f"Error loading parameters: {e}")
    return params

def plot_figure(dat, ph, params):
    fig = plt.figure(figsize=(15, 5))
    gs = gridspec.GridSpec(1, 3, width_ratios=[1, 1, 2], wspace=0.25)
    
    # Filter valid bins
    ph_valid = ph[ph[:, 3] > 0]
    
    # --- Panel A: Linear Regressions ---
    ax1 = fig.add_subplot(gs[0])
    target_phases = [0.0, 0.5]
    colors = ['red', 'blue']
    
    # Use a small window corresponding to exactly one bin
    window = 0.001 
    
    for phi, color in zip(target_phases, colors):
        # Find points in this phase bin [phi, phi + window)
        mask = (dat[:, 2] >= phi) & (dat[:, 2] < phi + window)
             
        pts = dat[mask]
        
        if len(pts) == 0:
            continue
            
        I_pts = pts[:, 3]
        V_pts = pts[:, 4]
        
        # Plot scatter
        ax1.scatter(V_pts, I_pts, s=10, alpha=0.5, color=color, label=f"$\\phi \\approx {phi}$", edgecolors='none')
        
        # Calculate regression from the selected points for visual consistency
        slope_py, intercept_py = np.polyfit(V_pts, I_pts, 1)
        G_tot = slope_py
        I_0 = intercept_py
        
        # Line: I = G * V + I0
        v_min, v_max = V_pts.min(), V_pts.max()
        v_line = np.array([v_min, v_max])
        i_line = G_tot * v_line + I_0
            
        ax1.plot(v_line, i_line, color=color, linewidth=2, linestyle='--')

    ax1.set_xlabel("V (mV)")
    ax1.set_ylabel("I (nA)")
    ax1.set_title("I-V Regressions")
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.text(-0.15, 1.05, "A", transform=ax1.transAxes, fontsize=16, fontweight='bold', va='top', ha='right')

    # --- Panel B: Wedge Plot ---
    ax2 = fig.add_subplot(gs[1])
    
    # Gtot (slope) vs I0 (intercept)
    # User requested FLIPPED AXES compared to previous:
    # "flip axes in B" -> If previous was I0(x)-Gtot(y), now Gtot(x)-I0(y).
    # wait, my previous code had:
    # sc = ax2.scatter(I0_vals, G_vals, ...) -> I0 is X, G is Y.
    # User said "flip axes". So G should be X, I0 should be Y.
    
    G_vals = ph_valid[:, 0] * 1000.0 # uS -> nS
    I0_vals = ph_valid[:, 1]         # nA
    
    # Plot trajectory
    # Plot trajectory - connect last and first points
    G_traj = np.concatenate([G_vals, [G_vals[0]]])
    I0_traj = np.concatenate([I0_vals, [I0_vals[0]]])
    
    ax2.plot(G_traj, I0_traj, color='black', linewidth=1, alpha=0.6)
    ax2.scatter(G_vals, I0_vals, color='black', s=5, alpha=0.6)
    
    # Reference Lines
    # I0 = -E * G_raw = -E * (G_ns / 1000)
    # I0 = (-E/1000) * G_ns
    Ei = params.get('Ei', -80.0)
    Ee = params.get('Ee', 0.0)
    g_start = params.get('g', 0.0) # Leak conductance (uS)
    E_leak = params.get('E', -60.0) # Leak potential (mV)
    
    # Determine range for lines
    g_min, g_max = G_vals.min(), G_vals.max()
    margin_x = (g_max - g_min) * 0.1
    g_line = np.array([g_min - margin_x, g_max + margin_x])
    
    # Pure Inh line account for leak: I0 = -Gtot*Ei + g(Ei - E)
    # Gtot is in nS (g_line)
    # g is in uS
    offset_i = g_start * (Ei - E_leak)
    i0_zi = (-Ei / 1000.0) * g_line + offset_i
    ax2.plot(g_line, i0_zi, color='blue', linestyle='--', label='Pure Inh ($G_{exc}=0$)')
    
    # Pure Exc line account for leak: I0 = -Gtot*Ee + g(Ee - E)
    offset_e = g_start * (Ee - E_leak)
    i0_ze = (-Ee / 1000.0) * g_line + offset_e
    ax2.plot(g_line, i0_ze, color='red', linestyle='--', label='Pure Exc ($G_{inh}=0$)')

    # Fix vertical range
    # Find min/max of data and lines within the view
    # y_vals includes lines which might go very high.
    # User wants less space on top, ok if lines are cut.
    # So y_max should be determined by DATA, not lines.
    y_min = min(I0_vals.min(), i0_zi.min(), i0_ze.min())
    y_max = I0_vals.max()
    
    margin_y = (y_max - y_min) * 0.1
    # Add margin to top of data, but let bottom go to min of lines/data
    ax2.set_ylim(y_min - margin_y, y_max + margin_y)
    
    ax2.set_xlabel("$G_{tot}$ (nS)")
    ax2.set_ylabel("$I_0$ (nA)")
    ax2.set_title("Wedge Plot")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.text(-0.15, 1.05, "B", transform=ax2.transAxes, fontsize=16, fontweight='bold', va='top', ha='right')
    
    # --- Panel C: Reconstructed Conductances ---
    ax3 = fig.add_subplot(gs[2])
    
    g_scale = params.get('g', 1.0)
    g_ns_factor = g_scale * 1000.0
    
    phs = ph_valid[:, 6] / 1000.0
    gi = ph_valid[:, 4] * g_ns_factor
    ge = ph_valid[:, 5] * g_ns_factor
    
    # Error handling
    count = ph_valid[:, 3]
    err_raw = ph_valid[:, 2]
    
    # Calculate scaled error (standard error of the mean scaled to conductance units)
    # Based on plot_selected_conductances.py
    # error is in uS (regression RMSE). Scale to nS.
    sem = (err_raw / np.sqrt(count)) * 1000.0
    
    # Repeat for 2 cycles
    phs_doubled = np.concatenate([phs, phs + 1.0])
    gi_doubled = np.concatenate([gi, gi])
    ge_doubled = np.concatenate([ge, ge])
    sem_doubled = np.concatenate([sem, sem])
    
    # Fill areas for Conductances
    ax3.fill_between(phs_doubled, ge_doubled, 0, color='red', alpha=0.5, label='$G_{exc}$', linewidth=0.0)
    ax3.fill_between(phs_doubled, gi_doubled, 0, color='blue', alpha=0.5, label='$G_{inh}$', linewidth=0.0)
    
    # Plot Error as black line
    ax3.plot(phs_doubled, sem_doubled, color='black', linewidth=1, label='Error')
    
    ax3.set_xticks(np.arange(0, 2.1, 0.5))
    ax3.set_xlabel("Phase (2 cycles)")
    ax3.set_ylabel("Conductance (nS)")
    ax3.set_title("Reconstructed Conductances")
    ax3.legend(loc='upper right')
    ax3.grid(True, alpha=0.3)
    ax3.text(-0.05, 1.05, "C", transform=ax3.transAxes, fontsize=16, fontweight='bold', va='top', ha='right')
    
    plt.tight_layout()
    out_file = os.path.join(RESULTS_DIR, "method_illustration.png")
    plt.savefig(out_file, dpi=300, bbox_inches='tight', pad_inches=0.1)
    print(f"Saved figure to {out_file}")

def main():
    if not os.path.exists(os.path.dirname(TMP_PH)):
        os.makedirs(os.path.dirname(TMP_PH))
        
    run_analysis()
    dat, ph = load_data()
    params = load_params()
    plot_figure(dat, ph, params)


if __name__ == "__main__":
    main()
