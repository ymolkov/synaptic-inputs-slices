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
if (!exists("out_pdf")) out_pdf="tmp.pdf"
if (!exists("out_png")) out_png="tmp.png"

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

# PDF Output Setup
set term pdfcairo size 5,10 font ",8"
set out out_pdf
set multi lay 4,1

unset key

# Load calculated parameters (Ta, dTa, q)
load par_file
if (!exists("Du")) Du=0 

# Plot 1: Raw trace and trigger
set title sprintf("T=%g dT=%g dT/T=%g Du=%g",Ta,dTa,dTa/Ta,Du)
last_ph=1
plot dat_file u 1:2 w l title "Signal", \
     q w l dt 2 title "Threshold", \
     dat_file u 1:(curr_ph=$3, val=($3==0 && last_ph!=0 ? $2 : NaN), last_ph=curr_ph, val) w p pt 7 ps 0.25 lc "red" title "Trigger"

set style fill transparent solid .5 noborder

# Plot 2: Conductance/Current traces
set title sprintf("G=%g E=%g",G,-I/G)
plot dat_file u 1:5 w l, dat_file u 1:(($4-I)/G) w l


set key
unset title

# Plot 3: Phase-dependent Inhibition/Excitation
if (nph > 0 && g != 0) {
    # Add duty factor visualization (shaded area)
    # Add fixed phase highlight (0.95 to 1.1)
    set obj 1 rect from tr_start/1000., graph 0 to tr_end/1000.+1, graph 1 fc rgb "gray" fs transparent solid 0.4 noborder back
    
    # Initialize mean variables if not present (safety)
    if (!exists("G_inh_tr")) { G_inh_tr=NaN }
    if (!exists("G_exc_tr")) { G_exc_tr=NaN }
    if (!exists("G_inh_st")) { G_inh_st=NaN }
    if (!exists("G_exc_st")) { G_exc_st=NaN }

    # Draw Mean Lines
    # Stationary (st) - drawn across full width as baseline reference? Or just outside transient?
    # User asked for "during transient and stationary... show them by horizontal lines"
    # To implement "during", we can use vectors/segments.
    # However, for visual clarity, simply drawing full lines with different styles might be easier.
    # Let's try drawing segments if possible, but modulo logic is hard for 'set arrow'.
    # Alternative: Plot constants conditioned on x-range.
    
    plot [][0:] ph_file u ($0/1000.):5 w filledcurves y=0 lc "blue" title "inhibition", \
                ph_file u ($0/1000.):6 w filledcurves y=0 lc "red" title "excitation", \
                ph_file u ($0/1000.):($3/g/sqrt($4)) w l lt -1 title "error", \
                ph_file u ($0/1000.):(is_transient($7) ? G_inh_tr : NaN) w l lc "blue" lw 2 dt 1 notitle, \
                ph_file u ($0/1000.):(is_transient($7) ? G_exc_tr : NaN) w l lc "red" lw 2 dt 1 notitle, \
                ph_file u ($0/1000.):(!is_transient($7) ? G_inh_st : NaN) w l lc "blue" lw 2 dt 2 notitle, \
                ph_file u ($0/1000.):(!is_transient($7) ? G_exc_st : NaN) w l lc "red" lw 2 dt 2 notitle
} else {
    set title "No cycle data"
    plot 0
}
	
# Plot 4: Regression stats and Polar Plot
set size .5,.25
set origin 0,0
unset key
set title sprintf("Ee=%g Ei=%g",Ee,Ei)

if (nph > 0) {
    plot ph_file w lp, -Ei*x+Ii, -Ee*x+Ie
} else {
    plot 0
}

# unset multi # End layout 4,1? No, we extended to 5,1
# Plot 5: Ginh vs Gexc (Now Plot 4b)
unset polar
unset key
set size .5, .25
set origin .5, 0
set title "Ginh vs Gexc"
# Default Median/MAD variables to 0 if not present
if (!exists("Gi0")) { Gi0=0 }
if (!exists("dGi")) { dGi=0 }
if (!exists("Ge0")) { Ge0=0 }
if (!exists("dGe")) { dGe=0 }
if (!exists("tr_start")) { tr_start=-1 }
if (!exists("tr_end")) { tr_end=-1 }

if (nph > 0 && g != 0) {
    # Draw rectangle Median +/- MAD
    set obj 10 rect from Ge0-dGe, Gi0-dGi to Ge0+dGe, Gi0+dGi fc rgb "green" fs transparent solid 0.3 noborder back
    
    # Transient Filter Function defined globally above
    
    plot ph_file u 6:5 w l lc "black" title "Trajectory"
} else {
    plot 0
}

unset multi

# PNG Output (Thumbnail)
# Use pngcairo for better quality and transparency support
set term pngcairo size 256,256
set out out_png

set polar
set grid polar
unset border
unset xtics
unset ytics
unset rtics
set style fill transparent solid 0.5 noborder

if (nph > 0 && g != 0) {
    plot ph_file u ($0/nph*2*pi):5 w filledcurves lc "blue" title "inhibition", \
         ph_file u ($0/nph*2*pi):6 w filledcurves lc "red" title "excitation", \
         ph_file u ($0/nph*2*pi):($3/g/sqrt($4)) w l lt -1 title "error"
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
