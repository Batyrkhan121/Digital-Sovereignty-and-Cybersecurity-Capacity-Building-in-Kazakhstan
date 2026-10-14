"""Phase F13.7a - step 4: supplementary/Supplementary_tables_draft.xlsx (openpyxl) and tables/X1_sheet_sources.csv.
One sheet per source file (so that every sheet can be checked against its file: rows and sha256 in X1); sheet names <= 31 characters;
a README sheet with the contents, sources and date. Values are the source's strings; a value becomes a number only when the number
writes back to exactly the same string (integers without leading zeros; decimals whose shortest form is the string), so nothing is
rounded. Four sources are derived here, in tables/, from closed phases' files: S1 (queries and totals from README_exports.txt, the
manifest, F12.4's T1_summary and the registry's F12.4 note), S6c (the top 30 of F13.2e's T3d_v31), S8s (F13.2's T3e_top20_cited without
EID and DOI, title cut to 15 words: R13's rule for listed works) and the Phase log (the one registry read of step 0). Record-level lists
(F12.4 T1c/T2b/T3b, F13.1 T3a_pairs) and raw funder strings (F13.2 T4c_funder_variants_raw) are left out (R13: aggregates and names
only). The xlsx is written deterministically (fixed zip times and document dates), so a second run is byte-identical."""
import sys
sys.dont_write_bytecode = True

import io
import json
import re
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f137a_lib as L

P = L.DPR
XLSX = L.SUPP / "Supplementary_tables_draft.xlsx"
FIXED_ZIP_TIME = (2026, 10, 13, 0, 0, 0)
FIXED_DOC_TIME = "2026-10-13T00:00:00Z"


def t(phase, name):
    return f"{P}{phase}/tables/{name}.csv"


