import sys
sys.dont_write_bytecode = True

# Independent verifier for phase F13.5 (co-word analysis on E1, thesaurus v4).
# Written from the method description only; does not import or read any other f135_* program.
# Reads from E1 only EID, Year, Title, Author Keywords, Index Keywords; never prints or writes titles.
# Output: phase_F13_5_independent_verification.csv (counts, keywords, short notes).

import csv
import itertools
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import networkx as nx
from networkx.algorithms.community import greedy_modularity_communities, louvain_communities, modularity

csv.field_size_limit(2 ** 31 - 1)

import os
ROOT = Path(os.environ.get("PROJECT_ROOT", "."))
OUT = ROOT / "outputs" / "dprg_revision_2026" / "phase_F13_5"
PREV = ROOT / "outputs" / "dprg_revision_2026" / "phase_F12_3c"
E1 = ROOT / "outputs" / "dprg_revision_2026" / "author_exports_2026_10" / "scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
TAB = OUT / "tables"
V3T = TAB / "v3_on_E1"
FIG = OUT / "figures"
RESULT = OUT / "phase_F13_5_independent_verification.csv"

GENERIC = {"cybersecurity", "information security", "kazakhstan", "security"}
DASH = [chr(0x2D), chr(0x2010), chr(0x2011), chr(0x2012), chr(0x2013), chr(0x2014), chr(0x2212)]
TRAIL = set(".,;:!?\"'()[]{}*") | {chr(0x2019), chr(0x201D), chr(0x201C)}
LAYERS = ("author", "index")

results = []


def nwords(s):
    return len(str(s).split())


def clip(s, n=30):
    w = str(s).split()
    if len(w) > n:
        return " ".join(w[:n - 1]) + " ..."
    return str(s)


def kws(k):
    n = nwords(k)
    return k if n <= 6 else "(keyword of %d words)" % n


def add(cid, what, exp, rec, ok, note=""):
    row = {"check_id": cid, "what": clip(what), "expected_from_tables": clip(exp), "recomputed": clip(rec),
           "verdict": "PASS" if ok else "FAIL", "note": clip(note)}
    results.append(row)
    print(cid, row["verdict"], "|", row["what"], "| exp:", row["expected_from_tables"], "| got:", row["recomputed"],
          ("| " + row["note"]) if row["note"] else "")


def norm_kw(s):
    s = s.lower()
    for d in DASH:
        s = s.replace(d, " ")
    s = " ".join(s.split())
    while s:
        c = s[-1]
        if c in TRAIL or c == " ":
            if c == ")" and "(" in s:
                break
            s = s[:-1]
        else:
            break
    while s:
        c = s[0]
        if c in TRAIL or c == " ":
            if c == "(" and ")" in s:
                break
            s = s[1:]
        else:
            break
    return s


