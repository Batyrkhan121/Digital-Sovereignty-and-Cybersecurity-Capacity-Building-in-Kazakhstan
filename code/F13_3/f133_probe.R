# Phase F13.3 - probe (run once after step 0, before the main program): how bibliometrix 5.5.0 imports E1 and E2.
# Prints column names, counts and shapes only - no record contents, names or reference texts. No network.
source(file.path(dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))), "f133_lib.R"))
P <- f133_paths()
M <- load_e1(P$E1, builtin = FALSE)
cat("\nE1 rows:", nrow(M), "| R13 dropped:", paste(attr(M, "r13_dropped"), collapse = " "), "\n")
cat("columns:", paste(sort(names(M)), collapse = " "), "\n")
need <- c("TI", "PY", "SO", "DE", "ID", "CR", "DI", "TC", "UT", "DT", "AU", "SR")
cat("needed present:", all(need %in% names(M)), "| missing:", paste(setdiff(need, names(M)), collapse = " "), "\n")
em <- "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}"
orc <- "\\b(?:0000|0009)-\\d{4}-\\d{4}-\\d{3}[\\dX]\\b"
sh <- vapply(names(M), function(c) { v <- as.character(M[[c]]); sum(grepl(em, v, perl = TRUE)) + sum(grepl(orc, v, perl = TRUE)) }, numeric(1))
cat("columns with e-mail/ORCID shapes after the drop:", paste(names(sh)[sh > 0], sh[sh > 0], collapse = "; "), "\n")
cat("UT looks like EID:", sum(grepl("^2-S2\\.0-", M$UT)), "| CR non-empty:", sum(nzchar(trim_u(M$CR)) & M$CR != "NONE"), "\n")
cat("DT:", paste(names(table(M$DT)), table(M$DT), collapse = "; "), "| PY range:", range(M$PY), "\n")
fx <- fix_cr(M$CR)
cat("fragments (unrepaired):", sum(fx$n_frag), "| references after the brief's rule:", sum(fx$n_ref), "| median:", med(fx$n_ref[fx$n_ref > 0]),
    "| max:", max(fx$n_ref), "| trailing author buffers:", sum(fx$n_tail), "| bodies without comma after authors:", sum(fx$n_nocomma_body), "\n")
fr <- trim_u(unlist(strsplit(M$CR, "; ", fixed = TRUE))); fr <- fr[nzchar(fr) & !grepl(",", fr, fixed = TRUE)]
short <- fr[nchar(fr) <= 24]
lit <- suppressWarnings(grepl("(*UCP)^(?:[A-Z][\\w'’\\-\\.]*\\s?)+[A-Z]\\.(?:\\s?[A-Z]\\.)*$", short, perl = TRUE))
cat("comma-free fragments:", length(fr), "| of them <= 24 chars:", length(short), "| literal vs linear pattern disagree:", sum(lit != is_author(short)), "\n")
B <- load_e1(P$E1, builtin = TRUE)
nb <- vapply(strsplit(B$CR, "; ", fixed = TRUE), function(x) sum(nzchar(trim_u(x))), integer(1))
cat("bibliometrix built-in repair: references", sum(nb), "| median", med(nb[nb > 0]), "| records differing from the brief's rule:", sum(nb != fx$n_ref), "\n")
W <- load_e2_nr(P$E2)
pr <- read.csv(P$pairs, colClasses = "character")
cat("E2 rows:", nrow(W), "| UT like WOS:", sum(grepl("^WOS:", W$UT)), "| NR numeric:", sum(!is.na(suppressWarnings(as.integer(W$NR)))),
    "| pairs:", nrow(pr), "| pairs found in M:", sum(toupper(pr$eid) %in% M$UT), "| in E2:", sum(toupper(pr$ut) %in% toupper(W$UT)), "\n")
cat("DE_raw present:", "DE_raw" %in% names(M), "| SR unique:", !any(duplicated(M$SR)), "| SR starting with a non-letter:", sum(!grepl("^[A-Za-z]", M$SR)), "\n")
