"""Phase F13.6b - the closing (--dry: gates and a draft report). No registry row is written: the row phase_F13_6b waits for the
author's 'реестр'; its file count and bytes are the folder's fixed point; it is kept, unwritten, in run_logs/registry_rows_pending.json."""
import sys
sys.dont_write_bytecode = True

import csv
import io
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f136b_lib as L
import f136b_gates
import f136b_report


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
    L.install_r17_guard()
    dry = "--dry" in sys.argv
    draft = f136b_report.build(None, f136b_gates.run_all())
    gates = f136b_gates.run_all(report=draft)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=f136b_gates.FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(gates)
    (L.OUT / "phase_F13_6b_checkpoint_assertions.csv").write_bytes(buf.getvalue().encode("utf-8"))
    ver = f136b_report.rows(L.OUT / "phase_F13_6b_independent_verification.csv")
    ok_ver = bool(ver) and all(r.get("verdict") in ("PASS", "INFO") for r in ver) and any(r.get("verdict") == "PASS" for r in ver)
    ok_gates = all(g["verdict"] == "PASS" and g["falsifiability"] == "DEMONSTRATED" for g in gates)
    L.jdump({"run_utc": L.now(), "gates": {g["gate"]: g["verdict"] for g in gates}, "verifier_rows": len(ver), "verifier_all_pass": ok_ver},
            L.RUN_LOGS / ("final_dry.json" if dry else "final.json"))
    if dry:
        (L.OUT / "phase_F13_6b_report.md").write_bytes(f136b_report.build(None, gates).encode("utf-8"))
        print(json.dumps({"dry": True, "gates": [(g["gate"], g["verdict"], g["falsifiability"]) for g in gates], "verifier": ok_ver}, indent=1))
        return 0
    assert ok_gates and ok_ver, (ok_gates, ok_ver)
    n = json.loads((L.OUT / "F13_6b_numbers.json").read_bytes().decode("utf-8"))
    note = (f"Draft of the new manuscript, part 1 (draft/main_v2.qmd): Methodology and Results rewritten on the new data layer (Decisions 38-46), "
            f"{n['words_sections_2_3_prose']} words; {n['tokens_sections_2_3']} numeric tokens traced in the evidence index (all table and formula tokens "
            f"match); other sections copied from main.qmd with {n['marks'].get(L.MARK_P2, 0)} part-2 marks; {n['marks'].get(L.MARK_2D, 0)} F13.2d marks; "
            f"citation structure left to part 2. Gates G1-G6 PASS; independent verifier {sum(1 for r in ver if r.get('verdict') == 'PASS')} PASS, {sum(1 for r in ver if r.get('verdict') == 'INFO')} informational, 0 FAIL. "
            "main.qmd untouched.")
    row = {"phase_id": "phase_F13_6b", "path": "outputs/dprg_revision_2026/phase_F13_6b", "created_utc": L.now(), "status": "COMPLETE",
           "produced_numbers": "NO (draft text from tables)", "superseded_by": "", "safe_to_publish": "YES", "file_count": 0, "bytes": 0, "note": note}
    assert sum(L.shape_counts(json.dumps(row, ensure_ascii=False)).values()) == 0
    guess, rounds = (0, 0), 0
    while True:
        rounds += 1
        row["file_count"], row["bytes"] = guess
        L.jdump({"rows_not_written": [row], "write_only_on": "the author's message 'реестр'"}, L.RUN_LOGS / "registry_rows_pending.json")
        (L.OUT / "phase_F13_6b_report.md").write_bytes(f136b_report.build([row], gates).encode("utf-8"))
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
