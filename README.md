# Synaptic Inputs Slices Analysis

This project implements a high-performance data analysis pipeline for electrophysiological recordings from brain slices. It processes raw traces to reconstruct synaptic conductances using a dynamic-Ei pivoting algorithm, aggregates population statistics, and generates publication-ready figures and an interactive dashboard.

## Overview

The core of the pipeline is a C++ analyzer that performs cycle detection and linear regression on membrane current traces to separate excitation and inhibition components. This is orchestrated by a Python-based automation layer and a root `Makefile` for reproducible builds.

## Project Structure

*   **/web**: Local directory containing the interactive analysis dashboard (`index.html`), high-res per-cell snapshots (`_full.png`, `_thumb.png`), and numerical analysis results (`.par`). (Ignored by Git)
*   **/results**: Strictly contains the population-level data dependencies (`*_conductances.csv`).
*   **/paper**: LaTeX manuscript source and final publication figures.
*   **/publication**: Staged publication assets including the formal summary table (LaTeX/Word).
*   **/src**: Core C++ implementation (`trace_analyzer.cpp`) featuring the geometric pivoting algorithm.
*   **/bin**: Destination for the compiled `trace_analyzer` binary.
*   **/scripts**: Automation logic, plotting systems, and deployment tools.
*   **/config**: Global and per-file analysis parameter overrides.

## Building and Usage

The project uses a standard `Makefile` to manage dependencies. Changes to any script or source file will only trigger necessary downstream rebuilds.

### Core Commands
*   `make all` (or `make paper`): Compiles the C++ analyzer, runs population analysis, generates all figures, and builds the final LaTeX manuscript (`paper/main.pdf`).
*   `make dashboard`: Processes all 59 data files in parallel and generates the interactive dashboard in the `/web` directory.
*   `make deploy`: (Prerequisite: `lftp`) Synchronizes the local `/web` dashboard to the remote server at `math.gsu.edu` via SFTP. Prompts for password interactively.
*   `make clean`: Removes binaries, temporary files, and local web assets for a fresh start.
*   `make push`: Stages all relevant changes, commits with a timestamped message, and pushes to the remote repository.

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
