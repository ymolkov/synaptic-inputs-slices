# SCION: Synaptic Conductance Inference for Oscillating Networks

This repository packages the **SCION** conductance-inference workflow for intracellular recordings from cells embedded in periodically active neural networks. It reconstructs phase-resolved excitatory and inhibitory synaptic conductance profiles from aligned current, voltage, and cycle-reference traces, then turns those profiles into population summaries, manuscript figures, and an interactive static dashboard.

The respiratory slice dataset in this repository is the worked example accompanying the slice manuscript (preprint forthcoming on [bioRxiv](https://www.biorxiv.org/)). The same inference strategy was introduced and validated on mature rat in situ respiratory CPG recordings in the eLife article [Inference technique for the synaptic conductances in rhythmically active networks and application to respiratory central pattern generation circuits](https://doi.org/10.7554/eLife.101959) (Molkov et al., 2025, eLife 13:RP101959).

Live companion site: [ymolkov.github.io/synaptic-inputs-slices](https://ymolkov.github.io/synaptic-inputs-slices/)

## Overview

The core of the pipeline is a C++ analyzer that detects network-cycle phase, pools current-voltage samples by phase, fits local I-V relationships, estimates recording-specific reversal geometry, and separates excitation from inhibition. The analyzer reports conductances normalized by leak conductance (`G_exc / g_leak`, `G_inh / g_leak`), and the Python automation layer plus root `Makefile` turn those outputs into CSV summaries, manuscript figures, and a companion web view.

SCION is designed around a reusable pattern:

*   align intracellular recordings to a reliable network phase reference;
*   pool samples from many cycles and command levels into phase bins;
*   fit local I-V relationships and infer reversal-potential geometry;
*   reconstruct excitatory and inhibitory conductance profiles through the cycle;
*   use those conductance profiles as evidence for functional circuit interactions in the studied rhythm.

## Project Structure

*   **/web**: Tracked companion site (`index.html`), interactive analysis dashboard (`dashboard.html`), site figures in `assets/site/`, and generated per-recording snapshots/parameters in `assets/recordings/`.
*   **/results**: Population-level CSV summaries (`*_conductances.csv`) produced from per-cell analyses.
*   **/paper**: LaTeX manuscript source, supplemental LaTeX, and the generated PDF figures used by the paper.
*   **/src**: Core C++ implementation (`trace_analyzer.cpp`) featuring the geometric pivoting algorithm.
*   **/bin**: Destination for the compiled `trace_analyzer` binary.
*   **/scripts**: Automation logic and plotting systems used by the Makefile targets.
*   **/config**: Global and per-file analysis parameter overrides.

## Building and Usage

The project uses a standard `Makefile` to manage dependencies. Changes to any script or source file will only trigger necessary downstream rebuilds.

### Core Commands
*   `make analysis`: Compiles the C++ analyzer if needed and regenerates the per-group CSV summaries in `/results`.
*   `make paper/figures/circuit_weighted.pdf`: Regenerates the weighted circuit diagram directly from the CSV-derived summary values.
*   `make figures`: Regenerates all generated PDF figures used by the manuscript.
*   `make all` (or `make paper`): Builds the LaTeX manuscript (`paper/Synaptic_Architecture_PreBotC.pdf`) plus the supplemental section and its declared dependencies.
*   `make dashboard`: Processes all 59 data files in parallel, writes per-recording dashboard artifacts to `web/assets/recordings/`, and regenerates `web/dashboard.html`.
*   `make clean`: Removes binaries, temporary files, and generated web output for a fresh start. Regenerate `web/` before committing if you want to preserve the tracked companion-site snapshot.

## Method Companion Site and Dashboard

The web companion is a static, deployable view of the method and its per-recording analysis outputs. It frames SCION as the reusable method across studies while keeping the respiratory slice recordings as the inspectable worked example.

The site links the current repository to the prior eLife method paper:

*   **Molkov et al. 2025, eLife 13:RP101959**: introduced the inference technique and used in situ respiratory CPG recordings to infer synaptic conductance profiles and functional respiratory connectomes.
*   **This repository**: applies the same method to VgluT2/VGAT respiratory slice recordings, with reproducible scripts, generated figures, and a browser for every per-recording analysis artifact.

The generated layout is:

```text
web/
  index.html
  index.css
  index.js
  dashboard.html
  assets/
    site/         # companion-site figures and hero imagery
    recordings/  # generated *_full.png, *_thumb.png, and *.par files
```

`scripts/run_analysis.sh` writes recording-level images and parameter files into `web/assets/recordings/`. `scripts/generate_report.py` scans that directory, parses the `.par` files, and embeds the dashboard index as static JSON inside `web/dashboard.html`. The dashboard can therefore be opened locally or deployed as plain static files without a server-side backend.

To publish the companion site with GitHub Pages, set the repository Pages source to GitHub Actions. The workflow in `.github/workflows/pages.yml` publishes `web/` as the site root.

## Conductance Conventions

*   The analyzer outputs normalized conductances, not absolute nS values.
*   Table 1 reports `$G_{exc}/g_{leak}$` and `$G_{inh}/g_{leak}$` as mean ± SEM after IQR-based outlier filtering.
*   Figure 4 summarizes those normalized conductances by group at target phases (Inspiration/Expiration). Additionally, the accompanying Figure 4 Phase Summary visualizes the full -0.25 to 0.25 phase interval for representative single cells, plotted natively as Synaptic / Leak Conductance.
*   Figure 5 uses the same CSV-derived population means to assign edge thicknesses in the inferred circuit diagram.
*   Connections below the display threshold of `0.05` are clipped from Figure 5.

## Prerequisites

*   **C++ Compiler**: `g++` (C++11 support required).
*   **Python 3**: With `numpy`, `matplotlib`, and `scipy`.
*   **LaTeX**: `pdflatex` required for manuscript compilation.

## Configuration

Analysis parameters (e.g., frequencies, thresholds, Ei overrides) are managed in:
`config/analysis_flags_overrides.txt`

Format: `basename = <flags>`
Example: `VgluT2-E-Cell1-V = -f 25 -x 100000`

## Authors

*   **Yaroslav I. Molkov** - [math.gsu.edu/ymolkov](https://math.gsu.edu/ymolkov)<br>
    Department of Mathematics and Statistics, Georgia State University, Atlanta, GA, USA<br>
    Neuroscience Institute, Georgia State University, Atlanta, GA, USA
*   **Hidehiko Koizumi**<br>
    Cellular and Systems Neurobiology Section, National Institute of Neurological Disorders and Stroke, National Institutes of Health, Bethesda, MD, USA
*   **Jeffrey C. Smith**<br>
    Cellular and Systems Neurobiology Section, National Institute of Neurological Disorders and Stroke, National Institutes of Health, Bethesda, MD, USA

## How to cite

If SCION informs your work, please cite both papers:

*   **Method paper.** Molkov YI, Borgmann A, Koizumi H, Hama N, Zhang R, Smith JC. *Inference technique for the synaptic conductances in rhythmically active networks and application to respiratory central pattern generation circuits.* eLife 13:RP101959 (2025). [doi.org/10.7554/eLife.101959](https://doi.org/10.7554/eLife.101959)
*   **Slice study (this repository).** Molkov YI, Koizumi H, Smith JC. *Synaptic architecture of the preBötzinger Complex inferred from conductance profiling of genetically identified VgluT2 and VGAT neurons.* Manuscript in preparation; preprint forthcoming on bioRxiv.

## License

This repository is shared under the Creative Commons Attribution 4.0 International License (CC BY 4.0) unless otherwise noted. See [LICENSE](LICENSE).
