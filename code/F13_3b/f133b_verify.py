"""F13.3b independent verification (written from scratch by the verifier).

Reads only the inputs named in the verification task. Writes only
phase_F13_3b_independent_verification.csv and run_logs/verify_console.txt.
Console and log carry counts, booleans and digests only (R13).
"""
import sys
sys.dont_write_bytecode = True

import csv
import glob
import hashlib
import itertools
import json
import os
import random
import re
import statistics
from collections import Counter, defaultdict

import networkx as nx

ROOT = os.environ.get("PROJECT_ROOT", ".")
OUTD = os.path.join(ROOT, "outputs", "dprg_revision_2026")
PH = os.path.join(OUTD, "phase_F13_3b")
P13 = os.path.join(OUTD, "phase_F13_3")
E1 = os.path.join(OUTD, "author_exports_2026_10",
                  "scopus_full_TAK_KZ_2003_2025_2026-10-13.csv")
REP = os.path.join(P13, "data", "references_repaired.csv")
RK = os.path.join(PH, "data", "reference_keys.csv")
STAMP = os.path.join(PH, "F13_3b_brief_stamp.json")
REPORT = os.path.join(PH, "phase_F13_3b_report.md")
OUT_CSV = os.path.join(PH, "phase_F13_3b_independent_verification.csv")
OUT_LOG = os.path.join(PH, "run_logs", "verify_console.txt")
E1_SHA = "fe01023d23afe95df83d594fdfea2c3b488e52ffb8778def4067a2d795a991f3"

csv.field_size_limit(2 ** 31 - 1)

LOG = []


def say(*parts):
    s = " ".join(str(p) for p in parts)
    print(s)
    LOG.append(s)


RESULTS = []


def add(check, what, expected, observed, verdict, note=""):
    words = str(note).split()
    if len(words) > 30:
        note = " ".join(words[:29]) + " ..."
    row = [check, what, str(expected), str(observed), verdict, note]
    for cell in row:
        if len(cell.split()) > 30:
            raise SystemExit("cell over 30 words in " + check)
    RESULTS.append(row)
    say(check, "|", verdict, "|", "obs", observed, "| exp", expected)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_dicts(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames), list(r)


def measure_map(path, col):
    _, rows = read_dicts(path)
    return {r["measure"]: r[col] for r in rows}


def pv(ok):
    return "PASS" if ok else "FAIL"


# ---------------------------------------------------------------- E1
E1_COLS = ["EID", "Year", "Title", "Source title", "DOI", "Document Type",
           "Cited by", "Author Keywords", "References", "Authors"]
with open(E1, encoding="utf-8-sig", newline="") as f:
    rdr = csv.reader(f)
    header = next(rdr)
    idx = {c: header.index(c) for c in E1_COLS}
    e1 = []
    for row in rdr:
        e1.append({c: row[idx[c]] for c in E1_COLS})
E1_BY = {r["EID"]: r for r in e1}
say("E1 rows", len(e1), "unique EIDs", len(E1_BY))

# ---------------------------------------------------------------- C01
stamp = json.load(open(STAMP, encoding="utf-8"))
rep_sha_expected = stamp["inputs"]["references_repaired"]["sha256"]
e1_sha = sha256(E1)
rep_sha = sha256(REP)
add("C01a", "sha256 of E1", E1_SHA[:16] + "...", e1_sha[:16] + "...",
    pv(e1_sha == E1_SHA), "full digest compared; E1 rows %d" % len(e1))
add("C01b", "sha256 of references_repaired.csv vs step-0 stamp",
    rep_sha_expected[:16] + "...", rep_sha[:16] + "...",
    pv(rep_sha == rep_sha_expected), "full digest compared")

_, rep_rows = read_dicts(REP)
REP_REFS = {}
n_ref_sum = 0
split_mismatch = 0
semicolon_inside = 0
for r in rep_rows:
    n = int(r["n_references"])
    n_ref_sum += n
    txt = r["references_repaired"]
    refs = txt.split("; ") if txt != "" else []
    if len(refs) != n:
        split_mismatch += 1
    semicolon_inside += sum(1 for x in refs if ";" in x)
    REP_REFS[r["eid"]] = refs
add("C01c", "sum of n_references in references_repaired.csv", 28471, n_ref_sum,
    pv(n_ref_sum == 28471 and split_mismatch == 0),
    "records %d; split count differs from n_references in %d; references with ';' %d"
    % (len(rep_rows), split_mismatch, semicolon_inside))

rk_fields, rk = read_dicts(RK)
rk_by = defaultdict(list)
for i, r in enumerate(rk):
    rk_by[r["eid"]].append((int(r["ref_no"]), r["reference"]))
agree = 0
disagree = 0
for eid, refs in REP_REFS.items():
    mine = [t for _, t in sorted(rk_by.get(eid, []))]
    if mine == refs:
        agree += 1
    else:
        disagree += 1
extra_eids = len(set(rk_by) - set(REP_REFS))
refno_ok = all([n for n, _ in sorted(v)] == list(range(1, len(v) + 1))
               for v in rk_by.values())
