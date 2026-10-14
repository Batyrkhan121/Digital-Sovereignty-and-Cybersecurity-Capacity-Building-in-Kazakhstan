"""Phase F13.2e - the report, built from the phase's records. Prose hard-wrapped (<= 25 words a line, gate G2)."""
import sys
sys.dont_write_bytecode = True

import json
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132e_lib as L

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


EXPECTED = {"Institute of Information and Computational Technologies": "<= 66",
            "Almaty University of Power Engineering and Telecommunications named after Gumarbek Daukeyev": "70",
            "S. Seifullin Kazakh Agrotechnical Research University": "22", "Akhmet Baitursynuly Kostanay Regional University": "7",
            "Asfendiyarov Kazakh National Medical University": "3", "Khoja Akhmet Yassawi International Kazakh-Turkish University": "4",
            "Abylkas Saginov Karaganda Technical University": "7", "Sh. Ualikhanov Kokshetau University": "6"}


def build(row, gates):
    num = j(L.OUT / "F13_2e_numbers.json")
    st = j(L.RUN_LOGS / "thesaurus_v31_status.json")
    stamp = j(L.OUT / "F13_2e_brief_stamp.json")
    ver = rows("phase_F13_2e_independent_verification.csv", L.OUT)
    out = ["# Phase F13.2e - institutions thesaurus v3.1: the nine residual spellings (author's decision 48)\n"]
    status = row["status"] if row else "(dry run - no pending registry row yet)"
    out.append(W(f"Status: {status}. Repository: {stamp['root']} (PHASE_REGISTRY.csv not touched during the phase). Brief: F13_2e_brief.md "
                 f"(sha256 {stamp['brief_sha256']}). E1 equals its accepted digest: {stamp['E1_accepted']}; read for EID, Year, Affiliations and "
                 "the count of Authors. No new clustering. The recount is F13.2d's function (f132d_build.tables_for, read-only); run with v3 it "
                 f"reproduces F13.2d's T3a_v3 and T3c_v3 exactly: {num['v3_reproduced_exactly']}. T2g follows F13.2b's rule (f132b_lib, read-only). "
                 "phase_F13_3b was neither read nor snapshotted. Supersedes F13.2d's T3a_v3, T3c_v3, T3d_v3, T2f_v3, T2f2_v3 and F13.2b's T2g.") + "\n")
    out.append("## 1. Thesaurus v3.1 - the nine rows, and what else changed\n")
    out.append(W(f"tables/institutions_thesaurus_v31.csv: {st['v31_rows']} rows = the {st['v3_rows']} rows of v3 in order + {st['new_rows_list']} rows "
                 f"of the professor's list + {st['new_rows_follow_on']} follow-on rows. Existing rows changed: {st['v3_rows_changed']} "
                 f"({st['caspian_reason_rows']} 'caspian' rows gain \"author's confirmation, decision 48\" in reason; {st['superseded_rows']} rows "
                 "superseded, see below); changed fields: " + ", ".join(st["changed_fields"]) + f". Chains {len(st['chains'])}; from and to disjoint "
                 f"{not st['from_cap_to']}; variants unique {st['active_variants_unique']}; the nine variants among the 207 names "
                 f"{st['list_variants_among_207']}.") + "\n")
    out.append(md("T1_thesaurus_v31_changes.md"))
    out.append(W("Row 7 needs two more rows. 'Institute of Informatics and Control Problems' was the canonical of two v3 rows (institute for "
                 "problems of informatics and control; institute of informatics and control sciences). Mapping its own key to IICT alone would "
                 "leave those two rows pointing at a name that is now a variant (a chain) and two of its three records apart. The two v3 rows "
                 "are therefore marked 'superseded (decision 48)' and re-mapped to IICT by two follow-on rows, as F13.2c did for decision 45; "
                 "the brief's 'nine new rows, reason the only change' cannot hold for row 7 otherwise.") + "\n")
    out.append("## 2. Recount\n")
    out.append(md("T3a_v31_kz_institutions.md"))
    a31 = {r["institution"]: r for r in rows("T3a_v31_kz_institutions.csv")}
    exp_rows = [{"institution": n, "records_v3": a31[n]["records_v3"], "records_v31": a31[n]["records"], "expected": e,
                 "rank_v3": a31[n]["rank_v3"], "rank_v31": a31[n]["rank"]} for n, e in EXPECTED.items()]
    out.append("### The nine affected institutions against the brief's expectation\n\n" + L.md_table(
        ["institution", "records_v3", "records_v31", "expected", "rank_v3", "rank_v31"], exp_rows) + "\n")
    out.append(W(f"Institutions {num['institutions_v3']} -> {num['institutions_v31']} (expected 198); links {num['links_v3']} -> {num['links_v31']}; "
                 f"rank changes in the top 10: {', '.join(num['top10_rank_moves']) or 'none'}.") + "\n")
    out.append(md("T3c_v31_concentration.md"))
    out.append(md("T3d_v31_kz_institution_pairs.md"))
    out.append(md("T2f2_v31_collaboration_by_period.md"))
    out.append(md("T2g_v31_authors_by_collaboration.md"))
    out.append(md("T2h_collaboration_transitions.md"))
    d1 = rows("D1_deltas_v3_v31.csv")
    cnt = Counter((r["table"], "row removed" if r["field"] == "(row)" else r["field"]) for r in d1)
    out.append("### D1 - changed cells against v3 (summary; every cell in tables/D1_deltas_v3_v31.csv)\n\n" + L.md_table(
        ["table", "field", "cells"], [{"table": t, "field": f, "cells": n} for (t, f), n in sorted(cnt.items())]) + "\n")
    out.append(L.md_table(["table", "row", "field", "old", "new"], [r for r in d1 if r["table"] == "T3c" or (r["table"] == "T3a" and r["field"] in ("records", "(row)"))]) + "\n")
    out.append("## 3. For the professor\n")
    moved = sum(num["transitions"].values())
    out.append(bullets([
        f"Nine spellings joined their institutions (decision 48): Kazakhstan institutions {num['institutions_v3']} -> {num['institutions_v31']}; "
        "IICT 63 -> 66, AUPET 69 -> 70, Seifullin 21 -> 22, Baitursynuly 5 -> 7, KazNMU 2 -> 3, Yassawi 3 -> 4, Saginov KTU 6 -> 7, "
        "Ualikhanov 5 -> 6; the top 10 keeps its order.",
        f"Collaboration types do not change ({moved} records move; international {num['collab_v31']['international']}); T2g therefore equals v3's; "
        "against F13.2b (thesaurus v1) four records moved from domestic multi-institution to single institution in F13.2d.",
        "Left as it is: '68/74 Abay Ave.' (a street address parsed as an institution, one record); the Caspian rows now carry the author's "
        "confirmation.",
    ]))
    out.append("## 4. Gates\n")
    lines = ["| gate | what | verdict | planted violation caught |", "| --- | --- | --- | --- |"]
    lines += [f"| {g['gate']} | {g['what']} | {g['verdict']} | {g['planted_verdict']} ({g['falsifiability']}) |" for g in gates]
    out.append("\n".join(lines) + "\n")
    first = rows("phase_F13_2e_checkpoint_assertions_first_run.csv", L.OUT)
    if first:
        out.append(W("First run: " + ", ".join(f"{g['gate']} {g['verdict']}" for g in first) + ".") + "\n")
    out.append("## 5. Independent verification\n")
    if ver:
        lines = ["| check | what | tables | recomputed | verdict |", "| --- | --- | --- | --- | --- |"]
        lines += ["| " + " | ".join(" ".join(str(r.get(k, "")).replace("|", "/").split()[:14])[:100] for k in
                                    ("check_id", "what", "expected_from_tables", "recomputed", "verdict")) + " |" for r in ver]
        out.append("\n".join(lines) + "\n")
        out.append(W(f"A subagent wrote its own program (programs/f132e_verify.py) without reading this phase's other programs: "
                     f"{sum(1 for r in ver if r.get('verdict') == 'PASS')} of {len(ver)} PASS.") + "\n")
    else:
        out.append("(not yet run)\n")
    out.append("## 6. Disclosures\n")
    out.append(bullets([
        "Row 7: two follow-on rows and two v3 rows set to 'superseded (decision 48)' (section 1); without them the thesaurus would hold a chain "
        "and IICT would gain one record instead of three. The brief's checks hold otherwise (v3 within v3.1 apart from these declared cells).",
        "'68/74 Abay Ave.' stays an institution row of one record, as the brief directs; it is a street address, not an institution.",
        "pandas was not needed: the tables are small and the csv module keeps F13.2d's exact formatting.",
        "The registry is written after the closing by one run of tools/registry_apply.py without --hold; its result (rows before and after, "
        "rows added) is in the closing message and in the tool's journal tools/registry_apply_<UTC>.json. It cannot stand in this report: "
        "the row records this folder's file count and bytes, which the report is part of.",
        "No network, no heredoc, no workflow or skill; one subagent (the verifier); nothing in .claude/; nothing deleted or moved; phase_F13_2d "
        "and phase_F13_2b read only; CORRECTIONS.csv unchanged (in the snapshot).",
    ]))
    out.append("## 7. Registry row\n")
    if row:
        out.append(W(f"{row['phase_id']} | {row['status']} | produced_numbers {row['produced_numbers']} | safe_to_publish {row['safe_to_publish']} | "
                     f"{row['file_count']} files, {row['bytes']} bytes (the folder's fixed point). Ready row: run_logs/registry_rows_pending.json.") + "\n")
        out.append(W("Note of the row: " + row["note"]) + "\n")
    else:
        out.append("(dry run)\n")
    return "\n".join(out)
