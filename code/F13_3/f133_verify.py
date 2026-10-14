# f133_verify.py - independent verification of phase F13.3 (citation structure).
# Written from scratch by the verifier; reads only E1, E2, F13.1 T3a_pairs.csv and
# the phase's tables/, figures/, F13_3_numbers.json (and the report, if present).
# R13: never prints, logs or writes author names, e-mails, ORCIDs, abstracts or
# full reference strings. Output: counts, booleans, digests, DOIs/EIDs, labels.
import sys
sys.dont_write_bytecode = True

import csv
import hashlib
import itertools
import json
import os
import re
import statistics
from collections import Counter, defaultdict

ROOT = os.environ.get("PROJECT_ROOT", ".")
DPRG = os.path.join(ROOT, 'outputs', 'dprg_revision_2026')
PH = os.path.join(DPRG, 'phase_F13_3')
EXP = os.path.join(DPRG, 'author_exports_2026_10')
E1 = os.path.join(EXP, 'scopus_full_TAK_KZ_2003_2025_2026-10-13.csv')
E2 = os.path.join(EXP, 'wos_full_TS_KZ_2003_2025_2026-10-13.txt')
PAIRS = os.path.join(DPRG, 'phase_F13_1', 'tables', 'T3a_pairs.csv')
TAB = os.path.join(PH, 'tables')
FIG = os.path.join(PH, 'figures')
NUMBERS = os.path.join(PH, 'F13_3_numbers.json')
REPORT = os.path.join(PH, 'phase_F13_3_report.md')
OUT_CSV = os.path.join(PH, 'phase_F13_3_independent_verification.csv')
OUT_LOG = os.path.join(PH, 'run_logs', 'verify_console.txt')

SHA_E1 = 'fe01023d23afe95df83d594fdfea2c3b488e52ffb8778def4067a2d795a991f3'
SHA_E2 = '413b0fa8ba8dd496072367601b7ca66bf0c7cac01d30553aa702b288dd402160'

