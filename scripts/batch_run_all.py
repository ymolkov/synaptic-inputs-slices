#!/usr/bin/env python3
import os
import re
import subprocess
import glob

def parse_makefile(makefile_path):
    """
    Parses the Makefile.orig to extract options for each target.
    Returns a dictionary mapping filename (without extension) to options string.
    """
    options_map = {}
    with open(makefile_path, 'r') as f:
        lines = f.readlines()

    current_target = None
    
    # Regex to find target definition: e.g. "VgluT2-I-Cell2-V.pdf: ..."
    target_regex = re.compile(r'^([a-zA-Z0-9_-]+)\.pdf:')
    # Regex to find command line: e.g. "./med2 -f 25 -q .003 -vc <$(basename $@) >dat 2>ph; ..."
    # We want to capture everything between ./med2 and <
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
                current_target = None # Reset after finding options

    return options_map

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    data_dir = os.path.join(project_root, 'data')
    makefile_path = os.path.join(project_root, 'legacy', 'Makefile.orig')
    run_script = os.path.join(script_dir, 'run_analysis.sh')

    print(f"Parsing {makefile_path}...")
    file_options = parse_makefile(makefile_path)
    print(f"Found options for {len(file_options)} files.")

    data_files = glob.glob(os.path.join(data_dir, '*'))
    data_files.sort()
    
    total_files = len(data_files)
    print(f"Found {total_files} data files in {data_dir}.")

    for i, data_file in enumerate(data_files):
        basename = os.path.basename(data_file)
        print(f"[{i+1}/{total_files}] Processing {basename}...")

        options = file_options.get(basename)
        if options:
            print(f"  Using specific options: {options}")
        else:
            # Default options if not found in Makefile
            options = "-f 25 -h 1000 -vc" # Baseline common options
            print(f"  Using default options: {options}")

        # Construct command
        # run_analysis.sh <data_file> [options]
        cmd = [run_script, data_file] + options.split()

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"  Error processing {basename}: {e}")
        except Exception as e:
             print(f"  An unexpected error occurred for {basename}: {e}")

if __name__ == "__main__":
    main()
