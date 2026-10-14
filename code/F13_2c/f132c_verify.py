import sys; sys.dont_write_bytecode = True
# F13.2c independent verifier. Own implementation of the rules in the verifier brief.
# R13: from E1 only EID, Year, Affiliations, Authors with affiliations and the count of
# Authors items are kept; author names live only in memory and are never printed or written.
import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict

NL = chr(10)
ROOT = os.environ.get("PROJECT_ROOT", ".")
DPRG = ROOT + "/outputs/dprg_revision_2026"
PH = DPRG + "/phase_F13_2c"
TAB = PH + "/tables"
B2 = DPRG + "/phase_F13_2b/tables"
E1 = DPRG + "/author_exports_2026_10/scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"
ACCEPTED = "fe01023d23afe95df83d594fdfea2c3b488e52ffb8778def4067a2d795a991f3"
STAMP = PH + "/F13_2c_brief_stamp.json"
NUMBERS = PH + "/F13_2c_numbers.json"
OUT = PH + "/phase_F13_2c_independent_verification.csv"

KZ = "Kazakhstan"
PERIODS = ["2003-2016", "2017-2021", "2022-2025"]
K_KZ = "Kazakhstan only"
K_FO = "foreign only"
K_BOTH = "both (Kazakhstan and abroad)"
K_NONE = "no address"
KINDS = [K_KZ, K_FO, K_BOTH, K_NONE]
AUPET = "Almaty University of Power Engineering and Telecommunications named after Gumarbek Daukeyev"
LETTERS = re.compile(r"[^\W\d_]+")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.reader(f)]


def period(y):
    if 2003 <= y <= 2016:
        return PERIODS[0]
    if 2017 <= y <= 2021:
        return PERIODS[1]
    if 2022 <= y <= 2025:
        return PERIODS[2]
    return None


def pct(a, b):
    return "%.1f" % (100.0 * a / b) if b else "0.0"


def words(s):
    return len(str(s).split())


def diff_rows(exp, got, cols):
    """exp, got: dict key -> list of strings (aligned with cols). Returns list of (key, col)."""
    out = []
    for k in sorted(set(exp) | set(got), key=str):
        e = exp.get(k)
        g = got.get(k)
        if e is None or g is None:
            out.append((k, "row missing"))
            continue
        for c, a, b in zip(cols, e, g):
            if a != b:
                out.append((k, c))
    return out


# ---------------------------------------------------------------- inputs
COUNTRY_ROWS = read_csv(B2 + "/scopus_country_names.csv")
_ci = COUNTRY_ROWS[0].index("country_name")
COUNTRIES = set(r[_ci] for r in COUNTRY_ROWS[1:] if r)

csv.field_size_limit(1 << 30)
WANT = ["EID", "Year", "Affiliations", "Authors with affiliations", "Authors"]
recs = []
with open(E1, encoding="utf-8-sig", newline="") as f:
    rd = csv.reader(f)
    header = next(rd)
    ix = dict((c, header.index(c)) for c in WANT)
    for row in rd:
        if not row or all(not x for x in row):
            continue
        n_auth = len([x for x in row[ix["Authors"]].split(";") if x.strip()])
        recs.append({
            "eid": row[ix["EID"]],
            "year": int(row[ix["Year"]].strip()),
            "aff": row[ix["Affiliations"]],
            "awa": row[ix["Authors with affiliations"]],
            "n_auth": n_auth,
        })
        row = None
N = len(recs)


# ---------------------------------------------------------------- rule 1 and rule 2
def split_semi(s):
    return s.split("; ") if s != "" else []


def line_country(line):
    last = line.split(", ")[-1]
    return last if last in COUNTRIES else None


def decompose(rest, lines_sorted, memo):
    if rest in memo:
        return memo[rest]
    res = None
    for ln in lines_sorted:
        if rest == ln:
            res = [ln]
            break
        if rest.startswith(ln + ", "):
            sub = decompose(rest[len(ln) + 2:], lines_sorted, memo)
            if sub is not None:
                res = [ln] + sub
                break
    memo[rest] = res
    return res


