"""Phase F13.2e - independent verification (checks C01-C05). Written from the verifier's brief; the parsing rules of F13.2c
(aff_lines, parts_of, institution_of, parse_line, norm_kz, most_common_form, inst_type, labels) are re-implemented from
phase_F13_2c/programs/f132c_lib.py and f132c_build.py, n_authors / mean / median from phase_F13_2b/programs/f132b_lib.py.
Nothing is imported from phase_F13_2e/programs (no file there is read). Local files only, no network module. Writes one file:
OUT/phase_F13_2e_independent_verification.csv.

R13: from E1 only EID, Year and Affiliations are kept per record, Authors becomes a count at once; the Authors column also feeds an
in-memory set of surname tokens for C05, which is never printed or written."""
import sys
sys.dont_write_bytecode = True

import csv
import hashlib
import io
import json
import re
import statistics
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import os
ROOT = Path(os.environ.get("PROJECT_ROOT", "."))
DPR = ROOT / "outputs" / "dprg_revision_2026"
OUT = DPR / "phase_F13_2e"
T = OUT / "tables"
D = DPR / "phase_F13_2d"
DT = D / "tables"
BT = DPR / "phase_F13_2b" / "tables"
E1 = DPR / "author_exports_2026_10" / "scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
RESULT = OUT / "phase_F13_2e_independent_verification.csv"

FORBIDDEN = {"PLAN_DPRG_MASTER_2026_09.md", "HANDOFF_DPRG_2026_09_11.md", "PLAN_SJAITU_META_ANALYSIS_PROFESSOR.md",
             "PROJECT_STRUCTURE_PROFESSOR.md", ".env", "PHASE_REGISTRY.csv"}
FORBIDDEN_DIRS = {"phase_F13_3b", ".claude", "programs"}


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


# ------------------------------------------------ F13.2b rules for T2g, re-implemented
def n_authors(cell):
    a = (cell or "").strip()
    if not a or a.startswith("[No author"):
        return 0
    return len([x for x in a.split(";") if x.strip()])


def mean_b(xs):
    return f"{sum(xs) / len(xs):.2f}" if xs else ""


def median_b(xs):
    xs = sorted(xs)
    if not xs:
        return ""
    m = len(xs) // 2
    v = xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2
    return int(v) if float(v).is_integer() else v


# ------------------------------------------------ data
def read_e1(cset_words):
    """Records (eid, year, affiliations, number of authors) and, for C05 only, the in-memory set of surname tokens."""
    csv.field_size_limit(1 << 30)
    recs, author_words, aff_words = [], set(), set()
    with open(guard(E1), "r", encoding="utf-8-sig", newline="") as f:
        rd = csv.reader(f)
        h = next(rd)
        ie, iy, ia, iu = h.index("EID"), h.index("Year"), h.index("Affiliations"), h.index("Authors")
        for row in rd:
            recs.append({"eid": row[ie], "year": row[iy], "aff": row[ia], "n_auth": n_authors(row[iu])})
            aff_words.update(w.lower() for w in re.findall(r"[^\W\d_]+", row[ia]))
            author_words.update(w.lower() for w in re.findall(r"[^\W\d_]+", row[iu]) if len(w) >= 4)
            row = None
    surnames = author_words - aff_words - cset_words
    return len(h), recs, surnames


def label(R, forms, rows):
    """F13.2c labels(): display name per normalised key from the ACTIVE rows; institutions and collaboration type per record."""
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
    ip = Counter(pr for r in R for pr in combinations(sorted(lab[r["eid"]][0]), 2))
    t3d = [(a, b, str(n)) for (a, b), n in sorted(ip.items(), key=lambda kv: (-kv[1], kv[0]))]
    t2g, stats_ok = {}, True
    for c in COLLAB + ["all"]:
        xs = [r["n_auth"] for r in R if c == "all" or lab[r["eid"]][1] == c]
        t2g[c] = {"records": str(len(xs)), "authors_mean": mean_b(xs), "authors_median": str(median_b(xs)),
                  "authors_max": str(max(xs)) if xs else ""}
        stats_ok &= (not xs) or (float(statistics.median(xs)) == float(median_b(xs))
                                 and f"{statistics.mean(xs):.2f}" == mean_b(xs))
    return {"inst": inst, "t3a": t3a, "calc": calc, "period": by_period, "year": by_year, "links": links, "t3d": t3d, "t2g": t2g,
            "stats_ok": stats_ok}


