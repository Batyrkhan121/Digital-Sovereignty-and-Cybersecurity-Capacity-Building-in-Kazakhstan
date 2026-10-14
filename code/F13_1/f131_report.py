"""Phase F13.1 - the report, built from the phase's records (counts only). Prose hard-wrapped (<= 25 words a line, gate G2)."""
import sys
sys.dont_write_bytecode = True

import csv
import io
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f131_lib as L

W = L.wrap


def j(p):
    return json.loads(Path(p).read_bytes().decode("utf-8"))


def md(name):
    return (L.TABLES / f"{name}.md").read_bytes().decode("utf-8").replace("## ", "### ", 1)


def rows(p):
    return list(csv.DictReader(io.StringIO(Path(p).read_bytes().decode("utf-8"), newline=""))) if Path(p).exists() else []


def bullets(items, width=22):
    return "\n".join("- " + W(x, width).replace("\n", "\n  ") for x in items) + "\n"


def build(rows_reg, gates):
    n = j(L.OUT / "F13_1_numbers.json")
    st = j(L.OUT / "F13_1_brief_stamp.json")
    ver = rows(L.OUT / "phase_F13_1_independent_verification.csv")
    b, t3, m, d = n["T1b"], n["T3a"], n["M"], n["T1d"]
    out = ["# Phase F13.1 - acceptance of the full Scopus and Web of Science exports; merged corpus\n"]
    out.append(W(f"Status: {'COMPLETE' if rows_reg else '(dry run)'}. Repository: {st['root']} (where PHASE_REGISTRY.csv is; the registry and "
                 f"phase_F12_3c were neither read nor written - a parallel session writes them). Brief: F13_1_brief.md (sha256 {st['brief_sha256']}). "
                 "No edit to the manuscript or the package. No analysis: acceptance, reconciliation and the merged corpus only.") + "\n")
    out.append("## 1. Inputs\n")
    lines = ["| input | file | sha256 | check |", "| --- | --- | --- | --- |"]
    files = {"E1": L.E1, "E1b": L.E1B, "E2": L.E2, "I1": L.I1, "I3": L.I3}
    for k, v in st["inputs"].items():
        lines.append(f"| {k} | {files[k]} | {v['sha256']} | equal to README / brief: {v['equal']} |")
    for f_, v in sorted(st["year_series"].items()):
        lines.append(f"| Y | {L.EXP}{f_} | {v['sha256']} | equal to manifest_year_series.json: {v['equal']} |")
    out.append("\n".join(lines) + "\n")
    out.append("Queries (README_exports.txt, verbatim):\n")
    readme = L.path(L.README).read_bytes().decode("utf-8")
    for key in ("TITLE-ABS-KEY(cybersecurity", "TS=("):
        line = next(x.strip() for x in readme.splitlines() if x.strip().startswith(key))
        out.append(f"- `{line}`")
    out.append("")
    out.append(W("Year series queries are listed in README_exports.txt section B; the series were transcribed from the Scopus 'Analyze search "
                 "results' table (the README says so) and each sums to the interface total.") + "\n")
    out.append("Parsing and matching parameters:\n")
    out.append(bullets([
        "E1/E1b: csv.DictReader on the UTF-8 (BOM) text, field size limit 1 GiB; 'Correspondence Address' popped from every row as it is read "
        "(its non-empty count kept for T1b).",
        "E2: ISI plain text; FN/VR header skipped; a record runs to ER; a line opening with a two-letter tag starts a field, a line opening "
        "with three spaces continues it; CR keeps one reference per line; tags EM, OI, RI, RP are counted and never stored.",
        "References per record: Scopus References split on '; '; WoS: CR lines (checked against NR).",
        "E1 <-> E2: DOI lowercase without https://doi.org/, http://dx.doi.org/, doi: prefixes; title lowercase, [^a-z0-9] to space, collapsed; "
        "DOI first, then exact normalised title among the unmatched; one-to-one; greedy in sorted id order; run both ways (equal: "
        f"{n['symmetry']['equal']}).",
    ]))
    out.append("## 2. T1 - parsing\n")
    out += [md("T1a_counts"), md("T1b_completeness"), md("T1c_E1_vs_E1b"), md("T1d_references")]
    out.append("## 3. T2 - E1 against the September frame and the June layer\n")
    out += [md("T2a_E1_vs_frame"), md("T2a2_field_differences"), md("T2b_years"), md("T2c_doc_types")]
    out.append("## 4. T3 - Scopus against Web of Science\n")
    out.append(md("T3a_scopus_wos"))
    out.append(W("The pairs (EID, UT, how matched): tables/T3a_pairs.csv.") + "\n")
    for tag in ("DT", "PY", "SO", "WE", "LA"):
        out.append(md(f"T3b_only_wos_{tag}"))
    for key in ("doc_type", "year", "source"):
        out.append(md(f"T3c_only_scopus_{key}"))
    out.append(md("T3d_reference_counts"))
    out.append("## 5. T4 - the merged corpus M\n")
    out += [md("T4_merged_by_year"), md("T4_merged_by_type"), md("T4_merged_flags")]
    out.append(W("M is data/merged_corpus_2026-10-13.csv (outside git; it holds abstracts and reference lists). Its codebook (data/codebook.md) "
                 "follows.") + "\n")
    cb = (L.DATA / "codebook.md").read_bytes().decode("utf-8")
    cb_lines = []
    for line in cb.split("\n"):
        if line.startswith("#"):
            cb_lines.append(line.replace("# ", "### ", 1))
        elif line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 2 and len(cells[1].split()) > 28:
                words = cells[1].split()
                chunks = [" ".join(words[i:i + 25]) for i in range(0, len(words), 25)]
                cb_lines.append(f"| {cells[0]} | {chunks[0]} |")
                cb_lines += [f"|  | {c} |" for c in chunks[1:]]
            else:
                cb_lines.append(line)
        else:
            cb_lines.append(W(line))
    out.append("\n".join(cb_lines) + "\n")
    out.append("## 6. T5 - topic share by year (for F13.4; table only)\n")
    out.append(md("T5_topic_share"))
    out.append("## 7. For the professor\n")
    t2 = n["T2a_diff"]
    prof = [
        f"Better than the previous layer: E1 carries reference lists for {b['E1:References']} of 841 records ({d['E1 references, total']} "
        f"references; median {d['E1 references per record after splitting on ' + chr(39) + '; ' + chr(39) + ' - median']} per record), "
        f"affiliations for all 841, author keywords for {b['E1:Author Keywords']}, index keywords for {b['E1:Index Keywords']} and funding "
        f"details for {b['E1:Funding Details']} - in one export, with no separate API enrichment; citation analysis becomes possible.",
        f"Web of Science adds independent coverage only at the margin: {t3['intersection']} of its {231} records are also in Scopus "
        f"({t3['share of WoS records also in Scopus (%)']} %), {t3['only WoS']} are WoS-only (mostly proceedings papers); on the shared "
        f"records Scopus lists more references (median {n['T3d']['Scopus references per record - median']} against WoS NR "
        f"{n['T3d']['WoS NR per record - median']}), and WoS brings its own citation counts (TC).",
        f"E1 and the September frame hold the same 841-record total and agree on {t2['common']} records (years, DOIs and document types "
        f"identical; the {sum(t2['doc_type'].values())} type differences are capitalisation only; one source title differs); 3 records left "
        "and 3 entered between the two snapshots, so four annual counts move by one (T2b) and Retracted rises from 2 to 3.",
        "Decision needed: adopt E1 (retrieved 2026-10-13) as the new reporting frame in place of the September frame - the change is three "
        "records each way - and decide whether Web of Science enters the analysis (union 856) or serves as a cross-check only.",
        f"{d['E1 References longer than 32,000 characters (Excel cell limit)']} reference cells exceed Excel's 32,000-character cell limit: "
        "the files must not be opened and re-saved in Excel.",
    ]
    out.append(bullets(prof))
    out.append("## 8. Gates\n")
    lines = ["| gate | what | verdict | planted violation caught |", "| --- | --- | --- | --- |"]
    lines += [f"| {g['gate']} | {g['what']} | {g['verdict']} | {g['planted_verdict']} ({g['falsifiability']}) |" for g in gates]
    out.append("\n".join(lines) + "\n")
    first = rows(L.OUT / "phase_F13_1_checkpoint_assertions_first_run.csv")
    if first:
        out.append(W("First run: " + ", ".join(f"{g['gate']} {g['verdict']}" for g in first) + ".") + "\n")
    out.append("## 9. Independent verification\n")
    if ver:
        lines = ["| check | what | tables | recomputed | verdict |", "| --- | --- | --- | --- | --- |"]
        lines += ["| " + " | ".join(str(r.get(k, ""))[:100] for k in ("check_id", "what", "expected_from_tables", "recomputed", "verdict")) + " |"
                  for r in ver]
        out.append("\n".join(lines) + "\n")
        out.append(W(f"A subagent wrote its own program (programs/f131_verify.py) from a description of the rules, without reading this "
                     f"phase's programs: {sum(1 for r in ver if r.get('verdict') == 'PASS')} of {len(ver)} PASS.") + "\n")
    else:
        out.append("(not yet run)\n")
    out.append("## 10. Disclosures\n")
    out.append(bullets([
        "Before any data file was written, the line outputs/dprg_revision_2026/phase_F13_1/data/ was added to .gitignore (the brief keeps data/ "
        "out of git); git check-ignore confirms it. .gitignore is the only file outside the phase folder this phase changed; it is not in the "
        "step-0 snapshot.",
        "A structure probe (programs/f131_probe.py; column and tag names, counts) ran after the brief was saved and before its stamp.",
        "The first run of the acceptance program mapped Scopus document types case-sensitively and put 422 records under 'other' (E1 writes "
        "'Conference paper', 'Book chapter'); the map was made case-insensitive and T2a gained a case-insensitive row before the gates ran.",
        "WoS edition labels carry an HTML entity in the export ('&amp;'); T3b shows them unescaped.",
        "Gates, first run: G2 failed on the console of the second acceptance run - its count summary was one JSON line of more than 30 "
        "words (counts only, no personal or licensed text). The summary is now printed over several lines; the gates were run again. Before "
        "that first run, G2 was aligned with two false positives the verifier had found in its own checker: tag names EM/OI/RI/RP as row "
        "values of T1b (only a table's first row is a header now) and bare years equal to broken reference entries (cells without letters "
        "are not compared with references).",
        "The verifier made two runs; its first failed C07 on the same two checker false positives, fixed in its second run.",
        "A dry run of the closing then found G2's own description (33 words) too long for a report line; it was shortened, and the closing "
        "ran with every gate passing.",
        f"One WoS record's CR line count differs from its NR; Scopus references are split on '; ' (an upper bound if a reference holds '; ').",
        "README_exports.txt states that the exports were made in the author's signed-in browser by an assistant session with the author's "
        "approval for each download, and that the year series were transcribed from the interface; this phase did not repeat either step.",
        "Contact fields (Correspondence Address; EM, OI, RI, RP) were counted by the parsers and never stored, copied or printed; no abstract, "
        "reference or author name appears in the report, tables/ or the console.",
        "No network module in programs/ (G6); no heredoc, workflow or skill; one subagent (the verifier); nothing in .claude/; nothing "
        "deleted or moved; CORRECTIONS.csv unchanged; PHASE_REGISTRY.csv and phase_F12_3c neither read nor written.",
    ]))
    if rows_reg:
        out.append("## 11. Registry rows (to be added on the author's command, in the order phase_F12_4, phase_F13_1)\n")
        for r in rows_reg:
            out.append(W(f"{r['phase_id']} | {r['status']} | produced_numbers {r['produced_numbers']} | safe_to_publish {r['safe_to_publish']} | "
                         f"{r['file_count']} files, {r['bytes']} bytes | path {r['path']}") + "\n")
        out.append(W("The phase_F12_4 row is taken unchanged from outputs/dprg_revision_2026/phase_F12_4/run_logs/registry_row_pending.json; the "
                     "phase_F13_1 row is in this phase's run_logs/registry_rows_pending.json with its file count and bytes at the fixed point.") + "\n")
    return "\n".join(out)
