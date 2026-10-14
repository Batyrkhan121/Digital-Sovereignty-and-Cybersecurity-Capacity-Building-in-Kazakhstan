"""Phase F13.1 - steps 1-5: parse and validate E1/E1b/E2, reconcile E1 with the September frame I1 and the June layer I3,
match E1 <-> E2 (DOI, then normalised title, one-to-one), build the merged corpus M (data/) with its codebook, and the topic-share
table T5. Tables hold counts only: no abstract, reference text, author name or contact detail is written to tables/ or printed.
Deterministic: every list has a full sort key; no timestamp in any table or data file."""
import sys
sys.dont_write_bytecode = True

import html
import json
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f131_lib as L

NUM = {}
FRAME_SERIES = [2, 1, 3, 7, 3, 12, 13, 16, 21, 38, 61, 67, 55, 73, 79, 145, 245]
FRAME_TYPES = {"Article": 398, "Conference Paper": 386, "Book Chapter": 32, "Review": 21, "Book": 2, "Retracted": 2}
COUNTRY_MAP = {"USA": "United States", "Peoples R China": "China", "Russia": "Russian Federation", "England": "United Kingdom",
               "Scotland": "United Kingdom", "Wales": "United Kingdom", "North Ireland": "United Kingdom", "Turkiye": "Turkey",
               "South Korea": "South Korea", "Korea": "South Korea", "Viet Nam": "Vietnam", "U Arab Emirates": "United Arab Emirates",
               "Czech Republic": "Czech Republic", "Byelarus": "Belarus"}
TYPE_MAP = {"article": "article", "review": "review", "conference paper": "conference paper", "book chapter": "book chapter", "book": "book"}


def split_semi(s):
    return [x.strip() for x in (s or "").split(";") if x.strip()]


def counts_rows(ctr, key, denom):
    return [{key: k, "n": n, "pct": L.pct(n, denom)} for k, n in sorted(ctr.items(), key=lambda kv: (-kv[1], str(kv[0])))]


# ---------- step 1: parse
cols1, E1 = L.parse_scopus(L.E1)
drop1 = dict(L.parse_scopus.dropped_nonempty)
cols1b, E1B = L.parse_scopus(L.E1B)
seen2, E2 = L.parse_wos(L.E2)
eid1 = [r["EID"].strip() for r in E1]
eid1b = [r["EID"].strip() for r in E1B]
ut2 = [L.wos_val(r, "UT") for r in E2]
rows = [{"file": "E1 Scopus full", "records": len(E1), "unique_ids": len(set(eid1)), "id": "EID", "columns_or_tags": len(cols1)},
        {"file": "E1b Scopus citation+abstract", "records": len(E1B), "unique_ids": len(set(eid1b)), "id": "EID", "columns_or_tags": len(cols1b)},
        {"file": "E2 WoS Core Collection", "records": len(E2), "unique_ids": len(set(ut2)), "id": "UT", "columns_or_tags": len(seen2)}]
L.table("T1a_counts", "T1a. Records and identifiers", ["file", "records", "unique_ids", "id", "columns_or_tags"], rows,
        f"E1 = {L.E1}; E1b = {L.E1B}; E2 = {L.E2}.")
NUM["T1a"] = rows

r1b = []
for c in cols1:
    n = drop1[c] if c in drop1 else sum(1 for r in E1 if (r.get(c) or "").strip())
    r1b.append({"source": "E1", "field": c, "non_empty": n, "pct": L.pct(n, len(E1)), "note": "dropped by the parser; counted only" if c in drop1 else ""})
for t in sorted(seen2):
    n = seen2[t] if t in L.WOS_DROP else sum(1 for r in E2 if any(x.strip() for x in r.get(t, [])))
    r1b.append({"source": "E2", "field": t, "non_empty": n, "pct": L.pct(n, len(E2)), "note": "dropped by the parser; counted only" if t in L.WOS_DROP else ""})