def kind_of(cs):
    if not cs:
        return K_NONE
    if KZ in cs:
        return K_KZ if len(cs) == 1 else K_BOTH
    return K_FO


for r in recs:
    lines = split_semi(r["aff"])
    r["lines"] = lines
    A = set()
    for ln in lines:
        c = line_country(ln)
        if c:
            A.add(c)
    r["A"] = A
    r["intl"] = any(c != KZ for c in A)
    r["per"] = period(r["year"])
    ls = sorted(set(lines), key=lambda x: (-len(x), x))
    memo = {}
    authors = []
    for e in split_semi(r["awa"]):
        p = e.find(", ")
        if p < 0:
            authors.append((e, frozenset(), "none", 0))
            continue
        name = e[:p]
        rest = e[p + 2:]
        d = decompose(rest, ls, memo)
        if d is None:
            cs = frozenset(x for x in rest.split(", ") if x in COUNTRIES)
            authors.append((name, cs, "fallback", 0))
        else:
            cs = frozenset(c for c in (line_country(x) for x in d) if c)
            authors.append((name, cs, "lines", len(d)))
    r["authors"] = authors
    r["kinds"] = [kind_of(a[1]) for a in authors]
    AU = set()
    for a in authors:
        AU |= a[1]
    r["AU"] = AU
    r["intl_au"] = any(c != KZ for c in AU)

rows_out = []


def add(cid, what, exp, got, ok):
    cells = [cid, what, exp, got, "PASS" if ok else "FAIL"]
    for c in cells:
        if words(c) > 30:
            raise SystemExit("cell over 30 words in " + cid)
    rows_out.append(cells)
    print(cid, cells[4], "|", got)


# ---------------------------------------------------------------- C01
stamp = json.load(open(STAMP, encoding="utf-8"))
eids = [r["eid"] for r in recs]
e1_sha = sha(E1)
inp = stamp["inputs"]
inp_ok = 0
for rel, meta in sorted(inp.items()):
    if sha(ROOT + "/" + rel) == meta["sha256"]:
        inp_ok += 1
c01 = (N == 841 and len(set(eids)) == 841 and e1_sha == ACCEPTED and len(inp) == 9 and inp_ok == 9)
add("C01", "E1 record count, unique EIDs, sha256 vs accepted; sha256 of the 9 stamped inputs",
    "841 records; 841 unique EIDs; sha256 fe01023d...91f3; 9 inputs as stamped",
    "%d records; %d unique EIDs; sha256 %s; %d of %d stamped inputs equal"
    % (N, len(set(eids)), "equal" if e1_sha == ACCEPTED else "DIFFERS", inp_ok, len(inp)),
    c01)

# ---------------------------------------------------------------- C02 T2a
base = [r for r in recs if r["intl"]]
CLS = ["(i)", "(ii)", "(iii)"]


def cls_of(r):
    fo = K_FO in r["kinds"]
    kza = (K_KZ in r["kinds"]) or (K_BOTH in r["kinds"])
    if fo and kza:
        return "(i)"
    if not fo:
        return "(ii)"
    return "(iii)"


cls_cnt = Counter()
cls_per = defaultdict(Counter)
base_per = Counter()
for r in base:
    c = cls_of(r)
    cls_cnt[c] += 1
    cls_per[c][r["per"]] += 1
    base_per[r["per"]] += 1
t2a = read_csv(TAB + "/T2a_international_by_author.csv")
t2a_h = t2a[0]
exp = {}
for row in t2a[1:]:
    if not row:
        continue
    key = row[0].split(" ")[0] if row[0].startswith("(") else row[0]
    exp[key] = row[1:]
got = {}
nb = len(base)
for c in CLS:
    v = [str(cls_cnt[c]), pct(cls_cnt[c], nb)]
    for p in PERIODS:
        v += [str(cls_per[c][p]), pct(cls_per[c][p], base_per[p])]
    got[c] = v
v = [str(nb), pct(nb, nb)]
for p in PERIODS:
    v += [str(base_per[p]), pct(base_per[p], base_per[p])]
