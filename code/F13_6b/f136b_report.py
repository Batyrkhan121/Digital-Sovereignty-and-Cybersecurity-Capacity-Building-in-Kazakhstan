"""Phase F13.6b - the report, built from the phase's records. Prose hard-wrapped (<= 25 words a line)."""
import sys
sys.dont_write_bytecode = True

import json
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f136b_lib as L

W = L.wrap

DOUBTS = [
    ("title-only version of the same query", "the harmonised query string and its retrieval date are not among this phase's inputs (phase_F12_4 tables give only "
     "the counts); quote them from phase F12.4's documentation"),
    ("resampling replicates", "the intervals' method is described generically from the tables (replicates column); name the resampling scheme as in phase F13.4"),
    ("Kazakhstan's cybersecurity output by publication year", "caption written from the figure's data file (year, Kazakhstan's records and share, "
     "four neighbours' counts); the figure was not viewed (R18)"),
    ("hand-written merge rules", "the five rows of the conference-series thesaurus are described as merge rules without reading their content"),
    ("successive names of the ministry", "the funder thesaurus is described from the label of its largest row"),
    ("national university bulletins and academy journals", "a qualitative reading of the only-OpenAlex source list; no journal is named"),
    ("about half as much again", "an interpretive rounding of the standardised indices near 1.5"),
    ("since 2023", "the year comes from the thesaurus reason that records the authors' Decision 45"),
    ("much faster than cybersecurity research worldwide", "a comparison of two growth rates computed in this phase (S4)"),
    ("the year most likely to grow with further indexing", "an assumption about indexing lag, not measured here"),
    ("remained the largest producer of the five in every period", "a claim read from phase_F13_4 T3b without a number in the sentence"),
    ("does not establish an effect of the programme", "chronology, not causality, as the brief requires; wording to confirm"),
]


def j(p):
    return json.loads(Path(p).read_bytes().decode("utf-8"))


def md(name):
    return (L.TABLES / f"{name}.md").read_bytes().decode("utf-8").replace("## ", "### ", 1)


def rows(p):
    return L.read_csv_out(p) if Path(p).exists() else []


def bullets(items, width=22):
    return "\n".join("- " + W(x, width).replace("\n", "\n  ") for x in items) + "\n"