L.table("T1b_completeness", "T1b. Field completeness (non-empty values)", ["source", "field", "non_empty", "pct", "note"], r1b,
        "E1: all 45 exported columns (n = 841). E2: every tag present (n = 231). Correspondence Address, EM, OI, RI and RP are counted "
        "by the parser and never kept.")
NUM["T1b"] = {f"{r['source']}:{r['field']}": r["non_empty"] for r in r1b}

common = ["Title", "Year", "DOI", "Abstract", "Author Keywords", "Index Keywords", "Cited by"]
b_by = {r["EID"].strip(): r for r in E1B}
r1c = [{"check": "EID sets equal", "value": int(set(eid1) == set(eid1b)), "detail": f"E1 {len(set(eid1))}, E1b {len(set(eid1b))}, common {len(set(eid1) & set(eid1b))}"}]
for c in common:
    eq = sum(1 for r in E1 if r["EID"].strip() in b_by and (r.get(c) or "") == (b_by[r["EID"].strip()].get(c) or ""))
    r1c.append({"check": f"column '{c}' equal per record", "value": eq, "detail": f"of {len(E1)}; differing {len(E1) - eq}"})
L.table("T1c_E1_vs_E1b", "T1c. E1 against its control copy E1b", ["check", "value", "detail"], r1c)
NUM["T1c"] = {r["check"]: r["value"] for r in r1c}

lens, nref1 = [], []
for r in E1:
    ref = r.get("References") or ""
    if ref.strip():
        lens.append(len(ref))
        nref1.append(len([x for x in ref.split("; ") if x.strip()]))
nr_tag = [int(L.wos_val(r, "NR") or 0) for r in E2]
cr_lines = [len([x for x in r.get("CR", []) if x.strip()]) for r in E2]
r1d = [
    {"measure": "E1 records with References", "value": len(lens)},
    {"measure": "E1 References length, max (characters)", "value": max(lens) if lens else ""},
    {"measure": "E1 References length, median", "value": L.median(lens)},
    {"measure": "E1 References longer than 32,000 characters (Excel cell limit)", "value": sum(1 for x in lens if x > 32000)},
    {"measure": "E1 references per record after splitting on '; ' - median", "value": L.median(nref1)},
    {"measure": "E1 references per record - max", "value": max(nref1) if nref1 else ""},
    {"measure": "E1 references, total", "value": sum(nref1)},
    {"measure": "E2 records with CR lines", "value": sum(1 for x in cr_lines if x)},
    {"measure": "E2 CR lines per record - median", "value": L.median(cr_lines)},
    {"measure": "E2 CR lines, total", "value": sum(cr_lines)},
    {"measure": "E2 records whose CR line count equals NR", "value": sum(1 for a, b in zip(cr_lines, nr_tag) if a == b)},
    {"measure": "E2 records whose CR line count differs from NR", "value": sum(1 for a, b in zip(cr_lines, nr_tag) if a != b)},
    {"measure": "E2 NR, total", "value": sum(nr_tag)},
]
L.table("T1d_references", "T1d. Reference lists", ["measure", "value"], r1d,
        "Counts only; no reference text is written. A Scopus reference containing '; ' inside itself would be split twice (upper bound).")
NUM["T1d"] = {r["measure"]: r["value"] for r in r1d}

