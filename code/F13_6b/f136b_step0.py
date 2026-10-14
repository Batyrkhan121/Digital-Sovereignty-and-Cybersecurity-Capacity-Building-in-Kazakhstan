"""Phase F13.6b - step 0: brief stamp; digests of the inputs; the one check of phase_F13_2d/run_logs/final.json (the brief's rule for
institution numbers; the decision is stored in the stamp and never re-checked: a later run reuses it); snapshot of the named
untouchables. phase_F13_2d, tools/ and PHASE_REGISTRY.csv are left out. With --after: compare with the step-0 snapshot."""
import sys
sys.dont_write_bytecode = True

import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f136b_lib as L

NAMED = ["main.qmd", "title_page_DPRG.qmd", "references.bib", L.DPR + "CORRECTIONS.csv"]
NAMED_FOLDERS = ["SUBMISSION_TP_2026_09_21/rebuilt", "outputs/tp_submission", "outputs/tables"]
NAMED_TREES = [L.DPR + p for p in ("phase_F12_4", "phase_F13_1", "phase_F13_2", "phase_F13_2b", "phase_F13_2c", "phase_F13_3", "phase_F13_4",
                                   "phase_F13_4b", "phase_F13_5", "phase_F13_6a", "author_exports_2026_10")]


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
        before = json.loads((L.OUT / "F13_6b_step0_snapshot.json").read_bytes().decode("utf-8"))["files"]
        print("changed since step 0:", sorted(k for k in set(before) | set(snap) if before.get(k) != snap.get(k)))
        return 0
    stamp_p = L.OUT / "F13_6b_brief_stamp.json"
    if stamp_p.exists():
        decision = json.loads(stamp_p.read_bytes().decode("utf-8"))["f13_2d"]
    else:
        flag = (L.ROOT / L.DPR / "phase_F13_2d" / "run_logs" / "final.json").exists()  # the one existence check of the brief
        decision = {"final_json_present": flag, "checked_utc": L.now(),
                    "institution_inputs": "phase_F13_2d v3" if flag else "phase_F13_2c v2, with the mark " + L.MARK_2D,
                    "note": "a shell pre-check at 2026-10-13T12:56:25Z gave the same answer (absent)"}
    inputs = {rel: {"bytes": L.path(rel).stat().st_size, "sha256": L.sha256_file(L.path(rel))} for rel in L.input_files()}
    brief = L.OUT / "F13_6b_brief.md"
    L.jdump({"run_utc": L.now(), "brief_sha256": L.sha256_file(brief), "brief_bytes": brief.stat().st_size, "root": str(L.ROOT).replace("\\", "/"),
             "registry_location": str(L.ROOT).replace("\\", "/") + "/" + L.DPR + "PHASE_REGISTRY.csv", "f13_2d": decision, "inputs": inputs,
             "inputs_count": len(inputs), "snapshot_files": len(snap),
             "left_out": [L.DPR + "phase_F13_2d", "tools", L.DPR + "PHASE_REGISTRY.csv"]}, stamp_p)
    L.jdump({"run_utc": L.now(), "files": snap}, L.OUT / "F13_6b_step0_snapshot.json")
    print("step 0:", len(snap), "snapshot files;", len(inputs), "inputs; F13.2d final.json present:", decision["final_json_present"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