def build(rows_reg, gates):
    n = j(L.OUT / "F13_6b_numbers.json")
    st = j(L.OUT / "F13_6b_brief_stamp.json")
    ver = rows(L.OUT / "phase_F13_6b_independent_verification.csv")
    draft = (L.DRAFT / "main_v2.qmd").read_bytes().decode("utf-8").split("\n")
    s2 = rows(L.TABLES / "S2_map_coverage.csv")
    d = st["f13_2d"]
    out = ["# Phase F13.6b - draft of the new manuscript, part 1: Methodology and Results\n"]
    out.append(W(f"Status: {'COMPLETE' if rows_reg else '(dry run)'}. Repository: {st['root']}; the phase registry is {st['registry_location']} "
                 f"(neither read nor written). Brief: F13_6b_brief.md (sha256 {st['brief_sha256']}). The draft is draft/main_v2.qmd; main.qmd is "
                 "untouched (G5).") + "\n")
    out.append(W(f"Institution numbers: phase_F13_2d/run_logs/final.json was {'present' if d['final_json_present'] else 'absent'} at step 0 "
                 f"({d['checked_utc']}), so the inputs of section 3.3 are {d['institution_inputs']}; the decision was not re-checked.") + "\n")
    out.append("## 1. Inputs\n")
    grp = Counter((k.split("/")[2] if k.startswith(L.DPR + "phase_") else k) for k in st["inputs"])
    out.append(L.md_table(["input", "files"], [{"input": k, "files": v} for k, v in sorted(grp.items())]) + "\n")
    out.append(W(f"{st['inputs_count']} inputs, each with its sha256 in F13_6b_brief_stamp.json; phase_F13_1's T1d and T3d are not inputs.") + "\n")
    out.append("## 2. Outline (S0)\n")
    out.append(md("S0_outline").split("\n", 2)[2])
    out.append("## 3. Word counts (S5)\n")
    out.append(md("S5_word_counts").split("\n", 2)[2])
    out.append(W(f"Sections 2-3 hold {n['words_sections_2_3_prose']} words of prose and captions (the brief asks for 3,200-3,800), plus "
                 f"{n['words_sections_2_3_tables']} words in table cells and the two queries in code spans.") + "\n")
    out.append("## 4. Evidence index (E1)\n")
    bk = n["by_kind"]
    out.append(W(f"{n['tokens_sections_2_3']} numeric tokens in sections 2-3 by the F13.6a rule (a year range is one token): table {bk.get('table', 0)}, "
                 f"formula {bk.get('formula', 0)}, external {bk.get('external', 0)} (the retrieval date and the programme year), count-of-text "
                 f"{bk.get('count-of-text', 0)} (the constants 1, 2 and 95 and the label of the part-2 mark). match = yes for {n['match_yes']} tokens and "
                 f"no for {n['match_no']}; every table and formula token matches: {n['table_formula_all_yes']}. {n['marked_F13_2d_tokens']} tokens stand "
                 "in sentences marked F13.2d. No number of sections 2-3 is written without a placeholder: the build stops on any bare number.") + "\n")
    out.append(md("E1_evidence_index").split("\n", 2)[2])
    out.append("## 5. Coverage of the F13.6a map (S2)\n")
    c2 = Counter((r["map"], r["basis"].split(" '")[0]) for r in s2)
    out.append(L.md_table(["map", "basis", "rows"], [{"map": a, "basis": b, "rows": v} for (a, b), v in sorted(c2.items())]) + "\n")
    out.append(W("N1 rows (status same or changed, Methodology and Results of main.qmd): where the new value stands in the draft, by the same cell, "
                 "the same table and value, or the same value for the corpus size, window, periods and year labels; otherwise the reason (mostly "
                 "the year-by-year counts, which are in the figure). N2 rows (remove or changed): removed, or the draft sentence id (D<line>s<k>) "
                 "of the subsection that rewrites them. All rows are in tables/S2_map_coverage.csv.") + "\n")
    out.append("## 6. Marks (S3)\n")
    out.append(md("S3_part2_marks").split("\n", 2)[2])
    out.append("## 7. Derived numbers (S4)\n")
    out.append(md("S4_derived_numbers").split("\n", 2)[2])
    out.append("## 8. Citation keys and sources needed (S5b, S6)\n")
    out.append(W(f"{n['citation_keys']} citation keys are used in the draft; missing in references.bib: {n['keys_missing_in_bib'] or 'none'}. No key was "
                 "added. The method sources the new text would cite are listed in S6 with DOIs from the executor's knowledge, to be checked "
                 "before they enter the bibliography.") + "\n")
    out += [md("S5b_citation_keys"), md("S6_citations_needed")]
    out.append("## 9. For the professor\n")
    new = [
        "New in the text: one corpus (Scopus, 841 records, retrieved 13 October 2026) with Web of Science as validation and OpenAlex as "
        "complementarity at an equal query; the three-layer design, the enriched layer and the Academic Iceberg Effect are gone.",
        "New indicators: log-linear growth with doubling times set against Kazakhstan's total output and world cybersecurity output; the "
        "activity index by period, standardised by year, with intervals and four neighbouring countries (Table and figure).",
        "New readings: document types, sources (journals and conference series apart), citations, open access and funding; international "
        "collaboration by author (types i-iii, first author); the co-word map with its stability checks and the keyword-based blind spots.",
    ]
    out.append(bullets(new))
    out.append("Places where the executor doubted the wording (draft line numbers):\n")
    dl = []
    for phrase, why in DOUBTS:
        ln = next((i for i, s in enumerate(draft, 1) if phrase in s), "")
        dl.append({"line": ln, "phrase": phrase, "why": why})
    out.append(L.md_table(["line", "phrase", "why"], dl) + "\n")
    out.append(W("Left to part 2: the citation structure (F13.3); the Abstract, Introduction, Discussion, Limitations and Conclusion, which still "
                 f"carry the old numbers ({n['marks'].get(L.MARK_P2, 0)} part-2 marks after removed claims; their figure and table references point "
                 "to items the new sections replace); the update of the institution numbers by F13.2d "
                 f"({n['marks'].get(L.MARK_2D, 0)} marks); the method references of S6; the supplementary tables (keyword and institution thesauri, "
                 "queries).") + "\n")
    out.append("## 10. Gates\n")
    lines = ["| gate | what | verdict | planted violation caught |", "| --- | --- | --- | --- |"]
    lines += [f"| {g['gate']} | {g['what']} | {g['verdict']} | {g['planted_verdict']} ({g['falsifiability']}) |" for g in gates]
    out.append("\n".join(lines) + "\n")
    first = rows(L.OUT / "phase_F13_6b_checkpoint_assertions_first_run.csv")
    if first:
        out.append(W("First run: " + ", ".join(f"{g['gate']} {g['verdict']}" for g in first) + ".") + "\n")
    out.append("## 11. Independent verification\n")
    if ver:
        lines = ["| check | what | tables | recomputed | verdict |", "| --- | --- | --- | --- | --- |"]
        def safe(v):
            # the verifier's own description of the ORCID pattern (0000-...) would itself match the shape test of G2
            return L.EMAIL.sub("[e-mail pattern]", L.ORCID.sub("[ORCID pattern]", str(v)))
        lines += ["| " + " | ".join(" ".join(safe(r.get(k, "")).split()[:28]) for k in ("check_id", "what", "expected_from_tables", "recomputed", "verdict")) + " |"
                  for r in ver]
        out.append("\n".join(lines) + "\n")
        out.append(W(f"A subagent wrote its own program (programs/f136b_verify.py) from a description of the rules, without reading this phase's other "
                     f"programs: {sum(1 for r in ver if r.get('verdict') == 'PASS')} PASS, {sum(1 for r in ver if r.get('verdict') == 'INFO')} informational rows, {sum(1 for r in ver if r.get('verdict') == 'FAIL')} FAIL. Its first run failed C07 on one extra newline at the end of the draft (the build wrote a final newline after main.qmd's own); the build was corrected and the verifier's program re-run on the corrected draft.") + "\n")
    else:
        out.append("(not yet run)\n")
    out.append("## 12. Disclosures\n")
    out.append(bullets([
        f"phase_F13_2d: the step-0 program checked once for run_logs/final.json ({d['checked_utc']}); a shell pre-check a few minutes earlier "
        "(2026-10-13T12:56:25Z) gave the same answer. The decision is stored in the stamp and was not checked again.",
        "The F13.6a extraction program is reused unchanged: its units() and tokens() run with its main_lines() pointed at the draft, then restored; "
        "no bytecode was written into phase_F13_6a (G5).",
        "Copied verbatim from main.qmd: the YAML block, the Introduction and everything from the Discussion on, including Funding and the AI "
        "declaration (the brief names sections 1 and 4-7; the remaining two are copied unchanged too). Part-2 marks follow each claim that "
        "F13.6a's N2 removes there.",
        "The text of sections 2-3 was written by the executor in a template whose every number is a placeholder resolved by the build program; "
        "no editor subagent was used.",
        "Quarto render was not attempted: the copied YAML points to references.bib relative to the draft's folder, and a render inside the "
        "author's Quarto project could write its cache outside the phase folder.",
        "The comparator table shows counts only; the pooled shares were left out so that no pooled activity index can be read off it.",
        "Gates, first run: G4 failed because the coverage table (S2) had been regenerated by a corrected program between the last build and "
        "the gate's second run; after a rebuild every gate passed. No number changed.",
        "Figures were not opened or viewed (R18); their captions were written from their data files.",
        "The closing's first attempt stopped at G2: the report quoted the verifier's description of the ORCID pattern (a run of zeros), which "
        "matches the shape test; the report now replaces such patterns in quoted verifier rows by a label. No personal data was involved.",
        "No network module in programs/ (G6); no heredoc, workflow or skill; one subagent (the verifier); nothing in .claude/; nothing deleted or "
        "moved (R17 audit hook); phase_F13_2d, tools/ and PHASE_REGISTRY.csv neither read nor written; phase_F13_3 only hashed for the snapshot.",
        "Registry: no 'реестр' has been given in this session; the rows of F12_4, F13_1, F13_2, F13_2b, F13_6a, F13_2c and this phase are unwritten.",
    ]))
    if rows_reg:
        out.append("## 13. Registry row (to be added on the author's command)\n")
        for r in rows_reg:
            out.append(W(f"{r['phase_id']} | {r['status']} | produced_numbers {r['produced_numbers']} | safe_to_publish {r['safe_to_publish']} | "
                         f"{r['file_count']} files, {r['bytes']} bytes | path {r['path']}") + "\n")
        out.append(W("The row is kept, unwritten, in run_logs/registry_rows_pending.json with its file count and bytes at the folder's fixed point.") + "\n")
    return "\n".join(out)