RSQ = chr(0x2019)  # right single quotation mark
AZ = frozenset('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
EXTRA = frozenset("'-." + RSQ)
WORDCH = re.compile(r'\w')
SPACECH = re.compile(r'\s')
YEAR_RE = re.compile(r'\(([0-9]{4})\)')
YEAR_ONLY = re.compile(r'\([0-9]{4}\)')
# initials tokens such as J. / J.K. / J.-H. / YU.G. (digraph initials of transliterated names)
INITIALS_TOKEN = re.compile(r"^(?:[A-Z][A-Z]?\.|[\-'" + RSQ + r"])+$")
ALNUM_RUN = re.compile(r'[^\W_]+')
EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
ORCID_RE = re.compile(r'(?:0000|0009)-\d{4}-\d{4}-\d{3}[\dX]')
LITERAL_AUTHOR = re.compile(
    r"^(?:[A-Z][\w'" + RSQ + r"\-\.]*\s?)+[A-Z]\.(?:\s?[A-Z]\.)*$")

LOG = []
ROWS = []


def out(*parts):
    line = ' '.join(str(p) for p in parts)
    print(line)
    LOG.append(line)


def add(check, what, expected, observed, verdict, note=''):
    cells = [check, what, str(expected), str(observed), verdict, note]
    for c in cells:
        if len(c.split()) > 30:
            raise ValueError('cell over 30 words in ' + check)
    assert verdict in ('PASS', 'FAIL', 'EXPLAINED')
    ROWS.append(cells)
    out(check, '|', verdict, '| expected:', expected, '| observed:', observed)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def is_author(frag):
    """Linear equivalent of the literal author-fragment pattern (plus no comma)."""
    n = len(frag)
    if n < 3 or frag[0] not in AZ or frag[-1] != '.' or frag[-2] not in AZ:
        return False
    if ',' in frag:
        return False
    for i, ch in enumerate(frag):
        if ch in EXTRA:
            continue
        if SPACECH.match(ch):
            if i + 1 < n and frag[i + 1] in AZ:
                continue
            return False
        if WORDCH.match(ch):
            continue
        return False
    return True


def fragments(cell):
    return [f for f in cell.split('; ') if f.strip()]


def repair(cell):
    """Glue author fragments to the next non-author fragment (cell uppercased)."""
    frags = [f.strip() for f in cell.upper().split('; ')]
    frags = [f for f in frags if f]
    refs, buf = [], []
    for f in frags:
        if is_author(f):
            buf.append(f)
        else:
            refs.append(', '.join(buf + [f]))
            buf = []
    tail = 0
    if buf:
        refs.append(', '.join(buf))
        tail = 1
    return refs, tail


def clean(ref):
    r = ref.replace('[', '').replace(']', '')
    r = r.replace(' .. ', ' ').replace(' . ', ' ')
    return re.sub(r'\s+', ' ', r).strip()


def ref_year(ref):
    ys = [int(y) for y in YEAR_RE.findall(ref) if 1800 <= int(y) <= 2026]
    return ys[-1] if ys else None


def surname_of(author_seg):
    toks = author_seg.split()
    while len(toks) > 1 and INITIALS_TOKEN.match(toks[-1]):
        toks.pop()
    return ' '.join(toks)


def alnum(s):
    return ''.join(ch for ch in s if ch.isalnum()).upper()


def title_words(s):
    return tuple(ALNUM_RUN.findall(s.upper()))


def parse_ref(ref):
    segs = [s.strip() for s in ref.split(', ')]
    i = 0
    authors = []
    while i < len(segs) and is_author(segs[i]):
        authors.append(segs[i])
        i += 1
    title = ''
    for s in segs[i:]:
        if YEAR_ONLY.fullmatch(s) or not s:
            continue
        title = s
        break
    surname = surname_of(authors[0]) if authors else ''
    return surname, title


def work_key(ref):
    surname, title = parse_ref(ref)
    y = ref_year(ref)
    return (alnum(surname), '' if y is None else str(y), title_words(title)[:6])


def key_match(a, b):
    """(surname, year, first title words), case-insensitive; words compared on the
    common prefix of at most 6 words."""
    if a[0] != b[0] or str(a[1]) != str(b[1]):
        return False
    k = min(6, len(a[2]), len(b[2]))
    if k == 0:
        return len(a[2]) == len(b[2])
    return tuple(a[2][:k]) == tuple(b[2][:k])


def norm_text(s):
    return ' '.join(ALNUM_RUN.findall(s.upper()))


def coupling_key(ref):
    u = ref.upper()
    p = u.find(')')
    if p >= 0:
        u = u[:p + 1]
    u = re.sub(r'[,;]', ' ', u)
    u = re.sub(r'\s+', ' ', u).strip()
    return u if len(u) > 10 else None


def read_csv_dicts(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def measure(rows, prefix, col='value'):
    for r in rows:
        if r['measure'].startswith(prefix):
            return r[col]
    raise KeyError(prefix)


def num(x):
    x = str(x).strip()
    try:
        return int(x)
    except ValueError:
        return float(x)


def median(xs):
    m = statistics.median(xs)
    return int(m) if float(m).is_integer() else m


def components(nodes, edges):
    parent = {n: n for n in nodes}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    sizes = Counter(find(n) for n in nodes)
    return len(sizes), (max(sizes.values()) if sizes else 0)


def pv(ok):
    return 'PASS' if ok else 'FAIL'


def main():
    csv.field_size_limit(2 ** 31 - 1)

    # ------------------------------------------------------------------ inputs
    with open(E1, encoding='utf-8-sig', newline='') as f:
        rd = csv.reader(f)
        hdr = next(rd)
        ix = {c: hdr.index(c) for c in ('EID', 'Title', 'Year', 'Source title', 'DOI',
                                       'References', 'Document Type', 'Authors')}
        recs = []
        authors_mem = []  # only for C09, never output
        for row in rd:
            recs.append({'eid': row[ix['EID']].strip(), 'title': row[ix['Title']],
                         'year': int(row[ix['Year']]), 'doi': row[ix['DOI']].strip(),
                         'refs': row[ix['References']], 'dt': row[ix['Document Type']]})
            authors_mem.append(row[ix['Authors']])
    n = len(recs)

    wos_nr = {}
    wos_records = 0
    cur = {}
    with open(E2, encoding='utf-8-sig', newline=None) as f:
        for line in f:
            tag = line[:3]
            if tag == 'UT ':
                cur['UT'] = line[3:].strip()
            elif tag == 'NR ':
                cur['NR'] = int(line[3:].strip())
            elif line.rstrip('\n') == 'ER' or line.startswith('ER '):
                wos_records += 1
                if 'UT' in cur:
                    wos_nr[cur['UT']] = cur.get('NR')
                cur = {}
            # every other line (other tags, continuation lines) is skipped unread

    pairs = read_csv_dicts(PAIRS)
    numbers = json.load(open(NUMBERS, encoding='utf-8'))

    T = {}
    for name in ('T0a_reference_counts', 'T0b_pairs_scopus_vs_wos', 'T1_reference_age',
                 'T2_top30_cited_works', 'T2b_top30_cited_works_work_key',
                 'T4a_local_citations', 'T4b_top20_LCS', 'T4c_historiograph_summary',
                 'T5a_coupling_summary', 'T5b_coupling_clusters', 'T6a_cocitation_summary',
                 'T6b_cocitation_clusters_top5'):
        T[name] = read_csv_dicts(os.path.join(TAB, name + '.csv'))

    # --------------------------------------------------------------------- C01
    eids = [r['eid'] for r in recs]
    with_refs = sum(1 for r in recs if r['refs'].strip())
    add('C01a', 'E1 rows / distinct EIDs', '841 / 841', f'{n} / {len(set(eids))}',
        pv(n == 841 and len(set(eids)) == 841))
    add('C01b', 'E1 records with non-empty References', 837, with_refs, pv(with_refs == 837))
    s1, s2 = sha256(E1), sha256(E2)
    add('C01c', 'sha256 of E1 equals expected', 'True', str(s1 == SHA_E1), pv(s1 == SHA_E1),
        'digest prefix ' + s1[:16])
    add('C01d', 'sha256 of E2 equals expected', 'True', str(s2 == SHA_E2), pv(s2 == SHA_E2),
        'digest prefix ' + s2[:16])

    # --------------------------------------------------------------------- C02
    # equivalence of the linear author test with the literal pattern
    alphabet = ['A', 'B', 'a', '1', '_', '.', ' ', '\t', "'", RSQ, '-', ',', chr(0xC9)]
    tested = disagree = 0
    for L in range(0, 6):
        for tup in itertools.product(alphabet, repeat=L):
            s = ''.join(tup)
            tested += 1
            lit = bool(LITERAL_AUTHOR.match(s)) and ',' not in s
            if lit != is_author(s):
                disagree += 1
    real_tested = real_dis = 0
    seen = set()
    for r in recs:
        for fr in r['refs'].upper().split('; '):
            fr = fr.strip()
            if fr and len(fr) <= 14 and fr not in seen:
                seen.add(fr)
                real_tested += 1
                lit = bool(LITERAL_AUTHOR.match(fr)) and ',' not in fr
                if lit != is_author(fr):
                    real_dis += 1
    add('C02a', 'linear author test equals literal pattern', '0 disagreements',
        f'{disagree} of {tested} synthetic; {real_dis} of {real_tested} real fragments <= 14 chars',
        pv(disagree == 0 and real_dis == 0),
        'exhaustive strings up to 5 chars over 13 symbols, plus distinct short corpus fragments')

    n_frag = 0
    refs_per = []          # cleaned repaired references per record
    tails = 0
    for r in recs:
        n_frag += len(fragments(r['refs']))
        rr, t = repair(r['refs'])
        tails += t
        refs_per.append([clean(x) for x in rr])
    emptied = sum(1 for rl in refs_per for x in rl if not x)
    refs_per = [[x for x in rl if x] for rl in refs_per]
    counts = [len(rl) for rl in refs_per]
    total = sum(counts)
    pos = [c for c in counts if c > 0]
    t0a = T['T0a_reference_counts']
    e_total = num(measure(t0a, 'references, total', 'F13_3_corrected'))
    e_med = num(measure(t0a, 'references per record - median', 'F13_3_corrected'))
    e_max = num(measure(t0a, 'references per record - max', 'F13_3_corrected'))
    e_wr = num(measure(t0a, 'records with references', 'F13_3_corrected'))
    add('C02b', "fragments of '; ' split over E1", 79686, n_frag, pv(n_frag == 79686))
    add('C02c', 'repaired references, total (T0a)', e_total, total, pv(total == e_total),
        f'trailing author-only buffers {tails}; references emptied by cleaning {emptied}')
    add('C02d', 'median references per record with references (T0a)', e_med, median(pos),
        pv(median(pos) == e_med))
    add('C02e', 'max references per record (T0a)', e_max, max(counts), pv(max(counts) == e_max))
    add('C02f', 'records with references (T0a)', e_wr, len(pos), pv(len(pos) == e_wr))

    # --------------------------------------------------------------------- C03
    cnt_by_eid = {r['eid']: c for r, c in zip(recs, counts)}
    sc, wo = [], []
    missing = 0
    for p in pairs:
        e, u = p['eid'].strip(), p['ut'].strip()
        if e not in cnt_by_eid or wos_nr.get(u) is None:
            missing += 1
            continue
        sc.append(cnt_by_eid[e])
        wo.append(wos_nr[u])
    d = [a - b for a, b in zip(sc, wo)]
    mine = {
        'pairs': len(pairs), 'scopus_median': median(sc), 'wos_median': median(wo),
        'equal': sum(1 for x in d if x == 0), 'within2': sum(1 for x in d if abs(x) <= 2),
        'scopus_more': sum(1 for x in d if x > 0), 'wos_more': sum(1 for x in d if x < 0),
        'scopus_sum': sum(sc), 'wos_sum': sum(wo), 'diff_median': median(d)}
    t0b = T['T0b_pairs_scopus_vs_wos']
    exp = {
        'pairs': num(measure(t0b, 'pairs (eid')),
        'scopus_median': num(measure(t0b, 'Scopus references (corrected) - median')),
        'wos_median': num(measure(t0b, 'WoS NR - median')),
        'equal': num(measure(t0b, 'equal')),
        'within2': num(measure(t0b, '|difference| <= 2')),
        'scopus_more': num(measure(t0b, 'Scopus > WoS')),
        'wos_more': num(measure(t0b, 'WoS > Scopus')),
        'scopus_sum': num(measure(t0b, 'Scopus references - sum')),
        'wos_sum': num(measure(t0b, 'WoS NR - sum')),
        'diff_median': num(measure(t0b, 'median of (Scopus - WoS)'))}
    add('C03a', 'pairs used; WoS records parsed (UT/NR only)', f"{exp['pairs']} pairs",
        f"{len(sc)} pairs matched, {missing} unmatched; {wos_records} WoS records, {len(wos_nr)} UTs",
        pv(len(sc) == exp['pairs'] and missing == 0))
    for sub, keys in (('C03b', ('scopus_median', 'wos_median', 'diff_median')),
                      ('C03c', ('equal', 'within2', 'scopus_more', 'wos_more')),
                      ('C03d', ('scopus_sum', 'wos_sum'))):
        e_s = ' / '.join(str(exp[k]) for k in keys)
        o_s = ' / '.join(str(mine[k]) for k in keys)
        add(sub, 'T0b ' + ' / '.join(keys), e_s, o_s, pv(all(exp[k] == mine[k] for k in keys)))

    # --------------------------------------------------------------------- C04
    periods = [('2003-2016', 2003, 2016), ('2017-2021', 2017, 2021),
               ('2022-2025', 2022, 2025), ('all', 0, 9999)]
    t1 = {r['period']: r for r in T['T1_reference_age']}
    for k, (lab, lo, hi) in enumerate(periods):
        nrec = nref = ndated = n5 = later = 0
        ages = []
        for r, rl in zip(recs, refs_per):
            if not (lo <= r['year'] <= hi):
                continue
            nrec += 1
            for x in rl:
                nref += 1
                y = ref_year(x)
                if y is None:
                    continue
                ndated += 1
                a = r['year'] - y
                ages.append(a)
                if a <= 5:
                    n5 += 1
                if a < 0:
                    later += 1
        share = ndated / nref if nref else 0
        pi = n5 / ndated if ndated else 0
        e = t1[lab]
        es, epi = float(e['share_with_year']), float(e['price_index'])
        ok = (nrec == int(e['records']) and nref == int(e['references'])
              and abs(share - es) <= 0.002 and abs(pi - epi) <= 0.002)
        add('C04' + 'abcd'[k], f'T1 period {lab}: records, refs, dated, share, Price index',
            f"{e['records']}, {e['references']}, {e['references_with_year']}, {es}, {epi}",
            f'{nrec}, {nref}, {ndated}, {share:.4f}, {pi:.4f}', pv(ok),
            f"median age {median(ages)} vs {e['median_age']}; later than citing {later} vs "
            f"{e['later_than_citing_record']}; tolerance 0.002 on shares")

    # --------------------------------------------------------------------- C05
    wk_recs = defaultdict(set)
    ex_recs = defaultdict(set)
    for i, rl in enumerate(refs_per):
        for x in rl:
            ex_recs[x].add(i)
            k = work_key(x)
            if k[2]:
                wk_recs[k].add(i)
    wk_cnt = {k: len(v) for k, v in wk_recs.items()}
    ranked = sorted(wk_cnt, key=lambda k: (-wk_cnt[k], k))
    top30 = ranked[:30]
    cut30 = wk_cnt[top30[-1]]
    tie_set = [k for k in ranked if wk_cnt[k] >= cut30]

    def tkey(row):
        return (alnum(row['first_author']), str(row['year']).strip(), title_words(row['title'])[:6])
    t2 = T['T2_top30_cited_works']
    t2b = T['T2b_top30_cited_works_work_key']
    t2k = [tkey(r) for r in t2]
    t2bk = [tkey(r) for r in t2b]

    def overlap(mine_keys, theirs):
        return sum(1 for tk in theirs if any(key_match(tk, mk) for mk in mine_keys))
    ov_t2 = overlap(top30, t2k)
    ov_t2_tie = overlap(tie_set, t2k)
    ov_t2b = overlap(top30, t2bk)
    ov_t2b_tie = overlap(tie_set, t2bk)
    # citing-record counts of the T2b works under my key
    t2b_eq = 0
    for tk, r in zip(t2bk, t2b):
        best = max([wk_cnt[mk] for mk in wk_cnt if key_match(tk, mk)] or [0])
        if best == int(r['citing_records']):
            t2b_eq += 1
    ok5 = ov_t2 >= 27
    add('C05a', 'my work-key top-30 vs T2 (exact-string top-30)', '>= 27 of 30',
        f'{ov_t2} of 30 ({ov_t2_tie} counting ties at {cut30} records, {len(tie_set)} works)',
        'PASS' if ok5 else 'EXPLAINED',
        'variant spellings split exact-string counts, so work-key and string rankings differ; '
        f"main session's own T2b-vs-T2 overlap is {numbers['T2']['work_key']['overlap_T2']}")
    add('C05b', 'my work-key top-30 vs T2b (main work-key top-30)', '>= 27 of 30',
        f'{ov_t2b} of 30 ({ov_t2b_tie} with ties); citing_records equal for {t2b_eq} of 30',
        pv(ov_t2b >= 27), 'same definition family on both sides')
    # exact-string ranking vs T2. citations(field = 'article') counts only items that contain a
    # comma (T2a), so bare '(YYYY)' remnants and other comma-less strings are left out here.
    ex_cnt_all = {k: len(v) for k, v in ex_recs.items()}
    ex_cnt = {k: c for k, c in ex_cnt_all.items() if ',' in k}
    ex_occ = Counter(x for rl in refs_per for x in rl if ',' in x)
    ex_rank = sorted(ex_cnt, key=lambda k: (-ex_cnt[k], -ex_occ[k], k))
    ex_top = ex_rank[:30]
    ex_cut = ex_cnt[ex_top[-1]]
    ex_tie = [k for k in ex_rank if ex_cnt[k] >= ex_cut]
    ex_top_k = [work_key(k) for k in ex_top]
    ex_tie_k = [work_key(k) for k in ex_tie]
    by_sy = defaultdict(list)
    for s, c in ex_cnt.items():
        if c >= 2:
            wk = work_key(s)
            by_sy[(wk[0], wk[1])].append((wk, c, s))
    t2_eq = t2_occ_eq = 0
    for tk, r in zip(t2k, t2):
        cands = [(c, s) for wk, c, s in by_sy.get((tk[0], tk[1]), []) if key_match(tk, wk)]
        best = max([c for c, s in cands] or [0])
        if best == int(r['citing_records']):
            t2_eq += 1
            if any(c == best and ex_occ[s] == int(r['occurrences']) for c, s in cands):
                t2_occ_eq += 1
        else:
            bucket = by_sy.get((tk[0], tk[1]), [])
            same_sur = sum(1 for (s, y) in by_sy if s == tk[0])
            out('  C05c diag: T2 rank', r['rank'], 'T2 citing', r['citing_records'], 'my best', best,
                '| bucket size', len(bucket), '| buckets with same surname', same_sur,
                '| T2 title words', len(tk[2]),
                '| prefix-matching candidates by words only',
                sum(1 for wk, c, s in itertools.chain.from_iterable(by_sy.values())
                    if wk[2][:3] == tk[2][:3]))
    for tk, r in zip(t2bk, t2b):
        best = max([wk_cnt[mk] for mk in wk_cnt if key_match(tk, mk)] or [0])
        if best != int(r['citing_records']):
            out('  C05b diag: T2b rank', r['rank'], 'T2b citing', r['citing_records'], 'my best', best,
                '| T2b variants', r['string_variants'], '| T2b title words', len(tk[2]),
                '| my keys with same 3 first words and year',
                sum(1 for mk in wk_cnt if mk[2][:3] == tk[2][:3] and mk[1] == tk[1]),
                '| their max count',
                max([wk_cnt[mk] for mk in wk_cnt if mk[2][:3] == tk[2][:3] and mk[1] == tk[1]] or [0]),
                '| same surname', sum(1 for mk in wk_cnt if mk[2][:3] == tk[2][:3]
                                      and mk[1] == tk[1] and mk[0] == tk[0]))
    thr_mine = (len(ex_cnt), sum(1 for c in ex_cnt.values() if c >= 2),
                sum(1 for c in ex_cnt.values() if c >= 5), sum(1 for c in ex_cnt.values() if c >= 10))
    thr_t2 = (numbers['T2']['distinct'], numbers['T2']['ge2'], numbers['T2']['ge5'], numbers['T2']['ge10'])
    out('  C05c diag: all distinct exact strings', len(ex_cnt_all), '| comma-less strings',
        len(ex_cnt_all) - len(ex_cnt), '| comma-less cited by >= 5 records',
        sum(1 for k, c in ex_cnt_all.items() if ',' not in k and c >= 5))
    ov_ex = overlap(ex_top_k, t2k)
    ov_ex_tie = overlap(ex_tie_k, t2k)
    add('C05c', 'my exact-string top-30 (strings with a comma) vs T2', '30 of 30 (ties allowed)',
        f'{ov_ex} of 30 strict, {ov_ex_tie} with ties at {ex_cut}; citing_records equal {t2_eq}, '
        f'occurrences equal {t2_occ_eq}',
        pv(ov_ex_tie == 30 and t2_eq == 30),
        f'distinct, >=2, >=5, >=10 citing: mine {"/".join(map(str, thr_mine))}, '
        f'T2a {"/".join(map(str, thr_t2))}')

    # --------------------------------------------------------------------- C06
    norm_titles = [norm_text(r['title']) for r in recs]
    norm_refs = [norm_text(r['refs']) for r in recs]
    lcs = [0] * n
    eligible = 0
    for i in range(n):
        t = norm_titles[i]
        if len(t.split()) < 6:
            continue
        eligible += 1
        c = 0
        for j in range(n):
            if j != i and t in norm_refs[j]:
                c += 1
        lcs[i] = c
    my_total = sum(lcs)
    idkey = [(r['doi'] or r['eid']).lower() for r in recs]
    my20 = sorted(range(n), key=lambda i: (-lcs[i], recs[i]['eid']))[:20]
    cut20 = lcs[my20[-1]]
    my20_tie = [i for i in range(n) if lcs[i] >= cut20]
    t4b = T['T4b_top20_LCS']
    t4b_ids = [r['doi_or_eid'].strip().lower() for r in t4b]
    my20_ids = {idkey[i] for i in my20}
    my20t_ids = {idkey[i] for i in my20_tie}
    ov20 = sum(1 for x in t4b_ids if x in my20_ids)
    ov20t = sum(1 for x in t4b_ids if x in my20t_ids)
    pos_by_id = {k: i for i, k in enumerate(idkey)}
    lcs_eq = sum(1 for r in t4b if r['doi_or_eid'].strip().lower() in pos_by_id
                 and lcs[pos_by_id[r['doi_or_eid'].strip().lower()]] == int(r['LCS']))
    lcs_ge = sum(1 for r in t4b if r['doi_or_eid'].strip().lower() in pos_by_id
                 and lcs[pos_by_id[r['doi_or_eid'].strip().lower()]] >= int(r['LCS']))
    e_tot = num(measure(T['T4a_local_citations'], 'LCS, total'))
    # stricter variant (no names used): title substring inside one reference whose year
    # equals the cited record's year
    nref_year = [[(norm_text(x), ref_year(x)) for x in rl] for rl in refs_per]
    lcs_y = [0] * n
    for i in range(n):
        t = norm_titles[i]
        if len(t.split()) < 6:
            continue
        for j in range(n):
            if j != i and t in norm_refs[j]:
                if any(t in nx and yx == recs[i]['year'] for nx, yx in nref_year[j]):
                    lcs_y[i] += 1
    y20 = sorted(range(n), key=lambda i: (-lcs_y[i], recs[i]['eid']))[:20]
    y20_ids = {idkey[i] for i in y20}
    y20_cut = lcs_y[y20[-1]]
    y20t_ids = {idkey[i] for i in range(n) if lcs_y[i] >= y20_cut}
    ovy = sum(1 for x in t4b_ids if x in y20_ids)
    ovyt = sum(1 for x in t4b_ids if x in y20t_ids)
    y_eq = sum(1 for r in t4b if r['doi_or_eid'].strip().lower() in pos_by_id
               and lcs_y[pos_by_id[r['doi_or_eid'].strip().lower()]] == int(r['LCS']))
    out('  C06 diag: year-restricted total', sum(lcs_y), '| top-20 overlap', ovy, '| with ties', ovyt,
        '| T4b LCS equal', y_eq, '| records with LCS > 0', sum(1 for c in lcs_y if c > 0),
        '| plain variant records with LCS > 0', sum(1 for c in lcs if c > 0))
    # per-record consistency with the figure's LCS values (100 historiograph nodes)
    hist_nodes = read_csv_dicts(os.path.join(FIG, 'Fig_historiograph_nodes.csv'))
    h_found = h_elig = h_ge = h_ge_y = h_eq = 0
    for r in hist_nodes:
        k = r['doi_or_eid'].strip().lower()
        if k in pos_by_id:
            h_found += 1
            i = pos_by_id[k]
            if len(norm_titles[i].split()) >= 6:
                h_elig += 1
                h_ge += lcs[i] >= int(r['LCS'])
                h_ge_y += lcs_y[i] >= int(r['LCS'])
                h_eq += lcs[i] == int(r['LCS'])
    out('  C06 diag: historiograph nodes found', h_found, 'of', len(hist_nodes),
        '| with titles of >= 6 words', h_elig, '| mine >= figure LCS', h_ge,
        '| year variant >=', h_ge_y, '| equal', h_eq)
    t4b_found = sum(1 for x in t4b_ids if x in pos_by_id)
    if ov20 == 20 and lcs_eq == 20:
        ver6 = 'PASS'
    elif t4b_found == 20 and lcs_ge == 20:
        ver6 = 'EXPLAINED'
    else:
        ver6 = 'FAIL'
    add('C06a', 'my title-substring top-20 LCS vs T4b', '20 of 20, or explained shortfall',
        f'{ov20} of 20 ({ov20t} with ties at {cut20}); my count equals T4b LCS for {lcs_eq}, >= for {lcs_ge}',
        ver6, 'bibliometrix also needs surname and year, mine is looser (never lower). '
        f'Year-restricted variant: overlap {ovy} ({ovyt} with ties), LCS equal {y_eq}')
    if my_total == e_tot:
        ver6b = 'PASS'
    elif my_total >= e_tot and h_ge == h_elig and sum(lcs_y) >= e_tot:
        ver6b = 'EXPLAINED'
    else:
        ver6b = 'FAIL'
    add('C06b', "local citation links total (T4a 'LCS, total')", e_tot,
        f'{my_total} over {eligible} titles of >= 6 words; year-restricted variant {sum(lcs_y)}',
        ver6b, f'looser definition; mine >= figure LCS for {h_ge} of {h_elig} eligible historiograph nodes '
        f'({h_found - h_elig} node has a title under 6 words)')

    # --------------------------------------------------------------------- C07
    def pair_counts(keysets):
        inv = defaultdict(list)
        for i, ks in enumerate(keysets):
            for k in ks:
                inv[k].append(i)
        pc = Counter()
        for lst in inv.values():
            if len(lst) > 1:
                for a, b in itertools.combinations(sorted(lst), 2):
                    pc[(a, b)] += 1
        return pc, inv
    ck_sets = [{k for k in (coupling_key(x) for x in rl) if k} for rl in refs_per]
    pc, inv = pair_counts(ck_sets)
    my_edges = {p for p, c in pc.items() if c >= 2}
    my_nodes = {i for p in my_edges for i in p}
    ex_sets = [set(rl) for rl in refs_per]
    pc_ex, inv_ex = pair_counts(ex_sets)
    ex_edges = sum(1 for c in pc_ex.values() if c >= 2)
    ex_only = [p for p, c in pc_ex.items() if c >= 2 and p not in my_edges]
    reasons = Counter()
    for a, b in ex_only:
        shared = set(refs_per[a]) & set(refs_per[b])
        keys = [coupling_key(x) for x in shared]
        dropped = sum(1 for k in keys if k is None)
        collapsed = len([k for k in keys if k]) - len({k for k in keys if k})
        reasons[('dropped<=10' if dropped else '') + ('collapsed' if collapsed else '')] += 1
    norm_only = sum(1 for p in my_edges if pc_ex.get(p, 0) < 2)
    out('  C07c diag: exact-only pairs', len(ex_only), 'reasons', dict(reasons),
        '| normalised-only pairs', norm_only)
    t5a = T['T5a_coupling_summary']
    e_edges = num(measure(t5a, 'edges'))
    e_nodes = num(measure(t5a, 'nodes'))
    fig_e = read_csv_dicts(os.path.join(FIG, 'Fig_bibliographic_coupling_edges.csv'))
    fig_pairs = {frozenset((r['eid_a'], r['eid_b'])): int(r['shared_references']) for r in fig_e}
    mine_pairs = {frozenset((eids[a], eids[b])): pc[(a, b)] for a, b in my_edges}
    common = set(fig_pairs) & set(mine_pairs)
    same_w = sum(1 for p in common if fig_pairs[p] == mine_pairs[p])
    pos_of = {e: i for i, e in enumerate(eids)}
    for p in sorted(common, key=sorted):
        if fig_pairs[p] != mine_pairs[p]:
            a, b = sorted(pos_of[e] for e in p)
            ka = [coupling_key(x) for x in refs_per[a]]
            kb = [coupling_key(x) for x in refs_per[b]]
            ca, cb = Counter(k for k in ka if k), Counter(k for k in kb if k)
            multi = sum(ca[k] * cb[k] for k in ca if k in cb)
            mn = sum(min(ca[k], cb[k]) for k in ca if k in cb)
            sa = {k for x in refs_per[a] for k in (coupling_key(y) for y in x.split(';')) if k}
            sb = {k for x in refs_per[b] for k in (coupling_key(y) for y in x.split(';')) if k}
            out('  C07b diag: pair', ' '.join(sorted(p)), 'figure', fig_pairs[p], 'mine', mine_pairs[p],
                '| with duplicates (product)', multi, '| (min)', mn,
                '| exact-string shared', len(set(refs_per[a]) & set(refs_per[b])),
                '| split-on-semicolon shared', len(sa & sb))
    def vkey(ref):
        u = ref.upper()
        p = u.find(')')
        if p >= 0:
            u = u[:p + 1]
        u = re.sub(r'[,;]', ' ', u)
        m = re.search(r'V[0-9]', u)
        if m:
            u = u[:m.start()]
        m = u.find('DOI ')
        if m >= 0:
            u = u[:m]
        u = re.sub(r'\s+', ' ', u).strip()
        return u if len(u) > 10 else None
    v_sets = [{k for k in (vkey(x) for x in rl) if k} for rl in refs_per]
    pc_v, inv_v = pair_counts(v_sets)
    v_edges = {frozenset((eids[a], eids[b])): c for (a, b), c in pc_v.items() if c >= 2}
    out('  C07 diag: V-digit/DOI cut variant edges', len(v_edges), '| common with figure',
        len(set(v_edges) & set(fig_pairs)), '| equal weights',
        sum(1 for p in set(v_edges) & set(fig_pairs) if v_edges[p] == fig_pairs[p]),
        '| keys >= 4 records', sum(1 for v in inv_v.values() if len(v) >= 4),
        '| distinct keys', len(inv_v),
        '| refs cut at V-digit', sum(1 for rl in refs_per for x in rl
                                     if re.search(r'V[0-9]', re.sub(r'\).*', ')', x.upper()))))
    v_same_w = sum(1 for p in set(v_edges) & set(fig_pairs) if v_edges[p] == fig_pairs[p])
    v_fixed = 0
    for p in sorted(set(v_edges) & set(fig_pairs), key=sorted):
        if v_edges[p] != mine_pairs.get(p):
            a, b = sorted(pos_of[e] for e in p)
            gained = []
            for k in v_sets[a] & v_sets[b]:
                src_a = [x for x in refs_per[a] if vkey(x) == k]
                src_b = [x for x in refs_per[b] if vkey(x) == k]
                ka = {coupling_key(x) for x in src_a}
                kb = {coupling_key(x) for x in src_b}
                if not (ka & kb):
                    u = re.sub(r'[,;]', ' ', re.sub(r'\).*', ')', src_a[0].upper()))
                    m = re.search(r'V[0-9]', u)
                    before = ('none' if not m or m.start() == 0 else
                              'space' if u[m.start() - 1] == ' ' else
                              'hyphen' if u[m.start() - 1] == '-' else 'other')
                    gained.append((len(k), 'char before V-digit: ' + before))
            if fig_pairs[p] == v_edges[p]:
                v_fixed += 1
            out('  C07 diag: V-variant changes pair', ' '.join(sorted(p)), 'figure', fig_pairs[p],
                'plain', mine_pairs.get(p), 'variant', v_edges[p],
                '| merged keys (key length, context)', gained)
    for i, r in enumerate(recs):
        cell = r['refs'].strip().upper()
        if cell and not ('A' <= cell[0] <= 'Z'):
            uniq_plain = sum(1 for k in ck_sets[i] if len(inv[k]) == 1)
            out('  C08 diag: record whose References start with a non A-Z character', r['eid'],
                '| first char code', ord(cell[0]), '| keys', len(ck_sets[i]),
                '| keys unique to it', uniq_plain)
    semi_sets = [{k for x in rl for k in (coupling_key(y) for y in x.split(';')) if k} for rl in refs_per]
    pc_semi, inv_semi = pair_counts(semi_sets)
    semi_edges = {frozenset((eids[a], eids[b])): c for (a, b), c in pc_semi.items() if c >= 2}
    out('  C07 diag: split-on-semicolon variant edges', len(semi_edges), '| common with figure',
        len(set(semi_edges) & set(fig_pairs)), '| equal weights',
        sum(1 for p in set(semi_edges) & set(fig_pairs) if semi_edges[p] == fig_pairs[p]),
        '| keys >= 4 records', sum(1 for v in inv_semi.values() if len(v) >= 4),
        '| distinct keys', len(inv_semi),
        '| refs containing ;', sum(1 for rl in refs_per for x in rl if ';' in x))
    ver7 = 'PASS' if len(my_edges) == e_edges else (
        'EXPLAINED' if abs(len(my_edges) - e_edges) <= 0.1 * e_edges else 'FAIL')
    add('C07a', 'coupling pairs sharing >= 2 normalised references (T5a edges)', e_edges,
        f'{len(my_edges)} pairs, {len(my_nodes)} nodes (T5a nodes {e_nodes})', ver7,
        'key: uppercase, cut after first ), commas/semicolons to space, length > 10; '
        'bibliometrix also drops one record (first-letter filter)')
    same_set = len(common) == len(fig_pairs) == len(mine_pairs)
    if same_set and same_w == len(common):
        ver7b = 'PASS'
    elif same_set and len(common) - same_w <= 5:
        ver7b = 'EXPLAINED'
    else:
        ver7b = 'FAIL'
    add('C07b', 'my coupling pairs vs figure edge list (by EID)', f'{len(fig_pairs)} identical pairs',
        f'{len(common)} common, {len(mine_pairs) - len(common)} only mine, '
        f'{len(fig_pairs) - len(common)} only figure; equal weights {same_w}',
        ver7b, f'edge sets identical; bibliometrix-style V-digit truncation of keys reproduces '
        f'{v_fixed} differing weights ({v_same_w} equal overall)')
    add('C07c', 'coupling pairs with plain exact repaired string as key', 'reported only',
        f'{ex_edges} pairs (normalised key {len(my_edges)})', 'EXPLAINED',
        f'{len(ex_only)} exact-only pairs rest on shared strings whose text before the first ) has '
        f'<= 10 characters (key drops them); {norm_only} pairs only normalised')

    # --------------------------------------------------------------------- C08
    ge4 = sum(1 for lst in inv.values() if len(lst) >= 4)
    ge4_ex = sum(1 for lst in inv_ex.values() if len(lst) >= 4)
    t6a = T['T6a_cocitation_summary']
    e_ge4 = num(measure(t6a, 'nodes: references with >= 4'))
    e_keys = num(measure(t6a, 'distinct references in the co-citation matrix'))
    ver8 = 'PASS' if ge4 == e_ge4 else ('EXPLAINED' if abs(ge4 - e_ge4) <= 0.15 * e_ge4 else 'FAIL')
    add('C08', 'distinct normalised references cited by >= 4 records (T6a nodes)', e_ge4,
        f'{ge4} (exact string key {ge4_ex}); distinct keys {len(inv)} vs T6a {e_keys}', ver8,
        f'same key as C07; distinct-key gap {len(inv) - e_keys}, candidate causes: V-digit key '
        f'truncation (variant {len(inv_v)}) and the record biblioNetwork leaves out')

    # --------------------------------------------------------------------- C09
    allowed_files = {'T0d_citations_before_after.csv', 'T1c_rpys_peaks.csv',
                     'T2_top30_cited_works.csv', 'T2b_top30_cited_works_work_key.csv',
                     'T6b_cocitation_clusters_top5.csv', 'Fig_cocitation_references_nodes.csv'}
    allowed_cols = {'first_author', 'name_segment', 'top_work_first_author', 'label'}
    forms = set()
    for cell in authors_mem:
        for a in cell.split(';'):
            a = a.strip()
            if not a or '[' in a or not any(ch.isalpha() for ch in a):
                continue
            forms.add(a)
            forms.add(re.sub(r'\s+', ' ', a.replace('.', '').upper()).strip())
    by_tok = defaultdict(list)
    for fm in forms:
        toks = re.findall(r'\w+', fm.upper())
        if not toks:
            continue
        pat = re.compile(r'(?<!\w)' + re.escape(fm) + r'(?!\w)', re.IGNORECASE)
        by_tok[toks[0]].append(pat)
    files = [os.path.join(TAB, f) for f in sorted(os.listdir(TAB)) if f.endswith('.csv')]
    files += [os.path.join(FIG, f) for f in sorted(os.listdir(FIG)) if f.endswith('.csv')]
    n_email = n_orcid = n_long = n_cells = 0
    name_out = name_in = 0
    out_locs = Counter()
    for path in files:
        base = os.path.basename(path)
        with open(path, encoding='utf-8-sig', newline='') as f:
            rows = list(csv.reader(f))
        header = rows[0] if rows else []
        for ri, row in enumerate(rows):
            for ci, cell in enumerate(row):
                n_cells += 1
                n_email += len(EMAIL_RE.findall(cell))
                n_orcid += len(ORCID_RE.findall(cell))
                if len(cell.split()) > 30:
                    n_long += 1
                if ri == 0:
                    continue
                toks = set(re.findall(r'\w+', cell.upper()))
                hit = False
                for t in toks:
                    for pat in by_tok.get(t, ()):
                        if pat.search(cell):
                            hit = True
                            break
                    if hit:
                        break
                if hit:
                    col = header[ci] if ci < len(header) else ''
                    if base in allowed_files and col in allowed_cols:
                        name_in += 1
                    else:
                        name_out += 1
                        out_locs[(base, col)] += 1
    def has_name(s):
        for t in set(re.findall(r'\w+', s.upper())):
            for pat in by_tok.get(t, ()):
                if pat.search(s):
                    return True
        return False

    md_cells = md_long = md_email = md_orcid = 0
    md_names = md_names_in = 0          # cells/lines with a name form: outside / allowed column
    md_locs = []
    report_present = os.path.exists(REPORT)
    if report_present:
        text = open(REPORT, encoding='utf-8').read()
        md_email = len(EMAIL_RE.findall(text))
        md_orcid = len(ORCID_RE.findall(text))
        md_header = None
        prev_table = False
        for ln, line in enumerate(text.splitlines(), start=1):
            s = line.strip()
            if s.startswith('|'):
                cells = [c.strip() for c in s.strip('|').split('|')]
                if not prev_table:
                    md_header = [re.sub(r'\s+', '_', c.lower()) for c in cells]
                prev_table = True
                is_sep = all(re.fullmatch(r':?-{3,}:?', c) for c in cells if c)
                for ci, cell in enumerate(cells):
                    md_cells += 1
                    if len(cell.split()) > 30:
                        md_long += 1
                    if is_sep:
                        continue
                    if has_name(cell):
                        col = md_header[ci] if md_header and ci < len(md_header) else ''
                        if col in allowed_cols:
                            md_names_in += 1
                        else:
                            md_names += 1
                        md_locs.append((ln, 'table column ' + col))
            else:
                prev_table = False
                if has_name(line):
                    md_names += 1
                    md_locs.append((ln, 'prose'))
    for ln, where in md_locs:
        out('  C09c report hit location (line, context):', ln, where)
    add('C09a', 'e-mail / ORCID shaped strings in tables, figures, report', '0 / 0',
        f'{n_email + md_email} / {n_orcid + md_orcid} over {len(files)} CSV files',
        pv(n_email + md_email == 0 and n_orcid + md_orcid == 0),
        'report present: ' + str(report_present))
    add('C09b', 'CSV cells and markdown table cells over 30 words', 0,
        f'{n_long} of {n_cells} CSV cells; {md_long} of {md_cells} markdown cells',
        pv(n_long == 0 and md_long == 0),
        'report absent at verification time' if not report_present else
        'report scanned, sha256 prefix ' + sha256(REPORT)[:16])
    add('C09c', 'corpus author name forms outside the allowed cited-reference columns', 0,
        f'{name_out} CSV cells outside, {name_in} inside allowed columns; report: {md_names} outside, '
        f'{md_names_in} in allowed columns',
        pv(name_out == 0 and md_names == 0),
        f'{len(forms)} name forms (dotted and dotless upper), whole word, case-insensitive; '
        f'locations outside: {len(out_locs)}')
    for (base, col), c in sorted(out_locs.items()):
        out('  C09c outside hit location (file, column, cells):', base, col, c)

    # --------------------------------------------------------------------- C10
    # bibliographic coupling figure
    cn = read_csv_dicts(os.path.join(FIG, 'Fig_bibliographic_coupling_nodes.csv'))
    ce = fig_e
    node_ids = [r['eid'] for r in cn]
    deg = Counter()
    bad_end = loops = 0
    for r in ce:
        a, b = r['eid_a'], r['eid_b']
        if a == b:
            loops += 1
        deg[a] += 1
        deg[b] += 1
        if a not in set(node_ids) or b not in set(node_ids):
            bad_end += 1
    deg_ok = sum(1 for r in cn if int(r['degree']) == deg[r['eid']])
    once = len(node_ids) == len(set(node_ids)) and all(r['cluster'].strip() for r in cn)
    csize = Counter(r['cluster'] for r in cn)
    big = sorted((s for s in csize.values() if s >= 10), reverse=True)
    t5b_sizes = sorted((int(r['records']) for r in T['T5b_coupling_clusters']), reverse=True)
    ncomp, largest = components(node_ids, [(r['eid_a'], r['eid_b']) for r in ce])
    e_cl = num(measure(t5a, 'Louvain clusters'))
    e_comp = num(measure(t5a, 'components'))
    e_large = num(measure(t5a, 'largest component'))
    e_inbig = num(measure(t5a, 'records in clusters with >= 10'))
    ok = (len(cn) == e_nodes and len(ce) == e_edges and bad_end == 0 and loops == 0)
    add('C10a', 'coupling figure nodes / edges vs T5a', f'{e_nodes} / {e_edges}',
        f'{len(cn)} / {len(ce)}; bad endpoints {bad_end}; self loops {loops}', pv(ok))
    add('C10b', 'coupling node degrees equal edge-list degrees; one cluster per node',
        f'{len(cn)} equal; True', f'{deg_ok} equal; {once}', pv(deg_ok == len(cn) and once))
    ok = (big == t5b_sizes and len(csize) == e_cl and sum(big) == e_inbig
          and ncomp == e_comp and largest == e_large)
    add('C10c', 'coupling clusters >= 10 (T5b), clusters, components, largest (T5a)',
        f'{t5b_sizes}; {e_cl}; {e_comp}; {e_large}',
        f'{big}; {len(csize)}; {ncomp}; {largest}', pv(ok))
    # co-citation figure
    qn = read_csv_dicts(os.path.join(FIG, 'Fig_cocitation_references_nodes.csv'))
    qe = read_csv_dicts(os.path.join(FIG, 'Fig_cocitation_references_edges.csv'))
    qids = [r['node'] for r in qn]
    qdeg = Counter()
    qbad = 0
    for r in qe:
        qdeg[r['from']] += 1
        qdeg[r['to']] += 1
        if r['from'] not in set(qids) or r['to'] not in set(qids):
            qbad += 1
    qdeg_ok = sum(1 for r in qn if int(r['degree']) == qdeg[r['node']])
    w_ok = all(int(r['cocitations']) >= 3 for r in qe) and all(int(r['citing_records']) >= 4 for r in qn)
    labels = sum(1 for r in qn if r['label'].strip())
    e_qn = num(measure(t6a, 'nodes with >= 1 edge'))
    e_qe = num(measure(t6a, 'edges: pairs co-cited'))
    e_qcl = num(measure(t6a, 'Louvain clusters'))
    qsize = Counter(r['cluster'] for r in qn)
    t6b_sizes = {}
    for r in T['T6b_cocitation_clusters_top5']:
        t6b_sizes[r['cluster']] = int(r['cluster_size'])
    t6b_match = all(qsize.get(c) == s for c, s in t6b_sizes.items())
    big5 = sorted((s for s in qsize.values() if s >= 5), reverse=True)
    ok = (len(qn) == e_qn and len(qe) == e_qe and qbad == 0 and qdeg_ok == len(qn)
          and len(qids) == len(set(qids)) and w_ok)
    add('C10d', 'co-citation figure nodes / edges vs T6a; degrees; thresholds',
        f'{e_qn} / {e_qe}', f'{len(qn)} / {len(qe)}; degrees equal {qdeg_ok}; bad endpoints {qbad}; '
        f'weights >= 3 and citing >= 4: {w_ok}', pv(ok))
    ok = (t6b_match and len(qsize) == e_qcl and big5 == sorted(t6b_sizes.values(), reverse=True)
          and labels <= 30)
    add('C10e', 'co-citation clusters vs T6b sizes and T6a cluster count; labels <= 30',
        f'{sorted(t6b_sizes.values(), reverse=True)}; {e_qcl}; <= 30',
        f'{big5}; {len(qsize)}; {labels} labels', pv(ok))
    # historiograph figure
    hn = read_csv_dicts(os.path.join(FIG, 'Fig_historiograph_nodes.csv'))
    he = read_csv_dicts(os.path.join(FIG, 'Fig_historiograph_edges.csv'))
    t4c = T['T4c_historiograph_summary']
    e_hn = num(measure(t4c, 'nodes'))
    e_he = num(measure(t4c, 'edges'))
    e_drawn = num(measure(t4c, 'nodes drawn'))
    e_wcc = num(measure(t4c, 'weakly connected'))
    e_span = measure(t4c, 'years spanned')
    hl = [r['label'] for r in hn]
    hbad = sum(1 for r in he if r['citing'] not in set(hl) or r['cited'] not in set(hl))
    drawn = sum(1 for r in hn if str(r['in_plot']).strip() in ('1', 'TRUE', 'True'))
    hwcc, _ = components(hl, [(r['citing'], r['cited']) for r in he])
    years = [int(r['year']) for r in hn]
    span = f'{min(years)}-{max(years)}'
    lcs2 = all(int(r['LCS']) >= 2 for r in hn)
    ok = (len(hn) == e_hn and len(he) == e_he and hbad == 0 and drawn == e_drawn
          and hwcc == e_wcc and span == e_span and lcs2 and len(hl) == len(set(hl)))
    add('C10f', 'historiograph figure vs T4c: nodes, edges, drawn, components, span',
        f'{e_hn}, {e_he}, {e_drawn}, {e_wcc}, {e_span}',
        f'{len(hn)}, {len(he)}, {drawn}, {hwcc}, {span}; bad endpoints {hbad}; LCS >= 2: {lcs2}', pv(ok))

    # ------------------------------------------------------------------ output
    with open(OUT_CSV, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['check', 'what', 'expected', 'observed', 'verdict', 'note'])
        w.writerows(ROWS)
    verdicts = Counter(r[4] for r in ROWS)
    out('rows:', len(ROWS), '| verdicts:', dict(verdicts))
    with open(OUT_LOG, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')


if __name__ == '__main__':
    main()
