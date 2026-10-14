"""Phase F13.4 - the closing (copied from F13.5's closing): gates on the final outputs including the report; no registry write (the
row is written on the author's command 'реестр'); the pending row goes to run_logs/registry_rows_pending.json and its file count and
bytes are the folder's fixed point. --dry: gates and the report without the pending row."""
import sys
sys.dont_write_bytecode = True

import csv
import io
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f134_lib as L
import f134_gates
import f134_report

PHASE_ID = "phase_F13_4"
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


def write_gates(gates):
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=f134_gates.FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(gates)
    (L.OUT / "phase_F13_4_checkpoint_assertions.csv").write_bytes(buf.getvalue().encode("utf-8"))


def main():
    dry = "--dry" in sys.argv
    draft = f134_report.build(None, f134_gates.run_all())
    gates = f134_gates.run_all(report=draft)
    write_gates(gates)
    ver = f134_report.rows("phase_F13_4_independent_verification.csv", L.OUT)
    ok_ver = bool(ver) and all(r.get("verdict") == "PASS" for r in ver)
    ok_gates = all(g["verdict"] == "PASS" and g["falsifiability"] == "DEMONSTRATED" for g in gates)
    L.jdump({"run_utc": L.now(), "gates": {g["gate"]: g["verdict"] for g in gates}, "verifier_rows": len(ver), "verifier_all_pass": ok_ver},
            L.RUN_LOGS / ("final_dry.json" if dry else "final.json"))
    if dry:
        (L.OUT / "phase_F13_4_report.md").write_bytes(f134_report.build(None, gates).encode("utf-8"))
        print(json.dumps({"dry": True, "gates": [(g["gate"], g["verdict"], g["falsifiability"]) for g in gates], "verifier": ok_ver}))
        return 0
    assert ok_gates, "a gate failed"
    assert ok_ver, "the verifier did not pass every check"
    num = L.jload(L.OUT / "F13_4_numbers.json")
    t2b = {r["window"]: r for r in num["T2b"]}
    fit = num["T1c"][0]
    note = (f"Replaces F13.1 T5. Growth and normalised activity from the Scopus year series of 2026-10-13: E1 {num['totals']['KZ']} "
            f"records; log-linear growth {fit['annual_growth_pct']} % a year over {fit['window']} (doubling {fit['doubling_time_years']} years, R2 "
            f"{fit['r_squared']}); activity index 2003-2025 {t2b['2003-2025']['activity_index']} (bootstrap {t2b['2003-2025']['ci95_low']}-"
            f"{t2b['2003-2025']['ci95_high']}), year-standardised {t2b['2003-2025']['ai_year_standardised']}; by period "
            + ", ".join(t2b[p]["activity_index"] for p, _, _ in L.PERIODS)
            + "; comparators UZ, AZ, BY, KG by topic counts and growth (no all-output series for them); figure Fig_normalised_growth "
            f"(pdf/png/tif, not viewed). Gates G1-G6 PASS; independent verifier {sum(1 for r in ver if r.get('verdict') == 'PASS')}/{len(ver)}. "
            "No manuscript or package file touched; CORRECTIONS unchanged. Numbers for the revision, not yet in the article.")
    row = {"phase_id": PHASE_ID, "path": "outputs/dprg_revision_2026/phase_F13_4", "created_utc": L.now(), "status": "COMPLETE",
           "produced_numbers": "YES", "superseded_by": "", "safe_to_publish": "YES - aggregates only", "file_count": 0, "bytes": 0, "note": note}
    assert list(row) == REGISTRY_FIELDS
    assert sum(L.shape_counts(json.dumps(row, ensure_ascii=False)).values()) == 0
    guess, rounds = (0, 0), 0
    while True:
        rounds += 1
        row["file_count"], row["bytes"] = guess
        (L.OUT / "phase_F13_4_report.md").write_bytes(f134_report.build(row, gates).encode("utf-8"))
        L.jdump({"phase": PHASE_ID, "command": "реестр (the author's word in this session)", "append_row": row, "set_superseded_by": [],
                 "program": "programs/f134_registry.py (checks, then appends the row)"}, PENDING)
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