def read_dicts(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ======================= inputs =======================
NEED = ["EID", "Year", "Title", "Author Keywords", "Index Keywords"]
E = []
blank = 0
with open(E1, encoding="utf-8-sig", newline="") as f:
    rd = csv.reader(f)
    header = next(rd)
    for c in NEED:
        if header.count(c) != 1:
            raise SystemExit("E1 column %s found %d times" % (c, header.count(c)))
    IX = [header.index(c) for c in NEED]
    for r in rd:
        if not r or all(not x.strip() for x in r):
            blank += 1
            continue
        E.append(tuple(r[i] if i < len(r) else "" for i in IX))
    del header
EIDS = [e[0].strip() for e in E]
YEAR = {e[0].strip(): int(e[1].strip()) for e in E}
TITLE = {e[0].strip(): e[2] for e in E}
RAW = {"author": {e[0].strip(): e[3] for e in E}, "index": {e[0].strip(): e[4] for e in E}}
semi_inside = sum(1 for L in LAYERS for cell in RAW[L].values() for p in cell.split("; ") if ";" in p)
print("E1 rows", len(E), "unique EIDs", len(set(EIDS)), "blank lines", blank, "parts still containing ';'", semi_inside)

v3rows = read_dicts(PREV / "tables" / "thesaurus.csv")
v4rows = read_dicts(TAB / "thesaurus.csv")
V3 = {r["from"]: r["to"] for r in v3rows}
V4 = {r["from"]: r["to"] for r in v4rows}
V4_TO = set(V4.values())


def layer_sets(cells, thes):
    recs = {}
    for eid, cell in cells.items():
        s = set()
        for part in cell.split("; "):
            k = norm_kw(part)
            if not k:
                continue
            k = thes.get(k, k)
            if k:
                s.add(k)
        if s:
            recs[eid] = s
    return recs


RUN = {}
for name, thes in (("v4", V4), ("v3", V3), ("raw", {})):
    for L in LAYERS:
        recs = layer_sets(RAW[L], thes)
        fr = Counter()
        for s in recs.values():
            fr.update(s)
        RUN[(name, L)] = (recs, fr)

NUMS = json.load(open(OUT / "F13_5_numbers.json", encoding="utf-8"))
NUMS3 = json.load(open(V3T / "numbers_v3_on_E1.json", encoding="utf-8"))
STATUS = json.load(open(OUT / "run_logs" / "thesaurus_v4_status.json", encoding="utf-8"))


def t1_rows(fr, base):
    ranked = sorted(fr.items(), key=lambda x: (-x[1], x[0]))
    rows = []
    for i, (k, c) in enumerate(ranked, 1):
        if nwords(k) > 6:
            continue
        rows.append((i, k, c, "%.1f" % (100.0 * c / base), 1 if k in GENERIC else 0))
    return rows


T1MINE = {}
for name in ("v4", "v3"):
    for L in LAYERS:
        recs, fr = RUN[(name, L)]
        T1MINE[(name, L)] = t1_rows(fr, len(recs))

# ======================= C01 =======================
A4 = RUN[("v4", "author")][0]
I4 = RUN[("v4", "index")][0]
add("C01a", "E1 records with >=1 author keyword (v4)", "797; json %s" % NUMS["author"]["records_with_keywords"], len(A4),
    len(A4) == 797 == NUMS["author"]["records_with_keywords"])
add("C01b", "E1 records with >=1 index keyword (v4)", "586; json %s" % NUMS["index"]["records_with_keywords"], len(I4),
    len(I4) == 586 == NUMS["index"]["records_with_keywords"])
add("C01c", "E1 records and unique EIDs", "841; json records_E1 %s" % NUMS["records_E1"],
    "%d rows; %d unique EIDs" % (len(E), len(set(EIDS))),
    len(E) == 841 == len(set(EIDS)) == NUMS["records_E1"],
    "blank lines %d; split on '; ' leaves %d parts containing ';'" % (blank, semi_inside))


# ======================= C02 / C03 (and C18 T1) =======================
def check_t1(cid, run, tdir, nj):
    for L in LAYERS:
        recs, fr = RUN[(run, L)]
        uk = len(fr)
        over6 = sum(1 for k in fr if nwords(k) > 6)
        add("%s_%s_unique" % (cid, L), "%s %s unique keywords / keywords over 6 words" % (run, L),
            "json %s / %s" % (nj[L]["unique_keywords"], nj[L]["keywords_over_6_words"]), "%d / %d" % (uk, over6),
            uk == nj[L]["unique_keywords"] and over6 == nj[L]["keywords_over_6_words"])
        T1 = read_dicts(tdir / ("T1_%s_frequencies.csv" % L))
        filerows = [(int(r["rank"]), r["keyword"], int(r["records"]), r["pct_of_records_with_keywords"], int(r["generic"]))
                    for r in T1]
        mine = T1MINE[(run, L)]
        kr_file = {(r[1], r[2]) for r in filerows}
        kr_mine = {(r[1], r[2]) for r in mine}
        add("%s_%s_T1rows" % (cid, L), "%s T1 %s: every row (keyword, records)" % (run, L), "%d rows" % len(filerows),
            "%d keywords <= 6 words" % len(mine), kr_file == kr_mine and len(filerows) == len(kr_file),
            "" if kr_file == kr_mine else "symmetric difference %d" % len(kr_file ^ kr_mine))
        bad_pct = sum(1 for a, b in zip(filerows, mine) if a[3] != b[3])
        bad_gen = sum(1 for a, b in zip(filerows, mine) if a[4] != b[4])
        bad_rank = sum(1 for a, b in zip(filerows, mine) if a[0] != b[0] or a[1] != b[1])
        add("%s_%s_T1pct" % (cid, L), "%s T1 %s: pct (1 dp, base %d), generic flag, rank and order" % (run, L, len(recs)),
            "0 / 0 / 0 mismatches", "%d / %d / %d" % (bad_pct, bad_gen, bad_rank),
            bad_pct == bad_gen == bad_rank == 0 and len(filerows) == len(mine),
            "ranks count keywords over 6 words, their rows omitted")


check_t1("C02", "v4", TAB, NUMS)

T1F_author = read_dicts(TAB / "T1_author_frequencies.csv")
top20_file = [(r["keyword"], int(r["records"])) for r in T1F_author[:20]]
top20_mine = [(r[1], r[2]) for r in T1MINE[("v4", "author")][:20]]
add("C03", "T1 author top 20 (keyword, records, order)", "; ".join("%s=%d" % x for x in top20_file[:4]) + " ...",
    "; ".join("%s=%d" % x for x in top20_mine[:4]) + " ...", top20_file == top20_mine,
    "order identical, ties alphabetical" if top20_file == top20_mine else "order differs")


# ======================= networks =======================
def network(recs, fr, t, with_generic):
    nodes = {k for k, c in fr.items() if c >= t and (with_generic or k not in GENERIC)}
    co = Counter()
    for s in recs.values():
        for a, b in itertools.combinations(sorted(s & nodes), 2):
            co[(a, b)] += 1
    return nodes, {e: w for e, w in co.items() if w >= 2}


NET = {}
for run in ("v4", "v3"):
    for L in LAYERS:
        recs, fr = RUN[(run, L)]
        for t in (3, 5, 8):
            for wg in (True, False):
                NET[(run, L, t, wg)] = network(recs, fr, t, wg)


def build_graph(nodes, edges, fr):
    G = nx.Graph()
    for n in sorted(nodes):
        G.add_node(n)
    for (a, b) in sorted(edges):
        G.add_edge(a, b, assoc=edges[(a, b)] / (fr[a] * fr[b]))
    return G


PART = {}
for run in ("v4", "v3"):
    for L in LAYERS:
        fr = RUN[(run, L)][1]
        nn, en = NET[(run, L, 5, False)]
        G = build_graph(nn, en, fr)
        comms = [frozenset(c) for c in greedy_modularity_communities(G, weight="assoc", resolution=1.0)]
        Q = modularity(G, comms, weight="assoc", resolution=1.0)
        PART[(run, L)] = (G, comms, Q)

# ======================= C04 =======================
for L in LAYERS:
    T2 = read_dicts(TAB / ("T2_%s_threshold_sensitivity.csv" % L))
    seen = set()
    for r in T2:
        t = int(r["threshold_records"])
        seen.add(t)
        nw, ew = NET[("v4", L, t, True)]
        nn, en = NET[("v4", L, t, False)]
        exp = (int(r["nodes_with_generic"]), int(r["edges_with_generic"]), int(r["nodes_without_generic"]),
               int(r["edges_without_generic"]))
        js = [s for s in NUMS[L]["sensitivity"] if s["threshold_records"] == t][0]
        jexp = (js["nodes_with_generic"], js["edges_with_generic"], js["nodes_without_generic"], js["edges_without_generic"])
        got = (len(nw), len(ew), len(nn), len(en))
        add("C04_%s_t%d" % (L, t), "T2 %s t=%d: nodes, edges with generic; nodes, edges without" % (L, t),
            "%s; json %s" % (exp, "agrees" if jexp == exp else jexp), got, exp == got == jexp)
    if seen != {3, 5, 8}:
        add("C04_%s_rows" % L, "T2 %s thresholds present" % L, "3, 5, 8", sorted(seen), False)


# ======================= C05 / C06 / C07 (and C18) =======================
def t3_partition(rows):
    d = defaultdict(set)
    for r in rows:
        if r["cluster"] != "":
            d[r["cluster"]].add(r["keyword"])
    return {frozenset(s) for s in d.values()}


def check_t3_t4(run, L, tdir, nj, ids):
    recs, fr = RUN[(run, L)]
    nw, ew = NET[(run, L, 5, True)]
    Gw = nx.Graph()
    Gw.add_nodes_from(nw)
    for (a, b), w in ew.items():
        Gw.add_edge(a, b, weight=w)
    T3 = read_dicts(tdir / ("T3_%s_nodes.csv" % L))
    t3n = {r["keyword"] for r in T3}
    bad = []
    for r in T3:
        k = r["keyword"]
        if k not in nw:
            continue
        exp = (int(r["records"]), int(r["degree"]), int(r["weighted_degree"]), int(r["generic"]))
        got = (fr[k], Gw.degree(k), Gw.degree(k, weight="weight"), 1 if k in GENERIC else 0)
        if exp != got:
            bad.append(k)
    ok_nodes = t3n == nw and len(T3) == len(t3n)
    add(ids["nodes"], "%s %s T3 node set = with-generic network t=5; records, degree, weighted degree, generic" % (run, L),
        "%d rows; json nodes %s" % (len(T3), nj[L]["nodes"]),
        "%d nodes; %d attribute mismatches" % (len(nw), len(bad)),
        ok_nodes and not bad and len(nw) == nj[L]["nodes"],
        ("symdiff %d" % len(t3n ^ nw) if not ok_nodes else "") + ("; first " + kws(bad[0]) if bad else ""))
    G, comms, Q = PART[(run, L)]
    tsets = t3_partition(T3)
    gen_blank = all((r["cluster"] == "") == (r["keyword"] in GENERIC) for r in T3)
    add(ids["clusters"], "%s %s clusters and modularity Q (assoc weight, 4 dp)" % (run, L),
        "json %d clusters, Q %s; T3 %d clusters" % (nj[L]["clusters"], nj[L]["modularity"], len(tsets)),
        "%d clusters, Q %.6f" % (len(comms), Q),
        len(comms) == nj[L]["clusters"] == len(tsets) and round(Q, 4) == nj[L]["modularity"],
        "singleton clusters %d (json isolated %s)" % (sum(1 for c in comms if len(c) == 1),
                                                      nj[L].get("isolated_clustered_nodes")))
    add(ids["partition"], "%s %s partition = T3 cluster column (sets of frozensets)" % (run, L),
        "%d sets, %d nodes" % (len(tsets), sum(len(s) for s in tsets)),
        "%d sets, %d nodes" % (len(comms), sum(len(c) for c in comms)),
        tsets == set(comms) and gen_blank, "generic nodes have blank cluster: %s" % gen_blank)
    T4 = read_dicts(tdir / ("T4_%s_edges.csv" % L))
    t4 = {}
    for r in T4:
        a, b = sorted((r["source"], r["target"]))
        t4[(a, b)] = (int(r["cooccurrence_records"]), r["association_strength"], r["in_clustering"])
    mine = {(a, b): (w, "%.6f" % (w / (fr[a] * fr[b])), "0" if (a in GENERIC or b in GENERIC) else "1")
            for (a, b), w in ew.items()}
    nbad = sum(1 for e in set(t4) | set(mine) if t4.get(e) != mine.get(e))
    add(ids["edges"], "%s %s T4 edges: co-occurrence, association 6 dp, in_clustering" % (run, L),
        "%d rows; json edges %s" % (len(T4), nj[L]["edges"]), "%d edges; %d mismatches" % (len(mine), nbad),
        t4 == mine and len(T4) == len(t4) and len(mine) == nj[L]["edges"])


for L in LAYERS:
    check_t3_t4("v4", L, TAB, NUMS, {"nodes": "C05_%s" % L, "clusters": "C06_%s_clusters_Q" % L,
                                     "partition": "C06_%s_partition" % L, "edges": "C07_%s" % L})

# ======================= C08 (T6) =======================
PERIODS = [("2003_2016", 2003, 2016), ("2017_2021", 2017, 2021), ("2022_2025", 2022, 2025)]
FA4 = RUN[("v4", "author")][1]
top30 = [k for k, c in sorted(FA4.items(), key=lambda x: (-x[1], x[0]))][:30]
pc = {}
bases = {}
bad_base = []
for p, y0, y1 in PERIODS:
    frame = [e for e in EIDS if y0 <= YEAR[e] <= y1]
    withkw = [e for e in frame if e in A4]
    bases[p] = len(withkw)
    c = Counter()
    for e in withkw:
        c.update(A4[e])
    pc[p] = c
    jp = NUMS["periods"][p]
    if (jp["frame_records"], jp["with_author_kw"]) != (len(frame), len(withkw)):
        bad_base.append(p)
add("C08_bases", "T6 period bases: frame records / records with author keywords per period (json)",
    "; ".join("%s %d/%d" % (p, NUMS["periods"][p]["frame_records"], NUMS["periods"][p]["with_author_kw"]) for p, _, _ in PERIODS),
    "; ".join("%s %d/%d" % (p, sum(1 for e in EIDS if y0 <= YEAR[e] <= y1), bases[p]) for p, y0, y1 in PERIODS),
    not bad_base, "years outside 2003-2025: %d" % sum(1 for e in EIDS if not 2003 <= YEAR[e] <= 2025))
T6 = read_dicts(TAB / "T6_author_keywords_by_period.csv")
bad6 = []
for r in T6:
    k = r["keyword"]
    exp = [int(r["generic"])]
    got = [1 if k in GENERIC else 0]
    for p, _, _ in PERIODS:
        exp += [int(r["records_" + p]), r["pct_" + p]]
        got += [pc[p][k], "%.1f" % (100.0 * pc[p][k] / bases[p])]
    if exp != got:
        bad6.append(k)
order_ok = [r["keyword"] for r in T6] == top30
add("C08_rows", "T6 rows: top 30 author keywords (order) and per-period records, pct, generic",
    "%d rows" % len(T6), "%d value mismatches; keyword list and order equal: %s" % (len(bad6), order_ok),
    not bad6 and order_ok, ("first " + kws(bad6[0])) if bad6 else "")

# ======================= C09 (T7) =======================
T7p = read_dicts(PREV / "tables" / "T7_blind_spots_keywords.csv")
T7o = {r["group"]: r for r in read_dicts(TAB / "T7_blind_spots_keywords.csv")}
T7m = defaultdict(set)
for r in read_dicts(TAB / "T7_blind_spots_matched_keywords.csv"):
    T7m[r["group"]].add(r["keyword"])
FI4 = RUN[("v4", "index")][1]
for r in T7p:
    g = r["group"]
    rx = re.compile(r["regex"])
    ra = {e for e, s in A4.items() if any(rx.search(x) for x in s)}
    ri = {e for e, s in I4.items() if any(rx.search(x) for x in s)}
    o = T7o.get(g)
    if o is None:
        add("C09_" + g.split(" ")[0], "T7 group present: " + g, "row", "missing", False)
        continue
    exp = (int(o["records_author_kw"]), int(o["records_index_kw"]), int(o["records_either"]))
    got = (len(ra), len(ri), len(ra | ri))
    matched = {x for x in FA4 if rx.search(x)} | {x for x in FI4 if rx.search(x)}
    add("C09_" + g.split(" ")[0].replace("/", ""), "T7 %s: records author / index / either" % g, exp, got,
        exp == got and o["regex"] == r["regex"] and NUMS["blind_spots"].get(g) == len(ra | ri),
        "regex equals F12.3c: %s; json = either: %s; matched-keyword list equals author+index matches: %s"
        % (o["regex"] == r["regex"], NUMS["blind_spots"].get(g) == len(ra | ri), T7m.get(g, set()) == matched))

# ======================= C10 =======================
V4_FROM = set(V4)
files10 = sorted(p for p in TAB.glob("T*.csv")) + sorted(FIG.glob("*.csv"))
hits10 = []
for fp in files10:
    for r in read_dicts(fp):
        for c in ("keyword", "source", "target", "largest_keyword", "as_keyword"):
            if c in r and r[c] in V4_FROM:
                hits10.append((fp.name, c, r[c]))
add("C10", "v4 'from' values in keyword columns of tables/T*.csv (top level) and figure CSVs", 0, len(hits10), not hits10,
    "%d files, %d from values" % (len(files10), len(V4_FROM)) + ("; first %s %s %s" % (hits10[0][0], hits10[0][1], kws(hits10[0][2])) if hits10 else ""))

# ======================= C11 =======================
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+")
ORCID = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dXx]\b")
KWC = {"keyword", "source", "target", "largest_keyword", "as_keyword", "from", "to", "merge_from", "merge_to",
       "keyword_a", "keyword_b", "leading_keyword", "v4_form_of_removed", "v4_form", "a", "b"}
