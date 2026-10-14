import sys
sys.dont_write_bytecode = True

# F13.4b independent verifier: recomputes the activity index of five countries
# from the Scopus year series and E1 (EID, Year only) and compares with the
# phase tables. Writes only phase_F13_4b_independent_verification.csv.

import csv
import json
import re
import hashlib
from pathlib import Path
from collections import Counter

import numpy as np

import os
ROOT = Path(os.environ.get("PROJECT_ROOT", "."))
DR = ROOT / "outputs" / "dprg_revision_2026"
OUT = DR / "phase_F13_4b"
EXP = DR / "author_exports_2026_10"
F134T = DR / "phase_F13_4" / "tables"
E1 = EXP / "scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
RESULT = OUT / "phase_F13_4b_independent_verification.csv"

YEARS = list(range(2003, 2026))
COUNTRIES = ["KZ", "UZ", "AZ", "BY", "KG"]
T4A_WINDOWS = [(2003, 2016), (2017, 2021), (2022, 2025), (2003, 2025), (2017, 2025)]
T4D_WINDOWS = [(2003, 2024), (2017, 2024), (2022, 2024)]
FIG_WINDOWS = [(2003, 2016), (2017, 2021), (2022, 2025)]
REPS = 1000
SEED = 42

EXPECTED_SUMS = {
    "scopus_years_KZ_all.csv": 75667,
    "scopus_years_world_topic.csv": 415133,
    "scopus_years_world_all.csv": 70937062,
    "scopus_years_UZ.csv": 539,
    "scopus_years_AZ.csv": 278,
    "scopus_years_BY.csv": 129,
    "scopus_years_KG.csv": 51,
    "scopus_years_UZ_all.csv": 47902,
    "scopus_years_AZ_all.csv": 36549,
    "scopus_years_BY_all.csv": 49270,
    "scopus_years_KG_all.csv": 8732,
}

results = []


def add(cid, what, expected, recomputed, ok, note=""):
    results.append([cid, what, str(expected), str(recomputed), "PASS" if ok else "FAIL", note])


def read_dicts(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))


def read_series(path):
    d = {}
    for r in read_dicts(path):
        d[int(r["year"])] = int(r["documents"])
    return d


def fmt(x, dp):
    return f"{x:.{dp}f}"


def wname(lo, hi):
    return f"{lo}-{hi}"


def window_years(lo, hi):
    return [y for y in YEARS if lo <= y <= hi]


# ---------------------------------------------------------------- C01 inputs
manifest = json.loads((EXP / "manifest_year_series.json").read_text(encoding="utf-8"))
man_files = [e["file"] for e in manifest]
add("C01-00", "manifest_year_series.json lists the eleven expected series files",
    "11 entries: " + str(len(EXPECTED_SUMS)) + " named files",
    f"{len(manifest)} entries; names match: {sorted(man_files) == sorted(EXPECTED_SUMS)}",
    len(manifest) == 11 and sorted(man_files) == sorted(EXPECTED_SUMS))

series = {}
for i, e in enumerate(manifest, 1):
    fn = e["file"]
    p = EXP / fn
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    s = read_series(p)
    tot = sum(s.values())
    series[fn] = s
    years_ok = sorted(s) == YEARS
    exp_sum = EXPECTED_SUMS.get(fn)
    ok = (sha == e["sha256"] and tot == exp_sum == e["sum_of_years"] == e["ui_total"] and years_ok)
    note = ""
    if not ok:
        bad = []
        if sha != e["sha256"]:
            bad.append("sha256")
        if tot != exp_sum or tot != e["sum_of_years"]:
            bad.append("sum")
        if tot != e["ui_total"]:
            bad.append("ui_total")
        if not years_ok:
            bad.append("years not 2003-2025")
        note = "mismatch: " + ", ".join(bad)
    add(f"C01-{i:02d}", f"{fn}: sha256 and sum of years vs manifest",
        f"sha256 {e['sha256']}; sum {exp_sum}; manifest sum {e['sum_of_years']}",
        f"sha256 {sha}; sum {tot}; years 2003-2025 {years_ok}", ok, note)

