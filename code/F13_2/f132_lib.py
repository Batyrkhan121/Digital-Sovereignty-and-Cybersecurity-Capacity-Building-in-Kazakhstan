"""Phase F13.2 - shared helpers and the two whitelist parsers. Local files only (no network module in programs/); writes only
inside the phase folder. ROOT is found from this file's place (programs -> phase_F13_2 -> dprg_revision_2026 -> outputs -> ROOT).
phase_F12_3c and PHASE_REGISTRY.csv (a parallel session) are neither read nor written; the merged corpus M is not read.

E1 parser: csv.reader; from each row only the whitelisted columns are taken by index and the row list is dropped at once.
'Authors' is turned into an author count on the spot and not kept. Abstract, References, Correspondence Address, Author full
names, Author(s) ID, Affiliations and Authors with affiliations are never taken.
E2 parser: only the tags UT, PY, DT, TC are kept; every other line (EM, OI, RI, RP included) is skipped as it is read."""
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
DPR = "outputs/dprg_revision_2026/"
EXP = DPR + "author_exports_2026_10/"
E1 = EXP + "scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
E2 = EXP + "wos_full_TS_KZ_2003_2025_2026-10-13.txt"
README = EXP + "README_exports.txt"
PAIRS = DPR + "phase_F13_1/tables/T3a_pairs.csv"
F131_YEARS = DPR + "phase_F13_1/tables/T2b_years.csv"
F121 = {k: DPR + "phase_F12_1/tables/" + v for k, v in {
    "types": "T1a_doc_types.csv", "sources": "T1b_top20_sources.csv", "year_type": "T1c_year_by_type.csv",
    "cites": "T1d_citations_by_year.csv", "lang": "T1e_language_I2.csv", "oa": "T1e_open_access_I2.csv"}.items()}
I1 = DPR + "phase_E2/corpora_rule_e/E2_L1_scopus_september_study_2003_2025_rule_e.csv"
EXPECTED = {"E1": "fe01023d23afe95df83d594fdfea2c3b488e52ffb8778def4067a2d795a991f3",
            "E2": "413b0fa8ba8dd496072367601b7ca66bf0c7cac01d30553aa702b288dd402160",
            "I1": "83215abe7de87a647488e183c383ac788ac9d2078a88d6b8997c9f2f46d7697c"}
FORBIDDEN = {"PLAN_DPRG_MASTER_2026_09.md", "HANDOFF_DPRG_2026_09_11.md", "PLAN_SJAITU_META_ANALYSIS_PROFESSOR.md",
             "PROJECT_STRUCTURE_PROFESSOR.md", ".env", "PHASE_REGISTRY.csv", "merged_corpus_2026-10-13.csv"}
E1_KEEP = ["EID", "Title", "Year", "Source title", "Cited by", "DOI", "Document Type", "Publication Stage", "Open Access",
           "Language of Original Document", "Funding Details", "Sponsors", "Publisher", "ISSN", "ISBN", "Conference name"]
E1_COUNT_ONLY = "Authors"
E1_NEVER = {"Abstract", "References", "Correspondence Address", "Author full names", "Author(s) ID", "Affiliations",
            "Authors with affiliations", "Authors"}
WOS_KEEP = {"UT", "PY", "DT", "TC"}
NAME_COLS = {"Authors", "Author full names", "Author(s) ID", "Authors with affiliations", "Correspondence Address", "EM", "OI", "RI", "RP",
             "authors", "author_names", "first_author"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ORCID = re.compile(r"\b(?:0000|0009)-\d{4}-\d{4}-\d{3}[\dX]\b")
YEARS = list(range(2003, 2026))
PERIODS = [("2003-2016", 2003, 2016), ("2017-2021", 2017, 2021), ("2022-2025", 2022, 2025)]
CITE_DATE = "Scopus 'Cited by' as of 2026-10-13"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def path(rel):
    p = ROOT / rel
    assert p.name not in FORBIDDEN and "phase_F12_3c" not in p.parts, p
    return p


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(rel, columns=None):
    csv.field_size_limit(1 << 30)
    rd = csv.reader(io.StringIO(path(rel).read_bytes().decode("utf-8-sig"), newline=""))
    header = next(rd)
    idx = {c: header.index(c) for c in (columns or header)}
    return [{c: row[i] for c, i in idx.items()} for row in rd]


def parse_e1():
    """Whitelisted columns of E1 plus n_authors; returns (header as exported, records)."""
    csv.field_size_limit(1 << 30)
    rd = csv.reader(io.StringIO(path(E1).read_bytes().decode("utf-8-sig"), newline=""))
    header = next(rd)
    idx = {c: header.index(c) for c in E1_KEEP}
    ia = header.index(E1_COUNT_ONLY)
    recs = []
    for row in rd:
        r = {c: row[i] for c, i in idx.items()}
        a = row[ia].strip()
        r["n_authors"] = 0 if (not a or a.startswith("[No author")) else len([x for x in a.split(";") if x.strip()])
        r["authors_missing"] = int(not a or a.startswith("[No author"))
        recs.append(r)
        del row
    return header, recs


def parse_e2():
    """Only UT, PY, DT, TC of every WoS record; other lines are skipped unread beyond their two-letter tag."""
    text = path(E2).read_bytes().decode("utf-8-sig")
    recs, cur, tag = [], None, None
    for line in text.splitlines():
        if line.startswith("ER"):
            if cur is not None:
                recs.append(cur)
            cur, tag = None, None
            continue
        if line.startswith("   "):
            if tag in WOS_KEEP:
                cur[tag] += " " + line.strip()
            continue
        if len(line) < 3 or line[2] != " " or line.startswith(("FN ", "VR ")):
            tag = None
            continue
        tag = line[:2]
        if tag == "PT":
            cur = {}
        if tag in WOS_KEEP and cur is not None:
            cur[tag] = line[3:].strip()
    return recs


def year_of(s):
    try:
        return int(float(str(s).strip()))
    except ValueError:
        return None


def norm_name(s):
    return " ".join(re.sub(r"[^a-z0-9]", " ", (s or "").lower()).split())


def shape_counts(text):
    return {"e_mail_shaped": len(EMAIL.findall(text)), "orcid_shaped": len(ORCID.findall(text))}


def cut30(s):
    w = (s or "").split()
    return " ".join(w[:30])


def write_csv(p, fields, rows):
    assert not (set(fields) & NAME_COLS), fields
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
    text = f"## {title}\n\n" + (wrap(note) + "\n\n" if note else "") + md_table(fields, rows if md_rows is None else md_rows) + "\n"
    (TABLES / f"{name}.md").write_bytes(text.encode("utf-8"))
    return text


def jdump(obj, p):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_bytes(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8"))


def pct(n, d, k=1):
    return f"{100.0 * n / d:.{k}f}" if d else ""


def median(xs):
    xs = sorted(xs)
    if not xs:
        return ""
    m = len(xs) // 2
    v = xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2
    return int(v) if float(v).is_integer() else v


def fmt(x, k=2):
    return f"{x:.{k}f}" if isinstance(x, float) else x
