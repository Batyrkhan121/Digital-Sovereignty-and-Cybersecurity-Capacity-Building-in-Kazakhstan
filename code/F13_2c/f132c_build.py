"""Phase F13.2c - step 1 (parsing of Authors with affiliations, T1), step 2 (structure of the international records by author, T2) and
step 3 (institutions thesaurus v2, the F13.2b institution and collaboration tables recomputed, deltas D1). Deterministic: no timestamp
in tables/ or F13_2c_numbers.json. Author names are used only in memory; every output is a count."""
import sys
sys.dont_write_bytecode = True

import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132c_lib as L

P = [p for p, _, _ in L.PERIODS]
AUPET = "Almaty University of Power Engineering and Telecommunications named after Gumarbek Daukeyev"
D45 = "merge: brand name (author's decision 45)"
CLASSES = ["(i) co-authorship with an author based only abroad", "(ii) foreign addresses only of dual-affiliated authors",
           "(iii) no author with a Kazakhstan address"]
FIRST = ["Kazakhstan only", "foreign only", "both (Kazakhstan and abroad)", "no address"]


def load():
    ncols, recs = L.parse_e1()
    cset = L.countries()
    R = []
    for r in recs:
        lines = [L.parse_line(x) for x in L.aff_lines(r["affiliations"])]
        au = L.authors(r, cset)
        A = {p["country_part"] for p in lines if p["country_part"] in cset}
        for a in au:
            a["kz"] = L.KZ in a["countries"]
            a["foreign"] = a["countries"] - {L.KZ}
            a["kind"] = ("both (Kazakhstan and abroad)" if a["kz"] and a["foreign"] else "Kazakhstan only" if a["kz"]
                         else "foreign only" if a["foreign"] else "no address")
        W = set().union(*(a["countries"] for a in au)) if au else set()
        y = L.year_of(r["year"])
        R.append({"eid": r["eid"], "year": y, "period": L.period_of(y), "n_authors": r["n_authors"], "lines": lines, "authors": au,
                  "A": A, "W": W, "foreign_A": sorted(A - {L.KZ}), "foreign_W": sorted(W - {L.KZ})})
        r["awa"] = None
    return ncols, R, cset


def classify(r):
    fo = any(a["kind"] == "foreign only" for a in r["authors"])
    kz = any(a["kz"] for a in r["authors"])
    if fo and kz:
        return CLASSES[0]
    if not fo:
        return CLASSES[1]
    return CLASSES[2]


def step1(R, texts, num):
    hows = Counter(a["how"] for r in R for a in r["authors"])
    pos = sum(len(r["authors"]) for r in R)
    names_rep = sum(len(r["authors"]) - len({a["name"] for a in r["authors"]}) for r in R)
    consec = sum(1 for r in R for x, y in zip(r["authors"], r["authors"][1:]) if x["name"] == y["name"])
    mism = [r for r in R if len(r["authors"]) != r["n_authors"]]
    t1a = [{"measure": "records parsed", "value": len(R)},
           {"measure": "author positions (entries of Authors with affiliations)", "value": pos},
           {"measure": "authors with two or more affiliations", "value": sum(1 for r in R for a in r["authors"] if len(a["affs"]) >= 2)},
           {"measure": "entries with one Affiliations line", "value": hows.get("one Affiliations line", 0)},
           {"measure": "entries with two or more Affiliations lines", "value": hows.get("two or more Affiliations lines", 0)},
           {"measure": "entries without an affiliation", "value": hows.get("no affiliation", 0)},
           {"measure": "entries read by the fallback (countries from the parts)", "value": hows.get("fallback: countries from the parts", 0)},
           {"measure": "records where author positions differ from the Authors count", "value": len(mism)},
           {"measure": "pairs of consecutive entries with the same name (two authors)", "value": consec},
           {"measure": "repeated names within a record (any position)", "value": names_rep}]
    texts.append(L.table("T1a_parsing", "T1a - parsing of Authors with affiliations", ["measure", "value"], t1a,
                         note="In E1 an entry is the author's name followed by all of that author's affiliations; an author with several "
                              "affiliations is one entry, not a repeated one. Authors are positions within a record."))
    diff = [r for r in R if r["A"] != r["W"]]
    reasons = Counter()
    for r in diff:
        if r["A"] - r["W"]:
            reasons["a country of Affiliations held by no author"] += 1
        if r["W"] - r["A"]:
            reasons["an author country absent from Affiliations"] += 1
    intl_a, intl_w = sum(1 for r in R if r["foreign_A"]), sum(1 for r in R if r["foreign_W"])
    t1b = [{"measure": "records whose country set by authors equals the set by Affiliations", "value": len(R) - len(diff)},
           {"measure": "records whose sets differ", "value": len(diff)}]
    t1b += [{"measure": "reason: " + k, "value": v} for k, v in sorted(reasons.items())]
    t1b += [{"measure": "international records by Affiliations", "value": intl_a}, {"measure": "international records by authors", "value": intl_w}]
    texts.append(L.table("T1b_country_check", "T1b - country sets: Authors with affiliations against Affiliations", ["measure", "value"], t1b))
    num["T1"] = {"positions": pos, "multi_affiliation_authors": t1a[2]["value"], "mismatch_authors_count": len(mism), "country_set_differs": len(diff),
                 "intl_by_affiliations": intl_a, "intl_by_authors": intl_w, "hows": dict(hows)}