SHEETS = [
    ("S1_queries", "derived:S1_queries", "Queries, retrieval dates and totals (Scopus, WoS, OpenAlex, Analyze series)"),
    ("S2_year_series", P + "author_exports_2026_10/scopus_years_all_series_long.csv", "Eleven Scopus Analyze year series 2003-2025 (long)"),
    ("S3a_AI_periods_F134", t("phase_F13_4", "T2b_activity_index_periods"), "Activity index by period, Kazakhstan (F13.4 T2b)"),
    ("S3b_AI_windows_F134", t("phase_F13_4", "T2d_activity_index_windows"), "Activity index by window (F13.4 T2d)"),
    ("S3c_AI_5countries_F134b", t("phase_F13_4b", "T4a_activity_index_five_countries"), "Activity index, five countries (F13.4b T4a)"),
    ("S3d_AI_ranking_F134b", t("phase_F13_4b", "T4c_ranking"), "Ranking by standardised index (F13.4b T4c)"),
    ("S3e_AI_no2025_F134b", t("phase_F13_4b", "T4d_without_2025"), "Windows ending in 2024 (F13.4b T4d)"),
    ("S4_kw_thesaurus_v4", t("phase_F13_5", "thesaurus"), "Keyword thesaurus v4, 680 rows (F13.5)"),
    ("S4b_kw_layers_versions", t("phase_F13_5", "D4_versions_summary"), "Author / index keyword layers by thesaurus version (F13.5 D4)"),
    ("S5_inst_thesaurus_v31", t("phase_F13_2e", "institutions_thesaurus_v31"), "Institutions thesaurus v3.1, 285 rows (F13.2e)"),
    ("S5b_inst_exclusions_v3", t("phase_F13_2d", "T1c_exclusions"), "Institutions: exclusions of v3 (F13.2d T1c)"),
    ("S5c_inst_name_rules_v3", t("phase_F13_2d", "T1d_name_token_rules"), "Institutions: name-token rules of v3 (F13.2d T1d)"),
    ("S6a_institutions_v31", t("phase_F13_2e", "T3a_v31_kz_institutions"), "Kazakhstan institutions, all (F13.2e T3a_v31)"),
    ("S6b_concentration_v31", t("phase_F13_2e", "T3c_v31_concentration"), "Institutional concentration (F13.2e T3c_v31)"),
    ("S6c_pairs_v31_top30", "derived:S6c_pairs_v31_top30", "Pairs of Kazakhstan institutions, top 30 (F13.2e T3d_v31)"),
    ("S7a_F132b_T2a_countries", t("phase_F13_2b", "T2a_countries_per_record"), "Countries per record (F13.2b T2a)"),
    ("S7b_F132b_T2b_partners", t("phase_F13_2b", "T2b_partner_countries"), "Partner countries (F13.2b T2b)"),
    ("S7c_F132b_T2c_intl_share", t("phase_F13_2b", "T2c_international_share"), "International share (F13.2b T2c)"),
    ("S7d_F132b_T2d_country_pairs", t("phase_F13_2b", "T2d_partner_country_pairs"), "Partner country pairs (F13.2b T2d)"),
    ("S7e_F132b_T2e_partner_srcs", t("phase_F13_2b", "T2e_partner_sources"), "Sources by partner country (F13.2b T2e)"),
    ("S7f_F132b_T3e_foreign_inst", t("phase_F13_2b", "T3e_foreign_institutions"), "Foreign institutions (F13.2b T3e)"),
    ("S7g_F132b_T3f_top10_partners", t("phase_F13_2b", "T3f_top10_partner_countries"), "Top 10 partner countries (F13.2b T3f)"),
    ("S7h_F132c_T2a_intl_by_author", t("phase_F13_2c", "T2a_international_by_author"), "International records by author (F13.2c T2a)"),
    ("S7i_F132c_T2b_first_author", t("phase_F13_2c", "T2b_first_author_country"), "First author's country (F13.2c T2b)"),
    ("S7j_F132c_T2c_not_ukraine", t("phase_F13_2c", "T2c_partners_other_than_ukraine"), "Partners other than Ukraine (F13.2c T2c)"),
    ("S7k_F132c_T2d_kz_positions", t("phase_F13_2c", "T2d_kazakhstan_positions"), "Kazakhstan author positions (F13.2c T2d)"),
    ("S7l_F132c_T2e_by_type", t("phase_F13_2c", "T2e_top_partners_by_type"), "Top partners by type (F13.2c T2e)"),
    ("S8a_F132_T1b_types_exported", t("phase_F13_2", "T1b_types_exported"), "Document types as exported (F13.2 T1b)"),
    ("S8b_F132_T1b_types_harm", t("phase_F13_2", "T1b_types_harmonised"), "Document types harmonised (F13.2 T1b)"),
    ("S8c_F132_T1c_year_by_type", t("phase_F13_2", "T1c_year_by_type"), "Year by type (F13.2 T1c)"),
    ("S8d_F132_T1d_periods", t("phase_F13_2", "T1d_periods"), "Periods (F13.2 T1d)"),
    ("S8e_F132_T1e_authors", t("phase_F13_2", "T1e_authors_per_record"), "Authors per record (F13.2 T1e)"),
    ("S8f_F132_T1f_language", t("phase_F13_2", "T1f_language"), "Language (F13.2 T1f)"),
    ("S8g_F132_T1f_stage", t("phase_F13_2", "T1f_publication_stage"), "Publication stage (F13.2 T1f)"),
    ("S8h_F132_T1g_retracted", t("phase_F13_2", "T1g_retracted"), "Retracted records (F13.2 T1g)"),
    ("S8i_F132_T2a_bradford", t("phase_F13_2", "T2a_concentration"), "Source concentration and Bradford zones (F13.2 T2a)"),
    ("S8j_F132_T2a_sources", t("phase_F13_2", "T2a_sources"), "All sources (F13.2 T2a)"),
    ("S8k_F132_T2b_journals", t("phase_F13_2", "T2b_top20_journals"), "Top 20 journals (F13.2 T2b)"),
    ("S8l_F132_T2c_conferences", t("phase_F13_2", "T2c_top20_conference_sources"), "Top 20 conference sources (F13.2 T2c)"),
    ("S8m_F132_T2d_publishers", t("phase_F13_2", "T2d_publishers"), "Publishers (F13.2 T2d)"),
    ("S8n_F132_T2e_series", t("phase_F13_2", "T2e_top15_series"), "Top 15 conference series (F13.2 T2e)"),
    ("S8o_F132_T3a_citations", t("phase_F13_2", "T3a_citations"), "Citations (F13.2 T3a)"),
    ("S8p_F132_T3b_cit_by_year", t("phase_F13_2", "T3b_citations_by_year"), "Citations by year (F13.2 T3b)"),
    ("S8q_F132_T3c_cit_by_type", t("phase_F13_2", "T3c_citations_by_type"), "Citations by type (F13.2 T3c)"),
    ("S8r_F132_T3d_cit_by_period", t("phase_F13_2", "T3d_citations_by_period"), "Citations by period (F13.2 T3d)"),
    ("S8s_F132_T3e_top20_cited", "derived:S8s_top20_cited", "Top 20 cited records, title cut to 15 words (F13.2 T3e)"),
    ("S8t_F132_T3f_src_by_cit", t("phase_F13_2", "T3f_top10_sources_by_citations"), "Top 10 sources by citations (F13.2 T3f)"),
    ("S8u_F132_T4a_open_access", t("phase_F13_2", "T4a_open_access"), "Open access (F13.2 T4a)"),
    ("S8v_F132_T4b_funding", t("phase_F13_2", "T4b_funding"), "Funding (F13.2 T4b)"),
    ("S8w_F132_T4c_funders", t("phase_F13_2", "T4c_top15_funders"), "Top 15 funders (F13.2 T4c)"),
    ("S9a_F135_T3_nodes", t("phase_F13_5", "T3_author_nodes"), "Co-word network nodes, author keywords (F13.5 T3)"),
    ("S9b_F135_T5_clusters", t("phase_F13_5", "T5_author_clusters"), "Clusters (F13.5 T5)"),
    ("S9c_F135_T5_top10", t("phase_F13_5", "T5_author_cluster_top10"), "Top 10 keywords per cluster (F13.5 T5)"),
    ("S9d_F135_T6_periods", t("phase_F13_5", "T6_author_keywords_by_period"), "Keywords by period (F13.5 T6)"),
    ("S9e_F135_T7_blind_spots", t("phase_F13_5", "T7_blind_spots_keywords"), "Blind spots with their patterns (F13.5 T7)"),
    ("S9f_F135_S1_agreement", t("phase_F13_5", "S1_partition_agreement"), "Partition agreement (F13.5 S1)"),
    ("S9g_F135_S2_louvain", t("phase_F13_5", "S2_algorithm_sensitivity"), "Algorithm sensitivity (F13.5 S2)"),
    ("S10a_F124_T1_summary", t("phase_F12_4", "T1_summary"), "OpenAlex coverage summary (F12.4 T1)"),
    ("S10b_F124_T1b_periods", t("phase_F12_4", "T1b_periods"), "Coverage by period (F12.4 T1b)"),
    ("S10c_F124_T1b_years", t("phase_F12_4", "T1b_years"), "Coverage by year (F12.4 T1b)"),
    ("S10d_F124_T2_oa_doi_prefix", t("phase_F12_4", "T2_only_openalex_doi_prefix"), "Only OpenAlex: DOI prefixes (F12.4 T2)"),
    ("S10e_F124_T2_oa_doi", t("phase_F12_4", "T2_only_openalex_doi_presence"), "Only OpenAlex: DOI presence (F12.4 T2)"),
    ("S10f_F124_T2_oa_sources", t("phase_F12_4", "T2_only_openalex_sources"), "Only OpenAlex: sources (F12.4 T2)"),
    ("S10g_F124_T2_oa_types", t("phase_F12_4", "T2_only_openalex_types"), "Only OpenAlex: types (F12.4 T2)"),
    ("S10h_F124_T2_oa_years", t("phase_F12_4", "T2_only_openalex_years"), "Only OpenAlex: years (F12.4 T2)"),
    ("S10i_F124_T3_sc_types", t("phase_F12_4", "T3_only_scopus_doc_types"), "Only Scopus: document types (F12.4 T3)"),
    ("S10j_F124_T3_sc_doi", t("phase_F12_4", "T3_only_scopus_doi_presence"), "Only Scopus: DOI presence (F12.4 T3)"),
    ("S10k_F124_T3_sc_in_oa_june", t("phase_F12_4", "T3_only_scopus_in_openalex_june"), "Only Scopus: in the June OpenAlex (F12.4 T3)"),
    ("S10l_F124_T3_sc_sources", t("phase_F12_4", "T3_only_scopus_sources"), "Only Scopus: sources (F12.4 T3)"),
    ("S10m_F124_T3_sc_years", t("phase_F12_4", "T3_only_scopus_years"), "Only Scopus: years (F12.4 T3)"),
    ("S10n_F124_T4_bridge_june", t("phase_F12_4", "T4_bridge_to_june"), "Bridge to the June layers (F12.4 T4)"),
    ("S11a_F133_T0a_ref_counts", t("phase_F13_3", "T0a_reference_counts"), "Reference counts (F13.3 T0a)"),
    ("S11b_F133_T0b_scopus_wos", t("phase_F13_3", "T0b_pairs_scopus_vs_wos"), "References, Scopus against WoS (F13.3 T0b)"),
    ("S11c_F133_T0c_by_period", t("phase_F13_3", "T0c_references_by_period_and_type"), "References by period and type (F13.3 T0c)"),
    ("S11d_F133_T1_ref_age", t("phase_F13_3", "T1_reference_age"), "Reference age (F13.3 T1)"),
    ("S11e_F133_T1a_age_dist", t("phase_F13_3", "T1a_age_distribution"), "Age distribution (F13.3 T1a)"),
    ("S11f_F133_T1b_rpys", t("phase_F13_3", "T1b_rpys"), "RPYS (F13.3 T1b)"),
    ("S11g_F133_T1c_rpys_peaks", t("phase_F13_3", "T1c_rpys_peaks"), "RPYS peaks with the top cited work (F13.3 T1c)"),
    ("S12a_F132_T5a_types", t("phase_F13_2", "T5a_types"), "WoS validation: types (F13.2 T5a)"),
    ("S12b_F132_T5b_years", t("phase_F13_2", "T5b_years"), "WoS validation: years (F13.2 T5b)"),
    ("S12c_F132_T5c_citations", t("phase_F13_2", "T5c_citations"), "WoS validation: citations (F13.2 T5c)"),
    ("S12d_F132_T5d_top20", t("phase_F13_2", "T5d_top20_overlap"), "WoS validation: top 20 overlap (F13.2 T5d)"),
    ("S12e_F131_T3a_scopus_wos", t("phase_F13_1", "T3a_scopus_wos"), "Scopus and WoS matching (F13.1 T3a)"),
    ("S12f_F131_T3b_wos_DT", t("phase_F13_1", "T3b_only_wos_DT"), "Only WoS: document types (F13.1 T3b)"),
    ("S12g_F131_T3b_wos_LA", t("phase_F13_1", "T3b_only_wos_LA"), "Only WoS: languages (F13.1 T3b)"),
    ("S12h_F131_T3b_wos_PY", t("phase_F13_1", "T3b_only_wos_PY"), "Only WoS: years (F13.1 T3b)"),
    ("S12i_F131_T3b_wos_SO", t("phase_F13_1", "T3b_only_wos_SO"), "Only WoS: sources (F13.1 T3b)"),
    ("S12j_F131_T3b_wos_WE", t("phase_F13_1", "T3b_only_wos_WE"), "Only WoS: editions (F13.1 T3b)"),
    ("Phase_log", "derived:phase_log_from_registry", "Phases F12.4 - F13.6b from PHASE_REGISTRY.csv (one read in step 0)"),
]
DERIVED_ORIGIN = {
    "S1_queries": "README_exports.txt; manifest_year_series.json; phase_F12_4 T1_summary; registry note of phase_F12_4",
    "S6c_pairs_v31_top30": "phase_F13_2e T3d_v31_kz_institution_pairs (first 30 rows)",
    "S8s_top20_cited": "phase_F13_2 T3e_top20_cited (EID and DOI dropped; title cut to 15 words)",
    "phase_log_from_registry": "PHASE_REGISTRY.csv, one read in step 0 (rows phase_F12_4 and phase_F13_*; note cut to 27 words)",
}


