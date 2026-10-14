"""Phase F13.2c - shared helpers, the whitelist parser of E1, the author-affiliation parser and the F13.2b affiliation rules (copied
unchanged from phase_F13_2b/programs/f132b_lib.py, so that institutions and countries are read exactly as there). Local files only
(no network module in programs/); writes only inside the phase folder. phase_F13_3, phase_F13_4b, phase_F13_6b and
PHASE_REGISTRY.csv are neither read nor written: path() refuses them.

Personal data (R13): from E1 only EID, Year, Affiliations and Authors with affiliations are kept; Authors becomes a count at once.
Author names live only in memory, to tie addresses to an author inside one record; no name leaves this module's callers except as
counts. Correspondence Address, Abstract, References, Author full names and Author(s) ID are never taken from a row."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import csv
import hashlib
import io
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
ROOT = OUT.parents[2]
TABLES = OUT / "tables"
RUN_LOGS = OUT / "run_logs"
DPR = "outputs/dprg_revision_2026/"
E1 = DPR + "author_exports_2026_10/scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
E1_SHA = "fe01023d23afe95df83d594fdfea2c3b488e52ffb8778def4067a2d795a991f3"  # accepted in F13.1 (Decision 40), frame by Decision 41
B = DPR + "phase_F13_2b/tables/"
IN_COUNTRIES = B + "scopus_country_names.csv"
IN_THES = B + "institutions_thesaurus.csv"
IN_T2C = B + "T2c_international_share.csv"
IN_DELTA = {"T3a": B + "T3a_kz_institutions.csv", "T3c": B + "T3c_concentration.csv", "T3d": B + "T3d_kz_institution_pairs.csv",
            "T2f": B + "T2f_collaboration_by_year.csv", "T2f2": B + "T2f2_collaboration_by_period.csv"}
INPUTS = [E1, IN_COUNTRIES, IN_THES, IN_T2C] + list(IN_DELTA.values())
FORBIDDEN = {"PLAN_DPRG_MASTER_2026_09.md", "HANDOFF_DPRG_2026_09_11.md", "PLAN_SJAITU_META_ANALYSIS_PROFESSOR.md",
             "PROJECT_STRUCTURE_PROFESSOR.md", ".env", "PHASE_REGISTRY.csv"}
FORBIDDEN_DIRS = {"phase_F13_3", "phase_F13_4b", "phase_F13_6b", ".claude"}

E1_KEEP = {"EID": "eid", "Year": "year", "Affiliations": "affiliations", "Authors with affiliations": "awa"}
E1_COUNT = "Authors"
E1_NEVER = {"Correspondence Address", "Abstract", "References", "Author full names", "Author(s) ID"}
AUTHOR_COLS = {"authors", "author", "author full names", "author(s) id", "authors with affiliations", "correspondence address",
               "author_names", "author_ids", "email", "orcid", "name", "surname"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ORCID = re.compile(r"\b(?:0000|0009)-\d{4}-\d{4}-\d{3}[\dX]\b")
YEARS = list(range(2003, 2026))
PERIODS = [("2003-2016", 2003, 2016), ("2017-2021", 2017, 2021), ("2022-2025", 2022, 2025)]
COLLAB = ["single institution", "domestic multi-institution", "international"]
KZ = "Kazakhstan"
INITIALS = re.compile(r"^(?:[A-ZЀ-Я][a-zа-я]{0,2}\.?[- ]?)+$")

# ------------------------------------------------ F13.2b rules (copied unchanged)
LEVELS = [
    ("L1 university", ["university", "универс"]),
    ("L2 institute / academy / college", ["institute", "academy", "college"]),
    ("L3 centre / center / laboratory", ["centre", "center", "laboratory"]),
    ("L4 company", ["company", "llp", "jsc", "ltd", "corporation"]),
    ("L5 government body", ["ministry", "agency", "committee", "department of"]),
    ("L6 hospital / clinic", ["hospital", "clinic"]),
]
SHORT_WORDS = {"llp", "jsc", "ltd"}
STATE_WORDS = ["republic", "kazakhstan", "city", "region", "regional", "police", "state", "government", "akimat", "national security",
               "internal affairs", "defence", "defense", "emergency"]
DASHES = "-‐‑‒–—"
UNIT_START = re.compile(r"^(the )?(department|faculty|school of|higher school of|chair|division|ece department)\b", re.I)
INST_TYPES = [
    ("university", ["university", "универс"]),
    ("school or college", ["college", "school", "lyceum", "gymnasium"]),
    ("research institute", ["institute", "academy", "centre", "center", "laboratory", "observatory"]),
    ("company", ["company", "llp", "jsc", "ltd", "corporation", "inc", "bank", "holding"]),
    ("government body", ["ministry", "agency", "committee", "department of", "akimat", "government"]),
]
TYPE_SHORT = {"llp", "jsc", "ltd", "inc"}


def inst_type(name):
    if UNIT_START.search(name or "") and not _has(name, ["university", "универс", "institute", "academy"], set()):
        return "other"
    for t, words in INST_TYPES:
        if _has(name, words, TYPE_SHORT):
            return t
    return "other"


def aff_lines(cell):
    return [x.strip() for x in (cell or "").split("; ") if x.strip()]


def parts_of(line):
    return [p.strip() for p in line.split(", ") if p.strip()]


def _state(low):
    return any(re.search(r"\b" + re.escape(w) + r"\b", low) for w in STATE_WORDS)


def _has(text, words, short):
    low = text.lower()
    for w in words:
        if w in short:
            if re.search(r"\b" + re.escape(w) + r"\b", low):
                return w
        elif w == "department of":
            if w in low and _state(low):
                return w
        elif w in low:
            return w
    return None


def institution_of(parts):
    cands = parts[:-2] if len(parts) >= 3 else parts[:-1]
    for label, words in LEVELS:
        for p in cands:
            if _has(p, words, SHORT_WORDS):
                return p, label, False
    return (parts[0] if parts else ""), "unresolved", True


def parse_line(line):
    parts = parts_of(line)
    inst, level, unres = institution_of(parts)
    return {"country_part": parts[-1] if parts else "", "institution": inst, "level": level, "unresolved": unres}


def norm_kz(s):
    s = (s or "").lower()
    s = re.sub(r"(?<![^\W\d_])[^\W\d_]\.", " ", s)
    for ch in DASHES + ".":
        s = s.replace(ch, " ")
    s = re.sub(r"\bnamed after\b", " ", s)
    s = re.sub(r"\bafter\b", " ", s)
    s = re.sub(r"\bthe\b", " ", s)
    return " ".join(s.split())


def most_common_form(forms):
    c = Counter(forms)
    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def n_authors(cell):
    a = (cell or "").strip()
    if not a or a.startswith("[No author"):
        return 0
    return len([x for x in a.split(";") if x.strip()])


def year_of(s):
    try:
        return int(float(str(s).strip()))
    except ValueError:
        return None


def period_of(y):
    for name, a, b in PERIODS:
        if y is not None and a <= y <= b:
            return name
    return ""


# ------------------------------------------------ helpers
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


def read_csv_out(p):
    return list(csv.DictReader(io.StringIO(Path(p).read_bytes().decode("utf-8"), newline="")))


def countries():
    return {r["country_name"] for r in read_csv(IN_COUNTRIES)}


def parse_e1():
    """Whitelist parser: (number of columns, records). A record holds eid, year, affiliations, awa (Authors with affiliations, in
    memory only) and n_authors."""
    csv.field_size_limit(1 << 30)
    recs = []
    with open(path(E1), "r", encoding="utf-8-sig", newline="") as f:
        rd = csv.reader(f)
        header = next(rd)
        idx = {header.index(c): k for c, k in E1_KEEP.items()}
        ai = header.index(E1_COUNT)
        assert not ({header[i] for i in idx} | {header[ai]}) & E1_NEVER
        for row in rd:
            r = {k: row[i] for i, k in idx.items()}
            r["n_authors"] = n_authors(row[ai])
            recs.append(r)
            row = None
    return len(header), recs


def _decompose(s, lines):
    """A sequence of the record's Affiliations lines that, joined by ', ', gives s exactly (longest lines tried first); None if none."""
    if s == "":
        return []
    for ln in lines:
        if s == ln:
            return [ln]
        if s.startswith(ln + ", "):
            rest = _decompose(s[len(ln) + 2:], lines)
            if rest is not None:
                return [ln] + rest
    return None


