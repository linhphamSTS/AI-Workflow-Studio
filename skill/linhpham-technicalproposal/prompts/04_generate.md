# Phase 4 — Generate diagrams, content, and document scaffold

After Phase 3 OK, run three subagents **in parallel** (one message, three
Agent tool calls). The agents produce independent artefacts that Phase 5a
assembles.

## Agent A — diagram-builder

**Goal**: render each diagram from the Phase 2 inventory as a sharp,
real-icon-bearing PNG that matches what a Senior Solution Architect would
hand a client (NOT generic placeholder boxes).

**Inputs**: the Phase 2 diagram inventory; the chosen techstack
(determines which icon set — AWS / Azure / GCP / K8s / on-prem).

**Output**: `project_dir/output/diagrams/<slug>.png` for each diagram, plus
a `diagrams.json` whose entries carry the full "diagram block" the proposal
will render — an intro sentence, the image, the caption, and the
explanation bullets:

```json
{
  "slug": "container_diagram",
  "subheading": "Container Diagram",
  "target_heading": "Container Diagram",
  "png": "project_dir/output/diagrams/container_diagram.png",
  "caption": "Container Diagram — Loyalty Platform",
  "intro_paragraph": "<2-3 sentence framing of what this diagram is showing and why the reader should care — NOT a summary of the bullets below. Use the actual products from the chosen stack — AWS services if AWS was chosen, Azure if Azure, K8s primitives if on-prem K8s, etc. Never copy phrasing from a prior bid.>",
  "explanation_bullets": [
    "**<Service A>** — <responsibility + scaling pattern; products = whatever the §2 tech-stack table picked, not the example>.",
    "**<Service B>** — <…>",
    "**<Datastore>** — <storage choice + HA/DR pattern from §2>",
    "..."
  ]
  // NOTE: do NOT prefix bullets with "1.", "(1)", "Step 1 — ". The renderer
  // prepends "●" automatically — adding a number creates a "● 1. text"
  // duplicate. Just start each item with the bold component name.
  // Examples (illustrative only — do NOT copy):
  //   AWS bid → "Member Service horizontally scaled behind ALB; reads from a dedicated Aurora reader"
  //   Azure bid → "Member Service in an AKS deployment behind Application Gateway; reads from a PostgreSQL Flexible read replica"
  //   On-prem K8s → "Member Service in an RKE2 deployment behind MetalLB; reads from a Patroni hot-standby Postgres replica"
}
```

**Document order rendered:** `heading → intro_paragraph → image → SEQ Figure caption → explanation_bullets`. This is the standard STS proposal convention.

Conventions:

- **`intro_paragraph`** (mandatory) — 1–3 sentences that frame what the
  diagram is showing and why the reader should care. Not a summary of
  the bullets; a context-setter.
- **`explanation_bullets`** — between 7 and 17 entries per diagram
  (the prior-bid quality bar): fewer for simple diagrams, more for layered ones.
  - **DO NOT prefix items with `"1. "`, `"(1) "`, `"Step 1 — "` or any other
    manual numbering.** `build_docx.py` prepends the `●` bullet glyph
    automatically — adding a number creates the duplicate `"●  1. text"`
    that the user has flagged as a quality bug. Just start the bullet
    with the component name.
  - Format: `"**Component name** — concise description that explains what
    it does and why it's in this design."` (no leading number, no leading `●`).
  - For sequence-style diagrams where step order matters semantically,
    write `"**Step — Bank API POST with Idempotency-Key** — ..."` (the
    word "Step" carries the order without imposing a digit on every bullet).
  - One bullet per visible element. Every box / icon / boundary in the
    PNG must be named in the prose so a reader can re-draw the diagram
    from the bullets alone.
  - Mention the specific architectural property the element provides
    (idempotency, durability, eventual consistency, circuit-breaker,
    etc.) — not just the product name.
  - Match the PL03 standard pattern used in the verbatim Section 3 of
    the template so the writing voice stays consistent across the doc.
- No marketing language. Same Senior-SA voice as Problems & Solutions.

### How to render (preferred — DO use this)

