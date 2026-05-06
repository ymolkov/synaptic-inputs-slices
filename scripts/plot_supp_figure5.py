import os
import re
import numpy as np
import matplotlib.pyplot as plt
from figure_style import (
    AXIS_LABEL_SIZE,
    GRID_ALPHA,
    HIGHLIGHT_COLOR,
    REF_COLOR,
    SCALEBAR_SIZE,
    TICK_LABEL_SIZE,
    TITLE_SIZE,
    TRACE_COLOR,
    apply_style,
    save_pdf,
    scaled_figsize,
)
from spike_repair import repair_undersampled_spikes

apply_style()

DISPLAY_XLIM = (-0.25, 1.25)
VC_DISPLAY_YLIM = (0.0, 1.0)
ROW_HEIGHT = 4.0 / 1.5
LABEL_FONT_SIZE = AXIS_LABEL_SIZE
TITLE_FONT_SIZE = TITLE_SIZE
SCALEBAR_FONT_SIZE = SCALEBAR_SIZE
FRAME_PAD_Y_FRAC = 0.012
CC_REF_BASELINE_FRAC = 0.01
CC_REF_AMPLITUDE_FRAC = 0.21
VC_REF_BASELINE_FRAC = CC_REF_BASELINE_FRAC
VC_REF_AMPLITUDE_FRAC = CC_REF_AMPLITUDE_FRAC
VC_BASELINE_FRAC = (-40.0 - (-100.0)) / (40.0 - (-100.0))
VC_PEAK_FRAC = ( 20.0 - (-100.0) ) / (40.0 - (-100.0))
CC_SPIKE_THRESHOLD_MV = -30.0
PRE_I_HIGHLIGHT_ALPHA = 0.15

def format_cc_label(name):
    return re.sub(r'-C(?:-[^-]+)?$', '', name)

def load_window(path, t_start, t_end, chan=2):
    data = []
    with open(path, 'r') as f:
        for i, line in enumerate(f):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    t = float(parts[0])
                    if t < t_start: continue
                    if t > t_end: break
                    sig = float(parts[chan])
                    ref = float(parts[3])
                    data.append((t, sig, ref))
                except ValueError: pass
    return np.array(data)

def median_filter(data, window_size):
    if window_size < 2: return data
    half = window_size // 2
    padded = np.pad(data, (half, half), mode='edge')
    return np.array([np.median(padded[i:i+window_size]) for i in range(len(data))])

def positive_dt(t):
    diffs = np.diff(t)
    diffs = diffs[diffs > 0]
    return np.median(diffs) if len(diffs) else 0.001

def find_sharp_onset_before_peak(t, ref_smooth, peak_idx, search_back_sec=0.6):
    dt = positive_dt(t)
    search_pts = max(3, int(round(search_back_sec / dt)))
    lo = max(0, peak_idx - search_pts)
    if peak_idx - lo < 3:
        return peak_idx

    peak_t = t[peak_idx]
    baseline_mask = (t >= peak_t - 0.35) & (t <= peak_t - 0.12)
    baseline_idx = np.where(baseline_mask & (np.arange(len(t)) < peak_idx))[0]
    if len(baseline_idx) < 3:
        fallback_hi = max(lo + 3, peak_idx - max(2, int(round(0.08 / dt))))
        baseline_idx = np.arange(lo, fallback_hi)
    if len(baseline_idx) < 3:
        return peak_idx

    baseline_vals = ref_smooth[baseline_idx]
    baseline = np.median(baseline_vals)
    noise_sigma = 1.4826 * np.median(np.abs(baseline_vals - baseline))
    peak_value = ref_smooth[peak_idx]
    amplitude = peak_value - baseline
    if amplitude <= max(4 * noise_sigma, 1e-6):
        return peak_idx

    onset_level = baseline + max(4 * noise_sigma, 0.18 * amplitude)
    search_start = max(lo, np.searchsorted(t, peak_t - 0.25, side='left'))
    onset_candidate = None
    sustain_sec = 0.02
    for idx in range(search_start, peak_idx + 1):
        if ref_smooth[idx] < onset_level:
            continue
        window_idx = np.where((t >= t[idx]) & (t <= t[idx] + sustain_sec))[0]
        if len(window_idx) < 2:
            continue
        if np.mean(ref_smooth[window_idx] >= onset_level) >= 0.8:
            onset_candidate = idx
            break
    if onset_candidate is None:
        return peak_idx

    high_level = baseline + 0.80 * amplitude
    high_idx = peak_idx
    for idx in range(onset_candidate, peak_idx + 1):
        if ref_smooth[idx] >= high_level:
            high_idx = idx
            break
    if high_idx - onset_candidate < 2:
        return onset_candidate

    rise_slice = ref_smooth[onset_candidate:high_idx + 1]
    rise_dt = np.diff(t[onset_candidate:high_idx + 1])
    rise_dv = np.diff(rise_slice)
    valid = rise_dt > 0
    if not np.any(valid):
        return onset_candidate

    slope = np.full_like(rise_dv, -np.inf, dtype=float)
    slope[valid] = rise_dv[valid] / rise_dt[valid]
    sharp_rel = int(np.argmax(slope))
    return onset_candidate + sharp_rel + 1

