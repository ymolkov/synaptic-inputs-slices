import os

def load_episode_with_interpolated_spikes(filepath, t_start, t_end, threshold):
    """Load data, reconstruct 1kHz timebase, and insert interpolated spike peaks."""
    raw_rows = []
    if not os.path.exists(filepath):
        return []
    
    with open(filepath, 'r') as f:
        started = False
        t_base = 0
        count = 0
        for line in f:
            parts = line.split()
            if len(parts) >= 4:
                try:
                    t_val = float(parts[0])
                    if not started:
                        if t_val < t_start - 0.1: continue
                        t_base = t_val
                        started = True
                    
                    t = t_base + count * 0.001
                    count += 1
                    if t >= t_start - 0.005 and t <= t_end + 0.005:
                        raw_rows.append([t, float(parts[2]), float(parts[3])])
                    elif t > t_end + 0.005:
                        break
                except ValueError:
                    continue
    
    if not raw_rows: return []

    # Insert interpolated peaks
    processed_data = []
    dt = 0.001
    for i in range(1, len(raw_rows) - 1):
        t0, v0, r0 = raw_rows[i-1]
        t1, v1, r1 = raw_rows[i]
        t2, v2, r2 = raw_rows[i+1]
        
        # Add the current point
        if t1 >= t_start and t1 <= t_end:
            processed_data.append([t1, v1, r1])
        
        # Check if t1 is a peak above threshold
        if v1 > threshold and v1 > v0 and v1 >= v2:
            # Parabolic interpolation: v(x) = ax^2 + bx + c, where x is in units of dt from t1
            c = v1
            b = (v2 - v0) / 2.0
            a = (v0 + v2) / 2.0 - v1
            
            if a < 0: # Downward parabola
                x_max = -b / (2.0 * a)
                if abs(x_max) < 1.0: # Sanity check: peak must be within the triplet
                    v_max = c - (b * b) / (4.0 * a)
                    t_max = t1 + x_max * dt
                    # Linear interpolation for the reference signal at t_max
                    r_max = r1 + x_max * (r2 - r1 if x_max > 0 else r1 - r0)
                    
                    # Insert the interpolated point
                    if t_max >= t_start and t_max <= t_end:
                        # Find insertion index to keep temporal order
                        # Since processed_data[-1] is likely t1, we usually insert right after or before
                        if t_max > t1:
                            processed_data.append([t_max, v_max, r_max])
                        else:
                            # Insert before t1 (which was just appended)
                            processed_data.insert(-1, [t_max, v_max, r_max])
                            
    return processed_data

