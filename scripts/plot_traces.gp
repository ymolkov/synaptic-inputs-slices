# Visualize script (Gnuplot)
# Expects:
# 'dat' file with columns: t, p_filtered, phase, ch0, ch1
# 'ph' file with columns: slope, intercept, error, count
# 'par' file with variables: Ta, dTa, q

# Optional arguments passed via -e "..."
if (!exists("Ei")) Ei=-80
if (!exists("Ee")) Ee=-10

if (!exists("dat_file")) dat_file="dat"
if (!exists("ph_file")) ph_file="ph"
if (!exists("par_file")) par_file="par"
if (!exists("raw_file")) raw_file=""
if (!exists("trig_y_file")) trig_y_file=""
if (!exists("out_full")) out_full="tmp_full.png"
if (!exists("out_thumb")) out_thumb="tmp_thumb.png"

# Calculated derived parameters - now loaded from par_file
if (!exists("n_lines")) n_lines = system(sprintf("grep -c . %s", ph_file)) + 0
nph = n_lines / 2.0

# Initialize transient variables if not present (safety)
if (!exists("tr_start")) tr_start=-1
if (!exists("tr_end")) tr_end=-1

# Transient Filter Function
# Use modulo arithmetic to handle both repeated limits (0..nph) and continuous indices (0..2*nph)
# This works regardless of whether the index column wraps or increments
is_transient(x) = (tr_start <= tr_end) ? ((int(x)%int(nph)) >= tr_start && (int(x)%int(nph)) <= tr_end) : ((int(x)%int(nph)) >= tr_start || (int(x)%int(nph)) <= tr_end)

# Full Resolution PNG Output Setup
set term pngcairo size 1000,1200 font "Arial,12"
set out out_full
set multiplot

# Load calculated parameters (Ta, dTa, q)
load par_file
if (!exists("Du")) Du=0 
if (!exists("trig_file")) trig_file=""

# --- Row 1: Raw trace and trigger ---
set size 1.0, 0.33
set origin 0.0, 0.66
# Force consistent top-row geometry so panel 1 and 2 x-axes align.
set lmargin at screen 0.07
set rmargin at screen 0.92
set title sprintf("Mean cycle period: %.2g s    CV: %.2g    Number of cycles detected: %d", Ta, (Ta != 0 ? dTa/Ta : 0), int(N))
set ylabel "Reference Signal (a.u.)"
set xlabel "Recording Time (s)"
set xtics
unset key
plot dat_file u 1:2 w l lc "black" title "Signal", \
     q w l dt 2 lc "gray" title "Threshold", \
     (trig_file ne "" ? trig_file : "NaN") u 1:(q) w p pt 7 ps 0.5 lc "red" title "Trigger"

# --- Row 2: Conductance/Current traces ---
set size 1.0, 0.33
set origin 0.0, 0.33
set lmargin at screen 0.07
set rmargin at screen 0.92
set xtics
unset xlabel
unset ylabel
set title sprintf("Estimated G_{leak}: %.2g nS    E_{leak}: %.2g mV", 1000.0*G, -I/G)
set style fill transparent solid .5 noborder
# Keep left axis as plotted voltage-equivalent scale, and expose actual current on right.
set ylabel "Voltage (mV)"
set y2label "Current (nA)"
set ytics nomirror
set y2tics
set y2tics 0.1
set format y2 "%.1f"
set link y2 via (G*y + I) inverse ((y - I)/G)
set key top left
plot dat_file u 1:5 w l lc "blue" title "Voltage", \
     dat_file u 1:(($4-I)/G) w l lc "red" title "Current"

# --- Row 3 Left: Wedge Plot (Regression stats and Polar Plot) ---
set size 0.5, 0.33
set origin 0.0, 0.0
# Force consistent bottom-row geometry so x-axes align.
set lmargin at screen 0.07
set rmargin at screen 0.49
set bmargin at screen 0.05
set tmargin at screen 0.28
unset key
unset y2tics
unset y2label
unset format y2
unset link y2
set title sprintf("Wedge Plot (E_e=%.2g mV, E_i=%.2g mV)", Ee, Ei)
set xlabel "G_{tot} (nS)"
set ylabel "I_0 (nA)"
set key top left font ",8"
if (nph > 0) {
    plot ph_file u ($1*1000.0):2 w lp pt 7 ps 0.4 lc "black" notitle, \
         (-Ei*(x/1000.0)+Ii) w l lc "blue" title "Pure Inhibition", \
         (-Ee*(x/1000.0)+Ie) w l lc "red" title "Pure Excitation"
} else {
    plot 0
}

# --- Row 3 Right: Phase-dependent Inhibition/Excitation ---
set size 0.5, 0.33
set origin 0.5, 0.0
set lmargin at screen 0.56
set rmargin at screen 0.98
set bmargin at screen 0.05
set tmargin at screen 0.28
set title "Reconstructed Conductances"
set xlabel "Phase (2 cycles)"
set ylabel "Synaptic / Leak Conductance" offset 1,0
set ytics 0.1
set xtics 0.5
set xrange [0:2]
set key top right font ",8"
unset obj 1
if (nph > 0 && g != 0) {
    plot [][0:] ph_file u ($0/1000.):5 w filledcurves y=0 lc "blue" title "inhibition", \
                ph_file u ($0/1000.):6 w filledcurves y=0 lc "red" title "excitation", \
                ph_file u ($0/1000.):($3/g/sqrt($4)) w l lt -1 title "error"
} else {
    plot 0
}

unset multiplot

# PNG Output (Thumbnail)
# Reset everything for a clean polar plot
unset object
unset arrow
unset label
unset title
unset key
unset xlabel
unset ylabel
unset x2label
unset y2label
unset xrange
unset yrange
unset x2range
unset y2range
set autoscale x
set autoscale y
unset lmargin
unset rmargin
unset tmargin
unset bmargin
set origin 0,0
set size 1,1

# Use pngcairo for better quality and transparency support
set term pngcairo size 256,256
set out out_thumb

set polar
set grid polar
unset border
unset xtics
unset ytics
unset rtics
set style fill transparent solid 0.5 noborder

if (nph > 0 && g != 0) {
    plot ph_file u ($0/nph*2*pi):5 w filledcurves lc "blue" notitle, \
         ph_file u ($0/nph*2*pi):6 w filledcurves lc "red" notitle, \
         ph_file u ($0/nph*2*pi):($3/g/sqrt($4)) w l lt -1 lw 0.5 notitle
} else {
    plot 0
}

# Report Output
set print "tmp.rp"
print "Ee=",Ee
print "Ei=",Ei
print "g=",g
print "E=",E
set print
