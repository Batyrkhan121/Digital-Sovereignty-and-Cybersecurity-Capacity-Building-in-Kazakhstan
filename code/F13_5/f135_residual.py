"""Phase F13.5 - step 5: residual scan R1 over the T1 tables after v4 (author, index); copied from F12.3c's residual scan;
changed: (iii) classes (c') and (f) added, declared keeps read from the candidates of v2, v3 and v4.
Classes: (a) equal without spaces; (b) X / X+s, X / X+es, X+y / X+ies; (c) final-bracket forms; (c') mid-string brackets;
(d) British / American endings; (e) acronyms with a single long form (printed residue); (f) a keyword of >= 2 words with exactly
one token in the abbreviation table whose expanded form is in T1 or among the thesaurus 'to' / 'from' values. The table is
rebuilt here from the rows of thesaurus v4 (by their rule) plus the brief's explicit list. Writes tables/R1_residual_scan.csv."""
import sys
sys.dont_write_bytecode = True

import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f135_lib as L

PLURAL_NAMES = {"internet of things", "industrial internet of things", "digital forensics", "multi criteria", "internet of vehicles"}
ENDINGS = [("isation", "ization"), ("ise", "ize"), ("our", "or"), ("lling", "ling"), ("ence", "ense"), ("yse", "yze")]
STOP = {"of", "and", "the", "for", "in", "a", "to"}
BR = re.compile(r"(.+?)\s*\((.+)\)")
MID = re.compile(r"(.*?)\s*\(([^()]*)\)\s*(.*\S)")
TOKEN = re.compile(r"[a-z0-9]{2,6}")
EXPLICIT_ABBR = {"iot": "internet of things", "iiot": "industrial internet of things", "ai": "artificial intelligence", "ml": "machine learning",
                 "dl": "deep learning", "ids": "intrusion detection system", "uav": "unmanned aerial vehicle", "sdn": "software defined networking",
                 "nlp": "natural language processing", "dos": "denial of service", "ddos": "distributed denial of service",
                 "fpga": "field programmable gate array", "puf": "physical unclonable function", "wsn": "wireless sensor network",
                 "cps": "cyber physical system", "ict": "information and communication technology", "cnn": "convolutional neural network",
                 "ecc": "elliptic curve cryptography", "qkd": "quantum key distribution", "llm": "large language model"}
FUNCTION_WORDS = {"a", "an", "as", "am", "at", "be", "by", "do", "in", "is", "no", "of", "on", "or", "so", "to", "up", "we", "and", "are",
                  "for", "the", "via", "with", "from", "into", "its", "not", "but", "can", "has", "was", "all", "any"}


def declared_keep():
    """Pairs and single forms kept by a declared decision: keep rows of the candidates of v2 (F12.3b), v3 (F12.3c) and v4."""
    pairs, singles = {}, {}
    for p, note in ((L.F123B / "tables" / "thesaurus_candidates_v2.csv", "v2"), (L.PREV_T / "thesaurus_candidates_v3.csv", "v3"),
                    (L.TABLES / "thesaurus_candidates_v4.csv", "v4")):
        for r in L.read_csv_path(p):
            if r["decision"] != "keep":
                continue
            if " | " in r["pair"]:
                a, b = r["pair"].split(" | ")
                pairs[(a, b)] = f"{note} keep ({r['class']}): {r['reason']}"
            else:
                singles[r["pair"]] = f"{note} keep ({r['class']}): {r['reason']}"
    return pairs, singles


def abbreviation_table(rows):
    TH = {r["from"]: r["to"] for r in rows}

    def fin(x):
        return TH.get(x, x)

    t = {}
    for r in rows:
        rule, f = r["rule"], r["from"]
        if r["version"] == "v1" and rule.startswith("abbreviation to long form"):
            t.setdefault(f, set()).add(fin(r["to"]))
        elif r["version"] == "v1" and rule.startswith("long form with abbreviation in parentheses"):
            t.setdefault(BR.fullmatch(f).group(2).strip(), set()).add(fin(r["to"]))
        elif rule.startswith(("v3 c bracket: abbreviation in brackets", "v4 c bracket (new form): abbreviation in brackets")):
            t.setdefault(BR.fullmatch(f).group(2).strip(), set()).add(fin(r["to"]))
        elif rule.startswith(("v3 c bracket: reverse form", "v4 c bracket (new form): reverse form")):
            t.setdefault(BR.fullmatch(f).group(1).strip(), set()).add(fin(r["to"]))
        elif rule.startswith("v3 e acronym"):
            t.setdefault(f, set()).add(fin(r["to"]))
        elif rule.startswith("v4 c' mid bracket: abbreviation in brackets"):
            m = MID.fullmatch(f)
            t.setdefault(m.group(2).strip(), set()).add(fin(m.group(1).strip()))
        elif rule.startswith("v4 c' mid bracket: reverse form"):
            m = MID.fullmatch(f)
            t.setdefault(m.group(1).strip(), set()).add(fin(m.group(2).strip()))
    for ab, lf in EXPLICIT_ABBR.items():
        t.setdefault(ab, set()).add(fin(lf))
    return t