Use the **`diagrams` Python package** (mingrammer/diagrams) together with
**Graphviz** as the layout engine. The package bundles 500+ real AWS / 800+
Azure / 120+ GCP / 170+ on-prem icons — auto-laid-out via Graphviz and
exported as PNG. This is the standard approach proven on prior STS bids.

### Also emit a `.drawio` editable source per diagram (MANDATORY)

PNG is great for the Word document, but the bid reviewer or the customer
will often want to **edit** the architecture in draw.io (diagrams.net)
without touching Python. After rendering each `<slug>.png`, also emit
`<slug>.drawio` to the same folder:

```python
from scripts.drawio_export import export_drawio

# Same node + edge structure you fed to the diagrams DSL,
# expressed as plain dicts for export_drawio.
nodes = [
    {"id": "alb",     "label": "ALB",           "shape": "aws-alb",     "x": 200, "y": 100},
    {"id": "eks",     "label": "EKS Cluster",   "shape": "aws-eks",     "x": 200, "y": 260},
    {"id": "aurora",  "label": "Aurora 16",     "shape": "aws-aurora",  "x": 200, "y": 420},
]
edges = [
    {"from": "alb",  "to": "eks",    "label": "HTTPS"},
    {"from": "eks",  "to": "aurora", "label": "SQL"},
]
clusters = [
    {"id": "vpc", "label": "VPC", "members": ["alb", "eks", "aurora"]},
]
export_drawio(nodes, edges, clusters,
              out_path=f"project_dir/output/diagrams/{slug}.drawio",
              title="Container Diagram")
```

The `.drawio` file opens in **app.diagrams.net** or the draw.io desktop
app and is fully editable — drag boxes, rename, reroute arrows, swap
shapes. Use the `shape` hints from `SHAPE_STYLES` so the file shows
real cloud-vendor icons (drawio binds the icon at render time —
omit/misname the hint and you get an empty rectangle). Available hints:

- **AWS:** aws-eks, aws-ec2, aws-ecs, aws-fargate, aws-lambda, aws-aurora,
  aws-rds, aws-dynamodb, aws-redis, aws-msk, aws-sqs, aws-sns, aws-s3,
  aws-glacier, aws-cloudfront, aws-api-gateway, aws-alb, aws-nlb,
  aws-route53, aws-cognito, aws-iam, aws-kms, aws-secrets, aws-vpc,
  aws-waf, aws-cloudwatch, aws-cloudtrail, aws-eventbridge,
  aws-stepfunctions, aws-codebuild, aws-codepipeline, aws-ecr
- **Azure:** azure-vm, azure-aks, azure-app-service, azure-functions,
  azure-front-door, azure-app-gateway, azure-api-management, azure-sql,
  azure-postgres, azure-mysql, azure-cosmos, azure-redis,
  azure-service-bus, azure-event-hub, azure-event-grid, azure-storage,
  azure-blob, azure-keyvault, azure-entra, azure-monitor, azure-devops,
  azure-container-reg, azure-cdn, azure-firewall, azure-waf
- **GCP:** gcp-gke, gcp-gce, gcp-cloud-run, gcp-cloud-functions, gcp-sql,
  gcp-spanner, gcp-firestore, gcp-bigtable, gcp-pubsub, gcp-gcs,
  gcp-load-balancing, gcp-cloud-cdn, gcp-iam, gcp-kms
- **Kubernetes (on-prem / vendor-neutral):** k8s-pod, k8s-deploy, k8s-svc,
  k8s-ing, k8s-ns, k8s-cm, k8s-secret, k8s-statefulset, k8s-daemonset,
  k8s-job, k8s-cronjob, k8s-node
- **Generic:** user, users, mobile, client, browser, server, database,
  firewall, router, switch, internet, cloud

Pick the hint whose label semantically matches the node (Front Door →
azure-front-door, NOT azure-aks just because both are Azure). Omit
`shape` for a plain labelled rounded rectangle. The `(x, y)` coordinates
only need to be approximate — the user will re-arrange in draw.io
anyway.

Both `.png` and `.drawio` are listed in the Phase 6 report.

Every diagram script starts with:

