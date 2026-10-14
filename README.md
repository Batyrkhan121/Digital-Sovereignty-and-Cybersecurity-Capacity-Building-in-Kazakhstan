# Digital Sovereignty and Cybersecurity Capacity Building in Kazakhstan: A Multi-Source Bibliometric Analysis, 2003–2025

Data and code for the manuscript of this title, submitted to Journal of Cyber Policy, 2026.

## Authors

Batyrkhan Abylkan, Darkan Serik, Syrym Sapash, Ademi Tursynkozha, Saule Amanzholova, Dauren Sagidullauly, Zhantore Yermukhanbetov, Aliya Kanatova

## Data sources

From the manuscript, section *Data sources and search strategy* (verbatim):

> *Corpus.* The corpus is a full export of Scopus records retrieved on 13 October 2026 with the query `TITLE-ABS-KEY(cybersecurity OR "information security" OR "cyber defense" OR "cyber defence" OR "network security" OR cryptography) AND AFFILCOUNTRY(kazakhstan) AND PUBYEAR > 2002 AND PUBYEAR < 2026`, that is, documents with at least one affiliation in Kazakhstan published in 2003–2025. The query returned 841 records with 841 distinct Scopus identifiers. They were exported with every field group the interface offers, cited references included, without truncation, in 45 columns. Throughout the article, ‘the corpus’ means these records (Scopus, 841 records, retrieved 13 October 2026).
>
> *Validation source.* Web of Science Core Collection was searched on the same day with `TS=(cybersecurity OR "information security" OR "cyber defense" OR "cyber defence" OR "network security" OR cryptography) AND CU=(Kazakhstan) AND PY=(2003-2025)`, which returned 231 records. Records were paired with the corpus one to one, first by DOI and then by normalized title: 184 pairs by DOI and 32 by title, 216 in all. Thus 93.5% of the Web of Science records are also in the corpus. The 15 records found only in Web of Science, 12 proceedings papers and 3 articles, were not added to the corpus, while 625 corpus records have no counterpart in Web of Science. Web of Science therefore checks the corpus rather than extending it.

The coverage comparison with OpenAlex (`data/openalex_union.csv`) used a title-only version of the corpus query, run in Scopus and OpenAlex on 4 September 2026. The yearly 'Analyze search results' counts and their queries are in `data/year_series/` (`manifest_year_series.json`).

## What is here

| Folder | Files | Contents |
|---|---|---|
| `data/` | 16 | Record identifiers: `corpus_identifiers.csv` (841 Scopus records: eid, doi, year, document_type), `wos_pairs.csv` (216 Scopus-WoS pairs: scopus_eid, wos_ut, year), `openalex_union.csv` (309 records of the equal-query comparison: scopus_eid, openalex_id, doi, year, set); `year_series/` (eleven Scopus interface year series, their long form and manifest) |
| `thesauri/` | 3 | Keyword thesaurus v4, institutions thesaurus v3.1, country names |
| `tables/` | 126 | Aggregated tables by phase, one folder per phase: every table the manuscript's numbers cite and every source of the supplementary workbook; `INDEX.csv` says what each holds, its rows, its source and sha256, and how many numbers of the manuscript draft's evidence index point to it |
| `figures/` | 14 | The six figures (PNG), their data (CSV) and `captions.txt` |
| `supplementary/` | 1 | `Supplementary_tables.xlsx` (the supplementary workbook) |
| `code/` | 117 | Programs of the phases that produced the tables; `code/INDEX.md` |

`MANIFEST.csv` lists every file with its size, sha256, source and class.

## What is not distributed

Abstracts, reference lists, affiliations, author names and keywords of the records are not distributed: the Scopus and Web of Science licences do not permit it. The thesauri list keyword and institution-name spellings and the forms they map to, without links to records; the cited-works tables withhold first authors who are corpus authors.

Reproduction needs your own exports: Scopus records by the identifiers in `data/corpus_identifiers.csv` (EID), Web of Science records by `data/wos_pairs.csv` (UT). The programs in `code/` read these exports by local paths and do not run without them (see `code/INDEX.md`).

## How to cite

Abylkan, B., Serik, D., Sapash, S., Tursynkozha, A., Amanzholova, S., Sagidullauly, D., Yermukhanbetov, Z., & Kanatova, A. (2026). Digital Sovereignty and Cybersecurity Capacity Building in Kazakhstan: A Multi-Source Bibliometric Analysis, 2003–2025. Submitted to Journal of Cyber Policy. DOI: [[AUTHOR: DOI after acceptance]]

## Licences

Code: MIT (`LICENSE`). Derived tables, thesauri and figure data: CC BY 4.0 (`LICENSE-DATA.md`); record identifiers are facts, and the rights in the databases remain with Elsevier, Clarivate and OpenAlex.

The authors may replace these licences before publication.

Folder assembled on 2026-10-14.
