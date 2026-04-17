# --- Configuration ---
BIN_DIR     = bin
SRC_DIR     = src
SCRIPT_DIR  = scripts
RESULTS_DIR = results
PAPER_DIR   = paper
FIG_DIR     = $(PAPER_DIR)/figures
WEB_DIR     = web
STYLE_SCRIPT = $(SCRIPT_DIR)/figure_style.py

# List of groups to process
GROUPS = VGAT-I VgluT2-I VGAT-E VgluT2-E
# Map groups to their output CSV files (replacing - with _)
CSV_OUTPUTS = $(foreach g,$(GROUPS),$(RESULTS_DIR)/$(subst -,_,$g)_conductances.csv)

MAIN_FIGURES = \
	$(FIG_DIR)/method_protocol_steps.pdf \
	$(FIG_DIR)/figure1_method.pdf \
	$(FIG_DIR)/figure2_four_populations.pdf \
	$(FIG_DIR)/figure3_selected.pdf \
	$(FIG_DIR)/figure4_phase_summary.pdf \
	$(FIG_DIR)/figure4_summary.pdf \
	$(FIG_DIR)/circuit_weighted.pdf

SUPP_FIGURES = \
	$(FIG_DIR)/supp_figure1_sensitivity.pdf \
	$(FIG_DIR)/supp_figure2_linearity.pdf \
	$(FIG_DIR)/supp_figure3_ectopic.pdf \
	$(FIG_DIR)/supp_figure4_pre_i_recruitment.pdf \
	$(FIG_DIR)/supp_figure5_pre_i_inhibition.pdf

FIGURES = $(MAIN_FIGURES) $(SUPP_FIGURES)
MANUSCRIPT = $(PAPER_DIR)/Synaptic_Architecture_PreBotC.pdf

# Tool paths
CXX = g++
CXXFLAGS = -O3

# --- Main Targets ---
.PHONY: all analysis figures paper dashboard clean help

all: paper

# 1. Compile the C++ analyzer
$(BIN_DIR)/trace_analyzer: $(SRC_DIR)/trace_analyzer.cpp
	@mkdir -p $(BIN_DIR)
	$(CXX) $(CXXFLAGS) $< -o $@

# 2. Run population analysis
$(RESULTS_DIR)/%_conductances.csv: $(BIN_DIR)/trace_analyzer $(SCRIPT_DIR)/batch_analyze_conductances.py
	@mkdir -p $(RESULTS_DIR)
	python3 $(SCRIPT_DIR)/batch_analyze_conductances.py --group $(subst _,-,$*)

# 3. Generate manuscript figures directly into paper/figures
$(FIG_DIR)/method_protocol_steps.pdf: $(SCRIPT_DIR)/make_methods_protocol_figure.py $(STYLE_SCRIPT)
	@mkdir -p $(FIG_DIR)
	python3 $(SCRIPT_DIR)/make_methods_protocol_figure.py --output $@

$(FIG_DIR)/figure1_method.pdf: $(BIN_DIR)/trace_analyzer $(SCRIPT_DIR)/make_manuscript_figures.py $(STYLE_SCRIPT)
	@mkdir -p $(FIG_DIR)
	python3 $(SCRIPT_DIR)/make_manuscript_figures.py --fig1

$(FIG_DIR)/figure2_four_populations.pdf: $(SCRIPT_DIR)/make_manuscript_figures.py $(STYLE_SCRIPT)
	@mkdir -p $(FIG_DIR)
	python3 $(SCRIPT_DIR)/make_manuscript_figures.py --fig2

$(FIG_DIR)/figure3_selected.pdf: $(BIN_DIR)/trace_analyzer $(SCRIPT_DIR)/make_manuscript_figures.py $(STYLE_SCRIPT)
	@mkdir -p $(FIG_DIR)
	python3 $(SCRIPT_DIR)/make_manuscript_figures.py --fig3

$(FIG_DIR)/figure4_phase_summary.pdf: $(BIN_DIR)/trace_analyzer $(SCRIPT_DIR)/make_manuscript_figures.py $(STYLE_SCRIPT)
	@mkdir -p $(FIG_DIR)
	python3 $(SCRIPT_DIR)/make_manuscript_figures.py --fig4phase

