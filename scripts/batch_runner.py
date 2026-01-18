import re
import subprocess
import multiprocessing
import os
import sys

# Define input Makefile and Runner script paths relative to project root
# This script is in scripts/, so root is ..
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
MAKEFILE = os.path.join(PROJECT_ROOT, "legacy", "Makefile.orig")
RUNNER_SCRIPT = os.path.join(SCRIPT_DIR, "run_analysis.sh")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

def parse_makefile():
    # Map basename -> flags string
    makefile_flags = {}
    
    try:
        with open(MAKEFILE, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Warning: {MAKEFILE} not found. Using defaults for all files.")
        return makefile_flags

    # Regex to capture target and the med2 command line
    pattern = re.compile(r"^([\w-]+)\.pdf:.*?\n\s+\./med2\s+(.*?)<", re.MULTILINE)
    matches = pattern.findall(content)
    
    for basename, flags in matches:
        # Strip -q value to force automatic threshold calculation
        flags = re.sub(r"-q\s+[\d\.]+", "", flags)
        makefile_flags[basename] = flags.strip()
        
    return makefile_flags

def run_job(basename, makefile_flags):
    data_path = os.path.join(DATA_DIR, basename)
    
    # Determine flags
    if basename in makefile_flags:
        flags_str = makefile_flags[basename]
    else:
        # Default flags for unknown files
        flags = ["-f", "25"]
        # Auto-apply -vc for Voltage Clamp files
        if basename.endswith("-V"):
            flags.append("-vc")
        flags_str = " ".join(flags)
        print(f"[{basename}] Using default flags: {flags_str}")

    cmd = [RUNNER_SCRIPT, data_path] + flags_str.split()
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"[{basename}] FAILED:\n{result.stderr}")
        return False
    return True

def main():
    if not os.access(RUNNER_SCRIPT, os.X_OK):
        subprocess.run(["chmod", "+x", RUNNER_SCRIPT])

    print("Loading flags from legacy Makefile...")
    makefile_flags = parse_makefile()

    print(f"Scanning {DATA_DIR} for data files...")
    data_files = [f for f in os.listdir(DATA_DIR) if os.path.isfile(os.path.join(DATA_DIR, f)) and not f.startswith(".")]
    print(f"Found {len(data_files)} data files.")

    cpu_count = multiprocessing.cpu_count()
    print(f"Running with {cpu_count} parallel processes...")

    # Prepare jobs
    with multiprocessing.Pool(processes=cpu_count) as pool:
        # Use partial or a wrapper to pass makefile_flags
        from functools import partial
        pool.map(partial(run_job, makefile_flags=makefile_flags), data_files)

    print("All jobs finished.")

if __name__ == "__main__":
    main()