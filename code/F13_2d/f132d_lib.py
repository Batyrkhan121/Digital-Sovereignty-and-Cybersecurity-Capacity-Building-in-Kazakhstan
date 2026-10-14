"""Phase F13.2d - shared helpers. The affiliation parsing is F13.2c's, imported read-only from phase_F13_2c/programs/f132c_lib.py
(aff_lines, parse_line, norm_kz, most_common_form, inst_type, year_of, period_of; the same normalisation and priority of parts); it is
not rewritten. E1 is read here by an own whitelist loader that keeps only EID, Year and Affiliations (R13: Authors with affiliations is
not needed). The surname set for gate G2 is read from the Authors column into memory only (surnames()). Local files only; writes only
inside the phase folder. phase_F13_6b and PHASE_REGISTRY.csv are refused by path()."""
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
F132C_PROGRAMS = ROOT / DPR / "phase_F13_2c" / "programs"
sys.path.insert(0, str(F132C_PROGRAMS))
import f132c_lib as C  # noqa: E402  (read-only reuse of F13.2c's parsing)

E1 = DPR + "author_exports_2026_10/scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
E1_SHA = "fe01023d23afe95df83d594fdfea2c3b488e52ffb8778def4067a2d795a991f3"
CT = DPR + "phase_F13_2c/tables/"
IN_THES = CT + "institutions_thesaurus_v2.csv"
IN_V2 = {"T3a": CT + "T3a_v2_kz_institutions.csv", "T3c": CT + "T3c_v2_concentration.csv", "T3d": CT + "T3d_v2_kz_institution_pairs.csv",
         "T2f": CT + "T2f_v2_collaboration_by_year.csv", "T2f2": CT + "T2f2_v2_collaboration_by_period.csv"}
IN_COUNTRIES = DPR + "phase_F13_2b/tables/scopus_country_names.csv"
INPUTS = [E1, IN_THES, IN_COUNTRIES] + list(IN_V2.values())
FORBIDDEN = {"PLAN_DPRG_MASTER_2026_09.md", "HANDOFF_DPRG_2026_09_11.md", "PLAN_SJAITU_META_ANALYSIS_PROFESSOR.md",
             "PROJECT_STRUCTURE_PROFESSOR.md", ".env", "PHASE_REGISTRY.csv"}
FORBIDDEN_DIRS = {"phase_F13_6b", ".claude"}
E1_KEEP = {"EID": "eid", "Year": "year", "Affiliations": "affiliations"}
AUTHOR_COLS = C.AUTHOR_COLS
KZ, COLLAB, PERIODS, YEARS = C.KZ, C.COLLAB, C.PERIODS, C.YEARS
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ORCID = re.compile(r"\b(?:0000|0009)-\d{4}-\d{4}-\d{3}[\dX]\b")

# the brief's stop-list of generic words (step 1); executor's additions are listed separately and printed in generic_tokens.csv
GENERIC_BRIEF = ["university", "univ", "state", "national", "research", "technical", "technological", "technology", "technologies",
                 "engineering", "institute", "academy", "named", "after", "name", "by", "on", "of", "the", "and", "in", "at", "for", "nao",
                 "njsc", "nc", "jsc", "llp", "nplc", "company", "corporation", "non", "profit", "limited", "joint", "stock", "kazakhstan",
                 "republic", "rk", "kazakh", "department", "faculty", "school", "laboratory", "center", "centre", "chair", "city", "regional"]
GENERIC_ADDED = {}


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


def countries():
    return {r["country_name"] for r in read_csv(IN_COUNTRIES)}


def load_e1():
    """Whitelist loader: EID, Year, Affiliations of each record; the rest of each row is dropped at once (R13)."""
    csv.field_size_limit(1 << 30)
    recs = []
    with open(path(E1), "r", encoding="utf-8-sig", newline="") as f:
        rd = csv.reader(f)
        header = next(rd)
        idx = {header.index(c): k for c, k in E1_KEEP.items()}
        for row in rd:
            recs.append({k: row[i] for i, k in idx.items()})
            row = None
    return len(header), recs


def surnames():
    """For gate G2 only: surname tokens (>= 4 letters) of the Authors column, minus words of E1's Affiliations and of the country
    list (those reach the outputs legitimately). Held in memory; never printed or written."""
    csv.field_size_limit(1 << 30)
    toks, aff_words = set(), set()
    with open(path(E1), "r", encoding="utf-8-sig", newline="") as f:
        rd = csv.reader(f)
        header = next(rd)
        ia, iaff = header.index("Authors"), header.index("Affiliations")
        for row in rd:
            for entry in row[ia].split(";"):
                s = re.sub(r"(?:\s+[A-ZЀ-Я][a-zа-я]{0,2}\.-?)+\s*$", "", entry.strip())
                toks |= {t for t in re.split(r"[\s,\-]+", s) if len(t) >= 4 and t.isalpha()}
            aff_words |= set(re.findall(r"[^\W\d_]+", row[iaff]))
            row = None
    for c in countries():
        aff_words |= set(re.findall(r"[^\W\d_]+", c))
    return sorted(toks - aff_words), len(toks), len(toks & aff_words)


def tokens(name):
    """Tokens of the normalised key (F13.2b's norm_kz), letters and digits only."""
    return re.findall(r"[^\W_]+", C.norm_kz(name))


def generic():
    return set(GENERIC_BRIEF) | set(GENERIC_ADDED)


def distinctive(name):
    g = generic()
    return [t for t in tokens(name) if t not in g]


def shape_counts(text):
    return {"e_mail_shaped": len(EMAIL.findall(text)), "orcid_shaped": len(ORCID.findall(text))}


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


def pct(n, d):
    return f"{100.0 * n / d:.1f}" if d else ""


def install_r17_guard():
    def hook(event, args):
        if event in {"os.remove", "os.rmdir", "os.rename", "shutil.rmtree", "shutil.move", "os.symlink", "os.link", "os.truncate"}:
            raise PermissionError(f"R17: {event} refused for {args[0] if args else ''}")
    sys.addaudithook(hook)
