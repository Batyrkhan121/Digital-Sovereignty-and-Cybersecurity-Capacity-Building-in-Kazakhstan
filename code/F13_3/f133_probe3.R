# Phase F13.3 - probe 3: the repaired CR built from the exported cells (counts), and the 150 most frequent cited sources from
# metaTagExtraction(M, "CR_SO") - journal and proceedings names only - to draft the light cited-sources thesaurus. No network.
source(file.path(dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))), "f133_lib.R"))
P <- f133_paths()
S <- build_M(P)
cat("\nexported fragments:", sum(S$fx$n_frag), "| import fragments:", sum(S$frag_import), "| references:", sum(lengths(S$refs)),
    "| median:", med(lengths(S$refs)[lengths(S$refs) > 0]), "| tails:", sum(S$fx$n_tail), "| emptied:", S$emptied,
    "| inner ';':", S$inner_semicolon, "| builtin:", sum(S$n_builtin), "| dropped named:", paste(S$dropped_named, collapse = " "), "\n")
M <- metaTagExtraction(S$M, Field = "CR_SO", sep = ";")
so <- trim_u(unlist(strsplit(M$CR_SO[!is.na(M$CR_SO)], ";", fixed = TRUE)))
so <- so[nzchar(so)]
tb <- sort(table(so), decreasing = TRUE)
cat("recognised sources:", length(so), "of", sum(lengths(S$refs)), "| distinct:", length(tb), "\n")
top <- head(tb, 150)
cat(paste0(seq_along(top), ". ", names(top), " [", as.integer(top), "]"), sep = "\n")
