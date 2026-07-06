#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch, PathPatch, Polygon
from matplotlib.path import Path as MplPath

from conductance_summary import load_all_group_summaries
from figure_style import ERROR_COLOR, apply_style, save_pdf

apply_style()

# Keep this diagram small and self-contained so it can be inserted at its
# native size without TeX rescaling.
CIRCUIT_FIGURE_WIDTH_IN = 2.17
NODE_LABEL_SIZE = 7.0

POS = {
    "VgluT2_I": np.array((0.0, 2.0)),
    "VgluT2_E": np.array((2.0, 2.0)),
    "VGAT_I": np.array((0.0, 0.0)),
    "VGAT_E": np.array((2.0, 0.0)),
}

LABELS = {
    "VgluT2_I": "VgluT2\n(pre-)I",
    "VgluT2_E": "VgluT2\nE",
    "VGAT_I": "VGAT\n(pre-)I",
    "VGAT_E": "VGAT\nE",
}

GROUP_TO_NODE = {
    "VgluT2-I": "VgluT2_I",
    "VgluT2-E": "VgluT2_E",
    "VGAT-I": "VGAT_I",
    "VGAT-E": "VGAT_E",
}

EXCITATORY_TARGET_GROUPS = ("VgluT2-I", "VgluT2-E", "VGAT-I", "VGAT-E")
VGAT_I_TARGET_GROUPS = ("VgluT2-I", "VgluT2-E", "VGAT-E", "VGAT-I")
VGAT_E_TARGET_GROUPS = ("VgluT2-I", "VGAT-I", "VGAT-E", "VgluT2-E")

NODE_COLORS = {
    "VgluT2_I": "#F4CCCC",
    "VgluT2_E": "#F4CCCC",
    "VGAT_I": "#C9D9F4",
    "VGAT_E": "#C9D9F4",
}

NODE_EDGE_COLORS = {
    "VgluT2_I": "#F06B6B",
    "VgluT2_E": "#F06B6B",
    "VGAT_I": "#4A82E5",
    "VGAT_E": "#4A82E5",
}

EDGE_COLORS = {
    "exc": "#F06B6B",
    "inh": "#4A82E5",
}

NODE_RADIUS = 0.44
TERMINAL_RADIUS = 0.065
MIN_VISIBLE_WEIGHT = 0.05
EDGE_WIDTH_SCALE = 0.85
EXCITATORY: list[tuple[str, str, float]] = []
INHIBITORY: list[tuple[str, str, float]] = []
MAX_WEIGHT = 1.0
VISIBLE_WEIGHTS: dict[tuple[str, str], float] = {}

# Manual geometry keeps the diagram visually close to the reference instead of using
# generic center-to-center routing.
EXCITATORY_GEOMETRY = {
    ("VgluT2_I", "VgluT2_I"): {"start": 126, "end": 28, "rad": 1.35},
    ("VgluT2_I", "VgluT2_E"): {"axis": "h", "offset": 0.016, "rad": 0.0},
    ("VgluT2_I", "VGAT_I"): {"axis": "v", "offset": -0.020, "rad": 0.0},
    ("VgluT2_I", "VGAT_E"): {"start": -18, "end": 162, "rad": 0.0},
}

INHIBITORY_GEOMETRY = {
    ("VGAT_I", "VgluT2_I"): {"axis": "v", "offset": -0.155, "rad": 0.0},
    ("VGAT_I", "VgluT2_E"): {"start": 34, "end": -146, "rad": 0.0},
    ("VGAT_I", "VGAT_E"): {"axis": "h", "offset": -0.225, "rad": 0.0},
    ("VGAT_I", "VGAT_I"): {"start": 238, "end": 152, "rad": -1.20},
    ("VGAT_E", "VgluT2_I"): {"start": 146, "end": -34, "rad": 0.0},
    ("VGAT_E", "VGAT_I"): {"axis": "h", "offset": 0.045, "rad": 0.0},
    ("VGAT_E", "VGAT_E"): {"start": -28, "end": -118, "rad": -1.05},
    ("VGAT_E", "VgluT2_E"): {"axis": "v", "offset": 0.105, "rad": 0.0},
}

