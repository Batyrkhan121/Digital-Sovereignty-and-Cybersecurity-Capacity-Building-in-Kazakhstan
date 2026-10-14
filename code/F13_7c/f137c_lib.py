"""Phase F13.7c - shared helpers. R19: the F13.7a programs (f137a_lib, f137a_workbook, f137a_figures with the manifest, f137a_step0's
phase log) are imported unchanged from phase_F13_7a/programs and pointed at this phase's folder by setting their module paths; their
source list is extended here (sheets_v2). Nothing in phase_F13_7a is written (bytecode off; G5).
Reads: the inputs of the brief (phase_F13_7a supplementary/tables/programs, the F13.6c draft for the figure order and captions, the
tables and figures of closed phases). E1's Authors column is read only in memory for the R13 check and for withholding a cited work's
first author who is also a corpus author (as in F13.6c); no name is written or printed. Refused by path(): phase_F13_6d, jcp_submission,
tools, .claude, main.qmd, references.bib, CORRECTIONS.csv, PHASE_REGISTRY.csv (its one read goes through f137a_lib.registry_once in
step 0) and the files the brief forbids."""
import sys
sys.dont_write_bytecode = True

import csv
import io
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
ROOT = OUT.parents[2]
DPR = "outputs/dprg_revision_2026/"
P7A = ROOT / DPR / "phase_F13_7a"
sys.path.insert(0, str(P7A / "programs"))
import f137a_lib as A  # noqa: E402
import f137a_figures as FG  # noqa: E402  (BASE is fixed below to F13.7a's v3.1 figure)
import f137a_workbook as WB  # noqa: E402
import f137a_step0 as S0A  # noqa: E402

A.OUT = OUT
A.TABLES, A.RENDER, A.SUPP, A.FIGURES, A.RUN_LOGS = OUT / "tables", OUT / "render", OUT / "supplementary", OUT / "figures", OUT / "run_logs"
A.DRAFT = DPR + "phase_F13_6c/draft/main_v2.qmd"
A.FORBIDDEN = {"PLAN_DPRG_MASTER_2026_09.md", "HANDOFF_DPRG_2026_09_11.md", "PLAN_SJAITU_META_ANALYSIS_PROFESSOR.md", "PROJECT_STRUCTURE_PROFESSOR.md",
               ".env", "PHASE_REGISTRY.csv", "main.qmd", "references.bib", "CORRECTIONS.csv"}
A.FORBIDDEN_DIRS = {"phase_F13_6d", "jcp_submission", "tools", ".claude"}
FG.BASE = P7A / "figures" / "Fig_collaboration_type_by_year_v31"
WB.XLSX = A.SUPP / "Supplementary_tables.xlsx"

TABLES, SUPP, FIGURES, RUN_LOGS = A.TABLES, A.SUPP, A.FIGURES, A.RUN_LOGS
DRAFT = A.DRAFT
E1 = DPR + "author_exports_2026_10/scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
FIXED_DATE = A.FIXED_DATE
path, sha256_file, read_csv, read_csv_path, write_csv, table, jdump, jload, words, wrap, md_table, now, shape_counts = (
    A.path, A.sha256_file, A.read_csv, A.read_csv_path, A.write_csv, A.table, A.jdump, A.jload, A.words, A.wrap, A.md_table, A.now, A.shape_counts)
EMAIL, ORCID, AUTHOR_COLS = A.EMAIL, A.ORCID, A.AUTHOR_COLS
WITHHELD = "withheld (R13)"
SHORT = {"fig-normalised-growth": "normalised_growth", "fig-activity-index-comparators": "activity_index",
         "fig-annual-output-by-type": "output_by_type", "fig-collaboration-type-by-year": "collaboration_v31",
         "fig-coword-author-keywords": "coword", "fig-coverage-union-by-year": "coverage_union"}


def t(phase, name):
    return f"{DPR}{phase}/tables/{name}.csv"


def install_r17_guard():
    """R17: no program of this phase deletes, moves or links anything. One exception: openpyxl writes each sheet through a temporary
    file in the system temp folder and removes it; removals are allowed there only (outside the repository)."""
    import os
    import tempfile
    tmp = os.path.normcase(os.path.abspath(tempfile.gettempdir()))  # tempfile's probe runs before the hook
    root = os.path.normcase(str(ROOT))
    assert not tmp.startswith(root)

    def hook(event, args):
        if event in {"os.remove", "os.rmdir", "os.rename", "shutil.rmtree", "shutil.move", "os.symlink", "os.link", "os.truncate"}:
            target = args[0] if args else ""
            if event == "os.remove" and isinstance(target, (str, bytes, os.PathLike)):
                p = os.path.normcase(os.path.abspath(os.fsdecode(target)))
                if p.startswith(tmp + os.sep):
                    return
            raise PermissionError(f"R17: {event} refused for {target}")
    sys.addaudithook(hook)


