#!/usr/bin/env python3
"""Pixel-perfect CLOUD / INFRA architecture renderer — manual grid layout (PIL).

Graphviz auto-layout can't hit brochure-grade cloud diagrams. This renderer puts
everything on a fixed grid with hand-computed coordinates and draws orthogonal
connectors itself — the approach that produces genuinely hand-crafted-looking
AWS/Azure/GCP diagrams.

Model (opinionated for tiered reference architectures):
  • COLUMNS = tiers, left→right (Edge | Public subnet | Private/compute | Data | Messaging).
    Each column stacks its NODES vertically and may carry its own sub-boundary label.
  • WRAPS = boundary boxes that span a CONTIGUOUS RANGE of columns (e.g. a VPC/VNet
    wrapping the public+private+data+messaging tiers). Drawn behind the columns.
  • SHARED band = a bottom strip for cross-cutting services (0–1 edges).
  • EDGES = explicit list, routed orthogonally (right-angle), solid/dashed + label.
Icons composited from the mingrammer `diagrams` package's bundled service PNGs.

Spec (dict):
{
 "title": "...",
 "columns": [
   {"id":"edge","boundary":{"label":"Edge / Global","fill":"#FFF8E1","stroke":"#F9A825"},
    "nodes":[{"id":"dns","label":"Route 53","icon":"route-53"}, ...]},
   {"id":"public","boundary":{"label":"Public Subnets","fill":"#FBF3E0","stroke":"#F9A825"},"nodes":[...]},
   {"id":"data","boundary":{"label":"Data (Multi-AZ)","fill":"#E7F0FA","stroke":"#1E88E5"},
    "nodes":[{"id":"aur","label":"Aurora primary","icon":"aurora","tags":["SoR","PII"]}, ...]},
   ...
 ],
 "wraps": [{"label":"VPC 10.0.0.0/16","fill":"#E8F1FB","stroke":"#8C4FFF","dashed":true,
            "cols":["public","eks","data","msg"]}],
 "shared": {"label":"Security & Observability","fill":"#FDECEA","stroke":"#DD344C","nodes":[...]},
 "edges": [{"from":"waf","to":"alb","label":"HTTPS"},
           {"from":"eks","to":"iam","label":"IAM / KMS / metrics","style":"dashed"}],
 "legend": true
}
Usage: python scripts/build_cloud.py --spec spec.json --out out.png
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont


def _resources_root():
    try:
        import diagrams
    except ImportError:
        return None
    base = Path(diagrams.__file__).parent
    for c in (base.parent / "resources", base / "resources"):
        if c.exists():
            return c
    return None

_RES = _resources_root()
_ASSETS = Path(__file__).resolve().parent.parent / "assets" / "icons"   # skill's own packs (e.g. ai/ LLM logos)
_ICON_CACHE: dict = {}

# icon-stem (provider/stem, as used in specs) -> draw.io NATIVE vendor stencil hint
# (drawio_export.SHAPE_STYLES). Used so the .drawio carries real vector AWS/Azure/GCP/K8s
# shapes (editable/swappable), not embedded raster images. Anything not mapped falls back
# to a base64 image cell (still an individually editable cell).
STEM2SHAPE = {
    "aws/route-53": "aws-route53", "aws/cloudfront": "aws-cloudfront", "aws/waf": "aws-waf",
    "aws/elb-application-load-balancer": "aws-alb", "aws/elastic-kubernetes-service": "aws-eks",
    "aws/aurora": "aws-aurora", "aws/elasticache": "aws-redis", "aws/managed-streaming-for-kafka": "aws-msk",
    "aws/simple-notification-service": "aws-sns", "aws/simple-queue-service": "aws-sqs",
    "aws/identity-and-access-management": "aws-iam", "aws/key-management-service": "aws-kms",
    "aws/secrets-manager": "aws-secrets", "aws/cloudwatch": "aws-cloudwatch",
    "aws/simple-storage-service": "aws-s3", "aws/ec2-container-registry": "aws-ecr",
    "azure/front-doors": "azure-front-door", "azure/application-gateway": "azure-app-gateway",
    "azure/kubernetes-services": "azure-aks", "azure/sql-database": "azure-sql", "azure/cache-redis": "azure-redis",
    "azure/blob-storage": "azure-blob", "azure/service-bus": "azure-service-bus",
    "azure/azure-active-directory": "azure-entra", "azure/key-vaults": "azure-keyvault", "azure/azure-monitor": "azure-monitor",
    "gcp/cdn": "gcp-cloud-cdn", "gcp/load-balancing": "gcp-load-balancing", "gcp/run": "gcp-cloud-run",
    "gcp/kubernetes-engine": "gcp-gke", "gcp/sql": "gcp-sql", "gcp/pubsub": "gcp-pubsub", "gcp/storage": "gcp-gcs",
    "gcp/iam": "gcp-iam", "gcp/key-management-service": "gcp-kms",
    "k8s/ing": "k8s-ing", "k8s/svc": "k8s-svc", "k8s/pod": "k8s-pod", "k8s/deploy": "k8s-deploy",
    "k8s/sts": "k8s-statefulset", "k8s/cm": "k8s-cm", "k8s/secret": "k8s-secret", "k8s/node": "k8s-node",
    "onprem/internet": "internet", "onprem/server": "server", "onprem/client": "client", "onprem/users": "users",
}

def _search(root: Path, stem: str):
    if not root or not root.exists():
        return None
    exact = list(root.rglob(f"{stem}.png"))
    if exact:
        return min(exact, key=lambda x: len(str(x)))
    loose = sorted(root.rglob(f"{stem}*.png"), key=lambda x: len(x.name))
    return loose[0] if loose else None

def resolve_icon(ref: str):
    """ref is 'provider/stem' (e.g. 'aws/route-53', 'gcp/run', 'ai/openai') or a bare
    stem. Searches the mingrammer bundled resources first, then the skill's own
    assets/icons/<prov> packs (for AI/LLM logos not in mingrammer)."""
    if ref in _ICON_CACHE:
        return _ICON_CACHE[ref]
    p = None
    if ref:
        if "/" in ref:
            prov, stem = ref.split("/", 1)
            p = _search((_RES / prov) if _RES else None, stem) or _search(_ASSETS / prov, stem)
        else:
            p = _search(_RES, ref)
    _ICON_CACHE[ref] = p
    return p

# ---- geometry (px @ 300 DPI) ---------------------------------------------------
S = 3
ICON = 54 * S            # official diagrams keep icons modest (airy)
CELL_W = 140 * S
LABEL_GAP = 5 * S
ROW_GAP = 42 * S         # generous, even whitespace between nodes
COL_PAD = 20 * S
COL_HDR = 28 * S
COL_GAP = 86 * S         # airy gutters between tiers
WRAP_PAD = 26 * S
WRAP_HDR = 32 * S
BR = 5 * S               # boundary corner radius (official boxes are near-square)
BADGE = 22 * S           # corner category-icon badge on a boundary (the official "#1 tell")
MARGIN = 38 * S
TITLE_H = 44 * S
BAND_GAP = 42 * S
INK = "#37474F"; PUR = "#8E24AA"; TXT = "#1b2733"

def _font(sz, bold=False):
    names = (["seguisb.ttf", "segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"])
    for r in ("C:/Windows/Fonts/", "/usr/share/fonts/truetype/dejavu/"):
        for n in names + (["DejaVuSans-Bold.ttf"] if bold else ["DejaVuSans.ttf"]):
            if (Path(r) / n).exists():
                return ImageFont.truetype(str(Path(r) / n), sz)
    return ImageFont.load_default()

FT = {}
def _init_fonts():
    # Sized against the PAGE, not against the canvas. A figure is embedded at 6.5in wide, so
    # a label lands at font_px * 72 * 6.5 / image_width points: at the old 10*S a five-column
    # architecture came out at 3.5pt, which is sharp and unreadable at once. The cell width is
    # deliberately NOT raised to match, because widening the cell widens the image and the two
    # cancel out exactly; the cost of bigger text is more wrapping and a taller figure, and
    # height is the dimension with room to spare.
    FT["title"] = _font(17 * S, True); FT["node"] = _font(14 * S, True)
    FT["tech"] = _font(9 * S); FT["hdr"] = _font(10 * S, True); FT["edge"] = _font(9 * S)

def _wrap_multi(draw, text, font, maxw, maxlines=0):
    words = str(text).split(); lines = []; cur = ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines[:maxlines] if maxlines else lines

def _wrap(draw, text, font, maxw):
    """Wrap a node label to at most three lines, and SAY SO when words are dropped.

    This silently returned the first three lines and discarded the rest, so a label one word
    too long lost that word in the delivered figure with nothing reporting it. Losing text
    without a trace is the worst defect this renderer can produce, because every check
    downstream sees a perfectly well-formed picture.
    """
    lines = _wrap_multi(draw, text, font, maxw)
    if len(lines) > 3:
        _lint_issue("label_truncated",
                    f"the label {str(text)[:44]!r} needs {len(lines)} lines and only three fit, "
                    f"so {' '.join(lines[3:])[:40]!r} is dropped from the figure; shorten it or "
                    f"move the detail into 'tech' / 'tags'")
    return lines[:3]

def _hdr_offset(has_badge):
    """left inset of a boundary's header text (past the corner category badge)."""
    return (9 * S + BADGE + 6 * S) if has_badge else 10 * S

