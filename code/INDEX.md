# Code index

The programs of the project phases that produced the tables in `tables/`, one folder per phase: byte for byte, except the edited copies named below and marked in MANIFEST.csv.

**They do not run from this repository.** Each program reads the licensed exports (Scopus, Web of Science) by local paths of the project's working folder (`outputs/dprg_revision_2026/author_exports_2026_10/`), and these files are not distributed. To rerun a phase, export the records yourself by the identifiers in `data/` and place the files at the same paths. Paths, folder names, gates and step-0 snapshots refer to that working layout.

Python 3.11 (pandas, networkx, scikit-learn, matplotlib, openpyxl, rapidfuzz); phase F13.3 runs R with bibliometrix 5.5.0. Program roles by name: `*_step0` input digests and snapshot; `*_gates` checks with planted violations; `*_verify` the independent verifier's own code; `*_report`, `*_final`, `*_registry` reports and closing; `*_probe` exploration; `*_lib` shared functions; the others compute.

Local paths: in 16 program copies the absolute paths of the author's machine were replaced - the interpreter by `sys.executable`, Rscript by the environment variable `RSCRIPT` (default `Rscript`), the project root by `PROJECT_ROOT` (default `.`); MANIFEST.csv marks them 'no (local paths removed)'.

## F12.4

