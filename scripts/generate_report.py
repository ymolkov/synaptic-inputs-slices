#!/usr/bin/env python3
import glob
import html as html_lib
import json
import os
import re
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
RECORDINGS_SUBDIR = os.path.join("assets", "recordings")

POPULATION_ORDER = ["VgluT2-I", "VGAT-I", "VGAT-E", "VgluT2-E"]


def get_category(basename):
    match = re.match(r"^([a-zA-Z0-9]+-[a-zA-Z0-9]+)", basename)
    if match:
        return match.group(1)
    return "Miscellaneous"


def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split("([0-9]+)", s)]


def read_par_file(path):
    values = {}
    if not os.path.exists(path):
        return values

    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            try:
                number = float(value)
            except ValueError:
                values[key] = value
                continue
            values[key] = int(number) if number.is_integer() else number
    return values


def recording_mode(basename):
    match = re.search(r"-(C|V)(?:-(\d+))?$", basename)
    if not match:
        return {"mode": "?", "label": "?", "variant": ""}

    mode = match.group(1)
    variant = match.group(2) or ""
    return {
        "mode": mode,
        "label": f"{mode}{variant}" if variant else mode,
        "variant": variant,
    }


def population_sort_key(category):
    if category in POPULATION_ORDER:
        return (0, POPULATION_ORDER.index(category))
    return (1, natural_sort_key(category))


def posix_join(*parts):
    return "/".join(part.strip("/") for part in parts if part)


def resolve_recordings_dir(target_dir):
    recordings_dir = os.path.join(target_dir, RECORDINGS_SUBDIR)
    if glob.glob(os.path.join(recordings_dir, "*_thumb.png")):
        return recordings_dir, RECORDINGS_SUBDIR.replace(os.sep, "/")
    return target_dir, ""


