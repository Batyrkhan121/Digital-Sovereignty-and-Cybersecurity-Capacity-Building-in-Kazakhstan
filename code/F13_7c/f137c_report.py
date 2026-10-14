"""Phase F13.7c - the report, built from the phase's records. Prose hard-wrapped (<= 25 words a line)."""
import sys
sys.dont_write_bytecode = True

from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f137c_lib as L

WRAP = L.wrap


def rows(p):
    return L.read_csv_path(p) if Path(p).exists() else []


def md(name):
    return (L.TABLES / f"{name}.md").read_bytes().decode("utf-8").replace("## ", "### ", 1)


def bullets(items, width=22):
    return "\n".join("- " + WRAP(x, width).replace("\n", "\n  ") for x in items) + "\n"


def safe(v):
    return L.EMAIL.sub("[e-mail pattern]", L.ORCID.sub("[ORCID pattern]", str(v)))


def build(rows_reg, gates):
    st = L.jload(L.OUT / "F13_7c_brief_stamp.json")
    wl = L.jload(L.RUN_LOGS / "workbook.json")
    fl = L.jload(L.RUN_LOGS / "figure_set.json")
    x2 = rows(L.TABLES / "X2_sheet_sources.csv")
    ver = rows(L.OUT / "phase_F13_7c_independent_verification.csv")
    reg = st["registry_one_read"]
    out = ["# Phase F13.7c - supplementary workbook v2 and the figure set for submission\n"]
    out.append(WRAP(f"Status: {'COMPLETE' if rows_reg else '(dry run)'}. Repository: {st['root']}. Brief: F13_7c_brief.md (sha256 {st['brief_sha256']}). "
                    "The manuscript was not touched: main.qmd, references.bib, CORRECTIONS.csv and phase_F13_6d were neither read nor written. R19: "
                    "the F13.7a programs (workbook, figures with the manifest, the step-0 phase log) were imported unchanged from phase_F13_7a/programs "
                    "and pointed at this folder; their source list is extended in programs/f137c_lib.py.") + "\n")
    out.append("## 1. Inputs\n")
    grp = Counter((k.split("/")[2] if k.startswith(L.DPR + "phase_") else k.split("/")[2] if k.startswith(L.DPR) else k) for k in st["inputs"])
    out.append(L.md_table(["input", "files"], [{"input": k, "files": v} for k, v in sorted(grp.items())]) + "\n")
    out.append(WRAP(f"{st['inputs_count']} inputs with sha256 in F13_7c_brief_stamp.json; tools: Python {st['tools']['python']}, openpyxl "
                    f"{st['tools']['openpyxl']}, Pillow {st['tools']['pillow']}; nothing installed.") + "\n")
    out.append("## 2. The workbook (supplementary/Supplementary_tables.xlsx)\n")
    g = wl["groups"]
    out.append(WRAP(f"{wl['sheets']} sheets: README and {wl['data_sheets']} data sheets with {wl['rows_total']:,} data rows "
                    f"({wl['xlsx_bytes']:,} bytes; F13.7a's draft had 90). By group: " + ", ".join(f"{k} {v}" for k, v in g.items()) + ".") + "\n")
    out.append(bullets([
        "S5: S5_inst_thesaurus_v31 (285 rows) as before; S5c is now the v3.1 changes (F13.2e T1, 19 rows: the 9 rows of the professor's list, "
        "2 follow-on rows, 2 rows superseded and 6 reasons confirmed by the author); the v3 name-token rules move from S5c to S5d.",
        "S6: S6a T3a_v31 (all), S6b T3c_v31, S6c T3d_v31 top 30 as before; new S6d T2f2_v31 and S6e T2g_v31.",
        f"S13 (16 sheets): the citation structure by work key (F13.3b). Three are derived under R13's rule for listed works: S13d (T2, top 30 "
        f"works) and S13m (T5b, co-citation clusters) show the first author as '{L.WITHHELD}' where the work is a corpus record or the surname is "
        f"a corpus author's ({wl['S13d_withheld']} of {wl['S13d_rows']} and {wl['S13m_withheld']} of {wl['S13m_rows']}); S13h (T3c, top 20 records "
        "by local citations) drops the record identifier; titles are cut to 15 words.",
        f"S14 (7 sheets): the data of the {wl['figures']} figures in the order of the F13.6c draft, figure_k_<name>; Figure 5 (co-word map) has two "
        "data files, nodes and edges, and so two sheets.",
        f"Phase log: {reg['rows_in_phase_log']} phases, phase_F12_4 to phase_F13_8 (F13.7b included), from the one registry read of step 0.",
        "README: contents, corpus, date, sources of every sheet (first 16 characters of each source's sha256) and the licence sentence: abstracts "
        "and the texts of reference lists are not included.",
    ]))
    out.append("Sheets and rows (sources and full sha256 in tables/X2_sheet_sources.csv):\n")
    out.append(L.md_table(["sheet", "rows", "source"], [{"sheet": r["sheet"], "rows": r["rows"], "source": r["source_file"].replace(L.DPR, "")} for r in x2]) + "\n")
    out.append("## 3. Figure set (F2)\n")
    out.append(md("F2_figure_set").split("\n", 2)[2])
    out.append(WRAP(f"{fl['figures']} figures, all 300 dpi, at least {fl['min_width_px']} px wide; figure_k.tif and figure_k.png are byte copies of their "
                    "sources (G3). figures/figure_captions.txt gives number, label, caption, sources and sha256; each caption is the draft's text with "
                    "the editorial mark removed. tables/F1_figure_manifest.csv is F13.7a's manifest run unchanged on the F13.6c draft.") + "\n")
    out.append("## 4. For the professor\n")
    out.append(bullets([
        "Six figures, not seven: F13.7a's seventh was main.qmd's blind-spots figure, which the final text no longer uses (its data are a table, "
        "@tbl-blind-spots). Figure 4 is the v3.1 redraw of F13.7a, so the draft's redraw mark is settled by pointing the image line at it (F13.6d).",
        f"R13 hides the first author of {wl['S13d_withheld']} of the top 30 cited works and {wl['S13m_withheld']} of the 45 works of the co-citation "
        "clusters: most are corpus records or other works of corpus authors. Classics by non-corpus authors keep their names.",
        "S5c holds all 19 rows of F13.2e T1 (the nine of the professor's list and their 10 consequential rows), not only the nine.",
    ]))
    out.append("## 5. Gates\n")
    lines = ["| gate | what | verdict | planted violation caught |", "| --- | --- | --- | --- |"]
    lines += [f"| {g_['gate']} | {L.words(g_['what'], 26)} | {g_['verdict']} | {g_['planted_verdict']} ({g_['falsifiability']}) |" for g_ in gates]
    out.append("\n".join(lines) + "\n")
    first = rows(L.OUT / "phase_F13_7c_checkpoint_assertions_first_run.csv")
    if first:
        out.append(WRAP("First run: " + ", ".join(f"{g_['gate']} {g_['verdict']}" for g_ in first) + ". G2 failed on one cited classic of the RPYS "
                        "sheet (S11g, a 1985 peak) whose first author was flagged only by a two-letter name particle that also occurs in corpus authors' "
                        "names; name particles (El, Al, De, Van and similar) are now set aside in the withholding test, the sheets were rebuilt (one "
                        "name fewer withheld in S13d and in S13m) and every gate was run again.") + "\n")
    out.append("## 6. Independent verification\n")
    if ver:
        cols = [c for c in ("check", "what", "observed", "verdict") if c in ver[0]] or list(ver[0])[:4]
        lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
        lines += ["| " + " | ".join(" ".join(safe(r.get(k, "")).replace("|", "/").split()[:28]) for k in cols) + " |" for r in ver]
        out.append("\n".join(lines) + "\n")
        out.append(WRAP(f"A subagent wrote its own program (programs/f137c_verify.py) without reading this phase's other programs: "
                        f"{sum(1 for r in ver if r.get('verdict') == 'PASS')} PASS, {sum(1 for r in ver if r.get('verdict') == 'INFO')} informational, "
                        f"{sum(1 for r in ver if r.get('verdict') == 'FAIL')} FAIL.") + "\n")
    else:
        out.append("(not yet run)\n")
    out.append("## 7. Disclosures\n")
    out.append(bullets([
        "R19: f137a_lib, f137a_workbook, f137a_figures and f137a_step0 were imported unchanged; their module paths (output folder, draft, refused "
        "folders, xlsx name) are set by f137c_lib. Bytecode was off, so nothing was written into phase_F13_7a (G5).",
        "F13.7a's build writes a draft README; the driver replaces that sheet after the build (openpyxl load and save) and then applies F13.7a's "
        "deterministic zip. G3 compares every data sheet with its source after this step.",
        "R13: E1's Authors column was read in memory only, for the surname scan (G2) and for withholding cited works' first authors, as in "
        "F13.6c; it is not among the brief's listed inputs and nothing from it is written. Its digest is in the stamp.",
        f"Registry: one read in step 0 through F13.7a's phase_log ({reg['registry_rows']} rows in the file, {reg['rows_in_phase_log']} kept). Before step "
        "0 a shell command also counted the file's lines (its size only); the brief allows one read before step 1. The registry was not written.",
        "Before step 0 a console preview of phase_F13_3 T0d (an input) showed name fragments of reference strings on the console only; T0d is "
        "not in the workbook, as in F13.7a.",
        "R17: openpyxl writes each sheet through a temporary file in the system temp folder and removes it; the audit hook allows removals there "
        "only (its first run refused them and stopped the build).",
        "Figure 5 has two data sheets (nodes and edges) instead of one; Phase log ends at F13.8 because the registry holds no later phase.",
        "Figures were not opened or viewed (R18); metadata with Pillow. main.qmd and references.bib are outside the snapshot (F13.6d changes them); "
        "CORRECTIONS.csv is only hashed.",
        "The closing's first attempt stopped at G2, which also scans this report: two gate descriptions in the gates table ran over 30 words; "
        "the table now cuts them to 26 words. No data changed.",
        "No network (G6), heredoc, workflow or skill; one subagent (the verifier); nothing in .claude/; nothing deleted or moved.",
        "Registry row: kept, unwritten, in run_logs/registry_rows_pending.json; the main session writes the registry.",
    ]))
    if rows_reg:
        out.append("## 8. Registry row (pending; written by the main session)\n")
        for r in rows_reg:
            out.append(WRAP(f"{r['phase_id']} | {r['status']} | produced_numbers {r['produced_numbers']} | safe_to_publish {r['safe_to_publish']} | "
                            f"{r['file_count']} files, {r['bytes']} bytes | path {r['path']}") + "\n")
    return "\n".join(out)