# E1: only EID and Year (R13)
csv.field_size_limit(2**31 - 1)
kz_topic_counter = Counter()
eids = set()
n_e1 = 0
bad_year = 0
with open(E1, encoding="utf-8-sig", newline="") as f:
    rd = csv.reader(f)
    hdr = next(rd)
    i_eid = hdr.index("EID")
    i_year = hdr.index("Year")
    for row in rd:
        if not row:
            continue
        eid = row[i_eid]
        yr = row[i_year]
        row = None
        n_e1 += 1
        eids.add(eid)
        try:
            y = int(yr)
        except ValueError:
            bad_year += 1
            continue
        if y not in YEARS:
            bad_year += 1
        kz_topic_counter[y] += 1
kz_topic = {y: kz_topic_counter.get(y, 0) for y in YEARS}
add("C01-12", "E1 (EID, Year only): KZ topic records per year, 2003-2025",
    "841 records, all years 2003-2025",
    f"{n_e1} records; {len(eids)} distinct EIDs; {bad_year} outside 2003-2025; sum by year {sum(kz_topic.values())}",
    n_e1 == 841 and len(eids) == 841 and bad_year == 0 and sum(kz_topic.values()) == 841)

topic = {"KZ": kz_topic,
         "UZ": series["scopus_years_UZ.csv"], "AZ": series["scopus_years_AZ.csv"],
         "BY": series["scopus_years_BY.csv"], "KG": series["scopus_years_KG.csv"]}
alls = {"KZ": series["scopus_years_KZ_all.csv"],
        "UZ": series["scopus_years_UZ_all.csv"], "AZ": series["scopus_years_AZ_all.csv"],
        "BY": series["scopus_years_BY_all.csv"], "KG": series["scopus_years_KG_all.csv"]}
wt = series["scopus_years_world_topic.csv"]
wa = series["scopus_years_world_all.csv"]


# ---------------------------------------------------------------- computation
def boot_crude(n, N, m, M):
    rng = np.random.default_rng(SEED)
    a = rng.binomial(N, n / N, REPS)
    b = rng.binomial(M, m / M, REPS)
    r = (a / N) / (b / M)
    lo, hi = np.percentile(r, [2.5, 97.5])
    return float(lo), float(hi)


def boot_std(c, ys, interleaved=True):
    rng = np.random.default_rng(SEED)
    obs = np.zeros(REPS)
    ex = np.zeros(REPS)
    if interleaved:
        for y in ys:
            Ny, ny, My, my = alls[c][y], topic[c][y], wa[y], wt[y]
            obs = obs + rng.binomial(Ny, ny / Ny, REPS)
            ex = ex + Ny * rng.binomial(My, my / My, REPS) / My
    else:
        for y in ys:
            Ny, ny = alls[c][y], topic[c][y]
            obs = obs + rng.binomial(Ny, ny / Ny, REPS)
        for y in ys:
            Ny, My, my = alls[c][y], wa[y], wt[y]
            ex = ex + Ny * rng.binomial(My, my / My, REPS) / My
    r = obs / ex
    lo, hi = np.percentile(r, [2.5, 97.5])
    return float(lo), float(hi)


def compute(c, lo, hi):
    ys = window_years(lo, hi)
    n = sum(topic[c][y] for y in ys)
    N = sum(alls[c][y] for y in ys)
    m = sum(wt[y] for y in ys)
    M = sum(wa[y] for y in ys)
    E = sum(alls[c][y] * wt[y] / wa[y] for y in ys)
    d = {"n": n, "N": N, "m": m, "M": M,
         "share_c": 1000 * n / N, "share_w": 1000 * m / M,
         "ai": (n / N) / (m / M), "E": E, "std": n / E}
    d["ci"] = boot_crude(n, N, m, M)
    d["sci"] = boot_std(c, ys, True)
    d["sci_alt"] = boot_std(c, ys, False)
    return d


calc = {}
for c in COUNTRIES:
    for lo, hi in T4A_WINDOWS + T4D_WINDOWS:
        calc[(c, wname(lo, hi))] = compute(c, lo, hi)


def mism(pairs):
    return [nm for nm, t, r in pairs if t != r]


# ---------------------------------------------------------------- C02 T4a crude
t4a = read_dicts(OUT / "tables" / "T4a_activity_index_five_countries.csv")
t4a_idx = {(r["country"], r["window"]): r for r in t4a}
expected_keys = [(c, wname(lo, hi)) for c in COUNTRIES for lo, hi in T4A_WINDOWS]
add("C02-00", "T4a has one row per country and window (5 x 5), no extras",
    "25 rows: " + ", ".join(COUNTRIES) + " x five windows",
    f"{len(t4a)} rows; keys match {sorted(t4a_idx) == sorted(expected_keys)}",
    len(t4a) == 25 and sorted(t4a_idx) == sorted(expected_keys))