def build_dashboard_data(scan_dir, asset_prefix=""):
    thumb_files = sorted(glob.glob(os.path.join(scan_dir, "*_thumb.png")), key=natural_sort_key)
    records = []
    cells_by_population = defaultdict(set)
    counts_by_population = defaultdict(lambda: {"recordings": 0, "current": 0, "voltage": 0, "accepted": 0})

    for thumb_path in thumb_files:
        basename = os.path.basename(thumb_path).replace("_thumb.png", "")
        category = get_category(basename)
        cell_match = re.match(r"^(.+)-[CV](?:-|$)", basename)
        cell_id = cell_match.group(1) if cell_match else basename
        mode_info = recording_mode(basename)
        par_name = f"{basename}.par"
        params = read_par_file(os.path.join(scan_dir, par_name))
        cycles = params.get("N")
        accepted = isinstance(cycles, (int, float)) and cycles > 25

        record = {
            "id": basename,
            "basename": basename,
            "category": category,
            "cell": cell_id,
            "cellLabel": cell_id.split("-")[-1],
            "mode": mode_info["mode"],
            "modeLabel": mode_info["label"],
            "variant": mode_info["variant"],
            "full": posix_join(asset_prefix, f"{basename}_full.png"),
            "thumb": posix_join(asset_prefix, f"{basename}_thumb.png"),
            "par": posix_join(asset_prefix, par_name),
            "params": params,
            "cycles": cycles,
            "accepted": accepted,
        }
        records.append(record)

        cells_by_population[category].add(cell_id)
        counts = counts_by_population[category]
        counts["recordings"] += 1
        counts["accepted"] += 1 if accepted else 0
        if mode_info["mode"] == "C":
            counts["current"] += 1
        elif mode_info["mode"] == "V":
            counts["voltage"] += 1

    mode_order = {"C": 0, "V": 1}
    records.sort(
        key=lambda record: (
            population_sort_key(record["category"]),
            natural_sort_key(record["cell"]),
            mode_order.get(record["mode"], 9),
            natural_sort_key(record["basename"]),
        )
    )

    populations = []
    for category in sorted(counts_by_population.keys(), key=population_sort_key):
        counts = counts_by_population[category]
        populations.append(
            {
                "name": category,
                "cells": len(cells_by_population[category]),
                "recordings": counts["recordings"],
                "current": counts["current"],
                "voltage": counts["voltage"],
                "accepted": counts["accepted"],
                "identity": "Excitatory" if category.startswith("VgluT2") else "Inhibitory",
                "phase": "Inspiratory" if category.endswith("-I") else "Expiratory",
            }
        )

    total_cycles = [
        record["cycles"]
        for record in records
        if isinstance(record["cycles"], (int, float))
    ]
    total_cycles_sorted = sorted(total_cycles)
    median_cycles = None
    if total_cycles_sorted:
        middle = len(total_cycles_sorted) // 2
        if len(total_cycles_sorted) % 2:
            median_cycles = total_cycles_sorted[middle]
        else:
            median_cycles = (total_cycles_sorted[middle - 1] + total_cycles_sorted[middle]) / 2

    return {
        "records": records,
        "populations": populations,
        "summary": {
            "recordings": len(records),
            "cells": len({record["cell"] for record in records}),
            "accepted": sum(1 for record in records if record["accepted"]),
            "current": sum(1 for record in records if record["mode"] == "C"),
            "voltage": sum(1 for record in records if record["mode"] == "V"),
            "medianCycles": median_cycles,
        },
    }


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analysis Dashboard | Synaptic Slices</title>
    <style>
        :root {
            --ink: #17191c;
            --muted: #626a73;
            --paper: #f7f6f2;
            --panel: #ffffff;
            --soft: #edf1f3;
            --line: #d7dde3;
            --dark: #111417;
            --exc: #c64056;
            --inh: #0f8499;
            --amber: #b77822;
            --green: #30795b;
            --shadow: 0 14px 34px rgba(17, 20, 23, 0.12);
        }

        * { box-sizing: border-box; }

        html, body {
            margin: 0;
            height: 100%;
            overflow: hidden;
            background: var(--paper);
            color: var(--ink);
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            font-size: 14px;
            line-height: 1.45;
        }

        button, input, select {
            font: inherit;
        }

        button, a {
            -webkit-tap-highlight-color: transparent;
        }

        svg, img {
            display: block;
        }

        .topbar {
            height: 68px;
            display: grid;
            grid-template-columns: minmax(260px, 1fr) auto auto;
            align-items: center;
            gap: 18px;
            padding: 0 18px;
            background: rgba(255, 255, 255, 0.92);
            border-bottom: 1px solid var(--line);
        }

        .title-block {
            min-width: 0;
        }

        h1 {
            margin: 0;
            font-size: 1.08rem;
            line-height: 1.15;
        }

        .subtitle {
            margin-top: 3px;
            color: var(--muted);
            font-size: 0.82rem;
        }

        .stat-strip {
            display: flex;
            gap: 8px;
            align-items: center;
        }

        .stat {
            min-width: 86px;
            padding: 8px 10px;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--panel);
        }

        .stat span {
            display: block;
            color: var(--muted);
            font-size: 0.7rem;
            font-weight: 800;
            text-transform: uppercase;
        }

        .stat strong {
            display: block;
            margin-top: 1px;
            font-size: 1.15rem;
            line-height: 1;
        }

        .top-actions,
        .viewer-actions,
        .segment {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .icon-button,
        .link-button,
        .segment button,
        .record-button {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--panel);
            color: var(--ink);
            cursor: pointer;
        }

        .icon-button,
        .link-button {
            min-height: 38px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 0 12px;
            text-decoration: none;
            font-weight: 800;
        }

        .icon-button {
            width: 38px;
            padding: 0;
        }

        .icon-button svg,
        .link-button svg,
        .search-wrap svg,
        .empty-state svg {
            width: 17px;
            height: 17px;
            fill: none;
            stroke: currentColor;
            stroke-width: 1.9;
            stroke-linecap: round;
            stroke-linejoin: round;
        }

        .icon-button:hover,
        .link-button:hover,
        .segment button:hover,
        .record-button:hover {
            border-color: #aeb8c2;
            transform: translateY(-1px);
        }

        .app-layout {
            height: calc(100% - 68px);
            display: grid;
            grid-template-columns: 230px 330px minmax(420px, 1fr) 300px;
            min-width: 0;
        }

        .panel {
            min-width: 0;
            min-height: 0;
            border-right: 1px solid var(--line);
            background: var(--panel);
            overflow: hidden;
        }

        .filter-panel,
        .browser-panel,
        .inspector-panel {
            display: flex;
            flex-direction: column;
        }

        .filter-panel {
            background: #fbfbf8;
        }

        .panel-head {
            padding: 16px;
            border-bottom: 1px solid var(--line);
        }

        .panel-kicker {
            margin: 0 0 7px;
            color: var(--amber);
            font-size: 0.72rem;
            font-weight: 850;
            text-transform: uppercase;
        }

        .panel-title {
            margin: 0;
            font-size: 1rem;
            font-weight: 850;
        }

        .population-list {
            display: grid;
            gap: 8px;
            padding: 12px;
            overflow-y: auto;
        }

        .population-button {
            width: 100%;
            display: grid;
            grid-template-columns: 10px minmax(0, 1fr) auto;
            gap: 10px;
            align-items: center;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #fff;
            padding: 10px;
            text-align: left;
            cursor: pointer;
        }

        .population-button.is-active {
            border-color: var(--dark);
            box-shadow: 0 0 0 1px var(--dark) inset;
        }

        .pop-dot {
            width: 10px;
            height: 42px;
            border-radius: 8px;
            background: var(--muted);
        }

        .pop-dot.exc { background: var(--exc); }
        .pop-dot.inh { background: var(--inh); }
        .pop-main {
            min-width: 0;
        }
        .pop-name {
            display: block;
            font-weight: 850;
        }
        .pop-meta {
            display: block;
            color: var(--muted);
            font-size: 0.78rem;
        }
        .pop-count {
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 800;
        }

        .filter-block {
            padding: 16px;
            border-top: 1px solid var(--line);
        }

        .filter-label {
            display: block;
            margin-bottom: 8px;
            color: var(--muted);
            font-size: 0.72rem;
            font-weight: 850;
            text-transform: uppercase;
        }

        .segment {
            width: 100%;
            padding: 3px;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--soft);
        }

        .segment button {
            min-height: 32px;
            flex: 1;
            border-color: transparent;
            background: transparent;
            font-weight: 800;
        }

        .segment button.is-active {
            background: #fff;
            border-color: var(--line);
            box-shadow: 0 1px 2px rgba(17, 20, 23, 0.08);
        }

        .browser-panel {
            background: #f8faf9;
        }

        .browser-top {
            padding: 12px;
            display: grid;
            gap: 10px;
            border-bottom: 1px solid var(--line);
        }

        .search-wrap {
            min-height: 40px;
            display: grid;
            grid-template-columns: auto 1fr;
            align-items: center;
            gap: 9px;
            padding: 0 12px;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #fff;
            color: var(--muted);
        }

        .search-wrap input {
            min-width: 0;
            border: 0;
            outline: 0;
            background: transparent;
            color: var(--ink);
        }

        .list-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            color: var(--muted);
            font-size: 0.82rem;
        }

        .recording-list {
            min-height: 0;
            overflow-y: auto;
            padding: 10px;
            display: grid;
            gap: 8px;
        }

        .record-button {
            width: 100%;
            display: grid;
            grid-template-columns: 58px minmax(0, 1fr);
            gap: 10px;
            padding: 8px;
            text-align: left;
        }

        .record-button.is-active {
            border-color: var(--dark);
            box-shadow: 0 0 0 1px var(--dark) inset;
            background: #fff;
        }

        .record-thumb {
            width: 58px;
            height: 58px;
            border: 1px solid var(--line);
            border-radius: 6px;
            object-fit: cover;
            background: #fff;
        }

        .record-main {
            min-width: 0;
            display: grid;
            gap: 5px;
        }

        .record-title-row,
        .badge-row {
            min-width: 0;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .record-name {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-weight: 850;
        }

        .record-file {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: var(--muted);
            font-size: 0.78rem;
        }

        .badge {
            display: inline-flex;
            align-items: center;
            min-height: 21px;
            padding: 0 7px;
            border-radius: 6px;
            background: var(--soft);
            color: var(--muted);
            font-size: 0.72rem;
            font-weight: 850;
        }

        .badge.mode-c {
            background: rgba(198, 64, 86, 0.13);
            color: var(--exc);
        }

        .badge.mode-v {
            background: rgba(15, 132, 153, 0.13);
            color: var(--inh);
        }

        .badge.accepted {
            background: rgba(48, 121, 91, 0.14);
            color: var(--green);
        }

        .badge.warn {
            background: rgba(183, 120, 34, 0.15);
            color: var(--amber);
        }

        .viewer-panel {
            min-width: 0;
            min-height: 0;
            display: grid;
            grid-template-rows: auto minmax(0, 1fr);
            background: #eff2f2;
            border-right: 1px solid var(--line);
        }

        .viewer-toolbar {
            min-width: 0;
            min-height: 64px;
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            align-items: center;
            gap: 12px;
            padding: 10px 14px;
            background: #fff;
            border-bottom: 1px solid var(--line);
        }

        .selected-name {
            margin: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 1rem;
            font-weight: 850;
        }

        .selected-subtitle {
            margin-top: 2px;
            color: var(--muted);
            font-size: 0.8rem;
        }

        .image-stage {
            min-width: 0;
            min-height: 0;
            display: grid;
            place-items: center;
            overflow: auto;
            padding: 18px;
        }

        .image-stage img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            transform-origin: center center;
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #fff;
            box-shadow: var(--shadow);
        }

        .inspector-panel {
            border-right: 0;
            background: #fff;
        }

        .inspector-scroll {
            min-height: 0;
            overflow-y: auto;
            padding: 12px;
            display: grid;
            gap: 12px;
        }

        .info-section {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #fff;
            overflow: hidden;
        }

        .info-section h2 {
            margin: 0;
            padding: 10px 12px;
            border-bottom: 1px solid var(--line);
            background: #f8faf9;
            font-size: 0.82rem;
            text-transform: uppercase;
        }

        .kv-list {
            display: grid;
        }

        .kv {
            display: grid;
            grid-template-columns: minmax(92px, 0.85fr) minmax(0, 1fr);
            gap: 8px;
            padding: 8px 12px;
            border-bottom: 1px solid var(--soft);
        }

        .kv:last-child {
            border-bottom: 0;
        }

        .kv dt {
            color: var(--muted);
            font-weight: 750;
        }

        .kv dd {
            margin: 0;
            min-width: 0;
            overflow-wrap: anywhere;
            font-weight: 750;
            text-align: right;
        }

        .meters {
            display: grid;
            gap: 12px;
            padding: 12px;
        }

        .meter-pair {
            display: grid;
            gap: 6px;
        }

        .meter-head {
            display: flex;
            justify-content: space-between;
            gap: 8px;
            font-size: 0.78rem;
            font-weight: 850;
        }

        .meter-track {
            height: 8px;
            display: grid;
            grid-template-columns: var(--excw, 0%) var(--inhw, 0%) 1fr;
            overflow: hidden;
            border-radius: 8px;
            background: var(--soft);
        }

        .meter-exc {
            background: var(--exc);
        }

        .meter-inh {
            background: var(--inh);
        }

        .meter-values {
            display: flex;
            justify-content: space-between;
            color: var(--muted);
            font-size: 0.72rem;
        }

        .empty-state {
            width: min(420px, calc(100% - 28px));
            display: grid;
            justify-items: center;
            gap: 12px;
            padding: 28px;
            border: 1px dashed #b8c2cc;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.72);
            color: var(--muted);
            text-align: center;
        }

        .empty-state svg {
            width: 26px;
            height: 26px;
        }

        @media (max-width: 1180px) {
            .topbar {
                grid-template-columns: minmax(220px, 1fr) auto;
            }

            .stat-strip {
                display: none;
            }

            .app-layout {
                grid-template-columns: 210px 300px minmax(380px, 1fr);
            }

            .inspector-panel {
                display: none;
            }
        }

        @media (max-width: 820px) {
            html, body {
                overflow: auto;
                overflow-x: hidden;
            }

            .topbar {
                height: auto;
                min-height: 68px;
                grid-template-columns: 1fr;
                align-items: start;
                padding: 12px;
            }

            .app-layout,
            .panel,
            .viewer-panel {
                width: 100%;
                max-width: 100vw;
            }

            .top-actions {
                justify-content: flex-start;
            }

            .app-layout {
                height: auto;
                min-height: calc(100vh - 92px);
                display: grid;
                grid-template-columns: 1fr;
            }

            .panel,
            .viewer-panel {
                border-right: 0;
                border-bottom: 1px solid var(--line);
            }

            .population-button {
                grid-template-columns: 10px minmax(0, 1fr);
            }

            .pop-count {
                display: none;
            }

            .segment,
            .search-wrap {
                max-width: calc(100vw - 32px);
            }

            .population-list,
            .recording-list {
                max-height: 320px;
            }

            .viewer-toolbar {
                grid-template-columns: 1fr;
            }

            .viewer-actions {
                flex-wrap: wrap;
            }

            .image-stage {
                min-height: 520px;
            }
        }
    </style>