files11 = sorted(p for p in TAB.rglob("*") if p.is_file()) + sorted(FIG.glob("*.csv"))
files11 += sorted(OUT.glob("*.json")) + sorted((OUT / "run_logs").glob("*.json"))
em = orc = 0
kwlong, celllong, mdlong, mdlong_plain, kw_exempt = [], [], [], [], []


def alnum_words(s):
    return sum(1 for w in s.split() if re.search(r"[A-Za-z0-9]", w))


for fp in files11:
    txt = open(fp, encoding="utf-8-sig").read()
    em += sum(1 for _ in EMAIL.finditer(txt))
    orc += len(ORCID.findall(txt))
    if fp.suffix == ".csv":
        for r in read_dicts(fp):
            for c, v in r.items():
                if v is None or c is None:
                    continue
                if (c in KWC or c.startswith("leading_")) and nwords(v) > 6:
                    if fp.name == "R1_residual_scan.csv" and c == "b" and r.get("class") == "f":
                        kw_exempt.append(v)
                    else:
                        kwlong.append((fp.name, c))
                if c != "title_bigram" and nwords(v) > 30:
                    celllong.append((fp.name, c))
    elif fp.suffix == ".md":
        for ln in txt.splitlines():
            if nwords(ln) > 30:
                mdlong_plain.append(fp.name)
            if alnum_words(ln) > 30:
                mdlong.append(fp.name)