- Closed: 2026-10-13 (project registry)
- Computes: Database coverage at an equal title-only query, Scopus against OpenAlex (4 September 2026): pairing by DOI, then normalised title; union 309; composition of the one-sided sets; data of figure 6
- Inputs: Scopus and OpenAlex title-only result sets of 4 September 2026 (project files, not distributed)
- Outputs here: `tables/F12_4/T1_summary.csv`, `tables/F12_4/T1b_periods.csv`, `tables/F12_4/T1b_years.csv`, `tables/F12_4/T2_only_openalex_doi_prefix.csv`, `tables/F12_4/T2_only_openalex_doi_presence.csv`, `tables/F12_4/T2_only_openalex_sources.csv`, `tables/F12_4/T2_only_openalex_types.csv`, `tables/F12_4/T2_only_openalex_years.csv`, `tables/F12_4/T3_only_scopus_doc_types.csv`, `tables/F12_4/T3_only_scopus_doi_presence.csv`, `tables/F12_4/T3_only_scopus_in_openalex_june.csv`, `tables/F12_4/T3_only_scopus_sources.csv`, `tables/F12_4/T3_only_scopus_years.csv`, `tables/F12_4/T4_bridge_to_june.csv`, `figures/figure_6_coverage_union.csv`
- Programs: `f124_coverage.py` (computation), `f124_final.py` (closing and registry row), `f124_lib.py` (shared functions), `f124_report.py` (report), `f124_step0.py` (step 0: input digests and snapshot), `f124_verify.py` (independent verifier's own code)
- Not included (CHK1 scan or declared R13 exclusion; class only): `f124_gates.py` (ORCID, e-mail)

## F13.1

- Closed: 2026-10-13 (project registry)
- Computes: Acceptance of the full exports: record and identifier counts, field completeness, Scopus-WoS pairing (216 pairs), profile of the WoS-only records
- Inputs: Scopus full export E1 and WoS full export (licensed, not distributed)
- Outputs here: `tables/F13_1/T1a_counts.csv`, `tables/F13_1/T1b_completeness.csv`, `tables/F13_1/T3a_scopus_wos.csv`, `tables/F13_1/T3b_only_wos_DT.csv`, `tables/F13_1/T3b_only_wos_LA.csv`, `tables/F13_1/T3b_only_wos_PY.csv`, `tables/F13_1/T3b_only_wos_SO.csv`, `tables/F13_1/T3b_only_wos_WE.csv`
- Programs: `f131_accept.py` (computation), `f131_final.py` (closing and registry row), `f131_lib.py` (shared functions), `f131_probe.py` (exploration), `f131_report.py` (report), `f131_step0.py` (step 0: input digests and snapshot), `f131_verify.py` (independent verifier's own code)
- Not included (CHK1 scan or declared R13 exclusion; class only): `f131_gates.py` (ORCID, e-mail)

## F13.2

- Closed: 2026-10-13 (project registry)
- Computes: Structural indicators: years, document types, sources and Bradford zones, conference series, citations, open access, funding, validation against WoS; data of figure 3
- Inputs: Scopus full export E1; WoS export for the validation (licensed)
- Outputs here: `tables/F13_2/F13_2_numbers.json`, `tables/F13_2/T1b_types_exported.csv`, `tables/F13_2/T1b_types_harmonised.csv`, `tables/F13_2/T1c_year_by_type.csv`, `tables/F13_2/T1d_periods.csv`, `tables/F13_2/T1e_authors_per_record.csv`, `tables/F13_2/T1f_language.csv`, `tables/F13_2/T1f_publication_stage.csv`, `tables/F13_2/T1g_retracted.csv`, `tables/F13_2/T2a_concentration.csv`, `tables/F13_2/T2a_sources.csv`, `tables/F13_2/T2b_top20_journals.csv`, `tables/F13_2/T2c_top20_conference_sources.csv`, `tables/F13_2/T2d_publishers.csv`, `tables/F13_2/T2e_top15_series.csv`, `tables/F13_2/T3a_citations.csv`, `tables/F13_2/T3b_citations_by_year.csv`, `tables/F13_2/T3c_citations_by_type.csv`, `tables/F13_2/T3d_citations_by_period.csv`, `tables/F13_2/T3f_top10_sources_by_citations.csv`, `tables/F13_2/T4a_open_access.csv`, `tables/F13_2/T4b_funding.csv`, `tables/F13_2/T4c_top15_funders.csv`, `tables/F13_2/T5a_types.csv`, `tables/F13_2/T5b_years.csv`, `tables/F13_2/T5c_citations.csv`, `tables/F13_2/T5d_top20_overlap.csv`, `tables/F13_2/conference_series_thesaurus.csv`, `tables/F13_2/funders_thesaurus.csv`, `figures/figure_3_output_by_type.csv`
- Programs: `f132_final.py` (closing and registry row), `f132_lib.py` (shared functions), `f132_probe.py` (exploration), `f132_report.py` (report), `f132_step0.py` (step 0: input digests and snapshot), `f132_structure.py` (computation), `f132_verify.py` (independent verifier's own code)
- Not included (CHK1 scan or declared R13 exclusion; class only): `f132_gates.py` (e-mail)

## F13.2b

- Closed: 2026-10-13 (project registry)
- Computes: Affiliations: countries per record, partner countries, international share, foreign institutions, country names
- Inputs: Affiliation fields of E1 (licensed)
- Outputs here: `tables/F13_2b/T2a_countries_per_record.csv`, `tables/F13_2b/T2b_partner_countries.csv`, `tables/F13_2b/T2c_international_share.csv`, `tables/F13_2b/T2d_partner_country_pairs.csv`, `tables/F13_2b/T2e_partner_sources.csv`, `tables/F13_2b/T3e_foreign_institutions.csv`, `tables/F13_2b/T3f_top10_partner_countries.csv`
- Programs: `f132b_affil.py` (computation), `f132b_final.py` (closing and registry row), `f132b_lib.py` (shared functions), `f132b_probe.py` (exploration), `f132b_report.py` (report), `f132b_step0.py` (step 0: input digests and snapshot), `f132b_thesaurus.py` (computation), `f132b_verify.py` (independent verifier's own code)
- Not included (CHK1 scan or declared R13 exclusion; class only): `f132b_gates.py` (e-mail)

## F13.2c

- Closed: 2026-10-13 (project registry)
- Computes: International records by author (Authors with affiliations, counts only)
- Inputs: E1 (licensed)
- Outputs here: `tables/F13_2c/T1a_parsing.csv`, `tables/F13_2c/T1b_country_check.csv`, `tables/F13_2c/T2a_international_by_author.csv`, `tables/F13_2c/T2b_first_author_country.csv`, `tables/F13_2c/T2c_partners_other_than_ukraine.csv`, `tables/F13_2c/T2d_kazakhstan_positions.csv`, `tables/F13_2c/T2e_top_partners_by_type.csv`
- Programs: `f132c_build.py` (computation), `f132c_final.py` (closing and registry row), `f132c_lib.py` (shared functions), `f132c_probe.py` (exploration), `f132c_report.py` (report), `f132c_step0.py` (step 0: input digests and snapshot), `f132c_verify.py` (independent verifier's own code)
- Not included (CHK1 scan or declared R13 exclusion; class only): `f132c_gates.py` (ORCID, e-mail)

## F13.2d

- Closed: 2026-10-13 (project registry)
- Computes: Institutions thesaurus v3: one-record spellings merged by distinctive tokens, exclusions, name-token rules
- Inputs: Affiliation fields of E1 (licensed); thesaurus v2
- Outputs here: `tables/F13_2d/T1c_exclusions.csv`, `tables/F13_2d/T1d_name_token_rules.csv`
- Programs: `f132d_build.py` (computation), `f132d_candidates.py` (computation), `f132d_final.py` (closing and registry row), `f132d_lib.py` (shared functions), `f132d_report.py` (report), `f132d_step0.py` (step 0: input digests and snapshot), `f132d_thesaurus.py` (computation), `f132d_verify.py` (independent verifier's own code)
- Not included (CHK1 scan or declared R13 exclusion; class only): `f132d_gates.py` (ORCID, e-mail)

## F13.2e

- Closed: 2026-10-13 (project registry)
- Computes: Institutions thesaurus v3.1 (author's decision 48); Kazakhstan institutions, concentration, institution pairs, collaboration types by period
- Inputs: Affiliation fields of E1 (licensed); thesaurus v3
- Outputs here: `tables/F13_2e/T1_thesaurus_v31_changes.csv`, `tables/F13_2e/T2f2_v31_collaboration_by_period.csv`, `tables/F13_2e/T2g_v31_authors_by_collaboration.csv`, `tables/F13_2e/T3a_v31_kz_institutions.csv`, `tables/F13_2e/T3c_v31_concentration.csv`, `tables/F13_2e/T3d_v31_kz_institution_pairs.csv`, `tables/F13_2e/institutions_thesaurus_v31.csv`
- Programs: `f132e_build.py` (computation), `f132e_final.py` (closing and registry row), `f132e_lib.py` (shared functions), `f132e_report.py` (report), `f132e_step0.py` (step 0: input digests and snapshot), `f132e_thesaurus.py` (computation), `f132e_verify.py` (independent verifier's own code)
- Not included (CHK1 scan or declared R13 exclusion; class only): `f132e_gates.py` (ORCID, e-mail)

## F13.3

- Closed: 2026-10-13 (project registry)
- Computes: Citation structure of the reference lists with bibliometrix 5.5.0 in R: reference counts, Scopus against WoS, reference age, reference publication year spectroscopy
- Inputs: Reference field of E1 (licensed); the 216 WoS pairs
- Outputs here: `tables/F13_3/T0a_reference_counts.csv`, `tables/F13_3/T0b_pairs_scopus_vs_wos.csv`, `tables/F13_3/T0c_references_by_period_and_type.csv`, `tables/F13_3/T1_reference_age.csv`, `tables/F13_3/T1a_age_distribution.csv`, `tables/F13_3/T1b_rpys.csv`, `tables/F13_3/T1c_rpys_peaks.csv`
- Programs: `f133_env.R` (computation), `f133_final.py` (closing and registry row), `f133_lib.R` (shared functions), `f133_lib.py` (shared functions), `f133_main.R` (computation), `f133_probe.R` (exploration), `f133_probe2.R` (computation), `f133_probe3.R` (computation), `f133_report.py` (report), `f133_sources_thesaurus.R` (computation), `f133_step0.py` (step 0: input digests and snapshot), `f133_verify.py` (independent verifier's own code)
- Not included (CHK1 scan or declared R13 exclusion; class only): `f133_gates.py` (e-mail)

## F13.3b

- Closed: 2026-10-13 (project registry)
- Computes: Work key as the main line: cited works, local citations, bibliographic coupling and co-citation clusters, cited sources
- Inputs: Reference field of E1 (licensed); F13.3's R functions
- Outputs here: `tables/F13_3b/T0_strings_vs_work_key.csv`, `tables/F13_3b/T1a_key_coverage.csv`, `tables/F13_3b/T1b2_collision_counts.csv`, `tables/F13_3b/T1c_key_sensitivity.csv`, `tables/F13_3b/T2a_thresholds.csv`, `tables/F13_3b/T3a_local_citations_title.csv`, `tables/F13_3b/T3b_local_citations_by_period.csv`, `tables/F13_3b/T4a_coupling_workkey.csv`, `tables/F13_3b/T4b_coupling_clusters.csv`, `tables/F13_3b/T4c_coupling_sensitivity.csv`, `tables/F13_3b/T5a_cocitation_workkey.csv`, `tables/F13_3b/T5c_cocitation_sensitivity.csv`, `tables/F13_3b/T6a2_sources_summary.csv`, `tables/F13_3b/T6a_sources_parse_rule.csv`
- Programs: `f133b_final.py` (closing and registry row), `f133b_keys.R` (computation), `f133b_lib.py` (shared functions), `f133b_main.py` (computation), `f133b_report.py` (report), `f133b_step0.py` (step 0: input digests and snapshot), `f133b_verify.py` (independent verifier's own code)
- Not included (CHK1 scan or declared R13 exclusion; class only): `f133b_gates.py` (e-mail)

## F13.4

- Closed: 2026-10-13 (project registry)
- Computes: Growth and normalised activity: yearly counts, log-linear growth, activity index with bootstrap intervals; data of figure 1
- Inputs: Years of E1; Scopus 'Analyze search results' year series (data/year_series)
- Outputs here: `tables/F13_4/T1a_years.csv`, `tables/F13_4/T1b_periods.csv`, `tables/F13_4/T1c_loglinear_fit.csv`, `tables/F13_4/T1d_recent_weight.csv`, `tables/F13_4/T2b_activity_index_periods.csv`, `tables/F13_4/T2d_activity_index_windows.csv`, `tables/F13_4/T3c_growth_by_country.csv`, `figures/figure_1_normalised_growth.csv`
- Programs: `f134_final.py` (closing and registry row), `f134_growth.py` (computation), `f134_lib.py` (shared functions), `f134_registry.py` (registry row), `f134_report.py` (report), `f134_step0.py` (step 0: input digests and snapshot), `f134_verify.py` (independent verifier's own code)
- Not included (CHK1 scan or declared R13 exclusion; class only): `f134_gates.py` (e-mail)

## F13.4b

- Closed: 2026-10-13 (project registry)
- Computes: Activity index of five countries from the all-output series; data of figure 2
- Inputs: Year series (data/year_series)
- Outputs here: `tables/F13_4b/T4a_activity_index_five_countries.csv`, `tables/F13_4b/T4c_ranking.csv`, `tables/F13_4b/T4d_without_2025.csv`, `figures/figure_2_activity_index.csv`
- Programs: `f134b_final.py` (closing and registry row), `f134b_index.py` (computation), `f134b_lib.py` (shared functions), `f134b_registry.py` (registry row), `f134b_report.py` (report), `f134b_step0.py` (step 0: input digests and snapshot), `f134b_verify.py` (independent verifier's own code)
- Not included (CHK1 scan or declared R13 exclusion; class only): `f134b_gates.py` (e-mail)

## F13.5

- Closed: 2026-10-13 (project registry)
- Computes: Co-word maps of author and index keywords with keyword thesaurus v4; clusters, periods, blind spots; data of figure 5
- Inputs: Keyword fields of E1 (licensed); thesaurus v3
- Outputs here: `tables/F13_5/D4_versions_summary.csv`, `tables/F13_5/F13_5_numbers.json`, `tables/F13_5/S1_partition_agreement.csv`, `tables/F13_5/S2_algorithm_sensitivity.csv`, `tables/F13_5/T2_author_threshold_sensitivity.csv`, `tables/F13_5/T3_author_nodes.csv`, `tables/F13_5/T5_author_cluster_top10.csv`, `tables/F13_5/T5_author_clusters.csv`, `tables/F13_5/T6_author_keywords_by_period.csv`, `tables/F13_5/T7_blind_spots_keywords.csv`, `tables/F13_5/T8_title_bigrams_vs_keywords.csv`, `tables/F13_5/thesaurus.csv`, `figures/figure_5_coword_edges.csv`, `figures/figure_5_coword_nodes.csv`
- Programs: `f135_candidates.py` (computation), `f135_coword.py` (computation), `f135_delta.py` (computation), `f135_final.py` (closing and registry row), `f135_lib.py` (shared functions), `f135_probe.py` (exploration), `f135_registry.py` (registry row), `f135_report.py` (report), `f135_residual.py` (computation), `f135_stability.py` (computation), `f135_step0.py` (step 0: input digests and snapshot), `f135_verify.py` (independent verifier's own code)
- Not included (CHK1 scan or declared R13 exclusion; class only): `f135_gates.py` (e-mail)

## F13.6b

- Closed: 2026-10-13 (project registry)
- Computes: Derived numbers of the manuscript (S4) from closed phases' tables; the same program wrote the text draft from a template that is not included
- Inputs: Closed phases' tables
- Outputs here: `tables/F13_6b/S4_derived_numbers.csv`
- Programs: `f136b_build.py` (computation), `f136b_final.py` (closing and registry row), `f136b_lib.py` (shared functions), `f136b_report.py` (report), `f136b_step0.py` (step 0: input digests and snapshot)
- Not included (CHK1 scan or declared R13 exclusion; class only): `f136b_gates.py` (ORCID, e-mail), `f136b_verify.py` (ORCID)

## F13.7a

- Closed: 2026-10-13 (project registry)
- Computes: Collaboration figure redrawn on thesaurus v3.1 (data of figure 4); workbook tools reused by F13.7c
- Inputs: F13.2e tables
- Outputs here: `figures/figure_4_collaboration_v31.csv`
- Programs: `f137a_corrections.py` (computation), `f137a_figures.py` (computation), `f137a_final.py` (closing and registry row), `f137a_lib.py` (shared functions), `f137a_render.py` (computation), `f137a_report.py` (report), `f137a_step0.py` (step 0: input digests and snapshot), `f137a_verify.py` (independent verifier's own code), `f137a_workbook.py` (computation)
- Not included (CHK1 scan or declared R13 exclusion; class only): `f137a_gates.py` (e-mail)

## F13.7c

- Closed: 2026-10-13 (project registry)
- Computes: Supplementary workbook v2 (116 sheets) and the figure set; R13 forms of the cited-works tables (first authors withheld where they are corpus authors)
- Inputs: Closed phases' tables and figures; E1 author names (memory only, for the withholding)
- Outputs here: `tables/F13_7c/S13d_top30_works.csv`, `tables/F13_7c/S13h_top20_LCS.csv`, `tables/F13_7c/S13m_cocitation_clusters.csv`, `tables/F13_7c/S1_queries.csv`, `tables/F13_7c/S6c_pairs_v31_top30.csv`, `tables/F13_7c/S8s_top20_cited.csv`, `tables/F13_7c/phase_log_from_registry.csv`
- Programs: `f137c_figures.py` (computation), `f137c_final.py` (closing and registry row), `f137c_lib.py` (shared functions), `f137c_report.py` (report), `f137c_step0.py` (step 0: input digests and snapshot), `f137c_verify.py` (independent verifier's own code), `f137c_workbook.py` (computation)
- Edited copy: `f137c_lib.py` - three corpus surnames in one docstring replaced by `<surname>` (R13); the code is unchanged (its AST without docstrings equals the original's).
- Not included (CHK1 scan or declared R13 exclusion; class only): `f137c_gates.py` (ORCID, e-mail)
