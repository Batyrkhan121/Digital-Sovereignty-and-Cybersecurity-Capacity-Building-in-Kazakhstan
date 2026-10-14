"""Phase F13.7a - shared helpers. Reads the tables of closed phases, the F13.6b draft (part 1) and the F13.6a maps; writes only inside
this phase's folder (tables/, render/, supplementary/, figures/, run_logs/). phase_F13_3b, phase_F13_6c and .claude are refused by path();
PHASE_REGISTRY.csv only through registry_once() in step 0 (one read, before step 1; brief)."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
ROOT = OUT.parents[2]
TABLES, RENDER, SUPP, FIGURES, RUN_LOGS = OUT / "tables", OUT / "render", OUT / "supplementary", OUT / "figures", OUT / "run_logs"
DPR = "outputs/dprg_revision_2026/"
DRAFT = DPR + "phase_F13_6b/draft/main_v2.qmd"
E1_INDEX = DPR + "phase_F13_6b/tables/E1_evidence_index.csv"
N1 = DPR + "phase_F13_6a/tables/N1_manuscript_numbers.csv"
N3 = DPR + "phase_F13_6a/tables/N3_figures_tables.csv"
T2F_V31 = DPR + "phase_F13_2e/tables/T2f_v31_collaboration_by_year.csv"
EXPORTS = DPR + "author_exports_2026_10/"
README_EXPORTS, MANIFEST, LONG = EXPORTS + "README_exports.txt", EXPORTS + "manifest_year_series.json", EXPORTS + "scopus_years_all_series_long.csv"
FIXED_DATE = "2026-10-13"
FORBIDDEN = {"PLAN_DPRG_MASTER_2026_09.md", "HANDOFF_DPRG_2026_09_11.md", "PLAN_SJAITU_META_ANALYSIS_PROFESSOR.md",
             "PROJECT_STRUCTURE_PROFESSOR.md", ".env", "PHASE_REGISTRY.csv"}
FORBIDDEN_DIRS = {"phase_F13_3b", "phase_F13_6c", ".claude"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ORCID = re.compile(r"\b(?:0000|0009)-\d{4}-\d{4}-\d{3}[\dX]\b")
AUTHOR_COLS = {"authors", "author", "author full names", "author(s) id", "authors with affiliations", "correspondence address",
               "author_names", "author_ids", "email", "orcid", "name", "surname", "abstract", "references"}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def path(rel):
    p = ROOT / rel
    assert p.name not in FORBIDDEN and not (set(Path(rel).parts) & FORBIDDEN_DIRS), p
    return p


def registry_once():
    """The one read of PHASE_REGISTRY.csv the brief allows (step 0, before step 1): bytes and digest."""
    p = ROOT / DPR / "PHASE_REGISTRY.csv"
    b = p.read_bytes()
    return b, hashlib.sha256(b).hexdigest()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(rel):
    return read_csv_path(path(rel))


def read_csv_path(p):
    return list(csv.DictReader(io.StringIO(Path(p).read_bytes().decode("utf-8-sig"), newline="")))


def header_of(p):
    return next(csv.reader(io.StringIO(Path(p).read_bytes().decode("utf-8-sig").split("\n", 1)[0])))


def shape_counts(text):
    return {"e_mail_shaped": len(EMAIL.findall(text)), "orcid_shaped": len(ORCID.findall(text))}


def write_csv(p, fields, rows):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in fields})
    p.write_bytes(buf.getvalue().encode("utf-8"))


def wrap(text, width=25):
    out = []
    for para in text.split("\n"):
        words = para.split()
        out += [" ".join(words[i:i + width]) for i in range(0, len(words), width)] or [""]
    return "\n".join(out)


def md_table(fields, rows):
    def cell(v):
        return str(v).replace("|", "/").replace("\n", " ")
    out = ["| " + " | ".join(fields) + " |", "|" + "|".join(" --- " for _ in fields) + "|"]
    out += ["| " + " | ".join(cell(r.get(k, "")) for k in fields) + " |" for r in rows]
    return "\n".join(out)


def table(name, title, fields, rows, note="", md_rows=None):
    write_csv(TABLES / f"{name}.csv", fields, rows)
    shown = rows if md_rows is None else rows[:md_rows]
    tail = f"\n\n(first {md_rows} of {len(rows)} rows; all in tables/{name}.csv)" if md_rows is not None and len(rows) > md_rows else ""
    text = f"## {title}\n\n" + (wrap(note) + "\n\n" if note else "") + md_table(fields, shown) + tail + "\n"
    (TABLES / f"{name}.md").write_bytes(text.encode("utf-8"))
    return text


def jdump(obj, p):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_bytes(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8"))


def jload(p):
    return json.loads(Path(p).read_bytes().decode("utf-8"))


def words(s, n):
    w = str(s or "").split()
    return " ".join(w[:n]) + (" ..." if len(w) > n else "")
