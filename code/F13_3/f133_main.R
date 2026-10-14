# Phase F13.3 - steps 1-7 on the frame E1 with bibliometrix 5.5.0 (R). No network. Writes tables/, data/, figures/ and
# F13_3_numbers.json under the phase folder, or under --out=<dir> (the second run of gate G4). Prints counts only: no record
# contents, no corpus author names, no reference texts. Corpus records in tables carry DOI/EID, year, source, title and counts;
# cited works carry first-author surname, year, title (<= 15 words) and source; full reference strings go to data/ only.
.f <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))))
source(file.path(.f, "f133_lib.R"))
source(file.path(.f, "f133_sources_thesaurus.R"))
suppressPackageStartupMessages(library(ggplot2))
P <- f133_paths()
a <- commandArgs(trailingOnly = TRUE)
OUT <- if (length(a) && startsWith(a[1], "--out=")) sub("^--out=", "", a[1]) else P$phase
TAB <- file.path(OUT, "tables"); DAT <- file.path(OUT, "data"); FIG <- file.path(OUT, "figures")
for (d in c(TAB, DAT, FIG)) dir.create(d, recursive = TRUE, showWarnings = FALSE)
NUM <- list()
ord <- function(...) order(..., method = "radix")
tab <- function(df, name) write_csv_lf(df, file.path(TAB, paste0(name, ".csv")))
cnt <- function(x) { t <- table(x); data.frame(item = names(t), n = as.integer(t)) }
tc_name <- function(s) gsub("(^|[ \\-'\u2019])(\\p{Ll})", "\\1\\U\\2", tolower(s), perl = TRUE)
relabel <- function(m, ids) {
  m <- as.character(m)
  k <- data.frame(c = unique(m))
  k$n <- vapply(k$c, function(x) sum(m == x), integer(1))
  k$first <- vapply(k$c, function(x) sort(ids[m == x], method = "radix")[1], character(1))
  o <- ord(-k$n, k$first)
  unname(setNames(seq_along(o), k$c[o])[m])
}
eid_of <- function(ut) tolower(ut)
doi_or_eid <- function(i) ifelse(!is.na(M$DI[i]) & nzchar(M$DI[i]), M$DI[i], eid_of(M$UT[i]))
save_plot <- function(name, draw, w = 8, h = 6.5) {
  grDevices::png(file.path(FIG, paste0(name, ".png")), width = w, height = h, units = "in", res = 300)
  draw(); invisible(grDevices::dev.off())
  grDevices::pdf(file.path(FIG, paste0(name, ".pdf")), width = w, height = h, useDingbats = FALSE)
  draw(); invisible(grDevices::dev.off())
}

## ---- Step 1: load, R13 drop, CR repair (T0) ----
S <- build_M(P)
M <- S$M
stopifnot(nrow(M) == 841, all(c("TI", "PY", "SO", "DE", "ID", "CR", "DI", "TC") %in% names(M)), !anyDuplicated(M$UT))
n_ref <- lengths(S$refs); n_frag <- S$fx$n_frag; n_bi <- S$n_builtin
split_back <- vapply(strsplit(M$CR, ";", fixed = TRUE), function(v) sum(nzchar(trim_u(v))), integer(1))
stopifnot(identical(split_back, n_ref))
frag_all <- trim_u(unlist(strsplit(S$M_before$CR, "; ", fixed = TRUE))); frag_all <- frag_all[nzchar(frag_all)]
cf <- frag_all[!grepl(",", frag_all, fixed = TRUE)]
cf_short <- cf[nchar(cf) <= 24]
lit <- suppressWarnings(grepl("(*UCP)^(?:[A-Z][\\w'\u2019\\-\\.]*\\s?)+[A-Z]\\.(?:\\s?[A-Z]\\.)*$", cf_short, perl = TRUE))
pos <- function(x) x[x > 0]
T0a <- data.frame(
  measure = c("references, total", "references per record - median (records with references)", "references per record - max",
              "records with references", "records without references"),
  F13_3_corrected = c(sum(n_ref), med(pos(n_ref)), max(n_ref), sum(n_ref > 0), sum(n_ref == 0)),
  F13_1_method_fragments_recomputed = c(sum(n_frag), med(pos(n_frag)), max(n_frag), sum(n_frag > 0), sum(n_frag == 0)),
  F13_1_published_replaced = c("79686", "67", "", "", ""),
  bibliometrix_5_5_builtin_repair = c(sum(n_bi), med(pos(n_bi)), max(n_bi), sum(n_bi > 0), sum(n_bi == 0)))
tab(T0a, "T0a_reference_counts")
T0a2 <- data.frame(measure = c(
  "fragments in the exported cells ('; ', non-empty) - the F13.1 count",
  "fragments after convert2df with bibliometrix's own repair switched off",
  "fragments without a comma", "of them author-shaped (glued to the next fragment)",
  "trailing author buffers kept as references of their own",
  "author buffers followed by a fragment without a comma",
  "references with an inner ';' (turned into ',')", "references emptied by the per-reference cleaning",
  "comma-free fragments of <= 24 characters checked against the literal pattern", "of them: literal and linear pattern disagree",
  "records whose count differs between the brief's rule and bibliometrix's built-in repair"),
  value = c(sum(n_frag), sum(S$frag_import), length(cf), sum(is_author(cf)), sum(S$fx$n_tail), sum(S$fx$n_nocomma_body),
            S$inner_semicolon, S$emptied, length(cf_short), sum(lit != is_author(cf_short)), sum(n_bi != n_ref)))
