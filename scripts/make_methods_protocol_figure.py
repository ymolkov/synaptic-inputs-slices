#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_OUTPUT = PROJECT_ROOT / "publication" / "figures" / "method_protocol_steps.png"

CC_BASENAME = "VgluT2-I-Cell2-C"
VC_BASENAME = "VgluT2-I-Cell2-V"
CC_EXCERPT_SECONDS = 220.0
VC_EXCERPT_SECONDS = 180.0


def _load_recording(basename: str) -> np.ndarray:
    path = DATA_DIR / basename
    return np.loadtxt(path)


def _median_dt(t: np.ndarray) -> float:
    diffs = np.diff(t)
    diffs = diffs[diffs > 0]
    return float(np.median(diffs)) if len(diffs) else 1e-3


def _coarse_median_trace(t: np.ndarray, x: np.ndarray, window_sec: float) -> tuple[np.ndarray, np.ndarray]:
    dt = _median_dt(t)
    window_pts = max(1, int(round(window_sec / dt)))
    n = (len(x) // window_pts) * window_pts
    if n == 0:
        return t - t[0], x
    x_blocks = x[:n].reshape(-1, window_pts)
    t_blocks = t[:n].reshape(-1, window_pts)
    return np.median(t_blocks, axis=1) - t[0], np.median(x_blocks, axis=1)


def _rolling_median(x: np.ndarray, window_pts: int) -> np.ndarray:
    window_pts = max(1, int(window_pts))
    if window_pts % 2 == 0:
        window_pts += 1
    if window_pts <= 1 or len(x) < window_pts:
        return x.copy()

    pad = window_pts // 2
    padded = np.pad(x, (pad, pad), mode="edge")
    windows = sliding_window_view(padded, window_pts)
    return np.median(windows, axis=-1)


def _merged_step_times(
    t: np.ndarray,
    command: np.ndarray,
    window_sec: float = 0.5,
    change_threshold: float = 0.05,
    merge_gap_sec: float = 1.0,
) -> np.ndarray:
    t_coarse, command_coarse = _coarse_median_trace(t, command, window_sec=window_sec)
    change_idx = np.where(np.abs(np.diff(command_coarse)) > change_threshold)[0]
    if len(change_idx) == 0:
        return np.empty(0)

    events = t_coarse[np.clip(change_idx + 1, 0, len(t_coarse) - 1)]
    merged = [float(events[0])]
    for event in events[1:]:
        event = float(event)
        if event - merged[-1] <= merge_gap_sec:
            merged[-1] = 0.5 * (merged[-1] + event)
        else:
            merged.append(event)
    return np.asarray(merged, dtype=float)


def _select_step_rich_start(
    t: np.ndarray,
    step_times: np.ndarray,
    duration_sec: float,
) -> float:
    total_duration = float(t[-1] - t[0])
    if total_duration <= duration_sec:
        return 0.0
    if len(step_times) == 0:
        return 0.5 * (total_duration - duration_sec)

    candidate_starts = [0.0, total_duration - duration_sec]
    for event in step_times:
        candidate_starts.extend(
            [
                event - 0.75 * duration_sec,
                event - 0.50 * duration_sec,
                event - 0.25 * duration_sec,
            ]
        )
    candidate_starts = np.clip(candidate_starts, 0.0, total_duration - duration_sec)
    candidate_starts = np.unique(np.round(candidate_starts, 3))

    best_start = 0.0
    best_score = (-1, -1.0, -np.inf)
    target_center = 0.5 * total_duration
    for start in candidate_starts:
        stop = start + duration_sec
        mask = (step_times >= start) & (step_times <= stop)
        count = int(np.sum(mask))
        span = float(step_times[mask][-1] - step_times[mask][0]) if count >= 2 else 0.0
        center_penalty = abs((start + stop) * 0.5 - target_center)
        score = (count, span, -center_penalty)
        if score > best_score:
            best_score = score
            best_start = float(start)
    return best_start


def _excerpt(
    arr: np.ndarray,
    start_sec: float,
    duration_sec: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    t, ch0, ch1, ref = arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3]
    abs_start = t[0] + start_sec
    abs_stop = abs_start + duration_sec
    mask = (t >= abs_start) & (t < abs_stop)
    t = t[mask]
    return t - t[0], ch0[mask], ch1[mask], ref[mask]


def _populate_excerpt_panel(
    ax_response,
    ax_ref,
    arr: np.ndarray,
    command: np.ndarray,
    response: np.ndarray,
    response_label: str,
    response_title: str,
    duration_sec: float,
):
    t_abs = arr[:, 0]
    step_times = _merged_step_times(t_abs, command)
    start_sec = _select_step_rich_start(t_abs, step_times, duration_sec)
    t, _, _, ref = _excerpt(arr, start_sec, duration_sec)
    excerpt_mask = (t_abs >= t_abs[0] + start_sec) & (t_abs < t_abs[0] + start_sec + duration_sec)
    response_excerpt = response[excerpt_mask]
    step_times_excerpt = step_times[(step_times >= start_sec) & (step_times <= start_sec + duration_sec)] - start_sec

    dt = _median_dt(t)
    response_smooth = _rolling_median(response_excerpt, int(round(0.02 / dt)))
    ref_smooth = _rolling_median(ref, int(round(0.10 / dt)))

    for ax in (ax_response, ax_ref):
        for event in step_times_excerpt:
            ax.axvline(event, color="0.85", linewidth=0.9, linestyle="--", zorder=0)
        ax.grid(alpha=0.18)

    ax_response.plot(t, response_smooth, color="#1f77b4", linewidth=1.0)
    ax_response.set_title(response_title)
    ax_response.set_ylabel(response_label, color="#1f77b4")
    ax_response.tick_params(axis="y", colors="#1f77b4")
    ax_response.spines["right"].set_visible(False)
    ax_response.spines["top"].set_visible(False)
    ax_response.tick_params(axis="x", labelbottom=False)

    ax_ref.plot(t, ref_smooth, color="#2ca02c", linewidth=1.2)
    ax_ref.set_ylabel(r"$\int$HNA", color="#2ca02c")
    ax_ref.tick_params(axis="y", colors="#2ca02c")
    ax_ref.spines["right"].set_visible(False)
    ax_ref.spines["top"].set_visible(False)
    ax_ref.set_xlabel("Time (s)")

    return start_sec


def build_figure(output_path: Path) -> None:
    cc = _load_recording(CC_BASENAME)
    vc = _load_recording(VC_BASENAME)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.labelsize": 13,
            "axes.titlesize": 14,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
        }
    )

    fig = plt.figure(figsize=(13.5, 8.35))
    grid = fig.add_gridspec(3, 2, height_ratios=[3.0, 3.0, 1.0], hspace=0.28, wspace=0.16)

    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[1, 0])
    ax_d = fig.add_subplot(grid[1, 1])
    ax_c_ref = fig.add_subplot(grid[2, 0], sharex=ax_c)
    ax_d_ref = fig.add_subplot(grid[2, 1], sharex=ax_d)

    t_cmd, i_cmd = _coarse_median_trace(cc[:, 0], cc[:, 1], window_sec=0.5)
    ax_a.plot(t_cmd, i_cmd, color="black", linewidth=1.5)
    ax_a.set_title("Current-clamp command (full recording)")
    ax_a.set_xlabel("")
    ax_a.set_ylabel("Injected current (nA)")
    ax_a.grid(alpha=0.2)
    ax_a.spines["right"].set_visible(False)
    ax_a.spines["top"].set_visible(False)

    t_cmd, v_cmd = _coarse_median_trace(vc[:, 0], vc[:, 2], window_sec=0.5)
    ax_b.plot(t_cmd, v_cmd, color="black", linewidth=1.5)
    ax_b.set_title("Voltage-clamp command (full recording)")
    ax_b.set_xlabel("")
    ax_b.set_ylabel("Command voltage (mV)")
    ax_b.grid(alpha=0.2)
    ax_b.spines["right"].set_visible(False)
    ax_b.spines["top"].set_visible(False)

    cc_start = _populate_excerpt_panel(
        ax_response=ax_c,
        ax_ref=ax_c_ref,
        arr=cc,
        command=cc[:, 1],
        response=cc[:, 2],
        response_label=r"$V_m$ (mV)",
        response_title=f"Current-clamp response (step-rich {int(CC_EXCERPT_SECONDS)} s excerpt)",
        duration_sec=CC_EXCERPT_SECONDS,
    )
    vc_start = _populate_excerpt_panel(
        ax_response=ax_d,
        ax_ref=ax_d_ref,
        arr=vc,
        command=vc[:, 2],
        response=vc[:, 1],
        response_label="Holding current (nA)",
        response_title=f"Voltage-clamp response (step-rich {int(VC_EXCERPT_SECONDS)} s excerpt)",
        duration_sec=VC_EXCERPT_SECONDS,
    )

    def _highlight_interval(ax, start, duration, label):
        stop = start + duration
        ax.axvspan(start, stop, color="#1f77b4", alpha=0.10, zorder=0)
        ax.axvline(start, color="#1f77b4", linewidth=1.1, linestyle="--", alpha=0.85, zorder=1)
        ax.axvline(stop, color="#1f77b4", linewidth=1.1, linestyle="--", alpha=0.85, zorder=1)
        y0, y1 = ax.get_ylim()
        y = y1 - 0.06 * (y1 - y0)
        ax.text(
            start + 0.5 * duration,
            y,
            label,
            color="#1f77b4",
            fontsize=10,
            ha="center",
            va="top",
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=1.5),
        )

    _highlight_interval(ax_a, cc_start, CC_EXCERPT_SECONDS, "C excerpt")
    _highlight_interval(ax_b, vc_start, VC_EXCERPT_SECONDS, "D excerpt")

    panel_axes = (
        ("A", ax_a),
        ("B", ax_b),
        ("C", ax_c),
        ("D", ax_d),
    )
    for label, ax in panel_axes:
        ax.text(-0.12, 1.05, label, transform=ax.transAxes, fontsize=16, fontweight="bold")
    fig.subplots_adjust(left=0.08, right=0.98, top=0.95, bottom=0.08)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the standalone methods protocol figure.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output image path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()
    build_figure(args.output.resolve())


if __name__ == "__main__":
    main()