add("C11_privacy", "e-mail / ORCID shapes in tables (recursive), figures CSVs, phase and run_logs json", "0 / 0",
    "%d / %d" % (em, orc), em == 0 and orc == 0, "%d files scanned" % len(files11))
all_kw = set()
for key, (recs_, fr_) in RUN.items():
    all_kw |= set(fr_)
exempt_is_kw = [v for v in kw_exempt if v in all_kw]
exempt_where = sorted({"%s %s" % (k[0], k[1]) for v in exempt_is_kw for k in RUN if v in RUN[k][1]})
add("C11_kwlen", "keyword cells over 6 words (keyword-type columns of tables, figures, incl. R1 a/b)", 0,
    "%d" % (len(kwlong) + len(kw_exempt)), not kwlong and not kw_exempt,
    "first run FAIL: 12 expanded forms of 7-8 words in R1 column b (one a 7-word index keyword); fixed by the executor; "
    "re-run %s" % ("PASS" if not kwlong and not kw_exempt else "FAIL: R1 col b %d, other %d" % (len(kw_exempt), len(kwlong))))
add("C11_celllen", "CSV cells / markdown lines over 30 words", "0 / 0",
    "%d / %d" % (len(celllong), len(mdlong)), not celllong and not mdlong,
    "title_bigram exempt; md words = tokens with a letter or digit; counting table pipes as words, %d md table rows exceed"
    % len(mdlong_plain) + ("; first cell %s %s" % celllong[0] if celllong else "") +
    ("; first md %s" % mdlong[0] if mdlong else ""))

# ======================= C12 =======================
fn = read_dicts(FIG / "Fig_coword_author_keywords_nodes.csv")
fe = read_dicts(FIG / "Fig_coword_author_keywords_edges.csv")
nn, en = NET[("v4", "author", 5, False)]
T3a = {r["keyword"]: r for r in read_dicts(TAB / "T3_author_nodes.csv")}
fnodes = {r["keyword"] for r in fn}
badn = [r["keyword"] for r in fn if r["keyword"] not in T3a or r["records"] != T3a[r["keyword"]]["records"]
        or r["cluster"] != T3a[r["keyword"]]["cluster"] or int(r["records"]) != FA4[r["keyword"]]]
lab = sum(1 for r in fn if r["labelled"] == "1")
lab_ok = all((r["labelled"] == "1") == (int(r["records"]) >= NUMS["parameters"]["label_min_records"]) for r in fn)
add("C12_nodes", "figure nodes = author network without generic t=5; records and cluster as T3",
    "%d rows; json %d" % (len(fn), NUMS["figure"]["nodes"]), "%d nodes; %d attribute mismatches" % (len(nn), len(badn)),
    fnodes == nn and len(fn) == len(fnodes) and not badn and len(fn) == NUMS["figure"]["nodes"],
    "labelled %d (json %d); labelled iff records >= %d: %s" % (lab, NUMS["figure"]["labelled"],
                                                               NUMS["parameters"]["label_min_records"], lab_ok))
fem = {}
for r in fe:
    a, b = sorted((r["source"], r["target"]))
    fem[(a, b)] = (int(r["cooccurrence_records"]), r["association_strength"])
mine12 = {e: (w, "%.6f" % (w / (FA4[e[0]] * FA4[e[1]]))) for e, w in en.items()}
add("C12_edges", "figure edges = that network's edges (co-occurrence, association 6 dp)",
    "%d rows; json %d" % (len(fe), NUMS["figure"]["edges"]), "%d edges" % len(mine12),
    fem == mine12 and len(fe) == len(fem) == NUMS["figure"]["edges"])

# ======================= C13 =======================
cand3 = read_dicts(PREV / "tables" / "thesaurus_candidates_v3.csv")
cand4 = read_dicts(TAB / "thesaurus_candidates_v4.csv")
T1V4 = {L: {r[1] for r in T1MINE[("v4", L)]} for L in LAYERS}
T1V4F = {L: {r["keyword"] for r in read_dicts(TAB / ("T1_%s_frequencies.csv" % L))} for L in LAYERS}
T1V3E = {L: {r[1] for r in T1MINE[("v3", L)]} for L in LAYERS}
viol = []
npairs = 0
for src, cand in (("v3", cand3), ("v4", cand4)):
    for r in cand:
        if r["decision"] != "merge" or " | " not in r["pair"]:
            continue
        a, b = r["pair"].split(" | ", 1)
        npairs += 1
        for L in LAYERS:
            for nm, s in (("T1", T1V4F[L]), ("recomputed", RUN[("v4", L)][1])):
                if a in s and b in s:
                    viol.append((src, L, nm))
add("C13_pairs", "merged pairs (candidates v3 and v4) with both forms remaining in T1 v4 or recomputed sets", 0,
    len(viol), not viol, "%d merge pairs checked" % npairs + ("; first %s" % (viol[0],) if viol else ""))

vc = Counter(r["version"] for r in v4rows)
vc3 = Counter(r["version"] for r in v3rows)
froms = [r["from"] for r in v4rows]
chain = sorted({r["to"] for r in v4rows if r["to"] in V4})
dupf = len(froms) - len(set(froms))
exp_ver = dict(vc3)
exp_ver["v4"] = STATUS["rows_new"]
add("C13_rows", "thesaurus v4: rows, per version, to-also-from, duplicate from, limit 700",
    "%s rows; %s" % (NUMS["thesaurus_rows"], ", ".join("%s=%d" % kv for kv in sorted(exp_ver.items()))),
    "%d rows; %s; chains %d; dup from %d" % (len(v4rows), ", ".join("%s=%d" % kv for kv in sorted(vc.items())), len(chain), dupf),
    len(v4rows) == NUMS["thesaurus_rows"] == STATUS["rows_v4"] == 680 and dict(vc) == exp_ver and not chain and dupf == 0
    and len(v4rows) <= 700)
mf4 = [r["merge_from"] for r in cand4 if r["decision"] == "merge"]
v4new = [r["from"] for r in v4rows if r["version"] == "v4"]
add("C13_v4rows", "every v4-version row = a merge decision (merge_from) in candidates v4, and vice versa",
    "%d merge decisions" % len(mf4), "%d v4 rows" % len(v4new),
    set(mf4) == set(v4new) and len(mf4) == len(set(mf4)) == len(v4new),
    "v4 rows without decision %d; decisions without row %d" % (len(set(v4new) - set(mf4)), len(set(mf4) - set(v4new))))
# v3 rows kept, retargeting declared
ret = {d["from"]: d for d in STATUS["retargeted_v3_rows"]}
changed = []
bad_ret = []
for r in v3rows:
    f4 = V4.get(r["from"])
    if f4 is None:
        changed.append(("missing", r["from"]))
        continue
    if f4 != r["to"]:
        d = ret.get(r["from"])
        if d is None or d["to_v3"] != r["to"] or d["to_v4"] != f4:
            changed.append(("undeclared", r["from"]))
        elif r["to"] not in V4 or V4[r["to"]] != f4:
            bad_ret.append(r["from"])