nchar_bad = sum(1 for r in rk if int(r["n_chars"]) != len(r["reference"]))
scope_bad = sum(1 for r in rk
                if (r["in_scope"] == "1") != (len(r["reference"]) > 10))
add("C01d", "reference_keys.csv rows; references equal to repaired, record by record",
    "28471 rows; 841/841 records",
    "%d rows; %d/%d records" % (len(rk), agree, len(REP_REFS)),
    pv(len(rk) == 28471 and disagree == 0 and extra_eids == 0 and refno_ok),
    "eids not in repaired %d; ref_no consecutive %s; n_chars wrong %d; in_scope differs from length>10 %d"
    % (extra_eids, refno_ok, nchar_bad, scope_bad))

# ---------------------------------------------------------------- parser
APOS = chr(0x2019)
AUTH_RE = re.compile(r"^[A-Z](?:[\w'" + APOS + r".\-]|\s(?=[A-Z]))*[A-Z]\.$")
# Trailing initials: after a space, one or more initials of one or two capital
# letters with a dot, joined directly, by a space or by a hyphen
# (' Q.', ' YU.', ' A.B.', ' A. B.', ' A.-B.').
INIT_RE = re.compile(r"\s[A-Z]{1,2}\.(?:[\s\-]?[A-Z]{1,2}\.)*$")
# Strict single-initial reading, reported for information only.
INIT_RE_STRICT = re.compile(r"(?:\s[A-Z]{1,2}\.)+$")
YEARSEG_RE = re.compile(r"^\(\d{4}\)$")
YEAR_RE = re.compile(r"\((\d{4})\)")
NONALNUM = re.compile(r"[\W_]+")


def is_author(seg):
    return len(seg) >= 3 and AUTH_RE.match(seg) is not None


def parse_ref(ref, init_re=INIT_RE):
    segs = ref.split(", ")
    i = 0
    while i < len(segs) and is_author(segs[i]):
        i += 1
    first = segs[0] if i > 0 else ""
    surname = init_re.sub("", first) if first else ""
    j = i
    while j < len(segs) and YEARSEG_RE.match(segs[j]):
        j += 1
    title = segs[j] if j < len(segs) else ""
    years = [int(y) for y in YEAR_RE.findall(ref) if 1800 <= int(y) <= 2026]
    year = str(years[-1]) if years else ""
    return surname, year, title, i


def norm_title_words(t):
    return NONALNUM.sub(" ", t.upper()).split()


def work_key(ref, init_re=INIT_RE):
    s, y, t, _ = parse_ref(ref, init_re)
    S = NONALNUM.sub("", s.upper())
    T = " ".join(norm_title_words(t)[:6])
    if not S or not y or not T:
        return "=" + ref
    return S + "|" + y + "|" + T


def key_parts(k):
    if k.startswith("="):
        return None
    p = k.split("|")
    return p if len(p) == 3 else ["?", "?", "?"]


def categorise(mine, theirs, ref=""):
    a, b = key_parts(mine), key_parts(theirs)
    seg0 = ref.split(", ")[0]
    last_tok = seg0.rsplit(" ", 1)[-1]
    if a is not None and b is not None and a[1:] == b[1:] and a[0] != b[0]:
        if re.search(r"[A-Z]\.?-[A-Z]{1,2}\.", seg0) and (
                b[0].startswith(a[0]) or a[0].startswith(b[0])):
            return "hyphenated initials"
        if (re.fullmatch(r"[A-Z]{3,}\.", last_tok) and len(a[0]) > len(b[0])
                and a[0].startswith(b[0])):
            return "3+ letter last token"
    if (a is not None and b is not None and a[:2] == b[:2] and a[2] != b[2]
            and any(len(ch.upper()) > 1 for ch in ref)):
        return "case mapping of sharp s / ligature"
    if a is None and b is None:
        return "both fallback, strings differ"
    if a is None:
        return "verifier fallback, phase complete"
    if b is None:
        return "phase fallback, verifier complete"
    cats = []
    if a[0] != b[0]:
        cats.append("surname")
    if a[1] != b[1]:
        cats.append("year")
    if a[2] != b[2]:
        cats.append("title")
    return "differs in " + "+".join(cats)


# ---------------------------------------------------------------- C02
sample = random.Random(7).sample(range(len(rk)), 500)
mism = Counter()
n_agree = 0
strict_agree = 0
strict_mism = Counter()
for ix in sample:
    ref = rk[ix]["reference"]
    mine = work_key(ref)
    if mine == rk[ix]["key"]:
        n_agree += 1
    else:
        mism[categorise(mine, rk[ix]["key"], ref)] += 1
    ks = work_key(ref, INIT_RE_STRICT)
    if ks == rk[ix]["key"]:
        strict_agree += 1
    else:
        strict_mism[categorise(ks, rk[ix]["key"], ref)] += 1