got["all international"] = v
d = diff_rows(exp, got, t2a_h[1:])
f2b = read_csv(B2 + "/T2c_international_share.csv")
f2b_h = f2b[0]
ref517 = None
for row in f2b[1:]:
    if row and row[0] == "all":
        ref517 = int(row[f2b_h.index("international")])


def fmt_cls(src):
    parts = []
    for c in CLS:
        e = src[c]
        parts.append("%s %s [%s/%s/%s]" % (c, e[0], e[2], e[4], e[6]))
    return "; ".join(parts)


add("C02", "T2a classes (i)/(ii)/(iii) of international records, overall and by period (with %), own author parsing",
    fmt_cls(exp) + "; base 517; F13.2b T2c all-international %s" % ref517,
    fmt_cls(got) + "; base %d; %d cells differ" % (nb, len(d)),
    (not d) and nb == 517 and ref517 == 517)

# ---------------------------------------------------------------- C03 T2b
t2b = read_csv(TAB + "/T2b_first_author_country.csv")
t2b_h = t2b[0]
exp = {}
for row in t2b[1:]:
    if row:
        exp[(row[0], row[1])] = row[2:]
no_entry = sum(1 for r in recs if not r["authors"])


def first_kind(r):
    return r["kinds"][0] if r["kinds"] else K_NONE


got = {}
for blabel, bset in (("841 records", recs), ("517 international records", base)):
    bper = Counter(r["per"] for r in bset)
    cnt = Counter(first_kind(r) for r in bset)
    cper = defaultdict(Counter)
    for r in bset:
        cper[first_kind(r)][r["per"]] += 1
    for k in KINDS:
        v = [str(cnt[k]), pct(cnt[k], len(bset))]
        for p in PERIODS:
            v += [str(cper[k][p]), pct(cper[k][p], bper[p])]
        got[(blabel, k)] = v
d = diff_rows(exp, got, t2b_h[2:])


def fmt_b(src):
    a = "/".join(src[("841 records", k)][0] for k in KINDS)
    b = "/".join(src[("517 international records", k)][0] for k in KINDS)
    return "841: %s; 517: %s (KZ/foreign/both/none)" % (a, b)


add("C03", "T2b first-author kind over 841 and over 517, overall and by period (with %)",
    fmt_b(exp), fmt_b(got) + "; %d cells differ; records without entries %d" % (len(d), no_entry),
    not d)

# ---------------------------------------------------------------- C04 T2c
t2c = read_csv(TAB + "/T2c_partners_other_than_ukraine.csv")
exp = {}
for row in t2c[1:]:
    if row:
        exp[row[0]] = row[1:]


def t2c_counts(key, ikey):
    other = ukr_only = with_ukr = intl = 0
    for r in recs:
        F = set(r[key]) - {KZ}
        if F - {"Ukraine"}:
            other += 1
        if F == {"Ukraine"}:
            ukr_only += 1
        if "Ukraine" in r[key]:
            with_ukr += 1
        if r[ikey]:
            intl += 1
    return [other, ukr_only, with_ukr, intl]


ca = t2c_counts("A", "intl")
cu = t2c_counts("AU", "intl_au")
labels = ["records with a foreign country other than Ukraine", "records whose only foreign country is Ukraine",
          "records with Ukraine among their countries", "international records"]
got = dict((labels[i], [str(ca[i]), str(cu[i])]) for i in range(4))
d = diff_rows(exp, got, t2c[0][1:])
add("C04", "T2c: other than Ukraine / Ukraine only / with Ukraine / international, by Affiliations and by authors",
    "; ".join("%s|%s" % tuple(exp[l]) for l in labels if l in exp),
    "; ".join("%d|%d" % (ca[i], cu[i]) for i in range(4)) + "; %d cells differ" % len(d),
    not d)

# ---------------------------------------------------------------- C06 T1a / T1b
t1b = read_csv(TAB + "/T1b_country_check.csv")
t1b_e = dict((row[0], row[1]) for row in t1b[1:] if row)
differ = 0
reasons = Counter()
for r in recs:
    if r["AU"] != r["A"]:
        differ += 1
        if r["AU"] - r["A"]:
            reasons["authors add a country"] += 1
        if r["A"] - r["AU"]:
            reasons["authors miss a country"] += 1
