#!/usr/bin/env python3
"""Make a Graphviz/mingrammer SVG self-contained by inlining external images.

Graphviz `-Tsvg` references icon PNGs by file path (`<image xlink:href="C:/.../eks.png">`),
so the SVG breaks when moved to another machine or opened in draw.io. This inlines
every local image as a base64 `data:` URI, producing a portable SVG that:
  * looks EXACTLY like the PNG (same render engine),
  * is vector (sharp at any zoom, prints crisply),
  * opens and edits in draw.io / any browser with the icons intact.

For icon-bearing (cloud / AI) diagrams this SVG is the recommended high-fidelity
editable deliverable; the `.drawio` is the native-shapes alternative.

Usage:
    python scripts/svg_util.py path/to/diagram.svg           # inline in place
    from svg_util import inline_images; inline_images(Path("d.svg"))
"""
from __future__ import annotations

import argparse
import base64
import mimetypes
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

_HREF = re.compile(r'(xlink:href|href)\s*=\s*"([^"]+)"')


def png_to_drawio(png_path: str | Path, title: str = "Diagram", out_path: str | Path | None = None) -> Path:
    """Wrap a rendered PNG as an editable draw.io file (single image cell).

    For diagrams that have no native mxGraph shape mapping (mingrammer icon
    diagrams, PIL sequences), this guarantees a `.drawio` that opens in draw.io
    showing the diagram EXACTLY as the PNG, and can be moved/resized/annotated.
    (Graphviz diagrams keep their native per-node editable `.drawio` instead.)"""
    from PIL import Image
    png_path = Path(png_path)
    out_path = Path(out_path) if out_path else png_path.with_suffix(".drawio")
    with Image.open(png_path) as im:
        w, h = im.size
    b64 = base64.b64encode(png_path.read_bytes()).decode("ascii")
    scale = 1200.0 / max(w, h)
    W, H = int(w * scale), int(h * scale)
    style = f"shape=image;verticalLabelPosition=bottom;verticalAlign=top;imageAspect=0;aspect=fixed;image=data:image/png,{b64};"
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<mxfile host="app.diagrams.net" version="24.0">\n'
        f'  <diagram name="{escape(title)}" id="d1">\n'
        f'    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" '
        f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{W + 40}" pageHeight="{H + 40}" math="0" shadow="0">\n'
        '      <root>\n        <mxCell id="0"/>\n        <mxCell id="1" parent="0"/>\n'
        f'        <mxCell id="2" value="" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="20" y="20" width="{W}" height="{H}" as="geometry"/></mxCell>\n'
        '      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n'
    )
    out_path.write_text(xml, encoding="utf-8")
    return out_path


def inline_images(svg_path: str | Path) -> Path:
    svg_path = Path(svg_path)
    text = svg_path.read_text(encoding="utf-8")
    base = svg_path.parent

    def repl(m: "re.Match") -> str:
        attr, ref = m.group(1), m.group(2)
        if ref.startswith(("data:", "http:", "https:", "#")):
            return m.group(0)
        p = Path(ref)
        if not p.is_absolute():
            p = (base / ref).resolve()
        if not p.exists():
            return m.group(0)
        mime = mimetypes.guess_type(str(p))[0] or "image/png"
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        return f'{attr}="data:{mime};base64,{b64}"'

    out = _HREF.sub(repl, text)
    svg_path.write_text(out, encoding="utf-8")
    return svg_path


def main() -> int:
    ap = argparse.ArgumentParser(description="Inline external images into an SVG (portable, self-contained).")
    ap.add_argument("svg", type=Path)
    args = ap.parse_args()
    if not args.svg.exists():
        print(f"! not found: {args.svg}", file=sys.stderr)
        return 1
    inline_images(args.svg)
    print(f"inlined images -> {args.svg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
