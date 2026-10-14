"""Phase F13.7c - step 2: the figure set for submission. In the order of the image lines of phase_F13_6c/draft/main_v2.qmd: figures/
figure_k.tif and figure_k.png, byte copies of the phases' files (for the collaboration types, F13.7a's v3.1 redraw, brief); figures/
figure_captions.txt (tab-separated: number, label, caption as in the draft with editorial marks removed, source files, sha256); tables/
F2_figure_set.csv (number, label, sources, dpi, size, bytes, sha256 of the TIFF and the PNG). Image metadata by F13.7a's meta() (Pillow;
no image is viewed, R18). F13.7a's manifest() is run unchanged on the F13.6c draft (tables/F1_figure_manifest.csv)."""
import sys
sys.dont_write_bytecode = True

import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f137c_lib as L

FG = L.FG
CAPTIONS = L.FIGURES / "figure_captions.txt"
CAP_FIELDS = ["number", "label", "caption", "source_tif", "sha256_tif", "source_png", "sha256_png"]


def main():
    L.install_r17_guard()
    figs = L.figure_order()
    FG.manifest()  # F13.7a's manifest of the draft's figures (+ the v3.1 redraw), now on the F13.6c draft
    L.FIGURES.mkdir(parents=True, exist_ok=True)
    rows, caps = [], ["\t".join(CAP_FIELDS)]
    for f in figs:
        k = f["k"]
        out = {}
        for ext in ("tif", "png"):
            src = f[ext]
            dst = L.FIGURES / f"figure_{k}.{ext}"
            b = L.path(L.rel(src)).read_bytes()
            dst.write_bytes(b)
            out[ext] = {"src": L.rel(src), "sha": L.sha256_file(dst), "meta": FG.meta(dst)}
            assert out[ext]["sha"] == L.sha256_file(src)
        mt, mp = out["tif"]["meta"], out["png"]["meta"]
        rows.append({"number": k, "label": "@" + f["label"], "draft_line": f["draft_line"], "source_tif": out["tif"]["src"], "source_png": out["png"]["src"],
                     "dpi_tif": mt["dpi"], "width_px_tif": mt["width_px"], "height_px_tif": mt["height_px"], "bytes_tif": mt["bytes"], "sha256_tif": out["tif"]["sha"],
                     "dpi_png": mp["dpi"], "width_px_png": mp["width_px"], "height_px_png": mp["height_px"], "bytes_png": mp["bytes"], "sha256_png": out["png"]["sha"],
                     "data_sheets": "; ".join(n for n, s, _ in L.figure_sheets([f]))})
        caps.append("\t".join([f"Figure {k}", "@" + f["label"], f["caption"], out["tif"]["src"], out["tif"]["sha"], out["png"]["src"], out["png"]["sha"]]))
    CAPTIONS.write_bytes(("\n".join(caps) + "\n").encode("utf-8"))
    fields = ["number", "label", "draft_line", "source_tif", "source_png", "dpi_tif", "width_px_tif", "height_px_tif", "bytes_tif", "sha256_tif", "dpi_png",
              "width_px_png", "height_px_png", "bytes_png", "sha256_png", "data_sheets"]
    L.table("F2_figure_set", "F2 - figure set for submission (order of the F13.6c draft)", fields, rows,
            note="figure_k.tif and figure_k.png are byte copies of the source files (sha256 equal); metadata read with Pillow, no image viewed (R18).")
    L.jdump({"figures": len(rows), "labels": [r["label"] for r in rows], "all_300_dpi": all(r["dpi_tif"] == 300 and r["dpi_png"] == 300 for r in rows),
             "min_width_px": min(min(r["width_px_tif"], r["width_px_png"]) for r in rows)}, L.RUN_LOGS / "figure_set.json")
    print(json.dumps({"figures": len(rows), "labels": [r["label"] for r in rows]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
