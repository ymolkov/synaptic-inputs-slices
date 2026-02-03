import os
import glob
import csv

def parse_par_file(filepath):
    """Parses a .par file into a dictionary."""
    data = {}
    try:
        with open(filepath, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    try:
                        data[key.strip()] = float(value.strip())
                    except ValueError:
                        data[key.strip()] = value.strip()
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
    return data

def main():
    results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
    output_file = os.path.join(results_dir, 'conductance_summary.csv')
    
    par_files = glob.glob(os.path.join(results_dir, '*.par'))
    
    # Define the fields we want to extract
    fields = [
        'Cell_ID',
        'G_inh_tr', 'G_exc_tr',
        'G_inh_st', 'G_exc_st',
        'G_inh_tr_min', 'G_inh_tr_max',
        'G_exc_tr_min', 'G_exc_tr_max',
        'G_inh_st_min', 'G_inh_st_max',
        'G_exc_st_min', 'G_exc_st_max',
        'Ta', 'Du', 'q'
    ]
    
    data_rows = []
    
    for par_file in par_files:
        basename = os.path.basename(par_file)
        cell_id = os.path.splitext(basename)[0]
        
        par_data = parse_par_file(par_file)
        
        row = {'Cell_ID': cell_id}
        for field in fields[1:]: # Skip Cell_ID as we set it manually
            # specific logic for fields present in par_data
            if field in par_data:
                 row[field] = par_data[field]
            else:
                 row[field] = 'N/A'
        
        data_rows.append(row)

    # Sort rows by Cell_ID for consistency
    data_rows.sort(key=lambda x: x['Cell_ID'])

    # Write to CSV
    try:
        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data_rows)
        print(f"Successfully aggregated results to {output_file}")
    except Exception as e:
        print(f"Error writing CSV: {e}")

if __name__ == "__main__":
    main()
