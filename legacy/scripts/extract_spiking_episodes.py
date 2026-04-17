import sys
import os
import numpy as np
import matplotlib.pyplot as plt

def extract_episodes(filepath, out_prefix, max_time=200, threshold=-20.0, burst_gap=0.5, padding=0.5):
    data = []
    start_time = None
    with open(filepath, 'r') as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 3:
                t = float(parts[0])
                if start_time is None:
                    start_time = t
                if max_time is not None and t > start_time + max_time:
                    break
                
                ch0 = float(parts[1])
                vm = float(parts[2])
                try:
                    ch3 = float(parts[3])
                except IndexError:
                    ch3 = 0.0
                data.append((t, ch0, vm, ch3))
                
    data = np.array(data)
    
    t = data[:, 0]
    vm = data[:, 2]
    
    # Find spike times (threshold crossings)
    spike_idx = np.where((vm[:-1] < threshold) & (vm[1:] >= threshold))[0]
    spike_times = t[spike_idx]
    print(f"Found {len(spike_times)} spikes.")
    
    if len(spike_times) == 0:
        print("No spikes found.")
        return
        
    # Group into bursts/episodes
    episodes = []
    current_episode_start = spike_times[0]
    current_episode_end = spike_times[0]
    
    for st in spike_times[1:]:
        if st - current_episode_end <= burst_gap:
            current_episode_end = st
        else:
            episodes.append((current_episode_start, current_episode_end))
            current_episode_start = st
            current_episode_end = st
    episodes.append((current_episode_start, current_episode_end))
    
    print(f"Found {len(episodes)} episodes.")
    
    # Save and Plot episodes
    fig, axes = plt.subplots(len(episodes), 1, figsize=(10, 2*len(episodes)))
    if len(episodes) == 1:
        axes = [axes]
        
    for i, (ep_start, ep_end) in enumerate(episodes):
        start_t = ep_start - padding
        end_t = ep_end + padding
        
        mask = (t >= start_t) & (t <= end_t)
        ep_data = data[mask]
        
        # Save to csv/txt
        out_file = f"{out_prefix}_ep{i+1:03d}.txt"
        np.savetxt(out_file, ep_data, fmt="%.6g")
        
        # Plot
        ax = axes[i]
        ax.plot(ep_data[:, 0], ep_data[:, 2], color='black', lw=0.5)
        ax.set_title(f"Episode {i+1} ({start_t:.1f}s to {end_t:.1f}s)")
        ax.set_ylabel("Vm (mV)")
        if i == len(episodes) - 1:
            ax.set_xlabel("Time (s)")
            
    plt.tight_layout()
    plt.savefig(f"{out_prefix}_episodes.png")
    print(f"Saved plots to {out_prefix}_episodes.png")

if __name__ == "__main__":
    filepath = sys.argv[1]
    out_prefix = sys.argv[2]
    extract_episodes(filepath, out_prefix)
