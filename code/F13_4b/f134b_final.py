"""Phase F13.4b - the closing (copied from F13.4's closing): gates on the final outputs including the report; no registry write; the
pending row goes to run_logs/registry_rows_pending.json, its file count and bytes the folder's fixed point. --dry: no pending row."""
import sys
sys.dont_write_bytecode = True

import csv
import io
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f134b_lib as L
import f134b_gates
import f134b_report

PHASE_ID = "phase_F13_4b"
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
    draft = f134b_report.build(None, f134b_gates.run_all())
    gates = f134b_gates.run_all(report=draft)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=f134b_gates.FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(gates)
    (L.OUT / "phase_F13_4b_checkpoint_assertions.csv").write_bytes(buf.getvalue().encode("utf-8"))
    ver = f134b_report.rows("phase_F13_4b_independent_verification.csv", L.OUT)
    ok_ver = bool(ver) and all(r.get("verdict") == "PASS" for r in ver)
    ok_gates = all(g["verdict"] == "PASS" and g["falsifiability"] == "DEMONSTRATED" for g in gates)
    L.jdump({"run_utc": L.now(), "gates": {g["gate"]: g["verdict"] for g in gates}, "verifier_rows": len(ver), "verifier_all_pass": ok_ver},
            L.RUN_LOGS / ("final_dry.json" if dry else "final.json"))
    if dry:
        (L.OUT / "phase_F13_4b_report.md").write_bytes(f134b_report.build(None, gates).encode("utf-8"))
        print(json.dumps({"dry": True, "gates": [(g["gate"], g["verdict"]) for g in gates], "verifier": ok_ver}))
        return 0
    assert ok_gates, "a gate failed"
    assert ok_ver, "the verifier did not pass every check"
    num = L.jload(L.OUT / "F13_4b_numbers.json")
    a = {(r["country"], r["window"]): r for r in num["T4a"]}
    std = "; ".join(f"{c} " + "/".join(a[(c, f'{lo}-{hi}')]["ai_year_standardised"] for lo, hi in L.PERIODS) for c in L.COUNTRIES)
    note = ("Complements F13.4 (tables T4; nothing in F13.4 changed): activity index for KZ, UZ, AZ, BY, KG from the new all-output series "
            "(Scopus Analyze, 2026-10-13); crude and year-standardised with bootstrap intervals; year-standardised by period 2003-2016/"
            f"2017-2021/2022-2025: {std}; KZ rows equal F13.4 T2b/T2d; sensitivity without 2025; figure Fig_activity_index_comparators "
            f"(pdf/png/tif, not viewed). Gates G1-G6 PASS; independent verifier {sum(1 for r in ver if r.get('verdict') == 'PASS')}/{len(ver)}. "
            "No manuscript or package file touched; CORRECTIONS unchanged.")
    row = {"phase_id": PHASE_ID, "path": "outputs/dprg_revision_2026/phase_F13_4b", "created_utc": L.now(), "status": "COMPLETE",
           "produced_numbers": "YES", "superseded_by": "", "safe_to_publish": "YES - aggregates", "file_count": 0, "bytes": 0, "note": note}
    assert list(row) == REGISTRY_FIELDS
    guess, rounds = (0, 0), 0
    while True:
        rounds += 1
        row["file_count"], row["bytes"] = guess
        (L.OUT / "phase_F13_4b_report.md").write_bytes(f134b_report.build(row, gates).encode("utf-8"))
        L.jdump({"phase": PHASE_ID, "command": "реестр (the author's word in this session)", "order": "after phase_F13_5 and phase_F13_4",
                 "append_row": row, "set_superseded_by": [], "program": "programs/f134b_registry.py"}, PENDING)
        measured = folder_size(L.OUT)
        if measured == guess:
            break
        assert rounds < 10
        guess = measured
    print(json.dumps({"fixed_point": folder_size(L.OUT) == guess, "files_bytes": guess, "rounds": rounds, "registry_written": False,
                      "gates": [(g["gate"], g["verdict"]) for g in gates]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
