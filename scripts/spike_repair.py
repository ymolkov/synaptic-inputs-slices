import numpy as np


def find_spike_peaks(vm, threshold=-30.0, min_distance=10):
    """Threshold-crossing spike segmentation with one apex per event."""
    peaks = []
    i = 1
    n = len(vm)
    last_peak = -min_distance

    while i < n - 1:
        # Upward crossing starts a spike event.
        if vm[i - 1] < threshold <= vm[i]:
            start = i
            j = i
            while j < n - 1 and vm[j] >= threshold:
                j += 1
            end = j

            if end > start:
                local_idx = start + int(np.argmax(vm[start:end]))
                if local_idx - last_peak >= min_distance:
                    peaks.append(local_idx)
                    last_peak = local_idx
            i = end
        else:
            i += 1

    return np.array(peaks, dtype=int)


def _extract_spike_segments(vm, peaks, base_threshold, half_window):
    segs = []
    for idx in peaks:
        if idx - half_window < 0 or idx + half_window >= len(vm):
            continue

        left = idx
        while left > 0 and vm[left] > base_threshold:
            left -= 1

        right = idx
        while right < len(vm) - 1 and vm[right] > base_threshold:
            right += 1

        left_slice = vm[max(0, left - 5):left + 1] if left > 0 else np.array([base_threshold])
        right_slice = vm[right:min(len(vm), right + 6)] if right < len(vm) - 1 else np.array([base_threshold])
        base_local = min(base_threshold, np.percentile(left_slice, 25), np.percentile(right_slice, 25))

        amp_raw = vm[idx] - base_local
        if amp_raw <= 1e-6:
            continue

        x = np.arange(-half_window, half_window + 1, dtype=float)
        y = vm[idx - half_window:idx + half_window + 1]
        y_norm = (y - base_local) / amp_raw

        segs.append(
            {
                "idx": idx,
                "left": left,
                "right": right,
                "base": float(base_local),
                "raw_peak": float(vm[idx]),
                "raw_amp": float(amp_raw),
                "x": x,
                "y": y,
                "y_norm": y_norm,
            }
        )

    return segs


def _build_template(segments):
    """
    Build a typical spike-top template from the strongest spikes.
    Template is normalized so max(template) == 1.
    """
    if not segments:
        return None, None

    amps = np.array([s["raw_amp"] for s in segments])
    amp_cut = np.percentile(amps, 80)
    top = [s for s in segments if s["raw_amp"] >= amp_cut]
    if len(top) < 5:
        top = segments

    y_stack = np.stack([s["y_norm"] for s in top], axis=0)
    template = np.median(y_stack, axis=0)

    # Mild smoothing to suppress point noise without flattening the apex.
    kernel = np.array([1.0, 2.0, 3.0, 2.0, 1.0], dtype=float)
    kernel /= np.sum(kernel)
    template = np.convolve(template, kernel, mode="same")

    template = np.maximum(template, 0.0)
    tmax = np.max(template)
    if tmax <= 1e-9:
        return None, None

    template /= tmax
    return top[0]["x"], template


def _fit_segment_to_template(seg, template_x, template_y):
    """
    Fit segment to y = base + A * template(x - shift).
    Returns estimated amplitude above base and fit RMSE.
    """
    x = seg["x"]
    y = seg["y"] - seg["base"]
    raw_amp = seg["raw_amp"]

    best = None
    for shift in np.linspace(-1.5, 1.5, 121):
        t = np.interp(x - shift, template_x, template_y, left=0.0, right=0.0)
        denom = np.dot(t, t)
        if denom <= 1e-9:
            continue

        amp = np.dot(y, t) / denom
        amp = max(amp, raw_amp)
        y_hat = amp * t
        rmse = np.sqrt(np.mean((y - y_hat) ** 2))

        if best is None or rmse < best[0]:
            best = (rmse, amp)

    if best is None:
        return raw_amp, np.inf

    return float(best[1]), float(best[0])


