#!/bin/bash
set -e

# Get script directory to locate resources
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Paths
SRC="$PROJECT_ROOT/src/trace_analyzer.cpp"
BIN_DIR="$PROJECT_ROOT/bin"
EXE="$BIN_DIR/trace_analyzer"
GP_SCRIPT="$SCRIPT_DIR/plot_traces.gp"
RESULTS_DIR="$PROJECT_ROOT/results"

mkdir -p "$BIN_DIR"
mkdir -p "$RESULTS_DIR"

CXX="g++"
CXXFLAGS="-O3"

# Compile if not exists or newer
if [ ! -f "$EXE" ] || [ "$SRC" -nt "$EXE" ]; then
    # echo "Compiling $SRC..."
    $CXX $CXXFLAGS "$SRC" -o "$EXE"
fi

# Usage check
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <data_file_path> [optional args for trace_analyzer]"
    exit 1
fi

DATA_FILE_PATH="$1"
shift
ARGS="$@"

BASENAME=$(basename "$DATA_FILE_PATH")
# Unique temporary files in specific temp dir or system temp
# Using PROJECT_ROOT/tmp to keep it contained
TMP_DIR="$PROJECT_ROOT/tmp"
mkdir -p "$TMP_DIR"

UUID="${BASENAME}_$$"
DAT_FILE="$TMP_DIR/${UUID}.dat"
PH_FILE="$TMP_DIR/${UUID}.ph"
PH_DBL_FILE="$TMP_DIR/${UUID}.ph_doubled"
PAR_FILE="$TMP_DIR/${UUID}.par"
TRIG_FILE="$TMP_DIR/${UUID}.trig"
TRIG_Y_FILE="$TMP_DIR/${UUID}.trig_y"
TMP_FULL="$TMP_DIR/${UUID}_full.png"
TMP_THUMB="$TMP_DIR/${UUID}_thumb.png"

echo "[${BASENAME}] Processing..."

# Run Analyzer
# Pass -par argument for the unique parameter file
"$EXE" $ARGS -par "$PAR_FILE" -trig "$TRIG_FILE" < "$DATA_FILE_PATH" > "$DAT_FILE" 2> "$PH_FILE"

# Prepare doubled ph file for cyclic plots
cat "$PH_FILE" "$PH_FILE" > "$PH_DBL_FILE"

# Map trigger timestamps to raw reference values (col 4) for plotting in raw units.
if [ -s "$TRIG_FILE" ]; then
    awk '
      FNR==NR {tr[++m]=$1; next}
      {n++; t[n]=$1; y[n]=$4}
      END {
        if (n < 1 || m < 1) exit;
        i=1;
        for (k=1; k<=m; k++) {
          tt=tr[k];
          while (i < n && t[i+1] < tt) i++;
          if (i < n && t[i+1] != t[i]) {
            yy = y[i] + (tt - t[i]) * (y[i+1] - y[i]) / (t[i+1] - t[i]);
          } else {
            yy = y[i];
          }
          printf "%.6f\t%.10g\n", tt, yy;
        }
      }
    ' "$TRIG_FILE" "$DATA_FILE_PATH" > "$TRIG_Y_FILE"
else
    : > "$TRIG_Y_FILE"
fi

# Run Gnuplot
gnuplot -e "par_file='$PAR_FILE'" \
        -e "dat_file='$DAT_FILE'" \
        -e "raw_file='$DATA_FILE_PATH'" \
        -e "trig_y_file='$TRIG_Y_FILE'" \
        -e "ph_file='$PH_DBL_FILE'" \
        -e "trig_file='$TRIG_FILE'" \
        -e "out_full='$TMP_FULL'" \
        -e "out_thumb='$TMP_THUMB'" \
        "$GP_SCRIPT"

# Move/Rename final outputs to the dashboard recording asset directory.
WEB_DIR="${CLAMP_WEB_DIR:-$PROJECT_ROOT/web}"
RECORDINGS_DIR="$WEB_DIR/assets/recordings"
mkdir -p "$RECORDINGS_DIR"
mv "$TMP_FULL" "$RECORDINGS_DIR/${BASENAME}_full.png"
mv "$TMP_THUMB" "$RECORDINGS_DIR/${BASENAME}_thumb.png"
cp "$PAR_FILE" "$RECORDINGS_DIR/${BASENAME}.par"

# Cleanup
rm -f "$DAT_FILE" "$PH_FILE" "$PH_DBL_FILE" "$PAR_FILE" "$TRIG_FILE" "$TRIG_Y_FILE"

echo "[${BASENAME}] Done."