SELF_LOOP_GEOMETRY = {
    ("exc", "VgluT2_I"): {"center_angle": 135.0, "loop_radius": 0.26, "overlap": 0.10, "sweep_sign": 1},
    ("inh", "VGAT_I"): {"center_angle": 225.0, "loop_radius": 0.24, "overlap": 0.09, "sweep_sign": -1},
    ("inh", "VGAT_E"): {"center_angle": 315.0, "loop_radius": 0.24, "overlap": 0.09, "sweep_sign": 1},
}


def configure_connection_data(results_dir: Path) -> None:
    global EXCITATORY, INHIBITORY, MAX_WEIGHT, VISIBLE_WEIGHTS

    summaries = load_all_group_summaries(results_dir)

    EXCITATORY = [
        (
            GROUP_TO_NODE["VgluT2-I"],
            GROUP_TO_NODE[group],
            float(summaries[group]["inspiration"]["exc"]),
        )
        for group in EXCITATORY_TARGET_GROUPS
    ]

    INHIBITORY = [
        (
            GROUP_TO_NODE["VGAT-I"],
            GROUP_TO_NODE[group],
            float(summaries[group]["inspiration"]["inh"]),
        )
        for group in VGAT_I_TARGET_GROUPS
    ] + [
        (
            GROUP_TO_NODE["VGAT-E"],
            GROUP_TO_NODE[group],
            float(summaries[group]["expiration"]["inh"]),
        )
        for group in VGAT_E_TARGET_GROUPS
    ]

    VISIBLE_WEIGHTS = {
        (src, tgt): weight
        for src, tgt, weight in EXCITATORY + INHIBITORY
        if weight >= MIN_VISIBLE_WEIGHT
    }
    if not VISIBLE_WEIGHTS:
        raise ValueError(f"No visible connections found in {results_dir}")

    MAX_WEIGHT = max(VISIBLE_WEIGHTS.values())


def thickness(weight: float) -> float:
    return EDGE_WIDTH_SCALE * (1.7 + 5.7 * (weight / MAX_WEIGHT))


def inhibitory_terminal_radius(width: float) -> float:
    return 0.11 * (width / thickness(MAX_WEIGHT))


def arrowhead_dims(width: float) -> tuple[float, float]:
    head_length = 0.05 + 0.02 * width
    head_half_width = 0.018 + 0.013 * width
    return head_length, head_half_width


def point_on_node(node: str, angle_deg: float, extra: float = 0.0) -> np.ndarray:
    angle_rad = np.deg2rad(angle_deg)
    direction = np.array((np.cos(angle_rad), np.sin(angle_rad)))
    return POS[node] + direction * (NODE_RADIUS + extra)


def polar_vector(angle_deg: float) -> np.ndarray:
    angle_rad = np.deg2rad(angle_deg)
    return np.array((np.cos(angle_rad), np.sin(angle_rad)))


def points_to_data(ax: plt.Axes, points: float) -> float:
    pixels = points * ax.figure.dpi / 72.0
    origin = ax.transData.transform((0.0, 0.0))
    shifted = origin + np.array((pixels, 0.0))
    data_shifted = ax.transData.inverted().transform(shifted)
    return abs(data_shifted[0])


def inhibitory_terminal_center(node: str, angle_deg: float, width: float) -> np.ndarray:
    return point_on_node(node, angle_deg, extra=inhibitory_terminal_radius(width))