def find_reference_onset_near_time(t, ref, target_time, search_radius=1.5):
    dt = positive_dt(t)
    ref_smooth = median_filter(ref, max(1, int(round(0.1 / dt))))
    idx_target = np.argmin(np.abs(t - target_time))
    radius_pts = max(1, int(round(search_radius / dt)))
    lo = max(0, idx_target - radius_pts)
    hi = min(len(t), idx_target + radius_pts + 1)
    local = ref_smooth[lo:hi]

    local_peak_idx = lo + int(np.argmax(local))
    local_min = np.min(local)
    local_max = np.max(local)
    onset_idx = find_sharp_onset_before_peak(t, ref_smooth, local_peak_idx)

    return ref_smooth, onset_idx, local_min, local_max

def find_reference_onset_candidates(t, ref_smooth):
    low = np.percentile(ref_smooth, 15)
    high = np.percentile(ref_smooth, 99.5)
    threshold = low + 0.20 * (high - low)
    above = ref_smooth >= threshold
    rise_indices = np.where((~above[:-1]) & (above[1:]))[0] + 1

    min_sep_sec = 1.0
    peak_indices = []
    for idx in rise_indices:
        peak_lo = idx
        peak_hi = peak_lo + 1
        while peak_hi < len(ref_smooth) and (t[peak_hi] - t[peak_lo]) <= 0.8:
            peak_hi += 1
        local_peak = peak_lo + int(np.argmax(ref_smooth[peak_lo:peak_hi]))
        if not peak_indices or (t[local_peak] - t[peak_indices[-1]]) > min_sep_sec:
            peak_indices.append(local_peak)
        elif ref_smooth[local_peak] > ref_smooth[peak_indices[-1]]:
            peak_indices[-1] = local_peak

    onset_indices = []
    for peak_idx in peak_indices:
        onset_idx = find_sharp_onset_before_peak(t, ref_smooth, peak_idx)
        if not onset_indices or (t[onset_idx] - t[onset_indices[-1]]) > min_sep_sec:
            onset_indices.append(onset_idx)
        elif t[onset_idx] < t[onset_indices[-1]]:
            onset_indices[-1] = onset_idx

    return onset_indices

def select_display_reference_onsets(t, ref, target_time, xlim, adjacent_side=None):
    ref_smooth, main_idx, _, _ = find_reference_onset_near_time(t, ref, target_time)
    onset_candidates = find_reference_onset_candidates(t, ref_smooth)
    if onset_candidates:
        main_idx = min(onset_candidates, key=lambda idx: abs(t[idx] - target_time))
    main_time = t[main_idx]
    if adjacent_side == "left":
        side_target = xlim[0]
    elif adjacent_side == "right":
        side_target = xlim[1]
    else:
        side_target = xlim[0] if abs(xlim[0]) > abs(xlim[1]) else xlim[1]

    onset_indices = [main_idx]
    if onset_candidates:
        if side_target < 0:
            side_candidates = [idx for idx in onset_candidates if t[idx] < main_time - 1.0]
            if side_candidates:
                onset_indices.append(max(side_candidates, key=lambda idx: t[idx]))
        else:
            side_candidates = [idx for idx in onset_candidates if t[idx] > main_time + 1.0]
            if side_candidates:
                onset_indices.append(min(side_candidates, key=lambda idx: t[idx]))

    if len(onset_indices) == 1:
        adj_time_guess = main_time + side_target
        _, adj_idx, _, _ = find_reference_onset_near_time(t, ref, adj_time_guess, search_radius=2.0)
        if abs(t[adj_idx] - main_time) > 1.0:
            onset_indices.append(adj_idx)

    onset_indices = sorted(set(onset_indices), key=lambda idx: t[idx])
    return ref_smooth, onset_indices

