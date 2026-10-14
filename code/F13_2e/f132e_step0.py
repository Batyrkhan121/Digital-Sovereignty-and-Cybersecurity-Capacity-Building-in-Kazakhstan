"""Phase F13.2e - step 0: brief stamp; digests of the inputs and of the reused programs (phase_F13_2d/programs, phase_F13_2b/programs and,
through them, phase_F13_2c/programs); snapshot of the brief's list: main.qmd, title_page_DPRG.qmd, references.bib, rebuilt/*,
outputs/tp_submission/*, the trees phase_F13_1, F13_2, F13_2b, F13_2c, F13_2d, F13_3, F13_4, F13_4b, F13_5, F13_6a, F13_6b and
author_exports_2026_10, plus CORRECTIONS.csv. PHASE_REGISTRY.csv and phase_F13_3b are not in it. --after: compare with step 0."""
import sys
sys.dont_write_bytecode = True

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132e_lib as L

NAMED = ["main.qmd", "title_page_DPRG.qmd", "references.bib", "outputs/dprg_revision_2026/CORRECTIONS.csv"]
NAMED_FOLDERS = ["SUBMISSION_TP_2026_09_21/rebuilt", "outputs/tp_submission"]
NAMED_TREES = [L.DPR + n for n in ("phase_F13_1", "phase_F13_2", "phase_F13_2b", "phase_F13_2c", "phase_F13_2d", "phase_F13_3", "phase_F13_4",
                                   "phase_F13_4b", "phase_F13_5", "phase_F13_6a", "phase_F13_6b", "author_exports_2026_10")]


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


def main():
    snap = snapshot()
    if "--after" in sys.argv:
        before = L.jload(L.OUT / "F13_2e_step0_snapshot.json")["files"]
        print("changed since step 0:", sorted(k for k in set(before) | set(snap) if before.get(k) != snap.get(k)))
        return 0
    brief = L.OUT / "F13_2e_brief.md"
    inputs = {rel: {"sha256": L.sha256_file(L.path(rel)), "bytes": L.path(rel).stat().st_size} for rel in L.INPUTS}
    progs = {}
    for folder in (L.F132D_PROGRAMS, L.F132B_PROGRAMS, L.D.F132C_PROGRAMS):
        for p in sorted(folder.iterdir(), key=lambda x: x.name):
            if p.suffix == ".py":
                progs[p.relative_to(L.ROOT).as_posix()] = L.sha256_file(p)
    L.jdump({"run_utc": L.now(), "brief_sha256": L.sha256_file(brief), "brief_bytes": brief.stat().st_size, "root": str(L.ROOT).replace("\\", "/"),
             "registry_path": "outputs/dprg_revision_2026/PHASE_REGISTRY.csv (not touched during the phase)", "inputs": inputs,
             "E1_accepted": inputs[L.E1]["sha256"] == L.E1_SHA, "programs_reused": progs}, L.OUT / "F13_2e_brief_stamp.json")
    L.jdump({"run_utc": L.now(), "files": snap}, L.OUT / "F13_2e_step0_snapshot.json")
    print("step 0:", len(snap), "files; E1 accepted:", inputs[L.E1]["sha256"] == L.E1_SHA, "; reused programs:", len(progs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
