# Figure Captions

## Figure 1: Method Illustration
A) Linear regressions of I-V curves at different phases. B) Wedge plot showing the trajectory of G_tot vs I_0. C) Reconstructed excitatory (red) and inhibitory (blue) conductances over two cycles. D) Polar representation of excitatory and inhibitory conductance profiles over one normalized cycle.

## Figure 2: Four Population Episodes
Representative 25-second rhythmic episodes highlighting the firing patterns of typical neurons in the VgluT2-I, VgluT2-E, VGAT-I, and VGAT-E populations. The blue trace illustrates the membrane potential ($V_m$) exhibiting distinct bursting dynamics time-aligned with the network rhythm. The green trace represents the integrated Hypoglossal Nerve Activity ($\int$ HNA), providing a global reference for the inspiratory phase. Action potential peaks are repaired spike-by-spike using a data-derived typical spike-top template fit to existing sampled points, increasing peak height and reducing undersampling-driven peak variability; episodes are selected from steady-current segments.

## Figure 3: Selected Conductances
Example traces of reconstructed conductances for selected cells from different populations (VgluT2-I, VgluT2-E, VGAT-I, VGAT-E).

## Figure 4: Combined Summary
Population-level summary of excitatory and inhibitory conductances during expiration and inspiration for the four main groups. Bars represent mean ± SEM of inliers (outliers removed via IQR method), with conductances normalized by leak conductance.

## Figure 4 (Polar Summary)
Polar representations of reconstructed conductances for representative cells corresponding to the group analysis in Figure 4. Displayed are matching single-cell profiles for VGAT-I, VgluT2-I, VGAT-E, and VgluT2-E population groups over one normalized cycle.

## Figure 4 (Phase Summary)
Phase-aligned Cartesian representations of reconstructed conductances for representative individual cells from each population group (VGAT-I, VgluT2-I, VGAT-E, VgluT2-E). Traces show excitatory (red) and inhibitory (blue) synaptic conductances normalized by the resting leak conductance, plotted over the normalized phase interval [-0.25, 0.25] surrounding the onset of the inspiratory burst. Solid outlines indicate the standard error of the mean (SEM).

## Figure 5: Weighted Circuit Diagram
Inferred preBotC population circuit with edge widths scaled to the same CSV-derived mean normalized conductances summarized in Table 1. Red arrows indicate excitatory drive from the inspiratory VgluT2 population, blue lines with terminal circles indicate inhibitory drive from the inspiratory and expiratory VGAT populations, and only connections exceeding the display threshold are shown. Connections below 0.05 are clipped from the diagram.

## Supplemental Figure 1: Sensitivity Analysis
Sensitivity of reconstructed conductances to variations in reversal potentials ($E_e$ and $E_i$). The grid shows results for variations of ±10 mV from default values.

## Supplemental Figure 2: Linearity Analysis
I-V regressions for all cells and recording modes presented in Figure 2. Scatter points represent data from specific phase bins ($\phi \approx 0.0$ in red, $\phi \approx 0.5$ in blue), with dashed lines indicating the corresponding linear fits.

## Supplemental Figure 3: Ectopic Bursting in Inhibitory Neurons
Representative 25-second inhibitory episodes highlighting ectopic bursting behavior. Each panel displays the membrane potential (blue) and the synchronized rhythmic reference signal (green). Action potential peaks have been accurately restored using parabolic interpolation to mitigate 1000 Hz undersampling. Episodes were selected for having clear ectopic bursts (>=3 spikes), a rhythmic network context (>=2 main bursts), and a steady holding current.

## Supplemental Figure 4: Pre-Inspiratory Initiator Activity
High-resolution comparison of pre-inspiratory action potential firing and underlying synaptic drive. **(Left column)** Current-clamp (CC) episodes show pre-inspiratory spiking (blue) preceding each network burst in the reference signal (green). **(Right column)** Corresponding voltage-clamp (VC) episodes from the same cells show the pre-inspiratory inward current (blue) preceding the same reference bursts (green). Each panel contains two adjacent reference bursts; pink shading marks the pre-inspiratory lead interval for each burst. Horizontal scale bars indicate 1 s, and VC panels include vertical current scale bars in native units.

## Supplemental Figure 5: Pre-Inspiratory Inhibition of Expiratory Cells
Examples of expiratory cells that stop firing before inspiratory onset and matched voltage-clamp recordings from the same cells showing a pre-inspiratory outward current. **(Left column)** Current-clamp (CC) episodes show expiratory spiking (blue) terminating before each inspiratory burst in the reference signal (green). **(Right column)** Corresponding voltage-clamp (VC) episodes show an outward synaptic current (blue) preceding the same inspiratory reference bursts (green). Each panel contains two adjacent reference bursts; pink shading marks the pre-inspiratory silent interval in CC and the pre-inspiratory outward-current interval in VC. Horizontal scale bars indicate 1 s, and VC panels include vertical current scale bars in native units.