k = 0
for c in COUNTRIES:
    for lo, hi in T4A_WINDOWS:
        k += 1
        w = wname(lo, hi)
        T = t4a_idx.get((c, w))
        d = calc[(c, w)]
        if T is None:
            add(f"C02-{k:02d}", f"T4a {c} {w} crude values", "row missing", "-", False, "row absent")
            continue
        pairs = [("topic", T["topic"], str(d["n"])), ("all", T["all"], str(d["N"])),
                 ("topic_world", T["topic_world"], str(d["m"])), ("all_world", T["all_world"], str(d["M"])),
                 ("share_topic_permille", T["share_topic_permille"], fmt(d["share_c"], 3)),
                 ("share_world_permille", T["share_world_permille"], fmt(d["share_w"], 3)),
                 ("activity_index", T["activity_index"], fmt(d["ai"], 3)),
                 ("replicates", T["replicates"], str(REPS)),
                 ("ci95_low", T["ci95_low"], fmt(d["ci"][0], 3)),
                 ("ci95_high", T["ci95_high"], fmt(d["ci"][1], 3))]
        bad = mism(pairs)
        add(f"C02-{k:02d}",
            f"T4a {c} {w}: topic, all, world counts, shares, crude AI, replicates, crude CI (own calculation)",
            " ".join(t for _, t, _ in pairs), " ".join(r for _, _, r in pairs),
            not bad, ("mismatch: " + ", ".join(bad)) if bad else "")

# KZ rows vs F13.4 T2b / T2d
t2b = {r["window"]: r for r in read_dicts(F134T / "T2b_activity_index_periods.csv")}
t2d = {r["window"]: r for r in read_dicts(F134T / "T2d_activity_index_windows.csv")}
colmap = [("topic_KZ", "topic"), ("all_KZ", "all"), ("topic_world", "topic_world"),
          ("all_world", "all_world"), ("share_topic_in_KZ_permille", "share_topic_permille"),
          ("share_topic_in_world_permille", "share_world_permille"),
          ("activity_index", "activity_index"), ("ci95_low", "ci95_low"), ("ci95_high", "ci95_high"),
          ("replicates", "replicates"), ("expected_topic_KZ_by_year", "expected_topic_by_year"),
          ("ai_year_standardised", "ai_year_standardised"), ("std_ci95_low", "std_ci95_low"),
          ("std_ci95_high", "std_ci95_high")]
ref_rows = [("2003-2016", "T2b", t2b.get("2003-2016")), ("2017-2021", "T2b", t2b.get("2017-2021")),
            ("2022-2025", "T2b", t2b.get("2022-2025")), ("2003-2025", "T2b", t2b.get("2003-2025")),
            ("2017-2025", "T2d", t2d.get("2017-2025"))]
for w, src, R in ref_rows:
    k += 1
    T = t4a_idx.get(("KZ", w))
    if R is None or T is None:
        add(f"C02-{k:02d}", f"T4a KZ {w} equals F13.4 {src}", "row present", "row missing", False)
        continue
    bad = [a for a, b in colmap if R[a] != T[b]]
    add(f"C02-{k:02d}", f"T4a KZ {w} equals F13.4 {src} row {w} in 14 corresponding columns",
        f"{src} {w}: AI {R['activity_index']}, E {R['expected_topic_KZ_by_year']}, std {R['ai_year_standardised']}",
        f"{len(colmap) - len(bad)}/{len(colmap)} columns equal", not bad,
        ("differ: " + ", ".join(bad)) if bad else "")

# T4a_KZ_check_against_F13_4.csv: values truly from T2b/T2d and T4a
chk = read_dicts(OUT / "tables" / "T4a_KZ_check_against_F13_4.csv")
srcmap = {w: R for w, _, R in ref_rows}
colmap_d = dict(colmap)
bad_chk = 0
for r in chk:
    R = srcmap.get(r["window"])
    T = t4a_idx.get(("KZ", r["window"]))
    col = r["F13_4_column"]
    if R is None or T is None or col not in colmap_d:
        bad_chk += 1
        continue
    if not (r["F13_4_value"] == R[col] and r["F13_4b_value"] == T[colmap_d[col]] and r["equal"] == "1"):
        bad_chk += 1