# ---------- step 2: E1 against I1 (frame) and I3 (June)
I1 = L.read_csv(L.I1)
I3 = L.read_csv(L.I3)
e1_by = {r["EID"].strip(): r for r in E1}
r2a, mism = [], {}
for tag, ref in (("I1 frame (September, n = 841)", I1), ("I3 June structural layer (n = 931)", I3)):
    ids = {"2-s2.0-" + r["scopus_id"].strip(): r for r in ref}
    com = set(ids) & set(e1_by)
    r2a.append({"against": tag, "common": len(com), "only_E1": len(set(e1_by) - set(ids)), "only_reference": len(set(ids) - set(e1_by))})
    if tag.startswith("I1"):
        yd, td, tdi, dd, sd = Counter(), Counter(), Counter(), 0, 0
        for k in com:
            a, b = e1_by[k], ids[k]
            ya, yb = L.year_of(a.get("Year")), L.year_of(b.get("publication_year"))
            if ya != yb:
                yd[f"E1 minus I1 = {(ya or 0) - (yb or 0):+d}"] += 1
            if (a.get("Document Type") or "").strip() != (b.get("doc_type") or "").strip():
                td[f"{(b.get('doc_type') or '').strip()} -> {(a.get('Document Type') or '').strip()}"] += 1
            if (a.get("Document Type") or "").strip().lower() != (b.get("doc_type") or "").strip().lower():
                tdi[f"{(b.get('doc_type') or '').strip()} -> {(a.get('Document Type') or '').strip()}"] += 1
            if L.norm_doi(a.get("DOI")) != L.norm_doi(b.get("doi")):
                dd += 1
            if L.norm_title(a.get("Source title")) != L.norm_title(b.get("source_title")):
                sd += 1
        mism = {"year": dict(yd), "doc_type": dict(td), "doc_type_ci": dict(tdi), "doi": dd, "source_title": sd, "common": len(com)}
L.table("T2a_E1_vs_frame", "T2a. E1 against the frame I1 and the June layer I3 (by EID)", ["against", "common", "only_E1", "only_reference"], r2a,
        "EID = '2-s2.0-' + scopus_id. I3 is the June export of a different query (F12.1), shown for scale.")
rows = [{"field": "Year", "differing": sum(mism["year"].values()), "breakdown": "; ".join(f"{k}: {v}" for k, v in sorted(mism["year"].items()))},
        {"field": "Document Type", "differing": sum(mism["doc_type"].values()),
         "breakdown": "; ".join(f"{k}: {v}" for k, v in sorted(mism["doc_type"].items(), key=lambda kv: (-kv[1], kv[0])))},
        {"field": "Document Type, case-insensitive", "differing": sum(mism["doc_type_ci"].values()),
         "breakdown": "; ".join(f"{k}: {v}" for k, v in sorted(mism["doc_type_ci"].items(), key=lambda kv: (-kv[1], kv[0])))},
        {"field": "DOI (normalised)", "differing": mism["doi"], "breakdown": ""},
        {"field": "Source title (normalised)", "differing": mism["source_title"], "breakdown": ""}]
L.table("T2a2_field_differences", f"T2a. Field differences on the {mism['common']} records common to E1 and I1", ["field", "differing", "breakdown"], rows,
        "Breakdowns are counts (I1 type -> E1 type; year difference); no titles.")
NUM["T2a"] = r2a
NUM["T2a_diff"] = mism
ye1 = Counter(L.year_of(r.get("Year")) for r in E1)
yi1 = Counter(L.year_of(r.get("publication_year")) for r in I1)
r2b = [{"year": y, "E1": ye1.get(y, 0), "frame_I1": yi1.get(y, 0), "difference": ye1.get(y, 0) - yi1.get(y, 0)} for y in L.YEARS]
r2b.append({"year": "2003-2025", "E1": sum(ye1.get(y, 0) for y in L.YEARS), "frame_I1": sum(yi1.get(y, 0) for y in L.YEARS),
            "difference": sum(ye1.get(y, 0) - yi1.get(y, 0) for y in L.YEARS)})
L.table("T2b_years", "T2b. Annual series, E1 against the frame", ["year", "E1", "frame_I1", "difference"], r2b,
        f"The brief's frame series (non-zero years) {FRAME_SERIES} equals I1's: {[yi1[y] for y in L.YEARS if yi1.get(y)] == FRAME_SERIES}.")
