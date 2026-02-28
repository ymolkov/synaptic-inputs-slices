import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLICATION_DIR = os.path.join(PROJECT_ROOT, "publication")
CAPTIONS_FILE = os.path.join(PUBLICATION_DIR, "captions.md")

def generate_captions():
    print("Generating captions standalone...")
    with open(CAPTIONS_FILE, "w") as f:
        f.write("# Figure Captions\n\n")
        f.write("## Figure 1: Method Illustration\n")
        f.write("A) Linear regressions of I-V curves at different phases. B) Wedge plot showing the trajectory of G_tot vs I_0. C) Reconstructed excitatory (red) and inhibitory (blue) conductances over two cycles. D) Polar representation of excitatory and inhibitory conductance profiles over one normalized cycle.\n\n")
        f.write("## Figure 2: Four Population Episodes\n")
        f.write(r"Representative 25-second rhythmic episodes highlighting the firing patterns of typical neurons in the VgluT2-I, VgluT2-E, VGAT-I, and VGAT-E populations. The blue trace illustrates the membrane potential ($V_m$) exhibiting distinct bursting dynamics time-aligned with the network rhythm. The green trace represents the integrated Hypoglossal Nerve Activity ($\int$ HNA), providing a global reference for the inspiratory phase. Action potential peaks have been individually corrected via parabolic interpolation to physiological maximums to accurately visualize the natural burst structures and mitigate continuous voltage undersampling artifacts inherent to the recording resolution." + "\n\n")
        f.write("## Figure 3: Selected Conductances\n")
        f.write("Example traces of reconstructed conductances for selected cells from different populations (VgluT2-I, VgluT2-E, VGAT-I, VGAT-E).\n\n")
        f.write("## Figure 4: Combined Summary\n")
        f.write("Population-level summary of excitatory and inhibitory conductances during expiration and inspiration for the three main groups. Bars represent mean ± SEM of inliers (outliers removed via IQR method).\n\n")
        f.write("## Supplemental Figure 1: Sensitivity Analysis\n")
        f.write("Sensitivity of reconstructed conductances to variations in reversal potentials ($E_e$ and $E_i$). The grid shows results for variations of ±10 mV from default values.\n\n")
        f.write("## Supplemental Figure 2: Linearity Analysis\n")
        f.write(r"I-V regressions for all cells and recording modes presented in Figure 2. Scatter points represent data from specific phase bins ($\phi \approx 0.0$ in red, $\phi \approx 0.5$ in blue), with dashed lines indicating the corresponding linear fits." + "\n\n")
        f.write("## Supplemental Figure 3: Ectopic Bursting in Inhibitory Neurons\n")
        f.write("Representative 25-second inhibitory episodes highlighting ectopic bursting behavior. Each panel displays the membrane potential (blue) and the synchronized rhythmic reference signal (green). Action potential peaks have been accurately restored using parabolic interpolation to mitigate 1000 Hz undersampling. Episodes were selected for having clear ectopic bursts (>=3 spikes), a rhythmic network context (>=2 main bursts), and a steady holding current.\n")

if __name__ == "__main__":
    generate_captions()
