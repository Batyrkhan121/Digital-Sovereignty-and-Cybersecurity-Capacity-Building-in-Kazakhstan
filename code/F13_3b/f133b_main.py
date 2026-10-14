"""Phase F13.3b - steps 1-7 on the work key (the main line now) and on title matching. Reads data/reference_keys.csv (written by
f133b_keys.R with F13.3's own key function), E1 by column whitelist, and the F13.3 tables named in the brief. Networks with networkx
(Louvain seed 42), partition comparison with sklearn.metrics, figures with matplotlib (not viewed; PDF/PNG/TIF byte-stable).
Writes tables/, figures/, F13_3b_numbers.json under the phase folder or under --out=<dir> (second run of gate G4). Prints counts only;
corpus author names (E1 'Authors', step-3 control) stay in memory. Cited works are shown as first-author surname, year, title, source."""
import sys
sys.dont_write_bytecode = True

import bisect
import difflib
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f133b_lib as L

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from PIL import Image
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

ARGS = [a for a in sys.argv[1:] if a.startswith("--out=")]
OUT = Path(ARGS[0][6:]) if ARGS else L.OUT
TAB, FIG = OUT / "tables", OUT / "figures"
NUM = {}
r4 = lambda x: round(float(x), 4)


def tab(name, fields, rows):
    L.write_csv(TAB / f"{name}.csv", fields, rows)


def f133(name):
    return L.read_csv(L.path(L.F133_TABLES[name]))


def kv(rows, k="measure", v="value"):
    return {r[k]: r[v] for r in rows}


