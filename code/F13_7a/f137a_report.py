"""Phase F13.7a - the report, built from the phase's records. Prose hard-wrapped (<= 25 words a line)."""
import sys
sys.dont_write_bytecode = True

import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f137a_lib as L

W = L.wrap


def j(p):
    return json.loads(Path(p).read_bytes().decode("utf-8"))


def rows(name, folder=None):
    p = (folder or L.TABLES) / name
    return L.read_csv_path(p) if p.exists() else []


def md(name):
    return (L.TABLES / name).read_bytes().decode("utf-8").replace("## ", "### ", 1)


def bullets(items, width=22):
    return "\n".join("- " + W(x, width).replace("\n", "\n  ") for x in items) + "\n"


def build(row, gates):
    st = j(L.OUT / "F13_7a_brief_stamp.json")
    rj = j(L.RUN_LOGS / "render.json")
    wb = j(L.RUN_LOGS / "workbook.json")
    cj = j(L.RUN_LOGS / "corrections.json")
    fj = j(L.RUN_LOGS / "figures.json")
    ver = rows("phase_F13_7a_independent_verification.csv", L.OUT)
    tools = st["tools"]
    out = ["# Phase F13.7a - package tools, part 1: trial render, figure manifest, supplementary workbook, v3.1 figure, draft CORRECTIONS lines\n"]
    status = row["status"] if row else "(dry run - no pending registry row yet)"
    out.append(W(f"Status: {status}. Repository: {st['root']}. Brief: F13_7a_brief.md (sha256 {st['brief_sha256']}). No change to main.qmd, the "
                 "package (outputs/tp_submission, SUBMISSION_TP_2026_09_21/rebuilt), outputs/tables, CORRECTIONS.csv or phase_F13_6b; the forks' "
                 "folders phase_F13_3b and phase_F13_6c were neither read nor snapshotted. Tools: Quarto " + tools["quarto"] + ", " + tools["pandoc (Quarto's)"]
                 + ", " + tools["tectonic"] + f", Python {tools['python']}, pandas {tools['pandas']}, openpyxl {tools['openpyxl']}, Pillow "
                 f"{tools['pillow']}, matplotlib {tools['matplotlib']}; nothing was installed.") + "\n")

    out.append("## 1. Trial render (render/)\n")
    o = rj["outputs"]
    out.append(W(f"The draft (part 1, phase_F13_6b/draft/main_v2.qmd) was copied to render/ with references.bib; in the copy only: "
                 f"{rj['copy_changes']['root_relative_figure_paths_fixed']} figure path written from the repository root made relative to render/, "
                 f"and tectonic given {rj['copy_changes']['pdf_engine_option_added']} so that no file is fetched. DOCX: built "
                 f"(render/main_v2.docx, {o['docx']['bytes']} bytes, {rj['docx']['media_files']} images, all TIFF). PDF: not built offline - tectonic "
                 "lacks one font in its cache; the fallback copy with xelatex (Quarto's TinyTeX, package auto-install off) stops on mismatched LaTeX "
                 f"support files. Unresolved cross-references: {len(rj['unresolved_cross_references'])}; citation keys missing from references.bib: "
                 f"{len(rj['citation_keys_missing'])} (of {rj['citation_keys_in_draft']} keys). Times: "
                 + "; ".join(f"{k} {v['seconds']} s (exit {v['returncode']})" for k, v in rj["commands"].items()) + ".") + "\n")
    out.append(md("R1_render_issues.md"))

    out.append("## 2. Figure manifest (F1)\n")
    out.append(md("F1_figure_manifest.md"))
    out.append(W(f"{fj['figures']} figures, {fj['manifest_rows']} files. Every existing file meets 300 dpi and a width of at least 1000 px (PDFs are "
                 f"vector). Not meeting: {', '.join(x.split('/')[-1] for x in fj['not_meeting']) or 'none'} (the file does not exist; the figure is the "
                 "one N3 of F13.6a marks for removal).") + "\n")

    out.append("## 3. Collaboration-type figure redrawn on thesaurus v3.1\n")
    out.append(W("figures/Fig_collaboration_type_by_year_v31.pdf, .png and .tif (300 dpi; TIFF with LZW) and its CSV (= phase_F13_2e T2f_v31), drawn "
                 "by programs/f137a_figures.py with F13.2b's code (same colours, size, font, labels; no title inside); not viewed (R18). It closes a "
                 "possible [[F13.6d: redraw figure]] mark of F13.6c.") + "\n")
    cap = ("Collaboration type of the corpus records by publication year, 2003-2025: single institution, domestic multi-institution and "
           "international (institutions thesaurus v3.1; Scopus, n = 841, retrieved 13 October 2026). Source: Authors' own work.")
    out.append("Draft caption:\n\n> " + W(cap).replace("\n", "\n> ") + "\n")

    out.append("## 4. Supplementary workbook (supplementary/Supplementary_tables_draft.xlsx)\n")
    out.append(W(f"{wb['sheets']} sheets ({wb['data_sheets']} data sheets and README), {wb['rows_total']} data rows, {wb['xlsx_bytes']} bytes; sheet names "
                 f"at most {wb['longest_sheet_name']} characters. One sheet per source file; numbers are the sources' strings (integers as numbers, "
                 "decimals as numbers shown with their own decimals, all else text). Four sources are derived in tables/: S1 queries, S6c (top 30 "
                 "of T3d_v31), S8s (top 20 cited records without EID / DOI, titles cut to 15 words) and the Phase log. Left out (R13: record-level "
                 "lists or raw strings): F12.4 T1c / T2b / T3b, F13.1 T3a_pairs, F13.2 T4c_funder_variants_raw.") + "\n")
    out.append(md("X1_sheet_sources.md"))

    out.append("## 5. Draft CORRECTIONS lines (C1; CORRECTIONS.csv not written)\n")
    out.append(W(f"{cj['lines']} lines: {cj['changed']} changed and {cj['removed']} removed numbers of main.qmd (F13.6a N1). Format: the eight columns of "
                 "CORRECTIONS.csv (read from its header and first line only); ids C558 onwards are provisional. Of the changed numbers, "
                 f"{cj['changed_found_in_E1']} carry their new value in the F13.6b evidence index; the others are not in part 1's index (Discussion, "
                 "Limitations and yearly counts belong to part 2) or have no new source in N1. Two new values of N1 (institution counts from F13.2b, "
                 "thesaurus v1) are replaced by the current F13.2e values: " + "; ".join(f"{k} {v[0]} -> {v[1]}" for k, v in cj["updated_to_v31"].items())
                 + ".") + "\n")
    out.append(md("C1b_corrections_summary.md"))
    c1 = rows("C1_corrections_draft.csv")
    out.append("### C1 - changed numbers (all 31 lines; the removed ones are in the CSV)\n\n" + L.md_table(
        ["n1_id", "section", "old_value", "n1_value_new", "new_value", "in_draft_E1", "note_for_F13_6d"],
        [r for r in c1 if r["n1_status"] == "changed"]) + "\n")

    out.append("## 6. For the professor\n")
    out.append(bullets([
        "The DOCX builds from the draft with every figure, cross-reference and citation resolved; the PDF does not build on this machine without "
        "network: tectonic misses one font in its cache and TinyTeX's formats are older than its LaTeX files.",
        "Before the package (F13.6d): the 35 editorial marks of the text, the main.qmd figure Fig3 that N3 removes, the collaboration figure "
        "switched to the v3.1 redraw, and PNG instead of TIFF in the DOCX.",
        "Needed from the author: the target journal and its template (LaTeX class or Word template; figure and supplement rules), the link of the "
        "data and code repository for the availability statement, and a choice for the PDF route (let tectonic fetch its font once, or repair TinyTeX).",
        f"The supplementary workbook ({wb['data_sheets']} sheets) and the draft CORRECTIONS lines ({cj['lines']}) are ready to be checked; both come "
        "only from closed phases' tables.",
    ]))

    out.append("## 7. Gates\n")
    lines = ["| gate | what | verdict | planted violation caught |", "| --- | --- | --- | --- |"]
    lines += [f"| {g['gate']} | {g['what']} | {g['verdict']} | {g['planted_verdict']} ({g['falsifiability']}) |" for g in gates]
    out.append("\n".join(lines) + "\n")
    out.append(W("First run of the gates (console): G2 FAIL (it read F13.3's numeric column 'references' as reference text) and G3 FAIL (decimals "
                 "such as '87.0' came back from Excel as 87). Fixed: G2 accepts a 'references' column holding only numbers; the workbook stores a "
                 "decimal with a display format of its own decimals and G3 compares at the source's precision. The file "
                 "phase_F13_7a_checkpoint_assertions_first_run.csv holds the run after these fixes (it was written again).") + "\n")
    out.append("## 8. Independent verification\n")
    if ver:
        lines = ["| check | what | tables | recomputed | verdict |", "| --- | --- | --- | --- | --- |"]
        lines += ["| " + " | ".join(" ".join(str(r.get(k, "")).replace("|", "/").split()[:14])[:100] for k in
                                    ("check_id", "what", "expected_from_tables", "recomputed", "verdict")) + " |" for r in ver]
        out.append("\n".join(lines) + "\n")
        out.append(W(f"A subagent wrote its own program (programs/f137a_verify.py) without reading this phase's other programs: "
                     f"{sum(1 for r in ver if r.get('verdict') == 'PASS')} of {len(ver)} PASS.") + "\n")
    else:
        out.append("(not yet run)\n")
    out.append("## 9. Disclosures\n")
    reg = st["registry_one_read"]
    out.append(bullets([
        f"PHASE_REGISTRY.csv was read once, in step 0 before step 1 (brief): {reg['registry_rows']} rows; the {reg['rows_kept']} rows phase_F12_4 "
        "and phase_F13_* went to tables/phase_log_from_registry.csv (notes cut to 27 words), the source of the Phase log sheet.",
        "No installation: Quarto, its Pandoc and TinyTeX, tectonic, pandas, openpyxl, Pillow and matplotlib were present.",
        "The render ran its engines offline: tectonic with -C; the xelatex fallback with latex-auto-install false. The fallback is a second copy "
        "(render/main_v2_xelatex.qmd) differing from the first only in the engine lines.",
        "Images were read for metadata only (Pillow; R18); no image was viewed. The redrawn figure was not viewed.",
        "Sheet S7i (F13.2c T2b) has a column 'first_author': its values are categories of the first author's addresses (Kazakhstan only, "
        "foreign only, both, no address), not names (the verifier's note).",
        "CORRECTIONS.csv: only its header and first line were read, for the format. Ids C558 onwards assume the 557 lines named in the brief.",
        "G2 cannot use the corpus surname set of earlier phases (E1 is not an input here): the sheets are byte copies of closed phases' tables "
        "that passed their own R13 gates (G3 proves the copies); the phase's own files are scanned for name shapes.",
        "No network module in the phase's programs, no heredoc, no workflow or skill; one subagent (the verifier); nothing in .claude/; nothing "
        "deleted or moved; CORRECTIONS.csv unchanged (in the snapshot).",
    ]))
    out.append("## 10. Registry row\n")
    if row:
        out.append(W(f"{row['phase_id']} | {row['status']} | produced_numbers {row['produced_numbers']} | safe_to_publish {row['safe_to_publish']} | "
                     f"{row['file_count']} files, {row['bytes']} bytes (the folder's fixed point). Ready row: run_logs/registry_rows_pending.json; "
                     "written after the closing by one run of tools/registry_apply.py (its result is in the closing message and the tool's journal).") + "\n")
        out.append(W("Note of the row: " + row["note"]) + "\n")
    else:
        out.append("(dry run)\n")
    return "\n".join(out)
