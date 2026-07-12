#!/usr/bin/env python3
"""Render a general-purpose diagram from a JSON spec via Graphviz at >= 300 DPI.

This is the renderer for every diagram that is NOT a cloud/infra architecture
(those use the mingrammer `diagrams` package with vendor icons — see
`03_generate.md`). It covers the broad "structural / process / hierarchy /
relationship" families with Graphviz as the layout engine:

  flowchart, decision tree, BPMN-lite, swimlane, state machine, user journey,
  C4 (context/container/component), microservices, class diagram, ER diagram,
  data-flow diagram, data pipeline, org chart, mind map, network topology,
  dependency graph, knowledge graph.

Why Graphviz (not a browser/mermaid): it is already bootstrapped for the cloud
path, needs no browser, renders crisp PNGs, and the SAME graph feeds
`drawio_export.export_drawio()` so the editable `.drawio` MATCHES the PNG.

Spec schema (JSON) — only `nodes` is strictly required:
{
  "slug": "order_flow",
  "title": "Order Processing Flow",
  "category": "process",          // informational; picks sensible defaults
  "diagram_type": "flowchart",    // flowchart|state|erd|class|orgchart|mindmap|
                                  // network|dependency|dfd|c4|microservices|generic
  "engine": "dot",                // dot|neato|fdp|sfdp|twopi|circo (auto by type)
  "direction": "TB",              // TB|LR|BT|RL (dot only)
  "nodes": [
    {"id": "start", "label": "Start",        "role": "start"},
    {"id": "recv",  "label": "Receive order","role": "process"},
    {"id": "pay",   "label": "Payment OK?",  "role": "decision"},
    {"id": "db",    "label": "Orders",        "role": "datastore"},
    // ER entity:  {"id":"u","type":"entity","label":"User","attributes":["id PK","email"]}
    // UML class:  {"id":"c","type":"class","label":"Order","fields":["+id"],"methods":["+total()"]}
  ],
  "edges": [
    {"from": "start", "to": "recv"},
    {"from": "pay",   "to": "ship", "label": "yes"},
    {"from": "pay",   "to": "cancel","label": "no"},
    {"from": "svc",   "to": "bus",  "kind": "async"},        // dashed event edge
    {"from": "child", "to": "base", "kind": "inheritance"}   // UML hollow triangle
  ],
  "clusters": [
    {"id": "swim1", "label": "Customer", "members": ["start","recv"]},
    {"id": "priv",  "label": "Backend",  "members": ["pay"], "parent": "swim1"}
  ]
}

Usage:
    python scripts/build_graph.py --spec spec.json --out out/foo.png
    python scripts/build_graph.py --spec spec.json --out out/foo.png --no-drawio
"""
from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
from pathlib import Path

# Reuse the canonical label wrapper + Graphviz locator from the shared engine.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from diagrams_runtime import wrap_label, _find_dot, _install_graphviz_windows  # noqa: E402
from drawio_export import export_drawio  # noqa: E402


# ---------------------------------------------------------------------------
# Role -> Graphviz shape/style. This is the standard flowchart/UML shape set
# (ISO 5807 flowchart, UML state/class, ERD) so a "decision" is a diamond, a
# "datastore" a cylinder, a "start/end" a stadium, etc.
# ---------------------------------------------------------------------------

