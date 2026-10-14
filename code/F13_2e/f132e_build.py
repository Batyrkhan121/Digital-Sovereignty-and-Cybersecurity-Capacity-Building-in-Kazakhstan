"""Phase F13.2e - step 2: the recount with thesaurus v3.1 by the same function as F13.2d (f132d_build.tables_for, read-only), after a check
that the same function with v3 reproduces F13.2d's T3a_v3 and T3c_v3 exactly. T2g by F13.2b's rule (n_authors = ';'-separated names of
Authors, counted; mean to 2 decimals, median, maximum; f132b_lib's helpers). Deltas: D1 against F13.2d's v3 tables (every changed cell),
T2h records whose collaboration type changed (v3 -> v3.1), T2g against v3 and against F13.2b. Deterministic."""
import sys
sys.dont_write_bytecode = True

import json
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132e_lib as L

P = [p for p, _, _ in L.PERIODS]
BL = L.BL


def t2g_of(R, lab):
    rows = []
    for c in L.COLLAB:
        xs = [r["n_authors"] for r in R if lab[r["eid"]][1] == c]
        rows.append({"collaboration": c, "records": len(xs), "authors_mean": BL.mean(xs), "authors_median": BL.median(xs), "authors_max": max(xs) if xs else ""})
    xs = [r["n_authors"] for r in R]
    rows.append({"collaboration": "all", "records": len(xs), "authors_mean": BL.mean(xs), "authors_median": BL.median(xs), "authors_max": max(xs)})
    return rows