vers_changed = sum(1 for r in v3rows if [x for x in v4rows if x["from"] == r["from"]][0]["version"] != r["version"])
ret_used = sum(1 for r in v3rows if V4.get(r["from"]) not in (None, r["to"]))
add("C13_v3kept", "all v3 rows in v4; retargets declared and only where the v3 'to' is merged in v4",
    "%d v3 rows; %d declared retargets" % (len(v3rows), len(ret)),
    "%d retargeted; undeclared/missing %d; to not merged %d; version changed %d" % (ret_used, len(changed), len(bad_ret), vers_changed),
    not changed and not bad_ret and ret_used == len(ret) and vers_changed == 0)
bycls = defaultdict(Counter)
for r in cand4:
    bycls[r["class"]][r["decision"]] += 1
st_ok = all(bycls[c][d] == n for c, dd in STATUS["by_class"].items() for d, n in dd.items()) and \
    set(bycls) == set(STATUS["by_class"])
forms_union = T1V3E["author"] | T1V3E["index"]
prevT1 = set()
for L in LAYERS:
    prevT1 |= {r["keyword"] for r in read_dicts(PREV / "tables" / ("T1_%s_frequencies.csv" % L))}
newforms = forms_union - prevT1
rawf = RUN[("raw", "author")][1].keys() | RUN[("raw", "index")][1].keys()
applied4 = sum(1 for f_ in V4 if f_ in rawf)
applied3 = sum(1 for f_ in V3 if f_ in rawf)
add("C13_status", "status json: class counts; T1 forms E1 x v3; forms new to frame; rows applied (v4, v3)",
    "classes ok; %d; %d; %d, %d" % (STATUS["T1_forms"], STATUS["T1_forms_new_to_frame"], NUMS["thesaurus_rows_applied"],
                                    NUMS3["thesaurus_rows_applied"]),
    "classes %s; %d; %d; %d, %d" % ("ok" if st_ok else "differ", len(forms_union), len(newforms), applied4, applied3),
    st_ok and len(forms_union) == STATUS["T1_forms"] and len(newforms) == STATUS["T1_forms_new_to_frame"]
    and applied4 == NUMS["thesaurus_rows_applied"] and applied3 == NUMS3["thesaurus_rows_applied"],
    "rows applied = 'from' values occurring among normalised E1 keywords, either layer")

# ======================= C14 =======================
kept_c = {r["pair"] for r in cand3 if r["class"].startswith("c") and r["decision"] == "keep"}
kept_c |= {r["pair"] for r in cand4 if r["class"] == "c bracket (new form)" and r["decision"] == "keep"}
mf_c = {r["merge_from"] for r in cand3 if r["class"].startswith("c") and r["decision"] == "merge"}
mf_c |= {r["merge_from"] for r in cand4 if r["class"] in ("c bracket (new form)", "c' mid bracket") and r["decision"] == "merge"}
kept_all = {r["pair"].split(" | ")[0] for r in cand3 + cand4 if r["decision"] == "keep"}


def ends_bracket(k):
    return k.endswith(")") and "(" in k


bad14, rem14, mid14, present = [], [], [], set()
for L in LAYERS:
    for k in T1V4F[L]:
        if ends_bracket(k):
            if k in kept_c:
                present.add(k)
            else:
                bad14.append(k)
        elif "(" in k or ")" in k:
            if k not in kept_all:
                mid14.append(k)
    rem14 += [x for x in mf_c if x in T1V4F[L]]
wide = [k for L in LAYERS for k in RUN[("v4", L)][1] if ends_bracket(k) and k not in kept_c]
add("C14", "T1 v4: final-bracket forms declared keeps; no c/c' merge_from left; no unkept mid-string bracket",
    "0 / 0 / 0 (declared keeps %d)" % len(kept_c), "%d / %d / %d" % (len(bad14), len(rem14), len(mid14)),
    not bad14 and not rem14 and not mid14,
    "declared keeps present in T1 v4: %d; final-bracket forms outside T1 (over 6 words) not declared: %d"
    % (len(present), len(wide)) + ("; first " + kws(bad14[0]) if bad14 else "") + ("; mid " + kws(mid14[0]) if mid14 else ""))

# ======================= C15 =======================
STOPI = {"of", "and", "the", "for", "in", "a", "to"}


def initials(s):
    return "".join(w[0] for w in s.split() if w not in STOPI)


e_rows = [r for r in v4rows if r["rule"].startswith("v3 e acronym")]
c3e = {r["merge_from"]: r for r in cand3 if r["class"] == "e acronym" and r["decision"] == "merge"}
b15a, b15b, nvar = [], [], 0
for r in e_rows:
    c = c3e.get(r["from"])
    if c is None:
        b15a.append((r["from"], "no candidate row"))
        continue
    variants = [v.strip() for v in c["long_form_matched"].split(";") if v.strip()]
    if not variants:
        b15a.append((r["from"], "no variants"))
    for v in variants:
        nvar += 1
        if initials(v) != r["from"]:
            b15a.append((r["from"], kws(v)))
        if V4.get(v, v) != r["to"]:
            b15b.append((r["from"], kws(v)))
add("C15", "class-e rows in v4: initials of each long_form_matched variant = from; each variant maps to the v4 'to'",
    "%d rows (8 in v3)" % len(e_rows), "%d variants; initials mismatches %d; mapping mismatches %d" % (nvar, len(b15a), len(b15b)),
    len(e_rows) == 8 and not b15a and not b15b, (str(b15a[:2]) + str(b15b[:2])) if (b15a or b15b) else "")

# ======================= C16 =======================
STOPF = set("a an as am at be by do in is no of on or so to up we and are for the via with from into its not but can "
            "has was all any".split())
EXPLICIT = [("iot", "internet of things"), ("iiot", "industrial internet of things"), ("ai", "artificial intelligence"),
            ("ml", "machine learning"), ("dl", "deep learning"), ("ids", "intrusion detection system"),
            ("uav", "unmanned aerial vehicle"), ("sdn", "software defined networking"),
            ("nlp", "natural language processing"), ("dos", "denial of service"),
            ("ddos", "distributed denial of service"), ("fpga", "field programmable gate array"),
            ("puf", "physical unclonable function"), ("wsn", "wireless sensor network"),
            ("cps", "cyber physical system"), ("ict", "information and communication technology"),
            ("cnn", "convolutional neural network"), ("ecc", "elliptic curve cryptography"),
            ("qkd", "quantum key distribution"), ("llm", "large language model")]
BRK = re.compile(r"^(.*?)\s*\(([^()]*)\)\s*(.*)$")


def bsplit(s):
    m = BRK.match(s)
    return (m.group(1).strip(), m.group(2).strip(), m.group(3).strip()) if m else (None, None, None)


