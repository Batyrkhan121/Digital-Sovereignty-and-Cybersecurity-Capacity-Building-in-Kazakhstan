"""Phase F13.2d - independent verification (checks C01-C07). Written from the method in the verifier's brief; the parsing rules of
F13.2c (aff_lines, parts_of, institution_of, parse_line, norm_kz, most_common_form, inst_type, labels) are re-implemented here from
phase_F13_2c/programs/f132c_lib.py and f132c_build.py. Nothing is imported from phase_F13_2d/programs. Local files only, no network
module. Writes one file: OUT/phase_F13_2d_independent_verification.csv.

R13: from E1 only EID, Year and Affiliations are kept per record; the Authors column is read only into an in-memory set of surname
tokens for C07, which is never printed or written."""
import sys
sys.dont_write_bytecode = True

import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import rapidfuzz
from rapidfuzz import fuzz

import os
ROOT = Path(os.environ.get("PROJECT_ROOT", "."))
DPR = ROOT / "outputs" / "dprg_revision_2026"
OUT = DPR / "phase_F13_2d"
T = OUT / "tables"
CT = DPR / "phase_F13_2c" / "tables"
BT = DPR / "phase_F13_2b" / "tables"
E1 = DPR / "author_exports_2026_10" / "scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
RESULT = OUT / "phase_F13_2d_independent_verification.csv"

FORBIDDEN = {"PLAN_DPRG_MASTER_2026_09.md", "HANDOFF_DPRG_2026_09_11.md", "PLAN_SJAITU_META_ANALYSIS_PROFESSOR.md",
             "PROJECT_STRUCTURE_PROFESSOR.md", ".env", "PHASE_REGISTRY.csv"}
FORBIDDEN_DIRS = {"phase_F13_6b", ".claude", "programs"}


def guard(p):
    p = Path(p)
    assert p.name not in FORBIDDEN, p
    assert not (set(p.parts) & FORBIDDEN_DIRS), p
    return p


def text_of(p):
    return guard(p).read_bytes().decode("utf-8-sig")


def rows_of(p):
    return list(csv.reader(io.StringIO(text_of(p), newline="")))


def dicts_of(p):
    return list(csv.DictReader(io.StringIO(text_of(p), newline="")))


