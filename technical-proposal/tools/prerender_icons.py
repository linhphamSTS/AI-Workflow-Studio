#!/usr/bin/env python3
"""Render every SVG in assets/icons/<pack>/svg/ to PNG at 200 and 300 DPI.

Output goes to `assets/icons/<pack>/png/<name>@200.png` and `@300.png`.
The diagram renderer prefers @300 then falls back to @200.

Uses cairosvg if available (cross-platform, no system deps beyond Python wheels).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
ICONS_ROOT = REPO_ROOT / "skill" / "linhpham-technicalproposal" / "assets" / "icons"


def render_svg(svg: Path, out: Path, dpi: int, base_px: int = 96) -> bool:
    try:
        import cairosvg
    except ImportError:
        print("! install cairosvg: pip install cairosvg", file=sys.stderr)
        return False
    out.parent.mkdir(parents=True, exist_ok=True)
    # We render at 'output_width' px where width is computed so a 1-inch SVG
    # renders to dpi px. SVG dimensions are unreliable, so we set a generous
    # output_width and let cairosvg scale up.
    output_width = int(base_px * dpi / 72)  # 72 = 1 inch in SVG units
    cairosvg.svg2png(url=str(svg), write_to=str(out),
                     output_width=output_width, dpi=dpi)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", action="append", help="Limit to specific pack(s)")
    ap.add_argument("--dpis", default="200,300", help="Comma-separated DPI list")
    args = ap.parse_args()

    dpis = [int(d) for d in args.dpis.split(",")]
    packs = [p.name for p in ICONS_ROOT.iterdir() if p.is_dir() and (p / "svg").exists()]
    selected = args.pack or packs

    rendered = 0
    for pack in selected:
        svg_dir = ICONS_ROOT / pack / "svg"
        if not svg_dir.exists():
            print(f"! no svg dir for pack: {pack}"); continue
        png_dir = ICONS_ROOT / pack / "png"
        for svg in svg_dir.glob("*.svg"):
            for dpi in dpis:
                out = png_dir / f"{svg.stem}@{dpi}.png"
                if render_svg(svg, out, dpi):
                    rendered += 1
    print(f"Rendered {rendered} PNG(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