def unit_vector(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if norm == 0:
        return np.array((1.0, 0.0))
    return vec / norm


def add_arrowhead(
    ax: plt.Axes, tip: np.ndarray, direction: np.ndarray, width: float, color: str, zorder: float
) -> None:
    direction = unit_vector(direction)
    normal = np.array((-direction[1], direction[0]))
    head_length, head_half_width = arrowhead_dims(width)
    base = tip - direction * head_length
    head = Polygon(
        [tip, base + normal * head_half_width, base - normal * head_half_width],
        closed=True,
        facecolor=color,
        edgecolor="none",
        zorder=zorder,
        clip_on=False,
    )
    ax.add_patch(head)


def arrowhead_vertices(
    tip: np.ndarray, direction: np.ndarray, width: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    direction = unit_vector(direction)
    normal = np.array((-direction[1], direction[0]))
    head_length, head_half_width = arrowhead_dims(width)
    base_mid = tip - direction * head_length
    base_left = base_mid + normal * head_half_width
    base_right = base_mid - normal * head_half_width
    return tip, base_mid, base_left, base_right


def circular_self_loop_points(node: str, kind: str, n_points: int = 140) -> np.ndarray:
    cfg = SELF_LOOP_GEOMETRY[(kind, node)]
    outward = polar_vector(cfg["center_angle"])
    loop_radius = cfg["loop_radius"]
    center_distance = NODE_RADIUS + loop_radius - cfg["overlap"]
    loop_center = POS[node] + outward * center_distance

    cos_alpha = (center_distance**2 + loop_radius**2 - NODE_RADIUS**2) / (2.0 * center_distance * loop_radius)
    alpha = np.arccos(np.clip(cos_alpha, -1.0, 1.0))
    theta_to_node = np.deg2rad(cfg["center_angle"] + 180.0)

    if cfg["sweep_sign"] > 0:
        start_angle = theta_to_node - alpha
        end_angle = theta_to_node + alpha - 2.0 * np.pi
    else:
        start_angle = theta_to_node + alpha
        end_angle = theta_to_node - alpha + 2.0 * np.pi

    angles = np.linspace(start_angle, end_angle, n_points)
    points = np.column_stack(
        [loop_center[0] + loop_radius * np.cos(angles), loop_center[1] + loop_radius * np.sin(angles)]
    )
    return points


def self_loop_center(node: str, kind: str) -> np.ndarray:
    cfg = SELF_LOOP_GEOMETRY[(kind, node)]
    outward = polar_vector(cfg["center_angle"])
    center_distance = NODE_RADIUS + cfg["loop_radius"] - cfg["overlap"]
    return POS[node] + outward * center_distance


def self_loop_tangent_at_point(
    point: np.ndarray, node: str, kind: str, path_direction: np.ndarray
) -> np.ndarray:
    loop_center = self_loop_center(node, kind)
    radius_dir = unit_vector(point - loop_center)
    tangent = np.array((-radius_dir[1], radius_dir[0]))
    if np.dot(tangent, unit_vector(path_direction)) < 0:
        tangent = -tangent
    return tangent


def self_loop_arrow_geometry(
    points: np.ndarray, node: str, kind: str, width: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    head_length, _ = arrowhead_dims(width)
    seg = np.linalg.norm(np.diff(points, axis=0), axis=1)
    total = float(np.sum(seg))
    min_retreat = max(head_length * 0.2, 0.01)
    max_retreat = min(total - 1e-6, max(head_length * 3.2, 0.18))

    best = None
    for retreat in np.linspace(min_retreat, max_retreat, 80):
        base_mid, path_direction = path_point_and_direction_from_end(points, retreat)
        head_direction = self_loop_tangent_at_point(base_mid, node, kind, path_direction)
        head_tip = base_mid + head_direction * head_length
        vertices = np.vstack(arrowhead_vertices(head_tip, head_direction, width))
        clearance = np.min(np.linalg.norm(vertices - POS[node], axis=1)) - NODE_RADIUS
        best = (base_mid, head_tip, head_direction, float(retreat))
        if clearance >= 0.008:
            break

    return best


def path_point_and_direction_from_end(
    points: np.ndarray, retreat: float
) -> tuple[np.ndarray, np.ndarray]:
    if len(points) < 2:
        return points[-1], np.array((1.0, 0.0))

    seg = np.linalg.norm(np.diff(points, axis=0), axis=1)
    total = np.sum(seg)
    if retreat <= 0:
        return points[-1], unit_vector(points[-1] - points[-2])
    if retreat >= total:
        return points[0], unit_vector(points[1] - points[0])

    target = total - retreat
    walked = 0.0
    for i, seg_len in enumerate(seg, start=1):
        if walked + seg_len < target:
            walked += seg_len
            continue
        remain = target - walked
        frac = remain / seg_len if seg_len > 0 else 0.0
        point = points[i - 1] + frac * (points[i] - points[i - 1])
        direction = unit_vector(points[i] - points[i - 1])
        return point, direction

    return points[-1], unit_vector(points[-1] - points[-2])


def path_prefix_near_end_at_distance(
    points: np.ndarray, center: np.ndarray, target_distance: float
) -> tuple[np.ndarray, np.ndarray]:
    distances = np.linalg.norm(points - center, axis=1)
    for i in range(len(points) - 2, -1, -1):
        d0 = distances[i]
        d1 = distances[i + 1]
        crosses = (d0 >= target_distance >= d1) or (d0 <= target_distance <= d1)
        if not crosses:
            continue
        delta = d1 - d0
        frac = 0.0 if abs(delta) < 1e-12 else (target_distance - d0) / delta
        point = points[i] + frac * (points[i + 1] - points[i])
        prefix = np.vstack([points[: i + 1], point])
        return prefix, point

    return points, points[-1]


def trim_path_end(points: np.ndarray, trim_length: float) -> np.ndarray:
    if trim_length <= 0 or len(points) < 2:
        return points

    seg = np.linalg.norm(np.diff(points, axis=0), axis=1)
    total = np.sum(seg)
    if trim_length >= total:
        return points[:1]

    target = total - trim_length
    walked = 0.0
    kept = [points[0]]
    for i, seg_len in enumerate(seg, start=1):
        if walked + seg_len < target:
            kept.append(points[i])
            walked += seg_len
            continue
        remain = target - walked
        frac = remain / seg_len if seg_len > 0 else 0.0
        interp = points[i - 1] + frac * (points[i] - points[i - 1])
        kept.append(interp)
        break
    return np.array(kept)


def add_path_line(ax: plt.Axes, points: np.ndarray, width: float, color: str, zorder: float) -> None:
    codes = [MplPath.MOVETO] + [MplPath.LINETO] * (len(points) - 1)
    path = MplPath(points, codes)
    patch = PathPatch(
        path,
        facecolor="none",
        edgecolor=color,
        linewidth=width,
        capstyle="round",
        joinstyle="round",
        zorder=zorder,
        clip_on=False,
    )
    ax.add_patch(patch)


def canonical_pair(src: str, tgt: str) -> tuple[str, str]:
    src_pos = POS[src]
    tgt_pos = POS[tgt]
    delta = tgt_pos - src_pos
    if abs(delta[0]) >= abs(delta[1]):
        return (src, tgt) if src_pos[0] <= tgt_pos[0] else (tgt, src)
    return (src, tgt) if src_pos[1] >= tgt_pos[1] else (tgt, src)


def outside_perpendicular(src: str, tgt: str) -> np.ndarray:
    canonical_src, canonical_tgt = canonical_pair(src, tgt)
    canonical_u = unit_vector(POS[canonical_tgt] - POS[canonical_src])
    canonical_perp = np.array((-canonical_u[1], canonical_u[0]))
    midpoint = 0.5 * (POS[canonical_src] + POS[canonical_tgt])
    center = np.mean(np.stack(list(POS.values())), axis=0)
    outward_sign = np.sign(np.dot(midpoint - center, canonical_perp))
    if outward_sign == 0:
        outward_sign = 1.0
    return outward_sign * canonical_perp


def reciprocal_offset_vector(
    ax: plt.Axes, src: str, tgt: str, width: float, reverse_width: float, gap_points: float = 6.0
) -> np.ndarray:
    width_data = points_to_data(ax, width)
    reverse_width_data = points_to_data(ax, reverse_width)
    gap_data = points_to_data(ax, gap_points)
    offset_mag = (width_data + reverse_width_data) / 4.0 + gap_data / 2.0
    outside = outside_perpendicular(src, tgt)
    if width > reverse_width:
        return offset_mag * outside
    if width < reverse_width:
        return -offset_mag * outside
    canonical_src, canonical_tgt = canonical_pair(src, tgt)
    return offset_mag * outside if (src, tgt) == (canonical_src, canonical_tgt) else -offset_mag * outside


def parallel_edge_points(
    src: str, tgt: str, delta: np.ndarray, start_pad: float, end_pad: float
) -> tuple[np.ndarray, np.ndarray]:
    src_center = POS[src]
    tgt_center = POS[tgt]
    direction = unit_vector(tgt_center - src_center)
    delta_mag = np.linalg.norm(delta)
    start_span = np.sqrt(max((NODE_RADIUS + start_pad) ** 2 - delta_mag**2, 0.0))
    end_span = np.sqrt(max((NODE_RADIUS + end_pad) ** 2 - delta_mag**2, 0.0))
    start = src_center + delta + direction * start_span
    end = tgt_center + delta - direction * end_span
    return start, end


def centerline_edge_points(
    src: str, tgt: str, start_pad: float, end_pad: float
) -> tuple[np.ndarray, np.ndarray]:
    return parallel_edge_points(
        src, tgt, np.array((0.0, 0.0)), start_pad=start_pad, end_pad=end_pad
    )


def add_excitatory(ax: plt.Axes, src: str, tgt: str, weight: float) -> None:
    if weight < MIN_VISIBLE_WEIGHT:
        return

    if src == tgt:
        width = thickness(weight)
        points = circular_self_loop_points(src, "exc")
        shaft_end, head_tip, head_direction, shaft_trim = self_loop_arrow_geometry(
            points, src, "exc", width
        )
        shaft_points = trim_path_end(points, shaft_trim)
        add_path_line(ax, shaft_points, width, EDGE_COLORS["exc"], zorder=1)
        add_arrowhead(ax, head_tip, head_direction, width, EDGE_COLORS["exc"], zorder=4.2)
        return

    geom = EXCITATORY_GEOMETRY[(src, tgt)]
    width = thickness(weight)
    reverse_weight = VISIBLE_WEIGHTS.get((tgt, src))
    if src != tgt and reverse_weight is not None:
        delta = reciprocal_offset_vector(ax, src, tgt, width, thickness(reverse_weight))
        start, end = parallel_edge_points(src, tgt, delta, start_pad=0.015, end_pad=0.0)
    else:
        start, end = centerline_edge_points(src, tgt, start_pad=0.015, end_pad=0.0)
    head_length, _ = arrowhead_dims(width)
    shaft_end = end - unit_vector(end - start) * (head_length * 0.82)

    shaft = FancyArrowPatch(
        start,
        shaft_end,
        connectionstyle=f"arc3,rad={geom['rad']}",
        arrowstyle="-",
        linewidth=width,
        color=EDGE_COLORS["exc"],
        capstyle="round",
        joinstyle="round",
        shrinkA=0,
        shrinkB=0,
        clip_on=False,
        zorder=1,
    )
    ax.add_patch(shaft)
    add_arrowhead(ax, end, end - start, width, EDGE_COLORS["exc"], zorder=4.2)


def add_inhibitory(ax: plt.Axes, src: str, tgt: str, weight: float) -> None:
    if weight < MIN_VISIBLE_WEIGHT:
        return

    geom = INHIBITORY_GEOMETRY[(src, tgt)]
    width = thickness(weight)
    if src == tgt:
        radius = inhibitory_terminal_radius(width)
        points = circular_self_loop_points(src, "inh")
        center_path, end = path_prefix_near_end_at_distance(
            points, POS[src], NODE_RADIUS + radius
        )
        shaft_points = trim_path_end(center_path, radius)
        add_path_line(ax, shaft_points, width, EDGE_COLORS["inh"], zorder=1)
        terminal = Circle(
            end,
            radius,
            facecolor=EDGE_COLORS["inh"],
            edgecolor="none",
            zorder=4,
            clip_on=False,
        )
        ax.add_patch(terminal)
        return

    reverse_weight = VISIBLE_WEIGHTS.get((tgt, src))
    if src != tgt and reverse_weight is not None:
        delta = reciprocal_offset_vector(ax, src, tgt, width, thickness(reverse_weight))
        start, end = parallel_edge_points(
            src, tgt, delta, start_pad=0.015, end_pad=inhibitory_terminal_radius(width)
        )
    else:
        start, end = centerline_edge_points(
            src, tgt, start_pad=0.015, end_pad=inhibitory_terminal_radius(width)
        )

    line = FancyArrowPatch(
        start,
        end,
        connectionstyle=f"arc3,rad={geom['rad']}",
        arrowstyle="-",
        linewidth=width,
        color=EDGE_COLORS["inh"],
        capstyle="round",
        joinstyle="round",
        shrinkA=0,
        shrinkB=0,
        clip_on=False,
        zorder=1,
    )
    ax.add_patch(line)

    terminal = Circle(
        end,
        inhibitory_terminal_radius(width),
        facecolor=EDGE_COLORS["inh"],
        edgecolor="none",
        zorder=4,
        clip_on=False,
    )
    ax.add_patch(terminal)


def draw_nodes(ax: plt.Axes) -> None:
    for node, center in POS.items():
        fill = Circle(
            center,
            NODE_RADIUS,
            facecolor=NODE_COLORS[node],
            edgecolor="none",
            zorder=3,
        )
        rim = Circle(
            center,
            NODE_RADIUS,
            facecolor="none",
            edgecolor=NODE_EDGE_COLORS[node],
            linewidth=1.45,
            zorder=3.1,
        )
        ax.add_patch(fill)
        ax.add_patch(rim)
        ax.text(
            center[0],
            center[1] - 0.05,
            LABELS[node],
            ha="center",
            va="center",
            multialignment="center",
            fontsize=NODE_LABEL_SIZE,
            fontweight="normal",
            color=ERROR_COLOR,
            linespacing=0.88,
            zorder=5,
        )


def make_figure(results_dir: Path) -> tuple[plt.Figure, plt.Axes]:
    configure_connection_data(results_dir)

    fig, ax = plt.subplots(
        figsize=(CIRCUIT_FIGURE_WIDTH_IN, CIRCUIT_FIGURE_WIDTH_IN),
        facecolor="white",
    )
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.01, top=0.99)
    ax.set_facecolor("white")
    ax.set_aspect("equal")
    # Keep just a small pad around the outer loops so the exported PNG is tight.
    ax.set_xlim(-0.75, 2.75)
    ax.set_ylim(-0.75, 2.75)
    ax.axis("off")

    for src, tgt, weight in INHIBITORY:
        add_inhibitory(ax, src, tgt, weight)

    for src, tgt, weight in EXCITATORY:
        add_excitatory(ax, src, tgt, weight)

    draw_nodes(ax)
    return fig, ax


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    default_output = root / "paper" / "figures" / "circuit_weighted.pdf"
    default_results = root / "results"

    parser = argparse.ArgumentParser(
        description="Render a weighted preBotC circuit diagram styled like the reference figure."
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=default_results,
        help=f"Directory containing per-population conductance CSVs (default: {default_results})",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=default_output,
        help=f"Output PDF path (default: {default_output})",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display the figure interactively after saving.",
    )
    args = parser.parse_args()

    fig, _ = make_figure(args.results_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    save_pdf(fig, args.out, facecolor=fig.get_facecolor())

    if args.show:
        plt.show()
    else:
        plt.close(fig)


if __name__ == "__main__":
    main()