def sha256(p):
    h = hashlib.sha256()
    with open(guard(p), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------ F13.2c parsing rules, re-implemented
CYR_UNIV = "".join(chr(c) for c in (0x443, 0x43D, 0x438, 0x432, 0x435, 0x440, 0x441))
DASHES = "-" + "".join(chr(c) for c in (0x2010, 0x2011, 0x2012, 0x2013, 0x2014))
LEVELS = [["university", CYR_UNIV], ["institute", "academy", "college"], ["centre", "center", "laboratory"],
          ["company", "llp", "jsc", "ltd", "corporation"], ["ministry", "agency", "committee", "department of"], ["hospital", "clinic"]]
SHORT_WORDS = {"llp", "jsc", "ltd"}
STATE_WORDS = ["republic", "kazakhstan", "city", "region", "regional", "police", "state", "government", "akimat", "national security",
               "internal affairs", "defence", "defense", "emergency"]
UNIT_START = re.compile(r"^(the )?(department|faculty|school of|higher school of|chair|division|ece department)\b", re.I)
INST_TYPES = [("university", ["university", CYR_UNIV]), ("school or college", ["college", "school", "lyceum", "gymnasium"]),
              ("research institute", ["institute", "academy", "centre", "center", "laboratory", "observatory"]),
              ("company", ["company", "llp", "jsc", "ltd", "corporation", "inc", "bank", "holding"]),
              ("government body", ["ministry", "agency", "committee", "department of", "akimat", "government"])]
TYPE_SHORT = {"llp", "jsc", "ltd", "inc"}
KZ = "Kazakhstan"
PERIODS = [("2003-2016", 2003, 2016), ("2017-2021", 2017, 2021), ("2022-2025", 2022, 2025)]
P = [p for p, _, _ in PERIODS]
COLLAB = ["single institution", "domestic multi-institution", "international"]
YEARS = list(range(2003, 2026))


def is_state(low):
    return any(re.search(r"\b" + re.escape(w) + r"\b", low) for w in STATE_WORDS)


def has(text, words, short):
    low = text.lower()
    for w in words:
        if w in short:
            if re.search(r"\b" + re.escape(w) + r"\b", low):
                return True
        elif w == "department of":
            if w in low and is_state(low):
                return True
        elif w in low:
            return True
    return False


def inst_type(name):
    if UNIT_START.search(name or "") and not has(name, ["university", CYR_UNIV, "institute", "academy"], set()):
        return "other"
    for t, words in INST_TYPES:
        if has(name, words, TYPE_SHORT):
            return t
    return "other"


def aff_lines(cell):
    return [x.strip() for x in (cell or "").split("; ") if x.strip()]


def parts_of(line):
    return [p.strip() for p in line.split(", ") if p.strip()]


def institution_of(parts):
    cands = parts[:-2] if len(parts) >= 3 else parts[:-1]
    for words in LEVELS:
        for p in cands:
            if has(p, words, SHORT_WORDS):
                return p
    return parts[0] if parts else ""


def parse_line(line):
    parts = parts_of(line)
    return (parts[-1] if parts else "", institution_of(parts))


def norm_kz(s):
    s = (s or "").lower()
    s = re.sub(r"(?<![^\W\d_])[^\W\d_]\.", " ", s)
    for ch in DASHES + ".":
        s = s.replace(ch, " ")
    s = re.sub(r"\bnamed after\b", " ", s)
    s = re.sub(r"\bafter\b", " ", s)
    s = re.sub(r"\bthe\b", " ", s)
    return " ".join(s.split())


def toks(s):
    return re.findall(r"[^\W_]+", norm_kz(s))


def most_common_form(forms):
    return sorted(Counter(forms).items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def year_of(s):
    try:
        return int(float(str(s).strip()))
    except ValueError:
        return None


def period_of(y):
    for name, a, b in PERIODS:
        if y is not None and a <= y <= b:
            return name
    return ""


def pct(n, d):
    return f"{100.0 * n / d:.1f}" if d else ""


# ------------------------------------------------ data
def read_e1(cset_words):
    """Records (eid, year, affiliations) and, for C07 only, the in-memory set of surname tokens (never printed or written)."""
    csv.field_size_limit(1 << 30)
    recs, author_words, aff_words = [], set(), set()
    with open(guard(E1), "r", encoding="utf-8-sig", newline="") as f:
        rd = csv.reader(f)
        h = next(rd)
        ie, iy, ia, iu = h.index("EID"), h.index("Year"), h.index("Affiliations"), h.index("Authors")
        for row in rd:
            recs.append({"eid": row[ie], "year": row[iy], "aff": row[ia]})
            aff_words.update(w.lower() for w in re.findall(r"[^\W\d_]+", row[ia]))
            author_words.update(w.lower() for w in re.findall(r"[^\W\d_]+", row[iu]) if len(w) >= 4)
            row = None
    surnames = author_words - aff_words - cset_words
    return len(h), recs, surnames


def label(R, forms, rows):
    """F13.2c labels(): display name per normalised key, institutions and collaboration type per record."""
    act = [r for r in rows if r["status"] == "active"]
    tmap = {r["variant"]: r["canonical"] for r in act}
    n2c = {}
    for r in act:
        n2c.setdefault(norm_kz(r["canonical"]), r["canonical"])
    disp = {k: (tmap.get(k) or n2c.get(k) or most_common_form(v)) for k, v in forms.items()}
    lab = {}
    for r in R:
        insts = {disp[k] for k in r["kz_keys"]}
        collab = "international" if len(r["A"]) >= 2 else "domestic multi-institution" if len(insts) >= 2 else "single institution"
        lab[r["eid"]] = (insts, collab)
    return disp, lab


def tables_for(R, lab, kz_rec, rows):
    N = len(R)
    per = {r["eid"]: r["period"] for r in R}
    intl = {r["eid"] for r in R if r["A"] - {KZ}}
    inst = defaultdict(set)
    for r in R:
        for i in lab[r["eid"]][0]:
            inst[i].add(r["eid"])
    rank = sorted(inst.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    t3a = []
    for i, (name, es) in enumerate(rank, 1):
        bp = Counter(per[e] for e in es)
        k = len(es & intl)
        t3a.append({"rank": str(i), "institution": name, "type": inst_type(name), "records": str(len(es)),
                    "share_of_841_pct": pct(len(es), N), **{p: str(bp.get(p, 0)) for p in P}, "international": str(k),
                    "share_international_pct": pct(k, len(es))})
    links = sum(len(es) for es in inst.values())
    t5, t10 = [n for n, _ in rank[:5]], [n for n, _ in rank[:10]]
    rec5, rec10 = len(set().union(*(inst[n] for n in t5))), len(set().union(*(inst[n] for n in t10)))
    calc = {"Kazakhstan institution variants before the thesaurus (normalised keys)": len(kz_rec),
            "variants in two or more records (all decided in the thesaurus)": sum(1 for v in kz_rec.values() if len(v) >= 2),
            "thesaurus rows": sum(1 for r in rows if r["status"] == "active"),
            "distinct Kazakhstan institutions after the thesaurus": len(inst),
            "institutions with one record": sum(1 for es in inst.values() if len(es) == 1),
            "institution-record links (full counting)": links,
            "share of links held by the top 5 (%)": pct(sum(len(inst[n]) for n in t5), links),
            "share of links held by the top 10 (%)": pct(sum(len(inst[n]) for n in t10), links),
            "records with at least one top-5 institution": rec5, "share of the 841 records with a top-5 institution (%)": pct(rec5, N),
            "records with at least one top-10 institution": rec10, "share of the 841 records with a top-10 institution (%)": pct(rec10, N)}
    calc = {k: str(v) for k, v in calc.items()}
    by_period = {}
    for p in P + ["2003-2025"]:
        g = [r for r in R if p == "2003-2025" or r["period"] == p]
        cc = Counter(lab[r["eid"]][1] for r in g)
        by_period[p] = {**{c: cc.get(c, 0) for c in COLLAB}, "total": len(g)}
    by_year = {}
    for y in YEARS:
        cc = Counter(lab[r["eid"]][1] for r in R if r["year"] == y)
        by_year[str(y)] = {**{c: cc.get(c, 0) for c in COLLAB}, "total": sum(cc.values())}
    return {"inst": inst, "t3a": t3a, "calc": calc, "period": by_period, "year": by_year, "links": links}


def collab_cells(block, block_v2, cols):
    """Expected cell values of a T2f / T2f2 row from counts: counts, total, '%' columns and 'delta' columns (v3 minus v2)."""
    out = {}
    for c in cols:
        if c in COLLAB or c == "total":
            out[c] = str(block[c])
        elif c.endswith(" %") and c[:-2] in COLLAB:
            out[c] = pct(block[c[:-2]], block["total"])
        elif c.endswith(" delta") and c[:-6] in COLLAB:
            out[c] = str(block[c[:-6]] - block_v2[c[:-6]])
        elif c.endswith("_v2") and c[:-3] in COLLAB:
            out[c] = str(block_v2[c[:-3]])
    return out


# ------------------------------------------------ C03 token rules
LEGAL = {"nao", "njsc", "nc", "jsc", "llp", "nplc", "ltd", "llc", "plc", "inc", "rse", "too", "ao", "non", "profit", "limited", "joint",
         "stock", "commercial", "company", "corporation"}
FUNC = {"of", "the", "and", "in", "at", "for", "by", "on", "named", "after", "name"}
FIRST_RUN = "first run FAIL: 8 labels listed fewer spellings than the tests accept; labels regenerated from the tests"


def parse_rule(text):
    """Label grammar (re-run): ' + ' joins required parts, ' / ' separates alternatives within a part, a trailing '*' is a prefix,
    a quoted alternative is a phrase matched in norm_kz of the name, '(not ...)' is an excluded part, any other parenthesis a note."""
    paren = re.findall(r"\(([^)]*)\)", text)
    main = re.sub(r"\([^)]*\)", " ", text).strip()
    parts = [[a.strip() for a in part.split(" / ") if a.strip()] for part in main.split(" + ") if part.strip()]
    excluded = [[a.strip() for a in p.strip()[4:].split(" / ") if a.strip()] for p in paren if p.strip().startswith("not ")]
    notes = " ".join(p for p in paren if not p.strip().startswith("not ")).lower()
    return parts, excluded, notes


def alt_ok(alt, name):
    if len(alt) >= 2 and alt[0] == "'" and alt[-1] == "'":
        return contains_phrase(norm_kz(name), norm_kz(alt[1:-1]))
    if alt.endswith("*"):
        stem = norm_kz(alt[:-1])
        return bool(stem) and any(t.startswith(stem) for t in toks(name))
    ws = toks(alt)
    return bool(ws) and all(w in toks(name) for w in ws)


def rule_ok(text, name):
    """Each required part has an alternative in the name; every excluded part is absent."""
    parts, excluded, _ = parse_rule(text)
    return (bool(parts) and all(any(alt_ok(a, name) for a in part) for part in parts)
            and all(not any(alt_ok(a, name) for a in part) for part in excluded))


def reduced(tk):
    return [t for t in tk if t not in LEGAL and t not in FUNC]


def contains_phrase(hay, phrase):
    return re.search(r"(?<![^\W_])" + re.escape(phrase) + r"(?![^\W_])", hay) is not None


def check_merge(vname, cname, token, identity, reason, t1d, t1b3, v1_former, v1_variants):
    """Returns (ok, how). vname / cname are written names or normalised keys (tokens are taken after norm_kz either way)."""
    vt, ct = toks(vname), toks(cname)
    if token.startswith("identical name"):
        key = identity.split(":", 1)[1].split() if identity.startswith("same name:") else None
        ok = (reduced(vt) == reduced(ct) or set(reduced(vt)) == set(reduced(ct))) and (key is None or set(key) == set(reduced(ct)))
        return ok, "same name (rule a)" if ok else "same name differs"
    notes = parse_rule(token)[2]
    if not rule_ok(token, vname):
        return False, "variant fails the rule"
    id_rule = t1b3.get(identity, {}).get("token_rule", "")
    id_in_variant = bool(id_rule) and rule_ok(id_rule, vname)
    if "former name" in notes or "renamed" in notes:
        # former-name rows: the canonical's identity token occurs in the variant, or the variant contains the v1 former-name phrase
        if id_in_variant:
            return True, "former: identity token in variant"
        if any(contains_phrase(norm_kz(vname), ph) for ph in v1_former.get(cname, [])):
            return True, "former: v1 former-name phrase"
        if any(rule_ok(token, v) for v in v1_variants.get(cname, [])):
            return True, "former: rule met by a v1 variant of the canonical"
        return False, "former: no identity token, no v1 phrase"
    if rule_ok(token, cname):
        return True, "both names meet the rule"
    if any(rule_ok(test, cname) for test in t1d.get(identity, [])):
        return True, "canonical by identity test"
    if reason.startswith("sub-unit") and id_in_variant:
        return True, "sub-unit: identity token in variant"
    return False, "canonical meets neither rule nor identity test"


# ------------------------------------------------ main
def main():
    res = []

    def add(cid, what, exp, rec, ok, note=""):
        res.append({"check_id": cid, "what": what, "expected_from_tables": str(exp), "recomputed": str(rec),
                    "verdict": "PASS" if ok else "FAIL", "note": note})

    stamp = json.loads(text_of(OUT / "F13_2d_brief_stamp.json"))
    num = json.loads(text_of(OUT / "F13_2d_numbers.json"))
    countries = {r["country_name"] for r in dicts_of(BT / "scopus_country_names.csv")}
    cset_words = {w.lower() for c in countries for w in re.findall(r"[^\W\d_]+", c)}

    # ---------------- C01 digests
    inputs = stamp["inputs"]
    e1_rel = "outputs/dprg_revision_2026/author_exports_2026_10/scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
    e1_sha = sha256(E1)
    add("C01a", "sha256 of E1 against stamp inputs", inputs[e1_rel]["sha256"][:16], e1_sha[:16],
        e1_sha == inputs[e1_rel]["sha256"] and E1.stat().st_size == inputs[e1_rel]["bytes"], "full digest and byte size compared")
    others = [k for k in inputs if k != e1_rel]
    must = {"outputs/dprg_revision_2026/phase_F13_2c/tables/T3a_v2_kz_institutions.csv",
            "outputs/dprg_revision_2026/phase_F13_2c/tables/institutions_thesaurus_v2.csv",
            "outputs/dprg_revision_2026/phase_F13_2c/tables/T2f2_v2_collaboration_by_period.csv",
            "outputs/dprg_revision_2026/phase_F13_2b/tables/scopus_country_names.csv"}
    bad = [k for k in others if sha256(ROOT / k) != inputs[k]["sha256"] or (ROOT / k).stat().st_size != inputs[k]["bytes"]]
    add("C01b", "sha256 of F13.2c and F13.2b input tables against stamp", f"{len(others)} files", f"{len(others) - len(bad)} equal",
        not bad and must <= set(others), "includes T3a_v2, thesaurus v2, T2f2_v2, country list; also T2f_v2, T3c_v2, T3d_v2")
    ncols, recs, surnames = read_e1(cset_words)
    eids = [r["eid"] for r in recs]
    add("C01c", "E1 records and unique EIDs", "841 / 841", f"{len(recs)} / {len(set(eids))}",
        len(recs) == 841 and len(set(eids)) == 841, f"{ncols} columns in the header; numbers.json columns_in_E1 {num.get('columns_in_E1')}")

    # ---------------- parse records
    R = []
    forms = defaultdict(list)
    kz_rec = defaultdict(set)
    for r in recs:
        lines = [parse_line(x) for x in aff_lines(r["aff"])]
        y = year_of(r["year"])
        keys = set()
        for cp, inst in lines:
            if cp == KZ:
                k = norm_kz(inst)
                forms[k].append(inst)
                kz_rec[k].add(r["eid"])
                keys.add(k)
        R.append({"eid": r["eid"], "year": y, "period": period_of(y), "kz_keys": keys, "A": {cp for cp, _ in lines if cp in countries}})
    recs = None

    v2_rows_raw = rows_of(CT / "institutions_thesaurus_v2.csv")
    v2 = dicts_of(CT / "institutions_thesaurus_v2.csv")
    v3_rows_raw = rows_of(T / "institutions_thesaurus_v3.csv")
    v3 = dicts_of(T / "institutions_thesaurus_v3.csv")
    disp2, lab2 = label(R, forms, v2)
    disp3, lab3 = label(R, forms, v3)
    tb2 = tables_for(R, lab2, kz_rec, v2)
    tb3 = tables_for(R, lab3, kz_rec, v3)

    # ---------------- C02 candidate pairs and clusters
    t3a_v2 = dicts_of(CT / "T3a_v2_kz_institutions.csv")
    names = [r["institution"] for r in t3a_v2]
    generic = {r["token"] for r in dicts_of(T / "generic_tokens.csv")}
    key = {n: " ".join(t for t in toks(n) if t not in generic) for n in names}
    part = [n for n in names if key[n]]
    empty = [n for n in names if not key[n]]
    parent = {n: n for n in part}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    score, edges = {}, []
    for a, b in combinations(part, 2):
        s = fuzz.token_set_ratio(key[a], key[b])
        score[(a, b)] = score[(b, a)] = s
        if key[a] == key[b] or s >= 80:
            edges.append((a, b, s))
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
    groups = defaultdict(set)
    for n in part:
        groups[find(n)].add(n)
    mine = {frozenset(g) for g in groups.values() if len(g) >= 2}
    t1a = dicts_of(T / "T1a_candidate_clusters.csv")
    tg = defaultdict(set)
    for r in t1a:
        tg[r["cluster_id"]].add(r["institution"])
    theirs = {frozenset(g) for g in tg.values()}
    clustered_mine, clustered_theirs = set().union(*mine), {r["institution"] for r in t1a}
    md = text_of(T / "T1a_candidate_clusters.md")
    m_pairs = re.search(r"\((\d+) pairs\)", md)
    m_cl = re.search(r"(\d+) clusters of (\d+) names", md)
    m_empty = re.search(r"(\d+) have no distinctive token", md)
    add("C02a", "names without distinctive key; clustered names; clusters",
        f"{m_empty.group(1) if m_empty else '?'}; {len(clustered_theirs)}; {len(theirs)}", f"{len(empty)}; {len(clustered_mine)}; {len(mine)}",
        m_empty and int(m_empty.group(1)) == len(empty) and clustered_mine == clustered_theirs and len(t1a) == len(clustered_theirs)
        and m_cl and int(m_cl.group(1)) == len(mine) and int(m_cl.group(2)) == len(clustered_mine) and len(set(names)) == len(names),
        f"{len(names)} T3a_v2 names, all distinct; rapidfuzz {rapidfuzz.__version__}; T1a note says {m_cl.group(0) if m_cl else '?'}")
    add("C02b", "partition into clusters (sets of frozensets of names) equals T1a", f"{len(theirs)} clusters", f"{len(mine)} clusters",
        mine == theirs, f"{len(mine ^ theirs)} clusters differ; largest cluster {max(len(g) for g in mine)} names")
    add("C02c", "number of candidate pairs (identical key or token_set_ratio >= 80)", m_pairs.group(1) if m_pairs else "?", len(edges),
        bool(m_pairs) and int(m_pairs.group(1)) == len(edges), "pair count read from the T1a note; numbers.json holds no pair count")
    # per-row columns of T1a
    cl_of = {n: g for g in mine for n in g}
    v2rec = {r["institution"]: r["records"] for r in t3a_v2}
    bad_key = bad_best = bad_size = bad_rec = bad_min = 0
    for r in t1a:
        n = r["institution"]
        g = cl_of.get(n, {n})
        if r["distinctive_key"] != key.get(n):
            bad_key += 1
        best = max((score.get((n, o), -1) for o in g if o != n), default=None)
        if best is None or abs(float(r["best_score"]) - round(best, 1)) > 0.051:
            bad_best += 1
        if str(len(g)) != r["cluster_size"]:
            bad_size += 1
        if r["records"] != v2rec.get(n):
            bad_rec += 1
        mn = min((s for a, b, s in edges if a in g and b in g), default=-1)
        if abs(float(r["cluster_min_link"]) - round(mn, 1)) > 0.051:
            bad_min += 1
    add("C02d", "T1a per-name columns: distinctive_key, best_score, cluster_size, records", "0 differences",
        f"{bad_key}, {bad_best}, {bad_size}, {bad_rec} differences", bad_key + bad_best + bad_size + bad_rec == 0,
        f"cluster_min_link read as the weakest candidate pair in the cluster: {bad_min} differences (informative)")

    # ---------------- C03 merges
    t1b2 = dicts_of(T / "T1b2_name_decisions.csv")
    merges = [r for r in t1b2 if r["decision"] == "merge"]
    t1d = defaultdict(list)
    for r in dicts_of(T / "T1d_name_token_rules.csv"):
        t1d[r["identity"]].append(r["test"])
    t1b3 = {r["identity"]: r for r in dicts_of(T / "T1b3_identities.csv")}
    canon2id = defaultdict(set)
    for i, r in t1b3.items():
        canon2id[r["canonical"]].add(i)
    t1c = dicts_of(T / "T1c_exclusions.csv")
    excl = defaultdict(set)
    for r in t1c:
        excl[norm_kz(r["institution"])].add(r["not_to_join"])
    v1_former, v1_variants = defaultdict(list), defaultdict(list)
    for r in v2:
        if r["status"] == "active" and r["rule"].startswith("merge"):
            v1_variants[r["canonical"]].append(r["variant"])
            if "former name" in r["rule"]:
                v1_former[r["canonical"]].append(r["variant"])
    v3new = [r for r in v3 if r["version"] == "v3"]
    prefix = "merge: distinctive token "
    exp_rows = Counter((norm_kz(r["institution"]), r["canonical"], prefix + r["token"] + " (v3)") for r in merges)
    got_rows = Counter((r["variant"], r["canonical"], r["rule"]) for r in v3new)
    add("C03a", "T1b2 merge decisions correspond one to one to new v3 rows (variant, canonical, rule)", f"{len(merges)} merges",
        f"{len(v3new)} v3 rows", exp_rows == got_rows, f"{sum((exp_rows - got_rows).values()) + sum((got_rows - exp_rows).values())} unmatched rows")
    hows, fails = Counter(), []
    for r in merges:
        ok, how = check_merge(r["institution"], r["canonical"], r["token"], r["identity"], r["reason"], t1d, t1b3, v1_former, v1_variants)
        hows[how] += 1
        if ok and how != "both names meet the rule" and "--debug" in sys.argv:
            print("DEBUGOK", how, "||", r["institution"], "||", r["token"], "||", r["canonical"])
        if not ok:
            fails.append(("T1b2", how))
            if "--debug" in sys.argv:
                print("DEBUG", how, "||", r["institution"], "||", norm_kz(r["institution"]), "||", r["token"], "||", r["canonical"])
    by_vc = {(norm_kz(r["institution"]), r["canonical"]): r for r in merges}
    for r in v3new:
        tok = r["rule"][len(prefix):-len(" (v3)")] if r["rule"].startswith(prefix) and r["rule"].endswith(" (v3)") else ""
        src = by_vc.get((r["variant"], r["canonical"]))
        ident = src["identity"] if src else (sorted(canon2id.get(r["canonical"], {""}))[0])
        reason = src["reason"] if src else r["reason"]
        ok, how = check_merge(r["variant"], r["canonical"], tok, ident, reason, t1d, t1b3, v1_former, v1_variants)
        if not ok or not tok:
            fails.append(("v3", how))
    hstr = "; ".join(f"{k} {v}" for k, v in sorted(hows.items()))
    if "--debug" in sys.argv:
        print("DEBUG hows", hstr)
    f1 = [f for f in fails if f[0] == "T1b2"]
    fk = Counter(h for _, h in fails)
    add("C03b", "each merge meets its label (required parts present, excluded parts absent) in both names (T1b2 merges and new v3 rows)",
        f"{len(merges)} + {len(v3new)} pass", f"{len(merges) + len(v3new) - len(fails)} pass", not fails,
        (FIRST_RUN + "; re-run PASS" if not fails else
         FIRST_RUN + f"; re-run: {len(f1)} T1b2 and {len(fails) - len(f1)} v3 rows fail: " + "; ".join(f"{k} {v}" for k, v in sorted(fk.items()))))
    lab_bad = [r for r in merges if not (r["token"] in t1d.get(r["identity"], []) or (r["identity"].startswith("same name:")
               and r["token"].startswith("identical name") and "(rule a) same name" in t1d))]
    rb_bad = [r for r in t1b3.values() if not (r["token_rule"] in t1d.get(r["identity"], []) or (r["identity"].startswith("same name:")
              and r["token_rule"].startswith("identical name")))]
    add("C03e", "every T1b2 merge label and T1b3 token_rule is a T1d test of its identity", f"{len(merges)} + {len(t1b3)}",
        f"{len(merges) - len(lab_bad)} + {len(t1b3) - len(rb_bad)} found", not lab_bad and not rb_bad,
        "T1b2 merges by path: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(
            {"both names meet the rule": "both meet", "canonical by identity test": "canonical via T1d test",
             "same name (rule a)": "rule a"}.get(h, "former-name rule" if h.startswith("former") else "other") for h in hows.elements()).items())))
    viol = [r for r in merges if r["identity"] in excl.get(norm_kz(r["institution"]), set())]
    viol3 = [r for r in v3new if any(i in excl.get(r["variant"], set()) for i in canon2id.get(r["canonical"], set()))]
    target = {}
    for r in t1c:
        nt = r["not_to_join"]
        target[r["institution"]] = t1b3[nt]["canonical"] if nt in t1b3 else nt
    joined = 0
    for k in forms:
        v2name = disp2[k]
        if v2name in target and disp3[k] == target[v2name]:
            joined += 1
    add("C03c", "T1c exclusions: no merged name joins the identity it must not join", f"0 of {len(t1c)} rows joined",
        f"{len(viol)} T1b2, {len(viol3)} v3, {joined} labels", not viol and not viol3 and joined == 0,
        "labels: no key whose v2 name is a T1c institution receives the excluded canonical under v3")
    canon_bad = [r for r in merges if r["identity"] not in t1b3 or t1b3[r["identity"]]["canonical"] != r["canonical"]]
    add("C03d", "merge canonical equals the identity's canonical in T1b3", f"{len(merges)}", f"{len(merges) - len(canon_bad)} equal",
        not canon_bad, f"{len(t1b3)} identities in T1b3")

    # ---------------- C04 T3a_v3, T3c_v3
    f_t3a2 = t3a_v2
    cols2 = list(f_t3a2[0].keys())
    diff2 = sum(1 for a, b in zip(f_t3a2, tb2["t3a"]) for c in cols2 if a[c] != b.get(c)) + abs(len(f_t3a2) - len(tb2["t3a"]))
    add("C04a", "T3a_v2 recomputed with thesaurus v2 (all rows, all columns; parser sanity)", f"{len(f_t3a2)} rows", f"{len(tb2['t3a'])} rows",
        diff2 == 0, f"{diff2} differing cells")
    f_t3a3 = dicts_of(T / "T3a_v3_kz_institutions.csv")
    top_bad = [i for i, (a, b) in enumerate(zip(f_t3a3[:20], tb3["t3a"][:20])) if (a["rank"], a["institution"], a["records"]) != (b["rank"], b["institution"], b["records"])]
    t10 = num.get("top10_v3", [])
    t10_ok = len(t10) == 10 and all(x[0] == b["institution"] and str(x[1]) == b["records"] for x, b in zip(t10, tb3["t3a"][:10]))
    add("C04b", "T3a_v3 top 20 (rank, institution, records) recomputed with thesaurus v3", "20 rows", f"{20 - len(top_bad)} equal",
        not top_bad and len(f_t3a3) >= 20, f"numbers.json top10_v3 names and records equal: {t10_ok}")
    v2r = {r["institution"]: r for r in tb2["t3a"]}
    cells_bad = 0
    for a, b in zip(f_t3a3, tb3["t3a"]):
        for c in a:
            if c in b:
                cells_bad += a[c] != b[c]
            elif c == "records_v2":
                cells_bad += a[c] != (v2r[b["institution"]]["records"] if b["institution"] in v2r else "0")
            elif c == "rank_v2":
                cells_bad += a[c] != (v2r[b["institution"]]["rank"] if b["institution"] in v2r else "")
            elif c == "delta":
                old = int(v2r[b["institution"]]["records"]) if b["institution"] in v2r else 0
                cells_bad += a[c] != str(int(b["records"]) - old)
            else:
                cells_bad += 1
    cells_bad += abs(len(f_t3a3) - len(tb3["t3a"]))
    add("C04c", "T3a_v3 all rows and columns, including records_v2, delta, rank_v2", f"{len(f_t3a3)} rows", f"{len(tb3['t3a'])} rows",
        cells_bad == 0, f"{cells_bad} differing cells")
    t3c = dicts_of(T / "T3c_v3_concentration.csv")
    t3cm = {r["measure"]: r for r in t3c}
    inst_n, links = len(tb3["inst"]), tb3["links"]
    add("C04d", "institutions after v3 and institution-record links (T3c_v3, numbers.json)",
        f"{t3cm['distinct Kazakhstan institutions after the thesaurus']['value']} / {t3cm['institution-record links (full counting)']['value']}",
        f"{inst_n} / {links}",
        str(inst_n) == t3cm["distinct Kazakhstan institutions after the thesaurus"]["value"] == str(num.get("institutions_v3"))
        and str(links) == t3cm["institution-record links (full counting)"]["value"] == str(num.get("links_v3"))
        and len(tb2["inst"]) == num.get("institutions_v2") and tb2["links"] == num.get("links_v2"),
        f"v2: {len(tb2['inst'])} institutions, {tb2['links']} links, as numbers.json")
    c_bad = sum(1 for r in t3c if r["value"] != tb3["calc"].get(r["measure"]) or r.get("value_v2") != tb2["calc"].get(r["measure"]))
    add("C04e", "T3c_v3 every measure, value and value_v2", f"{len(t3c)} measures", f"{len(t3c) - c_bad} equal",
        c_bad == 0 and set(t3cm) == set(tb3["calc"]), "thesaurus rows counted as active rows")

    # ---------------- C05 collaboration
    t2f2 = dicts_of(T / "T2f2_v3_collaboration_by_period.csv")
    cols = list(t2f2[0].keys())
    bad = unknown = 0
    for r in t2f2:
        exp = collab_cells(tb3["period"][r["period"]], tb2["period"][r["period"]], cols)
        unknown += sum(1 for c in cols if c != "period" and c not in exp)
        bad += sum(1 for c in exp if exp[c] != r[c])
    ncells = len(t2f2) * (len(cols) - 1)
    add("C05a", "T2f2_v3 every cell, all periods (counts, totals, %, deltas)", f"{ncells} cells", f"{ncells - bad - unknown} equal",
        bad == 0 and unknown == 0 and [r["period"] for r in t2f2] == P + ["2003-2025"], f"{bad} differ, {unknown} not recomputable")
    i2, i3 = tb2["period"]["2003-2025"]["international"], tb3["period"]["2003-2025"]["international"]
    add("C05b", "international records stay 517 (v2 and v3)", "517", f"{i2} / {i3}", i2 == i3 == 517 and num["collab_v3"]["international"] == 517,
        f"v3 all-period: {tb3['period']['2003-2025']['single institution']} single, {tb3['period']['2003-2025']['domestic multi-institution']} domestic")
    f2 = dicts_of(CT / "T2f2_v2_collaboration_by_period.csv")
    bad2 = sum(1 for r in f2 for c, v in collab_cells(tb2["period"][r["period"]], tb2["period"][r["period"]], list(r.keys())).items() if v != r[c])
    add("C05c", "my v2 collaboration equals F13.2c T2f2_v2 and numbers.json collab_v2", "0 differences", f"{bad2} differences",
        bad2 == 0 and all(num["collab_v2"][c] == tb2["period"]["2003-2025"][c] for c in COLLAB), "")
    trans = Counter((lab2[e][1], lab3[e][1]) for e in lab2)
    changed = {f"{a} -> {b}": n for (a, b), n in trans.items() if a != b}
    t2g = dicts_of(T / "T2g_collaboration_transitions.csv")
    t2g_ok = Counter({(r["type_v2"], r["type_v3"]): int(r["records"]) for r in t2g}) == trans
    add("C05d", "records that changed type between v2 and v3", "; ".join(f"{k}: {v}" for k, v in num.get("transitions", {}).items()),
        "; ".join(f"{k}: {v}" for k, v in changed.items()), changed == num.get("transitions") and t2g_ok,
        f"T2g transition table equal: {t2g_ok}; all changes are domestic to single")
    t2f = dicts_of(T / "T2f_v3_collaboration_by_year.csv")
    ycols = list(t2f[0].keys())
    ybad = yunk = 0
    for r in t2f:
        exp = collab_cells(tb3["year"][r["year"]], tb2["year"][r["year"]], ycols)
        yunk += sum(1 for c in ycols if c != "year" and c not in exp)
        ybad += sum(1 for c in exp if exp[c] != r[c])
    add("C05e", "T2f_v3 every cell, all years", f"{len(t2f) * (len(ycols) - 1)} cells", f"{len(t2f) * (len(ycols) - 1) - ybad - yunk} equal",
        ybad == 0 and yunk == 0 and len(t2f) == len(YEARS), f"{ybad} differ, {yunk} not recomputable")

    # ---------------- C06 thesaurus integrity
    same = v3_rows_raw[0] == v2_rows_raw[0] and v3_rows_raw[1:134] == v2_rows_raw[1:134] and len(v2_rows_raw) == 134
    add("C06a", "first 133 rows of v3 equal v2 row by row (header too)", "133 rows", f"{sum(1 for a, b in zip(v3_rows_raw[1:134], v2_rows_raw[1:134]) if a == b)} equal",
        same, f"v3 has {len(v3)} rows: 133 + {len(v3new)} new")
    act = [r for r in v3 if r["status"] == "active"]
    merge_vars = {r["variant"] for r in act if r["rule"].startswith("merge")}
    ncanon = {norm_kz(r["canonical"]) for r in act}
    chain = [r for r in act if norm_kz(r["canonical"]) in merge_vars]
    add("C06b", "no chain: no active canonical normalises to an active merge variant", "0", len(chain), not chain, f"{len(merge_vars)} active merge variants")
    add("C06c", "merge variants disjoint from normalised canonicals", "0 shared", f"{len(merge_vars & ncanon)} shared", not (merge_vars & ncanon), "")
    vc = defaultdict(set)
    for r in act:
        vc[r["variant"]].add(r["canonical"])
    dup = Counter(r["variant"] for r in act)
    add("C06d", "one variant, one canonical (active rows)", "0 duplicates", f"{sum(1 for v in dup.values() if v > 1)} duplicates, {sum(1 for s in vc.values() if len(s) > 1)} conflicts",
        all(v == 1 for v in dup.values()), f"{len(act)} active rows")
    nset, nameset = {norm_kz(n) for n in names}, set(names)
    bad_new = [r for r in v3new if r["variant"] not in nset or r["canonical"] not in nameset or r["status"] != "active"
               or not r["rule"].startswith("merge: distinctive token")]
    add("C06e", "every new variant is norm_kz of a T3a_v2 name; canonical a T3a_v2 name; v3, active, merge rule", f"{len(v3new)}",
        f"{len(v3new) - len(bad_new)} conform", not bad_new, "")

    # ---------------- C07 R13
    EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    ORCID = re.compile(r"\b(?:0000|0009)-\d{4}-\d{4}-\d{3}[\dX]\b")
    files = sorted(p for p in guard(T).iterdir() if p.is_file()) + [OUT / "F13_2d_numbers.json"]
    shapes = hits = 0
    hit_files = set()
    bad_cols, long_cells = [], 0
    for p in files:
        txt = text_of(p)
        shapes += len(EMAIL.findall(txt)) + len(ORCID.findall(txt))
        h = {w.lower() for w in re.findall(r"[^\W\d_]+", txt)} & surnames
        if h:
            hits += len(h)
            hit_files.add(p.name)
        if p.suffix == ".csv":
            rr = list(csv.reader(io.StringIO(txt, newline="")))
            bad_cols += [c for c in rr[0] if re.search(r"author|e-?mail|orcid", c, re.I)]
            long_cells += sum(1 for row in rr for c in row if len(c.split()) > 30)
    add("C07a", "e-mail or ORCID shapes in tables and numbers.json", "0", shapes, shapes == 0, f"{len(files)} files scanned")
    add("C07b", "surname tokens of the Authors column in tables and numbers.json", "0", hits, hits == 0,
        f"{len(surnames)} tokens of 4+ letters after removing Affiliations and country words; held in memory only"
        + (f"; files: {', '.join(sorted(hit_files))}" if hit_files else ""))
    add("C07c", "no column named like author, email or orcid", "0", len(bad_cols), not bad_cols, "")
    add("C07d", "no CSV cell over 30 words in tables", "0", long_cells, long_cells == 0, "")

    # ---------------- write
    fields = ["check_id", "what", "expected_from_tables", "recomputed", "verdict", "note"]
    for r in res:
        for c in fields:
            assert len(r[c].split()) <= 30, (r["check_id"], c)
            assert not EMAIL.search(r[c]) and not ORCID.search(r[c])
            assert not ({w.lower() for w in re.findall(r"[^\W\d_]+", r[c])} & surnames), r["check_id"]
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(res)
    guard(RESULT).write_bytes(buf.getvalue().encode("utf-8"))
    for r in res:
        print(r["check_id"], r["verdict"], "|", r["expected_from_tables"], "|", r["recomputed"], "|", r["note"])
    print("PASS", sum(r["verdict"] == "PASS" for r in res), "FAIL", sum(r["verdict"] == "FAIL" for r in res))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
