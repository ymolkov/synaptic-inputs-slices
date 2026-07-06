#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np


GROUPS = ("VGAT-I", "VgluT2-I", "VGAT-E", "VgluT2-E")

_PHASE_INDICES = (
    ("expiration", 0, 1),
    ("inspiration", 2, 3),
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_results_dir() -> Path:
    return repo_root() / "results"


def group_csv_path(group: str, results_dir: Path | None = None) -> Path:
    base_dir = default_results_dir() if results_dir is None else Path(results_dir)
    return base_dir / f"{group.replace('-', '_')}_conductances.csv"


def _load_group_matrix(csv_path: Path) -> np.ndarray:
    rows = []
    with csv_path.open("r", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                [
                    float(row["Mean_gExc_Stat"]),
                    float(row["Mean_gInh_Stat"]),
                    float(row["gExc_Phase0"]),
                    float(row["gInh_Phase0"]),
                ]
            )

    if not rows:
        raise ValueError(f"No conductance rows found in {csv_path}")

    return np.asarray(rows, dtype=float)


def _iqr_filtered_mean_sem(values: np.ndarray) -> tuple[float, float, int]:
    q1, q3 = np.percentile(values, [25, 75])
    iqr = q3 - q1
    mask = (values >= q1 - 1.5 * iqr) & (values <= q3 + 1.5 * iqr)
    clean = values[mask]
    mean = float(np.mean(clean)) if len(clean) > 0 else 0.0
    sem = float(np.std(clean, ddof=1) / np.sqrt(len(clean))) if len(clean) > 1 else 0.0
    return mean, sem, int(len(clean))


def summarize_group(group: str, results_dir: Path | None = None) -> dict[str, object]:
    csv_path = group_csv_path(group, results_dir)
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing conductance CSV for {group}: {csv_path}")

    data = _load_group_matrix(csv_path)
    stats = {}
    n_inliers = []

    for phase, exc_index, inh_index in _PHASE_INDICES:
        exc_mean, exc_sem, exc_n = _iqr_filtered_mean_sem(data[:, exc_index])
        inh_mean, inh_sem, inh_n = _iqr_filtered_mean_sem(data[:, inh_index])
        stats[phase] = {
            "exc": exc_mean,
            "exc_sem": exc_sem,
            "inh": inh_mean,
            "inh_sem": inh_sem,
        }
        n_inliers.extend((exc_n, inh_n))

    return {
        "group": group,
        "n_inliers": max(n_inliers),
        "expiration": stats["expiration"],
        "inspiration": stats["inspiration"],
    }


def load_all_group_summaries(results_dir: Path | None = None) -> dict[str, dict[str, object]]:
    return {group: summarize_group(group, results_dir) for group in GROUPS}
