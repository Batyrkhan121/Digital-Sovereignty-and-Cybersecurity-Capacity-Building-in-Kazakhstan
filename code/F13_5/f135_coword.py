"""Phase F13.5 - co-word analysis of E1 (the full Scopus export, 841 records): steps 1-5 of F12.3 with unchanged parameters.

Two runs: --v3 (step 1) applies F12.3c's thesaurus v3 as it is and writes T1/T3/T4/T5 of both layers and the numbers into
tables/v3_on_E1/ (not for publication; it separates the frame effect from the thesaurus effect); without it (step 4) applies
this phase's thesaurus v4 (tables/thesaurus.csv) and writes T1-T8, the figure with its data CSVs and F13_5_numbers.json.
Changed against F12.3c: (i) the input (E1 via f135_lib.load_records), T6 with three periods, T8 from E1's titles (bigrams of
two non-stop words, top 20 by records) against the top 20 author keywords; the thesaurus limit is 700.
Deterministic: sorted node and edge insertion, greedy modularity (no random seed involved), spring_layout seed 42, PDF written
without a creation date. Only keywords (at most 6 words in any table), title bigrams, counts and codes leave the program."""
import sys
sys.dont_write_bytecode = True

import json
import re
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f135_lib as L

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from networkx.algorithms.community import greedy_modularity_communities, modularity
import PIL
from PIL import Image

GENERIC = {"kazakhstan", "cybersecurity", "information security", "security"}
MAIN_T, SENS = 5, (3, 5, 8)
EDGE_MIN = 2
LABEL_MIN = 8
SEED = 42
PERIODS = [("2003_2016", 2003, 2016), ("2017_2021", 2017, 2021), ("2022_2025", 2022, 2025)]
STOP = sorted(set("""i me my myself we our ours ourselves you your yours yourself yourselves he him his himself she her hers herself it
its itself they them their theirs themselves what which who whom this that these those am is are was were be been being have has had
having do does did doing a an the and but if or because as until while of at by for with about against between into through during
before after above below to from up down in out on off over under again further then once here there when where why how all any both
each few more most other some such no nor not only own same so than too very s t can will just don should now d ll m o re ve y ain
aren couldn didn doesn hadn hasn haven isn ma mightn mustn needn shan shouldn wasn weren won wouldn""".split()))
V3_MODE = "--v3" in sys.argv
T = L.V3E1 if V3_MODE else L.TABLES
NUMBERS = (L.V3E1 / "numbers_v3_on_E1.json") if V3_MODE else (L.OUT / "F13_5_numbers.json")
NUM = {"versions": {"python": sys.version.split()[0], "networkx": nx.__version__, "matplotlib": matplotlib.__version__,
                    "pillow": PIL.__version__},
       "run": "E1 x thesaurus v3 (F12.3c, as it is)" if V3_MODE else "E1 x thesaurus v4",
       "parameters": {"node_threshold": MAIN_T, "sensitivity_thresholds": list(SENS), "edge_min_records": EDGE_MIN,
                      "association_strength": "w_ij / (n_i * n_j)", "clustering": "networkx greedy_modularity_communities, "
                      "weight = association strength, resolution 1.0, generic keywords excluded", "layout": f"spring_layout seed={SEED}, "
                      "weight = co-occurrence records", "label_min_records": LABEL_MIN, "generic": sorted(GENERIC)}}

# ---------- step 1: normalisation and thesaurus
TH_PATH = (L.PREV_T / "thesaurus.csv") if V3_MODE else (L.TABLES / "thesaurus.csv")
LIMIT = 650 if V3_MODE else 700
thes = L.read_csv_path(TH_PATH)
assert len(thes) <= LIMIT, len(thes)
TH = {}
for r in thes:
    f, t = L.norm_kw(r["from"]), L.norm_kw(r["to"])
    assert f == r["from"] and t == r["to"], ("thesaurus not in normal form", r)
    assert f not in TH, ("duplicate from", f)
    TH[f] = t
assert not (set(TH.values()) & set(TH)), "a 'to' is also a 'from' (chain)"


def canon(k):
    k = L.norm_kw(k)
    return TH.get(k, k)


recs = L.load_records(titles=not V3_MODE)
A = {e: {canon(k) for k in r["ak"]} - {""} for e, r in recs.items()}
I = {e: {canon(k) for k in r["ik"]} - {""} for e, r in recs.items()}
YEAR = {e: r["year"] for e, r in recs.items()}
applied = Counter()
for r in recs.values():
    for k in r["ak"] + r["ik"]:
        if L.norm_kw(k) in TH:
            applied[L.norm_kw(k)] += 1