def save_fig(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.pdf", metadata={"CreationDate": None, "ModDate": None, "Producer": None, "Creator": None})
    fig.savefig(FIG / f"{name}.png", dpi=300, metadata={"Software": None})
    plt.close(fig)
    with Image.open(FIG / f"{name}.png") as im:
        im.save(FIG / f"{name}.tif", compression="tiff_lzw", dpi=(300, 300))


def relabel(comms):
    """Louvain communities -> {node: cluster number}, numbered by size (desc), then smallest node id."""
    cs = sorted((sorted(c) for c in comms), key=lambda c: (-len(c), c[0]))
    return {n: i + 1 for i, c in enumerate(cs) for n in c}


def louvain(G, seed=42):
    comms = nx.community.louvain_communities(G, weight="weight", seed=seed)
    return relabel(comms), r4(nx.community.modularity(G, comms, weight="weight"))


def graph(nodes, edges):
    G = nx.Graph()
    G.add_nodes_from(sorted(nodes))
    for (a, b), w in sorted(edges.items()):
        G.add_edge(a, b, weight=w)
    return G


def compare(m1, m2):
    common = sorted(set(m1) & set(m2))
    if not common:
        return "", ""
    a, b = [m1[n] for n in common], [m2[n] for n in common]
    return r4(normalized_mutual_info_score(a, b)), r4(adjusted_rand_score(a, b))


def pair_counts(sets, min_w):
    """sets: {record: set(items)} -> {(a, b): shared items} for pairs sharing >= min_w items (a < b)."""
    inv = defaultdict(list)
    for r in sorted(sets):
        for it in sets[r]:
            inv[it].append(r)
    cnt = Counter()
    for it, rs in inv.items():
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                cnt[(rs[i], rs[j])] += 1
    return {p: w for p, w in cnt.items() if w >= min_w}


# ---------------- load ----------------
K = L.read_csv(OUT / "data" / "reference_keys.csv")
for r in K:
    r["in_scope"] = int(r["in_scope"])
    r["year_i"] = L.year_int(r["year"]) if r["year"] not in ("", "NA") else None
E = {r["EID"]: r for r in L.e1_columns(L.E1_COLS)}
for r in E.values():
    r["py"] = int(r["Year"])
    r["tc"] = int(r["Cited by"] or 0)
assert len(E) == 841 and len(K) == 28471
refs_per_rec = Counter(r["eid"] for r in K)
total_refs = len(K)
per = {e: L.period_of(r["py"]) for e, r in E.items()}
doi_or_eid = lambda e: E[e]["DOI"] or e
S = [r for r in K if r["in_scope"]]
rec_works = defaultdict(set)
for r in S:
    rec_works[r["eid"]].add(r["key"])
citing = Counter(k for ws in rec_works.values() for k in ws)
by_key = defaultdict(list)
for r in S:
    by_key[r["key"]].append(r)


def rep(key):
    """The most frequent exact string of a work (ties: alphabetical) and its parsed fields; source = most frequent non-empty form."""
    rows = by_key[key]
    c = Counter(r["reference"] for r in rows)
    best = sorted(c.items(), key=lambda x: (-x[1], x[0]))[0][0]
    row = next(r for r in rows if r["reference"] == best)
    src = Counter(r["source"] for r in rows if r["source"])
    return {"first_author": L.tc_name(row["first_author"]), "year": row["year"] if row["year"] != "NA" else "",
            "title": row["title"].strip().rstrip(" ,;:."), "source": sorted(src.items(), key=lambda x: (-x[1], x[0]))[0][0] if src else "",
            "variants": len(c)}


ranked = sorted(citing.items(), key=lambda x: (-x[1], x[0]))

# ---------------- step 1: key coverage, collisions, sensitivity ----------------
f2a = kv(f133("T2a"))
complete = [r for r in K if not r["key"].startswith("=")]
thr = lambda c: (sum(1 for v in c.values() if v >= 2), sum(1 for v in c.values() if v >= 5), sum(1 for v in c.values() if v >= 10))
t2, t5, t10 = thr(citing)
T1a = [
    {"measure": "references (F13.3 repaired)", "value": total_refs, "share": 1, "F13_3": f133("T0a")[0]["F13_3_corrected"]},
    {"measure": "references in scope (> 10 characters, as F13.3)", "value": len(S), "share": r4(len(S) / total_refs), "F13_3": ""},
    {"measure": "references with a complete key (first author, year, title)", "value": len(complete), "share": r4(len(complete) / total_refs), "F13_3": ""},
    {"measure": "references without a year", "value": sum(1 for r in K if r["year_i"] is None), "share": r4(sum(1 for r in K if r["year_i"] is None) / total_refs), "F13_3": ""},
    {"measure": "references without a title segment", "value": sum(1 for r in K if not r["title"]), "share": r4(sum(1 for r in K if not r["title"]) / total_refs), "F13_3": ""},
    {"measure": "references without a first author", "value": sum(1 for r in K if not r["first_author"]), "share": r4(sum(1 for r in K if not r["first_author"]) / total_refs), "F13_3": ""},
    {"measure": "works (distinct keys in scope; incomplete keys keep their string)", "value": len(citing), "share": "", "F13_3": f2a["work key (own code): distinct works"]},
    {"measure": "works with >= 2 citing records", "value": t2, "share": "", "F13_3": f2a["work key: works with >= 2 citing records"]},
    {"measure": "works with >= 5 citing records", "value": t5, "share": "", "F13_3": f2a["work key: works with >= 5 citing records"]},
    {"measure": "works with >= 10 citing records", "value": t10, "share": "", "F13_3": f2a["work key: works with >= 10 citing records"]}]
tab("T1a_key_coverage", ["measure", "value", "share", "F13_3"], T1a)
normu = lambda s: " ".join(re.sub(r"[\W_]+", " ", (s or "").upper()).split())
coll, coll_div, coll_diff = [], {}, {}
for k, rows in by_key.items():
    if k.startswith("="):
        continue
    ft = sorted({normu(r["title"]) for r in rows})
    if len(ft) > 1:
        coll.append(k)
        pairs = [(a, b) for i, a in enumerate(ft) for b in ft[i + 1:] if not (a.startswith(b) or b.startswith(a))]
        if pairs:
            coll_div[k] = min((r4(difflib.SequenceMatcher(None, a, b).ratio()), a, b) for a, b in pairs)
            if coll_div[k][0] < 0.8:
                coll_diff[k] = coll_div[k]
ex = sorted(coll_div, key=lambda k: (coll_div[k][0], -citing[k], k))[:10]
T1b = [{"rank": i, "first_author": rep(k)["first_author"], "year": k.split("|")[1], "title_a": L.cut_words(coll_div[k][1], 15),
        "title_b": L.cut_words(coll_div[k][2], 15), "similarity": coll_div[k][0], "likely_different_works": "yes" if k in coll_diff else "no",
        "citing_records": citing[k]} for i, k in enumerate(ex, 1)]
tab("T1b_key_collisions", ["rank", "first_author", "year", "title_a", "title_b", "similarity", "likely_different_works", "citing_records"], T1b)
tab("T1b2_collision_counts", ["measure", "value"], [
    {"measure": "complete keys with >= 2 different full titles (variant spellings included)", "value": len(coll)},
    {"measure": "of them: titles diverge (neither is a prefix of the other)", "value": len(coll_div)},
    {"measure": "of them: likely different works (similarity of the most different pair < 0.8)", "value": len(coll_diff)},
    {"measure": "citing records of the likely-different keys (sum)", "value": sum(citing[k] for k in coll_diff)},
    {"measure": "likely-different keys among works with >= 4 citing records", "value": sum(1 for k in coll_diff if citing[k] >= 4)}])


def works_of(field, merge_year=False):
    mp = {}
    if merge_year:
        groups = defaultdict(set)
        for v in {r[field] for r in S}:
            if not v.startswith("="):
                au, y, t = v.split("|", 2)
                groups[(au, t)].add(int(y))
        for (au, t), ys in groups.items():
            ys = sorted(ys)
            start = ys[0]
            for j, y in enumerate(ys):
                if j and y - ys[j - 1] > 1:
                    start = y
                mp[f"{au}|{y}|{t}"] = f"{au}|{start}|{t}"
    rw = defaultdict(set)
    for r in S:
        rw[r["eid"]].add(mp.get(r[field], r[field]))
    return rw


T1c = []
for label, field, my in (("title words 4", "key4", False), ("title words 6 (main)", "key", False), ("title words 8", "key8", False),
                         ("title words 6, year +/- 1 merged", "key", True)):
    rw = works_of(field, my)
    c = Counter(k for ws in rw.values() for k in ws)
    a2, a5, a10 = thr(c)
    T1c.append({"variant": label, "works": len(c), "ge2": a2, "ge5": a5, "ge10": a10})
tab("T1c_key_sensitivity", ["variant", "works", "ge2", "ge5", "ge10"], T1c)
NUM["T1"] = {"refs": total_refs, "in_scope": len(S), "complete": len(complete), "works": len(citing), "ge2": t2, "ge5": t5, "ge10": t10,
             "collisions": len(coll), "collisions_divergent": len(coll_div), "collisions_likely_different": len(coll_diff),
             "collisions_likely_different_ge4": sum(1 for k in coll_diff if citing[k] >= 4)}

# ---------------- step 3 (before T2: the corpus-record flag): local citations by title ----------------
tnorm = {e: L.norm_title(r["Title"]) for e, r in E.items()}
eligible = {e: t for e, t in tnorm.items() if len(t) >= 30}
tcount = Counter(eligible.values())
ambiguous = {t for t, c in tcount.items() if c >= 2}
titles = {e: t for e, t in eligible.items() if t not in ambiguous}
hay_refs = [L.norm_title(r["reference"]) for r in K]
blob = "\n".join(hay_refs)
starts = []
pos = 0
for h in hay_refs:
    starts.append(pos)
    pos += len(h) + 1
ref_hits = defaultdict(set)
for e, t in sorted(titles.items()):
    i = blob.find(t)
    while i != -1:
        ref_hits[bisect.bisect_right(starts, i) - 1].add(e)
        i = blob.find(t, i + 1)
links = defaultdict(list)
for ri, es in ref_hits.items():
    for e in es:
        if e != K[ri]["eid"]:
            links[(K[ri]["eid"], e)].append(ri)
internal_refs = {ri for (c, e), ris in links.items() for ri in ris}
LCS = Counter(e for (c, e) in links)
citing_recs = {c for (c, e) in links}
matched_keys = {K[ri]["key"] for ri in internal_refs}
auth = {r["EID"]: r["Authors"] for r in L.e1_columns(["EID", "Authors"])}


def first_surname(a):
    a = (a or "").split(";")[0].strip()
    return L.norm_title(re.sub(r"\s+(?:[A-Z][A-Za-z]?\.[-\s]?)+$", "", a))


ctrl = Counter()
for (c, e), ris in links.items():
    sur = first_surname(auth.get(e, ""))
    best = None
    for ri in ris:
        h = " " + hay_refs[ri] + " "
        s_ok = None if not sur else (" " + sur + " ") in h
        y = K[ri]["year_i"]
        y_ok = None if y is None else abs(y - E[e]["py"]) <= 1
        cat = ("surname not checkable" if s_ok is None else ("surname found" if s_ok else "surname missing")) + " / " + \
              ("year missing" if y_ok is None else ("year within 1" if y_ok else "year off by more than 1"))
        rank = (s_ok is True) + (y_ok is True)
        if best is None or rank > best[0]:
            best = (rank, cat)
    ctrl[best[1]] += 1
del auth
f4a = kv(f133("T4a"))
nl = len(links)
T3a = [
    {"measure": "local citation links (citing record -> cited record)", "title_match_F13_3b": nl, "localCitations_F13_3": f4a["LCS, total (local citation links)"]},
    {"measure": "citing records", "title_match_F13_3b": len(citing_recs), "localCitations_F13_3": "not in the F13.3 tables"},
    {"measure": "cited records (LCS > 0)", "title_match_F13_3b": len(LCS), "localCitations_F13_3": f4a["records with LCS > 0"]},
    {"measure": "LCS, max", "title_match_F13_3b": max(LCS.values()), "localCitations_F13_3": f4a["LCS, max"]},
    {"measure": "share of references: links / all references", "title_match_F13_3b": r4(nl / total_refs), "localCitations_F13_3": f4a["share of references pointing inside the corpus"]},
    {"measure": "references matching another record's title", "title_match_F13_3b": len(internal_refs), "localCitations_F13_3": ""},
    {"measure": "records with a normalised title of >= 30 characters", "title_match_F13_3b": len(eligible), "localCitations_F13_3": ""},
    {"measure": "ambiguous titles excluded (same title in >= 2 records): titles / records", "title_match_F13_3b":
     f"{len(ambiguous)} / {sum(tcount[t] for t in ambiguous)}", "localCitations_F13_3": ""}]
tab("T3a_local_citations_title", ["measure", "title_match_F13_3b", "localCitations_F13_3"], T3a)
tab("T3a2_control", ["control (best reference of each link)", "links"],
    [{"control (best reference of each link)": k, "links": v} for k, v in sorted(ctrl.items())])
# robustness of the title rule: the main links recomputed per record (references of a record joined by newlines, so a title
# cannot span two references) and under variants
raw_refs = {r["EID"]: r["References"] for r in L.e1_columns(["EID", "References"])}
uninorm = lambda s: " ".join(re.sub(r"[\W_]+", " ", (s or "").upper()).split())
by_rec_refs = defaultdict(list)
for r in K:
    by_rec_refs[r["eid"]].append(r["reference"])


def title_links(norm, hay_raw, min_len=30, amb="exclude", pad=False):
    t = {e: norm(r["Title"]) for e, r in E.items()}
    t = {e: x for e, x in t.items() if len(x) >= min_len}
    c = Counter(t.values())
    if amb == "exclude":
        t = {e: x for e, x in t.items() if c[x] == 1}
    elif amb == "keep_first":
        seen, t2 = set(), {}
        for e in sorted(t):
            if t[e] not in seen:
                t2[e], _ = t[e], seen.add(t[e])
        t = t2
    out = set()
    for ce in sorted(hay_raw):
        h = "\n".join(norm(x) for x in hay_raw[ce])
        h = " " + h.replace("\n", " \n ") + " " if pad else h
        for e, x in t.items():
            if e != ce and ((" " + x + " ") in h if pad else x in h):
                out.add((ce, e))
    return out


rec_refs = {e: by_rec_refs.get(e, []) for e in E}
T3a3 = []
for label, args in (("main: repaired references, Latin letters and digits, >= 30, ambiguous excluded", (L.norm_title, rec_refs)),
                    ("E1 References as exported (whole cell, mixed case)", (L.norm_title, {e: [raw_refs[e]] for e in E})),
                    ("all letters kept (not only Latin)", (uninorm, rec_refs)), ("whole-word match", (L.norm_title, rec_refs, 30, "exclude", True)),
                    ("title length >= 20", (L.norm_title, rec_refs, 20)), ("title length >= 35", (L.norm_title, rec_refs, 35)),
                    ("ambiguous titles: first record kept", (L.norm_title, rec_refs, 30, "keep_first")),
                    ("ambiguous titles: all records kept", (L.norm_title, rec_refs, 30, "all"))):
    lk = title_links(*args)
    lc = Counter(e for _, e in lk)
    T3a3.append({"variant": label, "links": len(lk), "citing_records": len({a for a, _ in lk}), "cited_records": len(lc), "LCS_max": max(lc.values())})
del raw_refs
assert T3a3[0]["links"] == len(links) and T3a3[0]["cited_records"] == len(LCS), (T3a3[0], len(links))
tab("T3a3_title_rule_variants", ["variant", "links", "citing_records", "cited_records", "LCS_max"], T3a3)
made = Counter(c for (c, e) in links)
T3b = []
for p, _, _ in L.PERIODS:
    es = [e for e in E if per[e] == p]
    T3b.append({"period": p, "records": len(es), "records_with_LCS": sum(1 for e in es if LCS[e] > 0), "LCS_received": sum(LCS[e] for e in es),
                "references_made": sum(refs_per_rec[e] for e in es), "internal_references_made": sum(made[e] for e in es),
                "share_internal": r4(sum(made[e] for e in es) / max(1, sum(refs_per_rec[e] for e in es)))})
tab("T3b_local_citations_by_period", ["period", "records", "records_with_LCS", "LCS_received", "references_made", "internal_references_made",
                                      "share_internal"], T3b)
top = sorted(LCS, key=lambda e: (-LCS[e], -E[e]["tc"], e))[:20]
tab("T3c_top20_LCS", ["rank", "doi_or_eid", "year", "source", "title", "LCS", "GCS"],
    [{"rank": i, "doi_or_eid": doi_or_eid(e), "year": E[e]["py"], "source": L.cut_words(E[e]["Source title"], 20),
      "title": L.cut_words(E[e]["Title"], 30), "LCS": LCS[e], "GCS": E[e]["tc"]} for i, e in enumerate(top, 1)])
hn = sorted((e for e in LCS if LCS[e] >= 2), key=lambda e: (E[e]["py"], e))
hlab = {e: f"#{i}" for i, e in enumerate(hn, 1)}
hset = set(hn)
hedges = sorted((c, e) for (c, e) in links if c in hset and e in hset)
H = nx.DiGraph()
H.add_nodes_from(hn)
H.add_edges_from(hedges)
pos_h = nx.spring_layout(H.to_undirected(), seed=42)
fig, ax = plt.subplots(figsize=(11, 7))
for c, e in hedges:
    ax.annotate("", xy=(E[e]["py"], pos_h[e][1]), xytext=(E[c]["py"], pos_h[c][1]),
                arrowprops={"arrowstyle": "->", "color": "0.6", "lw": 0.6})
ax.scatter([E[e]["py"] for e in hn], [pos_h[e][1] for e in hn], s=[18 + 10 * LCS[e] for e in hn], c="#2b6a99", alpha=0.75, zorder=3)
for e in hn:
    ax.text(E[e]["py"], pos_h[e][1] + 0.025, hlab[e], fontsize=5, ha="center", zorder=4)
ax.set_yticks([])
ax.set_xlabel("Publication year of the record")
ax.set_title(f"Within-corpus citations by title match: {len(hn)} records with LCS >= 2, {len(hedges)} links")
save_fig(fig, "Fig_historiograph_titlekey")
L.write_csv(FIG / "Fig_historiograph_titlekey_nodes.csv", ["label", "doi_or_eid", "year", "LCS", "GCS", "x", "y"],
            [{"label": hlab[e], "doi_or_eid": doi_or_eid(e), "year": E[e]["py"], "LCS": LCS[e], "GCS": E[e]["tc"], "x": E[e]["py"],
              "y": r4(pos_h[e][1])} for e in hn])
L.write_csv(FIG / "Fig_historiograph_titlekey_edges.csv", ["citing", "cited"], [{"citing": hlab[c], "cited": hlab[e]} for c, e in hedges])
wcc = nx.number_weakly_connected_components(H)
tab("T3d_historiograph", ["measure", "value"], [
    {"measure": "nodes (records with LCS >= 2)", "value": len(hn)}, {"measure": "edges (title-matched links among them)", "value": len(hedges)},
    {"measure": "weakly connected components (isolates included)", "value": wcc},
    {"measure": "nodes without a link to another node", "value": sum(1 for e in hn if H.degree(e) == 0)},
    {"measure": "years spanned", "value": f"{E[hn[0]]['py']}-{E[hn[-1]]['py']}"}])
L.write_csv(TAB / "T3d_historiograph_nodes.csv", ["label", "doi_or_eid", "year", "LCS", "GCS"],
            [{"label": hlab[e], "doi_or_eid": doi_or_eid(e), "year": E[e]["py"], "LCS": LCS[e], "GCS": E[e]["tc"]} for e in hn])
NUM["T3"] = {"links": nl, "citing": len(citing_recs), "cited": len(LCS), "max": max(LCS.values()), "share": r4(nl / total_refs),
             "ambiguous_titles": len(ambiguous), "ambiguous_records": sum(tcount[t] for t in ambiguous), "eligible": len(eligible),
             "control": dict(ctrl), "hist_nodes": len(hn), "hist_edges": len(hedges), "hist_wcc": wcc}

# ---------------- step 2: top-30 works ----------------
T2 = []
for i, (k, c) in enumerate(ranked[:30], 1):
    rp = rep(k)
    pc = Counter(per[e] for e, ws in rec_works.items() if k in ws)
    T2.append({"rank": i, "first_author": rp["first_author"], "year": rp["year"], "title": L.cut_words(rp["title"], 15),
               "source": L.cut_words(rp["source"], 15), "citing_records": c, "p2003_2016": pc["2003-2016"], "p2017_2021": pc["2017-2021"],
               "p2022_2025": pc["2022-2025"], "string_variants": rp["variants"], "corpus_record": "yes" if k in matched_keys else "no"})
tab("T2_top30_works", ["rank", "first_author", "year", "title", "source", "citing_records", "p2003_2016", "p2017_2021", "p2022_2025",
                       "string_variants", "corpus_record"], T2)
f2b = f133("T2b")
T2a = [{"measure": m, "work_key_F13_3b": v, "work_key_F13_3_sensitivity": f2a[fm], "strings_F13_3": f2a[sm]} for m, v, fm, sm in (
    ("distinct works / strings", len(citing), "work key (own code): distinct works", "distinct cited references (strings counted by citations())"),
    ("with >= 2 citing records", t2, "work key: works with >= 2 citing records", "with >= 2 citing records"),
    ("with >= 5 citing records", t5, "work key: works with >= 5 citing records", "with >= 5 citing records"),
    ("with >= 10 citing records", t10, "work key: works with >= 10 citing records", "with >= 10 citing records"))]
tab("T2a_thresholds", ["measure", "work_key_F13_3b", "work_key_F13_3_sensitivity", "strings_F13_3"], T2a)
same_top = sum(1 for a, b in zip(T2, f2b) if a["first_author"] == b["first_author"] and str(a["year"]) == b["year"] and a["citing_records"] == int(b["citing_records"]))
NUM["T2"] = {"top1_citing": T2[0]["citing_records"], "top30_equal_F13_3_T2b": same_top, "corpus_records_in_top30": sum(1 for r in T2 if r["corpus_record"] == "yes")}

# ---------------- step 4: bibliographic coupling on the work key ----------------
recs_with_refs = sorted(rec_works)
nwork = {e: len(ws) for e, ws in rec_works.items()}


def coupling(sets, min_w, salton=False):
    pc = pair_counts(sets, min_w)
    w = {p: (r4(v / (nwork[p[0]] * nwork[p[1]]) ** 0.5) if salton else v) for p, v in pc.items()}
    G = graph({n for p in pc for n in p}, w)
    m, q = louvain(G)
    return G, m, q, pc


G4, M4, Q4, PC4 = coupling(rec_works, 2)
comp = sorted(nx.connected_components(G4), key=len, reverse=True)
sz = Counter(M4.values())
big = sorted(c for c, n in sz.items() if n >= 10)
aris = []
for sd in range(1, 21):
    m, _ = louvain(G4, seed=sd)
    aris.append(compare(M4, m)[1])
f5c = f133("T5c")
f5a = kv(f133("T5a"))
T4a = [{"measure": m, "value": v} for m, v in (
    ("records with references in scope", len(recs_with_refs)), ("nodes (records sharing >= 2 works with another record)", G4.number_of_nodes()),
    ("isolated records with references", len(recs_with_refs) - G4.number_of_nodes()), ("edges", G4.number_of_edges()),
    ("components", len(comp)), ("largest component (records)", len(comp[0])), ("Louvain clusters (seed 42)", len(sz)),
    ("clusters with >= 10 records", len(big)), ("records in clusters with >= 10 records", sum(sz[c] for c in big)), ("modularity Q", Q4),
    ("stability: ARI to the main partition over 20 seeds - median", r4(statistics.median(aris))),
    ("stability: ARI over 20 seeds - minimum", min(aris)),
    ("F13.3 work-key sensitivity (igraph): nodes / edges / clusters >= 10", f"{f5c[3]['nodes']} / {f5c[3]['edges']} / {f5c[3]['clusters_ge10']}"),
    ("F13.3 strings (bibliometrix): nodes / edges / clusters >= 10", f"{f5a['nodes (records with >= 1 link of >= 2 shared references)']} / "
     f"{f5a['edges (pairs sharing >= 2 references)']} / {f5a['clusters with >= 10 records']}"))]
tab("T4a_coupling_workkey", ["measure", "value"], T4a)
kwd = {e: sorted({" ".join(k.lower().split()) for k in E[e]["Author Keywords"].split(";") if k.strip()}) for e in E}
T4b, T4b2 = [], []
for c in big:
    es = sorted(n for n, x in M4.items() if x == c)
    dt = Counter(E[e]["Document Type"] for e in es)
    kc = Counter(k for e in es for k in kwd[e])
    sc = Counter(E[e]["Source title"] for e in es)
    tcs = [E[e]["tc"] for e in es]
    T4b.append({"cluster": c, "records": len(es), "p2003_2016": sum(per[e] == "2003-2016" for e in es), "p2017_2021": sum(per[e] == "2017-2021" for e in es),
                "p2022_2025": sum(per[e] == "2022-2025" for e in es), "articles": dt["Article"], "conference_papers": dt["Conference paper"],
                "other_types": len(es) - dt["Article"] - dt["Conference paper"],
                "top5_author_keywords": "; ".join(L.cut_words(k, 5) for k, _ in sorted(kc.items(), key=lambda x: (-x[1], x[0]))[:5]),
                "main_source": L.cut_words(sorted(sc.items(), key=lambda x: (-x[1], x[0]))[0][0], 12),
                "main_source_records": sorted(sc.items(), key=lambda x: (-x[1], x[0]))[0][1], "mean_TC": round(statistics.mean(tcs), 2),
                "median_TC": statistics.median(tcs)})
    wc = Counter(k for e in es for k in rec_works[e])
    for j, (k, n) in enumerate(sorted(wc.items(), key=lambda x: (-x[1], x[0]))[:3], 1):
        rp = rep(k)
        T4b2.append({"cluster": c, "rank": j, "first_author": rp["first_author"], "year": rp["year"], "title": L.cut_words(rp["title"], 15),
                     "records_in_cluster": n})
tab("T4b_coupling_clusters", ["cluster", "records", "p2003_2016", "p2017_2021", "p2022_2025", "articles", "conference_papers", "other_types",
                              "top5_author_keywords", "main_source", "main_source_records", "mean_TC", "median_TC"], T4b)
tab("T4b2_cluster_shared_works", ["cluster", "rank", "first_author", "year", "title", "records_in_cluster"], T4b2)
rw4, rw8 = works_of("key4"), works_of("key8")
variants = [("main: shared works >= 2", G4, M4, Q4)]
for label, sets, mw, sal in (("shared works >= 3", rec_works, 3, False), ("Salton weights, shared works >= 2", rec_works, 2, True),
                             ("key with 4 title words, shared >= 2", rw4, 2, False), ("key with 8 title words, shared >= 2", rw8, 2, False)):
    G, m, q, _ = coupling(sets, mw, sal)
    variants.append((label, G, m, q))
T4c = []
for label, G, m, q in variants:
    s = Counter(m.values())
    nmi, ari = compare(M4, m)
    T4c.append({"variant": label, "nodes": G.number_of_nodes(), "edges": G.number_of_edges(), "clusters": len(s),
                "clusters_ge10": sum(1 for v in s.values() if v >= 10), "modularity": q, "nmi_vs_main": nmi, "ari_vs_main": ari})
tab("T4c_coupling_sensitivity", ["variant", "nodes", "edges", "clusters", "clusters_ge10", "modularity", "nmi_vs_main", "ari_vs_main"], T4c)
pos4 = nx.spring_layout(G4, seed=42, weight="weight")
cmap = plt.get_cmap("tab20")
col = {c: cmap(i % 20) for i, c in enumerate(big)}
fig, ax = plt.subplots(figsize=(10, 9))
nx.draw_networkx_edges(G4, pos4, ax=ax, edge_color="0.75", width=0.3, alpha=0.5)
nodes4 = sorted(G4.nodes())
ax.scatter([pos4[n][0] for n in nodes4], [pos4[n][1] for n in nodes4], s=10, zorder=3,
           c=[col.get(M4[n], (0.82, 0.82, 0.82, 1)) for n in nodes4], edgecolors="none")
for c in big:
    xs = [pos4[n][0] for n in nodes4 if M4[n] == c]
    ys = [pos4[n][1] for n in nodes4 if M4[n] == c]
    ax.text(sum(xs) / len(xs), sum(ys) / len(ys), str(c), fontsize=9, weight="bold", ha="center", va="center", zorder=4)
ax.set_axis_off()
ax.set_title(f"Bibliographic coupling on the work key: {G4.number_of_nodes()} records sharing >= 2 works; clusters >= 10 numbered (Louvain, seed 42)",
             fontsize=8)
save_fig(fig, "Fig_bibliographic_coupling_workkey")
L.write_csv(FIG / "Fig_bibliographic_coupling_workkey_nodes.csv", ["eid", "doi", "cluster", "degree", "x", "y"],
            [{"eid": n, "doi": E[n]["DOI"], "cluster": M4[n], "degree": G4.degree(n), "x": r4(pos4[n][0]), "y": r4(pos4[n][1])} for n in nodes4])
L.write_csv(FIG / "Fig_bibliographic_coupling_workkey_edges.csv", ["eid_a", "eid_b", "shared_works"],
            [{"eid_a": a, "eid_b": b, "shared_works": w} for (a, b), w in sorted(PC4.items())])
NUM["T4"] = {"nodes": G4.number_of_nodes(), "edges": G4.number_of_edges(), "components": len(comp), "largest": len(comp[0]), "clusters": len(sz),
             "big": len(big), "Q": Q4, "ari_median": r4(statistics.median(aris)), "ari_min": min(aris), "sizes_big": [sz[c] for c in big]}

# ---------------- step 5: co-citation on the work key ----------------
f6a = kv(f133("T6a"))
f6a2 = kv(f133("T6a2"))


recs_of = defaultdict(set)
for e, ws in rec_works.items():
    for k in ws:
        recs_of[k].add(e)


def cocitation(node_min, edge_min):
    """Works cited by >= node_min records; pairs of works cited together by >= edge_min records."""
    sel = {k for k, c in citing.items() if c >= node_min}
    pc = pair_counts({k: recs_of[k] for k in sel}, edge_min)
    G = graph({n for p in pc for n in p}, pc)
    m, q = louvain(G) if G.number_of_nodes() else ({}, "")
    return sel, G, m, q, pc


SEL5, G5, M5, Q5, PC5 = cocitation(4, 3)
s5 = Counter(M5.values())
big5 = sorted(c for c, n in s5.items() if n >= 5)
tab("T5a_cocitation_workkey", ["measure", "work_key_F13_3b", "work_key_F13_3_sensitivity", "strings_F13_3"], [
    {"measure": "nodes: works with >= 4 citing records", "work_key_F13_3b": len(SEL5), "work_key_F13_3_sensitivity": f6a2["works (work key) with >= 4 citing records"],
     "strings_F13_3": f6a["nodes: references with >= 4 citing records"]},
    {"measure": "nodes with >= 1 edge", "work_key_F13_3b": G5.number_of_nodes(), "work_key_F13_3_sensitivity": f6a2["of them with >= 1 edge"],
     "strings_F13_3": f6a["nodes with >= 1 edge"]},
    {"measure": "edges: pairs co-cited by >= 3 records", "work_key_F13_3b": G5.number_of_edges(), "work_key_F13_3_sensitivity": f6a2["edges: pairs co-cited by >= 3 records"],
     "strings_F13_3": f6a["edges: pairs co-cited by >= 3 records"]},
    {"measure": "Louvain clusters", "work_key_F13_3b": len(s5), "work_key_F13_3_sensitivity": f6a2["Louvain clusters"], "strings_F13_3": f6a["Louvain clusters (nodes with edges)"]},
    {"measure": "clusters with >= 5 nodes", "work_key_F13_3b": len(big5), "work_key_F13_3_sensitivity": f6a2["clusters with >= 5 nodes"],
     "strings_F13_3": f6a["clusters with >= 5 nodes"]},
    {"measure": "modularity Q", "work_key_F13_3b": Q5, "work_key_F13_3_sensitivity": f6a2["modularity Q"], "strings_F13_3": f6a["modularity Q"]}])
REP5 = {k: rep(k) for k in G5.nodes()}
T5b = []
for c in big5:
    ks = sorted((k for k, x in M5.items() if x == c), key=lambda k: (-citing[k], k))
    yrs = [int(REP5[k]["year"]) for k in ks if REP5[k]["year"]]
    for j, k in enumerate(ks[:5], 1):
        T5b.append({"cluster": c, "cluster_size": len(ks), "median_year": statistics.median(yrs) if yrs else "", "rank": j,
                    "first_author": REP5[k]["first_author"], "year": REP5[k]["year"], "title": L.cut_words(REP5[k]["title"], 15),
                    "citing_records": citing[k]})
tab("T5b_cocitation_clusters", ["cluster", "cluster_size", "median_year", "rank", "first_author", "year", "title", "citing_records"], T5b)
T5c = []
for label, nm, em in (("main: works >= 4 citing, co-cited >= 3", 4, 3), ("works >= 3 citing, co-cited >= 3", 3, 3), ("works >= 5 citing, co-cited >= 3", 5, 3),
                      ("works >= 4 citing, co-cited >= 2", 4, 2), ("works >= 4 citing, co-cited >= 4", 4, 4)):
    sel, G, m, q, _ = cocitation(nm, em)
    s = Counter(m.values())
    nmi, ari = compare(M5, m)
    T5c.append({"variant": label, "works": len(sel), "nodes_with_edges": G.number_of_nodes(), "edges": G.number_of_edges(), "clusters": len(s),
                "clusters_ge5": sum(1 for v in s.values() if v >= 5), "modularity": q, "nmi_vs_main": nmi, "ari_vs_main": ari})
tab("T5c_cocitation_sensitivity", ["variant", "works", "nodes_with_edges", "edges", "clusters", "clusters_ge5", "modularity", "nmi_vs_main", "ari_vs_main"], T5c)
nodes5 = sorted(G5.nodes(), key=lambda k: (-citing[k], k))
nid = {k: f"W{i:03d}" for i, k in enumerate(nodes5, 1)}
lab = {k: f"{REP5[k]['first_author']} {REP5[k]['year']}".strip() for k in nodes5[:30]}
pos5 = nx.spring_layout(G5, seed=42, weight="weight")
col5 = {c: cmap(i % 20) for i, c in enumerate(big5)}
fig, ax = plt.subplots(figsize=(10, 9))
nx.draw_networkx_edges(G5, pos5, ax=ax, edge_color="0.7", width=0.4, alpha=0.5)
order5 = sorted(G5.nodes())
ax.scatter([pos5[k][0] for k in order5], [pos5[k][1] for k in order5], s=[8 + 6 * citing[k] for k in order5], zorder=3,
           c=[col5.get(M5[k], (0.82, 0.82, 0.82, 1)) for k in order5], edgecolors="none")
for k in nodes5[:30]:
    ax.text(pos5[k][0], pos5[k][1] + 0.02, lab[k], fontsize=5, ha="center", zorder=4)
ax.set_axis_off()
ax.set_title(f"Co-citation on the work key: {G5.number_of_nodes()} works (>= 4 citing records, co-cited >= 3); the 30 most cited labelled", fontsize=8)
save_fig(fig, "Fig_cocitation_workkey")
L.write_csv(FIG / "Fig_cocitation_workkey_nodes.csv", ["node", "label", "first_author", "year", "title", "cluster", "citing_records", "degree", "x", "y"],
            [{"node": nid[k], "label": lab.get(k, ""), "first_author": REP5[k]["first_author"], "year": REP5[k]["year"],
              "title": L.cut_words(REP5[k]["title"], 10), "cluster": M5[k], "citing_records": citing[k], "degree": G5.degree(k),
              "x": r4(pos5[k][0]), "y": r4(pos5[k][1])} for k in nodes5])
L.write_csv(FIG / "Fig_cocitation_workkey_edges.csv", ["from", "to", "cocitations"],
            [{"from": min(nid[a], nid[b]), "to": max(nid[a], nid[b]), "cocitations": w} for (a, b), w in
             sorted(PC5.items(), key=lambda x: (min(nid[x[0][0]], nid[x[0][1]]), max(nid[x[0][0]], nid[x[0][1]])))])
L.write_csv(OUT / "data" / "cocitation_workkey_nodes.csv", ["node", "key", "representative_reference", "citing_records"],
            [{"node": nid[k], "key": k, "representative_reference": sorted(Counter(r["reference"] for r in by_key[k]).items(), key=lambda x: (-x[1], x[0]))[0][0],
              "citing_records": citing[k]} for k in nodes5])
NUM["T5"] = {"works": len(SEL5), "nodes": G5.number_of_nodes(), "edges": G5.number_of_edges(), "clusters": len(s5), "big": len(big5), "Q": Q5,
             "sizes_big": [s5[c] for c in big5]}

# ---------------- step 6: cited sources by the parse rule ----------------
th = {r["variant"]: r["canonical"] for r in f133("thesaurus")}
src = [(r["eid"], th.get(r["source"], r["source"])) for r in K if r["source"] and r["source_name_shaped"] == "0"]
sref = Counter(s for _, s in src)
srec = Counter(s for _, s in {(e, s) for e, s in src})
top_s = sorted(sref, key=lambda s: (-sref[s], -srec[s], s))[:30]
f3a = [r["source"] for r in f133("T3a")]
f3c = kv(f133("T3c"))
tab("T6a_sources_parse_rule", ["rank", "source", "references", "share_of_recognised", "share_of_all", "citing_records"],
    [{"rank": i, "source": L.cut_words(s, 20), "references": sref[s], "share_of_recognised": r4(sref[s] / len(src)),
      "share_of_all": r4(sref[s] / total_refs), "citing_records": srec[s]} for i, s in enumerate(top_s, 1)])
tab("T6a2_sources_summary", ["measure", "value"], [
    {"measure": "references with a source by the parse rule (thesaurus applied; name-shaped excluded)", "value": len(src)},
    {"measure": "share of all references", "value": r4(len(src) / total_refs)},
    {"measure": "F13.3: references with a source by metaTagExtraction(CR_SO)", "value": f3c["references with a source recognised by metaTagExtraction(CR_SO)"]},
    {"measure": "distinct sources", "value": len(sref)},
    {"measure": "share of all references on the top-30", "value": r4(sum(sref[s] for s in top_s) / total_refs)},
    {"measure": "top-30 sources also in the F13.3 T3a top-30", "value": sum(1 for s in top_s if s in f3a)}])
s10 = {s for s, n in sref.items() if n >= 10}
ssets = defaultdict(set)
for e, s in src:
    if s in s10:
        ssets[s].add(e)
spc = pair_counts(ssets, 5)
GS = graph({n for p in spc for n in p}, spc)
MS, QS = louvain(GS)
ss = Counter(MS.values())
T6b = []
for c in sorted(ss):
    ks = sorted((s for s, x in MS.items() if x == c), key=lambda s: (-sref[s], s))
    for j, s in enumerate(ks[:5], 1):
        T6b.append({"cluster": c, "cluster_size": len(ks), "rank": j, "source": L.cut_words(s, 20), "references": sref[s]})
tab("T6b_source_cocitation_clusters", ["cluster", "cluster_size", "rank", "source", "references"], T6b)
f6c = kv(f133("T6c"))
tab("T6b2_source_cocitation_summary", ["measure", "value"], [
    {"measure": "sources with >= 10 references", "value": len(s10)}, {"measure": "sources with >= 1 edge", "value": GS.number_of_nodes()},
    {"measure": "edges: source pairs cited together by >= 5 records", "value": GS.number_of_edges()}, {"measure": "Louvain clusters", "value": len(ss)},
    {"measure": "modularity Q", "value": QS}, {"measure": "F13.3 (metaTagExtraction sources): clusters", "value": f6c["Louvain clusters"]}])
NUM["T6"] = {"recognised": len(src), "share": r4(len(src) / total_refs), "top30_overlap_T3a": sum(1 for s in top_s if s in f3a),
             "sources10": len(s10), "clusters": len(ss), "Q": QS, "top1": top_s[0], "top1_refs": sref[top_s[0]]}

# ---------------- step 7: T0 strings (F13.3) against the work key (this phase) ----------------
T0 = [{"measure": m, "strings_F13_3": a, "source_F13_3": sa, "work_key_F13_3b": b, "source_F13_3b": sb} for m, a, sa, b, sb in (
    ("distinct references (strings) / works", f2a["distinct cited references (strings counted by citations())"], "T2a", len(citing), "T2a"),
    ("cited by >= 5 records", f2a["with >= 5 citing records"], "T2a", t5, "T2a"),
    ("cited by >= 10 records", f2a["with >= 10 citing records"], "T2a", t10, "T2a"),
    ("local citation links", f4a["LCS, total (local citation links)"], "T4a", nl, "T3a"),
    ("records cited inside the corpus", f4a["records with LCS > 0"], "T4a", len(LCS), "T3a"),
    ("coupling edges (>= 2 shared)", f5a["edges (pairs sharing >= 2 references)"], "T5a", G4.number_of_edges(), "T4a"),
    ("coupling clusters with >= 10 records", f5a["clusters with >= 10 records"], "T5a", len(big), "T4a"),
    ("co-citation nodes (>= 4 citing records)", f6a["nodes: references with >= 4 citing records"], "T6a", len(SEL5), "T5a"),
    ("co-citation edges (>= 3)", f6a["edges: pairs co-cited by >= 3 records"], "T6a", G5.number_of_edges(), "T5a"),
    ("co-citation clusters with >= 5 nodes", f6a["clusters with >= 5 nodes"], "T6a", len(big5), "T5a"))]
tab("T0_strings_vs_work_key", ["measure", "strings_F13_3", "source_F13_3", "work_key_F13_3b", "source_F13_3b"], T0)
import PIL
import sklearn
NUM["environment"] = {"python": sys.version.split()[0], "networkx": nx.__version__, "scikit-learn": sklearn.__version__,
                      "matplotlib": matplotlib.__version__, "Pillow": PIL.__version__, "keys": "R 4.6.1 (F13.3's work_key via f133_lib.R)"}
L.jdump(NUM, OUT / "F13_3b_numbers.json")
print("steps 1-7:", {"works": len(citing), "ge2/5/10": [t2, t5, t10], "links": nl, "citing": len(citing_recs), "cited": len(LCS),
                     "coupling": [G4.number_of_nodes(), G4.number_of_edges(), len(big)], "cocitation": [len(SEL5), G5.number_of_edges(), len(big5)],
                     "sources": len(src)})