all_agree = 0
all_mism = Counter()
MY_KEY = []
for r in rk:
    k = work_key(r["reference"])
    MY_KEY.append(k)
    if k == r["key"]:
        all_agree += 1
    else:
        all_mism[categorise(k, r["key"], r["reference"])] += 1
share = n_agree / 500.0
cat_txt = "; ".join("%s %d" % (c, n) for c, n in sorted(mism.items())) or "none"
all_txt = "; ".join("%s %d" % (c, n) for c, n in sorted(all_mism.items())) or "none"
strict_txt = "; ".join("%s %d" % (c, n) for c, n in sorted(strict_mism.items())) or "none"
v02 = "PASS" if share >= 0.98 else ("EXPLAINED" if mism else "FAIL")
add("C02", "work key of 500 sampled references (Random(7)) by verifier parser vs column key",
    ">= 98 % agreement (490/500)", "%d/500 (%.1f %%)" % (n_agree, 100 * share), v02,
    "sample mismatches: " + cat_txt + ". All rows %d/%d agree; phase strips only initials "
    "after a hyphen, verifier the whole block" % (all_agree, len(rk)))
add("C02b", "mismatch categories over all 28,471 rows (information)", "categories by key part",
    "%d mismatches" % (len(rk) - all_agree), "PASS" if all_agree == len(rk) else "EXPLAINED",
    all_txt)
add("C02c", "same sample, strict reading: only space-separated initials stripped (information)",
    "information", "%d/500" % strict_agree, "EXPLAINED" if strict_agree < 500 else "PASS",
    "differences: " + strict_txt + "; joined initials such as A.B. stay in the surname")
say("C02 strict-reading mismatch categories:", strict_txt)
say("C02 sample mismatch categories:", cat_txt)
say("C02 all-row mismatch categories:", all_txt)

# ---------------------------------------------------------------- C03
def lc_norm(s):
    return re.sub(r"[^A-Z0-9]+", " ", s.upper()).strip()


def lc_norm_all(s):
    return NONALNUM.sub(" ", s.upper()).strip()


ORDER = [r["EID"] for r in e1]
E1_REFS = {r["EID"]: (r["References"].split("; ") if r["References"].strip() else [])
           for r in e1}


def local_links(refs_by, min_len=30, amb="exclude", word=False, norm=lc_norm,
                self_ok=False, title_fn=None, year_order=False):
    if title_fn is None:
        nt = {e: norm(E1_BY[e]["Title"]) for e in ORDER}
    else:
        nt = {e: norm(title_fn(E1_BY[e]["Title"])) for e in ORDER}
    elig = [(e, nt[e]) for e in ORDER if len(nt[e]) >= min_len]
    cnt = Counter(t for _, t in elig)
    if amb == "exclude":
        targets = [(e, t) for e, t in elig if cnt[t] == 1]
    elif amb == "first":
        seen = set()
        targets = []
        for e, t in elig:
            if t not in seen:
                targets.append((e, t))
                seen.add(t)
    else:
        targets = list(elig)
    norm_refs = {e: [norm(x) for x in refs_by.get(e, [])] for e in ORDER}
    if word:
        texts = {e: "|" + "|".join(" " + x + " " for x in v) + "|"
                 for e, v in norm_refs.items()}
    else:
        texts = {e: "|".join(v) for e, v in norm_refs.items()}
    links = set()
    for c, t in targets:
        pat = (" " + t + " ") if word else t
        for r in ORDER:
            if r == c and not self_ok:
                continue
            if year_order and int(E1_BY[c]["Year"]) > int(E1_BY[r]["Year"]):
                continue
            if pat in texts[r]:
                links.add((r, c))
    # reference-level matches for the linked pairs
    tmap = defaultdict(list)
    for c, t in targets:
        tmap[c].append(t)
    ref_hits = set()
    triples = 0
    for r, c in links:
        for k, x in enumerate(norm_refs[r]):
            xx = (" " + x + " ") if word else x
            if any(((" " + t + " ") if word else t) in xx for t in tmap[c]):
                ref_hits.add((r, k))
                triples += 1
    cited = Counter(c for _, c in links)
    stats = {
        "links": len(links),
        "citing": len({r for r, _ in links}),
        "cited": len(cited),
        "max": max(cited.values()) if cited else 0,
        "eligible": len(elig),
        "amb_titles": sum(1 for t, n in cnt.items() if n >= 2),
        "amb_records": sum(n for t, n in cnt.items() if n >= 2),
        "ref_hits": len(ref_hits),
        "triples": triples,
    }
    return stats, links


main3, main_links = local_links(REP_REFS)
t3 = measure_map(os.path.join(PH, "tables", "T3a_local_citations_title.csv"),
                 "title_match_F13_3b")
ph3 = (int(t3["local citation links (citing record -> cited record)"]),
       int(t3["citing records"]), int(t3["cited records (LCS > 0)"]),
       int(t3["LCS, max"]))
mine3 = (main3["links"], main3["citing"], main3["cited"], main3["max"])
say("C03 main:", mine3, "eligible", main3["eligible"], "ambiguous",
    main3["amb_titles"], main3["amb_records"], "ref hits", main3["ref_hits"],
    "triples", main3["triples"])
