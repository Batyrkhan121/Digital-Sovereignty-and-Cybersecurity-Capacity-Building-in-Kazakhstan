"""Phase F13.2b - steps 1-4 on E1 (Scopus, 841): parsing of the affiliation strings (T1), countries and collaboration (T2),
Kazakhstan institutions with the thesaurus (T3), the figure (step 4). Deterministic: no timestamp in tables/, figures/*.csv or
F13_2b_numbers.json; the PDF carries no creation date. The figure is written by this script and not viewed (R18)."""
import sys
sys.dont_write_bytecode = True

import io
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132b_lib as L
import f132b_thesaurus as TH

P = [p for p, _, _ in L.PERIODS]
COLORS = {"single institution": "#9ecae1", "domestic multi-institution": "#3182bd", "international": "#e6550d"}


def thesaurus():
    tmap = {v: c for v, c, *_ in TH.ROWS}
    n2c = {}
    for _, c, *_ in TH.ROWS:
        n2c.setdefault(L.norm_kz(c), c)
    return tmap, n2c


def load():
    ncols, recs = L.parse_e1()
    tmap, n2c = thesaurus()
    forms = defaultdict(list)
    out = []
    for r in recs:
        y = L.year_of(r["year"])
        lines = [L.parse_line(x) for x in L.aff_lines(r["affiliations"])]
        for p in lines:
            if p["country_part"] == L.KZ:
                p["kz_key"] = L.norm_kz(p["institution"])
                forms[p["kz_key"]].append(p["institution"])
        out.append({"eid": r["eid"], "year": y, "period": L.period_of(y), "type": L.htype(r["doc_type"]), "source": r["source_title"].strip(),
                    "n_authors": r["n_authors"], "lines": lines})
    display = {k: (tmap.get(k) or n2c.get(k) or L.most_common_form(v)) for k, v in forms.items()}
    for r in out:
        ls = r["lines"]
        r["countries"] = sorted({p["country_part"] for p in ls if p["country_part"] in L.COUNTRY_SET})
        r["foreign"] = [c for c in r["countries"] if c != L.KZ]
        r["kz_keys"] = sorted({p["kz_key"] for p in ls if "kz_key" in p})
        r["kz_insts"] = sorted({display[k] for k in r["kz_keys"]})
        r["foreign_insts"] = sorted({(L.norm_foreign(p["institution"]), p["country_part"]) for p in ls
                                     if p["country_part"] in L.COUNTRY_SET and p["country_part"] != L.KZ})
        r["international"] = bool(r["foreign"])
        r["collab"] = ("international" if len(r["countries"]) >= 2 else
                       "domestic multi-institution" if len(r["kz_insts"]) >= 2 else "single institution")
    return ncols, out, forms, display, tmap, n2c


def by_period(eids_set, recs):
    c = Counter(r["period"] for r in recs if r["eid"] in eids_set)
    return {p: c.get(p, 0) for p in P}


