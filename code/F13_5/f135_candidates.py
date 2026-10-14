"""Phase F13.5 - steps 2-3: thesaurus v4 candidates from the T1 tables of the run 'E1 x v3' (tables/v3_on_E1/, both layers) and
thesaurus v4 (copied from F12.3c's candidates program; changed: (ii) the classes).

(c') a bracket in mid-string, 'X (Y) Z' (Z not empty): Y without spaces, <= 8 characters of [a-z0-9./-] -> merge to 'X Z'
     (spaces collapsed); else X without spaces, <= 8 characters and Y with a space (reverse form) -> merge to 'Y Z'; else keep.
     The same rule with an empty Z (v3's class c) is applied to final-bracket forms new to the frame (not in F12.3c's T1).
(f) an abbreviation inside a multi-word keyword. The table abbreviation -> long form comes from the thesaurus itself (v1 rows
     'abbreviation to long form' and v1 bracket rows; v3 rows of class c - the bracketed token, or X of a reverse form - and of
     class e - the 'from'; v4 rows of class c' - Y -> X, or X -> Y for a reverse form) plus the brief's explicit list; every long
     form resolved to its final form. A keyword of >= 2 words with exactly one token in the table (tokens of one character, digit
     tokens and English stop words are not considered) is expanded (token -> final long form); expanded form in T1 of either
     layer, or a thesaurus 'to' (or 'from') -> merge to its final form; else keep 'expanded form absent' (for the author); an
     abbreviation with several final long forms -> keep 'ambiguous'; an expanded form of more than 6 words -> keep.
(t) the tail, as in v3 (joined/spaced, plural, British/American; short forms <= 3 characters kept; v3's plural-name concepts).
All classes run on resolved forms and are repeated until no new merge appears (merges create new pairs and new table entries).
Linked merges form groups with one sink; every 'to' is resolved to its final form; a v3 row whose 'to' merges in v4 is
retargeted (printed)."""
import sys
sys.dont_write_bytecode = True

import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f135_lib as L

PLURAL_NAMES = ["internet of things", "industrial internet of things", "digital forensics", "multi criteria", "internet of vehicles"]
EXPLICIT_KEEP = {("s models", "smodels"): "different concepts possible: Smodels is an answer-set solver (kept since F12.3b)",
                 ("smodel", "smodels"): "different concepts possible: Smodels is an answer-set solver (as s models / smodels)"}
PLURAL_LAST_WORDS = {"biometrics": "biometrics names the field ('biometric' is an adjective)",
                     "analytics": "analytics names the field ('analytic' is an adjective)",
                     "dynamics": "system dynamics names the method ('dynamic' is an adjective)",
                     "robotics": "robotics names the field ('robotic' is an adjective)",
                     "means": "'means' (instruments) has no singular 'mean' in this sense"}
ENDINGS = [("isation", "ization"), ("ise", "ize"), ("our", "or"), ("lling", "ling"), ("ence", "ense"), ("yse", "yze")]
SHORT = 3
LIMIT = 700
EXPLICIT_ABBR = [("iot", "internet of things"), ("iiot", "industrial internet of things"), ("ai", "artificial intelligence"),
                 ("ml", "machine learning"), ("dl", "deep learning"), ("ids", "intrusion detection system"), ("uav", "unmanned aerial vehicle"),
                 ("sdn", "software defined networking"), ("nlp", "natural language processing"), ("dos", "denial of service"),
                 ("ddos", "distributed denial of service"), ("fpga", "field programmable gate array"), ("puf", "physical unclonable function"),
                 ("wsn", "wireless sensor network"), ("cps", "cyber physical system"), ("ict", "information and communication technology"),
                 ("cnn", "convolutional neural network"), ("ecc", "elliptic curve cryptography"), ("qkd", "quantum key distribution"),
                 ("llm", "large language model")]
# executor's guard (declared): English function words are not read as abbreviations inside a keyword (an, as, am would turn
# 'security as a service' into a nonsense expansion); the table entries this drops are printed in the status. 'it' is read:
# in E1's keywords it always stands for information technology (it security, it audit, it sector)
STOPWORDS = {"a", "an", "as", "am", "at", "be", "by", "do", "in", "is", "no", "of", "on", "or", "so", "to", "up", "we", "and", "are",
             "for", "the", "via", "with", "from", "into", "its", "not", "but", "can", "has", "was", "all", "any"}
