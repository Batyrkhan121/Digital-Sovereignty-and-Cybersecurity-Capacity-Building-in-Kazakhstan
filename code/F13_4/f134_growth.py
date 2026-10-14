"""Phase F13.4 - steps 1-4: growth of E1 (T1), normalised activity against Kazakhstan's and the world's Scopus output (T2),
comparators UZ, AZ, BY, KG (T3) and the figure Fig_normalised_growth. Inputs: E1 (EID, Year only), the seven year series of
author_exports_2026_10, F13.2's T1a (check). Writes tables/T1*-T3*, figures/Fig_normalised_growth.{pdf,png,tif,csv} and
F13_4_numbers.json. Deterministic: the bootstrap uses numpy's default_rng(42) afresh for each window; the PDF is written without
dates."""
import sys
sys.dont_write_bytecode = True

import json
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f134_lib as L

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import PIL
from PIL import Image

T, F = L.TABLES, L.FIGURES
B, SEED = 1000, 42
COUNTRIES = [("KZ", None), ("UZ", "UZ_topic"), ("AZ", "AZ_topic"), ("BY", "BY_topic"), ("KG", "KG_topic")]
NUM = {"versions": {"python": sys.version.split()[0], "numpy": np.__version__, "matplotlib": matplotlib.__version__, "pillow": PIL.__version__}}

years = L.load_years()
S = L.load_series()
KZ = {y: sum(1 for v in years.values() if v == y) for y in L.YEARS}
assert sum(KZ.values()) == len(years) == 841, (sum(KZ.values()), len(years))
TOPIC = {"KZ": KZ, **{c: S[s] for c, s in COUNTRIES if s}}


def f2(x):
    return f"{x:.2f}"


def window_sum(d, lo, hi):
    return sum(d[y] for y in range(lo, hi + 1))


# ---------- T1 growth
f132 = {int(r["year"]): int(r["records"]) for r in L.read_csv(L.F132_T1A) if r["year"].isdigit()}
cum, rows = 0, []
for y in L.YEARS:
    cum += KZ[y]
    ma = f2((KZ[y - 1] + KZ[y] + KZ[y + 1]) / 3) if 2003 < y < 2025 else ""
    rows.append({"year": y, "records": KZ[y], "pct_of_total": f"{100 * KZ[y] / 841:.1f}", "moving_average_3y_centred": ma, "cumulative": cum,
                 "F13_2_T1a_records": f132[y], "equal_F13_2": int(f132[y] == KZ[y])})
f = ["year", "records", "pct_of_total", "moving_average_3y_centred", "cumulative", "F13_2_T1a_records", "equal_F13_2"]
L.write_csv(T / "T1a_years.csv", f, rows)
L.write_md(T / "T1a_years.md", "T1a. E1 records by year, 2003-2025 (zeros included)", f, rows,
           "Moving average: centred over three years (t-1, t, t+1); none for 2003 and 2025. F13_2_T1a_records: F13.2's T1a for the check.")
NUM["T1a_equal_F13_2"] = all(r["equal_F13_2"] == 1 for r in rows)

rows, prev = [], None
for name, lo, hi in L.PERIODS:
    n = window_sum(KZ, lo, hi)
    yrs = hi - lo + 1
    r = {"period": name, "years": yrs, "records": n, "mean_per_year": f2(n / yrs),
         "ratio_records_to_previous": f2(n / prev[0]) if prev else "", "ratio_mean_to_previous": f2((n / yrs) / (prev[0] / prev[1])) if prev else ""}
    rows.append(r)
    prev = (n, yrs)
rows.append({"period": "2003-2025", "years": 23, "records": 841, "mean_per_year": f2(841 / 23)})
f = ["period", "years", "records", "mean_per_year", "ratio_records_to_previous", "ratio_mean_to_previous"]
L.write_csv(T / "T1b_periods.csv", f, rows)
L.write_md(T / "T1b_periods.md", "T1b. E1 records by period", f, rows,
           "Periods have 14, 5 and 4 years: the ratio of annual means compares like with like; the ratio of records is printed too.")
NUM["T1b"] = rows


