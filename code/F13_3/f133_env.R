# Phase F13.3 - records the R environment (versions only, no paths) in run_logs/environment.json. No network.
# Run: Rscript --vanilla f133_env.R  (from any folder; the phase folder is found from this file's place)
.libPaths(c(path.expand(Sys.getenv("R_LIBS_USER")), .libPaths()))
args <- commandArgs(trailingOnly = FALSE)
here <- dirname(normalizePath(sub("^--file=", "", args[grep("^--file=", args)])))
out <- file.path(dirname(here), "run_logs", "environment.json")
pk <- c("bibliometrix", "igraph", "Matrix", "dplyr", "ggplot2", "jsonlite", "readr", "stringr", "stringi", "tidyr")
v <- vapply(pk, function(p) as.character(utils::packageVersion(p)), character(1))
env <- list(R = R.version.string, platform = R.version$platform, bibliometrix = v[["bibliometrix"]], igraph = v[["igraph"]],
            packages = as.list(v[order(names(v))]), installed_from = "CRAN (cloud.r-project.org), Windows binaries, 2026-10-13",
            note = "installed before step 0 into the user library with install.packages('bibliometrix') and its dependencies")
env <- env[order(names(env))]
writeBin(charToRaw(enc2utf8(paste0(jsonlite::toJSON(env, auto_unbox = TRUE, pretty = TRUE), "\n"))), out)
cat("environment.json:", env$R, "| bibliometrix", env$bibliometrix, "| igraph", env$igraph, "\n")