BR = re.compile(r"(.+?)\s*\((.+)\)")
MID = re.compile(r"(.*?)\s*\(([^()]*)\)\s*(.*\S)")
ABBR = re.compile(r"[a-z0-9.\-]{1,8}")
ABBR_MID = re.compile(r"[a-z0-9./\-]{1,8}")


def considered(tok):
    return len(tok) > 1 and not tok.isdigit() and tok not in STOPWORDS


def abbreviates(short, long):
    """Executor's test for the final-bracket forms new to the frame (declared): E1's index terms use brackets for qualifiers
    ('gateways (computer networks)', 'mercury (metal)'); a short form counts as an abbreviation of the long form only when their
    first characters are equal and every character of the short form occurs in the long form in the same order."""
    s = re.sub(r"[^a-z0-9]", "", short)
    lf = re.sub(r"[^a-z0-9]", "", long)
    if not s or not lf or s[0] != lf[0]:
        return False
    it = iter(lf)
    return all(ch in it for ch in s)


def main():
    V3T = L.V3E1
    au = {r["keyword"]: int(r["records"]) for r in L.read_csv_path(V3T / "T1_author_frequencies.csv")}
    ix = {r["keyword"]: int(r["records"]) for r in L.read_csv_path(V3T / "T1_index_frequencies.csv")}
    K = sorted(set(au) | set(ix))
    T1KEYS = set(K)
    old = {r["keyword"] for n in ("author", "index") for r in L.read_csv_path(L.PREV_T / f"T1_{n}_frequencies.csv")}
    v3 = L.read_csv_path(L.PREV_T / "thesaurus.csv")
    M3 = {r["from"]: r["to"] for r in v3}
    keep_prev = set()
    for p in (L.F123B / "tables" / "thesaurus_candidates_v2.csv", L.PREV_T / "thesaurus_candidates_v3.csv"):
        for r in L.read_csv_path(p):
            if r["decision"] == "keep" and " | " in r["pair"]:
                keep_prev.add(tuple(r["pair"].split(" | ")))
    qmd = L.path("main.qmd").read_bytes().decode("utf-8").lower()
    for h in L.HYPHENS:
        qmd = qmd.replace(h, " ")
    qmd = " ".join(qmd.split())

    def qcount(form):
        return len(re.findall(r"(?<![a-z0-9])" + re.escape(form) + r"(?![a-z0-9])", qmd))

    rows, edges = [], []
    decided = set(keep_prev) | {(b, a) for a, b in keep_prev}
    cprime_pairs = []      # (abbreviation, long form) from the v4 bracket rows

    def rec(a, b, cls, decision, reason, mf="", mt="", lfm="", ra=None, rb=None, ia=None, ib=None):
        rows.append({"pair": f"{a} | {b}" if b else a, "class": cls,
                     "records_author_a": au.get(a, 0) if ra is None else ra, "records_author_b": (au.get(b, 0) if rb is None else rb) if b else "",
                     "records_index_a": ix.get(a, 0) if ia is None else ia, "records_index_b": (ix.get(b, 0) if ib is None else ib) if b else "",
                     "decision": decision, "reason": reason, "merge_from": mf, "merge_to": mt, "long_form_matched": lfm})
        if b:
            decided.add((a, b))
            decided.add((b, a))
        if decision == "merge":
            edges.append((mf, mt))

    # (c') and (c) on new final-bracket forms
    for k in K:
        m = MID.fullmatch(k)
        if m and not k.endswith(")"):
            x, y, z = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
            if not x:
                rec(k, "", "c' mid bracket", "keep", "no words before the bracket")
            elif " " not in y and ABBR_MID.fullmatch(y):
                to = " ".join((x + " " + z).split())
                rec(k, to, "c' mid bracket", "merge", f"abbreviation in brackets: '{y}'", k, to)
                cprime_pairs.append((y, x, k))
            elif " " not in x and len(x) <= 8 and " " in y:
                to = " ".join((y + " " + z).split())
                rec(k, to, "c' mid bracket", "merge", f"reverse form: '{x}' with the long form in brackets", k, to)
                cprime_pairs.append((x, y, k))
            else:
                rec(k, "", "c' mid bracket", "keep", "not an abbreviation in brackets nor a reverse form")
            continue
        m = BR.fullmatch(k)
        if m and k not in old:
            x, y = m.group(1).strip(), m.group(2).strip()
            if " " not in y and ABBR.fullmatch(y) and abbreviates(y, x):
                rec(k, x, "c bracket (new form)", "merge", f"abbreviation in brackets: '{y}'", k, x)
                cprime_pairs.append((y, x, k))
            elif " " not in x and len(x) <= 8 and " " in y and abbreviates(x, y):
                rec(k, y, "c bracket (new form)", "merge", f"reverse form: '{x}' with the long form in brackets", k, y)
                cprime_pairs.append((x, y, k))
            elif (" " not in y and ABBR.fullmatch(y)) or (" " not in x and len(x) <= 8 and " " in y):
                rec(k, "", "c bracket (new form)", "keep", "qualifier in brackets: fails the abbreviation test (first character, order)")
            else:
                rec(k, "", "c bracket (new form)", "keep", "not an abbreviation in brackets nor a reverse form")

    def groups_to_map(edge_list):
        parent = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for a, b in edge_list:
            parent[find(a)] = find(b)
        comp = {}
        for a, b in edge_list:
            for x in (a, b):
                comp.setdefault(find(x), set()).add(x)
        srcs = {a for a, _ in edge_list}
        out, bad = {}, []
        for members in comp.values():
            sinks = sorted(m for m in members if m not in srcs)
            if len(sinks) != 1:
                bad.append(sorted(members))
                continue
            for m in members:
                if m != sinks[0]:
                    out[m] = sinks[0]
        assert not bad, ("groups without a single sink", bad)
        return out

    state = {"new": groups_to_map(edges)}

    def resolve(x, seen=()):
        assert x not in seen, ("cycle", x)
        if x in state["new"]:
            return resolve(state["new"][x], seen + (x,))
        if x in M3:
            return resolve(M3[x], seen + (x,))
        return x

    def plural_name(p):
        return any(p == n or p.endswith(" " + n) for n in PLURAL_NAMES)

    def table():
        """abbreviation -> {final long form: [sources]}"""
        t = {}

        def add(ab, lf, src):
            t.setdefault(ab, {}).setdefault(resolve(lf), []).append(src)

        for r in v3:
            rule = r["rule"]
            if r["version"] == "v1" and rule.startswith("abbreviation to long form"):
                add(r["from"], r["to"], "v1 row")
            elif r["version"] == "v1" and rule.startswith("long form with abbreviation in parentheses"):
                add(BR.fullmatch(r["from"]).group(2).strip(), r["to"], "v1 bracket row")
            elif rule.startswith("v3 c bracket: abbreviation in brackets"):
                add(BR.fullmatch(r["from"]).group(2).strip(), r["to"], "v3 c row")
            elif rule.startswith("v3 c bracket: reverse form"):
                add(BR.fullmatch(r["from"]).group(1).strip(), r["to"], "v3 c row (reverse)")
            elif rule.startswith("v3 e acronym"):
                add(r["from"], r["to"], "v3 e row")
        for ab, lf, src in cprime_pairs:
            add(ab, lf, f"v4 bracket row '{src}'")
        for ab, lf in EXPLICIT_ABBR:
            add(ab, lf, "explicit list")
        return t

    pending_f = {}
    passes = 0
    while True:
        passes += 1
        assert passes <= 8
        before = len(edges)
        tag = "" if passes == 1 else f" (pass {passes})"
        state["new"] = groups_to_map(edges)
        cau, cix = {}, {}
        for k in K:
            f_ = resolve(k)
            cau[f_] = cau.get(f_, 0) + au.get(k, 0)
            cix[f_] = cix.get(f_, 0) + ix.get(k, 0)
        CS = sorted(set(cau) | set(cix))
        CSS = set(CS)

        def rec_t(a, b, cls, decision, reason, mf="", mt=""):
            rec(a, b, cls + tag, decision, reason, mf, mt, ra=cau.get(a, 0), rb=cau.get(b, 0), ia=cix.get(a, 0), ib=cix.get(b, 0))

        # (t) tail
        groups = {}
        for k in CS:
            groups.setdefault(k.replace(" ", ""), []).append(k)
        for ks in groups.values():
            ks = sorted(ks)
            for i in range(len(ks)):
                for j in range(i + 1, len(ks)):
                    a, b = ks[i], ks[j]
                    if (a, b) in decided:
                        continue
                    ra, rb = cau.get(a, 0), cau.get(b, 0)
                    if ra != rb:
                        to, why = (a, f"author {ra} > {rb}") if ra > rb else (b, f"author {rb} > {ra}")
                    elif qcount(a) != qcount(b):
                        to = a if qcount(a) > qcount(b) else b
                        why = f"author tie {ra}; main.qmd {qcount(a)} / {qcount(b)}"
                    else:
                        to = a if " " not in a else b
                        why = f"author tie {ra}; main.qmd tie {qcount(a)}; joined form"
                    rec_t(a, b, "t tail joined/spaced", "merge", why, b if to == a else a, to)
        for k in CS:
            for p in [k + "s", k + "es"] + ([k[:-1] + "ies"] if k.endswith("y") else []):
                if p not in CSS or (k, p) in decided:
                    continue
                if min(len(k), len(p)) <= SHORT:
                    rec_t(k, p, "t tail plural", "keep", f"short form (<= {SHORT} characters; possible abbreviation; author's rule)")
                elif (k, p) in EXPLICIT_KEEP:
                    rec_t(k, p, "t tail plural", "keep", EXPLICIT_KEEP[(k, p)])
                elif plural_name(p):
                    rec_t(k, p, "t tail plural", "merge", "plural-name concept: singular to plural", k, p)
                elif p.split()[-1] in PLURAL_LAST_WORDS:
                    rec_t(k, p, "t tail plural", "merge", "plural-name concept: singular to plural; " + PLURAL_LAST_WORDS[p.split()[-1]], k, p)
                else:
                    rec_t(k, p, "t tail plural", "merge", "plural to singular", p, k)
        for k in CS:
            for uk, us in ENDINGS:
                if uk in k:
                    alt = k.replace(uk, us)
                    if alt != k and alt in CSS and (k, alt) not in decided:
                        rec_t(k, alt, "t tail spelling", "merge", f"British to American ending ({uk} -> {us})", k, alt)
        state["new"] = groups_to_map(edges)

        # (f) on the forms as resolved now
        TB = table()
        TO = {resolve(v) for v in M3.values()} | {resolve(b) for _, b in edges}
        FROM = set(M3) | {a for a, _ in edges}
        cur = sorted({resolve(k) for k in K})
        pending_f = {}
        for k in cur:
            toks = k.split()
            if len(toks) < 2:
                continue
            hits = [t for t in toks if considered(t) and t in TB]
            if len(hits) != 1:
                continue
            t = hits[0]
            finals = sorted(TB[t])
            srcs = "; ".join(f"{lf} ({', '.join(sorted(set(s)))})" for lf, s in sorted(TB[t].items()))
            if len(finals) > 1:
                pending_f[k] = (k, "", "keep", f"ambiguous abbreviation '{t}': " + "; ".join(finals[:3]), "", "", srcs)
                continue
            exp = " ".join(finals[0] if x == t else x for x in toks)
            if len(exp.split()) > 6:
                # keywords over 6 words are counted, not printed (brief): the expanded form is left out of the row
                pending_f[k] = (k, "", "keep", f"expanded form of {len(exp.split())} words (> 6; not printed): '{t}' -> '{finals[0]}'", "", "", srcs)
                continue
            where = ("in T1" if exp in T1KEYS else "a thesaurus 'to'" if exp in TO else "a thesaurus 'from'" if exp in FROM else "")
            if where:
                tgt = resolve(exp)
                rec(k, exp, "f embedded abbreviation" + tag, "merge", f"'{t}' -> '{finals[0]}'; expanded form {where}", k, tgt, srcs,
                    ra=cau.get(k, 0), rb=cau.get(exp, 0), ia=cix.get(k, 0), ib=cix.get(exp, 0))
            else:
                pending_f[k] = (k, exp, "keep", f"expanded form absent ('{t}' -> '{finals[0]}')", "", "", srcs)
        if len(edges) == before:
            break

    state["new"] = groups_to_map(edges)
    cau, cix = {}, {}
    for k in K:
        f_ = resolve(k)
        cau[f_] = cau.get(f_, 0) + au.get(k, 0)
        cix[f_] = cix.get(f_, 0) + ix.get(k, 0)
    for k in sorted(pending_f):
        a, b, d, why, mf, mt, srcs = pending_f[k]
        if resolve(k) != k:
            continue
        rec(a, b, "f embedded abbreviation", d, why, mf, mt, srcs, ra=cau.get(a, 0), rb=cau.get(b, 0) if b else 0,
            ia=cix.get(a, 0), ib=cix.get(b, 0) if b else 0)
    f = ["pair", "class", "records_author_a", "records_author_b", "records_index_a", "records_index_b", "decision", "reason",
         "merge_from", "merge_to", "long_form_matched"]
    L.write_csv(L.TABLES / "thesaurus_candidates_v4.csv", f, rows)

    # thesaurus v4
    newfinal = {k: resolve(v) for k, v in state["new"].items()}
    out, retarget = [], []
    for r in v3:
        to = r["to"]
        fin = resolve(to)
        if fin != to:
            retarget.append({"from": r["from"], "version": r["version"], "to_v3": to, "to_v4": fin})
            out.append({"from": r["from"], "to": fin, "rule": r["rule"] + "; retargeted in v4 (its 'to' merged in v4)", "version": r["version"]})
        else:
            out.append(dict(r))
    for k in sorted(newfinal):
        assert k not in M3, ("already a v3 from", k)
        pr = next(r for r in rows if r["merge_from"] == k)
        rule = f"v4 {pr['class']}: {pr['reason']}" + (f"; group final form '{newfinal[k]}'" if newfinal[k] != pr["merge_to"] else "")
        out.append({"from": k, "to": newfinal[k], "rule": rule, "version": "v4"})
    froms, tos = {r["from"] for r in out}, {r["to"] for r in out}
    classes = sorted({r["class"] for r in rows})
    TB = table()
    dropped = sorted(ab for ab in TB if not considered(ab))
    tail_rows = [r for r in rows if r["class"].startswith("t ")]
    status = {"rows_v3": len(v3), "rows_new": len(newfinal), "rows_v4": len(out), "limit": LIMIT, "from_cap_to": sorted(froms & tos),
              "passes": passes, "retargeted_v3_rows": retarget, "plural_names": PLURAL_NAMES,
              "by_class": {c: {d: sum(1 for r in rows if r["class"] == c and r["decision"] == d) for d in ("merge", "keep")} for c in classes},
              "table_size": len(TB), "table_ambiguous": {ab: sorted(v) for ab, v in sorted(TB.items()) if len(v) > 1},
              "table_entries_not_considered": dropped, "stopword_guard": sorted(STOPWORDS),
              "tail_pairs": len(tail_rows),
              "tail_pairs_with_a_new_form": sum(1 for r in tail_rows if any(x not in old for x in r["pair"].split(" | "))),
              "T1_forms": len(K), "T1_forms_new_to_frame": len(T1KEYS - old)}
    L.jdump(status, L.RUN_LOGS / "thesaurus_v4_status.json")
    L.jdump({ab: {lf: sorted(set(s)) for lf, s in sorted(v.items())} for ab, v in sorted(TB.items())}, L.RUN_LOGS / "abbreviation_table_v4.json")
    print(json.dumps({k: v for k, v in status.items() if k not in ("plural_names", "stopword_guard")}, ensure_ascii=False, indent=1))
    for r in rows:
        print(r["class"], "|", r["pair"], "|", r["decision"], "|", r["reason"], "|", r["merge_to"])
    if len(out) > LIMIT or (froms & tos):
        print("NOT WRITTEN: over the limit or a chain")
        return 1
    L.write_csv(L.TABLES / "thesaurus.csv", ["from", "to", "rule", "version"], out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
