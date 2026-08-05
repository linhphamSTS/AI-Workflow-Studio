#!/usr/bin/env python3
"""Ingest a project folder into ONE text digest the diagram skill can analyse.

Extracts readable text from .txt / .md / .markdown / .csv / .json / .yaml / .docx /
.xlsx / .xlsm / .pdf under a folder (recursively, skipping noise dirs), and writes a
consolidated Markdown digest with one section per file. Phase 1 (Refine) reads the
digest to understand the system/requirements and propose the RIGHT SET of diagrams —
exactly the "point at a folder, ingest the docs, refine into diagram prompts" flow the
technical-proposal skill uses.

Readers: .docx → python-docx (paragraphs + tables); .xlsx/.xlsm → openpyxl (sheet
rows); .pdf → PyMuPDF (fitz) with a PyPDF2 fallback; text-like → read directly.

Usage:
  python ingest.py --dir <folder> [--out <digest.md>] [--max-chars-per-file N]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:  # so file names with non-ASCII (e.g. Vietnamese) never crash the cp1252 console
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "output", ".idea",
             ".vscode", "dist", "build", ".next", "bin", "obj", ".gradle", "target"}
TEXT_EXT = {".txt", ".md", ".markdown", ".csv", ".log", ".json", ".yaml", ".yml"}
DOC_EXT = {".docx"}
XLS_EXT = {".xlsx", ".xlsm"}
PDF_EXT = {".pdf"}
SUPPORTED = TEXT_EXT | DOC_EXT | XLS_EXT | PDF_EXT


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _read_docx(p: Path) -> str:
    from docx import Document
    doc = Document(str(p))
    parts = [para.text for para in doc.paragraphs if para.text.strip()]
    for tbl in doc.tables:
        for row in tbl.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def _read_xlsx(p: Path) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(str(p), read_only=True, data_only=True)
    out = []
    for ws in wb.worksheets:
        out.append(f"### Sheet: {ws.title}")
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None]
            if cells:
                out.append(" | ".join(cells))
    wb.close()
    return "\n".join(out)


def _read_pdf(p: Path) -> str:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(p))
        out = [page.get_text() for page in doc]
        doc.close()
        return "\n".join(out)
    except Exception:  # noqa: BLE001 — fall back to PyPDF2
        from PyPDF2 import PdfReader
        r = PdfReader(str(p))
        return "\n".join((pg.extract_text() or "") for pg in r.pages)


def extract(p: Path) -> str:
    ext = p.suffix.lower()
    if ext in DOC_EXT:
        return _read_docx(p)
    if ext in XLS_EXT:
        return _read_xlsx(p)
    if ext in PDF_EXT:
        return _read_pdf(p)
    if ext in TEXT_EXT:
        return _read_text(p)
    return ""


def _classify(p: Path, root: Path) -> str:
    """Sort one path into 'ingest', 'noise' (deliberately excluded) or 'unsupported'.

    The three-way split matters because the caller must ADVERTISE the unsupported ones.
    This script only extracts text formats, but the agent reading its digest is a full
    Claude session that can read a .pptx, a .doc or a screenshot perfectly well. So a
    silently-dropped file is not a capability limit, it is a lost pointer: the agent sees
    "4 files ingested", assumes that is the input set, and never opens the slide deck
    sitting next to them. Naming them converts a silent gap into an instruction.

    The exclusions mirror the skill's own Phase 1 rule ("skip hidden files, Word lock
    files, output/"). They lived only in the prompt before, so the web app — which
    pre-builds the digest with this script and hands it to the agent — ingested a
    `.internal/` folder of notes that a direct skill run would have skipped. A rule
    stated in a prompt and not enforced in the code that runs first is not a rule.

    Matching is done on the path RELATIVE to root: an absolute path may legitimately
    sit under a folder called `build`, `bin` or `.claude`, and matching the full path
    would silently ingest nothing at all from an otherwise valid project folder.
    """
    rel = p.relative_to(root).parts
    if any(part in SKIP_DIRS for part in rel):
        return "noise"
    if any(part.startswith(".") for part in rel):          # hidden files and hidden dirs
        return "noise"
    if p.name.startswith("~$"):                            # Word/Excel lock files
        return "noise"
    return "ingest" if p.suffix.lower() in SUPPORTED else "unsupported"


def ingest(root: Path, out: Path, max_chars: int = 20000):
    files, unsupported = [], []
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        kind = _classify(p, root)
        if kind == "ingest":
            files.append(p)
        elif kind == "unsupported":
            unsupported.append(p)
    sections = [f"# Ingested digest — {root.name}",
                f"_{len(files)} file(s) ingested from `{root}`._", ""]
    if unsupported:
        # Same principle as the truncation notice below: say what is missing and where to
        # get it, so nobody mistakes this digest for the complete input set.
        sections += [
            "## ⚠ Present in this folder but NOT extracted below",
            "",
            "This script extracts text formats only. The files below are real inputs it could",
            "not read. **Open them yourself** with the right handler before you analyse:",
            "`.doc` via LibreOffice, `.xls` via the spreadsheet reader, `.pptx` via python-pptx,",
            "images with vision, `.zip` by extracting it first. Treating the digest as complete",
            "would silently drop them.",
            "",
            *(f"- `{p.relative_to(root)}`" for p in unsupported),
            "",
        ]
    stats = []
    for p in files:
        rel = p.relative_to(root)
        try:
            text = extract(p).strip()
        except Exception as e:  # noqa: BLE001 — never fail the whole ingest on one file
            sections.append(f"## {rel}\n\n_(could not read: {type(e).__name__}: {e})_\n")
            stats.append((str(rel), "ERR")); continue
        trunc = ""
        if len(text) > max_chars:
            dropped = len(text) - max_chars
            text = text[:max_chars]
            # Say WHAT was lost and where to get it — a silent "…(truncated)" invites the
            # reader to treat a partial document as the whole requirement set.
            trunc = (f"  ⚠ TRUNCATED at {max_chars:,} chars — {dropped:,} more remain; "
                     f"open the original file for the rest")
        sections.append(f"## {rel}{trunc}\n\n{text or '_(no extractable text)_'}\n")
        stats.append((str(rel), f"{len(text)} chars"))
    for p in unsupported:
        # Surfaced on stdout as well as in the digest, so the web app's job log shows it
        # too and a human can spot a missed input without opening the digest.
        stats.append((str(p.relative_to(root)), "NOT EXTRACTED - open it yourself"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(sections), encoding="utf-8")
    return files, stats, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True, help="project folder to ingest")
    ap.add_argument("--out", type=Path, help="digest output path (default: <dir>/output/diagrams/_ingest_digest.md)")
    ap.add_argument("--max-chars-per-file", type=int, default=20000)
    a = ap.parse_args()
    if not a.dir.is_dir():
        print(f"! not a folder: {a.dir}", file=sys.stderr); sys.exit(2)
    out = a.out or (a.dir / "output" / "diagrams" / "_ingest_digest.md")
    files, stats, out = ingest(a.dir, out, a.max_chars_per_file)
    print(f"Ingested {len(files)} file(s) -> {out}")
    for name, st in stats:
        print(f"  - {name}: {st}")
    if not files:
        print("  (no supported files found: .txt .md .csv .json .yaml .docx .xlsx .pdf)")


if __name__ == "__main__":
    main()
