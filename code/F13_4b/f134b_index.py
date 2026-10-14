"""Phase F13.4b - steps 1-2: activity index for five countries (T4a-T4d) and the figure Fig_activity_index_comparators. The formulas
and the bootstrap are F13.4's (copied from f134_growth.ai_window, generalised to a country's topic and all-output series): crude AI =
(topic / all) / (topic world / all world) over the window; year-standardised AI = topic / sum over years of all_y x topic world_y /
all world_y; 1000 replicates, numpy default_rng(42) started afresh for each window (crude) and again for the standardised index
(drawn year by year: the country, then the world). KZ's topic is E1 counted by Year. Writes tables/T4*, the figure files and
F13_4b_numbers.json."""
import sys
sys.dont_write_bytecode = True

import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f134b_lib as L

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import PIL
from PIL import Image

T, F = L.TABLES, L.FIGURES
B, SEED = 1000, 42
CS, S = L.country_series()
assert sum(CS["KZ"][0].values()) == 841
for c in L.COUNTRIES:
    assert all(CS[c][0][y] <= CS[c][1][y] for y in L.YEARS), ("topic above all output", c)
NUM = {"versions": {"python": sys.version.split()[0], "numpy": np.__version__, "matplotlib": matplotlib.__version__, "pillow": PIL.__version__},
       "bootstrap": {"replicates": B, "seed": SEED}}
FIELDS = ["country", "window", "topic", "all", "topic_world", "all_world", "share_topic_permille", "share_world_permille", "activity_index",
          "ci95_low", "ci95_high", "replicates", "expected_topic_by_year", "ai_year_standardised", "std_ci95_low", "std_ci95_high"]


def wsum(d, lo, hi):
    return sum(d[y] for y in range(lo, hi + 1))


def ai_window(c, lo, hi):
    topic, allo = CS[c]
    n, N = wsum(topic, lo, hi), wsum(allo, lo, hi)
    m, M = wsum(S["world_topic"], lo, hi), wsum(S["world_all"], lo, hi)
    ai = (n / N) / (m / M)
    rng = np.random.default_rng(SEED)
    kz = rng.binomial(N, n / N, size=B)
    wd = rng.binomial(M, m / M, size=B)
    lo_ci, hi_ci = np.percentile((kz / N) / (wd / M), [2.5, 97.5])
    yrs = [y for y in range(lo, hi + 1) if allo[y] > 0]
    exp_ = sum(allo[y] * S["world_topic"][y] / S["world_all"][y] for y in yrs)
    rng2 = np.random.default_rng(SEED)
    obs_b, exp_b = np.zeros(B), np.zeros(B)
    for y in yrs:
        Ny, My = allo[y], S["world_all"][y]
        obs_b += rng2.binomial(Ny, topic[y] / Ny, size=B)
        exp_b += Ny * rng2.binomial(My, S["world_topic"][y] / My, size=B) / My
    slo, shi = np.percentile(obs_b / exp_b, [2.5, 97.5])
    return {"country": c, "window": f"{lo}-{hi}", "topic": n, "all": N, "topic_world": m, "all_world": M,
            "share_topic_permille": f"{1000 * n / N:.3f}", "share_world_permille": f"{1000 * m / M:.3f}", "activity_index": f"{ai:.3f}",
            "ci95_low": f"{lo_ci:.3f}", "ci95_high": f"{hi_ci:.3f}", "replicates": B, "expected_topic_by_year": f"{exp_:.1f}",
            "ai_year_standardised": f"{n / exp_:.3f}", "std_ci95_low": f"{slo:.3f}", "std_ci95_high": f"{shi:.3f}",
            "_zero_all_years": (hi - lo + 1) - len(yrs)}


# ---------- T4a
t4a = [ai_window(c, lo, hi) for c in L.COUNTRIES for lo, hi in L.WINDOWS]
assert all(r["_zero_all_years"] == 0 for r in t4a)
L.write_csv(T / "T4a_activity_index_five_countries.csv", FIELDS, t4a)
L.write_md(T / "T4a_activity_index_five_countries.md", "T4a. Activity index of five countries by window (crude and standardised by year)", FIELDS, t4a,
           "topic: the country's records for the topic query (KZ: E1); all: the country's whole Scopus output; world: the topic query "
           "without a country and every document. Intervals: record bootstrap of F13.4 (1000 replicates, seed 42).")
