"""Phase F13.5 - the report, built from the phase's records (copied from F12.3c's report; changed: sections for E1, thesaurus v4,
D0-D4, S1-S2 and the pending registry row). Prose hard-wrapped (<= 25 words a line, gate G2)."""
import sys
sys.dont_write_bytecode = True

import json
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f135_lib as L

W = L.wrap
CF = ["pair", "class", "records_author_a", "records_author_b", "records_index_a", "records_index_b", "decision", "reason"]


def j(p):
    return json.loads(Path(p).read_bytes().decode("utf-8"))


def md(name, demote=True, folder=None):
    t = ((folder or L.TABLES) / name).read_bytes().decode("utf-8")
    return t.replace("## ", "### ", 1) if demote else t


def rows(name, folder=None):
    p = (folder or L.TABLES) / name
    return L.read_csv_path(p) if p.exists() else []


def csv_as_md(title, name, folder=None, limit=None, note=""):
    r = rows(name, folder)
    if not r:
        return f"### {title}\n\n(none)\n"
    shown = r if limit is None else r[:limit]
    return f"### {title}\n\n" + (W(note) + "\n\n" if note else "") + L.md_table(list(r[0].keys()), shown) + "\n"


def bullets(items, width=22):
    return "\n".join("- " + W(x, width).replace("\n", "\n  ") for x in items) + "\n"


def clusters_text(kind):
    top = defaultdict(list)
    for r in rows(f"T5_{kind}_cluster_top10.csv"):
        top[int(r["cluster"])].append(f"{r['keyword']} ({r['records']})")
    return "\n".join(W(f"- C{c}: " + "; ".join(top[c])).replace("\n", "\n  ") for c in sorted(top)) + "\n"


