#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from conductance_summary import GROUPS, load_all_group_summaries, repo_root


def main() -> None:
    root = repo_root()
    summaries = load_all_group_summaries(root / "results")

    print("| Group | N | Phase | Excitation (G_exc / g_leak) | Inhibition (G_inh / g_leak) |")
    print("|-------|---|-------|-----------------------------|------------------------------|")

    latex_lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Summary of reconstructed synaptic conductances normalized by leak conductance across neuronal populations.}",
        r"\label{tab:conductance_summary}",
        r"\begin{tabular}{lcccc}",
        r"\hline",
        r"Group (N) & Phase & $G_{exc}/g_{leak}$ & $G_{inh}/g_{leak}$ \\",
        r"\hline",
    ]

    for group in GROUPS:
        summary = summaries[group]
        n_inliers = summary["n_inliers"]
        expiration = summary["expiration"]
        inspiration = summary["inspiration"]

        print(
            f"| {group} | {n_inliers} | Expiration | "
            f"{expiration['exc']:.4f} ± {expiration['exc_sem']:.4f} | "
            f"{expiration['inh']:.4f} ± {expiration['inh_sem']:.4f} |"
        )
        print(
            f"| | | Inspiration | "
            f"{inspiration['exc']:.4f} ± {inspiration['exc_sem']:.4f} | "
            f"{inspiration['inh']:.4f} ± {inspiration['inh_sem']:.4f} |"
        )

        latex_lines.append(
            f"{group} ({n_inliers}) & Expiration & "
            f"{expiration['exc']:.3f} $\\pm$ {expiration['exc_sem']:.3f} & "
            f"{expiration['inh']:.3f} $\\pm$ {expiration['inh_sem']:.3f} \\\\"
        )
        latex_lines.append(
            f"& Inspiration & "
            f"{inspiration['exc']:.3f} $\\pm$ {inspiration['exc_sem']:.3f} & "
            f"{inspiration['inh']:.3f} $\\pm$ {inspiration['inh_sem']:.3f} \\\\"
        )
        latex_lines.append(r"\hline")

    latex_lines.extend([r"\end{tabular}", r"\end{table}"])

    output_path = root / "publication" / "conductance_table.tex"
    output_path.write_text("\n".join(latex_lines) + "\n")
    print(f"\nLaTeX Table saved to {output_path}")


if __name__ == "__main__":
    main()