# ---- layout lint (self-check): headers must not overflow their box, and edge
# labels must not overlap node/header text. Runs on EVERY cloud render, so it
# guards all diagrams — not just the samples. Results go to <slug>.lint.json
# (read by diagram_check.py) and stderr.
_LINT = {"boxes": [], "issues": []}
# Canvas width, published once the size is known so an edge label can tell whether the gutter
# it wants to sit in actually exists. A same-column label in the LAST column was pushed into a
# right-hand gutter that is off the canvas, and the text was silently cut in half by the image
# edge; the layout lint saw a box, not a clipped one, so nothing reported it.
_CANVAS_W = 0
_DRAWIO_MEASURE = None
def _lint_reset():
    _LINT["boxes"] = []; _LINT["issues"] = []
def _lint_box(kind, bbox):
    _LINT["boxes"].append((kind, tuple(bbox)))
def _lint_issue(code, msg):
    _LINT["issues"].append({"code": code, "msg": msg})
def _bbox_overlap(a, b, pad=0):
    return not (a[2] <= b[0] + pad or b[2] <= a[0] + pad or a[3] <= b[1] + pad or b[3] <= a[1] + pad)
def _lint_layout():
    """cross-check collected label boxes; append overlap issues. Header-overflow
    issues are appended inline by _boundary. De-duplicates before returning."""
    edges = [b for k, b in _LINT["boxes"] if k == "edgelabel"]
    solids = [(k, b) for k, b in _LINT["boxes"] if k in ("nodelabel", "header", "icon")]
    for eb in edges:
        for k, ob in solids:
            if _bbox_overlap(eb, ob, pad=2 * S):
                _lint_issue("label_overlap", f"an edge label overlaps a {k.replace('label','')} label")
                break
    # Text drawn past the canvas is cut by the image edge and reads as a truncated word. The
    # overlap test above compared labels against each other and never against the page they
    # are on, so a clipped label passed every check while being unreadable in the delivered
    # figure. Anything drawn outside the canvas counts, not only edge labels.
    if _CANVAS_W:
        for k, b in _LINT["boxes"]:
            if b[0] < 0 or b[2] > _CANVAS_W:
                _lint_issue("label_clipped",
                            f"a {k.replace('label', ' ')} label is drawn past the canvas edge "
                            f"and will be cut off (x {int(b[0])}..{int(b[2])} of {_CANVAS_W})")
                break
    seen = set(); uniq = []
    for it in _LINT["issues"]:
        key = (it["code"], it["msg"])
        if key not in seen:
            seen.add(key); uniq.append(it)
    return uniq