L.write_csv(T / "thesaurus_applied.csv", ["from", "to", "keyword_occurrences_rewritten"],
            [{"from": f, "to": TH[f], "keyword_occurrences_rewritten": applied.get(f, 0)} for f in sorted(TH)])
NUM["records_E1"] = len(recs)
NUM["thesaurus_rows"] = len(TH)
NUM["thesaurus_rows_applied"] = sum(1 for f in TH if applied.get(f))


def analyse(kind, sets, label):
    recs_kw = {s: ks for s, ks in sets.items() if ks}
    n_rec = len(recs_kw)
    freq = Counter()
    for ks in recs_kw.values():
        freq.update(ks)
    allrank = [(i + 1, k, n) for i, (k, n) in enumerate(sorted(freq.items(), key=lambda kv: (-kv[1], kv[0])))]
    long_kw = [(r, k, n) for r, k, n in allrank if len(k.split()) > 6]
    rows = [{"rank": r, "keyword": k, "records": n, "pct_of_records_with_keywords": L.pct(n, n_rec), "generic": int(k in GENERIC)}
            for r, k, n in allrank if len(k.split()) <= 6]
    f = ["rank", "keyword", "records", "pct_of_records_with_keywords", "generic"]
    L.write_csv(T / f"T1_{kind}_frequencies.csv", f, rows)
    L.write_md(T / f"T1_{kind}_frequencies_top50.md", f"T1 ({label}). Keyword frequencies, top 50 of {len(freq)} (records with keywords: {n_rec})",
               f, rows[:50], f"Source: E1 (full Scopus export, {len(recs)} records); the normalisation and thesaurus of step 1 ({NUM['run']}). "
               f"The full list is in the CSV; {len(long_kw)} keywords of more than 6 words (records each: "
               f"{max((n for _, _, n in long_kw), default=0)} at most) are counted but not printed; their ranks are skipped.")
    long_kw = len(long_kw)

    def build(thr, with_generic=True):
        nodes = sorted(k for k, n in freq.items() if n >= thr and (with_generic or k not in GENERIC))
        ns = set(nodes)
        co = Counter()
        for ks in recs_kw.values():
            kk = sorted(ks & ns)
            for i in range(len(kk)):
                for j in range(i + 1, len(kk)):
                    co[(kk[i], kk[j])] += 1
        edges = sorted((a, b, w) for (a, b), w in co.items() if w >= EDGE_MIN)
        G = nx.Graph()
        for k in nodes:
            G.add_node(k, records=freq[k])
        for a, b, w in edges:
            G.add_edge(a, b, weight=w, assoc=w / (freq[a] * freq[b]))
        return G

    sens = []
    for thr in SENS:
        g1, g0 = build(thr, True), build(thr, False)
        sens.append({"threshold_records": thr, "nodes_with_generic": g1.number_of_nodes(), "edges_with_generic": g1.number_of_edges(),
                     "nodes_without_generic": g0.number_of_nodes(), "edges_without_generic": g0.number_of_edges()})
    if not V3_MODE:
        f = ["threshold_records", "nodes_with_generic", "edges_with_generic", "nodes_without_generic", "edges_without_generic"]
        L.write_csv(T / f"T2_{kind}_threshold_sensitivity.csv", f, sens)
        L.write_md(T / f"T2_{kind}_threshold_sensitivity.md", f"T2 ({label}). Nodes and edges by node threshold", f, sens,
                   f"Edges: co-occurrence in at least {EDGE_MIN} records. Main threshold: {MAIN_T} records.")

    G = build(MAIN_T, True)
    Gc = build(MAIN_T, False)
    comms = greedy_modularity_communities(Gc, weight="assoc", resolution=1.0)
    comms = sorted((sorted(c) for c in comms), key=lambda c: (-sum(freq[k] for k in c), c[0]))
    cl = {k: i + 1 for i, c in enumerate(comms) for k in c}
    q = modularity(Gc, [set(c) for c in comms], weight="assoc", resolution=1.0) if Gc.number_of_edges() else 0.0
    gw = greedy_modularity_communities(G, weight="assoc", resolution=1.0)
    qw = modularity(G, gw, weight="assoc", resolution=1.0) if G.number_of_edges() else 0.0
    gen_comm = {k: next(i for i, c in enumerate(sorted((sorted(c) for c in gw), key=lambda c: (-sum(freq[x] for x in c), c[0])))
                        if k in c) + 1 for k in sorted(GENERIC & set(G.nodes))}
    nodes = [{"keyword": k, "records": freq[k], "degree": G.degree(k), "weighted_degree": int(G.degree(k, weight="weight")),
              "cluster": cl.get(k, ""), "generic": int(k in GENERIC)}
             for k in sorted(G.nodes, key=lambda k: (-freq[k], k))]
    f = ["keyword", "records", "degree", "weighted_degree", "cluster", "generic"]
    L.write_csv(T / f"T3_{kind}_nodes.csv", f, nodes)
    if not V3_MODE:
        L.write_md(T / f"T3_{kind}_nodes.md", f"T3 ({label}). Nodes with at least {MAIN_T} records", f, nodes,
                   "Degree and weighted degree (co-occurrence records) on the network with generic keywords; cluster from the network "
                   "without them (generic = 1: no cluster).")
    edges = [{"source": a, "target": b, "cooccurrence_records": d["weight"], "association_strength": f"{d['assoc']:.6f}",
              "in_clustering": int(a not in GENERIC and b not in GENERIC)}
             for a, b, d in sorted(G.edges(data=True), key=lambda e: (-e[2]["weight"], min(e[0], e[1]), max(e[0], e[1])))]
    edges = [{**e, "source": min(e["source"], e["target"]), "target": max(e["source"], e["target"])} for e in edges]
    f = ["source", "target", "cooccurrence_records", "association_strength", "in_clustering"]
    L.write_csv(T / f"T4_{kind}_edges.csv", f, edges)
    summ, top = [], []
    for i, c in enumerate(comms):
        ks = sorted(c, key=lambda k: (-freq[k], k))
        summ.append({"cluster": i + 1, "size": len(c), "total_records": sum(freq[k] for k in c), "largest_keyword": ks[0]})
        top += [{"cluster": i + 1, "rank": j + 1, "keyword": k, "records": freq[k]} for j, k in enumerate(ks[:10])]
    L.write_csv(T / f"T5_{kind}_clusters.csv", ["cluster", "size", "total_records", "largest_keyword"], summ)
    L.write_csv(T / f"T5_{kind}_cluster_top10.csv", ["cluster", "rank", "keyword", "records"], top)
    L.write_md(T / f"T5_{kind}_clusters.md", f"T5 ({label}). Clusters (greedy modularity on association strength, generic excluded)",
               ["cluster", "size", "total_records", "largest_keyword"], summ,
               f"Modularity without generic keywords: {q:.4f} ({len(comms)} clusters). Sensitivity with the generic keywords kept: "
               f"{len(gw)} clusters, modularity {qw:.4f}; generic keywords then fall in clusters {gen_comm}. Top 10 per cluster: "
               f"T5_{kind}_cluster_top10.csv.")
    NUM[kind] = {"records_with_keywords": n_rec, "unique_keywords": len(freq), "keywords_over_6_words": long_kw,
                 "nodes": G.number_of_nodes(), "edges": G.number_of_edges(), "nodes_clustered": Gc.number_of_nodes(),
                 "edges_clustered": Gc.number_of_edges(), "clusters": len(comms), "modularity": round(q, 4),
                 "clusters_with_generic": len(gw), "modularity_with_generic": round(qw, 4), "generic_in_clusters_when_kept": gen_comm,
                 "isolated_clustered_nodes": sum(1 for k in Gc.nodes if Gc.degree(k) == 0), "sensitivity": sens,
                 "min_records_in_T3": min((n["records"] for n in nodes), default=None)}
    return freq, n_rec, Gc, cl, comms


