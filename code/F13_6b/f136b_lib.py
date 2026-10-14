"""Phase F13.6b - shared helpers: paths, the input list, table access for the draft's placeholders, and the numeric-token extraction
reused unchanged from phase_F13_6a/programs/f136a_lib.py (its units() reads a file's lines through main_lines(), which is pointed at
the draft for the evidence index; the extraction rule itself is not rewritten). Local files only (no network module in programs/);
writes only inside the phase folder. phase_F13_2d, tools/ and PHASE_REGISTRY.csv are neither read nor written (path() refuses them);
phase_F13_3 is only part of the snapshot."""
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
DRAFT = OUT / "draft"
RUN_LOGS = OUT / "run_logs"
DPR = "outputs/dprg_revision_2026/"
MAIN = "main.qmd"
BIB = "references.bib"
README = DPR + "author_exports_2026_10/README_exports.txt"
E1 = DPR + "author_exports_2026_10/scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
P6A = DPR + "phase_F13_6a/"
PHASES = ["phase_F12_4", "phase_F13_1", "phase_F13_2", "phase_F13_2b", "phase_F13_2c", "phase_F13_4", "phase_F13_4b", "phase_F13_5"]
EXCLUDED_INPUTS = {DPR + "phase_F13_1/tables/T1d_references.csv", DPR + "phase_F13_1/tables/T3d_reference_counts.csv"}
FORBIDDEN = {"PLAN_DPRG_MASTER_2026_09.md", "HANDOFF_DPRG_2026_09_11.md", "PLAN_SJAITU_META_ANALYSIS_PROFESSOR.md",
             "PROJECT_STRUCTURE_PROFESSOR.md", ".env", "PHASE_REGISTRY.csv"}
FORBIDDEN_DIRS = {"phase_F13_2d", "tools", ".claude"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ORCID = re.compile(r"\b(?:0000|0009)-\d{4}-\d{4}-\d{3}[\dX]\b")
AUTHOR_COLS = {"authors", "author", "author full names", "author(s) id", "authors with affiliations", "correspondence address", "email", "orcid"}
MARK_2D = "[[F13.2d: update institution counts]]"
MARK_P2 = "[[REWRITE IN PART 2]]"
MARK_F133 = "[[PART 2: F13.3]]"
SECTIONS_2_3 = ("Methodology", "Results")


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


def input_files():
    files = [MAIN, BIB, README]
    for sub in ("tables",):
        d = path(P6A + sub)
        files += [P6A + sub + "/" + e.name for e in sorted(d.iterdir(), key=lambda x: x.name) if e.is_file() and e.name.startswith("N")]
    files += [P6A + "programs/" + e.name for e in sorted(path(P6A + "programs").iterdir(), key=lambda x: x.name) if e.suffix == ".py"]
    for ph in PHASES:
        base = DPR + ph + "/"
        for sub in ("tables", "figures"):
            d = path(base + sub)
            if d.exists():
                files += [base + sub + "/" + e.name for e in sorted(d.iterdir(), key=lambda x: x.name) if e.is_file() and e.suffix == ".csv"]
        files += [base + e.name for e in sorted(path(base).iterdir(), key=lambda x: x.name) if e.is_file() and e.name.endswith("_numbers.json")]
    return [f for f in files if f not in EXCLUDED_INPUTS]


_CACHE = {}


def read_csv(rel):
    if rel not in _CACHE:
        csv.field_size_limit(1 << 30)
        _CACHE[rel] = list(csv.DictReader(io.StringIO(path(rel).read_bytes().decode("utf-8-sig"), newline="")))
    return _CACHE[rel]


def read_json(rel):
    if rel not in _CACHE:
        _CACHE[rel] = json.loads(path(rel).read_bytes().decode("utf-8"))
    return _CACHE[rel]


def alias_path(alias):
    """'F13_4/T1c_loglinear_fit' -> tables CSV; 'F13_4/figures/Fig_x' -> figures CSV; 'F13_5/numbers' -> numbers JSON."""
    ph, rest = alias.split("/", 1)
    base = DPR + "phase_" + ph + "/"
    if rest == "numbers":
        return base + "F" + ph[1:] + "_numbers.json" if not ph.startswith("F") else base + ph + "_numbers.json"
    if rest.startswith("figures/"):
        return base + rest + ".csv"
    return base + "tables/" + rest + ".csv"


def parse_where(w):
    """'k=v & k2=v2' -> dict; '#3' -> row index 3 (1-based); '' -> {}."""
    w = w.strip()
    if not w:
        return {}
    if w.startswith("#"):
        return {"#": int(w[1:])}
    out = {}
    for part in w.split(" & "):
        k, v = part.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def rows_matching(alias, where):
    rows = read_csv(alias_path(alias))
    if "#" in where:
        return [rows[where["#"] - 1]]
    return [r for r in rows if all((r.get(k) or "").strip() == v for k, v in where.items())]


def cell(alias, where, col):
    hit = rows_matching(alias, parse_where(where) if isinstance(where, str) else where)
    assert len(hit) == 1, (alias, where, col, len(hit))
    assert col in hit[0], (alias, col, list(hit[0]))
    return hit[0][col]


def jvalue(alias, key):
    d = read_json(alias_path(alias))
    for k in key.split("."):
        d = d[k]
    return d


# ---------------------------------------------------------------- reuse of the F13.6a extraction program
def f136a():
    """The F13.6a library, imported from its own folder without writing bytecode there."""
    if "f136a" not in _CACHE:
        p = str(path(P6A + "programs"))
        if p not in sys.path:
            sys.path.insert(0, p)
        import f136a_lib
        _CACHE["f136a"] = f136a_lib
    return _CACHE["f136a"]


def tokens_of(lines):
    """Numeric tokens of a text given as lines, by the F13.6a rule: units() and tokens() of f136a_lib run with main_lines() pointed at
    these lines (the module's own function is restored afterwards)."""
    T = f136a()
    saved = T.main_lines
    try:
        T.main_lines = lambda: list(lines)
        toks = T.tokens()
        units = T.units()
    finally:
        T.main_lines = saved
    return toks, units


def norm_num(s):
    return f136a().norm_num(s)


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


def read_csv_out(p):
    return list(csv.DictReader(io.StringIO(Path(p).read_bytes().decode("utf-8"), newline="")))


def wrap(text, width=25):
    out = []
    for para in text.split("\n"):
        words = para.split()
        out += [" ".join(words[i:i + width]) for i in range(0, len(words), width)] or [""]
    return "\n".join(out)


def md_table(fields, rows):
    def c(v):
        return str(v).replace("|", "/").replace("\n", " ")
    out = ["| " + " | ".join(fields) + " |", "|" + "|".join(" --- " for _ in fields) + "|"]
    out += ["| " + " | ".join(c(r.get(k, "")) for k in fields) + " |" for r in rows]
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


def install_r17_guard():
    def hook(event, args):
        if event in {"os.remove", "os.rmdir", "os.rename", "shutil.rmtree", "shutil.move", "os.symlink", "os.link", "os.truncate"}:
            raise PermissionError(f"R17: {event} refused for {args[0] if args else ''}")
    sys.addaudithook(hook)
