# Phase F13.3 - probe 2: why the fragment count after convert2df (79,685) differs from the raw export's (79,686, F13.1).
# Reads only EID and References of E1 with readr; prints counts and character shapes (letters -> a, digits -> 9) only.
source(file.path(dirname(normalizePath(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))), "f133_lib.R"))
P <- f133_paths()
M <- load_e1(P$E1, builtin = FALSE)
raw <- readr::read_csv(P$E1, col_select = c("EID", "References"), col_types = readr::cols(.default = "c"), na = character(),
                       progress = FALSE)
raw <- raw[match(M$UT, toupper(raw$EID)), ]
nf <- function(x) vapply(strsplit(x, "; ", fixed = TRUE), function(v) sum(nzchar(trim_u(v))), integer(1))
a <- nf(raw$References); b <- nf(M$CR)
cat("raw fragments:", sum(a), "| after convert2df:", sum(b), "| records differing:", sum(a != b), "\n")
shape <- function(s) gsub("[0-9]", "9", gsub("(*UCP)\\p{L}", "a", s, perl = TRUE), perl = TRUE)
for (i in which(a != b)) {
  fr <- trim_u(strsplit(raw$References[i], "; ", fixed = TRUE)[[1]]); fr <- fr[nzchar(fr)]
  cl <- trim_u(trimES(gsub("\\[,||\\[||\\]|| \\.\\. || \\. ", "", toupper(fr))))
  j <- which(!nzchar(cl) | cl == ";")
  cat("record", i, "raw", a[i], "imported", b[i], "| fragments emptied by the import cleaning:", length(j),
      "| their shapes:", paste0("[", shape(fr[j]), "]", collapse = " "), "\n")
  im <- trim_u(strsplit(M$CR[i], "; ", fixed = TRUE)[[1]]); im <- im[nzchar(im)]
  k <- which(cl[seq_along(im)] != im)[1]
  cat("  first divergence at fragment", k, "| raw fragment k ends:", paste0("[", shape(substr(fr[k], nchar(fr[k]) - 3, nchar(fr[k]))), "]"),
      "| raw fragment k+1 starts:", paste0("[", shape(substr(fr[k + 1], 1, 4)), "]"), "\n")
}