def main():
    L.install_r17_guard()
    ncols, R = L.records()
    num = {"records": len(R), "columns_in_E1": ncols, "authors_counted": sum(r["n_authors"] for r in R)}
    v3 = L.read_csv(L.IN_V3["thesaurus"])
    v31 = L.read_csv_path(L.TABLES / "institutions_thesaurus_v31.csv")
    old = {k: L.read_csv(p) for k, p in L.IN_V3.items() if k not in ("thesaurus", "T4")}
    a3, c3, d3, f3, ff3, lab3, inst3 = L.DB.tables_for(R, v3)
    v3_cols = list(old["T3a"][0].keys())
    repro = ([{k: str(r[k]) for k in v3_cols if k in r} for r in a3] == [{k: v for k, v in r.items() if k in a3[0]} for r in old["T3a"]]
             and [str(v) for v in c3.values()] == [r["value"] for r in old["T3c"]])
    num["v3_reproduced_exactly"] = repro
    assert repro, "the reused tables_for does not reproduce F13.2d's T3a_v3 / T3c_v3"
    a31, c31, d31, f31, ff31, lab31, inst31 = L.DB.tables_for(R, v31)
    r3 = {r["institution"]: r for r in old["T3a"]}
    for r in a31:
        o = r3.get(r["institution"])
        r["records_v3"] = o["records"] if o else ""
        r["delta"] = r["records"] - int(o["records"]) if o else ""
        r["rank_v3"] = o["rank"] if o else ""
    f3a = ["rank", "institution", "type", "records", "share_of_841_pct"] + P + ["international", "share_international_pct", "records_v3", "delta", "rank_v3"]
    L.table("T3a_v31_kz_institutions", "T3a_v31 - Kazakhstan institutions after thesaurus v3.1 (top 30; all in the CSV); records = records_v31, rank = rank_v31",
            f3a, a31, md_rows=30)
    t3c = [{"measure": m, "value": v, "value_v3": next(r["value"] for r in old["T3c"] if r["measure"] == m)} for m, v in c31.items()]
    L.table("T3c_v31_concentration", "T3c_v31 - concentration of Kazakhstan institutions (thesaurus v3.1; 'thesaurus rows' = active rows)",
            ["measure", "value", "value_v3"], t3c)
    L.table("T3d_v31_kz_institution_pairs", "T3d_v31 - pairs of Kazakhstan institutions in one record (top 15; all in the CSV)",
            ["institution_a", "institution_b", "records"], d31, md_rows=15)
    fy = ["year"] + L.COLLAB + ["total"] + [f"{c} %" for c in L.COLLAB]
    L.table("T2f_v31_collaboration_by_year", "T2f_v31 - collaboration type by year (thesaurus v3.1)", fy, f31)
    o2 = {r["period"]: r for r in old["T2f2"]}
    for r in ff31:
        for c in L.COLLAB:
            r[f"{c} delta"] = r[c] - int(o2[r["period"]][c])
    L.table("T2f2_v31_collaboration_by_period", "T2f2_v31 - collaboration type by period (thesaurus v3.1), with the change against v3",
            ["period"] + L.COLLAB + ["total"] + [f"{c} %" for c in L.COLLAB] + [f"{c} delta" for c in L.COLLAB], ff31)
    g31, g3 = t2g_of(R, lab31), t2g_of(R, lab3)
    gb = {r["collaboration"]: r for r in L.read_csv(L.IN_T2G)}
    g3m = {r["collaboration"]: r for r in g3}
    for r in g31:
        c = r["collaboration"]
        r.update({"records_v3": g3m[c]["records"], "authors_mean_v3": g3m[c]["authors_mean"], "authors_median_v3": g3m[c]["authors_median"],
                  "records_F13_2b": gb[c]["records"], "authors_mean_F13_2b": gb[c]["authors_mean"], "authors_median_F13_2b": gb[c]["authors_median"]})
    L.table("T2g_v31_authors_by_collaboration", "T2g_v31 - authors per record by collaboration type (F13.2b's rule), with v3 and F13.2b (v1)",
            ["collaboration", "records", "authors_mean", "authors_median", "authors_max", "records_v3", "authors_mean_v3", "authors_median_v3",
             "records_F13_2b", "authors_mean_F13_2b", "authors_median_F13_2b"], g31,
            note="Authors: the number of ';'-separated names in E1's Authors column (only the count is read). F13.2b's T2g used thesaurus v1.")
    tr = Counter((lab3[e][1], lab31[e][1]) for e in lab3)
    t2h = [{"type_v3": a, "type_v31": b, "records": n} for (a, b), n in sorted(tr.items())]
    L.table("T2h_collaboration_transitions", "T2h - collaboration type of each record, v3 against v3.1", ["type_v3", "type_v31", "records"], t2h)
    d1 = []
    specs = [("T3a", a31, "institution", f3a[:10]), ("T3c", [{"measure": m, "value": v} for m, v in c31.items()], "measure", ["measure", "value"]),
             ("T3d", d31, ("institution_a", "institution_b"), ["institution_a", "institution_b", "records"]),
             ("T2f", f31, "year", fy), ("T2f2", ff31, "period", ["period"] + L.COLLAB + ["total"] + [f"{c} %" for c in L.COLLAB])]
    for name, new, key, cols in specs:
        kf = (lambda r: " + ".join(str(r[k]) for k in key)) if isinstance(key, tuple) else (lambda r: str(r[key]))
        om = {kf(r): r for r in old[name]}
        nm = {kf(r): {k: str(r[k]) for k in cols} for r in new}
        for k in sorted(set(om) | set(nm)):
            o, n_ = om.get(k), nm.get(k)
            if o is None or n_ is None:
                d1.append({"table": name, "row": k, "field": "(row)", "old": "present" if o else "absent", "new": "present" if n_ else "absent"})
                continue
            for f in cols:
                if f in o and o[f] != n_[f]:
                    d1.append({"table": name, "row": k, "field": f, "old": o[f], "new": n_[f]})
    L.table("D1_deltas_v3_v31", "D1 - every cell that changed against F13.2d's v3 tables (T3a, T3c, T3d, T2f, T2f2)", ["table", "row", "field", "old", "new"], d1,
            note="Rows of T3a 'absent' in v3.1 are the names merged by the professor's list.", md_rows=80)
    touched = sorted({r["canonical"] for r in L.read_csv_path(L.TABLES / "institutions_thesaurus_v31.csv") if r["version"] == "v3.1"})
    num.update({"institutions_v3": len(inst3), "institutions_v31": len(inst31), "links_v3": sum(len(v) for v in inst3.values()),
                "links_v31": sum(len(v) for v in inst31.values()), "collab_v3": {c: ff3[-1][c] for c in L.COLLAB},
                "collab_v31": {c: ff31[-1][c] for c in L.COLLAB}, "transitions": {f"{a} -> {b}": n for (a, b), n in sorted(tr.items()) if a != b},
                "d1_cells": len(d1), "touched": {n: [len(inst3.get(n, ())), len(inst31.get(n, ()))] for n in touched},
                "top10_v31": [(r["institution"], r["records"], r["records_v3"], r["rank_v3"]) for r in a31[:10]],
                "top10_rank_moves": [r["institution"] for r in a31[:10] if r["rank_v3"] and int(r["rank_v3"]) != int(r["rank"])],
                "unresolved_address_line": "68/74 Abay Ave." in inst31})
    L.jdump(num, L.OUT / "F13_2e_numbers.json")
    print(json.dumps(num, ensure_ascii=True, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
