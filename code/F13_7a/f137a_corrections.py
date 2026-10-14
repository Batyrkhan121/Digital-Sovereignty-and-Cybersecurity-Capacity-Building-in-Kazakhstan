"""Phase F13.7a - step 5: draft lines for CORRECTIONS.csv (tables/C1_corrections_draft.csv); CORRECTIONS.csv itself is not written. One
line for every number of main.qmd that F13.6a's map N1 marks 'changed' or 'remove'. A changed number's new value and source come from
N1 and are looked up in F13.6b's evidence index E1 (the draft's numbers with their sources): same phase, table, row key and column.
The line follows CORRECTIONS.csv's format (its header and first row were read for that: correction_id, date, superseded_file,
superseded_field, superseded_value, corrected_value, evidence_file, phase); correction ids are provisional (C558 onwards, after the 557
existing lines named in the brief) and are assigned when the lines are written in F13.6d. Every cell <= 30 words."""
import sys
sys.dont_write_bytecode = True

import json
import re
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f137a_lib as L

FORMAT = ["correction_id", "date", "superseded_file", "superseded_field", "superseded_value", "corrected_value", "evidence_file", "phase"]
N1_SRC = re.compile(r"phase_(F[\w]+) (\S+) \[(.*?)\] (\S+)")
E1_SRC = re.compile(r"(F[\w]+?)/(\S+) \[(.*?)\] (\S+)")


def key_n1(s):
    m = N1_SRC.match(s or "")
    return (m.group(1), m.group(2), m.group(3), m.group(4)) if m else None


def key_e1(s):
    m = E1_SRC.match(s or "")
    return (m.group(1), m.group(2), m.group(3), m.group(4)) if m else None


# F13.2b's institution and collaboration tables (thesaurus v1) are superseded by F13.2e's (thesaurus v3.1): N1 predates F13.2d / F13.2e
SUPERSEDED = {"T3a_kz_institutions": "T3a_v31_kz_institutions", "T3c_concentration": "T3c_v31_concentration",
              "T3d_kz_institution_pairs": "T3d_v31_kz_institution_pairs", "T2f_collaboration_by_year": "T2f_v31_collaboration_by_year",
              "T2f2_collaboration_by_period": "T2f2_v31_collaboration_by_period"}


def norm(v):
    return str(v or "").replace(",", "").strip()


def current_value(k):
    """For a source in a superseded F13.2b table: the same row and column in F13.2e's table (or None)."""
    if not k or k[0] != "F13_2b" or k[1] not in SUPERSEDED:
        return None
    tab = SUPERSEDED[k[1]]
    conds = dict(x.split("=", 1) for x in re.split(r",\s*(?=\w+=)", k[2]) if "=" in x)
    for r in L.read_csv(f"{L.DPR}phase_F13_2e/tables/{tab}.csv"):
        if all(str(r.get(a, "")).startswith(b.rstrip(".")) for a, b in conds.items()) and k[3] in r:
            return tab, r[k[3]]
    return tab, ""


