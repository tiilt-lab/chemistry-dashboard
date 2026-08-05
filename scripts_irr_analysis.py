import mysql.connector, json, numpy as np
from scipy.stats import spearmanr, rankdata
import krippendorff

np.random.seed(42)

conn = mysql.connector.connect(host='localhost', user='vagrant', password='vagrant', database='discussion_capture')
cur = conn.cursor()

DEVICES = [26,27,32,33,34,35,43,46,47,48]
DIMS = ['climate','communication','compatibility','contribution','constructive','context','conflict']
RATERS = ['A','chenghong','david123','mw']

# Load LLM
cur.execute('SELECT session_device_id, analysis_summary FROM seven_cs_analysis WHERE session_device_id IN (%s)' % ','.join(str(d) for d in DEVICES))
llm = {}
for sdid, summary in cur.fetchall():
    s = json.loads(summary) if isinstance(summary, str) else summary
    for d in s:
        if isinstance(s[d], dict) and 'score' in s[d]:
            try: llm.setdefault(sdid, {})[d.lower()] = float(s[d]['score'])
            except: pass

# Load human
cur.execute('SELECT expert_id, session_device_id, annotation_data FROM expert_7c_annotation')
scores = {}  # rater -> device -> dim -> score
for eid, sdid, adata in cur.fetchall():
    adata = json.loads(adata) if isinstance(adata, str) else adata
    for dim in DIMS:
        if dim in adata:
            try: scores.setdefault(eid, {}).setdefault(sdid, {})[dim] = float(adata[dim]['score'])
            except: pass
conn.close()

# Verify data
total_annotations = sum(1 for r in RATERS for d in DEVICES if d in scores.get(r, {}))
print(f"Verified: {len(RATERS)} raters, {len(DEVICES)} devices, {total_annotations} annotations")
for r in RATERS:
    devs = sorted([d for d in DEVICES if d in scores.get(r, {})])
    print(f"  {r}: {len(devs)} devices -> {devs}")

##############################################
# Helper functions
##############################################
def build_matrix(rater_list, devices, dim, score_source):
    """Build reliability matrix. score_source: dict rater->device->dim->score"""
    mat = []
    for r in rater_list:
        row = []
        for sdid in devices:
            if sdid in score_source.get(r, {}) and dim in score_source.get(r, {}).get(sdid, {}):
                row.append(score_source[r][sdid][dim])
            else:
                row.append(np.nan)
        mat.append(row)
    return np.array(mat)

def add_llm_row(mat, devices, dim):
    llm_row = []
    for sdid in devices:
        if sdid in llm and dim in llm[sdid]:
            llm_row.append(llm[sdid][dim])
        else:
            llm_row.append(np.nan)
    return np.vstack([mat, [llm_row]])

def bootstrap_alpha(mat, level='interval', n_boot=10000):
    n_units = mat.shape[1]
    alphas = []
    for _ in range(n_boot):
        idx = np.random.choice(n_units, n_units, replace=True)
        sample = mat[:, idx]
        try:
            a = krippendorff.alpha(reliability_data=sample, level_of_measurement=level)
            alphas.append(a)
        except: pass
    return np.percentile(alphas, 2.5), np.percentile(alphas, 97.5)

def compute_alpha_section(rater_list, devices, dims, score_source, level, label, llm_source=None):
    """Compute per-dimension and overall alpha with bootstrap CIs."""
    print(f"\n=== {label} ===")
    all_mats = []
    for dim in dims:
        mat = build_matrix(rater_list, devices, dim, score_source)
        if llm_source is not None:
            # Add LLM row from llm_source
            llm_row = []
            for sdid in devices:
                if sdid in llm_source and dim in llm_source[sdid]:
                    llm_row.append(llm_source[sdid][dim])
                else:
                    llm_row.append(np.nan)
            mat = np.vstack([mat, [llm_row]])
        a = krippendorff.alpha(reliability_data=mat, level_of_measurement=level)
        lo, hi = bootstrap_alpha(mat, level=level)
        print(f"  {dim}: α = {a:.3f}, 95% CI [{lo:.3f}, {hi:.3f}]")
        all_mats.append(mat)
    # Overall
    overall_mat = np.hstack(all_mats)
    a = krippendorff.alpha(reliability_data=overall_mat, level_of_measurement=level)
    lo, hi = bootstrap_alpha(overall_mat, level=level)
    print(f"  Overall: α = {a:.3f}, 95% CI [{lo:.3f}, {hi:.3f}]")

