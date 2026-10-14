"""Phase F12.4 - steps 1-5: S <-> O matching on the harmonised H4Q title-only pair, the composition of the only-OpenAlex and
only-Scopus sets, the bridge to the June I3 <-> I4 divergence, and the union-by-year figure.

Matching rule (both pairs of files): DOI equality first, then exact equality of normalised titles among the still unmatched;
one-to-one; greedy in sorted id order; run from both sides and compared (gate G3). Only ids, titles (<= 30 words), years,
sources, types and DOIs leave this program - never the author columns."""
import sys
sys.dont_write_bytecode = True

import json
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f124_lib as L

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

YEARS = list(range(2003, 2026))
PERIODS = [("2003-2016", 2003, 2016), ("2017-2021", 2017, 2021), ("2022-2025", 2022, 2025)]
T, F = L.TABLES, L.FIGURES
NUM = {}
COLORS = {"only Scopus": "#1f4e79", "both": "#9e9e9e", "only OpenAlex": "#d97a1e"}


def recs(rel, id_col, year_col, src_col, type_col):
    out = []
    for r in L.read_csv(rel):
        out.append({"id": r[id_col].strip(), "doi_raw": (r.get("doi") or "").strip(), "doi": L.norm_doi(r.get("doi")),
                    "title": r.get("title") or "", "tn": L.norm_title(r.get("title")), "year": L.year_of(r.get(year_col)),
                    "source": (r.get(src_col) or "").strip(), "type": (r.get(type_col) or "").strip()})
    return sorted(out, key=lambda x: x["id"])


def match(A, B):
    """Pairs (a_id, b_id, how): DOI first, then normalised title, one-to-one, greedy in sorted id order."""
    used_a, used_b, pairs = set(), set(), []
    bdoi = defaultdict(list)
    for b in B:
        if b["doi"]:
            bdoi[b["doi"]].append(b["id"])
    for a in A:
        if a["doi"]:
            for bid in bdoi.get(a["doi"], []):
                if bid not in used_b:
                    pairs.append((a["id"], bid, "doi"))
                    used_a.add(a["id"])
                    used_b.add(bid)
                    break
    btit = defaultdict(list)
    for b in B:
        if b["id"] not in used_b and b["tn"]:
            btit[b["tn"]].append(b["id"])
    for a in A:
        if a["id"] in used_a or not a["tn"]:
            continue
        for bid in btit.get(a["tn"], []):
            if bid not in used_b:
                pairs.append((a["id"], bid, "title"))
                used_a.add(a["id"])
                used_b.add(bid)
                break
    return pairs


def both_ways(A, B):
    p1 = match(A, B)
    p2 = [(a, b, h) for b, a, h in match(B, A)]
    return p1, {"from_A_equals_from_B": sorted(p1) == sorted(p2), "pairs_from_A": len(p1), "pairs_from_B": len(p2)}


def counts_table(name, title, ctr, denom, note, key="value"):
    rows = [{key: k, "n": n, "pct": L.pct(n, denom)} for k, n in sorted(ctr.items(), key=lambda kv: (-kv[1], str(kv[0])))]
    L.write_csv(T / f"{name}.csv", [key, "n", "pct"], rows)
    return L.write_md(T / f"{name}.md", title, [key, "n", "pct"], rows, note)


