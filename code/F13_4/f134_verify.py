"""F13.4 independent verifier: growth and normalised activity from Scopus year series.

Recomputes every figure from the raw inputs (E1 columns EID and Year only, the seven
Scopus year series, their manifest, and the F13.2 T1a check table) and compares the
recomputation with the phase outputs. Written without reading the phase programs.
Writes exactly one file: OUT/phase_F13_4_independent_verification.csv.
"""
import sys; sys.dont_write_bytecode = True

import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np

import os
ROOT = Path(os.environ.get("PROJECT_ROOT", "."))
OUT = ROOT / "outputs" / "dprg_revision_2026" / "phase_F13_4"
EXP = ROOT / "outputs" / "dprg_revision_2026" / "author_exports_2026_10"
E1 = EXP / "scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
F132_T1A = ROOT / "outputs" / "dprg_revision_2026" / "phase_F13_2" / "tables" / "T1a_years.csv"
TAB = OUT / "tables"
FIG = OUT / "figures"
NUMBERS = OUT / "F13_4_numbers.json"
RESULT = OUT / "phase_F13_4_independent_verification.csv"

YEARS = list(range(2003, 2026))
PERIODS = [("2003-2016", 2003, 2016), ("2017-2021", 2017, 2021), ("2022-2025", 2022, 2025)]
SERIES = {
    "KZ_all": "scopus_years_KZ_all.csv",
    "world_topic": "scopus_years_world_topic.csv",
    "world_all": "scopus_years_world_all.csv",
    "UZ_topic": "scopus_years_UZ.csv",
    "AZ_topic": "scopus_years_AZ.csv",
    "BY_topic": "scopus_years_BY.csv",
    "KG_topic": "scopus_years_KG.csv",
}
BRIEF_SUMS = {"KZ_all": 75667, "world_topic": 415133, "world_all": 70937062,
              "UZ_topic": 539, "AZ_topic": 278, "BY_topic": 129, "KG_topic": 51}
COUNTRIES = ["KZ", "UZ", "AZ", "BY", "KG"]

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ORCID_RE = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b")
EID_SHAPE_RE = re.compile(r"2-s2\.0-\d+")
FORBIDDEN_TOKENS = {"eid", "eids", "title", "titles", "author", "authors", "abstract", "abstracts",
                    "reference", "references", "affiliation", "affiliations", "correspondence"}

rows = []


def clip(text, limit=30):
    words = str(text).split()
    return " ".join(words[:limit]) if len(words) > limit else str(text)


def add(cid, what, expected, recomputed, ok, note=""):
    rows.append([cid, clip(what), clip(expected), clip(recomputed), "PASS" if ok else "FAIL", clip(note)])


class Cmp:
    """Collects cell comparisons; numeric ones allow a half-unit tie at the printed precision."""

    def __init__(self):
        self.n = 0
        self.bad = []
        self.ties = 0

    def num(self, label, table_value, value, dp):
        self.n += 1
        s = str(table_value).strip()
        if value is None:
            if s != "":
                self.bad.append(f"{label}:{s}!=blank")
            return
        want = f"{value:.{dp}f}"
        if s == want:
            return
        try:
            t = float(s)
        except ValueError:
            self.bad.append(f"{label}:{s}!={want}")
            return
        if abs(t - value) <= 0.5 * 10 ** (-dp) + 1e-9:
            self.ties += 1
            return
        self.bad.append(f"{label}:{s}!={want}")

    def exact(self, label, table_value, value):
        self.n += 1
        if str(table_value).strip() != str(value):
            self.bad.append(f"{label}:{table_value}!={value}")

    def ok(self):
        return not self.bad and self.n > 0

    def summary(self):
        if self.bad:
            return f"{self.n - len(self.bad)}/{self.n} equal; first mismatches " + "; ".join(self.bad[:3])
        tail = f"; {self.ties} half-unit rounding ties" if self.ties else ""
        return f"{self.n}/{self.n} equal{tail}"