raw_table = defaultdict(set)
for r in v4rows:
    f_, t_, rule, ver = r["from"], r["to"], r["rule"], r["version"]
    X, Y, Z = bsplit(f_)
    if ver == "v1" and rule.startswith("abbreviation to long form"):
        raw_table[f_].add(t_)
    elif ver == "v1" and rule.startswith("long form with abbreviation in parentheses"):
        raw_table[Y].add(t_)
    elif rule.startswith("v3 c bracket: abbreviation in brackets") or \
            rule.startswith("v4 c bracket (new form): abbreviation in brackets"):
        raw_table[Y].add(t_)
    elif rule.startswith("v3 c bracket: reverse form") or rule.startswith("v4 c bracket (new form): reverse form"):
        raw_table[X].add(t_)
    elif rule.startswith("v3 e acronym"):
        raw_table[f_].add(t_)
    elif rule.startswith("v4 c' mid bracket: abbreviation in brackets"):
        raw_table[Y].add(X)
    elif rule.startswith("v4 c' mid bracket: reverse form"):
        raw_table[X].add(Y)
for ab, lf in EXPLICIT:
    raw_table[ab].add(lf)
TABLE = {ab: {V4.get(lf, lf) for lf in lfs} for ab, lfs in raw_table.items()}
logtab = json.load(open(OUT / "run_logs" / "abbreviation_table_v4.json", encoding="utf-8"))
logtab_sets = {ab: set(d.keys()) for ab, d in logtab.items()}
amb = sorted(ab for ab, s in TABLE.items() if len(s) > 1)
add("C16_table", "abbreviation table rebuilt from thesaurus v4 rules + explicit list (long forms mapped once via v4)",
    "status table_size %d; run log %d entries" % (STATUS["table_size"], len(logtab)),
    "%d entries; ambiguous: %s" % (len(TABLE), ", ".join(amb) or "none"),
    len(TABLE) == STATUS["table_size"] and TABLE == logtab_sets and amb == sorted(STATUS["table_ambiguous"]),
    "run log equal: %s" % (TABLE == logtab_sets) + ("" if TABLE == logtab_sets else "; differing keys %d" % len(
        {k for k in set(TABLE) | set(logtab_sets) if TABLE.get(k) != logtab_sets.get(k)})))


def considered(tk):
    return len(tk) > 1 and not tk.isdigit() and tk not in STOPF


def expand(kw):
    toks = kw.split()
    hits = [i for i, tk in enumerate(toks) if considered(tk) and tk in TABLE]
    if len(toks) < 2 or len(hits) != 1:
        return None, None, None
    i = hits[0]
    lfs = TABLE[toks[i]]
    if len(lfs) != 1:
        return toks[i], None, "ambiguous"
    lf = next(iter(lfs))
    return toks[i], " ".join(toks[:i] + [lf] + toks[i + 1:]), lf


frows = [r for r in cand4 if r["class"].startswith("f")]
p16 = Counter()
bad16 = []
NOTPRINTED = re.compile(r"expanded form of (\d+) words \(> 6; not printed\): '(.+?)' -> '(.+)'$")
n_np = 0
for r in frows:
    kw, ex = r["pair"].split(" | ", 1) if " | " in r["pair"] else (r["pair"], None)
    ab, mine, lf = expand(kw)
    if mine is None:
        bad16.append((kw, "not expandable" if ab is None else "ambiguous"))
        continue
    if ex is None:
        # expanded form not printed (> 6 words): recompute it and match the stated word count, token and long form
        n_np += 1
        mm = NOTPRINTED.search(r["reason"])
        if not mm or r["decision"] != "keep" or nwords(mine) <= 6 or int(mm.group(1)) != nwords(mine) \
                or mm.group(2) != ab or mm.group(3) != lf or lf not in r["long_form_matched"]:
            bad16.append((kw, "not-printed keep row inconsistent"))
        else:
            p16["keep_long"] += 1
        continue
    if ex != mine:
        bad16.append((kw, "expanded form differs"))
        continue
    if lf not in r["long_form_matched"]:
        bad16.append((kw, "long_form_matched lacks long form"))
    if nwords(mine) > 6:
        expd = "keep_long"
    elif mine in forms_union or mine in V4_TO:
        expd = "merge"
    else:
        expd = "keep_absent"
    p16[expd] += 1
    if expd == "merge":
        if r["decision"] != "merge" or r["merge_from"] != kw or V4.get(kw) != r["merge_to"] or \
                V4.get(kw) != V4.get(mine, mine):
            bad16.append((kw, "merge row inconsistent"))
    elif expd == "keep_long":
        if r["decision"] != "keep" or "> 6" not in r["reason"]:
            bad16.append((kw, "expected keep over 6 words"))
    else:
        if r["decision"] != "keep" or not r["reason"].startswith("expanded form absent"):
            bad16.append((kw, "expected keep expanded form absent"))
        if mine in forms_union or mine in V4_TO:
            bad16.append((kw, "expanded form exists"))
add("C16_rows", "class-f rows: expansion by one considered token; merge iff expanded form in E1 x v3 T1 or v4 'to'",
    "%d rows: merge %d, keep %d" % (len(frows), sum(1 for r in frows if r["decision"] == "merge"),
                                    sum(1 for r in frows if r["decision"] == "keep")),
    "merge %d, keep absent %d, keep over 6 words %d; problems %d" % (p16["merge"], p16["keep_absent"], p16["keep_long"], len(bad16)),
    not bad16 and p16["merge"] == sum(1 for r in frows if r["decision"] == "merge"),
    ("first %s: %s; " % (kws(bad16[0][0]), bad16[0][1]) if bad16 else "") +
    "%d keep rows with expanded form not printed: recomputed, > 6 words, word count, token, long form match" % n_np)
# completeness on the final T1 v4: no remaining keyword qualifies for an f merge
fkw = {r["pair"].split(" | ")[0] for r in frows}
uncovered, missed = [], []
for k in sorted(T1V4F["author"] | T1V4F["index"]):
    ab, mine, lf = expand(k)
    if ab is None:
        continue
    if k not in fkw:
        uncovered.append(k)
    if mine is not None and nwords(mine) <= 6 and (mine in forms_union or mine in V4_TO) and k not in fkw:
        missed.append(k)
print("C16 uncovered sample:", [kws(x) for x in uncovered[:15]])
add("C16_complete", "T1 v4 keywords that qualify for class f but carry no class-f decision (missed merges)",
    0, "%d missed merges; %d qualifying forms without a candidate row" % (len(missed), len(uncovered)),
    not missed, ("first missed " + kws(missed[0])) if missed else
    "forms without a row are keeps by definition (expanded form absent, over 6 words or ambiguous)")

# ======================= C17 (S1) =======================


def labels(rows):
    return {r["keyword"]: r["cluster"] for r in rows if r["cluster"] != ""}


def rand_stats(p1, p2):
    common = sorted(set(p1) & set(p2))
    n = len(common)
    tb = ab_ = o1 = o2 = 0
    for a, b in itertools.combinations(common, 2):
        s1 = p1[a] == p1[b]
        s2 = p2[a] == p2[b]
        if s1 and s2:
            tb += 1
        elif not s1 and not s2:
            ab_ += 1
        elif s1:
            o1 += 1
        else:
            o2 += 1
    pairs = n * (n - 1) // 2
    rand = (tb + ab_) / pairs if pairs else 1.0
    sa = tb + o1
    sb = tb + o2
    expv = sa * sb / pairs if pairs else 0.0
    mx = 0.5 * (sa + sb)
    ari = (tb - expv) / (mx - expv) if mx != expv else 1.0
    return {"n1": len(p1), "n2": len(p2), "common": n, "pairs": pairs, "tb": tb, "ab": ab_, "o1": o1, "o2": o2,
            "rand": rand, "ari": ari}


