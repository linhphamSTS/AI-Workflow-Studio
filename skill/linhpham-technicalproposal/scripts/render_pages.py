#!/usr/bin/env python3
"""Render a .docx to per-page PNGs at 300 DPI for the format reviewer's visual pass.

Pipeline: docx -> pdf (LibreOffice headless) -> per-page png (pdf2image / Poppler).

Outputs `<out_dir>/page_001.png`, `<out_dir>/page_002.png`, ...
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def find_libreoffice() -> str | None:
    candidates = ["soffice", "libreoffice",
                  r"C:\Program Files\LibreOffice\program\soffice.exe",
                  r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"]
    for c in candidates:
        if shutil.which(c) or Path(c).exists():
            return c
    return None


def docx_to_pdf(docx: Path, out_dir: Path) -> Path | None:
    soffice = find_libreoffice()
    if soffice is not None:
        r = subprocess.run([soffice, "--headless", "--convert-to", "pdf",
                            "--outdir", str(out_dir), str(docx)],
                           capture_output=True, text=True, timeout=180)
        if r.returncode == 0:
            pdf = out_dir / (docx.stem + ".pdf")
            if pdf.exists():
                return pdf
        print(f"! libreoffice failed: {r.stderr}", file=sys.stderr)
    # Fallback: Microsoft Word via win32com (Windows)
    try:
        import win32com.client  # type: ignore
        import pythoncom  # type: ignore
    except ImportError:
        print("! neither LibreOffice nor pywin32 available", file=sys.stderr)
        return None
    pdf = out_dir / (docx.stem + ".pdf")
    pythoncom.CoInitialize()
    word = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(str(docx.resolve()), ReadOnly=True)
        # 17 = wdFormatPDF
        doc.SaveAs(str(pdf.resolve()), FileFormat=17)
        doc.Close(False)
    except Exception as e:
        print(f"! Word COM conversion failed: {e}", file=sys.stderr)
        return None
    finally:
        try:
            if word is not None:
                word.Quit()
        except Exception:
            pass
        pythoncom.CoUninitialize()
    return pdf if pdf.exists() else None


def pdf_to_pngs(pdf: Path, out_dir: Path, dpi: int = 300) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    # Try pdf2image (needs Poppler) first
    try:
        from pdf2image import convert_from_path  # type: ignore
        try:
            pages = convert_from_path(str(pdf), dpi=dpi)
            for i, p in enumerate(pages, 1):
                path = out_dir / f"page_{i:03d}.png"
                p.save(path, "PNG")
                paths.append(path)
            return paths
        except Exception as e:
            print(f"! pdf2image failed ({e}); falling back to PyMuPDF", file=sys.stderr)
    except ImportError:
        pass
    # Fallback: PyMuPDF (self-contained, no system deps)
    try:
        import fitz  # type: ignore
    except ImportError:
        print("! install pdf2image+Poppler or PyMuPDF: pip install pymupdf", file=sys.stderr)
        return []
    doc = fitz.open(str(pdf))
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    for i, page in enumerate(doc, 1):
        pix = page.get_pixmap(matrix=mat, alpha=False)
        path = out_dir / f"page_{i:03d}.png"
        pix.save(str(path))
        paths.append(path)
    doc.close()
    return paths


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="docx", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dpi", type=int, default=300)
    args = ap.parse_args()

    if not args.docx.exists():
        print(f"! docx not found: {args.docx}", file=sys.stderr); return 1

    with tempfile.TemporaryDirectory() as td:
        pdf = docx_to_pdf(args.docx, Path(td))
        if pdf is None:
            print("! pdf conversion failed (LibreOffice missing?)", file=sys.stderr); return 1
        pages = pdf_to_pngs(pdf, args.out, dpi=args.dpi)
        print(f"Rendered {len(pages)} page(s) at {args.dpi} DPI -> {args.out}")
        for p in pages:
            print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
