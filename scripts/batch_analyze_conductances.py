import os
import subprocess
import glob
import re
import csv
import argparse
from analysis_options import get_flags_map, resolve_flags

# Setup Argparse
parser = argparse.ArgumentParser(description='Batch analyze conductances for a specific cell group.')
parser.add_argument('--group', type=str, default='VGAT-I', help='Cell group prefix (e.g., VGAT-I, VgluT2-I)')
parser.add_argument('--force-rerun', action='store_true', help='Recompute .par even when results/<basename>.par exists')
args = parser.parse_args()

GROUP = args.group
GROUP_Clean = GROUP.replace('-', '_') # For filenames

# Configuration
DATA_DIR = "data"
RESULTS_DIR = "results"
WEB_DIR = os.path.join("web", "assets", "recordings")
BIN_ANALYZER = "bin/trace_analyzer"
OUTPUT_CSV = os.path.join(RESULTS_DIR, f"{GROUP_Clean}_conductances.csv")

# Ensure directories exist
os.makedirs(WEB_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)


def load_par_file(par_path):
    """Load numeric key=value pairs from analyzer .par output."""
    data = {}
    if not os.path.exists(par_path):
        return data
    with open(par_path, 'r') as f:
        for line in f:
            if '=' in line:
                parts = line.strip().split('=')
                if len(parts) == 2:
                    key, val = parts
                    try:
                        data[key] = float(val)
                    except ValueError:
                        pass
    return data

# Load flags from Makefile + overrides
makefile_flags = get_flags_map(project_root=".", strip_q=True)

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
    escaped_group = re.escape(GROUP)
    match = re.search(fr"{escaped_group}-Cell(\d+)-([A-Za-z0-9-]+)", filename)
    if not match:
        print(f"Skipping {filename}: Could not parse Cell ID/Type")
        continue

    cell_id = match.group(1)
    rec_type = match.group(2) # e.g. "C", "V", "C-1"
    
    # Determine flags
    flags_str = resolve_flags(
        filename,
        makefile_flags,
        default_flags="-f 25",
        infer_vc_from_name=True
    )
    if filename not in makefile_flags:
        print(f"Warning: No configured flags for {filename}, using default/inferred: {flags_str}")
    
    print(f"Processing Cell {cell_id} ({filename}) with flags: {flags_str}")
    
    existing_par = os.path.join(WEB_DIR, f"{filename}.par")
    data = {}
    source = None

    if (not args.force_rerun) and os.path.exists(existing_par):
        data = load_par_file(existing_par)
        source = "existing"
    else:
        temp_par = os.path.join(WEB_DIR, f"temp_{filename}.par")
        analyzer_args = flags_str.split()
        cmd = [BIN_ANALYZER] + analyzer_args + ["-par", temp_par]
        try:
            with open(file_path, 'r') as stdin_f:
                subprocess.run(cmd, stdin=stdin_f, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error processing {filename}: {e}")
            if os.path.exists(temp_par):
                os.remove(temp_par)
            continue
        data = load_par_file(temp_par)
        source = "rerun"
        if os.path.exists(temp_par):
            os.remove(temp_par)

    if not data:
        print(f"  -> Skipping Cell {cell_id} ({rec_type}): no .par data ({source})")
        continue
    
    # Filter by Cycle Count N > 25
    cycles_n = int(data.get('N', 0))
    if cycles_n <= 25:
        print(f"  -> Skipping Cell {cell_id} ({rec_type}): N={cycles_n} (<= 25)")
        continue
        
    print(f"  -> Accepted: N={cycles_n} ({source})")

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
