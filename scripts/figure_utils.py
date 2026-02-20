import os
import subprocess
import numpy as np
from analysis_options import get_flags_map, resolve_flags

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
BIN_ANALYZER = os.path.join(PROJECT_ROOT, "bin", "trace_analyzer")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
TMP_DIR = os.path.join(PROJECT_ROOT, "tmp")
MAKEFILE_PATH = os.path.join(PROJECT_ROOT, "legacy", "Makefile.orig")

def ensure_dirs():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)

def parse_makefile():
    """Load per-file flags from Makefile + overrides."""
    return get_flags_map(PROJECT_ROOT, strip_q=True)

def run_analysis(basename, extra_flags=None, Ee=None, Ei=None):
    """
    Runs trace_analyzer for a given basename.
    Returns (dat_path, ph_path, par_path)
    """
    ensure_dirs()
    data_path = os.path.join(DATA_DIR, basename)
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file not found: {data_path}")

    flags_map = parse_makefile()
    flags_str = resolve_flags(basename, flags_map, default_flags="-f 25", infer_vc_from_name=True)
    
    if Ee is not None:
        flags_str += f" -Ee {Ee}"
    if Ei is not None:
        flags_str += f" -Ei {Ei}"
        
    if extra_flags:
        flags_str += " " + extra_flags
        
    dat_path = os.path.join(TMP_DIR, f"{basename}.dat")
    ph_path = os.path.join(TMP_DIR, f"{basename}.ph")
    par_path = os.path.join(TMP_DIR, f"{basename}.par")
    trig_path = os.path.join(TMP_DIR, f"{basename}.trig")
    
    cmd = [BIN_ANALYZER] + flags_str.split() + ["-par", par_path, "-trig", trig_path]
    
    with open(data_path, 'rb') as fin, \
         open(dat_path, 'wb') as fout, \
         open(ph_path, 'wb') as ferr:
        subprocess.run(cmd, stdin=fin, stdout=fout, stderr=ferr, check=True)
        
    return dat_path, ph_path, par_path

def load_params(par_path):
    params = {}
    if os.path.exists(par_path):
        with open(par_path, 'r') as f:
            for line in f:
                if '=' in line:
                    key, val = line.strip().split('=', 1)
                    try:
                        params[key] = float(val)
                    except ValueError:
                        params[key] = val
    return params
