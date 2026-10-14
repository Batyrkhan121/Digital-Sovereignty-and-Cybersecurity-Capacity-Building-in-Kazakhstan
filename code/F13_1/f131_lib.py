"""Phase F13.1 - shared helpers and the two parsers. Local files only (no network module anywhere in programs/); writes only
inside the phase folder. ROOT is found from this file's place (programs -> phase_F13_1 -> dprg_revision_2026 -> outputs -> ROOT).
phase_F12_3c and PHASE_REGISTRY.csv (a parallel session) are neither read nor written.

Personal data: the parsers drop Scopus 'Correspondence Address' and WoS tags EM, OI, RI, RP the moment a record is read; no
other code sees them."""
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
DATA = OUT / "data"
RUN_LOGS = OUT / "run_logs"
DPR = "outputs/dprg_revision_2026/"
EXP = DPR + "author_exports_2026_10/"
E1 = EXP + "scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
E1B = EXP + "scopus_citation_abstract_TAK_KZ_2003_2025_2026-10-13.csv"
E2 = EXP + "wos_full_TS_KZ_2003_2025_2026-10-13.txt"
YMAN = EXP + "manifest_year_series.json"
README = EXP + "README_exports.txt"
I1 = DPR + "phase_E2/corpora_rule_e/E2_L1_scopus_september_study_2003_2025_rule_e.csv"
I3 = DPR + "phase_E2/corpora_rule_e/E2_L1_scopus_june_dedup_rule_e.csv"
EXPECTED = {"E1": "fe01023d23afe95df83d594fdfea2c3b488e52ffb8778def4067a2d795a991f3",
            "E1b": "c23f6de1ba4032936534733565a4f6cc4a21ac5fc968ef73d11329f8e8897b31",
            "E2": "413b0fa8ba8dd496072367601b7ca66bf0c7cac01d30553aa702b288dd402160",
            "I1": "83215abe7de87a647488e183c383ac788ac9d2078a88d6b8997c9f2f46d7697c"}
EXPECTED_PREFIX = {"I3": "4e8d77e5"}
FORBIDDEN = {"PLAN_DPRG_MASTER_2026_09.md", "HANDOFF_DPRG_2026_09_11.md", "PLAN_SJAITU_META_ANALYSIS_PROFESSOR.md",
             "PROJECT_STRUCTURE_PROFESSOR.md", ".env", "PHASE_REGISTRY.csv"}
SCOPUS_DROP = {"Correspondence Address"}
WOS_DROP = {"EM", "OI", "RI", "RP"}
EXCLUDED_NAMES = {"Correspondence Address", "EM", "OI", "RI", "RP", "correspondence_address", "email", "orcid", "researcher_id"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ORCID = re.compile(r"\b(?:0000|0009)-\d{4}-\d{4}-\d{3}[\dX]\b")
YEARS = list(range(2003, 2026))


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


def read_csv(rel):
    csv.field_size_limit(1 << 30)
    return list(csv.DictReader(io.StringIO(path(rel).read_bytes().decode("utf-8-sig"), newline="")))


def parse_scopus(rel):
    """Scopus CSV export: utf-8-sig, field size limit 1 GiB. Returns (columns as exported, records without the dropped columns)."""
    csv.field_size_limit(1 << 30)
    rd = csv.DictReader(io.StringIO(path(rel).read_bytes().decode("utf-8-sig"), newline=""))
    cols = list(rd.fieldnames or [])
    recs = []
    dropped_nonempty = {c: 0 for c in SCOPUS_DROP if c in cols}
    for r in rd:
        for c in SCOPUS_DROP:
            v = r.pop(c, None)
            if c in dropped_nonempty and (v or "").strip():
                dropped_nonempty[c] += 1
        recs.append(r)
    parse_scopus.dropped_nonempty = dropped_nonempty
    return cols, recs


def parse_wos(rel):
    """ISI plain-text export: header FN/VR, records from PT to ER, continuation lines start with three spaces. Returns
    (tag counts over all records including the dropped tags - counts only, records as {tag: [lines]} without them)."""
    text = path(rel).read_bytes().decode("utf-8-sig")
    recs, cur, tag = [], None, None
    seen = {}
    for line in text.splitlines():
        if line.startswith("FN ") or line.startswith("VR ") or line.strip() == "EF" or not line.strip():
            continue
        if line.startswith("ER"):
            if cur is not None:
                recs.append(cur)
            cur, tag = None, None
            continue
        if line.startswith("   ") and tag is not None:
            if tag not in WOS_DROP:
                cur[tag].append(line[3:])
            continue
        t, rest = line[:2], line[3:]
        if cur is None:
            cur = {}
        tag = t
        seen[t] = seen.get(t, 0) + 1
        if t not in WOS_DROP:
            cur.setdefault(t, []).append(rest)
    return seen, recs


def wos_val(rec, tag, sep=" "):
    return sep.join(rec.get(tag, [])).strip()


def norm_doi(s):
    s = (s or "").strip().lower()
    for p in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:"):
        if s.startswith(p):
            s = s[len(p):]
    return s.strip()


def norm_title(s):
    return " ".join(re.sub(r"[^a-z0-9]", " ", (s or "").lower()).split())


def year_of(s):
    try:
        return int(float(str(s).strip()))
    except ValueError:
        return None


def shape_counts(text):
    return {"e_mail_shaped": len(EMAIL.findall(text)), "orcid_shaped": len(ORCID.findall(text))}


def write_csv(p, fields, rows):
    assert not (set(fields) & EXCLUDED_NAMES), fields
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


def table(name, title, fields, rows, note=""):
    write_csv(TABLES / f"{name}.csv", fields, rows)
    text = f"## {title}\n\n" + (wrap(note) + "\n\n" if note else "") + md_table(fields, rows) + "\n"
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