</head>
<body>
    <header class="topbar">
        <div class="title-block">
            <h1>Synaptic Conductance Dashboard</h1>
            <div class="subtitle">Per-recording audit view for CLAMP phase-binned inference</div>
        </div>
        <div id="summaryStats" class="stat-strip" aria-label="Dashboard summary"></div>
        <div class="top-actions">
            <a class="link-button" href="index.html">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 18l-6-6 6-6"></path></svg>
                <span>Companion</span>
            </a>
        </div>
    </header>

    <div class="app-layout">
        <aside class="panel filter-panel">
            <div class="panel-head">
                <p class="panel-kicker">Filter</p>
                <p class="panel-title">Populations</p>
            </div>
            <div id="populationList" class="population-list"></div>
            <div class="filter-block">
                <span class="filter-label">Acquisition</span>
                <div class="segment" role="group" aria-label="Acquisition mode">
                    <button class="is-active" type="button" data-mode="All">All</button>
                    <button type="button" data-mode="C">C</button>
                    <button type="button" data-mode="V">V</button>
                </div>
            </div>
        </aside>

        <section class="panel browser-panel" aria-label="Recording browser">
            <div class="browser-top">
                <label class="search-wrap">
                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z"></path><path d="M16 16l5 5"></path></svg>
                    <input id="searchInput" type="search" placeholder="Search cell or file" autocomplete="off">
                </label>
                <div class="list-meta">
                    <span id="visibleCount">0 recordings</span>
                    <span id="activeFilter">All populations</span>
                </div>
            </div>
            <div id="recordingList" class="recording-list"></div>
        </section>

        <main class="viewer-panel" aria-label="Selected recording">
            <div class="viewer-toolbar">
                <div class="selected-copy">
                    <p id="selectedName" class="selected-name">No recording selected</p>
                    <div id="selectedSubtitle" class="selected-subtitle">Choose a recording from the browser</div>
                </div>
                <div class="viewer-actions">
                    <button id="prevButton" class="icon-button" type="button" aria-label="Previous recording">
                        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 18l-6-6 6-6"></path></svg>
                    </button>
                    <button id="nextButton" class="icon-button" type="button" aria-label="Next recording">
                        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6-6 6"></path></svg>
                    </button>
                    <button id="zoomOutButton" class="icon-button" type="button" aria-label="Zoom out">
                        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14"></path></svg>
                    </button>
                    <button id="fitButton" class="icon-button" type="button" aria-label="Fit image">
                        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 3H3v5"></path><path d="M16 3h5v5"></path><path d="M8 21H3v-5"></path><path d="M16 21h5v-5"></path></svg>
                    </button>
                    <button id="zoomInButton" class="icon-button" type="button" aria-label="Zoom in">
                        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14"></path><path d="M5 12h14"></path></svg>
                    </button>
                    <a id="openImageLink" class="link-button" href="#" target="_blank" rel="noopener">
                        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 4h6v6"></path><path d="M10 14 20 4"></path><path d="M20 14v6H4V4h6"></path></svg>
                        <span>Open PNG</span>
                    </a>
                </div>
            </div>
            <div id="imageStage" class="image-stage">
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v14H4z"></path><path d="M8 9h8"></path><path d="M8 13h5"></path></svg>
                    <span>No recording selected</span>
                </div>
            </div>
        </main>

        <aside class="panel inspector-panel" aria-label="Recording parameters">
            <div class="panel-head">
                <p class="panel-kicker">Inspector</p>
                <p class="panel-title">Parameters</p>
            </div>
            <div id="inspector" class="inspector-scroll"></div>
        </aside>
    </div>

    <script id="dashboardData" type="application/json">__DASHBOARD_DATA__</script>
    <script>
        const DATA = JSON.parse(document.getElementById("dashboardData").textContent);
        const state = {
            population: "All",
            mode: "All",
            search: "",
            selectedId: null,
            zoom: 1,
            filtered: []
        };

        const els = {
            summaryStats: document.getElementById("summaryStats"),
            populationList: document.getElementById("populationList"),
            recordingList: document.getElementById("recordingList"),
            visibleCount: document.getElementById("visibleCount"),
            activeFilter: document.getElementById("activeFilter"),
            searchInput: document.getElementById("searchInput"),
            selectedName: document.getElementById("selectedName"),
            selectedSubtitle: document.getElementById("selectedSubtitle"),
            imageStage: document.getElementById("imageStage"),
            inspector: document.getElementById("inspector"),
            openImageLink: document.getElementById("openImageLink"),
            prevButton: document.getElementById("prevButton"),
            nextButton: document.getElementById("nextButton"),
            zoomOutButton: document.getElementById("zoomOutButton"),
            zoomInButton: document.getElementById("zoomInButton"),
            fitButton: document.getElementById("fitButton")
        };

        function escapeHtml(value) {
            return String(value ?? "").replace(/[&<>"']/g, (char) => ({
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;"
            }[char]));
        }

        function formatNumber(value, digits = 3) {
            if (value === null || value === undefined || Number.isNaN(Number(value))) {
                return "n/a";
            }
            const number = Number(value);
            if (Math.abs(number) >= 100 || Number.isInteger(number)) {
                return String(Math.round(number));
            }
            if (Math.abs(number) < 0.001 && number !== 0) {
                return number.toExponential(2);
            }
            return number.toFixed(digits);
        }

        function plural(count, singular, pluralLabel = `${singular}s`) {
            return `${count} ${count === 1 ? singular : pluralLabel}`;
        }

        function popClass(populationName) {
            return populationName.startsWith("VgluT2") ? "exc" : "inh";
        }

        function modeClass(mode) {
            return mode === "C" ? "mode-c" : mode === "V" ? "mode-v" : "";
        }

        function selectedRecord() {
            return DATA.records.find((record) => record.id === state.selectedId) || null;
        }

        function renderSummary() {
            const stats = [
                ["Recordings", DATA.summary.recordings],
                ["Cells", DATA.summary.cells],
                [">25 cycles", DATA.summary.accepted],
                ["Median N", formatNumber(DATA.summary.medianCycles, 1)]
            ];
            els.summaryStats.innerHTML = stats.map(([label, value]) => `
                <div class="stat">
                    <span>${escapeHtml(label)}</span>
                    <strong>${escapeHtml(value)}</strong>
                </div>
            `).join("");
        }

        function renderPopulationFilters() {
            const allRecordings = DATA.summary.recordings;
            const allCells = DATA.summary.cells;
            const buttons = [
                {
                    name: "All",
                    cells: allCells,
                    recordings: allRecordings,
                    identity: "All identities",
                    phase: "All phases"
                },
                ...DATA.populations
            ];

            els.populationList.innerHTML = buttons.map((population) => {
                const active = state.population === population.name;
                const dotClass = population.name === "All" ? "" : popClass(population.name);
                return `
                    <button class="population-button ${active ? "is-active" : ""}" type="button" data-population="${escapeHtml(population.name)}">
                        <span class="pop-dot ${dotClass}" aria-hidden="true"></span>
                        <span class="pop-main">
                            <span class="pop-name">${escapeHtml(population.name)}</span>
                            <span class="pop-meta">${escapeHtml(population.identity)} / ${escapeHtml(population.phase)}</span>
                        </span>
                        <span class="pop-count">${population.recordings} rec<br>${population.cells} cells</span>
                    </button>
                `;
            }).join("");

            els.populationList.querySelectorAll("[data-population]").forEach((button) => {
                button.addEventListener("click", () => {
                    state.population = button.dataset.population;
                    render();
                });
            });
        }

        function getFilteredRecords() {
            const term = state.search.trim().toLowerCase();
            return DATA.records.filter((record) => {
                if (state.population !== "All" && record.category !== state.population) {
                    return false;
                }
                if (state.mode !== "All" && record.mode !== state.mode) {
                    return false;
                }
                if (!term) {
                    return true;
                }
                return [
                    record.basename,
                    record.cell,
                    record.category,
                    record.modeLabel,
                    record.par
                ].some((field) => String(field).toLowerCase().includes(term));
            });
        }

        function renderRecordList() {
            state.filtered = getFilteredRecords();
            els.visibleCount.textContent = plural(state.filtered.length, "recording");
            els.activeFilter.textContent = state.population === "All" ? "All populations" : state.population;

            if (!state.filtered.length) {
                els.recordingList.innerHTML = `
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z"></path><path d="M16 16l5 5"></path></svg>
                        <span>No recordings match the current filters</span>
                    </div>
                `;
                state.selectedId = null;
                renderSelection();
                return;
            }

            if (!state.filtered.some((record) => record.id === state.selectedId)) {
                state.selectedId = state.filtered[0].id;
                state.zoom = 1;
            }

            els.recordingList.innerHTML = state.filtered.map((record) => {
                const active = record.id === state.selectedId;
                const cycles = record.cycles === null || record.cycles === undefined ? "n/a" : formatNumber(record.cycles, 0);
                return `
                    <button class="record-button ${active ? "is-active" : ""}" type="button" data-id="${escapeHtml(record.id)}">
                        <img class="record-thumb" src="${escapeHtml(record.thumb)}" alt="">
                        <span class="record-main">
                            <span class="record-title-row">
                                <span class="badge ${modeClass(record.mode)}">${escapeHtml(record.modeLabel)}</span>
                                <span class="record-name">${escapeHtml(record.cellLabel)}</span>
                            </span>
                            <span class="record-file">${escapeHtml(record.basename)}</span>
                            <span class="badge-row">
                                <span class="badge">${escapeHtml(record.category)}</span>
                                <span class="badge ${record.accepted ? "accepted" : "warn"}">N=${cycles}</span>
                            </span>
                        </span>
                    </button>
                `;
            }).join("");

            els.recordingList.querySelectorAll("[data-id]").forEach((button) => {
                button.addEventListener("click", () => {
                    state.selectedId = button.dataset.id;
                    state.zoom = 1;
                    render();
                });
            });
        }

        function kvRows(rows) {
            return rows.map(([key, value]) => `
                <div class="kv">
                    <dt>${escapeHtml(key)}</dt>
                    <dd>${escapeHtml(value)}</dd>
                </div>
            `).join("");
        }

        function meter(label, exc, inh) {
            const values = [Number(exc) || 0, Number(inh) || 0];
            const max = Math.max(...values, 0.001);
            const excWidth = Math.max(0, Math.min(100, values[0] / max * 100));
            const inhWidth = Math.max(0, Math.min(100, values[1] / max * 100));
            const total = excWidth + inhWidth;
            const scale = total > 100 ? 100 / total : 1;
            return `
                <div class="meter-pair">
                    <div class="meter-head">
                        <span>${escapeHtml(label)}</span>
                        <span>G/g_leak</span>
                    </div>
                    <div class="meter-track" style="--excw:${excWidth * scale}%; --inhw:${inhWidth * scale}%;">
                        <span class="meter-exc"></span>
                        <span class="meter-inh"></span>
                        <span></span>
                    </div>
                    <div class="meter-values">
                        <span>Exc ${formatNumber(exc)}</span>
                        <span>Inh ${formatNumber(inh)}</span>
                    </div>
                </div>
            `;
        }

        function renderInspector(record) {
            if (!record) {
                els.inspector.innerHTML = "";
                return;
            }

            const p = record.params || {};
            els.inspector.innerHTML = `
                <section class="info-section">
                    <h2>Recording</h2>
                    <dl class="kv-list">
                        ${kvRows([
                            ["Population", record.category],
                            ["Cell", record.cellLabel],
                            ["Mode", record.mode === "C" ? "Current clamp" : record.mode === "V" ? "Voltage clamp" : record.mode],
                            ["Cycles", formatNumber(record.cycles, 0)],
                            ["Screen", record.accepted ? "Accepted" : "Below threshold"]
                        ])}
                    </dl>
                </section>
                <section class="info-section">
                    <h2>Conductance Summary</h2>
                    <div class="meters">
                        ${meter("Phase 0", p.G_exc_ph0, p.G_inh_ph0)}
                        ${meter("Stationary", p.G_exc_st, p.G_inh_st)}
                        ${meter("Transient", p.G_exc_tr, p.G_inh_tr)}
                    </div>
                </section>
                <section class="info-section">
                    <h2>Geometry</h2>
                    <dl class="kv-list">
                        ${kvRows([
                            ["Ei", `${formatNumber(p.Ei)} mV`],
                            ["Ee", `${formatNumber(p.Ee)} mV`],
                            ["E leak", `${formatNumber(p.E)} mV`],
                            ["g leak", formatNumber(p.g)],
                            ["V range", `${formatNumber(p.Vmin)} to ${formatNumber(p.Vmax)} mV`]
                        ])}
                    </dl>
                </section>
                <section class="info-section">
                    <h2>Files</h2>
                    <dl class="kv-list">
                        ${kvRows([
                            ["Image", record.full],
                            ["Thumb", record.thumb],
                            ["Params", record.par]
                        ])}
                    </dl>
                </section>
            `;
        }

        function renderSelection() {
            const record = selectedRecord();
            if (!record) {
                els.selectedName.textContent = "No recording selected";
                els.selectedSubtitle.textContent = "Choose a recording from the browser";
                els.imageStage.innerHTML = `
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v14H4z"></path><path d="M8 9h8"></path><path d="M8 13h5"></path></svg>
                        <span>No recording selected</span>
                    </div>
                `;
                els.openImageLink.href = "#";
                renderInspector(null);
                return;
            }

            els.selectedName.textContent = record.basename;
            els.selectedSubtitle.textContent = `${record.category} / ${record.mode === "C" ? "current clamp" : "voltage clamp"} / ${record.accepted ? "accepted" : "below cycle threshold"}`;
            els.imageStage.innerHTML = `<img id="mainImage" src="${escapeHtml(record.full)}" alt="Analysis snapshot for ${escapeHtml(record.basename)}">`;
            const image = document.getElementById("mainImage");
            image.style.transform = `scale(${state.zoom})`;
            els.openImageLink.href = record.full;
            renderInspector(record);
        }

        function moveSelection(delta) {
            if (!state.filtered.length) {
                return;
            }
            const index = state.filtered.findIndex((record) => record.id === state.selectedId);
            const nextIndex = (index + delta + state.filtered.length) % state.filtered.length;
            state.selectedId = state.filtered[nextIndex].id;
            state.zoom = 1;
            render();
        }

        function setZoom(nextZoom) {
            state.zoom = Math.max(0.55, Math.min(2.4, nextZoom));
            const image = document.getElementById("mainImage");
            if (image) {
                image.style.transform = `scale(${state.zoom})`;
            }
        }

        function render() {
            renderSummary();
            renderPopulationFilters();
            renderRecordList();
            renderSelection();
        }

        document.querySelectorAll("[data-mode]").forEach((button) => {
            button.addEventListener("click", () => {
                state.mode = button.dataset.mode;
                document.querySelectorAll("[data-mode]").forEach((modeButton) => {
                    modeButton.classList.toggle("is-active", modeButton.dataset.mode === state.mode);
                });
                render();
            });
        });

        els.searchInput.addEventListener("input", () => {
            state.search = els.searchInput.value;
            render();
        });

        els.prevButton.addEventListener("click", () => moveSelection(-1));
        els.nextButton.addEventListener("click", () => moveSelection(1));
        els.zoomOutButton.addEventListener("click", () => setZoom(state.zoom - 0.15));
        els.zoomInButton.addEventListener("click", () => setZoom(state.zoom + 0.15));
        els.fitButton.addEventListener("click", () => setZoom(1));

        document.addEventListener("keydown", (event) => {
            if (event.target && event.target.tagName === "INPUT") {
                return;
            }
            if (event.key === "ArrowUp" || event.key === "ArrowLeft") {
                event.preventDefault();
                moveSelection(-1);
            }
            if (event.key === "ArrowDown" || event.key === "ArrowRight") {
                event.preventDefault();
                moveSelection(1);
            }
            if (event.key === "+" || event.key === "=") {
                setZoom(state.zoom + 0.15);
            }
            if (event.key === "-") {
                setZoom(state.zoom - 0.15);
            }
            if (event.key === "0") {
                setZoom(1);
            }
        });

        render();
    </script>
</body>
</html>
"""


def generate_report(target_dir=WEB_DIR):
    save_dir = target_dir
    scan_dir, asset_prefix = resolve_recordings_dir(target_dir)

    print(f"Generating analysis dashboard. Scanning {scan_dir}, saving to {save_dir}...")

    dashboard_data = build_dashboard_data(scan_dir, asset_prefix)
    data_json = json.dumps(dashboard_data, separators=(",", ":"), sort_keys=True)
    rendered = DASHBOARD_HTML.replace("__DASHBOARD_DATA__", html_lib.escape(data_json, quote=False))

    index_path = os.path.join(save_dir, "dashboard.html")
    with open(index_path, "w", encoding="utf-8") as handle:
        handle.write(rendered)

    print(f"Interactive dashboard generated at: {index_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate interactive dashboard.")
    parser.add_argument("--outdir", type=str, default=WEB_DIR, help="Web directory containing assets/recordings")
    args = parser.parse_args()

    generate_report(args.outdir)


if __name__ == "__main__":
    main()
