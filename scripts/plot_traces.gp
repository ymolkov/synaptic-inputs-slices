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
set title sprintf("T=%g dT=%g dT/T=%g Du=%g N=%d",Ta,dTa,dTa/Ta,Du,int(N))
unset key
plot dat_file u 1:2 w l lc "black" title "Signal", \
     q w l dt 2 lc "gray" title "Threshold", \
     (trig_file ne "" ? trig_file : "NaN") u 1:(q) w p pt 7 ps 0.5 lc "red" title "Trigger"

# --- Row 2: Conductance/Current traces ---
set size 1.0, 0.33
set origin 0.0, 0.33
set title sprintf("G=%g E=%g",G,-I/G)
set style fill transparent solid .5 noborder
plot dat_file u 1:5 w l lc "blue", dat_file u 1:(($4-I)/G) w l lc "red"

# --- Row 3 Left: Wedge Plot (Regression stats and Polar Plot) ---
set size 0.5, 0.33
set origin 0.0, 0.0
set title sprintf("Wedge Plot (Ee=%g Ei=%g)",Ee,Ei)
set key top left font ",8"
if (nph > 0) {
    plot ph_file w lp pt 7 ps 0.4 lc "black" title "Data", \
         -Ei*x+Ii w l lc "blue" dt 2 title "Inh", \
         -Ee*x+Ie w l lc "red" dt 2 title "Exc"
} else {
    plot 0
}

# --- Row 3 Right: Phase-dependent Inhibition/Excitation ---
set size 0.5, 0.33
set origin 0.5, 0.0
set title "Reconstructed Conductances"
set key top right font ",8"
unset obj 1
if (nph > 0 && g != 0) {
    set obj 1 rect from tr_start/1000., graph 0 to tr_end/1000.+1, graph 1 fc rgb "gray" fs transparent solid 0.2 noborder back
    
    # Initialize mean variables
    if (!exists("G_inh_tr")) { G_inh_tr=NaN }
    if (!exists("G_exc_tr")) { G_exc_tr=NaN }
    if (!exists("G_inh_st")) { G_inh_st=NaN }
    if (!exists("G_exc_st")) { G_exc_st=NaN }

    plot [][0:] ph_file u ($0/1000.):5 w filledcurves y=0 lc "blue" title "inhibition", \
                ph_file u ($0/1000.):6 w filledcurves y=0 lc "red" title "excitation", \
                ph_file u ($0/1000.):($3/g/sqrt($4)) w l lt -1 title "error", \
                ph_file u ($0/1000.):(is_transient($7) ? G_inh_tr : NaN) w l lc "blue" lw 2 notitle, \
                ph_file u ($0/1000.):(is_transient($7) ? G_exc_tr : NaN) w l lc "red" lw 2 notitle, \
                ph_file u ($0/1000.):(!is_transient($7) ? G_inh_st : NaN) w l lc "blue" lw 2 dt 2 notitle, \
                ph_file u ($0/1000.):(!is_transient($7) ? G_exc_st : NaN) w l lc "red" lw 2 dt 2 notitle
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
set margin 0,0,0,0
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
