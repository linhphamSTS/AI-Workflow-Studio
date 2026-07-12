#!/usr/bin/env python3
"""One-shot script: derive proposal_template.docx from any prior STS proposal docx.

Strips body text, tables, and inline images from Sections 1 (INTRODUCTION)
and 2 (PROPOSED TECHNOLOGY). Headings are preserved as structural markers
so build_docx.py can locate the right insertion points. Everything from
Section 3 (PROPOSED DEVELOPMENT MANAGEMENT) onwards is kept verbatim
because that content is common across STS proposals.

Run once when bootstrapping the repo (or when a better source proposal is
available); the output proposal_template.docx is then committed and the
build script in production never re-derives it.

Usage:
    python tools/strip_template.py --src <path/to/prior_proposal.docx>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


INTRO_MARKER = "INTRODUCTION"
KEEP_MARKER = "PROPOSED DEVELOPMENT MANAGEMENT"
SECTION_HEADING_LEVEL = 3  # The H3 we use to bound the strip zone


def build_style_map(doc) -> dict:
    """style_id -> friendly name (e.g. '4' -> 'Heading 3')."""
    return {s.style_id: s.name for s in doc.styles if getattr(s, "style_id", None)}


def heading_level(p_el, style_map: dict) -> int | None:
    pPr = p_el.find(qn("w:pPr"))
    if pPr is None:
        return None
    pStyle = pPr.find(qn("w:pStyle"))
    if pStyle is None:
        return None
    val = pStyle.get(qn("w:val"), "")
    name = style_map.get(val, val)
    if not name.startswith("Heading"):
        return None
    try:
        return int(name.split()[-1])
    except ValueError:
        return None


def para_text(p_el) -> str:
    parts = []
    for t in p_el.iter(qn("w:t")):
        parts.append(t.text or "")
    return "".join(parts)


def clear_runs(p_el) -> None:
    """Remove every <w:r> child (including any embedded drawings/images)."""
    for r in p_el.findall(qn("w:r")):
        p_el.remove(r)


def strip(src: Path, dst: Path) -> None:
    doc = Document(str(src))
    body = doc.element.body
    style_map = build_style_map(doc)

    state = "before"  # before | strip | keep
    to_remove: list = []
    stripped_paragraphs = 0
    removed_tables = 0

    for child in list(body):
        tag = child.tag.rsplit("}", 1)[-1]

        if tag == "p":
            lvl = heading_level(child, style_map)
            txt = para_text(child).strip()

            if state == "before":
                if lvl == SECTION_HEADING_LEVEL and txt == INTRO_MARKER:
                    state = "strip"
                # else: cover / TOC — leave alone
            elif state == "strip":
                if lvl == SECTION_HEADING_LEVEL and txt == KEEP_MARKER:
                    state = "keep"
                    # this heading itself stays
                elif lvl is None:
                    # Body paragraph inside the strip zone — wipe content
                    if child.findall(qn("w:r")):
                        clear_runs(child)
                        stripped_paragraphs += 1
                # heading paragraphs in strip zone stay (structural)
            # state == "keep": leave alone

        elif tag == "tbl":
            if state == "strip":
                to_remove.append(child)
                removed_tables += 1

    for el in to_remove:
        el.getparent().remove(el)

    dst.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(dst))

    print(f"Source : {src}")
    print(f"Target : {dst}")
    print(f"Stripped paragraphs (body text/images cleared): {stripped_paragraphs}")
    print(f"Removed tables in strip zone: {removed_tables}")
    print(f"Final size: {dst.stat().st_size:,} bytes")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--src", type=Path, required=True,
        help="Path to a prior STS proposal .docx to derive the template from",
    )
    parser.add_argument(
        "--dst", type=Path,
        default=Path(__file__).resolve().parent.parent / "skill" / "linhpham-technicalproposal" / "templates" / "proposal_template.docx",
        help="Output path",
    )
    args = parser.parse_args()

    if not args.src.exists():
        print(f"! source not found: {args.src}", file=sys.stderr)
        return 1

    strip(args.src, args.dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
