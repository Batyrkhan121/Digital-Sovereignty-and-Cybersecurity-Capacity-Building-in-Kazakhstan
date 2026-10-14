"""Phase F13.7a - step 0: brief stamp (tool versions, input digests), the snapshot of the brief's list, and the one read of
PHASE_REGISTRY.csv the brief allows (before step 1): rows phase_F12_4 and phase_F13_* -> tables/phase_log_from_registry.csv (phase_id,
status, created_utc, produced_numbers, superseded_by, first words of the note), the source of the workbook's Phase log sheet.
--after: compare the snapshot (console only)."""
import sys
sys.dont_write_bytecode = True

import csv
import io
import re
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f137a_lib as L

NAMED = ["main.qmd", "title_page_DPRG.qmd", "references.bib", L.DPR + "CORRECTIONS.csv"]
NAMED_FOLDERS = ["SUBMISSION_TP_2026_09_21/rebuilt", "outputs/tp_submission", "outputs/tables"]
NAMED_TREES = [L.DPR + n for n in ("phase_F12_4", "phase_F13_1", "phase_F13_2", "phase_F13_2b", "phase_F13_2c", "phase_F13_2d", "phase_F13_2e",
                                   "phase_F13_3", "phase_F13_4", "phase_F13_4b", "phase_F13_5", "phase_F13_6a", "phase_F13_6b", "author_exports_2026_10")]
INPUTS = [L.DRAFT, L.E1_INDEX, L.N1, L.N3, "main.qmd", "title_page_DPRG.qmd", "references.bib", L.README_EXPORTS, L.MANIFEST, L.LONG, L.T2F_V31]


def snapshot():
    files = {}
    for rel in NAMED:
        p = L.path(rel)
        files[rel] = {"bytes": p.stat().st_size, "sha256": L.sha256_file(p)} if p.exists() else None
    for folder in NAMED_FOLDERS:
        for e in sorted(L.path(folder).iterdir(), key=lambda x: x.name):
            if e.is_file() and not e.is_symlink():
                files[folder + "/" + e.name] = {"bytes": e.stat().st_size, "sha256": L.sha256_file(e)}
    for tree in NAMED_TREES:
        stack = [L.path(tree)]
        while stack:
            d = stack.pop()
            for e in sorted(d.iterdir(), key=lambda x: x.name):
                if e.is_symlink():
                    continue
                if e.is_dir():
                    stack.append(e)
                else:
                    files[e.relative_to(L.ROOT).as_posix()] = {"bytes": e.stat().st_size, "sha256": L.sha256_file(e)}
    return files


def version(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return (r.stdout or r.stderr).strip().splitlines()[0]
    except Exception as e:  # noqa: BLE001
        return f"not available ({type(e).__name__})"


def phase_log():
    raw, digest = L.registry_once()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline="")))
    keep = [r for r in rows if re.fullmatch(r"phase_F12_4|phase_F13_.*", r["phase_id"])]
    out = [{"phase_id": r["phase_id"], "status": r["status"], "created_utc": r["created_utc"], "produced_numbers": r["produced_numbers"],
            "superseded_by": r["superseded_by"], "note_first_words": L.words(r["note"], 27)} for r in keep]
    L.write_csv(L.TABLES / "phase_log_from_registry.csv", ["phase_id", "status", "created_utc", "produced_numbers", "superseded_by", "note_first_words"], out)
    return {"registry_rows": len(rows), "rows_kept": len(out), "registry_sha256_at_read": digest, "read_utc": L.now()}


def main():
    snap = snapshot()
    if "--after" in sys.argv:
        before = L.jload(L.OUT / "F13_7a_step0_snapshot.json")["files"]
        print("changed since step 0:", sorted(k for k in set(before) | set(snap) if before.get(k) != snap.get(k)))
        return 0
    import matplotlib
    import openpyxl
    import pandas
    import PIL
    tools = {"quarto": version(["quarto", "--version"]), "pandoc (Quarto's)": version(["quarto", "pandoc", "--version"]),
             "tectonic": version(["tectonic", "--version"]), "python": sys.version.split()[0], "pandas": pandas.__version__,
             "openpyxl": openpyxl.__version__, "pillow": PIL.__version__, "matplotlib": matplotlib.__version__, "installed_in_this_phase": []}
    inputs = {rel: {"sha256": L.sha256_file(L.path(rel)), "bytes": L.path(rel).stat().st_size} for rel in INPUTS}
    brief = L.OUT / "F13_7a_brief.md"
    reg = phase_log()
    L.jdump({"run_utc": L.now(), "brief_sha256": L.sha256_file(brief), "brief_bytes": brief.stat().st_size, "root": str(L.ROOT).replace("\\", "/"),
             "tools": tools, "inputs": inputs, "phase_tables": "digests of every table and figure file of the input phases are in "
             "F13_7a_step0_snapshot.json", "registry_one_read": reg}, L.OUT / "F13_7a_brief_stamp.json")
    L.jdump({"run_utc": L.now(), "files": snap}, L.OUT / "F13_7a_step0_snapshot.json")
    print("step 0:", len(snap), "files;", tools, "; registry:", {k: v for k, v in reg.items() if k != "registry_sha256_at_read"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