# (shape, extra style attrs, fill, stroke)
ROLE_STYLES: dict[str, tuple[str, str, str, str]] = {
    # flowchart / BPMN-lite
    "start":       ("ellipse",     "style=filled",             "#E8F5E9", "#43A047"),
    "end":         ("ellipse",     "style=filled",             "#FDECEA", "#E53935"),
    "terminator":  ("ellipse",     "style=filled",             "#E8F5E9", "#43A047"),
    "process":     ("box",         "style=\"rounded,filled\"", "#E8F1FB", "#1E88E5"),
    "task":        ("box",         "style=\"rounded,filled\"", "#E8F1FB", "#1E88E5"),
    "action":      ("box",         "style=\"rounded,filled\"", "#E8F1FB", "#1E88E5"),
    "decision":    ("diamond",     "style=filled",             "#FFF3E0", "#FB8C00"),
    "gateway":     ("diamond",     "style=filled",             "#FFF3E0", "#FB8C00"),
    "io":          ("parallelogram","style=filled",            "#F3E5F5", "#8E24AA"),
    "input":       ("parallelogram","style=filled",            "#F3E5F5", "#8E24AA"),
    "output":      ("parallelogram","style=filled",            "#F3E5F5", "#8E24AA"),
    "data":        ("parallelogram","style=filled",            "#F3E5F5", "#8E24AA"),
    "subprocess":  ("box",         "style=\"rounded,filled\" peripheries=2", "#EDE7F6", "#5E35B1"),
    "predefined":  ("box",         "style=\"rounded,filled\" peripheries=2", "#EDE7F6", "#5E35B1"),
    "document":    ("note",        "style=filled",             "#FFFDE7", "#FBC02D"),
    "manual":      ("trapezium",   "style=filled",             "#FCE4EC", "#D81B60"),
    "prepare":     ("hexagon",     "style=filled",             "#E0F7FA", "#00ACC1"),
    "connector":   ("circle",      "style=filled fixedsize=true width=0.4", "#ECEFF1", "#607D8B"),
    "datastore":   ("cylinder",    "style=filled",             "#E0F2F1", "#00897B"),
    "database":    ("cylinder",    "style=filled",             "#E0F2F1", "#00897B"),
    "queue":       ("box",         "style=\"filled\"",         "#F3E5F5", "#8E24AA"),
    # state machine
    "state":       ("box",         "style=\"rounded,filled\"", "#E8F1FB", "#1E88E5"),
    "initial":     ("circle",      "style=filled fixedsize=true width=0.28 label=\"\"", "#333333", "#333333"),
    "final":       ("doublecircle","style=filled fixedsize=true width=0.3 label=\"\"", "#333333", "#333333"),
    # actors / people / systems
    "actor":       ("box",         "style=\"rounded,filled\"", "#FFF8E1", "#F9A825"),
    "person":      ("box",         "style=\"rounded,filled\"", "#FFF8E1", "#F9A825"),
    "system":      ("box",         "style=\"rounded,filled\"", "#E3F2FD", "#1565C0"),
    "external":    ("box",         "style=\"rounded,filled,dashed\"", "#ECEFF1", "#607D8B"),
    "service":     ("box",         "style=\"rounded,filled\"", "#E8F1FB", "#1E88E5"),
    "component":   ("component",   "style=filled",             "#E8EAF6", "#3949AB"),
    "node":        ("box3d",       "style=filled",             "#ECEFF1", "#546E7A"),
    "folder":      ("folder",      "style=filled",             "#FFF8E1", "#F9A825"),
    # generic default
    "default":     ("box",         "style=\"rounded,filled\"", "#F5F5F5", "#666666"),
}

# Pale cluster fills / borders, cycled in declaration order (SA-grade tier colour).
CLUSTER_FILLS = [
    ("#E8F1FB", "#1E88E5"), ("#FBF3E0", "#FB8C00"), ("#FBE9E7", "#D84315"),
    ("#E8F5E9", "#43A047"), ("#F3E5F5", "#8E24AA"), ("#E0F2F1", "#00897B"),
    ("#EDE7F6", "#5E35B1"), ("#FFFDE7", "#F9A825"),
]

# Edge "kind" -> Graphviz arrow/line style. Covers flow + UML relationships.
EDGE_KINDS: dict[str, str] = {
    "default":     "",
    "sync":        "",
    "async":       'style=dashed arrowhead=vee color="#8E24AA" fontcolor="#8E24AA"',
    "event":       'style=dashed arrowhead=vee color="#8E24AA" fontcolor="#8E24AA"',
    "message":     'style=dashed arrowhead=vee color="#8E24AA" fontcolor="#8E24AA"',
    "dashed":      "style=dashed",
    "dependency":  'style=dashed arrowhead=vee',
    "inheritance": "arrowhead=empty",       # UML generalization (hollow triangle)
    "generalization": "arrowhead=empty",
    "realization": "style=dashed arrowhead=empty",
    "composition": "arrowhead=diamond",     # filled diamond at the whole
    "aggregation": "arrowhead=odiamond",    # open diamond
    "association": "arrowhead=vee",
    "bidirectional": "dir=both",
}

