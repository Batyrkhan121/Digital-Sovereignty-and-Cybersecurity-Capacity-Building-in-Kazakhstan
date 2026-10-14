"""Phase F13.3b - builds phase_F13_3b_report.md from the tables, the numbers, the stamp, the gates and the verifier's CSV.
Prose is wrapped at 25 words per line; table cells come from the CSVs (each <= 30 words). No corpus author names in prose."""
import sys
sys.dont_write_bytecode = True

import csv
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f133b_lib as L


def rows(p):
    p = Path(p)
    return L.read_csv(p) if p.exists() else []


def tmd(name, title, note=""):
    p = L.TABLES / f"{name}.csv"
    rd = csv.reader(io.StringIO(p.read_bytes().decode("utf-8"), newline=""))
    fields = next(rd)
    data = [dict(zip(fields, r)) for r in rd]
    return f"### {title}\n\n" + (L.wrap(" ".join(note.split())) + "\n\n" if note else "") + L.md_table(fields, data) + "\n"


def para(text):
    return L.wrap(" ".join(text.split())) + "\n"


def build(pending, gates, ver=None):
    st = L.jload(L.OUT / "F13_3b_brief_stamp.json")
    n = L.jload(L.OUT / "F13_3b_numbers.json")
    kv = lambda name, k="measure", v="value": {r[k]: r[v] for r in rows(L.TABLES / f"{name}.csv")}
    t0 = {r["measure"]: r for r in rows(L.TABLES / "T0_strings_vs_work_key.csv")}
    t1c = {r["variant"]: r for r in rows(L.TABLES / "T1c_key_sensitivity.csv")}
    t1b2 = kv("T1b2_collision_counts")
    t3a = {r["measure"]: r["title_match_F13_3b"] for r in rows(L.TABLES / "T3a_local_citations_title.csv")}
    t4a = kv("T4a_coupling_workkey")
    t4b = rows(L.TABLES / "T4b_coupling_clusters.csv")
    t4c = rows(L.TABLES / "T4c_coupling_sensitivity.csv")
    t5a = {r["measure"]: r["work_key_F13_3b"] for r in rows(L.TABLES / "T5a_cocitation_workkey.csv")}
    t6s = kv("T6a2_sources_summary")
    t6b = kv("T6b2_source_cocitation_summary")
    ver = ver if ver is not None else rows(L.OUT / "phase_F13_3b_independent_verification.csv")
    env = n["environment"]
    v = lambda m: t0[m]["work_key_F13_3b"]
    s = lambda m: t0[m]["strings_F13_3"]
    pc = lambda x: f"{100 * float(x):.1f} %"
    out = ["# Phase F13.3b - citation structure on the work key (main line) and local citations by title\n"]
    out.append(para(f"""Status: COMPLETE. Run date 2026-10-13. Repository root: {st['root']}. Complements F13.3; the manuscript was not touched;
        CORRECTIONS.csv is unchanged. Tools: Python {env['python']} (networkx {env['networkx']}, scikit-learn {env['scikit-learn']}, matplotlib
        {env['matplotlib']}, Pillow {env['Pillow']}); the work keys come from F13.3's own R function (R 4.6.1). Nothing had to be installed."""))
    out.append("## 1. Strings (F13.3) against the work key (this phase) - T0\n")
    out.append(para(f"""Counting references as strings split one work into several. On the work key the field has a thin but real shared
        base: {v('cited by >= 5 records')} works are cited by at least 5 records (strings: {s('cited by >= 5 records')}) and
        {v('cited by >= 10 records')} by at least 10 (strings: {s('cited by >= 10 records')}); coupling has {v('coupling edges (>= 2 shared)')}
        links and {v('coupling clusters with >= 10 records')} groups of at least 10 records (strings: {s('coupling edges (>= 2 shared)')} and
        {s('coupling clusters with >= 10 records')}); co-citation {v('co-citation edges (>= 3)')} links (strings: {s('co-citation edges (>= 3)')})."""))
    out.append(tmd("T0_strings_vs_work_key", "T0. Strings (F13.3, bibliometrix) against the work key and title matching (F13.3b)"))
    out.append("## 2. Inputs, step 0, R13\n")
    i = st["inputs"]
    out.append(para(f"""E1 sha256 {i['E1']['sha256'][:16]} (equal to README: {i['E1']['equal'] and i['E1']['in_README']});
        phase_F13_3/data/references_repaired.csv sha256 {i['references_repaired']['sha256'][:16]} (28,471 references, as F13.3 T0a);
        f133_lib.R sha256 {i['f133_lib_R']['sha256'][:16]}; the F13.3 tables read are recorded in F13_3b_brief_stamp.json. Step 0
        snapshotted {len(L.jload(L.OUT / 'F13_3b_step0_snapshot.json')['files'])} named untouchable files; phase_F13_2e, tools/ and the
        registry were neither read nor snapshotted. One line was appended to .gitignore before data/ was written: {L.GITIGNORE_LINE}"""))
    out.append(para("""R13: reference texts and per-reference keys are only in data/ (git-ignored). E1 is read by column whitelist; 'Authors' is
        read in memory for the step-3 control and gate G2 only; 'References' in memory for one variant of T3a3. Corpus records appear as
        DOI/EID, year, source, title and counts; cited works as first-author surname, year, title (at most 15 words) and source."""))
    out.append("## 3. Work key (step 1)\n")
    out.append(para(f"""Key = first-author surname + year + first six title words, computed for each of the 28,471 references by F13.3's
        work_key() (R, reused unchanged). As in F13.3, works are counted over the {n['T1']['in_scope']} references longer than 10 characters;
        a reference without surname, year or title keeps its exact string as key. {n['T1']['works']} works; {n['T1']['ge2']} / {n['T1']['ge5']}
        / {n['T1']['ge10']} cited by at least 2 / 5 / 10 records - identical to F13.3 T2a."""))
    out.append(tmd("T1a_key_coverage", "T1a. Key coverage"))
    out.append(para(f"""Collisions: {t1b2['complete keys with >= 2 different full titles (variant spellings included)']} keys carry two or more
        full titles, mostly spellings of one work (hyphenation, transliteration, articles); in {t1b2['of them: titles diverge (neither is a prefix of the other)']}
        the titles diverge, and only {t1b2['of them: likely different works (similarity of the most different pair < 0.8)']} look like different
        works by similarity (below 0.8). Reading them, two are genuinely different works (a two-part paper; two papers sharing author, year
        and six words) and two are one work (a translated title; a journal name inside the title segment)."""))
    out.append(tmd("T1b_key_collisions", "T1b. Ten keys whose full titles diverge, least similar first"))
    out.append(tmd("T1b2_collision_counts", "T1b2. Collision counts"))
    out.append(tmd("T1c_key_sensitivity", "T1c. Key sensitivity (works and thresholds)",
                   f"""Merging years one apart turns {t1c['title words 6 (main)']['works']} works into {t1c['title words 6, year +/- 1 merged']['works']}
                   and raises the works cited by at least 10 records from {t1c['title words 6 (main)']['ge10']} to {t1c['title words 6, year +/- 1 merged']['ge10']}."""))
    out.append("## 4. Most cited works (step 2)\n")
    out.append(tmd("T2_top30_works", "T2. Top 30 cited works on the work key",
                   """Source = the most frequent source form; corpus_record = the work is itself an E1 record (title match, step 3);
                   string_variants = distinct exact strings merged into the work. A title containing a comma is cut there (F13.3 rule)."""))
    out.append(tmd("T2a_thresholds", "T2a. Thresholds (work key = main line; F13.3 columns for comparison)"))
    out.append("## 5. Local citations by title (step 3)\n")
    out.append(para(f"""A reference points to a corpus record when the record's normalised title (at least 30 characters) is contained in the
        normalised reference; {n['T3']['ambiguous_titles']} titles shared by {n['T3']['ambiguous_records']} records are excluded.
        {t3a['local citation links (citing record -> cited record)']} links, {t3a['citing records']} citing and {t3a['cited records (LCS > 0)']}
        cited records, maximum LCS {t3a['LCS, max']}, {pc(t3a['share of references: links / all references'])} of all references. The
        professor's recount gave 538 / 270 / 228 / 12; eight variants of the rule (T3a3) all give 533 unless the ambiguous titles are kept,
        so the five-link gap is not explained here."""))
    out.append(tmd("T3a_local_citations_title", "T3a. Local citations by title against bibliometrix's localCitations (F13.3)"))
    out.append(tmd("T3a2_control", "T3a2. Control: surname of the cited record's first author in the reference; reference year within 1 year",
                   "Each link is classed by its best supporting reference; 'not checkable' would mean a surname without Latin letters."))
    out.append(tmd("T3a3_title_rule_variants", "T3a3. Variants of the title rule"))
    out.append(tmd("T3b_local_citations_by_period", "T3b. Local citations by period"))
    out.append(tmd("T3c_top20_LCS", "T3c. Top 20 records by local citations (title match); GCS = Scopus 'Cited by'"))
    out.append(tmd("T3d_historiograph", "T3d. Historiograph (records with LCS of at least 2)"))
    out.append(tmd("T3d_historiograph_nodes", "T3d. Historiograph nodes (label as in the figure)"))
    out.append("## 6. Bibliographic coupling on the work key (step 4)\n")
    out.append(para(f"""Records sharing at least 2 works: {t4a['nodes (records sharing >= 2 works with another record)']} records,
        {t4a['edges']} links, {t4a['components']} components (largest {t4a['largest component (records)']}); Louvain (networkx, seed 42):
        {t4a['Louvain clusters (seed 42)']} clusters, {t4a['clusters with >= 10 records']} with at least 10 records, Q {t4a['modularity Q']}.
        Over 20 other seeds the partition stays close (ARI median {t4a['stability: ARI to the main partition over 20 seeds - median']},
        minimum {t4a['stability: ARI over 20 seeds - minimum']}). Author keywords are shown raw (lowercased): no keyword thesaurus is an input here."""))
    out.append(tmd("T4a_coupling_workkey", "T4a. Coupling network"))
    out.append(tmd("T4b_coupling_clusters", "T4b. Coupling clusters with at least 10 records"))
    out.append(tmd("T4b2_cluster_shared_works", "T4b2. The three works shared most within each cluster"))
    out.append(tmd("T4c_coupling_sensitivity", "T4c. Sensitivity (NMI and ARI against the main partition on common records)"))
    out.append("## 7. Co-citation on the work key (step 5)\n")
    out.append(tmd("T5a_cocitation_workkey", "T5a. Co-citation network (F13.3 columns for comparison)"))
    out.append(tmd("T5b_cocitation_clusters", "T5b. Co-citation clusters with at least 5 works - top 5 works"))
    out.append(tmd("T5c_cocitation_sensitivity", "T5c. Sensitivity"))
    out.append("## 8. Cited sources by the parse rule (step 6)\n")
    out.append(para(f"""The parse rule (segment after the title) with F13.3's thesaurus finds a source for
        {t6s['references with a source by the parse rule (thesaurus applied; name-shaped excluded)']} references
        ({pc(t6s['share of all references'])}), against {t6s['F13.3: references with a source by metaTagExtraction(CR_SO)']} with
        metaTagExtraction in F13.3. Compared with F13.3, {t6s['top-30 sources also in the F13.3 T3a top-30']} of the top 30 sources are the
        same as in F13.3 T3a, and source co-citation splits into {t6b['Louvain clusters']} clusters instead of F13.3's
        {t6b['F13.3 (metaTagExtraction sources): clusters']}: the same three blocks (open-access mainstream, IoT and networking, regional
        proceedings) plus a small security-journal block and one of unmerged abbreviations."""))
    out.append(tmd("T6a_sources_parse_rule", "T6a. Top 30 cited sources (parse rule)"))
    out.append(tmd("T6a2_sources_summary", "T6a2. Cited sources - summary"))
    out.append(tmd("T6b_source_cocitation_clusters", "T6b. Source co-citation clusters - top 5 sources"))
    out.append(tmd("T6b2_source_cocitation_summary", "T6b2. Source co-citation - summary"))
    out.append("## 9. Draft figure captions (figures built by script, not viewed; PDF, PNG 300 dpi, TIF LZW)\n")
    out.append(para(f"""Fig_historiograph_titlekey: Within-corpus citations found by title match among the {n['T3']['hist_nodes']} records cited
        at least twice ({n['T3']['hist_edges']} links), placed by publication year; node size grows with local citations; labels are node
        numbers (T3d)."""))
    out.append(para(f"""Fig_bibliographic_coupling_workkey: Records sharing at least two cited works ({n['T4']['nodes']} records,
        {n['T4']['edges']} links); colours mark the {n['T4']['big']} Louvain clusters of at least 10 records, numbered as in T4b."""))
    out.append(para(f"""Fig_cocitation_workkey: Works cited by at least four records and co-cited by at least three ({n['T5']['nodes']} works,
        {n['T5']['edges']} links); colours mark the {n['T5']['big']} clusters of at least 5 works; the 30 most cited are labelled
        'first author year'."""))
    out.append("## 10. For the professor\n")
    out.append(para(f"""1. On the work key the corpus has a thin but real shared base: {v('cited by >= 5 records')} works cited by at least
        5 records and {v('cited by >= 10 records')} by at least 10 (strings: {s('cited by >= 5 records')} and {s('cited by >= 10 records')});
        coupling {v('coupling edges (>= 2 shared)')} links in {v('coupling clusters with >= 10 records')} groups of 10 or more; local citations
        {v('local citation links')} links ({pc(t3a['share of references: links / all references'])} of references)."""))
    out.append(para("""2. Coupling groups: a Ukrainian-Kazakh channel (clusters 1, 4 and 7: CEUR cryptography and quantum protocols, JATIT
        decision support, CEUR aviation and SIEM), machine learning and IoT (clusters 2 and 9), and cryptography (3 block ciphers and S-boxes,
        6 nonpositional polynomial ciphers, 10 FPGA PUFs, 11 elliptic curves and blockchain); smaller ones on reliability (5), genetic-algorithm
        protection planning (8) and audit expert systems (12, mostly 2003-2016)."""))
    out.append(para("""3. The classical public-key canon - Diffie-Hellman 1976 (10 records), ElGamal 1985 and RSA 1978 (8 each) - is the most
        cited cryptographic core from outside the region; the top of the list itself is regional (aviation security, decision support, cipher design)."""))
    out.append(para(f"""4. Unresolved: key collisions are rare ({t1b2['of them: likely different works (similarity of the most different pair < 0.8)']}
        likely, two real), but spelling variants beyond six words or a year apart still split some works (year +/- 1 merging gives
        {t1c['title words 6, year +/- 1 merged']['ge10']} works with 10 or more records); the professor's 538 local links are not reproduced
        exactly (533)."""))
    out.append("## 11. Gates\n")
    out.append(L.md_table(["gate", "what", "verdict", "planted_verdict", "falsifiability"],
                          [{k: g[k] for k in ("gate", "what", "verdict", "planted_verdict", "falsifiability")} for g in gates]) + "\n")
    out.append(para("""Full observations: phase_F13_3b_checkpoint_assertions.csv. G4 reran f133b_keys.R and f133b_main.py into data/rerun2
        (inside the git-ignored data/), compared the bytes of tables/, data/, figures/ (PDF, PNG, TIF and CSV) and the numbers, then removed the
        folder; Louvain clusters are renumbered deterministically, so equal bytes also mean equal partitions."""))
    out.append("## 12. Independent verifier\n")
    if ver:
        out.append(L.md_table(["check", "what", "expected", "observed", "verdict"], ver) + "\n")
        out.append(para(f"""A subagent wrote its own Python code (programs/f133b_verify.py) without reading the phases' programs:
            {sum(1 for r in ver if r.get('verdict') == 'PASS')} PASS, {sum(1 for r in ver if r.get('verdict') == 'EXPLAINED')} EXPLAINED,
            {sum(1 for r in ver if r.get('verdict') == 'FAIL')} FAIL of {len(ver)} rows (phase_F13_3b_independent_verification.csv)."""))
    else:
        out.append("(verifier pending)\n")
    out.append("## 13. Disclosures\n")
    disc = [
        """R19: the work key is F13.3's own work_key() from phase_F13_3/programs/f133_lib.R, sourced read-only (sourcing also loads bibliometrix
        and igraph, unused). work_key_n() for 4 and 8 title words is a copy of it with the word count as a parameter, asserted identical at 6;
        name_shaped() is copied from f133_main.R.""",
        """Title and source follow F13.3's rule. In the exported format the year comes last, so the brief's 'segment between the authors and the
        year' is F13.3's first non-author segment (title) and the next one (source); titles containing commas are cut there.""",
        """pandas was not needed: the csv module reads the inputs. All libraries were already installed; nothing was downloaded.""",
        """Besides the inputs named in the brief, F13.3's cited_sources_thesaurus.csv, T3a, T3c, T6c, T6c2 and T0a were read: steps 1 and 6
        name the thesaurus and the comparisons; their digests are in the stamp.""",
        f"""Local citations: {t3a['local citation links (citing record -> cited record)']} / {t3a['citing records']} / {t3a['cited records (LCS > 0)']}
        / {t3a['LCS, max']} against the professor's 538 / 270 / 228 / 12. Normalisation, haystack, length threshold and whole-word variants
        change nothing (T3a3); keeping ambiguous titles gives more links. The verifier tried 14 variants; the closest, allowing a record to
        cite itself, gives 536 / 270 / 231. The remaining gap is not explained.""",
        """F13.3's surname rule, reused unchanged (R19), strips only a trailing block of space-separated initials; for hyphenated initials
        ('A.-B.') the first initial stays in the key's surname (309 references). Grouping is consistent because one rule applies everywhere,
        but such a work cited once with and once without the hyphen splits. The verifier's own parser agrees on 490 of 500 sampled keys
        (98.0 %, the brief's threshold); all ten differences are hyphenated initials.""",
        """The control (T3a2) does not remove links; it shows that most links carry the cited record's first-author surname and a year within one
        year; a few links rest on a title alone.""",
        """Works, coupling and co-citation use the references longer than 10 characters, as F13.3 did (1,347 short ones excluded); local
        citations use all 28,471. Coupling uses all 841 records (F13.3's sensitivity had 840 after bibliometrix's first-letter filter); the
        counts are the same (401 records, 699 links).""",
        """Clusters come from networkx's Louvain (seed 42), not igraph's; the number of coupling clusters with at least 10 records is the
        same (12), and the co-citation network equals F13.3's sensitivity (197 / 133 / 364 / 22 / 9).""",
        """Collisions: the similarity threshold (0.8) is a heuristic; which of the flagged keys are really different works was judged by reading
        the four examples.""",
        """Cited works' first-author surnames appear in T1b, T2, T4b2, T5b and the co-citation figure, as R13 allows for cited works; some of
        these persons also author corpus records. As in F13.3, G2 allows names only in those columns.""",
        """The historiograph draws all records cited at least twice, including those without a link to another drawn record (F13.3's histPlot
        dropped such isolates).""",
        """F13.3 recorded no per-file digest of references_repaired.csv; G1 shows the file unchanged since this phase's step 0 and equal in
        content to F13.3's count (28,471 references in 837 records).""",
        """Registry: this phase's row is in run_logs/registry_rows_pending.json for the main session's script; the registry was not read.""",
    ]
    out.append("\n".join(L.wrap(f"{k}. " + " ".join(d.split())) for k, d in enumerate(disc, 1)) + "\n")
    out.append("## 14. Строка реестра\n")
    if pending:
        r = pending[-1]
        out.append(L.md_table(["phase_id", "status", "produced_numbers", "safe_to_publish", "file_count", "bytes"], [r]) + "\n")
        out.append(para("Note: " + r["note"]))
    else:
        out.append("(fixed point pending)\n")
    return "\n".join(out)


if __name__ == "__main__":
    print("build() is called by f133b_final.py")