# KZ check against F13.4
f134 = {r["window"].split(" ")[0]: r for r in L.read_csv(L.F134_T2B) + L.read_csv(L.F134_T2D)}
pairs = [("topic_KZ", "topic"), ("all_KZ", "all"), ("topic_world", "topic_world"), ("all_world", "all_world"),
         ("share_topic_in_KZ_permille", "share_topic_permille"), ("share_topic_in_world_permille", "share_world_permille"),
         ("activity_index", "activity_index"), ("ci95_low", "ci95_low"), ("ci95_high", "ci95_high"),
         ("expected_topic_KZ_by_year", "expected_topic_by_year"), ("ai_year_standardised", "ai_year_standardised"),
         ("std_ci95_low", "std_ci95_low"), ("std_ci95_high", "std_ci95_high")]
chk = []
for r in t4a:
    if r["country"] != "KZ":
        continue
    old = f134[r["window"]]
    for a, b in pairs:
        chk.append({"window": r["window"], "F13_4_column": a, "F13_4_value": old[a], "F13_4b_value": r[b], "equal": int(str(old[a]) == str(r[b]))})
L.write_csv(T / "T4a_KZ_check_against_F13_4.csv", ["window", "F13_4_column", "F13_4_value", "F13_4b_value", "equal"], chk)
NUM["KZ_rows_equal_F13_4"] = all(c["equal"] == 1 for c in chk)
NUM["KZ_check_cells"] = len(chk)

# ---------- T4b shares by year
rows = []
for y in L.YEARS:
    r = {"year": y, **{f"{c}_permille": f"{1000 * CS[c][0][y] / CS[c][1][y]:.3f}" for c in L.COUNTRIES},
         "world_permille": f"{1000 * S['world_topic'][y] / S['world_all'][y]:.3f}"}
    rows.append(r)
f = ["year"] + [f"{c}_permille" for c in L.COUNTRIES] + ["world_permille"]
L.write_csv(T / "T4b_topic_share_by_year.csv", f, rows)
L.write_md(T / "T4b_topic_share_by_year.md", "T4b. Topic share of each country's output and of the world's, by year (per mille)", f, rows,
           "Share = 1000 x topic records / all records of the country (or the world) in the year. Small outputs make single years noisy (KG).")

# ---------- T4c ranking
by = {(r["country"], r["window"]): r for r in t4a}
rows = []
for lo, hi in ((2017, 2021), (2022, 2025)):
    w = f"{lo}-{hi}"
    order = sorted(L.COUNTRIES, key=lambda c: (-float(by[(c, w)]["ai_year_standardised"]), c))
    kz = float(by[("KZ", w)]["ai_year_standardised"])
    for i, c in enumerate(order):
        r = by[(c, w)]
        rows.append({"window": w, "rank": i + 1, "country": c, "ai_year_standardised": r["ai_year_standardised"],
                     "std_ci95": f"{r['std_ci95_low']}-{r['std_ci95_high']}", "activity_index": r["activity_index"], "topic": r["topic"],
                     "above_world_share": "yes" if float(r["std_ci95_low"]) > 1 else ("no" if float(r["std_ci95_high"]) < 1 else "not clear"),
                     "ratio_KZ_to_country": f"{kz / float(r['ai_year_standardised']):.2f}"})
f = ["window", "rank", "country", "ai_year_standardised", "std_ci95", "activity_index", "topic", "above_world_share", "ratio_KZ_to_country"]
L.write_csv(T / "T4c_ranking.csv", f, rows)
L.write_md(T / "T4c_ranking.md", "T4c. Countries ranked by the year-standardised activity index", f, rows,
           "above_world_share: yes when the whole stability interval lies above 1, no when it lies below 1, otherwise not clear. "
           "ratio_KZ_to_country: Kazakhstan's standardised index over the country's.")
NUM["T4c"] = rows

# ---------- T4d without 2025
rows = []
for lo, hi in ((2003, 2024), (2017, 2024), (2022, 2024)):
    block = [ai_window(c, lo, hi) for c in L.COUNTRIES]
    order = sorted(L.COUNTRIES, key=lambda c: -float(next(r for r in block if r["country"] == c)["ai_year_standardised"]))
    for r in block:
        c = r["country"]
        tot, y25 = sum(CS[c][0].values()), CS[c][0][2025]
        rows.append({"window": r["window"], "country": c, "topic": r["topic"], "all": r["all"], "activity_index": r["activity_index"],
                     "ai_year_standardised": r["ai_year_standardised"], "std_ci95": f"{r['std_ci95_low']}-{r['std_ci95_high']}",
                     "rank_standardised": order.index(c) + 1, "topic_2025": y25, "share_2025_of_total_pct": f"{100 * y25 / tot:.1f}"})
