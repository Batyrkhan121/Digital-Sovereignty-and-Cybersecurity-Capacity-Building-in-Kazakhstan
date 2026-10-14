"""Phase F13.3b - the closing (--dry: gates and a draft report). The registry is not read or written here: this phase's row (file count
and bytes = the folder's fixed point) is kept in run_logs/registry_rows_pending.json for the main session's registry script."""
import sys
sys.dont_write_bytecode = True

import csv
import io
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f133b_lib as L
import f133b_gates
import f133b_report


def folder_size(p):
    files = L.folder_files(p)
    return len(files), sum(b for b, _ in files.values())


def main():
    dry = "--dry" in sys.argv
    gates = f133b_gates.run_all()
    gates = f133b_gates.run_all(report=f133b_report.build(None, gates))
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=f133b_gates.FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(gates)
    (L.OUT / "phase_F13_3b_checkpoint_assertions.csv").write_bytes(buf.getvalue().encode("utf-8"))
    ver = f133b_report.rows(L.OUT / "phase_F13_3b_independent_verification.csv")
    ok_ver = bool(ver) and all(r.get("verdict") in ("PASS", "EXPLAINED") for r in ver)
    ok_gates = all(g["verdict"] == "PASS" and g["falsifiability"] == "DEMONSTRATED" for g in gates)
    L.jdump({"run_utc": L.now(), "gates": {g["gate"]: g["verdict"] for g in gates}, "verifier_rows": len(ver), "verifier_ok": ok_ver},
            L.RUN_LOGS / ("final_dry.json" if dry else "final.json"))
    if dry:
        (L.OUT / "phase_F13_3b_report.md").write_bytes(f133b_report.build(None, gates).encode("utf-8"))
        print(json.dumps({"dry": True, "gates": [(g["gate"], g["verdict"], g["falsifiability"]) for g in gates], "verifier_ok": ok_ver}, indent=1))
        return 0
    assert ok_gates and ok_ver, (ok_gates, ok_ver)
    n = L.jload(L.OUT / "F13_3b_numbers.json")
    npass = sum(1 for r in ver if r.get("verdict") == "PASS")
    nexp = sum(1 for r in ver if r.get("verdict") == "EXPLAINED")
    note = ("supersedes F13.3 T2, T4a/T4a2/T4b/T4c, T5a/T5b/T5b2/T5b3, T6a/T6b as the main line; F13.3 T0, T1, T1a-T1c, T3 remain. "
            f"Work key (F13.3's function): {n['T1']['works']} works, {n['T1']['ge2']}/{n['T1']['ge5']}/{n['T1']['ge10']} cited by >= 2/5/10 records; "
            f"local citations by title {n['T3']['links']} links, {n['T3']['citing']} citing, {n['T3']['cited']} cited, max {n['T3']['max']}; "
            f"coupling {n['T4']['nodes']} records, {n['T4']['edges']} links, {n['T4']['big']} clusters >= 10; co-citation {n['T5']['works']} works, "
            f"{n['T5']['edges']} links, {n['T5']['big']} clusters >= 5; sources by parse rule {n['T6']['recognised']}. Gates G1-G6 PASS; "
            f"verifier {npass} PASS, {nexp} EXPLAINED, 0 FAIL of {len(ver)}. Figures not viewed. CORRECTIONS unchanged.")
    row = {"phase_id": "phase_F13_3b", "path": "outputs/dprg_revision_2026/phase_F13_3b", "created_utc": L.now(), "status": "COMPLETE",
           "produced_numbers": "YES", "superseded_by": "", "safe_to_publish": "YES - aggregate tables; data/ outside git",
           "file_count": 0, "bytes": 0, "note": note}
    assert sum(L.shape_counts(json.dumps(row, ensure_ascii=False)).values()) == 0
    guess, rounds = (0, 0), 0
    while True:
        rounds += 1
        row["file_count"], row["bytes"] = guess
        L.jdump({"rows_not_written_in_this_order": [row], "write_only_on": "the main session's registry script"}, L.RUN_LOGS / "registry_rows_pending.json")
        (L.OUT / "phase_F13_3b_report.md").write_bytes(f133b_report.build([row], gates, ver).encode("utf-8"))
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
