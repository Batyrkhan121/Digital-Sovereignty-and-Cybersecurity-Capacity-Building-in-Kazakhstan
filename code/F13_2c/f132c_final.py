"""Phase F13.2c - the closing (--dry: gates and a draft report). No registry row is written: the row phase_F13_2c waits for the
author's 'реестр'; its file count and bytes are the folder's fixed point; it is kept, unwritten, in run_logs/registry_rows_pending.json."""
import sys
sys.dont_write_bytecode = True

import csv
import io
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132c_lib as L
import f132c_gates
import f132c_report


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
    draft = f132c_report.build(None, f132c_gates.run_all())
    gates = f132c_gates.run_all(report=draft)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=f132c_gates.FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(gates)
    (L.OUT / "phase_F13_2c_checkpoint_assertions.csv").write_bytes(buf.getvalue().encode("utf-8"))
    ver = f132c_report.rows(L.OUT / "phase_F13_2c_independent_verification.csv")
    ok_ver = bool(ver) and all(r.get("verdict") == "PASS" for r in ver)
    ok_gates = all(g["verdict"] == "PASS" and g["falsifiability"] == "DEMONSTRATED" for g in gates)
    L.jdump({"run_utc": L.now(), "gates": {g["gate"]: g["verdict"] for g in gates}, "verifier_rows": len(ver), "verifier_all_pass": ok_ver},
            L.RUN_LOGS / ("final_dry.json" if dry else "final.json"))
    if dry:
        (L.OUT / "phase_F13_2c_report.md").write_bytes(f132c_report.build(None, gates).encode("utf-8"))
        print(json.dumps({"dry": True, "gates": [(g["gate"], g["verdict"], g["falsifiability"]) for g in gates], "verifier": ok_ver}, indent=1))
        return 0
    assert ok_gates and ok_ver, (ok_gates, ok_ver)
    n = json.loads((L.OUT / "F13_2c_numbers.json").read_bytes().decode("utf-8"))
    cl = n["T2"]["classes"]
    ks = [k for k in cl if k != "all international"]
    note = (f"International records by author on E1 (Authors with affiliations, counts only): of {n['T2']['base']} international records "
            f"{cl[ks[0]]} co-authorship with an author based only abroad, {cl[ks[1]]} dual affiliations only, {cl[ks[2]]} without a Kazakhstan "
            f"author; first author foreign-only in {n['T2']['first_author_517']['foreign only']}; partners other than Ukraine "
            f"{n['T2']['other_than_ukraine']['affiliations']}. Thesaurus v2 (decision 45: Energo University = AUPET, {n['T3']['aupet_records']} records). "
            "Supersedes F13.2b T3a/T3c/T3d/T2f/T2f2. Gates G1-G6 PASS; independent verifier "
            f"{sum(1 for r in ver if r.get('verdict') == 'PASS')}/{len(ver)}. No names.")
    row = {"phase_id": "phase_F13_2c", "path": "outputs/dprg_revision_2026/phase_F13_2c", "created_utc": L.now(), "status": "COMPLETE",
           "produced_numbers": "YES", "superseded_by": "", "safe_to_publish": "YES - counts only", "file_count": 0, "bytes": 0, "note": note}
    assert sum(L.shape_counts(json.dumps(row, ensure_ascii=False)).values()) == 0
    guess, rounds = (0, 0), 0
    while True:
        rounds += 1
        row["file_count"], row["bytes"] = guess
        L.jdump({"rows_not_written": [row], "write_only_on": "the author's message 'реестр'",
                 "supersedes": "phase_F13_2b tables T3a, T3c, T3d, T2f, T2f2"}, L.RUN_LOGS / "registry_rows_pending.json")
        (L.OUT / "phase_F13_2c_report.md").write_bytes(f132c_report.build([row], gates).encode("utf-8"))
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
