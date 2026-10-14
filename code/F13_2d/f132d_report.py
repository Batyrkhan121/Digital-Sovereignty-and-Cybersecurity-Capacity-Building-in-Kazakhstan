"""Phase F13.2d - the report, built from the phase's records. Prose hard-wrapped (<= 25 words a line, gate G2)."""
import sys
sys.dont_write_bytecode = True

import json
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132d_lib as L

W = L.wrap


def j(p):
    return json.loads(Path(p).read_bytes().decode("utf-8"))


def rows(name, folder=None):
    p = (folder or L.TABLES) / name
    return L.read_csv_path(p) if p.exists() else []


def md(name):
    return (L.TABLES / name).read_bytes().decode("utf-8").replace("## ", "### ", 1)


def bullets(items, width=22):
    return "\n".join("- " + W(x, width).replace("\n", "\n  ") for x in items) + "\n"


BOUNDS = {"Al-Farabi Kazakh National University": 156, "Institute of Information and Computational Technologies": 60,
          "L.N. Gumilyov Eurasian National University": 173, "Satbayev University": 75,
          "Almaty University of Power Engineering and Telecommunications named after Gumarbek Daukeyev": 68, "Yessenov University": 80}


def build(row, gates):
    num = j(L.OUT / "F13_2d_numbers.json")
    st = j(L.RUN_LOGS / "thesaurus_v3_status.json")
    stamp = j(L.OUT / "F13_2d_brief_stamp.json")
    inst = j(L.RUN_LOGS / "install_rapidfuzz.json")
    ver = rows("phase_F13_2d_independent_verification.csv", L.OUT)
    out = ["# Phase F13.2d - institutions thesaurus v3: merging the one-record spellings\n"]
    status = row["status"] if row else "(dry run - no pending registry row yet)"
    out.append(W(f"Status: {status}. Repository: {stamp['root']} (PHASE_REGISTRY.csv not touched during the phase). Brief: F13_2d_brief.md "
                 f"(sha256 {stamp['brief_sha256']}). E1 equals its accepted digest: {stamp['E1_accepted']}; only EID, Year and Affiliations read. "
                 f"Thesaurus v2 of F13.2c: {stamp['thesaurus_v2_rows']} rows ({stamp['thesaurus_v2_active']} active). The parsing is F13.2c's "
                 "(phase_F13_2c/programs/f132c_lib.py and f132c_build.labels, imported read-only; digests in the stamp); run with thesaurus v2 "
                 f"it reproduces F13.2c's T3a_v2 and T3c_v2 exactly: {num['v2_reproduced_exactly']}. phase_F13_6b was neither read nor "
                 "snapshotted. Supersedes F13.2c's T3a_v2, T3c_v2, T3d_v2, T2f_v2, T2f2_v2.") + "\n")
    out.append("## 1. Tools\n")
    out.append(W(f"Python {sys.version.split()[0]} by explicit path; rapidfuzz {stamp['rapidfuzz']} for the candidate scores "
                 f"(process.cdist with fuzz.token_set_ratio). rapidfuzz was not installed: {inst['command']} from {inst['source']} before step 0 "
                 f"({inst['downloaded']}; {inst['result']}) - the phase's only network use; no program of the phase imports a network module. "
                 "pandas (installed) was not needed: the tables are small and the csv module keeps F13.2c's exact formatting.") + "\n")
    out.append("## 2. Stop-list (generic tokens)\n")
    gen = rows("generic_tokens.csv")
    out.append(W(f"{len(gen)} tokens, all from the brief ({', '.join(r['token'] for r in gen)}); the executor added none, because the clusters are "
                 "only candidates and the decision rule reads name tokens.") + "\n")
    out.append("## 3. Candidates and decisions (T1a-T1d)\n")
    t1b = rows("T1b_decisions.csv")
    out.append(W(f"{st['names']} institutions of T3a_v2; candidate pairs (same distinctive key or token_set_ratio >= 80): {st['pairs']}; clusters of "
                 f"two or more names: {st['clusters']} with {st['clustered_names']} names. Decisions: accept {st['decisions']['accept']}, partly "
                 f"accept {st['decisions']['partly accept']}, reject {st['decisions']['reject']}. Merged: {st['names_merged']} names into "
                 f"{st['identities_merged']} institutions (confidence high {st['confidence']['high']}, medium {st['confidence']['medium']}). "
                 "Union-find chains clusters through descriptive words (cluster 1 holds 126 names linked by information, almaty, international, "
                 "astana): the clusters are candidates; the rule decides name by name.") + "\n")
    out.append(md("T1b_decisions.md"))
    out.append(md("T1b3_identities.md"))
    out.append(md("T1c_exclusions.md"))
    out.append(md("T1d_name_token_rules.md"))
    t1a = rows("T1a_candidate_clusters.csv")
    out.append("### T1a - the first 30 clusters (one row per name)\n\n" + L.md_table(
        ["cluster_id", "institution", "records", "distinctive_key", "best_score"], [r for r in t1a if int(r["cluster_id"]) <= 30]) + "\n")
    out.append(W("Decisions per name (merge / canon / reject with reason): tables/T1b2_name_decisions.csv.") + "\n")
    out.append("## 4. Thesaurus v3 - the new rows\n")
    out.append(W(f"tables/institutions_thesaurus_v3.csv: {st['v3_rows']} rows = the {st['v2_rows']} rows of v2 unchanged + {st['names_merged']} "
                 f"new. Checks: v2 within v3 row by row {st['v2_in_v3_rowwise']}; from and to disjoint {not st['from_cap_to']}; chains "
                 f"{len(st['chains'])}; one variant one canonical {st['active_variants_unique']}; every new variant among the 348 names "
                 f"{not st['new_variants_not_in_348']}.") + "\n")
    out.append(md("T2_thesaurus_v3_new_rows.md"))
    out.append("## 5. Recount with v3\n")
    out.append(md("T3a_v3_kz_institutions.md"))
    a3 = rows("T3a_v3_kz_institutions.csv")
    over = [f"{r['institution']} {r['records']} (bound {BOUNDS[r['institution']]})" for r in a3 if r["institution"] in BOUNDS
            and int(r["records"]) > BOUNDS[r["institution"]]]
    moves = [f"{r['institution']} {r['rank_v2']} -> {r['rank']}" for r in a3[:10] if r["rank_v2"] and int(r["rank_v2"]) != int(r["rank"])]
    out.append(W(f"Institutions {num['institutions_v2']} -> {num['institutions_v3']} (the brief expected about 260-300: the rule merged "
                 f"{st['names_merged']} names, more than the variants counted in the brief); links {num['links_v2']} -> {num['links_v3']}. Rank "
                 f"changes in the top 10: {'; '.join(moves) or 'none'}. Above the brief's upper bounds: {'; '.join(over) or 'none'} - the rule "
                 "found more spellings than the brief counted (tables/T2_thesaurus_v3_new_rows.csv lists them).") + "\n")
    out.append(md("T3c_v3_concentration.md"))
    out.append(md("T3d_v3_kz_institution_pairs.md"))
    out.append(md("T2f2_v3_collaboration_by_period.md"))
    out.append(md("T2g_collaboration_transitions.md"))
    d1 = rows("D1_deltas_v2_v3.csv")
    cnt = Counter((r["table"], "row removed" if r["field"] == "(row)" else r["field"]) for r in d1)
    out.append("### D1 - changed cells against v2 (summary; every cell in tables/D1_deltas_v2_v3.csv)\n\n" + L.md_table(
        ["table", "field", "cells"], [{"table": t, "field": f, "cells": n} for (t, f), n in sorted(cnt.items())]) + "\n")
    out.append(L.md_table(["table", "row", "field", "old", "new"], [r for r in d1 if r["table"] in ("T3c", "T2f2")]) + "\n")
    out.append("## 6. Residual (T4)\n")
    t4 = rows("T4_residual.csv")
    out.append(W("Counts by kind: " + "; ".join(f"{k} {v}" for k, v in num["residual_by_kind"].items()) + ". The rows of the first kind are likely "
                 "missed spellings that never formed a candidate pair (score below 80); they are left for the author (the brief allows no manual "
                 "variant list). '68/74 Abay Ave.' is a street address parsed as an institution, not Abai KazNPU.") + "\n")
    out.append(L.md_table(["institution", "canon", "kind", "reason"], [r for r in t4 if r["kind"] == "identity token, not a candidate"][:20]) + "\n")
    out.append("## 7. For the professor\n")
    t2g = rows("T2g_collaboration_transitions.csv")
    moved = sum(int(r["records"]) for r in t2g if r["type_v2"] != r["type_v3"])
    top = a3[:10]
    out.append(bullets([
        f"Thesaurus v3 merges {st['names_merged']} one-record spellings into {st['identities_merged']} institutions; Kazakhstan institutions "
        f"{num['institutions_v2']} -> {num['institutions_v3']}, institutions with one record {num_one(rows)}.",
        "Top 10 after v3: " + "; ".join(f"{r['institution'].split(' named after')[0]} {r['records']} ({'+' + str(r['delta']) if r['delta'] not in ('', '0') else '='})"
                                       for r in top) + (f". Rank change: {'; '.join(moves)}." if moves else "."),
        f"{moved} records change collaboration type (domestic multi-institution -> single institution: two spellings of one university); "
        f"international stays {num['collab_v3']['international']}.",
        f"Unresolved: {len(num['residual_identity_misses'])} likely spellings outside the candidate pairs (T4); Caspian State University of "
        "Technologies and Engineering = Yessenov University awaits the author's confirmation; departments named without their university stay "
        "separate; the T1c pairs stay apart by rule.",
    ]))
    out.append("## 8. Gates\n")
    lines = ["| gate | what | verdict | planted violation caught |", "| --- | --- | --- | --- |"]
    lines += [f"| {g['gate']} | {g['what']} | {g['verdict']} | {g['planted_verdict']} ({g['falsifiability']}) |" for g in gates]
    out.append("\n".join(lines) + "\n")
    first = rows("phase_F13_2d_checkpoint_assertions_first_run.csv", L.OUT)
    if first:
        out.append(W("First run: " + ", ".join(f"{g['gate']} {g['verdict']}" for g in first) + ".") + "\n")
    out.append("## 9. Independent verification\n")
    if ver:
        lines = ["| check | what | tables | recomputed | verdict |", "| --- | --- | --- | --- | --- |"]
        lines += ["| " + " | ".join(" ".join(str(r.get(k, "")).replace("|", "/").split()[:14])[:100] for k in
                                    ("check_id", "what", "expected_from_tables", "recomputed", "verdict")) + " |" for r in ver]
        out.append("\n".join(lines) + "\n")
        out.append(W(f"A subagent wrote its own program (programs/f132d_verify.py) without reading this phase's other programs: "
                     f"{sum(1 for r in ver if r.get('verdict') == 'PASS')} of {len(ver)} PASS.") + "\n")
    else:
        out.append("(not yet run)\n")
    out.append("## 10. Disclosures\n")
    out.append(bullets([
        f"Installation: {inst['result']} ({inst['downloaded']}) from {inst['source']} before step 0, with the brief's leave; the only network use.",
        "The executor extended the brief's name-token list (T1d) for the identities found in the clusters, and the exclusions (T1c, 'executor' "
        "rows); medium confidence marks word combinations (for example almaty + power, caspian + technolog, humanitarian + innovative).",
        "Two rules beyond the brief's wording, both declared: names identical apart from legal-form words, quotes or function words are one "
        "institution; identity groups span clusters (IICT and Shakarim spellings fell in two clusters each).",
        "Canon ties among one-record names go to the name that is not a sub-unit, then fewer tokens, then fewer quote or bracket "
        "characters, then the alphabet; a typo can therefore become a canon (Friendship of Nations: 'Universuty').",
        "Previous decisions followed: v1 reads 'Abay University' as Abai KazNPU and KazNTU / KazNRTU as former names of Satbayev "
        "University; v3 applies the same readings to one-record spellings.",
        "Names that are already v2 institutions with two or more records are never made variants (no v2 row changes, no chain).",
        "The verifier's first run had 1 FAIL (C03b): 8 token labels, written by hand, listed fewer spellings than their tests accept "
        "(satpaev, essenov, ualijhanov, serikbaev, daukeev, alfarabi, inf / tech, interior). The labels are now generated from the tests; "
        "decisions and counts did not change; the verifier re-ran.",
        "Caspian State University of Technologies and Engineering is merged into Yessenov University as the brief directs; the "
        "author's confirmation is still requested (medium confidence).",
        "No network module in the phase's programs, no heredoc, no workflow or skill; one subagent (the verifier); nothing in .claude/; nothing "
        "deleted or moved; phase_F13_2c read only; CORRECTIONS.csv unchanged (in the snapshot).",
    ]))
    out.append("## 11. Registry row (to be added by tools/registry_apply.py after the closing)\n")
    if row:
        out.append(W(f"{row['phase_id']} | {row['status']} | produced_numbers {row['produced_numbers']} | safe_to_publish {row['safe_to_publish']} | "
                     f"{row['file_count']} files, {row['bytes']} bytes (the folder's fixed point). Ready row: run_logs/registry_rows_pending.json.") + "\n")
        out.append(W("Note of the row: " + row["note"]) + "\n")
    else:
        out.append("(dry run)\n")
    return "\n".join(out)


def num_one(rows_fn):
    c = {r["measure"]: r for r in rows_fn("T3c_v3_concentration.csv")}
    r = c["institutions with one record"]
    return f"{r['value_v2']} -> {r['value']}"
