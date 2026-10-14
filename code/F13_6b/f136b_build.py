"""Phase F13.6b - steps 1-5: the outline (S0), the draft draft/main_v2.qmd, the evidence index (E1_evidence_index), the coverage of the
F13.6a map (S2), the marks (S3), the derived numbers (S4), word counts and citation keys (S5) and the citations needed (S6).

Sections 2-3 come from programs/f136b_template_sections_2_3.md, whose numbers are all placeholders: v (a table cell), j (a value of a
numbers file), n (a count of table rows), s (a derived number of S4), c (a text that stands in a table cell), x (an external source:
README_exports.txt or references.bib, checked by a pattern), t (a count or constant of the text), m (a mark), and the shorthands D
(retrieval date), P / P2 (period labels) and Y (year labels). The program renders them, records where each lands in the draft and
reads the draft's numeric tokens back with the F13.6a extraction rule. Everything else of main.qmd is copied verbatim, with the
part-2 marks after the claims that F13.6a's N2 removes."""
import sys
sys.dont_write_bytecode = True

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f136b_lib as L

TEMPLATE = L.HERE / "f136b_template_sections_2_3.md"
PH = re.compile(r"\{\{(.*?)\}\}")
README_DATE = r"Date of retrieval: 2026-10-13"
FORBIDDEN_TEXT = [("Iceberg", r"Iceberg"), ("1.97", r"1\.97"), ("superset", r"superset|надмножеств"),
                  ("September 2026 snapshot", r"September 2026 snapshot"), ("rule (e)", r"rule \(e\)"), ("L1", r"\bL1\b"),
                  ("enrichment layer", r"enrichment layer"), ("79,686", r"79,?686"), ("1.9 times", r"1\.9 times"),
                  ("Scientific Journal of Astana IT University", r"Scientific Journal of Astana IT University"),
                  ("layer terms (frame, snapshot, enrichment)", r"\bframe\b|\bsnapshot\b|\benrichment\b")]


# ---------------------------------------------------------------- S4 derived numbers
def loglin(years, ys):
    xs = [y - years[0] for y in years]
    ls = [math.log(v) for v in ys]
    n = len(xs)
    mx, ml = sum(xs) / n, sum(ls) / n
    b = sum((x - mx) * (l - ml) for x, l in zip(xs, ls)) / sum((x - mx) ** 2 for x in xs)
    a = ml - b * mx
    return a, b


def derived():
    t2a = L.read_csv(L.alias_path("F13_4/T2a_normalised_by_year"))
    yrs = list(range(2011, 2026))
    col = {c: [float(next(r[c] for r in t2a if r["year"] == str(y))) for y in yrs] for c in ("topic_KZ", "all_KZ", "topic_world", "all_world")}
    out = {}
    for key, c, what in (("KZTOPIC", "topic_KZ", "Kazakhstan's cybersecurity records (check against F13.4 T1c)"),
                         ("KZALL", "all_KZ", "all Kazakhstan-affiliated Scopus records"),
                         ("WTOPIC", "topic_world", "world cybersecurity records (the query without the country)"),
                         ("WALL", "all_world", "all Scopus records")):
        a, b = loglin(yrs, col[c])
        src = f"phase_F13_4 T2a_normalised_by_year column {c}, years 2011-2025"
        out[key + "_B"] = {"value": b, "formula": "OLS slope b of ln(n_t) on (t - 2011), 2011-2025", "inputs": src, "what": what}
        out[key + "_GROWTH"] = {"value": 100 * (math.exp(b) - 1), "formula": "100 * (exp(b) - 1), b from the OLS fit of ln(n_t) on (t - 2011)",
                                "inputs": src, "what": what + ": annual growth (%)"}
        out[key + "_DOUBLING"] = {"value": math.log(2) / b, "formula": "ln(2) / b", "inputs": src, "what": what + ": doubling time (years)"}
    t1c = next(r for r in L.read_csv(L.alias_path("F13_4/T1c_loglinear_fit")) if r["window"] == "2011-2025")
    assert abs(out["KZTOPIC_B"]["value"] - float(t1c["b"])) < 5e-5 and f"{out['KZTOPIC_GROWTH']['value']:.1f}" == t1c["annual_growth_pct"], "rule differs from F13.4"
    t1d = next(r for r in L.read_csv(L.alias_path("F13_2/T1d_periods")) if r["period"] == "2022-2025")
    out["CONF_2022_2025"] = {"value": 100 * int(t1d["conference paper"]) / int(t1d["records"]),
                             "formula": "100 * conference paper / records", "inputs": "phase_F13_2 T1d_periods [period=2022-2025] conference paper, records",
                             "what": "conference papers among the records of 2022-2025 (%)"}
    a2 = {r["class"]: int(r["records"]) for r in L.read_csv(L.alias_path("F13_2c/T2a_international_by_author"))}
    n = int(L.cell("F13_1/T1a_counts", "file=E1 Scopus full", "records"))
    out["TYPE_I_OF_841"] = {"value": 100 * a2["(i) co-authorship with an author based only abroad"] / n, "formula": "100 * type (i) records / all records",
                            "inputs": "phase_F13_2c T2a_international_by_author [class=(i) ...] records; phase_F13_1 T1a_counts [file=E1 Scopus full] records",
                            "what": "records with an author based only abroad, of all records (%)"}
    return out