def _clear_label_pos(tx, ty, w, hh, vert):
    """Slide an edge label ALONG its own run until it stops sitting on something.

    The lint reported an overlap and left it there, so the defect had to be fixed by hand in
    the spec every time, and on a generated run there is nobody to do that. Sliding along the
    run keeps the label on the line it belongs to, which a perpendicular nudge would not.
    Returns the original position when nothing is free, so the lint still reports it rather
    than the label being moved somewhere misleading.
    """
    solids = [b for k, b in _LINT["boxes"] if k in ("nodelabel", "header", "icon")]
    if not solids:
        return tx, ty

    def box(X, Y):
        return (X - 3, Y - hh / 2 - 2, X + w + 3, Y + hh / 2 + 2)

    for step in (0, 20 * S, -20 * S, 40 * S, -40 * S, 64 * S, -64 * S):
        X, Y = (tx, ty + step) if vert else (tx + step, ty)
        if _CANVAS_W and (X < MARGIN / 2 or X + w + 3 > _CANVAS_W - MARGIN / 2):
            continue
        if not any(_bbox_overlap(box(X, Y), ob, pad=2 * S) for ob in solids):
            return X, Y
    return tx, ty


def _ctext(draw, cx, y, text, font, fill=TXT):
    w = draw.textlength(text, font=font); draw.text((cx - w / 2, y), text, font=font, fill=fill)

def _node_lines(draw, n):
    lines = _wrap(draw, n.get("label", n["id"]), FT["node"], CELL_W - 6 * S)
    extra = []
    if n.get("tech"): extra.append(("tech", f'[{n["tech"]}]'))
    if n.get("tags"): extra.append(("tag", "  ".join(f'[{t}]' for t in n["tags"])))
    return lines, extra

def _node_h(draw, n):
    lines, extra = _node_lines(draw, n)
    return ICON + LABEL_GAP + len(lines) * (FT["node"].size + 2) + len(extra) * (FT["tech"].size + 3) + 3 * S

# ---- layout --------------------------------------------------------------------
def _measure_col(d, col):
    pad = COL_PAD if col.get("boundary") else 0
    ch = sum(_node_h(d, n) for n in col["nodes"]) + ROW_GAP * (len(col["nodes"]) - 1)
    base_w = CELL_W + 2 * pad
    hdr = 0
    if col.get("boundary"):
        b = col["boundary"]; label = b.get("label", "")
        toff = _hdr_offset(bool(b.get("icon")))
        # widen the box so the header fits on ONE line, up to a cap; past the cap,
        # wrap the header and grow the header zone — either way it never overflows.
        need = toff + int(d.textlength(label, font=FT["hdr"])) + 12 * S
        cap = int(2.4 * CELL_W)
        base_w = min(max(base_w, need), max(base_w, cap))
        avail = base_w - toff - 12 * S
        nlines = max(1, len(_wrap_multi(d, label, FT["hdr"], avail, 3)))
        hdr = COL_HDR + (nlines - 1) * (FT["hdr"].size + 6 * S)
    col["_w"] = base_w
    col["_h"] = ch + hdr + 2 * pad
    col["_hdr"] = hdr; col["_pad"] = pad; col["_content_h"] = ch

def _place_col(d, col, x, top, content_h):
    y0 = top + (content_h - col["_h"]) / 2
    col["_box"] = (x, y0, x + col["_w"], y0 + col["_h"])
    cy = y0 + col["_hdr"] + col["_pad"]
    cxc = x + col["_pad"] + CELL_W / 2
    for n in col["nodes"]:
        h = _node_h(d, n)
        n["_x"] = cxc; n["_y"] = cy + ICON / 2
        cy += h + ROW_GAP


def straighten_columns(spec: dict) -> str:
    """Reorder columns so arrows run short and forward. Returns a one-line report.

    A reader rejected a figure for "crooked, ugly arrows". Cropping the render showed the
    cause was not the renderer: several edges joined nodes four or five columns apart and one
    ran BACKWARD, from a later column to an earlier one. The layout has nowhere to route
    those, so each is pushed into a lane BELOW every boundary box, travelling down, across
    the full page width and back up. Five of them stacked is a tangle, however crisp each
    individual line is. Orthogonal routing was already correct; the defect is edge LENGTH
    and DIRECTION, and no spline setting repairs that.

    Column ORDER is free and edge length is not, so this is applied automatically at render
    time rather than left to whoever writes the spec. Ranked by (backward edges, worst span,
    total span): a reverse edge is what creates the loop, so it outranks everything. Column 0
    stays pinned because it is the reading entry point, and a figure that reads outwards from
    the middle is worse than one long edge.

    Every permutation is evaluated when the column count allows, so the outcome is
    deterministic rather than dependent on a search order.
    """
    import itertools

    cols = spec.get("columns") or []
    edges = spec.get("edges") or []
    if not (3 <= len(cols) <= 8) or not edges:
        return ""
    # A wrap (a VNet or region box) names its columns by id and must stay CONTIGUOUS, so a
    # permutation is only legal when every wrap's columns still form one unbroken block.
    # Refusing to reorder whenever a wrap exists, which was the first attempt, disqualified
    # exactly the figures that needed it most: the reference architecture is nothing but a
    # VNet wrap.
    wrap_sets = []
    for wrap in (spec.get("wraps") or []):
        ids = set(wrap.get("cols") or [])
        idxs = {i for i, c in enumerate(cols) if c.get("id") in ids}
        if idxs:
            wrap_sets.append(idxs)

    def wraps_intact(order):
        for want in wrap_sets:
            at = sorted(pos for pos, orig in enumerate(order) if orig in want)
            if at and at[-1] - at[0] + 1 != len(at):
                return False
        return True

    where = {n["id"]: i for i, c in enumerate(cols) for n in c.get("nodes", [])}

    def rank(order):
        pos = {orig: new for new, orig in enumerate(order)}
        back = worst = total = 0
        for e in edges:
            a, b = where.get(e.get("from")), where.get(e.get("to"))
            if a is None or b is None:
                continue
            d = pos[b] - pos[a]
            if d < 0:
                back += 1
            total += abs(d)
            worst = max(worst, abs(d))
        return (back, worst, total)

    identity = list(range(len(cols)))
    legal = [o for o in ([0] + list(p) for p in itertools.permutations(identity[1:]))
             if wraps_intact(o)]
    if not legal:
        return "columns not reordered: no ordering keeps every wrap contiguous"
    best = min(legal, key=rank)
    before, after = rank(identity), rank(best)
    if best == identity or after >= before:
        return "columns already optimal: %d backward, worst span %d" % before[:2]
    spec["columns"] = [cols[i] for i in best]
    return ("columns reordered to straighten arrows: backward %d->%d, worst span %d->%d, "
            "total %d->%d" % (before[0], after[0], before[1], after[1], before[2], after[2]))


