"""Phase F13.2d - steps 1-2: candidate clusters (f132d_candidates), the decisions by rule and thesaurus v3.

Decision rule (brief, step 1): names of the clusters are merged when they share a distinctive "name" token (a surname or a unique word
or word combination: IDENTITIES below, the brief's list extended by the executor for the clusters found) and none of them stands in the
exclusions (EXCLUSIONS, tables/T1c_exclusions.csv); a cluster whose names share only generic or descriptive words is rejected. Two
further rules, declared: (a) names identical apart from legal-form words, quotes and function words are one institution; (b) a
department or institute named with its parent ("Department of ... University X") goes to the parent's canon. Identity groups are formed
over all clusters (one institution's spellings can fall in two clusters). Canon of a group: its T3a_v2 name with the most records
(ties: not a sub-unit, fewer tokens, alphabetical). A name that is already an institution of v2 with two or more records is never made
a variant (that would change a v2 row or create a chain). Writes tables/T1b_decisions.csv (one row per cluster), T1b2_name_decisions.csv
(one row per name), T1b3_identities.csv, T1c_exclusions.csv, T1d_name_token_rules.csv, institutions_thesaurus_v3.csv and
T2_thesaurus_v3_new_rows.csv/md; run_logs/thesaurus_v3_status.json."""
import sys
sys.dont_write_bytecode = True

import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132d_lib as L
import f132d_candidates as K

C = L.C
LEGAL = {"jsc", "llp", "nao", "njsc", "nc", "nplc", "company", "non", "profit", "limited", "joint", "stock", "liability", "institution", "ltd",
         "of", "the", "and", "in", "at", "for", "named", "after", "name", "by", "on"}


class Test:
    """A name test with its own description, so that the printed token rule always lists exactly what the test accepts."""
    def __init__(self, f, desc):
        self.f, self.desc = f, desc

    def __call__(self, S, k):
        return self.f(S, k)


def T(*ws):
    return Test(lambda S, k: set(ws) <= S, " + ".join(ws))


def ANY(*ws):
    return Test(lambda S, k: bool(set(ws) & S), " / ".join(ws))


def PH(*phrases):
    return Test(lambda S, k: any(p in k for p in phrases), " / ".join(f"'{p}'" for p in phrases))


def PRE(prefix):
    return Test(lambda S, k: any(t.startswith(prefix) for t in S), prefix + "*")


def AND(*fs):
    return Test(lambda S, k: all(f(S, k) for f in fs), " + ".join(f.desc for f in fs if not f.desc.startswith("not ")) +
                "".join(f" ({f.desc})" for f in fs if f.desc.startswith("not ")))


def NOT(f):
    return Test(lambda S, k: not f(S, k), "not " + f.desc)


def R(test, note, conf):
    """(test, token label, confidence): the label is the test's own description plus a note."""
    return (test, test.desc + (f" ({note})" if note else ""), conf)


