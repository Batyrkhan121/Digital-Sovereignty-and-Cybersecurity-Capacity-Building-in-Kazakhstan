"""Phase F13.7a - step 3 (redraw) and step 2 (manifest).
Step 3: figures/Fig_collaboration_type_by_year_v31.{pdf,png,tif} and its CSV from phase_F13_2e's T2f_v31, drawn exactly as F13.2b's
f132b_affil.figure (stacked bars by year: single institution / domestic multi-institution / international; same colours, size, font,
labels; no title inside; 300 dpi; TIFF with LZW). Not viewed (R18).
Step 2: tables/F1_figure_manifest.csv - every figure the F13.6b draft references (its image lines) plus the redraw: one row per file
(pdf / png / tif): phase, file, format, pixels, dpi, bytes, data CSV, caption in the draft (first 15 words), and the usual journal
requirements (300 dpi; width >= 1000 px for one column). Image metadata only, read with Pillow (no image is viewed, R18); a PDF's
page size is read from its MediaBox. Deterministic."""
import sys
sys.dont_write_bytecode = True

import io
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f137a_lib as L

COLLAB = ["single institution", "domestic multi-institution", "international"]
COLORS = {"single institution": "#9ecae1", "domestic multi-institution": "#3182bd", "international": "#e6550d"}  # F13.2b's
BASE = L.FIGURES / "Fig_collaboration_type_by_year_v31"


def redraw():
    rows = [{"year": int(r["year"]), **{c: int(r[c]) for c in COLLAB}, "total": int(r["total"])} for r in L.read_csv(L.T2F_V31)]
    L.write_csv(str(BASE) + ".csv", ["year"] + COLLAB + ["total"], rows)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image
    matplotlib.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "svg.hashsalt": "f132b", "pdf.compression": 6})
    years = [r["year"] for r in rows]
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    bottom = [0] * len(rows)
    for c in COLLAB:
        vals = [r[c] for r in rows]
        ax.bar(years, vals, bottom=bottom, color=COLORS[c], edgecolor="white", linewidth=0.4, width=0.8, label=c)
        bottom = [a + b for a, b in zip(bottom, vals)]
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], rotation=90)
    ax.set_xlim(years[0] - 0.7, years[-1] + 0.7)
    ax.set_ylabel("Records (Scopus, n = 841)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(str(BASE) + ".pdf", metadata={"CreationDate": None, "ModDate": None})
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300, metadata={"Software": None})
    plt.close(fig)
    Path(str(BASE) + ".png").write_bytes(buf.getvalue())
    Image.open(io.BytesIO(buf.getvalue())).convert("RGB").save(str(BASE) + ".tif", compression="tiff_lzw", dpi=(300, 300))
    return rows


def meta(p):
    from PIL import Image
    if p.suffix.lower() == ".pdf":
        b = p.read_bytes()
        m = re.search(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]", b)
        w, h = (float(m.group(3)) - float(m.group(1)), float(m.group(4)) - float(m.group(2))) if m else (None, None)
        return {"format": "pdf", "width_px": "", "height_px": "", "dpi": "vector",
                "page_size_pt": f"{w:.1f} x {h:.1f}" if w else "", "bytes": p.stat().st_size}
    with Image.open(p) as im:
        dpi = im.info.get("dpi")
        d = round(float(dpi[0])) if dpi else ""
        return {"format": (im.format or p.suffix[1:]).lower(), "width_px": im.size[0], "height_px": im.size[1], "dpi": d, "page_size_pt": "",
                "bytes": p.stat().st_size}


def caption_words(cap, n=15):
    cap = re.sub(r"\[\[[^\]]*\]\]", " ", cap)
    cap = re.sub(r"[*_`]", "", cap)
    return L.words(cap, n)


def manifest():
    lines = L.path(L.DRAFT).read_bytes().decode("utf-8").splitlines()
    figs = []
    for i, ln in enumerate(lines, 1):
        m = re.match(r"^!\[(.*)\]\(([^)]+)\)\{#(fig-[\w-]+)\}", ln)
        if m:
            figs.append({"label": m.group(3), "draft_line": i, "caption": m.group(1), "path": m.group(2)})
    draft_dir = L.path(L.DRAFT).parent
    v1_caption = next((f["caption"] for f in figs if f["label"] == "fig-collaboration-type-by-year"), "")
    figs.append({"label": "fig-collaboration-type-by-year (v3.1 redraw)", "draft_line": "", "path": None,
                 "caption": v1_caption.replace("(Scopus", "(institutions thesaurus v3.1; Scopus", 1)})
    rows = []
    for f in figs:
        if f["path"] is None:
            base = BASE
        else:
            p = (draft_dir / f["path"]).resolve() if not f["path"].startswith("outputs/") else (L.ROOT / f["path"])
            base = p.with_suffix("")
        rel_base = base.relative_to(L.ROOT).as_posix()
        phase = next((part for part in rel_base.split("/") if part.startswith("phase_")), "outputs/figures (main.qmd's)")
        csvs = sorted(x.name for x in base.parent.iterdir() if x.name.startswith(base.name) and x.suffix == ".csv") if base.parent.exists() else []
        for ext in (".pdf", ".png", ".tif"):
            fp = Path(str(base) + ext)
            if not fp.exists():
                rows.append({"figure": f["label"], "draft_line": f["draft_line"], "phase": phase, "file": rel_base + ext, "format": ext[1:],
                             "exists": 0, "data_csv": "; ".join(csvs) or "none", "caption_first_15_words": caption_words(f["caption"]),
                             "meets_300_dpi": "", "meets_width_1000_px": "", "verdict": "file missing"})
                continue
            md = meta(fp)
            ok_dpi = md["dpi"] == "vector" or (md["dpi"] != "" and int(md["dpi"]) >= 300)
            ok_w = md["dpi"] == "vector" or (md["width_px"] != "" and int(md["width_px"]) >= 1000)
            rows.append({"figure": f["label"], "draft_line": f["draft_line"], "phase": phase, "file": rel_base + ext, "exists": 1, **md,
                         "data_csv": "; ".join(csvs) or "none", "caption_first_15_words": caption_words(f["caption"]),
                         "meets_300_dpi": "yes" if ok_dpi else "no", "meets_width_1000_px": "yes" if ok_w else "no",
                         "verdict": "meets" if ok_dpi and ok_w else "does not meet"})
    fields = ["figure", "draft_line", "phase", "file", "exists", "format", "width_px", "height_px", "dpi", "page_size_pt", "bytes", "data_csv",
              "caption_first_15_words", "meets_300_dpi", "meets_width_1000_px", "verdict"]
    L.table("F1_figure_manifest", "F1 - figures referenced by the draft (and the v3.1 redraw): files and journal requirements", fields, rows,
            note="Metadata only (Pillow; R18: no image viewed). Requirements: 300 dpi and width >= 1000 px for a one-column raster figure; a PDF "
                 "is vector (no pixel requirement). data_csv: the figure's data file beside it.")
    return figs, rows


def main():
    rows = redraw()
    figs, man = manifest()
    L.jdump({"redraw_rows": len(rows), "redraw_total": sum(r["total"] for r in rows), "figures": len(figs), "manifest_rows": len(man),
             "not_meeting": [r["file"] for r in man if r["verdict"] != "meets"]}, L.RUN_LOGS / "figures.json")
    print(len(figs), "figures;", len(man), "files;", sum(1 for r in man if r["verdict"] == "meets"), "meet;",
          [(r["file"].split("/")[-1], r["verdict"]) for r in man if r["verdict"] != "meets"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