S1 = read_dicts(TAB / "S1_partition_agreement.csv")
for L in LAYERS:
    out_l = labels(read_dicts(TAB / ("T3_%s_nodes.csv" % L)))
    for tag, src in (("a", PREV / "tables"), ("b", V3T)):
        first = labels(read_dicts(src / ("T3_%s_nodes.csv" % L)))
        st = rand_stats(first, out_l)
        comp = "I2 x v3 (F12.3c) vs E1 x v4" if tag == "a" else "E1 x v3 vs E1 x v4"
        rows = [r for r in S1 if r["layer"] == L and r["comparison"] == comp]
        if len(rows) != 1:
            add("C17_%s_%s" % (L, tag), "S1 row %s %s" % (L, comp), "1 row", "%d rows" % len(rows), False)
            continue
        r = rows[0]
        exp = (int(r["nodes_first"]), int(r["nodes_second"]), int(r["common_nodes"]), int(r["node_pairs"]),
               int(r["together_in_both"]), int(r["apart_in_both"]), int(r["together_only_in_first"]),
               int(r["together_only_in_second"]), float(r["rand_index"]), float(r["adjusted_rand_index"]))
        got = (st["n1"], st["n2"], st["common"], st["pairs"], st["tb"], st["ab"], st["o1"], st["o2"],
               round(st["rand"], 4), round(st["ari"], 4))
        add("C17_%s_%s" % (L, tag), "S1 %s %s: nodes, common, pairs, together/apart counts, Rand, ARI" % (L, comp),
            "; ".join(str(x) for x in exp), "; ".join(str(x) for x in got), exp == got,
            "Rand %.6f, ARI %.6f (Hubert-Arabie)" % (st["rand"], st["ari"]))

# ======================= C18 (v3 on E1) =======================
add("C18_records", "E1 x v3: records with author / index keywords",
    "json %s / %s" % (NUMS3["author"]["records_with_keywords"], NUMS3["index"]["records_with_keywords"]),
    "%d / %d" % (len(RUN[("v3", "author")][0]), len(RUN[("v3", "index")][0])),
    len(RUN[("v3", "author")][0]) == NUMS3["author"]["records_with_keywords"]
    and len(RUN[("v3", "index")][0]) == NUMS3["index"]["records_with_keywords"])
check_t1("C18_T1", "v3", V3T, NUMS3)
for L in LAYERS:
    bad = []
    for s in NUMS3[L]["sensitivity"]:
        t = s["threshold_records"]
        nw, ew = NET[("v3", L, t, True)]
        nn_, en_ = NET[("v3", L, t, False)]
        if (len(nw), len(ew), len(nn_), len(en_)) != (s["nodes_with_generic"], s["edges_with_generic"],
                                                      s["nodes_without_generic"], s["edges_without_generic"]):
            bad.append(t)
    add("C18_%s_sens" % L, "E1 x v3 %s threshold sensitivity t=3,5,8 (json)" % L, "json rows %d" % len(NUMS3[L]["sensitivity"]),
        "%d mismatching thresholds" % len(bad), not bad and len(NUMS3[L]["sensitivity"]) == 3)
    check_t3_t4("v3", L, V3T, NUMS3, {"nodes": "C18_%s_T3nodes" % L, "clusters": "C18_%s_clusters_Q" % L,
                                      "partition": "C18_%s_partition" % L, "edges": "C18_%s_T4" % L})

# ======================= C19 (S2 louvain) =======================
G, comms, Qg = PART[("v4", "author")]
greedy_lab = {}
for i, c in enumerate(comms):
    for n in c:
        greedy_lab[n] = i
S2 = read_dicts(TAB / "S2_algorithm_sensitivity.csv")
S2b = read_dicts(TAB / "S2b_leading_pairs.csv")
# leading pairs from my partition and T3 cluster numbers: top 3 keywords of clusters 1..10 by (-records, keyword)
t3lab = labels(read_dicts(TAB / "T3_author_nodes.csv"))
bycl = defaultdict(list)
for k, c in t3lab.items():
    bycl[int(c)].append(k)
lp_mine = []
for c in range(1, 11):
    top = sorted(bycl[c], key=lambda k: (-FA4[k], k))[:3]
    for a, b in itertools.combinations(top, 2):
        lp_mine.append((c, top[0], a, b))
lp_file = [(int(r["cluster"]), r["leading_keyword"], r["keyword_a"], r["keyword_b"]) for r in S2b]
together = Counter()
seed_rows = {}
for s in range(1, 21):
    lc = louvain_communities(G, weight="assoc", resolution=1.0, seed=s)
    lab = {}
    for i, c in enumerate(lc):
        for n in c:
            lab[n] = i
    q = modularity(G, lc, weight="assoc", resolution=1.0)
    st = rand_stats(greedy_lab, lab)
    lpt = 0
    for (_, _, a, b) in lp_file:
        if lab[a] == lab[b]:
            lpt += 1
            together[(a, b)] += 1
    seed_rows[str(s)] = (len(lc), round(q, 4), round(st["rand"], 4), round(st["ari"], 4), lpt, len(lp_file))
bad19 = []
for r in S2:
    if r["seed"] in seed_rows:
        exp = (int(r["clusters"]), float(r["modularity"]), float(r["rand_vs_greedy"]), float(r["adjusted_rand_vs_greedy"]),
               int(r["leading_pairs_together"]), int(r["leading_pairs"]))
        if exp != seed_rows[r["seed"]]:
            bad19.append(r["seed"])
nseed = sum(1 for r in S2 if r["seed"] in seed_rows)
add("C19_seeds", "S2 louvain seeds 1-20: clusters, modularity, Rand and ARI vs greedy, leading pairs together",
    "%d seed rows" % nseed, "%d mismatching seeds" % len(bad19), not bad19 and nseed == 20,
    ("mismatch seeds " + ",".join(bad19[:6])) if bad19 else "")
summ = {r["seed"]: r for r in S2 if r["seed"] not in seed_rows}
cols = ["clusters", "modularity", "rand_vs_greedy", "adjusted_rand_vs_greedy", "leading_pairs_together"]
bad_s = []
for j, cn in enumerate(cols):
    vals = [seed_rows[str(s)][j] for s in range(1, 21)]
    for key, fn_ in (("min", min), ("median", statistics.median), ("max", max)):
        if key in summ and abs(float(summ[key][cn]) - float(fn_(vals))) > 1e-9:
            bad_s.append("%s %s" % (key, cn))
g = summ.get("greedy (T5)")
g_ok = g is not None and int(g["clusters"]) == len(comms) and float(g["modularity"]) == round(Qg, 4)
add("C19_summary", "S2 min / median / max rows and greedy row", "rows min, median, max, greedy",
    "%d mismatches; greedy row ok: %s" % (len(bad_s), g_ok), not bad_s and g_ok, ", ".join(bad_s[:4]))
rt_bad = [r for r in S2b if int(r["runs_together"]) != together[(r["keyword_a"], r["keyword_b"])]
          or r["share_of_runs"] != "%.2f" % (together[(r["keyword_a"], r["keyword_b"])] / 20)]
add("C19_pairs", "S2b leading pairs = top-3 pairs of clusters 1-10; runs together and share over 20 seeds",
    "%d pairs" % len(lp_file), "%d pairs rebuilt; equal: %s; runs mismatches %d" % (len(lp_mine), lp_mine == lp_file, len(rt_bad)),
    lp_mine == lp_file and not rt_bad)

