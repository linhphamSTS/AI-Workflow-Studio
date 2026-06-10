#!/usr/bin/env python3
"""Extract text from a .pdf. Uses pypdf (pure Python, no system deps)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def read(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            raise RuntimeError("Install pypdf: pip install pypdf")

    reader = PdfReader(str(path))
    chunks: list[str] = []
    for i, page in enumerate(reader.pages, 1):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            text = f"[page {i}: extract error: {e}]"
        chunks.append(f"--- Page {i} ---\n{text}")
    return "\n\n".join(chunks)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    args = ap.parse_args()
    if not args.path.exists():
        print(f"! file not found: {args.path}", file=sys.stderr)
        return 1
    sys.stdout.write(read(args.path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
