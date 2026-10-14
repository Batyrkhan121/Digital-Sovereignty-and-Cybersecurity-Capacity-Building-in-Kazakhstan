import sys
sys.dont_write_bytecode = True

# Independent verifier of phase F13.2 (structural indicators of a Scopus export).
# Stdlib only, no network. Reads from E1 only the allowed columns (row values
# of all other columns are dropped at parse time and never accessed); from E2
# keeps only the tags UT, PY, DT, TC. Prints and writes only counts, ids,
# source names, column names and PASS/FAIL.

import csv
import hashlib
import re
import statistics
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import os
ROOT = os.environ.get("PROJECT_ROOT", ".")
DR = ROOT + "/outputs/dprg_revision_2026"
PH = DR + "/phase_F13_2"
TB = PH + "/tables"
FIGCSV = PH + "/figures/Fig_annual_output_by_type.csv"
NUMS = PH + "/F13_2_numbers.json"
E1 = DR + "/author_exports_2026_10/scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
E2 = DR + "/author_exports_2026_10/wos_full_TS_KZ_2003_2025_2026-10-13.txt"
PAIRS = DR + "/phase_F13_1/tables/T3a_pairs.csv"
T2B = DR + "/phase_F13_1/tables/T2b_years.csv"
F121 = DR + "/phase_F12_1/tables"
OUTCSV = PH + "/phase_F13_2_independent_verification.csv"

E1_SHA = "fe01023d23afe95df83d594fdfea2c3b488e52ffb8778def4067a2d795a991f3"
E2_SHA = "413b0fa8ba8dd496072367601b7ca66bf0c7cac01d30553aa702b288dd402160"

YEARS = list(range(2003, 2026))
TOT = "2003-2025"
TYPE_COLS = ["article", "conference paper", "book chapter", "review", "book", "retracted"]
PERIODS = [("2003-2016", 2003, 2016), ("2017-2021", 2017, 2021), ("2022-2025", 2022, 2025)]

rows_out = []


