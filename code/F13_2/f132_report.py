"""Phase F13.2 - the report, built from the phase's records (aggregates only). Prose hard-wrapped (<= 25 words a line, gate G2)."""
import sys
sys.dont_write_bytecode = True

import csv
import io
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132_lib as L

W = L.wrap


def j(p):
    return json.loads(Path(p).read_bytes().decode("utf-8"))


def md(name):
    return (L.TABLES / f"{name}.md").read_bytes().decode("utf-8").replace("## ", "### ", 1)


def rows(p):
    return list(csv.DictReader(io.StringIO(Path(p).read_bytes().decode("utf-8"), newline=""))) if Path(p).exists() else []


def csv_md(title, path, note=""):
    r = rows(path)
    return f"### {title}\n\n" + (W(note) + "\n\n" if note else "") + (L.md_table(list(r[0].keys()), r) if r else "(none)") + "\n"


def bullets(items, width=22):
    return "\n".join("- " + W(x, width).replace("\n", "\n  ") for x in items) + "\n"


def tv(name, key_col, key, val_col):
    return next((r[val_col] for r in rows(L.TABLES / f"{name}.csv") if r[key_col] == key), "")


def build(rows_reg, gates):
    n = j(L.OUT / "F13_2_numbers.json")
    st = j(L.OUT / "F13_2_brief_stamp.json")
    ver = rows(L.OUT / "phase_F13_2_independent_verification.csv")
    out = ["# Phase F13.2 - structural indicators on the new frame E1 (Scopus, 841); Web of Science as validation\n"]
    out.append(W(f"Status: {'COMPLETE' if rows_reg else '(dry run)'}. Repository: {st['root']} (where PHASE_REGISTRY.csv is; the registry and phase_F12_3c "
                 f"were neither read nor written - a parallel session writes them). Brief: F13_2_brief.md (sha256 {st['brief_sha256']}). No edit to the "
                 "manuscript or the package; the merged corpus M was not read; affiliations and countries are left to F13.2b.") + "\n")
    out.append("## 1. Inputs\n")
    lines = ["| input | file | sha256 | check |", "| --- | --- | --- | --- |"]
    for k, v in st["inputs"].items():
        chk = f"equal to the brief: {v['equal']}" + (f"; in README_exports.txt: {v['in_README']}" if "in_README" in v else "")
        lines.append(f"| {k} | {v['file']} | {v['sha256']} | {chk} |")
    for rel, sha in sorted(st["tables_read"].items()):
        lines.append(f"| table | {rel} | {sha} | read |")
    out.append("\n".join(lines) + "\n")
    out.append("Rules:\n")
    out.append(bullets([
        "E1 columns taken (whitelist): " + ", ".join(L.E1_KEEP) + "; 'Authors' only counted (';'-separated names), never kept. WoS: UT, PY, DT, TC only.",
        "Harmonised Scopus type: the exported Document Type lowercased - article, conference paper, book chapter, review, book, retracted (its own "
        "category, not 'other').",
        "WoS type (T5a): Retracted Publication -> retracted (flag); else Review -> review; Proceedings Paper -> conference paper; Book Chapter -> "
        "book chapter; otherwise article.",
        "Periods: 2003-2016, 2017-2021, 2022-2025. Citations: Scopus 'Cited by' of 2026-10-13; age = 2026 - year; h-index over the 841 records.",
        "Bradford zones: sources ranked by records (then name); a source belongs to zone 1 while the cumulative count before it is below N/3, to "
        "zone 2 while below 2N/3, else zone 3.",
        "Conference series: leading year, ordinal numbers (5th, XIX) and years removed, spaces collapsed; an acronym with a year after the last comma "
        "becomes the series key (rules R1-R7 and the thesaurus below).",
        "Funders: Funding Details split on '; '; funder = text before the first comma; counted once per record; thesaurus below.",
    ]))
    out.append("## 2. T1 - years and types\n")
    out += [md(x) for x in ("T1a_years", "T1b_types_exported", "T1b_types_harmonised", "T1c_year_by_type", "T1d_periods", "T1e_authors_per_record",
                            "T1f_language", "T1f_publication_stage", "T1g_retracted")]
    out.append("## 3. T2 - sources\n")
    out += [md(x) for x in ("T2a_sources", "T2a_concentration", "T2b_top20_journals", "T2c_top20_conference_sources", "T2d_publishers",
                            "T2e_series_decisions")]
    out.append(csv_md("Conference-series thesaurus (tables/conference_series_thesaurus.csv, complete)", L.TABLES / "conference_series_thesaurus.csv"))
    out += [md("T2e_top15_series"), md("T2e_remainder")]
    out.append("## 4. T3 - citations (Scopus 'Cited by', 2026-10-13)\n")
    out += [md(x) for x in ("T3a_citations", "T3b_citations_by_year", "T3c_citations_by_type", "T3d_citations_by_period", "T3e_top20_cited",
                            "T3f_top10_sources_by_citations")]
    out.append("## 5. T4 - open access and funding\n")
    out += [md("T4a_open_access"), md("T4b_funding")]
    out.append(csv_md("Funders thesaurus (tables/funders_thesaurus.csv, complete)", L.TABLES / "funders_thesaurus.csv"))
    out.append(md("T4c_top15_funders"))
    out.append(W("Raw first elements with their record counts: tables/T4c_funder_variants_raw.csv. Ministries named without a country (e.g. 'Ministry "
                 "of Education and Science', 'Ministry of Digital Development') are left unmerged.") + "\n")
    out.append("## 6. T5 - Web of Science validation (216 pairs)\n")
    out += [md(x) for x in ("T5a_types", "T5b_years", "T5c_citations", "T5d_top20_overlap")]
    out.append("## 7. Deltas against phase F12.1 (September frame)\n")
    d4 = n["D4_total"]
    t1b = n["T1b"]["exported"]
    reads = {
        "D1_types": f"Reading: Article {tv('D1_types', 'doc_type_E1', 'Article', 'n_F12_1')} -> {t1b.get('Article')}, conference papers "
                    f"{tv('D1_types', 'doc_type_E1', 'Conference paper', 'n_F12_1')} -> {t1b.get('Conference paper')}, retracted "
                    f"{tv('D1_types', 'doc_type_E1', 'Retracted', 'n_F12_1')} -> {t1b.get('Retracted')}; the changes come from the three records that "
                    "left and the three that entered (on the 838 common records the types agree).",
        "D2_top20_sources": "Reading: the top 20 are the same sources in the same order; only CEUR Workshop Proceedings gains one record.",
        "D3_year_by_type": "Reading: four annual totals move by one (2012 +1, 2016 -1, 2021 -1, 2024 +1), all from the frame change.",
        "D4_citations_by_year": f"Reading: citations rise from {d4['citations_F12_1']} to {d4['citations_E1']} (+{d4['difference']}): {d4['growth_common_838']} "
                                f"from six weeks of growth on the 838 common records, {d4['plus_entered_3']} brought by the entering records, "
                                f"{d4['minus_left_3']} lost with the leaving ones.",
        "D5_language_oa": "Reading: the counts differ mainly because the fields differ (Abstract Retrieval language code and openaccessFlag against the "
                          "export's language and Open Access columns); the manuscript should quote the E1 values.",
    }
    for k, r in reads.items():
        out.append(md(k))
        out.append(W(r) + "\n")
    out.append("## 8. Figure\n")
    out.append(W("Files: figures/Fig_annual_output_by_type.pdf, .png (300 dpi), .tif (300 dpi, LZW); data figures/Fig_annual_output_by_type.csv (= T1c). "
                 "Built by programs/f132_structure.py; nobody viewed it (R18). No title inside. Colours: " +
                 ", ".join(f"{k} {v}" for k, v in n["figure"]["colors"].items()) + ".") + "\n")
    t1d = {r["period"]: r for r in rows(L.TABLES / "T1d_periods.csv")}
    cap = (f"Annual number of Kazakhstan-affiliated cybersecurity publications in Scopus, 2003-2025 (n = {n['N']}; export of 13 October 2026, query "
           "TITLE-ABS-KEY on cybersecurity, information security, cyber defence, network security and cryptography with AFFILCOUNTRY Kazakhstan), "
           "by document type. Source: Authors' own work.")
    out.append("Draft caption:\n")
    out.append("> " + W(cap).replace("\n", "\n> ") + "\n")
    out.append("## 9. For the professor\n")
    t3a, t5 = n["T3a"], n["T5"]
    conc = {r["measure"]: r["value"] for r in rows(L.TABLES / "T2a_concentration.csv")}
    top_f = n["T4c"]["top15"][0]
    pub = rows(L.TABLES / "T2d_publishers.csv")[:3]
    prof = [
        f"Numbers that change in the manuscript (D1-D5): types {tv('D1_types', 'doc_type_E1', 'Article', 'n_F12_1')}/"
        f"{tv('D1_types', 'doc_type_E1', 'Conference paper', 'n_F12_1')} -> {t1b.get('Article')}/{t1b.get('Conference paper')} articles/conference "
        f"papers; four annual counts by one; citations {d4['citations_F12_1']} -> {d4['citations_E1']}; language and OA must be re-quoted from E1 "
        f"(English {n['T1f']['language'].get('English')}, OA {n['T4a']['oa']}); the top 20 sources are unchanged.",
        f"New descriptive evidence: h-index {t3a['h-index of the corpus']}; median {t3a['median']} citations, {t3a['uncited (%)']} % uncited; funding "
        f"details in {n['T4b']['funded']} records, of which {top_f[1]} name the Kazakhstan ministry of science or its Science Committee; publishers led by "
        + ", ".join(f"{r['publisher']} ({r['n']})" for r in pub) + ".",
        f"Bradford zones: {conc['Bradford zone 1: sources / records']} in the core, {conc['Bradford zone 2: sources / records']}, "
        f"{conc['Bradford zone 3: sources / records']} in the tail (sources / records); {conc['sources with one record']} of {conc['distinct sources']} "
        "sources hold one record.",
        f"Web of Science validation on 216 shared records: document types agree in {t5['type_agreement']} ({L.pct(t5['type_agreement'], 216)} %), years in "
        f"{t5['year_equal']}, Spearman rho {n['T5c']['Spearman rank correlation (average ranks for ties)']} between Scopus and WoS citation counts, and "
        f"{t5['top20_overlap']} of the 20 most cited by Scopus are also among the 20 most cited by WoS.",
        f"Looks problematic: conference papers are {L.pct(t1b.get('Conference paper', 0), n['N'])} % of the corpus "
        f"({t1d['2022-2025']['conference paper']} of {t1d['2022-2025']['records']} in 2022-2025); one workshop series outlet (CEUR Workshop Proceedings) "
        f"holds {n['T2a']['top20'][0][1]} records; the top 5 sources hold {conc['share of records in the top 5 sources (%)']} %; and the corpus "
        f"contains {n['T1g']} retracted records, which the text should mention or exclude.",
        f"Conference series (T2e): {n['T2e']['series']} acronym series for {n['T2e']['conference_papers']} conference papers; the largest is "
        f"{n['T2e']['top15'][0][0]} with {n['T2e']['top15'][0][1]} papers in 2021-2025.",
    ]
    out.append(bullets(prof))
    out.append("## 10. Gates\n")
    lines = ["| gate | what | verdict | planted violation caught |", "| --- | --- | --- | --- |"]
    lines += [f"| {g['gate']} | {g['what']} | {g['verdict']} | {g['planted_verdict']} ({g['falsifiability']}) |" for g in gates]
    out.append("\n".join(lines) + "\n")
    first = rows(L.OUT / "phase_F13_2_checkpoint_assertions_first_run.csv")
    if first:
        out.append(W("First run: " + ", ".join(f"{g['gate']} {g['verdict']}" for g in first) + ".") + "\n")
    out.append("## 11. Independent verification\n")
    if ver:
        lines = ["| check | what | tables | recomputed | verdict |", "| --- | --- | --- | --- | --- |"]
        lines += ["| " + " | ".join(" ".join(str(r.get(k, "")).split()[:25]) for k in ("check_id", "what", "expected_from_tables", "recomputed", "verdict")) + " |"
                  for r in ver]
        out.append("\n".join(lines) + "\n")
        out.append(W(f"A subagent wrote its own program (programs/f132_verify.py) from a description of the checks, without reading this phase's "
                     f"programs: {sum(1 for r in ver if r.get('verdict') == 'PASS')} of {len(ver)} PASS.") + "\n")
    else:
        out.append("(not yet run)\n")
    out.append("## 12. Disclosures\n")
    out.append(bullets([
        "A probe (programs/f132_probe.py: conference names, funder first elements, publishers, OA categories, languages, stages, WoS DT - "
        "organisation names and codes only) ran after the brief was saved and before its stamp.",
        "After the first table run, the Shota Rustaveli thesaurus label was corrected (five spellings, a joint call with STCU included) and D2's "
        "source names were cut to 30 words; tables were rebuilt before the gates.",
        "Abstracts and references are never loaded (parser whitelist); G2 therefore checks them by the whitelist and by cell length, not by "
        "comparing against the texts.",
        "Gates, first run: G2 failed because its list of name columns lacked 'canonical' (funders thesaurus), whose Kazakhstan ministry name has "
        "19 words; the column was added to the list and the gates were run again. A dry run of the closing then flagged the report's own "
        "description columns (what, tables, recomputed of the gate and verifier tables); they were added too. No personal or licensed text was involved.",
        "The verifier ran its program twice (the second run only reworded a note); both runs gave 53 checks and no failure.",
        "Publication years of conference papers can follow the event by a year (e.g. CybHyg 2019 papers carry 2020); T2e shows publication years.",
        "Funders: ministries named without a country are not merged with the Kazakhstan ministry, so its count is a lower bound.",
        "No network module in programs/ (G6); no heredoc, workflow or skill; one subagent (the verifier); nothing in .claude/; nothing deleted or "
        "moved; CORRECTIONS.csv unchanged; PHASE_REGISTRY.csv, phase_F12_3c and the merged corpus neither read nor written.",
    ]))
    if rows_reg:
        out.append("## 13. Registry rows (to be added on the author's command, in the order phase_F12_4, phase_F13_1, phase_F13_2)\n")
        for r in rows_reg:
            out.append(W(f"{r['phase_id']} | {r['status']} | produced_numbers {r['produced_numbers']} | safe_to_publish {r['safe_to_publish']} | "
                         f"{r['file_count']} files, {r['bytes']} bytes | path {r['path']}") + "\n")
        out.append(W("The first two rows are taken unchanged from outputs/dprg_revision_2026/phase_F13_1/run_logs/registry_rows_pending.json; all three "
                     "are in this phase's run_logs/registry_rows_pending.json.") + "\n")
    return "\n".join(out)