# ---------------------------------------------------------------- placeholders
def fmt(value, f):
    f = (f or "").strip()
    suffix = "%" if f.endswith("%") else ""
    f = f[:-1] if suffix else f
    v = str(value).strip()
    if f == "":
        out = v
    elif f == "dash":
        out = v.replace("-", "–")
    elif f == ",":
        out = f"{int(round(float(v))):,}"
    elif re.fullmatch(r"\.\d+f", f):
        out = format(float(v), f)
    else:
        raise ValueError(f)
    return out + suffix


def resolve(spec, S4):
    """-> (rendered text, record) for one placeholder."""
    kind, _, body = spec.partition(":")
    if spec == "D":
        kind, body = "x", f"13 October 2026 ~ {L.README} ~ {README_DATE}"
    elif kind == "P":
        kind, body = "v", f"F13_4/T1b_periods ~ period={body} ~ period ~ dash"
    elif kind == "P2":
        kind, body = "v", f"F13_4/T1c_loglinear_fit ~ window={body} ~ window ~ dash"
    elif kind == "Y":
        kind, body = "v", f"F13_4/T1a_years ~ year={body} ~ year"
    parts = [p.strip() for p in body.split(" ~ ")] if body else []
    if kind == "v":
        alias, where, col = parts[:3]
        val = L.cell(alias, where, col)
        cond = where if where else "-"
        return fmt(val, parts[3] if len(parts) > 3 else ""), {"kind": "table", "source": f"{alias} [{cond}] {col}", "value": val}
    if kind == "j":
        alias, key = parts[:2]
        val = L.jvalue(alias, key)
        return fmt(val, parts[2] if len(parts) > 2 else ""), {"kind": "table", "source": f"{alias} {key}", "value": str(val)}
    if kind == "n":
        alias, where = parts[0], (parts[1] if len(parts) > 1 else "")
        val = len(L.rows_matching(alias, L.parse_where(where)))
        return str(val), {"kind": "formula", "source": f"count of rows of {alias}" + (f" [{where}]" if where else ""), "value": str(val)}
    if kind == "s":
        d = S4[parts[0]]
        return fmt(d["value"], parts[1] if len(parts) > 1 else ""), {"kind": "formula", "source": f"S4 {parts[0]}: {d['formula']}", "value": repr(d["value"])}
    if kind == "c":
        alias, where, col, text = parts[:4]
        cellv = str(L.jvalue(alias, where)) if alias.endswith("/numbers") else L.cell(alias, where, col)
        assert text in cellv, (spec, cellv)
        return text, {"kind": "table", "source": f"{alias} [{where}] {col} (text contains)", "value": cellv, "contains": text}
    if kind == "x":
        text, f, rx = parts[:3]
        m = re.search(rx, L.path(f).read_bytes().decode("utf-8"))
        assert m, (spec,)
        return text, {"kind": "external", "source": f"{f}: '{m.group(0)}'", "value": m.group(0)}
    if kind == "t":
        return parts[0], {"kind": "count-of-text", "source": parts[1], "value": parts[0]}
    if kind == "m":
        if parts[0] == "F13.2d":
            return L.MARK_2D, {"kind": "mark", "source": "F13.2d", "value": ""}
        if parts[0] == "F13.3":
            return L.MARK_F133, {"kind": "count-of-text", "source": "label of the part-2 mark", "value": "2"}
    raise ValueError(spec)