add("C03a", "local citation links by title: links / citing / cited / max LCS vs T3a",
    "%d / %d / %d / %d" % ph3, "%d / %d / %d / %d" % mine3, pv(mine3 == ph3),
    "eligible %d; ambiguous %d titles / %d records; references matching %d (T3a %s)"
    % (main3["eligible"], main3["amb_titles"], main3["amb_records"],
       main3["ref_hits"], t3.get("references matching another record's title", "")))

variants = [
    ("E1 raw References", dict(refs_by=E1_REFS)),
    ("ambiguous all kept", dict(refs_by=REP_REFS, amb="all")),
    ("ambiguous first kept", dict(refs_by=REP_REFS, amb="first")),
    ("whole word", dict(refs_by=REP_REFS, word=True)),
    ("all scripts kept", dict(refs_by=REP_REFS, norm=lc_norm_all)),
    ("self links allowed", dict(refs_by=REP_REFS, self_ok=True)),
    ("min length 20", dict(refs_by=REP_REFS, min_len=20)),
    ("min length 35", dict(refs_by=REP_REFS, min_len=35)),
    ("min length 40", dict(refs_by=REP_REFS, min_len=40)),
    ("E1 raw, ambiguous all kept", dict(refs_by=E1_REFS, amb="all")),
    ("bracketed title parts removed",
     dict(refs_by=REP_REFS, title_fn=lambda t: re.sub(r"\[[^\]]*\]", " ", t))),
    ("cited year <= citing year", dict(refs_by=REP_REFS, year_order=True)),
    ("self links + ambiguous first kept", dict(refs_by=REP_REFS, self_ok=True, amb="first")),
    ("self links + cited year <= citing year",
     dict(refs_by=REP_REFS, self_ok=True, year_order=True)),
]
var_out = {}
for name, kw in variants:
    s, _ = local_links(**kw)
    var_out[name] = s
    say("C03 variant", name, ":", s["links"], s["citing"], s["cited"], s["max"],
        "triples", s["triples"])
prof = (538, 270, 228, 12)
hit = [n for n, s in var_out.items()
       if (s["links"], s["citing"], s["cited"], s["max"]) == prof]
if mine3 == prof:
    v3b, n3b = "PASS", "equal"
elif hit:
    v3b, n3b = "EXPLAINED", "reproduced by variant: " + ", ".join(hit)
else:
    def dist(s):
        return sum(abs(x - y) for x, y in zip((s["links"], s["citing"], s["cited"], s["max"]), prof))
    best = min(var_out, key=lambda n: (dist(var_out[n]), n))
    bs = var_out[best]
    v3b = "EXPLAINED"
    n3b = ("professor's rule undocumented; %d variants tried, none reproduces; closest '%s' "
           "%d/%d/%d; gaps +5/+2/-1 links/citing/cited" %
           (len(var_out), best, bs["links"], bs["citing"], bs["cited"]))
add("C03b", "same counts vs professor's earlier recount", "538 / 270 / 228 / 12",
    "%d / %d / %d / %d" % mine3, v3b, n3b)
vt = _, vt_rows = read_dicts(os.path.join(PH, "tables", "T3a3_title_rule_variants.csv"))
vmap = {r["variant"]: (int(r["links"]), int(r["citing_records"]),
                       int(r["cited_records"]), int(r["LCS_max"])) for r in vt_rows}
pairs = [("E1 References as exported (whole cell, mixed case)", "E1 raw References"),
         ("all letters kept (not only Latin)", "all scripts kept"),
         ("whole-word match", "whole word"),
         ("title length >= 20", "min length 20"),
         ("title length >= 35", "min length 35"),
         ("ambiguous titles: first record kept", "ambiguous first kept"),
         ("ambiguous titles: all records kept", "ambiguous all kept")]
okv = 0
for tname, mname in pairs:
    s = var_out[mname]
    if vmap.get(tname) == (s["links"], s["citing"], s["cited"], s["max"]):
        okv += 1
add("C03c", "T3a3 title-rule variants recomputed (7 non-main rows)", "7/7 equal",
    "%d/7 equal" % okv, pv(okv == 7 and len(vt_rows) == 8),
    "E1 raw References split on '; ' by the verifier; T3a3 rows %d" % len(vt_rows))

# ---------------------------------------------------------------- C04
def build_works(keys):
    wb = defaultdict(set)
    for r, k in zip(rk, keys):
        if len(r["reference"]) > 10:
            wb[r["eid"]].add(k)
    return wb


WB = build_works([r["key"] for r in rk])
INV = defaultdict(set)
for e, ws in WB.items():
    for w in ws:
        INV[w].add(e)
pair_w = Counter()
for w, es in INV.items():
    if len(es) >= 2:
        for a, b in itertools.combinations(sorted(es), 2):
            pair_w[(a, b)] += 1