def source_path(src):
    return L.TABLES / (src.split(":", 1)[1] + ".csv") if src.startswith("derived:") else L.path(src)


def derive():
    readme = L.path(L.README_EXPORTS).read_bytes().decode("utf-8")
    qs = re.findall(r"query exactly:\s*\n\s*(.+)", readme)
    date = re.search(r"Date of retrieval: (\d{4}-\d{2}-\d{2})", readme).group(1)
    man = L.jload(L.path(L.MANIFEST))
    t1 = {r["measure"]: r["value"] for r in L.read_csv(t("phase_F12_4", "T1_summary"))}
    log = L.read_csv_path(L.TABLES / "phase_log_from_registry.csv")
    f124 = next(r for r in log if r["phase_id"] == "phase_F12_4")
    f124_date = re.search(r"\d{4}-\d{2}-\d{2}", f124["note_first_words"]).group(0)
    rows = [{"database": "Scopus", "layer": "corpus E1 (full export)", "query": qs[0].strip(), "retrieved": date, "records": "841",
             "source": "README_exports.txt (A.1); 841 rows in the export"},
            {"database": "Web of Science Core Collection", "layer": "validation (savedrecs.txt)", "query": qs[1].strip(), "retrieved": date,
             "records": "231", "source": "README_exports.txt (A.2)"},
            {"database": "OpenAlex", "layer": "coverage at an equal query (H4Q title-only, harmonised)", "query": "H4Q title-only, harmonised with Scopus (F12.4)",
             "retrieved": f124_date, "records": next(v for k, v in t1.items() if k.startswith("|O|")), "source": "phase_F12_4 T1_summary; registry note"},
            {"database": "Scopus", "layer": "coverage at an equal query (H4Q title-only)", "query": "H4Q title-only (F12.4)",
             "retrieved": f124_date, "records": next(v for k, v in t1.items() if k.startswith("|S|")), "source": "phase_F12_4 T1_summary; registry note"}]
    for m in man:
        rows.append({"database": "Scopus (Analyze search results)", "layer": "year series " + m["series"], "query": m["query"], "retrieved": date,
                     "records": str(m["ui_total"]), "source": "manifest_year_series.json; " + m["file"]})
    L.write_csv(L.TABLES / "S1_queries.csv", ["database", "layer", "query", "retrieved", "records", "source"], rows)
    d = L.read_csv(t("phase_F13_2e", "T3d_v31_kz_institution_pairs"))
    L.write_csv(L.TABLES / "S6c_pairs_v31_top30.csv", list(d[0].keys()), d[:30])
    c = L.read_csv(t("phase_F13_2", "T3e_top20_cited"))
    keep = [k for k in c[0].keys() if k not in ("eid", "doi")]
    L.write_csv(L.TABLES / "S8s_top20_cited.csv", keep, [{**{k: r[k] for k in keep}, "title": L.words(r["title"], 15)} for r in c])