def build(row, gates, pending=None):
    num = j(L.OUT / "F13_5_numbers.json")
    nv3 = j(L.V3E1 / "numbers_v3_on_E1.json")
    stamp = j(L.OUT / "F13_5_brief_stamp.json")
    st = j(L.RUN_LOGS / "thesaurus_v4_status.json")
    dl = j(L.OUT / "F13_5_delta.json")
    sb = j(L.OUT / "F13_5_stability.json")
    ver = rows("phase_F13_5_independent_verification.csv", L.OUT)
    a, i = num["author"], num["index"]
    p = num["parameters"]
    sh = stamp["E1_shape"]
    out = ["# Phase F13.5 - co-word map on the new frame E1 (full Scopus export, 841 records) with thesaurus v4\n"]
    status = row["status"] if row else "(dry run - no pending registry row yet)"
    out.append(W(f"Status: {status}. Repository: {stamp['root']} (where PHASE_REGISTRY.csv is; the registry was neither read nor written "
                 f"by this phase). Brief: F13_5_brief.md (sha256 {stamp['brief_sha256']}). Input E1: {stamp['E1']} (sha256 {stamp['E1_sha256']}; "
                 f"equal to README_exports.txt: {stamp['E1_equal_README']}). Thesaurus v3 read from phase F12.3c (sha256 "
                 f"{stamp['thesaurus_v3_sha256']}, {stamp['thesaurus_v3_rows']} rows). The layer I2 (jsonl) is no longer read. No edit to "
                 "the manuscript, the package, main.qmd, references.bib or the folders phase_F12_3, phase_F12_3b and phase_F12_3c. This phase "
                 "replaces F12.3c for publication. The parallel session's folder phase_F13_2 was neither read nor snapshotted.") + "\n")

    out.append("## 1. Parameters\n")
    out.append(bullets([
        f"Records: E1 = the full Scopus export of 2026-10-13 ({sh['rows']} records, years {sh['years'][0]}-{sh['years'][1]}); only EID, "
        "Year, Title, Author Keywords and Index Keywords are kept from each row (R13). Keyword cells split at '; '. Non-empty cells: "
        f"author {sh['author_cells_non_empty']}, index {sh['index_cells_non_empty']}; {sh['semicolons_not_followed_by_space']} keyword "
        "parts end in a stray ';' (removed by the normalisation).",
        "Normalisation (unchanged; one function for both kinds): lowercase; hyphens and dashes to spaces; whitespace collapsed; leading and "
        "trailing punctuation trimmed (a closing bracket kept when the keyword holds an opening one); no stemming; then the thesaurus (one pass).",
        f"Generic keywords (flag generic = 1, kept in T1-T4, excluded from clustering and from the figure): {', '.join(p['generic'])}.",
        f"Nodes: keywords in >= {p['node_threshold']} records (sensitivity {p['sensitivity_thresholds']}); edges: co-occurrence in >= "
        f"{p['edge_min_records']} records; weight = co-occurrence records; association strength = {p['association_strength']}.",
        f"Clustering: {p['clustering']}. Deterministic: nodes and edges inserted in sorted order; the algorithm uses no random seed.",
        f"Layout: {p['layout']}. Labels on nodes with >= {p['label_min_records']} records.",
        "Versions: " + ", ".join(f"{k} {v}" for k, v in sorted(num["versions"].items())) + ".",
    ]))

    out.append("## 2. Step 1 - intermediate run E1 x v3 (tables/v3_on_E1/, not for publication)\n")
    out.append(L.md_table(["layer", "records_with_keywords", "unique_keywords", "nodes", "edges", "clusters", "modularity"],
                          [{"layer": k, **nv3[k]} for k in ("author", "index")]) + "\n")
    out.append(W(f"Records with author / index keywords: {nv3['author']['records_with_keywords']} / {nv3['index']['records_with_keywords']} "
                 "(expected 797 / 586). Thesaurus v3 as it is (579 rows; rows that rewrote at least one keyword of E1: "
                 f"{nv3['thesaurus_rows_applied']}).") + "\n")

    out.append("## 3. Thesaurus v4 (tables/thesaurus.csv, applied to both kinds)\n")
    cand = rows("thesaurus_candidates_v4.csv")
    bc = st["by_class"]
    out.append(W(f"Candidates from the T1 tables of E1 x v3 (both layers; {st['T1_forms']} forms, {st['T1_forms_new_to_frame']} of them new "
                 "to the frame, i.e. not in F12.3c's T1). Classes: c' bracket in mid-string; c bracket (new form) = v3's rule on final-bracket "
                 "forms new to the frame, with an abbreviation test (below); f abbreviation inside a multi-word keyword; t the tail as in v3. "
                 "All classes run on resolved forms and are repeated until no new merge appears "
                 f"({st['passes']} passes). " + "; ".join(f"{c}: merge {v['merge']}, keep {v['keep']}" for c, v in bc.items()) + ".") + "\n")
    out.append(W(f"Abbreviation table for class f: {st['table_size']} abbreviations, built from the thesaurus rows (v1 'abbreviation to long "
                 "form' and v1 bracket rows; v3 classes c and e; v4 bracket rows) plus the brief's explicit list of 20; full table in "
                 "run_logs/abbreviation_table_v4.json. Ambiguous (several final long forms): "
                 + "; ".join(f"{k} ({' / '.join(v)})" for k, v in st["table_ambiguous"].items())
                 + f". Not read as abbreviations (English function words, executor's guard): {', '.join(st['table_entries_not_considered'])}.") + "\n")
    out.append("### Class c' (bracket in mid-string), complete\n\n" + L.md_table(CF, [r for r in cand if r["class"].startswith("c'")]) + "\n")
    out.append("### Class f (abbreviation inside a multi-word keyword): merges, complete\n\n"
               + L.md_table(CF + ["merge_to"], [r for r in cand if r["class"].startswith("f") and r["decision"] == "merge"]) + "\n")
    keeps_f = [r for r in cand if r["class"].startswith("f") and r["decision"] == "keep"]
    out.append("### Class f keeps - for the author's decision (not merged)\n\n" + W(
        f"{len(keeps_f)} keywords hold one abbreviation from the table, but the expanded form occurs neither in T1 nor among the thesaurus "
        "'to' values (or would exceed 6 words, or the abbreviation is ambiguous). Each could be merged by hand if the expanded form is "
        "wanted. Some expansions are spurious and need no action (ho in 'ho momorphic encryptions', li in 'li fi', stem in 'drill stem "
        "test', ble -> 'bluetooth low energies').") + "\n\n" + L.md_table(CF, keeps_f) + "\n")
    out.append("### Class c bracket (new form), complete\n\n" + L.md_table(CF, [r for r in cand if r["class"].startswith("c bracket")]) + "\n")
    out.append("### Class t (tail), complete\n\n" + L.md_table(CF, [r for r in cand if r["class"].startswith("t ")]) + "\n")
    out.append(W(f"Tail pairs: {st['tail_pairs']}, every one with at least one form new to the frame ({st['tail_pairs_with_a_new_form']}); most are "
                 "Scopus index terms of E1 (singular and plural of one term).") + "\n")
    out.append("### Retargeted v3 rows (their 'to' merged in v4)\n\n" + L.md_table(["from", "version", "to_v3", "to_v4"], st["retargeted_v3_rows"]) + "\n")
    th = {r["from"]: r for r in rows("thesaurus_applied.csv")}
    v4 = rows("thesaurus.csv")
    out.append(W(f"Thesaurus v4: {st['rows_v4']} rows = {st['rows_v3']} v3 rows (versions v1, v2, v3) + {st['rows_new']} new (version v4); "
                 f"from and to disjoint; no chain; limit {st['limit']}. Rows that rewrote at least one keyword of E1: {num['thesaurus_rows_applied']}. "
                 "Full table (version, from, to, rule, keyword occurrences rewritten in E1):") + "\n")
    out.append(L.md_table(["version", "from", "to", "rule", "keyword_occurrences_rewritten"],
                          [{**r, "keyword_occurrences_rewritten": th.get(r["from"], {}).get("keyword_occurrences_rewritten", "")}
                           for r in sorted(v4, key=lambda r: (r["version"], r["from"]))]) + "\n")

    out.append("## 4. R1. Residual scan of T1 after v4 (both layers)\n")
    r1 = rows("R1_residual_scan.csv")
    gated = ("a", "b", "c", "c'", "d", "f")
    out.append(W("Classes a, b, c, c', d, f: " + "; ".join(f"{c} residual {sum(1 for r in r1 if r['class'] == c and r['status'] == 'residual')}, "
                                                          f"declared keep {sum(1 for r in r1 if r['class'] == c and r['status'] == 'declared keep')}"
                                                          for c in gated)
                 + f". Class e (printed residue: acronyms with a single long form left unmerged): {sum(1 for r in r1 if r['class'] == 'e')}.") + "\n")
    out.append(L.md_table(["class", "a", "b", "records_author_a", "records_author_b", "records_index_a", "records_index_b", "status", "note"],
                          [r for r in r1 if r["class"] != "f"]) + "\n")
    out.append(W("Class f rows of R1 are the declared keeps listed in section 3 (tables/R1_residual_scan.csv holds them all).") + "\n")

    for kind, lab, res, sec in (("author", "author keywords - main analysis", a, "5"), ("index", "index keywords - secondary analysis", i, "6")):
        out.append(f"## {sec}. {lab.capitalize()}\n")
        out.append(md(f"T1_{kind}_frequencies_top50.md"))
        out.append(md(f"T2_{kind}_threshold_sensitivity.md"))
        out.append(md(f"T5_{kind}_clusters.md"))
        out.append("Top 10 keywords per cluster (records):\n")
        out.append(clusters_text(kind))
        out.append(W(f"Nodes {res['nodes']} and edges {res['edges']} with generic keywords; clustered network {res['nodes_clustered']} nodes, "
                     f"{res['edges_clustered']} edges; {res['isolated_clustered_nodes']} nodes have no edge there and form one-keyword "
                     f"clusters. Modularity {res['modularity']} ({res['clusters']} clusters); with generic keywords kept "
                     f"{res['modularity_with_generic']} ({res['clusters_with_generic']} clusters).") + "\n")
        out.append(md(f"T3_{kind}_nodes.md"))
        if kind == "author":
            out.append(csv_as_md(f"T4 ({lab}). Edges", f"T4_{kind}_edges.csv"))
        else:
            out.append(csv_as_md(f"T4 ({lab}). Edges, the 100 strongest", f"T4_{kind}_edges.csv", limit=100,
                                 note=f"All {res['edges']} edges: tables/T4_index_edges.csv."))

    out.append("## 7. Periods, blind spots, title bigrams\n")
    out.append(md("T6_author_keywords_by_period.md"))
    out.append(md("T7_blind_spots_keywords.md"))
    out.append(csv_as_md("T7. Matched keywords", "T7_blind_spots_matched_keywords.csv"))
    out.append(md("T8_title_bigrams_vs_keywords.md"))
    out.append(csv_as_md("T8b. Author keywords top 20 against the title top 20", "T8b_keywords_vs_title_bigrams.csv"))

    out.append("## 8. Figure\n")
    fg = num["figure"]
    out.append(W("Files: figures/Fig_coword_author_keywords.pdf, .png (300 dpi), .tif (300 dpi, LZW, from the PNG); data: "
                 "figures/Fig_coword_author_keywords_nodes.csv (keyword, records, cluster, x, y, labelled) and _edges.csv. Built by "
                 "programs/f135_coword.py; nobody viewed it (R18). No title inside the figure. Generic keywords are not drawn; "
                 f"{fg['nodes']} nodes, {fg['edges']} edges, {fg['labelled']} labels.") + "\n")
    out.append("Draft caption:\n")
    cap = (f"Co-word map of author keywords in the Scopus reporting frame (full export of 13 October 2026, 2003-2025; "
           f"{a['records_with_keywords']} of {num['records_E1']} records carry author keywords). Nodes are the {fg['nodes']} keywords that "
           f"occur in at least five records, after normalisation and a {num['thesaurus_rows']}-row thesaurus; the field-level keywords "
           "(cybersecurity, information security, security, Kazakhstan) are omitted. Node area is proportional to the number of records; "
           "colour shows the cluster (greedy modularity on association strength); grey nodes have no co-occurrence link. Lines join "
           "keywords that co-occur in at least two records. Labels are shown for keywords in at least eight records. Source: Authors' own work.")
    out.append("> " + W(cap).replace("\n", "\n> ") + "\n")

    out.append("## 9. Deltas: frame effect (D0) and thesaurus effect (D1); D2-D4\n")
    out.append(md("D0_summary.md"))
    out.append(md("D0_author_nodes_delta.md"))
    d0 = {(r["layer"], r["measure"]): r for r in dl["D0"]["summary"]}
    ci = dl["D0"]["counts"]["index"]
    ti = rows("T1_index_frequencies.csv", L.V3E1)[:6]
    out.append(W(f"Index layer, D0: nodes added {ci['added']}, removed {ci['removed']}, records changed {ci['records changed']} "
                 "(tables/D0_nodes_delta.csv). E1's Index Keywords carry the full set of Scopus controlled terms (most frequent on E1: "
                 + "; ".join(f"{r['keyword']} {r['records']}" for r in ti) + "), which the enriched layer I2 held only in part; the "
                 f"index network therefore grows from {d0[('index', 'nodes (>= 5 records, with generic)')]['I2_v3']} to "
                 f"{d0[('index', 'nodes (>= 5 records, with generic)')]['E1_v3']} nodes with the same thesaurus.") + "\n")
    out.append(md("D1_summary.md"))
    out.append(md("D1_author_nodes_delta.md"))
    dm = dl["D1_merged"]
    out.append(csv_as_md("D1. Merged pairs that rewrote keywords of E1 (v4 rows and retargeted v3 rows)", "D1_merged_pairs.csv",
                         note=f"{dm['rows']} rows, {dm['applied']} of them applied to E1, {dm['occurrences']} keyword occurrences rewritten."))
    out.append(md("D2_author_clusters_delta.md"))
    out.append(md("D2_author_clusters_reverse.md"))
    out.append(md("D2_index_clusters_delta.md"))
    out.append(md("D2_index_clusters_reverse.md"))
    out.append(md("D3_figure_labels_delta.md"))
    out.append(md("D4_versions_summary.md"))
    d2 = dl["D2_author"]
    themes = [r for r in d2 if int(r["size_I2_v3"]) >= 5]
    kept = [f"{r['leading_I2_v3']} ({r['common_keywords']} of {r['size_I2_v3']})" for r in themes if r["leading_E1_v4"] == r["leading_I2_v3"]]
    moved = [f"{r['leading_I2_v3']} -> the cluster led by {r['leading_E1_v4']} ({r['common_keywords']} of {r['size_I2_v3']} keywords)"
             for r in themes if r["leading_E1_v4"] != r["leading_I2_v3"]]
    s1 = {(r["layer"], r["comparison"]): r for r in sb["S1"]}
    ca = dl["D0"]["counts"]["author"]
    d1a = dl["D1"]["counts"]["author"]
    para = (f"Themes. Of the {len(themes)} author themes of F12.3c (clusters of at least five keywords), {len(kept)} keep their leading "
            f"keyword on E1 x v4 (keywords shared in brackets): {'; '.join(kept)}. Regrouped: {'; '.join(moved) or 'none'}. The regrouping "
            "is a frame effect: E1 x v3 and E1 x v4 give the same partition on their common nodes (Rand "
            f"{s1[('author', 'E1 x v3 vs E1 x v4')]['rand_index']}), while I2 x v3 against E1 x v4 gives Rand "
            f"{s1[('author', 'I2 x v3 (F12.3c) vs E1 x v4')]['rand_index']} (adjusted {s1[('author', 'I2 x v3 (F12.3c) vs E1 x v4')]['adjusted_rand_index']}); "
            f"on the author layer the frame removed {ca['removed']} node, added {ca['added']} and changed the records of {ca['records changed']} "
            "by one or two (D0), enough to move the boundary between machine learning, artificial intelligence, network security and the "
            f"internet of things. The thesaurus effect on the author map: {d1a['removed']} nodes merged away, {d1a['added']} added under their "
            f"long forms, {d1a['records changed']} grown (D1), and the labels of D3. Blind spots (T7): "
            + ("unchanged in every group." if all(v["I2_v3"] == v["E1_v4"] for v in dl["T7"].values()) else
               "; ".join(f"{g} {v['I2_v3']} -> {v['E1_v4']}" for g, v in dl["T7"].items() if v["I2_v3"] != v["E1_v4"])))
    out.append(W(para) + "\n")

    out.append("## 10. Stability of the partition (S1, S2)\n")
    out.append(md("S1_partition_agreement.md"))
    out.append(md("S2_algorithm_sensitivity.md"))
    out.append(csv_as_md("S2b. Leading pairs of the greedy clusters (size >= 5) under Louvain, seeds 1-20", "S2b_leading_pairs.csv"))
    sm = {r["seed"]: r for r in sb["S2"]["summary"]}
    weak = [f"{r['keyword_a']} / {r['keyword_b']} ({r['share_of_runs']})" for r in sb["S2"]["pairs"] if float(r["share_of_runs"]) < 1]
    big = sorted({r["cluster"] for r in sb["S2"]["pairs"]})
    min_share = min(float(r["share_of_runs"]) for r in sb["S2"]["pairs"])
    same_runs = sum(1 for r in sb["S2"]["runs"] if r["adjusted_rand_vs_greedy"] == 1.0)
    para = (f"Reading. Louvain with 20 seeds gives {sm['min']['clusters']}-{sm['max']['clusters']} clusters (greedy: {sm['greedy (T5)']['clusters']}), "
            f"modularity {sm['min']['modularity']}-{sm['max']['modularity']} (greedy {sm['greedy (T5)']['modularity']}), Rand against the "
            f"greedy partition {sm['min']['rand_vs_greedy']}-{sm['max']['rand_vs_greedy']} (median {sm['median']['rand_vs_greedy']}; adjusted "
            f"{sm['min']['adjusted_rand_vs_greedy']}-{sm['max']['adjusted_rand_vs_greedy']}); {same_runs} of 20 runs give exactly the greedy "
            f"partition. The top-3 pairs of all {len(big)} clusters of five or more keywords stay together in at least {round(100 * min_share)} % "
            f"of runs; pairs below 100 %: {'; '.join(weak) or 'none'}. Themes that hold under any "
            "partition: cryptography (encryption, digital signature), identification (fuzzy logic, detection), vulnerability (smart city, "
            "threat), risk (information system, risk assessment), intrusion detection system (cyber threat, SIEM), data security (quantum "
            "cryptography, QKD), FPGA (elliptic curve cryptography, AES), and - within E1 - machine learning with artificial intelligence and "
            "deep learning, and the internet of things with neural networks and industrial IoT. Artefacts: the exact boundary between the "
            f"machine-learning and IoT themes (it moved with the frame, S1) and the {a['isolated_clustered_nodes']} one-keyword clusters (no "
            "co-occurrence link). Name themes in the article by their leading keywords, not by cluster numbers.")
    out.append(W(para) + "\n")

    out.append("## 11. For the professor (section 3.3)\n")
    stable = [r["leading_I2_v3"] for r in themes if r["leading_E1_v4"] == r["leading_I2_v3"] and int(r["common_keywords"]) * 2 >= int(r["size_I2_v3"])]
    ml = next(r for r in d2 if r["leading_I2_v3"] == "machine learning")
    t6 = {r["keyword"]: r for r in rows("T6_author_keywords_by_period.csv")}
    per = num["periods"]
    bs = num["blind_spots"]
    tb = num["title_bigrams"]
    prof = [
        f"Main themes (E1, author keywords, {a['clusters']} clusters, modularity {a['modularity']}), by leading keywords: machine learning "
        "with artificial intelligence, deep learning, blockchain and network security; cryptography with encryption and digital signatures; "
        "the internet of things with neural networks, industrial IoT and edge computing; cyberattacks with digitalisation and ICT; "
        "vulnerability with smart city and threats; risk with information systems; intrusion detection systems with cyber threats and SIEM; "
        "data security with quantum cryptography; FPGA with elliptic curve cryptography and AES; UAVs with optimisation.",
        f"Stable: {len(stable)} of the {len(themes)} F12.3c themes of five or more keywords keep their leading keyword and all or most "
        f"members on the new frame ({', '.join(stable)}); Louvain (20 seeds) gives exactly the greedy partition in {same_runs} runs, and "
        f"the leading pairs stay together in at least {round(100 * min_share)} % of runs.",
        "Not stable: the boundary between machine learning, artificial intelligence, network security and the internet of things. On "
        "F12.3c's layer machine learning sat with IoT; on E1 it sits with artificial intelligence and deep learning (machine learning keeps "
        f"its name but shares {ml['common_keywords']} of its {ml['size_I2_v3']} former keywords), and IoT forms its own theme. Write them as "
        "neighbouring themes, not as sharply separated ones.",
        f"E1 against F12.3c: the author map is almost the same ({a['records_with_keywords']} records in both; nodes {a['nodes']} against "
        f"{d0[('author', 'nodes (>= 5 records, with generic)')]['I2_v3']}; clusters {a['clusters']} against "
        f"{d0[('author', 'clusters (generic excluded)')]['I2_v3']}); the index map is not, because E1 carries the full Scopus index terms "
        f"({i['nodes']} nodes against {d0[('index', 'nodes (>= 5 records, with generic)')]['I2_v3']}); keep index keywords as a robustness view.",
        "Thesaurus v4 joins abbreviations inside keywords: " + "; ".join(
            f"{r['keyword']} ({r['records_E1_v3']} records) into {r['v4_form_of_removed']}" for r in dl["D1"]["author_rows"] if r["change"] == "removed")
        + "; resulting nodes: " + "; ".join(f"{r['keyword']} {r['records_E1_v4']}" for r in dl["D1"]["author_rows"] if r["change"] != "removed") + ".",
        f"Blind spots unchanged on E1 (n = {num['records_E1']}): SCADA {bs['SCADA']} record, ICS 0, OT 0, IIoT {bs['IIoT / industrial IoT']}, "
        f"LLM/generative AI {bs['LLM / generative AI / ChatGPT']}, agentic AI 0.",
        f"Periods: information security falls from {t6['information security']['pct_2003_2016']} % of keyword-bearing records in 2003-2016 "
        f"(n = {per['2003_2016']['with_author_kw']}) to {t6['information security']['pct_2017_2021']} % in 2017-2021 (n = "
        f"{per['2017_2021']['with_author_kw']}) and {t6['information security']['pct_2022_2025']} % in 2022-2025 (n = "
        f"{per['2022_2025']['with_author_kw']}); machine learning rises to {t6['machine learning']['pct_2022_2025']} % only in 2022-2025. "
        f"Title bigrams: {tb['top20_present_as_author_kw']} of the top 20 occur as author keywords, {tb['top20_in_author_top20']} among the top 20.",
    ]
    out.append(bullets(prof))

    out.append("## 12. Gates\n")
    lines = ["| gate | what | verdict | planted violation caught |", "| --- | --- | --- | --- |"]
    lines += [f"| {g['gate']} | {g['what']} | {g['verdict']} | {g['planted_verdict']} ({g['falsifiability']}) |" for g in gates]
    out.append("\n".join(lines) + "\n")
    first = rows("phase_F13_5_checkpoint_assertions_first_run.csv", L.OUT)
    if first:
        out.append(W("First run: " + ", ".join(f"{g['gate']} {g['verdict']}" for g in first) + ".") + "\n")
    out.append("## 13. Independent verification\n")
    if ver:
        lines = ["| check | what | tables | recomputed | verdict |", "| --- | --- | --- | --- | --- |"]
        lines += ["| " + " | ".join(" ".join(str(r.get(k, "")).replace("|", "/").split()[:14])[:100] for k in
                                    ("check_id", "what", "expected_from_tables", "recomputed", "verdict")) + " |" for r in ver]
        out.append("\n".join(lines) + "\n")
        out.append(W(f"A subagent wrote its own program (programs/f135_verify.py) from a description of the method, without reading this "
                     f"phase's other programs: {sum(1 for r in ver if r.get('verdict') == 'PASS')} of {len(ver)} PASS.") + "\n")
    else:
        out.append("(not yet run)\n")

    out.append("## 14. Disclosures\n")
    out.append(bullets(DISCLOSURES + [
        f"Keywords of more than 6 words ({a['keywords_over_6_words']} author, {i['keywords_over_6_words']} index, one record each at most) "
        "are counted but not printed and are not candidates (T1 omits them).",
    ]))

    out.append("## 15. Registry row (to be added on the author's command 'реестр', after the fork's rows)\n")
    if row:
        out.append(W(f"{row['phase_id']} | {row['status']} | produced_numbers {row['produced_numbers']} | safe_to_publish "
                     f"{row['safe_to_publish']} | {row['file_count']} files, {row['bytes']} bytes (the folder's fixed point). When written: "
                     "superseded_by = phase_F13_5 for the row phase_F12_3c. The fork's rows phase_F12_4, phase_F13_1 and phase_F13_2 come "
                     "first. Ready rows: run_logs/registry_rows_pending.json; program: programs/f135_registry.py (not run in this phase).") + "\n")
        out.append(W("Note of the row: " + row["note"]) + "\n")
    else:
        out.append("(dry run)\n")
    return "\n".join(out)


