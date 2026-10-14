"""Phase F12.4 - the report, built from the phase's records. Prose hard-wrapped (<= 25 words a line, gate G2)."""
import sys
sys.dont_write_bytecode = True

import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f124_lib as L

W = L.wrap


def j(p):
    return json.loads(Path(p).read_bytes().decode("utf-8"))


def md(name):
    return (L.TABLES / name).read_bytes().decode("utf-8").replace("## ", "### ", 1)


def rows(name, folder=None):
    import csv, io
    p = (folder or L.TABLES) / name
    return list(csv.DictReader(io.StringIO(p.read_bytes().decode("utf-8"), newline=""))) if p.exists() else []


def csv_md(title, name, limit=None, note=""):
    r = rows(name)
    shown = r if limit is None else r[:limit]
    return f"### {title}\n\n" + (W(note) + "\n\n" if note else "") + L.md_table(list(r[0].keys()), shown) + "\n"


def bullets(items, width=22):
    return "\n".join("- " + W(x, width).replace("\n", "\n  ") for x in items) + "\n"


def build(row, gates):
    n = j(L.OUT / "F12_4_numbers.json")
    st = j(L.OUT / "F12_4_brief_stamp.json")
    ver = rows("phase_F12_4_independent_verification.csv", L.OUT)
    t1, t4 = n["T1"], n["T4"]
    meta = {db: j(L.path(m)) for db, (_, m) in L.META.items()}
    nS, nO = t1["|S| Scopus H4Q title-only, 2003-2025"], t1["|O| OpenAlex H4Q title-only, 2003-2025"]
    inter, oS, oO, U = t1["intersection"], t1["only Scopus"], t1["only OpenAlex"], t1["union"]
    out = ["# Phase F12.4 - coverage on the harmonised pair (Scopus and OpenAlex, same title-only query)\n"]
    status = row["status"] if row else "(dry run)"
    out.append(W(f"Status: {status}. Repository: {st['root']} (where PHASE_REGISTRY.csv is; the registry was neither read nor written - a "
                 f"parallel session writes it). Brief: F12_4_brief.md (sha256 {st['brief_sha256']}). No edit to the manuscript, the package, "
                 "main.qmd or references.bib; phase_F12_3b not read.") + "\n")

    out.append("## 1. Inputs\n")
    lines = ["| input | file | sha256 | rows | check |", "| --- | --- | --- | --- | --- |"]
    for db, tag in (("scopus", "S"), ("openalex", "O")):
        m = st["S_O_against_manifest"][db]
        lines.append(f"| {tag} | {L.S if tag == 'S' else L.O} | {m['sha256']} | {m['rows']} | equal to manifest.csv: {m['equal']} |")
    for tag, rel in (("I1", L.I1), ("I3", L.I3), ("I4", L.I4)):
        lines.append(f"| {tag} | {rel} | {st['I_now'][tag]} | {841 if tag == 'I1' else 931 if tag == 'I3' else 1836} | "
                     f"equal to F12.1: {st['I_now'][tag] == st['I_in_F12_1'][tag]} |")
    for k, v in st["F12_1_tables"].items():
        lines.append(f"| F12.1 {k} | {L.F121_TABLES[k]} | {v} |  | read |")
    out.append("\n".join(lines) + "\n")
    out.append("Query strings (run_metadata.json, verbatim):\n")
    for db in ("scopus", "openalex"):
        out.append(f"- {db}: `{meta[db]['query_string_exact']}`")
    out.append("")
    out.append(W(f"Both runs: profile {meta['scopus']['profile']}, field scope {meta['scopus']['field_scope']}, matching "
                 f"{meta['scopus']['matching_semantics']}, retrieved {meta['scopus']['retrieval_started_utc'][:10]}, same spec "
                 f"({meta['scopus']['derived_from_spec']}, sha256 {meta['scopus']['spec_sha256'][:16]}...). Equivalence is close but not "
                 "literal: Scopus truncates (cybersecurit*, cryptograph*, \"cyber defen*\") and filters by AFFILCOUNTRY; OpenAlex searches "
                 "words in titles (with its own stemming) and filters by institutions.country_code. The query is the title-only H4Q profile, "
                 "narrower than the manuscript's title-abstract-keyword query.") + "\n")
    out.append("Matching parameters:\n")
    out.append(bullets([
        "DOI: strip, lowercase, leading https://doi.org/, http://doi.org/, https://dx.doi.org/, http://dx.doi.org/ or doi: removed.",
        "Title: lowercase; every character outside [a-z0-9] to a space; spaces collapsed (no S or O title is empty under it).",
        "Rule: DOI equality first; then exact equality of normalised titles among the unmatched; one-to-one; greedy in sorted id "
        "order; run from both sides - the pair sets are equal (" + str(n["symmetry_S_O"]["from_A_equals_from_B"]) + ").",
        "Years: a pair by its Scopus year, an only-Scopus record by its Scopus year, an only-OpenAlex record by its OpenAlex year.",
    ]))

    out.append("## 2. T1 - the harmonised pair\n")
    out += [md("T1_summary.md"), md("T1b_periods.md"), md("T1b_years.md")]
    out.append(W("The pairs themselves (ids, how matched, both years): tables/T1c_pairs.csv.") + "\n")

    out.append("## 3. T2 - only OpenAlex\n")
    out += [md("T2_only_openalex_types.md"), md("T2_only_openalex_sources.md"), md("T2_only_openalex_doi_presence.md"),
            md("T2_only_openalex_doi_prefix.md"), md("T2_only_openalex_years.md")]
    out.append(csv_md("T2b. Only-OpenAlex records (first 20 of " + str(n["T2"]["n"]) + "; full list in tables/T2b_only_openalex_records.csv)",
                      "T2b_only_openalex_records.csv", 20))
    out.append("## 4. T3 - only Scopus\n")
    out += [md("T3_only_scopus_doc_types.md"), md("T3_only_scopus_sources.md"), md("T3_only_scopus_doi_presence.md"),
            md("T3_only_scopus_years.md"), md("T3_only_scopus_in_openalex_june.md")]
    out.append(csv_md("T3b. Only-Scopus records (first 20 of " + str(n["T3"]["n"]) + "; full list in tables/T3b_only_scopus_records.csv)",
                      "T3b_only_scopus_records.csv", 20))

    out.append("## 5. T4 - bridge to the June divergence\n")
    out.append(md("T4_bridge_to_june.md"))
    jI, jS, jO = t4["June: intersection"], t4["June: only Scopus"], t4["June: only OpenAlex"]
    jU = jI + jS + jO
    ratio_h = nO / nS
    expected = ratio_h * 931
    excess = 1836 - 931
    query_part = 1836 - expected
    out.append(W(
        f"Reading. In June the OpenAlex export held 1,836 records against Scopus' 931 (1.97 times); under one rule only {jI} are shared and "
        f"{jO} sit only in OpenAlex ({L.pct(jO, jU)} % of the June union). Under the same title-only query in September the ratio falls to "
        f"{ratio_h:.2f}, and only-OpenAlex records are {oO} of {U} ({L.pct(oO, U)} % of the union). Of the {jO} June only-OpenAlex records "
        f"only {t4['June only-OpenAlex records found in O (harmonised OpenAlex)']} ({L.pct(t4['June only-OpenAlex records found in O (harmonised OpenAlex)'], jO)} %) "
        "fall inside the harmonised OpenAlex set; the rest lie outside the common query. If the harmonised ratio held for the June scope, "
        f"OpenAlex would hold about {expected:.0f} records, so roughly {query_part:.0f} of the {excess} excess records "
        f"({L.pct(query_part, excess)} %) would come from the non-equivalent queries and about {excess - query_part:.0f} "
        f"({L.pct(excess - query_part, excess)} %) from a genuine OpenAlex-only layer. This split is indicative only: the H4Q query is "
        "title-only and narrower than the June queries, and the two June harvests differ in more than the query.") + "\n")

    out.append("## 6. Figure\n")
    out.append(W("Files: figures/Fig_coverage_union_by_year.pdf, .png (300 dpi), .tif (300 dpi, LZW, from the PNG); data: "
                 "figures/Fig_coverage_union_by_year.csv. Built by programs/f124_coverage.py; nobody viewed it (R18). No title inside. "
                 f"Fixed colours: Scopus only {n['figure']['colors']['only Scopus']}, both {n['figure']['colors']['both']}, OpenAlex only "
                 f"{n['figure']['colors']['only OpenAlex']}.") + "\n")
    cap = (f"Records by publication year in the union of a Scopus and an OpenAlex export retrieved on 4 September 2026 with the same "
           f"title-only query (cybersecurity, information security, cyber defence, network security, cryptography) and a Kazakhstan "
           f"affiliation filter, 2003-2025 (union n = {U}; Scopus {nS}, OpenAlex {nO}). Each bar is split into records found only in "
           f"Scopus ({oS}), in both databases ({inter}; matched by DOI, then by normalised title) and only in OpenAlex ({oO}). Source: "
           "Authors' own work.")
    out.append("Draft caption:\n")
    out.append("> " + W(cap).replace("\n", "\n> ") + "\n")

    out.append("## 7. For the professor: sentences to replace the 'Academic Iceberg Effect'\n")
    srcO = [r["source"] for r in rows("T2_only_openalex_sources.csv") if r["source"] != "(no source)"][:4]
    srcS = [r["source_title"] for r in rows("T3_only_scopus_sources.csv")][:2]
    t3 = n["T3"]
    prof = [
        f"Under an identical title-only query run on the same day (4 September 2026), OpenAlex returned {nO} Kazakhstan-affiliated "
        f"records for 2003-2025 and Scopus {nS} (a ratio of {ratio_h:.2f}); {inter} records are shared, {oO} appear only in OpenAlex and "
        f"{oS} only in Scopus.",
        f"The OpenAlex-only records are mostly articles ({n['T2']['types'].get('article', 0)} of {oO}) in national and regional venues "
        f"and repositories (e.g. {', '.join(srcO)}); the Scopus-only records are mostly conference papers and articles without a DOI "
        f"({t3['without_doi']} of {oS}), led by {srcS[0]} and {srcS[1]}.",
        f"The larger June contrast (1,836 against 931 records) mainly reflects non-equivalent queries: only "
        f"{t4['June only-OpenAlex records found in O (harmonised OpenAlex)']} of the {jO} June OpenAlex-only records fall within the "
        "harmonised OpenAlex set.",
        f"Each database therefore covers only part of the combined record - Scopus {t1['share of the union in Scopus (%)']} % and OpenAlex "
        f"{t1['share of the union in OpenAlex (%)']} % of the union, both together {t1['share of the union in both (%)']} % - which supports "
        "reporting database complementarity rather than an 'iceberg' hidden below Scopus.",
    ]
    out.append(bullets(prof))

    out.append("## 8. Gates\n")
    lines = ["| gate | what | verdict | planted violation caught |", "| --- | --- | --- | --- |"]
    lines += [f"| {g['gate']} | {g['what']} | {g['verdict']} | {g['planted_verdict']} ({g['falsifiability']}) |" for g in gates]
    out.append("\n".join(lines) + "\n")
    first = rows("phase_F12_4_checkpoint_assertions_first_run.csv", L.OUT)
    if first:
        out.append(W("First run: " + ", ".join(f"{g['gate']} {g['verdict']}" for g in first) + ".") + "\n")
    out.append("## 9. Independent verification\n")
    if ver:
        lines = ["| check | what | tables | recomputed | verdict |", "| --- | --- | --- | --- | --- |"]
        lines += ["| " + " | ".join(str(r.get(k, ""))[:100] for k in ("check_id", "what", "expected_from_tables", "recomputed", "verdict")) + " |"
                  for r in ver]
        out.append("\n".join(lines) + "\n")
        out.append(W(f"A subagent wrote its own program (programs/f124_verify.py) from a description of the rules, without reading this "
                     f"phase's programs: {sum(1 for r in ver if r.get('verdict') == 'PASS')} of {len(ver)} PASS.") + "\n")
    else:
        out.append("(not yet run)\n")
    out.append("## 10. Disclosures\n")
    out.append(bullets([
        f"T4 under this phase's rule gives {jI} / {jS} / {jO} for June, not the 324 / 608 / 1,512 of F12.1: this rule is one-to-one and "
        "tries titles for every unmatched record, F12.1's tried titles only for records without a DOI and kept Unicode letters. "
        "F12.1's own rule, reproduced in T4, gives 324 / 1,512 / 608 exactly.",
        "source_in_scopus_frame compares normalised source names only (no ISSN in O); a renamed or translated venue is missed.",
        "in_openalex_june looks a DOI or title up in the June OpenAlex export (1,836 records), not in all of OpenAlex.",
        "The query strings are near-equivalent, not identical (truncation and filters differ by database; see section 1).",
        "No network module in programs/ (gate G6); no heredoc, workflow or skill; one subagent (the verifier); nothing in .claude/; "
        "nothing deleted or moved; CORRECTIONS.csv unchanged; PHASE_REGISTRY.csv and phase_F12_3b neither read nor written.",
        "Author-name columns of S, O, I3 and I4 were read by the programs (they sit in the same rows) but never written out.",
        "ORCID shape. Two DOIs of one journal (prefix 10.52123, suffix led by its ISSN 1994-2370) contain a four-block digit string. "
        "The verifier's plain pattern (C08b) counts them and fails; ORCID iDs start with 0000 or 0009, so this phase counts an ORCID "
        "shape only in those ranges (gate G2, verifier C08b3) and lists the raw four-block hits apart in G2's observation. C08b is "
        "kept as FAIL in the verifier's table and accepted as a declared exception only because C08b3 passes.",
        "The verifier made three trial runs before its final one (the first two differed only in its DOI-location test); its "
        "matching numbers were the same in every run.",
    ]))
    if row:
        out.append("## 11. Registry row (to be added on the author's command)\n")
        out.append(W(f"{row['phase_id']} | {row['status']} | produced_numbers {row['produced_numbers']} | safe_to_publish "
                     f"{row['safe_to_publish']} | {row['file_count']} files, {row['bytes']} bytes (the folder's fixed point) | path "
                     f"{row['path']}") + "\n")
        out.append("Note for the row:\n")
        out.append("> " + W(row["note"]).replace("\n", "\n> ") + "\n")
    return "\n".join(out)