# Engine defaults by diagram_type.
ENGINE_BY_TYPE: dict[str, str] = {
    "mindmap": "twopi", "knowledge": "neato", "network": "neato",
    "dependency": "dot", "orgchart": "dot",
}


def _q(s: str) -> str:
    """Quote a string for a Graphviz DOT attribute, escaping backslashes/quotes."""
    return '"' + (s or "").replace("\\", "\\\\").replace('"', '\\"') + '"'


def _gv_label(text: str) -> str:
    """DOT label: escape quotes and turn real newlines (from wrap_label) into
    Graphviz \\n line breaks. Must NOT double-escape backslashes — doing that
    rendered the line break as a literal '\\n' in the label."""
    s = (text or "").replace('"', '\\"').replace("\n", "\\n")
    return '"' + s + '"'


def _entity_html_label(node: dict) -> str:
    """HTML-table label for an ER entity: title row + one row per attribute."""
    name = html.escape(node.get("label", node.get("id", "")))
    attrs = node.get("attributes", []) or []
    rows = [f'<TR><TD BGCOLOR="#1565C0"><FONT COLOR="white"><B>{name}</B></FONT></TD></TR>']
    for a in attrs:
        rows.append(f'<TR><TD ALIGN="LEFT">{html.escape(str(a))}</TD></TR>')
    table = ('<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
             + "".join(rows) + "</TABLE>>")
    return table


def _class_record_label(node: dict) -> str:
    """UML class record label: {Name | fields \\l | methods \\l}."""
    name = node.get("label", node.get("id", ""))
    fields = node.get("fields", []) or []
    methods = node.get("methods", []) or []
    def esc(s: str) -> str:
        return s.replace("{", "\\{").replace("}", "\\}").replace("|", "\\|").replace("<", "\\<").replace(">", "\\>")
    parts = [esc(name)]
    parts.append("\\l".join(esc(str(f)) for f in fields) + ("\\l" if fields else ""))
    parts.append("\\l".join(esc(str(m)) for m in methods) + ("\\l" if methods else ""))
    # Record labels carry structural { } | and Graphviz \l left-justify breaks —
    # escape ONLY the quotes; never the backslashes (they are control sequences).
    body = "{" + "|".join(parts) + "}"
    return '"' + body.replace('"', '\\"') + '"'


# Roles rendered as a professional "card" (coloured header band + white body with
# optional subtitle / [tech] / [tags]) instead of a flat box — the senior-SA look.
# Flowchart/geometry roles (decision, start, end, io, datastore, state, ...) keep
# their standard ISO/UML shapes so meaning stays in the geometry.
CARD_ROLES = {"service", "system", "component", "actor", "person", "external"}


def _card_html_label(node: dict, accent: str) -> str:
    raw = wrap_label(node.get("label", node.get("id", "")), limit=22)
    name = html.escape(raw).replace("\n", "<BR/>")
    rows = [f'<TR><TD BGCOLOR="{accent}"><FONT COLOR="#FFFFFF" POINT-SIZE="13"><B>{name}</B></FONT></TD></TR>']
    if node.get("subtitle"):
        rows.append(f'<TR><TD BGCOLOR="#FFFFFF"><FONT COLOR="#5a6b7b" POINT-SIZE="10">'
                    f'{html.escape(str(node["subtitle"]))}</FONT></TD></TR>')
    if node.get("tech"):
        rows.append(f'<TR><TD BGCOLOR="#FFFFFF"><FONT COLOR="#8a95a3" POINT-SIZE="9">'
                    f'[{html.escape(str(node["tech"]))}]</FONT></TD></TR>')
    if node.get("tags"):
        tg = "  ".join(f"[{html.escape(str(t))}]" for t in node["tags"])
        rows.append(f'<TR><TD BGCOLOR="#FFFFFF"><FONT COLOR="#B71C1C" POINT-SIZE="9">{tg}</FONT></TD></TR>')
    return ('<<TABLE BORDER="1" COLOR="' + accent + '" CELLBORDER="0" CELLSPACING="0" '
            'CELLPADDING="7">' + "".join(rows) + "</TABLE>>")