t1b_g = {
    "records whose country set by authors equals the set by Affiliations": str(N - differ),
    "records whose sets differ": str(differ),
    "international records by Affiliations": str(sum(1 for r in recs if r["intl"])),
    "international records by authors": str(sum(1 for r in recs if r["intl_au"])),
}
t1b_ok = all(t1b_e.get(k) == v for k, v in t1b_g.items()) and len(t1b_e) == len(t1b_g)
t1a = read_csv(TAB + "/T1a_parsing.csv")
t1a_e = dict((row[0], row[1]) for row in t1a[1:] if row)
positions = sum(len(r["authors"]) for r in recs)
multi = sum(1 for r in recs for a in r["authors"] if a[2] == "lines" and a[3] >= 2)
one = sum(1 for r in recs for a in r["authors"] if a[2] == "lines" and a[3] == 1)
noaff = sum(1 for r in recs for a in r["authors"] if a[2] == "none")
fb = sum(1 for r in recs for a in r["authors"] if a[2] == "fallback")
mism = sum(1 for r in recs if len(r["authors"]) != r["n_auth"])
consec = 0
rep_pairs = 0
for r in recs:
    nm = [a[0] for a in r["authors"]]
    consec += sum(1 for i in range(len(nm) - 1) if nm[i] == nm[i + 1])
    rep_pairs += sum(1 for v in Counter(nm).values() if v >= 2)
t1a_g = {
    "records parsed": str(N),
    "author positions (entries of Authors with affiliations)": str(positions),
    "authors with two or more affiliations": str(multi),
    "entries with one Affiliations line": str(one),
    "entries with two or more Affiliations lines": str(multi),
    "entries without an affiliation": str(noaff),
    "entries read by the fallback (countries from the parts)": str(fb),
    "records where author positions differ from the Authors count": str(mism),
    "pairs of consecutive entries with the same name (two authors)": str(consec),
    "repeated names within a record (any position)": str(rep_pairs),
}
t1a_bad = sorted(k for k in t1a_g if t1a_e.get(k) != t1a_g[k])
core = ["author positions (entries of Authors with affiliations)", "authors with two or more affiliations",
        "records where author positions differ from the Authors count"]
c06_ok = t1b_ok and not any(k in t1a_bad for k in core) and differ == int(t1b_e.get("records whose sets differ", "-1"))
add("C06", "T1b country set by authors vs set A (count, reasons); T1a positions, authors with >=2 affiliations, Authors-count mismatches",
    "T1b differ %s; T1a positions %s, multi %s, mismatch %s"
    % (t1b_e.get("records whose sets differ"), t1a_e.get(core[0]), t1a_e.get(core[1]), t1a_e.get(core[2])),
    "differ %d (reasons %d); positions %d, multi %d, mismatch %d; other T1a rows differing %d"
    % (differ, sum(reasons.values()), positions, multi, mism, len(t1a_bad)),
    c06_ok)

# ---------------------------------------------------------------- rule 6 / 7 / 8 institutions
LEVELS = [
    ["university", "универс"],
    ["institute", "academy", "college"],
    ["centre", "center", "laboratory"],
    ["company", "llp", "jsc", "ltd", "corporation"],
    ["ministry", "agency", "committee", "department of"],
    ["hospital", "clinic"],
]
WHOLE = set(["llp", "jsc", "ltd"])
DEPT = ["republic", "kazakhstan", "city", "region", "regional", "police", "state", "government", "akimat",
        "national security", "internal affairs", "defence", "defense", "emergency"]
DEPT_RE = [re.compile(r"\b" + re.escape(w) + r"\b") for w in DEPT]
WHOLE_RE = dict((w, re.compile(r"\b" + w + r"\b")) for w in WHOLE)