def main():
    L.install_r17_guard()
    ncols, R, forms, display, tmap, n2c = load()
    N = len(R)
    num = {"records": N, "columns": ncols}
    texts = []

    # ---------- T1
    lines_all = [p for r in R for p in r["lines"]]
    kz_lines = [p for p in lines_all if p["country_part"] == L.KZ]
    rec_kz = sum(1 for r in R if any(p["country_part"] == L.KZ for p in r["lines"]))
    lpr = Counter(len(r["lines"]) for r in R)
    t1a = [{"measure": "records", "value": N, "expected": 841},
           {"measure": "affiliation lines (split on '; ')", "value": len(lines_all), "expected": 2778},
           {"measure": "lines whose last part is Kazakhstan", "value": len(kz_lines), "expected": ""},
           {"measure": "records with at least one Kazakhstan line", "value": rec_kz, "expected": 841},
           {"measure": "records without a Kazakhstan line", "value": N - rec_kz, "expected": 0},
           {"measure": "lines per record - mean", "value": L.mean([len(r["lines"]) for r in R]), "expected": ""},
           {"measure": "lines per record - median", "value": L.median([len(r["lines"]) for r in R]), "expected": ""},
           {"measure": "lines per record - maximum", "value": max(lpr), "expected": ""}]
    texts.append(L.table("T1a_counts", "T1a - affiliation lines", ["measure", "value", "expected"], t1a))
    texts.append(L.table("T1a2_lines_per_record", "T1a2 - affiliation lines per record", ["lines", "records", "share_pct"],
                         [{"lines": k, "records": v, "share_pct": L.pct(v, N)} for k, v in sorted(lpr.items())]))
    lev_all, lev_kz = Counter(p["level"] for p in lines_all), Counter(p["level"] for p in kz_lines)
    order = [lab for lab, _ in L.LEVELS] + ["unresolved"]
    texts.append(L.table("T1a3_rule_levels", "T1a3 - which level of the institution rule decided each line",
                         ["level", "all_lines", "kazakhstan_lines", "other_lines"],
                         [{"level": lv, "all_lines": lev_all.get(lv, 0), "kazakhstan_lines": lev_kz.get(lv, 0),
                           "other_lines": lev_all.get(lv, 0) - lev_kz.get(lv, 0)} for lv in order]))
    npart = Counter(p["n_parts"] for p in lines_all)
    texts.append(L.table("T1a4_parts_per_line", "T1a4 - parts per affiliation line (split on ', ')", ["parts", "lines"],
                         [{"parts": k, "lines": v} for k, v in sorted(npart.items())]))
    last_lines = Counter(p["country_part"] for p in lines_all)
    last_recs = Counter(c for r in R for c in {p["country_part"] for p in r["lines"]})
    t1b = [{"last_part": k, "lines": v, "records": last_recs[k], "in_country_list": "yes" if k in L.COUNTRY_SET else "no"}
           for k, v in L.top(last_lines)]
    texts.append(L.table("T1b_last_parts", "T1b - every last part of an affiliation line", ["last_part", "lines", "records", "in_country_list"], t1b))
    out_list = [x for x in t1b if x["in_country_list"] == "no"]
    texts.append(L.table("T1b2_last_parts_not_in_list", "T1b2 - last parts outside the country list (for the author)",
                         ["last_part", "lines", "records"], out_list))
    L.write_csv(L.TABLES / "scopus_country_names.csv", ["country_name"], [{"country_name": c} for c in L.SCOPUS_COUNTRIES])
    unres = [p for p in lines_all if p["unresolved"]]
    unres_kz = [p for p in unres if p["country_part"] == L.KZ]
    uc = Counter(p["first_part"] for p in unres)
    texts.append(L.table("T1c_unresolved_counts", "T1c - lines whose institution is 'unresolved'", ["measure", "value"],
                         [{"measure": "unresolved lines, all", "value": len(unres)},
                          {"measure": "unresolved lines, Kazakhstan", "value": len(unres_kz)},
                          {"measure": "unresolved lines, other countries", "value": len(unres) - len(unres_kz)},
                          {"measure": "distinct first parts of unresolved lines", "value": len(uc)},
                          {"measure": "distinct first parts with two or more lines", "value": sum(1 for v in uc.values() if v >= 2)}]))
    u_rows = [{"first_part": k, "lines": v, "kazakhstan_lines": sum(1 for p in unres_kz if p["first_part"] == k)} for k, v in L.top(uc)]
    texts.append(L.table("T1c2_unresolved_first_parts", "T1c2 - first parts of unresolved lines (two or more lines; all in the CSV)",
                         ["first_part", "lines", "kazakhstan_lines"], u_rows, md_rows=sum(1 for v in uc.values() if v >= 2)))
    num["T1"] = {"lines": len(lines_all), "kz_lines": len(kz_lines), "records_with_kz": rec_kz, "distinct_last_parts": len(last_lines),
                 "last_parts_not_in_list": len(out_list), "unresolved": len(unres), "unresolved_kz": len(unres_kz),
                 "levels": dict(lev_all), "two_part_lines": npart.get(2, 0)}

    # ---------- T2
    nc = Counter(min(len(r["countries"]), 4) for r in R)
    texts.append(L.table("T2a_countries_per_record", "T2a - records by number of countries", ["countries", "records", "share_pct"],
                         [{"countries": ("4 or more" if k == 4 else k), "records": nc.get(k, 0), "share_pct": L.pct(nc.get(k, 0), N)}
                          for k in (1, 2, 3, 4)]))
    pc = Counter(c for r in R for c in r["foreign"])
    pc_eids = defaultdict(set)
    for r in R:
        for c in r["foreign"]:
            pc_eids[c].add(r["eid"])
    t2b = []
    for i, (c, n) in enumerate(L.top(pc), 1):
        bp = by_period(pc_eids[c], R)
        t2b.append({"rank": i, "country": c, "records": n, "share_of_841_pct": L.pct(n, N), **{p: bp[p] for p in P}})
    texts.append(L.table("T2b_partner_countries", "T2b - partner countries by records (a record counts once per country)",
                         ["rank", "country", "records", "share_of_841_pct"] + P, t2b, md_rows=20))
    per_n = Counter(r["period"] for r in R)
    t2c = []
    for p in P:
        g = [r for r in R if r["period"] == p]
        k = sum(r["international"] for r in g)
        t2c.append({"group": "period", "value": p, "records": len(g), "international": k, "share_international_pct": L.pct(k, len(g))})
    for t in L.TYPES:
        g = [r for r in R if r["type"] == t]
        k = sum(r["international"] for r in g)
        t2c.append({"group": "type", "value": t, "records": len(g), "international": k, "share_international_pct": L.pct(k, len(g))})
    k_all = sum(r["international"] for r in R)
    t2c.append({"group": "all", "value": "2003-2025", "records": N, "international": k_all, "share_international_pct": L.pct(k_all, N)})
    texts.append(L.table("T2c_international_share", "T2c - share of international records (at least one country other than Kazakhstan)",
                         ["group", "value", "records", "international", "share_international_pct"], t2c))
    pairs = Counter(pr for r in R for pr in combinations(sorted(r["foreign"]), 2))
    texts.append(L.table("T2d_partner_country_pairs", "T2d - pairs of partner countries in one record (top 10; all in the CSV)",
                         ["country_a", "country_b", "records"],
                         [{"country_a": a, "country_b": b, "records": n} for (a, b), n in L.top(pairs)], md_rows=10))
    top5 = [x["country"] for x in t2b[:5]]
    t2e = []
    for c in top5:
        sc = Counter(r["source"] for r in R if c in r["foreign"])
        for i, (s, n) in enumerate(L.top(sc, 5), 1):
            t2e.append({"country": c, "country_records": len(pc_eids[c]), "rank": i, "source_title": s, "records": n,
                        "share_of_country_pct": L.pct(n, len(pc_eids[c]))})
    texts.append(L.table("T2e_partner_sources", "T2e - top five sources of the joint records of the five main partner countries",
                         ["country", "country_records", "rank", "source_title", "records", "share_of_country_pct"], t2e,
                         note="Ties at equal counts are ordered by source title."))
    cy = {y: Counter() for y in L.YEARS}
    for r in R:
        cy[r["year"]][r["collab"]] += 1
    t2f_y = []
    for y in L.YEARS:
        tot = sum(cy[y].values())
        t2f_y.append({"year": y, **{c: cy[y].get(c, 0) for c in L.COLLAB}, "total": tot,
                      **{f"{c} %": L.pct(cy[y].get(c, 0), tot) for c in L.COLLAB}})
    fields_y = ["year"] + L.COLLAB + ["total"] + [f"{c} %" for c in L.COLLAB]
    texts.append(L.table("T2f_collaboration_by_year", "T2f - collaboration type by year", fields_y, t2f_y))
    t2f_p = []
    for p in P + ["2003-2025"]:
        g = [r for r in R if p == "2003-2025" or r["period"] == p]
        cc = Counter(r["collab"] for r in g)
        t2f_p.append({"period": p, **{c: cc.get(c, 0) for c in L.COLLAB}, "total": len(g), **{f"{c} %": L.pct(cc.get(c, 0), len(g)) for c in L.COLLAB}})
    texts.append(L.table("T2f2_collaboration_by_period", "T2f2 - collaboration type by period", ["period"] + L.COLLAB + ["total"] + [f"{c} %" for c in L.COLLAB],
                         t2f_p, note="single institution: one Kazakhstan institution after the thesaurus and one country; domestic "
                                     "multi-institution: two or more Kazakhstan institutions and one country; international: two or more countries."))
    t2g = []
    for c in L.COLLAB:
        xs = [r["n_authors"] for r in R if r["collab"] == c]
        t2g.append({"collaboration": c, "records": len(xs), "authors_mean": L.mean(xs), "authors_median": L.median(xs), "authors_max": max(xs) if xs else ""})
    xs = [r["n_authors"] for r in R]
    t2g.append({"collaboration": "all", "records": len(xs), "authors_mean": L.mean(xs), "authors_median": L.median(xs), "authors_max": max(xs)})
    texts.append(L.table("T2g_authors_by_collaboration", "T2g - authors per record by collaboration type (count of ';'-separated names in Authors)",
                         ["collaboration", "records", "authors_mean", "authors_median", "authors_max"], t2g))
    num["T2"] = {"partner_countries": len(pc), "top5": top5, "international": k_all, "international_pct": L.pct(k_all, N),
                 "by_period": {x["value"]: x["share_international_pct"] for x in t2c if x["group"] == "period"},
                 "collab_all": {c: t2f_p[-1][c] for c in L.COLLAB}, "collab_by_period": {x["period"]: {c: x[c] for c in L.COLLAB} for x in t2f_p},
                 "countries_per_record": {str(k): v for k, v in sorted(nc.items())}}

    # ---------- T3
    th_rows = []
    kz_rec = defaultdict(set)
    for r in R:
        for k in r["kz_keys"]:
            kz_rec[k].add(r["eid"])
    two_plus = {k for k, es in kz_rec.items() if len(es) >= 2}
    variants = [x[0] for x in TH.ROWS]
    assert len(variants) == len(set(variants)) and set(variants) == two_plus, (sorted(two_plus - set(variants)), sorted(set(variants) - two_plus))
    merge_from = {v for v, c, rule, *_ in TH.ROWS if rule.startswith("merge")}
    for v, c, rule, *_ in TH.ROWS:
        assert rule.startswith("merge") or rule == TH.K, rule
        assert (L.norm_kz(c) == v) == (rule == TH.K), (v, c, rule)
        assert L.norm_kz(c) not in merge_from, (v, c)
    for v, c, rule, conf, reason in TH.ROWS:
        th_rows.append({"variant": v, "canonical": c, "rule": rule, "records": len(kz_rec.get(v, ())), "confidence": conf, "reason": reason})
    L.write_csv(L.TABLES / "institutions_thesaurus.csv", ["variant", "canonical", "rule", "records", "confidence", "reason"], th_rows)
    inst_eids = defaultdict(set)
    for r in R:
        for i in r["kz_insts"]:
            inst_eids[i].add(r["eid"])
    inst_rank = sorted(inst_eids.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    intl = {r["eid"] for r in R if r["international"]}
    t3a = []
    for i, (name, es) in enumerate(inst_rank, 1):
        bp = by_period(es, R)
        k = len(es & intl)
        t3a.append({"rank": i, "institution": name, "type": L.inst_type(name), "records": len(es), "share_of_841_pct": L.pct(len(es), N),
                    **{p: bp[p] for p in P}, "international": k, "share_international_pct": L.pct(k, len(es))})
    texts.append(L.table("T3a_kz_institutions", "T3a - Kazakhstan institutions by records after the thesaurus (full counting; top 30, all in the CSV)",
                         ["rank", "institution", "type", "records", "share_of_841_pct"] + P + ["international", "share_international_pct"], t3a, md_rows=30))
    type_inst = Counter(L.inst_type(n) for n in inst_eids)
    type_rec = Counter(t for r in R for t in {L.inst_type(i) for i in r["kz_insts"]})
    texts.append(L.table("T3b_institution_types", "T3b - Kazakhstan institutions by type (a record counts once per type)",
                         ["type", "institutions", "records", "share_of_841_pct", "keywords"],
                         [{"type": t, "institutions": type_inst.get(t, 0), "records": type_rec.get(t, 0), "share_of_841_pct": L.pct(type_rec.get(t, 0), N),
                           "keywords": next((", ".join(w) for tt, w in L.INST_TYPES if tt == t), "none of the above")} for t in L.INST_TYPE_ORDER],
                         note="The type is read from the canonical name: the first type whose keyword it contains, in the order shown "
                              "(llp, jsc, ltd and inc as whole words, the rest as substrings). 'department of' counts only with a state "
                              "word (" + ", ".join(L.STATE_WORDS) + "). A name that opens as an academic unit (department, faculty, school "
                              "of, higher school of, chair, division) and names no university, institute or academy is 'other'."))
    links = sum(len(es) for es in inst_eids.values())
    top5i, top10i = [n for n, _ in inst_rank[:5]], [n for n, _ in inst_rank[:10]]
    rec5 = len(set().union(*(inst_eids[n] for n in top5i)))
    rec10 = len(set().union(*(inst_eids[n] for n in top10i)))
    l5, l10 = sum(len(inst_eids[n]) for n in top5i), sum(len(inst_eids[n]) for n in top10i)
    t3c = [{"measure": "Kazakhstan institution variants before the thesaurus (normalised keys)", "value": len(kz_rec)},
           {"measure": "variants in two or more records (all decided in the thesaurus)", "value": sum(1 for v in kz_rec.values() if len(v) >= 2)},
           {"measure": "thesaurus rows", "value": len(TH.ROWS)},
           {"measure": "distinct Kazakhstan institutions after the thesaurus", "value": len(inst_eids)},
           {"measure": "institutions with one record", "value": sum(1 for es in inst_eids.values() if len(es) == 1)},
           {"measure": "institution-record links (full counting)", "value": links},
           {"measure": "share of links held by the top 5 (%)", "value": L.pct(l5, links)},
           {"measure": "share of links held by the top 10 (%)", "value": L.pct(l10, links)},
           {"measure": "records with at least one top-5 institution", "value": rec5},
           {"measure": "share of the 841 records with a top-5 institution (%)", "value": L.pct(rec5, N)},
           {"measure": "records with at least one top-10 institution", "value": rec10},
           {"measure": "share of the 841 records with a top-10 institution (%)", "value": L.pct(rec10, N)}]
    texts.append(L.table("T3c_concentration", "T3c - concentration of Kazakhstan institutions", ["measure", "value"], t3c))
    ip = Counter(pr for r in R for pr in combinations(r["kz_insts"], 2))
    texts.append(L.table("T3d_kz_institution_pairs", "T3d - pairs of Kazakhstan institutions in one record (top 15; all in the CSV)",
                         ["institution_a", "institution_b", "records"],
                         [{"institution_a": a, "institution_b": b, "records": n} for (a, b), n in L.top(ip)], md_rows=15))
    fo_eids, fo_forms = defaultdict(set), defaultdict(list)
    for r in R:
        for p in r["lines"]:
            if p["country_part"] in L.COUNTRY_SET and p["country_part"] != L.KZ:
                k = (L.norm_foreign(p["institution"]), p["country_part"])
                fo_eids[k].add(r["eid"])
                fo_forms[k].append(p["institution"])
    fo_rank = sorted(fo_eids.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    texts.append(L.table("T3e_foreign_institutions", "T3e - foreign partner institutions by records (top 15; all in the CSV)",
                         ["rank", "institution", "country", "records", "share_of_841_pct"],
                         [{"rank": i, "institution": L.most_common_form(fo_forms[k]), "country": k[1], "records": len(es), "share_of_841_pct": L.pct(len(es), N)}
                          for i, (k, es) in enumerate(fo_rank, 1)], md_rows=15,
                         note="No thesaurus: foreign institutions are grouped only by lowercase and punctuation-to-space normalisation within a "
                              "country, so spelling variants of one institution may be counted apart."))
    t3f = []
    byid = {r["eid"]: r for r in R}
    for name in top10i:
        cc = Counter(c for e in inst_eids[name] for c in byid[e]["foreign"])
        for j, (c, n) in enumerate(L.top(cc, 3), 1):
            t3f.append({"institution": name, "institution_records": len(inst_eids[name]), "rank": j, "partner_country": c, "records": n})
    texts.append(L.table("T3f_top10_partner_countries", "T3f - top three partner countries of the ten largest Kazakhstan institutions",
                         ["institution", "institution_records", "rank", "partner_country", "records"], t3f))

    # sensitivity (not applied): one-record variants sharing a distinctive token with a canonical name
    left = []
    s_map = {}
    for k, es in sorted(kz_rec.items()):
        if len(es) != 1 or k in tmap or k in n2c:
            continue
        hit = next(((t, c) for t, c in TH.TOKENS if t in k), None)
        if hit:
            left.append({"variant": k, "token": hit[0], "would_join": hit[1], "records": 1})
            s_map[k] = hit[1]
    changed = 0
    for r in R:
        alt = sorted({s_map.get(k) or display[k] for k in r["kz_keys"]})
        alt_c = "international" if len(r["countries"]) >= 2 else ("domestic multi-institution" if len(alt) >= 2 else "single institution")
        changed += alt_c != r["collab"]
    texts.append(L.table("S1_one_record_token_variants", "S1 - sensitivity (not applied): one-record variants left as they are that carry a canonical name's token",
                         ["variant", "token", "would_join", "records"], left,
                         note=f"{len(left)} one-record variants; merging them by token would change the collaboration type of {changed} records "
                              "(domestic multi-institution to single institution)."))
    unit_keys = {v for v, c, rule, conf, reason in TH.ROWS if reason == TH.UNIT}
    unit_changed = 0
    for r in R:
        if r["collab"] != "domestic multi-institution":
            continue
        rest = {display[k] for k in r["kz_keys"] if k not in unit_keys}
        unit_changed += len(rest) <= 1
    num["T3"] = {"variants": len(kz_rec), "variants_2plus": sum(1 for v in kz_rec.values() if len(v) >= 2), "thesaurus_rows": len(TH.ROWS),
                 "merge_rows": sum(1 for x in TH.ROWS if x[2].startswith("merge")), "keep_rows": sum(1 for x in TH.ROWS if x[2].startswith("keep")),
                 "low_confidence": sum(1 for x in TH.ROWS if x[3] == "low"), "medium_confidence": sum(1 for x in TH.ROWS if x[3] == "medium"),
                 "institutions": len(inst_eids), "one_record": sum(1 for es in inst_eids.values() if len(es) == 1), "links": links,
                 "top5_links_pct": L.pct(l5, links), "top10_links_pct": L.pct(l10, links), "top5_records": rec5, "top10_records": rec10,
                 "top10": [{"institution": x["institution"], "records": x["records"], "share_international_pct": x["share_international_pct"]} for x in t3a[:10]],
                 "S1_variants": len(left), "S1_changed_records": changed, "S2_unit_only_changed_records": unit_changed,
                 "foreign_institutions": len(fo_eids)}

    # ---------- step 4 - the figure
    fig_rows = [{"year": x["year"], **{c: x[c] for c in L.COLLAB}, "total": x["total"]} for x in t2f_y]
    L.write_csv(L.FIGURES / "Fig_collaboration_type_by_year.csv", ["year"] + L.COLLAB + ["total"], fig_rows)
    figure(fig_rows)
    L.jdump(num, L.OUT / "F13_2b_numbers.json")
    print(json.dumps({"records": N, "lines": len(lines_all), "kz_records": rec_kz, "distinct_last_parts": len(last_lines),
                      "international_pct": num["T2"]["international_pct"], "collab": num["T2"]["collab_all"],
                      "institutions": len(inst_eids), "thesaurus_rows": len(TH.ROWS)}, ensure_ascii=True, indent=1))
    return 0


def figure(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image
    matplotlib.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "svg.hashsalt": "f132b", "pdf.compression": 6})
    years = [r["year"] for r in rows]
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    bottom = [0] * len(rows)
    for c in L.COLLAB:
        vals = [r[c] for r in rows]
        ax.bar(years, vals, bottom=bottom, color=COLORS[c], edgecolor="white", linewidth=0.4, width=0.8, label=c)
        bottom = [a + b for a, b in zip(bottom, vals)]
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], rotation=90)
    ax.set_xlim(years[0] - 0.7, years[-1] + 0.7)
    ax.set_ylabel("Records (Scopus, n = 841)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    base = L.FIGURES / "Fig_collaboration_type_by_year"
    fig.savefig(str(base) + ".pdf", metadata={"CreationDate": None, "ModDate": None})
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300, metadata={"Software": None})
    plt.close(fig)
    (Path(str(base) + ".png")).write_bytes(buf.getvalue())
    img = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    img.save(str(base) + ".tif", compression="tiff_lzw", dpi=(300, 300))


if __name__ == "__main__":
    raise SystemExit(main())
