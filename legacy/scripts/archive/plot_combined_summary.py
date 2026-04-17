import os
import csv
import matplotlib.pyplot as plt
import numpy as np

# Configuration
RESULTS_DIR = "results"
GROUPS = [
    ("VGAT-I", os.path.join(RESULTS_DIR, "VGAT_I_conductances.csv")),
    ("VgluT2-I", os.path.join(RESULTS_DIR, "VgluT2_I_conductances.csv")),
    ("VGAT-E", os.path.join(RESULTS_DIR, "VGAT_E_conductances.csv")),
]
OUTPUT_PLOT = os.path.join(RESULTS_DIR, "combined_conductance_summary.png")

def get_stats_and_data(csv_path):
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return None
        
    data = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
            
    if not data:
        return None

    # Extract metrics
    # Metrics: Mean_gExc_Stat, Mean_gInh_Stat, gExc_Phase0, gInh_Phase0
    gExc_st = [float(row['Mean_gExc_Stat']) for row in data]
    gInh_st = [float(row['Mean_gInh_Stat']) for row in data]
    gExc_ph0 = [float(row['gExc_Phase0']) for row in data]
    gInh_ph0 = [float(row['gInh_Phase0']) for row in data]
    
    metrics = [gExc_st, gInh_st, gExc_ph0, gInh_ph0]
    
    # Statistics with IQR Outlier Handling
    means = []
    sems = []
    inliers_list = []
    outliers_list = []

    for m in metrics:
        m = np.array(m)
        q1 = np.percentile(m, 25)
        q3 = np.percentile(m, 75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        is_outlier = (m < lower_bound) | (m > upper_bound)
        inliers = m[~is_outlier]
        outliers = m[is_outlier]
        
        mean = np.mean(inliers) if len(inliers) > 0 else 0
        sem = np.std(inliers, ddof=1) / np.sqrt(len(inliers)) if len(inliers) > 1 else 0
        
        means.append(mean)
        sems.append(sem)
        inliers_list.append(inliers)
        outliers_list.append(outliers)
        
    return means, sems, inliers_list, outliers_list, len(data)

# Main Plotting
fig, axes = plt.subplots(1, 3, figsize=(16, 6), sharey=True)
labels = ['gExc\n(Expiration)', 'gInh\n(Expiration)', 'gExc\n(Inspiration)', 'gInh\n(Inspiration)']
colors = ['salmon', 'skyblue', 'red', 'blue']
x = np.arange(len(labels))

for i, (group_name, csv_path) in enumerate(GROUPS):
    ax = axes[i]
    stats = get_stats_and_data(csv_path)
    
    if not stats:
        ax.text(0.5, 0.5, "No Data", ha='center')
        continue
        
    means, sems, inliers_list, outliers_list, N = stats
    
    # Bars
    bars = ax.bar(x, means, yerr=sems, align='center', alpha=0.8, color=colors, ecolor='black', capsize=10)
    
    # Scatter points
    for j in range(len(x)):
        # Inliers
        if len(inliers_list[j]) > 0:
            jitter_in = np.random.normal(0, 0.04, size=len(inliers_list[j]))
            ax.scatter(x[j] + jitter_in, inliers_list[j], color='darkslategrey', alpha=0.5, zorder=10, s=15, label='Inliers' if i==0 and j==0 else "")
            
        # Outliers
        if len(outliers_list[j]) > 0:
            jitter_out = np.random.normal(0, 0.04, size=len(outliers_list[j]))
            ax.scatter(x[j] + jitter_out, outliers_list[j], color='magenta', marker='x', alpha=1.0, zorder=11, s=40, linewidth=2, label='Outliers' if i==0 and j==0 else "")

    ax.set_title(f"{group_name} (N={N})")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15)
    ax.set_ylim(0, 0.6)
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    if i == 0:
        ax.set_ylabel('Conductance (nS)')
        # Legend
        handles, leg_labels = ax.get_legend_handles_labels()
        if handles:
            by_label = dict(zip(leg_labels, handles))
            ax.legend(by_label.values(), by_label.keys(), loc='upper right')

plt.suptitle("Population Summary: Expiration vs Inspiration Conductances (Inlier Mean +/- SEM)", fontsize=14)
plt.tight_layout()
plt.savefig(OUTPUT_PLOT)
print(f"Saved combined summary plot to {OUTPUT_PLOT}")