NUM["T2b_frame_series_equals_brief"] = [yi1[y] for y in L.YEARS if yi1.get(y)] == FRAME_SERIES
te1 = Counter((r.get("Document Type") or "").strip() for r in E1)
ti1 = Counter((r.get("doc_type") or "").strip() for r in I1)
r2c = [{"doc_type": t, "E1": te1.get(t, 0), "frame_I1": ti1.get(t, 0), "difference": te1.get(t, 0) - ti1.get(t, 0)}
       for t in sorted(set(te1) | set(ti1), key=lambda t: (-(te1.get(t, 0) + ti1.get(t, 0)), t))]
L.table("T2c_doc_types", "T2c. Document types, E1 against the frame", ["doc_type", "E1", "frame_I1", "difference"], r2c,
        f"The brief's frame types {FRAME_TYPES} equal I1's: {dict(ti1) == FRAME_TYPES}.")
NUM["T2c"] = {"E1": dict(te1), "I1": dict(ti1)}

# ---------- step 3: E1 <-> E2
def recs1():
    return sorted(({"id": r["EID"].strip(), "doi": L.norm_doi(r.get("DOI")), "tn": L.norm_title(r.get("Title"))} for r in E1), key=lambda x: x["id"])


def recs2():
    return sorted(({"id": L.wos_val(r, "UT"), "doi": L.norm_doi(L.wos_val(r, "DI")), "tn": L.norm_title(L.wos_val(r, "TI"))} for r in E2),
                  key=lambda x: x["id"])


def match(A, B):
    used_a, used_b, pairs = set(), set(), []
    bd = defaultdict(list)
    for b in B:
        if b["doi"]:
            bd[b["doi"]].append(b["id"])
    for a in A:
        if a["doi"]:
            for bid in bd.get(a["doi"], []):
                if bid not in used_b:
                    pairs.append((a["id"], bid, "doi"))
                    used_a.add(a["id"])
                    used_b.add(bid)
                    break
    bt = defaultdict(list)
    for b in B:
        if b["id"] not in used_b and b["tn"]:
            bt[b["tn"]].append(b["id"])
    for a in A:
        if a["id"] in used_a or not a["tn"]:
            continue
        for bid in bt.get(a["tn"], []):
            if bid not in used_b:
                pairs.append((a["id"], bid, "title"))
                used_a.add(a["id"])
                used_b.add(bid)
                break
    return pairs


A, B = recs1(), recs2()
pairs = match(A, B)
pairs_rev = [(a, b, h) for b, a, h in match(B, A)]
NUM["symmetry"] = {"equal": sorted(pairs) == sorted(pairs_rev), "from_scopus": len(pairs), "from_wos": len(pairs_rev)}
pe, pu = {a for a, b, h in pairs}, {b for a, b, h in pairs}
w_by = {L.wos_val(r, "UT"): r for r in E2}
only1 = sorted(set(e1_by) - pe)
only2 = sorted(set(w_by) - pu)
inter = len(pairs)
r3a = [{"measure": "E1 Scopus", "n": len(E1)}, {"measure": "E2 WoS", "n": len(E2)},
       {"measure": "pairs by DOI", "n": sum(1 for p in pairs if p[2] == "doi")},
       {"measure": "pairs by normalised title", "n": sum(1 for p in pairs if p[2] == "title")},
       {"measure": "intersection", "n": inter}, {"measure": "only Scopus", "n": len(only1)}, {"measure": "only WoS", "n": len(only2)},
       {"measure": "union", "n": inter + len(only1) + len(only2)},
       {"measure": "share of WoS records also in Scopus (%)", "n": L.pct(inter, len(E2))},
       {"measure": "share of Scopus records also in WoS (%)", "n": L.pct(inter, len(E1))}]
L.table("T3a_scopus_wos", "T3a. Scopus E1 against WoS E2", ["measure", "n"], r3a,
        "DOI: lowercase, prefixes https://doi.org/, http://dx.doi.org/, doi: removed. Title: lowercase, [^a-z0-9] to space, collapsed. "
        "DOI first, then exact normalised title among the unmatched; one-to-one; greedy in sorted id order; run both ways.")
