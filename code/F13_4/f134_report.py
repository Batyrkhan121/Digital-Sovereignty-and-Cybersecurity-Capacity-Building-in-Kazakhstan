"""Phase F13.4 - the report, built from the phase's records. Prose hard-wrapped (<= 25 words a line, gate G2)."""
import sys
sys.dont_write_bytecode = True

import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f134_lib as L

W = L.wrap


def j(p):
    return json.loads(Path(p).read_bytes().decode("utf-8"))


def md(name):
    return (L.TABLES / name).read_bytes().decode("utf-8").replace("## ", "### ", 1)


def rows(name, folder=None):
    p = (folder or L.TABLES) / name
    return L.read_csv_path(p) if p.exists() else []


def bullets(items, width=22):
    return "\n".join("- " + W(x, width).replace("\n", "\n  ") for x in items) + "\n"


def build(row, gates):
    num = j(L.OUT / "F13_4_numbers.json")
    stamp = j(L.OUT / "F13_4_brief_stamp.json")
    ver = rows("phase_F13_4_independent_verification.csv", L.OUT)
    t1c = {r["window"].split(" ")[0]: r for r in num["T1c"]}
    t1d = num["T1d"]
    t2b = {r["window"]: r for r in num["T2b"]}
    t2d = {r["window"].split(" ")[0]: r for r in num["T2d"]}
    t3b = {r["period"]: r for r in num["T3b"]}
    t3c = {r["country"]: r for r in num["T3c"]}
    t3d = {r["country"]: r for r in num["T3d"]}
    out = ["# Phase F13.4 - growth and normalised activity from Scopus year series\n"]
    status = row["status"] if row else "(dry run - no pending registry row yet)"
    out.append(W(f"Status: {status}. Repository: {stamp['root']} (where PHASE_REGISTRY.csv is; the registry was neither read nor written by "
                 f"this phase). Brief: F13_4_brief.md (sha256 {stamp['brief_sha256']}). E1: sha256 {stamp['E1_sha256']} (equal to "
                 f"README_exports.txt: {stamp['E1_equal_README']}); only EID and Year read. The seven series equal the manifest's digests: "
                 f"{all(v['equal_manifest'] for v in stamp['series'].values())}. No edit to the manuscript or the package; the parallel "
                 "sessions' folders phase_F13_3 and phase_F13_6a were neither read nor snapshotted. Table T5 of F13.1 is recomputed here from "
                 "scratch and replaced (T2a-T2d).") + "\n")

    out.append("## 1. Inputs\n")
    out.append(L.md_table(["series", "file", "sha256", "equal_manifest", "manifest_sum_of_years"],
                          [{"series": k, **v} for k, v in stamp["series"].items()]) + "\n")
    out.append(W("Queries verbatim: author_exports_2026_10/README_exports.txt and manifest_year_series.json (Scopus Analyze search results, "
                 "13 October 2026). Topic query: TITLE-ABS-KEY(cybersecurity OR \"information security\" OR \"cyber defense\" OR \"cyber "
                 "defence\" OR \"network security\" OR cryptography), years 2003-2025; country series add AFFILCOUNTRY. Topic KZ is E1 "
                 "itself (841 records), counted by Year.") + "\n")

    out.append("## 2. Formulas\n")
    out.append(bullets([
        "Moving average (T1a): centred, (n_{t-1} + n_t + n_{t+1}) / 3; none for 2003 and 2025.",
        "Log-linear fit (T1c): ordinary least squares of ln(n_t) = a + b t, t = year - first year of the window; years with n_t = 0 "
        "excluded. Annual growth = e^b - 1; doubling time = ln 2 / b; R^2 on the log scale.",
        "Topic share (per mille): 1000 x topic / all. Activity index AI = (topic KZ / all KZ) / (topic world / all world) = (topic KZ / "
        "topic world) / (all KZ / all world). For a window the counts are summed first.",
        "Year-standardised AI (addition): topic KZ / E, with E = sum over the window's years of all KZ_y x (topic world_y / all world_y), "
        "the number of topic records Kazakhstan would have with the world's topic share of each year (indirect standardisation).",
        num["bootstrap"]["rule"],
    ]))

    out.append("## 3. Growth (T1)\n")
    for n in ("T1a_years.md", "T1b_periods.md", "T1c_loglinear_fit.md", "T1d_recent_weight.md"):
        out.append(md(n))

    out.append("## 4. Normalisation (T2)\n")
    for n in ("T2a_normalised_by_year.md", "T2b_activity_index_periods.md", "T2c_shares_of_world.md", "T2d_activity_index_windows.md"):
        out.append(md(n))
    full = t2b["2003-2025"]
    para = (f"Reading. For 2003-2025 the AI is {full['activity_index']} (interval {full['ci95_low']}-{full['ci95_high']}), as F13.1's T5 "
            f"found (1.899). Yet every period is lower: {', '.join(t2b[p]['activity_index'] for p, _, _ in L.PERIODS)} for "
            f"{', '.join(p for p, _, _ in L.PERIODS)}. The pooled value is raised by timing, not by specialisation: Kazakhstan's output is "
            f"concentrated in recent years ({t2b['2022-2025']['all_KZ']} of {full['all_KZ']} documents in 2022-2025), when the topic's world "
            f"share is highest ({t2b['2022-2025']['share_topic_in_world_permille']} per mille against {t2b['2003-2016']['share_topic_in_world_permille']} "
            f"in 2003-2016), while the pooled world share is weighted towards earlier, lower years. Standardised by year, the AI for 2003-2025 "
            f"is {full['ai_year_standardised']} ({full['std_ci95_low']}-{full['std_ci95_high']}); since 2017 crude and standardised values "
            f"agree near 1.5-1.6 (T2d). The figure to quote is about 1.5 for 2017-2025, not 1.9.")
    out.append(W(para) + "\n")

    out.append("## 5. Comparators (T3)\n")
    for n in ("T3a_comparators_by_year.md", "T3b_comparators_by_period.md", "T3c_growth_by_country.md", "T3d_without_2025.md"):
        out.append(md(n))
    uz = t3d["UZ"]
    para = (f"Caution. Uzbekistan's {uz['total_2003_2025']} topic records include {uz['records_2025']} from 2025 alone ({uz['share_2025_pct']} %); "
            f"without 2025 its growth from 2017-2021 to 2022-2024 is x{uz['ratio_means_2017_2021_to_2022_2024']} by annual means (x"
            f"{t3c['UZ']['ratio_means']} with 2025) and its share of the five over 2022-2024 is {uz['share_of_five_2022_2024_pct']} %. A "
            "one-year surge can reflect a few large conference volumes or collaborations rather than a lasting change. The author's "
            "observation in the Scopus Analyze interface - that the 2025 surge consists mainly of conference papers and of co-authorships "
            "with India and Iraq - was not checked in this phase and is in no table. Azerbaijan and Kyrgyzstan also have a third to a half of "
            f"their records in 2025 ({t3d['AZ']['share_2025_pct']} %, {t3d['KG']['share_2025_pct']} %); Kazakhstan {t3d['KZ']['share_2025_pct']} %, "
            f"Belarus {t3d['BY']['share_2025_pct']} %.")
    out.append(W(para) + "\n")

    out.append("## 6. Figure\n")
    out.append(W("Files: figures/Fig_normalised_growth.pdf, .png (300 dpi), .tif (300 dpi, LZW, from the PNG); data: "
                 "figures/Fig_normalised_growth.csv. Built by programs/f134_growth.py; nobody viewed it (R18). No titles inside; the panels "
                 "carry the letters (a) and (b) for the caption.") + "\n")
    cap = ("Growth and normalised activity of cybersecurity research in Kazakhstan, 2003-2025. (a) Kazakh records on the topic per year "
           "(bars, left axis) and the topic's share of Kazakhstan's total Scopus output (line, per mille, right axis). (b) Topic records per "
           "year for Kazakhstan, Uzbekistan, Azerbaijan, Belarus and Kyrgyzstan (same query with each country's affiliation; co-authored "
           "documents count for every country). Source: Scopus, retrieved 13 October 2026; Authors' own work.")
    out.append("Draft caption:\n\n> " + W(cap).replace("\n", "\n> ") + "\n")

    out.append("## 7. For the professor\n")
    a, b, c = t1c["2011-2025"], t1c["2017-2025"], t1c["2011-2024"]
    s17, s22, s24 = t2d["2017-2025"], t2d["2022-2025"], t2d["2003-2024"]
    tot5 = t3b["2003-2025"]
    out.append(bullets([
        f"Growth: {a['annual_growth_pct']} % a year over 2011-2025 (doubling every {a['doubling_time_years']} years, R^2 {a['r_squared']}); "
        f"{b['annual_growth_pct']} % over 2017-2025 (doubling {b['doubling_time_years']} years); without 2025 {c['annual_growth_pct']} %. "
        f"2024-2025 hold {t1d[0]['value']} % of all records; 2025 has {t1d[1]['value']} times the records of 2020.",
        f"Activity index: {full['activity_index']} for 2003-2025 pooled, but {full['ai_year_standardised']} standardised by year; by period "
        f"{', '.join(t2b[p]['activity_index'] for p, _, _ in L.PERIODS)}. Write 'about 1.5 times the world share since 2017' - "
        f"2017-2025 {s17['activity_index']} ({s17['ai_year_standardised']} standardised), 2022-2025 {s22['activity_index']} "
        f"({s22['ai_year_standardised']}); 2003-2024 (without 2025) {s24['activity_index']} pooled, {s24['ai_year_standardised']} standardised.",
        f"Topic share of Kazakhstan's output: {t2b['2003-2016']['share_topic_in_KZ_permille']} -> {t2b['2017-2021']['share_topic_in_KZ_permille']} -> "
        f"{t2b['2022-2025']['share_topic_in_KZ_permille']} per mille by period; the world's: {t2b['2003-2016']['share_topic_in_world_permille']} -> "
        f"{t2b['2017-2021']['share_topic_in_world_permille']} -> {t2b['2022-2025']['share_topic_in_world_permille']}.",
        f"Comparators show size and pace: Kazakhstan has {tot5['KZ_share_pct']} % of the five countries' topic records (2003-2025), "
        f"Uzbekistan {tot5['UZ_share_pct']} %; growth 2017-2021 -> 2022-2025 by annual means: KZ x{t3c['KZ']['ratio_means']}, UZ "
        f"x{t3c['UZ']['ratio_means']}, AZ x{t3c['AZ']['ratio_means']}, BY x{t3c['BY']['ratio_means']}, KG x{t3c['KG']['ratio_means']}; "
        f"Uzbekistan's 2025 alone is {uz['share_2025_pct']} % of its total.",
        "What comparators cannot show: there are no 'all output' series for UZ, AZ, BY or KG, so no activity index for them - their counts "
        "mix national output size with topic focus; co-authored documents count for each country.",
    ]))

    out.append("## 8. Gates\n")
    lines = ["| gate | what | verdict | planted violation caught |", "| --- | --- | --- | --- |"]
    lines += [f"| {g['gate']} | {g['what']} | {g['verdict']} | {g['planted_verdict']} ({g['falsifiability']}) |" for g in gates]
    out.append("\n".join(lines) + "\n")
    first = rows("phase_F13_4_checkpoint_assertions_first_run.csv", L.OUT)
    if first:
        out.append(W("First run: " + ", ".join(f"{g['gate']} {g['verdict']}" for g in first) + ".") + "\n")
    out.append("## 9. Independent verification\n")
    if ver:
        lines = ["| check | what | tables | recomputed | verdict |", "| --- | --- | --- | --- | --- |"]
        lines += ["| " + " | ".join(" ".join(str(r.get(k, "")).replace("|", "/").split()[:14])[:100] for k in
                                    ("check_id", "what", "expected_from_tables", "recomputed", "verdict")) + " |" for r in ver]
        out.append("\n".join(lines) + "\n")
        out.append(W(f"A subagent wrote its own program (programs/f134_verify.py) from a description of the method, without reading this "
                     f"phase's other programs: {sum(1 for r in ver if r.get('verdict') == 'PASS')} of {len(ver)} PASS.") + "\n")
    else:
        out.append("(not yet run)\n")

    out.append("## 10. Disclosures\n")
    out.append(bullets([
        "Additions beyond the brief, each declared: the year-standardised AI with its interval (T2b, T2d), because the pooled AI of "
        "2003-2025 exceeds every period's AI (time-composition effect); a third fit without 2025 in T1c; T3d for all five countries.",
        "Bootstrap: the brief asks for a record bootstrap. Resampling E1's records alone would leave a window's count fixed (no interval), "
        "so each replicate resamples the window's whole Kazakh output and the world's output; the binomial draw is the exact count "
        "distribution of such a resample. A bootstrap of annual counts was not used (23 non-exchangeable years).",
        "The intervals describe the stability of an index computed on a census, not sampling error; the world term contributes almost "
        "nothing to their width.",
        "T1b prints two ratios because the periods have 14, 5 and 4 years; the annual-mean ratio is the comparable one.",
        "Comparator counts come from the Scopus interface (Analyze), E1 from the export; both were taken on 13 October 2026 with the same "
        "topic query. Overlaps between countries are not removed (no record lists for UZ, AZ, BY, KG).",
        "The Uzbekistan composition remark (conference papers; co-authorship with India and Iraq) is the author's interface observation, "
        "repeated in the text only as such; nothing in this phase tests it.",
        "F13.1's table T5 is replaced; its 1.899 is reproduced (T2b 2003-2025) and qualified by the year-standardised index.",
        "No network, no heredoc, no workflow or skill; one subagent (the verifier); nothing in .claude/; nothing deleted or moved; "
        "phase_F13_3, phase_F13_6a and PHASE_REGISTRY.csv neither read nor written; CORRECTIONS.csv unchanged (in the snapshot).",
    ]))

    out.append("## 11. Registry row (to be added on the author's command 'реестр')\n")
    if row:
        out.append(W(f"{row['phase_id']} | {row['status']} | produced_numbers {row['produced_numbers']} | safe_to_publish {row['safe_to_publish']} | "
                     f"{row['file_count']} files, {row['bytes']} bytes (the folder's fixed point). Ready row: run_logs/registry_rows_pending.json; "
                     "program: programs/f134_registry.py (not run in this phase).") + "\n")
        out.append(W("Note of the row: " + row["note"]) + "\n")
    else:
        out.append("(dry run)\n")
    return "\n".join(out)