S = recs(L.S, "scopus_id", "publication_year", "source_title", "doc_type")
O = recs(L.O, "openalex_id", "year", "journal", "type")
I1 = L.read_csv(L.I1)
I3 = recs(L.I3, "scopus_id", "publication_year", "source_title", "doc_type")
I4 = recs(L.I4, "openalex_id", "year", "journal", "type")
pairs, sym = both_ways(S, O)
NUM["symmetry_S_O"] = sym
ms = {a for a, b, h in pairs}
mo = {b for a, b, h in pairs}
onlyS = [r for r in S if r["id"] not in ms]
onlyO = [r for r in O if r["id"] not in mo]
Sy = {r["id"]: r["year"] for r in S}
Oy = {r["id"]: r["year"] for r in O}
inter, nS, nO = len(pairs), len(S), len(O)
U = inter + len(onlyS) + len(onlyO)
by_doi = sum(1 for p in pairs if p[2] == "doi")
by_title = inter - by_doi
rows = [
    {"measure": "|S| Scopus H4Q title-only, 2003-2025", "value": nS},
    {"measure": "|O| OpenAlex H4Q title-only, 2003-2025", "value": nO},
    {"measure": "S with DOI", "value": sum(1 for r in S if r["doi"])},
    {"measure": "O with DOI", "value": sum(1 for r in O if r["doi"])},
    {"measure": "pairs by DOI", "value": by_doi},
    {"measure": "pairs by normalised title", "value": by_title},
    {"measure": "intersection", "value": inter},
    {"measure": "only Scopus", "value": len(onlyS)},
    {"measure": "only OpenAlex", "value": len(onlyO)},
    {"measure": "union", "value": U},
    {"measure": "share of the union in Scopus (%)", "value": L.pct(inter + len(onlyS), U)},
    {"measure": "share of the union in OpenAlex (%)", "value": L.pct(inter + len(onlyO), U)},
    {"measure": "share of the union in both (%)", "value": L.pct(inter, U)},
    {"measure": "ratio |O| / |S| (harmonised)", "value": f"{nO / nS:.2f}"},
    {"measure": "ratio OpenAlex / Scopus in June (1836 / 931, F12.1)", "value": f"{1836 / 931:.2f}"},
    {"measure": "pairs whose two years differ", "value": sum(1 for a, b, h in pairs if Sy[a] != Oy[b])},
    {"measure": "S records whose ASCII-normalised title is empty (cannot match by title)", "value": sum(1 for r in S if not r["tn"])},
    {"measure": "O records whose ASCII-normalised title is empty (cannot match by title)", "value": sum(1 for r in O if not r["tn"])},
    {"measure": "only-Scopus records without DOI", "value": sum(1 for r in onlyS if not r["doi"])},
    {"measure": "only-OpenAlex records without DOI", "value": sum(1 for r in onlyO if not r["doi"])},
]
L.write_csv(T / "T1_summary.csv", ["measure", "value"], rows)
L.write_md(T / "T1_summary.md", "T1. Scopus (S) and OpenAlex (O) under the same title-only query (H4Q, 2003-2025)", ["measure", "value"], rows,
           f"Sources: S = {L.S}; O = {L.O}. Matching: DOI equality, then exact normalised title among the unmatched; one-to-one.")
NUM["T1"] = {r["measure"]: r["value"] for r in rows}
L.write_csv(T / "T1c_pairs.csv", ["scopus_id", "openalex_id", "matched_by", "scopus_year", "openalex_year"],
            [{"scopus_id": a, "openalex_id": b, "matched_by": h, "scopus_year": Sy[a], "openalex_year": Oy[b]} for a, b, h in sorted(pairs)])


def bucket_rows(buckets):
    out = []
    for name, lo, hi in buckets:
        i_ = sum(1 for a, b, h in pairs if lo <= (Sy[a] or 0) <= hi)
        s_ = sum(1 for r in onlyS if lo <= (r["year"] or 0) <= hi)
        o_ = sum(1 for r in onlyO if lo <= (r["year"] or 0) <= hi)
        u_ = i_ + s_ + o_
        out.append({"bucket": name, "S": i_ + s_, "O": i_ + o_, "intersection": i_, "only_Scopus": s_, "only_OpenAlex": o_,
                    "union": u_, "pct_union_Scopus": L.pct(i_ + s_, u_), "pct_union_OpenAlex": L.pct(i_ + o_, u_),
                    "pct_union_both": L.pct(i_, u_)})
    return out


fb = ["bucket", "S", "O", "intersection", "only_Scopus", "only_OpenAlex", "union", "pct_union_Scopus", "pct_union_OpenAlex", "pct_union_both"]
per = bucket_rows(PERIODS)
yrs = bucket_rows([(str(y), y, y) for y in YEARS])
NOTE_Y = ("Year: a matched pair is placed by its Scopus year, an only-Scopus record by its Scopus year, an only-OpenAlex record by its "
          "OpenAlex year; S and O columns here = intersection + only-Scopus / only-OpenAlex in that bucket.")