def collab_cells(block, block_old, cols):
    """Expected cell values of a T2f / T2f2 row from counts: counts, total, '%' columns and 'delta' columns (v3.1 minus v3)."""
    out = {}
    for c in cols:
        if c in COLLAB or c == "total":
            out[c] = str(block[c])
        elif c.endswith(" %") and c[:-2] in COLLAB:
            out[c] = pct(block[c[:-2]], block["total"])
        elif c.endswith(" delta") and c[:-6] in COLLAB:
            out[c] = str(block[c[:-6]] - block_old[c[:-6]])
    return out


# ------------------------------------------------ the author's list (decision 48), as written in the brief
RULE31 = "merge: professor's list (v3.1), author's decision 48"
IICT = "Institute of Information and Computational Technologies"
OLD_IICT = "Institute of Informatics and Control Problems"
LIST = [("NC JSC 'S.Seifullin KATU'", "S. Seifullin Kazakh Agrotechnical Research University"),
        ("KazNMU named after S.D. Asfendiyarov", "Asfendiyarov Kazakh National Medical University"),
        ("G. Daukeev University of Power Engineering",
         "Almaty University of Power Engineering and Telecommunications named after Gumarbek Daukeyev"),
        ("Baytursynov Kostanay State University", "Akhmet Baitursynuly Kostanay Regional University"),
        ("Non-Profit Limited Company A. Baitursynov KRU", "Akhmet Baitursynuly Kostanay Regional University"),
        ("Kazakh-Turkish University named after H. A. Yesevi B.", "Khoja Akhmet Yassawi International Kazakh-Turkish University"),
        ("Institute of Informatics and Control Problems", IICT),
        ("Karagandy State Technical University", "Abylkas Saginov Karaganda Technical University"),
        ("Kokshetau State University", "Sh. Ualikhanov Kokshetau University")]
# brief's expectations (v3 -> v3.1 records) per distinct canonical of the list, in list order
EXPECT = {LIST[0][1]: (21, 22), LIST[1][1]: (2, 3), LIST[2][1]: (69, 70), LIST[3][1]: (5, 7), LIST[5][1]: (3, 4), IICT: (63, 66),
          LIST[7][1]: (6, 7), LIST[8][1]: (5, 6)}
YESSENOV = "Yessenov University"
CASPIAN_SUFFIX = "; author's confirmation, decision 48"


