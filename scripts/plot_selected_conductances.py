#!/usr/bin/env python3
import os
import re
import subprocess
import glob
import matplotlib.pyplot as plt
import numpy as np
import shutil
import uuid

# Configuration
CELLS = ["VgluT2-I-Cell2", "VgluT2-E-Cell1", "VGAT-I-Cell9", "VGAT-E-Cell8"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
MAKEFILE = os.path.join(PROJECT_ROOT, "legacy", "Makefile.orig")
EXE = os.path.join(PROJECT_ROOT, "bin", "trace_analyzer")
TMP_DIR = os.path.join(PROJECT_ROOT, "tmp")

def parse_makefile():
    makefile_flags = {}
    try:
        with open(MAKEFILE, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        return makefile_flags

    # Regex to capture target and the med2 command line
    pattern = re.compile(r"^([\w-]+)\.pdf:.*?\n\s+\./med2\s+(.*?)<", re.MULTILINE)
    matches = pattern.findall(content)
    
    for basename, flags in matches:
        flags = re.sub(r"-q\s+[\d\.]+", "", flags)
        makefile_flags[basename] = flags.strip()
    return makefile_flags

def run_analysis_to_get_files(basename, flags):
    """
    Runs trace_analyzer to generate the .ph and .par files.
    Returns (ph_file, par_file) or (None, None) on failure.
    """
    data_path = os.path.join(DATA_DIR, basename)
    if not os.path.exists(data_path):
        print(f"Data file not found: {data_path}")
        return None, None
        
    job_uuid = f"{basename}_{uuid.uuid4().hex[:8]}"
    par_file = os.path.join(TMP_DIR, f"{job_uuid}.par")
    dat_file = os.path.join(TMP_DIR, f"{job_uuid}.dat")
    ph_file = os.path.join(TMP_DIR, f"{job_uuid}.ph")
    trig_file = os.path.join(TMP_DIR, f"{job_uuid}.trig")
    
    cmd_flags = flags.split() + ["-par", par_file, "-trig", trig_file]
    
    try:
        with open(data_path, 'r') as fin, \
             open(dat_file, 'w') as fout, \
             open(ph_file, 'w') as ferr:
            
            subprocess.run([EXE] + cmd_flags, stdin=fin, stdout=fout, stderr=ferr, check=True)
            
        return ph_file, par_file
    except subprocess.CalledProcessError as e:
        print(f"Error running analysis for {basename}: {e}")
        return None, None
    except Exception as e:
        print(f"Unexpected error for {basename}: {e}")
        return None, None

def load_par(par_file):
    params = {}
    try:
        with open(par_file, 'r') as f:
            for line in f:
                if '=' in line:
                    key, val = line.strip().split('=', 1)
                    try:
                        params[key] = float(val)
                    except ValueError:
                        params[key] = val
    except Exception:
        pass
    return params

import multiprocessing
from functools import partial

# ... (previous includes)

# ... (parse_makefile, run_analysis_to_get_files, load_par functions remain same)

def process_file_wrapper(args):
    basename, flags = args
    print(f"  Running {basename} with {flags}...")
    return run_analysis_to_get_files(basename, flags)

def main():
    if not os.path.exists(TMP_DIR):
        os.makedirs(TMP_DIR)
        
    makefile_flags = parse_makefile()
    
    # Prepare list of jobs
    job_args = []
    # Map (i, j) to basename to reconstruct order later
    grid_map = {} 
    
    for i, cell in enumerate(CELLS):
        files = [f"{cell}-C", f"{cell}-V"]
        for j, basename in enumerate(files):
            flags = makefile_flags.get(basename, "-f 25")
            if "-V" in basename and "-vc" not in flags:
                 flags += " -vc"
                 
            # Overrides
            if basename == "VgluT2-E-Cell1-V":
                flags += " -l 100000"
            if basename == "VgluT2-I-Cell2-V":
                flags += " -x 100000"
            if basename == "VGAT-I-Cell9-C":
                flags += " -l 500000"
            
            job_args.append((basename, flags))
            grid_map[(i, j)] = basename

    # Run in parallel
    cpu_count = min(multiprocessing.cpu_count(), len(job_args))
    print(f"Running {len(job_args)} jobs with {cpu_count} processes...")
    
    results = {} # basename -> (ph_file, par_file)
    with multiprocessing.Pool(processes=cpu_count) as pool:
        # returns list of (ph_file, par_file) in order of job_args
        outputs = pool.map(process_file_wrapper, job_args)
        
    for (basename, _), output in zip(job_args, outputs):
        results[basename] = output

    # Plotting
    # Original (12, 16). Half height approx (12, 8) or (12, 10) to not squish too much.
    fig, axes = plt.subplots(4, 2, figsize=(12, 10), sharex=True)
    
    for i in range(4):
        # First pass: Collect data and find max conductance for the row
        row_data = [] # List of tuples: (ax, basename, data, g)
        max_g_val = 0
        
        for j in range(2):
            ax = axes[i, j]
            basename = grid_map[(i, j)]
            ph_file, par_file = results.get(basename, (None, None))
            
            if ph_file and par_file:
                try:
                    data = np.loadtxt(ph_file)
                    params = load_par(par_file)
                    g = params.get('g', 1.0)
                    row_data.append((ax, basename, data, g))
                    
                    # Estimate max for scaling
                    # Note: we will multiply by g * 1000 later.
                    # Current columns 4 and 5 are relative to g.
                    # So absolute is col * g.
                    # Units: g in uS -> * 1000 -> nS.
                    
                    # Convert to nS (assuming Input: nA, mV -> g: uS)
                    g_ns_factor = g * 1000.0
                    
                    g_inh_ns = data[:, 4] * g_ns_factor
                    g_exc_ns = data[:, 5] * g_ns_factor
                    
                    local_max = max(np.max(g_inh_ns), np.max(g_exc_ns))
                    if local_max > max_g_val:
                        max_g_val = local_max
                        
                except Exception as e:
                    print(f"Error loading {basename}: {e}")
            else:
                row_data.append((ax, basename, None, None))

        # Second pass: Plot with shared Y-limit
        for (ax, basename, data, g) in row_data:
            if data is not None:
                try:
                    n_bins = data.shape[0]
                    # 2 Cycles
                    phase = np.linspace(0, 2, 2 * n_bins)
                    data_tiled = np.tile(data, (2, 1))
                    
                    # Current data is relative G (G_raw / g)
                    # We want G_absolute_nS = G_relative * g * 1000
                    g_ns_factor = g * 1000.0
                    
                    g_inh = data_tiled[:, 4] * g_ns_factor
                    g_exc = data_tiled[:, 5] * g_ns_factor
                    
                    # Error: In file it's variance or std? 
                    # If relative error (normalized): error_abs = error_rel * g * 1000
                    # Wait, previously we plotted error/g/sqrt(count) * g = error/sqrt(count)
                    # Now we want that in nS. So * 1000.
                    # data[:, 2] is the error column.
                    
                    error = data_tiled[:, 2]
                    count = data_tiled[:, 3]
                    
                    with np.errstate(divide='ignore', invalid='ignore'):
                         # Original "scaled_error" was for relative plot?
                         # Let's assume col 2 is standard error of Regression slope/intercept.
                         # If normalized, we multiply by g_ns_factor.
                         # But wait, trace_analyzer output logic:
                         # Results are slopes.
                         # G_inh = (Ee*(slope - g) ...)/.../g  -> This is normalized.
                         # Error is likely in raw units or normalized?
                         # trace_analyzer: "results[l].error". 
                         # And "results[l]" stores {a, b, err, count}. 
                         # This 'err' is from the regression.
                         # It is likely in the same units as the Slope (Conductance, uS).
                         # So 'err' is absolute uS.
                         # So to get nS, just multiply by 1000.
                         # But we also divide by sqrt(count) for standard error of mean?
                         # The regression error is "standard error of the estimate" (RMSE of residuals).
                         # Standard error of the slope coefficient would be err / sqrt(Sxx) or similar.
                         # Let's stick to the previous logic but scaled.
                         # Previous: error / np.sqrt(count).  (This removed the /g).
                         # If 'error' is in uS, then error/sqrt(count) is uS. 
                         # So * 1000 to get nS.
                         
                         scaled_error = (error / np.sqrt(count)) * 1000.0
                         scaled_error[~np.isfinite(scaled_error)] = 0
                    
                    # Plot
                    ax.fill_between(phase, 0, g_inh, color='blue', alpha=0.5, label='Inhibition')
                    ax.fill_between(phase, 0, g_exc, color='red', alpha=0.5, label='Excitation')
                    
                    ax.plot(phase, scaled_error, color='black', linewidth=0.5, linestyle='-', label='Error')
                    
                    ax.set_title(f"{basename}", fontsize=10)
                    
                    # Set shared ylim
                    if max_g_val > 0:
                        ax.set_ylim(0, max_g_val * 1.1)
                    
                    if ax == axes[0, 0]: # Legend on first plot
                         ax.legend(loc='upper right')
                         
                except Exception as e:
                    print(f"Error plotting {basename}: {e}")
            else:
                 ax.text(0.5, 0.5, "No Data", ha='center', va='center')
                 
            # Labels
            if ax in axes[3,:]:
                ax.set_xlabel("Phase (2 cycles)")
            if ax in axes[:,0]:
                ax.set_ylabel("Conductance (nS)")

    plt.tight_layout()
    output_path = os.path.join(RESULTS_DIR, "selected_conductances.png")
    plt.savefig(output_path, dpi=300)
    print(f"Saved figure to {output_path}")

if __name__ == "__main__":
    main()