k += 1
add(f"C02-{k:02d}", "T4a_KZ_check_against_F13_4.csv: cells quote T2b/T2d and T4a truly, all equal",
    "65 rows, equal = 1, values as in source tables",
    f"{len(chk)} rows; {bad_chk} rows wrong", len(chk) == 65 and bad_chk == 0)

# T4b per-year shares
t4b = read_dicts(OUT / "tables" / "T4b_topic_share_by_year.csv")
bad_cells = []
for r in t4b:
    y = int(r["year"])
    for c in COUNTRIES:
        v = fmt(1000 * topic[c][y] / alls[c][y], 3)
        if r[f"{c}_permille"] != v:
            bad_cells.append(f"{c}{y}")
    if r["world_permille"] != fmt(1000 * wt[y] / wa[y], 3):
        bad_cells.append(f"world{y}")
k += 1
add(f"C02-{k:02d}", "T4b: per-year topic share per mille for five countries and world (own calculation)",
    "23 years x 6 columns", f"{len(t4b)} years; {23 * 6 - len(bad_cells)} of {23 * 6} cells equal",
    len(t4b) == 23 and [int(r["year"]) for r in t4b] == YEARS and not bad_cells,
    ("differ: " + ", ".join(bad_cells[:8])) if bad_cells else "")

# ---------------------------------------------------------------- C03 standardised
alt_notes = []
k = 0
for c in COUNTRIES:
    for lo, hi in T4A_WINDOWS:
        k += 1
        w = wname(lo, hi)
        T = t4a_idx.get((c, w))
        d = calc[(c, w)]
        if T is None:
            add(f"C03-{k:02d}", f"T4a {c} {w} standardised", "row missing", "-", False)
            continue
        pairs = [("expected_topic_by_year", T["expected_topic_by_year"], fmt(d["E"], 1)),
                 ("ai_year_standardised", T["ai_year_standardised"], fmt(d["std"], 3)),
                 ("std_ci95_low", T["std_ci95_low"], fmt(d["sci"][0], 3)),
                 ("std_ci95_high", T["std_ci95_high"], fmt(d["sci"][1], 3))]
        bad = mism(pairs)
        note = ""
        if bad:
            alt = [fmt(d["sci_alt"][0], 3), fmt(d["sci_alt"][1], 3)]
            note = "mismatch: " + ", ".join(bad) + f"; non-interleaved CI {alt[0]}-{alt[1]}"
        add(f"C03-{k:02d}", f"T4a {c} {w}: expected E, year-standardised AI, its CI (own calculation)",
            " ".join(t for _, t, _ in pairs), " ".join(r for _, _, r in pairs), not bad, note)

t4d = read_dicts(OUT / "tables" / "T4d_without_2025.csv")
t4d_idx = {(r["country"], r["window"]): r for r in t4d}
exp_d_keys = [(c, wname(lo, hi)) for c in COUNTRIES for lo, hi in T4D_WINDOWS]
k += 1
add(f"C03-{k:02d}", "T4d has one row per country and window ending 2024 (5 x 3)",
    "15 rows", f"{len(t4d)} rows; keys match {sorted(t4d_idx) == sorted(exp_d_keys)}",
    len(t4d) == 15 and sorted(t4d_idx) == sorted(exp_d_keys))
for c in COUNTRIES:
    for lo, hi in T4D_WINDOWS:
        k += 1
        w = wname(lo, hi)
        T = t4d_idx.get((c, w))
        d = calc[(c, w)]
        if T is None:
            add(f"C03-{k:02d}", f"T4d {c} {w}", "row missing", "-", False)
            continue
        pairs = [("topic", T["topic"], str(d["n"])), ("all", T["all"], str(d["N"])),
                 ("activity_index", T["activity_index"], fmt(d["ai"], 3)),
                 ("ai_year_standardised", T["ai_year_standardised"], fmt(d["std"], 3)),
                 ("std_ci95", T["std_ci95"], fmt(d["sci"][0], 3) + "-" + fmt(d["sci"][1], 3))]
        bad = mism(pairs)
        note = f"E = {fmt(d['E'], 1)} (not printed in T4d)"
        if bad:
            note = "mismatch: " + ", ".join(bad) + "; " + note
        add(f"C03-{k:02d}", f"T4d {c} {w}: topic, all, crude AI, standardised AI, its CI (own calculation)",
            " ".join(t for _, t, _ in pairs), " ".join(r for _, _, r in pairs), not bad, note)

