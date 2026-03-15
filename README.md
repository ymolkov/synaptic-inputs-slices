# Synaptic Inputs Slices Analysis

This project implements a data analysis pipeline for electrophysiological recordings from brain slices. It processes raw traces to reconstruct synaptic conductances using a dynamic-Ei pivoting algorithm, aggregates population statistics, and generates publication-ready figures and an interactive dashboard.

## Overview

The core of the pipeline is a C++ analyzer that performs cycle detection and linear regression on membrane current traces to separate excitation and inhibition components. The analyzer reports conductances normalized by leak conductance (`G_exc / g_leak`, `G_inh / g_leak`), and the Python automation layer plus root `Makefile` turn those outputs into CSV summaries, tables, and figures.

## Project Structure

*   **/web**: Local directory containing the interactive analysis dashboard (`index.html`), high-res per-cell snapshots (`_full.png`, `_thumb.png`), and numerical analysis results (`.par`). (Ignored by Git)
*   **/results**: Population-level CSV summaries (`*_conductances.csv`) produced from per-cell analyses.
*   **/paper**: LaTeX manuscript source and final publication figures.
*   **/publication**: Staged publication assets including the formal summary table (LaTeX/Word).
*   **/src**: Core C++ implementation (`trace_analyzer.cpp`) featuring the geometric pivoting algorithm.
*   **/bin**: Destination for the compiled `trace_analyzer` binary.
*   **/scripts**: Automation logic, plotting systems, and deployment tools.
*   **/config**: Global and per-file analysis parameter overrides.

## Building and Usage

The project uses a standard `Makefile` to manage dependencies. Changes to any script or source file will only trigger necessary downstream rebuilds.

### Core Commands
*   `make analysis`: Compiles the C++ analyzer if needed and regenerates the per-group CSV summaries in `/results`.
*   `make table`: Regenerates Table 1 at `publication/conductance_table.tex` from the CSV summaries.
*   `make publication/figures/figure5_circuit_weighted.png`: Regenerates the weighted circuit diagram directly from the same CSV-derived summary values used in Table 1.
*   `make figures`: Regenerates all publication figure assets, including `publication/figures/figure5_circuit_weighted.png`.
*   `make all` (or `make paper`): Builds the LaTeX manuscript (`paper/main.pdf`) and its declared dependencies.
*   `make dashboard`: Processes all 59 data files in parallel and generates the interactive dashboard in the `/web` directory.
*   `make deploy`: (Prerequisite: `lftp`) Synchronizes the local `/web` dashboard to the remote server at `math.gsu.edu` via SFTP. Prompts for password interactively.
*   `make clean`: Removes binaries, temporary files, and local web assets for a fresh start.
*   `make push`: Stages all changes, creates a commit with the fixed message `Build update via Makefile`, and pushes to `origin main`.

## Conductance Conventions

*   The analyzer outputs normalized conductances, not absolute nS values.
*   Table 1 reports `$G_{exc}/g_{leak}$` and `$G_{inh}/g_{leak}$` as mean ± SEM after IQR-based outlier filtering.
*   Figure 4 summarizes those normalized conductances by group and phase.
*   Figure 5 uses the same CSV-derived population means to assign edge thicknesses in the inferred circuit diagram.
*   Connections below the display threshold of `0.05` are clipped from Figure 5.

## Prerequisites

*   **C++ Compiler**: `g++` (C++11 support required).
*   **Python 3**: With `numpy`, `matplotlib`, and `scipy`.
*   **Gnuplot**: Required for trace visualization.
*   **LaTeX**: `pdflatex` required for manuscript compilation.
*   **lftp**: Required for the `make deploy` target.
*   **Pandoc**: (Optional) Used to convert the summary table to Word `.docx`.

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
