"""Phase F13.2 - steps 1-7: structural indicators of the frame E1 (Scopus, 841): years and types, sources (Bradford zones,
conference series), citations, open access and funding, Web of Science validation on the 216 pairs, deltas against phase
F12.1, and the annual-output figure. Aggregates only; record lists carry eid, year, type, source, doi, counts and a title cut to
30 words. Deterministic: full sort keys, no timestamps in tables, PDF without creation date."""
import sys
sys.dont_write_bytecode = True

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132_lib as L

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

NUM = {}
T = L.TABLES
HTYPES = ["article", "conference paper", "book chapter", "review", "book", "retracted"]
HMAP = {t: t for t in HTYPES}
COLORS = {"article": "#1f4e79", "conference paper": "#d97a1e", "book chapter": "#5b9e5b", "review": "#8064a2", "book": "#9e9e9e",
          "retracted": "#c0392b"}
LANG_CODES = {"eng": "English", "rus": "Russian", "kaz": "Kazakh", "pol": "Polish", "ukr": "Ukrainian", "spa": "Spanish", "kor": "Korean",
              "por": "Portuguese"}
KZ_MINISTRY = "Ministry of Education and Science / Ministry of Science and Higher Education of the Republic of Kazakhstan (incl. Science Committee)"


def harm(t):
    return HMAP.get((t or "").strip().lower(), "other")


def period_of(y):
    return next((p for p, lo, hi in L.PERIODS if lo <= y <= hi), "")


def to_int(s):
    try:
        return int(float(str(s).strip()))
    except ValueError:
        return 0


def counts(ctr, key, denom, k=1):
    return [{key: a, "n": n, "pct": L.pct(n, denom, k)} for a, n in sorted(ctr.items(), key=lambda kv: (-kv[1], str(kv[0])))]


# ---------- load
header, E1 = L.parse_e1()
for r in E1:
    r["eid"] = r["EID"].strip()
    r["year"] = L.year_of(r["Year"])
    r["type_exp"] = r["Document Type"].strip()
    r["type_h"] = harm(r["type_exp"])
    r["source"] = r["Source title"].strip() or "(empty)"
    r["cited"] = to_int(r["Cited by"])
    r["oa_cats"] = [x.strip() for x in r["Open Access"].split(";") if x.strip()]
    r["oa"] = bool(r["oa_cats"])
    r["funded"] = bool(r["Funding Details"].strip())
    r["period"] = period_of(r["year"])
N = len(E1)
E2 = L.parse_e2()
w_by = {r["UT"]: r for r in E2}
e_by = {r["eid"]: r for r in E1}
pairs = L.read_csv(L.PAIRS)
f131y = L.read_csv(L.F131_YEARS)
I1 = L.read_csv(L.I1, ["scopus_id", "publication_year", "citations_count"])
F = {k: L.read_csv(v) for k, v in L.F121.items()}
NUM["N"] = N

# ---------- step 1: years and types
yc = Counter(r["year"] for r in E1)
cum, rows = 0, []
for y in L.YEARS:
    cum += yc.get(y, 0)
    rows.append({"year": y, "records": yc.get(y, 0), "pct": L.pct(yc.get(y, 0), N), "cumulative": cum})
rows.append({"year": "2003-2025", "records": sum(yc.get(y, 0) for y in L.YEARS), "pct": "100.0", "cumulative": cum})
L.table("T1a_years", f"T1a. Records by year, E1 (n = {N})", ["year", "records", "pct", "cumulative"], rows,
        f"Source: {L.E1} (Scopus, retrieved 2026-10-13).")
NUM["T1a"] = {str(y): yc.get(y, 0) for y in L.YEARS}
te = Counter(r["type_exp"] for r in E1)
th = Counter(r["type_h"] for r in E1)
L.table("T1b_types_exported", f"T1b. Document types as exported (n = {N})", ["doc_type", "n", "pct"], counts(te, "doc_type", N))
L.table("T1b_types_harmonised", f"T1b. Document types, harmonised (n = {N})", ["doc_type", "n", "pct"], counts(th, "doc_type", N),
        "Rule: the exported Document Type, lowercased: article, conference paper, book chapter, review, book, retracted (kept as its "
        "own category); any other value would be 'other' (none occurs).")
NUM["T1b"] = {"exported": dict(te), "harmonised": dict(th)}
grid = defaultdict(Counter)
for r in E1:
    grid[r["year"]][r["type_h"]] += 1
rows = [{"year": y, **{t: grid[y][t] for t in HTYPES}, "total": sum(grid[y].values())} for y in L.YEARS]
rows.append({"year": "2003-2025", **{t: sum(r[t] for r in rows) for t in HTYPES}, "total": sum(r["total"] for r in rows)})
T1C_FIELDS = ["year"] + HTYPES + ["total"]
L.table("T1c_year_by_type", f"T1c. Year by harmonised type (n = {N})", T1C_FIELDS, rows)
T1C = rows
rows = []
for p, lo, hi in L.PERIODS:
    rr = [r for r in E1 if r["period"] == p]
    c = Counter(r["type_h"] for r in rr)
    rows.append({"period": p, "records": len(rr), "pct": L.pct(len(rr), N), "per_year": f"{len(rr) / (hi - lo + 1):.1f}", **{t: c[t] for t in HTYPES}})