# KZ 2003-2024 against F13.4 T2d row "2003-2024 (without 2025)"
R = t2d.get("2003-2024 (without 2025)")
d = calc[("KZ", "2003-2024")]
if R is not None:
    pairs = [("topic_KZ", R["topic_KZ"], str(d["n"])), ("all_KZ", R["all_KZ"], str(d["N"])),
             ("activity_index", R["activity_index"], fmt(d["ai"], 3)),
             ("ci95_low", R["ci95_low"], fmt(d["ci"][0], 3)), ("ci95_high", R["ci95_high"], fmt(d["ci"][1], 3)),
             ("expected_topic_KZ_by_year", R["expected_topic_KZ_by_year"], fmt(d["E"], 1)),
             ("ai_year_standardised", R["ai_year_standardised"], fmt(d["std"], 3)),
             ("std_ci95_low", R["std_ci95_low"], fmt(d["sci"][0], 3)),
             ("std_ci95_high", R["std_ci95_high"], fmt(d["sci"][1], 3))]
    bad = mism(pairs)
    k += 1
    add(f"C03-{k:02d}", "KZ 2003-2024 recomputed equals F13.4 T2d row 2003-2024 (without 2025)",
        " ".join(t for _, t, _ in pairs), " ".join(r for _, _, r in pairs), not bad,
        ("mismatch: " + ", ".join(bad)) if bad else "")

# ---------------------------------------------------------------- C04 ranking
t4c = read_dicts(OUT / "tables" / "T4c_ranking.csv")
k = 0
for w in ["2017-2021", "2022-2025"]:
    rows = [r for r in t4c if r["window"] == w]
    table_order = [r["country"] for r in sorted(rows, key=lambda r: int(r["rank"]))]
    file_order = [r["country"] for r in rows]
    own_order = sorted(COUNTRIES, key=lambda c: -calc[(c, w)]["std"])
    k += 1
    add(f"C04-{k:02d}", f"T4c {w}: order of countries by standardised AI, descending; ranks 1-5",
        " > ".join(table_order), " > ".join(own_order),
        table_order == own_order and file_order == table_order
        and [int(r["rank"]) for r in sorted(rows, key=lambda r: int(r["rank"]))] == [1, 2, 3, 4, 5])

    flags_t, flags_o = [], []
    ratios_t, ratios_o, ratios_r = [], [], []
    cons_bad = []
    for r in rows:
        c = r["country"]
        d = calc[(c, w)]
        lo_ci, hi_ci = d["sci"]
        own_flag = "yes" if lo_ci > 1 else ("no" if hi_ci < 1 else "not clear")
        flags_t.append(f"{c}:{r['above_world_share']}")
        flags_o.append(f"{c}:{own_flag}")
        kz = calc[("KZ", w)]["std"]
        ratios_t.append(f"{c}:{r['ratio_KZ_to_country']}")
        ratios_o.append(f"{c}:{fmt(kz / d['std'], 2)}")
        kz_r = float(fmt(kz, 3))
        ratios_r.append(f"{c}:{fmt(kz_r / float(fmt(d['std'], 3)), 2)}")
        T = t4a_idx[(c, w)]
        if not (r["ai_year_standardised"] == T["ai_year_standardised"]
                and r["std_ci95"] == T["std_ci95_low"] + "-" + T["std_ci95_high"]
                and r["activity_index"] == T["activity_index"] and r["topic"] == T["topic"]):
            cons_bad.append(c)
    k += 1
    add(f"C04-{k:02d}", f"T4c {w}: above_world_share flags from own standardised CI",
        " ".join(flags_t).replace("not clear", "not_clear"), " ".join(flags_o).replace("not clear", "not_clear"),
        flags_t == flags_o)
    k += 1
    ok_unr = ratios_t == ratios_o
    ok_rnd = ratios_t == ratios_r
    if ok_unr:
        shown = ratios_o
        note = "equals quotient of unrounded and of printed (3 dp) indices" if ok_rnd else "equals unrounded quotient"
    elif ok_rnd:
        shown = ratios_r
        diff = [o for o, t in zip(ratios_o, ratios_t) if o != t]
        note = "quotient of printed 3 dp indices; unrounded gives " + " ".join(diff)
    else:
        shown = ratios_o
        note = "neither unrounded nor printed-index quotient matches"
    add(f"C04-{k:02d}", f"T4c {w}: ratio_KZ_to_country = KZ standardised / country standardised, 2 dp",
        " ".join(ratios_t), " ".join(shown), ok_unr or ok_rnd, note)
    k += 1
    add(f"C04-{k:02d}", f"T4c {w}: standardised AI, CI, crude AI and topic equal T4a",
        "5 rows equal T4a", f"{5 - len(cons_bad)} rows equal", len(rows) == 5 and not cons_bad,
        ("differ: " + ", ".join(cons_bad)) if cons_bad else "")