L.write_csv(T / "T1b_periods.csv", fb, per)
L.write_md(T / "T1b_periods.md", "T1b. By period", fb, per, NOTE_Y)
L.write_csv(T / "T1b_years.csv", fb, yrs)
L.write_md(T / "T1b_years.md", "T1b. By year", fb, yrs, NOTE_Y)
NUM["T1b_period_totals"] = {r["bucket"]: r["union"] for r in per}
NUM["T1b_year_sum"] = {k: sum(r[k] for r in yrs) for k in ("intersection", "only_Scopus", "only_OpenAlex", "union")}

# ---------- T2: only OpenAlex
frame_src = {L.norm_title(r["source_title"]) for r in I1} - {""}
for r in onlyO:
    r["in_frame"] = int(bool(L.norm_title(r["source"])) and L.norm_title(r["source"]) in frame_src)
n2 = len(onlyO)
counts_table("T2_only_openalex_types", f"T2. Only-OpenAlex records by type (n = {n2})", Counter(r["type"] or "(empty)" for r in onlyO), n2,
             f"Source: {L.O}.", key="type")
src = Counter(r["source"] or "(no source)" for r in onlyO)
inframe_src = {r["source"] or "(no source)": r["in_frame"] for r in onlyO}
rows = [{"source": k, "n": n, "pct": L.pct(n, n2), "source_in_scopus_frame": inframe_src[k]}
        for k, n in sorted(src.items(), key=lambda kv: (-kv[1], kv[0]))]
L.write_csv(T / "T2_only_openalex_sources.csv", ["source", "n", "pct", "source_in_scopus_frame"], rows)
k_in = sum(r["in_frame"] for r in onlyO)
L.write_md(T / "T2_only_openalex_sources.md", f"T2. Only-OpenAlex records by source, full list (n = {n2})",
           ["source", "n", "pct", "source_in_scopus_frame"], rows,
           f"source_in_scopus_frame = 1: the normalised source name occurs among the sources of the frame I1 ({L.I1}); records: "
           f"{k_in} of {n2} ({L.pct(k_in, n2)} %). Such records sit in a venue Scopus indexes for this corpus; their absence from S "
           "points to affiliation linking or query matching, not to venue coverage.")
counts_table("T2_only_openalex_doi_presence", f"T2. Only-OpenAlex records: DOI present (n = {n2})",
             Counter("with DOI" if r["doi"] else "without DOI" for r in onlyO), n2, "", key="doi")
counts_table("T2_only_openalex_doi_prefix", f"T2. Only-OpenAlex records: DOI prefix (registrant) (n with DOI = {sum(1 for r in onlyO if r['doi'])})",
             Counter(r["doi"].split("/", 1)[0] for r in onlyO if r["doi"]), sum(1 for r in onlyO if r["doi"]),
             "The prefix identifies the registrant (publisher); names are not looked up (no network).", key="doi_prefix")
counts_table("T2_only_openalex_years", f"T2. Only-OpenAlex records by year (n = {n2})", Counter(r["year"] for r in onlyO), n2, "", key="year")
NUM["T2"] = {"n": n2, "types": dict(Counter(r["type"] for r in onlyO)), "source_in_scopus_frame_records": k_in,
             "with_doi": sum(1 for r in onlyO if r["doi"]), "unique_sources": len(src)}
rows = []
for r in onlyO:
    t, cut = L.cut30(r["title"])
    rows.append({"openalex_id": r["id"], "year": r["year"], "type": r["type"], "journal": r["source"], "doi": r["doi_raw"], "title": t,
                 "title_cut_to_30_words": cut, "source_in_scopus_frame": r["in_frame"]})
L.write_csv(T / "T2b_only_openalex_records.csv", ["openalex_id", "year", "type", "journal", "doi", "title", "title_cut_to_30_words",
                                                 "source_in_scopus_frame"], rows)

# ---------- T3: only Scopus
i4doi = {r["doi"] for r in I4} - {""}
i4tit = {r["tn"] for r in I4} - {""}
for r in onlyS:
    r["in_oa_june"] = int(r["doi"] in i4doi) if r["doi"] else ""
    r["title_in_oa_june"] = "" if r["doi"] else int(bool(r["tn"]) and r["tn"] in i4tit)
n3 = len(onlyS)
counts_table("T3_only_scopus_doc_types", f"T3. Only-Scopus records by document type (n = {n3})", Counter(r["type"] or "(empty)" for r in onlyS),
             n3, f"Source: {L.S}.", key="doc_type")