```python
from scripts.diagrams_runtime import bootstrap
bootstrap()  # pip-installs `diagrams` if missing, downloads & wires Graphviz portable

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EKS
from diagrams.aws.database import Aurora, ElasticacheForRedis
from diagrams.aws.network import APIGateway, CloudFront, ElbApplicationLoadBalancer
# … pick the import path that matches the chosen cloud
```

`bootstrap()` is idempotent and self-healing — first call on a fresh
machine pip-installs `diagrams` and downloads the Graphviz portable
build into `~/graphviz_portable`; subsequent calls are a no-op. **The
user never runs anything by hand.**

Common render settings for a 6.5-inch Word embed:

```python
COMMON = dict(
    show=False, outformat="png", direction="LR",  # or "TB"
    graph_attr={
        "fontsize": "18",
        "bgcolor": "white",
        "pad": "0.8",          # outer canvas padding so labels don't kiss the page edge
        "nodesep": "1.0",      # horizontal gap between sibling nodes — label rooms
        "ranksep": "1.2",      # vertical gap between ranks
        "splines": "ortho",    # orthogonal edges — never diagonal cuts through nodes
        "dpi": "300",          # 300 DPI minimum — sharp at Word's 6.5" embed
        "compound": "true",    # allow edges that cross cluster boundaries
        "labelloc": "t",       # cluster labels sit at TOP of the cluster, not floating
        "labeljust": "l",
    },
    node_attr={
        "fontsize": "14",
        "margin": "0.5,0.4",   # INNER padding around the label — pulls label away from icon edge
        "shape": "box",
        "style": "rounded,filled",
        "fillcolor": "white",
    },
    edge_attr={"fontsize": "11"},
)
```

### MANDATORY layout-quality rules (in addition to the SA Charter below)

The user has flagged these defects with zero tolerance. Apply BEFORE
rendering, then verify after render:

