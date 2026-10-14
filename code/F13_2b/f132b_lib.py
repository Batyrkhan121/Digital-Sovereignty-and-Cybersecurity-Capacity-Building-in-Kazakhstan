"""Phase F13.2b - shared helpers, the whitelist parser of E1 and the affiliation rules. Local files only (no network module anywhere
in programs/); writes only inside the phase folder. ROOT is found from this file's place (programs -> phase_F13_2b ->
dprg_revision_2026 -> outputs -> ROOT). phase_F13_2, phase_F13_5 and PHASE_REGISTRY.csv (parallel sessions) are neither read nor
written: path() refuses them.

Personal data (R13): from E1 only EID, Year, Document Type, Source title and Affiliations are kept, and Authors is turned into a
count the moment a row is read. Correspondence Address, Authors with affiliations, Author full names, Author(s) ID, Abstract and
References are never taken from a row (the CSV reader scans each row; only the whitelisted indexes leave the parser)."""
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
FIGURES = OUT / "figures"
RUN_LOGS = OUT / "run_logs"
DPR = "outputs/dprg_revision_2026/"
EXP = DPR + "author_exports_2026_10/"
E1 = EXP + "scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
README = EXP + "README_exports.txt"
T2B = DPR + "phase_F13_1/tables/T2b_years.csv"
E1_SHA_BRIEF_PREFIX = "fe01023d23afe95d"
FORBIDDEN = {"PLAN_DPRG_MASTER_2026_09.md", "HANDOFF_DPRG_2026_09_11.md", "PLAN_SJAITU_META_ANALYSIS_PROFESSOR.md",
             "PROJECT_STRUCTURE_PROFESSOR.md", ".env", "PHASE_REGISTRY.csv"}
FORBIDDEN_DIRS = {"phase_F13_2", "phase_F13_5", ".claude"}

E1_KEEP = {"EID": "eid", "Year": "year", "Document Type": "doc_type", "Source title": "source_title", "Affiliations": "affiliations"}
E1_COUNT = "Authors"
E1_NEVER = {"Correspondence Address", "Authors with affiliations", "Author full names", "Author(s) ID", "Abstract", "References"}
AUTHOR_COLS = {"authors", "author", "author full names", "author(s) id", "authors with affiliations", "correspondence address",
               "author_names", "author_ids", "email", "orcid"}

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ORCID = re.compile(r"\b(?:0000|0009)-\d{4}-\d{4}-\d{3}[\dX]\b")
SCOPUS_AUTHOR_ID = re.compile(r"(?<![0-9A-Za-z-])\d{10,11}(?![0-9A-Za-z-])")
NAME_INITIALS = re.compile(r"\b[A-Z][a-z'’-]+, (?:[A-Z]\.){1,3}(?=[\s;,]|$)")
YEARS = list(range(2003, 2026))
PERIODS = [("2003-2016", 2003, 2016), ("2017-2021", 2017, 2021), ("2022-2025", 2022, 2025)]
TYPE_MAP = {"article": "article", "review": "review", "conference paper": "conference paper", "book chapter": "book chapter",
            "book": "book", "retracted": "retracted"}
TYPES = ["article", "conference paper", "book chapter", "review", "retracted", "book"]
COLLAB = ["single institution", "domestic multi-institution", "international"]

# Step 1 - the institution is the first part (in line order) that holds a keyword of the earliest level; the last part is the country,
# the one before it the city; both are left out of the candidates (a line of two parts keeps its first part as the only candidate).
LEVELS = [
    ("L1 university", ["university", "универс"]),
    ("L2 institute / academy / college", ["institute", "academy", "college"]),
    ("L3 centre / center / laboratory", ["centre", "center", "laboratory"]),
    ("L4 company", ["company", "llp", "jsc", "ltd", "corporation"]),
    ("L5 government body", ["ministry", "agency", "committee", "department of"]),
    ("L6 hospital / clinic", ["hospital", "clinic"]),
]
SHORT_WORDS = {"llp", "jsc", "ltd"}  # matched as whole words; every other keyword as a substring
# 'department of' is a government body (not a university department) only when the same part names a state level:
STATE_WORDS = ["republic", "kazakhstan", "city", "region", "regional", "police", "state", "government", "akimat", "national security",
               "internal affairs", "defence", "defense", "emergency"]
# T3b: a canonical name that opens like an academic unit (no parent institution named) is typed 'other'
UNIT_START = re.compile(r"^(the )?(department|faculty|school of|higher school of|chair|division|ece department)\b", re.I)

