"""Phase F13.1 - step 0: brief stamp; input digests (E1, E1b, E2 against README_exports.txt; Y against manifest_year_series.json;
I1, I3 against the brief); snapshot of the named untouchables. phase_F12_3c and PHASE_REGISTRY.csv are left out (parallel
session). With --after: compare with the step-0 snapshot (console only)."""
import sys
sys.dont_write_bytecode = True

import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f131_lib as L

NAMED = ["main.qmd", "title_page_DPRG.qmd", "references.bib", L.I1, L.I3, "outputs/dprg_revision_2026/CORRECTIONS.csv"]
NAMED_FOLDERS = ["SUBMISSION_TP_2026_09_21/rebuilt", "outputs/tp_submission", "outputs/dprg_revision_2026/author_exports_2026_10"]
NAMED_TREES = ["outputs/dprg_revision_2026/phase_F12_1", "outputs/dprg_revision_2026/phase_F12_3", "outputs/dprg_revision_2026/phase_F12_3b",
               "outputs/dprg_revision_2026/phase_F12_4"]


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


def input_checks(snap):
    man = json.loads(L.path(L.YMAN).read_bytes().decode("utf-8"))
    y = {m["file"]: {"manifest_sha256": m["sha256"], "sha256": snap[L.EXP + m["file"]]["sha256"],
                     "equal": snap[L.EXP + m["file"]]["sha256"] == m["sha256"]} for m in man}
    e = {k: {"expected_sha256": L.EXPECTED[k], "sha256": snap[rel]["sha256"], "equal": snap[rel]["sha256"] == L.EXPECTED[k]}
         for k, rel in (("E1", L.E1), ("E1b", L.E1B), ("E2", L.E2), ("I1", L.I1))}
    e["I3"] = {"expected_prefix": L.EXPECTED_PREFIX["I3"], "sha256": snap[L.I3]["sha256"],
               "equal": snap[L.I3]["sha256"].startswith(L.EXPECTED_PREFIX["I3"])}
    return e, y


def main():
    snap = snapshot()
    if "--after" in sys.argv:
        before = json.loads((L.OUT / "F13_1_step0_snapshot.json").read_bytes().decode("utf-8"))["files"]
        print("changed since step 0:", sorted(k for k in set(before) | set(snap) if before.get(k) != snap.get(k)))
        return 0
    e, y = input_checks(snap)
    brief = L.OUT / "F13_1_brief.md"
    L.jdump({"run_utc": L.now(), "brief_sha256": L.sha256_file(brief), "brief_bytes": brief.stat().st_size, "root": str(L.ROOT).replace("\\", "/"),
             "inputs": e, "year_series": y, "gitignore_note": "outputs/dprg_revision_2026/phase_F13_1/data/ added to .gitignore before any data was written"},
            L.OUT / "F13_1_brief_stamp.json")
    L.jdump({"run_utc": L.now(), "files": snap}, L.OUT / "F13_1_step0_snapshot.json")
    print("step 0:", len(snap), "files; inputs equal:", {k: v["equal"] for k, v in e.items()}, "; year series equal:", all(v["equal"] for v in y.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