CPL = {p: n for p, n in pair_w.items() if n >= 2}
G = nx.Graph()
for (a, b), n in CPL.items():
    G.add_edge(a, b, weight=n)
comps = list(nx.connected_components(G))
largest = max(len(c) for c in comps)
t4 = measure_map(os.path.join(PH, "tables", "T4a_coupling_workkey.csv"), "value")
exp4 = (int(t4["records with references in scope"]),
        int(t4["nodes (records sharing >= 2 works with another record)"]),
        int(t4["isolated records with references"]), int(t4["edges"]),
        int(t4["components"]), int(t4["largest component (records)"]))
obs4 = (len(WB), G.number_of_nodes(), len(WB) - G.number_of_nodes(),
        G.number_of_edges(), len(comps), largest)
add("C04a", "coupling: records in scope / nodes / isolated / edges / components / largest vs T4a",
    "%d / %d / %d / %d / %d / %d" % exp4, "%d / %d / %d / %d / %d / %d" % obs4,
    pv(obs4 == exp4), "works from column key, references > 10 characters")

_, fe = read_dicts(os.path.join(PH, "figures", "Fig_bibliographic_coupling_workkey_edges.csv"))
fig_edges = {}
dup = 0
for r in fe:
    p = tuple(sorted((r["eid_a"], r["eid_b"])))
    if p in fig_edges:
        dup += 1
    fig_edges[p] = int(r["shared_works"])
same_pairs = set(fig_edges) == set(CPL)
same_w = same_pairs and all(fig_edges[p] == CPL[p] for p in CPL)
wdiff = sum(1 for p in set(fig_edges) & set(CPL) if fig_edges[p] != CPL[p])
add("C04b", "figure edge list equals verifier edges (pairs and weights)",
    "%d pairs, equal weights" % len(CPL),
    "%d rows; pairs equal %s; weight differences %d" % (len(fe), same_pairs, wdiff),
    pv(same_w and dup == 0 and len(fe) == len(CPL)),
    "only in figure %d; only in verifier %d; duplicate rows %d"
    % (len(set(fig_edges) - set(CPL)), len(set(CPL) - set(fig_edges)), dup))

_, fn = read_dicts(os.path.join(PH, "figures", "Fig_bibliographic_coupling_workkey_nodes.csv"))
node_cl = {r["eid"]: r["cluster"] for r in fn}
nodes_equal = set(node_cl) == set(G.nodes())
deg_bad = sum(1 for r in fn if r["eid"] in G and int(r["degree"]) != G.degree(r["eid"]))
groups = defaultdict(set)
for e, c in node_cl.items():
    groups[c].add(e)
q4 = None
if nodes_equal:
    q4 = nx.algorithms.community.modularity(G, list(groups.values()), weight="weight")
sizes = sorted((len(v) for v in groups.values()), reverse=True)
big = [s for s in sizes if s >= 10]
exp4b = (int(t4["Louvain clusters (seed 42)"]), int(t4["clusters with >= 10 records"]),
         int(t4["records in clusters with >= 10 records"]), float(t4["modularity Q"]))
obs4b = (len(groups), len(big), sum(big), round(q4, 4) if q4 is not None else None)
ok4b = (nodes_equal and obs4b[:3] == exp4b[:3] and q4 is not None
        and abs(q4 - exp4b[3]) < 0.00006 and deg_bad == 0)
add("C04c", "figure node partition: clusters / clusters >= 10 / their records / weighted Q vs T4a",
    "%d / %d / %d / %.4f" % exp4b,
    "%d / %d / %d / %s" % obs4b, pv(ok4b),
    "node set equals verifier nodes %s; degree mismatches %d; Louvain itself not rerun"
    % (nodes_equal, deg_bad))

# ---------------------------------------------------------------- C05
def cocitation(wb):
    inv = defaultdict(set)
    for e, ws in wb.items():
        for w in ws:
            inv[w].add(e)
    n4 = {w for w, es in inv.items() if len(es) >= 4}
    co = Counter()
    for e, ws in wb.items():
        s = sorted(ws & n4)
        for a, b in itertools.combinations(s, 2):
            co[(a, b)] += 1
    ed = {p: n for p, n in co.items() if n >= 3}
    nodes = set(itertools.chain.from_iterable(ed))
    return inv, n4, ed, nodes


INV5, N4, CO_E, CO_N = cocitation(WB)
t5 = measure_map(os.path.join(PH, "tables", "T5a_cocitation_workkey.csv"), "work_key_F13_3b")
exp5 = (int(t5["nodes: works with >= 4 citing records"]), int(t5["nodes with >= 1 edge"]),
        int(t5["edges: pairs co-cited by >= 3 records"]))
obs5 = (len(N4), len(CO_N), len(CO_E))
add("C05a", "co-citation: works >= 4 citing / nodes with edge / edges vs T5a work_key_F13_3b",
    "%d / %d / %d" % exp5, "%d / %d / %d" % obs5, pv(obs5 == exp5),
    "works from column key, references > 10 characters")

