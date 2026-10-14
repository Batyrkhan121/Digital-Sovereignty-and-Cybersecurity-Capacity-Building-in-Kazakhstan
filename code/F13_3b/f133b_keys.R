# Phase F13.3b - step 1 (keys): the work key of every repaired reference, computed by F13.3's OWN functions (R19: the same code,
# not rewritten). phase_F13_3/programs/f133_lib.R is sourced read-only (sourcing also loads bibliometrix/igraph, unused here);
# ref_parts(), ref_year() and work_key() come from it. work_key_n() below is a COPY of F13.3's work_key() with the number of title
# words as a parameter (source: phase_F13_3/programs/f133_lib.R, function work_key); n = 6 is asserted identical to work_key().
# name_shaped() is a COPY of the function of the same name in phase_F13_3/programs/f133_main.R (step 4).
# Input: phase_F13_3/data/references_repaired.csv. Output: data/reference_keys.csv (reference texts and keys - data/ only, git-ignored).
# No network. Prints counts only.
.f <- dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))))
phase <- dirname(.f)
root <- dirname(dirname(dirname(phase)))
suppressMessages(source(file.path(root, "outputs", "dprg_revision_2026", "phase_F13_3", "programs", "f133_lib.R")))
a <- commandArgs(trailingOnly = TRUE)
OUT <- if (length(a) && startsWith(a[1], "--out=")) sub("^--out=", "", a[1]) else phase
dir.create(file.path(OUT, "data"), recursive = TRUE, showWarnings = FALSE)

work_key_n <- function(refs, n) {
  p <- ref_parts(refs); y <- ref_year(refs)
  au <- gsub("(*UCP)[^\\p{L}\\p{N}]", "", toupper(p$first_author), perl = TRUE)
  ti <- trim_u(gsub("(*UCP)[^\\p{L}\\p{N}]+", " ", toupper(p$title), perl = TRUE))
  tn <- vapply(strsplit(ti, " ", fixed = TRUE), function(v) paste(head(v[nzchar(v)], n), collapse = " "), character(1))
  ok <- nzchar(au) & !is.na(y) & nzchar(tn)
  ifelse(ok, paste(au, y, tn, sep = "|"), paste0("=", refs))
}
name_shaped <- function(x) grepl("^[A-Z][A-Z'’\\-]+ (?:[A-Z]{1,2}\\.\\s?){1,3}$", x, perl = TRUE) | grepl("^[A-Z][A-Z'’\\-]+ [A-Z]{1,2}$", x, perl = TRUE)

rr <- readr::read_csv(file.path(root, "outputs", "dprg_revision_2026", "phase_F13_3", "data", "references_repaired.csv"),
                      col_types = readr::cols(.default = "c"), na = character(), progress = FALSE)
lst <- lapply(rr$references_repaired, function(s) { l <- sub("^\\s+", "", strsplit(s, ";", fixed = TRUE)[[1]]); l[nzchar(trim_u(l))] })
stopifnot(identical(lengths(lst), as.integer(rr$n_references)))
ref <- unlist(lst)
u <- sort(unique(ref), method = "radix")
p <- ref_parts(u)
k6 <- work_key(u)
stopifnot(identical(work_key_n(u, 6), k6))
k4 <- work_key_n(u, 4); k8 <- work_key_n(u, 8)
y <- ref_year(u)
j <- match(ref, u)
out <- data.frame(eid = rep(rr$eid, lengths(lst)), ref_no = unlist(lapply(lengths(lst), seq_len)), n_chars = nchar(ref),
                  in_scope = as.integer(nchar(ref) > 10), first_author = p$first_author[j], year = y[j], title = p$title[j],
                  source = p$source[j], n_authors = p$n_authors[j], key = k6[j], key4 = k4[j], key8 = k8[j],
                  source_name_shaped = as.integer(name_shaped(p$source[j])), reference = ref)
write_csv_lf(out, file.path(OUT, "data", "reference_keys.csv"))
cat("references:", nrow(out), "| in scope (> 10 characters):", sum(out$in_scope), "| complete keys:", sum(!startsWith(out$key, "=")),
    "| distinct strings:", length(u), "\n")