def render(spec: dict, out: Path):
    # Straighten the arrows before anything is measured: column order decides edge length,
    # and a long or backward edge is what gets pushed into a routing lane under the boxes.
    msg = straighten_columns(spec)
    if msg:
        print("  " + msg)
    _init_fonts()
    _lint_reset()
    d0 = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    cols = spec.get("columns", [])
    for c in cols:
        _measure_col(d0, c)
    content_h = max((c["_h"] for c in cols), default=0)
    wraps = spec.get("wraps", []) or []
    top = MARGIN + TITLE_H + (WRAP_HDR + WRAP_PAD if wraps else 0)

    x = MARGIN
    colmap = {}
    for c in cols:
        _place_col(d0, c, x, top, content_h)
        colmap[c.get("id")] = c
        x += c["_w"] + COL_GAP
    right = x - COL_GAP

    # wraps: bbox around member columns
    for w in wraps:
        members = [colmap[cid] for cid in w.get("cols", []) if cid in colmap]
        if not members:
            continue
        x0 = min(m["_box"][0] for m in members) - WRAP_PAD
        y0 = min(m["_box"][1] for m in members) - WRAP_HDR
        x1 = max(m["_box"][2] for m in members) + WRAP_PAD
        y1 = max(m["_box"][3] for m in members) + WRAP_PAD
        w["_box"] = (x0, y0, x1, y1)
        right = max(right, x1)

    # per-node column index + x-bounds — used to route tier-CROSSING edges AROUND
    # any intervening columns instead of straight through them.
    col_index = {}; col_bounds = {}
    for ci, c in enumerate(cols):
        col_bounds[ci] = (c["_box"][0], c["_box"][2])
        for n in c["nodes"]:
            col_index[n["id"]] = ci

    bottom = top + content_h
    if wraps:
        bottom = max(bottom, max(w["_box"][3] for w in wraps))

    # A SKIP edge spans >=2 columns (e.g. eks->msk over the data tier). Give each
    # its own clear horizontal "bus lane" below the column boxes (kept inside the
    # surrounding wrap) so it flies AROUND the columns it crosses rather than
    # grazing their icons. Diagrams with no skip edges are byte-for-byte unchanged.
    lane_y = {}; lane_ix = {}
    skips = []
    for e in spec.get("edges", []):
        ci = col_index.get(e.get("from")); cj = col_index.get(e.get("to"))
        if ci is not None and cj is not None and abs(ci - cj) >= 2:
            skips.append((e, ci, cj))
    if skips:
        base = bottom + WRAP_PAD * 0.45; step = 22 * S
        for k, (e, _ci, _cj) in enumerate(skips):
            lane_y[id(e)] = base + k * step; lane_ix[id(e)] = k
        grow_to = base + (len(skips) - 1) * step + WRAP_PAD * 0.55
        for w in wraps:
            mi = [i for i, c in enumerate(cols) if c.get("id") in w.get("cols", [])]
            if mi and any(min(ci, cj) >= min(mi) and max(ci, cj) <= max(mi) for _e, ci, cj in skips):
                x0, y0, x1, y1 = w["_box"]; w["_box"] = (x0, y0, x1, max(y1, grow_to))
        bottom = max(bottom, grow_to, max((w["_box"][3] for w in wraps), default=bottom))

    shared = spec.get("shared")
    band_h = 0
    if shared:
        band_h = COL_HDR + 2 * COL_PAD + ICON + LABEL_GAP + 2 * (FT["node"].size + 2)

    total_w = int(max(right, x - COL_GAP) + MARGIN)
    total_h = int(bottom + (BAND_GAP + band_h if shared else 0) + MARGIN)

    global _CANVAS_W
    _CANVAS_W = total_w
    img = Image.new("RGB", (total_w, total_h), "white"); d = ImageDraw.Draw(img)
    if spec.get("title"):
        _ctext(d, total_w / 2, MARGIN, spec["title"], FT["title"], TXT)

    # shared band
    if shared:
        by0 = bottom + BAND_GAP; bx0 = MARGIN; bx1 = total_w - MARGIN
        _boundary(d, bx0, by0, bx1, by0 + band_h, shared["label"], shared.get("fill", "#FAFAFA"), shared.get("stroke", "#B0BEC5"), img=img, icon=shared.get("icon"))
        spec["_sb"] = (bx0, by0, bx1, by0 + band_h)
        bn = shared["nodes"]; slot = (bx1 - bx0 - 2 * COL_PAD) / len(bn)
        for i, node in enumerate(bn):
            node["_x"] = bx0 + COL_PAD + slot * (i + 0.5); node["_y"] = by0 + COL_HDR + COL_PAD + ICON / 2

    # draw wraps (largest first), then column sub-boundaries
    for w in sorted(wraps, key=lambda w: -( (w["_box"][2]-w["_box"][0])*(w["_box"][3]-w["_box"][1]) )):
        x0, y0, x1, y1 = w["_box"]
        _boundary(d, x0, y0, x1, y1, w.get("label", ""), w.get("fill", "#EEF"), w.get("stroke", "#88A"), w.get("dashed", False), img=img, icon=w.get("icon"))
    for c in cols:
        if c.get("boundary"):
            x0, y0, x1, y1 = c["_box"]; b = c["boundary"]
            _boundary(d, x0, y0, x1, y1, b.get("label", ""), b.get("fill", "#FFF"), b.get("stroke", "#AAB"), b.get("dashed", False), img=img, icon=b.get("icon"))

    # index nodes
    idx = {}
    for c in cols:
        for n in c["nodes"]:
            idx[n["id"]] = n
    if shared:
        for n in shared["nodes"]:
            idx[n["id"]] = n

    _plan_edges(spec, idx, col_index)     # fan out shared node sides + stagger gutters (all edges)
    for n in idx.values():                # register node boxes so edge labels can dodge them
        _measure_node(d, n)
    for e in spec.get("edges", []):
        a = idx.get(e["from"]); b = idx.get(e["to"])
        if a and b:
            _edge(d, a, b, e, col_index, col_bounds, lane_y, lane_ix)
    _shared_anchor(d, spec, idx)          # ONE linkage line to the shared band (anti-orphan, not spider-web)
    for n in idx.values():
        _node(img, d, n)
    if spec.get("legend"):
        _legend(d, total_w - MARGIN - 96 * S, MARGIN + 2 * S)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, format="PNG", dpi=(300, 300))
    try:
        _emit_drawio(spec, cols, wraps, shared, idx, Path(out).with_suffix(".drawio"))
    except Exception as exc:  # noqa: BLE001 — .drawio is a bonus; never fail the PNG
        print(f"! .drawio emit skipped: {exc}", file=sys.stderr)
    # layout self-check: text must not overflow a box, labels must not overlap.
    # Write a sidecar ONLY when there are defects (diagram_check.py reads it);
    # remove any stale one so a fixed diagram clears its report.
    issues = _lint_layout()
    lint_path = Path(out).with_suffix(".lint.json")
    if issues:
        lint_path.write_text(json.dumps(issues, ensure_ascii=False), encoding="utf-8")
        for it in issues:
            print(f"! [lint] {it['code']}: {it['msg']}", file=sys.stderr)
    elif lint_path.exists():
        lint_path.unlink()
    print(f"Rendered {out}  ({total_w}x{total_h})  ->{6.5*total_h/total_w:.1f}in tall")
    return out