def read_dicts(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def read_raw(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.reader(fh))


def json_vs_csv(json_rows, csv_rows, key):
    """Every CSV cell equals the JSON value (missing JSON key = blank cell)."""
    c = Cmp()
    if len(json_rows) != len(csv_rows):
        c.n += 1
        c.bad.append(f"row count {len(json_rows)}!={len(csv_rows)}")
        return c
    for j, r in zip(json_rows, csv_rows):
        for col, val in r.items():
            jv = j.get(col, "")
            c.exact(f"{r[key]}/{col}", val, "" if jv is None else jv)
    return c


# ---------------------------------------------------------------- inputs
# E1: stream with csv.reader; keep only EID and Year; print nothing from it.
csv.field_size_limit(2 ** 31 - 1)
e1_years = Counter()
e1_eids = []
e1_bad_year = 0
with open(E1, encoding="utf-8-sig", newline="") as fh:
    reader = csv.reader(fh)
    header = [h.strip() for h in next(reader)]
    i_eid = header.index("EID")
    i_year = header.index("Year")
    del header
    for rec in reader:
        if not rec:
            continue
        eid, yr = rec[i_eid].strip(), rec[i_year].strip()
        del rec
        e1_eids.append(eid)
        if yr.isdigit():
            e1_years[int(yr)] += 1
        else:
            e1_bad_year += 1
E1_TOTAL = len(e1_eids)
E1_UNIQUE = len(set(e1_eids))
EID_SET = set(e1_eids)
n = {y: e1_years.get(y, 0) for y in YEARS}

manifest = {m["file"]: m for m in json.loads((EXP / "manifest_year_series.json").read_text(encoding="utf-8"))}
series = {}
series_meta = {}
for name, fname in SERIES.items():
    path = EXP / fname
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    recs = read_dicts(path)
    years_seen = [int(r["year"]) for r in recs]
    series[name] = {int(r["year"]): int(r["documents"]) for r in recs}
    series_meta[name] = (digest, years_seen)

K = series["KZ_all"]
WT = series["world_topic"]
WA = series["world_all"]
topic = {"KZ": n, "UZ": series["UZ_topic"], "AZ": series["AZ_topic"],
         "BY": series["BY_topic"], "KG": series["KG_topic"]}

numbers = json.loads(NUMBERS.read_text(encoding="utf-8"))

# ---------------------------------------------------------------- C01 series digests and sums
for name, fname in SERIES.items():
    digest, years_seen = series_meta[name]
    m = manifest.get(fname, {})
    total = sum(series[name].values())
    ok = (digest == m.get("sha256") and total == BRIEF_SUMS[name] == m.get("sum_of_years")
          and years_seen == YEARS)
    add(f"C01_{name}", f"sha256 and year sum of {fname}",
        f"manifest sha256 {str(m.get('sha256', ''))[:16]}...; sum_of_years {m.get('sum_of_years')}; brief {BRIEF_SUMS[name]}",
        f"sha256 {digest[:16]}...; sum {total}; years {years_seen[0]}-{years_seen[-1]}, {len(years_seen)} rows",
        ok, "full 64-hex digests compared" + ("" if m.get("ui_total") == total else f"; ui_total {m.get('ui_total')} differs"))

c = Cmp()
for name in SERIES:
    c.exact(name, numbers.get("series_sums", {}).get(name), sum(series[name].values()))
add("C01_numbers_sums", "F13_4_numbers.json series_sums equal recomputed series sums",
    "7 series sums in numbers.json", c.summary(), c.ok())

# ---------------------------------------------------------------- C02 T1a
t1a = read_dicts(TAB / "T1a_years.csv")
f132 = read_dicts(F132_T1A)
f132_by_year = {r["year"]: r for r in f132}

ok_e1 = (E1_TOTAL == 841 and E1_UNIQUE == 841 and e1_bad_year == 0
         and set(e1_years) <= set(YEARS) and min(e1_years) == 2003 and max(e1_years) == 2025)
add("C02_E1", "E1 read (EID and Year only): records, unique EIDs, year range",
    "841 records, years 2003-2025",
    f"{E1_TOTAL} rows, {E1_UNIQUE} unique EIDs, years {min(e1_years)}-{max(e1_years)}, {e1_bad_year} unreadable years",
    ok_e1)

c_rec, c_pct, c_ma, c_cum, c_f132 = Cmp(), Cmp(), Cmp(), Cmp(), Cmp()
if [r["year"] for r in t1a] != [str(y) for y in YEARS]:
    c_rec.n += 1
    c_rec.bad.append("T1a year list is not 2003-2025")
cum = 0
for r in t1a:
    y = int(r["year"])
    cum += n.get(y, 0)
    c_rec.exact(y, r["records"], n.get(y, 0))
    c_pct.num(y, r["pct_of_total"], 100.0 * n.get(y, 0) / E1_TOTAL, 1)
    ma = None if y in (2003, 2025) else (n[y - 1] + n[y] + n[y + 1]) / 3.0
    c_ma.num(y, r["moving_average_3y_centred"], ma, 2)
    c_cum.exact(y, r["cumulative"], cum)
    fr = f132_by_year.get(str(y), {})
    c_f132.exact(f"{y}/F13.2 records", fr.get("records"), n.get(y, 0))
    c_f132.exact(f"{y}/F13.2 cumulative", fr.get("cumulative"), cum)
    c_f132.exact(f"{y}/column F13_2_T1a_records", r["F13_2_T1a_records"], fr.get("records"))
    c_f132.exact(f"{y}/equal_F13_2", r["equal_F13_2"], 1)
tot = f132_by_year.get("2003-2025", {})
c_f132.exact("F13.2 total", tot.get("records"), 841)
add("C02_T1a_records", "T1a records per year equal E1 Year counts",
    "23 years 2003-2025; 2024=146, 2025=245, total 841", c_rec.summary(), c_rec.ok())
add("C02_T1a_pct", "T1a pct_of_total (1 dp) = records / 841", "23 values, e.g. 2025=29.1",
    c_pct.summary(), c_pct.ok())
add("C02_T1a_ma", "T1a centred 3-year moving average (2 dp), blank for 2003 and 2025",
    "23 cells, e.g. 2024=156.67", c_ma.summary(), c_ma.ok())
add("C02_T1a_cum", "T1a cumulative records", "23 values ending at 841", c_cum.summary(), c_cum.ok())
add("C02_T1a_F13_2", "T1a equals phase_F13_2 T1a (records, cumulative, copy column, equal flag)",
    "F13.2 T1a 23 years plus total 841", c_f132.summary(), c_f132.ok())
add("C02_numbers_T1a", "numbers.json T1a_equal_F13_2 flag", "true",
    str(numbers.get("T1a_equal_F13_2")).lower() + f"; recomputed equality {c_f132.ok()}",
    numbers.get("T1a_equal_F13_2") is True and c_f132.ok())

# T1b
t1b = read_dicts(TAB / "T1b_periods.csv")
t1b_by = {r["period"]: r for r in t1b}
prev = None
period_vals = {}
for label, a, b in PERIODS + [("2003-2025", 2003, 2025)]:
    yrs = b - a + 1
    recs = sum(n[y] for y in range(a, b + 1))
    mean = recs / yrs
    period_vals[label] = (yrs, recs, mean)
    r = t1b_by.get(label, {})
    c = Cmp()
    c.exact("years", r.get("years"), yrs)
    c.exact("records", r.get("records"), recs)
    c.num("mean", r.get("mean_per_year"), mean, 2)
    if label != "2003-2025" and prev is not None:
        rr, rm = recs / prev[1], mean / prev[2]
        c.num("ratio_records", r.get("ratio_records_to_previous"), rr, 2)
        c.num("ratio_mean", r.get("ratio_mean_to_previous"), rm, 2)
        rec_txt = f"records {recs}, mean {mean:.2f}, ratios {rr:.2f}/{rm:.2f}"
    else:
        c.num("ratio_records", r.get("ratio_records_to_previous"), None, 2)
        c.num("ratio_mean", r.get("ratio_mean_to_previous"), None, 2)
        rec_txt = f"records {recs}, mean {mean:.2f}, ratios blank"
    add(f"C02_T1b_{label}", f"T1b row {label}: years, records, mean per year, ratios to previous",
        f"years {r.get('years')}, records {r.get('records')}, mean {r.get('mean_per_year')}, "
        f"ratios {r.get('ratio_records_to_previous') or 'blank'}/{r.get('ratio_mean_to_previous') or 'blank'}",
        rec_txt + "; " + c.summary(), c.ok())
    if label != "2003-2025":
        prev = (yrs, recs, mean)
c = json_vs_csv(numbers.get("T1b", []), t1b, "period")
add("C02_numbers_T1b", "numbers.json T1b equals T1b_periods.csv", "4 rows", c.summary(), c.ok())

# ---------------------------------------------------------------- C03 T1c log-linear fits
first3 = min(y for y in YEARS if n[y] >= 3)
add("C03_first_year_3", "first year with at least 3 records (start of first window)", "2011 (numbers.json "
    f"{numbers.get('first_year_with_3')})", str(first3), first3 == 2011 == numbers.get("first_year_with_3"))


def ols(a, b):
    pts = [(y - a, math.log(n[y])) for y in range(a, b + 1) if n[y] > 0]
    zeros = sum(1 for y in range(a, b + 1) if n[y] == 0)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    xm, ym = sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - xm) ** 2 for x in xs)
    sxy = sum((x - xm) * (v - ym) for x, v in zip(xs, ys))
    slope = sxy / sxx
    icpt = ym - slope * xm
    ss_res = sum((v - (icpt + slope * x)) ** 2 for x, v in zip(xs, ys))
    ss_tot = sum((v - ym) ** 2 for v in ys)
    return dict(n=len(pts), zeros=zeros, a=icpt, b=slope, r2=1 - ss_res / ss_tot,
                g=(math.exp(slope) - 1) * 100, dt=math.log(2) / slope)


