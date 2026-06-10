#!/usr/bin/env python3
"""Read a legacy .doc (Word 97-2003) file by converting to .docx via LibreOffice headless,
then extracting via docx_reader. Falls back to antiword if available."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from docx_reader import read as read_docx


def find_libreoffice() -> str | None:
    candidates = ["soffice", "libreoffice"]
    if sys.platform == "win32":
        candidates += [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
    for c in candidates:
        if shutil.which(c) or Path(c).exists():
            return c
    return None


def convert_to_docx(doc_path: Path, out_dir: Path) -> Path | None:
    soffice = find_libreoffice()
    if soffice is None:
        return None
    cmd = [soffice, "--headless", "--convert-to", "docx", "--outdir", str(out_dir), str(doc_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"! libreoffice convert failed: {result.stderr}", file=sys.stderr)
        return None
    converted = out_dir / (doc_path.stem + ".docx")
    return converted if converted.exists() else None


def read(path: Path) -> str:
    with tempfile.TemporaryDirectory() as td:
        out = convert_to_docx(path, Path(td))
        if out is None:
            # antiword fallback (plain text)
            if shutil.which("antiword"):
                r = subprocess.run(["antiword", str(path)], capture_output=True, text=True)
                if r.returncode == 0:
                    return r.stdout
            raise RuntimeError(
                "Could not convert .doc to .docx — install LibreOffice or antiword."
            )
        return read_docx(out)


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
