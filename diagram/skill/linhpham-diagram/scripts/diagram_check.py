#!/usr/bin/env python3
"""Per-diagram self-check — run AFTER Agent A renders the diagrams.

Verifies EACH diagram is correct and presentation-grade, covering the defects
the user has flagged with zero tolerance:

  PNG  (the figure embedded in the Word doc)
    * file exists and is a valid, non-empty image
    * long side >= 1500 px               (sharp at the 6.5" Word embed)
    * rendered height <= 9.0 in          (fits one Word page at 6.5" wide)

  .drawio  (the editable source the client opens in diagrams.net)
    * file exists and is well-formed XML with a non-empty graph
    * has at least one node (and, for architecture diagrams, edges)
    * every label is clean: NO line ending on a dangling "(" — the
      "Amazon MSK (" / "Kafka)" defect — and no over-long single-line label
    * multi-line labels are encoded with &#10; (so draw.io keeps the wrap
      instead of collapsing it to one line)
    * nodes are not blank: each carries a stencil (shape=/image=) or is an
      intentional generic rounded box

Usage:
    python scripts/diagram_check.py --dir project_dir/output/diagrams
    python scripts/diagram_check.py --dir <dir> --json report.json

Exit code 0 = all diagrams pass; 1 = at least one blocker.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

MIN_LONG_SIDE_PX = 1500
MAX_RENDER_H_IN = 9.0        # hard cap: taller than this spills off a Word page
WORD_TARGET_H_IN = 8.5       # ideal: fit one page AND leave room for the caption
EMBED_WIDTH_IN = 6.5
EMBED_DPI_MIN = 220          # below this at the 6.5in Word embed = visibly blurry (blocker)
EMBED_DPI_TARGET = 300       # crisp target; between MIN and this = warn to re-render wider
MAX_LABEL_LINE = 24          # chars; a single line longer than this is cramped
MIN_PNG_BYTES = 3000
MAX_ELEMENTS = 34            # per figure; past this a reader stops parsing and starts scanning


class Report:
    def __init__(self) -> None:
        self.diagrams: list[dict] = []

    def add(self, slug: str, issues: list[dict]) -> None:
        self.diagrams.append({
            "slug": slug,
            "blockers": [i for i in issues if i["severity"] == "blocker"],
            "warnings": [i for i in issues if i["severity"] == "warning"],
            "issues": issues,
        })

    @property
    def blockers(self) -> int:
        return sum(len(d["blockers"]) for d in self.diagrams)

    @property
    def warnings(self) -> int:
        return sum(len(d["warnings"]) for d in self.diagrams)


def _issue(sev: str, code: str, msg: str) -> dict:
    return {"severity": sev, "code": code, "msg": msg}


def check_png(png: Path) -> list[dict]:
    issues: list[dict] = []
    if not png.exists():
        return [_issue("blocker", "png_missing", f"PNG not found: {png.name}")]
    if png.stat().st_size < MIN_PNG_BYTES:
        issues.append(_issue("blocker", "png_empty",
                             f"PNG suspiciously small ({png.stat().st_size} bytes) — render likely failed"))
    try:
        from PIL import Image
    except ImportError:
        issues.append(_issue("warning", "pil_missing", "Pillow not installed — skipped pixel checks"))
        return issues
    try:
        with Image.open(png) as im:
            w, h = im.size
            dpi = im.info.get("dpi", (0, 0))
    except Exception as e:  # noqa: BLE001
        return issues + [_issue("blocker", "png_unreadable", f"cannot open PNG: {e}")]
    long_side = max(w, h)
    if long_side < MIN_LONG_SIDE_PX:
        issues.append(_issue("blocker", "png_low_res",
                             f"long side {long_side}px < {MIN_LONG_SIDE_PX}px — blurry in Word; raise graph_attr dpi"))
    render_h_in = EMBED_WIDTH_IN * h / w if w else 99
    if render_h_in > MAX_RENDER_H_IN:
        issues.append(_issue("blocker", "png_too_tall",
                             f"renders {render_h_in:.1f}in tall at {EMBED_WIDTH_IN}in wide (> {MAX_RENDER_H_IN}in) — "
                             f"switch direction TB<->LR or split the diagram"))
    elif render_h_in > WORD_TARGET_H_IN:
        issues.append(_issue("warning", "png_tight_for_word",
                             f"renders {render_h_in:.1f}in tall at {EMBED_WIDTH_IN}in wide (> {WORD_TARGET_H_IN}in) — "
                             f"fits a Word page but leaves little room for the caption; consider LR or trimming a node"))
    # Sharpness at the ACTUAL Word embed: build_docx.py inserts figures at width = 6.5in,
    # so effective DPI = width_px / 6.5in. Only meaningful for a diagram that FITS at 6.5in
    # wide (a too-tall one is handled above; its width changes on the LR re-render, so
    # skip it here to avoid a confusing double-blocker).
    if render_h_in <= MAX_RENDER_H_IN and w:
        embed_dpi = w / EMBED_WIDTH_IN
        target_px = int(EMBED_WIDTH_IN * EMBED_DPI_TARGET)
        if embed_dpi < EMBED_DPI_MIN:
            issues.append(_issue("blocker", "png_soft_for_embed",
                                 f"only {embed_dpi:.0f} DPI at the {EMBED_WIDTH_IN}in Word embed ({w}px wide) — "
                                 f"blurry; re-render >= {target_px}px wide (raise dpi / bump the render scale)"))
        elif embed_dpi < EMBED_DPI_TARGET:
            issues.append(_issue("warning", "png_below_crisp",
                                 f"{embed_dpi:.0f} DPI at the {EMBED_WIDTH_IN}in embed ({w}px wide) — below the "
                                 f"{EMBED_DPI_TARGET} DPI crisp target; consider a wider render (>= {target_px}px)"))
    if dpi and dpi[0] and dpi[0] < 200:
        issues.append(_issue("warning", "png_dpi_meta", f"PNG dpi metadata {dpi[0]} < 200"))
    # SHARP and LEGIBLE are different properties and the checks above only measure the first.
    # An aspect-ratio rule was tried here as a proxy and removed: measured across the sample
    # set it fired on seven wide figures while missing the smallest text in the set, because
    # what decides the size a label lands at is the source font against the image WIDTH, not
    # the ratio. A 1.2:1 figure came out at 5.5pt and a 1.5:1 one at 3.4pt. Any real check
    # needs the source font size, which a PNG does not carry; raising it is a renderer change,
    # not a threshold.
    return issues


def _labels_from_drawio(root: ET.Element) -> list[tuple[str, str]]:
    """Return (cell_id, raw_value_with_newlines) for every cell that has a value.
    ElementTree converts &#10; back to '\\n', so we read the raw file separately
    for the dangling-'(' check; here we use the parsed value for structure."""
    out = []
    for cell in root.iter("mxCell"):
        val = cell.get("value")
        if val:
            out.append((cell.get("id", "?"), val, cell.get("edge") == "1"))
    return out


def check_drawio(drawio: Path) -> list[dict]:
    issues: list[dict] = []
    if not drawio.exists():
        # Not a blocker: sequence (PIL) and custom-icon diagrams are intentionally
        # PNG-only. A missing .drawio for a Graphviz/cloud diagram is worth noticing,
        # so surface it as a warning rather than failing the whole diagram.
        return [_issue("warning", "drawio_missing",
                       f".drawio not found: {drawio.name} (expected absent for sequence / "
                       f"custom-icon diagrams; for Graphviz/cloud diagrams re-emit it)")]
    raw = drawio.read_text(encoding="utf-8", errors="replace")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        return [_issue("blocker", "drawio_malformed", f"XML parse error: {e}")]

    cells = list(root.iter("mxCell"))
    verts = [c for c in cells if c.get("vertex") == "1"]
    edges = [c for c in cells if c.get("edge") == "1"]
    if not verts:
        issues.append(_issue("blocker", "drawio_empty", "no vertices in graph"))
    if verts and not edges:
        issues.append(_issue("warning", "drawio_no_edges",
                             "no edges — fine for a context/inventory diagram, odd for an architecture"))

    # Blank-box check: a vertex with neither a stencil nor a container style.
    for c in verts:
        style = c.get("style", "") or ""
        has_glyph = ("shape=" in style) or ("image=" in style)
        is_box = ("rounded=1" in style) or ("whiteSpace=wrap" in style) or style == ""
        if not has_glyph and not is_box:
            issues.append(_issue("warning", "drawio_blank_box",
                                 f"cell {c.get('id')} has no stencil and no box style — may render blank"))

    # Label hygiene — uses the parsed values (newlines restored from &#10;).
    multiline_seen = False
    for cid, val, is_edge in _labels_from_drawio(root):
        lines = val.split("\n")
        if len(lines) > 1:
            multiline_seen = True
        for ln in lines:
            if ln.rstrip().endswith("("):
                issues.append(_issue("blocker", "label_dangling_paren",
                                     f"label {cid!r} has a line ending on '(' — '{val[:40]}' "
                                     f"(wrap with wrap_label, which breaks BEFORE '(')"))
                break
        # Long-line warning applies to NODE/CLUSTER labels only — they sit in a
        # sized box and overflow it. Edge (flow-step) labels float on the line and
        # don't overflow anything, so a long one is not a defect.
        if is_edge:
            continue
        for ln in lines:
            if len(ln) > MAX_LABEL_LINE:
                issues.append(_issue("warning", "label_line_long",
                                     f"label {cid!r} line {len(ln)} chars (> {MAX_LABEL_LINE}): '{ln[:40]}'"))
                break

    # Multi-line labels MUST be stored as &#10; in the raw file, else draw.io
    # collapses them to a single line on open.
    if multiline_seen and "&#10;" not in raw and "<br" not in raw:
        issues.append(_issue("blocker", "drawio_newline_lost",
                             "multi-line labels found but no &#10;/<br> in file — wraps will collapse in draw.io"))

    # SA-grade structure enforcement — NARROW so it doesn't false-positive on a
    # legitimately-flat diagram (e.g. DDD bounded-context tiers are peers, not
    # nested). Only a NETWORK/DEPLOYMENT diagram (one with a VPC or subnet
    # boundary) must NEST those boundaries — flat sibling subnets is the
    # tool-generated look the SA charter rejects.
    cluster_cells = [c for c in verts if "fillColor=none" in (c.get("style", "") or "")]
    rects, clabels = [], []
    for c in cluster_cells:
        g = c.find("mxGeometry")
        if g is None:
            continue
        try:
            rects.append((float(g.get("x")), float(g.get("y")),
                          float(g.get("width")), float(g.get("height"))))
        except (TypeError, ValueError):
            continue
        clabels.append((c.get("value", "") or "").lower())
    if any("vpc" in l or "subnet" in l for l in clabels):
        nested = False
        for i, (x, y, w, h) in enumerate(rects):
            for j, (X, Y, W, H) in enumerate(rects):
                if i != j and X <= x and Y <= y and X + W >= x + w and Y + H >= y + h and W * H > w * h:
                    nested = True
                    break
            if nested:
                break
        if not nested:
            issues.append(_issue("warning", "flat_boundaries",
                                 "VPC/subnet boundaries are flat siblings — nest the subnets INSIDE "
                                 "the VPC (SA-grade trust-boundary nesting)"))
    return issues


def check_explanation_consistency(drawio_path: Path, entry: dict | None) -> list[dict]:
    """Warn when a diagram's explanation bullets (from diagrams.json) reference a
    component that is NOT in the diagram — a caption gone stale after the diagram
    was redrawn. Fuzzy word match, so emitted as warnings, not blockers."""
    if not entry or not drawio_path.exists():
        return []
    bullets = entry.get("explanation_bullets") or []
    if not bullets:
        return []
    try:
        root = ET.parse(drawio_path).getroot()
    except ET.ParseError:
        return []
    labels = []
    for c in root.iter("mxCell"):
        # Include CLUSTER labels too — a bullet may describe a grouping/boundary
        # (e.g. "Shared identity / audit / ops"), not just a leaf node.
        if c.get("vertex") == "1" or c.get("edge") == "1":
            v = (c.get("value", "") or "").replace("&#10;", " ").replace("\n", " ")
            if v.strip():
                labels.append(v)
    njoin = re.sub(r"[^a-z0-9]", "", " ".join(labels).lower())
    SKIP = ("step", "legend", "trust boundary", "vpc boundary", "datastore", "boundary",
            "sensitive", "audit edge", "ledger classification", "single trigger", "semantics")
    issues = []
    for b in bullets:
        m = re.match(r"\*\*(.+?)\*\*", b)
        if not m:
            continue
        term = m.group(1)
        if any(s in term.lower() for s in SKIP):
            continue
        words = [w for w in re.findall(r"[a-z0-9]+", term.lower()) if len(w) > 2]
        if words and not any(re.sub(r"[^a-z0-9]", "", w) in njoin for w in words):
            issues.append(_issue("warning", "explanation_orphan",
                                 f"bullet '{term[:32]}' has no matching node/edge — caption may be stale"))
    return issues


def check_diagram_block(slug: str, entry: dict | None) -> list[dict]:
    """Warn when the diagrams.json 'block' for a diagram is missing or thin — the
    caption + intro_paragraph + explanation_bullets that accompany the figure in the
    deliverable (mirrors the technical-proposal content contract). Warnings only: a quick
    ad-hoc diagram may legitimately ship without a full block."""
    issues: list[dict] = []
    if entry is None:
        return [_issue("warning", "block_missing",
                       f"no diagrams.json entry for '{slug}' — no caption / intro / explanation bullets")]
    caption = (entry.get("caption") or "").strip()
    if not caption:
        issues.append(_issue("warning", "caption_missing", f"'{slug}' has no caption"))
    elif "—" in caption:
        # Em-dashes are banned in delivered content (they read as machine-written);
        # the caption convention is "<Type>: <Scope>". BLOCKER, to match the technical
        # proposal reviewer, which blocks the same character in the same deliverable. It
        # was a warning here, so eight of eight captions in one run carried an em-dash and
        # nothing objected; a rule with two severities is a rule that gets ignored on the
        # softer side.
        issues.append(_issue("blocker", "caption_em_dash",
                             f"caption uses an em-dash; write '<Type>: <Scope>': {caption[:60]!r}"))
    elif ":" not in caption and " - " not in caption:
        issues.append(_issue("warning", "caption_format",
                             f"caption should read '<Type>: <Scope>': {caption[:60]!r}"))
    if not (entry.get("intro_paragraph") or "").strip():
        issues.append(_issue("warning", "intro_missing", f"'{slug}' has no intro_paragraph"))
    bullets = entry.get("explanation_bullets") or []
    if len(bullets) < 3:
        issues.append(_issue("warning", "bullets_sparse",
                             f"'{slug}' has {len(bullets)} explanation bullet(s) (< 3) — thin for a professional block"))
    return issues


def check_layout_lint(lint_path: Path) -> list[dict]:
    """Surface the manual-grid renderer's own layout self-check. build_cloud.render()
    writes <slug>.lint.json ONLY when it detects a text-overflow or label-overlap
    defect (measured with the real fonts + coordinates it drew with — far more
    reliable than inspecting pixels here). Its presence therefore means a real,
    zero-tolerance layout defect: header text crossing a boundary, or an edge label
    landing on a node/header label. Promote each to a BLOCKER."""
    if not lint_path.exists():
        return []
    try:
        items = json.loads(lint_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [_issue("warning", "lint_unreadable", f"could not read {lint_path.name}")]
    out: list[dict] = []
    for it in items or []:
        out.append(_issue("blocker", it.get("code", "layout_defect"),
                          it.get("msg", "layout defect reported by build_cloud lint")))
    return out


def check_spec_density(spec_path: Path) -> list[dict]:
    """Warn when a figure carries more elements than a reader will parse.

    Past roughly three dozen boxes a reader stops reading the diagram and starts scanning it,
    and the figure has to do the explaining that the bullets underneath should be doing. It is
    a warning rather than a blocker because a deliberately dense reference architecture is a
    legitimate choice; it just has to be a choice.

    Counted from the spec rather than the image because a spec says what the elements ARE,
    whatever shape the renderer gives them.
    """
    if not spec_path.exists():
        return []
    try:
        blob = spec_path.read_text(encoding="utf-8")
    except OSError:
        return []
    n = len(re.findall(r'"(?:id|node|name)"\s*:', blob))
    if n > MAX_ELEMENTS:
        return [_issue("warning", "figure_crowded",
                       f"about {n} elements (> {MAX_ELEMENTS}) — a reader scans rather than reads at "
                       f"this density; split the figure or move detail into the explanation bullets")]
    return []


def run(dir_path: Path) -> Report:
    rep = Report()
    inv = {}
    inv_path = dir_path / "diagrams.json"
    if inv_path.exists():
        try:
            inv = {d.get("slug"): d for d in json.loads(inv_path.read_text(encoding="utf-8"))}
        except (json.JSONDecodeError, AttributeError, TypeError):
            inv = {}
    pngs = sorted(dir_path.glob("*.png"))
    if not pngs:
        print(f"! no PNG diagrams found in {dir_path}", file=sys.stderr)
    for png in pngs:
        slug = png.stem
        issues = check_png(png)
        issues += check_drawio(png.with_suffix(".drawio"))
        issues += check_explanation_consistency(png.with_suffix(".drawio"), inv.get(slug))
        issues += check_diagram_block(slug, inv.get(slug))
        issues += check_layout_lint(png.with_suffix(".lint.json"))
        issues += check_spec_density(dir_path / f"{slug}.spec.json")
        rep.add(slug, issues)
    return rep


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True, help="diagrams output folder")
    ap.add_argument("--json", type=Path, help="write machine-readable report here")
    args = ap.parse_args()
    if not args.dir.exists():
        print(f"! folder not found: {args.dir}", file=sys.stderr)
        return 2

    rep = run(args.dir)
    print("=" * 64)
    print(f"DIAGRAM SELF-CHECK — {len(rep.diagrams)} diagram(s) in {args.dir}")
    print("=" * 64)
    for d in rep.diagrams:
        status = "FAIL" if d["blockers"] else ("WARN" if d["warnings"] else "PASS")
        print(f"  [{status}] {d['slug']}")
        for i in d["blockers"]:
            print(f"      BLOCKER {i['code']}: {i['msg']}")
        for i in d["warnings"]:
            print(f"      warn    {i['code']}: {i['msg']}")
    print("-" * 64)
    print(f"RESULT: {rep.blockers} blocker(s), {rep.warnings} warning(s) "
          f"across {len(rep.diagrams)} diagram(s)")

    if args.json:
        args.json.write_text(json.dumps(
            {"blockers": rep.blockers, "warnings": rep.warnings, "diagrams": rep.diagrams},
            indent=2), encoding="utf-8")
        print(f"report -> {args.json}")
    return 1 if rep.blockers else 0


if __name__ == "__main__":
    sys.exit(main())
