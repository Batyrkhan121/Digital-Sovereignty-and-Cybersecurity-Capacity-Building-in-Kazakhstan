"""Phase F13.2b - step 0: brief stamp; E1 digest against README_exports.txt and the brief's prefix; digest of the second input
(phase_F13_1/tables/T2b_years.csv); snapshot of the named untouchables (named files, named folders one level deep, named trees).
phase_F13_2, phase_F13_5 and PHASE_REGISTRY.csv are left out (parallel sessions). With --after: compare with the step-0 snapshot
(console only)."""
import sys
sys.dont_write_bytecode = True

import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132b_lib as L

NAMED = ["main.qmd", "title_page_DPRG.qmd", "references.bib", "outputs/dprg_revision_2026/CORRECTIONS.csv"]
NAMED_FOLDERS = ["SUBMISSION_TP_2026_09_21/rebuilt", "outputs/tp_submission"]
NAMED_TREES = ["outputs/dprg_revision_2026/phase_F12_1", "outputs/dprg_revision_2026/phase_F12_3", "outputs/dprg_revision_2026/phase_F12_3b",
               "outputs/dprg_revision_2026/phase_F12_3c", "outputs/dprg_revision_2026/phase_F12_4", "outputs/dprg_revision_2026/phase_F13_1",
               "outputs/dprg_revision_2026/author_exports_2026_10"]


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
            if not d.exists():
                continue
            for e in sorted(d.iterdir(), key=lambda x: x.name):
                if e.is_symlink():
                    continue
                if e.is_dir():
                    stack.append(e)
                else:
                    files[e.relative_to(L.ROOT).as_posix()] = {"bytes": e.stat().st_size, "sha256": L.sha256_file(e)}
    return files


def main():
    L.install_r17_guard()
    snap = snapshot()
    if "--after" in sys.argv:
        before = json.loads((L.OUT / "F13_2b_step0_snapshot.json").read_bytes().decode("utf-8"))["files"]
        print("changed since step 0:", sorted(k for k in set(before) | set(snap) if before.get(k) != snap.get(k)))
        return 0
    e1 = snap[L.E1]["sha256"]
    readme = L.readme_e1_sha()
    brief = L.OUT / "F13_2b_brief.md"
    stamp = {"run_utc": L.now(), "brief_sha256": L.sha256_file(brief), "brief_bytes": brief.stat().st_size,
             "root": str(L.ROOT).replace("\\", "/"), "registry_location": str(L.ROOT).replace("\\", "/") + "/" + L.DPR + "PHASE_REGISTRY.csv",
             "inputs": {"E1": {"file": L.E1, "sha256": e1, "readme_sha256": readme, "equal_readme": e1 == readme,
                               "brief_prefix": L.E1_SHA_BRIEF_PREFIX, "equal_brief_prefix": e1.startswith(L.E1_SHA_BRIEF_PREFIX)},
                        "T2b_years": {"file": L.T2B, "sha256": snap[L.T2B]["sha256"]}},
             "snapshot_files": len(snap), "left_out": ["outputs/dprg_revision_2026/phase_F13_2", "outputs/dprg_revision_2026/phase_F13_5",
                                                       "outputs/dprg_revision_2026/PHASE_REGISTRY.csv"]}
    L.jdump(stamp, L.OUT / "F13_2b_brief_stamp.json")
    L.jdump({"run_utc": L.now(), "files": snap}, L.OUT / "F13_2b_step0_snapshot.json")
    print("step 0:", len(snap), "files; E1 equal to README:", e1 == readme, "; brief prefix:", e1.startswith(L.E1_SHA_BRIEF_PREFIX))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
