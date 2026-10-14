"""Phase F12.4 - the closing (--dry: gates and a draft report). No registry row is written: the brief holds it until the
author writes 'реестр'. The report carries the ready row, its file count and bytes found as the folder's fixed point; the row
is also kept, unwritten, in run_logs/registry_row_pending.json (part of the fixed point)."""
import sys
sys.dont_write_bytecode = True

import csv
import io
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f124_lib as L
import f124_gates
import f124_report


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
    draft = f124_report.build(None, f124_gates.run_all())
    gates = f124_gates.run_all(report=draft)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=f124_gates.FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(gates)
    (L.OUT / "phase_F12_4_checkpoint_assertions.csv").write_bytes(buf.getvalue().encode("utf-8"))
    ver = f124_report.rows("phase_F12_4_independent_verification.csv", L.OUT)
    # declared exception: C08b (plain four-block pattern) may FAIL only on DOI suffixes, and only when C08b3 (ORCID ranges
    # 0000/0009) passes; every other row must pass
    byid = {r.get("check_id"): r.get("verdict") for r in ver}
    ok_ver = bool(ver) and byid.get("C08b3") == "PASS" and all(r.get("verdict") == "PASS" for r in ver if r.get("check_id") != "C08b")
    ok_gates = all(g["verdict"] == "PASS" and g["falsifiability"] == "DEMONSTRATED" for g in gates)
    L.jdump({"run_utc": L.now(), "gates": {g["gate"]: g["verdict"] for g in gates}, "verifier_rows": len(ver), "verifier_all_pass": ok_ver},
            L.RUN_LOGS / ("final_dry.json" if dry else "final.json"))
    if dry:
        (L.OUT / "phase_F12_4_report.md").write_bytes(f124_report.build(None, gates).encode("utf-8"))
        print(json.dumps({"dry": True, "gates": [(g["gate"], g["verdict"], g["falsifiability"]) for g in gates], "verifier": ok_ver}))
        return 0
    assert ok_gates and ok_ver, (ok_gates, ok_ver)
    t1 = json.loads((L.OUT / "F12_4_numbers.json").read_bytes().decode("utf-8"))["T1"]
    note = (f"Coverage on the harmonised pair (H4Q title-only, same query, 2026-09-04): Scopus {t1['|S| Scopus H4Q title-only, 2003-2025']}, "
            f"OpenAlex {t1['|O| OpenAlex H4Q title-only, 2003-2025']} (ratio {t1['ratio |O| / |S| (harmonised)']} against June's 1.97); "
            f"intersection {t1['intersection']}, only Scopus {t1['only Scopus']}, only OpenAlex {t1['only OpenAlex']}, union {t1['union']}; "
            "composition of both one-sided sets; bridge to June (F12.1's 324 / 1512 / 608 reproduced); figure "
            "Fig_coverage_union_by_year (not viewed). Gates G1-G6 PASS; independent verifier "
            f"{sum(1 for r in ver if r.get('verdict') == 'PASS')}/{len(ver)}. No manuscript or package file touched; CORRECTIONS unchanged. "
            "Basis for the author's decision on the term 'Academic Iceberg Effect'.")
    row = {"phase_id": "phase_F12_4", "path": "outputs/dprg_revision_2026/phase_F12_4", "created_utc": L.now(), "status": "COMPLETE",
           "produced_numbers": "YES", "superseded_by": "",
           "safe_to_publish": "YES - record ids, titles, sources and counts; no author names, contacts or abstracts",
           "file_count": 0, "bytes": 0, "note": note}
    assert sum(L.shape_counts(json.dumps(row, ensure_ascii=False)).values()) == 0
    guess, rounds = (0, 0), 0
    while True:
        rounds += 1
        row["file_count"], row["bytes"] = guess
        L.jdump({"row_not_written": row, "write_only_on": "the author's message 'реестр'"}, L.RUN_LOGS / "registry_row_pending.json")
        (L.OUT / "phase_F12_4_report.md").write_bytes(f124_report.build(row, gates).encode("utf-8"))
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