# ------------------------------------------------ main
def main():
    res = []

    def add(cid, what, exp, rec, ok, note=""):
        res.append({"check_id": cid, "what": what, "expected_from_tables": str(exp), "recomputed": str(rec),
                    "verdict": "PASS" if ok else "FAIL", "note": note})

    stamp = json.loads(text_of(OUT / "F13_2e_brief_stamp.json"))
    num = json.loads(text_of(OUT / "F13_2e_numbers.json"))
    countries = {r["country_name"] for r in dicts_of(BT / "scopus_country_names.csv")}
    cset_words = {w.lower() for c in countries for w in re.findall(r"[^\W\d_]+", c)}

    # ---------------- C01 digests
    inputs = stamp["inputs"]
    e1_rel = "outputs/dprg_revision_2026/author_exports_2026_10/scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
    e1_sha = sha256(E1)
    add("C01a", "sha256 and bytes of E1 against stamp inputs", inputs[e1_rel]["sha256"][:16], e1_sha[:16],
        e1_sha == inputs[e1_rel]["sha256"] and E1.stat().st_size == inputs[e1_rel]["bytes"]
        and e1_sha == "fe01023d23afe95df83d594fdfea2c3b488e52ffb8778def4067a2d795a991f3",
        "full digest and byte size compared; equals the digest accepted in F13.1")
    others = [k for k in inputs if k != e1_rel]
    must = {"outputs/dprg_revision_2026/phase_F13_2d/tables/institutions_thesaurus_v3.csv",
            "outputs/dprg_revision_2026/phase_F13_2d/tables/T3a_v3_kz_institutions.csv",
            "outputs/dprg_revision_2026/phase_F13_2b/tables/T2g_authors_by_collaboration.csv",
            "outputs/dprg_revision_2026/phase_F13_2b/tables/scopus_country_names.csv"}
    bad = [k for k in others if sha256(ROOT / k) != inputs[k]["sha256"] or (ROOT / k).stat().st_size != inputs[k]["bytes"]]
    add("C01b", "sha256 and bytes of the other input tables against stamp", f"{len(others)} files", f"{len(others) - len(bad)} equal",
        not bad and must <= set(others), "thesaurus v3, T3a/T3c/T3d/T2f/T2f2 v3, T4 residual (F13.2d); T2g and country list (F13.2b)")
    ncols, recs, surnames = read_e1(cset_words)
    eids = [r["eid"] for r in recs]
    add("C01c", "E1 records and unique EIDs", "841 / 841", f"{len(recs)} / {len(set(eids))}",
        len(recs) == 841 and len(set(eids)) == 841 and num.get("records") == 841,
        f"{ncols} header columns, numbers.json columns_in_E1 {num.get('columns_in_E1')}; only EID, Year, Affiliations, Authors read")

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
        R.append({"eid": r["eid"], "year": y, "period": period_of(y), "kz_keys": keys, "n_auth": r["n_auth"],
                  "A": {cp for cp, _ in lines if cp in countries}})
    recs = None

    v3_raw = rows_of(DT / "institutions_thesaurus_v3.csv")
    v3 = dicts_of(DT / "institutions_thesaurus_v3.csv")
    v31_raw = rows_of(T / "institutions_thesaurus_v31.csv")
    v31 = dicts_of(T / "institutions_thesaurus_v31.csv")
    disp3, lab3 = label(R, forms, v3)
    disp31, lab31 = label(R, forms, v31)
    tb3 = tables_for(R, lab3, kz_rec, v3)
    tb31 = tables_for(R, lab31, kz_rec, v31)
    t3a_v3 = dicts_of(DT / "T3a_v3_kz_institutions.csv")
    v3names = [r["institution"] for r in t3a_v3]
    v3norm = {norm_kz(n): n for n in v3names}

    # ---------------- C02 thesaurus v3.1
    new = v31[len(v3):]
    sup_v3 = [r for r in v3 if r["canonical"] == OLD_IICT and r["status"] == "active"]
    sup_vars = {r["variant"] for r in sup_v3}
    listrows = [r for r in new if r["variant"] not in sup_vars]
    follow = [r for r in new if r["variant"] in sup_vars]
    probs = []
    if len(listrows) != 9:
        probs.append(f"{len(listrows)} list rows")
    for (wname, canon), r in zip(LIST, listrows):
        if toks(wname) != toks(r["variant"]):
            probs.append("variant differs from the list")
        if r["canonical"] != canon:
            probs.append("canonical differs from the list")
        if r["variant"] not in v3norm:
            probs.append("variant not a normalised T3a_v3 name")
        if r["canonical"] not in v3names:
            probs.append("canonical not a T3a_v3 name")
        if (r["rule"], r["version"], r["status"], r["confidence"]) != (RULE31, "v3.1", "active", "high"):
            probs.append("rule/version/status/confidence")
        if r["records"] != str(len(kz_rec.get(r["variant"], ()))):
            probs.append("records column")
    add("C02a", "nine list rows: variant = norm_kz of a T3a_v3 name matching the list; canonical a T3a_v3 name; rule, v3.1, active",
        "9 rows conform", f"{9 - len(set(probs))} problems absent" if not probs else "; ".join(sorted(set(probs))), not probs and len(listrows) == 9,
        "order follows the list; list names compared by norm_kz tokens; records column equals records of the variant key")
    v31_by_var = defaultdict(list)
    for i, r in enumerate(v31):
        v31_by_var[r["variant"]].append((i, r))
    fprobs = []
    for r in sup_v3:
        old = [x for i, x in v31_by_var[r["variant"]] if i < len(v3)]
        nw = [x for i, x in v31_by_var[r["variant"]] if i >= len(v3)]
        if len(old) != 1 or not old[0]["status"].startswith("superseded (decision 48"):
            fprobs.append("v3 row not superseded")
        if len(nw) != 1 or (nw[0]["canonical"], nw[0]["rule"], nw[0]["version"], nw[0]["status"]) != (IICT, RULE31, "v3.1", "active"):
            fprobs.append("no new IICT row")
    still = [r for r in v31 if r["status"] == "active" and r["canonical"] == OLD_IICT]
    add("C02b", "two follow-on rows: v3 rows with the old IICT name as canonical superseded and re-mapped to IICT",
        f"{len(follow)} new rows", f"{len(sup_v3)} v3 rows; {len(fprobs)} problems", len(sup_v3) == 2 == len(follow) and not fprobs and not still,
        f"active rows still pointing to the old name: {len(still)}; 11 new rows = 9 list + 2 follow-on: {len(new) == 11}")
    diffs = Counter()
    other = 0
    hdr_ok = v31_raw[0] == v3_raw[0]
    for a, b in zip(v3, v31[:len(v3)]):
        for c in a:
            if a[c] == b[c]:
                continue
            if (c == "reason" and a["variant"].startswith("caspian") and a["canonical"] == YESSENOV and a["version"] == "v3"
                    and b[c] == a[c] + CASPIAN_SUFFIX):
                diffs["caspian reason"] += 1
            elif c == "status" and a["canonical"] == OLD_IICT and a[c] == "active" and b[c].startswith("superseded (decision 48"):
                diffs["superseded status"] += 1
            else:
                other += 1
    n_casp = sum(1 for r in v3 if r["variant"].startswith("caspian") and r["canonical"] == YESSENOV and r["version"] == "v3")
    add("C02c", "the 274 v3 rows equal in v3.1 except reason of the six caspian rows and status of the two superseded rows",
        "274 rows; 6 reason, 2 status", f"{len(v3)} rows; {diffs['caspian reason']} reason, {diffs['superseded status']} status, {other} other",
        len(v3) == 274 and len(v31) == 285 and hdr_ok and other == 0 and diffs["caspian reason"] == 6 == n_casp and diffs["superseded status"] == 2,
        f"header equal: {hdr_ok}; {len(v31)} rows; first run FAIL was mine: counted 4 v1 caspian rows too; six = version v3 rows; re-run")
    act = [r for r in v31 if r["status"] == "active"]
    merge_vars = {r["variant"] for r in act if r["rule"].startswith("merge")}
    ncanon = {norm_kz(r["canonical"]) for r in act}
    chain = [r for r in act if norm_kz(r["canonical"]) in merge_vars]
    add("C02d", "no chain: no active canonical normalises to an active merge variant", "0", len(chain), not chain,
        f"{len(merge_vars)} active merge variants")
    add("C02e", "active merge variants disjoint from normalised active canonicals", "0 shared", f"{len(merge_vars & ncanon)} shared",
        not (merge_vars & ncanon), "")
    dup = Counter(r["variant"] for r in act)
    add("C02f", "active variants unique (one variant, one canonical)", "0 duplicates", f"{sum(1 for v in dup.values() if v > 1)} duplicates",
        all(v == 1 for v in dup.values()), f"{len(act)} active rows (v3: {sum(1 for r in v3 if r['status'] == 'active')})")

    # ---------------- C03 institutions
    cols_shared = list(tb3["t3a"][0].keys())
    diff3 = sum(1 for a, b in zip(t3a_v3, tb3["t3a"]) for c in cols_shared if a[c] != b[c]) + abs(len(t3a_v3) - len(tb3["t3a"]))
    add("C03a", "parser sanity: T3a_v3 of F13.2d recomputed with thesaurus v3 (all rows, all non-v2 columns)", f"{len(t3a_v3)} rows",
        f"{len(tb3['t3a'])} rows", diff3 == 0, f"{diff3} differing cells")
    f31 = dicts_of(T / "T3a_v31_kz_institutions.csv")
    top_bad = [i for i, (a, b) in enumerate(zip(f31[:20], tb31["t3a"][:20]))
               if (a["rank"], a["institution"], a["records"]) != (b["rank"], b["institution"], b["records"])]
    v3r = {r["institution"]: r for r in tb3["t3a"]}
    t10 = num.get("top10_v31", [])
    t10_ok = len(t10) == 10 and all(
        x[0] == b["institution"] and str(x[1]) == b["records"] and str(x[2]) == v3r.get(b["institution"], {}).get("records")
        and str(x[3]) == v3r.get(b["institution"], {}).get("rank") for x, b in zip(t10, tb31["t3a"][:10]))
    moves = [b["institution"] for b in tb31["t3a"][:10] if v3r.get(b["institution"], {}).get("rank") != b["rank"]]
    add("C03b", "T3a_v31 top 20 (rank, institution, records) recomputed with active v3.1 rows", "20 rows", f"{20 - len(top_bad)} equal",
        not top_bad and len(f31) >= 20 and t10_ok and not moves and num.get("top10_rank_moves") == [],
        f"numbers.json top10_v31 equal: {t10_ok}; top-10 rank moves against v3: {len(moves)}")
    f31m = {r["institution"]: r for r in f31}
    m31 = {r["institution"]: r for r in tb31["t3a"]}
    affected = list(dict.fromkeys(c for _, c in LIST)) + [YESSENOV]
    a_bad, exp_s, rec_s = [], [], []
    for c in affected:
        f, m, o = f31m.get(c, {}), m31.get(c, {}), v3r.get(c, {})
        exp_s.append(f"{f.get('records', '?')}/{f.get('rank', '?')}")
        rec_s.append(f"{m.get('records', '?')}/{m.get('rank', '?')}")
        if (f.get("records"), f.get("rank"), f.get("records_v3"), f.get("rank_v3")) != (m.get("records"), m.get("rank"), o.get("records"), o.get("rank")):
            a_bad.append(c)
        if c in EXPECT:
            e3, e31 = EXPECT[c]
            if not (o.get("records") == str(e3) and (int(m.get("records", -1)) == e31 if c != IICT else 63 < int(m.get("records", -1)) <= 66)):
                a_bad.append(c)
            if num.get("touched", {}).get(c) != [int(o.get("records", -1)), int(m.get("records", -1))]:
                a_bad.append(c)
    gone = [v3norm[r["variant"]] for r in listrows if r["variant"] in v3norm]
    still_listed = [n for n in gone if n in f31m or n in m31]
    add("C03c", "nine affected canonicals (8 of the list, then the caspian rows' canonical): records/rank in T3a_v31, records_v3/rank_v3",
        "; ".join(exp_s), "; ".join(rec_s), not a_bad and len(gone) == 9 and not still_listed,
        f"brief expectations, numbers.json touched met: {not a_bad}; {len(gone)} absorbed T3a_v3 names, {len(still_listed)} still listed")
    t3c = dicts_of(T / "T3c_v31_concentration.csv")
    t3cm = {r["measure"]: r for r in t3c}
    inst_n, links = len(tb31["inst"]), tb31["links"]
    k_i, k_l = "distinct Kazakhstan institutions after the thesaurus", "institution-record links (full counting)"
    add("C03d", "institutions and institution-record links after v3.1 (T3c_v31, numbers.json); expected 198",
        f"{t3cm[k_i]['value']} / {t3cm[k_l]['value']}", f"{inst_n} / {links}",
        inst_n == 198 and str(inst_n) == t3cm[k_i]["value"] == str(num.get("institutions_v31")) and str(links) == t3cm[k_l]["value"]
        == str(num.get("links_v31")) and len(tb3["inst"]) == num.get("institutions_v3") == 207 and tb3["links"] == num.get("links_v3"),
        f"v3: {len(tb3['inst'])} institutions, {tb3['links']} links, as numbers.json")
    cells_bad = 0
    for a, b in zip(f31, tb31["t3a"]):
        o = v3r.get(b["institution"])
        for c in a:
            if c in b:
                cells_bad += a[c] != b[c]
            elif c == "records_v3":
                cells_bad += a[c] != (o["records"] if o else "0")
            elif c == "rank_v3":
                cells_bad += a[c] != (o["rank"] if o else "")
            elif c == "delta":
                cells_bad += a[c] != str(int(b["records"]) - (int(o["records"]) if o else 0))
            else:
                cells_bad += 1
    cells_bad += abs(len(f31) - len(tb31["t3a"]))
    add("C03e", "T3a_v31 all rows and columns, including records_v3, delta, rank_v3", f"{len(f31)} rows", f"{len(tb31['t3a'])} rows",
        cells_bad == 0, f"{cells_bad} differing cells")
    c_bad = sum(1 for r in t3c if r["value"] != tb31["calc"].get(r["measure"]) or r.get("value_v3") != tb3["calc"].get(r["measure"]))
    add("C03f", "T3c_v31 every measure, value and value_v3", f"{len(t3c)} measures", f"{len(t3c) - c_bad} equal",
        c_bad == 0 and set(t3cm) == set(tb31["calc"]), "thesaurus rows counted as active rows (282 v3.1, 273 v3)")
    t3d = [(r["institution_a"], r["institution_b"], r["records"]) for r in dicts_of(T / "T3d_v31_kz_institution_pairs.csv")]
    add("C03g", "T3d_v31 all institution pairs (sorted names, records, order)", f"{len(t3d)} pairs", f"{len(tb31['t3d'])} pairs",
        t3d == tb31["t3d"], f"{sum(1 for a, b in zip(t3d, tb31['t3d']) if a != b)} rows differ in order or value (extra check)")

    # ---------------- C04 collaboration and authors
    t2f2 = dicts_of(T / "T2f2_v31_collaboration_by_period.csv")
    cols = list(t2f2[0].keys())
    bad = unknown = 0
    for r in t2f2:
        exp = collab_cells(tb31["period"][r["period"]], tb3["period"][r["period"]], cols)
        unknown += sum(1 for c in cols if c != "period" and c not in exp)
        bad += sum(1 for c in exp if exp[c] != r[c])
    ncells = len(t2f2) * (len(cols) - 1)
    add("C04a", "T2f2_v31 every cell, all periods (counts, totals, %, deltas against v3)", f"{ncells} cells", f"{ncells - bad - unknown} equal",
        bad == 0 and unknown == 0 and [r["period"] for r in t2f2] == P + ["2003-2025"], f"{bad} differ, {unknown} not recomputable")
    i3, i31 = tb3["period"]["2003-2025"]["international"], tb31["period"]["2003-2025"]["international"]
    add("C04b", "international records stay 517 (v3 and v3.1)", "517", f"{i3} / {i31}",
        i3 == i31 == 517 and num["collab_v31"]["international"] == 517 and num["collab_v3"]["international"] == 517
        and all(num["collab_v31"][c] == tb31["period"]["2003-2025"][c] and num["collab_v3"][c] == tb3["period"]["2003-2025"][c] for c in COLLAB),
        f"v3.1 all-period: {tb31['period']['2003-2025']['single institution']} single, {tb31['period']['2003-2025']['domestic multi-institution']} domestic")
    t2g = dicts_of(T / "T2g_v31_authors_by_collaboration.csv")
    order_ok = [r["collaboration"] for r in t2g] == COLLAB + ["all"]
    g_bad = [r["collaboration"] for r in t2g for c in ("records", "authors_mean", "authors_median", "authors_max")
             if r[c] != tb31["t2g"].get(r["collaboration"], {}).get(c)]
    add("C04c", "T2g_v31 records, mean, median, max of authors per collaboration type and all",
        "; ".join(f"{r['records']}/{r['authors_mean']}/{r['authors_median']}/{r['authors_max']}" for r in t2g),
        "; ".join(f"{v['records']}/{v['authors_mean']}/{v['authors_median']}/{v['authors_max']}" for v in tb31["t2g"].values()),
        not g_bad and order_ok and tb31["stats_ok"], "rows: single, domestic, international, all; mean and median also cross-checked with statistics")
    g3_bad = [r["collaboration"] for r in t2g for c in ("records", "authors_mean", "authors_median")
              if r[c + "_v3"] != tb3["t2g"].get(r["collaboration"], {}).get(c)]
    add("C04d", "T2g_v31 v3 columns recounted with thesaurus v3", "; ".join(f"{r['records_v3']}/{r['authors_mean_v3']}/{r['authors_median_v3']}" for r in t2g),
        "; ".join(f"{v['records']}/{v['authors_mean']}/{v['authors_median']}" for v in tb3["t2g"].values()), not g3_bad and tb3["stats_ok"], "")
    b2g = {r["collaboration"]: r for r in dicts_of(BT / "T2g_authors_by_collaboration.csv")}
    gb_bad = [r["collaboration"] for r in t2g for c in ("records", "authors_mean", "authors_median")
              if r[c + "_F13_2b"] != b2g.get(r["collaboration"], {}).get(c)]
    tot_auth = sum(r["n_auth"] for r in R)
    zero = sum(1 for r in R if r["n_auth"] == 0)
    add("C04e", "T2g_v31 F13_2b columns equal F13.2b T2g; authors counted", f"{num.get('authors_counted')} authors", f"{tot_auth} authors",
        not gb_bad and tot_auth == num.get("authors_counted") and b2g.get("all", {}).get("authors_max") == tb31["t2g"]["all"]["authors_max"],
        f"{len(gb_bad)} F13_2b cells differ; {zero} records with no author, kept as 0 in mean and median")
    t2f = dicts_of(T / "T2f_v31_collaboration_by_year.csv")
    ycols = list(t2f[0].keys())
    ybad = yunk = 0
    for r in t2f:
        exp = collab_cells(tb31["year"][r["year"]], tb3["year"][r["year"]], ycols)
        yunk += sum(1 for c in ycols if c != "year" and c not in exp)
        ybad += sum(1 for c in exp if exp[c] != r[c])
    add("C04f", "T2f_v31 every cell, all years (extra check)", f"{len(t2f) * (len(ycols) - 1)} cells",
        f"{len(t2f) * (len(ycols) - 1) - ybad - yunk} equal", ybad == 0 and yunk == 0 and len(t2f) == len(YEARS)
        and sum(tb31["year"][str(y)]["total"] for y in YEARS) == 841, f"{ybad} differ, {yunk} not recomputable; years sum to 841")
    trans = Counter((lab3[e][1], lab31[e][1]) for e in lab3)
    changed = {f"{a} -> {b}": n for (a, b), n in trans.items() if a != b}
    t2h = Counter({(r["type_v3"], r["type_v31"]): int(r["records"]) for r in dicts_of(T / "T2h_collaboration_transitions.csv")})
    add("C04g", "records that change collaboration type between v3 and v3.1 (T2h, numbers.json)",
        f"{len(num.get('transitions', {}))} transitions", f"{len(changed)} transitions", changed == num.get("transitions") and t2h == trans,
        f"T2h cross-table equal: {t2h == trans}; no record changes type")

    # ---------------- C05 R13
    EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    ORCID = re.compile(r"\b(?:0000|0009)-\d{4}-\d{4}-\d{3}[\dX]\b")
    PERSONAL_COLS = {"authors", "author", "author full names", "author(s) id", "authors with affiliations", "correspondence address",
                     "author_names", "author_ids", "email", "orcid", "name", "surname"}
    files = sorted(p for p in guard(T).iterdir() if p.is_file()) + [OUT / "F13_2e_numbers.json"]
    shapes = hits = 0
    hit_files = set()
    bad_cols, agg_cols, long_cells = [], set(), 0
    for p in files:
        txt = text_of(p)
        shapes += len(EMAIL.findall(txt)) + len(ORCID.findall(txt))
        h = {w.lower() for w in re.findall(r"[^\W\d_]+", txt)} & surnames
        if h:
            hits += len(h)
            hit_files.add(p.name)
        if p.suffix == ".csv":
            rr = list(csv.reader(io.StringIO(txt, newline="")))
            for c in rr[0]:
                if c.lower() in PERSONAL_COLS or re.search(r"e-?mail|orcid", c, re.I):
                    bad_cols.append(c)
                elif re.search(r"author", c, re.I):
                    if re.fullmatch(r"authors_(mean|median|max)(_v3|_F13_2b)?", c):
                        agg_cols.add(c)
                    else:
                        bad_cols.append(c)
            long_cells += sum(1 for row in rr for c in row if len(c.split()) > 30)
    add("C05a", "e-mail or ORCID shapes in tables and numbers.json", "0", shapes, shapes == 0, f"{len(files)} files scanned")
    add("C05b", "surname tokens of the Authors column in tables and numbers.json", "0", hits, hits == 0,
        f"{len(surnames)} tokens of 4+ letters after removing Affiliations and country words; held in memory only"
        + (f"; files: {', '.join(sorted(hit_files))}" if hit_files else ""))
    add("C05c", "no author, email or orcid column", "0", len(bad_cols), not bad_cols,
        f"{len(agg_cols)} T2g columns named authors_mean/median/max hold aggregate counts, not names")
    add("C05d", "no CSV cell over 30 words in tables", "0", long_cells, long_cells == 0, "")

    # ---------------- write
    fields = ["check_id", "what", "expected_from_tables", "recomputed", "verdict", "note"]
    for r in res:
        for c in fields:
            assert len(r[c].split()) <= 30, (r["check_id"], c, len(r[c].split()))
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
