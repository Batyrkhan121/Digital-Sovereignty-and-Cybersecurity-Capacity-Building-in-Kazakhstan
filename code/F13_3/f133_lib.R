# Phase F13.3 - shared R helpers: loading E1/E2 through bibliometrix, the R13 column drop, the brief's CR repair rule,
# reference parsing (first author, year, title, source), CSV/JSON writers. Local files only (no network); sourced by
# f133_probe.R and f133_main.R. Nothing here prints record contents, author names or reference texts.
.libPaths(c(path.expand(Sys.getenv("R_LIBS_USER")), .libPaths()))
suppressPackageStartupMessages({
  library(bibliometrix)
  library(igraph)
  library(Matrix)
})
options(stringsAsFactors = FALSE, warn = 1, width = 160)

f133_paths <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  here <- dirname(normalizePath(sub("^--file=", "", args[grep("^--file=", args)])))
  phase <- dirname(here)
  root <- dirname(dirname(dirname(phase)))
  exp <- file.path(root, "outputs", "dprg_revision_2026", "author_exports_2026_10")
  list(here = here, phase = phase, root = root,
       E1 = file.path(exp, "scopus_full_TAK_KZ_2003_2025_2026-10-13.csv"),
       E2 = file.path(exp, "wos_full_TS_KZ_2003_2025_2026-10-13.txt"),
       pairs = file.path(root, "outputs", "dprg_revision_2026", "phase_F13_1", "tables", "T3a_pairs.csv"),
       thes = file.path(root, "outputs", "dprg_revision_2026", "phase_F12_3c", "tables", "thesaurus.csv"))
}

# R13: right after convert2df, before anything is written, RP/EM/OI/RI and any 'correspondence' column are dropped, and with
# them every column outside a short whitelist (AU1_UN is derived by convert2df from RP and carries e-mails; FX, C1, AF, Author(s)
# ID, Editors, AB ... are not needed). AU stays in memory only (SR, local citations); it is never written.
R13_DROP <- c("RP", "EM", "OI", "RI")
KEEP <- c("AU", "TI", "TI_raw", "PY", "SO", "JI", "J9", "DE", "DE_raw", "ID", "KW_Merged", "CR", "DI", "TC", "UT", "DT", "DB",
          "LA", "SR", "SR_FULL", "PU")
r13_drop <- function(M) {
  named <- union(intersect(names(M), R13_DROP), grep("correspondence", names(M), ignore.case = TRUE, value = TRUE))
  drop <- union(named, setdiff(names(M), KEEP))
  M <- M[, intersect(names(M), KEEP), drop = FALSE]
  attr(M, "r13_dropped_named") <- named
  attr(M, "r13_dropped") <- sort(drop, method = "radix")
  M
}

# E1 through bibliometrix. builtin = FALSE switches off bibliometrix 5.5.0's own separator repair
# (internal fix_scopus_author_separator) for this one call, so that CR holds the exported '; ' fragments (uppercased and
# cleaned by convert2df as usual); the brief's rule is then applied by fix_cr(). builtin = TRUE is the standard import.
load_e1 <- function(file, builtin = FALSE) {
  ns <- asNamespace("bibliometrix")
  orig <- get("fix_scopus_author_separator", envir = ns)
  if (!builtin) {
    unlockBinding("fix_scopus_author_separator", ns)
    assign("fix_scopus_author_separator", function(cr_vec) cr_vec, envir = ns)
    on.exit({ assign("fix_scopus_author_separator", orig, envir = ns); lockBinding("fix_scopus_author_separator", ns) }, add = TRUE)
  }
  M <- suppressWarnings(convert2df(file, dbsource = "scopus", format = "csv"))
  r13_drop(M)
}

# E2 through bibliometrix: only UT and NR are kept, everything else is dropped at once
load_e2_nr <- function(file) {
  W <- suppressWarnings(convert2df(file, dbsource = "wos", format = "plaintext"))
  W <- data.frame(UT = as.character(W$UT), NR = as.character(W$NR))
  W
}

trim_u <- function(x) gsub("(*UCP)^\\s+|\\s+$", "", x, perl = TRUE)
trimES <- function(x) gsub("\\s+", " ", x)   # as bibliometrix's internal trimES

