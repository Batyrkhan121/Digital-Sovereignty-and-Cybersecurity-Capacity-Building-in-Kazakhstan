"""Phase F13.4b - the registry step, NOT run in the phase: run only on the author's command 'реестр' in this session, after the rows
phase_F13_5 and phase_F13_4. Checks that phase_F13_4b is absent, that phase_F13_4 is present, and that the phase folder still has the
pending row's file count and bytes; then appends the row (the file's prefix kept). Console only. --check: checks, no write."""
import sys
sys.dont_write_bytecode = True

import csv
import io
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f134b_lib as L

REGISTRY = L.DPRG / "PHASE_REGISTRY.csv"


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


def append_row(path, row):
    before = path.read_bytes()
    text = before.decode("utf-8-sig")
    term = "\r\n" if "\r\n" in text.split("\n", 1)[0] + "\n" else "\n"
    header = next(csv.reader(io.StringIO(text.split(term, 1)[0])))
    assert list(row) == header, (list(row), header)
    n_before = len(list(csv.DictReader(io.StringIO(text, newline=""))))
    buf = io.StringIO(newline="")
    csv.DictWriter(buf, fieldnames=header, lineterminator=term).writerow(row)
    sep = b"" if before.endswith(term.encode()) else term.encode()
    path.write_bytes(before + sep + buf.getvalue().encode("utf-8"))
    after = path.read_bytes()
    rows_after = list(csv.DictReader(io.StringIO(after.decode("utf-8-sig"), newline="")))
    return {"prefix_kept": after.startswith(before), "rows_before": n_before, "rows_after": len(rows_after),
            "last_is_new": rows_after[-1]["phase_id"] == row["phase_id"]}


def main():
    row = L.jload(L.RUN_LOGS / "registry_rows_pending.json")["append_row"]
    ids = [r["phase_id"] for r in csv.DictReader(io.StringIO(REGISTRY.read_bytes().decode("utf-8-sig"), newline=""))]
    checks = {"phase_F13_4b_absent": "phase_F13_4b" not in ids, "phase_F13_4_present": "phase_F13_4" in ids,
              "folder_size_equals_row": list(folder_size(L.OUT)) == [row["file_count"], row["bytes"]]}
    print(json.dumps(checks, indent=1))
    if not all(checks.values()):
        print("STOP: a check failed; nothing written")
        return 1
    if "--check" in sys.argv:
        print("checks only; nothing written")
        return 0
    rec = append_row(REGISTRY, row)
    assert rec["prefix_kept"] and rec["rows_after"] == rec["rows_before"] + 1 and rec["last_is_new"], rec
    print(json.dumps({"appended": rec, "folder_still_equal": list(folder_size(L.OUT)) == [row["file_count"], row["bytes"]]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