def _emit_node(node: dict, indent: str) -> str:
    nid = _q(node["id"])
    ntype = node.get("type")
    if ntype == "entity":
        return f"{indent}{nid} [shape=plaintext label={_entity_html_label(node)}];"
    if ntype == "class":
        return f"{indent}{nid} [shape=record style=filled fillcolor=\"#E8EAF6\" color=\"#3949AB\" label={_class_record_label(node)}];"
    role = (node.get("role") or node.get("shape") or "default").lower()
    shape, extra, fill, stroke = ROLE_STYLES.get(role, ROLE_STYLES["default"])
    # Architecture roles render as cards. Geometric roles (decision/datastore/
    # state/...) keep their ISO/UML shape — fold any tech/tags into the text label
    # so a cylinder stays a cylinder but still shows its [PII]/[tech] annotation.
    if role in CARD_ROLES:
        return f"{indent}{nid} [shape=plaintext label={_card_html_label(node, stroke)}];"
    if 'label=""' in extra:  # initial/final states carry their own label=""
        label_attr = ""
    else:
        base = wrap_label(node.get("label", node["id"]), limit=20)
        extra_lines = []
        if node.get("tech"):
            extra_lines.append(f'[{node["tech"]}]')
        if node.get("tags"):
            extra_lines.append("  ".join(f'[{t}]' for t in node["tags"]))
        full = base + (("\n" + "\n".join(extra_lines)) if extra_lines else "")
        label_attr = f" label={_gv_label(full)}"
    fill_attr = f' fillcolor="{fill}" color="{stroke}" fontcolor="#1a1a1a"'
    return f"{indent}{nid} [shape={shape} {extra}{fill_attr}{label_attr}];"