t1c = read_dicts(TAB / "T1c_loglinear_fit.csv")
for prefix, a, b in [("2011-2025", 2011, 2025), ("2017-2025", 2017, 2025), ("2011-2024", 2011, 2024)]:
    r = next((x for x in t1c if x["window"].startswith(prefix)), {})
    f = ols(a, b)
    c = Cmp()
    c.exact("years_used", r.get("years_used"), f["n"])
    c.exact("zeros", r.get("zero_years_excluded"), f["zeros"])
    c.exact("t_origin", r.get("t_origin"), a)
    c.num("a", r.get("a"), f["a"], 4)
    c.num("b", r.get("b"), f["b"], 4)
    c.num("growth", r.get("annual_growth_pct"), f["g"], 1)
    c.num("doubling", r.get("doubling_time_years"), f["dt"], 2)
    c.num("R2", r.get("r_squared"), f["r2"], 4)
    add(f"C03_T1c_{prefix}", f"T1c OLS ln(n) on t=year-{a}, window {prefix}, zero years excluded",
        f"b {r.get('b')}, R2 {r.get('r_squared')}, growth {r.get('annual_growth_pct')}%, doubling {r.get('doubling_time_years')}, a {r.get('a')}, years {r.get('years_used')}",
        f"b {f['b']:.4f}, R2 {f['r2']:.4f}, growth {f['g']:.1f}%, doubling {f['dt']:.2f}, a {f['a']:.4f}, years {f['n']}; {c.summary()}",
        c.ok())
