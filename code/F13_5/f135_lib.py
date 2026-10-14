"""Phase F13.5 - shared helpers (copied from F12.3c; changed: (i) the input is E1, the full Scopus export (841 records), read as
a CSV stream of which only EID, Year, Title, Author Keywords and Index Keywords are kept (R13); PREV = phase_F12_3c, the phase
this one compares with; the registry is not read). Writes only inside the phase folder. The repository root is found from this
file's place (programs -> phase_F13_5 -> dprg_revision_2026 -> outputs -> ROOT)."""
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
V3E1 = TABLES / "v3_on_E1"
FIGURES = OUT / "figures"
RUN_LOGS = OUT / "run_logs"
DPRG = ROOT / "outputs" / "dprg_revision_2026"
F123 = DPRG / "phase_F12_3"
F123B = DPRG / "phase_F12_3b"
PREV = DPRG / "phase_F12_3c"
PREV_T, PREV_F = PREV / "tables", PREV / "figures"

E1 = "outputs/dprg_revision_2026/author_exports_2026_10/scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
E1_README = "outputs/dprg_revision_2026/author_exports_2026_10/README_exports.txt"
E1_COLS = ("EID", "Year", "Title", "Author Keywords", "Index Keywords")
SEP = "; "
FORBIDDEN = {"PLAN_DPRG_MASTER_2026_09.md", "HANDOFF_DPRG_2026_09_11.md", "PLAN_SJAITU_META_ANALYSIS_PROFESSOR.md",
             "PROJECT_STRUCTURE_PROFESSOR.md", ".env", "PHASE_REGISTRY.csv"}
FORBIDDEN_DIRS = {"phase_F13_2"}

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ORCID = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b")
HYPHENS = "-" + chr(0x2010) + chr(0x2011) + chr(0x2012) + chr(0x2013) + chr(0x2014) + chr(0x2212)
TRAIL = ".,;:!?\"'()[]{}*" + chr(0x2019) + chr(0x201D) + chr(0x201C)


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


def read_csv_path(p):
    return list(csv.DictReader(io.StringIO(Path(p).read_bytes().decode("utf-8-sig"), newline="")))


def read_csv(rel):
    return read_csv_path(path(rel))


def norm_kw(s):
    """The one normalisation for both keyword kinds: lowercase; hyphens and dashes to spaces; whitespace collapsed;
    trailing (and leading) punctuation trimmed; no stemming."""
    s = str(s or "").lower()
    for h in HYPHENS:
        s = s.replace(h, " ")
    s = " ".join(s.split())
    while s and s[-1] in TRAIL + " " and not (s[-1] == ")" and "(" in s):
        s = s[:-1]
    while s and s[0] in TRAIL + " " and not (s[0] == "(" and ")" in s):
        s = s[1:]
    return s


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


def write_md(p, title, fields, rows, note=""):
    text = f"## {title}\n\n" + (wrap(note) + "\n\n" if note else "") + md_table(fields, rows) + "\n"
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_bytes(text.encode("utf-8"))
    return text


def jdump(obj, p):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_bytes(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8"))


def jload(p):
    return json.loads(Path(p).read_bytes().decode("utf-8"))


def pct(n, d):
    return f"{100.0 * n / d:.1f}" if d else ""


def split_kw(cell):
    """A keyword cell of E1: keywords separated by '; ' (the export's separator); empty parts dropped."""
    return [k for k in str(cell or "").split(SEP) if k.strip()]


def load_records(titles=False):
    """E1 as a stream: EID -> {year, ak (raw author keywords), ik (raw index keywords)[, title]}. The CSV parser tokenises each
    row; only the five columns of E1_COLS are kept and the rest of the row is dropped at once (R13). Nothing else is stored."""
    csv.field_size_limit(2 ** 31 - 1)
    recs = {}
    with open(path(E1), "r", encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh)
        header = next(rd)
        idx = {c: header.index(c) for c in E1_COLS}
        for row in rd:
            if not row:
                continue
            keep = {c: row[i] for c, i in idx.items()}
            del row
            eid = keep["EID"].strip()
            assert eid and eid not in recs, ("EID empty or repeated", eid)
            r = {"year": int(keep["Year"]), "ak": split_kw(keep["Author Keywords"]), "ik": split_kw(keep["Index Keywords"]),
                 "ak_cell": bool(keep["Author Keywords"].strip()), "ik_cell": bool(keep["Index Keywords"].strip()),
                 "semicolon_without_space": sum(keep[c].count(";") - keep[c].count(SEP) for c in ("Author Keywords", "Index Keywords"))}
            if titles:
                r["title"] = keep["Title"]
            recs[eid] = r
    return recs
