"""Phase F13.7a - the closing: gates on the final outputs including the report; the pending registry row in
run_logs/registry_rows_pending.json (file count and bytes = the folder's fixed point). The registry is written afterwards by one run of
tools/registry_apply.py (brief). --dry: gates and the report without the pending row."""
import sys
sys.dont_write_bytecode = True

import csv
import io
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f137a_lib as L
import f137a_gates
import f137a_report

PHASE_ID = "phase_F13_7a"
PENDING = L.RUN_LOGS / "registry_rows_pending.json"
REGISTRY_FIELDS = ["phase_id", "path", "created_utc", "status", "produced_numbers", "superseded_by", "safe_to_publish", "file_count", "bytes", "note"]


def folder_size(p):
    n = b = 0
    stack = [Path(p)]
    while stack:
        d = stack.pop()
        for e in sorted(d.iterdir(), key=lambda x: x.name):
            if e.is_symlink():
                continue
            if e.is_dir():
                stack.append(e)
            else:
                n += 1
                b += e.stat().st_size
    return n, b


def main():
    dry = "--dry" in sys.argv
    draft = f137a_report.build(None, f137a_gates.run_all())
    gates = f137a_gates.run_all(report=draft)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=f137a_gates.FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(gates)
    (L.OUT / "phase_F13_7a_checkpoint_assertions.csv").write_bytes(buf.getvalue().encode("utf-8"))
    ver = f137a_report.rows("phase_F13_7a_independent_verification.csv", L.OUT)
    ok_ver = bool(ver) and all(r.get("verdict") == "PASS" for r in ver)
    ok_gates = all(g["verdict"] == "PASS" and g["falsifiability"] == "DEMONSTRATED" for g in gates)
    L.jdump({"run_utc": L.now(), "gates": {g["gate"]: g["verdict"] for g in gates}, "verifier_rows": len(ver), "verifier_all_pass": ok_ver},
            L.RUN_LOGS / ("final_dry.json" if dry else "final.json"))
    if dry:
        (L.OUT / "phase_F13_7a_report.md").write_bytes(f137a_report.build(None, gates).encode("utf-8"))
        print(json.dumps({"dry": True, "gates": [(g["gate"], g["verdict"]) for g in gates], "verifier": ok_ver}))
        return 0
    assert ok_gates, "a gate failed"
    assert ok_ver, "the verifier did not pass every check"
    rj = L.jload(L.RUN_LOGS / "render.json")
    wb = L.jload(L.RUN_LOGS / "workbook.json")
    cj = L.jload(L.RUN_LOGS / "corrections.json")
    note = ("Package tools, part 1 (no manuscript or package change): trial render of the F13.6b draft - DOCX built "
            f"({rj['docx']['media_files']} figures, 0 unresolved references), PDF not built offline (tectonic font cache; TinyTeX formats) - "
            f"issues in R1; figure manifest F1 (all files 300 dpi); collaboration figure redrawn on thesaurus v3.1; supplementary workbook "
            f"({wb['data_sheets']} sheets from closed phases' tables, X1 sources); {cj['lines']} draft CORRECTIONS lines (C1; CORRECTIONS.csv not "
            f"written). Gates G1-G6 PASS; independent verifier {sum(1 for r in ver if r.get('verdict') == 'PASS')}/{len(ver)}. Registry read once in "
            "step 0 for the Phase log sheet.")
    row = {"phase_id": PHASE_ID, "path": "outputs/dprg_revision_2026/phase_F13_7a", "created_utc": L.now(), "status": "COMPLETE",
           "produced_numbers": "NO (tools and assembly from closed phases' tables)", "superseded_by": "",
           "safe_to_publish": "YES - aggregates and names only; no author of the corpus", "file_count": 0, "bytes": 0, "note": note}
    assert list(row) == REGISTRY_FIELDS
    guess, rounds = (0, 0), 0
    while True:
        rounds += 1
        row["file_count"], row["bytes"] = guess
        (L.OUT / "phase_F13_7a_report.md").write_bytes(f137a_report.build(row, gates).encode("utf-8"))
        L.jdump({"phase": PHASE_ID, "append_row": row, "set_superseded_by": [],
                 "applied_by": "tools/registry_apply.py (one run without --hold after the closing, brief)"}, PENDING)
        measured = folder_size(L.OUT)
        if measured == guess:
            break
        assert rounds < 10
        guess = measured
    print(json.dumps({"fixed_point": folder_size(L.OUT) == guess, "files_bytes": guess, "rounds": rounds,
                      "gates": [(g["gate"], g["verdict"]) for g in gates]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