NUM["T3a"] = {r["measure"]: r["n"] for r in r3a}
L.write_csv(L.TABLES / "T3a_pairs.csv", ["eid", "ut", "matched_by"], [{"eid": a, "ut": b, "matched_by": h} for a, b, h in sorted(pairs)])

parts = []
for tag, label in (("DT", "document type"), ("PY", "year"), ("SO", "source"), ("WE", "edition"), ("LA", "language")):
    ctr = Counter()
    for u in only2:
        vals = w_by[u].get(tag, [])
        if tag == "WE":
            for v in vals:
                ctr[html.unescape(v.strip())] += 1
        else:
            ctr[" ".join(vals).strip() or "(empty)"] += 1
    rows = counts_rows(ctr, "value", len(only2))
    parts.append(L.table(f"T3b_only_wos_{tag}", f"T3b. Only-WoS records by {label} ({tag}) (n = {len(only2)})", ["value", "n", "pct"], rows,
                         "Editions: a record may carry several WE lines; each is counted." if tag == "WE" else ""))
NUM["T3b_n"] = len(only2)
for col, label, key in (("Document Type", "document type", "doc_type"), ("Year", "year", "year"), ("Source title", "source", "source")):
    ctr = Counter((e1_by[e].get(col) or "").strip() or "(empty)" for e in only1)
    L.table(f"T3c_only_scopus_{key}", f"T3c. Only-Scopus records by {label} (n = {len(only1)})", ["value", "n", "pct"], counts_rows(ctr, "value", len(only1)))
NUM["T3c_n"] = len(only1)
sc, wn = [], []
for a, b, h in pairs:
    ref = e1_by[a].get("References") or ""
    sc.append(len([x for x in ref.split("; ") if x.strip()]))
    wn.append(int(L.wos_val(w_by[b], "NR") or 0))
r3d = [{"measure": "pairs", "value": len(pairs)},
       {"measure": "Scopus references per record - median", "value": L.median(sc)},
       {"measure": "WoS NR per record - median", "value": L.median(wn)},
       {"measure": "Scopus > WoS", "value": sum(1 for x, y in zip(sc, wn) if x > y)},
       {"measure": "equal", "value": sum(1 for x, y in zip(sc, wn) if x == y)},
       {"measure": "Scopus < WoS", "value": sum(1 for x, y in zip(sc, wn) if x < y)},
       {"measure": "Scopus references, total", "value": sum(sc)}, {"measure": "WoS NR, total", "value": sum(wn)}]
L.table("T3d_reference_counts", "T3d. Reference counts on the records in both databases", ["measure", "value"], r3d)
NUM["T3d"] = {r["measure"]: r["value"] for r in r3d}

# ---------- step 4: the merged corpus M


def countries_scopus(aff):
    out = set()
    for a in split_semi(aff):
        c = a.split(",")[-1].strip().rstrip(".")
        if c:
            out.add(COUNTRY_MAP.get(c, c))
    return out


def countries_wos(c1_lines):
    out = set()
    for line in c1_lines:
        s = line.split("]", 1)[1] if line.startswith("[") and "]" in line else line
        c = s.strip().rstrip(".").split(",")[-1].strip()
        if c.endswith(" USA") or c == "USA":
            c = "USA"
        if c:
            out.add(COUNTRY_MAP.get(c, c))
    return out


def harmonise(st, wt):
    if st:
        return TYPE_MAP.get(st.strip().lower(), "other")
    w = wt or ""
    if "Review" in w:
        return "review"
    if "Proceedings Paper" in w:
        return "conference paper"
    if "Book Chapter" in w:
        return "book chapter"
    if "Article" in w:
        return "article"
    if "Book" in w:
        return "book"
    return "other"


def union_kw(a, b):
    seen, out = set(), []
    for k in split_semi(a) + split_semi(b):
        if k.lower() not in seen:
            seen.add(k.lower())
            out.append(k)
    return "; ".join(out)


