"""Phase F13.4b - the report, built from the phase's records. Prose hard-wrapped (<= 25 words a line, gate G2)."""
import sys
sys.dont_write_bytecode = True

import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f134b_lib as L

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
    num = j(L.OUT / "F13_4b_numbers.json")
    stamp = j(L.OUT / "F13_4b_brief_stamp.json")
    ver = rows("phase_F13_4b_independent_verification.csv", L.OUT)
    a = {(r["country"], r["window"]): r for r in num["T4a"]}
    c = {(r["country"], r["window"]): r for r in num["T4c"]}
    d = {(r["country"], r["window"]): r for r in num["T4d"]}
    out = ["# Phase F13.4b - activity index for five countries (KZ, UZ, AZ, BY, KG)\n"]
    status = row["status"] if row else "(dry run - no pending registry row yet)"
    out.append(W(f"Status: {status}. Repository: {stamp['root']} (where PHASE_REGISTRY.csv is; not read, not written). Brief: "
                 f"F13_4b_brief.md (sha256 {stamp['brief_sha256']}). Eleven series in the manifest; all equal its digests: "
                 f"{all(v['equal_manifest'] for v in stamp['series'].values())}. E1 (EID and Year only) equal to README: {stamp['E1_equal_README']}. "
                 "This phase adds tables T4 to F13.4 and changes nothing in F13.4; the forks' folders phase_F13_3 and phase_F13_2c were neither "
                 f"read nor snapshotted. Kazakhstan's rows equal F13.4's T2b/T2d in all {num['KZ_check_cells']} compared cells: {num['KZ_rows_equal_F13_4']}.") + "\n")
    out.append("## 1. Inputs\n")
    out.append(L.md_table(["series", "file", "sha256", "equal_manifest", "sum", "manifest_sum_of_years"],
                          [{"series": k, **v} for k, v in stamp["series"].items()]) + "\n")
    out.append(W("New all-output series (README_exports.txt, section B2): AFFILCOUNTRY(uzbekistan / azerbaijan / belarus / kyrgyzstan) AND "
                 "PUBYEAR > 2002 AND PUBYEAR < 2026, Scopus Analyze, 13 October 2026. Topic series of the four countries and the world as in F13.4; "
                 "Kazakhstan's topic counts are E1 by Year.") + "\n")
    out.append("## 2. Formulas (as in F13.4)\n")
    out.append(bullets([
        "Topic share (per mille) = 1000 x topic / all output of the country (or the world) over the window.",
        "Crude activity index AI = (topic / all) / (topic world / all world), counts summed over the window first.",
        "Year-standardised AI = topic / E, E = sum over the window's years of all_y x (topic world_y / all world_y): the topic records the "
        "country would have at the world's topic share of each year. It removes the effect of a country's output being concentrated in years "
        "when the topic's world share is high.",
        "Stability interval (95 %): 1000 replicates; numpy default_rng(42) afresh per window. Crude: Binomial(all, topic/all) for the "
        "country and Binomial(all world, topic world/all world); standardised: the same draws year by year. Percentiles 2.5 and 97.5.",
    ]))
    out.append("## 3. Tables\n")
    for n in ("T4a_activity_index_five_countries.md", "T4b_topic_share_by_year.md", "T4c_ranking.md", "T4d_without_2025.md"):
        out.append(md(n))
    out.append(W("Check of Kazakhstan's rows against F13.4 (65 cells): tables/T4a_KZ_check_against_F13_4.csv, all equal.") + "\n")
    gap = max(abs(float(r["activity_index"]) - float(r["ai_year_standardised"])) for r in num["T4a"]
              if r["window"] in ("2003-2016", "2017-2021", "2022-2025"))
    para = (f"Reading. Pooled over 2003-2025 the crude index puts Uzbekistan ({a[('UZ', '2003-2025')]['activity_index']}) level with "
            f"Kazakhstan ({a[('KZ', '2003-2025')]['activity_index']}); standardised by year it is {a[('UZ', '2003-2025')]['ai_year_standardised']} "
            f"against {a[('KZ', '2003-2025')]['ai_year_standardised']}, because Uzbekistan's topic output sits even more in the last years "
            f"({d[('UZ', '2003-2024')]['share_2025_of_total_pct']} % in 2025 alone). Within each period the crude and standardised indices "
            f"differ by at most {gap:.3f}; across countries and long windows compare the standardised ones.")
    out.append(W(para) + "\n")

    out.append("## 4. Figure\n")
    out.append(W("Files: figures/Fig_activity_index_comparators.pdf, .png (300 dpi), .tif (300 dpi, LZW, from the PNG); data: "
                 "figures/Fig_activity_index_comparators.csv. Built by programs/f134b_index.py; nobody viewed it (R18). Grouped bars by period, "
                 "whiskers = stability intervals, dashed line at 1.0; no title inside.") + "\n")
    cap = ("Activity index of cybersecurity research in five post-Soviet countries, standardised by year, 2003-2016, 2017-2021 and 2022-2025. "
           "Bars: each country's topic records in Scopus divided by the number expected at the world's topic share of each year, given the "
           "country's whole Scopus output; whiskers: 95 % bootstrap stability intervals; dashed line: the world level (1.0). Source: Scopus, "
           "retrieved 13 October 2026; Authors' own work.")
    out.append("Draft caption:\n\n> " + W(cap).replace("\n", "\n> ") + "\n")

    out.append("## 5. For the professor\n")

    def above(cn, w):
        return c[(cn, w)]["above_world_share"]

    kz1, kz2 = c[("KZ", "2017-2021")], c[("KZ", "2022-2025")]
    uz1, uz2 = c[("UZ", "2017-2021")], c[("UZ", "2022-2025")]
    out.append(bullets([
        f"Above the world share (interval above 1): Kazakhstan since 2017-2021 ({kz1['ai_year_standardised']}, {kz1['std_ci95']}) and in "
        f"2022-2025 ({kz2['ai_year_standardised']}, {kz2['std_ci95']}); Uzbekistan only in 2022-2025 ({uz2['ai_year_standardised']}, "
        f"{uz2['std_ci95']}; 2017-2021 {uz1['ai_year_standardised']}, {above('UZ', '2017-2021')}). Azerbaijan is near the world level "
        f"(2022-2025 {c[('AZ', '2022-2025')]['ai_year_standardised']}, {above('AZ', '2022-2025')}); Kyrgyzstan "
        f"{c[('KG', '2022-2025')]['ai_year_standardised']} ({above('KG', '2022-2025')}); Belarus stays below in every period "
        f"({', '.join(a[('BY', f'{lo}-{hi}')]['ai_year_standardised'] for lo, hi in L.PERIODS)}).",
        f"Kazakhstan ranks first of the five in both 2017-2021 and 2022-2025; its standardised index is {uz1['ratio_KZ_to_country']} times "
        f"Uzbekistan's in 2017-2021 and {uz2['ratio_KZ_to_country']} times in 2022-2025; Uzbekistan is closing the gap but has not passed "
        "Kazakhstan.",
        f"Without 2025 (T4d, 2022-2024): Kazakhstan {d[('KZ', '2022-2024')]['ai_year_standardised']} ({d[('KZ', '2022-2024')]['std_ci95']}), "
        f"Uzbekistan {d[('UZ', '2022-2024')]['ai_year_standardised']} ({d[('UZ', '2022-2024')]['std_ci95']}), so Uzbekistan's place above "
        "the world level rests on 2025, while Kazakhstan's does not; the ranking (Kazakhstan first, Uzbekistan second) does not change.",
        f"Do not quote pooled 2003-2025 crude indices: they favour countries whose output grew late (Uzbekistan {a[('UZ', '2003-2025')]['activity_index']} "
        f"crude, {a[('UZ', '2003-2025')]['ai_year_standardised']} standardised).",
    ]))

    out.append("## 6. Gates\n")
    lines = ["| gate | what | verdict | planted violation caught |", "| --- | --- | --- | --- |"]
    lines += [f"| {g['gate']} | {g['what']} | {g['verdict']} | {g['planted_verdict']} ({g['falsifiability']}) |" for g in gates]
    out.append("\n".join(lines) + "\n")
    first = rows("phase_F13_4b_checkpoint_assertions_first_run.csv", L.OUT)
    if first:
        out.append(W("First run: " + ", ".join(f"{g['gate']} {g['verdict']}" for g in first) + ".") + "\n")
    out.append("## 7. Independent verification\n")
    if ver:
        lines = ["| check | what | tables | recomputed | verdict |", "| --- | --- | --- | --- | --- |"]
        lines += ["| " + " | ".join(" ".join(str(r.get(k, "")).replace("|", "/").split()[:14])[:100] for k in
                                    ("check_id", "what", "expected_from_tables", "recomputed", "verdict")) + " |" for r in ver]
        out.append("\n".join(lines) + "\n")
        out.append(W(f"A subagent wrote its own program (programs/f134b_verify.py) from a description of the method, without reading this "
                     f"phase's other programs: {sum(1 for r in ver if r.get('verdict') == 'PASS')} of {len(ver)} PASS.") + "\n")
    else:
        out.append("(not yet run)\n")
    out.append("## 8. Disclosures\n")
    out.append(bullets([
        "author_exports_2026_10's manifest, README and long file changed after F13.4 closed (the four series were added); the seven series "
        "F13.4 used are unchanged (their digests equal the manifest). F13.4's step-0 snapshot therefore no longer matches those three files; "
        "F13.4 was not rerun.",
        "Additions beyond the brief: crude intervals in T4a (as in F13.4's T2b), a rank and the share of 2025 in T4d, the flag "
        "above_world_share in T4c (from the interval).",
        "Small outputs give wide intervals (Kyrgyzstan; the early period); a lower bound of 0 means some replicates drew no topic record.",
        "T4c's ratio_KZ_to_country divides the printed three-decimal indices (Belarus 2017-2021: 3.10; from unrounded values 3.11, the "
        "verifier's note).",
        "Topic counts of the comparators come from the Scopus interface (Analyze), Kazakhstan's from the export E1; a co-authored "
        "document counts for every country involved.",
        "No network, no heredoc, no workflow or skill; one subagent (the verifier); nothing in .claude/; nothing deleted or moved; "
        "phase_F13_3, phase_F13_2c and PHASE_REGISTRY.csv neither read nor written; CORRECTIONS.csv unchanged (in the snapshot).",
    ]))
    out.append("## 9. Registry row (to be added on the author's command 'реестр')\n")
    if row:
        out.append(W(f"{row['phase_id']} | {row['status']} | produced_numbers {row['produced_numbers']} | safe_to_publish {row['safe_to_publish']} | "
                     f"{row['file_count']} files, {row['bytes']} bytes (the folder's fixed point). Ready row: run_logs/registry_rows_pending.json; "
                     "program: programs/f134b_registry.py (not run in this phase; after the rows phase_F13_5 and phase_F13_4).") + "\n")
        out.append(W("Note of the row: " + row["note"]) + "\n")
    else:
        out.append("(dry run)\n")
    return "\n".join(out)
