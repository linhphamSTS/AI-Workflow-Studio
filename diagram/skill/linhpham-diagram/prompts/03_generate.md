# Phase 3 — Generate

Render the confirmed spec with the right engine. Output goes to `output/diagrams/`. Every diagram
produces a **PNG (>= 300 DPI)** for documents, a **vector `.svg`** (same render engine → pixel-faithful
to the PNG, infinitely sharp, and openable/editable in draw.io), and — where supported — a native
**`.drawio`**, plus a `diagrams.json` entry (caption + intro_paragraph + explanation_bullets).

**Three formats, three needs (tell the user):**
- **PNG** — drop into Word / slides.
- **SVG** — the high-fidelity editable/zoomable twin; looks EXACTLY like the PNG (do NOT expect a
  native `.drawio` to match the PNG pixel-for-pixel — Graphviz and mxGraph are different engines).
- **`.drawio`** — native draw.io shapes for heavy re-layout (a structural twin, not a pixel twin).

## Route by renderer (decided in Phase 1)

### A. graphviz  (structural / process / hierarchy / data / DevOps — most diagrams)
The spec is already at `output/diagrams/<slug>.spec.json`. Render:
```bash
python scripts/build_graph.py --spec output/diagrams/<slug>.spec.json --out output/diagrams/<slug>.png
```
This emits `<slug>.png` + `<slug>.drawio` (Graphviz-laid, matches the PNG). Node `role`/`type` and
edge `kind` were set per the type's KB. Pick the engine in the spec: `dot` (default / hierarchy /
flow), `twopi` (mind map / radial), `neato` (relationship map), `circo` (ring). Set `direction` LR
for pipelines/flows, TB for hierarchies/layered.

**A cluster label sits in the arrows' ENTRY CORRIDOR — keep it SHORT (≤ ~28 chars, one line).** A
Graphviz cluster header is centred across the TOP of the box (`labelloc=t`), which is exactly where
every inbound edge crosses on its way to the cluster's first node, so a two- or three-line header
gets SLICED by those arrowheads (observed: two inbound edges cut through
"Perimeter and identity (SEC-01, SEC-04, SEC-05)", and a third cut the last line of
"Data plane — UAE region only, residency enforced by policy-as-code (SEC-03)"). Name the zone and
nothing else — requirement IDs, CIDRs and rationale belong in the explanation bullet. Nothing catches
this automatically: the render-time layout lint exists for `build_cloud` only, so crop each cluster
header and `Read` it (Phase 4 §2).

### B. sequence  (time-ordered interactions)
```bash
python scripts/build_sequence.py --spec output/diagrams/<slug>.spec.json --out output/diagrams/<slug>.png
```
(No `.drawio` for sequences — the PNG is the deliverable; edit the spec to change it.)

### C. Cloud / infra / tech diagrams — use the SKILL's builders, DON'T freehand

**C1. Cloud/infra reference architectures (AWS, Azure, GCP, on-prem/hybrid, Kubernetes, Docker) →
the pixel-perfect MANUAL-GRID renderer.** These are defined as tiered specs in
`scripts/cloud_specs.py` and rendered by `scripts/build_cloud.py` (`build_cloud.render(spec, out)`).
Copy the closest spec (e.g. `cloud_specs.AWS`), adapt node labels / counts / tech / CIDRs / regions /
icons (`provider/stem`, e.g. `aws/route-53`, `gcp/run`, `k8s/ing`), and render. The renderer bakes
in the brochure-grade layout: tier-COLUMNS left→right, a VPC/VNet WRAP spanning the tiers, a bottom
SHARED band (no edges — position implies scope), orthogonal connectors, real icons. This beats
Graphviz auto-layout (which produced the curvy-spaghetti the user rejected). `render()` AUTO-EMITS a
NATIVE, per-component-editable `.drawio` next to the PNG (real vendor stencils + individually
draggable cells) — do NOT run `png_to_drawio` on a cloud diagram (that bakes a single flat image the
user rejected).

**Boundary style contract (this is what makes it look like an OFFICIAL AWS/Azure/GCP diagram — match
the real architecture-center house style, not a hand-drawn box):**
- **Outer network boundary** (VPC / VNet / global VPC) = **transparent** (`"fill": "#FFFFFF"`) +
  `"dashed": true` + a **corner category badge** `"icon"` (`aws/vpc`, `azure/virtual-networks`,
  `gcp/virtual-private-cloud`). The badge in the boundary's top-left corner is the single biggest
  "official diagram" tell — a boundary WITHOUT one reads as amateur.
