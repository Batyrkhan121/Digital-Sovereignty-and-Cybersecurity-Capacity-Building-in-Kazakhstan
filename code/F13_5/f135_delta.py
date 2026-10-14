"""Phase F13.5 - step 6: deltas in two steps (copied from F12.3c's delta; changed: (iv) D0 frame effect (I2 x v3 -> E1 x v3) and
D1 thesaurus effect (E1 x v3 -> E1 x v4) with the merged pairs; D2 clusters by leading keywords, I2 x v3 against E1 x v4; D3
figure labels; D4 v1 -> v2 -> v3 -> v4 with each version's frame). Reads only phase_F12_3c/tables/ and phase_F12_3c/figures/*.csv
(F12.3c's own numbers come from its D2_summary.csv and D4_versions_summary.csv), and this phase's tables. Writes tables/D0_* -
D4_* and F13_5_delta.json. Deterministic."""
import sys
sys.dont_write_bytecode = True

import json
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f135_lib as L

PT, PF = L.PREV_T, L.PREV_F
VT, CT, CF = L.V3E1, L.TABLES, L.FIGURES
MEASURES = (("unique_keywords", "unique keywords"), ("nodes", "nodes (>= 5 records, with generic)"), ("edges", "edges (with generic)"),
            ("nodes_clustered", "nodes clustered (generic excluded)"), ("edges_clustered", "edges clustered"),
            ("clusters", "clusters (generic excluded)"), ("isolated_clustered_nodes", "one-keyword clusters"), ("modularity", "modularity Q"))


def nodes(folder, kind):
    return {r["keyword"]: r for r in L.read_csv_path(folder / f"T3_{kind}_nodes.csv")}


def members(nd):
    m = defaultdict(set)
    for k, r in nd.items():
        if r["cluster"]:
            m[int(r["cluster"])].add(k)
    return m


def leading(folder, kind):
    return {int(r["cluster"]): r for r in L.read_csv_path(folder / f"T5_{kind}_clusters.csv")}


def prev_numbers():
    """F12.3c's (I2 x v3) measures from its D2_summary.csv (column v3)."""
    out = defaultdict(dict)
    for r in L.read_csv_path(PT / "D2_summary.csv"):
        v = r["v3"]
        out[r["layer"]][r["measure"]] = float(v) if "." in v else int(v)
    return out


def labels_of_t3(folder):
    """Figure labels as the figure defines them: clustered (non-generic) author nodes with >= 8 records."""
    return sum(1 for r in nodes(folder, "author").values() if r["generic"] == "0" and int(r["records"]) >= 8)


out = {}
th4 = L.read_csv_path(CT / "thesaurus.csv")
alias = {r["from"]: r["to"] for r in th4}
P = prev_numbers()
NV3 = L.jload(VT / "numbers_v3_on_E1.json")
NV4 = L.jload(L.OUT / "F13_5_numbers.json")


for step, (fa, fb, la, lb, na, nb, title, note) in {
        "D0": (PT, VT, "I2_v3", "E1_v3", P, NV3, "D0. Frame effect: I2 x v3 (F12.3c) against E1 x v3 (step 1)",
               "Same thesaurus (v3), different frame: the enriched layer I2 (838 records, F12.3c) and the full export E1 (841)."),
        "D1": (VT, CT, "E1_v3", "E1_v4", NV3, NV4, "D1. Thesaurus effect: E1 x v3 against E1 x v4",
               "Same frame (E1), thesaurus v3 against v4. The merged pairs are in D1_merged_pairs.csv.")}.items():
    summ, nrows = [], []
    for kind in ("author", "index"):
        x, y = na[kind], nb[kind]
        for key, lab in MEASURES:
            summ.append({"layer": kind, "measure": lab, la: x.get(key, ""), lb: y[key]})
        a, b = nodes(fa, kind), nodes(fb, kind)
        for k in sorted(set(a) | set(b)):
            ra, rb = a.get(k), b.get(k)
            if ra and rb and ra["records"] == rb["records"]:
                continue
            nrows.append({"layer": kind, "keyword": k, f"records_{la}": ra["records"] if ra else "", f"records_{lb}": rb["records"] if rb else "",
                          f"cluster_{la}": ra["cluster"] if ra else "", f"cluster_{lb}": rb["cluster"] if rb else "",
                          "change": "added" if not ra else "removed" if not rb else "records changed",
                          "v4_form_of_removed": alias.get(k, "") if not rb else ""})
    order = {"removed": 0, "added": 1, "records changed": 2}
    nrows.sort(key=lambda r: (r["layer"], order[r["change"]], r["keyword"]))
    f = ["layer", "measure", la, lb]
    L.write_csv(CT / f"{step}_summary.csv", f, summ)
    L.write_md(CT / f"{step}_summary.md", title, f, summ, note)
    f = ["layer", "keyword", f"records_{la}", f"records_{lb}", f"cluster_{la}", f"cluster_{lb}", "change", "v4_form_of_removed"]
    L.write_csv(CT / f"{step}_nodes_delta.csv", f, nrows)
    out[step] = {"summary": summ, "counts": {kind: {c: sum(1 for r in nrows if r["layer"] == kind and r["change"] == c)
                                                    for c in order} for kind in ("author", "index")},
                 "author_rows": [r for r in nrows if r["layer"] == "author"]}
    L.write_md(CT / f"{step}_author_nodes_delta.md", title.split(":")[0] + ": author-keyword nodes added, removed or changed",
               f[1:], out[step]["author_rows"], "Index-keyword rows: " + f"{step}_nodes_delta.csv. Cluster numbers are each run's own labels.")