# T3b - the type of an institution, from its canonical name (first matching type in this order)
INST_TYPES = [
    ("university", ["university", "универс"]),
    ("school or college", ["college", "school", "lyceum", "gymnasium"]),
    ("research institute", ["institute", "academy", "centre", "center", "laboratory", "observatory"]),
    ("company", ["company", "llp", "jsc", "ltd", "corporation", "inc", "bank", "holding"]),
    ("government body", ["ministry", "agency", "committee", "department of", "akimat", "government"]),
]
TYPE_SHORT = {"llp", "jsc", "ltd", "inc"}
INST_TYPE_ORDER = [t for t, _ in INST_TYPES] + ["other"]

# Country and territory names as Scopus writes them in the last part of an affiliation string (built for this phase).
SCOPUS_COUNTRIES = sorted({
    "Afghanistan", "Aland Islands", "Albania", "Algeria", "American Samoa", "Andorra", "Angola", "Anguilla", "Antarctica",
    "Antigua and Barbuda", "Argentina", "Armenia", "Aruba", "Australia", "Austria", "Azerbaijan", "Bahamas", "Bahrain", "Bangladesh",
    "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bermuda", "Bhutan", "Bolivia", "Bonaire, Sint Eustatius and Saba",
    "Bosnia and Herzegovina", "Botswana", "Brazil", "British Virgin Islands", "Brunei Darussalam", "Bulgaria", "Burkina Faso",
    "Burundi", "Cambodia", "Cameroon", "Canada", "Cape Verde", "Cayman Islands", "Central African Republic", "Chad", "Chile", "China",
    "Colombia", "Comoros", "Congo", "Cook Islands", "Costa Rica", "Cote d'Ivoire", "Côte d'Ivoire", "Croatia", "Cuba", "Curacao",
    "Cyprus", "Czech Republic", "Democratic Republic Congo", "Denmark", "Djibouti", "Dominica", "Dominican Republic", "Ecuador",
    "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini", "Ethiopia", "Falkland Islands (Malvinas)",
    "Faroe Islands", "Fiji", "Finland", "France", "French Guiana", "French Polynesia", "Gabon", "Gambia", "Georgia", "Germany",
    "Ghana", "Gibraltar", "Greece", "Greenland", "Grenada", "Guadeloupe", "Guam", "Guatemala", "Guernsey", "Guinea", "Guinea-Bissau",
    "Guyana", "Haiti", "Holy See (Vatican City State)", "Honduras", "Hong Kong", "Hungary", "Iceland", "India", "Indonesia", "Iran",
    "Iraq", "Ireland", "Isle of Man", "Israel", "Italy", "Jamaica", "Japan", "Jersey", "Jordan", "Kazakhstan", "Kenya", "Kiribati",
    "Kosovo", "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libyan Arab Jamahiriya", "Libya",
    "Liechtenstein", "Lithuania", "Luxembourg", "Macao", "Macedonia", "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta",
    "Marshall Islands", "Martinique", "Mauritania", "Mauritius", "Mayotte", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia",
    "Montenegro", "Montserrat", "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru", "Nepal", "Netherlands", "Netherlands Antilles",
    "New Caledonia", "New Zealand", "Nicaragua", "Niger", "Nigeria", "Niue", "Norfolk Island", "North Korea", "North Macedonia",
    "Northern Mariana Islands", "Norway", "Oman", "Pakistan", "Palau", "Palestine", "Panama", "Papua New Guinea", "Paraguay", "Peru",
    "Philippines", "Pitcairn", "Poland", "Portugal", "Puerto Rico", "Qatar", "Reunion", "Romania", "Russian Federation", "Rwanda",
    "Saint Barthelemy", "Saint Helena", "Saint Kitts and Nevis", "Saint Lucia", "Saint Martin", "Saint Pierre and Miquelon",
    "Saint Vincent and the Grenadines", "Samoa", "San Marino", "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia",
    "Serbia and Montenegro", "Seychelles", "Sierra Leone", "Singapore", "Sint Maarten", "Slovakia", "Slovenia", "Solomon Islands",
    "Somalia", "South Africa", "South Georgia and the South Sandwich Islands", "South Korea", "South Sudan", "Spain", "Sri Lanka",
    "Sudan", "Suriname", "Svalbard and Jan Mayen", "Swaziland", "Sweden", "Switzerland", "Syrian Arab Republic", "Taiwan",
    "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tokelau", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey",
    "Türkiye", "Turkmenistan", "Turks and Caicos Islands", "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom",
    "United States", "United States Minor Outlying Islands", "Uruguay", "Uzbekistan", "Vanuatu", "Venezuela", "Viet Nam",
    "Virgin Islands (U.S.)", "Wallis and Futuna", "Western Sahara", "Yemen", "Yugoslavia", "Zambia", "Zimbabwe",
})
COUNTRY_SET = set(SCOPUS_COUNTRIES)
KZ = "Kazakhstan"


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


