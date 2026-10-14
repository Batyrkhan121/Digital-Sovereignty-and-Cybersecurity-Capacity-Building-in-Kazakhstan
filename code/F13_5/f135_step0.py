"""Phase F13.5 - step 0 (copied from F12.3c; changed: the stamp holds E1's digest against README_exports.txt, the digest of
F12.3c's thesaurus and E1's aggregate shape; the snapshot list is the brief's: main.qmd, title_page_DPRG.qmd, references.bib,
rebuilt/*, outputs/tp_submission/*, the trees phase_F12_3, phase_F12_3b, phase_F12_3c, phase_F13_1, author_exports_2026_10,
plus CORRECTIONS.csv. PHASE_REGISTRY.csv and phase_F13_2/ are neither read nor snapshotted (brief). With --after: compare with
step 0 (console only)."""
import sys
sys.dont_write_bytecode = True

import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f135_lib as L

NAMED = ["main.qmd", "title_page_DPRG.qmd", "references.bib", "outputs/dprg_revision_2026/CORRECTIONS.csv"]
NAMED_FOLDERS = ["SUBMISSION_TP_2026_09_21/rebuilt", "outputs/tp_submission"]
NAMED_TREES = ["outputs/dprg_revision_2026/phase_F12_3", "outputs/dprg_revision_2026/phase_F12_3b", "outputs/dprg_revision_2026/phase_F12_3c",
               "outputs/dprg_revision_2026/phase_F13_1", "outputs/dprg_revision_2026/author_exports_2026_10"]


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


def e1_shape():
    """Aggregates only: rows, EIDs, years, non-empty keyword cells, records with keywords after the split, separators."""
    recs = L.load_records()
    ys = [r["year"] for r in recs.values()]
    return {"rows": len(recs), "years": [min(ys), max(ys)],
            "author_cells_non_empty": sum(r["ak_cell"] for r in recs.values()),
            "index_cells_non_empty": sum(r["ik_cell"] for r in recs.values()),
            "author_records_with_keywords": sum(1 for r in recs.values() if any(L.norm_kw(k) for k in r["ak"])),
            "index_records_with_keywords": sum(1 for r in recs.values() if any(L.norm_kw(k) for k in r["ik"])),
            "semicolons_not_followed_by_space": sum(r["semicolon_without_space"] for r in recs.values()),
            "columns_kept": list(L.E1_COLS)}


def main():
    snap = snapshot()
    if "--after" in sys.argv:
        before = L.jload(L.OUT / "F13_5_step0_snapshot.json")["files"]
        print("changed since step 0:", sorted(k for k in set(before) | set(snap) if before.get(k) != snap.get(k)))
        return 0
    readme = L.path(L.E1_README).read_bytes().decode("utf-8")
    line = next(ln for ln in readme.splitlines() if Path(L.E1).name in ln and "sha256" in ln)
    readme_sha = re.search(r"sha256 ([0-9a-f]{64})", line).group(1)
    e1_sha = snap[L.E1]["sha256"]
    th3 = L.PREV_T / "thesaurus.csv"
    brief = L.OUT / "F13_5_brief.md"
    shape = e1_shape()
    L.jdump({"run_utc": L.now(), "brief_sha256": L.sha256_file(brief), "brief_bytes": brief.stat().st_size,
             "root": str(L.ROOT).replace("\\", "/"), "registry_path": "outputs/dprg_revision_2026/PHASE_REGISTRY.csv (not read)",
             "E1": L.E1, "E1_sha256": e1_sha, "E1_bytes": snap[L.E1]["bytes"], "E1_sha256_in_README": readme_sha,
             "E1_equal_README": e1_sha == readme_sha, "E1_shape": shape,
             "thesaurus_v3": "outputs/dprg_revision_2026/phase_F12_3c/tables/thesaurus.csv", "thesaurus_v3_sha256": L.sha256_file(th3),
             "thesaurus_v3_rows": len(L.read_csv_path(th3))},
            L.OUT / "F13_5_brief_stamp.json")
    L.jdump({"run_utc": L.now(), "files": snap}, L.OUT / "F13_5_step0_snapshot.json")
    print("step 0:", len(snap), "files; E1 equal to README:", e1_sha == readme_sha, "; shape:", shape)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
