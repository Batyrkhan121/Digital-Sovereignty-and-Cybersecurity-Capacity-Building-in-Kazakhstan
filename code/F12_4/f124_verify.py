import sys
sys.dont_write_bytecode = True
# Independent verifier of phase F12.4 (written without reading f124_*.py).
# Prints only counts, ids, column names and PASS/FAIL (R13).
import csv
import json
import os
import re
from collections import Counter

csv.field_size_limit(2 ** 31 - 1)

ROOT = os.environ.get("PROJECT_ROOT", ".")
PH = ROOT + "/outputs/dprg_revision_2026/phase_F12_4"
TAB = PH + "/tables"
FIG = PH + "/figures/Fig_coverage_union_by_year.csv"
NUM = PH + "/F12_4_numbers.json"
OUT = PH + "/phase_F12_4_independent_verification.csv"
HARM = ROOT + "/outputs/dprg_revision_2026/refresh_2026_09/field_harmonised_H4Q_title_only_cryptography_corrected"
P_S = HARM + "/scopus/scopus_raw_H4Q_title_only_cryptography_corrected_2026_09_through_2025.csv"
P_O = HARM + "/openalex/openalex_raw_H4Q_title_only_cryptography_corrected_2026_09_through_2025.csv"
P_I1 = ROOT + "/outputs/dprg_revision_2026/phase_E2/corpora_rule_e/E2_L1_scopus_september_study_2003_2025_rule_e.csv"
P_I3 = ROOT + "/outputs/dprg_revision_2026/phase_E2/corpora_rule_e/E2_L1_scopus_june_dedup_rule_e.csv"
P_I4 = ROOT + "/openalex_cybersec_kz_raw.csv"

rows_out = []


def rec(cid, what, exp, got, ok, note=""):
    v = "PASS" if ok else "FAIL"
    rows_out.append([cid, what, str(exp), str(got), v, note])
    print(cid, v, "|", what, "| expected", exp, "| recomputed", got, ("| " + note) if note else "")