def render(S4):
    lines_out, spans = [], []
    for ln, line in enumerate(TEMPLATE.read_bytes().decode("utf-8").split("\n")):
        out, pos, sp = "", 0, []
        for m in PH.finditer(line):
            out += line[pos:m.start()]
            text, rec = resolve(m.group(1), S4)
            sp.append((len(out), len(out) + len(text), rec))
            out += text
            pos = m.end()
        out += line[pos:]
        assert "{{" not in out and "}}" not in out, (ln, out[:80])
        lines_out.append(out)
        spans.append(sp)
    while lines_out and not lines_out[-1].strip():
        lines_out.pop()
        spans.pop()
    return lines_out, spans


# ---------------------------------------------------------------- the draft
def part2_marks(lines):
    """[[REWRITE IN PART 2]] after every claim that F13.6a's N2 removes, outside the old sections 2-3 (which are replaced)."""
    T = L.f136a()
    n2 = L.read_csv(L.P6A + "tables/N2_claims.csv")
    old_start = next(i for i, s in enumerate(lines, 1) if s.startswith("# Methodology"))
    old_end = next(i for i, s in enumerate(lines, 1) if s.startswith("# Discussion"))
    units = {ln: (sec, text) for ln, sec, text in L.tokens_of(lines)[1]}
    todo = defaultdict(list)
    for r in n2:
        ln = int(r["line"])
        if r["status"] != "remove" or old_start <= ln < old_end:
            continue
        k = int(r["claim_key"].split("s")[-1])
        sec, text = units[ln]
        a, b = T.sentences(text)[k - 1]
        raw = lines[ln - 1]
        offset = raw.index(text) if sec != "Heading" else len(raw) - len(text)
        todo[ln].append((offset + b, r["id"], r["claim_key"], sec))
    marks = []
    out = list(lines)
    for ln, items in todo.items():
        s = out[ln - 1]
        for pos, nid, key, sec in sorted(items, reverse=True):
            s = s[:pos] + " " + L.MARK_P2 + s[pos:]
        out[ln - 1] = s
        marks += [{"mark": L.MARK_P2, "main_qmd_line": ln, "n2_id": nid, "claim_key": key, "section": sec} for pos, nid, key, sec in sorted(items)]
    return out, marks, old_start, old_end


def build_draft(S4):
    main = L.path(L.MAIN).read_bytes().decode("utf-8").split("\n")
    marked, marks, old_start, old_end = part2_marks(main)
    head = marked[:old_start - 1]
    tail = marked[old_end - 1:]
    body, spans = render(S4)
    draft = head + body + [""] + tail
    first_new = len(head) + 1
    span_by_line = {first_new + i: sp for i, sp in enumerate(spans) if sp}
    for m in marks:
        m["draft_line"] = m["main_qmd_line"] if m["main_qmd_line"] < old_start else m["main_qmd_line"] - old_end + first_new + len(body) + 1
    return draft, span_by_line, marks, (first_new, first_new + len(body) - 1), (old_start, old_end)


# ---------------------------------------------------------------- evidence index
def decimals(s):
    s = L.norm_num(s)
    return len(s.split(".")[1]) if "." in s else 0


def match(token, rec):
    if rec["kind"] in ("count-of-text", "mark"):
        return "n/a (text)"
    if rec["kind"] == "external":
        return "yes"
    if "contains" in rec:
        return "yes" if L.norm_num(token) == L.norm_num(rec["contains"]) and rec["contains"] in rec["value"] else "no"
    tok, val = L.norm_num(token), L.norm_num(rec["value"])
    if "-" in tok or "-" in val:
        return "yes" if tok == val else "no"
    try:
        return "yes" if round(float(val), decimals(token)) == float(tok) else "no"
    except ValueError:
        return "no"


