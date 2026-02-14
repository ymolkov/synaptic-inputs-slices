#!/usr/bin/env python3
import os
import re
import glob
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
INDEX_HTML = os.path.join(RESULTS_DIR, "index.html")

def get_category(basename):
    match = re.match(r"^([a-zA-Z0-9]+-[a-zA-Z0-9]+)", basename)
    if match:
        return match.group(1)
    return "Miscellaneous"

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

def generate_report():
    print("Generating high-res PNG dashboard...")
    
    thumb_files = sorted(glob.glob(os.path.join(RESULTS_DIR, "*_thumb.png")))
    categories = defaultdict(lambda: defaultdict(list))
    
    for thumb_path in thumb_files:
        basename = os.path.basename(thumb_path).replace("_thumb.png", "")
        
        cat = get_category(basename)
        cell_match = re.match(r"^(.+)-[CV]", basename)
        cell_id = cell_match.group(1) if cell_match else basename
        
        categories[cat][cell_id].append({
            'basename': basename,
            'full': f"{basename}_full.png",
            'thumb': f"{basename}_thumb.png",
            'type': 'V' if '-V' in basename else 'C'
        })

    html = ["""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Analysis Dashboard</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: -apple-system, system-ui, sans-serif; background: #f0f2f5; margin: 0; padding: 0; display: flex; height: 100vh; overflow: hidden; }
        
        .sidebar { width: 180px; background: #fff; border-right: 1px solid #ddd; padding: 15px; overflow-y: auto; flex-shrink: 0; }
        .gallery { flex: 1; min-width: 400px; padding: 20px; overflow-y: auto; background: #f8f9fa; }
        .preview { width: 45%; min-width: 400px; background: #fff; border-left: 1px solid #ddd; display: flex; align-items: center; justify-content: center; overflow: hidden; position: relative; }
        
        .cat-group { margin-bottom: 30px; }
        .group-header { background: #2c3e50; color: white; padding: 8px 12px; font-weight: bold; font-size: 0.9em; border-radius: 6px; margin-bottom: 15px; }
        
        .tile-grid { display: flex; flex-wrap: wrap; gap: 12px; }
        .cell-tile { background: white; border-radius: 6px; padding: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid #eee; display: inline-flex; flex-direction: column; min-width: 100px; }
        .cell-tile:hover { border-color: #3498db; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        
        .cell-id { font-weight: bold; font-size: 0.75em; color: #2c3e50; margin-bottom: 6px; text-align: center; border-bottom: 1px solid #f0f0f0; padding-bottom: 4px; }
        
        .thumbs { display: flex; gap: 6px; justify-content: center; }
        .thumb-btn { position: relative; cursor: pointer; border: 2px solid #eee; border-radius: 4px; overflow: hidden; background: white; padding: 0; width: 100px; flex-shrink: 0; }
        .thumb-btn:hover { border-color: #bdc3c7; }
        .thumb-btn img { width: 100%; height: auto; display: block; }
        .thumb-btn.active { border-color: #3498db; box-shadow: 0 0 5px rgba(52,152,219,0.3); }
        
        .label { position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0,0,0,0.7); color: white; font-size: 8px; padding: 1px; text-align: center; pointer-events: none; }
        .type-c { border-bottom: 3px solid #0288d1; }
        .type-v { border-bottom: 3px solid #f57c00; }
        
        .preview-img { max-width: 100%; max-height: 100%; object-fit: contain; padding: 10px; }
        .preview-placeholder { color: #999; font-style: italic; }
        
        .nav-link { display: block; padding: 6px 10px; font-size: 0.8em; color: #34495e; text-decoration: none; border-radius: 4px; margin-bottom: 2px; }
        .nav-link:hover { background: #ecf0f1; color: #2980b9; }
        h4 { margin: 0 0 10px 0; font-size: 0.9em; color: #7f8c8d; text-transform: uppercase; letter-spacing: 0.5px; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h4>Populations</h4>
"""]

    sorted_cats = sorted(categories.keys())
    for cat in sorted_cats:
        html.append(f'<a href="#{cat}" class="nav-link">{cat}</a>')
    
    html.append('</div><div class="gallery">')

    for cat in sorted_cats:
        html.append(f'<div id="{cat}" class="cat-group"><div class="group-header">{cat}</div>')
        html.append('<div class="tile-grid">')
        
        sorted_cells = sorted(categories[cat].keys(), key=natural_sort_key)
        for cell_id in sorted_cells:
            html.append(f'<div class="cell-tile">')
            html.append(f'<div class="cell-id">{cell_id}</div>')
            html.append('<div class="thumbs">')
            
            recordings = sorted(categories[cat][cell_id], key=lambda x: x['basename'])
            for rec in recordings:
                type_class = "type-c" if rec['type'] == 'C' else "type-v"
                suffix = rec['basename'].split('-')[-1]
                html.append(f"""
                    <button class="thumb-btn" onclick="showImg('{rec['full']}', this)">
                        <img src="{rec['thumb']}" class="{type_class}">
                        <div class="label">{suffix}</div>
                    </button>
                """)
            html.append('</div></div>')
        html.append('</div></div>')

    html.append("""
    </div>
    <div class="preview" id="preview-pane">
        <div class="preview-placeholder">Select a recording to preview</div>
    </div>

    <script>
        function showImg(url, btn) {
            document.querySelectorAll('.thumb-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const pane = document.getElementById('preview-pane');
            pane.innerHTML = `<img src="${url}" class="preview-img">`;
        }
        
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const id = link.getAttribute('href').substring(1);
                const el = document.getElementById(id);
                if (el) el.scrollIntoView({ behavior: 'smooth' });
            });
        });
    </script>
</body>
</html>
""")

    with open(INDEX_HTML, 'w') as f:
        f.write("\n".join(html))
    
    print(f"Interactive high-res PNG dashboard generated at: {INDEX_HTML}")

if __name__ == "__main__":
    generate_report()
