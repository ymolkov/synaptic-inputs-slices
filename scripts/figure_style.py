from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

FONT_FAMILY = "DejaVu Sans"
FIGURE_WIDTH_IN = 13.0

TITLE_SIZE = 15
AXIS_LABEL_SIZE = 14
TICK_LABEL_SIZE = 12
LEGEND_SIZE = 12
PANEL_LABEL_SIZE = 17
ANNOTATION_SIZE = 13
SCALEBAR_SIZE = 11
SMALL_SIZE = 11

EXC_COLOR = "#D62728"
INH_COLOR = "#1F77B4"
REF_COLOR = "#2CA02C"
TRACE_COLOR = "#1F77B4"
HIGHLIGHT_COLOR = "#C44E52"
ERROR_COLOR = "#1A1A1A"
GRID_ALPHA = 0.25
VOLTAGE_AXIS_BOUNDS = (-60, 40)


def apply_style() -> None:
    plt.rcParams.update(
        {
            "font.family": FONT_FAMILY,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.titlesize": TITLE_SIZE,
            "axes.labelsize": AXIS_LABEL_SIZE,
            "xtick.labelsize": TICK_LABEL_SIZE,
            "ytick.labelsize": TICK_LABEL_SIZE,
            "legend.fontsize": LEGEND_SIZE,
        }
    )


def save_pdf(fig, output_path: str | Path, **kwargs) -> None:
    options = {"dpi": 300}
    options.update(kwargs)
    fig.savefig(output_path, **options)


def scaled_figsize(width: float, height: float) -> tuple[float, float]:
    return (FIGURE_WIDTH_IN, height * FIGURE_WIDTH_IN / width)


def panel_label(ax, label: str, x: float = -0.12, y: float = 1.05) -> None:
    ax.text(
        x,
        y,
        label,
        transform=ax.transAxes,
        fontsize=PANEL_LABEL_SIZE,
        fontweight="bold",
        va="top",
        ha="left",
    )