def holds(part, lvl):
    low = part.lower()
    for kw in LEVELS[lvl]:
        if kw in WHOLE:
            if WHOLE_RE[kw].search(low):
                return True
        elif kw == "department of":
            if "department of" in low and any(x.search(low) for x in DEPT_RE):
                return True
        elif kw in low:
            return True
    return False


def institution(parts):
    cands = parts[:-2] if len(parts) >= 3 else parts[:-1]
    for lvl in range(len(LEVELS)):
        for c in cands:
            if holds(c, lvl):
                return c
    return parts[0]


INIT_RE = re.compile(r"(?<![^\W\d_])[^\W\d_]\.")
DASHES = ["-", chr(0x2010), chr(0x2011), chr(0x2012), chr(0x2013), chr(0x2014), "."]
R_NAMED = re.compile(r"\bnamed after\b")
R_AFTER = re.compile(r"\bafter\b")
R_THE = re.compile(r"\bthe\b")


def norm(s):
    s = s.lower()
    s = INIT_RE.sub(" ", s)
    for ch in DASHES:
        s = s.replace(ch, " ")
    s = R_NAMED.sub(" ", s)
    s = R_AFTER.sub(" ", s)
    s = R_THE.sub(" ", s)
    return " ".join(s.split())


rawcount = defaultdict(Counter)
for r in recs:
    keys = []
    for ln in r["lines"]:
        parts = ln.split(", ")
        if parts[-1] == KZ:
            inst = institution(parts)
            k = norm(inst)
            keys.append(k)
            rawcount[k][inst] += 1
    r["kzkeys"] = keys

thes = read_csv(TAB + "/institutions_thesaurus_v2.csv")
th_h = thes[0]
th_rows = [dict(zip(th_h, row)) for row in thes[1:] if row]
v2_rows = [x for x in th_rows if x["status"] == "active"]
v1_rows = [x for x in th_rows if x["version"] == "v1"]
not_norm = sum(1 for x in th_rows if norm(x["variant"]) != x["variant"])


