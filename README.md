# Synaptic Inputs Slices Analysis

This project implements a data analysis pipeline for electrophysiological recordings from brain slices. It processes raw traces to reconstruct synaptic conductances using a dynamic-Ei pivoting algorithm, aggregates population statistics, and generates publication-ready figures and an interactive dashboard.

## Overview

The core of the pipeline is a C++ analyzer that performs cycle detection and linear regression on membrane current traces to separate excitation and inhibition components. The analyzer reports conductances normalized by leak conductance (`G_exc / g_leak`, `G_inh / g_leak`), and the Python automation layer plus root `Makefile` turn those outputs into CSV summaries and manuscript figures.

## Project Structure

*   **/web**: Local directory containing the companion site (`index.html`), the interactive analysis dashboard (`dashboard.html`), site figures in `assets/site/`, and generated per-recording snapshots/parameters in `assets/recordings/`. This directory is generated/deployable output and is ignored by Git.
*   **/results**: Population-level CSV summaries (`*_conductances.csv`) produced from per-cell analyses.
*   **/paper**: LaTeX manuscript source, supplemental LaTeX, and the generated PDF figures used by the paper.
*   **/src**: Core C++ implementation (`trace_analyzer.cpp`) featuring the geometric pivoting algorithm.
*   **/bin**: Destination for the compiled `trace_analyzer` binary.
*   **/scripts**: Automation logic, plotting systems, and deployment tools.
*   **/config**: Global and per-file analysis parameter overrides.

## Building and Usage

The project uses a standard `Makefile` to manage dependencies. Changes to any script or source file will only trigger necessary downstream rebuilds.

### Core Commands
*   `make analysis`: Compiles the C++ analyzer if needed and regenerates the per-group CSV summaries in `/results`.
*   `make paper/figures/circuit_weighted.pdf`: Regenerates the weighted circuit diagram directly from the CSV-derived summary values.
*   `make figures`: Regenerates all generated PDF figures used by the manuscript.
*   `make all` (or `make paper`): Builds the LaTeX manuscript (`paper/Synaptic_Architecture_PreBotC.pdf`) plus the supplemental section and its declared dependencies.
*   `make dashboard`: Processes all 59 data files in parallel, writes per-recording dashboard artifacts to `web/assets/recordings/`, and regenerates `web/dashboard.html`.
*   `make deploy`: (Prerequisite: `lftp`) Synchronizes the local `/web` dashboard to the remote server at `math.gsu.edu` via SFTP. Prompts for password interactively.
*   `make clean`: Removes binaries, temporary files, and local web assets for a fresh start.
*   `make push`: Stages all changes, creates a commit with the fixed message `Build update via Makefile`, and pushes to `origin main`.

## Companion Site and Dashboard

The web companion is a static, deployable view of the method and its per-recording analysis outputs. It is intentionally kept out of Git because the dashboard artifacts are generated from the raw data and analysis scripts.

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

## Conductance Conventions

*   The analyzer outputs normalized conductances, not absolute nS values.
*   Table 1 reports `$G_{exc}/g_{leak}$` and `$G_{inh}/g_{leak}$` as mean ± SEM after IQR-based outlier filtering.
*   Figure 4 summarizes those normalized conductances by group at target phases (Inspiration/Expiration). Additionally, the accompanying Figure 4 Phase Summary visualizes the full -0.25 to 0.25 phase interval for representative single cells, plotted natively as Synaptic / Leak Conductance.
*   Figure 5 uses the same CSV-derived population means to assign edge thicknesses in the inferred circuit diagram.
*   Connections below the display threshold of `0.05` are clipped from Figure 5.

## Prerequisites

*   **C++ Compiler**: `g++` (C++11 support required).
*   **Python 3**: With `numpy`, `matplotlib`, and `scipy`.
*   **Gnuplot**: Required for trace visualization.
*   **LaTeX**: `pdflatex` required for manuscript compilation.
*   **lftp**: Required for the `make deploy` target.

## Configuration

Analysis parameters (e.g., frequencies, thresholds, Ei overrides) are managed in:
`config/analysis_flags_overrides.txt`

Format: `basename = <flags>`
Example: `VgluT2-E-Cell1-V = -f 25 -x 100000`

## Authors

*   **Y. Molkov** (Primary Investigator)
*   Antigravity AI (Implementation and Refactoring)

---
*Private Research Repository*