# ---------------------------------------------------------------- figures of the F13.6c draft, in order of appearance
def caption_clean(c):
    """The caption as text: editorial marks [[...]] removed, spaces collapsed."""
    return " ".join(re.sub(r"\[\[[^\]]*\]\]", " ", c).split())


def figure_order():
    lines = path(DRAFT).read_bytes().decode("utf-8").split("\n")
    draft_dir = path(DRAFT).parent
    out = []
    for i, ln in enumerate(lines, 1):
        m = re.match(r"^!\[(.*)\]\(([^)]+)\)\{#(fig-[\w-]+)\}", ln)
        if not m:
            continue
        label = m.group(3)
        if label == "fig-collaboration-type-by-year":
            base = FG.BASE  # the v3.1 redraw of F13.7a (brief)
        else:
            base = (draft_dir / m.group(2)).resolve().with_suffix("")
        csvs = sorted(x for x in base.parent.iterdir() if x.name.startswith(base.name) and x.suffix == ".csv")
        out.append({"k": len(out) + 1, "label": label, "draft_line": i, "caption_raw": m.group(1), "caption": caption_clean(m.group(1)),
                    "draft_path": m.group(2), "base": base, "tif": Path(str(base) + ".tif"), "png": Path(str(base) + ".png"), "csvs": csvs})
    return out


def rel(p):
    return Path(p).resolve().relative_to(ROOT).as_posix()


def figure_sheets(figs=None):
    figs = figs if figs is not None else figure_order()
    out = []
    for f in figs:
        short = SHORT.get(f["label"], f["label"][4:].replace("-", "_"))
        for c in f["csvs"]:
            suffix = c.stem[len(f["base"].name):].lstrip("_")
            name = f"figure_{f['k']}_{short}" + (f"_{suffix}" if suffix else "")
            out.append((name[:31], rel(c), f"Data of Figure {f['k']} (@{f['label']})" + (f", {suffix}" if suffix else "")))
    return out


# ---------------------------------------------------------------- the workbook's source list, v2
S13 = [
    ("S13a_F133b_T0_strings_vs_key", t("phase_F13_3b", "T0_strings_vs_work_key"), "Reference strings against the work key (F13.3b T0)"),
    ("S13b_F133b_T1a_key_coverage", t("phase_F13_3b", "T1a_key_coverage"), "Coverage of the work key (F13.3b T1a)"),
    ("S13c_F133b_T1c_key_sensitivity", t("phase_F13_3b", "T1c_key_sensitivity"), "Sensitivity of the work key (F13.3b T1c)"),
    ("S13d_F133b_T2_top30_works", "derived:S13d_top30_works", "Top 30 cited works by work key (F13.3b T2); first author withheld where a corpus author"),
    ("S13e_F133b_T2a_thresholds", t("phase_F13_3b", "T2a_thresholds"), "Works cited by at least 2, 5 and 10 records (F13.3b T2a)"),
    ("S13f_F133b_T3a_local_citations", t("phase_F13_3b", "T3a_local_citations_title"), "Local citations by title matching (F13.3b T3a)"),
    ("S13g_F133b_T3b_local_by_period", t("phase_F13_3b", "T3b_local_citations_by_period"), "Local citations by period (F13.3b T3b)"),
    ("S13h_F133b_T3c_top20_LCS", "derived:S13h_top20_LCS", "Top 20 records by local citations (F13.3b T3c); identifier dropped, title cut"),
    ("S13i_F133b_T4a_coupling", t("phase_F13_3b", "T4a_coupling_workkey"), "Bibliographic coupling by work key (F13.3b T4a)"),
    ("S13j_F133b_T4b_coupling_clust", t("phase_F13_3b", "T4b_coupling_clusters"), "Coupling clusters (F13.3b T4b)"),
    ("S13k_F133b_T4c_coupling_sens", t("phase_F13_3b", "T4c_coupling_sensitivity"), "Coupling sensitivity (F13.3b T4c)"),
    ("S13l_F133b_T5a_cocitation", t("phase_F13_3b", "T5a_cocitation_workkey"), "Co-citation by work key (F13.3b T5a)"),
    ("S13m_F133b_T5b_cocit_clusters", "derived:S13m_cocitation_clusters", "Co-citation clusters (F13.3b T5b); first author withheld where a corpus author"),
    ("S13n_F133b_T5c_cocit_sens", t("phase_F13_3b", "T5c_cocitation_sensitivity"), "Co-citation sensitivity (F13.3b T5c)"),
    ("S13o_F133b_T6a_sources", t("phase_F13_3b", "T6a_sources_parse_rule"), "Cited sources by the parse rule, top 30 (F13.3b T6a)"),
    ("S13p_F133b_T6a2_sources_summary", t("phase_F13_3b", "T6a2_sources_summary"), "Cited sources: summary (F13.3b T6a2)"),
]
DERIVED_ORIGIN_V2 = {
    "S13d_top30_works": "phase_F13_3b T2_top30_works (first author withheld where the work is a corpus record or the surname is a corpus author's; title cut to 15 words)",
    "S13h_top20_LCS": "phase_F13_3b T3c_top20_LCS (doi_or_eid dropped; title cut to 15 words)",
    "S13m_cocitation_clusters": "phase_F13_3b T5b_cocitation_clusters (first author withheld where the surname is a corpus author's or the work is a corpus record of T2; title cut to 15 words)",
    "phase_log_from_registry": "PHASE_REGISTRY.csv, one read in step 0 (rows phase_F12_4 and phase_F13_1 to phase_F13_8; note cut to 27 words)",
}


