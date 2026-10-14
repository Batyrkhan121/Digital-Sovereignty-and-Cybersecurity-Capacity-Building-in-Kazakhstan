"""Phase F13.3 - the closing (--dry: gates and a draft report). No registry row is written: the rows phase_F12_4, phase_F13_1,
phase_F13_2 (from phase_F13_2/run_logs/registry_rows_pending.json) and phase_F13_3 wait for the author's 'реестр'. The phase_F13_3
row's file count and bytes are the folder's fixed point; all four rows are kept, unwritten, in run_logs/registry_rows_pending.json."""
import sys
sys.dont_write_bytecode = True

import csv
import io
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f133_lib as L
import f133_gates
import f133_report

F132_PENDING = L.ROOT / "outputs" / "dprg_revision_2026" / "phase_F13_2" / "run_logs" / "registry_rows_pending.json"


def folder_size(p):
    files = L.folder_files(p)
    return len(files), sum(b for b, _ in files.values())


def main():
    dry = "--dry" in sys.argv
    gates = f133_gates.run_all()
    draft = f133_report.build(None, gates)
    gates = f133_gates.run_all(report=draft)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=f133_gates.FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(gates)
    (L.OUT / "phase_F13_3_checkpoint_assertions.csv").write_bytes(buf.getvalue().encode("utf-8"))
    ver = f133_report.rows(L.OUT / "phase_F13_3_independent_verification.csv")
    ok_ver = bool(ver) and all(r.get("verdict") in ("PASS", "EXPLAINED") for r in ver)
    ok_gates = all(g["verdict"] == "PASS" and g["falsifiability"] == "DEMONSTRATED" for g in gates)
    L.jdump({"run_utc": L.now(), "gates": {g["gate"]: g["verdict"] for g in gates}, "verifier_rows": len(ver), "verifier_ok": ok_ver},
            L.RUN_LOGS / ("final_dry.json" if dry else "final.json"))
    if dry:
        (L.OUT / "phase_F13_3_report.md").write_bytes(f133_report.build(None, gates).encode("utf-8"))
        print(json.dumps({"dry": True, "gates": [(g["gate"], g["verdict"], g["falsifiability"]) for g in gates], "verifier_ok": ok_ver}, indent=1))
        return 0
    assert ok_gates and ok_ver, (ok_gates, ok_ver)
    prev = L.jload(F132_PENDING)["rows_not_written_in_this_order"]
    assert [r["phase_id"] for r in prev] == ["phase_F12_4", "phase_F13_1", "phase_F13_2"], [r["phase_id"] for r in prev]
    n = L.jload(L.OUT / "F13_3_numbers.json")
    npass = sum(1 for r in ver if r.get("verdict") == "PASS")
    note = (f"supersedes F13.1 T1d/T3d. Citation structure of the E1 reference lists with bibliometrix 5.5.0 (Decision 44): references "
            f"repaired by the brief's rule, {n['T0']['references']} (median {n['T0']['median']}; fragments {n['T0']['fragments_exported']}); "
            f"216 WoS pairs medians {n['T0']['pairs_scopus_median']}/{n['T0']['pairs_wos_median']}; reference age and RPYS; top cited works "
            f"and sources; local citations {n['T4']['lcs_total']} links, historiograph {n['T4']['hist_nodes']} nodes; coupling "
            f"{n['T5']['nodes']} records, co-citation {n['T6']['nodes']} references; own-code work-key sensitivity. Gates G1-G6 PASS; "
            f"verifier {npass} PASS, {sum(1 for r in ver if r.get('verdict') == 'EXPLAINED')} EXPLAINED, 0 FAIL of {len(ver)}. "
            "Figures not viewed. CORRECTIONS unchanged.")
    row = {"phase_id": "phase_F13_3", "path": "outputs/dprg_revision_2026/phase_F13_3", "created_utc": L.now(), "status": "COMPLETE",
           "produced_numbers": "YES", "superseded_by": "",
           "safe_to_publish": "NO - data/ holds licensed reference texts (abstracts were not written)", "file_count": 0, "bytes": 0, "note": note}
    assert sum(L.shape_counts(json.dumps(row, ensure_ascii=False)).values()) == 0
    guess, rounds = (0, 0), 0
    while True:
        rounds += 1
        row["file_count"], row["bytes"] = guess
        L.jdump({"rows_not_written_in_this_order": prev + [row], "write_only_on": "the author's message 'реестр'"}, L.RUN_LOGS / "registry_rows_pending.json")
        (L.OUT / "phase_F13_3_report.md").write_bytes(f133_report.build(prev + [row], gates, ver).encode("utf-8"))
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