def initials(form):
    return "".join(w[0] for w in form.split() if w not in STOP)


def scan(au, ix, thes):
    K = sorted(set(au) | set(ix))
    S = set(K)
    pairs_keep, singles_keep = declared_keep()
    out = []

    def add(cls, a, b, status, note=""):
        out.append({"class": cls, "a": a, "b": b, "records_author_a": au.get(a, 0), "records_author_b": au.get(b, 0) if b else "",
                    "records_index_a": ix.get(a, 0), "records_index_b": ix.get(b, 0) if b else "", "status": status, "note": note})

    groups = {}
    for k in K:
        groups.setdefault(k.replace(" ", ""), []).append(k)
    for ks in groups.values():
        ks = sorted(ks)
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                key = (ks[i], ks[j])
                add("a", ks[i], ks[j], "declared keep" if key in pairs_keep else "residual", pairs_keep.get(key, ""))
    for k in K:
        for p in [k + "s", k + "es"] + ([k[:-1] + "ies"] if k.endswith("y") else []):
            if p in S:
                key = (k, p)
                if key in pairs_keep:
                    add("b", k, p, "declared keep", pairs_keep[key])
                else:
                    add("b", k, p, "residual", "plural-name concept" if p in PLURAL_NAMES else "")
    for k in K:
        if BR.fullmatch(k):
            add("c", k, "", "declared keep" if k in singles_keep else "residual", singles_keep.get(k, ""))
        elif MID.fullmatch(k):
            add("c'", k, "", "declared keep" if k in singles_keep else "residual", singles_keep.get(k, ""))
    for k in K:
        for uk, us in ENDINGS:
            if uk in k:
                alt = k.replace(uk, us)
                if alt != k and alt in S:
                    add("d", k, alt, "declared keep" if (k, alt) in pairs_keep else "residual", pairs_keep.get((k, alt), ""))
    by_init = {}
    for f in K:
        if len(f.split()) >= 2:
            by_init.setdefault(initials(f), set()).add(f)
    for k in K:
        if TOKEN.fullmatch(k) and (au.get(k, 0) >= 2 or ix.get(k, 0) >= 2):
            finals = sorted(by_init.get(k, set()) - {k})
            if len(finals) == 1:
                add("e", k, finals[0], "residual", "one long form left unmerged (printed residue)")
    tb = abbreviation_table(thes)
    tos, froms = {r["to"] for r in thes}, {r["from"] for r in thes}
    for k in K:
        toks = k.split()
        if len(toks) < 2:
            continue
        hits = [t for t in toks if len(t) > 1 and not t.isdigit() and t not in FUNCTION_WORDS and t in tb]
        if len(hits) != 1:
            continue
        t = hits[0]
        if len(tb[t]) > 1:
            add("f", k, "", "declared keep" if k in singles_keep else "residual", singles_keep.get(k, "ambiguous abbreviation, undeclared"))
            continue
        exp = " ".join(next(iter(tb[t])) if x == t else x for x in toks)
        present = exp in S or exp in tos or exp in froms
        if len(exp.split()) > 6:
            # counted, not printed (keywords over 6 words stay out of the outputs)
            add("f", k, "", "declared keep" if k in singles_keep else "residual",
                singles_keep.get(k, f"expanded form of {len(exp.split())} words, undeclared"))
        elif not present:
            st = "declared keep" if (k, exp) in pairs_keep else "residual"
            add("f", k, exp, st, pairs_keep.get((k, exp), "expanded form absent or over 6 words, undeclared"))
        else:
            add("f", k, exp, "declared keep" if (k, exp) in pairs_keep else "residual", pairs_keep.get((k, exp), "expanded form present"))
    return out, tb


def main():
    au = {r["keyword"]: int(r["records"]) for r in L.read_csv_path(L.TABLES / "T1_author_frequencies.csv")}
    ix = {r["keyword"]: int(r["records"]) for r in L.read_csv_path(L.TABLES / "T1_index_frequencies.csv")}
    thes = L.read_csv_path(L.TABLES / "thesaurus.csv")
    rows, tb = scan(au, ix, thes)
    summary = {}
    for r in rows:
        summary.setdefault(r["class"], {}).setdefault(r["status"], 0)
        summary[r["class"]][r["status"]] += 1
    f = ["class", "a", "b", "records_author_a", "records_author_b", "records_index_a", "records_index_b", "status", "note"]
    L.write_csv(L.TABLES / "R1_residual_scan.csv", f, rows)
    L.jdump({"summary": summary, "table_size": len(tb)}, L.RUN_LOGS / "R1_summary.json")
    print(json.dumps(summary, indent=1))
    for r in rows:
        if r["status"] == "residual" and r["class"] != "e":
            print("RESIDUAL", r["class"], "|", r["a"], "|", r["b"], "|", r["note"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
