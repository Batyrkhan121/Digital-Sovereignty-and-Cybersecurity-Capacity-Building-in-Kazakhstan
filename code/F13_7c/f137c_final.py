"""Phase F13.7c - the closing (--dry: gates and a draft report). No registry row is written: the row phase_F13_7c is kept in
run_logs/registry_rows_pending.json (the main session writes the registry); its file count and bytes are the folder's fixed point."""
import sys
sys.dont_write_bytecode = True

import csv
import io
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f137c_lib as L
import f137c_gates
import f137c_report


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
    draft = f137c_report.build(None, f137c_gates.run_all())
    gates = f137c_gates.run_all(report=draft)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=f137c_gates.FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(gates)
    (L.OUT / "phase_F13_7c_checkpoint_assertions.csv").write_bytes(buf.getvalue().encode("utf-8"))
    ver = f137c_report.rows(L.OUT / "phase_F13_7c_independent_verification.csv")
    ok_ver = bool(ver) and all(r.get("verdict") in ("PASS", "INFO") for r in ver) and any(r.get("verdict") == "PASS" for r in ver)
    ok_gates = all(g["verdict"] == "PASS" and g["falsifiability"] == "DEMONSTRATED" for g in gates)
    L.jdump({"run_utc": L.now(), "gates": {g["gate"]: g["verdict"] for g in gates}, "verifier_rows": len(ver), "verifier_all_pass": ok_ver},
            L.RUN_LOGS / ("final_dry.json" if dry else "final.json"))
    if dry:
        (L.OUT / "phase_F13_7c_report.md").write_bytes(f137c_report.build(None, gates).encode("utf-8"))
        print(json.dumps({"dry": True, "gates": [(g["gate"], g["verdict"], g["falsifiability"]) for g in gates], "verifier": ok_ver}, indent=1))
        return 0
    assert ok_gates and ok_ver, (ok_gates, ok_ver)
    wl = L.jload(L.RUN_LOGS / "workbook.json")
    fl = L.jload(L.RUN_LOGS / "figure_set.json")
    note = (f"Supplementary workbook v2 (supplementary/Supplementary_tables.xlsx, {wl['sheets']} sheets, {wl['rows_total']:,} data rows): F13.7a's "
            f"sheets with v3.1 replacements, S13 citation structure by work key (F13.3b; cited works' first authors withheld where corpus authors), "
            f"S14 figure data, Phase log to F13.8, README with licence sentence; figure set figures/figure_1-{fl['figures']} (.tif, .png, byte copies, "
            f"300 dpi) with captions from the F13.6c draft. F13.7a programs reused unchanged (R19). Gates G1-G6 PASS; independent verifier "
            f"{sum(1 for r in ver if r.get('verdict') == 'PASS')} PASS, 0 FAIL. Manuscript untouched.")
    row = {"phase_id": "phase_F13_7c", "path": "outputs/dprg_revision_2026/phase_F13_7c", "created_utc": L.now(), "status": "COMPLETE",
           "produced_numbers": "NO", "superseded_by": "", "safe_to_publish": "YES", "file_count": 0, "bytes": 0, "note": note}
    assert sum(L.shape_counts(json.dumps(row, ensure_ascii=False)).values()) == 0
    guess, rounds = (0, 0), 0
    while True:
        rounds += 1
        row["file_count"], row["bytes"] = guess
        L.jdump({"rows_not_written": [row], "write_only_by": "the main session (brief: PHASE_REGISTRY.csv is not touched by this phase)"},
                L.RUN_LOGS / "registry_rows_pending.json")
        (L.OUT / "phase_F13_7c_report.md").write_bytes(f137c_report.build([row], gates).encode("utf-8"))
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
