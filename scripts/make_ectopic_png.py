#!/usr/bin/env python3

import argparse
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUTPUT = os.path.join(
    PROJECT_ROOT, "publication", "figures", "supp_figure3_ectopic.png"
)


def load_episode_with_interpolated_spikes(filepath, t_start, t_end, threshold):
    """Load data, reconstruct a 1 kHz timebase, and insert interpolated spike peaks."""
    raw_rows = []
    if not os.path.exists(filepath):
        return []

    with open(filepath, "r") as f:
        started = False
        t_base = 0.0
        count = 0
        for line in f:
            parts = line.split()
            if len(parts) < 4:
                continue
            try:
                t_val = float(parts[0])
            except ValueError:
                continue

            if not started:
                if t_val < t_start - 0.1:
                    continue
                t_base = t_val
                started = True

            t = t_base + count * 0.001
            count += 1
            if t_start - 0.005 <= t <= t_end + 0.005:
                raw_rows.append([t, float(parts[2]), float(parts[3])])
            elif t > t_end + 0.005:
                break

    if not raw_rows:
        return []

    processed_data = []
    dt = 0.001
    for i in range(1, len(raw_rows) - 1):
        t0, v0, r0 = raw_rows[i - 1]
        t1, v1, r1 = raw_rows[i]
        t2, v2, r2 = raw_rows[i + 1]

        if t_start <= t1 <= t_end:
            processed_data.append([t1, v1, r1])

        if v1 > threshold and v1 > v0 and v1 >= v2:
            c = v1
            b = (v2 - v0) / 2.0
            a = (v0 + v2) / 2.0 - v1

            if a < 0:
                x_max = -b / (2.0 * a)
                if abs(x_max) < 1.0:
                    v_max = c - (b * b) / (4.0 * a)
                    t_max = t1 + x_max * dt
                    r_max = r1 + x_max * (r2 - r1 if x_max > 0 else r1 - r0)

                    if t_start <= t_max <= t_end:
                        if t_max > t1:
                            processed_data.append([t_max, v_max, r_max])
                        else:
                            processed_data.insert(-1, [t_max, v_max, r_max])

    return processed_data


def moving_average(x, window_pts):
    x = np.asarray(x, dtype=float)
    if len(x) == 0:
        return x
    w = max(1, int(window_pts))
    if w % 2 == 0:
        w += 1
    if w == 1:
        return x.copy()
    pad = w // 2
    x_pad = np.pad(x, (pad, pad), mode="edge")
    kernel = np.ones(w, dtype=float) / float(w)
    return np.convolve(x_pad, kernel, mode="valid")


def generate_png(episodes, output_path):
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.labelsize": 16,
            "xtick.labelsize": 12,
            "ytick.labelsize": 12,
        }
    )

    fig, axes = plt.subplots(
        len(episodes),
        1,
        figsize=(12, 10),
        sharex=True,
        gridspec_kw={"hspace": 0.18},
    )
    axes = np.atleast_1d(axes)
    fig.patch.set_facecolor("white")

    for idx, (name, path, t_start, t_end, threshold) in enumerate(episodes):
        ax = axes[idx]
        data = load_episode_with_interpolated_spikes(path, t_start, t_end, threshold)
        if not data:
            ax.text(0.5, 0.5, "Data unavailable", ha="center", va="center")
            ax.set_axis_off()
            continue

        arr = np.asarray(data, dtype=float)
        ts = arr[:, 0]
        vms = arr[:, 1]
        refs = arr[:, 2]

        t_rel = ts - ts[0]
        vm_min = float(np.min(vms))
        vm_max = float(np.max(vms))
        ref_max = vm_min - 5.0
        ref_min = ref_max - 25.0

        ref_smooth = moving_average(refs, 10)
        ref_span = float(np.max(ref_smooth) - np.min(ref_smooth))
        if ref_span <= 1e-12:
            ref_mapped = np.full_like(ref_smooth, ref_min)
        else:
            ref_mapped = (
                (ref_smooth - np.min(ref_smooth)) / ref_span * (ref_max - ref_min)
                + ref_min
            )

        ax.plot(t_rel, vms, color="#1f77b4", lw=1.0, alpha=0.95)
        ax.plot(t_rel, ref_mapped, color="#2ca02c", lw=2.3, alpha=0.85)
        ax.axhline(0, color="gray", linestyle="--", lw=0.5, alpha=0.5)

        ax.text(
            0.015,
            0.94,
            name,
            transform=ax.transAxes,
            fontsize=18,
            fontweight="bold",
            va="top",
            ha="left",
            bbox=dict(facecolor="white", alpha=0.82, edgecolor="none", pad=0.35),
        )

        ytick_max = 20 if vm_max < 30 else 40
        ax.set_yticks(np.arange(-60, ytick_max + 1, 20))
        ax.set_ylim(ref_min - 5, 40)
        ax.set_xlim(0, 25)
        ax.grid(axis="y", alpha=0.18)
        ax.set_facecolor("white")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(axis="y", labelsize=12)

        if idx < len(episodes) - 1:
            ax.spines["bottom"].set_visible(False)
            ax.tick_params(axis="x", bottom=False, labelbottom=False)
        else:
            ax.set_xticks(np.arange(0, 26, 5))
            ax.set_xlabel("Time (s)")
            ax.tick_params(axis="x", labelsize=12)

    fig.subplots_adjust(left=0.08, right=0.98, top=0.98, bottom=0.07)
    fig.savefig(output_path, dpi=300, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Generate Supplemental Figure 3 as PNG.")
    parser.add_argument("--out", default=DEFAULT_OUTPUT, help="Output PNG path.")
    args = parser.parse_args()

    episodes = [
        (
            "VGAT-I Cell 9 (~3394s)",
            os.path.join(PROJECT_ROOT, "data", "VGAT-I-Cell9-C"),
            3381.4,
            3406.4,
            -45.0,
        ),
        (
            "VgluT2-I Cell 4 (~479s)",
            os.path.join(PROJECT_ROOT, "data", "VgluT2-I-Cell4-C"),
            466.7,
            491.7,
            -35.0,
        ),
        (
            "VgluT2-I Cell 10-C-1 (~2963s)",
            os.path.join(PROJECT_ROOT, "data", "VgluT2-I-Cell10-C-1"),
            2950.0,
            2975.0,
            -40.0,
        ),
    ]

    generate_png(episodes, args.out)
    print(f"Done! Saved to {args.out}")


if __name__ == "__main__":
    main()