def readme_e1_sha():
    """The sha256 that README_exports.txt gives for E1 (the line that names the E1 file and carries 'sha256 <64 hex>')."""
    name = E1.rsplit("/", 1)[1]
    for line in path(README).read_bytes().decode("utf-8").splitlines():
        if line.strip().startswith("- " + name):
            m = re.search(r"sha256 ([0-9a-f]{64})", line)
            if m:
                return m.group(1)
    return None


def n_authors(cell):
    a = (cell or "").strip()
    if not a or a.startswith("[No author"):
        return 0
    return len([x for x in a.split(";") if x.strip()])


def parse_e1():
    """Whitelist parser: returns (number of columns, records). A record holds eid, year, doc_type, source_title, affiliations and
    n_authors only; nothing else of a row survives the loop."""
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


def year_of(s):
    try:
        return int(float(str(s).strip()))
    except ValueError:
        return None


def htype(s):
    return TYPE_MAP.get((s or "").strip().lower(), "other")


def period_of(y):
    for name, a, b in PERIODS:
        if y is not None and a <= y <= b:
            return name
    return ""


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
    """Returns (institution part, level label, unresolved flag)."""
    cands = parts[:-2] if len(parts) >= 3 else parts[:-1]
    for label, words in LEVELS:
        for p in cands:
            if _has(p, words, SHORT_WORDS):
                return p, label, False
    return (parts[0] if parts else ""), "unresolved", True


def parse_line(line):
    parts = parts_of(line)
    inst, level, unres = institution_of(parts)
    return {"country_part": parts[-1] if parts else "", "city_part": parts[-2] if len(parts) >= 2 else "", "institution": inst,
            "level": level, "unresolved": unres, "n_parts": len(parts), "first_part": parts[0] if parts else ""}


DASHES = "-‐‑‒–—"


def norm_kz(s):
    """Step-3 normalisation: lowercase; single-letter initials with a period removed; hyphens (and dashes) and periods to spaces;
    the words 'named after', 'after', 'the' removed; spaces collapsed."""
    s = (s or "").lower()
    s = re.sub(r"(?<![^\W\d_])[^\W\d_]\.", " ", s)
    for ch in DASHES + ".":
        s = s.replace(ch, " ")
    s = re.sub(r"\bnamed after\b", " ", s)
    s = re.sub(r"\bafter\b", " ", s)
    s = re.sub(r"\bthe\b", " ", s)
    return " ".join(s.split())


def norm_foreign(s):
    """T3e normalisation of foreign institutions: lowercase, every character that is not a letter, digit or space to a space,
    spaces collapsed (no thesaurus)."""
    s = (s or "").lower()
    s = re.sub(r"[^\w\s]|_", " ", s)
    return " ".join(s.split())


def inst_type(name):
    if UNIT_START.search(name or "") and not _has(name, ["university", "универс", "institute", "academy"], set()):
        return "other"
    for t, words in INST_TYPES:
        if _has(name, words, TYPE_SHORT):
            return t
    return "other"


def shape_counts(text):
    return {"e_mail_shaped": len(EMAIL.findall(text)), "orcid_shaped": len(ORCID.findall(text)),
            "scopus_author_id_shaped": len(SCOPUS_AUTHOR_ID.findall(text)), "surname_initials_shaped": len(NAME_INITIALS.findall(text))}


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


def read_csv_out(p):
    return list(csv.DictReader(io.StringIO(Path(p).read_bytes().decode("utf-8"), newline="")))


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
    """CSV with every row; the .md copy (used in the report) with md_rows rows if given."""
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
    return int(v) if float(v).is_integer() else v


def mean(xs):
    return f"{sum(xs) / len(xs):.2f}" if xs else ""


def top(counter, k=None):
    items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
    return items if k is None else items[:k]


def most_common_form(forms):
    """The most frequent raw spelling (ties: the first in sorted order)."""
    c = Counter(forms)
    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


_R17_ALLOWED = set()


def install_r17_guard():
    """R17: no program of this phase deletes, moves or links anything (it never needs to); an audit hook refuses it."""
    def hook(event, args):
        if event in {"os.remove", "os.rmdir", "os.rename", "shutil.rmtree", "shutil.move", "os.symlink", "os.link", "os.truncate"}:
            target = str(args[0]) if args else ""
            if target not in _R17_ALLOWED:
                raise PermissionError(f"R17: {event} refused for {target}")
    sys.addaudithook(hook)