def loglin(lo, hi):
    pts = [(y, KZ[y]) for y in range(lo, hi + 1) if KZ[y] > 0]
    zeros = sum(1 for y in range(lo, hi + 1) if KZ[y] == 0)
    t = np.array([y - lo for y, _ in pts], dtype=float)
    z = np.log(np.array([n for _, n in pts], dtype=float))
    tm, zm = t.mean(), z.mean()
    b = float(((t - tm) * (z - zm)).sum() / ((t - tm) ** 2).sum())
    a = float(zm - b * tm)
    res = z - (a + b * t)
    r2 = float(1 - (res ** 2).sum() / ((z - zm) ** 2).sum())
    return {"window": f"{lo}-{hi}", "years_used": len(pts), "zero_years_excluded": zeros, "t_origin": lo, "a": f"{a:.4f}", "b": f"{b:.4f}",
            "annual_growth_pct": f"{100 * (math.exp(b) - 1):.1f}", "doubling_time_years": f2(math.log(2) / b), "r_squared": f"{r2:.4f}"}


first3 = min(y for y in L.YEARS if KZ[y] >= 3)
fits = [loglin(first3, 2025), loglin(2017, 2025), loglin(first3, 2024)]
fits[2]["window"] += " (extra: without 2025)"
f = ["window", "years_used", "zero_years_excluded", "t_origin", "a", "b", "annual_growth_pct", "doubling_time_years", "r_squared"]
L.write_csv(T / "T1c_loglinear_fit.csv", f, fits)
L.write_md(T / "T1c_loglinear_fit.md", "T1c. Log-linear fit ln(n_t) = a + b t (ordinary least squares)", f, fits,
           f"t = year - t_origin. First year with at least 3 records: {first3}. Years with zero records are excluded (count printed). "
           "Annual growth = e^b - 1; doubling time = ln 2 / b. The third row (without 2025) is an addition for sensitivity.")
NUM["T1c"] = fits
NUM["first_year_with_3"] = first3
t1d = [{"measure": "share of 2024-2025 in the total (%)", "value": f"{100 * (KZ[2024] + KZ[2025]) / 841:.1f}", "detail": f"{KZ[2024] + KZ[2025]} of 841"},
       {"measure": "ratio 2025 / 2020", "value": f2(KZ[2025] / KZ[2020]), "detail": f"{KZ[2025]} / {KZ[2020]}"},
       {"measure": "ratio 2025 / 2015", "value": f2(KZ[2025] / KZ[2015]), "detail": f"{KZ[2025]} / {KZ[2015]}"}]
L.write_csv(T / "T1d_recent_weight.csv", ["measure", "value", "detail"], t1d)
L.write_md(T / "T1d_recent_weight.md", "T1d. Weight of the last years", ["measure", "value", "detail"], t1d)
NUM["T1d"] = t1d

# ---------- T2 normalisation
rows = []
for y in L.YEARS:
    sk, sw = KZ[y] / S["KZ_all"][y], S["world_topic"][y] / S["world_all"][y]
    rows.append({"year": y, "topic_KZ": KZ[y], "all_KZ": S["KZ_all"][y], "share_topic_in_KZ_permille": f"{1000 * sk:.3f}",
                 "topic_world": S["world_topic"][y], "all_world": S["world_all"][y], "share_topic_in_world_permille": f"{1000 * sw:.3f}",
                 "activity_index": f"{sk / sw:.3f}"})
f = ["year", "topic_KZ", "all_KZ", "share_topic_in_KZ_permille", "topic_world", "all_world", "share_topic_in_world_permille", "activity_index"]
L.write_csv(T / "T2a_normalised_by_year.csv", f, rows)
L.write_md(T / "T2a_normalised_by_year.md", "T2a. Topic share and activity index by year", f, rows,
           "AI = (topic KZ / all KZ) / (topic world / all world). topic KZ = E1; all KZ = AFFILCOUNTRY(kazakhstan); topic world = the "
           "topic query without a country; all world = every document; Scopus, 13 October 2026.")


