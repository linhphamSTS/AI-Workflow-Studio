#!/usr/bin/env python3
"""Render a UML SEQUENCE diagram from a JSON spec at >= 300 DPI (PIL).

Graphviz lays out graphs, not time-ordered interactions, so sequence diagrams
get their own lifeline-based renderer. Output is a sharp PNG suitable for a
6.5" Word embed. (No `.drawio` is emitted for sequences — draw.io's UML
sequence shapes don't round-trip from a Graphviz layout; the PNG is the
deliverable, edit the spec to change it.)

Spec schema (JSON):
{
  "slug": "checkout_seq",
  "title": "Checkout — Happy Path",
  "diagram_type": "sequence",
  "participants": [
    {"id": "u",   "label": "Customer", "role": "actor"},
    {"id": "api", "label": "Order API"},
    {"id": "pay", "label": "Payment GW", "role": "external"},
    {"id": "db",  "label": "Orders DB", "role": "database"}
  ],
  "messages": [
    {"from": "u",   "to": "api", "label": "POST /checkout",     "kind": "sync"},
    {"from": "api", "to": "db",  "label": "insert order",       "kind": "sync"},
    {"from": "api", "to": "pay", "label": "charge",             "kind": "sync"},
    {"from": "pay", "to": "api", "label": "authorised",         "kind": "return"},
    {"from": "api", "to": "api", "label": "emit OrderPlaced",   "kind": "self"},
    {"from": "api", "to": "u",   "label": "201 Created",        "kind": "return"}
  ],
  "fragments": [
    {"type": "alt", "label": "payment authorised", "from": 2, "to": 5}
  ]
}

message.kind: sync (solid, filled head) | async (dashed, open head) |
              return|reply (dashed, open head) | self (self-call loop) | create | destroy

Usage:
    python scripts/build_sequence.py --spec spec.json --out out/foo.png
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# --- geometry (pixels @ 300 DPI) ---
MARGIN = 110
TITLE_H = 130
HEAD_H = 150
COL_W = 640
MSG_GAP = 165
LIFELINE_PAD = 70
FRAG_PAD = 22

INK = "#1a1a1a"
LIFELINE = "#90A4AE"
ARROW = "#37474F"
HEAD_FILL = "#E3F2FD"
HEAD_STROKE = "#1565C0"
ACTOR_FILL = "#FFF8E1"
ACTOR_STROKE = "#F9A825"
EXT_FILL = "#ECEFF1"
EXT_STROKE = "#607D8B"
DB_FILL = "#E0F2F1"
DB_STROKE = "#00897B"
FRAG_STROKE = "#8E24AA"
FRAG_LABEL_BG = "#F3E5F5"


def load_font(size: int, bold: bool = False):
    names = (["seguisb.ttf", "segoeuib.ttf", "arialbd.ttf"] if bold
             else ["segoeui.ttf", "calibri.ttf", "arial.ttf"])
    roots = ["C:/Windows/Fonts/", "/System/Library/Fonts/", "/usr/share/fonts/truetype/dejavu/"]
    extra = ["DejaVuSans-Bold.ttf"] if bold else ["DejaVuSans.ttf"]
    for r in roots:
        for n in names + extra:
            p = Path(r) / n
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def _txt_wh(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def _centered(draw, cx, cy, text, font, fill=INK):
    bb = draw.textbbox((0, 0), text, font=font)
    w = bb[2] - bb[0]
    draw.text((cx - w / 2 - bb[0], cy - (bb[1] + bb[3]) / 2), text, font=font, fill=fill)


def _head_colors(role: str):
    return {
        "actor": (ACTOR_FILL, ACTOR_STROKE), "person": (ACTOR_FILL, ACTOR_STROKE),
        "external": (EXT_FILL, EXT_STROKE), "database": (DB_FILL, DB_STROKE),
        "datastore": (DB_FILL, DB_STROKE),
    }.get((role or "").lower(), (HEAD_FILL, HEAD_STROKE))


def _dashed_h(draw, x0, x1, y, color, width=3, dash=16, gap=12):
    x = x0
    while x < x1:
        draw.line([(x, y), (min(x + dash, x1), y)], fill=color, width=width)
        x += dash + gap


def _dashed_v(draw, x, y0, y1, color, width=3, dash=16, gap=12):
    y = y0
    while y < y1:
        draw.line([(x, y), (x, min(y + dash, y1))], fill=color, width=width)
        y += dash + gap


def _arrowhead(draw, x, y, direction, color, filled=True, size=20):
    """direction: +1 rightwards, -1 leftwards."""
    dx = size * direction
    pts = [(x, y), (x - dx, y - size * 0.55), (x - dx, y + size * 0.55)]
    if filled:
        draw.polygon(pts, fill=color)
    else:
        draw.line([pts[0], pts[1]], fill=color, width=3)
        draw.line([pts[0], pts[2]], fill=color, width=3)


def render(spec: dict, out: Path) -> Path:
    parts = spec.get("participants", [])
    msgs = spec.get("messages", [])
    frags = spec.get("fragments", []) or []
    if not parts:
        raise ValueError("sequence spec needs at least one participant")

    n = len(parts)
    n_rows = len(msgs)
    width = MARGIN * 2 + COL_W * n
    height = TITLE_H + HEAD_H + MSG_GAP * (n_rows + 1) + MARGIN

    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)

    f_title = load_font(54, bold=True)
    f_head = load_font(34, bold=True)
    f_msg = load_font(28)
    f_frag = load_font(26, bold=True)

    # title
    if spec.get("title"):
        _centered(d, width / 2, MARGIN * 0.7, spec["title"], f_title)

    # participant x-centres
    cx = {p["id"]: MARGIN + COL_W // 2 + i * COL_W for i, p in enumerate(parts)}
    head_top = TITLE_H
    head_bot = TITLE_H + HEAD_H
    life_bot = height - MARGIN

    # lifelines
    for p in parts:
        x = cx[p["id"]]
        _dashed_v(d, x, head_bot + 6, life_bot, LIFELINE)

    # participant header boxes
    for p in parts:
        x = cx[p["id"]]
        fill, stroke = _head_colors(p.get("role"))
        label = p.get("label", p["id"])
        bw = min(COL_W - 60, max(220, _txt_wh(d, label, f_head)[0] + 70))
        d.rounded_rectangle([x - bw / 2, head_top, x + bw / 2, head_bot],
                            radius=16, fill=fill, outline=stroke, width=4)
        _centered(d, x, (head_top + head_bot) / 2, label, f_head)

    # fragment boxes (drawn behind messages): map 1-based msg index -> y
    def msg_y(i):  # i is 0-based row
        return head_bot + MSG_GAP * (i + 1)

    for fr in frags:
        try:
            i0 = int(fr.get("from", 1)) - 1
            i1 = int(fr.get("to", n_rows)) - 1
        except (TypeError, ValueError):
            continue
        y0 = msg_y(i0) - MSG_GAP * 0.55
        y1 = msg_y(i1) + MSG_GAP * 0.4
        d.rectangle([MARGIN * 0.6, y0, width - MARGIN * 0.6, y1],
                    outline=FRAG_STROKE, width=3)
        tag = fr.get("type", "alt").upper()
        lbl = f"{tag}  [{fr.get('label','')}]" if fr.get("label") else tag
        tw, th = _txt_wh(d, lbl, f_frag)
        d.rectangle([MARGIN * 0.6, y0, MARGIN * 0.6 + tw + 2 * FRAG_PAD, y0 + th + 2 * FRAG_PAD],
                    fill=FRAG_LABEL_BG, outline=FRAG_STROKE, width=3)
        d.text((MARGIN * 0.6 + FRAG_PAD, y0 + FRAG_PAD), lbl, font=f_frag, fill=INK)

    # messages
    for i, m in enumerate(msgs):
        y = msg_y(i)
        src, dst = m.get("from"), m.get("to")
        if src not in cx or dst not in cx:
            continue
        kind = (m.get("kind") or "sync").lower()
        label = m.get("label", "")
        x0, x1 = cx[src], cx[dst]

        if kind == "self" or src == dst:
            # self-call loop to the right of the lifeline
            w = 150
            top, bot = y - 34, y + 34
            d.line([(x0, top), (x0 + w, top)], fill=ARROW, width=3)
            d.line([(x0 + w, top), (x0 + w, bot)], fill=ARROW, width=3)
            d.line([(x0 + w, bot), (x0, bot)], fill=ARROW, width=3)
            _arrowhead(d, x0, bot, -1, ARROW, filled=True)
            if label:
                d.text((x0 + w + 18, y - 18), label, font=f_msg, fill=INK)
            continue

        direction = 1 if x1 > x0 else -1
        dashed = kind in ("async", "return", "reply", "destroy")
        if dashed:
            _dashed_h(d, min(x0, x1), max(x0, x1), y, ARROW)
        else:
            d.line([(x0, y), (x1, y)], fill=ARROW, width=3)
        _arrowhead(d, x1, y, direction, ARROW, filled=(kind in ("sync", "create")))
        if label:
            tw, _ = _txt_wh(d, label, f_msg)
            lx = (x0 + x1) / 2
            _centered(d, lx, y - 26, label, f_msg)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, format="PNG", optimize=False, dpi=(300, 300))
    print(f"Rendered {out}  ({width}x{height} @ 300 DPI)")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Render a UML sequence diagram from a JSON spec (PIL @300 DPI).")
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if not args.spec.exists():
        print(f"! spec not found: {args.spec}", file=sys.stderr)
        return 1
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    render(spec, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