pair_by_e = {a: b for a, b, h in pairs}
works = []
for e in sorted(e1_by):
    s = e1_by[e]
    w = w_by.get(pair_by_e.get(e, ""), None)
    ref = s.get("References") or ""
    works.append({
        "eid": e, "ut": L.wos_val(w, "UT") if w else "", "doi": L.norm_doi(s.get("DOI")) or (L.norm_doi(L.wos_val(w, "DI")) if w else ""),
        "title": (s.get("Title") or "").strip(), "year": L.year_of(s.get("Year")), "doc_type_scopus": (s.get("Document Type") or "").strip(),
        "doc_type_wos": L.wos_val(w, "DT") if w else "", "source_title": (s.get("Source title") or "").strip(),
        "issn": (s.get("ISSN") or "").strip() or (L.wos_val(w, "SN") if w else ""),
        "language": (s.get("Language of Original Document") or "").strip(), "n_authors": len(split_semi(s.get("Authors"))),
        "author_names": "; ".join(split_semi(s.get("Authors"))), "affiliations": (s.get("Affiliations") or "").strip(),
        "countries": "; ".join(sorted(countries_scopus(s.get("Affiliations")))),
        "author_keywords": union_kw(s.get("Author Keywords"), L.wos_val(w, "DE") if w else ""),
        "index_keywords": (s.get("Index Keywords") or "").strip(), "keywords_plus": L.wos_val(w, "ID") if w else "",
        "abstract": (s.get("Abstract") or "").strip(), "references_raw": ref.strip(),
        "n_references": len([x for x in ref.split("; ") if x.strip()]), "cited_by_scopus": (s.get("Cited by") or "").strip(),
        "times_cited_wos": L.wos_val(w, "TC") if w else "", "open_access": int(bool((s.get("Open Access") or "").strip()) or bool(w and L.wos_val(w, "OA"))),
        "in_scopus": 1, "in_wos": int(w is not None), "funding_details_scopus": (s.get("Funding Details") or "").strip(),
        "funding_wos": L.wos_val(w, "FU") if w else ""})
for u in only2:
    w = w_by[u]
    cr = [x.strip() for x in w.get("CR", []) if x.strip()]
    works.append({
        "eid": "", "ut": u, "doi": L.norm_doi(L.wos_val(w, "DI")), "title": L.wos_val(w, "TI"), "year": L.year_of(L.wos_val(w, "PY")),
        "doc_type_scopus": "", "doc_type_wos": L.wos_val(w, "DT"), "source_title": L.wos_val(w, "SO"), "issn": L.wos_val(w, "SN"),
        "language": L.wos_val(w, "LA"), "n_authors": len([x for x in w.get("AU", []) if x.strip()]),
        "author_names": "; ".join(x.strip() for x in w.get("AF", []) if x.strip()), "affiliations": "",
        "countries": "; ".join(sorted(countries_wos(w.get("C1", [])))), "author_keywords": union_kw("", L.wos_val(w, "DE")),
        "index_keywords": "", "keywords_plus": L.wos_val(w, "ID"), "abstract": L.wos_val(w, "AB"), "references_raw": " | ".join(cr),
        "n_references": len(cr), "cited_by_scopus": "", "times_cited_wos": L.wos_val(w, "TC"), "open_access": int(bool(L.wos_val(w, "OA"))),
        "in_scopus": 0, "in_wos": 1, "funding_details_scopus": "", "funding_wos": L.wos_val(w, "FU")})
for x in works:
    x["doc_type_harmonised"] = harmonise(x["doc_type_scopus"], x["doc_type_wos"])
works.sort(key=lambda x: (x["year"] or 0, x["eid"] or "~", x["ut"]))
for i, x in enumerate(works, 1):
    x["work_id"] = f"W{i:04d}"