def _emit_drawio(spec, cols, wraps, shared, idx, out):
    """Emit a NATIVE, fully editable draw.io file (not an image capture): every
    boundary is a draggable rectangle, every node a draggable image cell (the real
    icon, base64-embedded), every edge an orthogonal connector — all individually
    editable in diagrams.net."""
    SD = 2.2  # px -> drawio units
    sc = lambda v: int(v / SD)
    global _DRAWIO_MEASURE
    _DRAWIO_MEASURE = ImageDraw.Draw(Image.new("RGB", (8, 8)))   # for wrapping labels only
    cells = []; cid = [2]

    def add(s):
        cells.append(s); cid[0] += 1

    fbadge = int(BADGE / SD)

    def rect(box, label, fill, stroke, dashed, icon=None):
        x0, y0, x1, y1 = box
        # transparent boundaries in the .drawio too (mirror the PNG); only tinted subnets keep a fill
        fc = "none" if (fill in (None, "none", "#FFFFFF", "#ffffff", "white")) else fill
        lpad = 8 + (fbadge + 6 if icon and resolve_icon(icon) else 0)
        style = (f"rounded=1;whiteSpace=wrap;html=1;fillColor={fc};strokeColor={stroke};"
                 f"verticalAlign=top;align=left;spacingLeft={lpad};spacingTop=4;fontSize=11;fontStyle=1;"
                 f"fontColor={stroke};arcSize=4;"
                 + ("dashed=1;" if dashed else ""))
        add(f'<mxCell id="{cid[0]}" value="{escape(label or "")}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{sc(x0)}" y="{sc(y0)}" width="{sc(x1 - x0)}" height="{sc(y1 - y0)}" as="geometry"/></mxCell>')
        ip = resolve_icon(icon) if icon else None
        if ip:
            b64 = base64.b64encode(Path(ip).read_bytes()).decode("ascii")
            bstyle = f"shape=image;html=1;imageAspect=1;aspect=fixed;image=data:image/png;base64,{b64};"
            add(f'<mxCell id="{cid[0]}" value="" style="{bstyle}" vertex="1" parent="1">'
                f'<mxGeometry x="{sc(x0) + 5}" y="{sc(y0) + 4}" width="{fbadge}" height="{fbadge}" as="geometry"/></mxCell>')

    for w in sorted(wraps, key=lambda w: -((w["_box"][2] - w["_box"][0]) * (w["_box"][3] - w["_box"][1]))):
        rect(w["_box"], w.get("label", ""), w.get("fill", "#EEF"), w.get("stroke", "#88A"), w.get("dashed", False), w.get("icon"))
    for c in cols:
        if c.get("boundary"):
            b = c["boundary"]; rect(c["_box"], b.get("label", ""), b.get("fill", "#FFF"), b.get("stroke", "#AAB"), b.get("dashed", False), b.get("icon"))
    if shared and spec.get("_sb"):
        rect(spec["_sb"], shared.get("label", ""), shared.get("fill", "#FAFAFA"), shared.get("stroke", "#B0BEC5"), False, shared.get("icon"))

    try:
        from drawio_export import SHAPE_STYLES
    except Exception:  # noqa: BLE001
        SHAPE_STYLES = {}
    ncell = {}
    for nid, n in idx.items():
        ref = n.get("icon", "")
        w = sc(ICON); x = sc(n["_x"]) - w // 2; y = sc(n["_y"]) - w // 2
        hint = STEM2SHAPE.get(ref)
        if hint and hint in SHAPE_STYLES:
            # NATIVE draw.io vendor stencil (real vector AWS/Azure/GCP/K8s shape)
            style = SHAPE_STYLES[hint]
        else:
            ip = resolve_icon(ref) if ref else None
            if ip:
                b64 = base64.b64encode(Path(ip).read_bytes()).decode("ascii")
                style = ("shape=image;html=1;verticalLabelPosition=bottom;verticalAlign=top;labelPosition=center;"
                         f"imageAspect=1;aspect=fixed;image=data:image/png;base64,{b64};")
            else:
                style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#ECEFF1;strokeColor=#90A4AE;"
        # Give the label the SAME wrapping the PNG applied. An image cell is only as wide as
        # its icon and carries no wrap, so a long label that the PNG breaks over three lines
        # was emitted as one long line and drew straight out of its subnet box: the picture
        # was right and the editable twin was not. Measured on a real run, 3 of 49 node
        # labels crossed their container this way.
        _lines, _ = _node_lines(_DRAWIO_MEASURE, n)
        value = "&#10;".join(escape(t) for t in _lines) or escape(n.get("label", nid))
        style += "" if "whiteSpace=wrap" in style else "whiteSpace=wrap;"
        style += f"labelWidth={sc(CELL_W)};labelPosition=center;align=center;"
        add(f'<mxCell id="{cid[0]}" value="{value}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{w}" as="geometry"/></mxCell>')
        ncell[nid] = cid[0] - 1

    for e in spec.get("edges", []):
        s = ncell.get(e["from"]); t = ncell.get(e["to"])
        if s is None or t is None:
            continue
        dashed = e.get("style") == "dashed"
        col = e.get("color") or ("#8E24AA" if dashed else "#37474F")
        style = f"edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor={col};endArrow=block;" + ("dashed=1;" if dashed else "")
        add(f'<mxCell id="{cid[0]}" value="{escape(e.get("label", ""))}" style="{style}" edge="1" parent="1" source="{s}" target="{t}">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>')

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<mxfile host="app.diagrams.net" version="24.0">\n'
           f'  <diagram name="{escape(spec.get("title", "Diagram"))}" id="d1">\n'
           '    <mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
           'arrows="1" fold="1" page="1" pageScale="1" pageWidth="1600" pageHeight="1100" math="0" shadow="0">\n'
           '      <root>\n        <mxCell id="0"/>\n        <mxCell id="1" parent="0"/>\n'
           + "\n".join("        " + c for c in cells) + "\n"
           '      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n')
    Path(out).write_text(xml, encoding="utf-8")