def ai_window(lo, hi):
    n, N = window_sum(KZ, lo, hi), window_sum(S["KZ_all"], lo, hi)
    m, M = window_sum(S["world_topic"], lo, hi), window_sum(S["world_all"], lo, hi)
    ai = (n / N) / (m / M)
    rng = np.random.default_rng(SEED)
    kz = rng.binomial(N, n / N, size=B)
    wd = rng.binomial(M, m / M, size=B)
    boot = (kz / N) / (wd / M)
    lo_ci, hi_ci = np.percentile(boot, [2.5, 97.5])
    # addition (declared): the year-standardised index = observed / expected, expected = sum over years of all KZ_y x world share_y
    # (indirect standardisation); it removes the effect of Kazakhstan's output being concentrated in recent years
    yrs = range(lo, hi + 1)
    exp_ = sum(S["KZ_all"][y] * S["world_topic"][y] / S["world_all"][y] for y in yrs)
    rng2 = np.random.default_rng(SEED)
    obs_b, exp_b = np.zeros(B), np.zeros(B)
    for y in yrs:
        Ny, My = S["KZ_all"][y], S["world_all"][y]
        obs_b += rng2.binomial(Ny, KZ[y] / Ny, size=B)
        exp_b += Ny * rng2.binomial(My, S["world_topic"][y] / My, size=B) / My
    slo, shi = np.percentile(obs_b / exp_b, [2.5, 97.5])
    return {"window": f"{lo}-{hi}", "topic_KZ": n, "all_KZ": N, "topic_world": m, "all_world": M,
            "share_topic_in_KZ_permille": f"{1000 * n / N:.3f}", "share_topic_in_world_permille": f"{1000 * m / M:.3f}",
            "activity_index": f"{ai:.3f}", "ci95_low": f"{lo_ci:.3f}", "ci95_high": f"{hi_ci:.3f}", "replicates": B,
            "expected_topic_KZ_by_year": f"{exp_:.1f}", "ai_year_standardised": f"{n / exp_:.3f}", "std_ci95_low": f"{slo:.3f}", "std_ci95_high": f"{shi:.3f}"}


f = ["window", "topic_KZ", "all_KZ", "topic_world", "all_world", "share_topic_in_KZ_permille", "share_topic_in_world_permille",
     "activity_index", "ci95_low", "ci95_high", "replicates", "expected_topic_KZ_by_year", "ai_year_standardised", "std_ci95_low", "std_ci95_high"]
t2b = [ai_window(lo, hi) for _, lo, hi in L.PERIODS] + [ai_window(2003, 2025)]
RULE = ("95 % interval: record bootstrap, 1000 replicates, numpy default_rng(42) started afresh for each window. Each replicate "
        "resamples the window's Kazakh publications (all KZ) with replacement and counts the topic ones - drawn as Binomial(all KZ, topic KZ / "
        "all KZ), the exact distribution of that count - and the world's publications likewise; AI is recomputed; 2.5th and 97.5th "
        "percentiles. It is a stability interval for a census (as in the Leiden Ranking), not a sampling confidence interval. "
        "Addition: ai_year_standardised = topic KZ / sum over the window's years of (all KZ_y x topic world_y / all world_y); its interval "
        "resamples each year the same way (own default_rng(42)).")
L.write_csv(T / "T2b_activity_index_periods.csv", f, t2b)
L.write_md(T / "T2b_activity_index_periods.md", "T2b. Activity index by period and for 2003-2025", f, t2b, RULE)
t2d = [ai_window(2003, 2025), ai_window(2017, 2025), ai_window(2022, 2025), ai_window(2003, 2024)]
t2d[0]["window"] += " (reference)"
t2d[3]["window"] += " (without 2025)"
L.write_csv(T / "T2d_activity_index_windows.csv", f, t2d)
L.write_md(T / "T2d_activity_index_windows.md", "T2d. Sensitivity of the activity index to the window", f, t2d, "Interval rule as in T2b.")
NUM["T2b"], NUM["T2d"] = t2b, t2d

rows = []
for y in L.YEARS:
    a, b = KZ[y] / S["world_topic"][y], S["KZ_all"][y] / S["world_all"][y]
    rows.append({"year_or_window": str(y), "topic_KZ": KZ[y], "topic_world": S["world_topic"][y], "KZ_share_of_world_topic_permille": f"{1000 * a:.4f}",
                 "all_KZ": S["KZ_all"][y], "all_world": S["world_all"][y], "KZ_share_of_world_all_permille": f"{1000 * b:.4f}",
                 "ratio_of_shares": f"{a / b:.3f}"})
for name, lo, hi in L.PERIODS + [("2003-2025", 2003, 2025)]:
    n, m = window_sum(KZ, lo, hi), window_sum(S["world_topic"], lo, hi)
    N, M = window_sum(S["KZ_all"], lo, hi), window_sum(S["world_all"], lo, hi)
    rows.append({"year_or_window": name, "topic_KZ": n, "topic_world": m, "KZ_share_of_world_topic_permille": f"{1000 * n / m:.4f}",
                 "all_KZ": N, "all_world": M, "KZ_share_of_world_all_permille": f"{1000 * N / M:.4f}", "ratio_of_shares": f"{(n / m) / (N / M):.3f}"})