def find_spike_bursts(t, vm, max_isi=0.17):
    spike_indices = np.where((vm[:-1] <= CC_SPIKE_THRESHOLD_MV) & (vm[1:] > CC_SPIKE_THRESHOLD_MV))[0]
    t_spikes = t[spike_indices]
    bursts = []
    if len(t_spikes) == 0:
        return bursts

    current = [t_spikes[0]]
    for k in range(1, len(t_spikes)):
        if t_spikes[k] - t_spikes[k - 1] <= max_isi:
            current.append(t_spikes[k])
        else:
            if len(current) >= 2:
                bursts.append(current)
            current = [t_spikes[k]]
    if len(current) >= 2:
        bursts.append(current)

    return bursts

def find_spike_times(t, vm):
    spike_indices = np.where((vm[:-1] <= CC_SPIKE_THRESHOLD_MV) & (vm[1:] > CC_SPIKE_THRESHOLD_MV))[0]
    return t[spike_indices]

def find_expiratory_burst_for_onset(bursts, ref_onset, max_gap=1.5):
    prior = [burst for burst in bursts if burst[-1] < ref_onset and (ref_onset - burst[-1]) <= max_gap]
    if not prior:
        return None
    return prior[-1]

def find_last_spike_for_episode(spike_times, episode_start, ref_onset):
    within_episode = spike_times[(spike_times >= episode_start) & (spike_times < ref_onset)]
    if len(within_episode) == 0:
        return None
    return within_episode[-1]

def find_spike_repolarization_time(t, vm, spike_time, threshold=CC_SPIKE_THRESHOLD_MV):
    spike_idx = int(np.searchsorted(t, spike_time, side='left'))
    if spike_idx >= len(t):
        return spike_time

    while spike_idx + 1 < len(t) and t[spike_idx] <= spike_time:
        if vm[spike_idx] > threshold and vm[spike_idx + 1] <= threshold:
            return t[spike_idx + 1]
        spike_idx += 1

    search_end = min(len(t), spike_idx + 1 + max(5, int(round(0.02 / positive_dt(t)))))
    for idx in range(spike_idx, search_end - 1):
        if vm[idx] > threshold and vm[idx + 1] <= threshold:
            return t[idx + 1]
    return spike_time

def find_outward_current_onset(t, inj_smooth, ref_onset):
    baseline_mask = (t >= ref_onset - 0.45) & (t <= ref_onset - 0.25)
    baseline_idx = np.where(baseline_mask)[0]
    baseline = inj_smooth[baseline_idx]
    if len(baseline) < 3:
        return None

    search_mask = (t >= ref_onset - 0.25) & (t <= ref_onset + 0.02)
    search_idx = np.where(search_mask)[0]
    if len(search_idx) == 0:
        return None

    base_inj = np.median(baseline)
    std_inj = np.std(baseline) + 1e-9
    idx_peak = search_idx[np.argmax(inj_smooth[search_idx])]
    rise_amp = inj_smooth[idx_peak] - base_inj
    sig_thresh = max(3 * std_inj, 0.03)
    if rise_amp < sig_thresh:
        return None

    onset_thresh = base_inj + max(1.5 * std_inj, 0.03)
    idx_onset = None
    for start_idx in search_idx:
        window_end = t[start_idx] + 0.04
        window_mask = (t >= t[start_idx]) & (t <= window_end)
        window_idx = np.where(window_mask)[0]
        if len(window_idx) < 4:
            continue
        if np.mean(inj_smooth[window_idx] > onset_thresh) >= 0.75:
            idx_onset = start_idx
            break
    if idx_onset is None:
        return None

    lead_window = ref_onset - t[idx_onset]
    short_lead = lead_window < 0.02
    grad = np.diff(inj_smooth)
    grad_mask = (t[:-1] >= ref_onset - 0.08) & (t[:-1] <= ref_onset)
    grad_window = grad[grad_mask]
    max_step = np.max(grad_window) if len(grad_window) > 0 else 0.0
    if short_lead and (std_inj > 0.05 or rise_amp < 0.08 or max_step < 0.02):
        return None

    return idx_onset