# D1: the merged pairs (v4 rows and retargeted v3 rows that rewrote keywords in E1)
applied = {r["from"]: int(r["keyword_occurrences_rewritten"]) for r in L.read_csv_path(CT / "thesaurus_applied.csv")}
merged = [{"from": r["from"], "to": r["to"], "version": r["version"], "retargeted": int("retargeted in v4" in r["rule"]),
           "keyword_occurrences_rewritten": applied.get(r["from"], 0)}
          for r in th4 if r["version"] == "v4" or "retargeted in v4" in r["rule"]]
merged.sort(key=lambda r: (-r["keyword_occurrences_rewritten"], r["from"]))
f = ["from", "to", "version", "retargeted", "keyword_occurrences_rewritten"]
L.write_csv(CT / "D1_merged_pairs.csv", f, merged)
out["D1_merged"] = {"rows": len(merged), "applied": sum(1 for r in merged if r["keyword_occurrences_rewritten"]),
                    "occurrences": sum(r["keyword_occurrences_rewritten"] for r in merged)}

# D2: clusters by leading keywords, I2 x v3 against E1 x v4
for kind in ("author", "index"):
    a, b = nodes(PT, kind), nodes(CT, kind)
    m3, m4 = members(a), members(b)
    l3, l4 = leading(PT, kind), leading(CT, kind)
    where4 = {k: int(r["cluster"]) for k, r in b.items() if r["cluster"]}
    rows = []
    for c in sorted(l3):
        lead = l3[c]["largest_keyword"]
        c4 = where4.get(lead) or where4.get(alias.get(lead, ""))
        common = len({alias.get(k, k) for k in m3[c]} & m4[c4]) if c4 else 0
        rows.append({"cluster_I2_v3": c, "leading_I2_v3": lead, "size_I2_v3": l3[c]["size"], "cluster_E1_v4": c4 or "",
                     "leading_E1_v4": l4[c4]["largest_keyword"] if c4 else "(not a clustered node)", "size_E1_v4": l4[c4]["size"] if c4 else "",
                     "common_keywords": common})
    f = ["cluster_I2_v3", "leading_I2_v3", "size_I2_v3", "cluster_E1_v4", "leading_E1_v4", "size_E1_v4", "common_keywords"]
    L.write_csv(CT / f"D2_{kind}_clusters_delta.csv", f, rows)
    L.write_md(CT / f"D2_{kind}_clusters_delta.md", f"D2 ({kind} keywords). Clusters of I2 x v3 (F12.3c) matched in E1 x v4 by the leading keyword",
               f, rows, "E1 x v4 cluster = the cluster holding the leading keyword of I2 x v3 (or its thesaurus v4 target); common = keywords "
               "of the I2 x v3 cluster (mapped by v4) also in the E1 x v4 cluster.")
    out["D2_" + kind] = rows
    rev = []
    where3 = {alias.get(k, k): int(r["cluster"]) for k, r in a.items() if r["cluster"]}
    for c in sorted(l4):
        lead = l4[c]["largest_keyword"]
        c3 = where3.get(lead)
        rev.append({"cluster_E1_v4": c, "leading_E1_v4": lead, "size_E1_v4": l4[c]["size"], "cluster_I2_v3": c3 or "",
                    "leading_I2_v3": l3[c3]["largest_keyword"] if c3 else "(not a clustered node)", "size_I2_v3": l3[c3]["size"] if c3 else "",
                    "common_keywords": len({alias.get(k, k) for k in m3[c3]} & m4[c]) if c3 else 0})
    f = ["cluster_E1_v4", "leading_E1_v4", "size_E1_v4", "cluster_I2_v3", "leading_I2_v3", "size_I2_v3", "common_keywords"]
    L.write_csv(CT / f"D2_{kind}_clusters_reverse.csv", f, rev)
    L.write_md(CT / f"D2_{kind}_clusters_reverse.md", f"D2 reverse ({kind} keywords). Clusters of E1 x v4 matched in I2 x v3 by the leading keyword",
               f, rev, "I2 x v3 cluster = the F12.3c cluster holding the E1 x v4 leading keyword (F12.3c keywords mapped by v4).")
    out["D2rev_" + kind] = rev