def repair_undersampled_spikes(
    vm,
    dt,
    peak_threshold=-30.0,
    base_threshold=-45.0,
    min_distance_ms=5.0,
    max_scale=3.0,
    max_extra_mv=25.0,
):
    """
    Conservative spike repair for undersampled peaks.
    - Per spike: estimate apex using local quadratic fit + template fit.
    - Only raises peaks (never downscales), so spikes cannot disappear.
    - Correction is apex-weighted to preserve spike width/shape.
    """
    vm = np.asarray(vm)
    if len(vm) < 5 or dt <= 0:
        return vm.copy(), {"num_peaks": 0, "mean_peak_lift": 0.0, "template_peak_amp": 0.0}

    min_dist_pts = max(1, int(round((min_distance_ms / 1000.0) / dt)))
    peaks = find_spike_peaks(vm, threshold=peak_threshold, min_distance=min_dist_pts)
    if len(peaks) == 0:
        return vm.copy(), {"num_peaks": 0, "mean_peak_lift": 0.0, "template_peak_amp": 0.0}

    segments = _extract_spike_segments(vm, peaks, base_threshold, half_window=4)
    if len(segments) < 3:
        return vm.copy(), {
            "num_peaks": int(len(peaks)),
            "mean_peak_lift": 0.0,
            "template_peak_amp": 0.0,
        }

    template_x, template_y = _build_template(segments)
    if template_x is None:
        return vm.copy(), {
            "num_peaks": int(len(peaks)),
            "mean_peak_lift": 0.0,
            "template_peak_amp": 0.0,
        }

    amps_fit = []
    for seg in segments:
        amp_est, _ = _fit_segment_to_template(seg, template_x, template_y)
        amps_fit.append(amp_est)
    amps_fit = np.array(amps_fit)
    raw_amps = np.array([s["raw_amp"] for s in segments])
    typical_amp = float(np.median(amps_fit))
    target_floor = float(np.percentile(raw_amps, 80))
    raw_cv = float(np.std(raw_amps) / (np.mean(raw_amps) + 1e-9))
    boost_strength = float(np.clip((raw_cv - 0.12) / 0.15, 0.0, 1.0))

    repaired = vm.copy()
    lifts = []
    max_target_peak = np.percentile(vm[peaks], 95) + max_extra_mv

    for seg, amp_est in zip(segments, amps_fit):
        raw_amp = seg["raw_amp"]
        raw_peak = seg["raw_peak"]
        base = seg["base"]
        idx = seg["idx"]

        # Local quadratic apex estimate (uses only existing points near apex).
        if idx >= 2 and idx <= len(vm) - 3:
            y = vm[idx - 2:idx + 3]
            x = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
            a, b, c = np.polyfit(x, y, 2)
            if a < 0:
                x_max = -b / (2.0 * a)
                if abs(x_max) <= 2.2:
                    quad_peak = float(a * x_max * x_max + b * x_max + c)
                else:
                    quad_peak = raw_peak
            else:
                quad_peak = raw_peak
        else:
            quad_peak = raw_peak
        quad_amp = max(raw_amp, quad_peak - base)

        # Up-only variability correction: lift low spikes toward a robust high-amp floor.
        amp_floor = raw_amp + boost_strength * 0.85 * max(0.0, target_floor - raw_amp)
        amp_target = max(raw_amp, quad_amp, min(amp_est, typical_amp * 1.10), amp_floor)
        target_peak = min(base + amp_target, max_target_peak)

        scale = (target_peak - base) / max(raw_amp, 1e-9)
        scale = np.clip(scale, 1.0, max_scale)  # never below 1.0 -> no downscaling

        lifts.append(max(0.0, target_peak - raw_peak))

        # Apex-weighted boost keeps flanks close to original and avoids waveform distortion.
        span = max(1, seg["right"] - seg["left"] + 1)
        sigma = max(1.0, span / 6.0)
        for j in range(seg["left"], seg["right"] + 1):
            if vm[j] > base:
                w = np.exp(-0.5 * ((j - idx) / sigma) ** 2)
                local_scale = 1.0 + (scale - 1.0) * w
                repaired[j] = base + (vm[j] - base) * local_scale

    return repaired, {
        "num_peaks": int(len(segments)),
        "mean_peak_lift": float(np.mean(lifts)) if lifts else 0.0,
        "template_peak_amp": float(typical_amp),
        "compression": float(boost_strength),
    }


def equalize_spike_heights_for_display(
    vm,
    dt,
    peak_threshold=-30.0,
    base_threshold=-45.0,
    min_distance_ms=5.0,
    target_percentile=85.0,
    retain_fraction=0.10,
    apex_half_window=2,
):
    """
    Display-only peak equalization.
    Pulls per-spike amplitudes toward a robust high percentile to reduce
    undersampling-driven height variability while keeping spikes generally taller.
    """
    vm = np.asarray(vm)
    if len(vm) < 5 or dt <= 0:
        return vm.copy(), {"num_spikes": 0, "target_amp": 0.0}

    min_dist_pts = max(1, int(round((min_distance_ms / 1000.0) / dt)))
    peaks = find_spike_peaks(vm, threshold=peak_threshold, min_distance=min_dist_pts)
    if len(peaks) == 0:
        return vm.copy(), {"num_spikes": 0, "target_amp": 0.0}

    segments = _extract_spike_segments(vm, peaks, base_threshold, half_window=3)
    if len(segments) < 3:
        return vm.copy(), {"num_spikes": int(len(peaks)), "target_amp": 0.0}

    amps = np.array([s["raw_amp"] for s in segments])
    target_amp = float(np.percentile(amps, target_percentile))

    out = vm.copy()
    for s in segments:
        raw_amp = s["raw_amp"]
        if raw_amp <= 1e-9:
            continue

        amp_target = retain_fraction * raw_amp + (1.0 - retain_fraction) * target_amp
        amp_target = np.clip(amp_target, 0.75 * target_amp, 1.15 * target_amp)

        scale = amp_target / raw_amp
        scale = np.clip(scale, 0.60, 3.0)
        base = s["base"]

        j0 = max(s["idx"] - apex_half_window, s["left"])
        j1 = min(s["idx"] + apex_half_window, s["right"])
        for j in range(j0, j1 + 1):
            if vm[j] > base:
                out[j] = base + (vm[j] - base) * scale

    return out, {"num_spikes": int(len(segments)), "target_amp": target_amp}