def step2(R, texts, num):
    I = [r for r in R if r["foreign_A"]]
    ref = next(r for r in L.read_csv(L.IN_T2C) if r["group"] == "all")
    cls = {r["eid"]: classify(r) for r in I}
    vac = sum(1 for r in I if cls[r["eid"]] == CLASSES[1] and not r["foreign_W"])
    rows = []
    for c in CLASSES:
        row = {"class": c, "records": sum(1 for r in I if cls[r["eid"]] == c)}
        row["share_of_517_pct"] = L.pct(row["records"], len(I))
        for p in P:
            g = [r for r in I if r["period"] == p]
            row[p] = sum(1 for r in g if cls[r["eid"]] == c)
            row[p + " %"] = L.pct(row[p], len(g))
        rows.append(row)
    rows.append({"class": "all international", "records": len(I), "share_of_517_pct": "100.0", **{p: sum(1 for r in I if r["period"] == p) for p in P},
                 **{p + " %": "100.0" for p in P}})
    texts.append(L.table("T2a_international_by_author", "T2a - the international records by the authors who carry the foreign addresses",
                         ["class", "records", "share_of_517_pct"] + [x for p in P for x in (p, p + " %")], rows,
                         note=f"Base: {len(I)} records with at least one country other than Kazakhstan by Affiliations (F13.2b T2c: "
                              f"{ref['international']}). (i): at least one author has only foreign addresses and at least one author a "
                              "Kazakhstan address. (ii): no author has only foreign addresses, so every foreign address belongs to an author "
                              f"who also has a Kazakhstan address ({vac} of them have no foreign address in the author column at all). (iii): an "
                              "author has only foreign addresses and no author has a Kazakhstan address."))
    t2b = []
    for base, recs in (("841 records", R), ("517 international records", I)):
        fc = Counter(r["authors"][0]["kind"] if r["authors"] else "no address" for r in recs)
        for k in FIRST:
            row = {"base": base, "first_author": k, "records": fc.get(k, 0), "share_pct": L.pct(fc.get(k, 0), len(recs))}
            for p in P:
                g = [r for r in recs if r["period"] == p]
                n = sum(1 for r in g if (r["authors"][0]["kind"] if r["authors"] else "no address") == k)
                row[p] = n
                row[p + " %"] = L.pct(n, len(g))
            t2b.append(row)
    texts.append(L.table("T2b_first_author_country", "T2b - country of the first author's addresses",
                         ["base", "first_author", "records", "share_pct"] + [x for p in P for x in (p, p + " %")], t2b))
    ua_only_a = sum(1 for r in I if r["foreign_A"] == ["Ukraine"])
    other_a = sum(1 for r in I if set(r["foreign_A"]) - {"Ukraine"})
    ua_only_w = sum(1 for r in R if r["foreign_W"] == ["Ukraine"])
    other_w = sum(1 for r in R if set(r["foreign_W"]) - {"Ukraine"})
    t2c = [{"measure": "records with a foreign country other than Ukraine", "by_affiliations": other_a, "by_authors": other_w},
           {"measure": "records whose only foreign country is Ukraine", "by_affiliations": ua_only_a, "by_authors": ua_only_w},
           {"measure": "records with Ukraine among their countries", "by_affiliations": sum(1 for r in I if "Ukraine" in r["foreign_A"]),
            "by_authors": sum(1 for r in R if "Ukraine" in r["foreign_W"])},
           {"measure": "international records", "by_affiliations": len(I), "by_authors": sum(1 for r in R if r["foreign_W"])}]
    texts.append(L.table("T2c_partners_other_than_ukraine", "T2c - partners other than Ukraine", ["measure", "by_affiliations", "by_authors"], t2c))
    shares = [sum(1 for a in r["authors"] if a["kz"]) / len(r["authors"]) for r in I if r["authors"]]
    kz_pos, all_pos = sum(sum(1 for a in r["authors"] if a["kz"]) for r in I), sum(len(r["authors"]) for r in I)
    t2d = [{"measure": "share of author positions with a Kazakhstan address, mean over records (%)", "value": f"{100 * sum(shares) / len(shares):.1f}"},
           {"measure": "share of author positions with a Kazakhstan address, median over records (%)", "value": f"{100 * L.median(shares):.1f}"},
           {"measure": "author positions in international records", "value": all_pos},
           {"measure": "positions with a Kazakhstan address (pooled share, %)", "value": f"{kz_pos} ({L.pct(kz_pos, all_pos)})"},
           {"measure": "positions with only foreign addresses", "value": sum(1 for r in I for a in r["authors"] if a["kind"] == "foreign only")},
           {"measure": "positions with addresses in Kazakhstan and abroad", "value": sum(1 for r in I for a in r["authors"] if a["kind"] == FIRST[2])}]
    texts.append(L.table("T2d_kazakhstan_positions", "T2d - author positions with a Kazakhstan address in the international records", ["measure", "value"], t2d))
    pc = Counter(c for r in I for c in r["foreign_A"])
    t2e = []
    for c, n in L.top(pc, 5):
        g = [r for r in I if c in r["foreign_A"]]
        held_fo = sum(1 for r in g if any(c in a["countries"] and a["kind"] == "foreign only" for a in r["authors"]))
        held_dual = sum(1 for r in g if any(c in a["countries"] for a in r["authors"])
                        and not any(c in a["countries"] and a["kind"] == "foreign only" for a in r["authors"]))
        row = {"country": c, "records": n}
        for k, lab in zip(CLASSES[:2], ("type_i", "type_ii")):
            m = sum(1 for r in g if cls[r["eid"]] == k)
            row[lab] = m
            row[lab + "_pct"] = L.pct(m, n)
        row["country_held_by_author_only_abroad"] = held_fo
        row["country_held_only_by_dual_authors"] = held_dual
        t2e.append(row)
    texts.append(L.table("T2e_top_partners_by_type", "T2e - the five main partner countries: records of type (i) and (ii)",
                         ["country", "records", "type_i", "type_i_pct", "type_ii", "type_ii_pct", "country_held_by_author_only_abroad",
                          "country_held_only_by_dual_authors"], t2e,
                         note="type_i / type_ii: the record's class (T2a). The last two columns read the country itself: whether at least one "
                              "author based only abroad holds an address in it, or only authors with a Kazakhstan address do."))
    num["T2"] = {"base": len(I), "ref_T2c": int(ref["international"]), "classes": {r["class"]: r["records"] for r in rows},
                 "vacuous_ii": vac, "first_author_841": {r["first_author"]: r["records"] for r in t2b if r["base"] == "841 records"},
                 "first_author_517": {r["first_author"]: r["records"] for r in t2b if r["base"] != "841 records"},
                 "other_than_ukraine": {"affiliations": other_a, "authors": other_w}, "ukraine_only": {"affiliations": ua_only_a, "authors": ua_only_w},
                 "kz_share_mean": t2d[0]["value"], "kz_share_median": t2d[1]["value"], "top5": [r["country"] for r in t2e]}