tab(T0a2, "T0a2_repair_diagnostics")
W <- load_e2_nr(P$E2)
pr <- utils::read.csv(P$pairs, colClasses = "character")
im <- match(toupper(pr$eid), M$UT); iw <- match(toupper(pr$ut), toupper(W$UT))
stopifnot(nrow(pr) == 216, !anyNA(im), !anyNA(iw))
sc <- n_ref[im]; wn <- as.integer(W$NR[iw]); dfp <- sc - wn
T0b <- data.frame(measure = c("pairs (eid <-> ut, F13.1 T3a)", "Scopus references (corrected) - median", "WoS NR - median",
                              "equal", "|difference| <= 2", "Scopus > WoS", "WoS > Scopus", "Scopus references - sum", "WoS NR - sum",
                              "median of (Scopus - WoS)", "F13.1 method: Scopus fragments - median (recomputed)",
                              "F13.1 T3d as published (replaced): Scopus median 88, WoS NR median 30"),
                  value = c(nrow(pr), med(sc), med(wn), sum(dfp == 0), sum(abs(dfp) <= 2), sum(dfp > 0), sum(dfp < 0), sum(sc), sum(wn),
                            med(dfp), med(n_frag[im]), "88 / 30"))
tab(T0b, "T0b_pairs_scopus_vs_wos")
per <- period_of(M$PY)
grp_rows <- function(kind, g) do.call(rbind, lapply(sort(unique(g), method = "radix"), function(v) {
  i <- which(g == v)
  data.frame(group_kind = kind, group = v, records = length(i), records_with_references = sum(n_ref[i] > 0),
             references = sum(n_ref[i]), median_per_record = med(pos(n_ref[i])), mean_per_record = r4(mean(n_ref[i]), 2))
}))
T0c <- rbind(grp_rows("period", per), grp_rows("document type (as exported)", M$DT), grp_rows("all", rep("all records", nrow(M))))
tab(T0c, "T0c_references_by_period_and_type")
# control: citations() before and after the repair (top 5 each; strings shorter than 30 words)
top_tab <- function(t, k = 5) { d <- data.frame(s = names(t), n = as.integer(t)); d <- d[lengths(strsplit(d$s, "\\s+")) < 30, ]; head(d[ord(-d$n, d$s), ], k) }
fr_t <- top_tab(table(frag_all))
cb <- citations(S$M_before, field = "article", sep = ";")$Cited
ca <- citations(M, field = "article", sep = ";")$Cited
cb_t <- top_tab(cb); ca_t <- top_tab(ca)
pb <- ref_parts(cb_t$s); pa <- ref_parts(ca_t$s)
T0d <- rbind(
  data.frame(block = "unrepaired: most frequent '; ' fragments", rank = 1:5, name_segment = fr_t$s, year = "", title = "", n = fr_t$n),
  data.frame(block = "unrepaired: citations(field = 'article') - first segment = last author of the work", rank = 1:5,
             name_segment = pb$first_author, year = ref_year(cb_t$s), title = cut_words(pb$title, 10), n = cb_t$n),
  data.frame(block = "repaired: citations(field = 'article')", rank = 1:5, name_segment = pa$first_author, year = ref_year(ca_t$s),
             title = cut_words(pa$title, 10), n = ca_t$n))
tab(T0d, "T0d_citations_before_after")
write_csv_lf(data.frame(eid = eid_of(M$UT), n_fragments = n_frag, n_references = n_ref, trailing_buffer = S$fx$n_tail,
                        references_repaired = M$CR)[ord(eid_of(M$UT)), ], file.path(DAT, "references_repaired.csv"))
NUM$T0 <- list(references = sum(n_ref), median = med(pos(n_ref)), max = max(n_ref), with_refs = sum(n_ref > 0), fragments_exported = sum(n_frag),
               fragments_import = sum(S$frag_import), tails = sum(S$fx$n_tail), nocomma_bodies = sum(S$fx$n_nocomma_body),
               builtin = sum(n_bi), builtin_median = med(pos(n_bi)), builtin_records_differ = sum(n_bi != n_ref),
               inner_semicolon = S$inner_semicolon, literal_disagree = sum(lit != is_author(cf_short)),
               pairs_scopus_median = med(sc), pairs_wos_median = med(wn), pairs_equal = sum(dfp == 0), pairs_within2 = sum(abs(dfp) <= 2),
               pairs_scopus_more = sum(dfp > 0), pairs_wos_more = sum(dfp < 0), pairs_scopus_sum = sum(sc), pairs_wos_sum = sum(wn),
               r13_dropped_named = S$dropped_named, r13_dropped_all = length(S$dropped), columns_kept = sort(names(M), method = "radix"))
cat("step 1: references", sum(n_ref), "| fragments", sum(n_frag), "| pairs medians", med(sc), med(wn), "\n")

## ---- Step 2: reference age (T1) and RPYS (T1b) ----
yr <- lapply(S$refs, ref_year)
age <- mapply(function(y, py) py - y, yr, M$PY, SIMPLIFY = FALSE)
bins <- c("< 0", "0-2", "3-5", "6-10", "11-15", "> 15")
bin_of <- function(x) ifelse(x < 0, bins[1], ifelse(x <= 2, bins[2], ifelse(x <= 5, bins[3], ifelse(x <= 10, bins[4], ifelse(x <= 15, bins[5], bins[6])))))
T1 <- NULL; T1a <- NULL
for (p in c(PERIODS, "all")) {
  i <- if (p == "all") seq_len(nrow(M)) else which(per == p)
  ag <- unlist(age[i]); dated <- ag[!is.na(ag)]
  T1 <- rbind(T1, data.frame(period = p, records = length(i), references = sum(n_ref[i]), references_with_year = length(dated),
                             share_with_year = r4(length(dated) / sum(n_ref[i])), median_age = med(dated),
                             price_index = r4(mean(dated <= 5)), share_older_than_15 = r4(mean(dated > 15)),
                             later_than_citing_record = sum(dated < 0)))
  bb <- table(factor(bin_of(dated), levels = bins))
  T1a <- rbind(T1a, data.frame(period = p, age_bin = bins, references = as.integer(bb), share = r4(as.integer(bb) / length(dated))))
}
tab(T1, "T1_reference_age"); tab(T1a, "T1a_age_distribution")
RP <- rpys(M, sep = ";", graph = FALSE)
rt <- as.data.frame(RP$rpysTable)
rt <- rt[ord(rt$Year), ]
# peaks as rpys() marks them: diffMedian above both neighbours (first and last year excluded), the ten highest
nr <- nrow(rt); dm <- rt$diffMedian
pk <- which(c(FALSE, dm[2:(nr - 1)] > dm[1:(nr - 2)] & dm[2:(nr - 1)] > dm[3:nr], FALSE))
pk <- pk[ord(-dm[pk], rt$Year[pk])]
pk <- head(pk, 10)
T1b <- data.frame(year = rt$Year, citations = rt$Citations, dev_median5_backward = rt$diffMedian5, dev_median_centered = rt$diffMedian2,
                  dev_plotted = rt$diffMedian, peak_rank = "")