def conv(v):
    """(value, number_format): integers without leading zeros -> int; decimals that print back exactly with their own number of places
    -> float shown with that many places (so '87.0' stays '87.0' in Excel); everything else stays text."""
    if v is None or v == "":
        return None, None
    if re.fullmatch(r"-?(0|[1-9]\d{0,14})", v):
        return int(v), None
    m = re.fullmatch(r"-?(0|[1-9]\d{0,14})\.(\d{1,10})", v)
    if m:
        d = len(m.group(2))
        f = float(v)
        if f"{f:.{d}f}" == v:
            return f, "0." + "0" * d
    return v, None


def same(src, got):
    """The comparison of G3 and the verifier: a cell equals its source string at the source's own precision."""
    val, fmt = conv(src)
    if val is None:
        return got in (None, "")
    if isinstance(val, int):
        return isinstance(got, (int, float)) and not isinstance(got, bool) and float(got) == val and str(int(got)) == src
    if fmt:
        return isinstance(got, (int, float)) and f"{float(got):.{len(fmt) - 2}f}" == src
    return str(got) == src


def build():
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    ws0 = wb.active
    ws0.title = "README"
    x1 = []
    for name, src, desc in SHEETS:
        assert len(name) <= 31, name
        p = source_path(src)
        text = p.read_bytes().decode("utf-8-sig")
        import csv as _csv
        rows = list(_csv.reader(io.StringIO(text, newline="")))
        ws = wb.create_sheet(name)
        for r, row in enumerate(rows, 1):
            for c, v in enumerate(row, 1):
                val, fmt = (v, None) if r == 1 else conv(v)
                cell = ws.cell(row=r, column=c, value=val)
                if fmt:
                    cell.number_format = fmt
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    cell.data_type = "s"
                if r == 1:
                    cell.font = Font(bold=True)
        ws.freeze_panes = "A2"
        for c in range(1, (len(rows[0]) if rows else 0) + 1):
            width = max(len(str(rows[i][c - 1])) if c - 1 < len(rows[i]) else 0 for i in range(len(rows)))
            ws.column_dimensions[get_column_letter(c)].width = min(60, max(8, width + 2))
        origin = DERIVED_ORIGIN.get(src.split(":", 1)[1], "") if src.startswith("derived:") else ""
        x1.append({"sheet": name, "source_file": p.relative_to(L.ROOT).as_posix(), "origin": origin or "the file itself",
                   "rows": len(rows) - 1, "columns": len(rows[0]) if rows else 0, "sha256": L.sha256_file(p), "description": desc})
    readme = [["Supplementary tables (draft) - Kazakhstan cybersecurity research, Scopus 2003-2025"],
              ["Date", L.FIXED_DATE],
              ["Built by", "phase F13.7a from the tables of closed phases; every number is copied from those tables, none computed here"],
              ["Personal data", "Aggregates and names of institutions, countries, sources, keywords and cited works only (R13); no author of the corpus is named"],
              ["Status", "Draft for the package (F13.6d); sheet names and order may change"],
              [],
              ["sheet", "contents", "source (phase / table)", "rows", "sha256 of the source (first 16)"]]
    for r in x1:
        readme.append([r["sheet"], r["description"], r["source_file"] + ("" if r["origin"] == "the file itself" else " <- " + r["origin"]), r["rows"],
                       r["sha256"][:16]])
    for i, row in enumerate(readme, 1):
        for j, v in enumerate(row, 1):
            cell = ws0.cell(row=i, column=j, value=v)
            if i in (1, 7):
                cell.font = Font(bold=True)
    for col, w in (("A", 30), ("B", 70), ("C", 80), ("D", 8), ("E", 18)):
        ws0.column_dimensions[col].width = w
    wb.properties.creator = "phase F13.7a"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue(), x1