# ------------------------------------------------ step 3
def thesaurus_v2(kz_rec):
    v1 = L.read_csv(L.IN_THES)
    rows = []
    for r in v1:
        sup = "energo university" in r["variant"] and r["rule"].startswith("keep")
        rows.append({**r, "version": "v1", "status": "superseded (decision 45)" if sup else "active"})
    for k in sorted(k for k in kz_rec if "energo university" in k):
        rows.append({"variant": k, "canonical": AUPET, "rule": D45, "records": len(kz_rec[k]), "confidence": "high",
                     "reason": "Energo University is the brand name of AUPET since 2023 (author's decision 45)", "version": "v2", "status": "active"})
    return v1, rows


def labels(R, rows):
    act = [r for r in rows if r["status"] == "active"]
    tmap = {r["variant"]: r["canonical"] for r in act}
    n2c = {}
    for r in act:
        n2c.setdefault(L.norm_kz(r["canonical"]), r["canonical"])
    forms = defaultdict(list)
    for r in R:
        for p in r["lines"]:
            if p["country_part"] == L.KZ:
                forms[L.norm_kz(p["institution"])].append(p["institution"])
    disp = {k: (tmap.get(k) or n2c.get(k) or L.most_common_form(v)) for k, v in forms.items()}
    for r in R:
        keys = sorted({L.norm_kz(p["institution"]) for p in r["lines"] if p["country_part"] == L.KZ})
        r["kz_insts"] = sorted({disp[k] for k in keys})
        r["collab"] = ("international" if len(r["A"]) >= 2 else "domestic multi-institution" if len(r["kz_insts"]) >= 2 else "single institution")
    return forms