DISCLOSURES = [
    "Class 'c bracket (new form)' is the executor's: the brief's G7 asks for zero residual final-bracket forms, and E1 brings 31 new "
    "ones, mostly Scopus index qualifiers ('gateways (computer networks)', 'mercury (metal)'). v3's rule is applied with an added test "
    "(first characters equal, the short form's characters in order in the long form); without it qualifiers became 'abbreviations' "
    "(metal -> mercury, online -> social networking) and fed nonsense into class f. 11 merged, 20 kept.",
    "Class f guard (executor's): English function words (an, as, am and others) are not read as abbreviations ('security as a service'). "
    "'it' is read (it security, it audit), so those keywords appear among the keeps for the author.",
    "Class c' follows the brief literally (no abbreviation test); 'modem (com) ports' becomes 'modem ports', and the table pair com -> "
    "modem it creates matches no keyword. 5g / 6g pairs from c' rows make '5g network' merge into 'fifth generation network' by rule f.",
    "Class f checks the expanded form against T1 and the thesaurus 'to' values (the brief), and also against 'from' values (a known "
    "form whose final form is a 'to'); no merge used the 'from' path.",
    "Not covered by any class: a pair that differs by both a space and a plural ending. In the index layer 'ho momorphic encryptions' "
    "(9 records, a Scopus term) and 'homomorphic encryption' (8) stay two nodes of one cluster; a candidate for the author's decision.",
    "The index layer changed by the frame, not by the method: E1's Index Keywords are the full Scopus controlled terms, I2 held a "
    "subset. Index results of F12.3c and F13.5 are not comparable term by term (S1, index layer).",
    "Title bigrams (T8) now come from E1's titles (the brief), not from the manuscript's Figure 5 term list as in F12.3c; the "
    "stop-word list is printed in T8. Other punctuation ends a segment so that no bigram spans a colon or comma.",
    "S1 compares partitions on common nodes by identical keyword strings (no thesaurus mapping); the adjusted Rand index is added "
    "because with many clusters most node pairs are apart in any partition and the plain Rand index stays high.",
    "programs/f135_probe.py (console only) looked at the two keyword parts that end in ';' before the run; it prints keywords only.",
    "The verifier's first run had 1 FAIL of 75 rows (C11_kwlen): 12 class-f keep rows printed their expanded form of 7-8 words "
    "(R1 column b, the candidates' pair). These forms are now counted, not printed (the reason gives the word count, the token and the "
    "long form); the chain was rerun and the verifier re-ran its program; the first finding stays in its note.",
    "Markdown tables are checked cell by cell (G2; each cell <= 30 words); five table rows of S1 and D4 exceed 30 tokens only "
    "when the pipes are counted as words (the verifier's note).",
    "The programs are F12.3c's, copied; changed in (i) the input (E1 stream, five columns), (ii) thesaurus v4 (candidates), (iii) the "
    "residual scan, (iv) the deltas, (v) the new stability block; plus T6 with three periods, T8 from E1 titles, gates G1-G8, the "
    "report and the closing (no registry write).",
    "The figure omits the generic keywords; the node table keeps them. The delta tables, R1 and the candidates name earlier forms by "
    "design and are outside G3's scope; tables/v3_on_E1/ uses thesaurus v3 by design.",
    "E1 was read only inside programs, as a CSV stream of which five columns were kept; no abstract, reference, author, address, "
    "e-mail or ORCID value is in any output; G2 also checks that no E1 title stands in any output.",
    "No network, no heredoc, no workflow or skill; one subagent (the verifier); nothing in .claude/; nothing deleted or moved; "
    "phase_F13_2 and PHASE_REGISTRY.csv neither read nor written; CORRECTIONS.csv unchanged (in the snapshot).",
]
