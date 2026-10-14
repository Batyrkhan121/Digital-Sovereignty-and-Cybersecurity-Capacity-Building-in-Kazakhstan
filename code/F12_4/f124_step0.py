"""Phase F12.4 - step 0: brief stamp; input digests (S and O against their manifest.csv; I1, I3, I4 against phase F12.1's probe
record); snapshot of the named untouchables (phase_F12_3b and PHASE_REGISTRY.csv are left out: a parallel session writes them).
With --after: compare with the step-0 snapshot (console only)."""
import sys
sys.dont_write_bytecode = True

import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f124_lib as L

NAMED = ["main.qmd", "title_page_DPRG.qmd", "references.bib", L.S, L.O, L.I1, L.I3, L.I4, "outputs/dprg_revision_2026/CORRECTIONS.csv"] \
    + [p for pair in L.META.values() for p in pair]
NAMED_FOLDERS = ["SUBMISSION_TP_2026_09_21/rebuilt", "outputs/tp_submission"]
NAMED_TREES = ["outputs/dprg_revision_2026/phase_F12_1", "outputs/dprg_revision_2026/phase_F12_3"]


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


def manifest_check():
    out = {}
    for db, (man, meta) in L.META.items():
        rows = L.read_csv(man)
        target = L.S if db == "scopus" else L.O
        name = target.rsplit("/", 1)[1]
        rec = next(r for r in rows if r["artifact"] == name)
        p = L.path(target)
        out[db] = {"artifact": name, "manifest_sha256": rec["sha256"], "sha256": L.sha256_file(p), "manifest_rows": int(rec["rows"]),
                   "rows": len(L.read_csv(target)), "manifest_bytes": int(rec["file_size_bytes"]), "bytes": p.stat().st_size}
        out[db]["equal"] = (out[db]["sha256"] == rec["sha256"] and out[db]["rows"] == int(rec["rows"])
                            and out[db]["bytes"] == int(rec["file_size_bytes"]))
    return out


def main():
    snap = snapshot()
    if "--after" in sys.argv:
        before = json.loads((L.OUT / "F12_4_step0_snapshot.json").read_bytes().decode("utf-8"))["files"]
        print("changed since step 0:", sorted(k for k in set(before) | set(snap) if before.get(k) != snap.get(k)))
        return 0
    probe = json.loads((L.F121 / "run_logs" / "probe.json").read_bytes().decode("utf-8"))["files"]
    f121 = {"I1": probe["I1"]["sha256"], "I3": probe["I3"]["sha256"], "I4": probe["I4"]["sha256"]}
    now = {"I1": snap[L.I1]["sha256"], "I3": snap[L.I3]["sha256"], "I4": snap[L.I4]["sha256"]}
    man = manifest_check()
    brief = L.OUT / "F12_4_brief.md"
    L.jdump({"run_utc": L.now(), "brief_sha256": L.sha256_file(brief), "brief_bytes": brief.stat().st_size,
             "root": str(L.ROOT).replace("\\", "/"), "S_O_against_manifest": man, "I_now": now, "I_in_F12_1": f121,
             "I_equal_F12_1": now == f121, "F12_1_tables": {k: L.sha256_file(L.path(v)) for k, v in L.F121_TABLES.items()}},
            L.OUT / "F12_4_brief_stamp.json")
    L.jdump({"run_utc": L.now(), "files": snap}, L.OUT / "F12_4_step0_snapshot.json")
    print("step 0:", len(snap), "files; S/O = manifest:", {k: v["equal"] for k, v in man.items()}, "; I1/I3/I4 = F12.1:", now == f121)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
