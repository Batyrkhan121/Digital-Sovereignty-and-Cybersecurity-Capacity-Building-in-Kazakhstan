"""Phase F13.2d - steps 3-4: the institution and collaboration tables recomputed with thesaurus v3 by F13.2c's own labelling
(f132c_build.labels, imported read-only: Kazakhstan lines of Affiliations, institution part by F13.2b's priority, norm_kz key, thesaurus
variant -> canonical, else the canonical's own key, else the most common written form), deltas against F13.2c's v2 tables (D1, every
changed cell), the records whose collaboration type changed, and the residual scan T4. Before v3, the same code is run with v2 and must
reproduce F13.2c's T3a_v2 exactly (a check, recorded in F13_2d_numbers.json). Deterministic; no timestamp in tables/."""
import sys
sys.dont_write_bytecode = True

import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132d_lib as L
import f132c_build as B  # F13.2c's programs, read-only (on sys.path through f132d_lib)
import f132d_thesaurus as TH

C = L.C
P = [p for p, _, _ in L.PERIODS]


def load():
    ncols, recs = L.load_e1()
    cset = L.countries()
    R = []
    for r in recs:
        lines = [C.parse_line(x) for x in C.aff_lines(r["affiliations"])]
        A = {p["country_part"] for p in lines if p["country_part"] in cset}
        y = C.year_of(r["year"])
        R.append({"eid": r["eid"], "year": y, "period": C.period_of(y), "lines": lines, "A": A, "foreign_A": sorted(A - {L.KZ})})
    return ncols, R