for lo, hi in T4D_WINDOWS:
    w = wname(lo, hi)
    own_order = sorted(COUNTRIES, key=lambda c: -calc[(c, w)]["std"])
    own_rank = {c: i + 1 for i, c in enumerate(own_order)}
    tr = [f"{c}:{t4d_idx[(c, w)]['rank_standardised']}" for c in COUNTRIES]
    orr = [f"{c}:{own_rank[c]}" for c in COUNTRIES]
    k += 1
    add(f"C04-{k:02d}", f"T4d {w}: rank_standardised from own standardised AI, descending",
        " ".join(tr), " ".join(orr), tr == orr)

tot = {c: sum(topic[c].values()) for c in COUNTRIES}
t25 = [f"{c}:{t4d_idx[(c, wname(lo, hi))]['topic_2025']}/{t4d_idx[(c, wname(lo, hi))]['share_2025_of_total_pct']}"
       for lo, hi in T4D_WINDOWS for c in COUNTRIES]
o25 = [f"{c}:{topic[c][2025]}/{fmt(100 * topic[c][2025] / tot[c], 1)}" for lo, hi in T4D_WINDOWS for c in COUNTRIES]
k += 1
add(f"C04-{k:02d}", "T4d topic_2025 and share_2025_of_total_pct (100 x 2025 / 2003-2025 total, 1 dp), 15 rows",
    " ".join(t25[:5]), " ".join(o25[:5]), t25 == o25,
    "same values repeated in all three windows" if t25 == o25 else "mismatch")

# ---------------------------------------------------------------- C05 figure data
fig = read_dicts(OUT / "figures" / "Fig_activity_index_comparators.csv")
fig_keys = [(r["country"], r["period"]) for r in fig]
exp_fig_keys = [(c, wname(lo, hi)) for lo, hi in FIG_WINDOWS for c in COUNTRIES]
k = 0
k += 1
add(f"C05-{k:02d}", "Figure CSV has 15 rows: three periods x five countries",
    "15 rows, periods 2003-2016, 2017-2021, 2022-2025", f"{len(fig)} rows; keys match {sorted(fig_keys) == sorted(exp_fig_keys)}",
    len(fig) == 15 and sorted(fig_keys) == sorted(exp_fig_keys))
for lo, hi in FIG_WINDOWS:
    w = wname(lo, hi)
    bad = []
    tv, ov = [], []
    for r in [r for r in fig if r["period"] == w]:
        c = r["country"]
        T = t4a_idx[(c, w)]
        d = calc[(c, w)]
        own = [fmt(d["std"], 3), fmt(d["sci"][0], 3), fmt(d["sci"][1], 3), fmt(d["ai"], 3)]
        fv = [r["ai_year_standardised"], r["std_ci95_low"], r["std_ci95_high"], r["activity_index"]]
        tt = [T["ai_year_standardised"], T["std_ci95_low"], T["std_ci95_high"], T["activity_index"]]
        tv.append(f"{c}:{fv[0]}")
        ov.append(f"{c}:{own[0]}")
        if not (fv == tt == own):
            bad.append(c)
    k += 1
    add(f"C05-{k:02d}", f"Figure CSV {w}: standardised AI, CI, crude AI equal T4a and own calculation",
        " ".join(tv), " ".join(ov), not bad, ("differ: " + ", ".join(bad)) if bad else "")

