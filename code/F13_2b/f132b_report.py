"""Phase F13.2b - the report, built from the phase's records (aggregates only). Prose hard-wrapped (<= 25 words a line, gate G2)."""
import sys
sys.dont_write_bytecode = True

import json
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132b_lib as L
import f132b_thesaurus as TH

W = L.wrap


def j(p):
    return json.loads(Path(p).read_bytes().decode("utf-8"))


def md(name):
    return (L.TABLES / f"{name}.md").read_bytes().decode("utf-8").replace("## ", "### ", 1)


def rows(p):
    return L.read_csv_out(p) if Path(p).exists() else []


def bullets(items, width=22):
    return "\n".join("- " + W(x, width).replace("\n", "\n  ") for x in items) + "\n"


def build(rows_reg, gates):
    n = j(L.OUT / "F13_2b_numbers.json")
    st = j(L.OUT / "F13_2b_brief_stamp.json")
    ver = rows(L.OUT / "phase_F13_2b_independent_verification.csv")
    t1, t2, t3 = n["T1"], n["T2"], n["T3"]
    t2b = rows(L.TABLES / "T2b_partner_countries.csv")
    t2c = {(r["group"], r["value"]): r for r in rows(L.TABLES / "T2c_international_share.csv")}
    t2e = rows(L.TABLES / "T2e_partner_sources.csv")
    t2f2 = {r["period"]: r for r in rows(L.TABLES / "T2f2_collaboration_by_period.csv")}
    t2g = {r["collaboration"]: r for r in rows(L.TABLES / "T2g_authors_by_collaboration.csv")}
    t3a = rows(L.TABLES / "T3a_kz_institutions.csv")
    t3e = rows(L.TABLES / "T3e_foreign_institutions.csv")
    t3f = rows(L.TABLES / "T3f_top10_partner_countries.csv")
    th = rows(L.TABLES / "institutions_thesaurus.csv")
    e1 = st["inputs"]["E1"]
    out = ["# Phase F13.2b - affiliations on the frame E1 (Scopus, 841): countries, collaboration types, Kazakhstan institutions\n"]
    out.append(W(f"Status: {'COMPLETE' if rows_reg else '(dry run)'}. Repository: {st['root']}; the phase registry is "
                 f"{st['registry_location']} (neither read nor written - parallel sessions write it). Brief: F13_2b_brief.md (sha256 "
                 f"{st['brief_sha256']}). No edit to the manuscript or the package; years, types, sources and citations are left to F13.2.") + "\n")
    out.append("## 1. Inputs and rules\n")
    out.append("\n".join(["| input | file | sha256 | check |", "| --- | --- | --- | --- |",
                          f"| E1 | {L.E1} | {e1['sha256']} | equal to README_exports.txt: {e1['equal_readme']}; brief prefix {e1['brief_prefix']}: "
                          f"{e1['equal_brief_prefix']} |",
                          f"| T2b_years | {L.T2B} | {st['inputs']['T2b_years']['sha256']} | annual series of E1, used by gate G3 |"]) + "\n")
    lev = "; ".join(f"{lab}: {' / '.join(w)}" for lab, w in L.LEVELS)
    out.append(bullets([
        "E1 is read with csv.reader (UTF-8 with BOM, field size limit 1 GiB); only the columns EID, Year, Document Type, Source title and "
        "Affiliations leave the parser, and Authors becomes a count of its non-empty ';'-separated items at once. The other columns of a row "
        "are scanned by the CSV reader and dropped with the row.",
        "Affiliation lines: the Affiliations cell split on '; '. Parts of a line: split on ', '. Country = last part; city = the part before "
        "it (not used).",
        "Institution of a line: candidates are all parts except the last two (a line of two parts keeps its first part as the only "
        f"candidate). Levels in order - {lev}. For each level in turn, the first candidate (in line order) holding one of its keywords is "
        "the institution; if no level matches, the first part, flagged 'unresolved'.",
        "Matching is case-insensitive; llp, jsc and ltd are whole words, every other keyword a substring. 'department of' counts as a "
        "government body (the brief: not a university department) only when the same part also holds a state word as a whole word: "
        + ", ".join(L.STATE_WORDS) + ".",
        "Kazakhstan line: last part exactly 'Kazakhstan'. Countries of a record: the set of last parts that are in the country list "
        "(section 2). International record: at least one country other than Kazakhstan.",
        "Normalisation of Kazakhstan institutions (step 3): lowercase; single-letter initials with a period removed (a letter not preceded "
        "by a letter, then '.'); hyphens, dashes (U+2010-U+2014) and periods to spaces; the words 'named after', 'after', 'the' removed; "
        "spaces collapsed. The normalised string is the variant.",
        "Label of a Kazakhstan institution: the canonical name of its variant in the thesaurus; else the canonical name whose normalised "
        "form equals the variant; else the most frequent raw spelling of the variant (ties: first in sorted order).",
        "Foreign institutions (T3e): no thesaurus; lowercase, every character other than a letter, digit or space to a space, spaces "
        "collapsed; grouped within a country; shown in their most frequent spelling.",
        "Collaboration type: international if two or more countries; else domestic multi-institution if two or more Kazakhstan "
        "institutions (labels); else single institution.",
        "Periods 2003-2016 / 2017-2021 / 2022-2025; types mapped case-insensitively (article, review, conference paper, book chapter, "
        "book, retracted). Rankings: count descending, then name ascending.",
    ]))
    out.append("## 2. Country list\n")
    out.append(W(f"The list of country and territory names as Scopus writes them in the last part of an affiliation was built for this phase "
                 f"({len(L.SCOPUS_COUNTRIES)} names; tables/scopus_country_names.csv): " + "; ".join(L.SCOPUS_COUNTRIES) + ".") + "\n")
    out.append(W(f"All {t1['distinct_last_parts']} distinct last parts of E1 are in the list (T1b); the list of last parts outside it, for the "
                 "author, is empty (T1b2).") + "\n")
    out.append("## 3. T1 - parsing\n")
    out += [md("T1a_counts"), md("T1a2_lines_per_record"), md("T1a3_rule_levels"), md("T1a4_parts_per_line"), md("T1b_last_parts"),
            md("T1b2_last_parts_not_in_list"), md("T1c_unresolved_counts"), md("T1c2_unresolved_first_parts")]
    out.append("## 4. T2 - countries and collaboration\n")
    out += [md("T2a_countries_per_record"), md("T2b_partner_countries"), md("T2c_international_share"), md("T2d_partner_country_pairs"),
            md("T2e_partner_sources"), md("T2f_collaboration_by_year"), md("T2f2_collaboration_by_period"), md("T2g_authors_by_collaboration")]
    out.append("## 5. T3 - Kazakhstan institutions\n")
    out.append("### Institutions thesaurus (tables/institutions_thesaurus.csv, in full)\n")
    out.append(W(f"{len(th)} rows: one decision for each of the {t3['variants_2plus']} variants (of {t3['variants']}) that occur in two or "
                 f"more records - {t3['merge_rows']} merges into another institution's canonical name and {t3['keep_rows']} kept as distinct "
                 "institutions under their canonical name (whose normalised form is the variant itself). One-record variants join a canonical "
                 "name only when their normalised form equals it; all others stay as they are (sensitivity S1). Canonical names are the "
                 "current full English names from the executor's knowledge (no network); confidence high / medium / low. Integrity: no merge "
                 "variant equals a normalised canonical name (from and to disjoint), so no chain; every variant occurs in E1.") + "\n")
    out.append(L.md_table(["variant", "canonical", "rule", "records", "confidence", "reason"], th) + "\n")
    out += [md("T3a_kz_institutions"), md("T3b_institution_types"), md("T3c_concentration"), md("T3d_kz_institution_pairs"),
            md("T3e_foreign_institutions"), md("T3f_top10_partner_countries")]
    s1 = rows(L.TABLES / "S1_one_record_token_variants.csv")
    g = defaultdict(int)
    for r in s1:
        g[r["would_join"]] += 1
    out.append("### S1 - sensitivity (not applied): one-record variants that carry a canonical name's token\n")
    out.append(W(f"{len(s1)} one-record variants share a distinctive token with a canonical name but stay as they are (the brief merges "
                 f"one-record variants only by equality after normalisation). Merged by token, they would move {t3['S1_changed_records']} "
                 "records from domestic multi-institution to single institution; the top-30 counts would rise by at most the numbers below. "
                 "Every variant is listed in tables/S1_one_record_token_variants.csv.") + "\n")
    out.append(L.md_table(["would_join", "variants"], [{"would_join": k, "variants": v} for k, v in sorted(g.items(), key=lambda kv: (-kv[1], kv[0]))]) + "\n")
    out.append(W(f"S2 (not applied): if the {sum(1 for x in TH.ROWS if x[4] == TH.UNIT)} kept units without a parent name (departments, "
                 f"schools, a city) were not counted as institutions, {t3['S2_unit_only_changed_records']} records would move from domestic "
                 "multi-institution to single institution.") + "\n")
    out.append("## 6. For the author\n")
    unres = [r for r in rows(L.TABLES / "T1c2_unresolved_first_parts.csv") if int(r["lines"]) >= 2]
    out.append(bullets([
        f"Unresolved institutions: {t1['unresolved']} lines ({t1['unresolved_kz']} in Kazakhstan); the {len(unres)} first parts with two or "
        "more lines are listed in T1c2 (section 3), all of them in tables/T1c2_unresolved_first_parts.csv.",
        "Last parts outside the country list: none (T1b2 is empty).",
        f"Thesaurus decisions of low confidence ({t3['low_confidence']}) and medium confidence ({t3['medium_confidence']}) are marked in the "
        "confidence column; they are the ones to confirm.",
    ]))
    out.append("## 7. Figure\n")
    out.append(W("figures/Fig_collaboration_type_by_year.pdf, .png and .tif (300 dpi; TIFF with LZW), data in "
                 "figures/Fig_collaboration_type_by_year.csv (= T2f by year). Built by programs/f132b_affil.py; not viewed (R18). Stacked "
                 "bars 2003-2025, segments in the fixed order single institution (light blue #9ecae1), domestic multi-institution (blue "
                 "#3182bd), international (orange #e6550d); no title inside.") + "\n")
    out.append(W(f"Draft caption: Figure X. Collaboration type of Kazakhstan's cybersecurity publications by year, 2003-2025 (Scopus, n = 841). "
                 "Single institution: one Kazakhstan institution and no foreign country; domestic multi-institution: two or more Kazakhstan "
                 "institutions and no foreign country; international: at least one foreign country. Institutions after harmonising name "
                 f"variants ({len(th)} thesaurus decisions). Source: Scopus export of 13 October 2026.") + "\n")
    out.append("## 8. For the professor\n")
    tp = {r["country"]: r for r in t2b[:5]}
    ukr = next(r for r in t2e if r["country"] == "Ukraine" and r["rank"] == "1")
    yu = next(r for r in t3a if r["institution"] == TH.YU)
    yu_ua = next(r for r in t3f if r["institution"] == TH.YU and r["rank"] == "1")
    nu = next(r for r in t3a if r["institution"] == TH.NU)
    other_top = ", ".join(f"{r['country']} {r['records']}" for r in t2b[1:5])
    prof = [
        f"International records are {t2['international_pct']} % of the corpus ({t2['international']} of 841): "
        f"{t2c[('period', '2003-2016')]['share_international_pct']} % in 2003-2016, {t2c[('period', '2017-2021')]['share_international_pct']} % "
        f"in 2017-2021 and {t2c[('period', '2022-2025')]['share_international_pct']} % in 2022-2025; the recent fall is relative - domestic "
        f"multi-institution work rose from {t2f2['2017-2021']['domestic multi-institution %']} % to {t2f2['2022-2025']['domestic multi-institution %']} %.",
        f"Ukraine is the partner by far ({tp['Ukraine']['records']} records, {tp['Ukraine']['share_of_841_pct']} %), then {other_top}. "
        f"{ukr['records']} of the Ukrainian joint records ({ukr['share_of_country_pct']} %) are in {ukr['source_title']}; the top foreign "
        f"institutions are Ukrainian ({t3e[0]['institution']} {t3e[0]['records']}, {t3e[1]['institution']} {t3e[1]['records']}).",
        f"Collaboration is carried by a few pairings: {yu['international']} of {yu['records']} {TH.YU} records are international, "
        f"{yu_ua['records']} of them with Ukraine; {TH.NU} is {nu['share_international_pct']} % international, mainly with "
        + ", ".join(f"{r['partner_country']} ({r['records']})" for r in t3f if r["institution"] == TH.NU) + ".",
        f"Concentration: {t3['institutions']} Kazakhstan institutions after the thesaurus, {t3['one_record']} of them with one record; the top "
        f"five hold {t3['top5_links_pct']} % of institution-record links and appear in {L.pct(t3['top5_records'], 841)} % of the records, the "
        f"top ten in {L.pct(t3['top10_records'], 841)} %.",
        f"Types: single institution {t2f2['2003-2025']['single institution %']} %, domestic multi-institution "
        f"{t2f2['2003-2025']['domestic multi-institution %']} %, international {t2f2['2003-2025']['international %']} %; mean authors "
        f"{t2g['single institution']['authors_mean']} / {t2g['domestic multi-institution']['authors_mean']} / {t2g['international']['authors_mean']}.",
        "Uncertain in the thesaurus: 'Kazakh National University' read as al-Farabi KazNU "
        f"({next(r['records'] for r in th if r['variant'] == 'kazakh national university')} records); 'Abay University' as Abai KazNPU; "
        "'Almaty University of Energy and Communications' as AUPET; 'South Kazakhstan State University' as Auezov; Energo University, "
        "Almaty Academy and Kazakh University of Economics kept as written.",
        f"{sum(1 for x in TH.ROWS if x[4] == TH.UNIT)} units without a parent name (departments, schools, a city) are kept as institutions; "
        f"{t3['S1_variants']} one-record spelling "
        f"variants are not merged. Both choices move only {t3['S1_changed_records']} and {t3['S2_unit_only_changed_records']} records between "
        "collaboration types. Foreign institutions are not harmonised.",
    ]
    out.append(bullets(prof))
    out.append("## 9. Gates\n")
    lines = ["| gate | what | verdict | planted violation caught |", "| --- | --- | --- | --- |"]
    lines += [f"| {g['gate']} | {g['what']} | {g['verdict']} | {g['planted_verdict']} ({g['falsifiability']}) |" for g in gates]
    out.append("\n".join(lines) + "\n")
    first = rows(L.OUT / "phase_F13_2b_checkpoint_assertions_first_run.csv")
    if first:
        out.append(W("First run: " + ", ".join(f"{g['gate']} {g['verdict']}" for g in first) + ".") + "\n")
    out.append("## 10. Independent verification\n")
    if ver:
        lines = ["| check | what | tables | recomputed | verdict |", "| --- | --- | --- | --- | --- |"]
        lines += ["| " + " | ".join(" ".join(str(r.get(k, "")).split()[:28]) for k in ("check_id", "what", "expected_from_tables", "recomputed", "verdict")) + " |"
                  for r in ver]
        out.append("\n".join(lines) + "\n")
        out.append(W(f"A subagent wrote its own program (programs/f132b_verify.py) from a description of the rules, without reading this "
                     f"phase's other programs: {sum(1 for r in ver if r.get('verdict') == 'PASS')} of {len(ver)} PASS.") + "\n")
    else:
        out.append("(not yet run)\n")
    out.append("## 11. Disclosures\n")
    out.append(bullets(disclosures(t1)))
    if rows_reg:
        out.append("## 12. Registry row (to be added on the author's command, after the rows of the other sessions)\n")
        for r in rows_reg:
            out.append(W(f"{r['phase_id']} | {r['status']} | produced_numbers {r['produced_numbers']} | safe_to_publish {r['safe_to_publish']} | "
                         f"{r['file_count']} files, {r['bytes']} bytes | path {r['path']}") + "\n")
        out.append(W("The row is kept, unwritten, in run_logs/registry_rows_pending.json with its file count and bytes at the folder's fixed "
                     "point. In this session the rows phase_F12_4, phase_F13_1 and phase_F13_2 are also pending; on 'реестр' they go first, "
                     "in that order, and phase_F13_2b after the row of phase F13.5 (other session).") + "\n")
    return "\n".join(out)


