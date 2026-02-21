import csv
import numpy as np
import os

results_dir = "/Users/ymolkov/clamp/results"
groups = ["VGAT-I", "VgluT2-I", "VGAT-E", "VgluT2-E"]
files = ["VGAT_I_conductances.csv", "VgluT2_I_conductances.csv", "VGAT_E_conductances.csv", "VgluT2_E_conductances.csv"]

print("| Group | N | Phase | Excitation (nS) | Inhibition (nS) |")
print("|-------|---|-------|-----------------|-----------------|")

latex_table = r"""\begin{table}[htbp]
\centering
\caption{Summary of reconstructed synaptic conductances across neuronal populations.}
\label{tab:conductance_summary}
\begin{tabular}{lcccc}
\hline
Group (N) & Phase & $G_{exc}$ (nS) & $G_{inh}$ (nS) \\
\hline
"""

for group, filename in zip(groups, files):
    path = os.path.join(results_dir, filename)
    if not os.path.exists(path):
        continue
        
    data = []
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append([
                float(row['Mean_gExc_Stat']), float(row['Mean_gInh_Stat']),
                float(row['gExc_Phase0']), float(row['gInh_Phase0'])
            ])
            
    data = np.array(data)
    
    # Extract stats using IQR filtering as in the plotting script
    stats = []
    for j in range(4):
        m = data[:, j]
        q1, q3 = np.percentile(m, [25, 75])
        iqr = q3 - q1
        mask = (m >= q1 - 1.5*iqr) & (m <= q3 + 1.5*iqr)
        clean = m[mask]
        mean = np.mean(clean) if len(clean) > 0 else 0
        sem = np.std(clean, ddof=1) / np.sqrt(len(clean)) if len(clean) > 1 else 0
        stats.append((mean, sem))
        
    m = data[:, 0]
    q1, q3 = np.percentile(m, [25, 75])
    iqr = q3 - q1
    n_filtered = np.sum((m >= q1 - 1.5*iqr) & (m <= q3 + 1.5*iqr))

    # Markdown rows
    print(f"| {group} | {n_filtered} | Expiration | {stats[0][0]:.4f} ± {stats[0][1]:.4f} | {stats[1][0]:.4f} ± {stats[1][1]:.4f} |")
    print(f"| | | Inspiration | {stats[2][0]:.4f} ± {stats[2][1]:.4f} | {stats[3][0]:.4f} ± {stats[3][1]:.4f} |")
    
    # LaTeX rows
    latex_table += f"{group} ({n_filtered}) & Expiration & {stats[0][0]:.3f} $\pm$ {stats[0][1]:.3f} & {stats[1][0]:.3f} $\pm$ {stats[1][1]:.3f} \\\\\n"
    latex_table += f"& Inspiration & {stats[2][0]:.3f} $\pm$ {stats[2][1]:.3f} & {stats[3][0]:.3f} $\pm$ {stats[3][1]:.3f} \\\\\n"
    latex_table += "\\hline\n"

latex_table += r"""\end{tabular}
\end{table}"""

output_path = "/Users/ymolkov/clamp/publication/conductance_table.tex"
with open(output_path, "w") as f:
    f.writelines(latex_table)

print(f"\nLaTeX Table saved to {output_path}")