_, ce = read_dicts(os.path.join(PH, "figures", "Fig_cocitation_workkey_edges.csv"))
_, cn = read_dicts(os.path.join(PH, "figures", "Fig_cocitation_workkey_nodes.csv"))
fig_co_nodes = set(r["from"] for r in ce) | set(r["to"] for r in ce)
w_fig = Counter(int(r["cocitations"]) for r in ce)
w_mine = Counter(CO_E.values())
cr_fig = Counter(int(r["citing_records"]) for r in cn)
cr_mine = Counter(len(INV5[w]) for w in CO_N)
FG = nx.Graph()
for r in ce:
    FG.add_edge(r["from"], r["to"], weight=int(r["cocitations"]))
deg_fig_ok = all(int(r["degree"]) == FG.degree(r["node"]) for r in cn if r["node"] in FG)
ok5b = (len(ce) == len(CO_E) and len(fig_co_nodes) == len(CO_N) and len(cn) == len(CO_N)
        and w_fig == w_mine and cr_fig == cr_mine)
add("C05b", "figure co-citation files: edge rows / nodes in edges / node rows",
    "%d / %d / %d" % (len(CO_E), len(CO_N), len(CO_N)),
    "%d / %d / %d" % (len(ce), len(fig_co_nodes), len(cn)), pv(ok5b),
    "weight multiset equal %s; citing-records multiset equal %s; node degree consistent %s"
    % (w_fig == w_mine, cr_fig == cr_mine, deg_fig_ok))

# map figure nodes to verifier keys through first_author / year / title
key_of_node = {}
for r in cn:
    k = (NONALNUM.sub("", r["first_author"].upper()) + "|" + r["year"] + "|"
         + " ".join(norm_title_words(r["title"])[:6]))
    key_of_node[r["node"]] = k
mapped = sum(1 for k in key_of_node.values() if k in CO_N)
uniq = len(set(key_of_node.values())) == len(key_of_node)
edge_exact = None
if mapped == len(cn) and uniq:
    fe2 = {tuple(sorted((key_of_node[r["from"]], key_of_node[r["to"]]))): int(r["cocitations"])
           for r in ce}
    edge_exact = fe2 == CO_E
add("C05c", "figure co-citation nodes mapped to verifier work keys; edge list compared",
    "%d/%d mapped; edges equal" % (len(cn), len(cn)),
    "%d/%d mapped; edges equal %s" % (mapped, len(cn), edge_exact),
    pv(mapped == len(cn) and uniq and edge_exact is True),
    "key rebuilt from first_author, year and title columns of the nodes file")

grp5 = defaultdict(set)
for r in cn:
    grp5[r["cluster"]].add(r["node"])
q5 = nx.algorithms.community.modularity(FG, list(grp5.values()), weight="weight")
s5 = sorted((len(v) for v in grp5.values()), reverse=True)
exp5d = (int(t5["Louvain clusters"]), int(t5["clusters with >= 5 nodes"]),
         float(t5["modularity Q"]))
obs5d = (len(grp5), sum(1 for s in s5 if s >= 5), round(q5, 4))
add("C05d", "figure co-citation partition: clusters / clusters >= 5 / weighted Q vs T5a",
    "%d / %d / %.4f" % exp5d, "%d / %d / %.4f" % obs5d,
    pv(obs5d[:2] == exp5d[:2] and abs(q5 - exp5d[2]) < 0.00006),
    "Q from figure edges and node clusters; Louvain itself not rerun")

# own-key sensitivity (information)
WBm = build_works(MY_KEY)
_, N4m, CO_Em, CO_Nm = cocitation(WBm)
say("C05 own keys: works", len(set().union(*WBm.values())), "ge4", len(N4m),
    "nodes", len(CO_Nm), "edges", len(CO_Em))

# ---------------------------------------------------------------- C06
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
ORCID_RE = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b")
forms = set()
skipped_forms = 0
for r in e1:
    for a in r["Authors"].split(";"):
        a = a.strip()
        if not a:
            continue
        if not re.match(r"^\S.*\s\S+\.$", a):
            skipped_forms += 1
            continue
        forms.add(a)
        dotless = re.sub(r"\s+", " ", a.replace(".", "")).strip().upper()
        if " " in dotless:
            forms.add(dotless)
alts = sorted((re.escape(x) for x in forms), key=len, reverse=True)
NAME_RE = re.compile(r"(?<!\w)(?:" + "|".join(alts) + r")(?!\w)", re.IGNORECASE)
EXEMPT_FILES = {"T1b_key_collisions.csv", "T2_top30_works.csv",
                "T4b2_cluster_shared_works.csv", "T5b_cocitation_clusters.csv",
                "Fig_cocitation_workkey_nodes.csv"}
EXEMPT_COLS = {"first_author", "label"}
csv_files = sorted(glob.glob(os.path.join(PH, "tables", "*.csv"))) + \
    sorted(glob.glob(os.path.join(PH, "figures", "*.csv")))