fa, na, Gc_a, cl_a, comms_a = analyse("author", A, "author keywords")
fi, ni, _, _, _ = analyse("index", I, "index keywords")

if V3_MODE:
    L.jdump(NUM, NUMBERS)
    for kind in ("author", "index"):
        print(kind, {k: v for k, v in NUM[kind].items() if k != "sensitivity"})
    raise SystemExit(0)

# ---------- step 3: periods (three)
withkw = {s for s, ks in A.items() if ks}
per = {name: [s for s in sorted(recs) if lo <= YEAR[s] <= hi] for name, lo, hi in PERIODS}
perk = {name: [s for s in ss if s in withkw] for name, ss in per.items()}
top30 = [k for k, n in sorted(fa.items(), key=lambda kv: (-kv[1], kv[0]))[:30]]
rows = []
for k in top30:
    r = {"keyword": k, "generic": int(k in GENERIC)}
    for name, _, _ in PERIODS:
        n = sum(1 for s in perk[name] if k in A[s])
        r[f"records_{name}"] = n
        r[f"pct_{name}"] = L.pct(n, len(perk[name]))
    rows.append(r)
f = ["keyword", "generic"] + [x for name, _, _ in PERIODS for x in (f"records_{name}", f"pct_{name}")]
L.write_csv(T / "T6_author_keywords_by_period.csv", f, rows)
L.write_md(T / "T6_author_keywords_by_period.md", "T6. Top 30 author keywords (whole frame) by period", f, rows,
           "Records with author keywords: " + "; ".join(f"{name.replace('_', '-')}: {len(perk[name])} (of {len(per[name])} frame records)"
                                                         for name, _, _ in PERIODS)
           + ". Shares use the records with author keywords of each period. No network by period.")