counts_table("T3_only_scopus_sources", f"T3. Only-Scopus records by source, full list (n = {n3})", Counter(r["source"] or "(no source)" for r in onlyS),
             n3, "", key="source_title")
counts_table("T3_only_scopus_doi_presence", f"T3. Only-Scopus records: DOI present (n = {n3})",
             Counter("with DOI" if r["doi"] else "without DOI" for r in onlyS), n3, "", key="doi")
counts_table("T3_only_scopus_years", f"T3. Only-Scopus records by year (n = {n3})", Counter(r["year"] for r in onlyS), n3, "", key="year")
wd = [r for r in onlyS if r["doi"]]
nd = [r for r in onlyS if not r["doi"]]
rows = [{"measure": "only-Scopus records with DOI", "n": len(wd)},
        {"measure": "... whose DOI is in the June OpenAlex export I4 (in_openalex_june = 1)", "n": sum(r["in_oa_june"] for r in wd)},
        {"measure": "only-Scopus records without DOI", "n": len(nd)},
        {"measure": "... whose normalised title is in I4 (title_in_openalex_june = 1)", "n": sum(r["title_in_oa_june"] for r in nd)}]
L.write_csv(T / "T3_only_scopus_in_openalex_june.csv", ["measure", "n"], rows)
L.write_md(T / "T3_only_scopus_in_openalex_june.md", "T3. Only-Scopus records known to OpenAlex in June", ["measure", "n"], rows,
           f"I4 = {L.I4} (June OpenAlex export, n = 1,836). A flag of 1: OpenAlex holds the work but did not return it under the same "
           "title query (affiliation linking or title matching).")
NUM["T3"] = {"n": n3, "doc_types": dict(Counter(r["type"] for r in onlyS)), "with_doi": len(wd),
             "in_openalex_june": sum(r["in_oa_june"] for r in wd), "without_doi": len(nd),
             "title_in_openalex_june": sum(r["title_in_oa_june"] for r in nd)}
rows = []
for r in onlyS:
    t, cut = L.cut30(r["title"])
    rows.append({"scopus_id": r["id"], "year": r["year"], "doc_type": r["type"], "source_title": r["source"], "doi": r["doi_raw"],
                 "title": t, "title_cut_to_30_words": cut, "in_openalex_june": r["in_oa_june"], "title_in_openalex_june": r["title_in_oa_june"]})
L.write_csv(T / "T3b_only_scopus_records.csv", ["scopus_id", "year", "doc_type", "source_title", "doi", "title", "title_cut_to_30_words",
                                               "in_openalex_june", "title_in_openalex_june"], rows)

# ---------- T4: the bridge to June
jp, jsym = both_ways(I3, I4)
NUM["symmetry_I3_I4"] = jsym
jms, jmo = {a for a, b, h in jp}, {b for a, b, h in jp}
j_onlyS = [r for r in I3 if r["id"] not in jms]
j_onlyO = [r for r in I4 if r["id"] not in jmo]
bridge_O = match(j_onlyO, O)
bridge_S = match(j_onlyS, S)
o_in_i4 = match(O, I4)
s_in_i3 = match(S, I3)


def f121_rule():
    """Phase F12.1's own rule, reproduced: an I4 record with a DOI matches iff its DOI is in I3; without a DOI iff its title
    (Unicode letters and digits kept) is among I3's titles; seen from I3 likewise; not one-to-one."""
    def tn(s):
        return " ".join("".join(ch if ch.isalnum() else " " for ch in (s or "").lower()).split())
    d3 = {r["doi"] for r in I3} - {""}
    t3 = {tn(r["title"]) for r in I3} - {""}
    d4 = {r["doi"] for r in I4} - {""}
    t4n = {tn(r["title"]) for r in I4 if not r["doi"]} - {""}
    inter = sum(1 for r in I4 if (r["doi"] in d3) if r["doi"]) + sum(1 for r in I4 if not r["doi"] and tn(r["title"]) in t3)
    i3_found = sum(1 for r in I3 if (r["doi"] and r["doi"] in d4) or (tn(r["title"]) and tn(r["title"]) in t4n))
    return inter, len(I4) - inter, len(I3) - i3_found


