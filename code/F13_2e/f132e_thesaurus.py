"""Phase F13.2e - step 1: thesaurus v3.1 = the 274 rows of v3 + the nine rows of the professor's list (author's decision 48). No new
clustering. Changes to existing rows: (i) the v3 rows 'caspian ...' -> Yessenov University gain "author's confirmation, decision 48" in
reason (brief); (ii) declared, needed by row 7: 'Institute of Informatics and Control Problems' is the canonical of two v3 rows; with
its own key merged into IICT those two rows would form a chain and keep two records apart, so they are marked 'superseded (decision
48)' and re-mapped to IICT by two follow-on v3.1 rows (the F13.2c precedent of decision 45). Writes tables/institutions_thesaurus_v31.csv,
tables/T1_thesaurus_v31_changes.csv/md and run_logs/thesaurus_v31_status.json."""
import sys
sys.dont_write_bytecode = True

import json
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132e_lib as L

C = L.C
RULE = "merge: professor's list (v3.1), author's decision 48"
LIST = [
    ("NC JSC “S.Seifullin KATU”", "S. Seifullin Kazakh Agrotechnical Research University", "abbreviation KATU of the Seifullin university"),
    ("KazNMU named after S.D. Asfendiyarov", "Asfendiyarov Kazakh National Medical University", "abbreviation KazNMU"),
    ("G. Daukeev University of Power Engineering", "Almaty University of Power Engineering and Telecommunications named after Gumarbek Daukeyev",
     "a variant of AUPET's name"),
    ("Baytursynov Kostanay State University", "Akhmet Baitursynuly Kostanay Regional University", "former name"),
    ("Non-Profit Limited Company A. Baitursynov KRU", "Akhmet Baitursynuly Kostanay Regional University", "abbreviation KRU"),
    ("Kazakh-Turkish University named after H. A. Yesevi B.", "Khoja Akhmet Yassawi International Kazakh-Turkish University", "transliteration Yesevi"),
    ("Institute of Informatics and Control Problems", "Institute of Information and Computational Technologies",
     "former name of IICT until 2014; its records date from before 2017"),
    ("Karagandy State Technical University", "Abylkas Saginov Karaganda Technical University", "former name"),
    ("Kokshetau State University", "Sh. Ualikhanov Kokshetau University", "former name"),
]
FIELDS = ["variant", "canonical", "rule", "records", "confidence", "reason", "version", "status"]
CASPIAN_NOTE = "; author's confirmation, decision 48"
SUPERSEDED = "superseded (decision 48: its canonical joins IICT)"


def key_records():
    _, R = L.records()
    kz = defaultdict(set)
    for r in R:
        for p in r["lines"]:
            if p["country_part"] == L.KZ:
                kz[C.norm_kz(p["institution"])].add(r["eid"])
    return kz


def main():
    v3 = L.read_csv(L.IN_V3["thesaurus"])
    t3a = {r["institution"]: r for r in L.read_csv(L.IN_V3["T3a"])}
    kz = key_records()
    out, changed = [], []
    moved_canon = LIST[6][0]
    follow = []
    for r in v3:
        r2 = dict(r)
        if r["version"] == "v3" and "caspian" in r["variant"] and r["canonical"] == "Yessenov University" and r["status"] == "active":
            r2["reason"] = r["reason"] + CASPIAN_NOTE
            changed.append({"change": "reason: author's confirmation", **r2})
        if r["canonical"] == moved_canon and r["status"] == "active":
            r2["status"] = SUPERSEDED
            changed.append({"change": "status: superseded (row 7)", **r2})
            follow.append({"variant": r["variant"], "canonical": LIST[6][1], "rule": RULE, "records": len(kz.get(r["variant"], ())), "confidence": "high",
                           "reason": "follows row 7: a spelling of the Institute of Informatics and Control Problems, IICT's former name",
                           "version": "v3.1", "status": "active"})
        out.append(r2)
    new = []
    for name, canon, why in LIST:
        assert name in t3a and canon in t3a, (name, canon)
        v = C.norm_kz(name)
        new.append({"variant": v, "canonical": canon, "rule": RULE, "records": len(kz.get(v, ())), "confidence": "high", "reason": why,
                    "version": "v3.1", "status": "active"})
    out += new + follow
    L.write_csv(L.TABLES / "institutions_thesaurus_v31.csv", FIELDS, out)
    rows = [{"change": "new (professor's list)", **r} for r in new] + [{"change": "new (follow-on of row 7)", **r} for r in follow] + changed
    L.table("T1_thesaurus_v31_changes", "Thesaurus v3.1 - new rows and changed rows (the full v3.1 is tables/institutions_thesaurus_v31.csv)",
            ["change"] + FIELDS, rows)
    act = [r for r in out if r["status"] == "active"]
    merge_from = {r["variant"] for r in act if r["rule"].startswith("merge")}
    to_norm = {C.norm_kz(r["canonical"]) for r in act}
    keys207 = {C.norm_kz(n) for n in t3a}
    same = [a == b for a, b in zip(v3, out[:len(v3)])]
    diff_fields = sorted({k for a, b in zip(v3, out[:len(v3)]) for k in FIELDS if a[k] != b[k]})
    status = {"v3_rows": len(v3), "v31_rows": len(out), "new_rows_list": len(new), "new_rows_follow_on": len(follow),
              "v3_rows_unchanged": sum(same), "v3_rows_changed": len(same) - sum(same), "changed_fields": diff_fields,
              "caspian_reason_rows": sum(1 for c in changed if c["change"].startswith("reason")), "superseded_rows": len(follow),
              "from_cap_to": sorted(merge_from & to_norm), "chains": sorted(r["variant"] for r in act if C.norm_kz(r["canonical"]) in merge_from),
              "keep_not_identity": sorted(r["variant"] for r in act if r["rule"].startswith("keep") and C.norm_kz(r["canonical"]) != r["variant"]),
              "active_variants_unique": len([r["variant"] for r in act]) == len({r["variant"] for r in act}),
              "list_variants_among_207": all(r["variant"] in keys207 for r in new),
              "follow_on_variants_are_v3_variants": all(any(f["variant"] == r["variant"] for r in v3) for f in follow),
              "records_of_new_keys": {r["variant"]: r["records"] for r in new + follow}}
    L.jdump(status, L.RUN_LOGS / "thesaurus_v31_status.json")
    print(json.dumps(status, ensure_ascii=True, indent=1))
    ok = (not status["from_cap_to"] and not status["chains"] and not status["keep_not_identity"] and status["active_variants_unique"]
          and status["list_variants_among_207"] and set(diff_fields) <= {"reason", "status"})
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