MF = ["work_id", "eid", "ut", "doi", "title", "year", "doc_type_scopus", "doc_type_wos", "doc_type_harmonised", "source_title", "issn",
      "language", "n_authors", "author_names", "affiliations", "countries", "author_keywords", "index_keywords", "keywords_plus", "abstract",
      "references_raw", "n_references", "cited_by_scopus", "times_cited_wos", "open_access", "in_scopus", "in_wos", "funding_details_scopus",
      "funding_wos"]
L.write_csv(L.DATA / "merged_corpus_2026-10-13.csv", MF, works)
codebook = f"""# Codebook - merged corpus M (data/merged_corpus_2026-10-13.csv)

One row per work: the {len(E1)} Scopus records of E1 (of which {inter} matched to a WoS record of E2) and the {len(only2)} WoS-only records.
Rows sorted by year, then EID (WoS-only rows after the Scopus rows of their year, by UT); work_id = W0001... in that order.
Excluded and never copied: Scopus 'Correspondence Address'; WoS tags EM, OI, RI, RP (dropped by the parser).

| field | rule |
| --- | --- |
| work_id | sequential id W0001-W{len(works):04d} |
| eid / ut | Scopus EID / WoS UT (empty when absent) |
| doi | normalised: lowercase, prefixes https://doi.org/, http://dx.doi.org/, doi: removed; Scopus first, else WoS DI |
| title, year | Scopus Title and Year; WoS-only rows: TI and PY |
| doc_type_scopus / doc_type_wos | as exported (Document Type / DT) |
| doc_type_harmonised | from the Scopus type when present: Article -> article, Review -> review, Conference Paper -> conference paper, Book Chapter -> book chapter, Book -> book, anything else (e.g. Retracted, Erratum) -> other; WoS-only rows: DT containing Review -> review, else Proceedings Paper -> conference paper, else Book Chapter -> book chapter, else Article -> article, else Book -> book, else other |
| source_title, issn, language | Scopus Source title, ISSN (else WoS SN), Language of Original Document; WoS-only rows: SO, SN, LA |
| n_authors, author_names | Scopus Authors split on ';'; WoS-only rows: AU lines (count) and AF lines (names), joined with '; ' |
| affiliations | Scopus Affiliations as exported (empty for WoS-only rows) |
| countries | Scopus: the last comma-separated element of each ';'-separated affiliation; WoS-only rows: the last comma-separated element of each C1 line (text after the bracketed author list), any '... USA' -> USA; then the map {json.dumps(COUNTRY_MAP, ensure_ascii=False)}; unique, sorted, '; ' |
| author_keywords | union of Scopus Author Keywords and WoS DE, case-insensitive de-duplication, first spelling kept, '; ' |
| index_keywords / keywords_plus | Scopus Index Keywords / WoS ID |
| abstract | Scopus Abstract; WoS-only rows: AB |
| references_raw | Scopus References as exported ('; ' between references); WoS-only rows: the CR lines joined with ' / ' written as ' | ' |
| n_references | Scopus References split on '; ' (non-empty items); WoS-only rows: number of CR lines |
| cited_by_scopus / times_cited_wos | Scopus Cited by (2026-10-13) / WoS TC (Core Collection) |
| open_access | 1 if Scopus Open Access or WoS OA is non-empty, else 0 |
| in_scopus / in_wos | 1 if the work is in E1 / E2 |
| funding_details_scopus / funding_wos | Scopus Funding Details / WoS FU |
"""
(L.DATA / "codebook.md").write_bytes(codebook.encode("utf-8"))
NUM["M"] = {"rows": len(works), "in_scopus": sum(x["in_scopus"] for x in works), "in_wos": sum(x["in_wos"] for x in works),
            "both": sum(1 for x in works if x["in_scopus"] and x["in_wos"]), "open_access": sum(x["open_access"] for x in works)}
yt = defaultdict(Counter)
for x in works:
    yt[x["year"]]["both" if x["in_scopus"] and x["in_wos"] else "scopus_only" if x["in_scopus"] else "wos_only"] += 1
