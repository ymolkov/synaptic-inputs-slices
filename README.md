# Synaptic Inputs Slices Analysis

This project implements a data analysis pipeline for electrophysiological recordings from brain slices. It processes raw traces to detect periodic synaptic events, analyzes their phase dependence, and visualizes the results.

## Project Structure

*   **`src/`**: Contains the core C++ source code (`trace_analyzer.cpp`) for signal processing, median filtering, and phase-dependent regression.
*   **`scripts/`**: Python and Shell scripts for orchestration and visualization.
    *   `batch_runner.py`: The main entry point. Orchestrates parallel analysis of all data files.
    *   `analysis_options.py`: Shared parser/resolver for per-file processing flags.
    *   `run_analysis.sh`: Wrapper script that compiles the C++ tool and runs the pipeline for a single file.
    *   `plot_traces.gp`: Gnuplot script for generating visualization (linear and polar plots).
    *   `generate_report.py`: Generates an HTML gallery of the results.
*   **`config/`**:
    *   `analysis_flags_overrides.txt`: Sole source of per-file processing options (one `basename = flags` entry per data file).
*   **`data/`**: Directory containing the raw experimental data files (e.g., `VGAT-*-*`, `VgluT2-*-*`).
*   **`results/`**: Output directory where generated PDFs, PNG thumbnails, and the `index.html` report are stored.
*   **`publication/`**: Dedicated folder for publication-ready figures and captions.
    *   `figures/`: Generated figure files (PNG).
    *   `captions.md`: Figure captions.
*   **`legacy/`**: Contains original Makefiles and older code versions for reference.
*   **`bin/`**: Destination for compiled executables.

## Prerequisites

*   **C++ Compiler**: `g++` (GCC) with C++11 support or later.
*   **Python 3**: For the runner scripts.
*   **Gnuplot**: For generating plots (`gnuplot` must be in your PATH).
*   **Standard Unix Tools**: `bash`, `cat`, `grep`, `mv`, `rm`.

## Usage

### 1. Run the Analysis
To process all data files in the `data/` directory in parallel and generate the report:

```bash
python3 scripts/batch_runner.py
```

Equivalent command (same behavior) used in publication runs:

```bash
python3 scripts/batch_run_all.py
```

This script will:
1.  Compile the analyzer if necessary.
2.  Detect all valid data files in `data/`.
3.  Run the analysis on available CPU cores.
4.  Generate PDF plots and PNG thumbnails in `results/`.

### 2. Generate/Update Report
The batch runner automatically invokes the report generator, but you can run it manually if needed:

```bash
python3 scripts/generate_report.py
```

### 3. Generate Publication Figures
To generate all figures and captions:

```bash
python3 scripts/make_publication_figures.py
```

To regenerate a specific figure (e.g., Figure 1):

```bash
python3 scripts/make_publication_figures.py --fig1
```

Options: `--fig1`, `--fig2`, `--fig3`, `--supp1`, `--supp2`, `--captions`.

### 4. Configure Per-File Processing Flags
All per-file analyzer flags are resolved from:

```text
config/analysis_flags_overrides.txt
```

Format:

```text
<data basename> = <flags>
```

Example:

```text
VgluT2-I-Cell6-V = -f 25 -h 1000 -vc -k 150 -s -1 -W 2000 -Ei -60
```

Notes:
1. This file is the only place to edit custom processing options.
2. For `*-V*` files, `-vc` is auto-added if missing.
3. If a basename is not listed, default flags `-f 25` are used.

### 5. Rebuild Group Conductance CSV/Plots (Figure 3 inputs)
Per-group CSVs/plots are generated with:

```bash
python3 scripts/batch_analyze_conductances.py --group VGAT-I
python3 scripts/batch_analyze_conductances.py --group VgluT2-I
python3 scripts/batch_analyze_conductances.py --group VGAT-E
```

Behavior:
1. By default, it reuses existing `results/<basename>.par` files (fast, reproducible).
2. Use `--force-rerun` to recompute `.par` from raw data with current flags.

### 6. View Results
Open `results/index.html` in your web browser to view the organized gallery of analysis results.

## Analysis Details

The core analyzer (`trace_analyzer`) performs the following:
*   **Filtering**: Applies median filtering to smooth the raw traces and the reference signal.
*   **Thresholding**: Uses a robust MAD (Median Absolute Deviation) based approach to automatically detect periodic cycles in the reference signal, separating them from background noise.
*   **Phase Analysis**: Bins the data by phase and performs linear regression to separate excitation (red) and inhibition (blue) components.
*   **Visualization**: Generates linear traces and polar plots to visualize the phase-dependent modulation of synaptic inputs.

## License

Private repository. All rights reserved.