def read_csv(p):
    with open(p, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        rows = list(r)
        return r.fieldnames, rows


PREF = ["https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:"]


def ndoi(x):
    d = (x or "").strip().lower()
    for p in PREF:
        if d.startswith(p):
            d = d[len(p):]
            break
    return d


def ntitle(x):
    t = (x or "").lower()
    t = re.sub(r"[^a-z0-9]", " ", t)
    return " ".join(t.split())


def ntitle_u(x):
    t = (x or "").lower()
    t = "".join(c if c.isalnum() else " " for c in t)
    return " ".join(t.split())


def nloose(x):
    t = (x or "").casefold()
    t = "".join(c if c.isalnum() else " " for c in t)
    return " ".join(t.split())


def year(x):
    x = (x or "").strip()
    if not x:
        return None
    try:
        return int(float(x))
    except ValueError:
        return None


def prep(rows, idc, tc, dc):
    L = [(r[idc], ndoi(r.get(dc)), ntitle(r.get(tc)), r) for r in rows]
    L.sort(key=lambda z: z[0])
    return L


def match(A, B):
    """A, B: lists of (id, doi, title, row) sorted by id. Returns list of (ia, ib, method)."""
    mA = [False] * len(A)
    mB = [False] * len(B)
    pairs = []
    for key_pos, meth in ((1, "doi"), (2, "title")):
        idx = {}
        for j, b in enumerate(B):
            k = b[key_pos]
            if k and not mB[j]:
                idx.setdefault(k, []).append(j)
        for i, a in enumerate(A):
            if mA[i]:
                continue
            k = a[key_pos]
            if not k:
                continue
            for j in idx.get(k, []):
                if not mB[j]:
                    mA[i] = True
                    mB[j] = True
                    pairs.append((i, j, meth))
                    break
    return pairs, mA, mB


def match_sym(A, B):
    p1, mA, mB = match(A, B)
    p2, _, _ = match(B, A)
    s1 = set((A[i][0], B[j][0]) for i, j, _ in p1)
    s2 = set((A[j][0], B[i][0]) for i, j, _ in p2)
    return p1, mA, mB, s1 == s2, len(s1), len(s2)


def table(path):
    f, rows = read_csv(path)
    return f, rows


def kv(path):
    _, rows = read_csv(path)
    return {r[list(r.keys())[0]]: r[list(r.keys())[1]] for r in rows}


# ---------------- load inputs ----------------
fS, S_rows = read_csv(P_S)
fO, O_rows = read_csv(P_O)
fI1, I1_rows = read_csv(P_I1)
fI3, I3_rows = read_csv(P_I3)
fI4, I4_rows = read_csv(P_I4)
print("loaded S", len(S_rows), "O", len(O_rows), "I1", len(I1_rows), "I3", len(I3_rows), "I4", len(I4_rows))
for name, f, need in (("S", fS, ["scopus_id", "title", "publication_year", "doi", "source_title", "doc_type"]),
                      ("O", fO, ["openalex_id", "title", "year", "doi", "type", "journal"]),
                      ("I1", fI1, ["source_title"]),
                      ("I3", fI3, ["scopus_id", "title", "doi", "publication_year"]),
                      ("I4", fI4, ["openalex_id", "title", "doi", "year"])):
    miss = [c for c in need if c not in f]
    print("columns present", name, "missing:", miss)

S = prep(S_rows, "scopus_id", "title", "doi")
O = prep(O_rows, "openalex_id", "title", "doi")
I3 = prep(I3_rows, "scopus_id", "title", "doi")
I4 = prep(I4_rows, "openalex_id", "title", "doi")
for nm, L in (("S", S), ("O", O), ("I3", I3), ("I4", I4)):
    print("unique ids", nm, len(set(z[0] for z in L)), "of", len(L))

T1 = kv(TAB + "/T1_summary.csv")
NJ = json.load(open(NUM, encoding="utf-8"))

# ---------------- C01 ----------------
sd = sum(1 for z in S if z[1])
od = sum(1 for z in O if z[1])
exp = (int(T1["|S| Scopus H4Q title-only, 2003-2025"]), int(T1["|O| OpenAlex H4Q title-only, 2003-2025"]),
       int(T1["S with DOI"]), int(T1["O with DOI"]))
got = (len(S), len(O), sd, od)
rec("C01", "|S|, |O|, S with DOI, O with DOI", exp, got, exp == got and exp[:2] == (203, 229))

# ---------------- C02 ----------------
pSO, mS, mO, symSO, n1, n2 = match_sym(S, O)
ndoi_p = sum(1 for p in pSO if p[2] == "doi")
nti_p = sum(1 for p in pSO if p[2] == "title")
inter = len(pSO)
onlyS = len(S) - inter
onlyO = len(O) - inter
union = inter + onlyS + onlyO
exp = tuple(int(T1[k]) for k in ("pairs by DOI", "pairs by normalised title", "intersection", "only Scopus", "only OpenAlex", "union"))
got = (ndoi_p, nti_p, inter, onlyS, onlyO, union)
rec("C02a", "pairs by DOI, by title, intersection, only Scopus, only OpenAlex, union", exp, got, exp == got)
rec("C02b", "S<->O and O<->S give the same pair set", "True (123/123)", "%s (%d/%d)" % (symSO, n1, n2), symSO and n1 == 123)
ydiff = sum(1 for i, j, _ in pSO if year(S[i][3]["publication_year"]) != year(O[j][3]["year"]))
shares = ("%.1f" % (100.0 * (inter + onlyS) / union), "%.1f" % (100.0 * (inter + onlyO) / union),
          "%.1f" % (100.0 * inter / union), "%.2f" % (len(O) / len(S)))
exp = (T1["share of the union in Scopus (%)"], T1["share of the union in OpenAlex (%)"],
       T1["share of the union in both (%)"], T1["ratio |O| / |S| (harmonised)"], int(T1["pairs whose two years differ"]),
       int(T1["only-Scopus records without DOI"]), int(T1["only-OpenAlex records without DOI"]))
oS = [S[i] for i in range(len(S)) if not mS[i]]
oO = [O[j] for j in range(len(O)) if not mO[j]]
got = shares + (ydiff, sum(1 for z in oS if not z[1]), sum(1 for z in oO if not z[1]))
rec("C02c", "shares S/O/both, ratio O/S, pairs with differing years, only-S without DOI, only-O without DOI", exp, got, exp == got)


# ---------------- C02d: T1c_pairs.csv ----------------
P_T1C = TAB + "/T1c_pairs.csv"
if os.path.exists(P_T1C):
    fT, T1c = read_csv(P_T1C)
    print("T1c columns:", fT, "rows:", len(T1c), "matched_by values:", dict(Counter(r.get("matched_by", "") for r in T1c)))

    def meth(x):
        x = (x or "").strip().lower()
        return "doi" if "doi" in x else ("title" if "title" in x else x)

    mine_p = set((S[i][0], O[j][0], m) for i, j, m in pSO)
    tab_p = set((r["scopus_id"].strip(), r["openalex_id"].strip(), meth(r["matched_by"])) for r in T1c)
    mine_y = {(S[i][0], O[j][0]): (year(S[i][3]["publication_year"]), year(O[j][3]["year"])) for i, j, _ in pSO}
    ybad = sum(1 for r in T1c if mine_y.get((r["scopus_id"].strip(), r["openalex_id"].strip())) != (year(r.get("scopus_year")), year(r.get("openalex_year"))))
    ok = tab_p == mine_p and len(T1c) == len(tab_p) == 123
    rec("C02d", "T1c_pairs.csv = my 123 pairs (scopus_id, openalex_id, matched_by)", "123 rows, identical set",
        "%d rows, %d distinct, %d only in table, %d only mine" % (len(T1c), len(tab_p), len(tab_p - mine_p), len(mine_p - tab_p)),
        ok, "year columns differing from mine: %d; doi/title in table: %d/%d" % (
            ybad, sum(1 for p in tab_p if p[2] == "doi"), sum(1 for p in tab_p if p[2] == "title")))
else:
    rec("C02d", "T1c_pairs.csv = my 123 pairs", "file present", "file absent", False)


# ---------------- top-10 helper ----------------
def top10_cmp(exp_list, mine_counter):
    """exp_list: [(name, n)] in table order; mine_counter: Counter keyed by loose name."""
    e_sorted = sorted(exp_list, key=lambda z: -z[1])
    e10 = e_sorted[:10]
    m10 = mine_counter.most_common()
    m10 = sorted(m10, key=lambda z: -z[1])[:10]
    c10 = e10[-1][1]
    e_counts = sorted([n for _, n in e10])
    m_counts = sorted([n for _, n in m10])
    e_set = set(nloose(k) for k, n in e10 if n > c10)
    m_set = set(k for k, n in m10 if n > c10)
    full_e = Counter({nloose(k): n for k, n in exp_list})
    full_m = Counter(dict(mine_counter))
    return e_counts, m_counts, e_set == m_set, len(e_set), full_e == full_m


# ---------------- C03 ----------------
_, T2t = table(TAB + "/T2_only_openalex_types.csv")
exp_types = {r["type"]: int(r["n"]) for r in T2t}
got_types = dict(Counter((z[3].get("type") or "").strip() for z in oO))
rec("C03a", "only-OpenAlex by type", sorted(exp_types.items()), sorted(got_types.items()), exp_types == got_types)

_, T2s = table(TAB + "/T2_only_openalex_sources.csv")
exp_src = [(r["source"], int(r["n"])) for r in T2s]
msrc = Counter()
for z in oO:
    j = (z[3].get("journal") or "").strip()
    msrc[nloose(j) if j else nloose("(no source)")] += 1
ec, mc, setok, nset, fullok = top10_cmp(exp_src, msrc)
rec("C03b", "only-OpenAlex top-10 sources: count multiset; untied names as set", ec, mc,
    ec == mc and setok, "untied names compared: %d, set equal %s; full list (all %d sources) equal: %s" % (nset, setok, len(exp_src), fullok))

frame = set()
for r in I1_rows:
    k = ntitle(r.get("source_title"))
    if k:
        frame.add(k)
infr = 0
fr_by_src = Counter()
for z in oO:
    k = ntitle(z[3].get("journal"))
    if k and k in frame:
        infr += 1
        fr_by_src[nloose(z[3].get("journal"))] += 1
exp_fr = NJ["T2"]["source_in_scopus_frame_records"]
tab_fr = sum(int(r["n"]) for r in T2s if r["source_in_scopus_frame"] == "1")
tab_fr_names = Counter({nloose(r["source"]): int(r["n"]) for r in T2s if r["source_in_scopus_frame"] == "1"})
rec("C03c", "only-OpenAlex records with source_in_scopus_frame = 1 (json; table flag sum)", "%d; %d" % (exp_fr, tab_fr), infr,
    exp_fr == infr == tab_fr and tab_fr_names == fr_by_src, "flagged sources equal to mine: %s (%d sources)" % (tab_fr_names == fr_by_src, len(fr_by_src)))

# ---------------- C04 ----------------
_, T3d = table(TAB + "/T3_only_scopus_doc_types.csv")
exp_dt = {r["doc_type"]: int(r["n"]) for r in T3d}
got_dt = dict(Counter((z[3].get("doc_type") or "").strip() for z in oS))
rec("C04a", "only-Scopus by doc_type", sorted(exp_dt.items()), sorted(got_dt.items()), exp_dt == got_dt)

_, T3s = table(TAB + "/T3_only_scopus_sources.csv")
exp_s3 = [(r["source_title"], int(r["n"])) for r in T3s]
ms3 = Counter()
for z in oS:
    j = (z[3].get("source_title") or "").strip()
    ms3[nloose(j) if j else nloose("(no source)")] += 1
ec, mc, setok, nset, fullok = top10_cmp(exp_s3, ms3)
rec("C04b", "only-Scopus top-10 sources: count multiset; untied names as set", ec, mc,
    ec == mc and setok, "untied names compared: %d, set equal %s; full list (all %d sources) equal: %s" % (nset, setok, len(exp_s3), fullok))

T3j = kv(TAB + "/T3_only_scopus_in_openalex_june.csv")
i4dois = set(z[1] for z in I4 if z[1])
i4titles = set(z[2] for z in I4 if z[2])
oS_d = [z for z in oS if z[1]]
oS_nd = [z for z in oS if not z[1]]
got = (len(oS_d), sum(1 for z in oS_d if z[1] in i4dois), len(oS_nd), sum(1 for z in oS_nd if z[2] in i4titles))
exp = tuple(int(v) for v in T3j.values())
rec("C04c", "only-Scopus with DOI, in_openalex_june, without DOI, title_in_openalex_june", exp, got, exp == got,
    "title test uses the [a-z0-9] title rule against all non-empty I4 titles")

# ---------------- C05 ----------------
T4 = kv(TAB + "/T4_bridge_to_june.csv")
p34, m3, m4, sym34, a1, a2 = match_sym(I3, I4)
g = (len(I3), len(I4), sum(1 for p in p34 if p[2] == "doi"), sum(1 for p in p34 if p[2] == "title"),
     len(p34), len(I3) - len(p34), len(I4) - len(p34))
e = tuple(int(T4[k]) for k in ("June: I3 Scopus structural layer", "June: I4 OpenAlex export", "June: pairs (same rule) - by DOI",
                               "June: pairs - by title", "June: intersection", "June: only Scopus", "June: only OpenAlex"))
rec("C05a", "I3<->I4 same rule: |I3|, |I4|, pairs DOI, pairs title, intersection, only Scopus, only OpenAlex", e, g,
    e == g and e[4:] == (331, 600, 1505))
rec("C05b", "I3<->I4 symmetric pair set", "True (331/331)", "%s (%d/%d)" % (sym34, a1, a2), sym34 and a1 == 331)

# F12.1 rule (Unicode titles)
i3_dois = set(ndoi(r.get("doi")) for r in I3_rows) - {""}
i3_titles = set(ntitle_u(r.get("title")) for r in I3_rows) - {""}
i4_dois_all = set(ndoi(r.get("doi")) for r in I4_rows) - {""}
i4_nodoi_titles = set(ntitle_u(r.get("title")) for r in I4_rows if not ndoi(r.get("doi"))) - {""}
m_i4 = 0
for r in I4_rows:
    d = ndoi(r.get("doi"))
    if d:
        m_i4 += d in i3_dois
    else:
        t = ntitle_u(r.get("title"))
        m_i4 += bool(t) and t in i3_titles
m_i3 = 0
for r in I3_rows:
    d = ndoi(r.get("doi"))
    t = ntitle_u(r.get("title"))
    m_i3 += (bool(d) and d in i4_dois_all) or (bool(t) and t in i4_nodoi_titles)
g = (m_i4, len(I4_rows) - m_i4, len(I3_rows) - m_i3)
e = (int(T4["June under F12.1's rule (reproduced): intersection"]), int(T4["June under F12.1's rule: only OpenAlex"]),
     int(T4["June under F12.1's rule: only Scopus (seen from I3)"]))
rec("C05c", "F12.1 rule reproduced: intersection (I4 side), only OpenAlex, only Scopus (I3 side)", e, g, e == g == (324, 1512, 608),
    "I3 records with a counterpart under this rule: %d" % m_i3)

j_oO = [I4[j] for j in range(len(I4)) if not m4[j]]
j_oS = [I3[i] for i in range(len(I3)) if not m3[i]]
pb1, _, _, sb1, b1a, b1b = match_sym(j_oO, O)
pb2, _, _, sb2, b2a, b2b = match_sym(j_oS, S)
pc1, _, _, sc1, _, _ = match_sym(O, I4)
pc2, _, _, sc2, _, _ = match_sym(S, I3)
e = (int(T4["June only-OpenAlex records found in O (harmonised OpenAlex)"]), int(T4["June only-Scopus records found in S (harmonised Scopus)"]),
     int(T4["context: O records found in I4"]), int(T4["context: S records found in I3"]))
g = (len(pb1), len(pb2), len(pc1), len(pc2))
rec("C05d", "bridge: June only-OA in O, June only-Scopus in S; context O in I4, S in I3", e, g, e == g and e[:2] == (85, 98),
    "all four symmetric: %s" % (sb1 and sb2 and sc1 and sc2))

# ---------------- C06 ----------------
yb = {}
for i, j, _ in pSO:
    y = year(S[i][3]["publication_year"])
    yb.setdefault(y, Counter())["intersection"] += 1
for z in oS:
    yb.setdefault(year(z[3]["publication_year"]), Counter())["only_Scopus"] += 1
for z in oO:
    yb.setdefault(year(z[3]["year"]), Counter())["only_OpenAlex"] += 1
out_of_range = [y for y in yb if y is None or y < 2003 or y > 2025]
print("year buckets outside 2003-2025:", out_of_range)


def bucket_row(ys):
    c = Counter()
    for y in ys:
        c.update(yb.get(y, Counter()))
    it, s_, o_ = c["intersection"], c["only_Scopus"], c["only_OpenAlex"]
    u = it + s_ + o_
    pc = lambda a: ("%.1f" % (100.0 * a / u)) if u else ""
    return {"S": it + s_, "O": it + o_, "intersection": it, "only_Scopus": s_, "only_OpenAlex": o_, "union": u,
            "pct_union_Scopus": pc(it + s_), "pct_union_OpenAlex": pc(it + o_), "pct_union_both": pc(it)}


COLS = ["S", "O", "intersection", "only_Scopus", "only_OpenAlex", "union", "pct_union_Scopus", "pct_union_OpenAlex", "pct_union_both"]


def cmp_table(path, buckets):
    _, rows = table(path)
    bad = []
    seen = []
    for r in rows:
        b = r["bucket"]
        seen.append(b)
        if b not in buckets:
            bad.append(b + ":unknown")
            continue
        mine = bucket_row(buckets[b])
        for c in COLS:
            ev = r[c]
            mv = mine[c]
            if c.startswith("pct"):
                okc = (ev == mv) or (ev and mv and abs(float(ev) - float(mv)) < 0.051)
            else:
                okc = int(ev) == mv
            if not okc:
                bad.append("%s.%s %s/%s" % (b, c, ev, mv))
    missing = [b for b in buckets if b not in seen]
    return rows, bad, missing


periods = {"2003-2016": range(2003, 2017), "2017-2021": range(2017, 2022), "2022-2025": range(2022, 2026)}
prow, pbad, pmiss = cmp_table(TAB + "/T1b_periods.csv", periods)
rec("C06a", "T1b_periods: all 9 columns for 3 periods", "3 rows match", "%d mismatches, %d missing" % (len(pbad), len(pmiss)),
    not pbad and not pmiss, "; ".join(pbad[:5]))
years = {str(y): [y] for y in range(2003, 2026)}
yrow, ybad, ymiss = cmp_table(TAB + "/T1b_years.csv", years)
rec("C06b", "T1b_years: all 9 columns for 23 years", "23 rows match", "%d mismatches, %d missing" % (len(ybad), len(ymiss)),
    not ybad and not ymiss, "; ".join(ybad[:5]))
sums = tuple(sum(int(r[c]) for r in yrow) for c in ("intersection", "only_Scopus", "only_OpenAlex", "union"))
psums = tuple(sum(int(r[c]) for r in prow) for c in ("intersection", "only_Scopus", "only_OpenAlex", "union"))
e = tuple(int(T1[k]) for k in ("intersection", "only Scopus", "only OpenAlex", "union"))
rec("C06c", "sums over years (and over periods) equal T1 intersection, only S, only O, union", e, "%s; %s" % (sums, psums),
    sums == e and psums == e and not out_of_range)

# ---------------- C07 ----------------
ff, frows = table(FIG)
fbad = []
ymap = {r["bucket"]: r for r in yrow}
fy = [r["year"] for r in frows]
for r in frows:
    t = ymap.get(r["year"])
    mine = bucket_row([int(r["year"])])
    if t is None:
        fbad.append(r["year"] + ":not in T1b")
        continue
    for fc, tc in (("only_Scopus", "only_Scopus"), ("both", "intersection"), ("only_OpenAlex", "only_OpenAlex"), ("union", "union")):
        if not (int(r[fc]) == int(t[tc]) == mine[tc]):
            fbad.append("%s.%s" % (r["year"], fc))
rec("C07", "figure CSV equals T1b_years (and my recompute), 2003-2025", "23 rows equal",
    "%d rows, %d mismatches" % (len(frows), len(fbad)), not fbad and fy == [str(y) for y in range(2003, 2026)], "; ".join(fbad[:5]))

# ---------------- C08 ----------------
EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
ORCID = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b")
BANNED = {"authors", "author_ids", "first_author"}
tab_files = sorted(os.path.join(TAB, f) for f in os.listdir(TAB) if os.path.isfile(os.path.join(TAB, f)))
csvs = [p for p in tab_files if p.endswith(".csv")] + [FIG]
mds = [p for p in tab_files if p.endswith(".md")]
others = [p for p in tab_files if not (p.endswith(".csv") or p.endswith(".md"))]
banned_hits = []
long_cells = []
title_long = []
n_cells = 0
for p in csvs:
    with open(p, "r", encoding="utf-8-sig", newline="") as f:
        rr = list(csv.reader(f))
    hdr = [h.strip().lower() for h in rr[0]] if rr else []
    for h in hdr:
        if h in BANNED:
            banned_hits.append(os.path.basename(p) + ":" + h)
    for row in rr:
        for k, cell in enumerate(row):
            n_cells += 1
            w = len(cell.split())
            if w > 30:
                long_cells.append(os.path.basename(p))
            if k < len(hdr) and "title" in hdr[k] and hdr[k] not in ("source_title",) and w > 30:
                title_long.append(os.path.basename(p))
long_md = []
n_md_lines = 0
for p in mds:
    with open(p, "r", encoding="utf-8-sig") as f:
        for line in f:
            n_md_lines += 1
            s = line.strip()
            if s.startswith("|"):
                cells = s.strip("|").split("|")
                if any(len(c.split()) > 30 for c in cells):
                    long_md.append(os.path.basename(p))
            elif len(s.split()) > 30:
                long_md.append(os.path.basename(p))
em = 0
oc = 0
oc_in_doi = 0
oc_where = []
oc_suffix_start_1994 = []
for p in tab_files + [FIG, NUM]:
    with open(p, "r", encoding="utf-8-sig", errors="replace") as f:
        txt = f.read()
    em += len(EMAIL.findall(txt))
    for mo in ORCID.finditer(txt):
        oc += 1
        # locate the enclosing token (whitespace / comma / pipe / quote delimited); never print the value
        a = mo.start()
        b = mo.end()
        while a > 0 and txt[a - 1] not in " ,|\"\n\t":
            a -= 1
        while b < len(txt) and txt[b] not in " ,|\"\n\t":
            b += 1
        tok = txt[a:b].lower()
        rel = mo.start() - a
        k10 = tok.find("10.")
        is_doi = 0 <= k10 < rel and "/" in tok[k10:rel]
        oc_in_doi += is_doi
        oc_suffix_start_1994.append(is_doi and txt[mo.start() - 1] == "/" and mo.group(0)[:4] == "1994")
        line_no = txt.count("\n", 0, mo.start()) + 1
        oc_where.append("%s line %d%s" % (os.path.basename(p), line_no, " inside a DOI suffix" if is_doi else " NOT in a DOI"))
print("ORCID-shape locations:", oc_where)
# which CSV column holds each hit (column name only)
for p in tab_files:
    if not p.endswith(".csv"):
        continue
    with open(p, "r", encoding="utf-8-sig", newline="") as f:
        rr = list(csv.reader(f))
    for row in rr[1:]:
        for k, cell in enumerate(row):
            if ORCID.search(cell):
                print("ORCID-shape column:", os.path.basename(p), rr[0][k], "| cell starts with 10. or a doi.org URL:",
                      cell.strip().lower().startswith(("10.", "https://doi.org/10.", "http://doi.org/10.")))
rec("C08a", "no authors/author_ids/first_author column in tables/*.csv or figure CSV", 0, len(banned_hits), not banned_hits,
    "%d CSV files checked" % len(csvs))
all_1994 = bool(oc_suffix_start_1994) and all(oc_suffix_start_1994)
print("ORCID-shape hits each at the start of a DOI suffix with first block 1994:", oc_suffix_start_1994)
rec("C08b", "e-mail and ORCID shapes in tables/*, figure CSV, numbers json", "0; 0", "%d; %d" % (em, oc), em == 0 and oc == 0,
    "%d files scanned; ORCID-shape hits inside a DOI suffix: %d of %d (%s)%s" % (
        len(tab_files) + 2, oc_in_doi, oc, "; ".join(oc_where),
        "; every hit is a DOI suffix starting with an ISSN, first block 1994 - not an ORCID iD" if all_1994 else ""))
# C08b3: ORCID iD ranges only (first block 0000 or 0009), same files as C08b
ORCID_RANGE = re.compile(r"\b(?:0000|0009)-\d{4}-\d{4}-\d{3}[\dX]\b")
oc3 = 0
for p in tab_files + [FIG, NUM]:
    with open(p, "r", encoding="utf-8-sig", errors="replace") as f:
        oc3 += len(ORCID_RANGE.findall(f.read()))
rec("C08b3", "ORCID-shaped strings whose first block is 0000 or 0009 (the ORCID iD ranges), same files as C08b", 0, oc3, oc3 == 0,
    "%d files scanned; T1c_pairs.csv present: %s" % (len(tab_files) + 2, os.path.exists(os.path.join(TAB, "T1c_pairs.csv"))))
# Same scan with the ORCID shape bounded so it cannot sit inside a DOI suffix (not preceded by '/', '-' or a digit).
ORCID_STRICT = re.compile(r"(?<![/\-\d.])\d{4}-\d{4}-\d{4}-\d{3}[\dX](?![\d\-])")
oc2 = 0
for p in tab_files + [FIG, NUM]:
    with open(p, "r", encoding="utf-8-sig", errors="replace") as f:
        oc2 += len(ORCID_STRICT.findall(f.read()))
rec("C08b2", "ORCID shapes outside DOI suffixes (bounded pattern)", 0, oc2, oc2 == 0 and oc == oc_in_doi,
    "every broad-pattern hit lies inside a DOI suffix: %s" % (oc == oc_in_doi))
rec("C08c", "CSV cells over 30 words; title cells over 30 words", "0; 0", "%d; %d" % (len(long_cells), len(title_long)),
    not long_cells and not title_long, "%d cells checked; files with long cells: %s" % (n_cells, sorted(set(long_cells))))
rec("C08d", "markdown lines over 30 words (table rows per cell)", 0, len(long_md), not long_md,
    "%d md files, %d lines; other non-csv/md files in tables: %d" % (len(mds), n_md_lines, len(others)))

with open(OUT, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["check_id", "what", "expected_from_tables", "recomputed", "verdict", "note"])
    w.writerows(rows_out)
print("PASS", sum(1 for r in rows_out if r[4] == "PASS"), "FAIL", sum(1 for r in rows_out if r[4] == "FAIL"))
