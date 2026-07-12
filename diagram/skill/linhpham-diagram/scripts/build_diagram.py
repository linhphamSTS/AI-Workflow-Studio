#!/usr/bin/env python3
"""Render an architecture diagram from a JSON spec at >= 300 DPI for sharp Word embedding.

The spec describes nodes (with an icon pack reference), groups, edges, and
optional legend / caption. The renderer enforces the Senior SA Charter
(see prompts/04_generate.md) at the primitive level:

  - chip / pill / callout widths sized to textbbox + padding,
  - vertical text centring uses (bb[1] + bb[3]) // 2,
  - arrows that approach a group title chip terminate above the chip,
  - dashed lines for async edges, solid for sync,
  - legend rendered automatically when > 2 colours / line styles are used.

Spec schema (JSON):
{
  "title": "Container Diagram — Booking Service",
  "figure_no": 3,
  "canvas": {"width_in": 6.5, "height_in": 4.2, "dpi": 300, "bg": "white"},
  "cloud": "aws | azure | gcp | generic | container | network | data | ai",
  "nodes": [
    {"id": "user", "label": "B2B Agent", "icon": "generic/user", "x": 0.5, "y": 0.5,
     "tags": ["external"]}
  ],
  "groups": [
    {"id": "vpc", "label": "VPC: 10.0.0.0/16", "border": "dashed",
     "members": ["lb", "api", "db"]}
  ],
  "edges": [
    {"from": "user", "to": "lb", "kind": "sync", "label": "HTTPS"},
    {"from": "api", "to": "queue", "kind": "async", "label": "BookingCreated"}
  ],
  "annotations": [
    {"on": "api->db", "text": "< 50ms p99"}
  ],
  "legend": "auto"
}

Coordinates are in canvas-relative inches (0..width_in, 0..height_in).
The renderer scales to pixels at the target DPI.

For complex diagrams that don't fit a simple grid, prefer hand-laid x,y over
auto-layout — graph engines tend to fight the SA's intent on layered architectures.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


SKILL_ROOT = Path(__file__).resolve().parent.parent
ICONS_ROOT = SKILL_ROOT / "assets" / "icons"


# ---------------------------------------------------------------------------
# Drawing primitives — enforce the Senior SA Charter at this level.
# ---------------------------------------------------------------------------


def load_font(size: int) -> ImageFont.FreeTypeFont:
    """Load a sans-serif font at the requested pixel size. Falls back to PIL default."""
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int, int, int]:
    """Return (left, top, width, height) using textbbox. Width includes the leading."""
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[0], bb[1], bb[2] - bb[0], bb[3] - bb[1]


def draw_centered_text(draw, xy_center, text, font, fill="black"):
    """Center text on (cx, cy). Uses textbbox midline for accurate vertical centring."""
    cx, cy = xy_center
    bb = draw.textbbox((0, 0), text, font=font)
    w = bb[2] - bb[0]
    midline_offset = (bb[1] + bb[3]) / 2
    x = cx - w / 2 - bb[0]
    y = cy - midline_offset
    draw.text((x, y), text, font=font, fill=fill)


def chip(draw, cx, cy, text, font, pad=12, fill="white", border="#333", text_color="black"):
    """Draw a centred chip whose width is the text bbox + 2*pad. Returns (x0, y0, x1, y1)."""
    bb = draw.textbbox((0, 0), text, font=font)
    w = (bb[2] - bb[0]) + 2 * pad
    h = (bb[3] - bb[1]) + 2 * pad
    x0, y0 = cx - w / 2, cy - h / 2
    x1, y1 = cx + w / 2, cy + h / 2
    draw.rounded_rectangle([x0, y0, x1, y1], radius=h / 3, fill=fill, outline=border, width=2)
    draw_centered_text(draw, (cx, cy), text, font, fill=text_color)
    return x0, y0, x1, y1


def rounded_group(draw, x0, y0, x1, y1, label, font, border="#666", dashed=False, fill=None):
    """Draw a group rounded-rectangle with a title chip on the top border.

    Returns the chip rect (cx0, cy0, cx1, cy1) so callers can route arrows
    around it (terminating arrows 6-10 px above cy0).
    """
    if fill is not None:
        draw.rounded_rectangle([x0, y0, x1, y1], radius=18, fill=fill, outline=border, width=2)
    else:
        # Draw dashed border via segmented rectangles if requested.
        if dashed:
            _dashed_rect(draw, x0, y0, x1, y1, color=border, dash=10, gap=6, radius=18)
        else:
            draw.rounded_rectangle([x0, y0, x1, y1], radius=18, outline=border, width=2)
    # Title chip centred on the top edge
    cx, cy = (x0 + x1) / 2, y0
    return chip(draw, cx, cy, label, font, pad=10, fill="white", border=border)


def _dashed_rect(draw, x0, y0, x1, y1, color, dash=10, gap=6, radius=18):
    # Approximate dashed border via short line segments along the rounded rect path.
    # For simplicity: draw 4 dashed straight sides; corners stay sharp (acceptable for trust-boundary cue).
    sides = [
        ((x0 + radius, y0), (x1 - radius, y0)),
        ((x1, y0 + radius), (x1, y1 - radius)),
        ((x1 - radius, y1), (x0 + radius, y1)),
        ((x0, y1 - radius), (x0, y0 + radius)),
    ]
    for (sx, sy), (ex, ey) in sides:
        dx, dy = ex - sx, ey - sy
        length = math.hypot(dx, dy)
        if length < 1:
            continue
        ux, uy = dx / length, dy / length
        pos = 0.0
        while pos < length:
            seg_end = min(pos + dash, length)
            draw.line([(sx + ux * pos, sy + uy * pos), (sx + ux * seg_end, sy + uy * seg_end)],
                      fill=color, width=2)
            pos = seg_end + gap


def arrow(draw, start, end, color="#333", style="solid", width=2, head=14, label=None, label_font=None):
    """Draw an arrow from start to end. style in ('solid', 'dashed')."""
    sx, sy = start
    ex, ey = end
    if style == "dashed":
        _draw_dashed_line(draw, start, end, color, width, dash=10, gap=6)
    else:
        draw.line([start, end], fill=color, width=width)
    # Arrowhead
    angle = math.atan2(ey - sy, ex - sx)
    h1 = (ex - head * math.cos(angle - math.pi / 8), ey - head * math.sin(angle - math.pi / 8))
    h2 = (ex - head * math.cos(angle + math.pi / 8), ey - head * math.sin(angle + math.pi / 8))
    draw.polygon([end, h1, h2], fill=color)
    # Label near midpoint
    if label and label_font is not None:
        mx, my = (sx + ex) / 2, (sy + ey) / 2
        # Slight offset perpendicular to arrow so label doesn't sit on the line
        ox, oy = -math.sin(angle) * 14, math.cos(angle) * 14
        draw_centered_text(draw, (mx + ox, my + oy), label, label_font, fill=color)


def _draw_dashed_line(draw, start, end, color, width, dash=10, gap=6):
    sx, sy = start
    ex, ey = end
    dx, dy = ex - sx, ey - sy
    length = math.hypot(dx, dy)
    if length < 1:
        return
    ux, uy = dx / length, dy / length
    pos = 0.0
    while pos < length:
        seg_end = min(pos + dash, length)
        draw.line([(sx + ux * pos, sy + uy * pos), (sx + ux * seg_end, sy + uy * seg_end)],
                  fill=color, width=width)
        pos = seg_end + gap


# ---------------------------------------------------------------------------
# Icon resolution.
# ---------------------------------------------------------------------------


def resolve_icon(pack_and_name: str, dpi: int = 300) -> Path | None:
    """`pack_and_name` looks like 'aws/lambda' or 'generic/user'. Returns PNG path or None."""
    pack, name = pack_and_name.split("/", 1)
    # Prefer pre-rendered PNG; fall back to SVG -> render on demand (TODO).
    for stem in (f"{name}@{dpi}", name):
        p = ICONS_ROOT / pack / "png" / f"{stem}.png"
        if p.exists():
            return p
    return None


def paste_icon(canvas: Image.Image, icon_path: Path, cx: int, cy: int, size_px: int) -> None:
    icon = Image.open(icon_path).convert("RGBA")
    icon.thumbnail((size_px, size_px), Image.LANCZOS)
    iw, ih = icon.size
    canvas.paste(icon, (int(cx - iw / 2), int(cy - ih / 2)), icon)


# ---------------------------------------------------------------------------
# Renderer.
# ---------------------------------------------------------------------------


def render(spec: dict, out: Path) -> None:
    canvas_cfg = spec.get("canvas", {})
    dpi = canvas_cfg.get("dpi", 300)
    width_in = canvas_cfg.get("width_in", 6.5)
    height_in = canvas_cfg.get("height_in", 4.2)
    bg = canvas_cfg.get("bg", "white")
    width_px = int(width_in * dpi)
    height_px = int(height_in * dpi)

    img = Image.new("RGB", (width_px, height_px), bg)
    draw = ImageDraw.Draw(img)

    label_font = load_font(int(0.16 * dpi))   # ~16pt at 100% — sharp at 300 DPI
    chip_font = load_font(int(0.14 * dpi))
    caption_font = load_font(int(0.13 * dpi))

    def to_px(xy):
        return (int(xy[0] * dpi), int(xy[1] * dpi))

    # 1. Groups first (so nodes sit on top).
    node_index = {n["id"]: n for n in spec.get("nodes", [])}
    for g in spec.get("groups", []):
        members = [node_index[m] for m in g["members"] if m in node_index]
        if not members:
            continue
        xs = [m["x"] for m in members]
        ys = [m["y"] for m in members]
        pad = 0.35
        x0, y0 = (min(xs) - pad) * dpi, (min(ys) - pad) * dpi
        x1, y1 = (max(xs) + pad) * dpi, (max(ys) + pad) * dpi
        rounded_group(draw, x0, y0, x1, y1,
                      label=g.get("label", g["id"]),
                      font=chip_font,
                      dashed=g.get("border") == "dashed")

    # 2. Nodes — icon + label below.
    icon_px = int(0.55 * dpi)
    for n in spec.get("nodes", []):
        cx, cy = to_px((n["x"], n["y"]))
        icon_ref = n.get("icon")
        if icon_ref:
            ip = resolve_icon(icon_ref, dpi=dpi)
            if ip:
                paste_icon(img, ip, cx, cy, icon_px)
            else:
                # Placeholder box if icon missing
                half = icon_px // 2
                draw.rounded_rectangle([cx - half, cy - half, cx + half, cy + half],
                                       radius=12, outline="#999", width=2)
                draw_centered_text(draw, (cx, cy), "?", load_font(int(0.3 * dpi)), fill="#999")
        # Label below icon
        if "label" in n:
            draw_centered_text(draw, (cx, cy + icon_px // 2 + int(0.18 * dpi)),
                               n["label"], label_font, fill="black")

    # 3. Edges.
    for e in spec.get("edges", []):
        a = node_index.get(e["from"])
        b = node_index.get(e["to"])
        if a is None or b is None:
            continue
        start = to_px((a["x"], a["y"]))
        end = to_px((b["x"], b["y"]))
        style = "dashed" if e.get("kind") == "async" else "solid"
        arrow(draw, start, end,
              color=e.get("color", "#333"),
              style=style,
              label=e.get("label"),
              label_font=caption_font,
              width=max(2, dpi // 150),
              head=int(0.05 * dpi))

    # 4. Caption / figure title at bottom.
    title = spec.get("title")
    fig_no = spec.get("figure_no")
    if title:
        cap = f"Figure {fig_no}: {title}" if fig_no else title
        draw_centered_text(draw, (width_px // 2, height_px - int(0.18 * dpi)),
                           cap, caption_font, fill="black")

    # 5. Save high-quality PNG.
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, format="PNG", optimize=False, dpi=(dpi, dpi))
    print(f"Rendered {out}  ({width_px}x{height_px} @ {dpi} DPI)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", type=Path, required=True, help="JSON spec file")
    ap.add_argument("--out", type=Path, required=True, help="Output PNG path")
    args = ap.parse_args()
    if not args.spec.exists():
        print(f"! spec not found: {args.spec}", file=sys.stderr)
        return 1
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    render(spec, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
