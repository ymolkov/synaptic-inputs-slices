import csv
import math
import numpy as np
import os

# Configuration
RESULTS_DIR = "/Users/ymolkov/clamp/results"
GROUPS = {
    "VGAT-I": os.path.join(RESULTS_DIR, "VGAT_I_conductances.csv"),
    "VgluT2-I": os.path.join(RESULTS_DIR, "VgluT2_I_conductances.csv"),
    "VGAT-E": os.path.join(RESULTS_DIR, "VGAT_E_conductances.csv"),
}

def calculate_stats_with_iqr(values):
    """Calculates mean and SEM after removing IQR outliers, matching plot_combined_summary.py"""
    if not values:
        return 0.0, 0.0
    
    m = np.array(values)
    q1 = np.percentile(m, 25)
    q3 = np.percentile(m, 75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    
    is_outlier = (m < lower_bound) | (m > upper_bound)
    inliers = m[~is_outlier]
    
    if len(inliers) == 0:
        return 0.0, 0.0
    
    mean = np.mean(inliers)
    sem = np.std(inliers, ddof=1) / np.sqrt(len(inliers)) if len(inliers) > 1 else 0.0
    return mean, sem

def analyze_groups():
    print(f"{'Target Population':<18} | {'Source (Input)':<25} | {'Metric':<15} | {'Mean +/- SEM (Inliers)':<25} | {'Rank'}")
    print("-" * 110)

    for group_name, csv_path in GROUPS.items():
        if not os.path.exists(csv_path):
            print(f"Skipping {group_name}: {csv_path} not found")
            continue
            
        # Read Data
        gExc_st = [] # Mean_gExc_Stat
        gInh_st = [] # Mean_gInh_Stat
        gExc_ph0 = [] # gExc_Phase0
        gInh_ph0 = [] # gInh_Phase0
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    gExc_st.append(float(row['Mean_gExc_Stat']))
                    gInh_st.append(float(row['Mean_gInh_Stat']))
                    gExc_ph0.append(float(row['gExc_Phase0']))
                    gInh_ph0.append(float(row['gInh_Phase0']))
                except ValueError:
                    continue
        
        # Calculate Stats (Mean of Inliers)
        stats = {
            'Gi_tr': calculate_stats_with_iqr(gInh_ph0), # Inhibition during Insp
            'Gi_st': calculate_stats_with_iqr(gInh_st),  # Inhibition during Exp
            'Ge_tr': calculate_stats_with_iqr(gExc_ph0), # Excitation during Insp
            'Ge_st': calculate_stats_with_iqr(gExc_st)   # Excitation during Exp
        }

        # Define Source Map based on Phase/Type logic
        source_map = {
            'Gi_tr': 'VGAT-I (Inh, Insp)',
            'Gi_st': 'VGAT-E (Inh, Exp)',
            'Ge_tr': 'VgluT2-I (Exc, Insp)',
            'Ge_st': 'Unknown (Exc, Exp)' 
        }

        # Select metrics to rank
        # We rank all 4 to see complete picture, but usually Ge_st is weak/negligible
        metrics_to_rank = ['Gi_tr', 'Gi_st', 'Ge_tr', 'Ge_st']
        
        ranked_results = []
        for metric in metrics_to_rank:
            mean, sem = stats[metric]
            ranked_results.append({
                'metric': metric,
                'mean': mean,
                'sem': sem,
                'desc': source_map[metric]
            })
            
        ranked_results.sort(key=lambda x: x['mean'], reverse=True)
        
        ranks = ['Strong', 'Moderate', 'Weak']
        
        for i, item in enumerate(ranked_results):
            rank_label = ranks[i] if i < 3 else 'Weak'
            print(f"{group_name:<18} | {item['desc']:<25} | {item['metric']:<15} | {item['mean']:.4f} +/- {item['sem']:.4f}   | {rank_label}")
        print("-" * 110)

if __name__ == "__main__":
    analyze_groups()
