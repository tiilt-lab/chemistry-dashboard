import mysql.connector, json, numpy as np, os
from scipy.stats import mannwhitneyu
from openai import OpenAI

# Load API key from server/.env
from dotenv import load_dotenv
load_dotenv('/home/ubuntu/chemistry-dashboard/server/.env')
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

DEVICES = [26,27,32,33,34,35,43,46,47,48]
DIMS = ['climate','communication','compatibility','contribution','constructive','context','conflict']
RATERS = ['chenghong','david123','mw']  # Exclude A

conn = mysql.connector.connect(host='localhost', user='vagrant', password='vagrant', database='discussion_capture')
cur = conn.cursor()

cur.execute('SELECT session_device_id, analysis_summary FROM seven_cs_analysis WHERE session_device_id IN (%s)' % ','.join(str(d) for d in DEVICES))
llm_data = {}
for sdid, summary in cur.fetchall():
    s = json.loads(summary) if isinstance(summary, str) else summary
    llm_data[sdid] = s

cur.execute('SELECT expert_id, session_device_id, annotation_data FROM expert_7c_annotation')
human_data = {}
for eid, sdid, adata in cur.fetchall():
    a = json.loads(adata) if isinstance(adata, str) else adata
    human_data[(eid, sdid)] = a
conn.close()

def get_embedding(text):
    if not text or (isinstance(text, str) and text.strip() == ''):
        return None
    response = client.embeddings.create(model="text-embedding-3-large", input=text)
    return np.array(response.data[0].embedding)

def cosine_sim(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# Collect all texts and embed them
print("Collecting texts...")
texts = {}  # (rater_or_LLM, device, dim) -> analysis text
for (eid, sdid), adata in human_data.items():
    for dim in DIMS:
        if dim in adata:
            t = adata[dim].get('analysis', '')
            if t and t.strip():
                texts[(eid, sdid, dim)] = t

for sdid in DEVICES:
    for dim in DIMS:
        if dim in llm_data.get(sdid, {}):
            t = llm_data[sdid][dim].get('explanation', '')
            if t and t.strip():
                texts[('LLM', sdid, dim)] = t

print(f"Total texts to embed: {len(texts)}")

# Embed all
print("Embedding...")
embeddings = {}
all_texts = list(texts.items())
# Batch embed
batch_size = 50
for i in range(0, len(all_texts), batch_size):
    batch = all_texts[i:i+batch_size]
    batch_texts = [t[1] for t in batch]
    response = client.embeddings.create(model="text-embedding-3-large", input=batch_texts)
    for j, emb in enumerate(response.data):
        key = batch[j][0]
        embeddings[key] = np.array(emb.embedding)
    print(f"  Embedded {min(i+batch_size, len(all_texts))}/{len(all_texts)}")

# Compute similarities
hh_sims = []  # (device, dim, sim)
hl_sims = []

for sdid in DEVICES:
    for dim in DIMS:
        # Get human raters with embeddings for this unit
        h_raters = [r for r in RATERS if (r, sdid, dim) in embeddings]
        has_llm = ('LLM', sdid, dim) in embeddings

        # Human-human pairs
        for i in range(len(h_raters)):
            for j in range(i+1, len(h_raters)):
                sim = cosine_sim(embeddings[(h_raters[i], sdid, dim)],
                                 embeddings[(h_raters[j], sdid, dim)])
                hh_sims.append((sdid, dim, sim))

        # Human-LLM pairs
        if has_llm:
            for r in h_raters:
                sim = cosine_sim(embeddings[(r, sdid, dim)],
                                 embeddings[('LLM', sdid, dim)])
                hl_sims.append((sdid, dim, sim))

hh_vals = [s[2] for s in hh_sims]
hl_vals = [s[2] for s in hl_sims]

print(f"\nHuman-Human pairs: {len(hh_vals)}")
print(f"Human-LLM pairs: {len(hl_vals)}")

# Overall
u, p = mannwhitneyu(hh_vals, hl_vals, alternative='two-sided')
print(f"\nOverall:")
print(f"  HH: mean={np.mean(hh_vals):.3f}, SD={np.std(hh_vals,ddof=1):.3f}")
print(f"  HL: mean={np.mean(hl_vals):.3f}, SD={np.std(hl_vals,ddof=1):.3f}")
print(f"  Mann-Whitney U={u:.0f}, p={p:.4f}")

# Per dimension
print("\nPer dimension:")
for dim in DIMS:
    hh_d = [s[2] for s in hh_sims if s[1]==dim]
    hl_d = [s[2] for s in hl_sims if s[1]==dim]
    if hh_d and hl_d:
        u, p = mannwhitneyu(hh_d, hl_d, alternative='two-sided')
        print(f"  {dim}: HH={np.mean(hh_d):.3f} (SD={np.std(hh_d,ddof=1):.3f}, n={len(hh_d)}), HL={np.mean(hl_d):.3f} (SD={np.std(hl_d,ddof=1):.3f}, n={len(hl_d)}), U={u:.0f}, p={p:.4f}")