f121_inter, f121_onlyO, f121_onlyS = f121_rule()
rows = [
    {"measure": "June: I3 Scopus structural layer", "n": len(I3)},
    {"measure": "June: I4 OpenAlex export", "n": len(I4)},
    {"measure": "June: pairs (same rule) - by DOI", "n": sum(1 for p in jp if p[2] == "doi")},
    {"measure": "June: pairs - by title", "n": sum(1 for p in jp if p[2] == "title")},
    {"measure": "June: intersection", "n": len(jp)},
    {"measure": "June: only Scopus", "n": len(j_onlyS)},
    {"measure": "June: only OpenAlex", "n": len(j_onlyO)},
    {"measure": "June under F12.1's rule (reproduced): intersection", "n": f121_inter},
    {"measure": "June under F12.1's rule: only OpenAlex", "n": f121_onlyO},
    {"measure": "June under F12.1's rule: only Scopus (seen from I3)", "n": f121_onlyS},
    {"measure": "June only-OpenAlex records found in O (harmonised OpenAlex)", "n": len(bridge_O)},
    {"measure": "June only-Scopus records found in S (harmonised Scopus)", "n": len(bridge_S)},
    {"measure": "context: O records found in I4", "n": len(o_in_i4)},
    {"measure": "context: S records found in I3", "n": len(s_in_i3)},
]
L.write_csv(T / "T4_bridge_to_june.csv", ["measure", "n"], rows)
L.write_md(T / "T4_bridge_to_june.md", "T4. Bridge to the June divergence (I3 931 / I4 1,836)", ["measure", "n"], rows,
           f"I3 = {L.I3}; I4 = {L.I4}. Same matching rule as T1 (one-to-one, DOI then normalised title, ASCII title normalisation). "
           "F12.1 reported 324 / 608 / 1,512 under its own rule (title match for records without DOI, not one-to-one, Unicode letters "
           "kept).")
NUM["T4"] = {r["measure"]: r["n"] for r in rows}

# ---------- the figure
F.mkdir(parents=True, exist_ok=True)
fig_rows = [{"year": r["bucket"], "only_Scopus": r["only_Scopus"], "both": r["intersection"], "only_OpenAlex": r["only_OpenAlex"],
             "union": r["union"]} for r in yrs]
L.write_csv(F / "Fig_coverage_union_by_year.csv", ["year", "only_Scopus", "both", "only_OpenAlex", "union"], fig_rows)
fig, ax = plt.subplots(figsize=(9, 4.8))
x = [int(r["year"]) for r in fig_rows]
b1 = [r["only_Scopus"] for r in fig_rows]
b2 = [r["both"] for r in fig_rows]
b3 = [r["only_OpenAlex"] for r in fig_rows]
ax.bar(x, b1, color=COLORS["only Scopus"], label="Scopus only", width=0.75)
ax.bar(x, b2, bottom=b1, color=COLORS["both"], label="Both databases", width=0.75)
ax.bar(x, b3, bottom=[p + q for p, q in zip(b1, b2)], color=COLORS["only OpenAlex"], label="OpenAlex only", width=0.75)
ax.set_xlabel("Publication year")
ax.set_ylabel("Records (union of the two exports)")
ax.set_xticks([y for y in YEARS if y % 2 == 1])
ax.tick_params(axis="x", labelsize=8)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.legend(frameon=False, loc="upper left")
fig.tight_layout()
base = F / "Fig_coverage_union_by_year"
fig.savefig(str(base) + ".pdf", metadata={"CreationDate": None, "ModDate": None, "Producer": None, "Creator": None})
fig.savefig(str(base) + ".png", dpi=300, metadata={"Software": None})
plt.close(fig)
with Image.open(str(base) + ".png") as im:
    im.convert("RGB").save(str(base) + ".tif", compression="tiff_lzw", dpi=(300, 300))
NUM["figure"] = {"years": len(fig_rows), "union": sum(r["union"] for r in fig_rows), "colors": COLORS}
L.jdump(NUM, L.OUT / "F12_4_numbers.json")
print(json.dumps({k: NUM[k] for k in ("T1", "symmetry_S_O", "T2", "T3", "T4", "symmetry_I3_I4")}, ensure_ascii=False, indent=1))
