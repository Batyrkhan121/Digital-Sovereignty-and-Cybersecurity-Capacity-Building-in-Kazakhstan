"""Phase F13.2e - shared helpers. Reuses, read-only: phase_F13_2d/programs (f132d_lib for F13.2c's parsing; f132d_build.tables_for, the
function that applies a thesaurus and computes T3a/T3c/T3d/T2f/T2f2) and phase_F13_2b/programs/f132b_lib (n_authors, mean, median: the
T2g rule). E1 is read by an own whitelist loader: EID, Year, Affiliations, and Authors only as a count (names dropped at once, R13).
Writes only inside this phase's folder (its own table helpers; the imported modules' writers are never called). phase_F13_3b and
PHASE_REGISTRY.csv are refused by path()."""
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
RUN_LOGS = OUT / "run_logs"
DPR = "outputs/dprg_revision_2026/"
F132D_PROGRAMS = ROOT / DPR / "phase_F13_2d" / "programs"
F132B_PROGRAMS = ROOT / DPR / "phase_F13_2b" / "programs"
sys.path.insert(0, str(F132B_PROGRAMS))
sys.path.insert(0, str(F132D_PROGRAMS))
import f132d_lib as D  # noqa: E402  (F13.2d's helpers; it imports F13.2c's parsing)
import f132d_build as DB  # noqa: E402  (tables_for: the same recount function)
import f132b_lib as BL  # noqa: E402  (n_authors, mean, median: F13.2b's T2g rule)

C = D.C
E1 = D.E1
E1_SHA = D.E1_SHA
DT = DPR + "phase_F13_2d/tables/"
IN_V3 = {"thesaurus": DT + "institutions_thesaurus_v3.csv", "T3a": DT + "T3a_v3_kz_institutions.csv", "T3c": DT + "T3c_v3_concentration.csv",
         "T3d": DT + "T3d_v3_kz_institution_pairs.csv", "T2f": DT + "T2f_v3_collaboration_by_year.csv",
         "T2f2": DT + "T2f2_v3_collaboration_by_period.csv", "T4": DT + "T4_residual.csv"}
IN_T2G = DPR + "phase_F13_2b/tables/T2g_authors_by_collaboration.csv"
IN_COUNTRIES = DPR + "phase_F13_2b/tables/scopus_country_names.csv"
INPUTS = [E1] + list(IN_V3.values()) + [IN_T2G, IN_COUNTRIES]
FORBIDDEN = {"PLAN_DPRG_MASTER_2026_09.md", "HANDOFF_DPRG_2026_09_11.md", "PLAN_SJAITU_META_ANALYSIS_PROFESSOR.md",
             "PROJECT_STRUCTURE_PROFESSOR.md", ".env", "PHASE_REGISTRY.csv"}
FORBIDDEN_DIRS = {"phase_F13_3b", ".claude"}
KZ, COLLAB, PERIODS, YEARS = C.KZ, C.COLLAB, C.PERIODS, C.YEARS
AUTHOR_COLS = C.AUTHOR_COLS


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


def read_csv(rel):
    return list(csv.DictReader(io.StringIO(path(rel).read_bytes().decode("utf-8-sig"), newline="")))


def read_csv_path(p):
    return list(csv.DictReader(io.StringIO(Path(p).read_bytes().decode("utf-8-sig"), newline="")))


def load_e1():
    """EID, Year, Affiliations of each record and the number of authors (F13.2b's n_authors on the Authors cell; the cell itself is
    dropped at once)."""
    csv.field_size_limit(1 << 30)
    recs = []
    with open(path(E1), "r", encoding="utf-8-sig", newline="") as f:
        rd = csv.reader(f)
        header = next(rd)
        ie, iy, iaf, iau = header.index("EID"), header.index("Year"), header.index("Affiliations"), header.index("Authors")
        for row in rd:
            recs.append({"eid": row[ie], "year": row[iy], "affiliations": row[iaf], "n_authors": BL.n_authors(row[iau])})
            row = None
    return len(header), recs


def records():
    """R as F13.2d's build constructs it (parse_line of F13.2c; countries by F13.2b's list), plus n_authors."""
    ncols, recs = load_e1()
    cset = {r["country_name"] for r in read_csv(IN_COUNTRIES)}
    R = []
    for r in recs:
        lines = [C.parse_line(x) for x in C.aff_lines(r["affiliations"])]
        A = {p["country_part"] for p in lines if p["country_part"] in cset}
        y = C.year_of(r["year"])
        R.append({"eid": r["eid"], "year": y, "period": C.period_of(y), "lines": lines, "A": A, "foreign_A": sorted(A - {KZ}),
                  "n_authors": r["n_authors"]})
    return ncols, R


def shape_counts(text):
    return D.shape_counts(text)


def write_csv(p, fields, rows):
    assert not ({f.lower() for f in fields} & AUTHOR_COLS), fields
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in fields})
    p.write_bytes(buf.getvalue().encode("utf-8"))


def wrap(text, width=25):
    return D.wrap(text, width)


def md_table(fields, rows):
    return D.md_table(fields, rows)


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


def pct(n, d):
    return f"{100.0 * n / d:.1f}" if d else ""


def install_r17_guard():
    D.install_r17_guard()
