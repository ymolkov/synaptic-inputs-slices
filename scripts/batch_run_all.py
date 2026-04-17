#!/usr/bin/env python3
import os
import subprocess
import glob
import multiprocessing
from analysis_options import get_flags_map, resolve_flags

def parse_makefile(_makefile_path):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return get_flags_map(project_root, strip_q=True)

def run_single_analysis(args):
    data_file, run_script, options, i, total, web_outdir = args
    basename = os.path.basename(data_file)
    print(f"[{i+1}/{total}] Starting {basename}...")
    cmd = [run_script, data_file] + options.split()
    env = os.environ.copy()
    if web_outdir:
        env["CLAMP_WEB_DIR"] = web_outdir
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=env)
        return True, basename, None
    except subprocess.CalledProcessError as e:
        return False, basename, e.stderr.decode()
    except Exception as e:
        return False, basename, str(e)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    data_dir = os.path.join(project_root, 'data')
    makefile_path = os.path.join(project_root, 'legacy', 'Makefile.orig')
    run_script = os.path.join(script_dir, 'run_analysis.sh')

    import argparse
    parser = argparse.ArgumentParser(description="Batch run analysis and plotting.")
    parser.add_argument('--outdir', type=str, default=None, help="Optional separate directory for web deployment")
    args_cli = parser.parse_args()
    web_outdir = args_cli.outdir
    if web_outdir and not os.path.isabs(web_outdir):
        web_outdir = os.path.join(project_root, web_outdir)

    file_options = parse_makefile(makefile_path)
    data_files = sorted(glob.glob(os.path.join(data_dir, '*')))
    total_files = len(data_files)
    
    print(f"Found {total_files} data files. Starting parallel processing...")

    tasks = []
    for i, data_file in enumerate(data_files):
        basename = os.path.basename(data_file)
        options = resolve_flags(
            basename,
            file_options,
            default_flags="-f 25",
            infer_vc_from_name=True
        )
        tasks.append((data_file, run_script, options, i, total_files, web_outdir))

    # Determine number of processes (CPU count)
    num_processes = multiprocessing.cpu_count()
    print(f"Using {num_processes} parallel processes.")

    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.map(run_single_analysis, tasks)

    success_count = sum(1 for r in results if r[0])
    print(f"\nProcessing complete: {success_count}/{total_files} files succeeded.")
    
    for success, basename, error in results:
        if not success:
            print(f"FAILED: {basename}\n  {error}")

    # Automatically regenerate report at the end
    print("Updating report...")
    report_cmd = ["python3", os.path.join(script_dir, "generate_report.py")]
    if args_cli.outdir:
        report_cmd += ["--outdir", args_cli.outdir]
    subprocess.run(report_cmd)

if __name__ == "__main__":
    main()