c = json_vs_csv(numbers.get("T1c", []), t1c, "window")
add("C03_numbers_T1c", "numbers.json T1c equals T1c_loglinear_fit.csv", "3 windows", c.summary(), c.ok())

# T1d
t1d = read_dicts(TAB / "T1d_recent_weight.csv")
recent = n[2024] + n[2025]
want_t1d = [
    (100.0 * recent / E1_TOTAL, 1, f"{recent} of {E1_TOTAL}"),
    (n[2025] / n[2020], 2, f"{n[2025]} / {n[2020]}"),
    (n[2025] / n[2015], 2, f"{n[2025]} / {n[2015]}"),
]
c = Cmp()
if len(t1d) != 3:
    c.n += 1
    c.bad.append(f"{len(t1d)} rows")
for r, (val, dp, det) in zip(t1d, want_t1d):
    c.num(r["measure"][:20], r["value"], val, dp)
    c.exact(r["measure"][:20] + " detail", r["detail"], det)
add("C03_T1d", "T1d: share of 2024-2025 in 841; 2025/2020; 2025/2015 (values and detail strings)",
    " | ".join(f"{r['value']} ({r['detail']})" for r in t1d),
    f"{want_t1d[0][0]:.1f}, {want_t1d[1][0]:.2f}, {want_t1d[2][0]:.2f}; {c.summary()}", c.ok())
c = json_vs_csv(numbers.get("T1d", []), t1d, "measure")
add("C03_numbers_T1d", "numbers.json T1d equals T1d_recent_weight.csv", "3 rows", c.summary(), c.ok())

# ---------------------------------------------------------------- C04 activity index
t2a = read_dicts(TAB / "T2a_normalised_by_year.csv")
c_cnt, c_sh, c_ai = Cmp(), Cmp(), Cmp()
if [r["year"] for r in t2a] != [str(y) for y in YEARS]:
    c_cnt.n += 1
    c_cnt.bad.append("T2a year list is not 2003-2025")
ai_year = {}
for r in t2a:
    y = int(r["year"])
    c_cnt.exact(f"{y}/topic_KZ", r["topic_KZ"], n[y])
    c_cnt.exact(f"{y}/all_KZ", r["all_KZ"], K[y])
    c_cnt.exact(f"{y}/topic_world", r["topic_world"], WT[y])
    c_cnt.exact(f"{y}/all_world", r["all_world"], WA[y])
    c_sh.num(f"{y}/KZ", r["share_topic_in_KZ_permille"], 1000.0 * n[y] / K[y], 3)
    c_sh.num(f"{y}/world", r["share_topic_in_world_permille"], 1000.0 * WT[y] / WA[y], 3)
    ai_year[y] = (n[y] / K[y]) / (WT[y] / WA[y])
    c_ai.num(y, r["activity_index"], ai_year[y], 3)
add("C04_T2a_counts", "T2a counts per year equal E1 and the KZ_all, world_topic, world_all series",
    "23 years x 4 counts", c_cnt.summary(), c_cnt.ok())
add("C04_T2a_shares", "T2a per-mille shares (3 dp): topic in KZ and topic in world",
    "46 values, e.g. 2025 21.764 / 13.026", c_sh.summary(), c_sh.ok())
add("C04_T2a_AI", "T2a activity index by year (3 dp) = share KZ / share world",
    "23 values, e.g. 2003 2.210, 2025 1.671", c_ai.summary(), c_ai.ok())

t2c = read_dicts(TAB / "T2c_shares_of_world.csv")
t2c_by = {r["year_or_window"]: r for r in t2c}
t2a_by = {r["year"]: r for r in t2a}
c_eq, c_y = Cmp(), Cmp()
for y in YEARS:
    r = t2c_by.get(str(y), {})
    c_eq.exact(y, r.get("ratio_of_shares"), t2a_by.get(str(y), {}).get("activity_index"))
    c_y.exact(f"{y}/topic_KZ", r.get("topic_KZ"), n[y])
    c_y.exact(f"{y}/topic_world", r.get("topic_world"), WT[y])
    c_y.exact(f"{y}/all_KZ", r.get("all_KZ"), K[y])
    c_y.exact(f"{y}/all_world", r.get("all_world"), WA[y])
    c_y.num(f"{y}/of topic", r.get("KZ_share_of_world_topic_permille"), 1000.0 * n[y] / WT[y], 4)
    c_y.num(f"{y}/of all", r.get("KZ_share_of_world_all_permille"), 1000.0 * K[y] / WA[y], 4)
    c_y.num(f"{y}/ratio", r.get("ratio_of_shares"), (n[y] / WT[y]) / (K[y] / WA[y]), 3)
add("C04_T2c_eq_T2a", "T2c ratio_of_shares equals T2a activity_index for every year (cell text)",
    "23 equal cells", c_eq.summary(), c_eq.ok())
add("C04_T2c_years", "T2c per-year counts, KZ share of world topic and of world all (per mille, 4 dp), ratio (3 dp)",
    "23 years x 7 cells", c_y.summary(), c_y.ok())


