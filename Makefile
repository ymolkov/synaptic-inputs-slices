# --- Configuration ---
BIN_DIR     = bin
SRC_DIR     = src
SCRIPT_DIR  = scripts
RESULTS_DIR = results
PUB_DIR     = publication
PAPER_DIR   = paper
WEB_DIR = web

# List of groups to process
GROUPS = VGAT-I VgluT2-I VGAT-E VgluT2-E
# Map groups to their output CSV files (replacing - with _)
CSV_OUTPUTS = $(foreach g,$(GROUPS),$(RESULTS_DIR)/$(subst -,_,$g)_conductances.csv)

# Tool paths
CXX = g++
CXXFLAGS = -O3
PANDOC = pandoc

# --- Main Targets ---
.PHONY: all analysis figures table paper clean push help

all: paper

# 1. Compile the C++ analyzer
$(BIN_DIR)/trace_analyzer: $(SRC_DIR)/trace_analyzer.cpp
	@mkdir -p $(BIN_DIR)
	$(CXX) $(CXXFLAGS) $< -o $@

# 2. Run population analysis (runs if C++ binary or aggregation script changes)
# We use a pattern rule for the CSVs.
$(RESULTS_DIR)/%_conductances.csv: $(BIN_DIR)/trace_analyzer $(SCRIPT_DIR)/batch_analyze_conductances.py
	@mkdir -p $(RESULTS_DIR)
	python3 $(SCRIPT_DIR)/batch_analyze_conductances.py --group $(subst _,-,$*)

# 3. Generate publication figures
$(PUB_DIR)/figures/figure1_method.png: $(BIN_DIR)/trace_analyzer $(SCRIPT_DIR)/make_publication_figures.py
	@mkdir -p $(PUB_DIR)/figures
	python3 $(SCRIPT_DIR)/make_publication_figures.py --fig1 --captions
	cp $(PUB_DIR)/figures/figure1_method.png $(PAPER_DIR)/figures/figure1_method.png

$(PUB_DIR)/figures/figure2_four_populations.png: $(SCRIPT_DIR)/make_publication_figures.py
	@mkdir -p $(PUB_DIR)/figures
	python3 $(SCRIPT_DIR)/make_publication_figures.py --fig2 --captions
	cp $(PUB_DIR)/figures/figure2_four_populations.png $(PAPER_DIR)/figures/figure2_four_populations.png

$(PUB_DIR)/figures/figure3_selected.png: $(BIN_DIR)/trace_analyzer $(SCRIPT_DIR)/make_publication_figures.py
	@mkdir -p $(PUB_DIR)/figures
	python3 $(SCRIPT_DIR)/make_publication_figures.py --fig3 --captions
	cp $(PUB_DIR)/figures/figure3_selected.png $(PAPER_DIR)/figures/figure3_selected.png

$(PUB_DIR)/figures/figure4_summary.png: $(CSV_OUTPUTS) $(SCRIPT_DIR)/make_publication_figures.py
	@mkdir -p $(PUB_DIR)/figures
	python3 $(SCRIPT_DIR)/make_publication_figures.py --fig4 --captions
	cp $(PUB_DIR)/figures/figure4_summary.png $(PAPER_DIR)/figures/figure4_summary.png

$(PUB_DIR)/figures/supp_figure1_sensitivity.png: $(SCRIPT_DIR)/make_publication_figures.py
	@mkdir -p $(PUB_DIR)/figures
	python3 $(SCRIPT_DIR)/make_publication_figures.py --supp1 --captions
	cp $(PUB_DIR)/figures/supp_figure1_sensitivity.png $(PAPER_DIR)/figures/supp_figure1_sensitivity.png

$(PUB_DIR)/figures/supp_figure2_linearity.png: $(SCRIPT_DIR)/make_publication_figures.py
	@mkdir -p $(PUB_DIR)/figures
	python3 $(SCRIPT_DIR)/make_publication_figures.py --supp2 --captions
	cp $(PUB_DIR)/figures/supp_figure2_linearity.png $(PAPER_DIR)/figures/supp_figure2_linearity.png