def deterministic(raw):
    """Rewrite the xlsx zip with fixed entry times and fixed document dates (openpyxl stamps both with the current time)."""
    src = zipfile.ZipFile(io.BytesIO(raw))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for info in sorted(src.infolist(), key=lambda i: src.namelist().index(i.filename)):
            data = src.read(info.filename)
            if info.filename == "docProps/core.xml":
                data = re.sub(rb"(<dcterms:(created|modified)[^>]*>)[^<]*(</dcterms:)", rb"\g<1>" + FIXED_DOC_TIME.encode() + rb"\g<3>", data)
            zi = zipfile.ZipInfo(info.filename, date_time=FIXED_ZIP_TIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = info.external_attr
            z.writestr(zi, data)
    return out.getvalue()


def main():
    derive()
    raw, x1 = build()
    L.SUPP.mkdir(parents=True, exist_ok=True)
    XLSX.write_bytes(deterministic(raw))
    L.table("X1_sheet_sources", "X1 - workbook sheets and their source files", ["sheet", "source_file", "origin", "rows", "columns", "sha256", "description"], x1)
    L.jdump({"sheets": len(x1) + 1, "data_sheets": len(x1), "rows_total": sum(r["rows"] for r in x1), "xlsx_bytes": XLSX.stat().st_size,
             "longest_sheet_name": max(len(r["sheet"]) for r in x1)}, L.RUN_LOGS / "workbook.json")
    print(json.dumps({"sheets": len(x1) + 1, "rows_total": sum(r["rows"] for r in x1), "xlsx_bytes": XLSX.stat().st_size}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