def tables_for(R, rows):
    """T3a, T3c (dict), T3d, T2f, T2f2 and the per-record labels, as F13.2c's step 3 computes them."""
    B.labels(R, rows)
    kz_rec = defaultdict(set)
    for r in R:
        for p in r["lines"]:
            if p["country_part"] == L.KZ:
                kz_rec[C.norm_kz(p["institution"])].add(r["eid"])
    N = len(R)
    inst = defaultdict(set)
    for r in R:
        for i in r["kz_insts"]:
            inst[i].add(r["eid"])
    rank = sorted(inst.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    intl = {r["eid"] for r in R if r["foreign_A"]}
    per = {r["eid"]: r["period"] for r in R}
    t3a = []
    for i, (name, es) in enumerate(rank, 1):
        bp = Counter(per[e] for e in es)
        k = len(es & intl)
        t3a.append({"rank": i, "institution": name, "type": C.inst_type(name), "records": len(es), "share_of_841_pct": L.pct(len(es), N),
                    **{p: bp.get(p, 0) for p in P}, "international": k, "share_international_pct": L.pct(k, len(es))})
    links = sum(len(es) for es in inst.values())
    t5, t10 = [n for n, _ in rank[:5]], [n for n, _ in rank[:10]]
    rec5, rec10 = len(set().union(*(inst[n] for n in t5))), len(set().union(*(inst[n] for n in t10)))
    calc = {"Kazakhstan institution variants before the thesaurus (normalised keys)": len(kz_rec),
            "variants in two or more records (all decided in the thesaurus)": sum(1 for v in kz_rec.values() if len(v) >= 2),
            "thesaurus rows": sum(1 for r in rows if r["status"] == "active"),
            "distinct Kazakhstan institutions after the thesaurus": len(inst),
            "institutions with one record": sum(1 for es in inst.values() if len(es) == 1),
            "institution-record links (full counting)": links,
            "share of links held by the top 5 (%)": L.pct(sum(len(inst[n]) for n in t5), links),
            "share of links held by the top 10 (%)": L.pct(sum(len(inst[n]) for n in t10), links),
            "records with at least one top-5 institution": rec5, "share of the 841 records with a top-5 institution (%)": L.pct(rec5, N),
            "records with at least one top-10 institution": rec10, "share of the 841 records with a top-10 institution (%)": L.pct(rec10, N)}
    ip = Counter(pr for r in R for pr in combinations(r["kz_insts"], 2))
    t3d = [{"institution_a": a, "institution_b": b, "records": n} for (a, b), n in sorted(ip.items(), key=lambda kv: (-kv[1], kv[0]))]
    cy = {y: Counter() for y in L.YEARS}
    for r in R:
        cy[r["year"]][r["collab"]] += 1
    t2f = []
    for y in L.YEARS:
        tot = sum(cy[y].values())
        t2f.append({"year": y, **{c: cy[y].get(c, 0) for c in L.COLLAB}, "total": tot, **{f"{c} %": L.pct(cy[y].get(c, 0), tot) for c in L.COLLAB}})
    t2f2 = []
    for p in P + ["2003-2025"]:
        g = [r for r in R if p == "2003-2025" or r["period"] == p]
        cc = Counter(r["collab"] for r in g)
        t2f2.append({"period": p, **{c: cc.get(c, 0) for c in L.COLLAB}, "total": len(g), **{f"{c} %": L.pct(cc.get(c, 0), len(g)) for c in L.COLLAB}})
    labels = {r["eid"]: (tuple(r["kz_insts"]), r["collab"]) for r in R}
    return t3a, calc, t3d, t2f, t2f2, labels, inst


def main():
    L.install_r17_guard()
    ncols, R = load()
    num = {"records": len(R), "columns_in_E1": ncols}
    v2 = L.read_csv(L.IN_THES)
    v3 = L.read_csv_path(L.TABLES / "institutions_thesaurus_v3.csv")
    a2, c2, d2, f2, ff2, lab2, inst2 = tables_for(R, v2)
    old = {k: L.read_csv(p) for k, p in L.IN_V2.items()}
    repro = [{k: str(v) for k, v in r.items()} for r in a2] == old["T3a"] and [{"measure": m, "value": str(v)} for m, v in c2.items()] == old["T3c"]
    num["v2_reproduced_exactly"] = repro
    assert repro, "the reused labelling does not reproduce F13.2c's T3a_v2 / T3c_v2"
    a3, c3, d3, f3, ff3, lab3, inst3 = tables_for(R, v3)
    assert [r["measure"] for r in old["T3c"]] == list(c3), "T3c labels differ from v2"
    r2 = {r["institution"]: r for r in old["T3a"]}
    for r in a3:
        o = r2.get(r["institution"])
        r["records_v2"] = o["records"] if o else ""
        r["delta"] = r["records"] - int(o["records"]) if o else ""
        r["rank_v2"] = o["rank"] if o else ""
    f3a = ["rank", "institution", "type", "records", "share_of_841_pct"] + P + ["international", "share_international_pct", "records_v2", "delta", "rank_v2"]
    L.table("T3a_v3_kz_institutions", "T3a_v3 - Kazakhstan institutions after thesaurus v3 (top 30; all in the CSV); records = records_v3, rank = rank_v3",
            f3a, a3, md_rows=30)
    t3c = [{"measure": m, "value": v, "value_v2": next(r["value"] for r in old["T3c"] if r["measure"] == m)} for m, v in c3.items()]
    L.table("T3c_v3_concentration", "T3c_v3 - concentration of Kazakhstan institutions (thesaurus v3; 'thesaurus rows' = active rows)",
            ["measure", "value", "value_v2"], t3c)
    L.table("T3d_v3_kz_institution_pairs", "T3d_v3 - pairs of Kazakhstan institutions in one record (top 15; all in the CSV)",
            ["institution_a", "institution_b", "records"], d3, md_rows=15)
    fy = ["year"] + L.COLLAB + ["total"] + [f"{c} %" for c in L.COLLAB]
    L.table("T2f_v3_collaboration_by_year", "T2f_v3 - collaboration type by year (thesaurus v3)", fy, f3)
    o2 = {r["period"]: r for r in old["T2f2"]}
    for r in ff3:
        for c in L.COLLAB:
            r[f"{c} delta"] = r[c] - int(o2[r["period"]][c])
    L.table("T2f2_v3_collaboration_by_period", "T2f2_v3 - collaboration type by period (thesaurus v3), with the change against v2",
            ["period"] + L.COLLAB + ["total"] + [f"{c} %" for c in L.COLLAB] + [f"{c} delta" for c in L.COLLAB], ff3)
    # records that changed collaboration type
    tr = Counter((lab2[e][1], lab3[e][1]) for e in lab2)
    t2g = [{"type_v2": a, "type_v3": b, "records": n} for (a, b), n in sorted(tr.items())]
    L.table("T2g_collaboration_transitions", "T2g - collaboration type of each record, v2 against v3", ["type_v2", "type_v3", "records"], t2g)
    # D1: every changed cell
    d1 = []
    specs = [("T3a", a3, "institution", f3a[:10]), ("T3c", [{"measure": m, "value": v} for m, v in c3.items()], "measure", ["measure", "value"]),
             ("T3d", d3, ("institution_a", "institution_b"), ["institution_a", "institution_b", "records"]),
             ("T2f", f3, "year", fy), ("T2f2", ff3, "period", ["period"] + L.COLLAB + ["total"] + [f"{c} %" for c in L.COLLAB])]
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
    L.table("D1_deltas_v2_v3", "D1 - every cell that changed against F13.2c's v2 tables (T3a, T3c, T3d, T2f, T2f2)", ["table", "row", "field", "old", "new"], d1,
            note="Rows of T3a that are 'absent' in v3 are the names merged into a canon (thesaurus v3); rank changes follow from them.", md_rows=60)
    # T4 residual: one-record institutions after v3 sharing a distinctive token with a canon (>= 2 records after v3 or a thesaurus canonical)
    canons = {n for n, es in inst3.items() if len(es) >= 2} | {r["canonical"] for r in v3 if r["status"] == "active"}
    canons &= set(inst3)
    dk = {n: set(L.distinctive(n)) for n in inst3}
    freq = Counter(t for n in inst3 for t in dk[n])
    dec = {r["institution"]: r for r in L.read_csv_path(L.TABLES / "T1b2_name_decisions.csv")}
    canon_of = {r["identity"]: r["canonical"] for r in L.read_csv_path(L.TABLES / "T1b3_identities.csv")}
    excl = {(n, i) for n, i, _ in TH.EXCLUSIONS}
    t4 = []
    order = {"identity token, not a candidate": 0, "excluded (T1c)": 1, "rare token, no identity": 2, "common word": 3}
    for n in sorted(x for x, es in inst3.items() if len(es) == 1):
        ids = [h for h in TH.identity_of(n) if (n, h[0]) not in excl]
        for cn in sorted(canons):
            if cn == n:
                continue
            shared = sorted(dk[n] & dk[cn])
            id_hit = [h for h in ids if canon_of.get(h[0]) == cn]
            if not shared and not id_hit:
                continue
            rare = [t for t in shared if freq[t] <= 3]
            d = dec.get(n)
            if id_hit:
                kind, why = "identity token, not a candidate", f"matches {id_hit[0][0]} ({id_hit[0][1]}); no candidate pair (score below 80)"
            elif d and d["reason"].startswith("excluded"):
                kind, why = "excluded (T1c)", d["reason"]
            elif rare:
                kind, why = "rare token, no identity", (d["reason"] if d else "not in any candidate cluster; no identity rule matches")
            else:
                kind, why = "common word", "shares only common words: " + ", ".join(shared[:3])
            t4.append({"institution": n, "canon": cn, "shared_tokens": " ".join(shared), "rare_shared_tokens": " ".join(rare), "kind": kind,
                       "reason": why[:150]})
    t4.sort(key=lambda r: (order[r["kind"]], r["institution"], r["canon"]))
    L.table("T4_residual", "T4 - residual: one-record institutions after v3 that share a distinctive token with a canon", ["institution", "canon",
            "shared_tokens", "rare_shared_tokens", "kind", "reason"], t4,
            note="kind: 'identity token, not a candidate' = the name matches a name-token rule (T1d) of that canon but never formed a candidate "
                 "pair (token_set_ratio below 80) - a likely missed variant, left for the author; 'excluded (T1c)'; 'rare token, no identity' = a "
                 "shared token found in at most three institutions after v3; 'common word' = more frequent.", md_rows=20)
    num.update({"institutions_v2": len(inst2), "institutions_v3": len(inst3), "links_v2": sum(len(v) for v in inst2.values()),
                "links_v3": sum(len(v) for v in inst3.values()), "collab_v2": {c: ff2[-1][c] for c in L.COLLAB}, "collab_v3": {c: ff3[-1][c] for c in L.COLLAB},
                "transitions": {f"{a} -> {b}": n for (a, b), n in sorted(tr.items()) if a != b}, "d1_cells": len(d1),
                "residual_rows": len(t4), "residual_by_kind": {k: sum(1 for r in t4 if r["kind"] == k) for k in order},
                "residual_identity_misses": sorted({r["institution"] for r in t4 if r["kind"] == "identity token, not a candidate"}),
                "top10_v3": [(r["institution"], r["records"], r["records_v2"], r["rank_v2"]) for r in a3[:10]]})
    L.jdump(num, L.OUT / "F13_2d_numbers.json")
    print(json.dumps(num, ensure_ascii=True, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