# ---- drawing -------------------------------------------------------------------
def _boundary(d, x0, y0, x1, y1, label, fill, stroke, dashed=False, img=None, icon=None):
    # fill None/"none"/white => transparent (only subnets are tinted in official diagrams)
    f = None if (fill in (None, "none", "#FFFFFF", "#ffffff", "white")) else fill
    if dashed:
        if f:
            d.rounded_rectangle((x0, y0, x1, y1), radius=BR, fill=f)
        _dash_rrect(d, (x0, y0, x1, y1), BR, stroke, 2 * S)
    else:
        d.rounded_rectangle((x0, y0, x1, y1), radius=BR, fill=f, outline=stroke, width=2 * S)
    # corner category-icon badge (top-left) — the signature of official cloud diagrams
    tx = x0 + 10 * S
    ip = resolve_icon(icon) if icon else None
    if ip and img is not None:
        try:
            bd = Image.open(ip).convert("RGBA"); bd.thumbnail((BADGE, BADGE), Image.LANCZOS)
            img.paste(bd, (int(x0 + 9 * S), int(y0 + 6 * S)), bd)
            tx = x0 + 9 * S + bd.width + 6 * S
        except Exception:
            ip = None
    if label:
        avail = (x1 - tx) - 12 * S
        lines = _wrap_multi(d, label, FT["hdr"], max(avail, 20 * S), 3)
        line_h = FT["hdr"].size + 6 * S
        block_h = len(lines) * line_h - 6 * S
        # vertically centre the header block against the badge when one is present
        ty0 = (y0 + 6 * S + (BADGE - block_h) / 2) if ip else (y0 + 6 * S)
        wmax = 0
        for i, ln in enumerate(lines):
            d.text((tx, ty0 + i * line_h), ln, font=FT["hdr"], fill=stroke)
            wmax = max(wmax, d.textlength(ln, font=FT["hdr"]))
            if d.textlength(ln, font=FT["hdr"]) > avail + 2 * S:  # a single word wider than the box
                _lint_issue("header_overflow", f"boundary header '{label}' overflows its box")
        _lint_box("header", (tx, ty0, tx + wmax, ty0 + block_h))

def _dash_rrect(d, box, r, color, width):
    x0, y0, x1, y1 = box
    for a, b in [((x0 + r, y0), (x1 - r, y0)), ((x1, y0 + r), (x1, y1 - r)), ((x1 - r, y1), (x0 + r, y1)), ((x0, y1 - r), (x0, y0 + r))]:
        _dash(d, a, b, color, width)

def _measure_node(d, n):
    """Register a node's icon and label boxes WITHOUT drawing them.

    Edges are drawn before nodes so that arrows tuck behind the boxes, which means that when
    an edge label is positioned nothing has registered a node box yet and it has nothing to
    avoid. Measuring first is what makes the avoidance possible; the order of drawing stays
    as it was.
    """
    cx, cy = n["_x"], n["_y"]
    _lint_box("icon", (cx - ICON / 2, cy - ICON / 2, cx + ICON / 2, cy + ICON / 2))
    lines, extra = _node_lines(d, n)
    ty = cy + ICON / 2 + LABEL_GAP
    lbl_top, lbl_w = ty, 0
    for ln in lines:
        lbl_w = max(lbl_w, d.textlength(ln, font=FT["node"])); ty += FT["node"].size + 2
    for _kind, t in extra:
        lbl_w = max(lbl_w, d.textlength(t, font=FT["tech"])); ty += FT["tech"].size + 3
    _lint_box("nodelabel", (cx - lbl_w / 2, lbl_top, cx + lbl_w / 2, ty))


def _node(img, d, n):
    cx, cy = n["_x"], n["_y"]
    ip = resolve_icon(n.get("icon", "")) if n.get("icon") else None
    if ip:
        try:
            ic = Image.open(ip).convert("RGBA"); ic.thumbnail((ICON, ICON), Image.LANCZOS)
            img.paste(ic, (int(cx - ic.width / 2), int(cy - ic.height / 2)), ic)
        except Exception:
            ip = None
    if not ip:
        d.rounded_rectangle((cx - ICON / 2, cy - ICON / 2, cx + ICON / 2, cy + ICON / 2), radius=9 * S, fill="#ECEFF1", outline="#90A4AE", width=2 * S)
    _lint_box("icon", (cx - ICON / 2, cy - ICON / 2, cx + ICON / 2, cy + ICON / 2))
    lines, extra = _node_lines(d, n); ty = cy + ICON / 2 + LABEL_GAP
    lbl_top = ty; lbl_w = 0
    for ln in lines:
        _ctext(d, cx, ty, ln, FT["node"], TXT); lbl_w = max(lbl_w, d.textlength(ln, font=FT["node"])); ty += FT["node"].size + 2
    for kind, t in extra:
        _ctext(d, cx, ty, t, FT["tech"], "#B71C1C" if kind == "tag" else "#8a95a3"); lbl_w = max(lbl_w, d.textlength(t, font=FT["tech"])); ty += FT["tech"].size + 3
    _lint_box("nodelabel", (cx - lbl_w / 2, lbl_top, cx + lbl_w / 2, ty))

