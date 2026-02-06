import os
import subprocess
import glob
import re
import csv
import matplotlib.pyplot as plt
import numpy as np
import argparse

# Setup Argparse
parser = argparse.ArgumentParser(description='Batch analyze conductances for a specific cell group.')
parser.add_argument('--group', type=str, default='VGAT-I', help='Cell group prefix (e.g., VGAT-I, VgluT2-I)')
args = parser.parse_args()

GROUP = args.group
GROUP_Clean = GROUP.replace('-', '_') # For filenames

# Configuration
DATA_DIR = "data"
RESULTS_DIR = "results"
BIN_ANALYZER = "bin/trace_analyzer"
MAKEFILE_PATH = "legacy/Makefile.orig"
OUTPUT_CSV = os.path.join(RESULTS_DIR, f"{GROUP_Clean}_conductances.csv")
OUTPUT_PLOT = os.path.join(RESULTS_DIR, f"{GROUP_Clean}_conductances.png")
VIOLIN_PLOT = os.path.join(RESULTS_DIR, f"{GROUP_Clean}_conductances_violin.png")

# Ensure results directory exists
os.makedirs(RESULTS_DIR, exist_ok=True)

def parse_makefile(makefile_path):
    """Parse legacy Makefile to get flags for each file."""
    flags_map = {}
    if not os.path.exists(makefile_path):
        print(f"Warning: {makefile_path} not found.")
        return flags_map

    with open(makefile_path, 'r') as f:
        content = f.read()

    # Regex to capture target and the med2 command line
    pattern = re.compile(r"^([\w-]+)\.pdf:.*?\n\s+\./med2\s+(.*?)<", re.MULTILINE)
    matches = pattern.findall(content)

    for basename, flags in matches:
        # Strip -q value to force automatic threshold calculation
        flags = re.sub(r"-q\s+[\d\.]+", "", flags)
        flags_map[basename] = flags.strip()
    
    return flags_map

# Load flags
makefile_flags = parse_makefile(MAKEFILE_PATH)

# Find all files for the group (both C and V)
# Pattern: GROUP-Cell*
files = glob.glob(os.path.join(DATA_DIR, f"{GROUP}-Cell*"))
files.sort()

results = []

print(f"Found {len(files)} potential files to process for group {GROUP}.")