- **Subnets / zones** (the tier COLUMNS inside the VPC) = a **pale tint** fill + solid stroke + their
  own badge (`aws/public-subnet`, `aws/private-subnet`, `azure/subnets`). Only subnets are tinted.
- **Cluster** boundary = badge `k8s/ns` (a namespace) or `k8s/k8s` (a whole cluster).
- **Logical tier boxes** that are NOT a real network container (Edge/Global, Messaging, a DDD bounded
  context) = keep a light tint, NO badge (official diagrams badge containers, not arbitrary groupings).
- **Shared band** = pale tint, no badge (it is a logical rail). Icons are `provider/stem`; verify each
  resolves (see kb Appendix A) — a missing icon falls back to a grey box and looks unfinished.
  - **Populate it from THIS PROJECT's real cross-cutting services** — never leave the canonical
    IAM/KMS/Secrets/CloudWatch/S3 list verbatim. Different projects have different rails (add WAF logs,
    Cost, Backup, tracing, a secrets store the project actually uses; drop what it doesn't).
  - **Give it exactly ONE `anchor`** `{"from": "<compute node id>", "label": "<svc / svc / … (all tiers)>"}`
    so the band is visibly LINKED, not orphaned. The engine draws a single dashed connector from that
    compute node down to the band. NEVER add one edge per band icon — that fan-out is the spider-web.
    "Connects to everything ⇒ one representative line + position implies scope."

**Edge-label placement is a SPEC decision, not just a renderer job** (the renderer offsets a label into
the nearest clear gutter — you have to give it a gutter to use):
- **Never label a same-column (stacked) edge in the FIRST or LAST column.** Its label is pushed into the
  side gutter, and outside the outermost column there is no gutter — the text renders past the canvas
  edge and is CLIPPED off the image (observed: `curated knowledge → pgvector` "chunk + embed" in a
  last-column Grounding-stores tier came out as "chunk + embec"). Either put the two nodes in **adjacent
  columns**, or leave that edge **unlabelled** (a stacked pair inside one tier already reads as
  "feeds"), or move the tier inward. The layout lint does NOT catch this — it only tests label↔label
  overlap, not canvas bounds — so it will ship silently.
- **Keep a CROSS-ROW edge label short (≤ ~14 chars) or align the endpoints on the same row.** An edge
  between adjacent columns whose endpoints are in *different rows* runs its vertical leg past the other
  rows of the target column, and a long label there lands on an intervening node's label (observed:
  `orchestration → second provider` "failover / portability" printed over "Document Intelligence" =
  a `label_overlap` BLOCKER). Put the detail in the explanation bullet, not on the arrow.

**A node `label` is the component NAME only — every qualifier goes in `tech` / `tags` / `subtitle`.**
Keep it to ~24 chars (one line at `CELL_W`) and never write `Name — qualifier`:
- the PNG wraps a node label to at most **3 lines and silently DROPS the rest** (`_wrap` returns
  `lines[:3]`, no ellipsis) — a 56-char label already fills all three, so one more word disappears
  with nothing reported;