$(PUB_DIR)/figures/supp_figure3_ectopic.svg: $(SCRIPT_DIR)/make_ectopic_svg.py
	@mkdir -p $(PUB_DIR)/figures
	python3 $(SCRIPT_DIR)/make_ectopic_svg.py
	mv selected_ectopic_bursts_interpolated.svg $(PUB_DIR)/figures/supp_figure3_ectopic.svg
	python3 $(SCRIPT_DIR)/generate_captions.py

$(PUB_DIR)/figures/supp_figure4_pre_i_recruitment.png: $(SCRIPT_DIR)/plot_refined_5x2.py
	@mkdir -p $(PUB_DIR)/figures
	python3 $(SCRIPT_DIR)/plot_refined_5x2.py
	python3 $(SCRIPT_DIR)/generate_captions.py
	cp $(PUB_DIR)/figures/supp_figure4_pre_i_recruitment.png $(PAPER_DIR)/figures/supp_figure4_pre_i_recruitment.png
	cp $(PUB_DIR)/captions.md $(PAPER_DIR)/captions.md

# 4. Generate the summary table (Tex and Docx)
$(PUB_DIR)/conductance_table.tex: $(CSV_OUTPUTS) $(SCRIPT_DIR)/generate_summary_table.py
	@mkdir -p $(PUB_DIR)
	python3 $(SCRIPT_DIR)/generate_summary_table.py
	@if command -v $(PANDOC) >/dev/null 2>&1; then \
		$(PANDOC) $(PUB_DIR)/conductance_table.tex -o $(PUB_DIR)/conductance_table.docx; \
	fi
	cp $(PUB_DIR)/conductance_table.tex $(PAPER_DIR)/conductance_table.tex

# 5. Compile the LaTeX manuscript
$(PAPER_DIR)/main.pdf: $(PAPER_DIR)/main.tex \
                    $(PUB_DIR)/figures/figure1_method.png \
                    $(PUB_DIR)/figures/figure2_four_populations.png \
                    $(PUB_DIR)/figures/figure3_selected.png \
                    $(PUB_DIR)/figures/figure4_summary.png \
                    $(PUB_DIR)/figures/supp_figure1_sensitivity.png \
                    $(PUB_DIR)/figures/supp_figure2_linearity.png \
                    $(PUB_DIR)/figures/supp_figure3_ectopic.svg \
                    $(PUB_DIR)/figures/supp_figure4_pre_i_recruitment.png \
                    $(PUB_DIR)/conductance_table.tex
	cd $(PAPER_DIR) && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex

# --- Shorthand commands ---
analysis: $(CSV_OUTPUTS)
figures:  $(PUB_DIR)/figures/figure1_method.png \
          $(PUB_DIR)/figures/figure2_four_populations.png \
          $(PUB_DIR)/figures/figure3_selected.png \
          $(PUB_DIR)/figures/figure4_summary.png \
          $(PUB_DIR)/figures/supp_figure1_sensitivity.png \
          $(PUB_DIR)/figures/supp_figure2_linearity.png \
          $(PUB_DIR)/figures/supp_figure3_ectopic.svg \
          $(PUB_DIR)/figures/supp_figure4_pre_i_recruitment.png
table:    $(PUB_DIR)/conductance_table.tex
paper:    $(PAPER_DIR)/main.pdf

dashboard: $(BIN_DIR)/trace_analyzer
	@mkdir -p $(WEB_DIR)
	python3 $(SCRIPT_DIR)/batch_run_all.py --outdir $(WEB_DIR)
	python3 $(SCRIPT_DIR)/generate_report.py --outdir $(WEB_DIR)

deploy:
	bash $(SCRIPT_DIR)/deploy_web.sh

push:
	git add -A
	git commit -m "Build update via Makefile"
	git push origin main

clean:
	rm -rf $(BIN_DIR)/*
	rm -rf tmp/*
	rm -rf $(WEB_DIR)

help:
	@echo "Available targets:"
	@echo "  all       : Complete pipeline (builds paper)"
	@echo "  analysis  : Run all population analyses"
	@echo "  figures   : Generate publication figures"
	@echo "  table     : Generate summary tables"
	@echo "  paper     : Compile LaTeX manuscript"
	@echo "  dashboard : Generate standalone web-deployable dashboard"
	@echo "  push      : Commit and push all changes"
	@echo "  clean     : Remove binaries, temporary files and dashboard"