for file_path in files:
    filename = os.path.basename(file_path)
    
    # Filter for valid data files (simple heuristic: starts with GROUP-Cell)
    if not filename.startswith(f"{GROUP}-Cell"):
        continue
    
    # Extract Cell ID and Type (C/V) for sorting/labeling
    # Try to parse "GROUP-Cell<ID>-<Type>"
    # Type could be C, V, C-1, V-2 etc.
    # Regex needs to be flexible for the group name
    # We essentially want the part after "{GROUP}-Cell"
    # e.g. VGAT-I-Cell1-C -> ID=1, Type=C
    
    # Escape group name for regex just in case
    escaped_group = re.escape(GROUP)
    match = re.search(fr"{escaped_group}-Cell(\d+)-([A-Za-z0-9-]+)", filename)
    if not match:
        print(f"Skipping {filename}: Could not parse Cell ID/Type")
        continue

    cell_id = match.group(1)
    rec_type = match.group(2) # e.g. "C", "V", "C-1"
    
    # Determine flags
    flags_str = "-f 25" # Default
    if filename in makefile_flags:
        flags_str = makefile_flags[filename]
    else:
        # Fallback logic from batch_runner if not in Makefile
        if filename.endswith("-V") or "-V-" in filename: # loosely check for V
             if "-vc" not in flags_str:
                 flags_str += " -vc"
        print(f"Warning: No flags found for {filename}, using default/inferred: {flags_str}")
    
    print(f"Processing Cell {cell_id} ({filename}) with flags: {flags_str}")
    
    temp_par = os.path.join(RESULTS_DIR, f"temp_{filename}.par")
    
    args = flags_str.split()
    cmd = [BIN_ANALYZER] + args + ["-par", temp_par]
    
    try:
        with open(file_path, 'r') as stdin_f:
            subprocess.run(cmd, stdin=stdin_f, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error processing {filename}: {e}")
        if os.path.exists(temp_par):
            os.remove(temp_par)
        continue
        
    data = {}
    if os.path.exists(temp_par):
        with open(temp_par, 'r') as f:
            for line in f:
                if '=' in line:
                    key, val = line.strip().split('=')
                    try:
                        data[key] = float(val)
                    except ValueError:
                        pass # Ignore non-numeric
        os.remove(temp_par)
    
    # Filter by Cycle Count N >= 30
    cycles_n = int(data.get('N', 0))
    if cycles_n < 30:
        print(f"  -> Skipping Cell {cell_id} ({rec_type}): N={cycles_n} (< 30)")
        continue
        
    print(f"  -> Accepted: N={cycles_n}")

    res_entry = {
        'CellID_Str': f"Cell {cell_id} ({rec_type})",
        'CellNum': int(cell_id),
        'Type': rec_type,
        'N': cycles_n,
        'Mean_gExc_Stat': data.get('G_exc_st', 0),
        'Mean_gInh_Stat': data.get('G_inh_st', 0),
        'gExc_Phase0': data.get('G_exc_ph0', 0),
        'gInh_Phase0': data.get('G_inh_ph0', 0)
    }
    results.append(res_entry)

# Sort by CellNum, then Type
results.sort(key=lambda x: (x['CellNum'], x['Type']))

# Save to CSV
header = ['CellID', 'N', 'Mean_gExc_Stat', 'Mean_gInh_Stat', 'gExc_Phase0', 'gInh_Phase0']
with open(OUTPUT_CSV, 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=header)
    writer.writeheader()
    for row in results:
        writer.writerow({
            'CellID': row['CellID_Str'],
            'N': row['N'],
            'Mean_gExc_Stat': row['Mean_gExc_Stat'],
            'Mean_gInh_Stat': row['Mean_gInh_Stat'],
            'gExc_Phase0': row['gExc_Phase0'],
            'gInh_Phase0': row['gInh_Phase0']
        })
print(f"Saved data to {OUTPUT_CSV}")

if not results:
    print("No data to plot.")
    exit()

# Plotting
cell_ids = [r['CellID_Str'] for r in results]
mean_exc = [r['Mean_gExc_Stat'] for r in results]
mean_inh = [r['Mean_gInh_Stat'] for r in results]
ph0_exc = [r['gExc_Phase0'] for r in results]
ph0_inh = [r['gInh_Phase0'] for r in results]

fig, ax = plt.subplots(figsize=(14, 7)) # Increased width for more bars

x = np.arange(len(cell_ids))
width = 0.2

rects1 = ax.bar(x - 1.5*width, mean_exc, width, label='Mean gExc (Stationary)', color='salmon')
rects2 = ax.bar(x - 0.5*width, mean_inh, width, label='Mean gInh (Stationary)', color='skyblue')
rects3 = ax.bar(x + 0.5*width, ph0_exc, width, label='gExc (Phase 0)', color='red', alpha=0.9)
rects4 = ax.bar(x + 1.5*width, ph0_inh, width, label='gInh (Phase 0)', color='blue', alpha=0.9)

ax.set_ylabel('Conductance (nS)')
ax.set_title(f'{GROUP} Neurons (N >= 30): Stationary Mean vs Phase 0 Conductances')
ax.set_xticks(x)
ax.set_xticklabels(cell_ids, rotation=45, ha='right')
ax.legend()

ax.yaxis.grid(True, linestyle='--', alpha=0.7)

plt.tight_layout()
plt.savefig(OUTPUT_PLOT)
print(f"Saved plot to {OUTPUT_PLOT}")

# Violin Plot
data_to_plot = [mean_exc, mean_inh, ph0_exc, ph0_inh]
labels = ['Mean gExc (Stat)', 'Mean gInh (Stat)', 'gExc (Phase 0)', 'gInh (Phase 0)']

fig, ax = plt.subplots(figsize=(10, 6))

# Create violin plot
parts = ax.violinplot(data_to_plot, showmeans=False, showmedians=True, showextrema=False)

# Customize colors
colors = ['salmon', 'skyblue', 'red', 'blue']
for i, pc in enumerate(parts['bodies']):
    pc.set_facecolor(colors[i])
    pc.set_edgecolor('black')
    pc.set_alpha(0.7)

# Add jittered individual points
for i, data in enumerate(data_to_plot):
    y = data
    x = np.random.normal(i + 1, 0.04, size=len(y))
    ax.scatter(x, y, alpha=0.9, s=20, color='darkslategrey', zorder=10)

# Set labels
ax.set_xticks(np.arange(1, len(labels) + 1))
ax.set_xticklabels(labels)
ax.set_ylabel('Conductance (nS)')
ax.set_title(f'{GROUP} Conductance Distributions (N >= 30)')

# Grid
ax.yaxis.grid(True, linestyle='--', alpha=0.7)

plt.tight_layout()
plt.savefig(VIOLIN_PLOT)
print(f"Saved violin plot to {VIOLIN_PLOT}")
