import sys
sys.dont_write_bytecode = True

# Independent verifier of phase F13.2b (affiliations on the Scopus export E1).
# Written from the verification rules only; reads no other program of the phase.
# R13: from E1 only EID, Year, Document Type, Source title, Affiliations are kept;
# Authors is turned into a count at once; no other column is kept or printed.

import csv
import hashlib
import os
import re
from collections import Counter, defaultdict

ROOT = os.environ.get("PROJECT_ROOT", ".")
DPRG = os.path.join(ROOT, "outputs", "dprg_revision_2026")
PH = os.path.join(DPRG, "phase_F13_2b")
TAB = os.path.join(PH, "tables")
FIG = os.path.join(PH, "figures")
E1 = os.path.join(DPRG, "author_exports_2026_10",
                  "scopus_full_TAK_KZ_2003_2025_2026-10-13.csv")
README = os.path.join(DPRG, "author_exports_2026_10", "README_exports.txt")
T2B_YEARS = os.path.join(DPRG, "phase_F13_1", "tables", "T2b_years.csv")
OUT = os.path.join(PH, "phase_F13_2b_independent_verification.csv")
BRIEF_PREFIX = "fe01023d23afe95d"
E1_NAME = "scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"

PERIODS = ["2003-2016", "2017-2021", "2022-2025"]
TYPE_MAP = {"article": "article", "review": "review",
            "conference paper": "conference paper",
            "book chapter": "book chapter", "book": "book",
            "retracted": "retracted"}
COLLAB = ["single institution", "domestic multi-institution", "international"]


def period_of(y):
    if 2003 <= y <= 2016:
        return "2003-2016"
    if 2017 <= y <= 2021:
        return "2017-2021"
    if 2022 <= y <= 2025:
        return "2022-2025"
    return None


def pct(a, b):
    return "{:.1f}".format(100.0 * a / b) if b else ""


def rank_items(counter):
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))


def read_table(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------- rule 2
GOV_WORDS = ["republic", "kazakhstan", "city", "region", "regional", "police",
             "state", "government", "akimat", "national security",
             "internal affairs", "defence", "defense", "emergency"]
GOV_RE = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in GOV_WORDS) + r")\b",
                    re.IGNORECASE)
WHOLE = {w: re.compile(r"\b" + w + r"\b", re.IGNORECASE) for w in ("llp", "jsc", "ltd")}


def has_level(part, lvl):
    low = part.lower()
    if lvl == 1:
        return "university" in low or "универс" in low
    if lvl == 2:
        return any(k in low for k in ("institute", "academy", "college"))
    if lvl == 3:
        return any(k in low for k in ("centre", "center", "laboratory"))
    if lvl == 4:
        return ("company" in low or "corporation" in low
                or any(WHOLE[w].search(part) for w in ("llp", "jsc", "ltd")))
    if lvl == 5:
        if any(k in low for k in ("ministry", "agency", "committee")):
            return True
        return "department of" in low and GOV_RE.search(part) is not None
    if lvl == 6:
        return "hospital" in low or "clinic" in low
    return False


def institution_of(parts):
    cands = parts[:-2] if len(parts) >= 3 else parts[:-1]
    for lvl in range(1, 7):
        for c in cands:
            if has_level(c, lvl):
                return c, lvl
    return parts[0], 0  # unresolved


# ---------------------------------------------------------------- rule 4
INIT_RE = re.compile(r"(?<![^\W\d_])[^\W\d_]\.")
PUNCT_RE = re.compile("[-\u2010\u2011\u2012\u2013\u2014.]")
NAMED_RE = re.compile(r"\bnamed after\b")
AFTER_RE = re.compile(r"\bafter\b")
THE_RE = re.compile(r"\bthe\b")