def normalize_two_burst_time(values, onset_times):
    onset_start, onset_end = sorted(onset_times)
    span = onset_end - onset_start
    if abs(span) < 1e-9:
        return np.zeros_like(values)
    return (values - onset_start) / span

def median_abs_deviation(values):
    center = np.median(values)
    return np.median(np.abs(values - center))

def vc_display_noise_mad(t, inj, inj_smooth, onset_times):
    _, inj_smooth_disp, _ = map_vc_current_trace(
        inj, inj_smooth, onset_times, t, (0.0, 1.0)
    )
    baseline_segments = []
    for onset in onset_times:
        baseline_mask = (t >= onset - 0.45) & (t <= onset - 0.25)
        if np.count_nonzero(baseline_mask) < 5:
            continue
        t_seg = t[baseline_mask]
        y_seg = inj_smooth_disp[baseline_mask]
        coeffs = np.polyfit(t_seg - t_seg[0], y_seg, 1)
        detrended = y_seg - np.polyval(coeffs, t_seg - t_seg[0])
        baseline_segments.append(detrended)
    if not baseline_segments:
        return 0.0
    baseline = np.concatenate(baseline_segments)
    return 1.4826 * median_abs_deviation(baseline)

def choose_vc_smoothing_seconds(t, inj, onset_times):
    return 0.10

def choose_vc_smoothing_for_target_noise(t, inj, onset_times, target_noise_mad):
    dt = positive_dt(t)
    candidates = np.arange(0.01, 1.501, 0.01)
    best_sec = 0.10
    best_err = np.inf
    for smooth_sec in candidates:
        inj_smooth = median_filter(inj, max(1, int(round(smooth_sec / dt))))
        noise_mad = vc_display_noise_mad(t, inj, inj_smooth, onset_times)
        err = abs(noise_mad - target_noise_mad)
        if err < best_err:
            best_err = err
            best_sec = float(smooth_sec)
    return best_sec

def map_reference_trace(ref_smooth, y_limits, baseline_frac, amplitude_frac):
    y_min, y_max = y_limits
    y_span = y_max - y_min
    ref_min = np.min(ref_smooth)
    ref_max = np.max(ref_smooth)
    ref_norm = (ref_smooth - ref_min) / (ref_max - ref_min + 1e-9)
    baseline = y_min + baseline_frac * y_span
    amplitude = amplitude_frac * y_span
    return baseline + amplitude * ref_norm

def map_vc_current_trace(inj, inj_smooth, onset_times, t, y_limits):
    y_min, y_max = y_limits
    y_span = y_max - y_min

    baseline_samples = []
    peak_samples = []
    for onset in onset_times:
        baseline_mask = (t >= onset - 0.45) & (t <= onset - 0.25)
        peak_mask = (t >= onset - 0.25) & (t <= onset + 0.10)
        if np.any(baseline_mask):
            baseline_samples.append(inj_smooth[baseline_mask])
        if np.any(peak_mask):
            peak_samples.append(inj_smooth[peak_mask])

    if baseline_samples:
        native_baseline = np.median(np.concatenate(baseline_samples))
    else:
        native_baseline = np.median(inj_smooth)
    if peak_samples:
        native_peak = np.max(np.concatenate(peak_samples))
    else:
        native_peak = np.max(inj_smooth)

    native_span = max(native_peak - native_baseline, 1e-9)
    display_baseline = y_min + VC_BASELINE_FRAC * y_span
    display_peak = y_min + VC_PEAK_FRAC * y_span
    display_amplitude = max(display_peak - display_baseline, 1e-9)
    scale = display_amplitude / native_span

    return (
        display_baseline + (inj - native_baseline) * scale,
        display_baseline + (inj_smooth - native_baseline) * scale,
        scale,
    )

