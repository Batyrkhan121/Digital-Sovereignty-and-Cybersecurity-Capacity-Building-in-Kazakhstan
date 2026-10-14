"""Phase F13.5 - the registry step, NOT run in the phase: run only on the author's command 'реестр' in this session, after the
fork has written its rows phase_F12_4, phase_F13_1 and phase_F13_2. Reads run_logs/registry_rows_pending.json; checks that the
fork's three rows are present, that phase_F13_5 is absent, that phase_F12_3c's superseded_by is empty and that the phase folder
still has the pending row's file count and bytes; then fills superseded_by = phase_F13_5 in the row phase_F12_3c (only that line
is rewritten; every other line byte-equal) and appends the row (the file's prefix kept). Writes nothing inside the phase folder
(console only), so the folder's size stays the row's. --check: all checks, no write."""
import sys
sys.dont_write_bytecode = True

import csv
import io
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f135_lib as L

REGISTRY = L.DPRG / "PHASE_REGISTRY.csv"
FORK_ROWS = ["phase_F12_4", "phase_F13_1", "phase_F13_2"]


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


def registry_rows():
    text = REGISTRY.read_bytes().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text, newline="")))


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


def set_superseded(path, phase_id, by):
    before = path.read_bytes()
    text = before.decode("utf-8-sig")
    term = "\r\n" if "\r\n" in text.split("\n", 1)[0] + "\n" else "\n"
    header = next(csv.reader(io.StringIO(text.split(term, 1)[0])))
    old_rows = list(csv.DictReader(io.StringIO(text, newline="")))
    hits = [r for r in old_rows if r["phase_id"] == phase_id]
    assert len(hits) == 1 and hits[0]["superseded_by"] == "", hits
    raw = before.split(term.encode())
    starts = [n for n, ln in enumerate(raw) if ln.startswith((phase_id + ",").encode())]
    assert len(starts) == 1, starts
    n = starts[0]
    parsed = next(csv.reader(io.StringIO(raw[n].decode("utf-8"))))
    assert dict(zip(header, parsed)) == hits[0], "the line does not parse to the row"
    buf = io.StringIO(newline="")
    csv.DictWriter(buf, fieldnames=header, lineterminator="").writerow(dict(hits[0], superseded_by=by))
    raw[n] = buf.getvalue().encode("utf-8")
    after = term.encode().join(raw)
    path.write_bytes(after)
    new_rows = list(csv.DictReader(io.StringIO(path.read_bytes().decode("utf-8-sig"), newline="")))
    changed = [(r1["phase_id"], k) for r1, r2 in zip(old_rows, new_rows) for k in header if r1[k] != r2[k]]
    other_lines_equal = all(before.split(term.encode())[m] == after.split(term.encode())[m] for m in range(len(raw)) if m != n)
    return {"row": phase_id, "changed_cells": changed, "rows_equal_in_number": len(old_rows) == len(new_rows),
            "other_lines_bytes_equal": other_lines_equal}


def main():
    pend = L.jload(L.RUN_LOGS / "registry_rows_pending.json")
    row = pend["append_row"]
    ids = [r["phase_id"] for r in registry_rows()]
    checks = {"fork_rows_present": {f: f in ids for f in FORK_ROWS}, "phase_F13_5_absent": "phase_F13_5" not in ids,
              "F12_3c_superseded_empty": [r["superseded_by"] for r in registry_rows() if r["phase_id"] == "phase_F12_3c"] == [""],
              "folder_size_equals_row": list(folder_size(L.OUT)) == [row["file_count"], row["bytes"]]}
    print(json.dumps(checks, indent=1))
    ok = all(checks["fork_rows_present"].values()) and checks["phase_F13_5_absent"] and checks["F12_3c_superseded_empty"] and checks["folder_size_equals_row"]
    if not ok:
        print("STOP: a check failed; nothing written")
        return 1
    if "--check" in sys.argv:
        print("checks only; nothing written")
        return 0
    sup = set_superseded(REGISTRY, "phase_F12_3c", "phase_F13_5")
    assert sup["changed_cells"] == [("phase_F12_3c", "superseded_by")] and sup["rows_equal_in_number"] and sup["other_lines_bytes_equal"], sup
    rec = append_row(REGISTRY, row)
    assert rec["prefix_kept"] and rec["rows_after"] == rec["rows_before"] + 1 and rec["last_is_new"], rec
    print(json.dumps({"superseded": sup, "appended": rec, "folder_still_equal": list(folder_size(L.OUT)) == [row["file_count"], row["bytes"]]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