T1b$peak_rank[pk] <- seq_along(pk)
tab(T1b, "T1b_rpys")
save_plot("Fig_rpys", function() {
  graphics::par(mar = c(4, 4.2, 2, 1))
  yl <- range(c(rt$Citations, rt$diffMedian))
  plot(rt$Year, rt$Citations, type = "l", lwd = 1.2, col = "black", ylim = yl, xlab = "Publication year of the cited reference",
       ylab = "Cited references", main = "Reference publication year spectroscopy (rpys, bibliometrix; E1 841 records)")
  graphics::lines(rt$Year, rt$diffMedian, col = "firebrick", lwd = 1.2)
  graphics::abline(h = 0, col = "grey70", lty = 3)
  graphics::points(rt$Year[pk], rt$diffMedian[pk], pch = 19, col = "#D6604D", cex = 0.8)
  graphics::text(rt$Year[pk], rt$diffMedian[pk], labels = rt$Year[pk], pos = 3, cex = 0.6, col = "#D6604D")
  graphics::legend("topleft", legend = c("cited references per year", "deviation from the centred 5-year median"),
                   col = c("black", "firebrick"), lwd = 1.2, cex = 0.7, bty = "n")
})
rcr <- as.data.frame(RP$CR)
write_csv_lf(rcr[ord(rcr$Year, rcr$Reference), c("Year", "Reference", "Freq")], file.path(DAT, "rpys_cited_references_by_year.csv"))
NUM$T1 <- list(all = as.list(T1[T1$period == "all", ]), rpys_span = range(rt$Year), rpys_peaks = rt$Year[pk])

## ---- Step 3: most cited works (T2) ----
items <- lapply(strsplit(M$CR, ";", fixed = TRUE), function(l) { l <- l[grepl(",", l, fixed = TRUE)]; l <- l[nchar(l) >= 3]; sub("^\\s+", "", l) })
citing <- table(unlist(lapply(items, unique)))
cd <- data.frame(ref = names(ca), occurrences = as.integer(ca))
cd$citing_records <- as.integer(citing[cd$ref])
stopifnot(!anyNA(cd$citing_records), sum(cd$occurrences) == length(unlist(items)))
cd <- cd[ord(-cd$citing_records, -cd$occurrences, cd$ref), ]
pp <- ref_parts(cd$ref)
cd$year <- ref_year(cd$ref); cd$first_author <- pp$first_author; cd$title <- pp$title; cd$source <- pp$source
write_csv_lf(cd, file.path(DAT, "cited_references.csv"))
t2 <- head(cd, 30)
T2 <- data.frame(rank = 1:30, first_author = tc_name(t2$first_author), year = t2$year, title = cut_words(t2$title, 15),
                 source = cut_words(t2$source, 15), citing_records = t2$citing_records, occurrences = t2$occurrences)
tab(T2, "T2_top30_cited_works")
T2a <- data.frame(measure = c("distinct cited references (strings counted by citations())", "with >= 2 citing records",
                              "with >= 5 citing records", "with >= 10 citing records",
                              "references without a comma (not counted by citations(field = 'article'))",
                              "references cited more than once within one record (occurrences - citing records)"),
                  value = c(nrow(cd), sum(cd$citing_records >= 2), sum(cd$citing_records >= 5), sum(cd$citing_records >= 10),
                            sum(n_ref) - sum(cd$occurrences), sum(cd$occurrences) - sum(cd$citing_records)))
# own-code sensitivity: the same references grouped by a work key (first-author surname + year + six title words)
allref <- lapply(strsplit(M$CR, ";", fixed = TRUE), function(l) { l <- sub("^\\s+", "", l); l[nchar(l) > 10] })
uref <- sort(unique(unlist(allref)), method = "radix")
ukey <- work_key(uref)
rec_keys <- lapply(allref, function(l) unique(ukey[match(l, uref)]))
wk <- table(unlist(rec_keys))
wd <- data.frame(key = names(wk), citing_records = as.integer(wk))
occ_all <- table(unlist(allref))
vt <- data.frame(ref = uref, key = ukey, occurrences = as.integer(occ_all[uref]))
vt <- vt[ord(vt$key, -vt$occurrences, vt$ref), ]
wd$variants <- as.integer(table(vt$key)[wd$key])
wd$representative <- vt$ref[!duplicated(vt$key)][match(wd$key, vt$key[!duplicated(vt$key)])]
wd <- wd[ord(-wd$citing_records, wd$key), ]
w30 <- head(wd, 30); wp <- ref_parts(w30$representative)
t2key <- work_key(t2$ref)
T2b <- data.frame(rank = 1:30, first_author = tc_name(wp$first_author), year = ref_year(w30$representative), title = cut_words(wp$title, 15),
                  source = cut_words(wp$source, 15), citing_records = w30$citing_records, string_variants = w30$variants,
                  T2_rank = vapply(w30$key, function(k) paste(which(t2key == k), collapse = " "), character(1)))
tab(T2b, "T2b_top30_cited_works_work_key")
T2a <- rbind(T2a, data.frame(measure = c("work key (own code): distinct works", "work key: works with >= 2 citing records",
                                         "work key: works with >= 5 citing records", "work key: works with >= 10 citing records",
                                         "work key: T2 top-30 rows whose work is in the work-key top-30"),
                             value = c(nrow(wd), sum(wd$citing_records >= 2), sum(wd$citing_records >= 5), sum(wd$citing_records >= 10),
                                       sum(t2key %in% w30$key))))
