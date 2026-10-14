"""Phase F13.1 - the closing (--dry: gates and a draft report). No registry row is written: the brief holds the rows for
phase_F12_4 and phase_F13_1 until the author writes 'реестр'. The phase_F13_1 row's file count and bytes are the folder's fixed
point; both rows are kept, unwritten, in run_logs/registry_rows_pending.json."""
import sys
sys.dont_write_bytecode = True

import csv
import io
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f131_lib as L
import f131_gates
import f131_report

F124_PENDING = L.ROOT / "outputs" / "dprg_revision_2026" / "phase_F12_4" / "run_logs" / "registry_row_pending.json"


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
    draft = f131_report.build(None, f131_gates.run_all())
    gates = f131_gates.run_all(report=draft)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=f131_gates.FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(gates)
    (L.OUT / "phase_F13_1_checkpoint_assertions.csv").write_bytes(buf.getvalue().encode("utf-8"))
    ver = f131_report.rows(L.OUT / "phase_F13_1_independent_verification.csv")
    ok_ver = bool(ver) and all(r.get("verdict") == "PASS" for r in ver)
    ok_gates = all(g["verdict"] == "PASS" and g["falsifiability"] == "DEMONSTRATED" for g in gates)
    L.jdump({"run_utc": L.now(), "gates": {g["gate"]: g["verdict"] for g in gates}, "verifier_rows": len(ver), "verifier_all_pass": ok_ver},
            L.RUN_LOGS / ("final_dry.json" if dry else "final.json"))
    if dry:
        (L.OUT / "phase_F13_1_report.md").write_bytes(f131_report.build(None, gates).encode("utf-8"))
        print(json.dumps({"dry": True, "gates": [(g["gate"], g["verdict"], g["falsifiability"]) for g in gates], "verifier": ok_ver}))
        return 0
    assert ok_gates and ok_ver, (ok_gates, ok_ver)
    f124 = json.loads(F124_PENDING.read_bytes().decode("utf-8"))["row_not_written"]
    n = json.loads((L.OUT / "F13_1_numbers.json").read_bytes().decode("utf-8"))
    t3, m = n["T3a"], n["M"]
    note = (f"Acceptance of the full exports (Decision 40): Scopus E1 841 records / 841 EID (45 columns incl. References, 837 non-empty), control "
            f"copy E1b identical on 7 columns; WoS E2 231 / 231 UT (Full Record + Cited References). E1 vs September frame: 838 common, 3/3 swapped, "
            f"no field difference beyond capitalisation (1 source title). Scopus vs WoS: intersection {t3['intersection']}, only Scopus "
            f"{t3['only Scopus']}, only WoS {t3['only WoS']}; merged corpus M {m['rows']} works in data/ (abstracts, references; outside git; "
            "contact fields excluded). Topic-share table T5. Gates G1-G6 PASS; independent verifier "
            f"{sum(1 for r in ver if r.get('verdict') == 'PASS')}/{len(ver)}. CORRECTIONS unchanged.")
    row = {"phase_id": "phase_F13_1", "path": "outputs/dprg_revision_2026/phase_F13_1", "created_utc": L.now(), "status": "COMPLETE",
           "produced_numbers": "YES", "superseded_by": "", "safe_to_publish": "NO - data/ holds abstracts and reference lists (licensed)",
           "file_count": 0, "bytes": 0, "note": note}
    assert sum(L.shape_counts(json.dumps(row, ensure_ascii=False)).values()) == 0
    guess, rounds = (0, 0), 0
    while True:
        rounds += 1
        row["file_count"], row["bytes"] = guess
        L.jdump({"rows_not_written_in_this_order": [f124, row], "write_only_on": "the author's message 'реестр'"},
                L.RUN_LOGS / "registry_rows_pending.json")
        (L.OUT / "phase_F13_1_report.md").write_bytes(f131_report.build([f124, row], gates).encode("utf-8"))
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