# identity: (label, [(test, token label, confidence)]); the first matching test gives the name's token and confidence
IDENTITIES = [
    ("ENU", [R(ANY("gumilyov", "gumilev", "gumiyev", "gumileva", "gumilyev"), "", "high")]),
    ("KazNU", [R(ANY("farabi", "alfarabi"), "", "high")]),
    ("Satbayev", [R(ANY("satbayev", "satpayev", "satpaev", "kaznrtu", "kazntu"), "", "high"),
                  R(PH("kazakh national research technical university", "kazakh national technical university"), "former name, v1", "high"),
                  R(ANY("satbavev"), "misspelt satbayev", "medium")]),
    ("AUPET", [R(ANY("daukeyev", "daukeev", "aupet", "energo"), "", "high"),
               R(T("almaty", "power"), "AUPET's name, v1 practice", "medium"),
               R(T("almaty", "energy", "communications"), "v1 practice", "medium")]),
    ("Yessenov", [R(ANY("yessenov", "yesenov", "esenov", "essenov", "yesenova"), "", "high"),
                  R(AND(ANY("caspian"), PRE("technolog")), "former name; author's check requested", "medium")]),
    ("IICT", [R(ANY("iict"), "", "high"),
              R(AND(ANY("information", "informational"), ANY("computational")), "", "high"),
              R(AND(ANY("information", "informational"), ANY("computing")), "translation variant", "medium")]),
    ("KBTU", [R(ANY("kbtu", "british"), "", "high")]),
    ("Abai KazNPU", [R(AND(ANY("abai", "abay"), ANY("pedagogical")), "", "high"),
                     R(AND(ANY("abai", "abay"), NOT(ANY("myrzakhmetov", "kokshetau"))), "v1: the Abai University brand", "medium"),
                     R(AND(T("national", "pedagogical"), NOT(ANY("friendship", "south"))), "the only national one", "medium")]),
    ("Myrzakhmetov", [R(ANY("myrzakhmetov"), "", "high")]),
    ("Ualikhanov", [R(ANY("ualikhanov", "ualijhanov"), "", "high")]),
    ("Seifullin", [R(ANY("seifullin"), "", "high")]),
    ("Serikbayev", [R(ANY("serikbayev", "serikbaev"), "", "high")]),
    ("Buketov", [R(ANY("buketov"), "", "high")]),
    ("Zhubanov", [R(ANY("zhubanov"), "", "high")]),
    ("Baitursynuly", [R(ANY("baitursynov", "baytursynov", "baitursynuly", "baytursinuly"), "", "high")]),
    ("Shakarim", [R(PRE("shakarim"), "", "high")]),
    ("Dulaty", [R(ANY("dulaty", "dulati"), "", "high")]),
    ("Auezov", [R(ANY("auezov"), "", "high")]),
    ("Kozybayev", [R(ANY("kozybayev"), "", "high")]),
    ("Korkyt", [R(ANY("korkyt"), "", "high")]),
    ("Toraighyrov", [R(ANY("toraighyrov"), "", "high")]),
    ("Zhangir Khan", [R(ANY("zhangir"), "", "high")]),
    ("Nazarbayev University", [R(AND(ANY("nazarbayev"), NOT(ANY("intellectual"))), "", "high")]),
    ("Nazarbayev Intellectual Schools", [R(T("nazarbayev", "intellectual"), "", "high")]),
    ("Yassawi", [R(ANY("yassawi", "yasawi", "yesevi"), "", "high")]),
    ("Dosmukhamedov", [R(ANY("dosmukhamedov"), "", "high")]),
    ("Asfendiyarov", [R(ANY("asfendiyarov"), "", "high")]),
    ("Nur-Mubarak", [R(ANY("mubarak"), "", "high")]),
    ("TSARKA", [R(ANY("tsarka"), "", "high")]),
    ("Esil", [R(ANY("esil"), "", "high")]),
    ("Murtaza", [R(ANY("murtaza"), "renamed Taraz institute", "medium")]),
    ("KUTB", [R(ANY("kulazhanov"), "", "high"), R(PH("university of technology and business"), "", "medium")]),
    ("Yesbulatov MIA Academy", [R(ANY("yesbulatov", "esbulatov", "esbolatov"), "", "high"),
                                R(AND(T("almaty", "academy"), ANY("internal", "interior")), "v1", "medium")]),
    ("Turan University", [R(AND(ANY("turan"), NOT(ANY("astana"))), "", "high")]),
    ("Astana IT University", [R(T("astana", "it"), "", "high")]),
    ("IITU", [R(ANY("iitu"), "", "high"),
              R(AND(ANY("international"), ANY("information", "inf"), ANY("technology", "tech"), NOT(ANY("engineering"))), "", "medium")]),
    ("Almaty Management University", [R(ANY("almu"), "", "high"), R(T("almaty", "management"), "", "medium")]),
    ("Law Enforcement Academy", [R(AND(T("law", "enforcement"), PRE("prosecutor")), "", "medium")]),
    ("Civil Aviation Academy", [R(T("civil", "aviation"), "", "medium")]),
    ("Tynyshpayev Academy", [R(ANY("tynyshpaev", "tynyshpayev"), "", "high"),
                             R(AND(T("transport", "communications", "academy")), "", "medium")]),
    ("KHJIU", [R(T("humanitarian", "innovative"), "", "medium")]),
    ("International Educational Corporation", [R(T("educational", "corporation"), "", "medium")]),
    ("Informatics and Control", [R(T("informatics", "control"), "", "medium")]),
    ("KazNARU", [R(PH("national agrarian research university"), "", "high")]),
    ("Friendship of Nations", [R(T("friendship", "pedagogical"), "", "medium")]),
    ("National Defense University", [R(AND(T("defense", "university"), NOT(ANY("ministry"))), "", "medium")]),
]
# exclusions: (name as in T3a_v2, identity it must not join, reason) - the brief's list and the executor's additions
EXCLUSIONS = [
    ("Caspian University", "Yessenov", "brief: Caspian University (Almaty) is not the Caspian State University of Technologies (Yessenov)"),
    ("Turan Astana University", "Turan University", "brief: Turan-Astana University is not Turan University"),
    ("Astana International University", "Astana IT University", "brief: two different universities in Astana"),
    ("Nazarbayev Intellectual School", "Nazarbayev University", "brief: the schools are not the university"),
    ("Nazarbayev Intellectual Schools", "Nazarbayev University", "brief: the schools are not the university"),
    ("Abay Myrzakhmetov Kokshetau University", "Abai KazNPU", "brief: Kokshetau university, not Abai KazNPU"),
    ("Abai Myrzakhmetov Kokshetau University", "Abai KazNPU", "brief: Kokshetau university, not Abai KazNPU"),
    ("Kazakh National Agrarian Research University", "KazNU", "brief: KazNARU is not Al-Farabi KazNU"),
    ("Kazakh National Women‘s Teacher Training University", "KazNU", "brief: not Al-Farabi KazNU"),
    ("Kazakh National Women’s Teacher Training University", "KazNU", "brief: not Al-Farabi KazNU"),
    ("International Engineering Technological University", "IITU", "brief: IETU is not IITU"),
    ("Asfendiyarov Kazakh National Medical University", "KazNU", "brief: KazNMU is not KazNU"),
    ("Sanzhar Asfendiyarov Kazakh national medical University", "KazNU", "brief: KazNMU is not KazNU"),
    ("Abylkas Saginov Karaganda Technical University", "Buketov", "brief: Karaganda Technical University is not Buketov University"),
    ("Kazakhstan Humanitarian Law University", "KHJIU", "executor: KazGUU (Astana) is not the Humanitarian Juridical Innovative University (Semey)"),
    ("Eurasian Technological University", "ENU", "executor: a different Eurasian-named university (Almaty)"),
    ("Eurasian Humanitarian Institute", "ENU", "executor: a different Eurasian-named institute"),
    ("A.K. Kussayinov Eurasian Humanities Institute", "ENU", "executor: a different Eurasian-named institute"),
    ("Almaty Academy", "Yesbulatov MIA Academy", "executor: ambiguous short name, kept apart in v1"),
    ("Kokshetau State University", "Ualikhanov", "executor: two universities in Kokshetau; no name token"),
    ("Ministry of Defense of the Republic of Kazakhstan", "National Defense University", "executor: the ministry is not the university"),
    ("Karaganda Academy of the Ministry of Internal Affairs of the Republic of Kazakhstan named after Barimbek Beisenov", "Yesbulatov MIA Academy",
     "executor: the Karaganda academy is not the Almaty one"),
    ("Ministry of Internal Affairs of the Republic of Kazakhstan", "Yesbulatov MIA Academy", "executor: the ministry is not its academy"),
    ("Institute of Economics", "Kazakh University of Economics", "executor: only the word economics is shared; v1 found the parent unclear"),
    ("National Academy of Agrarian Sciences", "KazNARU", "executor: the academy of sciences is not the university"),
    ("South Kazakhstan Pedagogical University", "Abai KazNPU", "executor: a different pedagogical university (Shymkent)"),
    ("Kazakhstan Engineering Pedagogical Universuty of Friendship of Nations", "Abai KazNPU", "executor: a different pedagogical university"),
    ("Kazakhstan Engineering and Pedagogical University of Friendship of the People", "Abai KazNPU", "executor: a different pedagogical university"),
]


