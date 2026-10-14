"""Phase F13.2 - step 0: brief stamp; input digests (E1, E2 against README_exports.txt; I1 against the brief; the F13.1 and F12.1
tables recorded); snapshot of the named untouchables. phase_F12_3c and PHASE_REGISTRY.csv are left out (parallel session).
With --after: compare with the step-0 snapshot (console only)."""
import sys
sys.dont_write_bytecode = True

import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132_lib as L

NAMED = ["main.qmd", "title_page_DPRG.qmd", "references.bib", L.I1, "outputs/dprg_revision_2026/CORRECTIONS.csv"]
NAMED_FOLDERS = ["SUBMISSION_TP_2026_09_21/rebuilt", "outputs/tp_submission", "outputs/dprg_revision_2026/author_exports_2026_10"]
NAMED_TREES = ["outputs/dprg_revision_2026/" + p for p in ("phase_F12_1", "phase_F12_3", "phase_F12_3b", "phase_F12_4", "phase_F13_1")]


def snapshot():
    files = {}
    for rel in NAMED:
        p = L.path(rel)
        files[rel] = {"bytes": p.stat().st_size, "sha256": L.sha256_file(p)} if p.exists() else None
    for folder in NAMED_FOLDERS:
        for e in sorted((L.ROOT / folder).iterdir(), key=lambda x: x.name):
            if e.is_file() and not e.is_symlink():
                files[folder + "/" + e.name] = {"bytes": e.stat().st_size, "sha256": L.sha256_file(e)}
    for tree in NAMED_TREES:
        stack = [L.ROOT / tree]
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
        before = json.loads((L.OUT / "F13_2_step0_snapshot.json").read_bytes().decode("utf-8"))["files"]
        print("changed since step 0:", sorted(k for k in set(before) | set(snap) if before.get(k) != snap.get(k)))
        return 0
    inputs = {k: {"file": rel, "sha256": snap[rel]["sha256"], "expected": L.EXPECTED[k], "equal": snap[rel]["sha256"] == L.EXPECTED[k]}
              for k, rel in (("E1", L.E1), ("E2", L.E2), ("I1", L.I1))}
    readme = L.path(L.README).read_bytes().decode("utf-8")
    inputs["E1"]["in_README"] = L.EXPECTED["E1"] in readme
    inputs["E2"]["in_README"] = L.EXPECTED["E2"] in readme
    tables = {rel: snap.get(rel, {}).get("sha256") for rel in [L.PAIRS, L.F131_YEARS] + list(L.F121.values())}
    brief = L.OUT / "F13_2_brief.md"
    L.jdump({"run_utc": L.now(), "brief_sha256": L.sha256_file(brief), "brief_bytes": brief.stat().st_size, "root": str(L.ROOT).replace("\\", "/"),
             "inputs": inputs, "tables_read": tables}, L.OUT / "F13_2_brief_stamp.json")
    L.jdump({"run_utc": L.now(), "files": snap}, L.OUT / "F13_2_step0_snapshot.json")
    print("step 0:", len(snap), "files; inputs equal:", {k: v["equal"] for k, v in inputs.items()}, "; tables recorded:", sum(1 for v in tables.values() if v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