1. **Label NEVER touches its icon.** Use `node_attr["margin"] >= "0.6,0.5"`.
   In the `diagrams` package the icon is the node "shape" and the label
   sits below it; the margin pads the label inside the cell. Insufficient
   margin = "chữ với ảnh icon dính nhau" (the user's literal complaint).
2. **Label NEVER overflows the cluster frame.** Wrap EVERY label (node AND
   cluster) longer than 14 chars with `\n` at semantic boundaries (`+`,
   `/`, `→`, `(`, space, `-`). The label width sets the visual cell width
   — a single-line label of 25 chars punches through the cluster border
   because the cluster auto-sizes to fit nodes but NOT the cluster's own
   label. Two short lines fit, one long line doesn't.
   - Apply the same `wrap(s, limit=14)` helper to `Cluster(name=...)` —
     do NOT pass an unwrapped 32-char cluster name. The cluster name
     header overflows the cluster border just like a node label does.
3. **Cluster pad ≥ 0.6, margin ≥ 30.** Set `Cluster(name=wrap(label),
   graph_attr={"pad": "0.6", "margin": "30", "fontsize": "13"})` on every
   cluster so the border breathes around its members and the cluster name
   header doesn't crowd the topmost row of nodes.
4. **Aspect ratio for Word embed.** After render, every PNG must satisfy
   `rendered_h_in = 6.5 * height_px / width_px <= 9.0` so the diagram
   fits on a single Word page at 6.5" embed width without spilling. If
   it exceeds 9.0:
   - Switch `direction` from TB to LR (or vice versa) and re-render.
   - If still too tall, split the diagram into 2 figures (e.g.
     "Reference Architecture — Compute & Network" + "— Data & Audit").
     NEVER drop content to make it fit.
5. **Sharpness.** `graph_attr["dpi"] = "300"`. PNG must be ≥ 1500 px on
   its long side. Verify after render via PIL.

The agent re-checks rules 1, 2, 4 by re-opening each PNG with PIL and
inspecting size + a cropped view of the densest cluster. Re-render until
all four rules pass.

Use `Cluster(...)` for VPC / AZ / trust-boundary groupings, `Edge(style="dashed")`
for async events, and label every edge with the actual mechanism (`HTTPS`,
`gRPC`, event name) per the SA Charter below.

### Fallback path (only if the diagrams DSL is unavailable)

If `bootstrap()` cannot install Graphviz (e.g. an offline air-gapped
machine where the portable zip can't be downloaded), fall back to
`python scripts/build_diagram.py --spec <spec.json> --out <png>` — the
generic JSON-spec renderer. It produces less polished output but does
not require Graphviz.

### Senior SA Charter — apply to every diagram

Bake these rules into each `spec.json` and into the layout choices the agent makes.

#### A. Flow and layout conventions

- Read **top -> bottom** or **left -> right** (Western reading order); pick one and don't mix.
- User / client always **top or left**.
- Data stores at the **bottom** (not floating in the middle).
- External systems on the **right**, or inside a clearly-bordered "external" boundary box.
- One diagram = **one concern**. Don't mix deployment view + runtime view + data flow.
- **7 ± 2** elements per group. More -> split into sub-groups or split the diagram.
- Every box must be defensible in the narrative. If you can't say why X is there, remove X.

#### A.1. Reference Architecture — extra rules (Senior-SA polish)

The Reference Architecture is the diagram clients linger on. Treat it as a
portfolio piece. In addition to the rules below, the diagram-builder agent
must:

- **No orphan labels.** Every text label must be attached to a node or an
  edge. A floating `secrets` / `notes` label in empty whitespace = reject.
- **Horizontal lane alignment.** When the architecture is multi-region or
  multi-AZ, draw each region as a horizontal lane with the SAME compute /
  data / messaging tier at the SAME y-coordinate across lanes. The reader
  scans top-to-bottom and sees one consistent shape repeated.
- **Brand stripe + title at the top.** Use `labelloc="t"` (not the default
  bottom) so the diagram title is the first thing the reader sees, not the
  last. Optionally add a thin colored bar above the title using a 1-row
  hidden cluster.
- **Legend mandatory** on any Reference Architecture — even if the diagram
  uses only solid + dashed. Place it as a small `Cluster("Legend", graph_attr={"rank":"sink"})`
  at the bottom-right with 2-3 sample edges (solid = sync, dashed = async,
  red = failure / fallback). Don't make readers guess.
- **Region color hierarchy.** Primary region = saturated tint; secondary
  regions = muted tint; failover-only / shared = grey. Don't paint every
  cluster the same default `lightblue` — visual hierarchy makes the diagram
  scannable.
- **Identity / audit sits OUTSIDE region boundaries**, drawn as a single
  shared cluster on one side (typically right or bottom). Don't tuck it
  into a region's box — it spans regions.
- **`× N` notation for repeated nodes** — render as a stacked-icon group
  (mingrammer supports `[]` lists), NOT as a single icon labelled "× 4". A
  reader should see "this is a fleet" at a glance.
- **`rank="same"` discipline.** Group nodes that belong in the same horizontal
  band by passing `graph_attr={"rank":"same"}` on a wrapper cluster, OR by
  ordering siblings inside the same `Cluster()`. Don't let Graphviz make
  the layout decision when the architecture has obvious lanes.

#### B. Trust boundary and security cues (single biggest senior signal)

- VPC / subnet / DMZ -> rounded rectangle, dashed border, label `VPC: 10.0.0.0/16`.
- Public vs Private -> public subnet on top, private below; show Internet Gateway / NAT explicitly.
- Trust boundary -> bold line with label `Trust Boundary`.
- Auth flow -> arrow label is the **specific mechanism** (`JWT`, `OAuth2`, `mTLS`, `API Key`) — never generic "auth".
- Sensitive data path -> different colour edge (yellow / soft red) for PII / PCI.
- Encryption -> padlock icon on data store + label `AES-256 at rest`, `TLS 1.3 in transit`.

#### C. Flow semantics

- Sync request / response -> **solid** line, solid arrowhead, label `HTTP` or `gRPC`.
- Async / event -> **dashed** line, hollow arrowhead, label the event name.
- Read path vs Write path -> different colours (separate CQRS visually).
- Failover / fallback -> dashed grey, label `fallback`.
- Critical path -> number the steps ①->②->③->④.

#### D. Resilience and scale signals

- HA / replication -> 2-3 instance stack with arrow `replication` between them.
- Multi-AZ / multi-region -> boundary boxes labelled `AZ-1a`, `AZ-1b`, `region: ap-southeast-1`.
- Stateful vs stateless -> stateful icons get a thicker border or a tag.
- Scaling unit -> annotation `× N` or `auto-scale 2-20`.
- Circuit breaker / retry / timeout -> small edge labels `CB`, `retry 3×`, `timeout 5s`.

#### E. Annotations

- Latency budget on critical edges: `< 200 ms p99`.
- Throughput: `~10K rps`, `~500 msg/s`.
- Data classification tag on stores: `[PII]`, `[PCI]`, `[Public]`.
- Ownership: colour band per team / bounded context (DDD).
- **Legend mandatory** when the diagram uses more than 2 colours or 2 line styles.
- Caption text: write `<Type> — <Scope>` only (e.g. `Container Diagram — Booking Service`). `build_docx.py` wraps it as `Figure {SEQ}: <Type> — <Scope>` at assemble time so the number stays in sync as more diagrams are added.

#### F. Pixel-level quality rules

Hard-won lessons from prior PIL / diagrams-DSL passes. Apply to every diagram.

- **Text overflowing its own box** — never let a label cross the node's
  outer frame. For the diagrams DSL: keep node labels under ~24 chars per
  line and use `\n` to break long ones into 2-3 short lines; for the PIL
  spec renderer: chip / pill / callout width = `textbbox.width + 2 × padding`,
  never hard-code width. If a label needs more, set explicit node padding
  (Graphviz `margin="0.25,0.15"`) or shorten.
- **Arrow cutting through a `rounded_group` title chip** — terminate the arrow 6-10 px above the chip's top edge (use the chip's `cy, ch` returned by `rounded_group`). The arrow points *at* the chip.
- **Arrow cutting through other cards** — route via outer-backbone -> bridge at an x outside any title chip's x-range -> inner-backbone -> per-icon fan-out. Don't draw N parallel verticals through stacked cards.
- **Index badges (1, 2, 3 …) covering the first letter of a centred title** — place each badge as a *tab* on the card's top edge (cy = card_y, half above / half on the border), not tucked into the top-left corner.
- **Vertical centring of text in pills** — use `(bb[1] + bb[3]) // 2` against the box midline, not `(box_h - th) // 2` (PIL `textbbox.th` doesn't include `bb[1]`).
- **Diagonal cross-row arrows across long distances** slice through labels of items in between. Use orthogonal routing, or omit (the snake layout already implies the flow).

#### G. Anti-patterns to avoid

- "Kitchen sink" diagram with everything on one page.
- Drawing technology logos for tools that aren't in the stack just to look professional.
- The same component drawn twice under different names.
- Bidirectional arrows ↔ that hide the actual flow direction — split into two one-way arrows.
- A giant generic "cloud" cylinder that says nothing.
- Server icon when the stack is containerised — use container / K8s icons.
- Single DB icon when the design includes read replica / cache — show them.
- Missing legend when the diagram has 4+ colours.

#### H. Sharpness, canvas, orientation — non-negotiable

- **Orientation is chosen to fit one Word page at 6.5 inches wide, not
  by a fixed type → orientation table.** Word's body column is 6.5" wide
  and roughly 9" tall before the footer. Any embedded PNG is scaled to
  6.5" wide; its rendered height is `6.5 × (image_height / image_width)`.
  When that rendered height crosses ~9", Word splits the diagram across
  pages OR scales the text so small it's unreadable. Either is a defect.

- **Pick orientation, then measure, then decide.** The natural shape
  hint by diagram type:

  | Type | First-pick direction | Why |
  |---|---|---|
  | System Context, Container, Network / Security View | `TB` | usually stacks neatly (actors → system → datastores) |
  | Deployment Topology, Kubernetes Topology | `TB` | layered (edge → region → AZ → nodes) |
  | Sequence, Anti-Corruption Layer, CI/CD pipeline, Data Pipeline Lineage | `LR` | natural left-to-right flow |
  | AI Agent Topology | depends | LR if orchestrator-centric, TB if tool-stack-heavy |

  After the first render, **inspect the PNG aspect ratio**:

  - If `height / width > 1.4` (taller than 1.4× wide) on a `TB`
    diagram → switch to `LR`, OR drop a redundant node, OR split into
    two diagrams (e.g. separate the data tier into its own figure).
  - If `width / height > 1.8` (much wider than tall) on an `LR`
    diagram → switch to `TB`, OR group related nodes into a single
    cluster, OR break into two diagrams.
  - The sweet spot is roughly **5:4 portrait** or **3:2 landscape** —
    these embed cleanly at 6.5" wide.

- **Hard cap on rendered height:** at 6.5" embed width, the diagram's
  height must be ≤ 8.5" after scaling. If `image_height_px / image_width_px > 8.5 / 6.5 ≈ 1.31`, fix it: change direction, reduce
  nodes, or split.

- **Sharpness:** render canvas at `dpi="300"` in Graphviz `graph_attr`;
  label fonts 36–48 px at 300 DPI so they remain readable after Word
  scales down. PNG save: `optimize=False`. Use `Image.LANCZOS` if any
  resize is needed. `build_docx` default embed width is 6.5"; the pixel
  data stays at full resolution so print output is crisp.

- **Always re-open the rendered PNG and check before declaring "done":**
  load it with PIL, read its size, compute the would-be rendered height
  at 6.5" embed, and fail loudly if it exceeds 8.5". This is the
  self-check the SA Charter §I already requires; orientation belongs
  inside it.

#### I. Self-check before reporting "done"

After each PNG is rendered, the diagram-builder agent must:

1. `Read` the PNG itself and inspect the image with vision.
2. Open it with PIL, read `(w, h)`, and verify the rendered height at
   6.5" Word embed:  `rendered_h_in = 6.5 * h / w`. **Fail loudly if
   `rendered_h_in > 8.5"`** (the diagram will spill off the page).
   Re-render with the opposite direction, fewer nodes, or split the
   diagram in two — do NOT just shrink to fit.
3. Crop the most-risky region (densest area, or where chips touch arrows) and `Read` the crop too.
4. Verify each item from the list below visually:
   - Flow direction is consistent and matches the convention.
   - User / client is at top or left; data stores at bottom.
   - External systems are inside a boundary box.
   - Trust boundaries are drawn where the stack has them.
   - Sync vs Async edges are distinguishable (solid vs dashed).
   - Legend is present when needed and is readable.
   - Caption is `Figure N: Type — Scope`.
   - No text overflowing any box.
   - No arrow cutting through a chip or another card.
   - No group exceeds 9 elements.

If any check fails -> fix the spec and re-render before moving to the next diagram.

## Agent B — content-writer

**Goal**: produce the prose for every section that the stripped template
left blank (Sections 1, 2, and CASE STUDY + SUMMARY). Sections 3 (Dev
Management) is verbatim — do not rewrite it.

**Inputs**: `requirements.json` (Phase 1) + `proposal_brief.md` (Phase 2).

**Output**: a `replacements.json` whose keys are placeholder tokens used in
`proposal_template.docx` and whose values are the text to substitute. Keys
include:

```json
{
  "client_name": "...",
  "client_contact_email": "...",
  "project_title": "...",  // BARE project name only (e.g. "Phoenix Trade Compliance Platform"). The template cover already wraps it as "Technical Proposal - High Level for {{PROJECT_TITLE}} - {{CLIENT_NAME}}". DO NOT append "- High Level Technical Proposal" or "- Proposal" — that duplicates the suffix in the rendered cover.
  "proposal_date": "DD Month YYYY",
  "version": "1.0",
  "vendor_partner_name": "name of the upstream / partner system, e.g. 'the booking aggregator'; use 'the partner system' as a neutral default when the architecture has no specific external partner — never leave null because this placeholder lives in body prose, not in an optional section",
  "executive_summary": "...",
  "problems_and_solutions": [
    {"problem": "...", "solution": "..."},
    ...
  ],
  "purpose": "...",
  "system_overview_intro": "...",
  "diagram_captions": { "<diagram_slug>": "<title only — no 'Figure N:' prefix>" },
  "techstack_backend": "...",
  "techstack_frontend": "...",
  "techstack_database": "...",
  "techstack_server_hosting": "...",
  "techstack_data": "... | null",
  "techstack_ai": "... | null",
  "mobile_app_strategy": "... | null",
  "case_study_title": "...",
  "summary_body": "..."
}
```

**Required keys** — the template carries `{{KEY}}` placeholders for every
key above. Missing keys are caught by the strict reviewer's
`unfilled_placeholder` check; the build fails until they're filled. Use
`null` only for the explicitly-optional keys (`techstack_data`,
`techstack_ai`, `mobile_app_strategy`) — `build_docx.py` drops the
surrounding heading + body when their value is null. `vendor_partner_name`
must NOT be null because it lives in inline body prose, not in an optional
section; use the neutral default `"the partner system"` when no specific
upstream partner exists.

**Writing style** (from feedback memory):

- No RFP section-number references.
- No phase plans / sprint plans.
- No specific region names unless client stated one.
- Justify alignment for body text.
- **NO em-dashes (` — `) in body prose paragraphs** (executive_summary,
  purpose, system_overview_intro, techstack_*, summary_body). The user
  flagged em-dashes as "looks AI" and rejected them. Use commas,
  semicolons, parentheses, or split into two sentences. Em-dashes ARE
  still allowed in: (a) the `problems_and_solutions` rows where they
  delimit problem/solution structure, and (b) explanation_bullets where
  they delimit `**Component** — description`.
- **Problems & Solutions** — render as bullets following the Phase 2 brief's `1b` section verbatim (don't summarise it down). Each bullet is two sentences: the bold problem name + root-cause + quantified pain; then the solution named by architectural pattern + trade-off + measurable acceptance criterion. Reject vague consultant-speak ("leverage", "best-in-class", "world-class", "robust solution", "seamlessly integrate", "modernise"). The bullet count follows the brief, not a fixed quota.
- Mobile App Strategy: short and decision-only. If mobile is not in scope, set `mobile_app_strategy` to `null` and the build script will skip the section. The same null-drop applies to `techstack_data` and `techstack_ai` — only fill them when the project actually needs a data pipeline / AI layer.
- **`summary_body`** — final wrap-up of the proposal: 3–8 short paragraphs that restate the headline architectural choice, the four commitments (tech depth, delivery confidence, IP / portability, post-go-live ownership), and the service-level targets. Per-project; do not recycle wording from prior bids.
- **`case_study_title`** — the CASE STUDY section body itself is kept verbatim from the template (a single intro paragraph plus a hyperlink to a relevant STS case study). Only the title is per-project — set this to the name of the comparable client / engagement you want referenced. If the template's existing reference is not the best fit for this bid, flag it in the Phase 6 caveats so the user can swap the hyperlink target manually.
- **`diagram_captions`** — write each value as the FIGURE TITLE ONLY, e.g. `"Container Diagram — Booking Service"` (no `"Figure 3: "` prefix). `build_docx.py` wraps it with a Word SEQ field so the figure number is computed by Word automatically when the file opens. This keeps Section 2 diagrams (Figures 1–N, per project) and Section 3's verbatim diagrams (Figures N+1 onwards) renumbered correctly no matter how many diagrams a given project has. Match the diagram slugs you set in `diagrams.json` for `target_heading` so the caption attaches to the right image.

## Agent C — template-setup

**Goal**: prepare the per-project output folder and a fresh copy of
`proposal_template.docx`.

**Output**:

- `project_dir/output/{Project} - High Level Technical Proposal.docx` is a
  pristine copy of `templates/proposal_template.docx` (the reusable template)
  — Agent B's replacements + Agent A's diagrams have **not** been applied
  yet. That happens in Phase 5a.
- `project_dir/output/diagrams/` exists and is empty (Agent A populates it).
- A `manifest.json` recording the project name, timestamp, techstack chosen,
  and the diagram inventory, for Phase 6 to cite.

## Don't proceed to Phase 5a until all three agents return

If any agent fails, surface the error and ask the user whether to retry the
failed agent, skip it, or abort the whole run.
