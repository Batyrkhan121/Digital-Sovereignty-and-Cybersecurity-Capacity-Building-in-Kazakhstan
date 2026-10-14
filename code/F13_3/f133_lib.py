"""Phase F13.3 - shared Python helpers (step 0, gates, report, closing). Local files only; writes only inside the phase folder.
ROOT is found from this file's place (programs -> phase_F13_3 -> dprg_revision_2026 -> outputs -> ROOT). The analysis itself runs in
R (bibliometrix); see f133_lib.R and f133_main.R. phase_F13_5 and phase_F13_2b (parallel sessions) and PHASE_REGISTRY.csv are never
read or written here; the merged corpus M of F13.1 is not read.

E1 is read by Python only in the gates: EID, References (emptiness only) and Authors (surname set for the leak check, in memory,
never written or printed). E2 is not read by Python."""
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
TABLES = OUT / "tables"
FIGURES = OUT / "figures"
DATA = OUT / "data"
RUN_LOGS = OUT / "run_logs"
DPR = "outputs/dprg_revision_2026/"
EXP = DPR + "author_exports_2026_10/"
E1 = EXP + "scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
E2 = EXP + "wos_full_TS_KZ_2003_2025_2026-10-13.txt"
README = EXP + "README_exports.txt"
PAIRS = DPR + "phase_F13_1/tables/T3a_pairs.csv"
THES = DPR + "phase_F12_3c/tables/thesaurus.csv"
EXPECTED = {"E1": "fe01023d23afe95df83d594fdfea2c3b488e52ffb8778def4067a2d795a991f3",
            "E2": "413b0fa8ba8dd496072367601b7ca66bf0c7cac01d30553aa702b288dd402160"}
FORBIDDEN = {"PLAN_DPRG_MASTER_2026_09.md", "HANDOFF_DPRG_2026_09_11.md", "PLAN_SJAITU_META_ANALYSIS_PROFESSOR.md",
             "PROJECT_STRUCTURE_PROFESSOR.md", ".env", "PHASE_REGISTRY.csv", "merged_corpus_2026-10-13.csv"}
FORBIDDEN_DIRS = {"phase_F13_5", "phase_F13_2b", ".claude"}
GITIGNORE_LINE = "outputs/dprg_revision_2026/phase_F13_3/data/"
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ORCID = re.compile(r"\b(?:0000|0009)-\d{4}-\d{4}-\d{3}[\dX]\b")
PERIODS = [("2003-2016", 2003, 2016), ("2017-2021", 2017, 2021), ("2022-2025", 2022, 2025)]
import os
RSCRIPT = Path(os.environ.get("RSCRIPT", "Rscript"))


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def path(rel):
    p = ROOT / rel
    assert p.name not in FORBIDDEN and not (set(p.parts) & FORBIDDEN_DIRS), p
    return p


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(p):
    csv.field_size_limit(1 << 30)
    return list(csv.DictReader(io.StringIO(Path(p).read_bytes().decode("utf-8-sig"), newline="")))


def e1_columns(keep):
    """Only the named E1 columns, row by row; the rest of each row is dropped at once."""
    csv.field_size_limit(1 << 30)
    rd = csv.reader(io.StringIO(path(E1).read_bytes().decode("utf-8-sig"), newline=""))
    header = next(rd)
    idx = {c: header.index(c) for c in keep}
    out = []
    for row in rd:
        out.append({c: row[i] for c, i in idx.items()})
        del row
    return out


def shape_counts(text):
    return {"e_mail_shaped": len(EMAIL.findall(text)), "orcid_shaped": len(ORCID.findall(text))}


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


def jdump(obj, p):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_bytes(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8"))


def jload(p):
    return json.loads(Path(p).read_bytes().decode("utf-8"))


def folder_files(p):
    """All files under p (no symlinks followed), as {posix path relative to p: (bytes, sha256)}."""
    out = {}
    stack = [Path(p)]
    while stack:
        d = stack.pop()
        for e in sorted(d.iterdir(), key=lambda x: x.name):
            if e.is_symlink():
                continue
            if e.is_dir():
                stack.append(e)
            else:
                out[e.relative_to(p).as_posix()] = (e.stat().st_size, sha256_file(e))
    return out