def window_stats(years):
    s_n = sum(n[y] for y in years)
    s_k = sum(K[y] for y in years)
    s_wt = sum(WT[y] for y in years)
    s_wa = sum(WA[y] for y in years)
    expct = sum(K[y] * WT[y] / WA[y] for y in years)
    return dict(n=s_n, k=s_k, wt=s_wt, wa=s_wa, shk=1000.0 * s_n / s_k, shw=1000.0 * s_wt / s_wa,
                ai=(s_n / s_k) / (s_wt / s_wa), exp=expct, ais=s_n / expct)


c = Cmp()
for label, a, b in PERIODS + [("2003-2025", 2003, 2025)]:
    w = window_stats(range(a, b + 1))
    r = t2c_by.get(label, {})
    c.exact(f"{label}/topic_KZ", r.get("topic_KZ"), w["n"])
    c.exact(f"{label}/topic_world", r.get("topic_world"), w["wt"])
    c.exact(f"{label}/all_KZ", r.get("all_KZ"), w["k"])
    c.exact(f"{label}/all_world", r.get("all_world"), w["wa"])
    c.num(f"{label}/of topic", r.get("KZ_share_of_world_topic_permille"), 1000.0 * w["n"] / w["wt"], 4)
    c.num(f"{label}/of all", r.get("KZ_share_of_world_all_permille"), 1000.0 * w["k"] / w["wa"], 4)
    c.num(f"{label}/ratio", r.get("ratio_of_shares"), w["ai"], 3)
add("C04_T2c_windows", "T2c window rows (three periods and 2003-2025): sums, shares, ratio = window AI",
    "4 windows x 7 cells", c.summary(), c.ok())

# bootstrap (optional re-run): default_rng(42) afresh per window
R = 1000


def boot_ai(w):
    rng = np.random.default_rng(42)
    kk = rng.binomial(w["k"], w["n"] / w["k"], size=R)
    ww = rng.binomial(w["wa"], w["wt"] / w["wa"], size=R)
    ai = (kk / w["k"]) / (ww / w["wa"])
    lo, hi = np.percentile(ai, [2.5, 97.5])
    return float(lo), float(hi)


def boot_std(years, variant):
    years = list(years)
    rng = np.random.default_rng(42)
    kd, wd = {}, {}
    if variant == "per-year KZ then world":
        for y in years:
            kd[y] = rng.binomial(K[y], n[y] / K[y], size=R)
            wd[y] = rng.binomial(WA[y], WT[y] / WA[y], size=R)
    else:  # all KZ years first, then all world years
        for y in years:
            kd[y] = rng.binomial(K[y], n[y] / K[y], size=R)
        for y in years:
            wd[y] = rng.binomial(WA[y], WT[y] / WA[y], size=R)
    num = sum(kd[y] for y in years)
    den = sum(K[y] * wd[y] / WA[y] for y in years)
    lo, hi = np.percentile(num / den, [2.5, 97.5])
    return float(lo), float(hi)


STD_VARIANTS = ["per-year KZ then world", "all KZ years then all world years"]
boot_rows = []  # (table, label, row, w, years)


def check_windows(table_name, csv_rows, windows, cid_prefix):
    for prefix, a, b in windows:
        r = next((x for x in csv_rows if x["window"].startswith(prefix)), {})
        years = range(a, b + 1)
        w = window_stats(years)
        c = Cmp()
        c.exact("topic_KZ", r.get("topic_KZ"), w["n"])
        c.exact("all_KZ", r.get("all_KZ"), w["k"])
        c.exact("topic_world", r.get("topic_world"), w["wt"])
        c.exact("all_world", r.get("all_world"), w["wa"])
        c.num("share KZ", r.get("share_topic_in_KZ_permille"), w["shk"], 3)
        c.num("share world", r.get("share_topic_in_world_permille"), w["shw"], 3)
        c.num("AI", r.get("activity_index"), w["ai"], 3)
        c.num("expected", r.get("expected_topic_KZ_by_year"), w["exp"], 1)
        c.num("AI std", r.get("ai_year_standardised"), w["ais"], 3)
        c.exact("replicates", r.get("replicates"), R)
        add(f"{cid_prefix}_{prefix}", f"{table_name} window {r.get('window', prefix)}: sums, per-mille shares, AI, year-standardised AI",
            f"AI {r.get('activity_index')}; std AI {r.get('ai_year_standardised')}; expected {r.get('expected_topic_KZ_by_year')}; "
            f"shares {r.get('share_topic_in_KZ_permille')}/{r.get('share_topic_in_world_permille')}",
            f"AI {w['ai']:.3f}; std AI {w['ais']:.3f}; expected {w['exp']:.1f}; shares {w['shk']:.3f}/{w['shw']:.3f}; {c.summary()}",
            c.ok())
        boot_rows.append((table_name, prefix, r, w, years))


t2b = read_dicts(TAB / "T2b_activity_index_periods.csv")
t2d = read_dicts(TAB / "T2d_activity_index_windows.csv")
check_windows("T2b", t2b, PERIODS + [("2003-2025", 2003, 2025)], "C04_T2b")
check_windows("T2d", t2d, [("2003-2025", 2003, 2025), ("2017-2025", 2017, 2025),
                           ("2022-2025", 2022, 2025), ("2003-2024", 2003, 2024)], "C04_T2d")
