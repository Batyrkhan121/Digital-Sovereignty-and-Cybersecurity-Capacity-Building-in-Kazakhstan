"""Phase F13.3b - step 0: brief stamp; input digests (E1 against README; references_repaired.csv, the F13.3 tables and
f133_lib.R recorded); snapshot of the named untouchables (named list, no walk from the root). phase_F13_2e, tools/ and the registry
are left out (parallel session). With --after: compare with the step-0 snapshot (console only)."""
import sys
sys.dont_write_bytecode = True

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f133b_lib as L

NAMED = ["main.qmd", "title_page_DPRG.qmd", "references.bib", "outputs/dprg_revision_2026/CORRECTIONS.csv", ".gitignore"]
NAMED_FOLDERS = ["SUBMISSION_TP_2026_09_21/rebuilt", "outputs/tp_submission"]
NAMED_TREES = ["outputs/dprg_revision_2026/" + p for p in (
    "phase_F13_1", "phase_F13_2", "phase_F13_2b", "phase_F13_2c", "phase_F13_2d", "phase_F13_3", "phase_F13_4", "phase_F13_4b",
    "phase_F13_5", "phase_F13_6a", "phase_F13_6b", "author_exports_2026_10")]


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
        before = L.jload(L.OUT / "F13_3b_step0_snapshot.json")
        changed = sorted(k for k in set(before["files"]) | set(snap) if before["files"].get(k) != snap.get(k))
        print("changed since step 0:", changed, "; .gitignore lines added:", [x for x in gitignore_lines() if x not in before["gitignore_lines"]])
        return 0
    readme = L.path(L.README).read_bytes().decode("utf-8")
    inputs = {"E1": {"file": L.E1, "sha256": snap[L.E1]["sha256"], "equal": snap[L.E1]["sha256"] == L.E1_SHA, "in_README": L.E1_SHA in readme},
              "references_repaired": {"file": L.REFS, "sha256": snap[L.REFS]["sha256"], "bytes": snap[L.REFS]["bytes"]},
              "f133_lib_R": {"file": L.F133_LIB_R, "sha256": snap[L.F133_LIB_R]["sha256"]}}
    for k, rel in L.F133_TABLES.items():
        inputs["F13_3_" + k] = {"file": rel, "sha256": snap[rel]["sha256"]}
    brief = L.OUT / "F13_3b_brief.md"
    L.jdump({"run_utc": L.now(), "brief_sha256": L.sha256_file(brief), "brief_bytes": brief.stat().st_size, "root": str(L.ROOT).replace("\\", "/"),
             "inputs": inputs}, L.OUT / "F13_3b_brief_stamp.json")
    L.jdump({"run_utc": L.now(), "files": snap, "gitignore_lines": gitignore_lines()}, L.OUT / "F13_3b_step0_snapshot.json")
    print("step 0:", len(snap), "files; E1 equal/in README:", inputs["E1"]["equal"], inputs["E1"]["in_README"],
          "; references_repaired sha", inputs["references_repaired"]["sha256"][:16], "; F13.3 tables recorded:", len(L.F133_TABLES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
