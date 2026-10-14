"""Phase F13.5 - the closing (copied from F12.3c; changed: no registry write - the brief defers the row until the author's command
'реестр' after the fork's rows). Gates on the final outputs including the report; the pending registry row and the superseded_by
instruction go to run_logs/registry_rows_pending.json; the row's file count and bytes are the folder's fixed point (the report and
the pending file are rewritten until the measured size equals the row). --dry: gates and the report without the pending row."""
import sys
sys.dont_write_bytecode = True

import csv
import io
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f135_lib as L
import f135_gates
import f135_report

PHASE_ID = "phase_F13_5"
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
    w = csv.DictWriter(buf, fieldnames=f135_gates.FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(gates)
    (L.OUT / "phase_F13_5_checkpoint_assertions.csv").write_bytes(buf.getvalue().encode("utf-8"))


def pending_doc(row):
    return {"phase": PHASE_ID, "command": "реестр (the author's word in this session)",
            "order": "after the fork has written its rows phase_F12_4, phase_F13_1 and phase_F13_2",
            "append_row": row, "set_superseded_by": [{"phase_id": "phase_F12_3c", "superseded_by": PHASE_ID}],
            "program": "programs/f135_registry.py (checks the fork's rows, the folder's size, then writes the cell and the row)"}


def main():
    dry = "--dry" in sys.argv
    draft = f135_report.build(None, f135_gates.run_all())
    gates = f135_gates.run_all(report=draft)
    write_gates(gates)
    ver = f135_report.rows("phase_F13_5_independent_verification.csv", L.OUT)
    ok_ver = bool(ver) and all(r.get("verdict") == "PASS" for r in ver)
    ok_gates = all(g["verdict"] == "PASS" and g["falsifiability"] == "DEMONSTRATED" for g in gates)
    L.jdump({"run_utc": L.now(), "gates": {g["gate"]: g["verdict"] for g in gates}, "verifier_rows": len(ver), "verifier_all_pass": ok_ver},
            L.RUN_LOGS / ("final_dry.json" if dry else "final.json"))
    if dry:
        (L.OUT / "phase_F13_5_report.md").write_bytes(f135_report.build(None, gates).encode("utf-8"))
        print(json.dumps({"dry": True, "gates": [(g["gate"], g["verdict"], g["falsifiability"]) for g in gates], "verifier": ok_ver}))
        return 0
    assert ok_gates, "a gate failed"
    assert ok_ver, "the verifier did not pass every check"
    num = L.jload(L.OUT / "F13_5_numbers.json")
    st = L.jload(L.RUN_LOGS / "thesaurus_v4_status.json")
    a, i = num["author"], num["index"]
    note = (f"Replaces phase_F12_3c for publication: co-word map on the new frame E1 (full Scopus export of 2026-10-13, {num['records_E1']} "
            f"records; decision 41) with thesaurus v4 ({num['thesaurus_rows']} rows = 579 v3 + {st['rows_new']} new: mid-string brackets, "
            "abbreviations inside keywords, final-bracket forms new to the frame with an abbreviation test, the tail; "
            f"{len(st['retargeted_v3_rows'])} v3 rows retargeted); F12.3's parameters unchanged: author keywords {a['records_with_keywords']} "
            f"records, {a['nodes']} nodes >= 5 records, {a['edges']} edges, {a['clusters']} clusters (modularity {a['modularity']}); index "
            f"keywords {i['records_with_keywords']} records; run E1 x v3 in tables/v3_on_E1 separates the frame effect (D0) from the "
            "thesaurus effect (D1); stability S1 (Rand) and S2 (Louvain, 20 seeds); residual scan R1 zero apart from declared keeps; figure "
            "Fig_coword_author_keywords (pdf/png/tif, not viewed). Gates G1-G8 PASS; independent verifier "
            f"{sum(1 for r in ver if r.get('verdict') == 'PASS')}/{len(ver)}. No manuscript or package file touched; CORRECTIONS unchanged. "
            "Numbers for section 3.3, not yet in the article.")
    row = {"phase_id": PHASE_ID, "path": "outputs/dprg_revision_2026/phase_F13_5", "created_utc": L.now(), "status": "COMPLETE",
           "produced_numbers": "YES", "superseded_by": "",
           "safe_to_publish": "YES - keyword aggregates and a figure; no contacts, no abstracts", "file_count": 0, "bytes": 0, "note": note}
    assert list(row) == REGISTRY_FIELDS
    assert sum(L.shape_counts(json.dumps(row, ensure_ascii=False)).values()) == 0
    guess, rounds = (0, 0), 0
    while True:
        rounds += 1
        row["file_count"], row["bytes"] = guess
        (L.OUT / "phase_F13_5_report.md").write_bytes(f135_report.build(row, gates).encode("utf-8"))
        L.jdump(pending_doc(row), PENDING)
        measured = folder_size(L.OUT)
        if measured == guess:
            break
        assert rounds < 10
        guess = measured
    print(json.dumps({"fixed_point": folder_size(L.OUT) == guess, "files_bytes": guess, "rounds": rounds, "registry_written": False,
                      "pending": str(PENDING.relative_to(L.OUT)), "gates": [(g["gate"], g["verdict"]) for g in gates]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
