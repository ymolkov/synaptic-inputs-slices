import re
import subprocess
import multiprocessing
import os
import sys
import shutil
import uuid

# Define input Makefile and Runner script paths relative to project root
# This script is in scripts/, so root is ..
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
MAKEFILE = os.path.join(PROJECT_ROOT, "legacy", "Makefile.orig")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
BIN_DIR = os.path.join(PROJECT_ROOT, "bin")
EXE = os.path.join(BIN_DIR, "trace_analyzer.exe")
TMP_DIR = os.path.join(PROJECT_ROOT, "tmp")
GP_SCRIPT = os.path.join(SCRIPT_DIR, "plot_traces.gp")
REPORT_GENERATOR = os.path.join(SCRIPT_DIR, "generate_report.py")

# Add Gnuplot to PATH
GNUPLOT_BIN = r"c:\users\ymolk\home\gnuplot\bin"
os.environ["PATH"] += os.pathsep + GNUPLOT_BIN

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
        
    # Unique temporary files
    job_uuid = f"{basename}_{uuid.uuid4().hex[:8]}"
    par_file = os.path.join(TMP_DIR, f"{job_uuid}.par")
    dat_file = os.path.join(TMP_DIR, f"{job_uuid}.dat")
    ph_file = os.path.join(TMP_DIR, f"{job_uuid}.ph")
    ph_dbl_file = os.path.join(TMP_DIR, f"{job_uuid}.ph_doubled")
    tmp_pdf = os.path.join(TMP_DIR, f"{job_uuid}.pdf")
    tmp_png = os.path.join(TMP_DIR, f"{job_uuid}.png")
    
    print(f"[{basename}] Processing with flags: {flags_str}")
    
    # 1. Run Analyzer
    # cmd: trace_analyzer.exe <args> -par <par_file> < <data_file> > <dat_file> 2> <ph_file>
    analyzer_args = flags_str.split() + ["-par", par_file]
    
    try:
        with open(data_path, 'r') as fin, \
             open(dat_file, 'w') as fout, \
             open(ph_file, 'w') as ferr:
            
            ret = subprocess.run([EXE] + analyzer_args, stdin=fin, stdout=fout, stderr=ferr)
            
            if ret.returncode != 0:
                print(f"[{basename}] Analyzer FAILED (return code {ret.returncode})")
                return False

        # 2. Prepare doubled ph file for cyclic plots
        # cat ph_file ph_file > ph_dbl_file
        with open(ph_dbl_file, 'wb') as fout:
            with open(ph_file, 'rb') as fin:
                shutil.copyfileobj(fin, fout)
            with open(ph_file, 'rb') as fin:
                shutil.copyfileobj(fin, fout)

        # Count lines in ph_dbl_file (for Gnuplot check)
        n_lines = 0
        try:
             with open(ph_dbl_file, 'r') as f:
                 for line in f:
                     if line.strip():
                         n_lines += 1
        except Exception:
             pass

        # 3. Run Gnuplot
        # gnuplot -e "par_file='...'" ... "plot_traces.gp"
        # We need to escape backslashes for Gnuplot strings on Windows
        def gp_path(p): return p.replace('\\', '/')
        
        gp_cmd = [
            "gnuplot",
            "-e", f"par_file='{gp_path(par_file)}'",
            "-e", f"dat_file='{gp_path(dat_file)}'",
            "-e", f"ph_file='{gp_path(ph_dbl_file)}'",
            "-e", f"out_pdf='{gp_path(tmp_pdf)}'",
            "-e", f"out_png='{gp_path(tmp_png)}'",
            "-e", f"n_lines={n_lines}",
            GP_SCRIPT
        ]
        
        gp_ret = subprocess.run(gp_cmd, capture_output=True, text=True)
        if gp_ret.returncode != 0:
            print(f"[{basename}] Gnuplot warning:\n{gp_ret.stderr}")
            # Don't fail the job, just maybe missing plots
            # But usually if gnuplot fails, we don't get the output files.
        else:
             # 4. Move/Rename final outputs
             shutil.move(tmp_pdf, os.path.join(RESULTS_DIR, f"{basename}.pdf"))
             shutil.move(tmp_png, os.path.join(RESULTS_DIR, f"{basename}.png"))

    except Exception as e:
        print(f"[{basename}] Exception: {e}")
        return False
    finally:
        # Cleanup
        for f in [par_file, dat_file, ph_file, ph_dbl_file]:
            if os.path.exists(f):
                os.remove(f)
                
    return True

def main():
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
    if not os.path.exists(TMP_DIR):
        os.makedirs(TMP_DIR)

    print("Loading flags from legacy Makefile...")
    makefile_flags = parse_makefile()

    print(f"Scanning {DATA_DIR} for data files...")
    all_files = os.listdir(DATA_DIR)
    data_files = [f for f in all_files if os.path.isfile(os.path.join(DATA_DIR, f)) and not f.startswith(".")]
    print(f"Found {len(data_files)} data files.")

    # Sort for consistent order or leave as is
    data_files.sort()

    cpu_count = multiprocessing.cpu_count()
    print(f"Running with {cpu_count} parallel processes...")

    # Prepare jobs
    from functools import partial
    with multiprocessing.Pool(processes=cpu_count) as pool:
        pool.map(partial(run_job, makefile_flags=makefile_flags), data_files)

    print("Analysis finished. Generating report...")
    subprocess.run([sys.executable, REPORT_GENERATOR])
    print("Done.")

if __name__ == "__main__":
    main()