def add_time_scalebar(ax, onset_times, seconds=1.0, y_frac=0.07, label_offset_frac=0.04):
    onset_start, onset_end = sorted(onset_times)
    span = max(onset_end - onset_start, 1e-9)
    bar_width = seconds / span
    y_min, y_max = ax.get_ylim()
    y_span = y_max - y_min
    y_bar = y_min + y_frac * y_span
    x_right = DISPLAY_XLIM[1]
    x_left = x_right - bar_width
    min_left = DISPLAY_XLIM[0]
    if x_left < min_left:
        x_left = min_left
        x_right = x_left + bar_width

    ax.plot(
        [x_left, x_right],
        [y_bar, y_bar],
        color='black',
        lw=2.6,
        solid_capstyle='butt',
        clip_on=False,
    )
    ax.text((x_left + x_right) / 2, y_bar - label_offset_frac * y_span, "1 s",
            ha='center', va='top', fontsize=SCALEBAR_FONT_SIZE, clip_on=False)

def y_to_axes_frac(ax, y_value):
    y_min, y_max = ax.get_ylim()
    if abs(y_max - y_min) < 1e-9:
        return 0.0
    return float(np.clip((y_value - y_min) / (y_max - y_min), 0.0, 1.0))

def add_current_scalebar(ax, scale, current_nA=0.2):
    y_min, y_max = ax.get_ylim()
    y_span = y_max - y_min
    bar_height = current_nA * scale
    x_bar = DISPLAY_XLIM[1]
    display_baseline = y_min + VC_BASELINE_FRAC * y_span
    display_peak = y_min + VC_PEAK_FRAC * y_span
    transient_center = 0.5 * (display_baseline + display_peak)
    y_bottom = transient_center - 0.5 * bar_height
    ax.plot(
        [x_bar, x_bar],
        [y_bottom, y_bottom + bar_height],
        color='black',
        lw=2.0,
        solid_capstyle='butt',
        clip_on=False,
    )
    ax.text(
        x_bar - 0.02,
        y_bottom + 0.5 * bar_height,
        f"{current_nA:.1f} nA",
        ha='right',
        va='center',
        fontsize=SCALEBAR_FONT_SIZE,
        clip_on=False,
    )

def style_panel_axes(ax, y_spine_bounds=None, show_left=True):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(show_left)
    if show_left and y_spine_bounds is not None:
        ax.spines["left"].set_bounds(*y_spine_bounds)
    ax.tick_params(axis="x", bottom=False, labelbottom=False)
    if not show_left:
        ax.tick_params(axis="y", left=False, labelleft=False)