def _anchor(n, side):
    cx, cy = n["_x"], n["_y"]; h = ICON / 2
    return {"r": (cx + h, cy), "l": (cx - h, cy), "t": (cx, cy - h), "b": (cx, cy + h)}[side]


def _anchor_fan(n, side, i, count):
    """Like _anchor, but when `count` edges share one side of a node, spread their
    attachment points along that side so the arrows fan out instead of piling onto a
    single point."""
    cx, cy = n["_x"], n["_y"]; h = ICON / 2
    span = ICON * 0.72
    off = 0.0 if count <= 1 else (i - (count - 1) / 2) * (span / (count - 1))
    off = max(-h * 0.9, min(h * 0.9, off))
    if side == "r":
        return (cx + h, cy + off)
    if side == "l":
        return (cx - h, cy + off)
    if side == "t":
        return (cx + off, cy - h)
    return (cx + off, cy + h)   # "b"


def _plan_edges(spec, idx, col_index):
    """Pre-route pass: for every edge decide which SIDE of each endpoint it uses, then
    (1) fan out edges that share a node side so they never pile onto one point, and
    (2) stagger the shared vertical channel so parallel runs in a gutter never overlap
    or sit too close. Results are stashed on each edge (`_sa/_sb/_kind/_a_pt/_b_pt/
    _chan_dx`). Runs for every diagram, so it applies to ALL edges, not just skips."""
    from collections import defaultdict
    edges = [e for e in spec.get("edges", []) if e.get("from") in idx and e.get("to") in idx]
    for e in edges:
        a, b = idx[e["from"]], idx[e["to"]]
        ci, cj = col_index.get(a["id"]), col_index.get(b["id"])
        if ci is not None and cj is not None and abs(ci - cj) >= 2:
            e["_sa"], e["_sb"], e["_kind"] = (("r", "l", "skip") if cj > ci else ("l", "r", "skip"))
        elif abs(b["_x"] - a["_x"]) >= abs(b["_y"] - a["_y"]):
            r = b["_x"] >= a["_x"]
            e["_sa"], e["_sb"], e["_kind"] = ("r" if r else "l", "l" if r else "r", "h")
        else:
            dn = b["_y"] >= a["_y"]
            e["_sa"], e["_sb"], e["_kind"] = ("b" if dn else "t", "t" if dn else "b", "v")

    # (1) fan out per (node, side), ordered by the partner coordinate to avoid crossings
    grp = defaultdict(list)
    for e in edges:
        grp[(e["from"], e["_sa"])].append(("a", e))
        grp[(e["to"], e["_sb"])].append(("b", e))
    for (nid, side), lst in grp.items():
        n = idx[nid]
        horiz_side = side in ("r", "l")
        lst.sort(key=lambda it: (idx[it[1]["to"]] if it[0] == "a" else idx[it[1]["from"]])
                 ["_y" if horiz_side else "_x"])
        for i, (end, e) in enumerate(lst):
            e["_a_pt" if end == "a" else "_b_pt"] = _anchor_fan(n, side, i, len(lst))

    # (2) stagger the vertical channel of horizontal-route edges sharing a gutter
    chan = defaultdict(list)
    for e in edges:
        if e["_kind"] == "h":
            chan[(col_index.get(e["from"]), col_index.get(e["to"]))].append(e)
    for key, lst in chan.items():
        if len(lst) < 2:
            continue
        lst.sort(key=lambda e: idx[e["to"]]["_y"])
        for i, e in enumerate(lst):
            e["_chan_dx"] = (i - (len(lst) - 1) / 2) * 18 * S
    return edges

def _route_skip(sp, ep, ci, cj, col_bounds, lane, k=0):
    """Route a tier-crossing edge AROUND the columns it spans: out through the
    source-side gutter, along a clear bus lane below the boxes, up through the
    target-side gutter — never straight across the intervening column icons.
    `k` staggers the gutter channels so stacked skip edges don't overlap. sp/ep are
    the (already fanned) source/target anchor points."""
    off = min(k * 16 * S, COL_GAP * 0.35)   # keep the channel inside its gutter
    if cj > ci:
        xs = col_bounds[ci][1] + COL_GAP * 0.5 - off; xt = col_bounds[cj][0] - COL_GAP * 0.5 + off
    else:
        xs = col_bounds[ci][0] - COL_GAP * 0.5 + off; xt = col_bounds[cj][1] + COL_GAP * 0.5 - off
    if lane is None:
        lane = max(sp[1], ep[1]) + ROW_GAP
    return [sp, (xs, sp[1]), (xs, lane), (xt, lane), (xt, ep[1]), ep]

