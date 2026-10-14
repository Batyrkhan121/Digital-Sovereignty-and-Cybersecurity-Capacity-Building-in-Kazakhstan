"""Phase F13.4b - shared helpers (copied from F13.4's library; changed: eleven series (the four all-output series of UZ, AZ, BY,
KG added), the five countries with their topic and all-output series, the forks' folders of this brief). E1 is read for EID and
Year only (R13). Writes only inside the phase folder; the root is found from this file's place. The registry is not read."""
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
RUN_LOGS = OUT / "run_logs"
DPRG = ROOT / "outputs" / "dprg_revision_2026"

EXPORTS = "outputs/dprg_revision_2026/author_exports_2026_10"
E1 = EXPORTS + "/scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
MANIFEST = EXPORTS + "/manifest_year_series.json"
README = EXPORTS + "/README_exports.txt"
LONG = EXPORTS + "/scopus_years_all_series_long.csv"
F134_T2B = "outputs/dprg_revision_2026/phase_F13_4/tables/T2b_activity_index_periods.csv"
F134_T2D = "outputs/dprg_revision_2026/phase_F13_4/tables/T2d_activity_index_windows.csv"
SERIES = {"KZ_all": "scopus_years_KZ_all.csv", "world_topic": "scopus_years_world_topic.csv", "world_all": "scopus_years_world_all.csv",
          "UZ_topic": "scopus_years_UZ.csv", "AZ_topic": "scopus_years_AZ.csv", "BY_topic": "scopus_years_BY.csv", "KG_topic": "scopus_years_KG.csv",
          "UZ_all": "scopus_years_UZ_all.csv", "AZ_all": "scopus_years_AZ_all.csv", "BY_all": "scopus_years_BY_all.csv", "KG_all": "scopus_years_KG_all.csv"}
EXPECTED_SUMS = {"KZ_all": 75667, "world_topic": 415133, "world_all": 70937062, "UZ_topic": 539, "AZ_topic": 278, "BY_topic": 129, "KG_topic": 51,
                 "UZ_all": 47902, "AZ_all": 36549, "BY_all": 49270, "KG_all": 8732}
COUNTRIES = ["KZ", "UZ", "AZ", "BY", "KG"]
NAMES = {"KZ": "Kazakhstan", "UZ": "Uzbekistan", "AZ": "Azerbaijan", "BY": "Belarus", "KG": "Kyrgyzstan"}
YEARS = list(range(2003, 2026))
WINDOWS = [(2003, 2016), (2017, 2021), (2022, 2025), (2003, 2025), (2017, 2025)]
PERIODS = [(2003, 2016), (2017, 2021), (2022, 2025)]
FORBIDDEN = {"PLAN_DPRG_MASTER_2026_09.md", "HANDOFF_DPRG_2026_09_11.md", "PLAN_SJAITU_META_ANALYSIS_PROFESSOR.md",
             "PROJECT_STRUCTURE_PROFESSOR.md", ".env", "PHASE_REGISTRY.csv"}
FORBIDDEN_DIRS = {"phase_F13_3", "phase_F13_2c"}

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ORCID = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b")


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


def load_years():
    """E1 as a stream: EID -> Year; only EID and Year are kept (R13), the rest of each row is dropped at once."""
    csv.field_size_limit(2 ** 31 - 1)
    out = {}
    with open(path(E1), "r", encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh)
        header = next(rd)
        ie, iy = header.index("EID"), header.index("Year")
        for row in rd:
            if not row:
                continue
            eid, year = row[ie].strip(), int(row[iy])
            del row
            assert eid and eid not in out, ("EID empty or repeated", eid)
            out[eid] = year
    return out


def load_series():
    out = {}
    for name, fn in SERIES.items():
        rows = read_csv(EXPORTS + "/" + fn)
        d = {int(r["year"]): int(r["documents"]) for r in rows}
        assert sorted(d) == YEARS and len(rows) == len(YEARS), (name, sorted(d))
        out[name] = d
    return out


def country_series():
    """country -> (topic by year, all output by year); KZ's topic is E1 counted by Year."""
    S = load_series()
    yrs = load_years()
    kz = {y: sum(1 for v in yrs.values() if v == y) for y in YEARS}
    out = {"KZ": (kz, S["KZ_all"])}
    for c in COUNTRIES[1:]:
        out[c] = (S[c + "_topic"], S[c + "_all"])
    return out, S