NUM["periods"] = {name: {"frame_records": len(per[name]), "with_author_kw": len(perk[name])} for name, _, _ in PERIODS}

# ---------- step 4: blind spots (groups and regular expressions of F12.3c)
PATTERNS = [
    ("SCADA", r"\bscada\b|supervisory control and data acquisition"),
    ("ICS / industrial control", r"\bics\b|industrial control"),
    ("OT / operational technology", r"\bot\b|operational technolog"),
    ("IIoT / industrial IoT", r"\biiot\b|industrial internet of things|industrial iot"),
    ("LLM / generative AI / ChatGPT", r"\bllms?\b|large language model|generative (ai|artificial intelligence|pre trained)|chatgpt|\bgpt\b"),
    ("agentic AI / AI agent", r"\bagentic\b|\bai agents?\b|artificial intelligence agents?"),
]
rows, hits = [], {}
for name, rx in PATTERNS:
    c = re.compile(rx)
    ra = {s for s, ks in A.items() if any(c.search(k) for k in ks)}
    ri = {s for s, ks in I.items() if any(c.search(k) for k in ks)}
    rows.append({"group": name, "regex": rx, "records_author_kw": len(ra), "records_index_kw": len(ri), "records_either": len(ra | ri)})
    hits[name] = sorted({k for ks in list(A.values()) + list(I.values()) for k in ks if c.search(k) and len(k.split()) <= 6})
f = ["group", "regex", "records_author_kw", "records_index_kw", "records_either"]
L.write_csv(T / "T7_blind_spots_keywords.csv", f, rows)
L.write_md(T / "T7_blind_spots_keywords.md", f"T7. Blind-spot groups in keywords (author + index, E1 n = {len(recs)})", f, rows,
           "Regular expressions (Python re.search) on each normalised keyword after the thesaurus; a record counts once per group. "
           "The matched keywords are listed in T7_blind_spots_matched_keywords.csv.")
L.write_csv(T / "T7_blind_spots_matched_keywords.csv", ["group", "keyword"], [{"group": g, "keyword": k} for g, ks in hits.items() for k in ks])
NUM["blind_spots"] = {r["group"]: r["records_either"] for r in rows}


# ---------- title bigrams of E1 against author keywords
def title_bigrams(title):
    """lowercase; hyphens and dashes to spaces; any other character outside [a-z0-9 ] ends a segment; bigrams of two adjacent
    non-stop words inside a segment; each bigram once per title."""
    t = str(title or "").lower()
    for h in L.HYPHENS:
        t = t.replace(h, " ")
    out = set()
    for seg in re.split(r"[^a-z0-9 ]+", t):
        toks = seg.split()
        for a, b in zip(toks, toks[1:]):
            if a not in STOP and b not in STOP:
                out.add(a + " " + b)
    return out


bg = Counter()
for r in recs.values():
    bg.update(title_bigrams(r["title"]))
