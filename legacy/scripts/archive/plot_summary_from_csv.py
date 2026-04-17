import os
import csv
import matplotlib.pyplot as plt
import numpy as np
import argparse

# Setup Argparse
parser = argparse.ArgumentParser(description='Create summary bar plot from conductance CSV.')
parser.add_argument('input_csv', type=str, help='Path to the input CSV file')
args = parser.parse_args()

INPUT_CSV = args.input_csv

if not os.path.exists(INPUT_CSV):
    print(f"Error: {INPUT_CSV} not found.")
    exit(1)

# Derive output name: <basename>_summary_bar.png
dirname = os.path.dirname(INPUT_CSV)
basename = os.path.splitext(os.path.basename(INPUT_CSV))[0]
OUTPUT_PLOT = os.path.join(dirname, f"{basename}_summary_bar.png")
GROUP_NAME = basename.replace('_conductances', '').replace('_', '-') # Approximation

# Read CSV
data = []
with open(INPUT_CSV, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        data.append(row)

if not data:
    print("Error: No data in CSV.")
    exit(1)

# Extract metrics
# Metrics: Mean_gExc_Stat, Mean_gInh_Stat, gExc_Phase0, gInh_Phase0
# Convert to float
gExc_st = [float(row['Mean_gExc_Stat']) for row in data]
gInh_st = [float(row['Mean_gInh_Stat']) for row in data]
gExc_ph0 = [float(row['gExc_Phase0']) for row in data]
gInh_ph0 = [float(row['gInh_Phase0']) for row in data]

# Calculate Statistics and Filter Outliers
metrics = [gExc_st, gInh_st, gExc_ph0, gInh_ph0]
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

# Plotting
labels = ['Mean gExc (Stationary)', 'Mean gInh (Stationary)', 'gExc (Phase 0)', 'gInh (Phase 0)']
x = np.arange(len(labels))
colors = ['salmon', 'skyblue', 'red', 'blue']

fig, ax = plt.subplots(figsize=(10, 7))

# Bars with Error Bars (Inliers only)
bars = ax.bar(x, means, yerr=sems, align='center', alpha=0.8, color=colors, ecolor='black', capsize=10)

# Overlay individual points
for i in range(len(metrics)):
    # Plot Inliers
    jitter_in = np.random.normal(0, 0.04, size=len(inliers_list[i]))
    ax.scatter(x[i] + jitter_in, inliers_list[i], color='darkslategrey', alpha=0.5, zorder=10, s=15, label='Inliers' if i == 0 else "")
    
    # Plot Outliers
    if len(outliers_list[i]) > 0:
        jitter_out = np.random.normal(0, 0.04, size=len(outliers_list[i]))
        ax.scatter(x[i] + jitter_out, outliers_list[i], color='magenta', marker='x', alpha=1.0, zorder=11, s=40, linewidth=2, label='Outliers' if i == 0 else "")

# Handle legend duplication
handles, leg_labels = ax.get_legend_handles_labels()
by_label = dict(zip(leg_labels, handles))
ax.legend(by_label.values(), by_label.keys())

ax.set_ylabel('Conductance (nS)')
ax.set_title(f'{GROUP_NAME} Population Summary (Inlier Mean +/- SEM, N={len(data)})')
ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=15)
ax.set_ylim(0, 1)  # Standardized Y-axis scale
ax.yaxis.grid(True, linestyle='--', alpha=0.7)

# Add values on top of bars
for bar, mean, sem in zip(bars, means, sems):
    height = bar.get_height()
    #ax.text(bar.get_x() + bar.get_width() / 2, height + sem + 0.05, f'{mean:.2f}', ha='center', va='bottom')

plt.tight_layout()
plt.savefig(OUTPUT_PLOT)
print(f"Saved summary bar plot to {OUTPUT_PLOT} (Outliers excluded from stats)")