##############################################
# 1. Krippendorff's α human-only (raw, interval)
##############################################
np.random.seed(42)
compute_alpha_section(RATERS, DEVICES, DIMS, scores, 'interval',
    "1. Krippendorff's Alpha (Human Only, raw, interval)")

##############################################
# 2. Krippendorff's α human+LLM (raw, interval)
##############################################
# Build LLM as a "rater" in scores format
llm_as_rater = {}
for sdid in DEVICES:
    if sdid in llm:
        llm_as_rater[sdid] = llm[sdid]

np.random.seed(42)
compute_alpha_section(RATERS, DEVICES, DIMS, scores, 'interval',
    "2. Krippendorff's Alpha (Human+LLM, raw, interval)", llm_source=llm)

##############################################
# 3. Spearman's ρ (human mean vs LLM)
##############################################
print("\n=== 3. Spearman's ρ (Human Mean vs LLM) ===")
all_h, all_l = [], []
for dim in DIMS:
    h_vals, l_vals = [], []
    for sdid in DEVICES:
        hscores = [scores[r][sdid][dim] for r in RATERS if sdid in scores.get(r, {}) and dim in scores.get(r, {}).get(sdid, {})]
        if hscores and sdid in llm and dim in llm[sdid]:
            h_vals.append(np.mean(hscores))
            l_vals.append(llm[sdid][dim])
    all_h.extend(h_vals); all_l.extend(l_vals)
    rho, p = spearmanr(h_vals, l_vals)
    print(f"  {dim}: ρ = {rho:.3f}, p = {p:.4f} (n={len(h_vals)})")
rho, p = spearmanr(all_h, all_l)
print(f"  Overall: ρ = {rho:.3f}, p = {p:.6f} (n={len(all_h)})")

##############################################
# 4. MAD Human vs LLM
##############################################
print("\n=== 4. MAD Human vs LLM ===")
overall_hl = []
for dim in DIMS:
    vals = []
    for sdid in DEVICES:
        hscores = [scores[r][sdid][dim] for r in RATERS if sdid in scores.get(r, {}) and dim in scores.get(r, {}).get(sdid, {})]
        if hscores and sdid in llm and dim in llm[sdid]:
            for hs in hscores:
                vals.append(abs(hs - llm[sdid][dim]))
    overall_hl.extend(vals)
    print(f"  {dim}: {np.mean(vals):.2f}")
print(f"  Overall: {np.mean(overall_hl):.2f}")

##############################################
# 5. MAD Human vs Human
##############################################
print("\n=== 5. MAD Human vs Human ===")
overall_hh = []
for dim in DIMS:
    vals = []
    for sdid in DEVICES:
        hscores = [scores[r][sdid][dim] for r in RATERS if sdid in scores.get(r, {}) and dim in scores.get(r, {}).get(sdid, {})]
        if len(hscores) >= 2:
            for i in range(len(hscores)):
                for j in range(i+1, len(hscores)):
                    vals.append(abs(hscores[i] - hscores[j]))
    overall_hh.extend(vals)
    print(f"  {dim}: {np.mean(vals):.2f}")
print(f"  Overall: {np.mean(overall_hh):.2f}")