f = ["year_or_window", "topic_KZ", "topic_world", "KZ_share_of_world_topic_permille", "all_KZ", "all_world", "KZ_share_of_world_all_permille", "ratio_of_shares"]
L.write_csv(T / "T2c_shares_of_world.csv", f, rows)
L.write_md(T / "T2c_shares_of_world.md", "T2c. Kazakhstan's share of the world's topic output and of all output", f, rows,
           "ratio_of_shares = (topic KZ / topic world) / (all KZ / all world), algebraically equal to the activity index of T2a and T2b.")

# ---------- T3 comparators
rows = []
for y in L.YEARS:
    r = {"year": y, **{c: TOPIC[c][y] for c, _ in COUNTRIES}}
    r["sum_five"] = sum(r[c] for c, _ in COUNTRIES)
    rows.append(r)
tot = {"year": "2003-2025", **{c: sum(TOPIC[c].values()) for c, _ in COUNTRIES}}
tot["sum_five"] = sum(tot[c] for c, _ in COUNTRIES)
rows.append(tot)
f = ["year"] + [c for c, _ in COUNTRIES] + ["sum_five"]
L.write_csv(T / "T3a_comparators_by_year.csv", f, rows)
L.write_md(T / "T3a_comparators_by_year.md", "T3a. Topic records by year: Kazakhstan (E1) and four comparators", f, rows,
           "Same topic query with AFFILCOUNTRY of each country (Scopus Analyze, 13 October 2026). A document with authors from two of "
           "these countries counts for both, so sum_five may count a document twice.")
rows = []
for name, lo, hi in L.PERIODS + [("2003-2025", 2003, 2025)]:
    cnt = {c: window_sum(TOPIC[c], lo, hi) for c, _ in COUNTRIES}
    s = sum(cnt.values())
    rows.append({"period": name, **{f"{c}_records": cnt[c] for c in cnt}, **{f"{c}_share_pct": f"{100 * cnt[c] / s:.1f}" for c in cnt}, "sum_five": s})
f = ["period"] + [f"{c}_records" for c, _ in COUNTRIES] + [f"{c}_share_pct" for c, _ in COUNTRIES] + ["sum_five"]
L.write_csv(T / "T3b_comparators_by_period.csv", f, rows)
L.write_md(T / "T3b_comparators_by_period.md", "T3b. Topic records by period and each country's share of the five", f, rows)
NUM["T3b"] = rows
rows = []
for c, _ in COUNTRIES:
    p2, p3 = window_sum(TOPIC[c], 2017, 2021), window_sum(TOPIC[c], 2022, 2025)
    rows.append({"country": c, "records_2017_2021": p2, "records_2022_2025": p3, "ratio_records": f2(p3 / p2) if p2 else "",
                 "mean_2017_2021": f2(p2 / 5), "mean_2022_2025": f2(p3 / 4), "ratio_means": f2((p3 / 4) / (p2 / 5)) if p2 else ""})
f = ["country", "records_2017_2021", "records_2022_2025", "ratio_records", "mean_2017_2021", "mean_2022_2025", "ratio_means"]
L.write_csv(T / "T3c_growth_by_country.csv", f, rows)
L.write_md(T / "T3c_growth_by_country.md", "T3c. Growth 2017-2021 -> 2022-2025 by country", f, rows,
           "Ratio of means: annual mean of 2022-2025 (4 years) over that of 2017-2021 (5 years).")
NUM["T3c"] = rows
rows = []
s24 = sum(window_sum(TOPIC[c], 2003, 2024) for c, _ in COUNTRIES)
s2224 = sum(window_sum(TOPIC[c], 2022, 2024) for c, _ in COUNTRIES)
for c, _ in COUNTRIES:
    total, y25 = sum(TOPIC[c].values()), TOPIC[c][2025]
    p2, p3x = window_sum(TOPIC[c], 2017, 2021), window_sum(TOPIC[c], 2022, 2024)
    rows.append({"country": c, "total_2003_2025": total, "records_2025": y25, "share_2025_pct": f"{100 * y25 / total:.1f}",
                 "total_2003_2024": total - y25, "share_of_five_2003_2024_pct": f"{100 * (total - y25) / s24:.1f}",
                 "records_2022_2024": p3x, "share_of_five_2022_2024_pct": f"{100 * p3x / s2224:.1f}",
                 "ratio_means_2017_2021_to_2022_2024": f2((p3x / 3) / (p2 / 5)) if p2 else ""})