if len(t2b) != 4 or len(t2d) != 4:
    add("C04_rowcount", "T2b and T2d row counts", "4 and 4", f"{len(t2b)} and {len(t2d)}", False)

c_ci = Cmp()
for table_name, prefix, r, w, years in boot_rows:
    lo, hi = boot_ai(w)
    c_ci.num(f"{table_name} {prefix} low", r.get("ci95_low"), lo, 3)
    c_ci.num(f"{table_name} {prefix} high", r.get("ci95_high"), hi, 3)
add("C04_bootstrap_AI", "Re-run AI 95% interval: default_rng(42) per window, Binomial(allKZ) then Binomial(worldall), 1000 reps, linear 2.5/97.5",
    "8 window intervals in T2b and T2d (16 bounds)", c_ci.summary(), c_ci.ok())

std_result = None
for variant in STD_VARIANTS:
    c_std = Cmp()
    for table_name, prefix, r, w, years in boot_rows:
        lo, hi = boot_std(years, variant)
        c_std.num(f"{table_name} {prefix} low", r.get("std_ci95_low"), lo, 3)
        c_std.num(f"{table_name} {prefix} high", r.get("std_ci95_high"), hi, 3)
    if c_std.ok():
        std_result = (variant, c_std)
        break
    if std_result is None or len(c_std.bad) < len(std_result[1].bad):
        std_result = (variant, c_std)
STD_BOOT = std_result  # reported below only if reproduced (the draw order is not fixed by the method)
if STD_BOOT[1].ok():
    add("C04_bootstrap_std", "Re-run year-standardised AI 95% interval, per-year binomial resampling, own default_rng(42)",
        "8 window intervals (16 bounds)", STD_BOOT[1].summary(), True, f"draw order used: {STD_BOOT[0]}")

c = json_vs_csv(numbers.get("T2b", []), t2b, "window")
add("C04_numbers_T2b", "numbers.json T2b equals T2b_activity_index_periods.csv", "4 windows x 15 cells",
    c.summary(), c.ok())
c = json_vs_csv(numbers.get("T2d", []), t2d, "window")
add("C04_numbers_T2d", "numbers.json T2d equals T2d_activity_index_windows.csv", "4 windows x 15 cells",
    c.summary(), c.ok())

# ---------------------------------------------------------------- C05 comparators
t3a = read_dicts(TAB / "T3a_comparators_by_year.csv")
t3a_by = {r["year"]: r for r in t3a}
c = Cmp()
for y in YEARS:
    r = t3a_by.get(str(y), {})
    for ctry in COUNTRIES:
        c.exact(f"{y}/{ctry}", r.get(ctry), topic[ctry][y])
    c.exact(f"{y}/sum_five", r.get("sum_five"), sum(topic[x][y] for x in COUNTRIES))
add("C05_T3a_years", "T3a topic counts per year for KZ (E1), UZ, AZ, BY, KG and sum of five",
    "23 years x 6 cells", c.summary(), c.ok())
c = Cmp()
r = t3a_by.get("2003-2025", {})
totals = {x: sum(topic[x].values()) for x in COUNTRIES}
for ctry in COUNTRIES:
    c.exact(ctry, r.get(ctry), totals[ctry])
    c.exact(f"numbers.json totals {ctry}", numbers.get("totals", {}).get(ctry), totals[ctry])
c.exact("sum_five", r.get("sum_five"), sum(totals.values()))
c.exact("UZ series sum", totals["UZ"], BRIEF_SUMS["UZ_topic"])
c.exact("AZ series sum", totals["AZ"], BRIEF_SUMS["AZ_topic"])
c.exact("BY series sum", totals["BY"], BRIEF_SUMS["BY_topic"])
c.exact("KG series sum", totals["KG"], BRIEF_SUMS["KG_topic"])
add("C05_T3a_totals", "T3a total row equals series sums (KZ from E1) and numbers.json totals",
    f"KZ {r.get('KZ')}, UZ {r.get('UZ')}, AZ {r.get('AZ')}, BY {r.get('BY')}, KG {r.get('KG')}, sum {r.get('sum_five')}",
    f"KZ {totals['KZ']}, UZ {totals['UZ']}, AZ {totals['AZ']}, BY {totals['BY']}, KG {totals['KG']}; {c.summary()}",
    c.ok())

t3b = read_dicts(TAB / "T3b_comparators_by_period.csv")
for label, a, b in PERIODS + [("2003-2025", 2003, 2025)]:
    r = next((x for x in t3b if x["period"] == label), {})
    recs = {x: sum(topic[x][y] for y in range(a, b + 1)) for x in COUNTRIES}
    s5 = sum(recs.values())
    c = Cmp()
    for ctry in COUNTRIES:
        c.exact(f"{ctry} records", r.get(f"{ctry}_records"), recs[ctry])
        c.num(f"{ctry} share", r.get(f"{ctry}_share_pct"), 100.0 * recs[ctry] / s5, 1)
    c.exact("sum_five", r.get("sum_five"), s5)
    add(f"C05_T3b_{label}", f"T3b {label}: records per country and percent share of the five (1 dp)",
        "shares " + "/".join(str(r.get(f"{x}_share_pct")) for x in COUNTRIES) + f"; sum {r.get('sum_five')}",
        "shares " + "/".join(f"{100.0 * recs[x] / s5:.1f}" for x in COUNTRIES) + f"; sum {s5}; {c.summary()}",
        c.ok())

