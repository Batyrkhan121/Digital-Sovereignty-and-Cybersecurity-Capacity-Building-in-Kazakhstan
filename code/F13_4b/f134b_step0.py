"""Phase F13.4b - step 0 (copied from F13.4's step 0; changed: eleven series against the manifest, the sums of the four new ones, and
the brief's snapshot list: main.qmd, title_page_DPRG.qmd, references.bib, rebuilt/*, outputs/tp_submission/*, the trees phase_F13_1,
phase_F13_2, phase_F13_2b, phase_F13_4, phase_F13_5, phase_F13_6a, author_exports_2026_10, plus CORRECTIONS.csv). PHASE_REGISTRY.csv,
phase_F13_3/ and phase_F13_2c/ are neither read nor snapshotted. With --after: compare with step 0 (console only)."""
import sys
sys.dont_write_bytecode = True

import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f134b_lib as L

NAMED = ["main.qmd", "title_page_DPRG.qmd", "references.bib", "outputs/dprg_revision_2026/CORRECTIONS.csv"]
NAMED_FOLDERS = ["SUBMISSION_TP_2026_09_21/rebuilt", "outputs/tp_submission"]
NAMED_TREES = ["outputs/dprg_revision_2026/" + n for n in ("phase_F13_1", "phase_F13_2", "phase_F13_2b", "phase_F13_4", "phase_F13_5",
                                                          "phase_F13_6a", "author_exports_2026_10")]


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


def inputs():
    man = {m["file"]: m for m in L.jload(L.path(L.MANIFEST))}
    S = L.load_series()
    series = {}
    for name, fn in L.SERIES.items():
        d = L.sha256_file(L.path(L.EXPORTS + "/" + fn))
        series[name] = {"file": fn, "sha256": d, "equal_manifest": d == man[fn]["sha256"], "sum": sum(S[name].values()),
                        "manifest_sum_of_years": man[fn]["sum_of_years"], "manifest_ui_total": man[fn]["ui_total"]}
    readme = L.path(L.README).read_bytes().decode("utf-8")
    line = next(ln for ln in readme.splitlines() if Path(L.E1).name in ln and "sha256" in ln)
    e1 = L.sha256_file(L.path(L.E1))
    rs = re.search(r"sha256 ([0-9a-f]{64})", line).group(1)
    return {"series": series, "manifest_entries": len(man), "E1_sha256": e1, "E1_equal_README": e1 == rs,
            "other_inputs": {rel: L.sha256_file(L.path(rel)) for rel in (L.MANIFEST, L.README, L.LONG, L.F134_T2B, L.F134_T2D)}}


def main():
    snap = snapshot()
    if "--after" in sys.argv:
        before = L.jload(L.OUT / "F13_4b_step0_snapshot.json")["files"]
        print("changed since step 0:", sorted(k for k in set(before) | set(snap) if before.get(k) != snap.get(k)))
        return 0
    brief = L.OUT / "F13_4b_brief.md"
    inp = inputs()
    L.jdump({"run_utc": L.now(), "brief_sha256": L.sha256_file(brief), "brief_bytes": brief.stat().st_size,
             "root": str(L.ROOT).replace("\\", "/"), "registry_path": "outputs/dprg_revision_2026/PHASE_REGISTRY.csv (not read)", **inp},
            L.OUT / "F13_4b_brief_stamp.json")
    L.jdump({"run_utc": L.now(), "files": snap}, L.OUT / "F13_4b_step0_snapshot.json")
    print("step 0:", len(snap), "files; manifest entries:", inp["manifest_entries"], "; equal manifest:",
          all(v["equal_manifest"] for v in inp["series"].values()), "; sums:", {k: v["sum"] for k, v in inp["series"].items()},
          "; E1 equal README:", inp["E1_equal_README"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