- the **`.drawio` does not wrap a node label at all** — it sits on a `shape=image` cell with no
  `whiteSpace=wrap`, so it renders as ONE long line and CROSSES its subnet/tier box even though the
  PNG of the same spec looks fine (observed: "Guardrails: moderation, injection defence, PII
  redaction" ran 23 units past its box). `diagram_check` flags this as `label_line_long`: on a NODE
  label that warning is REAL, on a boundary / wrap / shared-band label it is benign (those cells DO
  wrap inside their box in draw.io). Don't dismiss the whole code because most of it is the benign kind.

**ADAPT the scaffold to the PROMPT — never emit a canonical spec verbatim.** The `cloud_specs.py`
entries exist to hand you the proven LAYOUT (columns, wrap, badges, band, ortho connectors) — the
CONTENT is yours to derive from the confirmed requirements: the actual tiers, service names, engine
choices, counts/CIDRs/regions, which subnets exist, the real shared-services rail, and every edge
label. If two runs for two different projects produce identical diagrams, you copied instead of
designing. The samples look identical ONLY because a sample renders the unmodified canonical spec to
demonstrate the house style; a real run must reflect the user's system.

**C2. Other tech diagrams (CI/CD, GitOps, data pipeline, microservices, C4 container, deployment,
AI-RAG) → the mingrammer builders in `scripts/diagram_templates.py`.**
**DO NOT freehand a mingrammer script — that reproduces the curvy-spaghetti / spider-web look.**
`scripts/diagram_templates.py` has proven CLEAN-LAYOUT builders (the same code the samples use):
`aws_ref, azure_ref, gcp_ref, k8s_topology, docker_compose, onprem_hybrid, cicd, gitops,
data_pipeline, microservices, c4_container, uml_deployment, ai_rag`. Each already encodes the layout
discipline (ortho edges, ONE spine, shared-services as an edgeless band anchored by ONE grouped edge,
nested shrink-wrapped boundaries, multi-AZ data + replication, real icons).

**Adapt the closest template to the project:** copy its function body into your run script and edit the
node labels / counts / tech / CIDRs / regions to match this project — but KEEP the structure (the
clusters, the ortho `graph_attr G`, the invisible-chain band + single anchor edge, the spine). Then
call `svg_util.inline_images` + `png_to_drawio` (the template's `_finish()` already does this). Only
freehand when NO template fits, and then obey the SA-GRADE rules below to the letter.

If you do freehand, start every script with:
```python
from scripts.diagrams_runtime import bootstrap, wrap_label
bootstrap()                      # installs `diagrams` + icons + Graphviz portable if missing
from diagrams import Diagram, Cluster, Edge
# import the icons for the CHOSEN cloud (see kb_cloud_refarch Appendix A for verified paths)
```
Use `Diagram(name, filename="output/diagrams/<slug>", outformat=["png","svg"], show=False, direction=..., graph_attr=COMMON_GRAPH_ATTR)` — request BOTH png and svg.
Then make the SVG self-contained (mingrammer SVG references icon files by path) so it stays faithful
and portable:
```python
from scripts.svg_util import inline_images
inline_images("output/diagrams/<slug>.svg")   # base64-inlines the vendor icons
```
After rendering, emit the matching `.drawio` with `scripts/drawio_export.export_drawio(nodes, edges, clusters, out_path=..., title=..., direction=...)` using the SAME wrapped labels and the `shape` hints from that module's `SHAPE_STYLES` (draw.io renders those vendor stencils natively, so the `.drawio` looks good IN draw.io even though it will not pixel-match the PNG).

## SA-GRADE rules (mingrammer + apply the spirit everywhere)
Read `reference/kb_diagram_layout.md` (clean-layout rulebook) + the chosen `reference/kb_*.md`. The
messy-diagram root cause is **too many edges** + **loose boxes**, NOT routing. Non-negotiables:
- **ORTHOGONAL edges** (`splines="ortho"`), never curved. One dominant flow axis (LR request/pipeline, TB hierarchy); cap **1–2 flows** = a single clean spine (`users → edge → LB → compute → data`). No backtracking, single-ended arrows.
- **Shared/cross-cutting services (IAM/KMS/Secrets/monitoring) = a compact BAND with 0–1 edges — NEVER a dashed edge from compute to each.** That fan-out IS the spider web. Draw them as a labelled panel whose position implies scope; line the icons up with an invisible chain (`a >> Edge(style="invis") >> b >> …`). "Connects to everything ⇒ connect to nothing."
- **Fleets/replicas** = one representative + `×N` (or a small stack), connect the GROUP box, not each pod. Attached resources (ConfigMap/Secret/HPA/PVC) side-attach with SHORT dashed connectors.
Then the structural non-negotiables:
- **NEST trust boundaries** — network boundary (AWS VPC / Azure VNet / GCP global VPC) is an OUTER
  cluster containing subnets containing nodes. Never flat sibling subnets. CIDR on the boundary box.
- **LEGEND mandatory** on every architecture/context diagram: a small `Cluster("Legend")` with a
  solid (sync) + dashed (async) sample edge; add "orange edge = PII" if you use one.
- **COLOUR hierarchy** — pale per-tier `bgcolor`; AWS uses category colours (compute orange, storage
  green, net/analytics purple, DB magenta, security red); Azure/GCP icons are multicolored — do NOT
  recolor them, tint only the boundary boxes. Every cluster connects to the flow or is a labelled
  cross-cutting sidebar; no floating unconnected clusters.
- **FLOW discipline** — Western reading order (clients top/left → edge → app → data bottom/right);
  `splines="ortho"`; single-ended arrows labelled with the mechanism (HTTPS/gRPC/event name).
- **Edge/CDN/WAF OUTSIDE the network boundary; identity/secrets/observability = side rail outside.**
  Azure exception: App Gateway+WAF & Firewall INSIDE the VNet; PaaS data OUTSIDE via private endpoint.
- **Labels:** wrap EVERY node AND cluster label with `wrap_label()` — never hand-insert `\n`, never
  end a line on `(` (it breaks BEFORE `(`). Keep `node_attr["margin"] >= "0.4,0.3"` so text never
  touches the icon.
- **Fit one Word/page column:** after render, if `rendered_h_in = 6.5 * h/w > 9.0` → flip direction
  (TB↔LR) or split into two figures; never shrink to fit. Render at `dpi="300"`.

Recommended `graph_attr` for a 6.5" embed: `{"fontsize":"18","bgcolor":"white","pad":"0.8","nodesep":"1.0","ranksep":"1.2","splines":"ortho","dpi":"300","compound":"true","labelloc":"t","labeljust":"l"}` and `node_attr={"fontsize":"14","margin":"0.5,0.4","shape":"box","style":"rounded,filled","fillcolor":"white"}`.

## Write the `diagrams.json` sidecar
Create/append `output/diagrams/diagrams.json` (a JSON array) with one entry:
`{slug, subheading, target_heading, png, caption:"<Type>: <Scope>", intro_paragraph (2–4 sentences),
explanation_bullets:["**Component**: description", ...] }`. One bullet per visible element; a
sequence uses `**Step <n>, <label>**: description`. No leading numbers/`●` in bullets.
**Use a COLON, never an em-dash**, in the caption and in every bullet — `diagram_check` makes an
em-dash caption a **BLOCKER** (`caption_em_dash`), and it fires on EVERY diagram of a run if you
template it in.

**The same ban covers every string DRAWN INTO the picture** — the diagram `title`, node / boundary /
wrap / cluster `label`s, `subtitle`, `tech` and edge labels. Nothing scrubs those: the caption gate
only reads the descriptor, so an em-dash in a spec label ships inside the image and the figure then
contradicts its own caption (observed: 31 em-dashes drawn across one 8-diagram run whose captions all
read with a colon — "AEGI Digital Platform — Azure UAE North Reference Architecture" sitting above
"Cloud Reference Architecture: the shared platform on Azure UAE North"). Write
`AKS: namespace per bounded context`, use a comma, or move the qualifier into `tech`.

**Write the `intro_paragraph` and bullets like a Solution Architect with 20 years' experience — they
must genuinely EXPLAIN THE DESIGN, not fill a template.** The reader should finish the paragraph
understanding *why the system is built this way*, grounded in THIS project's requirements (never reuse
another project's wording — every project differs). Explain the design decisions and their rationale:
why these components, why this boundary/trust split, why sync here and async there, how the design meets
the concrete requirement (scale, availability, latency, isolation, compliance, cost). If you ingested
project docs (Phase 1), tie the explanation to what they actually asked for.
- FORBIDDEN because they narrate the DRAWING, not the design (read as machine-generated / amateur / a
  filled template): "reads left-to-right across N tiers", "laid out top-to-bottom with N nodes and M
  connections", restating the legend ("solid connectors are synchronous, dashed are asynchronous" — it
  is already IN the image), "shape and colour encode the role", and any boilerplate sentence you would
  reuse verbatim on a different project. Narrate the SYSTEM and its reasoning, never the picture.
- Each **explanation bullet** is self-contained and explains that element's ROLE and design reason: what
  it is, how it connects (mechanism), and why it is there, e.g. "**API Gateway** — single entry point
  that terminates TLS and routes to the services; chosen so the mobile clients hold one endpoint and
  cross-cutting auth/rate-limiting live in one place". A bullet that only restates the label is not
  enough.
- Do NOT be formulaic across diagrams: two diagrams in the same project must read as two distinct
  explanations, not the same sentence with nouns swapped.

If `bootstrap()` cannot install Graphviz (offline), fall back to `scripts/build_diagram.py` (PIL
JSON-spec renderer). Then proceed to Phase 4.