t3c = read_dicts(TAB / "T3c_growth_by_country.csv")
c = Cmp()
for ctry in COUNTRIES:
    r = next((x for x in t3c if x["country"] == ctry), {})
    r1 = sum(topic[ctry][y] for y in range(2017, 2022))
    r2 = sum(topic[ctry][y] for y in range(2022, 2026))
    c.exact(f"{ctry} r1", r.get("records_2017_2021"), r1)
    c.exact(f"{ctry} r2", r.get("records_2022_2025"), r2)
    c.num(f"{ctry} ratio", r.get("ratio_records"), r2 / r1, 2)
    c.num(f"{ctry} m1", r.get("mean_2017_2021"), r1 / 5, 2)
    c.num(f"{ctry} m2", r.get("mean_2022_2025"), r2 / 4, 2)
    c.num(f"{ctry} ratio means", r.get("ratio_means"), (r2 / 4) / (r1 / 5), 2)
add("C05_T3c", "T3c growth 2017-2021 to 2022-2025 per country: records, ratio, annual means (5 and 4 years), ratio of means",
    "5 countries x 6 cells; ratio_means " + "/".join(x["ratio_means"] for x in t3c),
    c.summary(), c.ok())

t3d = read_dicts(TAB / "T3d_without_2025.csv")
tot24 = {x: sum(topic[x][y] for y in range(2003, 2025)) for x in COUNTRIES}
r2224 = {x: sum(topic[x][y] for y in range(2022, 2025)) for x in COUNTRIES}
c = Cmp()
for ctry in COUNTRIES:
    r = next((x for x in t3d if x["country"] == ctry), {})
    r1 = sum(topic[ctry][y] for y in range(2017, 2022))
    c.exact(f"{ctry} total", r.get("total_2003_2025"), totals[ctry])
    c.exact(f"{ctry} 2025", r.get("records_2025"), topic[ctry][2025])
    c.num(f"{ctry} share2025", r.get("share_2025_pct"), 100.0 * topic[ctry][2025] / totals[ctry], 1)
    c.exact(f"{ctry} total24", r.get("total_2003_2024"), tot24[ctry])
    c.num(f"{ctry} share5 03-24", r.get("share_of_five_2003_2024_pct"), 100.0 * tot24[ctry] / sum(tot24.values()), 1)
    c.exact(f"{ctry} 22-24", r.get("records_2022_2024"), r2224[ctry])
    c.num(f"{ctry} share5 22-24", r.get("share_of_five_2022_2024_pct"), 100.0 * r2224[ctry] / sum(r2224.values()), 1)
    c.num(f"{ctry} ratio means", r.get("ratio_means_2017_2021_to_2022_2024"), (r2224[ctry] / 3) / (r1 / 5), 2)
uz = next((x for x in t3d if x["country"] == "UZ"), {})
c.exact("UZ 258 of 539", f"{uz.get('records_2025')} of {uz.get('total_2003_2025')}", "258 of 539")
add("C05_T3d", "T3d per country: 2025 share of total, totals and shares without 2025, 2022-2024 means ratio",
    f"5 countries x 8 cells; UZ {uz.get('records_2025')} of {uz.get('total_2003_2025')} ({uz.get('share_2025_pct')}%)",
    f"UZ {topic['UZ'][2025]} of {totals['UZ']}; {c.summary()}", c.ok())

for key, rows_csv, idcol in [("T3b", t3b, "period"), ("T3c", t3c, "country"), ("T3d", t3d, "country")]:
    c = json_vs_csv(numbers.get(key, []), rows_csv, idcol)
    add(f"C05_numbers_{key}", f"numbers.json {key} equals the {key} CSV", f"{len(rows_csv)} rows", c.summary(), c.ok())

# ---------------------------------------------------------------- C06 R13 scan
scan_files = []
for folder in (TAB, FIG):
    for pattern in ("*.md", "*.csv", "*.json"):
        scan_files.extend(sorted(folder.glob(pattern)))
scan_files.append(NUMBERS)
texts = {p: p.read_text(encoding="utf-8-sig") for p in scan_files}
n_md = sum(1 for p in scan_files if p.suffix == ".md")
n_csv = sum(1 for p in scan_files if p.suffix == ".csv")
n_json = sum(1 for p in scan_files if p.suffix == ".json")
scope = f"{len(scan_files)} files ({n_csv} csv, {n_md} md, {n_json} json)"

email_hits = [p.name for p, t in texts.items() if EMAIL_RE.search(t)]
orcid_hits = [p.name for p, t in texts.items() if ORCID_RE.search(t)]
add("C06_email", "No e-mail shape in any output text (tables, figures, numbers.json)", "0 files with a hit",
    f"{len(email_hits)} files with a hit in {scope}" + (": " + ", ".join(email_hits[:3]) if email_hits else ""),
    not email_hits)
add("C06_orcid", "No ORCID shape in any output text", "0 files with a hit",
    f"{len(orcid_hits)} files with a hit in {scope}" + (": " + ", ".join(orcid_hits[:3]) if orcid_hits else ""),
    not orcid_hits)