$(FIG_DIR)/figure4_summary.pdf: $(CSV_OUTPUTS) $(SCRIPT_DIR)/make_manuscript_figures.py $(STYLE_SCRIPT)
	@mkdir -p $(FIG_DIR)
	python3 $(SCRIPT_DIR)/make_manuscript_figures.py --fig4

$(FIG_DIR)/circuit_weighted.pdf: $(CSV_OUTPUTS) $(SCRIPT_DIR)/plot_weighted_circuit.py $(SCRIPT_DIR)/conductance_summary.py $(STYLE_SCRIPT)
	@mkdir -p $(FIG_DIR)
	python3 $(SCRIPT_DIR)/plot_weighted_circuit.py --out $@

$(FIG_DIR)/supp_figure1_sensitivity.pdf: $(SCRIPT_DIR)/make_manuscript_figures.py $(STYLE_SCRIPT)
	@mkdir -p $(FIG_DIR)
	python3 $(SCRIPT_DIR)/make_manuscript_figures.py --supp1

$(FIG_DIR)/supp_figure2_linearity.pdf: $(SCRIPT_DIR)/make_manuscript_figures.py $(STYLE_SCRIPT)
	@mkdir -p $(FIG_DIR)
	python3 $(SCRIPT_DIR)/make_manuscript_figures.py --supp2

$(FIG_DIR)/supp_figure3_ectopic.pdf: $(SCRIPT_DIR)/make_ectopic_png.py $(STYLE_SCRIPT)
	@mkdir -p $(FIG_DIR)
	python3 $(SCRIPT_DIR)/make_ectopic_png.py --out $@

$(FIG_DIR)/supp_figure4_pre_i_recruitment.pdf: $(SCRIPT_DIR)/plot_refined_5x2.py $(STYLE_SCRIPT)
	@mkdir -p $(FIG_DIR)
	python3 $(SCRIPT_DIR)/plot_refined_5x2.py

$(FIG_DIR)/supp_figure5_pre_i_inhibition.pdf: $(SCRIPT_DIR)/plot_supp_figure5.py $(STYLE_SCRIPT)
	@mkdir -p $(FIG_DIR)
	python3 $(SCRIPT_DIR)/plot_supp_figure5.py

# 4. Compile the LaTeX manuscript
$(MANUSCRIPT): $(PAPER_DIR)/Synaptic_Architecture_PreBotC.tex \
               $(PAPER_DIR)/Synaptic_Architecture_PreBotC-supp.tex \
               $(PAPER_DIR)/references.bib \
               $(FIGURES) \
               $(FIG_DIR)/Fig8.pdf
	cd $(PAPER_DIR) && \
		pdflatex -interaction=nonstopmode Synaptic_Architecture_PreBotC.tex && \
		bibtex Synaptic_Architecture_PreBotC && \
		pdflatex -interaction=nonstopmode Synaptic_Architecture_PreBotC.tex && \
		pdflatex -interaction=nonstopmode Synaptic_Architecture_PreBotC.tex

# --- Shorthand commands ---
analysis: $(CSV_OUTPUTS)
figures:  $(FIGURES)
paper:    $(MANUSCRIPT)

dashboard: $(BIN_DIR)/trace_analyzer
	@mkdir -p $(WEB_DIR)
	python3 $(SCRIPT_DIR)/batch_run_all.py --outdir $(WEB_DIR)
	python3 $(SCRIPT_DIR)/generate_report.py --outdir $(WEB_DIR)

clean:
	rm -rf $(BIN_DIR)/*
	rm -rf tmp/*
	rm -rf $(WEB_DIR)

help:
	@echo "Available targets:"
	@echo "  all       : Complete pipeline (builds paper)"
	@echo "  analysis  : Run all population analyses"
	@echo "  figures   : Generate manuscript figures"
	@echo "  paper     : Compile LaTeX manuscript"
	@echo "  dashboard : Generate standalone web-deployable dashboard"
	@echo "  clean     : Remove binaries, temporary files and dashboard"