ttop = sorted(bg.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
arank = {k: i + 1 for i, (k, n) in enumerate(sorted(fa.items(), key=lambda kv: (-kv[1], kv[0])))}
rows = []
for i, (b, n) in enumerate(ttop):
    k = canon(b)
    rows.append({"title_rank": i + 1, "title_bigram": b, "title_records": n, "as_keyword": k, "author_kw_records": fa.get(k, 0),
                 "author_kw_rank": arank.get(k, "")})
f = ["title_rank", "title_bigram", "title_records", "as_keyword", "author_kw_records", "author_kw_rank"]
L.write_csv(T / "T8_title_bigrams_vs_keywords.csv", f, rows)
tset = {canon(b) for b, _ in ttop}
rows2 = [{"author_kw_rank": arank[k], "keyword": k, "records": fa[k], "generic": int(k in GENERIC), "in_title_top20": int(k in tset)}
         for k in sorted(fa, key=lambda k: arank[k])[:20]]
f2 = ["author_kw_rank", "keyword", "records", "generic", "in_title_top20"]
L.write_csv(T / "T8b_keywords_vs_title_bigrams.csv", f2, rows2)
L.write_md(T / "T8_title_bigrams_vs_keywords.md", "T8. Title bigrams of E1 (top 20 by records) against author keywords", f, rows,
           f"Titles of E1 ({len(recs)} records): lowercase; hyphens and dashes to spaces; other punctuation ends a segment; bigrams of two "
           f"adjacent non-stop words inside a segment, counted once per title. Stop words ({len(STOP)}): {' '.join(STOP)}. as_keyword: "
           "the bigram under this phase's normalisation and thesaurus. Reverse view (author keywords top 20 against the title top 20): "
           "T8b_keywords_vs_title_bigrams.csv.")
NUM["title_bigrams"] = {"distinct": len(bg), "top20_in_author_top20": sum(1 for r in rows if r["author_kw_rank"] != "" and int(r["author_kw_rank"]) <= 20),
                        "top20_present_as_author_kw": sum(1 for r in rows if r["author_kw_records"]), "stop_words": len(STOP)}

# ---------- step 5: the figure (author keywords, nodes >= 5 records, generic keywords excluded, as clustered)
F = L.FIGURES
F.mkdir(parents=True, exist_ok=True)
pos = nx.spring_layout(Gc_a, seed=SEED, weight="weight")
cmap = plt.get_cmap("tab20")
ordered = sorted(Gc_a.nodes)
fig, ax = plt.subplots(figsize=(10, 8))
for a, b, d in sorted(Gc_a.edges(data=True), key=lambda e: (min(e[0], e[1]), max(e[0], e[1]))):
    ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color="#9a9a9a", alpha=0.35, linewidth=0.4 + 0.3 * d["weight"], zorder=1)
sizes = [30 * fa[k] for k in ordered]
colors = [cmap((cl_a[k] - 1) % 20) if len(comms_a[cl_a[k] - 1]) > 1 else "#bdbdbd" for k in ordered]
ax.scatter([pos[k][0] for k in ordered], [pos[k][1] for k in ordered], s=sizes, c=colors, edgecolors="white", linewidths=0.6, zorder=2)
for k in ordered:
    if fa[k] >= LABEL_MIN:
        ax.annotate(k, (pos[k][0], pos[k][1]), fontsize=7, ha="center", va="center", zorder=3)
ax.set_axis_off()
fig.tight_layout()
base = F / "Fig_coword_author_keywords"
fig.savefig(str(base) + ".pdf", metadata={"CreationDate": None, "ModDate": None, "Producer": None, "Creator": None})
fig.savefig(str(base) + ".png", dpi=300, metadata={"Software": None})
plt.close(fig)
with Image.open(str(base) + ".png") as im:
    im.convert("RGB").save(str(base) + ".tif", compression="tiff_lzw", dpi=(300, 300))
L.write_csv(F / "Fig_coword_author_keywords_nodes.csv", ["keyword", "records", "cluster", "x", "y", "labelled"],
            [{"keyword": k, "records": fa[k], "cluster": cl_a[k], "x": f"{pos[k][0]:.6f}", "y": f"{pos[k][1]:.6f}",
              "labelled": int(fa[k] >= LABEL_MIN)} for k in ordered])
L.write_csv(F / "Fig_coword_author_keywords_edges.csv", ["source", "target", "cooccurrence_records", "association_strength"],
            [{"source": min(a, b), "target": max(a, b), "cooccurrence_records": d["weight"], "association_strength": f"{d['assoc']:.6f}"}
             for a, b, d in sorted(Gc_a.edges(data=True), key=lambda e: (min(e[0], e[1]), max(e[0], e[1])))])
NUM["figure"] = {"nodes": Gc_a.number_of_nodes(), "edges": Gc_a.number_of_edges(), "labelled": sum(1 for k in ordered if fa[k] >= LABEL_MIN),
                 "generic_excluded": sorted(GENERIC & set(fa))}
L.jdump(NUM, NUMBERS)
print(json.dumps({k: NUM[k] for k in ("records_E1", "thesaurus_rows", "thesaurus_rows_applied", "periods", "blind_spots", "figure", "title_bigrams")},
                 ensure_ascii=False, indent=1))
for kind in ("author", "index"):
    print(kind, {k: v for k, v in NUM[kind].items() if k != "sensitivity"})