tab(T2a, "T2a_cited_thresholds")
pk_t2 <- vapply(rt$Year[pk], function(y) paste(T2$rank[!is.na(T2$year) & T2$year == y], collapse = " "), character(1))
wd$year <- ref_year(wd$representative)
pk_top <- lapply(rt$Year[pk], function(y) { j <- which(!is.na(wd$year) & wd$year == y)[1]
  if (is.na(j)) c("", "", "") else { q <- ref_parts(wd$representative[j]); c(tc_name(q$first_author), cut_words(q$title, 10), wd$citing_records[j]) } })
T1c <- data.frame(peak_rank = seq_along(pk), year = rt$Year[pk], citations = rt$Citations[pk], dev_median_centered = rt$diffMedian2[pk],
                  dev_median5_backward = rt$diffMedian5[pk],
                  distinct_cited_works_of_year = vapply(rt$Year[pk], function(y) sum(as.character(rcr$Year) == as.character(y)), integer(1)),
                  T2_ranks_of_that_year = pk_t2, top_work_first_author = vapply(pk_top, `[`, "", 1),
                  top_work_title = vapply(pk_top, `[`, "", 2), top_work_citing_records = vapply(pk_top, `[`, "", 3))
tab(T1c, "T1c_rpys_peaks")
NUM$T2 <- list(distinct = nrow(cd), ge2 = sum(cd$citing_records >= 2), ge5 = sum(cd$citing_records >= 5), ge10 = sum(cd$citing_records >= 10),
               top1_citing = t2$citing_records[1], top30_min = t2$citing_records[30],
               work_key = list(works = nrow(wd), ge2 = sum(wd$citing_records >= 2), ge5 = sum(wd$citing_records >= 5),
                               ge10 = sum(wd$citing_records >= 10), top1_citing = w30$citing_records[1], overlap_T2 = sum(t2key %in% w30$key)))
cat("step 2-3: dated share", T1$share_with_year[T1$period == "all"], "| distinct cited", nrow(cd), "\n")

## ---- Step 4: cited sources (T3) ----
M <- metaTagExtraction(M, Field = "CR_SO", sep = ";")
so <- lapply(M$CR_SO, function(s) if (is.na(s)) character(0) else { v <- trim_u(strsplit(s, ";", fixed = TRUE)[[1]]); v[nzchar(v)] })
# a person's name returned as a 'source': ONE surname token followed by one to three initials (abbreviated journal titles
# such as 'IEEE COMMUN. MAG.' or 'IEEE INTERNET THINGS J.' have several tokens and are kept)
name_shaped <- function(x) grepl("^[A-Z][A-Z'’\\-]+ (?:[A-Z]{1,2}\\.\\s?){1,3}$", x, perl = TRUE) | grepl("^[A-Z][A-Z'’\\-]+ [A-Z]{1,2}$", x, perl = TRUE)
n_name <- sum(name_shaped(unlist(so)))
so <- lapply(so, function(v) v[!name_shaped(v)])
th <- setNames(SOURCES_THESAURUS$canonical, SOURCES_THESAURUS$variant)
changed <- table(factor(unlist(so)[unlist(so) %in% names(th)], levels = SOURCES_THESAURUS$variant))
so_th <- lapply(so, function(v) unname(ifelse(v %in% names(th), th[v], v)))
tab(data.frame(SOURCES_THESAURUS, items_changed = as.integer(changed)), "cited_sources_thesaurus")
sref <- table(unlist(so_th)); srec <- table(unlist(lapply(so_th, unique)))
sd <- data.frame(source = names(sref), references = as.integer(sref)); sd$citing_records <- as.integer(srec[sd$source])
s1 <- head(sd[ord(-sd$references, -sd$citing_records, sd$source), ], 30)
s2 <- head(sd[ord(-sd$citing_records, -sd$references, sd$source), ], 30)
tab(data.frame(rank = 1:30, source = cut_words(s1$source, 20), references = s1$references, citing_records = s1$citing_records), "T3a_top30_sources_by_references")
tab(data.frame(rank = 1:30, source = cut_words(s2$source, 20), citing_records = s2$citing_records, references = s2$references), "T3b_top30_sources_by_records")
n_rec_src <- length(unlist(so_th))
ps <- ref_parts(unlist(S$refs))$source
ps <- unname(ifelse(ps %in% names(th), th[ps], ps)); ps <- ps[nzchar(ps) & !name_shaped(ps)]
pst <- table(ps); pst <- data.frame(source = names(pst), n = as.integer(pst)); p30 <- head(pst[ord(-pst$n, pst$source), ], 30)
T3c <- data.frame(measure = c("references, total", "references with a source recognised by metaTagExtraction(CR_SO)",
                              "share of all references", "CR_SO items shaped like a person's name - one surname and initials (unrecognised)",
                              "distinct sources (after the thesaurus)", "items changed by the thesaurus",
                              "share of all references on the top-30 sources (by references)", "share of recognised references on the top-30",
                              "cross-check: references with a source by the brief's parse rule (segment after the title)",
                              "cross-check: top-30 sources by that rule also in T3a"),
                  value = c(sum(n_ref), n_rec_src, r4(n_rec_src / sum(n_ref)), n_name, nrow(sd), sum(changed),
                            r4(sum(s1$references) / sum(n_ref)), r4(sum(s1$references) / n_rec_src), length(ps), sum(p30$source %in% s1$source)))
tab(T3c, "T3c_cited_sources_summary")
NUM$T3 <- list(recognised = n_rec_src, share = r4(n_rec_src / sum(n_ref)), name_shaped = n_name, distinct = nrow(sd), changed = sum(changed),
               top30_share_all = r4(sum(s1$references) / sum(n_ref)), top1 = s1$source[1], top1_refs = s1$references[1])

