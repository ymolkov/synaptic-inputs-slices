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

# Calculate stats from 'ph_file'
# Check if file has data first
# n_lines passed from batch_runner.py
# n_lines = system(sprintf("grep -c . %s", ph_file)) + 0
if (n_lines > 0) {
    stats ph_file u ($2+Ei*$1) nooutput name "S1"
    Ii=S1_max

    stats ph_file u ($2+Ee*$1) nooutput name "S2"
    Ie=S2_min

    stats ph_file u 1:2 nooutput name "S3"
    G=S3_mean_x
    I=S3_mean_y
    # ph_file is doubled, so single cycle count is half
    nph=S3_records / 2.0
} else {
    Ii=0; Ie=0; G=1e-9; I=0; nph=0
}

# Calculated derived parameters
if (Ee != Ei && (Ie - Ii) != 0) {
    g=(Ie-Ii)/(Ee-Ei)
    E=Ei-Ii/g
} else {
    g=1e-9
    E=0
}

# PDF Output Setup
set term pdfcairo size 5,10 font ",8"
set out out_pdf
set multi lay 4,1

unset key

# Load calculated parameters (Ta, dTa, q)
load par_file
set title sprintf("T=%g dT=%g dT/T=%g",Ta,dTa,dTa/Ta)

# Plot 1: Raw trace and trigger
set title sprintf("T=%g dT=%g dT/T=%g",Ta,dTa,dTa/Ta)
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
    plot [][0:] ph_file u 0:(0):((Ee*($1-g)-(-$2-g*E))/(Ee-Ei)/g) w filledcurves lc "blue" title "inhibition", \
                ph_file u 0:(0):(($1-(Ee*($1-g)-(-$2-g*E))/(Ee-Ei)-g)/g) w filledcurves lc "red" title "excitation", \
                ph_file u ($3/g/sqrt($4)) w l lt -1 title "error"
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

set size .5,.25
set origin .5,0

set grid polar
unset key
unset border
unset xtics
unset ytics
unset rtics

set polar
unset title

# Polar Plot
if (nph > 0 && g != 0) {
    plot ph_file u ($0/nph*2*pi):((Ee*($1-g)-(-$2-g*E))/(Ee-Ei)/g) w filledcurves lc "blue" title "inhibition", \
         ph_file u ($0/nph*2*pi):(($1-(Ee*($1-g)-(-$2-g*E))/(Ee-Ei)-g)/g) w filledcurves lc "red" title "excitation", \
         ph_file u ($0/nph*2*pi):($3/g/sqrt($4)) w l lt -1 title "error"
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
    plot ph_file u ($0/nph*2*pi):((Ee*($1-g)-(-$2-g*E))/(Ee-Ei)/g) w filledcurves lc "blue" title "inhibition", \
         ph_file u ($0/nph*2*pi):(($1-(Ee*($1-g)-(-$2-g*E))/(Ee-Ei)-g)/g) w filledcurves lc "red" title "excitation", \
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
