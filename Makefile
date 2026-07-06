# --- Configuration ---
BIN_DIR     = bin
SRC_DIR     = src
SCRIPT_DIR  = scripts
RESULTS_DIR = results
WEB_DIR     = web

# List of groups to process
GROUPS = VGAT-I VgluT2-I VGAT-E VgluT2-E
# Map groups to their output CSV files (replacing - with _)
CSV_OUTPUTS = $(foreach g,$(GROUPS),$(RESULTS_DIR)/$(subst -,_,$g)_conductances.csv)

# Tool paths
CXX = g++
CXXFLAGS = -O3

# --- Main Targets ---
.PHONY: all analysis dashboard clean help

all: analysis dashboard

# 1. Compile the C++ analyzer
$(BIN_DIR)/trace_analyzer: $(SRC_DIR)/trace_analyzer.cpp
	@mkdir -p $(BIN_DIR)
	$(CXX) $(CXXFLAGS) $< -o $@

# 2. Run population analysis
$(RESULTS_DIR)/%_conductances.csv: $(BIN_DIR)/trace_analyzer $(SCRIPT_DIR)/batch_analyze_conductances.py
	@mkdir -p $(RESULTS_DIR)
	python3 $(SCRIPT_DIR)/batch_analyze_conductances.py --group $(subst _,-,$*)

# --- Shorthand commands ---
analysis: $(CSV_OUTPUTS)

dashboard: $(BIN_DIR)/trace_analyzer
	@mkdir -p $(WEB_DIR)
	python3 $(SCRIPT_DIR)/batch_run_all.py --outdir $(WEB_DIR)
	python3 $(SCRIPT_DIR)/generate_report.py --outdir $(WEB_DIR)

clean:
	rm -rf $(BIN_DIR)/*
	rm -rf tmp/*

help:
	@echo "Available targets:"
	@echo "  all       : Run analysis and regenerate the dashboard"
	@echo "  analysis  : Run all population analyses"
	@echo "  dashboard : Generate standalone web-deployable dashboard"
	@echo "  clean     : Remove binaries and temporary files"
