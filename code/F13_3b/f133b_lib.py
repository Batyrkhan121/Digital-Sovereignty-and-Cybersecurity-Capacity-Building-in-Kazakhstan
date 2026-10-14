"""Phase F13.3b - shared Python helpers. Local files only (no network); writes only inside the phase folder. ROOT is found from this
file's place (programs -> phase_F13_3b -> dprg_revision_2026 -> outputs -> ROOT). phase_F13_2e, tools/ and PHASE_REGISTRY.csv
(parallel session) are never read or written. E1 is read by column whitelist; 'Authors' only in memory (step-3 control, gate G2)."""
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
E1 = DPR + "author_exports_2026_10/scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
E1_SHA = "fe01023d23afe95df83d594fdfea2c3b488e52ffb8778def4067a2d795a991f3"
README = DPR + "author_exports_2026_10/README_exports.txt"
F133 = DPR + "phase_F13_3/"
REFS = F133 + "data/references_repaired.csv"
F133_LIB_R = F133 + "programs/f133_lib.R"
F133_TABLES = {k: F133 + "tables/" + v for k, v in {
    "T2a": "T2a_cited_thresholds.csv", "T2b": "T2b_top30_cited_works_work_key.csv", "T4a": "T4a_local_citations.csv",
    "T4b": "T4b_top20_LCS.csv", "T5a": "T5a_coupling_summary.csv", "T5c": "T5c_coupling_sensitivity.csv",
    "T5d": "T5d_work_key_coupling_clusters.csv", "T6a": "T6a_cocitation_summary.csv", "T6a2": "T6a2_cocitation_work_key_sensitivity.csv",
    "thesaurus": "cited_sources_thesaurus.csv", "T3a": "T3a_top30_sources_by_references.csv", "T3c": "T3c_cited_sources_summary.csv",
    "T6c": "T6c_source_cocitation_summary.csv", "T6c2": "T6c2_source_clusters.csv", "T0a": "T0a_reference_counts.csv"}.items()}
E1_COLS = ["EID", "Year", "Title", "Source title", "DOI", "Document Type", "Cited by", "Author Keywords"]
FORBIDDEN = {"PLAN_DPRG_MASTER_2026_09.md", "HANDOFF_DPRG_2026_09_11.md", "PLAN_SJAITU_META_ANALYSIS_PROFESSOR.md",
             "PROJECT_STRUCTURE_PROFESSOR.md", ".env", "PHASE_REGISTRY.csv"}
FORBIDDEN_DIRS = {"phase_F13_2e", "tools", ".claude"}
GITIGNORE_LINE = "outputs/dprg_revision_2026/phase_F13_3b/data/"
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ORCID = re.compile(r"\b(?:0000|0009)-\d{4}-\d{4}-\d{3}[\dX]\b")
PERIODS = [("2003-2016", 2003, 2016), ("2017-2021", 2017, 2021), ("2022-2025", 2022, 2025)]
import os
RSCRIPT = Path(os.environ.get("RSCRIPT", "Rscript"))
PY = Path(sys.executable)


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def path(rel):
    p = ROOT / rel
    assert p.name not in FORBIDDEN and not (set(Path(rel).parts) & FORBIDDEN_DIRS), p
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


def write_csv(p, fields, rows):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in fields})
    p.write_bytes(buf.getvalue().encode("utf-8"))


def jdump(obj, p):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_bytes(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8"))


def jload(p):
    return json.loads(Path(p).read_bytes().decode("utf-8"))


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


def folder_files(p):
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


def norm_title(s):
    """Step-3 normalisation: uppercase, Latin letters and digits kept, everything else a space, spaces collapsed."""
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", (s or "").upper()).split())


def cut_words(s, n):
    return " ".join((s or "").split()[:n])


def tc_name(s):
    return re.sub(r"(^|[ \-'\u2019])([^\W\d_])", lambda m: m.group(1) + m.group(2).upper(), (s or "").lower())


def period_of(y):
    return "2003-2016" if y <= 2016 else ("2017-2021" if y <= 2021 else "2022-2025")


def year_int(s):
    try:
        return int(float(str(s).strip()))
    except ValueError:
        return None