def generate_svg(episodes, output_path):
    width = 1200
    panel_height = 240
    padding = 60
    total_height = (panel_height + padding) * len(episodes) + padding
    
    svg = [f'<svg width="{width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg">']
    svg.append('<rect width="100%" height="100%" fill="white" />')
    
    for i, (name, path, s, e, threshold) in enumerate(episodes):
        data = load_episode_with_interpolated_spikes(path, s, e, threshold)
        if not data: continue
        
        y_offset = padding + i * (panel_height + padding)
        ts = [p[0] for p in data]
        vms = [p[1] for p in data]
        refs = [p[2] for p in data]
        
        t0 = ts[0]
        duration = ts[-1] - t0
        
        v_low = -80.0
        v_high = 45.0
        
        def tx(t):
            return 80 + (t - t0) / duration * (width - 160)
        
        def ty_vm(v):
            return (y_offset + panel_height * 0.75) - (v - v_low) / (v_high - v_low) * (panel_height * 0.7)

        def ty_ref(r):
            r_min, r_max = min(refs), max(refs)
            r_top = (y_offset + panel_height * 0.75) + 2
            r_bottom = y_offset + panel_height - 5
            if r_max == r_min: return r_bottom
            return r_bottom - (r - r_min) / (r_max - r_min + 1e-12) * (r_bottom - r_top)

        # Plot Vm (Blue) including interpolated peaks
        vm_points = [f"{tx(ts[j]):.2f},{ty_vm(vms[j]):.2f}" for j in range(len(vms))]
        svg.append(f'<polyline points="{" ".join(vm_points)}" fill="none" stroke="#1f77b4" stroke-width="0.8" />')
        
        # Plot Ref (Green)
        smoothed_ref = []
        for j in range(0, len(refs), 10):
            win = refs[max(0, j-10):min(len(refs), j+10)]
            r_avg = sum(win) / len(win)
            smoothed_ref.append(f"{tx(ts[j]):.2f},{ty_ref(r_avg):.2f}")
        svg.append(f'<polyline points="{" ".join(smoothed_ref)}" fill="none" stroke="#2ca02c" stroke-width="2.5" opacity="0.8" />')
        
        svg.append(f'<text x="90" y="{y_offset + 35}" font-family="Arial" font-size="18" font-weight="bold" fill="black">{name}</text>')
        
        yticks = [-80, -60, -40, -20, 0, 20, 40]
        # if "Cell 10" in name: yticks = [-90, -70, -50, -30, -10, 10, 30]

        
        # Filter ticks that fit in panel and draw Y-axis line between them
        valid_ticks = [v for v in yticks if y_offset <= ty_vm(v) <= y_offset + panel_height]
        if valid_ticks:
            y_min_tick = ty_vm(max(valid_ticks)) # Top tick has max voltage, min Y
            y_max_tick = ty_vm(min(valid_ticks)) # Bottom tick has min voltage, max Y
            svg.append(f'<line x1="80" y1="{y_min_tick:.2f}" x2="80" y2="{y_max_tick:.2f}" stroke="black" stroke-width="2" />')
        
        for v in yticks:
            y = ty_vm(v)
            if y_offset <= y <= y_offset + panel_height:
                svg.append(f'<text x="25" y="{y+5}" font-family="Arial" font-size="12" fill="#666">{v}</text>')
                svg.append(f'<line x1="75" y1="{y}" x2="80" y2="{y}" stroke="#666" />')
                svg.append(f'<line x1="80" y1="{y}" x2="{width-80}" y2="{y}" stroke="#f0f0f0" stroke-width="0.5" />')

    # Shared X-Axis
    last_y = total_height - 60
    svg.append(f'<line x1="80" y1="{last_y}" x2="{width-80}" y2="{last_y}" stroke="black" stroke-width="2" />')
    for t in range(0, 26, 5):
        x = 80 + t / 25.0 * (width - 140)
        svg.append(f'<line x1="{x}" y1="{last_y}" x2="{x}" y2="{last_y+10}" stroke="black" stroke-width="2" />')
        svg.append(f'<text x="{x-8}" y="{last_y+30}" font-family="Arial" font-size="16" fill="black">{t}</text>')
    svg.append(f'<text x="{width/2}" y="{last_y+55}" font-family="Arial" font-size="18" text-anchor="middle">Time (s)</text>')
    
    svg.append('</svg>')
    
    with open(output_path, 'w') as f:
        f.write("\n".join(svg))

if __name__ == "__main__":
    # Episodes: (label, path, start, end, detection_threshold)
    episodes = [
        ("VGAT-I Cell 9 (~3394s)", "data/VGAT-I-Cell9-C", 3381.4, 3406.4, -45.0),
        ("VgluT2-I Cell 4 (~479s)", "data/VgluT2-I-Cell4-C", 466.7, 491.7, -35.0),
        ("VgluT2-I Cell 10-C-1 (~2963s)", "data/VgluT2-I-Cell10-C-1", 2950.0, 2975.0, -40.0)
    ]
    
    generate_svg(episodes, "selected_ectopic_bursts_interpolated.svg")
    print("Done! Saved to selected_ectopic_bursts_interpolated.svg")