r4 = [{"year": y, "scopus_only": yt[y]["scopus_only"], "both": yt[y]["both"], "wos_only": yt[y]["wos_only"], "total": sum(yt[y].values())} for y in L.YEARS]
outside = sum(sum(c.values()) for y, c in yt.items() if y not in L.YEARS)
r4.append({"year": "2003-2025", **{k: sum(r[k] for r in r4) for k in ("scopus_only", "both", "wos_only", "total")}})
L.table("T4_merged_by_year", f"T4. Merged corpus M by year and source flags (n = {len(works)})", ["year", "scopus_only", "both", "wos_only", "total"], r4,
        f"Rows outside 2003-2025: {outside}.")
ht = Counter(x["doc_type_harmonised"] for x in works)
L.table("T4_merged_by_type", f"T4. Merged corpus M by harmonised document type (n = {len(works)})", ["value", "n", "pct"], counts_rows(ht, "value", len(works)),
        "Rule in the codebook.")
fl = [{"flag": "in_scopus", "n": NUM["M"]["in_scopus"]}, {"flag": "in_wos", "n": NUM["M"]["in_wos"]}, {"flag": "both", "n": NUM["M"]["both"]},
      {"flag": "open_access", "n": NUM["M"]["open_access"]}, {"flag": "rows", "n": len(works)}]
L.table("T4_merged_flags", "T4. Merged corpus M: flags", ["flag", "n"], fl)

# ---------- step 5: topic share by year


def series(name):
    return {int(r["year"]): int(r["documents"]) for r in L.read_csv(L.EXP + name)}


kz, wt_, wa = series("scopus_years_KZ_all.csv"), series("scopus_years_world_topic.csv"), series("scopus_years_world_all.csv")
r5 = []
for y in L.YEARS:
    sk = ye1.get(y, 0) / kz[y] if kz.get(y) else None
    sw = wt_[y] / wa[y] if wa.get(y) else None
    r5.append({"year": y, "topic_KZ_E1": ye1.get(y, 0), "KZ_all": kz.get(y, 0), "share_KZ_pct": f"{100 * sk:.3f}" if sk is not None else "",
               "topic_world": wt_.get(y, 0), "world_all": wa.get(y, 0), "share_world_pct": f"{100 * sw:.3f}" if sw is not None else "",
               "activity_index": f"{sk / sw:.3f}" if sk is not None and sw else ""})
tk, ta, tw, tA = sum(ye1.get(y, 0) for y in L.YEARS), sum(kz.get(y, 0) for y in L.YEARS), sum(wt_.get(y, 0) for y in L.YEARS), sum(wa.get(y, 0) for y in L.YEARS)
r5.append({"year": "2003-2025", "topic_KZ_E1": tk, "KZ_all": ta, "share_KZ_pct": f"{100 * tk / ta:.3f}", "topic_world": tw, "world_all": tA,
           "share_world_pct": f"{100 * tw / tA:.3f}", "activity_index": f"{(tk / ta) / (tw / tA):.3f}"})
f5 = ["year", "topic_KZ_E1", "KZ_all", "share_KZ_pct", "topic_world", "world_all", "share_world_pct", "activity_index"]
L.table("T5_topic_share", "T5. Topic share by year: Kazakhstan (E1 / all KZ output) and world (topic / all output)", f5, r5,
        "share_KZ = E1 records of the year / scopus_years_KZ_all; share_world = scopus_years_world_topic / scopus_years_world_all; "
        "activity index = share_KZ / share_world. Year series transcribed from the Scopus interface (README_exports.txt). Table only.")
NUM["T5_total"] = r5[-1]
L.jdump(NUM, L.OUT / "F13_1_numbers.json")
print(json.dumps({"T1a": [(r["file"], r["records"], r["unique_ids"]) for r in NUM["T1a"]], "T2a": NUM["T2a"], "T3a": NUM["T3a"], "M": NUM["M"],
                  "symmetry": NUM["symmetry"], "T5_total": NUM["T5_total"]["activity_index"]}, ensure_ascii=False, indent=1))
