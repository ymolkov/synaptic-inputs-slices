import csv
import numpy as np
import os

CSV_PATH = "/Users/ymolkov/clamp/results/VGAT_I_conductances.csv"

def calculate_stats_with_iqr_debug(values, name):
    print(f"\n--- Debug Stats for {name} ---")
    print(f"Raw Values ({len(values)}): {values}")
    
    if not values:
        return 0, 0
    
    m = np.array(values)
    q1 = np.percentile(m, 25)
    q3 = np.percentile(m, 75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    
    print(f"Q1: {q1}, Q3: {q3}, IQR: {iqr}")
    print(f"Bounds: [{lower_bound}, {upper_bound}]")
    
    is_outlier = (m < lower_bound) | (m > upper_bound)
    inliers = m[~is_outlier]
    
    print(f"Inliers ({len(inliers)}): {inliers}")
    
    mean = np.mean(inliers) if len(inliers) > 0 else 0
    print(f"Mean: {mean}")
    return mean

gExc_ph0 = []

with open(CSV_PATH, 'r') as f:
    reader = csv.DictReader(f)
    print("Reading CSV Rows:")
    for row in reader:
        try:
            val = float(row['gExc_Phase0'])
            print(f"  {row['CellID']}: {val}")
            gExc_ph0.append(val)
        except ValueError:
            print(f"  Skipping row: {row}")

calculate_stats_with_iqr_debug(gExc_ph0, "gExc_Phase0")