L.table("T1d_periods", f"T1d. Periods (n = {N})", ["period", "records", "pct", "per_year"] + HTYPES, rows, "per_year = records / years in the period.")
NUM["T1d"] = {r["period"]: r["records"] for r in rows}


def author_stats(rr):
    na = [r["n_authors"] for r in rr if not r["authors_missing"]]
    return {"records": len(rr), "with_authors": len(na), "mean": f"{sum(na) / len(na):.2f}" if na else "", "median": L.median(na),
            "max": max(na) if na else "", "single_author": sum(1 for x in na if x == 1), "single_author_pct": L.pct(sum(1 for x in na if x == 1), len(na))}


rows = [{"group": "2003-2025", **author_stats(E1)}] + [{"group": p, **author_stats([r for r in E1 if r["period"] == p])} for p, _, _ in L.PERIODS]
L.table("T1e_authors_per_record", "T1e. Authors per record (count of ';'-separated names in Authors; names are not kept)",
        ["group", "records", "with_authors", "mean", "median", "max", "single_author", "single_author_pct"], rows,
        f"Records without an author list: {sum(r['authors_missing'] for r in E1)}.")
NUM["T1e"] = rows[0]
lc = Counter(r["Language of Original Document"].strip() or "(empty)" for r in E1)
sc = Counter(r["Publication Stage"].strip() or "(empty)" for r in E1)
L.table("T1f_language", f"T1f. Language of the original document, as exported (n = {N})", ["language", "n", "pct"], counts(lc, "language", N))
L.table("T1f_publication_stage", f"T1f. Publication stage (n = {N})", ["stage", "n", "pct"], counts(sc, "stage", N))
NUM["T1f"] = {"language": dict(lc), "stage": dict(sc)}
rows = [{"eid": r["eid"], "year": r["year"], "doc_type": r["type_exp"], "source": r["source"]} for r in sorted(E1, key=lambda r: r["eid"]) if r["type_h"] == "retracted"]
L.table("T1g_retracted", f"T1g. Retracted records (n = {len(rows)})", ["eid", "year", "doc_type", "source"], rows, "No titles (brief).")
NUM["T1g"] = len(rows)

# ---------- step 2: sources
by_src = defaultdict(list)
for r in E1:
    by_src[r["source"]].append(r)
