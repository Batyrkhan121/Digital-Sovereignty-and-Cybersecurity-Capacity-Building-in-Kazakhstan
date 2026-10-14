"""Phase F12.4 - shared helpers. Local files only (no network module is imported anywhere in programs/); writes only inside
the phase folder. ROOT is found from this file's place (programs -> phase_F12_4 -> dprg_revision_2026 -> outputs -> ROOT).
Phase F12.3b (a parallel session) and PHASE_REGISTRY.csv are neither read nor written."""
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
H4Q = DPR + "refresh_2026_09/field_harmonised_H4Q_title_only_cryptography_corrected/"
S = H4Q + "scopus/scopus_raw_H4Q_title_only_cryptography_corrected_2026_09_through_2025.csv"
O = H4Q + "openalex/openalex_raw_H4Q_title_only_cryptography_corrected_2026_09_through_2025.csv"
META = {"scopus": (H4Q + "scopus/manifest.csv", H4Q + "scopus/run_metadata.json"),
        "openalex": (H4Q + "openalex/manifest.csv", H4Q + "openalex/run_metadata.json")}
I1 = DPR + "phase_E2/corpora_rule_e/E2_L1_scopus_september_study_2003_2025_rule_e.csv"
I3 = DPR + "phase_E2/corpora_rule_e/E2_L1_scopus_june_dedup_rule_e.csv"
I4 = "openalex_cybersec_kz_raw.csv"
F121 = ROOT / "outputs" / "dprg_revision_2026" / "phase_F12_1"
F121_TABLES = {"T1b": "outputs/dprg_revision_2026/phase_F12_1/tables/T1b_top20_sources.csv",
               "T3c": "outputs/dprg_revision_2026/phase_F12_1/tables/T3c_overlap.csv"}
FORBIDDEN = {"PLAN_DPRG_MASTER_2026_09.md", "HANDOFF_DPRG_2026_09_11.md", "PLAN_SJAITU_META_ANALYSIS_PROFESSOR.md",
             "PROJECT_STRUCTURE_PROFESSOR.md", ".env", "PHASE_REGISTRY.csv"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ORCID = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b")
NAME_COLS = {"authors", "author_ids", "first_author"}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def path(rel):
    p = ROOT / rel
    assert p.name not in FORBIDDEN and "phase_F12_3b" not in p.parts, p
    return p


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(rel):
    return list(csv.DictReader(io.StringIO(path(rel).read_bytes().decode("utf-8-sig"), newline="")))


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


def cut30(s):
    w = (s or "").split()
    return " ".join(w[:30]), int(len(w) > 30)


def shape_counts(text):
    """ORCID shape = dddd-dddd-dddd-dddX whose first block is 0000 or 0009 (the only ORCID iD ranges). Four-block strings
    with another first block (e.g. an ISSN-led DOI suffix such as 10.52123/1994-2370-...) are counted apart, as raw hits."""
    raw = ORCID.findall(text)
    return {"e_mail_shaped": len(EMAIL.findall(text)), "orcid_shaped": sum(1 for m in raw if m[:4] in ("0000", "0009"))}


def raw_four_block(text):
    return len(ORCID.findall(text))


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


def write_md(p, title, fields, rows, note=""):
    text = f"## {title}\n\n" + (wrap(note) + "\n\n" if note else "") + md_table(fields, rows) + "\n"
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_bytes(text.encode("utf-8"))
    return text


def jdump(obj, p):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_bytes(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8"))


def pct(n, d):
    return f"{100.0 * n / d:.1f}" if d else ""