def author_entries(rec):
    """Entries of Authors with affiliations ('; '-separated) as (name, [affiliation lines], how). In E1 an entry is the author's name
    (the first ', '-part, 'Surname I.') followed by all of that author's affiliations, joined by ', '; the rest of the entry is
    decomposed into lines of the record's own Affiliations column. If it does not decompose, the countries are read from the parts of
    the rest that are country names ('fallback'); an entry of one part has no affiliation."""
    lines = sorted(set(aff_lines(rec["affiliations"])), key=len, reverse=True)
    out = []
    for e in [x.strip() for x in (rec["awa"] or "").split("; ") if x.strip()]:
        name, _, rest = e.partition(", ")
        if not rest:
            out.append((name, [], "no affiliation"))
            continue
        dec = _decompose(rest, lines)
        if dec is not None:
            out.append((name, dec, "one Affiliations line" if len(dec) == 1 else "two or more Affiliations lines"))
        else:
            out.append((name, [rest], "fallback: countries from the parts"))
    return out


def entry_countries(affs, how, cset):
    if how.startswith("fallback"):
        return {p for p in parts_of(affs[0]) if p in cset}
    return {parts_of(a)[-1] for a in affs if parts_of(a) and parts_of(a)[-1] in cset}


def authors(rec, cset):
    """Author positions of a record: one per entry, in order (in E1 an author with several affiliations is one entry; two entries
    with the same name are two authors - the Authors column counts them both). Each author: position, name (memory only),
    affiliation lines, how, set of countries."""
    out = []
    for name, affs, how in author_entries(rec):
        out.append({"pos": len(out) + 1, "name": name, "affs": list(affs), "how": how, "countries": entry_countries(affs, how, cset)})
    return out


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


def pct(n, d):
    return f"{100.0 * n / d:.1f}" if d else ""


def median(xs):
    xs = sorted(xs)
    if not xs:
        return ""
    m = len(xs) // 2
    v = xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2
    return round(v, 3)


def top(counter, k=None):
    items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    return items if k is None else items[:k]


def install_r17_guard():
    def hook(event, args):
        if event in {"os.remove", "os.rmdir", "os.rename", "shutil.rmtree", "shutil.move", "os.symlink", "os.link", "os.truncate"}:
            raise PermissionError(f"R17: {event} refused for {args[0] if args else ''}")
    sys.addaudithook(hook)