def forbidden(name):
    toks = set(t.lower() for t in re.split(r"[^A-Za-z0-9]+", str(name)) if t)
    return bool(toks & FORBIDDEN_TOKENS)


def json_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from json_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from json_keys(v)


col_hits = []
n_cols = 0
for p, t in texts.items():
    names = []
    if p.suffix == ".csv":
        raw = read_raw(p)
        names = raw[0] if raw else []
    elif p.suffix == ".md":
        lines = t.splitlines()
        for i in range(len(lines) - 1):
            if lines[i].lstrip().startswith("|") and re.match(r"^\s*\|\s*:?-{3,}", lines[i + 1]):
                names.extend(cell.strip() for cell in lines[i].strip().strip("|").split("|"))
    elif p.suffix == ".json":
        names = list(json_keys(json.loads(t)))
    n_cols += len(names)
    col_hits.extend(f"{p.name}:{x}" for x in names if forbidden(x))
add("C06_columns", "No column or key named like EID, Title, Authors, Abstract, References, Affiliations, Correspondence Address",
    "0 forbidden names", f"{len(col_hits)} hits among {n_cols} CSV headers, md table headers and JSON keys"
    + (": " + ", ".join(col_hits[:3]) if col_hits else ""), not col_hits)

long_cells = []
n_cells = 0
for p in scan_files:
    if p.suffix != ".csv":
        continue
    for ri, rec in enumerate(read_raw(p)):
        for ci, cell in enumerate(rec):
            n_cells += 1
            if len(cell.split()) > 30:
                long_cells.append(f"{p.name} r{ri} c{ci}")
add("C06_cell_words", "No CSV cell over 30 words in output CSVs", "0 long cells",
    f"{len(long_cells)} of {n_cells} cells in {n_csv} CSVs over 30 words" + (": " + ", ".join(long_cells[:3]) if long_cells else ""),
    not long_cells)

eid_hits = [p.name for p, t in texts.items() if any(e and e in t for e in EID_SET)]
shape_hits = [p.name for p, t in texts.items() if EID_SHAPE_RE.search(t)]
add("C06_eid", "No E1 EID value (nor any 2-s2.0- shape) appears in any output text", "0 files",
    f"{len(eid_hits)} files with an E1 EID, {len(shape_hits)} with the 2-s2.0- shape; {len(EID_SET)} EIDs searched",
    not eid_hits and not shape_hits)

# ---------------------------------------------------------------- C07 figure data
fig = read_dicts(FIG / "Fig_normalised_growth.csv")
t3a_years = {r["year"]: r for r in t3a}
c = Cmp()
if [r["year"] for r in fig] != [str(y) for y in YEARS]:
    c.n += 1
    c.bad.append("figure year list is not 2003-2025")
for r in fig:
    y = int(r["year"])
    ta = t2a_by.get(str(y), {})
    tb = t3a_years.get(str(y), {})
    c.exact(f"{y}/KZ_topic", r["KZ_topic_records"], n[y])
    c.exact(f"{y}/KZ_topic vs T2a", r["KZ_topic_records"], ta.get("topic_KZ"))
    c.exact(f"{y}/KZ_all", r["KZ_all_records"], K[y])
    c.exact(f"{y}/KZ_all vs T2a", r["KZ_all_records"], ta.get("all_KZ"))
    c.num(f"{y}/share", r["KZ_share_permille"], 1000.0 * n[y] / K[y], 3)
    c.exact(f"{y}/share vs T2a", r["KZ_share_permille"], ta.get("share_topic_in_KZ_permille"))
    for ctry in COUNTRIES:
        c.exact(f"{y}/{ctry}", r[ctry], topic[ctry][y])
        c.exact(f"{y}/{ctry} vs T3a", r[ctry], tb.get(ctry))
add("C07_figure_data", "Fig_normalised_growth.csv equals recomputation and T2a/T3a: KZ records, all KZ, share per mille, five countries",
    "23 years x 16 comparisons", c.summary(), c.ok())

# ---------------------------------------------------------------- write result
for rec in rows:
    for cell in rec:
        assert len(str(cell).split()) <= 30, rec
        assert not EMAIL_RE.search(str(cell)) and not ORCID_RE.search(str(cell)), rec
        assert not EID_SHAPE_RE.search(str(cell)), rec
with open(RESULT, "w", encoding="utf-8", newline="") as fh:
    wr = csv.writer(fh)
    wr.writerow(["check_id", "what", "expected_from_tables", "recomputed", "verdict", "note"])
    wr.writerows(rows)

n_pass = sum(1 for r in rows if r[4] == "PASS")
n_fail = sum(1 for r in rows if r[4] == "FAIL")
print(f"rows {len(rows)}: PASS {n_pass}, FAIL {n_fail}")
for r in rows:
    if r[4] == "FAIL":
        print("FAIL", r[0], "|", r[3])
if not STD_BOOT[1].ok():
    print("std bootstrap not reproduced; closest variant:", STD_BOOT[0], "|", STD_BOOT[1].summary())
else:
    print("std bootstrap reproduced with variant:", STD_BOOT[0])
print("written", RESULT.name)