# D3: figure labels, F12.3c against this phase
fn3 = {r["keyword"]: r for r in L.read_csv_path(PF / "Fig_coword_author_keywords_nodes.csv")}
fn4 = {r["keyword"]: r for r in L.read_csv_path(CF / "Fig_coword_author_keywords_nodes.csv")}
lab3 = {k for k, r in fn3.items() if r["labelled"] == "1"}
lab4 = {k for k, r in fn4.items() if r["labelled"] == "1"}
rows = [{"keyword": k, "label_change": "added", "v4_form": ""} for k in sorted(lab4 - lab3)] + \
       [{"keyword": k, "label_change": "removed", "v4_form": alias.get(k, "")} for k in sorted(lab3 - lab4)]
L.write_csv(CT / "D3_figure_labels_delta.csv", ["keyword", "label_change", "v4_form"], rows)
e3 = len(L.read_csv_path(PF / "Fig_coword_author_keywords_edges.csv"))
e4 = len(L.read_csv_path(CF / "Fig_coword_author_keywords_edges.csv"))
L.write_md(CT / "D3_figure_labels_delta.md", "D3. Figure labels, F12.3c (I2 x v3) against F13.5 (E1 x v4)", ["keyword", "label_change", "v4_form"], rows,
           f"Nodes {len(fn3)} -> {len(fn4)}; edges {e3} -> {e4}; labels {len(lab3)} -> {len(lab4)}. v4_form: the thesaurus v4 target of a "
           "removed label, when it has one.")
out["D3"] = {"labels_added": sorted(lab4 - lab3), "labels_removed": sorted(lab3 - lab4), "nodes": [len(fn3), len(fn4)], "edges": [e3, e4],
             "labels": [len(lab3), len(lab4)]}

# D4: v1 -> v2 -> v3 -> v3 on E1 -> v4
cols = ["v1 (F12.3; I2, 838)", "v2 (F12.3b; I2, 838)", "v3 (F12.3c; I2, 838)", "v3 on E1 (F13.5 step 1; E1, 841)", "v4 (F13.5; E1, 841)"]
key_of = {"unique keywords": "unique_keywords", "nodes (>= 5 records, with generic)": "nodes", "edges (with generic)": "edges",
          "clusters (generic excluded)": "clusters", "one-keyword clusters": "isolated_clustered_nodes", "modularity Q": "modularity"}
rows = []
for r in L.read_csv_path(PT / "D4_versions_summary.csv"):
    row = {"layer": r["layer"], "measure": r["measure"], cols[0]: r["v1 (F12.3)"], cols[1]: r["v2 (F12.3b)"], cols[2]: r["v3 (F12.3c)"]}
    if r["layer"] in ("author", "index"):
        row[cols[3]] = NV3[r["layer"]][key_of[r["measure"]]]
        row[cols[4]] = NV4[r["layer"]][key_of[r["measure"]]]
    elif r["layer"] == "figure":
        row[cols[3]] = labels_of_t3(VT)
        row[cols[4]] = NV4["figure"]["labelled"]
    else:
        row[cols[3]] = NV3["thesaurus_rows"]
        row[cols[4]] = NV4["thesaurus_rows"]
    rows.append(row)
f = ["layer", "measure"] + cols
L.write_csv(CT / "D4_versions_summary.csv", f, rows)
L.write_md(CT / "D4_versions_summary.md", "D4. Summary v1 -> v2 -> v3 -> v4, with each version's frame", f, rows,
           "Sources: phase F12.3c's D4_versions_summary.csv (v1-v3, frame I2 = the enriched layer, 838 records) and this phase's numbers "
           "(E1 = the full Scopus export, 841 records). Figure labels of 'v3 on E1': clustered author nodes with >= 8 records (no figure is "
           "drawn in step 1).")
out["D4"] = rows

# T6 / T7 against F12.3c
t6a = [r["keyword"] for r in L.read_csv_path(PT / "T6_author_keywords_by_period.csv")]
t6b = [r["keyword"] for r in L.read_csv_path(CT / "T6_author_keywords_by_period.csv")]
out["T6"] = {"entered_top30": sorted(set(t6b) - set(t6a)), "left_top30": sorted(set(t6a) - set(t6b))}
t7a = {r["group"]: r for r in L.read_csv_path(PT / "T7_blind_spots_keywords.csv")}
t7b = {r["group"]: r for r in L.read_csv_path(CT / "T7_blind_spots_keywords.csv")}
out["T7"] = {g: {"I2_v3": t7a[g]["records_either"], "E1_v4": t7b[g]["records_either"], "author_I2_v3": t7a[g]["records_author_kw"],
                 "author_E1_v4": t7b[g]["records_author_kw"]} for g in t7a}
L.jdump(out, L.OUT / "F13_5_delta.json")
print(json.dumps({k: v for k, v in out.items() if k in ("D1_merged", "D3", "T6", "T7")}, ensure_ascii=False, indent=1))
for step in ("D0", "D1"):
    print(step, out[step]["counts"])
    for r in out[step]["summary"]:
        print(" ", r)
    for r in out[step]["author_rows"]:
        print("  author", r)
for kind in ("author", "index"):
    for r in out["D2_" + kind]:
        print("D2", kind, r)