def add(cid, what, exp, rec, ok, note=""):
    rows_out.append([cid, what, str(exp), str(rec), "PASS" if ok else "FAIL", note])


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def read_table(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        r = csv.reader(f)
        hdr = next(r)
        data = [row for row in r if row]
    return hdr, data


def read_dicts(path):
    hdr, data = read_table(path)
    return hdr, [dict(zip(hdr, row)) for row in data]


def num(x):
    s = str(x).strip()
    try:
        return int(s)
    except ValueError:
        return float(s)


def to_int0(s):
    s = (s or "").strip()
    return int(s) if s else 0


def norm(s):
    return " ".join(re.sub(r"[^0-9a-z]+", " ", s.casefold()).split())


def short(lst, k=5):
    lst = list(lst)
    return "; ".join(str(x) for x in lst[:k]) + (" ..." if len(lst) > k else "")


# ---------------------------------------------------------------- E1
csv.field_size_limit(2 ** 31 - 1)
KEEP = ["EID", "Year", "Source title", "Cited by", "Document Type", "Open Access",
        "Language of Original Document", "Funding Details"]
recs = []
bad_len = 0
with open(E1, encoding="utf-8-sig", newline="") as f:
    rdr = csv.reader(f)
    hdr = [h.strip() for h in next(rdr)]
    miss = [k for k in KEEP if k not in hdr]
    if miss:
        print("E1 missing columns:", miss)
        sys.exit(1)
    idx = {k: hdr.index(k) for k in KEEP}
    for row in rdr:
        if not row:
            continue
        if len(row) != len(hdr):
            bad_len += 1
        recs.append({
            "eid": row[idx["EID"]].strip(),
            "year": int(row[idx["Year"]].strip()),
            "src": row[idx["Source title"]],
            "cites": to_int0(row[idx["Cited by"]]),
            "dt": row[idx["Document Type"]].strip(),
            "oa": row[idx["Open Access"]],
            "lang": row[idx["Language of Original Document"]].strip(),
            "fund_nonempty": bool(row[idx["Funding Details"]].strip()),
        })
        row = None
N = len(recs)
print("E1 columns in header:", len(hdr), "| rows:", N, "| rows with unexpected length:", bad_len)

# ---------------------------------------------------------------- E2
WKEEP = {"UT", "PY", "DT", "TC"}
wos = []
cur = {}
last = None
tag_re = re.compile(r"^([A-Z][A-Z0-9])(?: (.*))?$")
with open(E2, encoding="utf-8-sig", errors="replace") as f:
    for line in f:
        line = line.rstrip("\r\n")
        if line == "ER" or line.startswith("ER "):
            if cur:
                wos.append(cur)
            cur = {}
            last = None
            continue
        if line.startswith("   "):
            if last in WKEEP:
                cur[last] = cur[last] + " " + line.strip()
            continue
        m = tag_re.match(line)
        if m:
            last = m.group(1)
            if last in WKEEP:
                cur[last] = (m.group(2) or "").strip()
            continue
        last = None
wos_by_ut = {}
dup_ut = 0
for w in wos:
    ut = w.get("UT", "").strip()
    if ut in wos_by_ut:
        dup_ut += 1
    wos_by_ut[ut] = w
print("E2 records:", len(wos), "| unique UT:", len(wos_by_ut), "| duplicate UT:", dup_ut)

# ---------------------------------------------------------------- C01
eids = [r["eid"] for r in recs]
add("C01a", "E1 data rows", 841, N, N == 841)
add("C01b", "E1 unique EID", 841, len(set(eids)), len(set(eids)) == 841)
h1 = sha256(E1)
add("C01c", "sha256 of E1", E1_SHA, h1, h1 == E1_SHA)
h2 = sha256(E2)
add("C01d", "sha256 of E2", E2_SHA, h2, h2 == E2_SHA,
    "E2 parsed: %d records, %d unique UT" % (len(wos), len(wos_by_ut)))

# ---------------------------------------------------------------- C02
yc = {y: 0 for y in YEARS}
out_rng = 0
for r in recs:
    if r["year"] in yc:
        yc[r["year"]] += 1
    else:
        out_rng += 1
_, t1a = read_dicts(TB + "/T1a_years.csv")
t1a_m = {row["year"].strip(): num(row["records"]) for row in t1a}
_, t2b = read_dicts(T2B)
t2b_m = {row["year"].strip(): num(row["E1"]) for row in t2b}
bad = [y for y in YEARS if not (t1a_m.get(str(y)) == t2b_m.get(str(y)) == yc[y])]
tot_ok = t1a_m.get(TOT) == t2b_m.get(TOT) == sum(yc.values()) == 841
add("C02", "records by year 2003-2025: T1a_years = F13.1 T2b_years E1 = own count",
    "T1a total %s; T2b total %s; 2024=%s; 2025=%s" % (t1a_m.get(TOT), t2b_m.get(TOT), t1a_m.get("2024"), t1a_m.get("2025")),
    "own total %d; 2024=%d; 2025=%d; out of range %d" % (sum(yc.values()), yc[2024], yc[2025], out_rng),
    not bad and tot_ok and out_rng == 0,
    "23 years compared; mismatching years: %s" % (bad or "none"))

# ---------------------------------------------------------------- C03
CALLER_TYPES = [("Article", 396), ("Conference paper", 387), ("Book chapter", 32),
                ("Review", 21), ("Retracted", 3), ("Book", 2)]
tc = Counter(r["dt"] for r in recs)
_, t1b = read_dicts(TB + "/T1b_types_exported.csv")
t1b_l = [(row["doc_type"].strip(), num(row["n"])) for row in t1b]
ok = (dict(t1b_l) == dict(CALLER_TYPES) == dict(tc)) and len(t1b_l) == len(CALLER_TYPES)
add("C03", "document types as exported (T1b_types_exported)",
    "; ".join("%s %d" % kv for kv in t1b_l),
    "; ".join("%s %d" % kv for kv in sorted(tc.items(), key=lambda kv: -kv[1])),
    ok, "also equals the brief's list (Article 396 ... Book 2)" if dict(t1b_l) == dict(CALLER_TYPES) else "differs from the brief's list")

# ---------------------------------------------------------------- C04
sc_cnt = Counter(r["src"] for r in recs)
ranked = sorted(sc_cnt.items(), key=lambda kv: (-kv[1], kv[0].casefold(), kv[0]))
n_strip = len(set(r["src"].strip() for r in recs))
n_fold = len(set(r["src"].strip().casefold() for r in recs))
n_empty = sum(1 for r in recs if not r["src"].strip())
_, t2a_src = read_dicts(TB + "/T2a_sources.csv")
_, conc_rows = read_table(TB + "/T2a_concentration.csv")
conc = {row[0].strip(): row[1].strip() for row in conc_rows}
add("C04a", "distinct sources (Source title as exported)",
    "%s (T2a_concentration); %d rows in T2a_sources" % (conc.get("distinct sources"), len(t2a_src)),
    len(sc_cnt),
    num(conc.get("distinct sources")) == len(sc_cnt) == len(t2a_src),
    "after strip %d; after strip+casefold %d; empty titles %d" % (n_strip, n_fold, n_empty))

exp20 = [(row["source_title"], num(row["records"])) for row in t2a_src[:20]]
rec20 = ranked[:20]
diff20 = [i + 1 for i in range(20) if i >= len(exp20) or exp20[i] != rec20[i]]
add("C04b", "top 20 sources of T2a_sources (name, records, order)",
    "20 rows; #1 %s %d; #20 %s %d" % (exp20[0] + exp20[19]),
    "20 rows; #1 %s %d; #20 %s %d" % (rec20[0] + rec20[19]),
    not diff20, "ranks differing: %s; 21st own: %s %d" % (diff20 or "none", ranked[20][0], ranked[20][1]))

expall = [(row["rank"].strip(), row["source_title"], num(row["records"])) for row in t2a_src]
recall = [(str(i + 1), kv[0], kv[1]) for i, kv in enumerate(ranked)]
diffall = [e[0] for e, r in zip(expall, recall) if e != r]
add("C04c", "full ranking of T2a_sources (rank, name, records) for all sources",
    "%d rows" % len(expall), "%d rows" % len(recall),
    not diffall and len(expall) == len(recall), "ranks differing: %s" % (short(diffall) if diffall else "none"))

zone_of = {}
cum = 0
for name, n in ranked:
    if cum < N / 3:
        z = 1
    elif cum < 2 * N / 3:
        z = 2
    else:
        z = 3
    zone_of[name] = z
    cum += n
for z in (1, 2, 3):
    rec_set = {nm for nm, zz in zone_of.items() if zz == z}
    rec_recs = sum(sc_cnt[nm] for nm in rec_set)
    exp_set = {row["source_title"] for row in t2a_src if row["bradford_zone"].strip() == str(z)}
    exp_recs = sum(num(row["records"]) for row in t2a_src if row["bradford_zone"].strip() == str(z))
    conc_v = conc.get("Bradford zone %d: sources / records" % z, "")
    ok = (rec_set == exp_set and conc_v.replace(" ", "") == "%d/%d" % (len(rec_set), rec_recs)
          and exp_recs == rec_recs)
    add("C04d%d" % z, "Bradford zone %d: sources and records" % z,
        "%s (T2a_concentration); T2a_sources column: %d / %d" % (conc_v, len(exp_set), exp_recs),
        "%d / %d" % (len(rec_set), rec_recs), ok,
        "source sets equal" if rec_set == exp_set else
        "only in tables: %s | only own: %s" % (short(sorted(exp_set - rec_set), 3), short(sorted(rec_set - exp_set), 3)))

one_rec = sum(1 for v in sc_cnt.values() if v == 1)
sh = {k: round(100.0 * sum(n for _, n in ranked[:k]) / N, 1) for k in (5, 10, 20)}
exp_ext = "one-record %s; top5 %s; top10 %s; top20 %s" % (
    conc.get("sources with one record"), conc.get("share of records in the top 5 sources (%)"),
    conc.get("share of records in the top 10 sources (%)"), conc.get("share of records in the top 20 sources (%)"))
rec_ext = "one-record %d; top5 %.1f; top10 %.1f; top20 %.1f" % (one_rec, sh[5], sh[10], sh[20])
ok = (num(conc.get("sources with one record")) == one_rec
      and float(conc.get("share of records in the top 5 sources (%)")) == sh[5]
      and float(conc.get("share of records in the top 10 sources (%)")) == sh[10]
      and float(conc.get("share of records in the top 20 sources (%)")) == sh[20])
add("C04e", "extra: one-record sources and top-k shares (T2a_concentration)", exp_ext, rec_ext, ok)

# ---------------------------------------------------------------- C05
cites = [r["cites"] for r in recs]
tot_c = sum(cites)
med_c = statistics.median(cites)
unc = sum(1 for c in cites if c == 0)
srt = sorted(cites, reverse=True)
hidx = sum(1 for i, c in enumerate(srt, 1) if c >= i)
_, t3a_rows = read_table(TB + "/T3a_citations.csv")
t3a = {row[0].strip(): row[1].strip() for row in t3a_rows}
add("C05a", "citations total", t3a.get("citations, total"), tot_c, num(t3a.get("citations, total")) == tot_c)
add("C05b", "citations median", t3a.get("median"), med_c, float(t3a.get("median")) == float(med_c))
add("C05c", "uncited records", t3a.get("uncited records"), unc, num(t3a.get("uncited records")) == unc)
add("C05d", "h-index of the corpus", t3a.get("h-index of the corpus"), hidx, num(t3a.get("h-index of the corpus")) == hidx)
ext_e = "records %s; mean %s; max %s; >=10 %s; >=50 %s; >=100 %s; uncited%% %s" % (
    t3a.get("records"), t3a.get("mean per record"), t3a.get("maximum"), t3a.get("records with >= 10 citations"),
    t3a.get("records with >= 50 citations"), t3a.get("records with >= 100 citations"), t3a.get("uncited (%)"))
ge = {k: sum(1 for c in cites if c >= k) for k in (10, 50, 100)}
mean_c = round(tot_c / N, 2)
unc_p = round(100.0 * unc / N, 1)
ext_r = "records %d; mean %.2f; max %d; >=10 %d; >=50 %d; >=100 %d; uncited%% %.1f" % (
    N, mean_c, max(cites), ge[10], ge[50], ge[100], unc_p)
ok = (num(t3a.get("records")) == N and float(t3a.get("mean per record")) == mean_c
      and num(t3a.get("maximum")) == max(cites) and num(t3a.get("records with >= 10 citations")) == ge[10]
      and num(t3a.get("records with >= 50 citations")) == ge[50]
      and num(t3a.get("records with >= 100 citations")) == ge[100] and float(t3a.get("uncited (%)")) == unc_p)
add("C05f", "extra: other rows of T3a_citations", ext_e, ext_r, ok)

top = sorted(recs, key=lambda r: (-r["cites"], r["eid"]))
top20 = top[:20]
_, t3e = read_dicts(TB + "/T3e_top20_cited.csv")
e_ids = [row["eid"].strip() for row in t3e]
r_ids = [r["eid"] for r in top20]
same_order = e_ids == r_ids
cit_ok = [num(row["cited_by"]) for row in t3e] == [r["cites"] for r in top20]
add("C05e", "set of EIDs of the 20 most cited (T3e_top20_cited; ties by EID)",
    "%d EIDs; cited_by %s..%s" % (len(e_ids), t3e[0]["cited_by"], t3e[-1]["cited_by"]),
    "%d EIDs; cited_by %d..%d" % (len(r_ids), top20[0]["cites"], top20[-1]["cites"]),
    set(e_ids) == set(r_ids) and len(e_ids) == 20,
    "order identical: %s; cited_by identical: %s; 21st own cited_by %d (boundary tie: %s)" % (
        same_order, cit_ok, top[20]["cites"], top[20]["cites"] == top20[-1]["cites"]))

# ---------------------------------------------------------------- C06
oa_recs = [r for r in recs if r["oa"].strip()]
cat = Counter()
for r in oa_recs:
    for c in {p.strip() for p in r["oa"].split(";") if p.strip()}:
        cat[c] += 1
_, t4a = read_dicts(TB + "/T4a_open_access.csv")
add("C06a", "records with non-empty Open Access (T4a first row)",
    "%s (%s)" % (t4a[0]["n"], t4a[0]["category"].strip()), len(oa_recs), num(t4a[0]["n"]) == len(oa_recs))
t4a_m = {row["category"].strip(): row["n"].strip() for row in t4a}
t4a_cats = {k for k in list(t4a_m)[1:] if not k.startswith("open access in") and not k.startswith("citations of")}
for c in sorted(cat, key=lambda k: -cat[k]):
    ev = t4a_m.get(c)
    add("C06b_" + c.replace(" ", "_"), "open access category '%s'" % c, ev, cat[c],
        ev is not None and num(ev) == cat[c])
if t4a_cats != set(cat):
    add("C06b_set", "open access category set", short(sorted(t4a_cats)), short(sorted(cat)), False)
per_e, per_r, ok = [], [], True
for lab, a, b in PERIODS:
    n_oa = sum(1 for r in oa_recs if a <= r["year"] <= b)
    ev = t4a_m.get("open access in " + lab)
    per_e.append("%s %s" % (lab, ev))
    per_r.append("%s %d" % (lab, n_oa))
    ok = ok and ev is not None and num(ev) == n_oa
add("C06c", "extra: open access records by period (T4a)", "; ".join(per_e), "; ".join(per_r), ok)


def mm(lst):
    return "%.2f / %s" % (sum(lst) / len(lst), ("%g" % statistics.median(lst)))


oa_c = [r["cites"] for r in oa_recs]
no_c = [r["cites"] for r in recs if not r["oa"].strip()]
e_oa = t4a_m.get("citations of OA records: mean / median", "")
e_no = t4a_m.get("citations of non-OA records: mean / median", "")
add("C06d", "extra: citations of OA / non-OA records, mean / median (T4a)",
    "OA %s; non-OA %s" % (e_oa, e_no), "OA %s; non-OA %s" % (mm(oa_c), mm(no_c)),
    e_oa.replace(" ", "") == mm(oa_c).replace(" ", "") and e_no.replace(" ", "") == mm(no_c).replace(" ", ""))

lc = Counter(r["lang"] for r in recs)
_, t1f = read_dicts(TB + "/T1f_language.csv")
t1f_m = {row["language"].strip(): num(row["n"]) for row in t1f}
add("C06e", "languages as exported (T1f_language)",
    "; ".join("%s %d" % kv for kv in t1f_m.items()),
    "; ".join("%s %d" % kv for kv in sorted(lc.items(), key=lambda kv: -kv[1])),
    t1f_m == dict(lc), "multi-language values (with ';'): %d" % sum(1 for r in recs if ";" in r["lang"]))

fund_n = sum(1 for r in recs if r["fund_nonempty"])
_, t4b = read_dicts(TB + "/T4b_funding.csv")
add("C06f", "records with non-empty Funding Details (T4b first row)",
    "%s of %s (%s)" % (t4b[0]["funded"], t4b[0]["records"], t4b[0]["group"].strip()),
    "%d of %d" % (fund_n, N), num(t4b[0]["funded"]) == fund_n and num(t4b[0]["records"]) == N)
grp = {}
for lab, a, b in PERIODS:
    sub = [r for r in recs if a <= r["year"] <= b]
    grp[lab] = (len(sub), sum(1 for r in sub if r["fund_nonempty"]))
for t in TYPE_COLS:
    sub = [r for r in recs if r["dt"].lower() == t]
    grp[t] = (len(sub), sum(1 for r in sub if r["fund_nonempty"]))
bad = []
for row in t4b[1:]:
    g = row["group"].strip()
    if g in grp:
        if (num(row["records"]), num(row["funded"])) != grp[g]:
            bad.append(g)
covered = [row["group"].strip() for row in t4b[1:] if row["group"].strip() in grp]
add("C06g", "extra: funded records by period and type (T4b rows)",
    "%d groups compared" % len(covered), "%d groups computed" % len(grp),
    not bad and len(covered) == len(grp), "mismatching groups: %s" % (bad or "none"))

# ---------------------------------------------------------------- C07
_, pairs = read_dicts(PAIRS)
by_eid = {r["eid"]: r for r in recs}
sv, wv = [], []
miss_p, miss_tc = 0, 0
for p in pairs:
    e = by_eid.get(p["eid"].strip())
    w = wos_by_ut.get(p["ut"].strip())
    if e is None or w is None:
        miss_p += 1
        continue
    if not w.get("TC", "").strip():
        miss_tc += 1
    sv.append(e["cites"])
    wv.append(to_int0(w.get("TC", "")))


def avg_ranks(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    rk = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        a = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            rk[order[k]] = a
        i = j + 1
    return rk


def pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    sab = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    saa = sum((x - ma) ** 2 for x in a)
    sbb = sum((y - mb) ** 2 for y in b)
    return sab / (saa * sbb) ** 0.5


rho = pearson(avg_ranks(sv), avg_ranks(wv))
_, t5c_rows = read_table(TB + "/T5c_citations.csv")
t5c = {row[0].strip(): row[1].strip() for row in t5c_rows}
n_pairs = len(sv)
add("C07a", "pairs found in E1 and E2", "%s (T5c); %d rows in T3a_pairs" % (t5c.get("pairs"), len(pairs)),
    n_pairs, num(t5c.get("pairs")) == n_pairs == len(pairs) == 216,
    "unmatched pairs %d; pairs with empty TC %d; unique eid %d, unique ut %d" % (
        miss_p, miss_tc, len({p["eid"] for p in pairs}), len({p["ut"] for p in pairs})))
er = t5c.get("Spearman rank correlation (average ranks for ties)")
add("C07b", "Spearman rho, Scopus Cited by vs WoS TC (3 decimals)", er, "%.3f" % rho,
    float(er) == round(rho, 3), "unrounded %.6f" % rho)
ms, mw = statistics.median(sv), statistics.median(wv)
add("C07c", "medians Scopus / WoS", "%s / %s" % (t5c.get("median Scopus Cited by"), t5c.get("median WoS TC")),
    "%g / %g" % (ms, mw), float(t5c.get("median Scopus Cited by")) == ms and float(t5c.get("median WoS TC")) == mw)
add("C07d", "sums Scopus / WoS", "%s / %s" % (t5c.get("sum Scopus Cited by"), t5c.get("sum WoS TC")),
    "%d / %d" % (sum(sv), sum(wv)), num(t5c.get("sum Scopus Cited by")) == sum(sv) and num(t5c.get("sum WoS TC")) == sum(wv))
gt = sum(1 for a, b in zip(sv, wv) if a > b)
eq = sum(1 for a, b in zip(sv, wv) if a == b)
lt = sum(1 for a, b in zip(sv, wv) if a < b)
add("C07e", "counts Scopus > WoS / equal / WoS > Scopus",
    "%s / %s / %s" % (t5c.get("Scopus > WoS"), t5c.get("equal"), t5c.get("WoS > Scopus")),
    "%d / %d / %d" % (gt, eq, lt),
    (num(t5c.get("Scopus > WoS")), num(t5c.get("equal")), num(t5c.get("WoS > Scopus"))) == (gt, eq, lt))

# ---------------------------------------------------------------- C08 (F12.1 side)
_, f_t1a = read_dicts(F121 + "/T1a_doc_types.csv")
f_types = {row["doc_type"].strip(): num(row["n"]) for row in f_t1a}
_, d1 = read_dicts(TB + "/D1_types.csv")
bad = [row["doc_type_F12_1"] for row in d1 if f_types.get(row["doc_type_F12_1"].strip()) != num(row["n_F12_1"])]
d1_types = {row["doc_type_F12_1"].strip() for row in d1}
add("C08a", "D1_types n_F12_1 = F12.1 T1a_doc_types n",
    "%d types in F12.1, sum %d" % (len(f_types), sum(f_types.values())),
    "%d rows in D1, sum %d" % (len(d1), sum(num(row["n_F12_1"]) for row in d1)),
    not bad and d1_types == set(f_types), "mismatches: %s" % (bad or "none"))

_, f_t1b = read_dicts(F121 + "/T1b_top20_sources.csv")
f_src = {num(row["rank"]): (row["source_title"], num(row["n"])) for row in f_t1b}
_, d2 = read_dicts(TB + "/D2_top20_sources.csv")
bad, name_bad = [], []
seen = set()
for row in d2:
    rk = row["rank_F12_1"].strip()
    if not rk:
        continue
    rk = num(rk)
    seen.add(rk)
    fv = f_src.get(rk)
    if fv is None or fv[1] != num(row["n_F12_1"]):
        bad.append(rk)
    elif norm(fv[0]) != norm(row["source"]):
        name_bad.append(rk)
add("C08b", "D2_top20_sources rank_F12_1, n_F12_1 = F12.1 T1b_top20_sources (by rank)",
    "%d ranks in F12.1" % len(f_src), "%d ranks in D2" % len(seen),
    not bad and seen == set(f_src),
    "count mismatches: %s; ranks whose F12.1 name differs beyond case/punctuation: %s" % (bad or "none", name_bad or "none"))

_, f_t1c = read_dicts(F121 + "/T1c_year_by_type.csv")
f_yt = {row["year"].strip(): (num(row["Article"]), num(row["Conference Paper"]), num(row["Other"]), num(row["total"])) for row in f_t1c}
_, d3 = read_dicts(TB + "/D3_year_by_type.csv")
bad = []
for row in d3:
    y = row["year"].strip()
    v = (num(row["article_F12_1"]), num(row["conference_F12_1"]), num(row["other_F12_1"]), num(row["total_F12_1"]))
    if f_yt.get(y) != v:
        bad.append(y)
add("C08c", "D3_year_by_type F12.1 side = F12.1 T1c_year_by_type",
    "%d rows in F12.1 (total %s)" % (len(f_yt), f_yt.get(TOT)), "%d rows in D3" % len(d3),
    not bad and {row["year"].strip() for row in d3} == set(f_yt), "mismatching years: %s" % (bad or "none"))

_, f_t1d = read_dicts(F121 + "/T1d_citations_by_year.csv")
f_cy = {row["year"].strip(): (num(row["n"]), num(row["citations_sum"])) for row in f_t1d}
_, d4 = read_dicts(TB + "/D4_citations_by_year.csv")
bad = [row["year"] for row in d4 if f_cy.get(row["year"].strip()) != (num(row["records_F12_1"]), num(row["citations_F12_1"]))]
add("C08d", "D4_citations_by_year F12.1 side = F12.1 T1d n, citations_sum",
    "%d rows in F12.1 (total %s)" % (len(f_cy), f_cy.get(TOT)), "%d rows in D4" % len(d4),
    not bad and {row["year"].strip() for row in d4} == set(f_cy), "mismatching years: %s" % (bad or "none"))

_, f_lang = read_dicts(F121 + "/T1e_language_I2.csv")
f_lm = {row["doc_language"].strip(): num(row["n"]) for row in f_lang}
_, f_oa = read_dicts(F121 + "/T1e_open_access_I2.csv")
f_om = {row["openaccess_flag"].strip(): num(row["n"]) for row in f_oa}
_, d5 = read_dicts(TB + "/D5_language_oa.csv")
bad = []
codes_seen = set()
for row in d5:
    lab = row["language"].strip()
    code = row["code_F12_1"].strip()
    v = num(row["n_F12_1_I2_838"])
    if lab.startswith("open access: F12.1 flag true"):
        exp = f_om.get("true")
    elif lab.startswith("open access: F12.1 flag false"):
        exp = f_om.get("false", 0) + f_om.get("(missing)", 0)
    else:
        exp = f_lm.get(code, 0) if code else 0
        if code:
            codes_seen.add(code)
    if exp != v:
        bad.append(lab)
add("C08e", "D5_language_oa n_F12_1_I2_838 = F12.1 T1e_language_I2 and T1e_open_access_I2 (true; false + missing)",
    "languages %d codes; OA true %s; false+missing %d" % (len(f_lm), f_om.get("true"), f_om.get("false", 0) + f_om.get("(missing)", 0)),
    "%d rows in D5" % len(d5), not bad and codes_seen == set(f_lm), "mismatching rows: %s" % (bad or "none"))

# ---------------------------------------------------------------- C08 extras (E1 side vs own counts)
bad = [row["doc_type_E1"] for row in d1 if tc.get(row["doc_type_E1"].strip(), 0) != num(row["n_E1"])]
add("C08f", "extra: D1 E1 side (doc_type_E1, n_E1) = own count", "%d rows" % len(d1), "%d types" % len(tc),
    not bad and {row["doc_type_E1"].strip() for row in d1} == set(tc), "mismatches: %s" % (bad or "none"))

bad = []
for row in d2:
    rk = row["rank_E1"].strip()
    if not rk:
        continue
    rk = num(rk)
    if rk > len(ranked) or ranked[rk - 1] != (row["source"], num(row["n_E1"])):
        bad.append(rk)
add("C08g", "extra: D2 E1 side (source, rank_E1, n_E1) = own ranking", "%d rows" % len(d2), "own top 20",
    not bad, "mismatching ranks: %s" % (bad or "none"))

yt = {}
for r in recs:
    yt[(r["year"], r["dt"].lower())] = yt.get((r["year"], r["dt"].lower()), 0) + 1


def own_year_type(y):
    vals = [yt.get((y, t), 0) for t in TYPE_COLS]
    return vals + [sum(vals)]


own_tot = [sum(own_year_type(y)[i] for y in YEARS) for i in range(7)]
bad = []
for row in d3:
    y = row["year"].strip()
    v = own_tot if y == TOT else own_year_type(int(y))
    if (num(row["article_E1"]), num(row["conference_E1"]), num(row["other_E1"]), num(row["total_E1"])) != (v[0], v[1], sum(v[2:6]), v[6]):
        bad.append(y)
add("C08h", "extra: D3 E1 side = own year-by-type count (other = chapter+review+book+retracted)",
    "%d rows" % len(d3), "24 rows", not bad, "mismatching years: %s" % (bad or "none"))

cy = {y: [0, 0] for y in YEARS}
for r in recs:
    if r["year"] in cy:
        cy[r["year"]][0] += 1
        cy[r["year"]][1] += r["cites"]
cy_tot = [sum(v[0] for v in cy.values()), sum(v[1] for v in cy.values())]
bad = []
for row in d4:
    y = row["year"].strip()
    v = cy_tot if y == TOT else cy[int(y)]
    if [num(row["records_E1"]), num(row["citations_E1"])] != v:
        bad.append(y)
add("C08i", "extra: D4 E1 side (records_E1, citations_E1) = own count", "%d rows" % len(d4),
    "total %d / %d" % tuple(cy_tot), not bad, "mismatching years: %s" % (bad or "none"))

bad = []
for row in d5:
    lab = row["language"].strip()
    v = num(row["n_E1_841"])
    if lab.startswith("open access: F12.1 flag true"):
        exp = len(oa_recs)
    elif lab.startswith("open access: F12.1 flag false"):
        exp = N - len(oa_recs)
    else:
        exp = lc.get(lab, 0)
    if exp != v:
        bad.append(lab)
lang_cov = {row["language"].strip() for row in d5}
add("C08j", "extra: D5 E1 side (n_E1_841) = own language and OA counts", "%d rows" % len(d5),
    "OA %d; non-OA %d" % (len(oa_recs), N - len(oa_recs)),
    not bad and set(lc) <= lang_cov, "mismatching rows: %s" % (bad or "none"))

# ---------------------------------------------------------------- C09
import glob
import os

FORBID = {"authors", "author full names", "author(s) id", "authors with affiliations",
          "correspondence address", "em", "oi", "ri", "rp"}
csv_files = sorted(glob.glob(TB + "/*.csv")) + [FIGCSV]
md_files = sorted(glob.glob(TB + "/*.md"))
all_tables = sorted(p for p in glob.glob(TB + "/*") if os.path.isfile(p))
scan_files = all_tables + [FIGCSV, NUMS]

bad_cols = []
for p in csv_files:
    hdr_c, _ = read_table(p)
    for h in hdr_c:
        if h.strip().casefold() in FORBID:
            bad_cols.append("%s:%s" % (os.path.basename(p), h))
md_hdr_bad = []
for p in md_files:
    with open(p, encoding="utf-8-sig") as f:
        for ln in f:
            s = ln.strip()
            if s.startswith("|"):
                for c in s.strip("|").split("|"):
                    if c.strip().casefold() in FORBID:
                        md_hdr_bad.append(os.path.basename(p))
add("C09a", "no forbidden column names in tables/*.csv and the figure CSV", 0, len(bad_cols), not bad_cols,
    "%d CSV files checked; md table cells equal to a forbidden name: %d; offenders: %s" % (
        len(csv_files), len(md_hdr_bad), short(bad_cols) if bad_cols else "none"))

email_re = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+")
orcid_re = re.compile(r"(?<![0-9])(?:0000|0009)-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X](?![0-9X])")
any_orcid_re = re.compile(r"(?<![0-9])[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X](?![0-9X])")
n_mail = n_orc = n_any = n_at = 0
mail_files, orc_files = set(), set()
for p in scan_files:
    with open(p, encoding="utf-8-sig", errors="replace") as f:
        txt = f.read()
    a = len(email_re.findall(txt))
    b = len(orcid_re.findall(txt))
    n_mail += a
    n_orc += b
    n_any += len(any_orcid_re.findall(txt))
    n_at += txt.count("@")
    if a:
        mail_files.add(os.path.basename(p))
    if b:
        orc_files.add(os.path.basename(p))
add("C09b", "e-mail shapes in tables/*, figure CSV, F13_2_numbers.json", 0, n_mail, n_mail == 0,
    "%d files scanned; '@' characters %d; files: %s" % (len(scan_files), n_at, sorted(mail_files) or "none"))
add("C09c", "ORCID shapes (0000-/0009- first block) in the same files", 0, n_orc, n_orc == 0,
    "any dddd-dddd-dddd-dddX shape: %d; files: %s" % (n_any, sorted(orc_files) or "none"))

long_csv = []
for p in csv_files:
    hdr_c, data = read_table(p)
    for i, row in enumerate([hdr_c] + data, 1):
        for c in row:
            if len(c.split()) > 30:
                long_csv.append("%s row %d" % (os.path.basename(p), i))
add("C09d", "no CSV cell over 30 words (tables/*.csv, figure CSV)", 0, len(long_csv), not long_csv,
    "offenders: %s" % (short(long_csv) if long_csv else "none"))

sep_re = re.compile(r"^:?-{3,}:?$")
long_lines, long_cells = [], []
Z = chr(0)
for p in md_files:
    with open(p, encoding="utf-8-sig") as f:
        lines = f.read().splitlines()
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if s.startswith("|"):
            cells = [c.replace(Z, "|").strip() for c in s.replace("\\|", Z).strip("|").split("|")]
            if cells and all(sep_re.match(c) for c in cells if c):
                continue
            for c in cells:
                if len(c.split()) > 30:
                    long_cells.append("%s line %d" % (os.path.basename(p), i))
        elif len(s.split()) > 30:
            long_lines.append("%s line %d" % (os.path.basename(p), i))
add("C09e", "markdown: no non-table line over 30 words (tables/*.md)", 0, len(long_lines), not long_lines,
    "%d md files; offenders: %s" % (len(md_files), short(long_lines) if long_lines else "none"))
add("C09f", "markdown: no table cell over 30 words, header row included (tables/*.md)", 0, len(long_cells), not long_cells,
    "offenders: %s" % (short(long_cells) if long_cells else "none"))

# ---------------------------------------------------------------- C10
fh, fd = read_table(FIGCSV)
th, td = read_table(TB + "/T1c_year_by_type.csv")
with open(FIGCSV, "rb") as f:
    fb = f.read()
with open(TB + "/T1c_year_by_type.csv", "rb") as f:
    tb = f.read()
add("C10a", "figures/Fig_annual_output_by_type.csv equals tables/T1c_year_by_type.csv",
    "%d columns, %d rows" % (len(th), len(td)), "%d columns, %d rows" % (len(fh), len(fd)),
    [h.strip() for h in fh] == [h.strip() for h in th] and fd == td,
    "byte-identical: %s; headers identical: %s" % (fb == tb, fh == th))

exp_hdr = ["year"] + TYPE_COLS + ["total"]
bad = []
for row in td:
    y = row[0].strip()
    v = own_tot if y == TOT else own_year_type(int(y))
    if [num(x) for x in row[1:]] != v:
        bad.append(y)
add("C10b", "extra: T1c_year_by_type equals own year-by-type count",
    "%d rows, total %s" % (len(td), td[-1][-1]), "24 rows, total %d" % own_tot[-1],
    [h.strip() for h in th] == exp_hdr and not bad and len(td) == 24, "mismatching years: %s" % (bad or "none"))

# ---------------------------------------------------------------- write
with open(OUTCSV, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["check_id", "what", "expected_from_tables", "recomputed", "verdict", "note"])
    w.writerows(rows_out)

n_fail = sum(1 for r in rows_out if r[4] != "PASS")
for r in rows_out:
    print(" | ".join(r))
print("checks: %d, FAIL: %d" % (len(rows_out), n_fail))