# ---------------------------------------------------------------- C06 privacy / cell length
EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
ORCID = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dXx]\b")
files = []
for sub in ["tables", "figures"]:
    for p in sorted((OUT / sub).iterdir()):
        if p.is_file() and p.suffix.lower() in (".csv", ".md"):
            files.append(p)
hits = []
long_cells = []
max_words = 0
n_cells = 0
for p in files:
    text = p.read_text(encoding="utf-8-sig")
    if EMAIL.search(text) or ORCID.search(text) or "orcid" in text.lower():
        hits.append(p.name)
    if p.suffix.lower() == ".csv":
        cells = [cell for row in read_rows(p) for cell in row]
    else:
        cells = []
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("|"):
                cells.extend(x.strip() for x in s.strip("|").split("|"))
    for cell in cells:
        n_cells += 1
        nw = len(cell.split())
        max_words = max(max_words, nw)
        if nw > 30:
            long_cells.append(p.name)
add("C06-01", "No e-mail or ORCID shapes in tables/ and figures/ CSV and MD files",
    f"0 hits in {len(files)} files", f"{len(hits)} files with hits", not hits,
    ("files: " + ", ".join(hits)) if hits else "")
add("C06-02", "No cell over 30 words in tables/ and figures/ CSV and MD table cells",
    "max 30 words", f"{n_cells} cells; max {max_words} words; {len(long_cells)} over 30",
    not long_cells, "MD prose notes are not table cells; not counted")

# ---------------------------------------------------------------- C07 MD = CSV
k = 0
for stem in ["T4a_activity_index_five_countries", "T4b_topic_share_by_year", "T4c_ranking", "T4d_without_2025"]:
    csv_rows = read_rows(OUT / "tables" / f"{stem}.csv")
    md_rows = []
    for line in (OUT / "tables" / f"{stem}.md").read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if s.startswith("|"):
            cells = [x.strip() for x in s.strip("|").split("|")]
            if all(set(x) <= set("-: ") for x in cells):
                continue
            md_rows.append(cells)
    k += 1
    add(f"C07-{k:02d}", f"{stem}.md table equals {stem}.csv (header and rows)",
        f"{len(csv_rows)} rows incl. header", f"{len(md_rows)} rows; equal {md_rows == csv_rows}",
        md_rows == csv_rows)

# ---------------------------------------------------------------- C08 numbers.json
nums = json.loads((OUT / "F13_4b_numbers.json").read_text(encoding="utf-8"))
k = 0
for key, fn in [("T4a", "T4a_activity_index_five_countries.csv"), ("T4c", "T4c_ranking.csv"),
                ("T4d", "T4d_without_2025.csv")]:
    rows = read_dicts(OUT / "tables" / fn)
    js = nums.get(key, [])
    ok = len(js) == len(rows) and all(
        set(j) == set(r) and all(str(j[col]) == r[col] for col in r) for j, r in zip(js, rows))
    k += 1
    add(f"C08-{k:02d}", f"F13_4b_numbers.json {key} equals {fn}",
        f"{len(rows)} rows", f"{len(js)} entries; equal {ok}", ok)
tt_ok = nums.get("topic_totals") == tot
at_ok = nums.get("all_totals") == {c: sum(alls[c].values()) for c in COUNTRIES}
bs_ok = nums.get("bootstrap") == {"replicates": REPS, "seed": SEED}
k += 1
add(f"C08-{k:02d}", "F13_4b_numbers.json topic_totals, all_totals and bootstrap settings",
    f"topic {nums.get('topic_totals')}", f"topic {tot}; all equal {at_ok}; bootstrap equal {bs_ok}",
    tt_ok and at_ok and bs_ok)

# ---------------------------------------------------------------- write
for r in results:
    for cell in r:
        if len(cell.split()) > 30:
            print("WARNING long cell in", r[0])
with open(RESULT, "w", encoding="utf-8", newline="") as f:
    wtr = csv.writer(f)
    wtr.writerow(["check_id", "what", "expected_from_tables", "recomputed", "verdict", "note"])
    wtr.writerows(results)

n_pass = sum(1 for r in results if r[4] == "PASS")
n_fail = sum(1 for r in results if r[4] == "FAIL")
print(f"checks {len(results)} PASS {n_pass} FAIL {n_fail}")
for r in results:
    if r[4] == "FAIL":
        print("FAIL", r[0], "|", r[1], "|", r[2], "|", r[3], "|", r[5])