def plot_final_grid_tight():
    cell_data = [
        {
            "cc_name": "VGAT-E-Cell7-C",
            "cc_t": 3660.72,
            "cc_xlim": (-7.0, 1.0),
            "cc_side": "left",
            "vc_side": "left",
            "vc_name": "VGAT-E-Cell7-V",
            "vc_t": 2828.12,
            "vc_xlim": (-7.2, 1.0),
            "vc_side": "left",
            "vc_smooth_sec": 0.30,
        },
        {
            "cc_name": "VGAT-E-Cell8-C",
            "cc_t": 850.953,
            "cc_xlim": (-4.5, 1.0),
            "cc_side": "left",
            "vc_name": "VGAT-E-Cell8-V",
            "vc_t": 303.365,
            "vc_xlim": (-10.0, 1.0),
            "vc_side": "left",
            "vc_smooth_sec": 0.08,
        },
        {
            "cc_name": "VgluT2-E-Cell1-C",
            "cc_t": 327.995,
            "cc_xlim": (-6.5, 1.0),
            "cc_side": "left",
            "vc_name": "VgluT2-E-Cell1-V",
            "vc_t": 905.461,
            "vc_xlim": (-7.5, 1.0),
            "vc_side": "left",
            "vc_smooth_sec": 0.08,
        },
        {
            "cc_name": "VGAT-E-Cell2-C",
            "cc_t": 851.312,
            "cc_xlim": (-8.0, 1.0),
            "cc_side": "left",
            "vc_name": "VGAT-E-Cell2-V-2",
            "vc_t": 963.668,
            "vc_xlim": (-6.0, 1.0),
            "vc_side": "left",
            "vc_smooth_sec": 0.08,
        },
    ]

    target_vc_display_noise_mad = None
    first_vc = cell_data[0]
    rec = load_window(
        f"data/{first_vc['vc_name']}",
        first_vc["vc_t"] + first_vc["vc_xlim"][0] - 1.0,
        first_vc["vc_t"] + first_vc["vc_xlim"][1] + 1.0,
        chan=1,
    )
    if len(rec) > 0:
        t, inj, ref = rec[:, 0], rec[:, 1], rec[:, 2]
        dt = positive_dt(t)
        _, onset_indices = select_display_reference_onsets(
            t, ref, first_vc["vc_t"], first_vc["vc_xlim"], first_vc.get("vc_side")
        )
        onset_times = [t[idx] for idx in onset_indices]
        ref_smooth_sec = first_vc.get("vc_smooth_sec", choose_vc_smoothing_seconds(t, inj, onset_times))
        inj_smooth = median_filter(inj, max(1, int(round(ref_smooth_sec / dt))))
        target_vc_display_noise_mad = vc_display_noise_mad(t, inj, inj_smooth, onset_times)
    
    num_cells = len(cell_data)
    fig, axes = plt.subplots(
        num_cells,
        2,
        figsize=scaled_figsize(18, ROW_HEIGHT * num_cells),
        sharex=False,
    )
    
    for row, panel in enumerate(cell_data):
        # --- Column 1: Current Clamp ---
        ax = axes[row, 0]
        cc_name = panel["cc_name"]
        cc_t = panel["cc_t"]
        cc_xlim = panel["cc_xlim"]
        cc_pad = 1.0
        rec = load_window(
            f"data/{cc_name}",
            cc_t + cc_xlim[0] - cc_pad,
            cc_t + cc_xlim[1] + cc_pad,
            chan=2,
        )
        if len(rec) > 0:
            t, vm, ref = rec[:, 0], rec[:, 1], rec[:, 2]
            dt = positive_dt(t)
            vm_repaired, _ = repair_undersampled_spikes(
                vm, dt, peak_threshold=-30.0, base_threshold=-45.0
            )
            ref_smooth, onset_indices = select_display_reference_onsets(
                t, ref, cc_t, cc_xlim, panel.get("cc_side")
            )
            onset_times = [t[idx] for idx in onset_indices]
            bursts = find_spike_bursts(t, vm_repaired)
            spike_times = find_spike_times(t, vm_repaired)
            tx = normalize_two_burst_time(t, onset_times)
            ax.plot(tx, vm_repaired, color=TRACE_COLOR, lw=0.8)
            ax.set_ylim(-100, 40)
            ax.set_yticks(np.arange(-60, 41, 20))
            ref_mapped = map_reference_trace(
                ref_smooth, ax.get_ylim(), CC_REF_BASELINE_FRAC, CC_REF_AMPLITUDE_FRAC
            )
            ax.plot(tx, ref_mapped, color=REF_COLOR, lw=2, alpha=0.7)

            for onset_idx in onset_indices:
                ref_x = normalize_two_burst_time(np.array([t[onset_idx]]), onset_times)[0]
                prior_burst = find_expiratory_burst_for_onset(bursts, t[onset_idx])
                if prior_burst is not None:
                    last_spike_t = find_last_spike_for_episode(
                        spike_times, prior_burst[0], t[onset_idx]
                    )
                    if last_spike_t is None:
                        continue
                    repolarized_t = find_spike_repolarization_time(t, vm_repaired, last_spike_t)
                    t_start_x = normalize_two_burst_time(np.array([repolarized_t]), onset_times)[0]
                    shade_start = max(DISPLAY_XLIM[0], t_start_x)
                    if shade_start < ref_x:
                        ax.axvspan(
                            shade_start,
                            ref_x,
                            color=HIGHLIGHT_COLOR,
                            alpha=PRE_I_HIGHLIGHT_ALPHA,
                        )

            ax.set_ylabel(format_cc_label(cc_name), fontsize=LABEL_FONT_SIZE)
            ax.yaxis.set_label_coords(-0.08, y_to_axes_frac(ax, 0.0))
            if row == 0: ax.set_title("Current Clamp", fontsize=TITLE_FONT_SIZE)
            ax.set_xlim(*DISPLAY_XLIM)
            ax.set_xticks([])
            add_time_scalebar(ax, onset_times, y_frac=-0.02, label_offset_frac=0.03)
            style_panel_axes(ax, y_spine_bounds=(-60, 40))
            ax.tick_params(axis="y", labelsize=TICK_LABEL_SIZE)

        # --- Column 2: Voltage Clamp ---
        ax = axes[row, 1]
        vc_name = panel["vc_name"]
        vc_t = panel["vc_t"]
        vc_xlim = panel["vc_xlim"]
        vc_pad = 1.0
        rec = load_window(
            f"data/{vc_name}",
            vc_t + vc_xlim[0] - vc_pad,
            vc_t + vc_xlim[1] + vc_pad,
            chan=1,
        )
        if len(rec) > 0:
            t, inj, ref = rec[:, 0], rec[:, 1], rec[:, 2]
            dt = positive_dt(t)
            ax.set_ylim(*VC_DISPLAY_YLIM)
            ref_smooth, onset_indices = select_display_reference_onsets(
                t, ref, vc_t, vc_xlim, panel.get("vc_side")
            )
            onset_times = [t[idx] for idx in onset_indices]
            if "vc_smooth_sec" in panel:
                vc_smooth_sec = panel["vc_smooth_sec"]
            elif target_vc_display_noise_mad is not None:
                vc_smooth_sec = choose_vc_smoothing_for_target_noise(
                    t, inj, onset_times, target_vc_display_noise_mad
                )
            else:
                vc_smooth_sec = choose_vc_smoothing_seconds(t, inj, onset_times)
            inj_smooth = median_filter(inj, max(1, int(round(vc_smooth_sec / dt))))
            
            tx = normalize_two_burst_time(t, onset_times)
            _, inj_smooth_disp, vc_scale = map_vc_current_trace(
                inj, inj_smooth, onset_times, t, VC_DISPLAY_YLIM
            )
            ax.plot(tx, inj_smooth_disp, color=TRACE_COLOR, lw=1.25)

            ref_mapped = map_reference_trace(
                ref_smooth, VC_DISPLAY_YLIM, VC_REF_BASELINE_FRAC, VC_REF_AMPLITUDE_FRAC
            )
            ax.plot(tx, ref_mapped, color=REF_COLOR, lw=2, alpha=0.8)

            for onset_idx in onset_indices:
                ref_x = normalize_two_burst_time(np.array([t[onset_idx]]), onset_times)[0]
                idx_onset_vc = find_outward_current_onset(t, inj_smooth, t[onset_idx])
                if idx_onset_vc is None:
                    continue
                t_lead_vc_x = normalize_two_burst_time(np.array([t[idx_onset_vc]]), onset_times)[0]
                shade_start_vc = max(DISPLAY_XLIM[0], t_lead_vc_x)
                if shade_start_vc < ref_x:
                    ax.axvspan(
                        shade_start_vc,
                        ref_x,
                        color=HIGHLIGHT_COLOR,
                        alpha=PRE_I_HIGHLIGHT_ALPHA,
                    )

            if row == 0: ax.set_title("Voltage Clamp", fontsize=TITLE_FONT_SIZE)
            ax.set_xlim(*DISPLAY_XLIM)
            ax.set_yticks([])
            ax.set_xticks([])
            add_time_scalebar(ax, onset_times, y_frac=-0.02, label_offset_frac=0.03)
            add_current_scalebar(ax, vc_scale, current_nA=0.2)
            style_panel_axes(ax, show_left=False)
            ax.grid(alpha=GRID_ALPHA)

    plt.tight_layout()
    out_path = os.path.join("paper", "figures", "supp_figure5_pre_i_inhibition.pdf")
    save_pdf(plt.gcf(), out_path)
    print(f"Saved plot to {out_path}")

if __name__ == "__main__":
    plot_final_grid_tight()