def disclosures(t1):
    return [
    "The brief names F13.2 as a parallel session; F13.2 was in fact closed earlier in this same session (13 October). As the brief asks, "
    "phase_F13_2/ was neither read nor touched by this phase and is not in the step-0 snapshot; nothing from it is used.",
    "A structure probe (programs/f132b_probe.py: counts, last parts, institution strings; written to run_logs/) ran after step 0 and again "
    "after the 'department of' refinement below; it read no author field.",
    "Refinements the brief's words leave open, chosen by the executor: a two-part line keeps its first part as candidate; llp, jsc, ltd "
    "as whole words; dashes U+2010-U+2014 treated as hyphens; 'department of' needs a state word.",
    "The first analysis run counted every 'Department of ...' part as a government body (88 lines); the brief excludes university "
    f"departments, so the state-word condition was added before the gates ran ({t1['levels'].get('L5 government body', 0)} lines remain "
    f"at that level, {t1['unresolved']} lines are unresolved). The Kazakhstan variants and the thesaurus were unchanged by it.",
    "T3b keywords beyond the brief's six types are the executor's (college, school, lyceum, gymnasium; observatory; inc, bank, holding; "
    "akimat, government); names that open as an academic unit are typed 'other'.",
    "Canonical names come from the executor's knowledge without a network check; renamings (e.g. Satbayev, Yessenov, SDU, Toraighyrov, "
    "Buketov, Narikbayev) should be confirmed by the author before publication.",
    "Branch campuses written with Kazakhstan (De Montfort University, Heriot-Watt University Aktobe Campus) are Kazakhstan institutions here; "
    "one Kazakhstan line names the University of Jordan (one record, kept as written).",
    "Foreign institutions are not harmonised: e.g. 'University of Science and Technology' (China) is apart from 'University of Science and "
    "Technology Beijing' where the city stands as its own part.",
    "Authors counts: no record lacks author names; the count is the number of ';'-separated items in Authors, which is never stored or printed.",
    "The PDF is written without a creation date, so it is byte-stable; the figure was not opened or viewed (R18).",
    "Every program installs an audit hook that refuses deleting, moving or linking (R17); nothing was deleted or moved. Console output is "
    "ASCII only (the Windows console is cp1251).",
    "Heredoc: one shell command of the executor (a search of the report builder for hard-coded numbers) carried by mistake an empty "
    "heredoc fed to the interpreter; it held no code, ran nothing and wrote nothing. No other heredoc was used.",
    "No network module in programs/ (G6); no workflow or skill; one subagent (the verifier); nothing in .claude/; CORRECTIONS.csv "
    "unchanged; PHASE_REGISTRY.csv, phase_F13_2 and phase_F13_5 neither read nor written; .gitignore unchanged.",
    ]