## ---- Step 5: local citations (T4) and historiograph ----
LC <- localCitations(M, sep = ";")
stopifnot(identical(LC$M$UT, M$UT))
LCS <- as.integer(LC$M$LCS)
H <- histNetwork(M, min.citations = 2, sep = ";")
NET <- H$NetMatrix
stopifnot(all(M$SR %in% rownames(NET)), all(M$SR %in% colnames(NET)))
NET <- NET[M$SR, M$SR]
stopifnot(all(colSums(NET) - 1 == LCS), all(diag(NET) == 1), identical(as.integer(H$LCS), LCS))
int_refs <- rowSums(NET) - 1
T4a <- data.frame(measure = c("records with LCS > 0", "share of 841", "LCS, total (local citation links)", "LCS, max", "references, total",
                              "share of references pointing inside the corpus", "records with LCS > GCS (Scopus 'Cited by')"),
                  value = c(sum(LCS > 0), r4(mean(LCS > 0)), sum(LCS), max(LCS), sum(n_ref), r4(sum(LCS) / sum(n_ref)), sum(LCS > M$TC)))
tab(T4a, "T4a_local_citations")
T4ap <- do.call(rbind, lapply(PERIODS, function(p) { i <- which(per == p)
  data.frame(period = p, records = length(i), records_with_LCS = sum(LCS[i] > 0), LCS_received = sum(LCS[i]),
             references_made = sum(n_ref[i]), internal_references_made = sum(int_refs[i]),
             share_internal = r4(sum(int_refs[i]) / sum(n_ref[i]))) }))
tab(T4ap, "T4a2_local_citations_by_period")
o4 <- ord(-LCS, -M$TC, M$UT)[1:20]
T4b <- data.frame(rank = 1:20, doi_or_eid = doi_or_eid(o4), year = M$PY[o4], source = M$SO[o4], title = cut_words(M$TI_raw[o4], 30),
                  LCS = LCS[o4], GCS = M$TC[o4])
tab(T4b, "T4b_top20_LCS")
hn <- which(LCS >= 2)
hn <- hn[ord(M$PY[hn], M$UT[hn])]
hlab <- paste0("#", seq_along(hn), ", ", M$PY[hn])
NET2 <- NET[hn, hn, drop = FALSE]; dimnames(NET2) <- list(hlab, hlab)
h_edges <- sum(NET2) - length(hn)
hr <- list(NetMatrix = NET2, histData = data.frame(Paper = hlab, Title = M$TI[hn], Author_Keywords = M$DE[hn], KeywordsPlus = M$ID[hn],
                                                    DOI = M$DI[hn], Year = M$PY[hn], LCS = LCS[hn], GCS = M$TC[hn]), M = NULL, LCS = LCS[hn])
set.seed(42)
HP <- suppressWarnings(histPlot(hr, n = length(hn), size = 3, labelsize = 2.2, verbose = FALSE))
g_h <- HP$g
g_h$layers <- Filter(function(l) !inherits(l$geom, "GeomCustomAnn"), g_h$layers)
suppressWarnings({
  ggsave(file.path(FIG, "Fig_historiograph.png"), g_h, width = 11, height = 7, dpi = 300)
  ggsave(file.path(FIG, "Fig_historiograph.pdf"), g_h, width = 11, height = 7)
})
lay_h <- as.data.frame(HP$layout)
in_plot <- hlab %in% lay_h$name
hx <- lay_h$x[match(hlab, lay_h$name)]; hy <- lay_h$y[match(hlab, lay_h$name)]
hnodes <- data.frame(label = hlab, doi_or_eid = doi_or_eid(hn), year = M$PY[hn], LCS = LCS[hn], GCS = M$TC[hn], in_plot = as.integer(in_plot),
                     x = ifelse(is.na(hx), "", r4(hx)), y = ifelse(is.na(hy), "", r4(hy)))
write_csv_lf(hnodes, file.path(FIG, "Fig_historiograph_nodes.csv"))
eh <- which(NET2 == 1, arr.ind = TRUE); eh <- eh[eh[, 1] != eh[, 2], , drop = FALSE]
hedges <- data.frame(citing = hlab[eh[, 1]], cited = hlab[eh[, 2]]); hedges <- hedges[ord(match(hedges$citing, hlab), match(hedges$cited, hlab)), ]
write_csv_lf(hedges, file.path(FIG, "Fig_historiograph_edges.csv"))
tab(hnodes[, c("label", "doi_or_eid", "year", "LCS", "GCS")], "T4c_historiograph_nodes")
gh <- graph_from_adjacency_matrix(NET2, mode = "directed", diag = FALSE)
T4c <- data.frame(measure = c("nodes (records with LCS >= 2)", "edges (citations among them)", "nodes drawn (histPlot drops isolates)",
                              "weakly connected components (isolates included)", "years spanned"),
                  value = c(length(hn), h_edges, sum(in_plot), components(gh, mode = "weak")$no, paste(range(M$PY[hn]), collapse = "-")))
tab(T4c, "T4c_historiograph_summary")
NUM$T4 <- list(lcs_pos = sum(LCS > 0), lcs_share = r4(mean(LCS > 0)), lcs_total = sum(LCS), lcs_max = max(LCS), internal_share = r4(sum(LCS) / sum(n_ref)),
               hist_nodes = length(hn), hist_edges = h_edges, hist_drawn = sum(in_plot), lcs_gt_gcs = sum(LCS > M$TC))
cat("step 5: LCS>0", sum(LCS > 0), "| LCS total", sum(LCS), "| historiograph", length(hn), "nodes", h_edges, "edges\n")

## ---- Step 6: bibliographic coupling (T5) ----
thes <- readr::read_csv(P$thes, col_types = readr::cols(.default = "c"), progress = FALSE)
kw <- lapply(M$DE_raw, function(s) { v <- tolower(trimES(trim_u(strsplit(ifelse(is.na(s), "", s), ";", fixed = TRUE)[[1]]))); v <- v[nzchar(v)]
  unique(ifelse(v %in% thes$from, thes$to[match(v, thes$from)], v)) })