def main():
    hdr = L.header_of(L.path(L.DPR + "CORRECTIONS.csv"))
    assert hdr == FORMAT, hdr
    n1 = L.read_csv(L.N1)
    e1 = L.read_csv(L.E1_INDEX)
    by_src, by_table = {}, {}
    for r in e1:
        k = key_e1(r["source"])
        if k:
            by_src.setdefault(k, []).append(r)
            by_table.setdefault(k[:2], []).append(r)
    rows = []
    sel = [r for r in n1 if r["status"] in ("changed", "remove")]
    for i, r in enumerate(sel):
        k = key_n1(r["source_new"])
        note = ""
        if r["status"] == "changed":
            new = r["value_new"]
            cur = current_value(k)
            if cur and cur[1] and norm(cur[1]) != norm(new):
                note = f"N1's value {new} is from F13.2b (thesaurus v1); F13.2e {cur[0]} gives {cur[1]}"
                new = cur[1]
            exact = [h for h in by_src.get(k, []) if norm(h["value_in_source"]) == norm(new)] if k else []
            loose = [h for h in by_table.get(k[:2], []) if norm(h["value_in_source"]) == norm(new)] if k else []
            hits = exact or loose
            in_draft = ("; ".join(h["id"] for h in hits[:4]) + ("" if exact else " (same table and value)")) if hits else \
                ("no new source in N1" if not k else "not in the draft's index (part 1)")
            ev = (f"{L.DPR}phase_{k[0]}/tables/{k[1]}.csv [{k[2]}] {k[3]}" if k else ("N1 " + r["id"] + ": " + L.words(r["note"], 12)))
            if cur and note:
                ev = f"{L.DPR}phase_F13_2e/tables/{cur[0]}.csv [{k[2]}] {k[3]}"
        else:
            in_draft = "removed (not expected in the draft)"
            new = "removed"
            ev = f"{L.DPR}phase_F13_6a/tables/N1_manuscript_numbers.csv ({r['id']})"
        field = f"{r['section']} (line {r['line']}): {r['what_it_denotes']}"
        rows.append({"draft_no": i + 1, "n1_id": r["id"], "n1_status": r["status"], "section": r["section"], "main_qmd_line": r["line"],
                     "old_value": r["number_as_written"], "n1_value_new": r["value_new"], "new_value": new, "source_of_new": L.words(r["source_new"], 25),
                     "in_draft_E1": in_draft, "note_for_F13_6d": note,
                     "correction_id": f"C{558 + i:03d}", "date": L.FIXED_DATE, "superseded_file": "main.qmd", "superseded_field": L.words(field, 26),
                     "superseded_value": r["number_as_written"],
                     "corrected_value": new if r["status"] == "changed" else "removed: " + L.words(r["note"], 24),
                     "evidence_file": L.words(ev, 28), "phase": "F13.6d (drafted in F13.7a)"})
    fields = ["draft_no", "n1_id", "n1_status", "section", "main_qmd_line", "old_value", "n1_value_new", "new_value", "source_of_new", "in_draft_E1",
              "note_for_F13_6d"] + FORMAT
    L.table("C1_corrections_draft", "C1 - draft lines for CORRECTIONS.csv (not written there); the last eight columns are the file's format",
            fields, rows, note="correction_id is provisional (C558 onwards, after the 557 existing lines); ids are assigned when F13.6d writes the "
            "lines. in_draft_E1: the F13.6b evidence-index rows that carry the new value from the same source.", md_rows=40)
    summ = [{"section": s, "changed": sum(1 for r in rows if r["section"] == s and r["n1_status"] == "changed"),
             "removed": sum(1 for r in rows if r["section"] == s and r["n1_status"] == "remove"),
             "lines": sum(1 for r in rows if r["section"] == s)} for s in sorted({r["section"] for r in rows})]
    summ.append({"section": "all", "changed": sum(x["changed"] for x in summ), "removed": sum(x["removed"] for x in summ), "lines": len(rows)})
    L.table("C1b_corrections_summary", "C1b - draft CORRECTIONS lines by section", ["section", "changed", "removed", "lines"], summ)
    changed = [r for r in rows if r["n1_status"] == "changed"]
    L.jdump({"lines": len(rows), "changed": len(changed), "removed": len(rows) - len(changed),
             "changed_found_in_E1": sum(1 for r in changed if r["in_draft_E1"].startswith("E-")),
             "changed_not_in_E1": {r["n1_id"]: r["in_draft_E1"] for r in changed if not r["in_draft_E1"].startswith("E-")},
             "updated_to_v31": {r["n1_id"]: [r["n1_value_new"], r["new_value"]] for r in rows if r["note_for_F13_6d"]},
             "n1_status_counts": dict(Counter(r["status"] for r in n1)), "corrections_header_read": hdr}, L.RUN_LOGS / "corrections.json")
    print(len(rows), "lines;", len(changed), "changed, of which in E1:", sum(1 for r in changed if r["in_draft_E1"].startswith("E-")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