def build_dot(spec: dict) -> str:
    dtype = (spec.get("diagram_type") or "generic").lower()
    engine = (spec.get("engine") or ENGINE_BY_TYPE.get(dtype) or "dot").lower()
    direction = spec.get("direction", "TB")
    if direction not in ("TB", "LR", "BT", "RL"):
        direction = "TB"

    nodes = spec.get("nodes", [])
    edges = spec.get("edges", [])
    clusters = spec.get("clusters", []) or []
    node_ids = {n["id"] for n in nodes}
    node_by_id = {n["id"]: n for n in nodes}

    # Edge labels and splines=ortho don't mix — Graphviz can drop a label or drop
    # it ON a node/edge. When any edge carries a label, use spline routing, which
    # reserves space for each label so text never lands on a node or another arrow.
    has_labeled_edges = any(e.get("label") for e in edges)
    lines = ["digraph G {"]
    if engine == "dot":
        lines.append(f"  rankdir={direction};")
        lines.append('  splines=%s;' % ("spline" if has_labeled_edges else "ortho"))
    else:
        lines.append('  splines=true; overlap=false;')
    lines += [
        '  bgcolor="white";',
        # generous spacing so labels/arrows never crowd or cross a node
        '  pad="0.5"; nodesep="0.7"; ranksep="1.0";',
        '  graph [dpi=300, fontname="Segoe UI", fontsize=15];',
        '  node  [fontname="Segoe UI", fontsize=13, margin="0.28,0.18", penwidth=1.6];',
        '  edge  [fontname="Segoe UI", fontsize=11, color="#37474F", penwidth=1.8, arrowsize=0.9];',
    ]
    if spec.get("title"):
        lines.append('  label=%s; labelloc="t"; labeljust="c"; fontsize=20; '
                     'fontcolor="#12212e"; fontname="Segoe UI";' % _gv_label(spec["title"]))

    # --- clusters (support one level of nesting via "parent") ---
    cluster_by_id = {c["id"]: c for c in clusters}
    children: dict[str, list[str]] = {c["id"]: [] for c in clusters}
    roots: list[str] = []
    for c in clusters:
        p = c.get("parent")
        (children[p].append(c["id"]) if p and p in cluster_by_id else roots.append(c["id"]))
    member_of = {m: c["id"] for c in clusters for m in c.get("members", [])}
    fill_cycle = iter(CLUSTER_FILLS * 4)

    def emit_cluster(cid: str, indent: str) -> None:
        c = cluster_by_id[cid]
        fill, pen = next(fill_cycle)
        lines.append(f"{indent}subgraph cluster_{cid} {{")
        lines.append(f'{indent}  label={_gv_label(wrap_label(c.get("label", cid), limit=26))};')
        lines.append(f'{indent}  style="rounded,filled"; fillcolor="{fill}"; color="{pen}"; '
                     f'penwidth=1.5; fontsize=14; fontname="Segoe UI"; labelloc=t; margin=16;')
        for m in c.get("members", []):
            if m in node_by_id:
                lines.append(_emit_node(node_by_id[m], indent + "  "))
        for ch in children.get(cid, []):
            emit_cluster(ch, indent + "  ")
        lines.append(f"{indent}}}")

    for cid in roots:
        emit_cluster(cid, "  ")

    # --- free nodes (not in any cluster) ---
    for n in nodes:
        if n["id"] not in member_of:
            lines.append(_emit_node(n, "  "))

    # --- edges ---
    for e in edges:
        if e["from"] not in node_ids or e["to"] not in node_ids:
            continue
        kind = (e.get("kind") or ("dashed" if e.get("dashed") else "default")).lower()
        style = EDGE_KINDS.get(kind, "")
        attrs = [style] if style else []
        if e.get("label"):
            attrs.append(f'label={_gv_label(e["label"])}')
        if e.get("color"):
            attrs.append(f'color="{e["color"]}"')
        astr = (" [" + " ".join(a for a in attrs if a) + "]") if attrs else ""
        lines.append(f'  {_q(e["from"])} -> {_q(e["to"])}{astr};')

    # Auto-legend: when the diagram distinguishes sync vs async edges, add a small
    # legend so the reader never guesses what solid vs dashed means (SA convention).
    _async = {"async", "event", "message", "dashed", "dependency", "realization"}
    has_async = any((e.get("kind") or ("dashed" if e.get("dashed") else "")).lower() in _async
                    for e in edges)
    if has_async and engine == "dot":
        lines.append('  subgraph cluster_legend {')
        lines.append('    style="rounded,filled"; fillcolor="#FAFAFA"; color="#CBD5E0"; margin=6; label="";')
        lines.append('    _legend [shape=plaintext label=<'
                     '<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="3" CELLPADDING="2">'
                     '<TR><TD COLSPAN="2" ALIGN="LEFT"><FONT POINT-SIZE="11" COLOR="#37474F"><B>Legend</B></FONT></TD></TR>'
                     '<TR><TD><TABLE BORDER="0" CELLSPACING="0"><TR><TD BGCOLOR="#37474F" HEIGHT="3" WIDTH="36"></TD></TR></TABLE></TD>'
                     '<TD ALIGN="LEFT"><FONT POINT-SIZE="10" COLOR="#37474F"> synchronous (request / response)</FONT></TD></TR>'
                     '<TR><TD><TABLE BORDER="0" CELLSPACING="0"><TR><TD BGCOLOR="#8E24AA" HEIGHT="3" WIDTH="36"></TD></TR></TABLE></TD>'
                     '<TD ALIGN="LEFT"><FONT POINT-SIZE="10" COLOR="#8E24AA"> asynchronous (event, dashed)</FONT></TD></TR>'
                     '</TABLE>>];')
        lines.append('  }')

    lines.append("}")
    return "\n".join(lines)


def ensure_dot() -> str:
    dot = _find_dot()
    if dot is None:
        import platform
        if platform.system() == "Windows":
            dot = _install_graphviz_windows()
        if dot is None:
            raise RuntimeError(
                "Graphviz `dot` not found. Install it (brew/apt install graphviz) "
                "or let the Windows portable auto-installer run.")
    return str(dot)