NetC <- biblioNetwork(M, analysis = "coupling", network = "references", sep = ";", shortlabel = FALSE)
stopifnot(isSymmetric(NetC))
ic <- match(rownames(NetC), M$SR); stopifnot(!anyNA(ic))
graph_at <- function(A, thr, weights = NULL) {
  A <- as(as(A, "generalMatrix"), "CsparseMatrix"); diag(A) <- 0; keep <- A >= thr
  W <- if (is.null(weights)) A else as(as(weights, "generalMatrix"), "CsparseMatrix")
  W <- W * keep; W <- drop0(W)
  g <- graph_from_adjacency_matrix(W, mode = "undirected", weighted = TRUE, diag = FALSE)
  V(g)$eid <- eid_of(M$UT[ic])
  delete_vertices(g, which(degree(g) == 0))
}
louvain <- function(g) { set.seed(42); cl <- cluster_louvain(g, weights = E(g)$weight); m <- relabel(membership(cl), V(g)$eid)
  list(m = m, Q = modularity(g, m, weights = E(g)$weight)) }
g1 <- graph_at(NetC, 2); L1 <- louvain(g1)
stopifnot(length(L1$m) == vcount(g1), !anyNA(L1$m))
sz <- table(L1$m); big <- as.integer(names(sz)[sz >= 10])
T5a <- data.frame(measure = c("records in the coupling matrix", "records left out by biblioNetwork's first-letter filter",
                              "nodes (records with >= 1 link of >= 2 shared references)", "isolated records with references",
                              "edges (pairs sharing >= 2 references)", "components", "largest component (records)", "Louvain clusters",
                              "clusters with >= 10 records", "records in clusters with >= 10 records", "modularity Q"),
                  value = c(nrow(NetC), nrow(M) - nrow(NetC), vcount(g1), sum(n_ref[ic] > 0) - vcount(g1), ecount(g1), components(g1)$no,
                            max(components(g1)$csize), length(sz), length(big), sum(sz[sz >= 10]), r4(L1$Q)))
tab(T5a, "T5a_coupling_summary")
vi <- match(V(g1)$eid, eid_of(M$UT))
T5b <- NULL; T5bs <- NULL; T5bk <- NULL
for (k in big) {
  i <- vi[L1$m == k]
  T5b <- rbind(T5b, data.frame(cluster = k, records = length(i), p2003_2016 = sum(per[i] == PERIODS[1]), p2017_2021 = sum(per[i] == PERIODS[2]),
                               p2022_2025 = sum(per[i] == PERIODS[3]), articles = sum(M$DT[i] == "ARTICLE"), conference_papers = sum(M$DT[i] == "CONFERENCE PAPER"),
                               other_types = sum(!M$DT[i] %in% c("ARTICLE", "CONFERENCE PAPER")), mean_TC = r4(mean(M$TC[i]), 2), median_TC = med(M$TC[i])))
  s5 <- cnt(M$SO[i]); s5 <- head(s5[ord(-s5$n, s5$item), ], 5)
  T5bs <- rbind(T5bs, data.frame(cluster = k, rank = seq_len(nrow(s5)), source = s5$item, records = s5$n))
  k10 <- cnt(unlist(kw[i])); k10 <- head(k10[ord(-k10$n, k10$item), ], 10)
  T5bk <- rbind(T5bk, data.frame(cluster = k, rank = seq_len(nrow(k10)), keyword = k10$item, records = k10$n))
}
tab(T5b, "T5b_coupling_clusters"); tab(T5bs, "T5b2_cluster_sources"); tab(T5bk, "T5b3_cluster_keywords")
SAL <- normalizeSimilarity(NetC, type = "salton")
g2 <- graph_at(NetC, 2, weights = SAL); L2 <- louvain(g2)
g3 <- graph_at(NetC, 3); L3 <- louvain(g3)
cmp <- function(g, L) { common <- intersect(V(g1)$eid, V(g)$eid)
  a1 <- L1$m[match(common, V(g1)$eid)]; a2 <- L$m[match(common, V(g)$eid)]
  c(r4(igraph::compare(a1, a2, method = "nmi")), r4(igraph::compare(a1, a2, method = "adjusted.rand"))) }
c2 <- cmp(g2, L2); c3 <- cmp(g3, L3)
# own-code sensitivity: coupling on work keys (records x works, binary), shared works >= 2
wkeys <- sort(unique(unlist(rec_keys)), method = "radix")
WK <- Matrix::sparseMatrix(i = rep(seq_along(rec_keys), lengths(rec_keys)), j = match(unlist(rec_keys), wkeys), x = 1,
                           dims = c(nrow(M), length(wkeys)), dimnames = list(M$SR, NULL))
CK <- Matrix::tcrossprod(WK)[rownames(NetC), rownames(NetC)]
g4 <- graph_at(CK, 2); L4 <- louvain(g4); c4 <- cmp(g4, L4)
T5c <- data.frame(variant = c("main: shared references >= 2, raw weights", "Salton-normalised weights, shared references >= 2",
                              "shared references >= 3, raw weights", "own code: shared works (work key) >= 2, raw weights"),
                  nodes = c(vcount(g1), vcount(g2), vcount(g3), vcount(g4)), edges = c(ecount(g1), ecount(g2), ecount(g3), ecount(g4)),
                  clusters = c(length(unique(L1$m)), length(unique(L2$m)), length(unique(L3$m)), length(unique(L4$m))),
                  clusters_ge10 = c(length(big), sum(table(L2$m) >= 10), sum(table(L3$m) >= 10), sum(table(L4$m) >= 10)),
                  modularity = r4(c(L1$Q, L2$Q, L3$Q, L4$Q)),
                  nmi_vs_main = c(1, c2[1], c3[1], c4[1]), ari_vs_main = c(1, c2[2], c3[2], c4[2]))
tab(T5c, "T5c_coupling_sensitivity")
# own-code sensitivity, continued: the work-key coupling clusters with >= 10 records
v4 <- match(V(g4)$eid, eid_of(M$UT)); s4 <- table(L4$m); b4 <- as.integer(names(s4)[s4 >= 10])
T5d <- do.call(rbind, lapply(b4, function(k) { i <- v4[L4$m == k]
  k5 <- cnt(unlist(kw[i])); k5 <- head(k5[ord(-k5$n, k5$item), ], 5); s1c <- cnt(M$SO[i]); s1c <- s1c[ord(-s1c$n, s1c$item), ][1, ]
  data.frame(cluster = k, records = length(i), p2003_2016 = sum(per[i] == PERIODS[1]), p2017_2021 = sum(per[i] == PERIODS[2]),
             p2022_2025 = sum(per[i] == PERIODS[3]), top5_author_keywords = paste(k5$item, collapse = "; "),
             top_source = cut_words(s1c$item, 12), top_source_records = s1c$n, mean_TC = r4(mean(M$TC[i]), 2)) }))