f = ["country", "total_2003_2025", "records_2025", "share_2025_pct", "total_2003_2024", "share_of_five_2003_2024_pct", "records_2022_2024",
     "share_of_five_2022_2024_pct", "ratio_means_2017_2021_to_2022_2024"]
L.write_csv(T / "T3d_without_2025.csv", f, rows)
L.write_md(T / "T3d_without_2025.md", "T3d. The weight of 2025 and the same indicators without 2025 (Uzbekistan first of interest)", f, rows,
           "Without 2025: shares of the five over 2003-2024 and 2022-2024; growth as the annual mean of 2022-2024 (3 years) over that of 2017-2021 (5 years).")
NUM["T3d"] = rows
uz = next(r for r in rows if r["country"] == "UZ")
assert (uz["records_2025"], uz["total_2003_2025"]) == (258, 539), uz

# ---------- figure
F.mkdir(parents=True, exist_ok=True)
share = {y: 1000 * KZ[y] / S["KZ_all"][y] for y in L.YEARS}
L.write_csv(F / "Fig_normalised_growth.csv", ["year", "KZ_topic_records", "KZ_all_records", "KZ_share_permille", "KZ", "UZ", "AZ", "BY", "KG"],
            [{"year": y, "KZ_topic_records": KZ[y], "KZ_all_records": S["KZ_all"][y], "KZ_share_permille": f"{share[y]:.3f}",
              **{c: TOPIC[c][y] for c, _ in COUNTRIES}} for y in L.YEARS])
fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(8, 8))
ax1.bar(L.YEARS, [KZ[y] for y in L.YEARS], color="#4c72b0", width=0.7, zorder=2)
ax1.set_ylabel("Records (topic, Kazakhstan)")
ax1.set_xticks(L.YEARS[::2])
ax2 = ax1.twinx()
ax2.plot(L.YEARS, [share[y] for y in L.YEARS], color="#c44e52", marker="o", markersize=3, linewidth=1.4, zorder=3)
ax2.set_ylabel("Share of the topic in Kazakhstan's output (‰)")
ax2.set_ylim(bottom=0)
ax1.text(0.01, 0.97, "(a)", transform=ax1.transAxes, ha="left", va="top", fontsize=10)
styles = {"KZ": ("#4c72b0", "-"), "UZ": ("#dd8452", "--"), "AZ": ("#55a868", "-."), "BY": ("#8172b3", ":"), "KG": ("#937860", "-")}
names = {"KZ": "Kazakhstan", "UZ": "Uzbekistan", "AZ": "Azerbaijan", "BY": "Belarus", "KG": "Kyrgyzstan"}
for c, _ in COUNTRIES:
    col, ls = styles[c]
    ax3.plot(L.YEARS, [TOPIC[c][y] for y in L.YEARS], color=col, linestyle=ls, linewidth=1.5, label=names[c])
ax3.set_xlabel("Year")
ax3.set_ylabel("Records (topic)")
ax3.set_xticks(L.YEARS[::2])
ax3.legend(frameon=False, fontsize=8)
ax3.text(0.01, 0.97, "(b)", transform=ax3.transAxes, ha="left", va="top", fontsize=10)
fig.tight_layout()
base = F / "Fig_normalised_growth"
fig.savefig(str(base) + ".pdf", metadata={"CreationDate": None, "ModDate": None, "Producer": None, "Creator": None})
fig.savefig(str(base) + ".png", dpi=300, metadata={"Software": None})
plt.close(fig)
with Image.open(str(base) + ".png") as im:
    im.convert("RGB").save(str(base) + ".tif", compression="tiff_lzw", dpi=(300, 300))

NUM["totals"] = {c: sum(TOPIC[c].values()) for c, _ in COUNTRIES}
NUM["series_sums"] = {k: sum(v.values()) for k, v in S.items()}
NUM["bootstrap"] = {"replicates": B, "seed": SEED, "rule": RULE}
L.jdump(NUM, L.OUT / "F13_4_numbers.json")
print(json.dumps({k: NUM[k] for k in ("T1a_equal_F13_2", "first_year_with_3", "T1c", "T1d", "T2b", "T2d", "totals")}, ensure_ascii=False, indent=1))
for r in NUM["T3c"] + NUM["T3d"]:
    print(r)