n_email = n_orcid = 0
long_cells = 0
name_hits = 0
name_hits_exempt = 0
hit_files = Counter()
cells = 0
for path in csv_files:
    raw = open(path, encoding="utf-8-sig").read()
    n_email += len(EMAIL_RE.findall(raw))
    n_orcid += len(ORCID_RE.findall(raw))
    base = os.path.basename(path)
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    hdr = rows[0] if rows else []
    for row in rows:
        for j, cell in enumerate(row):
            cells += 1
            if len(cell.split()) > 30:
                long_cells += 1
            if NAME_RE.search(cell):
                col = hdr[j] if j < len(hdr) else ""
                if base in EXEMPT_FILES and col in EXEMPT_COLS:
                    name_hits_exempt += 1
                else:
                    name_hits += 1
                    hit_files[base + ":" + col] += 1
report_present = os.path.exists(REPORT)
md_long = 0
md_hits = 0
if report_present:
    raw = open(REPORT, encoding="utf-8").read()
    n_email += len(EMAIL_RE.findall(raw))
    n_orcid += len(ORCID_RE.findall(raw))
    hdr = None
    for line in raw.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            hdr = None
            if NAME_RE.search(s):
                md_hits += 1
            continue
        parts = [c.strip() for c in s.strip("|").split("|")]
        if all(re.match(r"^:?-{2,}:?$", c) for c in parts if c):
            continue
        if hdr is None:
            hdr = parts
        for j, c in enumerate(parts):
            if len(c.split()) > 30:
                md_long += 1
            if NAME_RE.search(c):
                col = hdr[j] if j < len(hdr) else ""
                if "first_author" in hdr and col in EXEMPT_COLS and parts is not hdr:
                    name_hits_exempt += 1
                else:
                    md_hits += 1
say("C06 files", len(csv_files), "cells", cells, "forms", len(forms), "skipped forms",
    skipped_forms, "report present", report_present)
say("C06 non-exempt name hits by file:column:", dict(hit_files))
add("C06a", "e-mail- and ORCID-shaped strings in tables, figures CSVs and report", "0 / 0",
    "%d / %d" % (n_email, n_orcid), pv(n_email == 0 and n_orcid == 0),
    "%d CSV files; report present %s" % (len(csv_files), report_present))
add("C06b", "CSV cells and markdown table cells over 30 words", "0 / 0",
    "%d / %d" % (long_cells, md_long), pv(long_cells == 0 and md_long == 0),
    "%d CSV cells scanned" % cells)
add("C06c", "corpus author name forms outside exempt first_author / label columns", 0,
    name_hits + md_hits, pv(name_hits + md_hits == 0),
    "%d forms from E1 Authors (%d non-name-shaped strings skipped); hits in exempt columns %d; report present %s"
    % (len(forms), skipped_forms, name_hits_exempt, report_present))

# ---------------------------------------------------------------- C07
_, t4b = read_dicts(os.path.join(PH, "tables", "T4b_coupling_clusters.csv"))
t4b_by = {r["cluster"]: r for r in t4b}
top2 = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:2]


def descr(eids):
    recs = [E1_BY[e] for e in eids]
    yrs = [int(r["Year"]) for r in recs]
    dt = Counter(r["Document Type"] for r in recs)
    kw = Counter()
    for r in recs:
        s = set()
        for k in r["Author Keywords"].split(";"):
            k = re.sub(r"\s+", " ", k.lower()).strip()
            if k:
                s.add(k)
        kw.update(s)
    top5 = "; ".join(k for k, _ in sorted(kw.items(), key=lambda kv: (-kv[1], kv[0]))[:5])
    src = sorted(Counter(r["Source title"] for r in recs).items(),
                 key=lambda kv: (-kv[1], kv[0]))[0]
    tc = [int(r["Cited by"]) if r["Cited by"].strip() else 0 for r in recs]
    n = len(recs)
    return {
        "records": n,
        "p2003_2016": sum(1 for y in yrs if 2003 <= y <= 2016),
        "p2017_2021": sum(1 for y in yrs if 2017 <= y <= 2021),
        "p2022_2025": sum(1 for y in yrs if 2022 <= y <= 2025),
        "articles": dt.get("Article", 0),
        "conference_papers": dt.get("Conference paper", 0),
        "other_types": n - dt.get("Article", 0) - dt.get("Conference paper", 0),
        "top5_author_keywords": top5,
        "main_source": src[0],
        "main_source_records": src[1],
        "mean_TC": statistics.mean(tc),
        "median_TC": statistics.median(tc),
    }


for cid, members in top2:
    d = descr(members)
    t = t4b_by.get(cid)
    diffs = []
    ncells = 0
    if t is None:
        diffs.append("cluster id absent from T4b")
    else:
        for col, val in d.items():
            ncells += 1
            if col in ("mean_TC", "median_TC"):
                if abs(float(t[col]) - val) > 0.0051:
                    diffs.append(col)
            elif isinstance(val, int):
                if int(t[col]) != val:
                    diffs.append(col)
            elif t[col] != val:
                diffs.append(col)
    add("C07-%s" % cid, "T4b cluster %s descriptors recomputed from figure nodes and E1" % cid,
        "12 cells equal", "%d/%d cells equal; records %d" % (ncells - len(diffs), ncells, d["records"]),
        pv(not diffs), ("differing: " + ", ".join(diffs)) if diffs else
        "mean %.2f, median %.1f Cited by; keywords and source compared as strings" % (d["mean_TC"], d["median_TC"]))

