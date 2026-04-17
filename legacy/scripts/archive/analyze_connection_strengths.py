import csv
import math

class Statistics:
    def __init__(self):
        self.values = []
    
    def add(self, val):
        self.values.append(val)
        
    def mean(self):
        if not self.values: return 0.0
        return sum(self.values) / len(self.values)
        
    def sem(self):
        if len(self.values) < 2: return 0.0
        m = self.mean()
        variance = sum((x - m) ** 2 for x in self.values) / (len(self.values) - 1)
        return math.sqrt(variance) / math.sqrt(len(self.values))

# Data buckets
groups = {
    'VGAT-I': {'Gi_tr': Statistics(), 'Gi_st': Statistics(), 'Ge_tr': Statistics(), 'Ge_st': Statistics()},
    'VgluT2-I': {'Gi_tr': Statistics(), 'Gi_st': Statistics(), 'Ge_tr': Statistics(), 'Ge_st': Statistics()},
    'VGAT-E': {'Gi_tr': Statistics(), 'Gi_st': Statistics(), 'Ge_tr': Statistics(), 'Ge_st': Statistics()}
}

# Source mapping definitions
source_map = {
    'Gi_tr': 'VGAT-I (Inh, Insp)',
    'Gi_st': 'VGAT-E (Inh, Exp)',
    'Ge_tr': 'VgluT2-I (Exc, Insp)',
    'Ge_st': 'Unknown (Exc, Exp)' # User says this is negligible
}

try:
    with open('/Users/ymolkov/clamp/results/conductance_summary.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cell_id = row['Cell_ID']
            
            # Determine group
            group_name = None
            if cell_id.startswith('VGAT-I'): group_name = 'VGAT-I'
            elif cell_id.startswith('VgluT2-I'): group_name = 'VgluT2-I'
            elif cell_id.startswith('VGAT-E'): group_name = 'VGAT-E'
            
            if group_name:
                # Extract values, clip negative to 0
                try:
                    gi_tr = max(0, float(row['G_inh_tr']))
                    gi_st = max(0, float(row['G_inh_st']))
                    ge_tr = max(0, float(row['G_exc_tr']))
                    ge_st = max(0, float(row['G_exc_st']))
                    
                    groups[group_name]['Gi_tr'].add(gi_tr)
                    groups[group_name]['Gi_st'].add(gi_st)
                    groups[group_name]['Ge_tr'].add(ge_tr)
                    groups[group_name]['Ge_st'].add(ge_st)
                except ValueError:
                    continue

    print(f"{'Target Population':<18} | {'Source (Input)':<25} | {'Metric':<8} | {'Mean +/- SEM':<20} | {'Rank'}")
    print("-" * 105)

    for group_name in ['VGAT-I', 'VgluT2-I', 'VGAT-E']:
        stats = groups[group_name]
        
        # Calculate means for sorting
        means = []
        # We only care about the main identified sources for ranking: Gi_tr, Gi_st, Ge_tr
        # But let's check Ge_st just to confirm it's negligible as user said
        
        metrics_to_rank = ['Gi_tr', 'Gi_st', 'Ge_tr', 'Ge_st']
        
        for metric in metrics_to_rank:
            stat_obj = stats[metric]
            means.append({
                'metric': metric,
                'mean': stat_obj.mean(),
                'sem': stat_obj.sem(),
                'desc': source_map[metric]
            })
        
        # Sort by mean descending
        means.sort(key=lambda x: x['mean'], reverse=True)
        
        ranks = ['Strong', 'Moderate', 'Weak']
        
        for i, item in enumerate(means):
            rank_label = ranks[i] if i < 3 else 'Weak'
            print(f"{group_name:<18} | {item['desc']:<25} | {item['metric']:<8} | {item['mean']:.4f} +/- {item['sem']:.4f} | {rank_label}")
        print("-" * 105)

except Exception as e:
    print(f"Error: {e}")