tab(T5d, "T5d_work_key_coupling_clusters")
set.seed(42); lay1 <- layout_with_fr(g1, weights = E(g1)$weight)
pal <- grDevices::hcl.colors(max(length(big), 2), "Dark 3")
vcol <- ifelse(L1$m %in% big, pal[match(L1$m, big)], "grey80")
save_plot("Fig_bibliographic_coupling", function() {
  graphics::par(mar = c(0, 0, 1.5, 0))
  plot(g1, layout = lay1, vertex.label = NA, vertex.size = 2.2, vertex.color = vcol, vertex.frame.color = NA,
       edge.color = grDevices::adjustcolor("grey60", 0.25), edge.width = 0.3,
       main = "Bibliographic coupling of the E1 records (shared references >= 2; Louvain, seed 42)")
  graphics::legend("bottomleft", legend = c(paste("cluster", big), "smaller clusters"), col = c(pal[seq_along(big)], "grey80"), pch = 19,
                   cex = 0.6, bty = "n")
})
cn <- data.frame(eid = V(g1)$eid, doi = ifelse(is.na(M$DI[vi]), "", M$DI[vi]), cluster = L1$m, degree = degree(g1), x = r4(lay1[, 1]), y = r4(lay1[, 2]))
write_csv_lf(cn[ord(cn$eid), ], file.path(FIG, "Fig_bibliographic_coupling_nodes.csv"))
el <- as_edgelist(g1, names = FALSE)
ce <- data.frame(eid_a = V(g1)$eid[el[, 1]], eid_b = V(g1)$eid[el[, 2]], shared_references = E(g1)$weight)
sw <- ce$eid_a > ce$eid_b; tmp <- ce$eid_a[sw]; ce$eid_a[sw] <- ce$eid_b[sw]; ce$eid_b[sw] <- tmp
write_csv_lf(ce[ord(ce$eid_a, ce$eid_b), ], file.path(FIG, "Fig_bibliographic_coupling_edges.csv"))
NUM$T5 <- list(nodes = vcount(g1), edges = ecount(g1), clusters = length(sz), big = length(big), Q = r4(L1$Q), filtered = nrow(M) - nrow(NetC),
               salton = as.list(T5c[2, -1]), thr3 = as.list(T5c[3, -1]), work_key = as.list(T5c[4, -1]))
cat("step 6: coupling", vcount(g1), "nodes", ecount(g1), "edges", length(sz), "clusters, Q", r4(L1$Q), "\n")

## ---- Step 7: co-citation (T6) ----
NetCo <- biblioNetwork(M, analysis = "co-citation", network = "references", sep = ";", shortlabel = FALSE)
dg <- diag(NetCo); keys <- colnames(NetCo)
sel <- which(dg >= 4)
B <- as(as(NetCo[sel, sel], "generalMatrix"), "CsparseMatrix"); diag(B) <- 0; B <- drop0(B * (B >= 3))
gc <- graph_from_adjacency_matrix(B, mode = "undirected", weighted = TRUE, diag = FALSE)
V(gc)$key <- keys[sel]; V(gc)$citing <- as.integer(dg[sel])
gc1 <- delete_vertices(gc, which(degree(gc) == 0))
V(gc1)$eid <- V(gc1)$key
Lc <- louvain(gc1)
key_of <- function(l) { l <- gsub("\\).*", ")", l); l <- gsub(",", " ", l); l <- gsub(";", " ", l); trimES(bibliometrix:::reduceRefs(l)) }
occ <- lapply(strsplit(M$CR, ";", fixed = TRUE), function(l) { l <- sub("^\\s+", "", l); l[nchar(l) > 10] })
ko <- data.frame(ref = unlist(occ)); ko$key <- key_of(ko$ref)
ko <- ko[ko$key %in% keys[sel], ]
kt <- stats::aggregate(list(n = rep(1L, nrow(ko))), by = list(key = ko$key, ref = ko$ref), FUN = sum)
kt <- kt[ord(kt$key, -kt$n, kt$ref), ]; rep_ref <- kt[!duplicated(kt$key), ]
stopifnot(all(keys[sel] %in% rep_ref$key))
rp <- rep_ref$ref[match(V(gc1)$key, rep_ref$key)]
rpp <- ref_parts(rp)
V(gc1)$first <- tc_name(rpp$first_author); V(gc1)$year <- ref_year(rp); V(gc1)$title <- cut_words(rpp$title, 10)
csz <- table(Lc$m); cbig <- as.integer(names(csz)[csz >= 5])
T6a <- data.frame(measure = c("distinct references in the co-citation matrix", "nodes: references with >= 4 citing records",
                              "nodes with >= 1 edge", "edges: pairs co-cited by >= 3 records", "Louvain clusters (nodes with edges)",
                              "clusters with >= 5 nodes", "modularity Q"),
                  value = c(length(keys), length(sel), vcount(gc1), ecount(gc1), length(csz), length(cbig), r4(Lc$Q)))
tab(T6a, "T6a_cocitation_summary")
# own-code sensitivity: co-citation on work keys
wsel <- which(Matrix::colSums(WK) >= 4)
CW <- as(as(Matrix::crossprod(WK[, wsel, drop = FALSE]), "generalMatrix"), "CsparseMatrix"); diag(CW) <- 0; CW <- drop0(CW * (CW >= 3))
gw <- graph_from_adjacency_matrix(CW, mode = "undirected", weighted = TRUE, diag = FALSE)
V(gw)$eid <- wkeys[wsel]
gw1 <- delete_vertices(gw, which(degree(gw) == 0)); Lw <- louvain(gw1)
T6a2 <- data.frame(measure = c("works (work key) with >= 4 citing records", "of them with >= 1 edge", "edges: pairs co-cited by >= 3 records",
                               "Louvain clusters", "clusters with >= 5 nodes", "modularity Q"),
                   value = c(length(wsel), vcount(gw1), ecount(gw1), length(unique(Lw$m)), sum(table(Lw$m) >= 5), r4(Lw$Q)))