f = ["window", "country", "topic", "all", "activity_index", "ai_year_standardised", "std_ci95", "rank_standardised", "topic_2025", "share_2025_of_total_pct"]
L.write_csv(T / "T4d_without_2025.csv", f, rows)
L.write_md(T / "T4d_without_2025.md", "T4d. Sensitivity: windows ending in 2024 (2025 excluded)", f, rows,
           "Same formulas and bootstrap; topic_2025 and its share show how much each country's total rests on 2025.")
NUM["T4d"] = rows

# ---------- figure
F.mkdir(parents=True, exist_ok=True)
frows = [{"period": f"{lo}-{hi}", "country": c, "ai_year_standardised": by[(c, f"{lo}-{hi}")]["ai_year_standardised"],
          "std_ci95_low": by[(c, f"{lo}-{hi}")]["std_ci95_low"], "std_ci95_high": by[(c, f"{lo}-{hi}")]["std_ci95_high"],
          "activity_index": by[(c, f"{lo}-{hi}")]["activity_index"]} for lo, hi in L.PERIODS for c in L.COUNTRIES]
L.write_csv(F / "Fig_activity_index_comparators.csv", ["period", "country", "ai_year_standardised", "std_ci95_low", "std_ci95_high", "activity_index"], frows)
colors = {"KZ": "#4c72b0", "UZ": "#dd8452", "AZ": "#55a868", "BY": "#8172b3", "KG": "#937860"}
fig, ax = plt.subplots(figsize=(8, 4.8))
width = 0.16
xs = np.arange(len(L.PERIODS))
for i, c in enumerate(L.COUNTRIES):
    vals = [float(by[(c, f"{lo}-{hi}")]["ai_year_standardised"]) for lo, hi in L.PERIODS]
    los = [float(by[(c, f"{lo}-{hi}")]["std_ci95_low"]) for lo, hi in L.PERIODS]
    his = [float(by[(c, f"{lo}-{hi}")]["std_ci95_high"]) for lo, hi in L.PERIODS]
    err = [[v - a for v, a in zip(vals, los)], [b - v for v, b in zip(vals, his)]]
    ax.bar(xs + (i - 2) * width, vals, width, color=colors[c], label=L.NAMES[c], yerr=err, capsize=2, error_kw={"linewidth": 0.8}, zorder=2)
ax.axhline(1.0, color="#333333", linestyle="--", linewidth=0.9, zorder=3)
ax.set_xticks(xs)
ax.set_xticklabels([f"{lo}–{hi}" for lo, hi in L.PERIODS])
ax.set_ylabel("Activity index, standardised by year")
ax.set_ylim(bottom=0)
ax.legend(frameon=False, fontsize=8, ncol=5, loc="upper left")
fig.tight_layout()
base = F / "Fig_activity_index_comparators"
fig.savefig(str(base) + ".pdf", metadata={"CreationDate": None, "ModDate": None, "Producer": None, "Creator": None})
fig.savefig(str(base) + ".png", dpi=300, metadata={"Software": None})
plt.close(fig)
with Image.open(str(base) + ".png") as im:
    im.convert("RGB").save(str(base) + ".tif", compression="tiff_lzw", dpi=(300, 300))

NUM["T4a"] = [{k: v for k, v in r.items() if not k.startswith("_")} for r in t4a]
NUM["topic_totals"] = {c: sum(CS[c][0].values()) for c in L.COUNTRIES}
NUM["all_totals"] = {c: sum(CS[c][1].values()) for c in L.COUNTRIES}
L.jdump(NUM, L.OUT / "F13_4b_numbers.json")
print("KZ rows equal F13.4:", NUM["KZ_rows_equal_F13_4"], NUM["KZ_check_cells"])
for r in t4a:
    print(r["country"], r["window"], r["activity_index"], r["ai_year_standardised"], r["std_ci95_low"], r["std_ci95_high"])
for r in NUM["T4c"]:
    print("T4c", r)
for r in NUM["T4d"]:
    print("T4d", r)