def step3(R, texts, num):
    kz_rec = defaultdict(set)
    for r in R:
        for p in r["lines"]:
            if p["country_part"] == L.KZ:
                kz_rec[L.norm_kz(p["institution"])].add(r["eid"])
    v1, rows = thesaurus_v2(kz_rec)
    fields = ["variant", "canonical", "rule", "records", "confidence", "reason", "version", "status"]
    L.write_csv(L.TABLES / "institutions_thesaurus_v2.csv", fields, rows)
    new_or_changed = [r for r in rows if r["version"] == "v2" or r["status"] != "active"]
    texts.append(L.table("T3_thesaurus_v2_changes", "Institutions thesaurus v2 - new and changed rows (the full v2 is tables/institutions_thesaurus_v2.csv)",
                         fields, new_or_changed))
    labels(R, rows)
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
        t3a.append({"rank": i, "institution": name, "type": L.inst_type(name), "records": len(es), "share_of_841_pct": L.pct(len(es), N),
                    **{p: bp.get(p, 0) for p in P}, "international": k, "share_international_pct": L.pct(k, len(es))})
    f3a = ["rank", "institution", "type", "records", "share_of_841_pct"] + P + ["international", "share_international_pct"]
    texts.append(L.table("T3a_v2_kz_institutions", "T3a_v2 - Kazakhstan institutions after thesaurus v2 (top 30; all in the CSV)", f3a, t3a, md_rows=30))
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
    v1c = L.read_csv(L.IN_DELTA["T3c"])
    assert [r["measure"] for r in v1c] == list(calc), "T3c labels differ from F13.2b"
    t3c = [{"measure": m, "value": v} for m, v in calc.items()]
    texts.append(L.table("T3c_v2_concentration", "T3c_v2 - concentration of Kazakhstan institutions (thesaurus v2; 'thesaurus rows' = active rows)",
                         ["measure", "value"], t3c))
    ip = Counter(pr for r in R for pr in combinations(r["kz_insts"], 2))
    t3d = [{"institution_a": a, "institution_b": b, "records": n} for (a, b), n in L.top(ip)]
    texts.append(L.table("T3d_v2_kz_institution_pairs", "T3d_v2 - pairs of Kazakhstan institutions in one record (top 15; all in the CSV)",
                         ["institution_a", "institution_b", "records"], t3d, md_rows=15))
    cy = {y: Counter() for y in L.YEARS}
    for r in R:
        cy[r["year"]][r["collab"]] += 1
    t2f = []
    for y in L.YEARS:
        tot = sum(cy[y].values())
        t2f.append({"year": y, **{c: cy[y].get(c, 0) for c in L.COLLAB}, "total": tot, **{f"{c} %": L.pct(cy[y].get(c, 0), tot) for c in L.COLLAB}})
    fy = ["year"] + L.COLLAB + ["total"] + [f"{c} %" for c in L.COLLAB]
    texts.append(L.table("T2f_v2_collaboration_by_year", "T2f_v2 - collaboration type by year (thesaurus v2)", fy, t2f))
    t2f2 = []
    for p in P + ["2003-2025"]:
        g = [r for r in R if p == "2003-2025" or r["period"] == p]
        cc = Counter(r["collab"] for r in g)
        t2f2.append({"period": p, **{c: cc.get(c, 0) for c in L.COLLAB}, "total": len(g), **{f"{c} %": L.pct(cc.get(c, 0), len(g)) for c in L.COLLAB}})
    texts.append(L.table("T2f2_v2_collaboration_by_period", "T2f2_v2 - collaboration type by period (thesaurus v2)",
                         ["period"] + L.COLLAB + ["total"] + [f"{c} %" for c in L.COLLAB], t2f2))
    # D1 - deltas against F13.2b
    d1 = []
    specs = [("T3a", t3a, "institution"), ("T3c", t3c, "measure"), ("T3d", t3d, ("institution_a", "institution_b")), ("T2f", t2f, "year"),
             ("T2f2", t2f2, "period")]
    for name, new, key in specs:
        old = L.read_csv(L.IN_DELTA[name])
        kf = (lambda r: " + ".join(str(r[k]) for k in key)) if isinstance(key, tuple) else (lambda r: str(r[key]))
        om, nm = {kf(r): r for r in old}, {kf(r): {k: str(v) for k, v in r.items()} for r in new}
        for k in sorted(set(om) | set(nm)):
            o, n_ = om.get(k), nm.get(k)
            if o is None or n_ is None:
                d1.append({"table": name, "row": k, "field": "(row)", "old": "present" if o else "absent", "new": "present" if n_ else "absent"})
                continue
            for f in o:
                if f in n_ and o[f] != n_[f] and not (name == "T3a" and f == "rank"):
                    d1.append({"table": name, "row": k, "field": f, "old": o[f], "new": n_[f]})
    rank_moves = sum(1 for r in t3a for o in L.read_csv(L.IN_DELTA["T3a"]) if o["institution"] == r["institution"] and o["rank"] != str(r["rank"]))
    texts.append(L.table("D1_deltas_v1_v2", "D1 - rows that changed against F13.2b (T3a, T3c, T3d, T2f, T2f2)", ["table", "row", "field", "old", "new"], d1,
                         note=f"Rank changes in T3a are not listed row by row ({rank_moves} institutions move in rank because one row left the "
                              "list); every other changed cell is."))
    old_c = {r["eid"]: None for r in R}
    num["T3"] = {"v1_rows": len(v1), "v2_rows": len(rows), "active_rows": sum(1 for r in rows if r["status"] == "active"),
                 "new_rows": sum(1 for r in rows if r["version"] == "v2"), "superseded": sum(1 for r in rows if r["status"] != "active"),
                 "aupet_records": len(inst.get(AUPET, ())), "institutions": len(inst), "d1_rows": len(d1), "rank_moves": rank_moves,
                 "collab_v2": {c: t2f2[-1][c] for c in L.COLLAB}}
    del old_c
    return rows


def main():
    L.install_r17_guard()
    ncols, R, cset = load()
    texts, num = [], {"records": len(R), "columns": ncols}
    step1(R, texts, num)
    step2(R, texts, num)
    step3(R, texts, num)
    old = {r["period"]: r for r in L.read_csv(L.IN_DELTA["T2f2"])}
    num["T3"]["collab_v1"] = {c: int(old["2003-2025"][c]) for c in L.COLLAB}
    L.jdump(num, L.OUT / "F13_2c_numbers.json")
    print(json.dumps({"records": num["records"], "positions": num["T1"]["positions"], "base": num["T2"]["base"], "classes": num["T2"]["classes"],
                      "other_than_ukraine": num["T2"]["other_than_ukraine"], "aupet": num["T3"]["aupet_records"], "d1_rows": num["T3"]["d1_rows"]},
                     ensure_ascii=True, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
