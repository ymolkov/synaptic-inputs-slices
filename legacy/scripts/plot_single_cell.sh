#!/bin/bash
CELL=$1

export PYTHONPATH=/Users/ymolkov/clamp/scripts
python3 -c "
from scripts.figure_utils import run_analysis
run_analysis('${CELL}')
"

# Double the ph file for 2-cycle plotting
cat "tmp/${CELL}.ph" "tmp/${CELL}.ph" > "tmp/${CELL}.ph_doubled"
N_LINES=$(wc -l < "tmp/${CELL}.ph_doubled")

gnuplot -e "basename='${CELL}'" \
        -e "dat_file='tmp/${CELL}.dat'" \
        -e "ph_file='tmp/${CELL}.ph_doubled'" \
        -e "par_file='tmp/${CELL}.par'" \
        -e "trig_y_file='tmp/${CELL}.trig'" \
        -e "out_full='results/${CELL}_full.png'" \
        -e "out_thumb='results/${CELL}_thumb.png'" \
        -e "n_lines=${N_LINES}" \
        -e "E_leak=-60" \
        scripts/plot_traces.gp
echo "Saved PNG to results/${CELL}_full.png"