def is_subunit(name):
    return bool(C.UNIT_START.search(name or "")) or name.lower().startswith(("laboratory", "information processing", "information systems",
                                                                             "information security laboratory", "research institute", "ietp"))


def identity_of(name):
    S, k = set(L.tokens(name)), C.norm_kz(name)
    hits = []
    for label, tests in IDENTITIES:
        for f, tok, conf in tests:
            if f(S, k):
                hits.append((label, tok, conf))
                break
    return hits


def stray(name):
    """Characters other than letters, digits, spaces, hyphens, dots and apostrophes (quotes, brackets, commas): fewer is a cleaner canon."""
    return len(re.findall(r"[^\w\s.\-'’]", name or ""))


def reduced(name):
    return " ".join(t for t in L.tokens(name) if t not in LEGAL)


def main():
    names, keys, pairs, rows = K.clusters()
    K.write_tables(names, keys, pairs, rows)
    rec = dict(names)
    v2 = L.read_csv(L.IN_THES)
    act = [r for r in v2 if r["status"] == "active"]
    v2_canon = {r["canonical"] for r in act}
    protected = {n for n, c in names if c >= 2} | v2_canon
    excl = {(n, ident): why for n, ident, why in EXCLUSIONS}
    by_name = {}
    clustered = sorted({r["institution"] for r in rows}, key=lambda n: (-rec[n], n))
    cl_of = {r["institution"]: r["cluster_id"] for r in rows}
    for n in clustered:
        hits = identity_of(n)
        hits = [h for h in hits if (n, h[0]) not in excl]
        blocked = [ident for (nn, ident) in excl if nn == n]
        if len(hits) > 1:
            by_name[n] = {"identity": "", "token": "", "confidence": "", "status": "reject",
                          "reason": "conflict: tokens of " + " and ".join(h[0] for h in hits)}
        elif hits:
            by_name[n] = {"identity": hits[0][0], "token": hits[0][1], "confidence": hits[0][2], "status": "candidate", "reason": ""}
        else:
            by_name[n] = {"identity": "", "token": "", "confidence": "", "status": "reject",
                          "reason": ("excluded (T1c): " + ", ".join(blocked)) if blocked else "no shared name token (generic or descriptive words only)"}
    # rule (a): identical names apart from legal-form and function words, among names without an identity
    groups_a = {}
    for n in clustered:
        # an exclusion bars joining one named institution, not the merge of a name with its own identical spelling
        if by_name[n]["status"] == "reject" and not by_name[n]["reason"].startswith("conflict") and not is_subunit(n) and reduced(n):
            groups_a.setdefault(reduced(n), []).append(n)
    for key, ns in groups_a.items():
        if len(ns) >= 2:
            for n in ns:
                by_name[n] = {"identity": "same name: " + key, "token": "identical name (legal form, quotes or function words differ)",
                              "confidence": "high", "status": "candidate", "reason": ""}
    # identity groups over all clusters; canon; decisions
    groups = {}
    for n in clustered:
        if by_name[n]["status"] == "candidate":
            groups.setdefault(by_name[n]["identity"], []).append(n)
    new_rows, ident_rows = [], []
    for ident, ns in sorted(groups.items(), key=lambda kv: (-max(rec[n] for n in kv[1]), kv[0])):
        if len(ns) < 2:
            for n in ns:
                by_name[n].update(status="reject", reason=f"alone: no other name of {ident} in the clusters")
            continue
        ns = sorted(ns, key=lambda n: (-rec[n], is_subunit(n), len(L.tokens(n)), stray(n), n))
        canon = ns[0]
        merged = []
        for n in ns[1:]:
            if n in protected:
                by_name[n].update(status="reject", reason=f"kept: already a v2 institution with {rec[n]} records (would change v2)")
                continue
            by_name[n].update(status="merge", canonical=canon, reason=("sub-unit named with its parent; " if is_subunit(n) else "")
                              + f"shares '{by_name[n]['token']}' with {canon}")
            merged.append(n)
        by_name[canon].update(status="canon", canonical=canon, reason=f"canon of {ident} ({rec[canon]} records)")
        for n in merged:
            v = C.norm_kz(n)
            conf = "medium" if by_name[n]["confidence"] == "medium" or by_name[canon]["confidence"] == "medium" else "high"
            new_rows.append({"variant": v, "canonical": canon, "rule": f"merge: distinctive token {by_name[n]['token']} (v3)", "records": rec[n],
                             "confidence": conf, "reason": by_name[n]["reason"], "version": "v3", "status": "active", "_name": n, "_ident": ident})
        ident_rows.append({"identity": ident, "token_rule": by_name[canon]["token"], "canonical": canon, "canonical_records_v2": rec[canon],
                           "names_merged": len(merged), "records_of_merged_names": sum(rec[n] for n in merged),
                           "clusters": " ".join(sorted({str(cl_of[n]) for n in ns}, key=int)), "confidence": "medium" if any(
                               by_name[n]["confidence"] == "medium" for n in merged) else "high"})
    # tables T1b2 (per name), T1b (per cluster), T1b3 (per identity), T1c, T1d
    t1b2 = [{"cluster_id": cl_of[n], "institution": n, "records": rec[n], "identity": by_name[n]["identity"], "token": by_name[n]["token"],
             "decision": by_name[n]["status"], "canonical": by_name[n].get("canonical", ""), "confidence": by_name[n]["confidence"],
             "reason": by_name[n]["reason"]} for n in sorted(clustered, key=lambda n: (cl_of[n], -rec[n], n))]
    L.table("T1b2_name_decisions", "T1b2 - decision for every clustered name", ["cluster_id", "institution", "records", "identity", "token", "decision",
                                                                                 "canonical", "confidence", "reason"], t1b2)
    t1b = []
    for cid in sorted({r["cluster_id"] for r in rows}):
        ns = [r for r in t1b2 if r["cluster_id"] == cid]
        m = [r for r in ns if r["decision"] == "merge"]
        idents = sorted({r["identity"] for r in ns if r["decision"] in ("merge", "canon")})
        dec = "accept" if m and all(r["decision"] in ("merge", "canon") for r in ns) else "partly accept" if m else "reject"
        t1b.append({"cluster_id": cid, "names": len(ns), "merged": len(m), "canons": sum(1 for r in ns if r["decision"] == "canon"),
                    "rejected": sum(1 for r in ns if r["decision"] == "reject"), "decision": dec,
                    "identities": "; ".join(idents)[:180] if len(idents) <= 6 else f"{len(idents)} identities (T1b3)",
                    "reason": "names share a name token" if dec == "accept" else
                              "rejected names share only generic or descriptive words, or are excluded (T1b2)" if dec == "partly accept" else
                              "names share only generic or descriptive words, or are excluded (T1b2)"})
    L.table("T1b_decisions", "T1b - decision for every candidate cluster", ["cluster_id", "names", "merged", "canons", "rejected", "decision",
                                                                             "identities", "reason"], t1b)
    L.table("T1b3_identities", "T1b3 - accepted merges by institution (identity)", ["identity", "token_rule", "canonical", "canonical_records_v2",
                                                                                    "names_merged", "records_of_merged_names", "clusters", "confidence"], ident_rows)
    t1c = [{"institution": n, "not_to_join": ident, "reason": why, "in_T3a_v2": int(n in rec), "in_a_cluster": int(n in cl_of),
            "joined_anyway": int(by_name.get(n, {}).get("identity") == ident and by_name.get(n, {}).get("status") in ("merge", "canon"))}
           for n, ident, why in EXCLUSIONS]
    L.table("T1c_exclusions", "T1c - known different institutions with a shared token (exclusions)",
            ["institution", "not_to_join", "reason", "in_T3a_v2", "in_a_cluster", "joined_anyway"], t1c)
    t1d = [{"identity": lab, "test": tok, "confidence": conf} for lab, tests in IDENTITIES for _, tok, conf in tests]
    t1d.append({"identity": "(rule a) same name", "test": "identical apart from legal-form words, quotes and function words", "confidence": "high"})
    L.table("T1d_name_token_rules", "T1d - name tokens and word combinations used by the rule (the brief's list extended by the executor)",
            ["identity", "test", "confidence"], t1d)
    # thesaurus v3
    fields = ["variant", "canonical", "rule", "records", "confidence", "reason", "version", "status"]
    v3 = [{k: r[k] for k in fields} for r in v2] + [{k: r[k] for k in fields} for r in sorted(new_rows, key=lambda r: (r["canonical"], r["variant"]))]
    L.write_csv(L.TABLES / "institutions_thesaurus_v3.csv", fields, v3)
    L.table("T2_thesaurus_v3_new_rows", "Institutions thesaurus v3 - the new rows (the full v3 is tables/institutions_thesaurus_v3.csv)", fields,
            [{k: r[k] for k in fields} for r in sorted(new_rows, key=lambda r: (r["canonical"], r["variant"]))])
    # checks
    a3 = [r for r in v3 if r["status"] == "active"]
    merge_from = {r["variant"] for r in a3 if r["rule"].startswith("merge")}
    to_norm = {C.norm_kz(r["canonical"]) for r in a3}
    variants = [r["variant"] for r in a3]
    keys348 = {C.norm_kz(n) for n, _ in names}
    status = {"names": len(names), "clustered_names": len(clustered), "clusters": len(t1b), "pairs": len(pairs),
              "decisions": {d: sum(1 for r in t1b if r["decision"] == d) for d in ("accept", "partly accept", "reject")},
              "names_merged": len(new_rows), "identities_merged": len(ident_rows), "v2_rows": len(v2), "v3_rows": len(v3),
              "v2_in_v3_rowwise": v3[:len(v2)] == [{k: r[k] for k in fields} for r in v2], "from_cap_to": sorted(merge_from & to_norm),
              "chains": sorted(r["variant"] for r in a3 if C.norm_kz(r["canonical"]) in merge_from),
              "keep_not_identity": sorted(r["variant"] for r in a3 if r["rule"].startswith("keep") and C.norm_kz(r["canonical"]) != r["variant"]),
              "active_variants_unique": len(variants) == len(set(variants)), "new_variants_not_in_348": sorted(r["variant"] for r in new_rows if r["variant"] not in keys348),
              "exclusions_joined": [r["institution"] for r in t1c if r["joined_anyway"]], "generic_tokens": len(L.generic()),
              "confidence": {c: sum(1 for r in new_rows if r["confidence"] == c) for c in ("high", "medium")}}
    L.jdump(status, L.RUN_LOGS / "thesaurus_v3_status.json")
    print(json.dumps(status, ensure_ascii=True, indent=1))
    for r in ident_rows:
        print("IDENT", json.dumps(r, ensure_ascii=True))
    ok = (status["v2_in_v3_rowwise"] and not status["from_cap_to"] and not status["chains"] and not status["keep_not_identity"]
          and status["active_variants_unique"] and not status["new_variants_not_in_348"] and not status["exclusions_joined"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