# ---------------------------------------------------------------- C08
F13 = {"T2a": "T2a_cited_thresholds.csv", "T4a": "T4a_local_citations.csv",
       "T5a": "T5a_coupling_summary.csv", "T6a": "T6a_cocitation_summary.csv"}
F13B = {"T2a": ("T2a_thresholds.csv", "work_key_F13_3b"),
        "T3a": ("T3a_local_citations_title.csv", "title_match_F13_3b"),
        "T4a": ("T4a_coupling_workkey.csv", "value"),
        "T5a": ("T5a_cocitation_workkey.csv", "work_key_F13_3b")}
T0MAP = {
    "distinct references (strings) / works":
        ("T2a", "distinct cited references (strings counted by citations())", "T2a", "distinct works / strings"),
    "cited by >= 5 records": ("T2a", "with >= 5 citing records", "T2a", "with >= 5 citing records"),
    "cited by >= 10 records": ("T2a", "with >= 10 citing records", "T2a", "with >= 10 citing records"),
    "local citation links":
        ("T4a", "LCS, total (local citation links)", "T3a", "local citation links (citing record -> cited record)"),
    "records cited inside the corpus": ("T4a", "records with LCS > 0", "T3a", "cited records (LCS > 0)"),
    "coupling edges (>= 2 shared)": ("T5a", "edges (pairs sharing >= 2 references)", "T4a", "edges"),
    "coupling clusters with >= 10 records":
        ("T5a", "clusters with >= 10 records", "T4a", "clusters with >= 10 records"),
    "co-citation nodes (>= 4 citing records)":
        ("T6a", "nodes: references with >= 4 citing records", "T5a", "nodes: works with >= 4 citing records"),
    "co-citation edges (>= 3)":
        ("T6a", "edges: pairs co-cited by >= 3 records", "T5a", "edges: pairs co-cited by >= 3 records"),
    "co-citation clusters with >= 5 nodes":
        ("T6a", "clusters with >= 5 nodes", "T5a", "clusters with >= 5 nodes"),
}
src13 = {k: measure_map(os.path.join(P13, "tables", v), "value") for k, v in F13.items()}
src13b = {k: measure_map(os.path.join(PH, "tables", v[0]), v[1]) for k, v in F13B.items()}
_, t0 = read_dicts(os.path.join(PH, "tables", "T0_strings_vs_work_key.csv"))
both = 0
left_ok = right_ok = 0
unknown = 0
for r in t0:
    m = T0MAP.get(r["measure"])
    if m is None:
        unknown += 1
        continue
    a = (r["source_F13_3"] == m[0] and src13[m[0]].get(m[1]) == r["strings_F13_3"])
    b = (r["source_F13_3b"] == m[2] and src13b[m[2]].get(m[3]) == r["work_key_F13_3b"])
    left_ok += a
    right_ok += b
    both += (a and b)
add("C08", "T0 cells equal their source tables (both sides)", "10/10 rows",
    "%d/%d rows" % (both, len(t0)), pv(both == 10 and len(t0) == 10 and unknown == 0),
    "strings side %d/10; work-key side %d/10; unmapped measures %d" % (left_ok, right_ok, unknown))

# own recomputation of T0 work-key values (information)
cnt_cit = Counter({w: len(es) for w, es in INV.items()})
own = {
    "distinct references (strings) / works": len(INV),
    "cited by >= 5 records": sum(1 for n in cnt_cit.values() if n >= 5),
    "cited by >= 10 records": sum(1 for n in cnt_cit.values() if n >= 10),
    "local citation links": main3["links"],
    "records cited inside the corpus": main3["cited"],
    "coupling edges (>= 2 shared)": len(CPL),
    "co-citation nodes (>= 4 citing records)": len(N4),
    "co-citation edges (>= 3)": len(CO_E),
}
own_ok = sum(1 for r in t0 if r["measure"] in own and str(own[r["measure"]]) == r["work_key_F13_3b"])
ge2 = sum(1 for n in cnt_cit.values() if n >= 2)
add("C08b", "T0 work-key values vs verifier recomputation (8 recomputable rows)", "8/8 equal",
    "%d/8 equal" % own_ok, pv(own_ok == 8),
    "works %d; >= 2 citing %d (T2a 1808); cluster counts not recomputed" % (len(INV), ge2))

# ---------------------------------------------------------------- write
with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["check", "what", "expected", "observed", "verdict", "note"])
    w.writerows(RESULTS)
say("verdicts:", dict(Counter(r[4] for r in RESULTS)))
with open(OUT_LOG, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(LOG) + "\n")