# ======================= C20 (T8 title bigrams, extra) =======================
mdtxt = " ".join(open(TAB / "T8_title_bigrams_vs_keywords.md", encoding="utf-8").read().split())
m = re.search(r"Stop words \((\d+)\): (.*?)\. as_keyword:", mdtxt)
STOPW = set(m.group(2).split()) if m else set()
nstop_decl = int(m.group(1)) if m else -1
bg = Counter()
for e in EIDS:
    t = TITLE[e].lower()
    for d in DASH:
        t = t.replace(d, " ")
    seen = set()
    for seg in re.split(r"[^a-z0-9 ]", t):
        toks = seg.split()
        for a, b in zip(toks, toks[1:]):
            if a not in STOPW and b not in STOPW:
                seen.add(a + " " + b)
    bg.update(seen)
rank_author = {r[1]: r[0] for r in T1MINE[("v4", "author")]}
top20 = sorted(bg.items(), key=lambda x: (-x[1], x[0]))[:20]
mine8 = []
for i, (b, c) in enumerate(top20, 1):
    ak = norm_kw(b)
    ak = V4.get(ak, ak)
    mine8.append((str(i), b, str(c), ak, str(FA4.get(ak, 0)), str(rank_author[ak]) if ak in rank_author else ""))
T8 = [(r["title_rank"], r["title_bigram"], r["title_records"], r["as_keyword"], r["author_kw_records"], r["author_kw_rank"])
      for r in read_dicts(TAB / "T8_title_bigrams_vs_keywords.csv")]
tb_json = NUMS["title_bigrams"]
in_top20 = sum(1 for x in mine8 if x[5] != "" and int(x[5]) <= 20)
present = sum(1 for x in mine8 if int(x[4]) > 0)
add("C20_T8", "extra: T8 title bigrams top 20 (records, as_keyword, author records and rank); json counts",
    "%d rows; json distinct %d, stop words %d, in author top20 %d, present %d"
    % (len(T8), tb_json["distinct"], tb_json["stop_words"], tb_json["top20_in_author_top20"], tb_json["top20_present_as_author_kw"]),
    "rows equal: %s; distinct %d, stop words %d (md says %d), %d, %d" % (T8 == mine8, len(bg), len(STOPW), nstop_decl, in_top20, present),
    T8 == mine8 and len(bg) == tb_json["distinct"] and len(STOPW) == tb_json["stop_words"] == nstop_decl
    and in_top20 == tb_json["top20_in_author_top20"] and present == tb_json["top20_present_as_author_kw"])
asset = {x[3] for x in mine8}
T8b = [(r["author_kw_rank"], r["keyword"], r["records"], r["generic"], r["in_title_top20"])
       for r in read_dicts(TAB / "T8b_keywords_vs_title_bigrams.csv")]
mine8b = [(str(r[0]), r[1], str(r[2]), str(r[4]), "1" if r[1] in asset else "0") for r in T1MINE[("v4", "author")][:20]]
add("C20_T8b", "extra: T8b author top 20 against title top 20 (in_title_top20 = as_keyword match)",
    "%d rows" % len(T8b), "rows equal: %s" % (T8b == mine8b), T8b == mine8b)

# ======================= C21 (class c / c' decisions, extra) =======================


def red(s):
    return re.sub(r"[^a-z0-9]", "", s)


def abbr_test(short, long_):
    a, b = red(short), red(long_)
    if not a or not b or a[0] != b[0]:
        return False
    it = iter(b)
    return all(ch in it for ch in a)


bad21 = []
n21 = Counter()
for r in cand4:
    cl = r["class"]
    if cl not in ("c' mid bracket", "c bracket (new form)"):
        continue
    kw = r["pair"].split(" | ")[0]
    X, Y, Z = bsplit(kw)
    if cl == "c' mid bracket":
        if X is None or not Z:
            bad21.append((kw, "not a mid bracket form"))
            continue
        if re.fullmatch(r"[a-z0-9./-]{1,8}", Y):
            exp = " ".join((X + " " + Z).split())
        elif " " not in X and len(X) <= 8 and " " in Y:
            exp = " ".join((Y + " " + Z).split())
        else:
            exp = None
    else:
        if X is None or Z or not kw.endswith(")"):
            bad21.append((kw, "not a final bracket form"))
            continue
        if re.fullmatch(r"[a-z0-9.-]{1,8}", Y):
            exp = X if abbr_test(Y, X) else None
        elif " " not in X and len(X) <= 8 and " " in Y:
            exp = Y if abbr_test(X, Y) else None
        else:
            exp = None
        if kw in prevT1:
            bad21.append((kw, "form present in F12.3c T1"))
    n21[cl] += 1
    if exp is None:
        if r["decision"] != "keep":
            bad21.append((kw, "expected keep"))
    else:
        if r["decision"] != "merge" or r["pair"] != kw + " | " + exp or r["merge_from"] != kw or \
                V4.get(kw) != V4.get(exp, exp):
            bad21.append((kw, "expected merge to rule target"))
# completeness against the E1 x v3 T1 forms
cnew_exp = {k for k in forms_union if k.endswith(")") and "(" in k and bsplit(k)[2] == "" and k not in prevT1}
cmid_exp = {k for k in forms_union if bsplit(k)[0] is not None and bsplit(k)[2] != ""}
cnew_got = {r["pair"].split(" | ")[0] for r in cand4 if r["class"] == "c bracket (new form)"}
cmid_got = {r["pair"].split(" | ")[0] for r in cand4 if r["class"] == "c' mid bracket"}
add("C21_c_classes", "extra: class c' and c (new form) decisions by the stated rules; candidate sets vs E1 x v3 T1 forms",
    "c' %d rows, c new %d rows" % (len(cmid_got), len(cnew_got)),
    "rule problems %d; c' set equal: %s (%d forms); c new set equal: %s (%d forms)"
    % (len(bad21), cmid_exp == cmid_got, len(cmid_exp), cnew_exp == cnew_got, len(cnew_exp)),
    not bad21 and cmid_exp == cmid_got and cnew_exp == cnew_got,
    ("first %s: %s" % (kws(bad21[0][0]), bad21[0][1])) if bad21 else
    ("c' only in T1: %d, only in candidates: %d; c new only in T1: %d, only in candidates: %d"
     % (len(cmid_exp - cmid_got), len(cmid_got - cmid_exp), len(cnew_exp - cnew_got), len(cnew_got - cnew_exp))))
print("c' T1-only:", [kws(x) for x in sorted(cmid_exp - cmid_got)][:10], "cand-only:", [kws(x) for x in sorted(cmid_got - cmid_exp)][:10])
print("c new T1-only:", [kws(x) for x in sorted(cnew_exp - cnew_got)][:10], "cand-only:", [kws(x) for x in sorted(cnew_got - cnew_exp)][:10])

# ======================= write =======================
for r in results:
    for c, v in r.items():
        assert nwords(v) <= 30, (r["check_id"], c)
with open(RESULT, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["check_id", "what", "expected_from_tables", "recomputed", "verdict", "note"])
    w.writeheader()
    w.writerows(results)
print("PASS", sum(1 for r in results if r["verdict"] == "PASS"), "FAIL", sum(1 for r in results if r["verdict"] == "FAIL"))
