"""Phase F13.3 - builds phase_F13_3_report.md from the tables, the numbers, the stamp, the gates and the verifier's CSV.
Prose is wrapped at 25 words per line; table cells come from the CSVs (each <= 30 words). No names of corpus authors appear in prose."""
import sys
sys.dont_write_bytecode = True

import csv
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f133_lib as L


def rows(p):
    p = Path(p)
    return L.read_csv(p) if p.exists() else []


def tmd(name, title, note=""):
    p = L.TABLES / f"{name}.csv"
    rd = csv.reader(io.StringIO(p.read_bytes().decode("utf-8"), newline=""))
    fields = next(rd)
    data = [dict(zip(fields, r)) for r in rd]
    return f"### {title}\n\n" + (L.wrap(note) + "\n\n" if note else "") + L.md_table(fields, data) + "\n"


def para(text):
    return L.wrap(" ".join(text.split())) + "\n"


def build(pending, gates, ver=None):
    st = L.jload(L.OUT / "F13_3_brief_stamp.json")
    env = st["environment"]
    n = L.jload(L.OUT / "F13_3_numbers.json")
    kv = lambda name, k="measure", v="value": {r[k]: r[v] for r in rows(L.TABLES / f"{name}.csv")}
    t0a = {r["measure"]: r for r in rows(L.TABLES / "T0a_reference_counts.csv")}
    t0b = kv("T0b_pairs_scopus_vs_wos")
    t1 = {r["period"]: r for r in rows(L.TABLES / "T1_reference_age.csv")}
    t1c = rows(L.TABLES / "T1c_rpys_peaks.csv")
    t2a = kv("T2a_cited_thresholds")
    t3a = rows(L.TABLES / "T3a_top30_sources_by_references.csv")
    t3c = kv("T3c_cited_sources_summary")
    t4a = kv("T4a_local_citations")
    t4c = kv("T4c_historiograph_summary")
    t5a = kv("T5a_coupling_summary")
    t5c = rows(L.TABLES / "T5c_coupling_sensitivity.csv")
    t5d = rows(L.TABLES / "T5d_work_key_coupling_clusters.csv")
    t6a = kv("T6a_cocitation_summary")
    t6a2 = kv("T6a2_cocitation_work_key_sensitivity")
    t6c = kv("T6c_source_cocitation_summary")
    ver = ver if ver is not None else rows(L.OUT / "phase_F13_3_independent_verification.csv")
    tot = int(t0a["references, total"]["F13_3_corrected"])
    med = t0a["references per record - median (records with references)"]["F13_3_corrected"]
    peaks = [r["year"] for r in t1c]
    old_peaks = sorted(int(y) for y in peaks if int(y) < 2020)
    pc = lambda x: f"{100 * float(x):.1f} %"
    named = n["T0"]["r13_dropped_named"]
    named = [named] if isinstance(named, str) else named
    wk = n["T2"]["work_key"]
    out = []
    out.append("# Phase F13.3 - citation structure of the E1 reference lists with bibliometrix (R)\n")
    out.append(para(f"""Status: COMPLETE. Run date 2026-10-13. Repository root (where the phase registry lies): {st['root']}; the registry is
        {st['registry_file']} (only its existence was checked; it was not read). Frame E1 = the Scopus full export of 2026-10-13, 841 records.
        The manuscript was not touched. CORRECTIONS.csv is unchanged."""))
    out.append("## 1. Environment (preparation, before step 0)\n")
    out.append(para(f"""{env['R']}; bibliometrix {env['bibliometrix']}; igraph {env['igraph']} (other packages in run_logs/environment.json).
        bibliometrix was installed from CRAN with install.packages('bibliometrix') and its dependencies into the user R library (outside the
        repository), with network access only for that installation (log: run_logs/install_bibliometrix.log). The phase programs (programs/*.R,
        programs/*.py) use no network."""))
    out.append("## 2. Inputs, step 0, .gitignore\n")
    i = st["inputs"]
    out.append(L.md_table(["input", "sha256 (first 16)", "equal to expected", "in README"], [
        {"input": "E1 Scopus CSV", "sha256 (first 16)": i["E1"]["sha256"][:16], "equal to expected": i["E1"]["equal"], "in README": i["E1"]["in_README"]},
        {"input": "E2 WoS plain text (UT and NR only)", "sha256 (first 16)": i["E2"]["sha256"][:16], "equal to expected": i["E2"]["equal"],
         "in README": i["E2"]["in_README"]},
        {"input": "phase_F13_1 T3a_pairs.csv", "sha256 (first 16)": i["pairs"]["sha256"][:16], "equal to expected": "recorded", "in README": ""},
        {"input": "phase_F12_3c thesaurus.csv (v3)", "sha256 (first 16)": i["thesaurus_v3"]["sha256"][:16], "equal to expected": "recorded", "in README": ""}]) + "\n")
    out.append(para(f"""Step 0 recorded the brief stamp (F13_3_brief_stamp.json), the environment, and a snapshot of
        {len(L.jload(L.OUT / 'F13_3_step0_snapshot.json')['files'])} named untouchable files (main.qmd, title_page_DPRG.qmd, references.bib,
        rebuilt/*, outputs/tp_submission/*, phases F12_1, F12_3, F12_3b, F12_3c, F12_4, F13_1 with data/, F13_2, author_exports_2026_10,
        CORRECTIONS.csv, .gitignore). phase_F13_5, phase_F13_2b and the registry were neither read nor snapshotted.
        Disclosed change outside the phase folder: one line appended to .gitignore before anything was written to data/:
        {L.GITIGNORE_LINE}"""))
    out.append("## 3. Personal data (R13)\n")
    out.append(para(f"""Right after convert2df, before any write, the object kept only a whitelist of {len(n['T0']['columns_kept'])} columns
        ({', '.join(n['T0']['columns_kept'])}); {n['T0']['r13_dropped_all']} columns were dropped, among them the named ones
        ({', '.join(named)}; E1 has no EM, OI, RI columns) and AU1_UN, which convert2df derives from the correspondence
        address inside the import call and which carried e-mails. AU (corpus authors) stayed in memory for SR and local citations and is written
        nowhere. Abstracts were not written at all. Full reference texts are only in data/ (git-ignored). Cited works appear in tables only as
        first-author surname, year, title (at most 15 words) and source; corpus records only as DOI/EID, year, source, title and counts."""))
    out.append("## 4. CR repair rule\n")
    out.append(para("""The Scopus CSV separates references AND the authors inside one reference with '; '. The rule of the brief: split the cell on
        '; ' into fragments (non-empty after trimming); a fragment without a comma shaped 'Surname Initials.' is an author fragment (pattern
        ^(?:[A-Z][\\w'’\\-\\.]*\\s?)+[A-Z]\\.(?:\\s?[A-Z]\\.)*$, applied to the uppercased text as bibliometrix stores it, so particles pass);
        consecutive author fragments are attached with ', ' to the next fragment (the body); a trailing buffer of authors without a body is a
        reference of its own; references are written back to CR with '; '. Template (not real data):"""))
    out.append("```\nexported : Surname1 A.; Surname2 B.C.; Surname3 D., Title one, Journal, 34, 10, pp. 1-10, (2022); Surname4 E., Title two, Source, (2019)\n"
               "fragments: 'Surname1 A.' | 'Surname2 B.C.' | 'Surname3 D., Title one, ...(2022)' | 'Surname4 E., Title two, ...(2019)'  (4)\n"
               "repaired : SURNAME1 A., SURNAME2 B.C., SURNAME3 D., TITLE ONE, JOURNAL, 34, 10, PP. 1-10, (2022); SURNAME4 E., TITLE TWO, SOURCE, (2019)  (2)\n```\n")
    out.append(para(f"""The literal pattern backtracks exponentially on long all-capital fragments, so an equivalent linear form is used; on
        {kv('T0a2_repair_diagnostics')['comma-free fragments of <= 24 characters checked against the literal pattern']} short comma-free
        fragments both forms agree in every case (T0a2). Trailing author buffers: {n['T0']['tails']}. bibliometrix 5.5.0 repairs the separator
        itself during import (split only after '(YYYY);', every other ';' turned into ','); that gives {n['T0']['builtin']} references,
        because a reference without a trailing year is glued to the next one ({n['T0']['builtin_records_differ']} records differ). The brief's
        rule is applied instead (see disclosures 1-2)."""))
    out.append("## 5. Reference counts (T0) - заменяет T1d и T3d фазы F13.1\n")
    out.append(para(f"""These tables replace (заменяет) T1d and T3d of phase F13.1, which counted fragments, not references. Corrected: {tot}
        references, median {med} per record. On the 216 Scopus-WoS pairs the medians are close: Scopus {t0b['Scopus references (corrected) - median']}
        against WoS NR {t0b['WoS NR - median']} (F13.1 had 88 against 30)."""))
    out.append(tmd("T0a_reference_counts", "T0a. References per record (corrected) beside the replaced F13.1 counts",
                   "Column F13_1_published_replaced quotes the replaced F13.1 numbers (T1d: 79,686 references, median 67) - заменены."))
    out.append(tmd("T0a2_repair_diagnostics", "T0a2. Repair diagnostics"))
    out.append(tmd("T0b_pairs_scopus_vs_wos", "T0b. 216 pairs: Scopus references (corrected) against WoS NR"))
    out.append(tmd("T0c_references_by_period_and_type", "T0c. References by period and by document type (as exported, uppercased by bibliometrix)"))
    out.append(tmd("T0d_citations_before_after", "T0d. Control: top 5 before and after the repair",
                   """Block 1: the most frequent '; ' fragments of the unrepaired cells - bare author fragments. Block 2: citations(field = 'article')
                   on the unrepaired CR; it keeps only items with a comma, so each work appears under its LAST author. Block 3: after the repair.
                   name_segment holds a cited author (bibliographic data of the cited works)."""))
    out.append("## 6. Reference age (T1) and RPYS (T1b)\n")
    out.append(para(f"""Year of a reference = its last '(YYYY)' within 1800-2026: {pc(t1['all']['share_with_year'])} of the references carry one.
        Median age {t1['all']['median_age']} years; Price index (share not older than 5 years) {t1['all']['price_index']}, rising from
        {t1['2003-2016']['price_index']} (2003-2016) to {t1['2022-2025']['price_index']} (2022-2025); share older than 15 years
        {t1['all']['share_older_than_15']}."""))
    out.append(tmd("T1_reference_age", "T1. Reference age by period of the citing records"))
    out.append(tmd("T1a_age_distribution", "T1a. Age distribution (share of dated references)"))
    out.append(para(f"""RPYS (rpys(M, sep = ';', graph = FALSE); cited years {n['T1']['rpys_span'][0]}-{n['T1']['rpys_span'][1]}, the
        bibliometrix default window). Peaks (deviation from the centred five-year median above both neighbours, ten highest): {', '.join(peaks)}.
        The 2021 peak is the recency surge. Among the older peaks ({', '.join(str(y) for y in old_peaks)}) the most cited works of the year
        (T1c) are the founding papers of public-key cryptography (1976, 1978), the discrete-logarithm signature scheme (1985), elliptic-curve
        cryptosystems (1987), a security-audit expert system (1990), finite-automaton public-key cryptosystems (2001), residue-class machine
        arithmetic (1968, behind the nonpositional-notation ciphers) and speech-intelligibility measurement (1962)."""))
    out.append(tmd("T1c_rpys_peaks", "T1c. RPYS peaks", "top_work_* = the most cited work of that year under the work key (own-code sensitivity, section 7)."))
    out.append(tmd("T1b_rpys", "T1b. RPYS table (cited year, references, deviations from the five-year medians)"))
    out.append("## 7. Most cited works (T2)\n")
    out.append(para(f"""citations(M, field = 'article', sep = ';') counts exact reference strings. {t2a['distinct cited references (strings counted by citations())']}
        distinct strings; {t2a['with >= 2 citing records']} are cited by at least 2 records, {t2a['with >= 5 citing records']} by at least 5 and
        {t2a['with >= 10 citing records']} by 10 or more. One work spelt in several ways is counted as several strings (T2 ranks 20 and 21 are
        one work). Own-code sensitivity T2b groups strings by a work key (first-author surname + year + first six title words): {wk['works']}
        works, {wk['ge10']} cited by at least 10 records; {wk['overlap_T2']} of the T2 top 30 are also in the T2b top 30."""))
    out.append(tmd("T2_top30_cited_works", "T2. Top 30 cited works (bibliometrix, exact strings)",
                   "Title and source are cut from the reference by the brief's rule (authors, then title, then source); a title containing a comma is cut there."))
    out.append(tmd("T2a_cited_thresholds", "T2a. Thresholds"))
    out.append(tmd("T2b_top30_cited_works_work_key", "T2b. Top 30 cited works by work key (own-code sensitivity)",
                   "string_variants = distinct exact strings merged into the work; T2_rank = rank(s) of those strings in T2."))
    out.append("## 8. Cited sources (T3)\n")
    out.append(para(f"""metaTagExtraction(M, Field = 'CR_SO') recognises a source for {t3c['references with a source recognised by metaTagExtraction(CR_SO)']}
        references ({pc(t3c['share of all references'])} of all). For references without a trailing year it returns the first author as the
        'source'; {t3c["CR_SO items shaped like a person's name - one surname and initials (unrecognised)"]} such items were treated as
        unrecognised. The light thesaurus (55 rows, printed below) merged obvious variants of one journal ({t3c['items changed by the thesaurus']}
        items changed). The top-30 sources hold {pc(t3c['share of all references on the top-30 sources (by references)'])} of all references;
        {t3a[0]['source']} leads with {t3a[0]['references']}. Cross-check: the brief's parse rule finds a source for
        {t3c["cross-check: references with a source by the brief's parse rule (segment after the title)"]} references, and
        {t3c['cross-check: top-30 sources by that rule also in T3a']} of its top 30 are in T3a."""))
    out.append(tmd("cited_sources_thesaurus", "Cited-sources thesaurus (tables/cited_sources_thesaurus.csv)"))
    out.append(tmd("T3a_top30_sources_by_references", "T3a. Top 30 cited sources by references"))
    out.append(tmd("T3b_top30_sources_by_records", "T3b. Top 30 cited sources by citing records"))
    out.append(tmd("T3c_cited_sources_summary", "T3c. Cited sources - summary"))
    out.append("## 9. Local citations (T4) and historiograph\n")
    out.append(para(f"""localCitations(M, sep = ';'): {t4a['records with LCS > 0']} records ({pc(t4a['share of 841'])} of 841) are cited by other corpus
        records; {t4a['LCS, total (local citation links)']} links in all, maximum {t4a['LCS, max']}; only {pc(t4a['share of references pointing inside the corpus'])}
        of all references point inside the corpus. No record has LCS above its Scopus 'Cited by'. Historiograph: {t4c['nodes (records with LCS >= 2)']}
        records with LCS of at least 2, {t4c['edges (citations among them)']} citation links among them, {t4c['nodes drawn (histPlot drops isolates)']}
        drawn."""))
    out.append(tmd("T4a_local_citations", "T4a. Local citations"))
    out.append(tmd("T4a2_local_citations_by_period", "T4a2. Local citations by period (received by the period's records; made by them)"))
    out.append(tmd("T4b_top20_LCS", "T4b. Top 20 records by local citations (LCS); GCS = Scopus 'Cited by'"))
    out.append(tmd("T4c_historiograph_summary", "T4c. Historiograph - summary"))
    out.append(tmd("T4c_historiograph_nodes", "T4c. Historiograph nodes (label = '#number, year', as in the figure)"))
    out.append("## 10. Bibliographic coupling (T5)\n")
    out.append(para(f"""biblioNetwork(M, analysis = 'coupling', network = 'references', sep = ';'); links with at least 2 shared references;
        Louvain (igraph::cluster_louvain, set.seed(42)). Only {t5a['nodes (records with >= 1 link of >= 2 shared references)']} records are
        coupled, by {t5a['edges (pairs sharing >= 2 references)']} links in {t5a['components']} components (largest
        {t5a['largest component (records)']}); {t5a['clusters with >= 10 records']} clusters reach 10 records; modularity {t5a['modularity Q']}.
        Salton normalisation leaves the partition unchanged; at 3 shared references {t5c[2]['nodes']} records remain. With the work key
        (own code) {t5c[3]['nodes']} records couple by {t5c[3]['edges']} links into {t5c[3]['clusters_ge10']} groups of at least 10 records
        (T5d)."""))
    out.append(tmd("T5a_coupling_summary", "T5a. Coupling network"))
    out.append(tmd("T5b_coupling_clusters", "T5b. Coupling clusters with at least 10 records"))
    out.append(tmd("T5b2_cluster_sources", "T5b2. Top 5 sources of the clusters"))
    out.append(tmd("T5b3_cluster_keywords", "T5b3. Top 10 author keywords of the clusters (after thesaurus v3)"))
    out.append(tmd("T5c_coupling_sensitivity", "T5c. Sensitivity (NMI and ARI against the main partition on common records)"))
    out.append(tmd("T5d_work_key_coupling_clusters", "T5d. Work-key coupling groups with at least 10 records (own-code sensitivity)"))
    out.append("## 11. Co-citation (T6)\n")
    out.append(para(f"""biblioNetwork(M, analysis = 'co-citation', network = 'references', sep = ';'): {t6a['nodes: references with >= 4 citing records']}
        references are cited by at least 4 records; {t6a['nodes with >= 1 edge']} of them have a co-citation link of at least 3, with
        {t6a['edges: pairs co-cited by >= 3 records']} links in {t6a['Louvain clusters (nodes with edges)']} clusters (Q {t6a['modularity Q']}).
        With the work key: {t6a2['works (work key) with >= 4 citing records']} works, {t6a2['edges: pairs co-cited by >= 3 records']} links,
        {t6a2['clusters with >= 5 nodes']} clusters of at least 5. Source co-citation: {t6c['sources with >= 10 references']} sources with at
        least 10 references, {t6c['edges: source pairs co-cited by >= 5 records']} links, {t6c['Louvain clusters']} clusters."""))
    out.append(tmd("T6a_cocitation_summary", "T6a. Co-citation of references"))
    out.append(tmd("T6a2_cocitation_work_key_sensitivity", "T6a2. Co-citation on the work key (own-code sensitivity)"))
    out.append(tmd("T6b_cocitation_clusters_top5", "T6b. Co-citation clusters with at least 5 nodes - top 5 references"))
    out.append(tmd("T6c_source_cocitation_summary", "T6c. Co-citation of sources"))
    out.append(tmd("T6c2_source_clusters", "T6c2. Source co-citation clusters - leading sources"))
    out.append("## 12. Draft figure captions (figures built by script, not viewed)\n")
    out.append(para(f"""Fig_rpys (PNG/PDF): Reference publication year spectroscopy of the {tot} cited references of the 841 Scopus records
        (cited years {n['T1']['rpys_span'][0]}-{n['T1']['rpys_span'][1]}; bibliometrix rpys). Black: cited references per year; red:
        deviation from the centred five-year median; labelled: the ten peaks."""))
    out.append(para(f"""Fig_historiograph (PNG/PDF; nodes/edges CSV): Within-corpus citations among the {t4c['nodes (records with LCS >= 2)']} records
        with at least two local citations ({t4c['nodes drawn (histPlot drops isolates)']} drawn; histPlot omits isolates), placed by year;
        labels give node number and year (T4c)."""))
    out.append(para(f"""Fig_bibliographic_coupling (PNG/PDF; nodes/edges CSV): Records sharing at least two references
        ({t5a['nodes (records with >= 1 link of >= 2 shared references)']} records, {t5a['edges (pairs sharing >= 2 references)']} links);
        Louvain clusters (seed 42), the clusters with at least 10 records coloured; nodes unlabelled."""))
    out.append(para(f"""Fig_cocitation_references (PNG/PDF; nodes/edges CSV): References cited by at least four records and co-cited by at
        least three ({t6a['nodes with >= 1 edge']} nodes, {t6a['edges: pairs co-cited by >= 3 records']} links); Louvain clusters; the 30 most
        cited labelled 'first author year'."""))
    out.append("## 13. For the professor\n")
    generic = {"information security", "cybersecurity", "security", "information protection"}
    themes = "; ".join(" / ".join([k for k in r["top5_author_keywords"].split("; ") if k not in generic][:2]) + f" ({r['records']})" for r in t5d)
    out.append(para(f"""1. Reference counts are corrected: {tot} references, median {med} per record (not 79,686 / 67); on the 216 WoS pairs
        Scopus and WoS NR medians are equal ({t0b['Scopus references (corrected) - median']})."""))
    out.append(para(f"""2. Intellectual base: no single work is cited by 10 or more of the 841 records as an exact string; grouping spellings,
        {wk['ge10']} works reach 10: regional papers on aviation security, decision support and cipher design, and one public-key classic (1976)."""))
    out.append(para(f"""3. Most older RPYS peaks ({', '.join(str(y) for y in old_peaks)}) point to cryptographic roots; the 2021 peak is recency.
        Median reference age is {t1['all']['median_age']} years, Price index {t1['all']['price_index']}."""))
    out.append(para(f"""4. Most cited sources: {t3a[0]['source']}, {t3a[1]['source']}, {t3a[2]['source']}, {t3a[3]['source']}; the top 30 hold
        only {pc(t3c['share of all references on the top-30 sources (by references)'])} of all references. Source co-citation splits into
        mainstream open-access, IoT and networking, and regional proceedings venues."""))
    out.append(para(f"""5. Self-citation of the literature is low: {t4a['records with LCS > 0']} records ({pc(t4a['share of 841'])}) are cited inside
        the corpus, and {pc(t4a['share of references pointing inside the corpus'])} of all references point inside it."""))
    out.append(para(f"""6. Coupling groups: with bibliometrix's exact matching only {t5a['clusters with >= 10 records']} groups reach 10 records;
        with the work key {t5c[3]['clusters_ge10']} groups, led by: {themes}."""))
    out.append(para("""7. These groups echo themes of the keyword map (cryptography, ML and IoT security, decision support, audit expert
        systems), but no formal crosswalk was made: the F12.3c cluster tables were not an input of this phase."""))
    out.append("## 14. Gates\n")
    out.append(L.md_table(["gate", "what", "verdict", "planted_verdict", "falsifiability"],
                          [{k: g[k] for k in ("gate", "what", "verdict", "planted_verdict", "falsifiability")} for g in gates]) + "\n")
    out.append(para("""Full observations: phase_F13_3_checkpoint_assertions.csv. G4 ran f133_main.R a second time into data/rerun2 (inside the
        git-ignored data/), compared bytes of tables/, data/, the figure CSVs and the numbers, and removed the folder; Louvain labels are
        renumbered deterministically (size, then smallest id), so byte equality also proves equal partitions."""))
    out.append("## 15. Independent verifier\n")
    if ver:
        out.append(L.md_table(["check", "what", "expected", "observed", "verdict"], ver) + "\n")
        out.append(para(f"""A subagent wrote its own Python code (programs/f133_verify.py) without reading the phase programs:
            {sum(1 for r in ver if r.get('verdict') == 'PASS')} PASS, {sum(1 for r in ver if r.get('verdict') == 'EXPLAINED')} EXPLAINED,
            {sum(1 for r in ver if r.get('verdict') == 'FAIL')} FAIL of {len(ver)} rows (phase_F13_3_independent_verification.csv)."""))
    else:
        out.append("(verifier pending)\n")
    out.append("## 16. Disclosures\n")
    disc = [
        f"""bibliometrix 5.5.0 differs from the brief's expectation: csvScopus2df already repairs the separator (internal
        fix_scopus_author_separator: split only after '(YYYY);', other ';' to ','), giving {n['T0']['builtin']} references. To apply the
        brief's rule, this internal function was replaced by identity for one convert2df call (restored at once); the standard import was
        also run, for the comparison column of T0a.""",
        f"""convert2df's CR cleaning removes ' . ' and so erased one separator ('; . '): {n['T0']['fragments_import']} fragments instead of
        {n['T0']['fragments_exported']}. The rule therefore runs on the exported cells (E1 'References', read with readr, uppercased as
        bibliometrix does), and the same cleaning is applied to each repaired reference. {n['T0']['inner_semicolon']} references had an inner
        ';' turned into ','.""",
        """citations(field = 'article') drops items without a comma, so before the repair its top 5 shows reference bodies under their last
        author, not bare fragments like 'LI Q.'; the bare fragments are shown separately (T0d block 1).""",
        f"""histNetwork() ignores min.citations in 5.5.0 (set to 0 inside); the historiograph keeps the records with LCS of at least 2 by hand.
        histPlot labels were replaced by '#number, year', its logo layer removed; it drops isolates
        ({t4c['nodes drawn (histPlot drops isolates)']} of {t4c['nodes (records with LCS >= 2)']} drawn).""",
        """metaTagExtraction(CR_SO) returns the first author as 'source' when a reference lacks a trailing year; such items (one surname and
        initials) were treated as unrecognised. A first, broader test also removed abbreviated journal titles; it was narrowed before the final run.""",
        f"""biblioNetwork keeps only matrix rows whose label starts with a letter; {t5a["records left out by biblioNetwork's first-letter filter"]}
        record was left out of the coupling matrix.""",
        """citations() and biblioNetwork() match exact strings (biblioNetwork cuts a reference at its first ')' and drops commas), so variant
        spellings of one work count separately. The work-key tables (T2b, T5c row 4, T5d, T6a2) are own code, added as a sensitivity to show
        the size of this effect; the main results remain bibliometrix's.""",
        """rpys() uses the default window (max year - 100 to max year - 3) and the FIRST '(YYYY)' of a reference; T1 uses the LAST one.""",
        """Title and source of a cited work are cut by the brief's comma rule; titles containing commas are cut early (e.g. T2 rank 13). Surname
        extraction was fixed for two-letter initials, and a parsing slip for references without authors was fixed, before the final run.""",
        """Three probes ran after step 0, before the main program (consoles in run_logs/). Probe 3 printed cited-source strings, some of which
        were person names (the CR_SO defect above); its saved console was redacted in run_logs (32 lines, broad test) and the original moved to
        data/probe_logs/ (git-ignored).""",
        """The main program ran several times during development before the gates; the final outputs are those of the last run, reproduced
        byte for byte by G4.""",
        """G2's first run also applied the 30-word rule to console lines and failed on two (a column-name list in probe 1's console, one line
        of the verifier's console); no contact shape, corpus name or reference text was found. The rule now covers table and report cells, as
        the brief words it; consoles keep the other checks. First run: phase_F13_3_checkpoint_assertions_first_run.csv.""",
        """The registry row's safe_to_publish says NO because data/ holds licensed reference texts; abstracts were not written (the brief's
        wording mentions them).""",
        """Verifier's own disclosures: one listing of the phase folder showed the file names in programs/ (no contents read); an early dump of
        the first 300 bytes of E2 showed one author line in its session console (written nowhere; afterwards only UT, NR and ER lines were
        read). Its C09 first ran on the dry-run report and was re-run, by running its script unchanged, on the final report.""",
        """Registry: the rows phase_F12_4, phase_F13_1 and phase_F13_2 of this session have not been written yet (they wait for 'реестр');
        the phase_F13_3 row joins them, so four rows are pending, in that order.""",
    ]
    out.append("\n".join(L.wrap(f"{k}. " + " ".join(d.split())) for k, d in enumerate(disc, 1)) + "\n")
    out.append("## 17. Строка реестра (к добавлению по команде автора)\n")
    if pending:
        r = pending[-1]
        out.append(L.md_table(["phase_id", "status", "produced_numbers", "safe_to_publish", "file_count", "bytes"], [r]) + "\n")
        out.append(para("Note (supersedes F13.1 T1d/T3d): " + r["note"]))
        out.append(para("Pending rows, to be appended in this order on the author's 'реестр': " + ", ".join(p["phase_id"] for p in pending)
                        + " (run_logs/registry_rows_pending.json)."))
    else:
        out.append("(fixed point pending)\n")
    return "\n".join(out)


if __name__ == "__main__":
    print("build() is called by f133_final.py")