# The brief's author pattern ^(?:[A-Z][\w'’\-\.]*\s?)+[A-Z]\.(?:\s?[A-Z]\.)*$ written in an equivalent linear form (the nested
# quantifiers of the literal pattern backtrack exponentially on long all-capital fragments): the fragment starts with A-Z, every
# character is a word character, apostrophe, right single quote, hyphen, dot or a whitespace followed by A-Z, it ends with
# 'A-Z.' and it is at least 3 characters long. No comma (checked separately).
AUTHOR_BODY <- "(*UCP)^[A-Z](?:[\\w'’\\-.]|\\s(?=[A-Z]))*$"
is_author <- function(fr) {
  !grepl(",", fr, fixed = TRUE) & nchar(fr) >= 3 & grepl("[A-Z]\\.$", fr, perl = TRUE) & grepl(AUTHOR_BODY, fr, perl = TRUE)
}

# The brief's repair of one CR cell: split on '; ' into fragments (non-empty after trimming); consecutive author fragments are
# attached to the next fragment with ', '; a trailing buffer of authors without a body is a reference of its own.
fix_cell <- function(cell) {
  if (is.na(cell) || !nzchar(trim_u(cell))) return(list(refs = character(0), frags = 0L, tails = 0L, nocomma_body = 0L))
  fr <- trim_u(strsplit(cell, "; ", fixed = TRUE)[[1]])
  fr <- fr[nzchar(fr)]
  au <- is_author(fr)
  refs <- character(0); buf <- character(0); nocomma <- 0L
  for (i in seq_along(fr)) {
    if (au[i]) { buf <- c(buf, fr[i]); next }
    if (length(buf) && !grepl(",", fr[i], fixed = TRUE)) nocomma <- nocomma + 1L
    refs <- c(refs, paste(c(buf, fr[i]), collapse = ", "))
    buf <- character(0)
  }
  tails <- 0L
  if (length(buf)) { refs <- c(refs, paste(buf, collapse = ", ")); tails <- 1L }
  list(refs = refs, frags = length(fr), tails = tails, nocomma_body = nocomma)
}

fix_cr <- function(cr) {
  res <- lapply(cr, fix_cell)
  list(CR = vapply(res, function(r) paste(r$refs, collapse = "; "), character(1)),
       refs = lapply(res, `[[`, "refs"),
       n_frag = vapply(res, `[[`, integer(1), "frags"),
       n_ref = vapply(res, function(r) length(r$refs), integer(1)),
       n_tail = vapply(res, `[[`, integer(1), "tails"),
       n_nocomma_body = vapply(res, `[[`, integer(1), "nocomma_body"))
}

# year of a reference: the last '(YYYY)' whose value lies in 1800-2026
ref_year <- function(s) {
  m <- regmatches(s, gregexpr("\\((\\d{4})\\)", s))
  vapply(m, function(v) {
    y <- as.integer(substr(v, 2, 5)); y <- y[!is.na(y) & y >= 1800 & y <= 2026]
    if (length(y)) y[length(y)] else NA_integer_
  }, integer(1))
}

# first author, title, source of a repaired reference: comma-free author segments first, then the title, then the source
# trailing initials of one or two letters (Slavic 'YU.', 'ZH.', 'KH.') after a space are removed
surname_of <- function(a) {
  s <- trim_u(gsub("(*UCP)\\s+(?:[A-Z]{1,2}\\.\\s?)+$", "", a, perl = TRUE))
  s <- ifelse(nzchar(s) & s != a, s, trim_u(gsub("(*UCP)(?:[A-Z]\\.\\s?)+$", "", a, perl = TRUE)))
  ifelse(nzchar(s), s, a)
}
cut_words <- function(s, n) vapply(strsplit(trim_u(s), "\\s+"), function(w) paste(head(w, n), collapse = " "), character(1))
ref_parts <- function(s) {
  seg <- strsplit(s, ", ", fixed = TRUE)
  out <- lapply(seg, function(x) {
    x <- trim_u(x); x <- x[nzchar(x)]
    a <- is_author(x)
    k <- 0L
    while (k < length(x) && a[k + 1L]) k <- k + 1L
    first <- if (k > 0L) surname_of(x[1]) else ""
    rest <- if (k > 0L) x[-seq_len(k)] else x
    rest <- rest[!grepl("^\\(\\d{4}\\)$", rest)]
    c(first, if (length(rest) >= 1) rest[1] else "", if (length(rest) >= 2) rest[2] else "", as.character(k))
  })
  data.frame(first_author = vapply(out, `[`, "", 1), title = vapply(out, `[`, "", 2), source = vapply(out, `[`, "", 3),
             n_authors = as.integer(vapply(out, `[`, "", 4)))
}

# convert2df's own CR cleaning (bibliometrix 5.5.0: '[', ']', ' .. ', ' . ' removed, spaces collapsed, ';;' -> ';'), applied
# here to each repaired reference separately so that it cannot join two references; an inner ';' becomes ',' so that
# bibliometrix's split on ';' returns exactly the repaired references.
clean_ref <- function(r) {
  r <- trim_u(trimES(gsub("\\[,||\\[||\\]|| \\.\\. || \\. ", "", r)))
  gsub(";", ",", r, fixed = TRUE)
}