def norm(s):
    s = s.lower()
    s = INIT_RE.sub(" ", s)
    s = PUNCT_RE.sub(" ", s)
    s = NAMED_RE.sub(" ", s)
    s = AFTER_RE.sub(" ", s)
    s = THE_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    rows_out = []

    def add(cid, what, exp, rec, ok):
        rows_out.append([cid, what, exp, rec, "PASS" if ok else "FAIL"])

    # ------------------------------------------------------------ load E1
    csv.field_size_limit(1 << 30)
    keep_cols = ["EID", "Year", "Document Type", "Source title", "Affiliations"]
    records = []
    with open(E1, "r", encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh)
        header = next(rd)
        idx = {}
        for name in keep_cols + ["Authors"]:
            hits = [i for i, h in enumerate(header) if h.strip() == name]
            if len(hits) != 1:
                raise SystemExit("header column not found exactly once: " + name)
            idx[name] = hits[0]
        for row in rd:
            if not row:
                continue
            n_auth = len([a for a in row[idx["Authors"]].split(";") if a.strip()])
            rec = {
                "eid": row[idx["EID"]].strip(),
                "year": int(row[idx["Year"]].strip()),
                "dtype": row[idx["Document Type"]].strip().lower(),
                "source": row[idx["Source title"]].strip(),
                "aff": row[idx["Affiliations"]],
                "n_auth": n_auth,
            }
            records.append(rec)
            del row
    n_rec = len(records)
    n_eid = len(set(r["eid"] for r in records))

    # ------------------------------------------------------------ C01
    digest = sha256_of(E1)
    readme_sha = None
    with open(README, "r", encoding="utf-8-sig") as fh:
        for line in fh:
            if line.lstrip().startswith("- " + E1_NAME):
                m = re.search(r"sha256 ([0-9a-f]{64})", line)
                if m:
                    readme_sha = m.group(1)
    ok = (n_rec == 841 and n_eid == 841 and readme_sha is not None
          and digest == readme_sha and digest.startswith(BRIEF_PREFIX))
    add("C01", "E1 records, unique EID, sha256 vs README and brief prefix",
        "841 records; 841 unique EID; README sha256 " + (readme_sha or "missing")[:16] + "...",
        "{} records; {} unique EID; sha256 {}...; equals README {}; prefix {}".format(
            n_rec, n_eid, digest[:16], digest == readme_sha, digest.startswith(BRIEF_PREFIX)),
        ok)

    # ------------------------------------------------------------ parse
    country_names = set(r["country_name"].strip()
                        for r in read_table(os.path.join(TAB, "scopus_country_names.csv")))
    n_lines = 0
    n_kz_lines = 0
    last_lines = Counter()
    last_recs = Counter()
    kz_key_raw = defaultdict(Counter)  # key -> raw institution counts (lines)
    kz_key_recs = defaultdict(set)     # key -> record indices
    for i, r in enumerate(records):
        lines = [s.strip() for s in r["aff"].split("; ")]
        lines = [s for s in lines if s]
        r["lines"] = []
        lasts = set()
        for ln in lines:
            parts = [p.strip() for p in ln.split(", ")]
            parts = [p for p in parts if p]
            if not parts:
                continue
            n_lines += 1
            last = parts[-1]
            last_lines[last] += 1
            lasts.add(last)
            inst, lvl = institution_of(parts)
            is_kz = last == "Kazakhstan"
            key = norm(inst) if is_kz else None
            if is_kz:
                n_kz_lines += 1
                kz_key_raw[key][inst] += 1
                kz_key_recs[key].add(i)
            r["lines"].append((parts, inst, lvl, is_kz, key))
        for la in lasts:
            last_recs[la] += 1
        r["countries"] = set(la for la in lasts if la in country_names)
        r["partners"] = r["countries"] - {"Kazakhstan"}
        r["has_kz"] = any(t[3] for t in r["lines"])
        del r["aff"]

    recs_with_kz = sum(1 for r in records if r["has_kz"])

    # ------------------------------------------------------------ C02
    t1a = {row["measure"]: row["value"] for row in read_table(os.path.join(TAB, "T1a_counts.csv"))}
    t1b = read_table(os.path.join(TAB, "T1b_last_parts.csv"))
    exp_lines = t1a.get("affiliation lines (split on '; ')")
    exp_kzl = t1a.get("lines whose last part is Kazakhstan")
    exp_rkz = t1a.get("records with at least one Kazakhstan line")
    t1b_full = sorted((x["last_part"], x["lines"], x["records"]) for x in t1b)
    my_full = sorted((k, str(v), str(last_recs[k])) for k, v in last_lines.items())
    ok = (exp_lines == str(n_lines) and len(t1b) == len(last_lines)
          and exp_rkz == str(recs_with_kz) and exp_kzl == str(n_kz_lines))
    add("C02", "affiliation lines, distinct last parts, records with a Kazakhstan line",
        "lines {}; last parts {} rows; Kazakhstan lines {}; records with KZ line {}".format(
            exp_lines, len(t1b), exp_kzl, exp_rkz),
        "lines {}; last parts {}; Kazakhstan lines {}; records with KZ line {}; T1b list and frequencies equal: {}".format(
            n_lines, len(last_lines), n_kz_lines, recs_with_kz, t1b_full == my_full),
        ok)

    # ------------------------------------------------------------ partners
    partner_cnt = Counter()
    partner_per = defaultdict(Counter)
    for r in records:
        r["period"] = period_of(r["year"])
        for c in r["partners"]:
            partner_cnt[c] += 1
            partner_per[c][r["period"]] += 1
    partner_rank = rank_items(partner_cnt)

    t2b = read_table(os.path.join(TAB, "T2b_partner_countries.csv"))
    exp20 = [(x["rank"], x["country"], x["records"]) for x in t2b[:20]]
    my20 = [(str(i + 1), c, str(n)) for i, (c, n) in enumerate(partner_rank[:20])]
    exp_all = [(x["rank"], x["country"], x["records"], x["share_of_841_pct"],
                x["2003-2016"], x["2017-2021"], x["2022-2025"]) for x in t2b]
    my_all = [(str(i + 1), c, str(n), pct(n, n_rec),
               str(partner_per[c]["2003-2016"]), str(partner_per[c]["2017-2021"]),
               str(partner_per[c]["2022-2025"])) for i, (c, n) in enumerate(partner_rank)]
    ok = exp20 == my20
    if ok:
        rec_txt = "top 20 equal; first: {} {}; 20th: {} {}; full {}-row list with shares and periods equal: {}".format(
            my20[0][1], my20[0][2], my20[19][1], my20[19][2], len(my_all), exp_all == my_all)
    else:
        diffs = [k + 1 for k in range(20) if k >= len(exp20) or exp20[k] != my20[k]]
        rec_txt = "differs at ranks {}; e.g. table {} vs mine {}".format(
            diffs[:5], exp20[diffs[0] - 1][1:] if diffs[0] - 1 < len(exp20) else None,
            my20[diffs[0] - 1][1:])
    add("C03", "top-20 partner countries by records (names, counts, order)",
        "T2b rows 1-20; first: {} {}".format(exp20[0][1], exp20[0][2]), rec_txt, ok)

    # ------------------------------------------------------------ C04
    t2c = read_table(os.path.join(TAB, "T2c_international_share.csv"))
    exp_p = [(x["value"], x["records"], x["international"], x["share_international_pct"])
             for x in t2c if x["group"] == "period"]
    my_p = []
    for p in PERIODS:
        rs = [r for r in records if r["period"] == p]
        ni = sum(1 for r in rs if r["partners"])
        my_p.append((p, str(len(rs)), str(ni), pct(ni, len(rs))))
    exp_t = [(x["value"], x["records"], x["international"], x["share_international_pct"])
             for x in t2c if x["group"] == "type"]
    tcnt = Counter(TYPE_MAP.get(r["dtype"], "other:" + r["dtype"]) for r in records)
    tint = Counter(TYPE_MAP.get(r["dtype"], "other:" + r["dtype"]) for r in records if r["partners"])
    my_t = [(t, str(n), str(tint[t]), pct(tint[t], n)) for t, n in rank_items(tcnt)]
    ok = exp_p == my_p
    add("C04", "share of international records by period (records, international, share)",
        "; ".join("{} {}/{} {}%".format(*e[0:1], e[2], e[1], e[3]) for e in exp_p),
        "; ".join("{} {}/{} {}%".format(m[0], m[2], m[1], m[3]) for m in my_p)
        + "; type rows also equal: {}".format(exp_t == my_t),
        ok)

    # ------------------------------------------------------------ thesaurus and labels
    thes = read_table(os.path.join(TAB, "institutions_thesaurus.csv"))
    var2can = {}
    dup_var = 0
    for t in thes:
        v = t["variant"]
        if v in var2can and var2can[v] != t["canonical"]:
            dup_var += 1
        var2can.setdefault(v, t["canonical"])
    normcan = defaultdict(set)
    for t in thes:
        normcan[norm(t["canonical"])].add(t["canonical"])
    ambiguous_nc = sum(1 for k, s in normcan.items() if len(s) > 1)

    label_of = {}
    for k, cnt in kz_key_raw.items():
        if k in var2can:
            label_of[k] = var2can[k]
        elif k in normcan:
            label_of[k] = sorted(normcan[k])[0]
        else:
            label_of[k] = rank_items(cnt)[0][0]

    for r in records:
        r["kz_inst"] = set(label_of[t[4]] for t in r["lines"] if t[3])
        if len(r["countries"]) >= 2:
            r["collab"] = "international"
        elif len(r["kz_inst"]) >= 2:
            r["collab"] = "domestic multi-institution"
        else:
            r["collab"] = "single institution"
    consistent_intl = all((len(r["countries"]) >= 2) == bool(r["partners"]) for r in records)

    # ------------------------------------------------------------ C05
    t2f2 = read_table(os.path.join(TAB, "T2f2_collaboration_by_period.csv"))
    exp5 = [tuple(x[c] for c in ["period"] + COLLAB + ["total"] + [k + " %" for k in COLLAB])
            for x in t2f2]
    my5 = []
    for p in PERIODS + ["2003-2025"]:
        rs = [r for r in records if p == "2003-2025" or r["period"] == p]
        cc = Counter(r["collab"] for r in rs)
        my5.append(tuple([p] + [str(cc[k]) for k in COLLAB] + [str(len(rs))]
                         + [pct(cc[k], len(rs)) for k in COLLAB]))
    ok = exp5 == my5
    add("C05", "collaboration types by period with the thesaurus (counts, totals, percentages)",
        "; ".join("{} {}/{}/{} of {}".format(*e[:5]) for e in exp5),
        "; ".join("{} {}/{}/{} of {}".format(*m[:5]) for m in my5)
        + ("; percentages equal" if ok else "; differs"),
        ok)

    # ------------------------------------------------------------ C06
    inst_cnt = Counter()
    inst_per = defaultdict(Counter)
    inst_int = Counter()
    for r in records:
        for l in r["kz_inst"]:
            inst_cnt[l] += 1
            inst_per[l][r["period"]] += 1
            if r["partners"]:
                inst_int[l] += 1
    inst_rank = rank_items(inst_cnt)
    t3a = read_table(os.path.join(TAB, "T3a_kz_institutions.csv"))
    cols = ["rank", "institution", "records", "2003-2016", "2017-2021", "2022-2025", "international"]
    exp6 = [tuple(x[c] for c in cols) for x in t3a[:30]]
    my6 = [(str(i + 1), l, str(n), str(inst_per[l]["2003-2016"]), str(inst_per[l]["2017-2021"]),
            str(inst_per[l]["2022-2025"]), str(inst_int[l])) for i, (l, n) in enumerate(inst_rank[:30])]
    exp_all3 = [(x["rank"], x["institution"], x["records"], x["share_of_841_pct"],
                 x["2003-2016"], x["2017-2021"], x["2022-2025"], x["international"],
                 x["share_international_pct"]) for x in t3a]
    my_all3 = [(str(i + 1), l, str(n), pct(n, n_rec), str(inst_per[l]["2003-2016"]),
                str(inst_per[l]["2017-2021"]), str(inst_per[l]["2022-2025"]), str(inst_int[l]),
                pct(inst_int[l], n)) for i, (l, n) in enumerate(inst_rank)]
    ok = exp6 == my6
    if ok:
        rec_txt = ("top 30 equal (names, counts, order, periods, international); records at ranks 1/2/3/30: "
                   "{}/{}/{}/{}; all {} rows equal: {}").format(
            my6[0][2], my6[1][2], my6[2][2], my6[29][2], len(my_all3), exp_all3 == my_all3)
    else:
        diffs = [k + 1 for k in range(30) if k >= len(exp6) or k >= len(my6) or exp6[k] != my6[k]]
        d = diffs[0] - 1
        fields = [cols[j] for j in range(len(cols))
                  if d < len(exp6) and d < len(my6) and exp6[d][j] != my6[d][j]]
        rec_txt = "differs at ranks {}; first differing fields at rank {}: {}; table records {} vs mine {}".format(
            diffs[:6], d + 1, fields, exp6[d][2] if d < len(exp6) else None, my6[d][2] if d < len(my6) else None)
    add("C06", "top-30 Kazakhstan institutions by records after the thesaurus",
        "T3a rows 1-30; records at ranks 1/2/3/30: {}/{}/{}/{}; {} rows in T3a".format(
            exp6[0][2], exp6[1][2], exp6[2][2], exp6[29][2], len(t3a)),
        rec_txt, ok)

    # ------------------------------------------------------------ C07
    F = set(t["variant"] for t in thes if t["rule"].startswith("merge"))
    T = set(norm(t["canonical"]) for t in thes)
    f_and_t = F & T
    chains = [t for t in thes if t["rule"].startswith("merge") and norm(t["canonical"]) in F]
    keep_bad = [t for t in thes if t["rule"].startswith("keep") and norm(t["canonical"]) != t["variant"]]
    other_rule = [t for t in thes if not (t["rule"].startswith("merge") or t["rule"].startswith("keep"))]
    all_keys = set(kz_key_raw)
    var_missing = [t["variant"] for t in thes if t["variant"] not in all_keys]
    multi_keys = [k for k, s in kz_key_recs.items() if len(s) >= 2]
    multi_missing = [k for k in multi_keys if k not in var2can]
    t3a_in_F = [x["institution"] for x in t3a if norm(x["institution"]) in F]
    var_not_norm = [t["variant"] for t in thes if norm(t["variant"]) != t["variant"]]
    rec_col_bad = [t["variant"] for t in thes if t["records"] != str(len(kz_key_recs.get(t["variant"], ())))]
    ok = (not f_and_t and not chains and not keep_bad and not var_missing and not multi_missing
          and len(thes) <= 200 and not t3a_in_F and dup_var == 0)
    add("C07", "thesaurus integrity (from/to disjoint, no chains, keep rows, variants in data, coverage, size, T3a)",
        "{} rows (<= 200); {} merge variants; F and T disjoint; no chains; keys in >= 2 records covered".format(
            len(thes), len(F)),
        ("F&T {}; chains {}; bad keep {}; variants not in E1 {}; uncovered multi-record keys {} of {}; "
         "T3a in F {}; other rules {}; records-column mismatches {}").format(
            len(f_and_t), len(chains), len(keep_bad), len(var_missing), len(multi_missing), len(multi_keys),
            len(t3a_in_F), len(other_rule), len(rec_col_bad)),
        ok)
    extra_c07 = (len(var_not_norm), ambiguous_nc, dup_var)

    # ------------------------------------------------------------ C08
    EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    ORCID = re.compile(r"\b(?:0000|0009)-\d{4}-\d{4}-\d{3}[\dX]\b")
    SURN = re.compile(r"\b[A-Z][a-z'-]+, (?:[A-Z]\.){1,3}")
    DIGITS = re.compile(r"\b\d{10,11}\b")
    BAD_HEAD = {"authors", "author full names", "author(s) id", "authors with affiliations",
                "correspondence address"}
    hits = Counter()
    hit_where = []
    files = sorted(os.path.join(TAB, f) for f in os.listdir(TAB)
                   if os.path.isfile(os.path.join(TAB, f)))
    files += sorted(os.path.join(FIG, f) for f in os.listdir(FIG)
                    if f.lower().endswith(".csv") and os.path.isfile(os.path.join(FIG, f)))
    n_units = 0

    def scan_unit(text, fname, is_header):
        nonlocal n_units
        n_units += 1
        if EMAIL.search(text):
            hits["email"] += 1
            hit_where.append((fname, "email"))
        if ORCID.search(text):
            hits["orcid"] += 1
            hit_where.append((fname, "orcid"))
        if SURN.search(text):
            hits["surname"] += 1
            hit_where.append((fname, "surname"))
        if DIGITS.search(text):
            hits["digits"] += 1
            hit_where.append((fname, "digits"))
        if len(text.split()) > 30:
            hits["long"] += 1
            hit_where.append((fname, "long"))
        if is_header and text.strip().lower() in BAD_HEAD:
            hits["header"] += 1
            hit_where.append((fname, "header"))

    for path in files:
        fname = os.path.basename(path)
        if fname.lower().endswith(".csv"):
            with open(path, "r", encoding="utf-8-sig", newline="") as fh:
                for j, row in enumerate(csv.reader(fh)):
                    for cell in row:
                        scan_unit(cell, fname, j == 0)
        else:
            with open(path, "r", encoding="utf-8-sig") as fh:
                lines = fh.read().split("\n")
            for j, line in enumerate(lines):
                s = line.strip()
                if s.startswith("|"):
                    inner = s[1:-1] if s.endswith("|") else s[1:]
                    cells = inner.split("|")
                    nxt = lines[j + 1].strip() if j + 1 < len(lines) else ""
                    is_head = nxt.startswith("|") and set(nxt.replace("|", "").replace(" ", "")) <= set("-:")
                    for cell in cells:
                        scan_unit(cell, fname, is_head)
                elif s:
                    scan_unit(s, fname, False)
            # whole-file pass for e-mail / ORCID shapes split across cells
            with open(path, "r", encoding="utf-8-sig") as fh:
                whole = fh.read()
            if EMAIL.search(whole):
                hits["email_file"] += 1
            if ORCID.search(whole):
                hits["orcid_file"] += 1
    ok = sum(hits.values()) == 0
    if ok:
        rec_txt = ("0 hits in {} cells/lines of {} files; author names cannot reach outputs: labels come "
                   "from Affiliations or thesaurus, Authors loaded as count").format(n_units, len(files))
    else:
        rec_txt = "hits {}; first in {}".format(dict(hits), sorted(set(hit_where))[:3])
    add("C08", "R13 shapes, author headers and cell length over tables/ and figures/*.csv",
        "no e-mail, ORCID, author header, 'Surname, I.', 10-11 digit number, cell > 30 words",
        rec_txt, ok)

    # ------------------------------------------------------------ C09
    fig = read_table(os.path.join(FIG, "Fig_collaboration_type_by_year.csv"))
    t2f = read_table(os.path.join(TAB, "T2f_collaboration_by_year.csv"))
    yrs = read_table(T2B_YEARS)
    fcols = ["year"] + COLLAB + ["total"]
    fig_rows = [tuple(x[c] for c in fcols) for x in fig]
    t2f_rows = [tuple(x[c] for c in fcols) for x in t2f]
    my9 = []
    for y in range(2003, 2026):
        rs = [r for r in records if r["year"] == y]
        cc = Counter(r["collab"] for r in rs)
        my9.append(tuple([str(y)] + [str(cc[k]) for k in COLLAB] + [str(len(rs))]))
    e1_years = [(x["year"], x["E1"]) for x in yrs if x["year"].isdigit()]
    fig_tot = [(x[0], x[4]) for x in fig_rows]
    yr_out = sum(1 for r in records if not (2003 <= r["year"] <= 2025))
    sums_ok = all(int(x[1]) + int(x[2]) + int(x[3]) == int(x[4]) for x in fig_rows)
    ok = fig_rows == t2f_rows and fig_rows == my9 and fig_tot == e1_years and sums_ok and yr_out == 0
    add("C09", "figure CSV vs T2f by year, own recomputation and F13.1 T2b_years E1 column",
        "{} figure rows 2003-2025; totals sum {}".format(len(fig_rows), sum(int(x[4]) for x in fig_rows)),
        "fig = T2f: {}; fig = recomputed: {}; totals = T2b_years E1: {}; segments sum to totals: {}; years outside range {}".format(
            fig_rows == t2f_rows, fig_rows == my9, fig_tot == e1_years, sums_ok, yr_out),
        ok)

    # ------------------------------------------------------------ C10
    t2e = read_table(os.path.join(TAB, "T2e_partner_sources.csv"))
    ecols = ["country", "country_records", "rank", "source_title", "records"]
    exp10 = [tuple(x[c] for c in ecols) for x in t2e]
    my10 = []
    my10_share = []
    for c, n in partner_rank[:5]:
        sc = Counter(r["source"] for r in records if c in r["partners"])
        for j, (s, m) in enumerate(rank_items(sc)[:5]):
            my10.append((c, str(n), str(j + 1), s, str(m)))
            my10_share.append(pct(m, n))
    exp10_share = [x["share_of_country_pct"] for x in t2e]
    ok = exp10 == my10
    if ok:
        rec_txt = "25 rows equal for {}; Ukraine first: CEUR Workshop Proceedings {}; shares equal: {}".format(
            ", ".join(c for c, _ in partner_rank[:5]),
            next(m[4] for m in my10 if m[0] == "Ukraine" and m[2] == "1"), exp10_share == my10_share)
    else:
        diffs = [k + 1 for k in range(max(len(exp10), len(my10)))
                 if k >= len(exp10) or k >= len(my10) or exp10[k] != my10[k]]
        d = diffs[0] - 1
        rec_txt = "{} rows differ; first at row {}: table {} n={} vs mine {} n={}".format(
            len(diffs), d + 1,
            exp10[d][0] + " r" + exp10[d][2] if d < len(exp10) else None, exp10[d][4] if d < len(exp10) else None,
            my10[d][0] + " r" + my10[d][2] if d < len(my10) else None, my10[d][4] if d < len(my10) else None)
    add("C10", "T2e top-5 sources of the five main partner countries (sources, counts, order)",
        "{} rows; Ukraine first source n={}".format(len(exp10), exp10[0][4] if exp10 else None),
        rec_txt, ok)

    # ------------------------------------------------------------ write
    for row in rows_out:
        for cell in row:
            if len(cell.split()) > 30:
                raise SystemExit("output cell longer than 30 words in " + row[0])
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["check_id", "what", "expected_from_tables", "recomputed", "verdict"])
        w.writerows(rows_out)

    for row in rows_out:
        print(row[0], row[4])
    print("info: consistent international definitions:", consistent_intl,
          "| variants not in normal form:", extra_c07[0],
          "| ambiguous normalised canonicals:", extra_c07[1],
          "| duplicate variants:", extra_c07[2],
          "| distinct KZ labels:", len(inst_cnt),
          "| doc types:", sorted(tcnt))


if __name__ == "__main__":
    main()
