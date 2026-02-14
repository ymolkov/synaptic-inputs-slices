#!/usr/bin/env python3
import os
import re
import subprocess
import glob
import multiprocessing

def parse_makefile(makefile_path):
    options_map = {}
    if not os.path.exists(makefile_path):
        return options_map
    with open(makefile_path, 'r') as f:
        lines = f.readlines()
    current_target = None
    target_regex = re.compile(r'^([a-zA-Z0-9_-]+)\.pdf:')
    command_regex = re.compile(r'\./med2\s+(.*?)\s*<')
    for line in lines:
        target_match = target_regex.match(line)
        if target_match:
            current_target = target_match.group(1)
            continue
        if current_target:
            command_match = command_regex.search(line)
            if command_match:
                options = command_match.group(1).strip()
                options_map[current_target] = options
                current_target = None
    return options_map

def run_single_analysis(args):
    data_file, run_script, options, i, total = args
    basename = os.path.basename(data_file)
    print(f"[{i+1}/{total}] Starting {basename}...")
    cmd = [run_script, data_file] + options.split()
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
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

    file_options = parse_makefile(makefile_path)
    data_files = sorted(glob.glob(os.path.join(data_dir, '*')))
    total_files = len(data_files)
    
    print(f"Found {total_files} data files. Starting parallel processing...")

    tasks = []
    for i, data_file in enumerate(data_files):
        basename = os.path.basename(data_file)
        options = file_options.get(basename, "-f 25 -h 1000 -vc")
        tasks.append((data_file, run_script, options, i, total_files))

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
    subprocess.run(["/usr/bin/python3", os.path.join(script_dir, "generate_report.py")])

if __name__ == "__main__":
    main()
