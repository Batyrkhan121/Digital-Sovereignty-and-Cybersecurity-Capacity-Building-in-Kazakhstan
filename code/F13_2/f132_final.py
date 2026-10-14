"""Phase F13.2 - the closing (--dry: gates and a draft report). No registry row is written: the rows phase_F12_4, phase_F13_1
(from phase_F13_1/run_logs/registry_rows_pending.json) and phase_F13_2 wait for the author's 'реестр'. The phase_F13_2 row's file
count and bytes are the folder's fixed point; all three rows are kept, unwritten, in run_logs/registry_rows_pending.json."""
import sys
sys.dont_write_bytecode = True

import csv
import io
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132_lib as L
import f132_gates
import f132_report

F131_PENDING = L.ROOT / "outputs" / "dprg_revision_2026" / "phase_F13_1" / "run_logs" / "registry_rows_pending.json"


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
    draft = f132_report.build(None, f132_gates.run_all())
    gates = f132_gates.run_all(report=draft)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=f132_gates.FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(gates)
    (L.OUT / "phase_F13_2_checkpoint_assertions.csv").write_bytes(buf.getvalue().encode("utf-8"))
    ver = f132_report.rows(L.OUT / "phase_F13_2_independent_verification.csv")
    ok_ver = bool(ver) and all(r.get("verdict") == "PASS" for r in ver)
    ok_gates = all(g["verdict"] == "PASS" and g["falsifiability"] == "DEMONSTRATED" for g in gates)
    L.jdump({"run_utc": L.now(), "gates": {g["gate"]: g["verdict"] for g in gates}, "verifier_rows": len(ver), "verifier_all_pass": ok_ver},
            L.RUN_LOGS / ("final_dry.json" if dry else "final.json"))
    if dry:
        (L.OUT / "phase_F13_2_report.md").write_bytes(f132_report.build(None, gates).encode("utf-8"))
        print(json.dumps({"dry": True, "gates": [(g["gate"], g["verdict"], g["falsifiability"]) for g in gates], "verifier": ok_ver}))
        return 0
    assert ok_gates and ok_ver, (ok_gates, ok_ver)
    prev = json.loads(F131_PENDING.read_bytes().decode("utf-8"))["rows_not_written_in_this_order"]
    n = json.loads((L.OUT / "F13_2_numbers.json").read_bytes().decode("utf-8"))
    note = (f"Structural indicators on the frame E1 (Scopus export 2026-10-13, 841; Decisions 41-42): years, types (retracted kept apart), "
            f"{n['T2a']['sources']} sources with Bradford zones, {n['T2e']['series']} conference series, citations (h-index "
            f"{n['T3a']['h-index of the corpus']}, total {n['T3a']['citations, total']}), open access {n['T4a']['oa']}, funding {n['T4b']['funded']}, "
            f"WoS validation on 216 pairs (types {n['T5']['type_agreement']}/216, rho {n['T5c']['Spearman rank correlation (average ranks for ties)']}), "
            "deltas D1-D5 against F12.1, figure Fig_annual_output_by_type (not viewed). Gates G1-G6 PASS; independent verifier "
            f"{sum(1 for r in ver if r.get('verdict') == 'PASS')}/{len(ver)}. No author names, abstracts or references; CORRECTIONS unchanged.")
    row = {"phase_id": "phase_F13_2", "path": "outputs/dprg_revision_2026/phase_F13_2", "created_utc": L.now(), "status": "COMPLETE",
           "produced_numbers": "YES", "superseded_by": "",
           "safe_to_publish": "YES - aggregates and titles of the top-20 works; no names, abstracts or references", "file_count": 0, "bytes": 0, "note": note}
    assert sum(L.shape_counts(json.dumps(row, ensure_ascii=False)).values()) == 0
    guess, rounds = (0, 0), 0
    while True:
        rounds += 1
        row["file_count"], row["bytes"] = guess
        L.jdump({"rows_not_written_in_this_order": prev + [row], "write_only_on": "the author's message 'реестр'"}, L.RUN_LOGS / "registry_rows_pending.json")
        (L.OUT / "phase_F13_2_report.md").write_bytes(f132_report.build(prev + [row], gates).encode("utf-8"))
        measured = folder_size(L.OUT)
        if measured == guess:
            break
        assert rounds < 12
        guess = measured
    print(json.dumps({"fixed_point": folder_size(L.OUT) == guess, "files_bytes": guess, "rounds": rounds,
                      "gates": [(g["gate"], g["verdict"]) for g in gates], "registry_written": False}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