def sheets_v2(figs=None):
    out = []
    for name, src, desc in WB.SHEETS:
        if name == "S5c_inst_name_rules_v3":
            out.append(("S5c_inst_v31_changes", t("phase_F13_2e", "T1_thesaurus_v31_changes"),
                        "Institutions thesaurus: the v3.1 changes, 9 rows of the professor's list and 10 consequential rows (F13.2e T1)"))
            out.append(("S5d_inst_name_rules_v3", src, desc))
        elif name == "S6c_pairs_v31_top30":
            out.append((name, src, desc))
            out.append(("S6d_collab_by_period_v31", t("phase_F13_2e", "T2f2_v31_collaboration_by_period"), "Collaboration type by period (F13.2e T2f2_v31)"))
            out.append(("S6e_authors_by_collab_v31", t("phase_F13_2e", "T2g_v31_authors_by_collaboration"), "Authors per record by collaboration type (F13.2e T2g_v31)"))
        elif name == "Phase_log":
            out += S13 + figure_sheets(figs)
            out.append(("Phase_log", src, "Phases F12.4 - F13.8 from PHASE_REGISTRY.csv (one read in step 0)"))
        else:
            out.append((name, src, desc))
    return out


# ---------------------------------------------------------------- R13 (memory only)
_SUR = {}


def corpus_tokens():
    """(tokens >= 4 letters for the scan, all tokens >= 2 letters for withholding) of E1's Authors column; memory only."""
    if not _SUR:
        csv.field_size_limit(1 << 30)
        trail = re.compile(r"(?:\s+[A-ZЀ-Я][a-zа-я]{0,2}\.-?)+\s*$")
        long_, all_ = set(), set()
        with open(path(E1), "r", encoding="utf-8-sig", newline="") as f:
            rd = csv.reader(f)
            h = next(rd)
            ai = h.index("Authors")
            for row in rd:
                for a in row[ai].split(";"):
                    s = trail.sub("", a.strip())
                    for tok in re.split(r"[\s\-]+", s):
                        if tok.isalpha() and tok[:1].isupper():
                            all_.add(tok.lower()) if len(tok) >= 2 else None
                            long_.add(tok) if len(tok) >= 4 else None
                row = None
        _SUR["long"], _SUR["all"] = long_, all_
    return _SUR["long"], _SUR["all"]


def organisation_words():
    """Words of organisation and place names that reach the tables as such (institutions v3.1, foreign institutions, countries,
    sources and publishers): set aside in the surname scan, as in F13.6c (plus sources and publishers)."""
    allowed = set()
    for rel_, col in ((t("phase_F13_2e", "T3a_v31_kz_institutions"), "institution"), (t("phase_F13_2b", "T3e_foreign_institutions"), "institution"),
                      (t("phase_F13_2b", "scopus_country_names"), "country_name"), (t("phase_F13_2", "T2a_sources"), "publisher"),
                      (t("phase_F13_2", "T2a_sources"), "source_title"), (t("phase_F13_2", "T2d_publishers"), "publisher")):
        rows = read_csv(rel_)
        if rows and col in rows[0]:
            for r in rows:
                allowed |= set(re.findall(r"[^\W\d_]+", r[col]))
    return allowed


PARTICLES = {"al", "el", "de", "da", "di", "du", "la", "le", "van", "von", "der", "den", "del", "dos", "bin", "ibn", "abu", "ben", "mc", "mac", "st"}


def is_corpus_author(name):
    """True when a token of the name (two letters or more, name particles such as El, Al, De or Van set aside) is a token of a corpus
    author's name: the short tokens catch surnames like <surname>, <surname> or <surname>, which the four-letter scan of G2 cannot."""
    _, all_ = corpus_tokens()
    return any(tok.lower() in all_ for tok in re.findall(r"[^\W\d_]+", name or "") if len(tok) >= 2 and tok.lower() not in PARTICLES)


def surname_regex():
    long_, _ = corpus_tokens()
    names = sorted(long_ - organisation_words())
    return re.compile(r"\b(?:" + "|".join(re.escape(n) for n in names) + r")\b"), len(long_), len(names)
