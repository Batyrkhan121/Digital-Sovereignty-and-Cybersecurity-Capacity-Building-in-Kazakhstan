"""Phase F13.2c - the report, built from the phase's records (counts only). Prose hard-wrapped (<= 25 words a line, gate G2)."""
import sys
sys.dont_write_bytecode = True

import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132c_lib as L

W = L.wrap


def j(p):
    return json.loads(Path(p).read_bytes().decode("utf-8"))


def md(name):
    return (L.TABLES / f"{name}.md").read_bytes().decode("utf-8").replace("## ", "### ", 1)


def rows(p):
    return L.read_csv_out(p) if Path(p).exists() else []


def bullets(items, width=22):
    return "\n".join("- " + W(x, width).replace("\n", "\n  ") for x in items) + "\n"


def build(rows_reg, gates):
    n = j(L.OUT / "F13_2c_numbers.json")
    st = j(L.OUT / "F13_2c_brief_stamp.json")
    ver = rows(L.OUT / "phase_F13_2c_independent_verification.csv")
    t1, t2, t3 = n["T1"], n["T2"], n["T3"]
    cl = t2["classes"]
    ci, cii, ciii = (cl[k] for k in [k for k in cl if k != "all international"])
    fa841, fa517 = t2["first_author_841"], t2["first_author_517"]
    out = ["# Phase F13.2c - international records by author (dual affiliations, first author, partners other than Ukraine) and institutions thesaurus v2\n"]
    out.append(W(f"Status: {'COMPLETE' if rows_reg else '(dry run)'}. Repository: {st['root']}; the phase registry is {st['registry_location']} "
                 f"(neither read nor written). Brief: F13_2c_brief.md (sha256 {st['brief_sha256']}). Counts only; no manuscript or package file "
                 "changed; CORRECTIONS.csv unchanged.") + "\n")
    out.append("## 1. Inputs\n")
    lines = ["| input | sha256 |", "| --- | --- |"] + [f"| {k} | {v['sha256']} |" for k, v in st["inputs"].items()]
    out.append("\n".join(lines) + "\n")
    out.append(W(f"E1's sha256 equals the value accepted in F13.1: {st['E1_equals_accepted_sha256']}.") + "\n")
    out.append("## 2. Parsing rule\n")
    out.append(bullets([
        "From E1 only EID, Year, Affiliations and Authors with affiliations are kept; Authors is turned into a count at once (for T1a). Author "
        "names stay in memory to tie addresses to an author inside one record; no name is written anywhere.",
        "Authors with affiliations is split on '; ' into entries. In E1 one entry is one author: the name (the text before the first ', ') "
        "followed by all of that author's affiliations joined by ', '. The brief expected an author with two affiliations to be repeated; "
        "E1 does not repeat authors.",
        "The rest of an entry is decomposed into lines of the record's own Affiliations column (longest lines tried first, recursively, "
        "until the rest is used up exactly). An entry that does not decompose has its countries read from the parts that are country names "
        "(fallback); an entry without ', ' has no affiliation.",
        "An author's countries are the last parts of its affiliation lines that are in phase_F13_2b's country list. Kinds: Kazakhstan only, "
        "foreign only, both (Kazakhstan and abroad), no address. Authors are positions within a record (one per entry).",
        "International record (the base of T2): at least one country other than Kazakhstan among the last parts of its Affiliations lines - "
        "the F13.2b rule.",
        "Classes: (i) an author with only foreign addresses and an author with a Kazakhstan address; (ii) no author with only foreign "
        "addresses, so every foreign address belongs to an author who also has a Kazakhstan address; (iii) an author with only foreign "
        "addresses and no author with a Kazakhstan address.",
        "Institutions, normalisation, labels and collaboration types: the F13.2b rules unchanged (copied from phase_F13_2b's library), with "
        "thesaurus v2 in place of v1.",
    ]))
    out.append("## 3. T1 - parsing\n")
    out += [md("T1a_parsing"), md("T1b_country_check")]
    out.append("## 4. T2 - structure of the international records\n")
    out += [md("T2a_international_by_author"), md("T2b_first_author_country"), md("T2c_partners_other_than_ukraine"),
            md("T2d_kazakhstan_positions"), md("T2e_top_partners_by_type")]
    out.append(W(f"(iii) is empty, as AFFILCOUNTRY(kazakhstan) in the E1 query implies: every international record has at least one author "
                 f"with a Kazakhstan address. The vacuous case of (ii) - no foreign address in the author column - occurs {t2['vacuous_ii']} times.") + "\n")
    out.append("## 5. Thesaurus v2 and the recomputed institution tables\n")
    out.append(W("This phase заменяет T3a, T3c, T3d, T2f, T2f2 фазы F13.2b (supersedes F13.2b T3a, T3c, T3d, T2f, T2f2): the tables "
                 "T3a_v2, T3c_v2, T3d_v2, T2f_v2 and T2f2_v2 are the ones to cite.") + "\n")
    out.append(W(f"Thesaurus v2 (tables/institutions_thesaurus_v2.csv): the {t3['v1_rows']} rows of v1 plus {t3['new_rows']} new row (every "
                 "Kazakhstan variant containing 'energo university'); the v1 row that kept Energo University apart is marked superseded. "
                 f"{t3['v2_rows']} rows, {t3['active_rows']} active. Only the new and changed rows:") + "\n")
    out.append(md("T3_thesaurus_v2_changes").split("\n", 2)[2])
    out += [md("T3a_v2_kz_institutions"), md("T3c_v2_concentration"), md("T2f2_v2_collaboration_by_period"), md("D1_deltas_v1_v2")]
    cv1, cv2 = t3["collab_v1"], t3["collab_v2"]
    changed = sum(abs(int(cv2[c]) - int(cv1[c])) for c in L.COLLAB) // 2
    out.append(W(f"Expected: AUPET 60 -> 63 (found {t3['aupet_records']}); collaboration types: {changed} records change type (the brief allowed up "
                 "to three) - the three Energo University records carry no other AUPET line, so no record loses an institution. T3d_v2 (all pairs) "
                 "and T2f_v2 (by year) are in tables/.") + "\n")
    out.append("## 6. For the professor\n")
    prof = [
        f"Of the {t2['base']} international records, {ci} ({L.pct(ci, t2['base'])} %) are co-authorship with at least one author based only "
        f"abroad; {cii} ({L.pct(cii, t2['base'])} %) rest on dual affiliations alone (every foreign address belongs to an author who also has "
        f"a Kazakhstan address); {ciii} have no author with a Kazakhstan address.",
        f"Who leads: in {fa517['foreign only']} of the {t2['base']} ({L.pct(fa517['foreign only'], t2['base'])} %) the first author has only "
        f"foreign addresses, in {fa517['Kazakhstan only']} only Kazakhstan ones, in {fa517['both (Kazakhstan and abroad)']} both; over all 841 "
        f"records a first author with only Kazakhstan addresses leads {fa841['Kazakhstan only']} ({L.pct(fa841['Kazakhstan only'], 841)} %).",
        f"Authors with a Kazakhstan address hold {t2['kz_share_mean']} % of the author positions of an international record on average "
        f"(median {t2['kz_share_median']} %); partners other than Ukraine appear in {t2['other_than_ukraine']['affiliations']} of the "
        f"{t2['base']} records, Ukraine alone in {t2['ukraine_only']['affiliations']}.",
        f"So '61.5 % international' stands as genuine co-authorship: {ci} of 841 records ({L.pct(ci, 841)} %) have an author based only "
        f"abroad; the wording should add that the first author is foreign-based in more than half of the international records "
        f"({fa517['foreign only']} of {t2['base']}).",
        f"Energo University is merged into AUPET (decision 45): AUPET {t3['aupet_records']} records; no collaboration type changes.",
    ]
    out.append(bullets(prof))
    out.append("## 7. Gates\n")
    lines = ["| gate | what | verdict | planted violation caught |", "| --- | --- | --- | --- |"]
    lines += [f"| {g['gate']} | {g['what']} | {g['verdict']} | {g['planted_verdict']} ({g['falsifiability']}) |" for g in gates]
    out.append("\n".join(lines) + "\n")
    first = rows(L.OUT / "phase_F13_2c_checkpoint_assertions_first_run.csv")
    if first:
        out.append(W("First run: " + ", ".join(f"{g['gate']} {g['verdict']}" for g in first) + ".") + "\n")
    out.append("## 8. Independent verification\n")
    if ver:
        lines = ["| check | what | tables | recomputed | verdict |", "| --- | --- | --- | --- | --- |"]
        lines += ["| " + " | ".join(" ".join(str(r.get(k, "")).split()[:28]) for k in ("check_id", "what", "expected_from_tables", "recomputed", "verdict")) + " |"
                  for r in ver]
        out.append("\n".join(lines) + "\n")
        out.append(W(f"A subagent wrote its own program (programs/f132c_verify.py) from a description of the rules, without reading this phase's "
                     f"other programs: {sum(1 for r in ver if r.get('verdict') == 'PASS')} of {len(ver)} PASS.") + "\n")
    else:
        out.append("(not yet run)\n")
    out.append("## 9. Disclosures\n")
    out.append(bullets([
        "Format of Authors with affiliations: the brief describes an author repeated for each affiliation; in E1 an author is one entry "
        f"carrying all affiliations ({t1['multi_affiliation_authors']} authors with two or more). The parser follows E1; with it the author "
        "positions equal the Authors count in all 841 records.",
        "One record lists two consecutive entries with the same name; the Authors column counts both, so they are two authors. Names repeat "
        "inside nine records in all (counted, never printed).",
        "The Authors column is read only as a count (for T1a's comparison), as in F13.2b; the brief's list of loaded columns does not name it.",
        "The F13.2b parsing rules were copied unchanged from phase_F13_2b/programs/f132b_lib.py (read as code, not as data) into this phase's "
        "library; the F13.2b input tables were used only for the deltas and the check of 517.",
        "Gates, first run: G2 failed. Its 'Surname I.' shape test hit 28 strings that are parts of institution names in E1's Affiliations "
        "(for example 'Academician U.A.' in an institute's name). A shape that stands verbatim in the Affiliations text is now counted "
        "apart; the surname test (no surname of the author column in any output) found nothing in either run.",
        "E1's digest is checked against the value accepted in F13.1 (README_exports.txt is not an input of this phase).",
        "No network module in programs/ (G6); no heredoc, workflow or skill; one subagent (the verifier); nothing in .claude/; nothing deleted "
        "or moved (R17 audit hook); phase_F13_3, phase_F13_4b, phase_F13_6b and PHASE_REGISTRY.csv neither read nor written.",
        "Registry: no 'реестр' has been given in this session yet; the pending rows of F12_4, F13_1, F13_2, F13_2b and F13_6a are still unwritten.",
    ]))
    if rows_reg:
        out.append("## 10. Registry row (to be added on the author's command)\n")
        for r in rows_reg:
            out.append(W(f"{r['phase_id']} | {r['status']} | produced_numbers {r['produced_numbers']} | safe_to_publish {r['safe_to_publish']} | "
                         f"{r['file_count']} files, {r['bytes']} bytes | path {r['path']} | note: supersedes F13.2b T3a/T3c/T3d/T2f/T2f2") + "\n")
        out.append(W("The row is kept, unwritten, in run_logs/registry_rows_pending.json with its file count and bytes at the folder's fixed point.") + "\n")
    return "\n".join(out)