def make_labeler(rows):
    vmap = {}
    for x in rows:
        vmap[x["variant"]] = x["canonical"]
    cmap = {}
    for c in sorted(set(x["canonical"] for x in rows)):
        cmap.setdefault(norm(c), c)
    cache = {}

    def label(key):
        if key in cache:
            return cache[key]
        if key in vmap:
            res = vmap[key]
        elif key in cmap:
            res = cmap[key]
        else:
            res = sorted(rawcount[key].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        cache[key] = res
        return res
    return label


lab_v1 = make_labeler(v1_rows)
lab_v2 = make_labeler(v2_rows)
sets_v1 = [set(lab_v1(k) for k in r["kzkeys"]) for r in recs]
sets_v2 = [set(lab_v2(k) for k in r["kzkeys"]) for r in recs]


def t3a(labelsets):
    cnt = Counter()
    per = defaultdict(Counter)
    intl = Counter()
    for r, labs in zip(recs, labelsets):
        for l in labs:
            cnt[l] += 1
            per[l][r["per"]] += 1
            if r["intl"]:
                intl[l] += 1
    order = sorted(cnt, key=lambda k: (-cnt[k], k))
    out = []
    for i, k in enumerate(order, 1):
        out.append([str(i), k, str(cnt[k]), pct(cnt[k], N)] + [str(per[k][p]) for p in PERIODS]
                   + [str(intl[k]), pct(intl[k], cnt[k])])
    return out, cnt


def strip_type(row, h):
    ti = h.index("type")
    return row[:ti] + row[ti + 1:]


my_v2, cnt_v2 = t3a(sets_v2)
my_v1, cnt_v1 = t3a(sets_v1)
t3 = read_csv(TAB + "/T3a_v2_kz_institutions.csv")
t3_h = t3[0]
t3_rows = [strip_type(row, t3_h) for row in t3[1:] if row]
cols = [c for c in t3_h if c != "type"]
top_bad = []
for i in range(30):
    for c, a, b in zip(cols, t3_rows[i], my_v2[i]):
        if a != b:
            top_bad.append((i + 1, c))
all_equal_v2 = (t3_rows == my_v2)
t3b = read_csv(B2 + "/T3a_kz_institutions.csv")
t3b_rows = [strip_type(row, t3b[0]) for row in t3b[1:] if row]
all_equal_v1 = (t3b_rows == my_v1)
v1_sub = read_csv(B2 + "/institutions_thesaurus.csv")
v1_h = v1_sub[0]
v1_file = [tuple(row) for row in v1_sub[1:] if row]
v1_in_v2 = [tuple(x[c] for c in v1_h) for x in v1_rows]
v1_match = (v1_file == v1_in_v2)
aupet_v2 = cnt_v2.get(AUPET, 0)
aupet_tab = None
for row in t3[1:]:
    if row and row[1] == AUPET:
        aupet_tab = int(row[t3_h.index("records")])
add("C07", "T3a_v2 top 30 recomputed with thesaurus v2 (names, records, order, periods, international); AUPET records",
    "T3a_v2 rows 1-30 (%d institutions); AUPET %s (expected 63)" % (len(t3_rows), aupet_tab),
    "%d of %d top-30 cells differ (type not compared); AUPET %d; all %d rows equal %s; v1 rerun equals F13.2b T3a %s"
    % (len(top_bad), 30 * len(cols), aupet_v2, len(my_v2), "yes" if all_equal_v2 else "no", "yes" if all_equal_v1 else "no"),
    (not top_bad) and aupet_v2 == 63 and aupet_tab == 63)

# ---------------------------------------------------------------- C08 T2f2_v2
CT = ["single institution", "domestic multi-institution", "international"]


def collab(labelsets):
    out = []
    for r, labs in zip(recs, labelsets):
        if len(r["A"]) >= 2:
            out.append(CT[2])
        elif len(labs) >= 2:
            out.append(CT[1])
        else:
            out.append(CT[0])
    return out


ty_v1 = collab(sets_v1)
ty_v2 = collab(sets_v2)
changed = sum(1 for a, b in zip(ty_v1, ty_v2) if a != b)


def by_period(types):
    out = {}
    for p in PERIODS + ["2003-2025"]:
        sel = [t for r, t in zip(recs, types) if p == "2003-2025" or r["per"] == p]
        c = Counter(sel)
        tot = len(sel)
        out[p] = [str(c[t]) for t in CT] + [str(tot)] + [pct(c[t], tot) for t in CT]
    return out


t2f2 = read_csv(TAB + "/T2f2_v2_collaboration_by_period.csv")
exp = dict((row[0], row[1:]) for row in t2f2[1:] if row)
got = by_period(ty_v2)
d = diff_rows(exp, got, t2f2[0][1:])
f2b2 = read_csv(B2 + "/T2f2_collaboration_by_period.csv")
exp_v1 = dict((row[0], row[1:]) for row in f2b2[1:] if row)
d_v1 = diff_rows(exp_v1, by_period(ty_v1), f2b2[0][1:])
intl_r9 = sum(1 for t in ty_v2 if t == CT[2])
intl_r1 = sum(1 for r in recs if r["intl"])
add("C08", "T2f2_v2 collaboration types by period (rule 9, thesaurus v2); records changing type v1 to v2",
    "2003-2025 %s; numbers.json collab_v1 equals collab_v2" % "/".join(exp["2003-2025"][:4]),
    "2003-2025 %s; %d cells differ; %d records change type; v1 rerun equals F13.2b T2f2 %s"
    % ("/".join(got["2003-2025"][:4]), len(d), changed, "yes" if not d_v1 else "no"),
    not d)

# ---------------------------------------------------------------- C05 R13
INITIAL_TOK = re.compile(r"^(?:[^\W\d_]{1,3}\.-?)+$")
aff_words = set()
for r in recs:
    for w in LETTERS.findall(r["aff"]):
        aff_words.add(w.lower())
for c in COUNTRIES:
    for w in LETTERS.findall(c):
        aff_words.add(w.lower())
toks_all = set()
skipped_names = 0
for r in recs:
    for a in r["authors"]:
        nm = a[0].strip()
        if nm.startswith("["):
            skipped_names += 1
            continue
        parts = nm.split()
        while len(parts) > 1 and INITIAL_TOK.match(parts[-1]):
            parts.pop()
        for t in parts:
            for w in LETTERS.findall(t):
                if len(w) >= 4:
                    toks_all.add(w.lower())
set_aside = toks_all & aff_words
checked = toks_all - set_aside

files = [TAB + "/" + n for n in sorted(os.listdir(TAB))] + [NUMBERS]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
ORCID = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dXx]\b")
NAME_HDR = re.compile(r"^\s*(authors?|author[ _]?names?|names?|surnames?|full[ _]?names?|given[ _]?names?|"
                      r"authors with affiliations|author full names|author\(s\) id|orcid|e-?mails?)\s*$", re.I)