def render(spec: dict, out: Path, emit_drawio: bool = True) -> Path:
    dot_bin = ensure_dot()
    src = build_dot(spec)
    out.parent.mkdir(parents=True, exist_ok=True)
    engine = (spec.get("engine") or ENGINE_BY_TYPE.get((spec.get("diagram_type") or "").lower()) or "dot").lower()
    # dot_bin points at `dot`; other engines live beside it in the same bin/.
    engine_bin = str(Path(dot_bin).with_name(("dot" if engine == "dot" else engine) +
                                             (".exe" if dot_bin.endswith(".exe") else "")))
    proc = subprocess.run([engine_bin, "-Tpng", "-o", str(out)],
                          input=src, capture_output=True, text=True, encoding="utf-8",
                          creationflags=(subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0))
    if proc.returncode != 0:
        raise RuntimeError(f"Graphviz render failed ({engine}):\n{proc.stderr}\n--- DOT ---\n{src}")
    print(f"Rendered {out}")

    # Also emit an SVG twin: rendered by the SAME engine so it is pixel-faithful
    # to the PNG, but vector (infinitely sharp, zoomable) AND openable/editable in
    # draw.io. This is the high-fidelity editable format — see 03_generate.md.
    try:
        svg_out = out.with_suffix(".svg")
        svg_proc = subprocess.run([engine_bin, "-Tsvg", "-o", str(svg_out)],
                                  input=src, capture_output=True, text=True, encoding="utf-8",
                                  creationflags=(subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0))
        if svg_proc.returncode == 0:
            print(f"Rendered {svg_out}")
    except Exception as exc:  # noqa: BLE001 — SVG is a bonus; never fail the PNG
        print(f"! SVG export skipped: {exc}", file=sys.stderr)

    if emit_drawio:
        # Emit an editable .drawio from the SAME graph (Graphviz-laid to match).
        nodes = [{"id": n["id"],
                  "label": wrap_label(n.get("label", n["id"]), limit=20),
                  "shape": _drawio_shape(n)} for n in spec.get("nodes", [])]
        edges = [{"from": e["from"], "to": e["to"], "label": e.get("label", ""),
                  "dashed": (e.get("kind") in ("async", "event", "message", "dashed", "dependency", "realization"))
                            or bool(e.get("dashed"))}
                 for e in spec.get("edges", []) if e.get("from") and e.get("to")]
        clusters = [{"id": c["id"], "label": c.get("label", c["id"]),
                     "members": c.get("members", []), "parent": c.get("parent")}
                    for c in (spec.get("clusters") or [])]
        try:
            export_drawio(nodes, edges, clusters,
                          out_path=out.with_suffix(".drawio"),
                          title=spec.get("title", "Diagram"),
                          direction=spec.get("direction", "TB"))
            print(f"Rendered {out.with_suffix('.drawio')}")
        except Exception as exc:  # noqa: BLE001 — .drawio is a bonus; never fail the PNG
            print(f"! .drawio export skipped: {exc}", file=sys.stderr)
    return out


def _drawio_shape(node: dict) -> str | None:
    """Map a generic node role to a draw.io generic stencil hint where one fits."""
    role = (node.get("role") or node.get("shape") or "").lower()
    return {"datastore": "database", "database": "database",
            "actor": "user", "person": "user", "external": "cloud"}.get(role)


def main() -> int:
    ap = argparse.ArgumentParser(description="Render a general diagram from a JSON spec via Graphviz.")
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--no-drawio", action="store_true", help="Skip the editable .drawio export.")
    ap.add_argument("--print-dot", action="store_true", help="Print the generated DOT and exit.")
    args = ap.parse_args()
    if not args.spec.exists():
        print(f"! spec not found: {args.spec}", file=sys.stderr)
        return 1
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    if args.print_dot:
        print(build_dot(spec))
        return 0
    render(spec, args.out, emit_drawio=not args.no_drawio)
    return 0


if __name__ == "__main__":
    sys.exit(main())