tab(T6a2, "T6a2_cocitation_work_key_sensitivity")
T6b <- NULL
for (k in cbig) { j <- which(Lc$m == k); j <- j[ord(-V(gc1)$citing[j], V(gc1)$key[j])][1:min(5, length(j))]
  T6b <- rbind(T6b, data.frame(cluster = k, cluster_size = sum(Lc$m == k), rank = seq_along(j), first_author = V(gc1)$first[j],
                               year = V(gc1)$year[j], title = V(gc1)$title[j], citing_records = V(gc1)$citing[j])) }
tab(T6b, "T6b_cocitation_clusters_top5")
oc <- ord(-V(gc1)$citing, V(gc1)$key)
nid <- character(vcount(gc1)); nid[oc] <- sprintf("C%03d", seq_along(oc))
lab30 <- oc[1:min(30, length(oc))]
labs <- rep("", vcount(gc1)); labs[lab30] <- paste(V(gc1)$first[lab30], V(gc1)$year[lab30])
set.seed(42); layc <- layout_with_fr(gc1, weights = E(gc1)$weight)
palc <- grDevices::hcl.colors(max(length(cbig), 2), "Dark 3")
ccol <- ifelse(Lc$m %in% cbig, palc[match(Lc$m, cbig)], "grey80")
save_plot("Fig_cocitation_references", function() {
  graphics::par(mar = c(0, 0, 1.5, 0))
  plot(gc1, layout = layc, vertex.label = ifelse(nzchar(labs), labs, NA), vertex.label.cex = 0.45, vertex.label.color = "black",
       vertex.size = 2 + 4 * sqrt(V(gc1)$citing / max(V(gc1)$citing)), vertex.color = ccol, vertex.frame.color = NA,
       edge.color = grDevices::adjustcolor("grey60", 0.3), edge.width = 0.4,
       main = "Co-citation of references (>= 4 citing records, edges >= 3; Louvain, seed 42)")
  graphics::legend("bottomleft", legend = c(paste("cluster", cbig), "smaller clusters"), col = c(palc[seq_along(cbig)], "grey80"), pch = 19,
                   cex = 0.6, bty = "n")
})
conodes <- data.frame(node = nid, label = labs, first_author = V(gc1)$first, year = V(gc1)$year, title = V(gc1)$title, cluster = Lc$m,
                      citing_records = V(gc1)$citing, degree = degree(gc1), x = r4(layc[, 1]), y = r4(layc[, 2]))
write_csv_lf(conodes[ord(conodes$node), ], file.path(FIG, "Fig_cocitation_references_nodes.csv"))
elc <- as_edgelist(gc1, names = FALSE)
coe <- data.frame(from = nid[elc[, 1]], to = nid[elc[, 2]], cocitations = E(gc1)$weight)
sw <- coe$from > coe$to; tmp <- coe$from[sw]; coe$from[sw] <- coe$to[sw]; coe$to[sw] <- tmp
write_csv_lf(coe[ord(coe$from, coe$to), ], file.path(FIG, "Fig_cocitation_references_edges.csv"))
write_csv_lf(data.frame(node = nid, key = V(gc1)$key, representative_reference = rp, citing_records = V(gc1)$citing)[ord(nid), ],
             file.path(DAT, "cocitation_nodes_keys.csv"))
# sources
M2 <- M; M2$CR_SO <- vapply(so_th, function(v) if (length(v)) paste(v, collapse = ";") else NA_character_, character(1))
NetS <- biblioNetwork(M2, analysis = "co-citation", network = "sources", sep = ";")
ssel <- sd$source[sd$references >= 10]
stopifnot(all(ssel %in% colnames(NetS)))
BS <- as(as(NetS[ssel, ssel], "generalMatrix"), "CsparseMatrix"); diag(BS) <- 0; BS <- drop0(BS * (BS >= 5))
gs <- graph_from_adjacency_matrix(BS, mode = "undirected", weighted = TRUE, diag = FALSE)
V(gs)$eid <- V(gs)$name
gs1 <- delete_vertices(gs, which(degree(gs) == 0))
Ls <- louvain(gs1)
ssz <- table(Ls$m)
T6c <- data.frame(measure = c("sources with >= 10 references", "sources with >= 1 edge", "edges: source pairs co-cited by >= 5 records",
                              "Louvain clusters", "modularity Q"),
                  value = c(length(ssel), vcount(gs1), ecount(gs1), length(ssz), r4(Ls$Q)))
tab(T6c, "T6c_source_cocitation_summary")
T6c2 <- NULL
for (k in sort(unique(Ls$m))) { nm <- V(gs1)$name[Ls$m == k]; rr <- sd$references[match(nm, sd$source)]
  o <- ord(-rr, nm)[1:min(5, length(nm))]
  T6c2 <- rbind(T6c2, data.frame(cluster = k, cluster_size = length(nm), rank = seq_along(o), source = cut_words(nm[o], 20), references = rr[o])) }
tab(T6c2, "T6c2_source_clusters")
NUM$T6 <- list(keys = length(keys), nodes = length(sel), nodes_with_edges = vcount(gc1), edges = ecount(gc1), clusters = length(csz), big = length(cbig),
               Q = r4(Lc$Q), sources = length(ssel), source_nodes = vcount(gs1), source_edges = ecount(gs1), source_clusters = length(ssz), source_Q = r4(Ls$Q),
               work_key = setNames(as.list(T6a2$value), c("works_ge4", "with_edges", "edges", "clusters", "clusters_ge5", "Q")))
cat("step 7: co-citation", length(sel), "nodes,", ecount(gc1), "edges,", length(csz), "clusters | sources", length(ssel), "\n")
write_json_sorted(NUM, file.path(OUT, "F13_3_numbers.json"))
cat("done\n")