em = orc = hdr = over30 = 0
hit_files = Counter()
hdr_with_author = []
max_words = 0


def cells_of(path, text):
    if path.endswith(".csv"):
        rows = list(csv.reader(text.splitlines()))
        return (rows[0] if rows else []), [c for row in rows for c in row]
    if path.endswith(".json"):
        out = []

        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    out.append(str(k))
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
            else:
                out.append(str(o))
        walk(json.loads(text))
        return [], out
    hdrs, cells, in_table = [], [], False
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("|"):
            parts = [p.strip() for p in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", p) for p in parts if p):
                continue
            if not in_table:
                hdrs += parts
            in_table = True
            cells += parts
        else:
            in_table = False
    return hdrs, cells


for path in files:
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    em += len(EMAIL.findall(text))
    orc += len(ORCID.findall(text))
    hdrs, cells = cells_of(path, text)
    for h in hdrs:
        if NAME_HDR.match(h):
            hdr += 1
        if "author" in h.lower() or "name" in h.lower():
            hdr_with_author.append(h)
    for c in cells:
        w = words(c)
        max_words = max(max_words, w)
        if w > 30:
            over30 += 1
    fw = set(w.lower() for w in LETTERS.findall(text))
    h = len(checked & fw)
    if h:
        hit_files[os.path.basename(path)] += h
hits = sum(hit_files.values())
c05_ok = em == 0 and orc == 0 and hdr == 0 and over30 == 0 and hits == 0
add("C05", "R13 over tables/* and numbers.json: e-mail/ORCID shapes, author-name headers, cells over 30 words, surname tokens as whole words",
    "0 e-mail, 0 ORCID, 0 name headers, 0 cells over 30 words, 0 surname hits",
    "%d files; e-mail %d, ORCID %d, name headers %d, cells>30 %d (max %d); %d tokens checked, %d set aside; hits %d"
    % (len(files), em, orc, hdr, over30, max_words, len(checked), len(set_aside), hits),
    c05_ok)

# ---------------------------------------------------------------- write
order = ["C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08"]
rows_out.sort(key=lambda x: order.index(x[0]))
with open(OUT, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator=NL)
    w.writerow(["check_id", "what", "expected_from_tables", "recomputed", "verdict"])
    for row in rows_out:
        w.writerow(row)

print("info: columns in E1", len(header), "| records outside periods", sum(1 for r in recs if r["per"] is None))
print("info: thesaurus rows", len(th_rows), "active", len(v2_rows), "v1", len(v1_rows), "variants not normalised", not_norm,
      "| v1 rows equal F13.2b thesaurus", v1_match)
print("info: rule-9 international", intl_r9, "rule-1 international", intl_r1)
print("info: T1b reasons", sum(reasons.values()), "| T1a rows differing", len(t1a_bad), "| names skipped (bracketed)", skipped_names)
print("info: headers containing author/name:", sorted(set(hdr_with_author)))
print("info: surname-hit files:", dict(hit_files))
print("info: T2a/T3a diffs", top_bad[:5], "| T2f2 diff", d, "| v1 T2f2 diff", d_v1)
print("info: v1 rerun all rows equal F13.2b T3a", all_equal_v1, "| v2 all rows equal", all_equal_v2)
print("sha256 of output", sha(OUT))