def _edge(d, a, b, e, col_index=None, col_bounds=None, lane_y=None, lane_ix=None):
    color = e.get("color") or (PUR if e.get("style") == "dashed" else INK)
    dashed = e.get("style") == "dashed"
    ax, ay, bx, by = a["_x"], a["_y"], b["_x"], b["_y"]
    ci = (col_index or {}).get(a["id"]); cj = (col_index or {}).get(b["id"])
    sa = e.get("_sa")
    # use the fanned anchor points from _plan_edges; fall back to a plain anchor
    sp = e.get("_a_pt") or _anchor(a, sa or ("r" if bx >= ax else "l"))
    ep = e.get("_b_pt") or _anchor(b, e.get("_sb") or ("l" if bx >= ax else "r"))
    if e.get("_kind") == "skip" and col_bounds:
        pts = _route_skip(sp, ep, ci, cj, col_bounds, (lane_y or {}).get(id(e)), (lane_ix or {}).get(id(e), 0))
    elif (sa or ("r" if abs(bx - ax) >= abs(by - ay) else "t")) in ("r", "l"):
        mx = (sp[0] + ep[0]) / 2 + e.get("_chan_dx", 0); pts = [sp, (mx, sp[1]), (mx, ep[1]), ep]
    else:
        my = (sp[1] + ep[1]) / 2; pts = [sp, (sp[0], my), (ep[0], my), ep]
    for i in range(len(pts) - 1):
        (_dash if dashed else _line)(d, pts[i], pts[i + 1], color, 2 * S)
    _arrow(d, pts[-2], pts[-1], color)
    if e.get("label"):
        (mx, my), vert = _longest_mid(pts)   # midpoint of the longest run = always in a clear gutter
        w = d.textlength(e["label"], font=FT["edge"]); hh = FT["edge"].size
        same_col = (ci is not None and ci == cj)
        if vert:
            # A same-column (stacked) edge runs at the node centre, so its label must
            # clear the whole cell AND the box padding — otherwise it lands on the
            # centred node label or straddles the boundary. It then sits in the clear
            # right-hand gutter. A gutter vertical (adjacent/skip) only needs a nudge.
            off = CELL_W / 2 + COL_PAD + 10 * S if same_col else 6 * S
            tx = mx + off
            # The right gutter does not exist for the last column, so put the label in the
            # left one instead of letting the canvas edge cut it in half.
            if _CANVAS_W and tx + w + 3 > _CANVAS_W - MARGIN / 2:
                tx = mx - off - w
        else:     # centre on a horizontal run (sits in the gutter between tiers)
            tx = mx - w / 2
        tx, my = _clear_label_pos(tx, my, w, hh, vert)
        d.rectangle((tx - 3, my - hh / 2 - 2, tx + w + 3, my + hh / 2 + 2), fill="white")
        d.text((tx, my - hh / 2), e["label"], font=FT["edge"], fill=color)
        _lint_box("edgelabel", (tx - 3, my - hh / 2 - 2, tx + w + 3, my + hh / 2 + 2))

def _longest_mid(pts):
    best = pts[len(pts) // 2]; bl = -1; vert = False
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L > bl:
            bl = L; best = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2); vert = abs(b[1] - a[1]) > abs(b[0] - a[0])
    return best, vert

def _point_at(pts, frac):
    segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs) or 1
    target = total * frac; run = 0
    for a, b in segs:
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if run + L >= target:
            t = (target - run) / (L or 1)
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        run += L
    return pts[-1]

def _line(d, a, b, color, w):
    d.line([a, b], fill=color, width=w)

def _dash(d, a, b, color, w):
    ax, ay = a; bx, by = b; L = math.hypot(bx - ax, by - ay)
    if L < 1:
        return
    ux, uy = (bx - ax) / L, (by - ay) / L; dash = 9 * S / 2; gap = 6 * S / 2; p = 0
    while p < L:
        ee = min(p + dash, L); d.line([(ax + ux * p, ay + uy * p), (ax + ux * ee, ay + uy * ee)], fill=color, width=w); p = ee + gap

def _arrow(d, frm, to, color):
    ax, ay = frm; bx, by = to; ang = math.atan2(by - ay, bx - ax); s = 8 * S
    d.polygon([to, (bx - s * math.cos(ang - 0.4), by - s * math.sin(ang - 0.4)), (bx - s * math.cos(ang + 0.4), by - s * math.sin(ang + 0.4))], fill=color)

def _shared_anchor(d, spec, idx):
    """Draw ONE dashed connector from a compute tier down to the shared band, so the band
    reads as intentionally-scoped-to-all rather than orphaned. This is the sanctioned
    '0-1 edges' linkage — NEVER one edge per band icon (that is the spider-web we avoid).
    Spec: shared["anchor"] = {"from": <node id>, "label": "IAM / KMS / ... (all tiers)"}."""
    sh = spec.get("shared"); box = spec.get("_sb")
    if not (sh and box and sh.get("anchor")):
        return
    a = sh["anchor"]; src = idx.get(a.get("from"))
    if not src:
        return
    bx0, by0, bx1, _ = box
    x = min(max(src["_x"], bx0 + 40 * S), bx1 - 40 * S)
    sy = src["_y"] + ICON / 2
    midy = (sy + by0) / 2
    pts = [(src["_x"], sy), (src["_x"], midy), (x, midy), (x, by0)]
    for i in range(len(pts) - 1):
        _dash(d, pts[i], pts[i + 1], "#90A4AE", 2 * S)
    _arrow(d, pts[-2], pts[-1], "#90A4AE")
    lbl = a.get("label")
    if lbl:
        w = d.textlength(lbl, font=FT["edge"]); hh = FT["edge"].size
        lx = min(max(x, bx0 + w / 2 + 6), bx1 - w / 2 - 6)
        d.rectangle((lx - w / 2 - 3, by0 - hh - 8, lx + w / 2 + 3, by0 - 3), fill="white")
        d.text((lx - w / 2, by0 - hh - 6), lbl, font=FT["edge"], fill="#607D8B")

def _legend(d, x, y):
    w = 96 * S; h = 48 * S
    d.rounded_rectangle((x, y, x + w, y + h), radius=6 * S, fill="#FFFFFF", outline="#CBD5E0", width=2 * S)
    d.text((x + 9 * S, y + 6 * S), "Legend", font=FT["hdr"], fill=INK)
    ln = x + 10 * S; le = x + 30 * S; lx = x + 36 * S
    yr1 = y + 24 * S; yr2 = y + 37 * S
    d.line([(ln, yr1), (le, yr1)], fill=INK, width=2 * S)
    d.text((lx, yr1 - FT["edge"].size / 2), "sync", font=FT["edge"], fill=INK)
    _dash(d, (ln, yr2), (le, yr2), PUR, 2 * S)
    d.text((lx, yr2 - FT["edge"].size / 2), "async", font=FT["edge"], fill=PUR)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--spec", type=Path, required=True); ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    render(json.loads(a.spec.read_text(encoding="utf-8")), a.out)

if __name__ == "__main__":
    main()