def evidence(draft, span_by_line, rng):
    toks, units = L.tokens_of(draft)
    T = L.f136a()
    rows, orphan, bare, heading_digits = [], [], [], []
    used = set()
    for t in toks:
        if not (rng[0] <= t["line"] <= rng[1]):
            continue
        if t["section"] == "Heading":
            heading_digits.append(t["line"])
            continue
        hit = None
        for i, (a, b, rec) in enumerate(span_by_line.get(t["line"], [])):
            if a <= t["start"] < b:
                hit = (i, rec)
                break
        if hit is None:
            bare.append({"line": t["line"], "token": t["token"]})
            continue
        used.add((t["line"], hit[0]))
        rec = hit[1]
        sa, sb = T.sentence_of(t["text"], t["start"])
        rows.append({"id": f"E-{len(rows) + 1:03d}", "section": t["section"], "line": t["line"], "sentence": T.quote(t["text"], t["start"], t["end"]),
                     "number_as_written": t["token"], "kind": rec["kind"], "source": rec["source"], "value_in_source": rec["value"],
                     "match": match(t["token"], rec), "mark": "F13.2d" if L.MARK_2D in t["text"][sa:sb + len(L.MARK_2D) + 2] else ""})
    for ln, sp in span_by_line.items():
        for i, (a, b, rec) in enumerate(sp):
            if (ln, i) not in used and rec["kind"] != "mark":
                orphan.append({"line": ln, "source": rec["source"]})
    return rows, bare, orphan, heading_digits


# ---------------------------------------------------------------- word counts and citations
CITE = re.compile(r"\[@([^\]]+)\]")


def words_of(lines):
    prose = tables = code = 0
    for s in lines:
        if s.startswith("#"):
            prose += len(s.lstrip("#").split())
            continue
        s2 = re.sub(r"<!--.*?-->", " ", s)
        s2 = s2.replace(L.MARK_2D, " ").replace(L.MARK_P2, " ").replace(L.MARK_F133, " ")
        code += sum(len(c.split()) for c in re.findall(r"`([^`]*)`", s2))
        s2 = re.sub(r"`[^`]*`", " ", s2)
        s2 = re.sub(r"\[@[^\]]*\]", " ", s2)
        s2 = re.sub(r"\]\([^)]*\)", "]", s2)
        s2 = re.sub(r"\{#[^}]*\}", " ", s2).replace("![", " ")
        if s2.startswith("|"):
            if not re.fullmatch(r"\|[\s\-:|]+\|?", s2.strip()):
                tables += len(" ".join(c for c in s2.strip().strip("|").split("|")).split())
            continue
        if s2.startswith(": "):
            s2 = s2[2:]
        prose += len(s2.split())
    return prose, tables, code


def sections(draft):
    out, cur = [], None
    yaml_end = next(i for i in range(1, len(draft)) if draft[i].strip() == "---")
    for i, s in enumerate(draft[yaml_end + 1:], yaml_end + 2):
        if s.startswith("# "):
            cur = {"h1": s[2:].strip(), "h2": "", "lines": []}
            out.append(cur)
        elif s.startswith("## ") and cur is not None:
            cur = {"h1": cur["h1"], "h2": s[3:].strip(), "lines": []}
            out.append(cur)
        if cur is not None:
            cur["lines"].append(s)
    return out


