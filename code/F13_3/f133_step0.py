"""Phase F13.3 - step 0: brief stamp; input digests (E1, E2 against README_exports.txt and the brief's prefixes; T3a_pairs and the
v3 thesaurus recorded); environment.json recorded; snapshot of the named untouchables (named list, no walk from the root).
phase_F13_5, phase_F13_2b and PHASE_REGISTRY.csv are left out (parallel sessions); the registry's place is only checked to exist.
With --after: compare with the step-0 snapshot (console only)."""
import sys
sys.dont_write_bytecode = True

import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f133_lib as L

NAMED = ["main.qmd", "title_page_DPRG.qmd", "references.bib", "outputs/dprg_revision_2026/CORRECTIONS.csv", ".gitignore"]
NAMED_FOLDERS = ["SUBMISSION_TP_2026_09_21/rebuilt", "outputs/tp_submission"]
NAMED_TREES = ["outputs/dprg_revision_2026/" + p for p in ("phase_F12_1", "phase_F12_3", "phase_F12_3b", "phase_F12_3c", "phase_F12_4",
                                                         "phase_F13_1", "phase_F13_2", "author_exports_2026_10")]
REGISTRY = "outputs/dprg_revision_2026/PHASE_REGISTRY.csv"


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
        for rel, (b, h) in L.folder_files(L.ROOT / tree).items():
            files[tree + "/" + rel] = {"bytes": b, "sha256": h}
    return files


def gitignore_lines():
    return L.path(".gitignore").read_bytes().decode("utf-8").split("\n")


def main():
    snap = snapshot()
    if "--after" in sys.argv:
        before = L.jload(L.OUT / "F13_3_step0_snapshot.json")
        changed = sorted(k for k in set(before["files"]) | set(snap) if before["files"].get(k) != snap.get(k))
        added = [x for x in gitignore_lines() if x not in before["gitignore_lines"]]
        print("changed since step 0:", changed, "; .gitignore lines added:", added)
        return 0
    inputs = {k: {"file": rel, "sha256": snap[rel]["sha256"], "expected": L.EXPECTED[k], "equal": snap[rel]["sha256"] == L.EXPECTED[k]}
              for k, rel in (("E1", L.E1), ("E2", L.E2))}
    readme = L.path(L.README).read_bytes().decode("utf-8")
    for k in ("E1", "E2"):
        inputs[k]["in_README"] = L.EXPECTED[k] in readme
    inputs["E1"]["brief_prefix"] = L.EXPECTED["E1"].startswith("fe01023d23afe95d")
    inputs["E2"]["brief_prefix"] = L.EXPECTED["E2"].startswith("413b0fa8")
    for k, rel in (("pairs", L.PAIRS), ("thesaurus_v3", L.THES)):
        inputs[k] = {"file": rel, "sha256": snap[rel]["sha256"], "bytes": snap[rel]["bytes"]}
    env = L.RUN_LOGS / "environment.json"
    brief = L.OUT / "F13_3_brief.md"
    L.jdump({"run_utc": L.now(), "brief_sha256": L.sha256_file(brief), "brief_bytes": brief.stat().st_size,
             "root": str(L.ROOT).replace("\\", "/"), "registry_file": REGISTRY, "registry_exists": (L.ROOT / REGISTRY).exists(),
             "inputs": inputs, "environment_sha256": L.sha256_file(env), "environment": L.jload(env)}, L.OUT / "F13_3_brief_stamp.json")
    L.jdump({"run_utc": L.now(), "files": snap, "gitignore_lines": gitignore_lines()}, L.OUT / "F13_3_step0_snapshot.json")
    print("step 0:", len(snap), "files; inputs equal:", {k: v["equal"] for k, v in inputs.items() if "equal" in v},
          "; in README:", {k: inputs[k]["in_README"] for k in ("E1", "E2")}, "; registry exists:", (L.ROOT / REGISTRY).exists())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
