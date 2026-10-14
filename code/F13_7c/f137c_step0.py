"""Phase F13.7c - step 0: brief stamp (tools, input digests), the snapshot of the untouchables, and the one read of PHASE_REGISTRY.csv
(before step 1) through F13.7a's phase_log() (rows phase_F12_4 and phase_F13_*; kept here up to phase_F13_8). A rerun never reads the
registry again (the stamp keeps the read). --after: compare the snapshot (console only). main.qmd, references.bib, phase_F13_6d,
outputs/jcp_submission and PHASE_REGISTRY.csv are not in the snapshot (brief)."""
import sys
sys.dont_write_bytecode = True

import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f137c_lib as L

NAMED = ["title_page_DPRG.qmd", L.DPR + "CORRECTIONS.csv"]
NAMED_FOLDERS = ["SUBMISSION_TP_2026_09_21/rebuilt", "outputs/tp_submission", "outputs/tables"]
CLOSED = ["phase_F12_4", "phase_F13_1", "phase_F13_2", "phase_F13_2b", "phase_F13_2c", "phase_F13_2d", "phase_F13_2e", "phase_F13_3", "phase_F13_3b",
          "phase_F13_4", "phase_F13_4b", "phase_F13_5", "phase_F13_6a", "phase_F13_6b", "phase_F13_6c", "phase_F13_7a", "phase_F13_7b", "phase_F13_8"]
TREES = [L.DPR + p for p in CLOSED] + [L.DPR + "author_exports_2026_10"]


def snapshot():
    files = {}
    for rel in NAMED:
        p = L.ROOT / rel  # CORRECTIONS.csv is refused by path() for reading; here only hashed
        files[rel] = {"bytes": p.stat().st_size, "sha256": L.sha256_file(p)} if p.exists() else None
    for folder in NAMED_FOLDERS:
        for e in sorted((L.ROOT / folder).iterdir(), key=lambda x: x.name):
            if e.is_file() and not e.is_symlink():
                files[folder + "/" + e.name] = {"bytes": e.stat().st_size, "sha256": L.sha256_file(e)}
    for tree in TREES:
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


def input_files():
    p7a = L.DPR + "phase_F13_7a/"
    files = [p7a + "supplementary/" + e.name for e in sorted(L.path(p7a + "supplementary").iterdir(), key=lambda x: x.name) if e.is_file()]
    files += [p7a + "tables/X1_sheet_sources.csv", p7a + "tables/F1_figure_manifest.csv"]
    files += [p7a + "programs/" + e.name for e in sorted(L.path(p7a + "programs").iterdir(), key=lambda x: x.name) if e.suffix == ".py"]
    files.append(L.DRAFT)
    figs = L.figure_order()
    for name, src, _ in L.sheets_v2(figs):
        if not src.startswith("derived:"):
            files.append(src)
    files += [L.A.README_EXPORTS, L.A.MANIFEST, L.t("phase_F12_4", "T1_summary"), L.t("phase_F13_2e", "T3d_v31_kz_institution_pairs"),
              L.t("phase_F13_2", "T3e_top20_cited"), L.t("phase_F13_3b", "T2_top30_works"), L.t("phase_F13_3b", "T3c_top20_LCS"),
              L.t("phase_F13_3b", "T5b_cocitation_clusters")]
    for f in figs:
        files += [L.rel(f["tif"]), L.rel(f["png"])] + [L.rel(c) for c in f["csvs"]]
    files += [L.E1, L.t("phase_F13_2e", "T3a_v31_kz_institutions"), L.t("phase_F13_2b", "T3e_foreign_institutions"),
              L.t("phase_F13_2b", "scopus_country_names"), L.t("phase_F13_2", "T2a_sources"), L.t("phase_F13_2", "T2d_publishers")]
    return sorted(set(files))


def keep_phase(pid):
    if pid == "phase_F12_4":
        return True
    m = re.fullmatch(r"phase_F13_(\d+)[a-z]?(?:_.*)?", pid)
    return bool(m) and int(m.group(1)) <= 8


def main():
    L.install_r17_guard()
    snap = snapshot()
    if "--after" in sys.argv:
        before = L.jload(L.OUT / "F13_7c_step0_snapshot.json")["files"]
        print("changed since step 0:", sorted(k for k in set(before) | set(snap) if before.get(k) != snap.get(k)))
        return 0
    stamp_p = L.OUT / "F13_7c_brief_stamp.json"
    old = L.jload(stamp_p) if stamp_p.exists() else {}
    if "registry_one_read" in old:
        reg = old["registry_one_read"]  # the registry is read once only
    else:
        reg = L.S0A.phase_log()  # F13.7a's function: the one read; writes tables/phase_log_from_registry.csv
        rows = L.read_csv_path(L.TABLES / "phase_log_from_registry.csv")
        kept = [r for r in rows if keep_phase(r["phase_id"])]
        if len(kept) != len(rows):
            L.write_csv(L.TABLES / "phase_log_from_registry.csv", list(rows[0].keys()), kept)
        reg = {**reg, "rows_after_F13_8_dropped": len(rows) - len(kept), "rows_in_phase_log": len(kept), "phases": [r["phase_id"] for r in kept]}
    import openpyxl
    import PIL
    tools = {"python": sys.version.split()[0], "openpyxl": openpyxl.__version__, "pillow": PIL.__version__, "installed_in_this_phase": []}
    inputs = {rel: {"sha256": L.sha256_file(L.path(rel)), "bytes": L.path(rel).stat().st_size} for rel in input_files()}
    brief = L.OUT / "F13_7c_brief.md"
    L.jdump({"run_utc": L.now(), "brief_sha256": L.sha256_file(brief), "brief_bytes": brief.stat().st_size, "root": str(L.ROOT).replace("\\", "/"),
             "tools": tools, "inputs": inputs, "inputs_count": len(inputs), "registry_one_read": reg,
             "r13_check": "E1's Authors column is read in memory only (surname tokens), as in F13.6c; nothing from it is written",
             "left_out_of_snapshot": ["main.qmd", "references.bib", L.DPR + "PHASE_REGISTRY.csv", L.DPR + "phase_F13_6d", "outputs/jcp_submission",
                                      L.DPR + "phase_F13_7c (this phase)"]}, stamp_p)
    L.jdump({"run_utc": L.now(), "files": snap}, L.OUT / "F13_7c_step0_snapshot.json")
    print("step 0:", len(snap), "snapshot files;", len(inputs), "inputs;", tools, "; registry rows kept:", reg.get("rows_in_phase_log"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