def main():
    L.install_r17_guard()
    S4 = derived()
    draft, span_by_line, marks, rng, old = build_draft(S4)
    L.DRAFT.mkdir(parents=True, exist_ok=True)
    (L.DRAFT / "main_v2.qmd").write_bytes("\n".join(draft).encode("utf-8"))  # main.qmd ends with a newline: its last split element is empty
    ev, bare, orphan, hdig = evidence(draft, span_by_line, rng)
    assert not bare, ("bare numbers in sections 2-3", bare[:5])
    fe = ["id", "section", "line", "sentence", "number_as_written", "kind", "source", "value_in_source", "match", "mark"]
    L.table("E1_evidence_index", "E1 - evidence index of every numeric token of sections 2-3 (first 40; all in the CSV)", fe, ev, md_rows=40)
    # S0 outline
    outline = [
        ("Title, YAML, abstract", "kept from main.qmd", "main.qmd lines 1-49; part-2 marks in the abstract"),
        ("1 Introduction", "kept from main.qmd", "main.qmd; rewritten in part 2"),
        ("2 Methodology / Research design", "new", "the brief's three questions and contributions; Decision 38"),
        ("2 Methodology / Data sources and search strategy", "rewritten", "README_exports.txt; phase_F13_1 T1a, T3a, T3b; phase_F12_4 T1; phase_F13_4b T4a"),
        ("2 Methodology / Data processing", "rewritten", "phase_F13_1 T1b; phase_F13_5 numbers; phase_F13_2c T3c_v2, T1a, thesaurus v2; phase_F13_2 thesauri"),
        ("2 Methodology / Indicators", "rewritten", "phase_F13_4 T1c, T2b; phase_F13_5 numbers, S2, T2; references.bib (cyber_shield)"),
        ("2 Methodology / Validation and reliability", "rewritten", "phase_F13_2 T5a-T5d; phase_F13_2c T1b"),
        ("2 Methodology / Limitations of the data", "new", "phase_F13_2 T1b, T1f; phase_F12_4 T1, T2"),
        ("3 Results / Growth and normalised activity", "rewritten", "phase_F13_4 T1b-T1d, T2b, T3c; phase_F13_4b T4a, T4d; S4"),
        ("3 Results / Document types, sources and citation impact", "new", "phase_F13_2 T1b, T1d, T1f, T2a-T2e, T3a-T3d, T4a-T4c"),
        ("3 Results / Institutions and collaboration", "rewritten", "phase_F13_2b T2a-T2e, T2g, T3e; phase_F13_2c T2a-T2f, T3a_v2, T3c_v2, T3d_v2"),
        ("3 Results / Thematic structure", "rewritten", "phase_F13_5 numbers, T5, T6, T7, T8, S1, S2"),
        ("3 Results / Database coverage at an equal query", "rewritten", "phase_F12_4 T1, T1b, T2, T3"),
        ("3 Results / Citation structure", "part 2", "phase_F13_3 (not used here)"),
        ("4 Discussion to the AI declaration", "kept from main.qmd", "main.qmd; part-2 marks after removed claims"),
    ]
    L.table("S0_outline", "S0 - outline of the draft", ["section", "status", "sources"], [{"section": a, "status": b, "sources": c} for a, b, c in outline])
    # S3 marks
    s3 = [{"mark": m["mark"], "draft_line": m["draft_line"], "main_qmd_line": m["main_qmd_line"], "where": m["section"],
           "reason": f"N2 {m['n2_id']} ({m['claim_key']}) status remove"} for m in marks]
    for ln, sp in sorted(span_by_line.items()):
        for a, b, rec in sp:
            if rec["kind"] == "mark":
                s3.append({"mark": L.MARK_2D, "draft_line": ln, "main_qmd_line": "", "where": draft[ln - 1][:60].strip(),
                           "reason": "depends on institution counts, ranks or the single / domestic types (phase_F13_2d not closed at step 0)"})
            elif rec["source"] == "label of the part-2 mark":
                s3.append({"mark": L.MARK_F133, "draft_line": ln, "main_qmd_line": "", "where": "Results / Citation structure", "reason": "written in part 2 from F13.3"})
    L.table("S3_part2_marks", "S3 - marks in the draft", ["mark", "draft_line", "main_qmd_line", "where", "reason"], s3)
    # S4
    s4 = [{"id": k, "what": d["what"], "formula": d["formula"], "inputs": d["inputs"], "value": f"{d['value']:.6f}"} for k, d in S4.items()]
    L.table("S4_derived_numbers", "S4 - numbers derived in this phase", ["id", "what", "formula", "inputs", "value"], s4)
    # S2 coverage of the F13.6a map
    n1 = L.read_csv(L.P6A + "tables/N1_manuscript_numbers.csv")
    n2 = L.read_csv(L.P6A + "tables/N2_claims.csv")
    by_src, by_val = defaultdict(list), defaultdict(list)
    for e in ev:
        by_src[e["source"]].append(e["id"])
        try:
            by_val[float(L.norm_num(e["number_as_written"]))].append(e["id"])
        except ValueError:
            by_val[L.norm_num(e["number_as_written"])].append(e["id"])
    reasons = {"annual": "annual counts are shown in the figure and the periods, not listed year by year",
               "title-term": "title bigrams are summarised (three leading pairs) rather than listed",
               "frame": "the corpus size appears in the text", "window": "the window appears as a period label",
               "period": "the 2017-2025 span is given as its two periods (2017-2021 and 2022-2025)"}
    def parse_n1(src):
        m = re.match(r"^phase_(\S+) (\S+) \[(.*)\] (\S+)$", src or "")
        if not m:
            return None
        return (m.group(1), m.group(2), frozenset(x.strip() for x in m.group(3).split(", ")), m.group(4))

    def parse_ev(src):
        m = re.match(r"^(\S+?)/(\S+) \[(.*)\] (\S+)$", src or "")
        if not m:
            return None
        w = m.group(3)
        return (m.group(1), m.group(2), frozenset() if w == "-" else frozenset(x.strip() for x in w.split(" & ")), m.group(4))

    ev_keys = defaultdict(list)
    for e in ev:
        k = parse_ev(e["source"])
        if k:
            ev_keys[k].append(e)
    s2 = []
    for r in n1:
        sec = r["section"].split(" / ")[0]
        if r["status"] not in ("same", "changed") or not (sec.startswith("Methodology") or sec.startswith("Results")):
            continue
        k1 = parse_n1(r["source_new"])
        same_cell = ev_keys.get(k1, []) if k1 else []
        try:
            key = float(L.norm_num(r["value_new"])) if r["value_new"] else None
        except ValueError:
            key = L.norm_num(r["value_new"])
        generic = r["category"] in ("frame", "window", "period", "policy") or r["what_it_denotes"] == "year label"
        same_tab = [e for e in ev if k1 and parse_ev(e["source"]) and parse_ev(e["source"])[1] == k1[1] and
                    by_val.get(key) and e["id"] in by_val.get(key, [])] if key is not None else []
        same_val = by_val.get(key, []) if (key is not None and generic) else []
        if same_cell:
            hit, basis = same_cell[0]["id"], "same cell"
        elif same_tab:
            hit, basis = same_tab[0]["id"], "same table and value"
        elif same_val:
            hit, basis = same_val[0], "same value (corpus size, window, period or year label)"
        else:
            hit, basis = "", "not in the draft"
        s2.append({"map": "N1", "id": r["id"], "line_in_main": r["line"], "status": r["status"], "value_new": r["value_new"], "in_draft": hit,
                   "basis": basis, "reason": "" if hit else reasons.get(r["category"], "not needed in the rewritten text")})
    sents = []
    for ln in range(rng[0], rng[1] + 1):
        s = draft[ln - 1]
        if not s.strip() or s.startswith("#") or s.startswith("|"):
            continue
        for k, (a, b) in enumerate(L.f136a().sentences(s), 1):
            sents.append({"sid": f"D{ln}s{k}", "line": ln, "text": s[a:b]})
    secmap = [("Methodology / Research Design", "Research design", None), ("Methodology / Data Sources", "Data sources", "OpenAlex"),
              ("Methodology / Data Normalization", "Data processing", None), ("Methodology / Institutional Counts", "Indicators", "international"),
              ("Methodology / Title-Term", "Indicators", "co-word"), ("Methodology / Longitudinal", "Indicators", "periods"),
              ("Methodology / Validity", "Validation", None), ("Methodology / Bibliometric and Scientometric", "Indicators", None),
              ("Methodology / Layer-Specific", "Data sources", "OpenAlex"), ("Methodology / Computational", "Validation", "scripted"),
              ("Results: Bibliometric Mapping and Trends / Publication", "Growth", None),
              ("Results: Bibliometric Mapping and Trends / Institutions", "Institutions", None),
              ("Results: Bibliometric Mapping and Trends / Title-Term", "Thematic", None),
              ("Results: Bibliometric Mapping and Trends / OpenAlex", "Database coverage", None),
              ("Results: Bibliometric Mapping and Trends", "Growth", None), ("Methodology", "Research design", None)]
    h2_of = {}
    cur = ""
    for ln in range(rng[0], rng[1] + 1):
        if draft[ln - 1].startswith("## "):
            cur = draft[ln - 1][3:].strip()
        h2_of[ln] = cur
    for r in n2:
        ln = int(r["line"])
        if r["status"] not in ("remove", "changed") or not (old[0] <= ln < old[1]):
            continue
        target = next(((t, kw) for pre, t, kw in secmap if r["section"].startswith(pre)), ("Research design", None))
        cand = [s for s in sents if h2_of.get(s["line"], "").startswith(target[0])]
        if target[1]:
            cand = [s for s in cand if target[1].lower() in s["text"].lower()] or cand
        if r["status"] == "remove":
            s2.append({"map": "N2", "id": r["id"], "line_in_main": ln, "status": "remove", "value_new": "", "in_draft": "",
                       "basis": "removed", "reason": "decisions " + r["decisions"] if r["decisions"] else "claim dropped"})
        else:
            s2.append({"map": "N2", "id": r["id"], "line_in_main": ln, "status": "changed", "value_new": "", "in_draft": cand[0]["sid"] if cand else "",
                       "basis": f"rewritten in '{target[0]}'", "reason": r["note"][:120]})
    L.table("S2_map_coverage", "S2 - the F13.6a map against the draft (Methodology and Results)", ["map", "id", "line_in_main", "status", "value_new",
                                                                                                  "in_draft", "basis", "reason"], s2)
    # S5 words and citation keys
    secs = sections(draft)
    rows5 = []
    for s in secs:
        p, t, c = words_of(s["lines"])
        rows5.append({"section": s["h1"] + (" / " + s["h2"] if s["h2"] else ""), "prose_words": p, "table_words": t, "code_words": c})
    p23 = sum(r["prose_words"] for r, s in zip(rows5, secs) if s["h1"] in L.SECTIONS_2_3)
    t23 = sum(r["table_words"] for r, s in zip(rows5, secs) if s["h1"] in L.SECTIONS_2_3)
    pall = sum(r["prose_words"] for r in rows5)
    rows5 += [{"section": "sections 2-3 (Methodology and Results)", "prose_words": p23, "table_words": t23, "code_words": ""},
              {"section": "whole draft after the YAML block", "prose_words": pall, "table_words": sum(r["table_words"] for r in rows5[:len(secs)]), "code_words": ""}]
    L.table("S5_word_counts", "S5 - word counts (prose and captions; tables and code spans apart)", ["section", "prose_words", "table_words", "code_words"], rows5,
            note="Words are whitespace-separated tokens after removing citations, comments, marks, link targets and attribute blocks; table cells and "
                 "code spans (the queries) are counted apart; headings count as prose.")
    bib = set(re.findall(r"^@\w+\{([^,]+),", L.path(L.BIB).read_bytes().decode("utf-8"), re.M))
    used_all, used23 = Counter(), Counter()
    for i, s in enumerate(draft, 1):
        for grp in CITE.findall(s):
            for k in re.findall(r"@([\w:-]+)", "@" + grp if not grp.startswith("@") else grp):
                used_all[k] += 1
                if rng[0] <= i <= rng[1]:
                    used23[k] += 1
    keys = [{"key": k, "uses_in_draft": used_all[k], "uses_in_sections_2_3": used23.get(k, 0), "in_references_bib": "yes" if k in bib else "NO"}
            for k in sorted(used_all)]
    L.table("S5b_citation_keys", "S5b - citation keys used in the draft", ["key", "uses_in_draft", "uses_in_sections_2_3", "in_references_bib"], keys)
    needed = [
        ("Bradford zones", "Bradford (1934), Sources of information on specific subjects, Engineering 137, 85-86", "no DOI", "Bradford"),
        ("activity index", "Schubert and Braun (1986), Relative indicators and relational charts, Scientometrics 9, 281-291", "10.1007/BF02017249", "activity index compares"),
        ("resampling intervals", "Efron (1979), Bootstrap methods: another look at the jackknife, Annals of Statistics 7, 1-26", "10.1214/aos/1176344552", "resampling replicates"),
        ("h-index", "Hirsch (2005), An index to quantify an individual's scientific research output, PNAS 102, 16569-16572", "10.1073/pnas.0507655102", "h-index of the corpus is the largest"),
        ("co-word analysis", "Callon, Courtial, Turner and Bauin (1983), From translations to problematic networks, Social Science Information 22, 191-235",
         "10.1177/053901883022002003", "co-word network"),
        ("association strength", "van Eck and Waltman (2009), How to normalize cooccurrence data?, JASIST 60, 1635-1651", "10.1002/asi.21075", "association strength"),
        ("greedy modularity", "Clauset, Newman and Moore (2004), Finding community structure in very large networks, Physical Review E 70, 066111",
         "10.1103/PhysRevE.70.066111", "greedy agglomeration"),
        ("Louvain algorithm", "Blondel, Guillaume, Lambiotte and Lefebvre (2008), Fast unfolding of communities in large networks, J. Stat. Mech. P10008",
         "10.1088/1742-5468/2008/10/P10008", "Louvain algorithm"),
        ("Rand index", "Rand (1971), Objective criteria for the evaluation of clustering methods, JASA 66, 846-850", "10.1080/01621459.1971.10482356", "Rand index and"),
        ("adjusted Rand index", "Hubert and Arabie (1985), Comparing partitions, Journal of Classification 2, 193-218", "10.1007/BF01908075", "adjusted Rand index between"),
        ("bibliometrix (part 2)", "Aria and Cuccurullo (2017), bibliometrix: an R-tool for comprehensive science mapping analysis, J. Informetrics 11, 959-975",
         "10.1016/j.joi.2017.08.007", None),
    ]
    s6 = []
    for what, ref, doi, kw in needed:
        where = next((f"line {i}" for i in range(rng[0], rng[1] + 1) if kw and kw in draft[i - 1]), "part 2 (citation structure)")
        s6.append({"method": what, "reference": ref, "doi": doi, "where_in_draft": where, "note": "DOI from the executor's knowledge; verify before adding to references.bib"})
    L.table("S6_citations_needed", "S6 - method sources the draft needs (not added to references.bib)", ["method", "reference", "doi", "where_in_draft", "note"], s6)
    # numbers
    kinds = Counter(e["kind"] for e in ev)
    num = {"tokens_sections_2_3": len(ev), "by_kind": dict(sorted(kinds.items())), "match_yes": sum(1 for e in ev if e["match"] == "yes"),
           "match_no": sum(1 for e in ev if e["match"] == "no"), "table_formula_all_yes": all(e["match"] == "yes" for e in ev if e["kind"] in ("table", "formula")),
           "marked_F13_2d_tokens": sum(1 for e in ev if e["mark"]), "orphan_placeholders": len(orphan), "heading_tokens": len(hdig),
           "words_sections_2_3_prose": p23, "words_sections_2_3_tables": t23, "words_draft_prose": pall,
           "marks": dict(Counter(m["mark"] for m in s3)), "draft_lines": len(draft), "sections_2_3_lines": list(rng), "old_sections_2_3_in_main": [old[0], old[1] - 1],
           "citation_keys": len(keys), "keys_missing_in_bib": [k["key"] for k in keys if k["in_references_bib"] != "yes"],
           "s2": dict(Counter((r["map"], r["basis"].split(" '")[0]) for r in s2).items()) if False else {f"{a}: {b}": c for (a, b), c in Counter((r["map"], r["basis"].split(" '")[0]) for r in s2).items()},
           "forbidden_in_sections_2_3": {n: len(re.findall(rx, "\n".join(draft[rng[0] - 1:rng[1]]), re.I if n != "L1" else 0)) for n, rx in FORBIDDEN_TEXT}}
    L.jdump(num, L.OUT / "F13_6b_numbers.json")
    print(json.dumps({k: num[k] for k in ("tokens_sections_2_3", "by_kind", "match_no", "orphan_placeholders", "words_sections_2_3_prose",
                                          "words_sections_2_3_tables", "marks", "keys_missing_in_bib", "forbidden_in_sections_2_3")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