# Step 1 in one place: M (bibliometrix import, R13 drop) with CR replaced by the repaired references; the unrepaired state
# (exported cells, uppercased as bibliometrix does) for the control; the import with bibliometrix's own repair, for comparison.
build_M <- function(P) {
  M0 <- load_e1(P$E1, builtin = FALSE)
  raw <- readr::read_csv(P$E1, col_select = c("EID", "References"), col_types = readr::cols(.default = "c"), na = character(),
                         progress = FALSE)
  raw <- raw[match(M0$UT, toupper(raw$EID)), ]
  stopifnot(!anyNA(raw$EID))
  cell <- toupper(raw$References)
  frag_import <- vapply(strsplit(M0$CR, "; ", fixed = TRUE), function(v) sum(nzchar(trim_u(v))), integer(1))
  fx <- fix_cr(cell)
  cleaned <- lapply(fx$refs, clean_ref)
  inner_semicolon <- sum(vapply(fx$refs, function(v) sum(grepl(";", trim_u(trimES(gsub("\\[,||\\[||\\]|| \\.\\. || \\. ", "", v))), fixed = TRUE)), integer(1)))
  emptied <- sum(vapply(cleaned, function(v) sum(!nzchar(v)), integer(1)))
  refs <- lapply(cleaned, function(v) v[nzchar(v)])
  M <- M0
  M$CR <- vapply(refs, paste, character(1), collapse = "; ")
  Mb <- M0
  Mb$CR <- cell
  B <- load_e1(P$E1, builtin = TRUE)
  stopifnot(identical(B$UT, M0$UT))
  n_builtin <- vapply(strsplit(B$CR, "; ", fixed = TRUE), function(v) sum(nzchar(trim_u(v))), integer(1))
  list(M = M, M_before = Mb, refs = refs, fx = fx, exported_nonempty = sum(nzchar(trim_u(cell))), frag_import = frag_import,
       inner_semicolon = inner_semicolon, emptied = emptied, n_builtin = n_builtin,
       dropped = attr(M0, "r13_dropped"), dropped_named = attr(M0, "r13_dropped_named"))
}

# own-code sensitivity (not bibliometrix): a work key = first-author surname + year + first six title words (letters and
# digits only); references lacking any of the three keep their exact string as key
work_key <- function(refs) {
  p <- ref_parts(refs); y <- ref_year(refs)
  au <- gsub("(*UCP)[^\\p{L}\\p{N}]", "", toupper(p$first_author), perl = TRUE)
  ti <- trim_u(gsub("(*UCP)[^\\p{L}\\p{N}]+", " ", toupper(p$title), perl = TRUE))
  t6 <- vapply(strsplit(ti, " ", fixed = TRUE), function(v) paste(head(v[nzchar(v)], 6), collapse = " "), character(1))
  ok <- nzchar(au) & !is.na(y) & nzchar(t6)
  ifelse(ok, paste(au, y, t6, sep = "|"), paste0("=", refs))
}

period_of <- function(py) ifelse(py <= 2016, "2003-2016", ifelse(py <= 2021, "2017-2021", "2022-2025"))
PERIODS <- c("2003-2016", "2017-2021", "2022-2025")

# CSV writer: UTF-8, LF, minimal quoting (as Python's csv module reads it); numbers written as given
csv_cell <- function(v) {
  v <- ifelse(is.na(v), "", as.character(v))
  q <- grepl("[\",\n\r]", v) | grepl("^\\s|\\s$", v)
  ifelse(q, paste0("\"", gsub("\"", "\"\"", v, fixed = TRUE), "\""), v)
}
write_csv_lf <- function(df, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  df <- as.data.frame(df)
  lines <- c(paste(csv_cell(names(df)), collapse = ","),
             if (nrow(df)) do.call(paste, c(lapply(df, csv_cell), sep = ",")) else character(0))
  writeBin(charToRaw(enc2utf8(paste0(paste(lines, collapse = "\n"), "\n"))), path)
}
write_json_sorted <- function(x, path) {
  srt <- function(v) if (is.list(v) && !is.null(names(v))) lapply(v[order(names(v))], srt) else if (is.list(v)) lapply(v, srt) else v
  writeBin(charToRaw(enc2utf8(paste0(jsonlite::toJSON(srt(x), auto_unbox = TRUE, pretty = TRUE, digits = NA, null = "null"), "\n"))), path)
}
r4 <- function(x, k = 4) round(x, k)
med <- function(x) if (length(x)) stats::median(x) else NA
