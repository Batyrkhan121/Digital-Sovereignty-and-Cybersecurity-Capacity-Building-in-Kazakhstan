import sys
sys.dont_write_bytecode = True
import csv
import json
import os
import re
from collections import Counter

csv.field_size_limit(2 ** 31 - 1)

ROOT = os.environ.get("PROJECT_ROOT", ".")
PH = ROOT + "/outputs/dprg_revision_2026/phase_F13_1"
EX = ROOT + "/outputs/dprg_revision_2026/author_exports_2026_10"
E1P = EX + "/scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
E2P = EX + "/wos_full_TS_KZ_2003_2025_2026-10-13.txt"
I1P = ROOT + "/outputs/dprg_revision_2026/phase_E2/corpora_rule_e/E2_L1_scopus_september_study_2003_2025_rule_e.csv"
TAB = PH + "/tables"
NUMS = PH + "/F13_1_numbers.json"
MERGED = PH + "/data/merged_corpus_2026-10-13.csv"
OUT = PH + "/phase_F13_1_independent_verification.csv"

CONTACT_E1 = {"Correspondence Address"}
CONTACT_E2 = {"EM", "OI", "RI", "RP"}
BANNED_COLS = {"correspondence address", "em", "oi", "ri", "rp", "email", "orcid", "researcher_id"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
ORCID_RE = re.compile(r"(?<![0-9])(?:0000|0009)-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9Xx](?![0-9])")

results = []


def add(cid, what, expected, recomputed, ok, note=""):
    results.append({"check_id": cid, "what": what, "expected_from_tables": str(expected),
                    "recomputed": str(recomputed), "verdict": "PASS" if ok else "FAIL", "note": note})
    print(cid, "PASS" if ok else "FAIL", "|", what, "| expected:", expected, "| recomputed:", recomputed,
          ("| " + note) if note else "")


def read_table(name):
    with open(TAB + "/" + name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def ne(v):
    return v is not None and str(v).strip() != ""


# ---------------- E1 ----------------
e1_counts = Counter()
e1 = []
with open(E1P, encoding="utf-8-sig", newline="") as f:
    rd = csv.DictReader(f)
    e1_cols = list(rd.fieldnames)
    for row in rd:
        for c in e1_cols:
            if ne(row.get(c)):
                e1_counts[c] += 1
        for c in CONTACT_E1:
            row.pop(c, None)  # contact field dropped right after counting
        e1.append(row)
n_e1 = len(e1)
e1_eids = [r["EID"].strip() for r in e1]

# ---------------- E2 ----------------
TAG_RE = re.compile(r"^([A-Z][A-Z0-9]) (.*)$")
e2 = []
e2_counts = Counter()
e2_tags_seen = set()


def close_record(rec):
    for t, lines in rec.items():
        if any(x.strip() for x in lines):
            e2_counts[t] += 1
    for t in CONTACT_E2:
        rec.pop(t, None)  # contact fields dropped right after counting
    e2.append(rec)


with open(E2P, encoding="utf-8-sig") as f:
    rec = None
    cur = None
    for raw in f:
        line = raw.rstrip("\r\n")
        if line == "ER" or line.startswith("ER "):
            if rec is not None:
                close_record(rec)
            rec = None
            cur = None
            continue
        if line == "EF":
            continue
        if line.startswith("   ") and cur is not None and rec is not None:
            rec[cur].append(line[3:])
            continue
        m = TAG_RE.match(line)
        if m:
            tag, val = m.group(1), m.group(2)
            if rec is None and tag in ("FN", "VR"):
                continue
            if rec is None:
                rec = {}
            rec.setdefault(tag, []).append(val)
            e2_tags_seen.add(tag)
            cur = tag
        # blank lines ignored
    if rec is not None:
        close_record(rec)

n_e2 = len(e2)


def f1(rec, tag, sep=" "):
    return sep.join(x.strip() for x in rec.get(tag, [])).strip()


e2_uts = [f1(r, "UT") for r in e2]

# ---------------- C01 ----------------
t1a = read_table("T1a_counts.csv")
t1a_e1 = [r for r in t1a if r["file"].startswith("E1 ")][0]
t1a_e2 = [r for r in t1a if r["file"].startswith("E2 ")][0]
rec01 = (n_e1, len(set(e1_eids)), n_e2, len(set(e2_uts)))
exp01 = (int(t1a_e1["records"]), int(t1a_e1["unique_ids"]), int(t1a_e2["records"]), int(t1a_e2["unique_ids"]))
add("C01", "E1 rows/unique EID; E2 records/unique UT", "841/841; 231/231 (T1a %s)" % (exp01,),
    "%d/%d; %d/%d" % rec01, rec01 == (841, 841, 231, 231) and exp01 == rec01,
    "E1 columns %d (T1a %s); E2 tags %d (T1a %s)" % (len(e1_cols), t1a_e1["columns_or_tags"],
                                                    len(e2_tags_seen), t1a_e2["columns_or_tags"]))

# ---------------- C02 ----------------
spec_e1 = {"DOI": 685, "Abstract": 841, "Author Keywords": 797, "Index Keywords": 586, "References": 837}
spec_e2 = {"CR": 231, "AB": 231, "DE": 227, "DI": 194}
got = {k: e1_counts[k] for k in spec_e1}
got2 = {k: e2_counts[k] for k in spec_e2}
add("C02a", "E1 non-empty DOI/Abstract/AuthorKW/IndexKW/References", spec_e1, got, got == spec_e1)
add("C02b", "E2 records with CR/AB/DE/DI", spec_e2, got2, got2 == spec_e2)
t1b = read_table("T1b_completeness.csv")
mism = []
for r in t1b:
    src, fld = r["source"], r["field"]
    mine = e1_counts[fld] if src == "E1" else e2_counts[fld]
    tot = n_e1 if src == "E1" else n_e2
    pct = round(100.0 * mine / tot, 1)
    if int(r["non_empty"]) != mine or abs(float(r["pct"]) - pct) > 1e-9:
        mism.append("%s/%s" % (src, fld))
t1b_e1 = {r["field"] for r in t1b if r["source"] == "E1"}
t1b_e2 = {r["field"] for r in t1b if r["source"] == "E2"}
cover = (t1b_e1 == set(e1_cols)) and (t1b_e2 == e2_tags_seen)
add("C02c", "all T1b rows (non_empty, pct) equal recomputed; T1b covers every E1 column and E2 tag",
    "%d rows" % len(t1b), "%d mismatches; coverage %s" % (len(mism), cover), not mism and cover,
    ("mismatches: " + ", ".join(mism)) if mism else "")

# ---------------- C03 ----------------
i1 = {}
with open(I1P, encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        i1["2-s2.0-" + r["scopus_id"].strip()] = (r["publication_year"].strip(), r["doc_type"].strip())
e1_by = {r["EID"].strip(): r for r in e1}
common = set(e1_by) & set(i1)
only_e1 = set(e1_by) - set(i1)
only_i1 = set(i1) - set(e1_by)
t2a = read_table("T2a_E1_vs_frame.csv")
t2a_i1 = [r for r in t2a if r["against"].startswith("I1")][0]
exp03 = (int(t2a_i1["common"]), int(t2a_i1["only_E1"]), int(t2a_i1["only_reference"]))
rec03 = (len(common), len(only_e1), len(only_i1))
add("C03a", "E1 vs I1 by EID: common/only E1/only I1", "838/3/3 (T2a %s)" % (exp03,), "%d/%d/%d" % rec03,
    rec03 == (838, 3, 3) and exp03 == rec03, "I1 rows %d" % len(i1))


def yr(v):
    v = v.strip()
    try:
        return str(int(float(v)))
    except ValueError:
        return v


ydiff = sum(1 for k in common if yr(e1_by[k]["Year"]) != yr(i1[k][0]))
dt_cs = sum(1 for k in common if e1_by[k]["Document Type"].strip() != i1[k][1])
dt_ci = sum(1 for k in common if e1_by[k]["Document Type"].strip().lower() != i1[k][1].lower())
t2a2 = {r["field"]: r for r in read_table("T2a2_field_differences.csv")}
exp_y = int(t2a2["Year"]["differing"])
exp_ci = int(t2a2["Document Type, case-insensitive"]["differing"])
exp_cs = int(t2a2["Document Type"]["differing"])
add("C03b", "common records: year diffs / doc-type diffs case-insensitive",
    "0/0 (T2a2 %d/%d)" % (exp_y, exp_ci), "%d/%d" % (ydiff, dt_ci),
    ydiff == 0 and dt_ci == 0 and exp_y == 0 and exp_ci == 0,
    "case-sensitive doc-type diffs %d (T2a2 %d)" % (dt_cs, exp_cs))

# ---------------- C04 ----------------
DOI_PREF = ["https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:"]


def ndoi(v):
    v = (v or "").strip().lower()
    for p in DOI_PREF:
        if v.startswith(p):
            v = v[len(p):]
            break
    return v


def ntitle(v):
    v = re.sub(r"[^a-z0-9]", " ", (v or "").lower())
    return " ".join(v.split())


A = sorted(((r["EID"].strip(), ndoi(r.get("DOI")), ntitle(r.get("Title"))) for r in e1), key=lambda x: x[0])
B = sorted(((f1(r, "UT"), ndoi(f1(r, "DI", "")), ntitle(f1(r, "TI"))) for r in e2), key=lambda x: x[0])


def match(X, Y):
    usedx, usedy = set(), set()
    pairs = {}
    for idx, key in ((1, "doi"), (2, "title")):
        for xid, xd, xt in X:
            if xid in usedx:
                continue
            k = xd if idx == 1 else xt
            if not k:
                continue
            for yid, yd, yt in Y:
                if yid in usedy:
                    continue
                if (yd if idx == 1 else yt) == k:
                    pairs[(xid, yid)] = key
                    usedx.add(xid)
                    usedy.add(yid)
                    break
    return pairs


p12 = match(A, B)
p21 = {(y, x): v for (x, y), v in match(B, A).items()}
by_doi = sum(1 for v in p12.values() if v == "doi")
by_ti = sum(1 for v in p12.values() if v == "title")
inter = len(p12)
only_s = n_e1 - inter
only_w = n_e2 - inter
union = n_e1 + n_e2 - inter
t3a = {r["measure"]: r["n"] for r in read_table("T3a_scopus_wos.csv")}
exp04 = tuple(int(t3a[k]) for k in ["pairs by DOI", "pairs by normalised title", "intersection",
                                     "only Scopus", "only WoS", "union"])
rec04 = (by_doi, by_ti, inter, only_s, only_w, union)
add("C04a", "Scopus-WoS: by DOI/by title/intersection/only S/only W/union",
    "184/32/216/625/15/856 (T3a %s)" % ("/".join(map(str, exp04)),), "/".join(map(str, rec04)),
    rec04 == (184, 32, 216, 625, 15, 856) and exp04 == rec04)
sym = set(p12) == set(p21)
sym_lab = p12 == p21
add("C04b", "E1->E2 and E2->E1 matching give the same pair set", "identical",
    "identical set: %s; identical labels: %s; E2->E1 pairs %d" % (sym, sym_lab, len(p21)), sym,
    "" if sym_lab else "labels differ on %d pairs" % sum(1 for k in p12 if p21.get(k) != p12[k]))
tp = read_table("T3a_pairs.csv")
tp_set = {(r["eid"].strip(), r["ut"].strip()): r["matched_by"].strip() for r in tp}
lab_norm = {"doi": "doi", "title": "title", "normalised title": "title", "normalised_title": "title"}
tp_lab = {k: lab_norm.get(v.lower(), v.lower()) for k, v in tp_set.items()}
eq_set = set(tp_set) == set(p12)
eq_lab = tp_lab == p12
add("C04c", "tables/T3a_pairs.csv equals recomputed pair set", "%d rows" % len(tp),
    "%d pairs; set equal %s; matched_by equal %s; only-table %d; only-mine %d" % (
        len(p12), eq_set, eq_lab, len(set(tp_set) - set(p12)), len(set(p12) - set(tp_set))),
    eq_set and eq_lab and len(tp) == len(tp_set))

# ---------------- C05 / C08 merged ----------------
with open(MERGED, encoding="utf-8-sig", newline="") as f:
    rd = csv.DictReader(f)
    mcols = list(rd.fieldnames)
    mrows = list(rd)
low = {c.lower(): c for c in mcols}


def col(*names):
    for n in names:
        if n in low:
            return low[n]
    return None


c_eid, c_ut = col("eid", "scopus_eid"), col("ut", "wos_ut")
c_s, c_w, c_id = col("in_scopus"), col("in_wos"), col("work_id")
if None in (c_eid, c_ut, c_s, c_w, c_id):
    print("merged columns:", mcols)
n_m = len(mrows)
ins = sum(1 for r in mrows if r[c_s].strip() in ("1", "1.0", "True", "true"))
inw = sum(1 for r in mrows if r[c_w].strip() in ("1", "1.0", "True", "true"))
both = sum(1 for r in mrows if r[c_s].strip() in ("1", "1.0", "True", "true")
           and r[c_w].strip() in ("1", "1.0", "True", "true"))
eid_c = Counter(r[c_eid].strip() for r in mrows if ne(r[c_eid]))
ut_c = Counter(r[c_ut].strip() for r in mrows if ne(r[c_ut]))
eid_ok = all(eid_c.get(e) == 1 for e in e1_eids) and set(eid_c) == set(e1_eids)
ut_ok = all(ut_c.get(u) == 1 for u in e2_uts) and set(ut_c) == set(e2_uts)
wid_ok = len({r[c_id] for r in mrows}) == n_m and all(ne(r[c_id]) for r in mrows)
mpairs = {(r[c_eid].strip(), r[c_ut].strip()) for r in mrows if ne(r[c_eid]) and ne(r[c_ut])}
flag_consistent = all((r[c_s].strip() in ("1", "1.0", "True", "true")) == ne(r[c_eid]) and
                      (r[c_w].strip() in ("1", "1.0", "True", "true")) == ne(r[c_ut]) for r in mrows)
t4 = {r["flag"]: r["n"] for r in read_table("T4_merged_flags.csv")}
rec05 = (n_m, ins, inw, both)
add("C05a", "merged corpus rows / in_scopus / in_wos / both",
    "856/841/231/216 (T4 %s/%s/%s/%s)" % (t4.get("rows"), t4.get("in_scopus"), t4.get("in_wos"), t4.get("both")),
    "%d/%d/%d/%d" % rec05,
    rec05 == (856, 841, 231, 216) and (int(t4["rows"]), int(t4["in_scopus"]), int(t4["in_wos"]), int(t4["both"])) == rec05)
add("C05b", "every E1 EID once, every E2 UT once, work_id unique; flags agree with id presence; merged pairs = recomputed pairs",
    "all true", "EID %s; UT %s; work_id %s; flags %s; pairs equal %s (%d)" % (
        eid_ok, ut_ok, wid_ok, flag_consistent, mpairs == set(p12), len(mpairs)),
    eid_ok and ut_ok and wid_ok and flag_consistent and mpairs == set(p12))

bad_m = [c for c in mcols if c.strip().lower() in BANNED_COLS]
m_email = m_orcid = 0
for r in mrows:
    for v in r.values():
        if v:
            m_email += len(EMAIL_RE.findall(v))
            m_orcid += len(ORCID_RE.findall(v))
add("C08", "merged corpus: banned contact columns / e-mail shapes / ORCID shapes", "0/0/0",
    "%d/%d/%d" % (len(bad_m), m_email, m_orcid), not bad_m and m_email == 0 and m_orcid == 0,
    "%d columns checked" % len(mcols) + (("; banned: " + ",".join(bad_m)) if bad_m else ""))
del mrows

# ---------------- C06 ----------------


def series(name):
    with open(EX + "/" + name, encoding="utf-8-sig", newline="") as f:
        return {int(r["year"]): int(r["documents"]) for r in csv.DictReader(f)}


kz, wt, wa = series("scopus_years_KZ_all.csv"), series("scopus_years_world_topic.csv"), series("scopus_years_world_all.csv")
e1y = Counter(int(yr(r["Year"])) for r in e1)
t5 = {r["year"]: r for r in read_table("T5_topic_share.csv")}
bad6 = []
bad6_round = []
years = [str(y) for y in range(2003, 2026)] + ["2003-2025"]
for y in years:
    if y == "2003-2025":
        tk = sum(e1y[i] for i in range(2003, 2026))
        k = sum(kz[i] for i in range(2003, 2026))
        w = sum(wt[i] for i in range(2003, 2026))
        a = sum(wa[i] for i in range(2003, 2026))
    else:
        i = int(y)
        tk, k, w, a = e1y[i], kz[i], wt[i], wa[i]
    sk = 100.0 * tk / k
    sw = 100.0 * w / a
    ai = sk / sw
    r = t5.get(y)
    if r is None:
        bad6.append(y + ":missing")
        continue
    if (int(r["topic_KZ_E1"]), int(r["KZ_all"]), int(r["topic_world"]), int(r["world_all"])) != (tk, k, w, a):
        bad6.append(y + ":counts")
    if "%.3f" % sk != "%.3f" % float(r["share_KZ_pct"]) or "%.3f" % sw != "%.3f" % float(r["share_world_pct"]):
        bad6.append(y + ":shares")
    if "%.3f" % ai != "%.3f" % float(r["activity_index"]):
        bad6.append(y + ":AI")
    if abs(ai - float(r["activity_index"])) > 0.0005 + 1e-12:
        bad6_round.append(y)
extra = set(t5) - set(years)
add("C06", "T5 topic share: counts, share_KZ, share_world, activity index (3 dp) for 2003-2025 and total",
    "24 rows of T5", "%d mismatching rows; extra rows %d" % (len(bad6), len(extra)), not bad6 and not extra,
    ("; ".join(bad6)) if bad6 else "E1 total %d; AI total %.3f" % (sum(e1y.values()), (841 / 75667) / (415133 / 70937062)))

# ---------------- C07 ----------------
abstracts = set()
abs60 = set()
for r in e1:
    a = (r.get("Abstract") or "").strip()
    if a:
        abstracts.add(a)
        abs60.add(a[:60])
for r in e2:
    a = f1(r, "AB")
    if a:
        abstracts.add(a)
refs = set()
for r in e1:
    for x in (r.get("References") or "").split("; "):
        if x.strip():
            refs.add(x.strip())
for r in e2:
    for x in r.get("CR", []):
        if x.strip():
            refs.add(x.strip())

files = sorted(os.listdir(TAB))
targets = [TAB + "/" + fn for fn in files] + [NUMS]
n_email = n_orcid = n_badcol = n_abs = n_abs60 = n_ref = 0
cells_checked = 0
hit_files = set()
NUM_RE = re.compile(r"^[0-9]+(?:[.,][0-9]+)?$")
numeric_refs = set()
n_ref_numeric = 0


def json_strings(o, keys):
    if isinstance(o, dict):
        for k, v in o.items():
            keys.append(str(k))
            yield str(k)
            yield from json_strings(v, keys)
    elif isinstance(o, list):
        for v in o:
            yield from json_strings(v, keys)
    elif o is not None:
        yield str(o)


for p in targets:
    with open(p, encoding="utf-8-sig") as f:
        text = f.read()
    base = os.path.basename(p)
    e = len(EMAIL_RE.findall(text))
    o = len(ORCID_RE.findall(text))
    a60 = sum(1 for s in abs60 if s in text)
    cells = []
    headers = []
    if p.endswith(".csv"):
        rows = list(csv.reader(text.splitlines()))
        if rows:
            headers = rows[0]
        for row in rows:
            cells.extend(row)
    elif p.endswith(".md"):
        in_table = False
        for ln in text.splitlines():
            if "|" in ln:
                parts = [c.strip() for c in ln.strip().strip("|").split("|")]
                cells.extend(parts)
                if not in_table:
                    headers.extend(parts)  # first row of each markdown table = column names
                in_table = True
            else:
                in_table = False
                cells.append(ln.strip())
    elif p.endswith(".json"):
        keys = []
        cells = list(json_strings(json.loads(text), keys))
        headers = keys
    else:
        cells = [ln.strip() for ln in text.splitlines()]
    bc = sum(1 for h in headers if h.strip().lower() in {"correspondence address", "em", "oi", "ri", "rp"})
    ab = sum(1 for c in cells if c.strip() and c.strip() in abstracts)
    rf_all = [c.strip() for c in cells if c.strip() and c.strip() in refs]
    numeric_refs.update(c for c in rf_all if NUM_RE.match(c))
    n_ref_numeric += sum(1 for c in rf_all if NUM_RE.match(c))
    rf = sum(1 for c in rf_all if not NUM_RE.match(c))
    cells_checked += len(cells)
    n_email += e
    n_orcid += o
    n_badcol += bc
    n_abs += ab
    n_abs60 += a60
    n_ref += rf
    if e or o or bc or ab or a60 or rf:
        hit_files.add(base)
add("C07", "R13 in tables/* and numbers.json: e-mail / ORCID shapes / contact-named columns / abstract cells / abstract 60-char prefixes / reference cells",
    "0/0/0/0/0/0", "%d/%d/%d/%d/%d/%d" % (n_email, n_orcid, n_badcol, n_abs, n_abs60, n_ref),
    n_email == n_orcid == n_badcol == n_abs == n_abs60 == n_ref == 0,
    "%d files, %d cells; %d abstracts, %d distinct references" % (len(targets), cells_checked, len(abstracts), len(refs))
    + "; set aside %d purely numeric cells that coincide with degenerate one-number references (values: %s)" % (
        n_ref_numeric, ",".join(sorted(numeric_refs)))
    + (("; files with hits: " + ",".join(sorted(hit_files))) if hit_files else ""))

with open(OUT, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["check_id", "what", "expected_from_tables", "recomputed", "verdict", "note"])
    w.writeheader()
    w.writerows(results)
print("written", OUT, "PASS", sum(1 for r in results if r["verdict"] == "PASS"), "of", len(results))
