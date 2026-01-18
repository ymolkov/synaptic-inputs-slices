import re
import os
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
MAKEFILE = os.path.join(PROJECT_ROOT, "legacy", "Makefile.orig")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
INDEX_HTML = os.path.join(RESULTS_DIR, "index.html")

def parse_html_targets(content):
    targets = {}
    pattern = re.compile(r"^([\w\.-]+\.html):\s+(.*)$", re.MULTILINE)
    matches = pattern.findall(content)
    
    for target, deps_str in matches:
        deps = deps_str.strip().split()
        targets[target] = deps
    return targets

def group_cells(file_list):
    # Group by Cell ID
    # Pattern: (Type-Region-Cell\d+)
    # Example: VGAT-E-Cell1-C -> VGAT-E-Cell1
    groups = defaultdict(list)
    
    for fname in file_list:
        match = re.match(r"^([a-zA-Z0-9]+-[a-zA-Z0-9]+-Cell\d+)", fname)
        if match:
            cell_id = match.group(1)
            groups[cell_id].append(fname)
        else:
            # Fallback for unexpected naming
            groups["Misc"].append(fname)
            
    return groups

def generate_sub_table(title, cells_files):
    # Create a nested table for this category
    html = "<td style='vertical-align:top'>\n"
    html += "<table border='0' width='100%'>\n"
    # Header removed per user request
    
    # Group files by Cell ID
    grouped = group_cells(cells_files)
    
    # Sort Cell IDs naturally (numerically if possible)
    # Cell1, Cell2, Cell10...
    def sort_key(cid):
        # Extract number if possible
        m = re.search(r"Cell(\d+)", cid)
        if m:
            return int(m.group(1))
        return cid
        
    sorted_ids = sorted(grouped.keys(), key=sort_key)
    
    for cell_id in sorted_ids:
        files = grouped[cell_id]
        
        # Split into C and V lists
        c_files = []
        v_files = []
        others = []
        
        for f in files:
            # Check for -C or -V. Note: suffixes like -C-1 exist.
            if "-C" in f:
                c_files.append(f)
            elif "-V" in f:
                v_files.append(f)
            else:
                others.append(f)
                
        # Sort files within C and V (e.g. C-1, C-2)
        c_files.sort()
        v_files.sort()
        others.sort()
        
        # Build Row
        html += "<tr>\n"
        html += "<td style='white-space: nowrap; border-bottom: 1px solid #eee'>\n"
        
        # Display all files for this cell horizontally
        for f in c_files + v_files + others:
            html += f"<div style='display:inline-block; margin:10px; text-align:center; vertical-align:top'>"
            html += f"<a href='{f}.pdf'><img src='{f}.png' title='{f}' width='256' style='border:1px solid #ddd'></a>"
            html += f"<br><span style='font-size:10px'>{f}</span>"
            html += "</div>"
            
        html += "</td>\n"
        html += "</tr>\n"
        
    html += "</table>\n"
    html += "</td>\n"
    return html

def main():
    if not os.path.exists(MAKEFILE):
        print("Makefile not found.")
        return

    with open(MAKEFILE, 'r') as f:
        content = f.read()
        
    targets = parse_html_targets(content)
    
    if "index.html" not in targets:
        print("index.html target not found in Makefile.")
        return
        
    # The dependencies of index.html are the columns (e.g. VgluT2-I.html)
    columns = targets["index.html"]
    
    # Start building index.html
    html_content = "<html>\n<head><title>Analysis Results</title>\n"
    html_content += "<style>table { border-collapse: collapse; } th, td { padding: 5px; }</style>\n"
    html_content += "</head>\n<body>\n"
    html_content += "<table border='1'>\n"
    
    # Header Row
    html_content += "<tr>\n"
    for col_file in columns:
        # Title is basename without extension
        title = col_file.replace(".html", "")
        html_content += f"<th>{title}</th>\n"
    html_content += "</tr>\n"
    
    # Content Row
    html_content += "<tr valign='top'>\n"
    for col_file in columns:
        if col_file in targets:
            cells = targets[col_file]
            html_content += generate_sub_table(col_file, cells)
        else:
            html_content += "<td>(Missing data)</td>\n"
    html_content += "</tr>\n"
    
    html_content += "</table>\n</body>\n</html>"
    
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
        
    with open(INDEX_HTML, 'w') as f:
        f.write(html_content)
        
    print(f"Report generated at: {INDEX_HTML}")

if __name__ == "__main__":
    main()