"""Phase F13.7a - step 1: trial render of the F13.6b draft (part 1). A copy of phase_F13_6b/draft/main_v2.qmd goes to render/ with two
changes, both in the copy only: the one figure path written from the repository root ('outputs/figures/...') is made relative to
render/ (the '../../phase_*' paths resolve from render/ as from draft/), and the PDF engine (tectonic, the draft's choice) gets
'-C' (--only-cached) so that the render uses no network. references.bib is copied beside it (the draft names no title page).
quarto render -> docx, then -> pdf. Writes run_logs/render.json and tables/R1_render_issues.csv. Nothing in phase_F13_6b is changed."""
import sys
sys.dont_write_bytecode = True

import re
import shutil
import subprocess
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f137a_lib as L

ROOT_FIG = "](outputs/figures/"
ROOT_FIG_FIXED = "](../../../../outputs/figures/"
ENGINE_LINE = "    pdf-engine: tectonic\n"
ENGINE_OPT = "    pdf-engine-opt: -C\n"


def run(args):
    t0 = time.time()
    r = subprocess.run(args, cwd=str(L.RENDER), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {"args": args, "returncode": r.returncode, "seconds": round(time.time() - t0, 1), "stdout": r.stdout, "stderr": r.stderr}


def warnings_of(text):
    out = []
    for ln in text.splitlines():
        s = ln.strip()
        if re.search(r"\bWARN(ING)?\b|\bERROR\b|\[WARNING\]|\[ERROR\]|could not|not found|Unable to", s, re.I):
            out.append(s[:300])
    return out


def bib_keys(text):
    return set(re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", text))


def cite_keys(qmd):
    body = qmd.split("\n---\n", 1)[1] if qmd.startswith("---") else qmd
    keys = set()
    for m in re.finditer(r"(?<![\w.])@([A-Za-z][\w:.-]*[\w])", body):
        k = m.group(1)
        if not k.startswith(("fig-", "tbl-", "sec-", "eq-")):
            keys.add(k)
    return keys


def line_of(lines, needle):
    for i, ln in enumerate(lines, 1):
        if needle in ln:
            return i
    return ""


def main():
    L.RENDER.mkdir(parents=True, exist_ok=True)
    src = L.path(L.DRAFT).read_bytes().decode("utf-8")
    n_fix = src.count(ROOT_FIG)
    copy = src.replace(ROOT_FIG, ROOT_FIG_FIXED)
    assert copy.count(ENGINE_LINE) == 1, "the draft's pdf-engine line was not found once"
    copy = copy.replace(ENGINE_LINE, ENGINE_LINE + ENGINE_OPT)
    (L.RENDER / "main_v2.qmd").write_bytes(copy.encode("utf-8"))
    shutil.copyfile(L.path("references.bib"), L.RENDER / "references.bib")
    draft_lines = src.splitlines()
    runs = {"docx": run(["quarto", "render", "main_v2.qmd", "--to", "docx"]), "pdf": run(["quarto", "render", "main_v2.qmd", "--to", "pdf"])}
    fallback = None
    if not (L.RENDER / "main_v2.pdf").exists():
        # tectonic offline lacked a cached font: second copy with Quarto's TinyTeX (xelatex), package auto-install off (no network)
        fb = copy.replace(ENGINE_LINE + ENGINE_OPT, "    pdf-engine: xelatex\n    latex-auto-install: false\n")
        (L.RENDER / "main_v2_xelatex.qmd").write_bytes(fb.encode("utf-8"))
        runs["pdf_xelatex"] = run(["quarto", "render", "main_v2_xelatex.qmd", "--to", "pdf"])
        fallback = "main_v2_xelatex.qmd: pdf-engine xelatex (Quarto's TinyTeX), latex-auto-install false"
    outputs = {}
    for name, ext in (("main_v2", "docx"), ("main_v2", "pdf"), ("main_v2", "tex"), ("main_v2_xelatex", "pdf"), ("main_v2_xelatex", "tex")):
        p = L.RENDER / f"{name}.{ext}"
        outputs[f"{name}.{ext}"] = {"file": f"render/{name}.{ext}", "exists": p.exists(), "bytes": p.stat().st_size if p.exists() else 0}
    outputs["docx"] = outputs["main_v2.docx"]
    pdf_name = "main_v2.pdf" if outputs["main_v2.pdf"]["exists"] else "main_v2_xelatex.pdf"
    outputs["pdf"] = outputs[pdf_name]
    issues = []
    unresolved_xref, missing_cites, docx_info = set(), set(), {}
    for fmt, r in runs.items():
        text = r["stdout"] + "\n" + r["stderr"]
        unresolved_xref |= set(re.findall(r"(?:Unable to resolve crossref|crossref[^@]*)@((?:fig|tbl|sec|eq)-[\w-]+)", text))
        missing_cites |= set(re.findall(r"[Cc]itation ([^\s,]+) not found", text))
        r["warnings"] = warnings_of(text)
    if outputs["docx"]["exists"]:
        with zipfile.ZipFile(L.RENDER / "main_v2.docx") as z:
            names = z.namelist()
            doc = z.read("word/document.xml").decode("utf-8", "replace")
        media = [n for n in names if n.startswith("word/media/")]
        exts = {}
        for n in media:
            exts[Path(n).suffix.lower()] = exts.get(Path(n).suffix.lower(), 0) + 1
        plain = re.sub(r"<[^>]+>", "", doc)
        unresolved_xref |= set(re.findall(r"\?@((?:fig|tbl|sec|eq)-[\w-]+)", plain))
        docx_info = {"media_files": len(media), "media_by_extension": exts, "question_marks_unresolved": plain.count("?@"),
                     "triple_question_marks": plain.count("???"), "editorial_marks_in_text": len(re.findall(r"\[\[[^\]]+\]\]", plain))}
    if outputs["pdf"]["exists"]:
        b = (L.RENDER / pdf_name).read_bytes()
        outputs["pdf"]["pages"] = len(re.findall(rb"/Type\s*/Page(?!s)", b))
    bib = bib_keys(L.path("references.bib").read_bytes().decode("utf-8", "replace"))
    static_missing = sorted(cite_keys(src) - bib)
    for k in sorted(unresolved_xref):
        issues.append({"draft_line": line_of(draft_lines, "@" + k), "kind": "unresolved cross-reference", "detail": "@" + k,
                       "suggestion": "give the figure or table the label {#" + k + "} or correct the reference"})
    for k in sorted(set(static_missing) | missing_cites):
        issues.append({"draft_line": line_of(draft_lines, "@" + k), "kind": "citation key not in references.bib", "detail": "@" + k,
                       "suggestion": "add the entry to references.bib or correct the key"})
    if docx_info.get("media_by_extension", {}).get(".tif") or docx_info.get("media_by_extension", {}).get(".tiff"):
        for i, ln in enumerate(draft_lines, 1):
            if ln.startswith("![") and ".tif)" in ln:
                issues.append({"draft_line": i, "kind": "TIFF image embedded in the DOCX", "detail": re.search(r"\]\(([^)]+)\)", ln).group(1),
                               "suggestion": "use the PNG sibling for the DOCX (TIFF makes the file large; some viewers do not show TIFF)"})
    n3_remove = {Path(r["file"]).name for r in L.read_csv(L.N3) if r["status"] == "remove" and r["file"]}
    for i, ln in enumerate(draft_lines, 1):
        m = re.search(r"^!\[.*\]\(([^)]+)\)", ln)
        if not m:
            continue
        name = Path(m.group(1)).name
        if name in n3_remove:
            issues.append({"draft_line": i, "kind": "figure marked 'remove' in F13.6a N3 still in the draft", "detail": name,
                           "suggestion": "drop it in part 2 (N3: replaced by a table)"})
        if name == "Fig_collaboration_type_by_year.tif":
            issues.append({"draft_line": i, "kind": "figure drawn on institutions thesaurus v1", "detail": name,
                           "suggestion": "use figures/Fig_collaboration_type_by_year_v31 of this phase (thesaurus v3.1)"})
    if not outputs["main_v2.pdf"]["exists"]:
        err = next((w for w in runs["pdf"]["warnings"] if w.lower().startswith("error:") and "font" in w.lower()), "see run_logs/render.json")
        issues.append({"draft_line": "", "kind": "PDF with tectonic offline not built", "detail": L.words(err, 22),
                       "suggestion": ("built instead with xelatex (TinyTeX), offline" if outputs["pdf"]["exists"] else "no PDF built offline")
                                     + "; for the package let tectonic fetch the missing font once (network), then build offline"})
    if "pdf_xelatex" in runs and not outputs["main_v2_xelatex.pdf"]["exists"]:
        t = runs["pdf_xelatex"]["stdout"] + runs["pdf_xelatex"]["stderr"]
        m = re.search(r"is dated (\S+), but in your TeX tree the files require\s*\S*\s*at least (\S+?)\.", t)
        detail = ("mismatched LaTeX support files: format dated " + m.group(1) + ", expl3 files require " + m.group(2)) if m else \
            L.words(next((w for w in runs["pdf_xelatex"]["warnings"] if "error" in w.lower()), "see run_logs/render.json"), 22)
        issues.append({"draft_line": "", "kind": "PDF with xelatex (TinyTeX) offline not built", "detail": detail,
                       "suggestion": "regenerate TinyTeX's formats (fmtutil) or update TinyTeX on the author's machine; not done here"})
    if not outputs["docx"]["exists"]:
        issues.append({"draft_line": "", "kind": "DOCX not built", "detail": " | ".join(runs["docx"]["warnings"][-3:])[:200],
                       "suggestion": "see run_logs/render.json"})
    for i, ln in enumerate(draft_lines, 1):
        for m in re.finditer(r"\[\[([^\]]+)\]\]", ln):
            issues.append({"draft_line": i, "kind": "editorial mark left in the text", "detail": L.words(m.group(1), 12),
                           "suggestion": "resolved in F13.6c / F13.6d before the package is built"})
    other = sorted({w for r in runs.values() for w in r["warnings"]
                    if not re.search(r"crossref|[Cc]itation .* not found", w)})
    for w in other:
        issues.append({"draft_line": "", "kind": "other render message", "detail": L.words(w, 25), "suggestion": "see run_logs/render.json"})
    L.table("R1_render_issues", "R1 - render issues of the draft (part 1)", ["draft_line", "kind", "detail", "suggestion"], issues)
    log = {"run_utc": L.now(), "copy_changes": {"root_relative_figure_paths_fixed": n_fix, "pdf_engine_option_added": "-C (--only-cached)",
                                                "pdf_fallback_copy": fallback, "pdf_file_used": pdf_name},
           "commands": {k: {"args": " ".join(v["args"]), "returncode": v["returncode"], "seconds": v["seconds"]} for k, v in runs.items()},
           "outputs": outputs, "docx": docx_info, "unresolved_cross_references": sorted(unresolved_xref),
           "citation_keys_missing": sorted(set(static_missing) | missing_cites), "citation_keys_in_draft": len(cite_keys(src)),
           "warnings": {k: v["warnings"] for k, v in runs.items()}, "issues_in_R1": len(issues),
           "issue_kinds": {k: sum(1 for x in issues if x["kind"] == k) for k in sorted({x["kind"] for x in issues})}}
    L.jdump(log, L.RUN_LOGS / "render.json")
    for k, v in runs.items():
        (L.RUN_LOGS / f"render_{k}_console.txt").write_bytes((v["stdout"] + "\n----- stderr -----\n" + v["stderr"]).encode("utf-8"))
    print({k: (v["returncode"], v["seconds"]) for k, v in runs.items()}, outputs, docx_info, log["issue_kinds"],
          "unresolved:", log["unresolved_cross_references"], "missing cites:", log["citation_keys_missing"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