##############################################
# 6. Descriptive Statistics
##############################################
print("\n=== 6. Descriptive Statistics ===")
print("Human scores:")
for dim in DIMS:
    vals = [scores[r][sdid][dim] for r in RATERS for sdid in DEVICES if sdid in scores.get(r, {}) and dim in scores.get(r, {}).get(sdid, {})]
    print(f"  {dim}: mean = {np.mean(vals):.2f}, SD = {np.std(vals, ddof=1):.2f} (n={len(vals)})")
print("LLM scores:")
for dim in DIMS:
    vals = [llm[sdid][dim] for sdid in DEVICES if sdid in llm and dim in llm[sdid]]
    print(f"  {dim}: mean = {np.mean(vals):.2f}, SD = {np.std(vals, ddof=1):.2f} (n={len(vals)})")

##############################################
# 7. Rank-based agreement (ordinal alpha)
##############################################
# Convert each rater's scores to within-rater ranks per dimension
rank_scores = {}
for r in RATERS:
    rank_scores[r] = {}
    for dim in DIMS:
        vals = [(sdid, scores[r][sdid][dim]) for sdid in DEVICES if sdid in scores.get(r, {}) and dim in scores.get(r, {}).get(sdid, {})]
        if vals:
            devs_r, scores_r = zip(*vals)
            ranks = rankdata(scores_r)
            for d, rank in zip(devs_r, ranks):
                rank_scores[r].setdefault(d, {})[dim] = rank

# LLM ranks per dimension
llm_rank = {}
for dim in DIMS:
    vals = [(sdid, llm[sdid][dim]) for sdid in DEVICES if sdid in llm and dim in llm[sdid]]
    if vals:
        devs_r, scores_r = zip(*vals)
        ranks = rankdata(scores_r)
        for d, rank in zip(devs_r, ranks):
            llm_rank.setdefault(d, {})[dim] = rank

np.random.seed(42)
compute_alpha_section(RATERS, DEVICES, DIMS, rank_scores, 'ordinal',
    "7a. Krippendorff's Alpha (Human Only, rank-based, ordinal)")

np.random.seed(42)
compute_alpha_section(RATERS, DEVICES, DIMS, rank_scores, 'ordinal',
    "7b. Krippendorff's Alpha (Human+LLM, rank-based, ordinal)", llm_source=llm_rank)

##############################################
# 8. Z-score normalized (interval alpha)
##############################################
# Z-score each rater per dimension
zscore_scores = {}
for r in RATERS:
    zscore_scores[r] = {}
    for dim in DIMS:
        vals = [(sdid, scores[r][sdid][dim]) for sdid in DEVICES if sdid in scores.get(r, {}) and dim in scores.get(r, {}).get(sdid, {})]
        if len(vals) >= 2:
            devs_r, scores_r = zip(*vals)
            m, s = np.mean(scores_r), np.std(scores_r, ddof=1)
            if s > 0:
                for d, v in zip(devs_r, scores_r):
                    zscore_scores[r].setdefault(d, {})[dim] = (v - m) / s

# LLM z-scores per dimension
llm_zscore = {}
for dim in DIMS:
    vals = [(sdid, llm[sdid][dim]) for sdid in DEVICES if sdid in llm and dim in llm[sdid]]
    if len(vals) >= 2:
        devs_r, scores_r = zip(*vals)
        m, s = np.mean(scores_r), np.std(scores_r, ddof=1)
        if s > 0:
            for d, v in zip(devs_r, scores_r):
                llm_zscore.setdefault(d, {})[dim] = (v - m) / s

np.random.seed(42)
compute_alpha_section(RATERS, DEVICES, DIMS, zscore_scores, 'interval',
    "8a. Krippendorff's Alpha (Human Only, z-score normalized, interval)")

np.random.seed(42)
compute_alpha_section(RATERS, DEVICES, DIMS, zscore_scores, 'interval',
    "8b. Krippendorff's Alpha (Human+LLM, z-score normalized, interval)", llm_source=llm_zscore)

print("\n=== DONE ===")