order = sorted(by_src, key=lambda s: (-len(by_src[s]), s.casefold(), s))
rows, cum = [], 0
for i, s in enumerate(order, 1):
    rr = by_src[s]
    c = Counter(r["type_h"] for r in rr)
    issn = sorted({r["ISSN"].strip() for r in rr if r["ISSN"].strip()})
    isbn = sorted({r["ISBN"].split(";")[0].strip() for r in rr if r["ISBN"].strip()})
    pub = Counter(r["Publisher"].strip() for r in rr if r["Publisher"].strip())
    before = cum
    cum += len(rr)
    zone = 1 if before < N / 3 else 2 if before < 2 * N / 3 else 3
    rows.append({"rank": i, "source_title": L.cut30(s), "records": len(rr), "pct": L.pct(len(rr), N), **{t: c[t] for t in HTYPES},
                 "issn": "; ".join(issn[:2]), "isbn_first": "; ".join(isbn[:2]),
                 "publisher": sorted(pub.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if pub else "",
                 "first_year": min(r["year"] for r in rr), "last_year": max(r["year"] for r in rr), "cumulative": cum, "bradford_zone": zone})
T2A_F = ["rank", "source_title", "records", "pct"] + HTYPES + ["issn", "isbn_first", "publisher", "first_year", "last_year", "cumulative", "bradford_zone"]
T2A = rows
L.table("T2a_sources", f"T2a. Sources (Source title), E1 (n = {N}; {len(order)} sources) - top 20 shown, full list in the CSV", T2A_F, rows,
        "Order: records, then name. ISSN: distinct values (up to 2); ISBN: the first ISBN of each record, distinct (up to 2); publisher: the most "
        "frequent value. Bradford zone: a source is in zone 1 while the cumulative count before it is below N/3, in zone 2 while below 2N/3.",
        md_rows=rows[:20])
zones = {z: [r for r in rows if r["bradford_zone"] == z] for z in (1, 2, 3)}
conc = [{"measure": "distinct sources", "value": len(order)},
        {"measure": "sources with one record", "value": sum(1 for s in order if len(by_src[s]) == 1)},
        {"measure": "share of records in the top 5 sources (%)", "value": L.pct(sum(r["records"] for r in rows[:5]), N)},
        {"measure": "share of records in the top 10 sources (%)", "value": L.pct(sum(r["records"] for r in rows[:10]), N)},
        {"measure": "share of records in the top 20 sources (%)", "value": L.pct(sum(r["records"] for r in rows[:20]), N)}]
for z in (1, 2, 3):
    conc.append({"measure": f"Bradford zone {z}: sources / records", "value": f"{len(zones[z])} / {sum(r['records'] for r in zones[z])}"})
L.table("T2a_concentration", "T2a. Source concentration and Bradford zones", ["measure", "value"], conc)
NUM["T2a"] = {"sources": len(order), "singletons": conc[1]["value"], "zones": {z: [len(zones[z]), sum(r["records"] for r in zones[z])] for z in (1, 2, 3)},
              "top20": [(r["source_title"], r["records"]) for r in rows[:20]], "sum_records": sum(r["records"] for r in rows)}


def top_sources(pred, k):
    c = Counter(r["source"] for r in E1 if pred(r))
    tot = sum(c.values())
    return [{"rank": i, "source_title": L.cut30(s), "records": n, "pct_of_subset": L.pct(n, tot)}
            for i, (s, n) in enumerate(sorted(c.items(), key=lambda kv: (-kv[1], kv[0].casefold(), kv[0]))[:k], 1)], tot


rows, tot = top_sources(lambda r: r["type_h"] in ("article", "review"), 20)
L.table("T2b_top20_journals", f"T2b. Top 20 journals (records of type article or review, n = {tot})", ["rank", "source_title", "records", "pct_of_subset"], rows)
rows, tot = top_sources(lambda r: r["type_h"] == "conference paper", 20)
L.table("T2c_top20_conference_sources", f"T2c. Top 20 sources of conference papers (n = {tot})", ["rank", "source_title", "records", "pct_of_subset"], rows)
pc = Counter(r["Publisher"].strip() or "(empty)" for r in E1)
L.table("T2d_publishers", f"T2d. Publishers as exported, top 15 (n = {N})", ["publisher", "n", "pct"], counts(pc, "publisher", N)[:15],
        f"Distinct publisher strings: {len(pc)}. Variants of one publisher (e.g. 'MDPI' and 'Multidisciplinary Digital Publishing Institute (MDPI)') "
        "are kept as exported.")
NUM["T2d_distinct"] = len(pc)

# ---------- T2e: conference series
CONNECT = {"and", "&"}


def is_acronym(acr):
    toks = acr.split()
    if not toks or len(toks) > 5:
        return False
    if len(toks) == 1 and toks[0][:1].isupper() and len(toks[0]) >= 4 and toks[0].isalpha():
        return True
    strong = any(sum(ch.isupper() for ch in t) >= 2 for t in toks)
    ok = all(t in CONNECT or t[:1].isupper() or t[:1].isdigit() for t in toks)
    return strong and ok


def norm_conf(s):
    s = s.lower()
    s = re.sub(r"^\s*(19|20)\d{2}\s+", " ", s)
    s = re.sub(r"\bproceedings of the\b", " ", s)
    s = re.sub(r"\b\d+(st|nd|rd|th)\b", " ", s)
    s = re.sub(r"\b(19|20)\d{2}\b", " ", s)
    s = re.sub(r"[^a-z0-9]", " ", s)
    s = " ".join(t for t in s.split() if not re.fullmatch(r"[ivxlc]+", t))
    return s


def conf_key(name):
    s = " ".join(name.split())
    if not s:
        return "(no conference name)", "none", ""
    segs = s.split(",")
    last = segs[-1].strip()
    m = re.fullmatch(r"(?P<acr>.+?)\s*[’']?(?P<yr>(?:19|20)?\d{2})(?:-[A-Za-z]+)?", last)
    if m and is_acronym(m.group("acr").strip()):
        return " ".join(m.group("acr").split()), "acronym", norm_conf(",".join(segs[:-1]))
    return norm_conf(s), "name", norm_conf(s)


confs = [r for r in E1 if r["type_h"] == "conference paper"]
for r in confs:
    r["ckey"], r["ckind"], r["cname"] = conf_key(r["Conference name"])
keys = Counter(r["ckey"] for r in confs)
kind = {r["ckey"]: r["ckind"] for r in confs}
namepart = defaultdict(Counter)
for r in confs:
    if r["ckind"] == "acronym" and r["cname"]:
        namepart[r["ckey"]][r["cname"]] += 1
acrs = sorted(k for k in keys if kind[k] == "acronym")
decisions = []
for k in acrs:
    m = re.fullmatch(r"(.+)-\d+", k)
    if m:
        decisions.append({"variant": k, "candidate_series": m.group(1), "rule": "R1 numeric suffix", "decision": "merge",
                          "reason": "the same workshop numbered within one year"})
    for j in acrs:
        if j != k and "/" in j and k in [x.strip() for x in j.split("/")]:
            decisions.append({"variant": k, "candidate_series": j, "rule": "R2 component of a joint (slash) key", "decision": "merge",
                              "reason": "the joint event appears under both forms"})
        if j != k and " and " in j and k in [x.strip() for x in j.split(" and ")]:
            decisions.append({"variant": k, "candidate_series": j, "rule": "R2b component of a joint (and) key", "decision": "merge",
                              "reason": "the event continued under the joint name"})
        if j != k and j.lower() == k.lower() and (keys[j], j) > (keys[k], k):
            decisions.append({"variant": k, "candidate_series": j, "rule": "R3 case variant", "decision": "merge", "reason": "same acronym"})
        if j != k and re.fullmatch(re.escape(j) + r"\s+Workshops?", k):
            decisions.append({"variant": k, "candidate_series": j, "rule": "R4 workshop of a conference", "decision": "keep",
                              "reason": "a workshop is a separate venue from the main conference"})
        if j != k and re.fullmatch(re.escape(j) + r"-[A-Za-z][A-Za-z0-9]*", k) and not re.fullmatch(r".+-\d+", k):
            decisions.append({"variant": k, "candidate_series": j, "rule": "R5 named sub-event", "decision": "keep",
                              "reason": "a named sub-event (e.g. a symposium or second workshop) is kept apart"})
name_index = {}
for a in acrs:
    for nm, _ in namepart[a].most_common():
        name_index.setdefault(nm, a)
for k in sorted(k for k in keys if kind[k] == "name"):
    if k in name_index:
        decisions.append({"variant": k, "candidate_series": name_index[k], "rule": "R7 full name of an acronym series", "decision": "merge",
                          "reason": "the name without acronym equals the series' full name"})
merge = {}
for d in decisions:
    if d["decision"] == "merge" and d["variant"] not in merge:
        merge[d["variant"]] = d["candidate_series"]


def resolve(k, seen=()):
    return resolve(merge[k], seen + (k,)) if k in merge and k not in seen else k


thes = [{"variant": v, "series": resolve(v), "rule": next(d["rule"] for d in decisions if d["variant"] == v and d["decision"] == "merge")}
        for v in sorted(merge)]
assert len(thes) <= 60, len(thes)
L.write_csv(T / "conference_series_thesaurus.csv", ["variant", "series", "rule"], thes)
L.table("T2e_series_decisions", "T2e. Conference-series candidates and decisions", ["variant", "candidate_series", "rule", "decision", "reason"],
        sorted(decisions, key=lambda d: (d["rule"], d["variant"], d["candidate_series"])))
TH = {r["variant"]: r["series"] for r in thes}
for r in confs:
    r["series"] = TH.get(r["ckey"], r["ckey"])
    r["series_kind"] = "acronym" if (kind.get(r["series"]) == "acronym" or r["series"] in acrs) else ("none" if r["ckind"] == "none" else "name")
ser = defaultdict(list)
for r in confs:
    if r["series_kind"] == "acronym":
        ser[r["series"]].append(r["year"])
srows = [{"series": s, "records": len(ys), "first_year": min(ys), "last_year": max(ys), "years": "; ".join(str(y) for y in sorted(set(ys)))}
         for s, ys in ser.items()]
srows.sort(key=lambda r: (-r["records"], r["series"].casefold(), r["series"]))
L.table("T2e_top15_series", f"T2e. Conference series, top 15 (conference papers n = {len(confs)}; {len(ser)} acronym series)",
        ["series", "records", "first_year", "last_year", "years"], srows[:15],
        "Normalisation: leading year, ordinal numbers (5th, XIX) and years removed, spaces collapsed; when the part after the last comma is an "
        "acronym with a year (e.g. 'SIST 2025', 'SNPD 2025-Summer', 'ACR'23'), the series key is the acronym; thesaurus "
        "tables/conference_series_thesaurus.csv applied. Full list: T2e_all_series.csv.")
L.write_csv(T / "T2e_all_series.csv", ["series", "records", "first_year", "last_year", "years"], srows)
rem = Counter(r["series"] for r in confs if r["series_kind"] != "acronym")
L.table("T2e_remainder", f"T2e. Conference papers without an acronym series ({sum(rem.values())} records, {len(rem)} name keys)",
        ["name_key", "records"], [{"name_key": L.cut30(k), "records": n} for k, n in sorted(rem.items(), key=lambda kv: (-kv[1], kv[0]))])
NUM["T2e"] = {"conference_papers": len(confs), "series": len(ser), "thesaurus_rows": len(thes), "remainder_records": sum(rem.values()),
              "remainder_keys": len(rem), "top15": [(r["series"], r["records"]) for r in srows[:15]]}

# ---------- step 3: citations
cites = sorted((r["cited"] for r in E1), reverse=True)
h = sum(1 for i, c in enumerate(cites, 1) if c >= i)
tot = sum(cites)
rows = [{"measure": "records", "value": N}, {"measure": "citations, total", "value": tot}, {"measure": "mean per record", "value": f"{tot / N:.2f}"},
        {"measure": "median", "value": L.median(cites)}, {"measure": "maximum", "value": cites[0]},
        {"measure": "uncited records", "value": sum(1 for c in cites if c == 0)}, {"measure": "uncited (%)", "value": L.pct(sum(1 for c in cites if c == 0), N)},
        {"measure": "records with >= 10 citations", "value": sum(1 for c in cites if c >= 10)},
        {"measure": "records with >= 50 citations", "value": sum(1 for c in cites if c >= 50)},
        {"measure": "records with >= 100 citations", "value": sum(1 for c in cites if c >= 100)}, {"measure": "h-index of the corpus", "value": h}]
L.table("T3a_citations", f"T3a. Citations ({L.CITE_DATE})", ["measure", "value"], rows)
NUM["T3a"] = {r["measure"]: r["value"] for r in rows}
rows = []
for y in L.YEARS:
    rr = [r for r in E1 if r["year"] == y]
    c = sum(r["cited"] for r in rr)
    age = 2026 - y
    rows.append({"year": y, "records": len(rr), "citations": c, "mean": f"{c / len(rr):.2f}" if rr else "",
                 "age": age, "cites_per_record_per_year": f"{c / len(rr) / age:.2f}" if rr else ""})
rows.append({"year": "2003-2025", "records": N, "citations": tot, "mean": f"{tot / N:.2f}", "age": "", "cites_per_record_per_year": ""})
L.table("T3b_citations_by_year", f"T3b. Citations by year ({L.CITE_DATE}; age = 2026 - year)", ["year", "records", "citations", "mean", "age",
                                                                                               "cites_per_record_per_year"], rows)
T3B = rows


def cite_rows(groups, label):
    out = []
    for g, rr in groups:
        cs = [r["cited"] for r in rr]
        out.append({label: g, "records": len(rr), "citations": sum(cs), "mean": f"{sum(cs) / len(rr):.2f}" if rr else "", "median": L.median(cs),
                    "uncited_pct": L.pct(sum(1 for c in cs if c == 0), len(rr))})
    return out


T3C = cite_rows([(t, [r for r in E1 if r["type_h"] == t]) for t in HTYPES], "doc_type")
L.table("T3c_citations_by_type", f"T3c. Citations by harmonised type ({L.CITE_DATE})", ["doc_type", "records", "citations", "mean", "median", "uncited_pct"], T3C)
T3D = cite_rows([(p, [r for r in E1 if r["period"] == p]) for p, _, _ in L.PERIODS], "period")
L.table("T3d_citations_by_period", f"T3d. Citations by period ({L.CITE_DATE})", ["period", "records", "citations", "mean", "median", "uncited_pct"], T3D)
top = sorted(E1, key=lambda r: (-r["cited"], r["eid"]))[:20]
rows = [{"rank": i, "eid": r["eid"], "year": r["year"], "doc_type": r["type_exp"], "source": L.cut30(r["source"]), "doi": r["DOI"].strip(),
         "cited_by": r["cited"], "cites_per_year": f"{r['cited'] / (2026 - r['year']):.1f}", "title": L.cut30(r["Title"])} for i, r in enumerate(top, 1)]
L.table("T3e_top20_cited", f"T3e. The 20 most cited records ({L.CITE_DATE}; cites_per_year = cited_by / (2026 - year))",
        ["rank", "eid", "year", "doc_type", "source", "doi", "cited_by", "cites_per_year", "title"], rows,
        f"The 20th record has {top[-1]['cited']} citations; records with that count: {sum(1 for r in E1 if r['cited'] == top[-1]['cited'])} (ties by EID).")
NUM["T3e_eids"] = [r["eid"] for r in top]
sc_ = defaultdict(list)
for r in E1:
    sc_[r["source"]].append(r["cited"])
rows = [{"rank": i, "source_title": L.cut30(s), "records": len(v), "citations": sum(v), "mean_if_n_ge_5": f"{sum(v) / len(v):.2f}" if len(v) >= 5 else ""}
        for i, (s, v) in enumerate(sorted(sc_.items(), key=lambda kv: (-sum(kv[1]), kv[0].casefold(), kv[0]))[:10], 1)]
L.table("T3f_top10_sources_by_citations", f"T3f. Top 10 sources by total citations ({L.CITE_DATE})", ["rank", "source_title", "records", "citations",
                                                                                                    "mean_if_n_ge_5"], rows)

# ---------- step 4: open access and funding
oa = [r for r in E1 if r["oa"]]
cat = Counter(c for r in E1 for c in r["oa_cats"])
rows = [{"category": "any open access (non-empty Open Access)", "n": len(oa), "pct": L.pct(len(oa), N)}] + \
       [{"category": k, "n": n, "pct": L.pct(n, N)} for k, n in sorted(cat.items(), key=lambda kv: (-kv[1], kv[0]))]
for p, _, _ in L.PERIODS:
    rr = [r for r in E1 if r["period"] == p]
    rows.append({"category": f"open access in {p}", "n": sum(1 for r in rr if r["oa"]), "pct": L.pct(sum(1 for r in rr if r["oa"]), len(rr))})
co, cn = [r["cited"] for r in oa], [r["cited"] for r in E1 if not r["oa"]]
rows += [{"category": "citations of OA records: mean / median", "n": f"{sum(co) / len(co):.2f} / {L.median(co)}", "pct": ""},
         {"category": "citations of non-OA records: mean / median", "n": f"{sum(cn) / len(cn):.2f} / {L.median(cn)}", "pct": ""}]
L.table("T4a_open_access", f"T4a. Open access (n = {N}; categories overlap; period shares use the period's records)", ["category", "n", "pct"], rows,
        "Descriptive only: OA and non-OA records differ in year, type and venue, so the citation contrast is not an OA effect.")
NUM["T4a"] = {"oa": len(oa), "categories": dict(cat)}
fu = [r for r in E1 if r["funded"]]
rows = [{"group": "all records", "records": N, "funded": len(fu), "pct": L.pct(len(fu), N)}]
rows += [{"group": p, "records": len([r for r in E1 if r["period"] == p]), "funded": sum(1 for r in fu if r["period"] == p),
          "pct": L.pct(sum(1 for r in fu if r["period"] == p), len([r for r in E1 if r["period"] == p]))} for p, _, _ in L.PERIODS]
rows += [{"group": t, "records": th[t], "funded": sum(1 for r in fu if r["type_h"] == t), "pct": L.pct(sum(1 for r in fu if r["type_h"] == t), th[t])}
         for t in HTYPES if th[t]]
rows.append({"group": "records with Sponsors (count only)", "records": N, "funded": sum(1 for r in E1 if r["Sponsors"].strip()),
             "pct": L.pct(sum(1 for r in E1 if r["Sponsors"].strip()), N)})
L.table("T4b_funding", "T4b. Records with Funding Details", ["group", "records", "funded", "pct"], rows)
NUM["T4b"] = {"funded": len(fu), "sponsors": rows[-1]["funded"]}
raw = Counter()
per_rec_raw = []
for r in E1:
    firsts = {x.split(",")[0].strip() for x in r["Funding Details"].split("; ") if x.strip()} - {""}
    per_rec_raw.append(firsts)
    raw.update(firsts)
KZ_RX = re.compile(r"(ministry of (education and science|science and higher education)|committee of science|science committee).*kazakhstan", re.I)
fthes = []
for v in sorted(raw):
    if KZ_RX.search(v):
        fthes.append({"variant": v, "canonical": KZ_MINISTRY, "rule": "Kazakhstan ministry of science / Science Committee (country named)"})
    elif re.search(r"shota rustaveli", v, re.I) or v == "SRNSFG":
        fthes.append({"variant": v, "canonical": "Shota Rustaveli National Science Foundation of Georgia",
                      "rule": "spelling variants of one foundation (a joint call with STCU counted under it)"})
    elif re.fullmatch(r"institute of information and comput(ational|er) technologies", v, re.I):
        fthes.append({"variant": v, "canonical": "Institute of Information and Computational Technologies", "rule": "one institute, two spellings"})
assert len(fthes) <= 40, len(fthes)
L.write_csv(T / "funders_thesaurus.csv", ["variant", "canonical", "rule"], fthes)
FT = {r["variant"]: r["canonical"] for r in fthes}
canon = Counter()
for s in per_rec_raw:
    canon.update({FT.get(v, v) for v in s})
L.table("T4c_top15_funders", f"T4c. Top 15 funders (first element of each Funding Details item; once per record; funded records n = {len(fu)})",
        ["funder", "n", "pct"], [{"funder": L.cut30(k), "n": n, "pct": L.pct(n, len(fu))} for k, n in sorted(canon.items(), key=lambda kv: (-kv[1], kv[0]))[:15]],
        "pct of funded records. Funding Details split on '; '; funder = text before the first comma; thesaurus tables/funders_thesaurus.csv. "
        "Unnamed-country ministries ('Ministry of Education and Science') are not merged.")
L.write_csv(T / "T4c_funder_variants_raw.csv", ["variant", "records"], [{"variant": L.cut30(k), "records": n} for k, n in sorted(raw.items(), key=lambda kv: (-kv[1], kv[0]))])
NUM["T4c"] = {"thesaurus_rows": len(fthes), "distinct_raw": len(raw), "top15": sorted(canon.items(), key=lambda kv: (-kv[1], kv[0]))[:15]}

# ---------- step 5: WoS validation on the 216 pairs


def wos_h(dt):
    if "Retracted Publication" in dt:
        return "retracted"
    if "Review" in dt:
        return "review"
    if "Proceedings Paper" in dt:
        return "conference paper"
    if "Book Chapter" in dt:
        return "book chapter"
    return "article"


P = [(e_by[p["eid"]], w_by[p["ut"]]) for p in pairs]
ct = Counter((s["type_exp"], w.get("DT", "")) for s, w in P)
rows = [{"scopus_type": a, "wos_dt": b, "n": n} for (a, b), n in sorted(ct.items(), key=lambda kv: (-kv[1], kv[0]))]
agree = sum(1 for s, w in P if s["type_h"] == wos_h(w.get("DT", "")))
rows.append({"scopus_type": "agreement after harmonisation", "wos_dt": f"{agree} of {len(P)}", "n": L.pct(agree, len(P))})
rows.append({"scopus_type": "WoS 'Retracted Publication' flag", "wos_dt": "records", "n": sum(1 for s, w in P if "Retracted Publication" in w.get("DT", ""))})
L.table("T5a_types", f"T5a. Document type, Scopus x WoS, on the {len(P)} pairs", ["scopus_type", "wos_dt", "n"], rows,
        "WoS harmonisation: Retracted Publication -> retracted (flag); else contains Review -> review; Proceedings Paper -> conference paper; Book "
        "Chapter -> book chapter; otherwise article.")
yd = Counter((L.year_of(w.get("PY")) or 0) - s["year"] for s, w in P)
rows = [{"wos_minus_scopus_year": k, "n": n} for k, n in sorted(yd.items())]
L.table("T5b_years", f"T5b. Publication year, WoS PY minus Scopus Year, on the {len(P)} pairs", ["wos_minus_scopus_year", "n"], rows)


def ranks(v):
    o = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]:
            j += 1
        for k in range(i, j + 1):
            r[o[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a) ** 0.5
    vb = sum((y - mb) ** 2 for y in b) ** 0.5
    return cov / (va * vb)


sv = [s["cited"] for s, w in P]
wv = [to_int(w.get("TC")) for s, w in P]
rho = pearson(ranks(sv), ranks(wv))
rows = [{"measure": "pairs", "value": len(P)}, {"measure": "Spearman rank correlation (average ranks for ties)", "value": f"{rho:.3f}"},
        {"measure": "median Scopus Cited by", "value": L.median(sv)}, {"measure": "median WoS TC", "value": L.median(wv)},
        {"measure": "sum Scopus Cited by", "value": sum(sv)}, {"measure": "sum WoS TC", "value": sum(wv)},
        {"measure": "Scopus > WoS", "value": sum(1 for a, b in zip(sv, wv) if a > b)}, {"measure": "equal", "value": sum(1 for a, b in zip(sv, wv) if a == b)},
        {"measure": "WoS > Scopus", "value": sum(1 for a, b in zip(sv, wv) if b > a)}]
L.table("T5c_citations", f"T5c. Citations, Scopus Cited by x WoS TC (Core Collection), on the {len(P)} pairs", ["measure", "value"], rows,
        "Both retrieved 2026-10-13.")
NUM["T5c"] = {r["measure"]: r["value"] for r in rows}
ts = {s["eid"] for s, w in sorted(P, key=lambda p: (-p[0]["cited"], p[0]["eid"]))[:20]}
tw = {s["eid"] for s, w in sorted(P, key=lambda p: (-to_int(p[1].get("TC")), p[1]["UT"]))[:20]}
rows = [{"measure": "top 20 by Scopus Cited by that are also in the top 20 by WoS TC", "value": len(ts & tw)},
        {"measure": "WoS-only records (not in the corpus, not used here)", "value": len(E2) - len(P)}]
L.table("T5d_top20_overlap", "T5d. Agreement of the most cited (216 pairs)", ["measure", "value"], rows, "Ties at the 20th place broken by EID / UT.")
NUM["T5"] = {"pairs": len(P), "type_agreement": agree, "year_equal": yd.get(0, 0), "top20_overlap": len(ts & tw)}

# ---------- step 6: deltas against F12.1
f_types = {r["doc_type"]: int(r["n"]) for r in F["types"]}
rows = []
for t in sorted(set(k.lower() for k in f_types) | set(k.lower() for k in te), key=lambda x: (-(te.get(next((k for k in te if k.lower() == x), ""), 0)), x)):
    fk = next((k for k in f_types if k.lower() == t), "")
    ek = next((k for k in te if k.lower() == t), "")
    rows.append({"doc_type_F12_1": fk, "n_F12_1": f_types.get(fk, 0), "doc_type_E1": ek, "n_E1": te.get(ek, 0), "difference": te.get(ek, 0) - f_types.get(fk, 0)})
D1 = rows
L.table("D1_types", "D1. Document types: F12.1 (September frame) against E1", ["doc_type_F12_1", "n_F12_1", "doc_type_E1", "n_E1", "difference"], rows,
        "Matched case-insensitively (F12.1 'Conference Paper' = E1 'Conference paper').")
f_src = [(int(r["rank"]), r["source_title"], int(r["n"])) for r in F["sources"]]
e_rank = {L.norm_name(r["source_title"]): (r["rank"], r["source_title"], r["records"]) for r in T2A}
e_full = {L.norm_name(s): (i, s, len(by_src[s])) for i, s in enumerate(order, 1)}
rows, seen = [], set()
for rk, s, n in f_src:
    k = L.norm_name(s)
    seen.add(k)
    er = e_full.get(k)
    rows.append({"source": L.cut30(er[1] if er else s), "rank_F12_1": rk, "n_F12_1": n, "rank_E1": er[0] if er else "", "n_E1": er[2] if er else 0,
                 "status": "in both top 20" if er and er[0] <= 20 else "left the top 20"})
for r in T2A[:20]:
    k = L.norm_name(r["source_title"])
    if k not in seen:
        rows.append({"source": r["source_title"], "rank_F12_1": "", "n_F12_1": "", "rank_E1": r["rank"], "n_E1": r["records"], "status": "entered the top 20"})
D2 = rows
L.table("D2_top20_sources", "D2. Top 20 sources: F12.1 against E1", ["source", "rank_F12_1", "n_F12_1", "rank_E1", "n_E1", "status"], rows,
        "Matched on names lowercased with punctuation removed (F12.1 stores Title Case without punctuation). n_E1 and rank_E1 are E1's full ranking. "
        f"Distinct sources: F12.1 360 (T1b note), E1 {len(order)}.")
fyt = {r["year"]: r for r in F["year_type"]}
rows = []
for y in [str(y) for y in L.YEARS] + ["2003-2025"]:
    f = fyt[y]
    if y == "2003-2025":
        ea = sum(1 for r in E1 if r["type_exp"].lower() == "article")
        ec = sum(1 for r in E1 if r["type_exp"].lower() == "conference paper")
        et = N
    else:
        rr = [r for r in E1 if r["year"] == int(y)]
        ea = sum(1 for r in rr if r["type_exp"].lower() == "article")
        ec = sum(1 for r in rr if r["type_exp"].lower() == "conference paper")
        et = len(rr)
    rows.append({"year": y, "article_F12_1": int(f["Article"]), "article_E1": ea, "conference_F12_1": int(f["Conference Paper"]), "conference_E1": ec,
                 "other_F12_1": int(f["Other"]), "other_E1": et - ea - ec, "total_F12_1": int(f["total"]), "total_E1": et})
D3 = rows
L.table("D3_year_by_type", "D3. Year by type: F12.1 against E1 (Article / Conference paper / other, exported types)",
        ["year", "article_F12_1", "article_E1", "conference_F12_1", "conference_E1", "other_F12_1", "other_E1", "total_F12_1", "total_E1"], rows)
fc = {r["year"]: r for r in F["cites"]}
i1 = {"2-s2.0-" + r["scopus_id"].strip(): (L.year_of(r["publication_year"]), to_int(r["citations_count"])) for r in I1}
left = set(i1) - set(e_by)
entered = set(e_by) - set(i1)
common = set(i1) & set(e_by)
rows = []
for y in [str(y) for y in L.YEARS] + ["2003-2025"]:
    sel = (lambda yy: True) if y == "2003-2025" else (lambda yy, y=int(y): yy == y)
    fl = sum(i1[k][1] for k in left if sel(i1[k][0]))
    en = sum(e_by[k]["cited"] for k in entered if sel(e_by[k]["year"]))
    gr = sum(e_by[k]["cited"] - i1[k][1] for k in common if sel(e_by[k]["year"]))
    e_c = sum(r["cited"] for r in E1 if sel(r["year"]))
    rows.append({"year": y, "records_F12_1": int(fc[y]["n"]), "citations_F12_1": int(fc[y]["citations_sum"]), "records_E1": sum(1 for r in E1 if sel(r["year"])),
                 "citations_E1": e_c, "difference": e_c - int(fc[y]["citations_sum"]), "minus_left_3": -fl, "plus_entered_3": en, "growth_common_838": gr})
D4 = rows
L.table("D4_citations_by_year", "D4. Citations by year: F12.1 (I1, snapshot 2026-09-01) against E1 (2026-10-13), decomposed by EID",
        ["year", "records_F12_1", "citations_F12_1", "records_E1", "citations_E1", "difference", "minus_left_3", "plus_entered_3", "growth_common_838"], rows,
        f"difference = minus_left_3 + plus_entered_3 + growth_common_838 (left: {len(left)} I1 records not in E1; entered: {len(entered)}; common: "
        f"{len(common)}). Common records are placed by their E1 year (equal to I1's on all of them).")
NUM["D4_total"] = rows[-1]
fl_ = {r["doc_language"]: int(r["n"]) for r in F["lang"]}
rows = []
for code, n in sorted(fl_.items(), key=lambda kv: (-kv[1], kv[0])):
    nm = LANG_CODES.get(code, code)
    rows.append({"language": nm, "code_F12_1": code, "n_F12_1_I2_838": n, "n_E1_841": lc.get(nm, 0)})
for nm, n in sorted(lc.items()):
    if nm not in [LANG_CODES.get(c, c) for c in fl_]:
        rows.append({"language": nm, "code_F12_1": "", "n_F12_1_I2_838": 0, "n_E1_841": n})
fo = {r["openaccess_flag"]: int(r["n"]) for r in F["oa"]}
rows.append({"language": "open access: F12.1 flag true / E1 non-empty Open Access", "code_F12_1": "openaccessFlag", "n_F12_1_I2_838": fo.get("true", 0),
             "n_E1_841": len(oa)})
rows.append({"language": "open access: F12.1 flag false or missing", "code_F12_1": "false / (missing)", "n_F12_1_I2_838": fo.get("false", 0) + fo.get("(missing)", 0),
             "n_E1_841": N - len(oa)})
D5 = rows
L.table("D5_language_oa", "D5. Language and open access: F12.1 (I2 Abstract Retrieval, 838) against E1 (export, 841)",
        ["language", "code_F12_1", "n_F12_1_I2_838", "n_E1_841"], rows,
        "Different fields: F12.1 used the Abstract Retrieval language code and openaccessFlag; E1 uses 'Language of Original Document' and 'Open Access'.")
NUM["D"] = {"D1": D1, "D2": D2, "D3_total": D3[-1], "D4_total": D4[-1], "D5": D5}

# ---------- step 7: the figure
FIG = L.FIGURES
FIG.mkdir(parents=True, exist_ok=True)
L.write_csv(FIG / "Fig_annual_output_by_type.csv", T1C_FIELDS, T1C)
fig, ax = plt.subplots(figsize=(9, 4.8))
xs = list(L.YEARS)
bottom = [0] * len(xs)
labels = {"article": "Article", "conference paper": "Conference paper", "book chapter": "Book chapter", "review": "Review", "book": "Book",
          "retracted": "Retracted"}
for t in HTYPES:
    vals = [grid[y][t] for y in xs]
    ax.bar(xs, vals, bottom=bottom, color=COLORS[t], label=labels[t], width=0.75)
    bottom = [b + v for b, v in zip(bottom, vals)]
ax.set_xlabel("Publication year")
ax.set_ylabel("Records")
ax.set_xticks([y for y in xs if y % 2 == 1])
ax.tick_params(axis="x", labelsize=8)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.legend(frameon=False, loc="upper left")
fig.tight_layout()
base = FIG / "Fig_annual_output_by_type"
fig.savefig(str(base) + ".pdf", metadata={"CreationDate": None, "ModDate": None, "Producer": None, "Creator": None})
fig.savefig(str(base) + ".png", dpi=300, metadata={"Software": None})
plt.close(fig)
with Image.open(str(base) + ".png") as im:
    im.convert("RGB").save(str(base) + ".tif", compression="tiff_lzw", dpi=(300, 300))
NUM["figure"] = {"colors": COLORS}
NUM["f131_years_equal"] = all(int(r["E1"]) == yc.get(int(r["year"]), 0) for r in f131y if r["year"].isdigit())
L.jdump(NUM, L.OUT / "F13_2_numbers.json")
print(json.dumps({"N": N, "types": NUM["T1b"]["harmonised"], "sources": NUM["T2a"]["sources"], "zones": NUM["T2a"]["zones"],
                  "series": NUM["T2e"]["series"], "conf_thesaurus": NUM["T2e"]["thesaurus_rows"], "h": NUM["T3a"]["h-index of the corpus"],
                  "cites": NUM["T3a"]["citations, total"], "oa": NUM["T4a"]["oa"], "funded": NUM["T4b"]["funded"],
                  "funder_thesaurus": NUM["T4c"]["thesaurus_rows"], "T5": NUM["T5"], "rho": NUM["T5c"]["Spearman rank correlation (average ranks for ties)"],
                  "f131_years_equal": NUM["f131_years_equal"]}, ensure_ascii=False, indent=1))
