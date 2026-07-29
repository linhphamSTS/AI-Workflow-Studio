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
  "caption": "Container Diagram: Loyalty Platform",
  "intro_paragraph": "<2-3 sentence framing of what this diagram is showing and why the reader should care. NOT a summary of the bullets below. Use the actual products from the chosen stack: AWS services if AWS was chosen, Azure if Azure, K8s primitives if on-prem K8s. Never copy phrasing from a prior bid. No em-dashes and no Latin abbreviations in this text.>",
  "explanation_bullets": [
    "**<Service A>**: <responsibility + scaling pattern; products = whatever the §2 tech-stack table picked, not the example>.",
    "**<Service B>**: <…>",
    "**<Datastore>**: <storage choice + HA/DR pattern from §2>",
    "..."
  ]
  // NOTE: do NOT prefix bullets with "1.", "(1)", "Step 1: ". The renderer
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

- **`intro_paragraph`** (mandatory) — 1–3 sentences, **at most 70 words**, framing what the
  diagram shows and why the reader should care. Not a summary of the bullets; a
  context-setter. Measured on two deliveries, the intro is the second-largest source of
  bloat after the words inside each bullet, and it is the easiest to cut because the figure
  and its bullets carry the content.
- **`explanation_bullets`** — between 7 and 17 entries per diagram
  (the prior-bid quality bar): fewer for simple diagrams, more for layered ones.
  **Averaging at most 25 words each, and no single bullet past 40.** The count is not what
  makes a figure section long; the words inside each bullet are. Twelve tight bullets beat six
  loose ones at the same budget and let a reader name every component.

  The AVERAGE is the measure, not the longest, and that is deliberate: measured across a
  delivery the reader rates highly, the per-figure averages sit at 21 to 24 and cluster
  tightly, while the longest bullet ranges from 26 to 51 and tells you nothing. A single long
  bullet among eleven tight ones is fine; eleven bullets that are all a bit too long is what
  reads as padding. (Note this is the OPPOSITE of the rule for prose sections, where one
  over-long entry hiding among short ones is exactly what a reader stumbles on. Different
  signal, different statistic. Do not copy one rule onto the other.)
  - **DO NOT prefix items with `"1. "`, `"(1) "`, `"Step 1 — "` or any other
    manual numbering.** `build_docx.py` prepends the `●` bullet glyph
    automatically — adding a number creates the duplicate `"●  1. text"`
    that the user has flagged as a quality bug. Just start the bullet
    with the component name.
  - Format: `"**Component name**: concise description that explains what
    it does and why it's in this design."` (no leading number, no leading `●`,
    and a COLON after the bold label, never a dash).
  - For sequence-style diagrams where step order matters semantically,
    write `"**Step, Bank API POST with Idempotency-Key**: ..."` (the
    word "Step" carries the order without imposing a digit on every bullet).
  - One bullet per visible element. Every box / icon / boundary in the
    PNG must be named in the prose so a reader can re-draw the diagram
    from the bullets alone.
  - Mention the specific architectural property the element provides
    (idempotency, durability, eventual consistency, circuit-breaker,
    etc.) — not just the product name.

  **A component bullet carries FOUR things in one sentence.** This is what separates a
  figure a reader trusts from a caption they skim. Not every bullet can carry all four, but
  a figure whose bullets carry none of them is a labelled picture with a list beside it:

  1. **The concrete product or service, named, in the bold label.** `**Customer app
     (Flutter)**`, `**Managed PostgreSQL**`, `**MoMo / ZaloPay / VNPay + cards**`. A generic
     label such as `**Database**` or `**The API layer**` wastes the one place a reader looks
     for the technology decision. Where the platform is chosen, name the platform's service.
  2. **What travels on the wire.** `HTTPS`, `WSS`, `gRPC`, `mTLS`, `webhook`, `OIDC`, `SOAP`,
     `file exchange`, `AMQP`, `Kafka protocol`. An architecture diagram whose prose never
     names a protocol has not described an integration.
  3. **Synchronous or asynchronous**, in those words or their equivalent. This is the single
     most useful fact about an edge and the one most often left out. "invoked synchronously
     to charge and asynchronously via webhook for confirmation" tells a reviewer more than
     three sentences of description.
  4. **What happens when it fails, or the property that stops it failing.** "so a push
     outage cannot block a transaction", "never trusted as a source of truth", "so a retried
     payment cannot double-charge", "replaced behind an abstraction without touching the
     domain". If an element cannot fail interestingly, give its ordering, durability or
     isolation property instead.

  **Naming the protocol and closing with the line convention are expected, not universal.**
  Measured on the well-rated delivery, five of eight figures name a wire protocol and only two
  restate the line convention: a decomposition view or a pipeline view legitimately names
  neither. So the reviewer prompts for both rather than failing them. **Saying whether an
  interaction is synchronous or asynchronous IS universal** — that delivery carries it on
  every figure, and it is checked as a hard requirement.

  Where the figure has a legend, the last bullet explains the line convention, so the reader can interpret the picture without scrolling back to the legend:

  > `**Edge semantics**: solid edges are synchronous request and response; dashed edges are
  > asynchronous events or fire-and-forget, a convention carried through every later figure.`

  **Rejected bullets:** one that only restates its own label; one that describes what a
  component *is* without saying what it *does for this design*; two bullets for one element;
  a bullet naming a component that is not in the rendered figure.
  - Match the PL03 standard pattern used in the verbatim Section 3 of
    the template so the writing voice stays consistent across the doc.
- No marketing language. Same Senior-SA voice as Problems & Solutions.

### How to render — PRIMARY: the deterministic SA-grade renderers (DO use these first)

Render each diagram with the skill's dedicated renderers in `scripts/`. They are
deterministic (you author a `spec.json`; they draw it) and they BAKE IN the senior-SA
structure — nested trust boundaries, a legend, per-tier colour hierarchy, `wrap_label`
(no orphaned "("), orthogonal + skip-edge routing, arrow anti-overlap, 300 DPI, and the
Word aspect cap — and they emit a NATIVE per-component-editable `.drawio` + an `.svg`
twin automatically. **You do NOT hand-code layout or call `export_drawio` yourself** —
each renderer writes `<slug>.png` + `<slug>.svg` + `<slug>.drawio` (+ `<slug>.lint.json`)
in one shot. Pick the renderer by diagram family:

**1. Cloud / infra / architecture / K8s / on-prem / CI-CD / data-pipeline / microservices
→ `scripts/build_cloud.py`** (manual-grid, brochure-grade). Author a `spec.json`:

```json
{
  "title": "AWS Reference Architecture — Multi-AZ",
  "legend": true,
  "columns": [
    {"id": "edge", "boundary": {"label": "Edge / Global", "fill": "#FFF8E1", "stroke": "#F9A825"},
     "nodes": [{"id": "dns", "label": "Route 53", "icon": "aws/route-53"},
               {"id": "waf", "label": "AWS WAF",  "icon": "aws/waf"}]},
    {"id": "data", "boundary": {"label": "Data Subnets (Multi-AZ)", "fill": "#E7F0FA", "stroke": "#1E88E5"},
     "nodes": [{"id": "aur", "label": "Aurora primary", "icon": "aws/aurora", "tags": ["SoR"]}]}
  ],
  "wraps":  [{"label": "VPC 10.0.0.0/16", "stroke": "#8C4FFF", "dashed": true,
              "icon": "aws/vpc", "cols": ["edge", "data"]}],
  "shared": {"label": "Security & Observability (account-scoped)", "fill": "#FDECEA", "stroke": "#DD344C",
             "anchor": {"from": "data", "label": "IAM / KMS / TLS / metrics"},
             "nodes": [{"id": "iam", "label": "IAM", "icon": "aws/identity-and-access-management"}]},
  "edges":  [{"from": "waf", "to": "aur", "label": "HTTPS"},
             {"from": "aur", "to": "aur2", "label": "replication", "style": "dashed", "color": "#2E7D32"}]
}
```
- `columns[]` = tiers left→right; each has an optional `boundary{label,fill,stroke,icon,dashed}`
  (the subnet box) and `nodes[]{id,label,icon,tech?,tags?}`.
- `wraps[]{label,fill,stroke,dashed,icon,cols[]}` = a boundary (VPC / VNet) spanning a
  contiguous range of columns → this is what gives the VPC⊃subnet NESTING.
- `shared{label,fill,stroke,anchor{from,label},nodes[]}` = the bottom cross-cutting band
  (IAM / KMS / observability), linked by ONE anchor edge (never a per-icon spider-web).
- `edges[]{from,to,label?,style?("dashed"),color?}`; `"legend": true` draws the sync/async legend.
- Icons are `provider/stem` refs (`aws/aurora`, `azure/aks`, `gcp/gke`, `ai/openai`,
  `network/...`, `container/...`, `generic/...`). The renderer maps each to a native draw.io
  vendor stencil where one exists, else embeds the icon PNG as an individually-editable cell.
- **13 ready-made canonical specs live in `scripts/cloud_specs.py`** (`aws_ref`, `azure_ref`,
  `gcp_ref`, `onprem_hybrid`, `k8s_topology`, `docker_compose`, `cicd`, `data_pipeline`,
  `gitops`, `microservices`, `c4_container`, `uml_deployment`, `ai_rag`) — start from the one
  matching Phase 2's cloud and adapt names/edges to THIS project.

Render: `python scripts/build_cloud.py --spec <slug>.spec.json --out project_dir/output/diagrams/<slug>.png`

**2. Notation diagrams (flowchart, decision tree, state machine, ERD, UML class,
C4 context/container, DFD, org chart, mind map, network, swimlane) → `scripts/build_graph.py`**
(Graphviz, correct ISO / UML shapes — diamond decision, ellipse start, cylinder datastore):

```json
{"slug": "order_flow", "title": "Order Processing Flow", "diagram_type": "flowchart",
 "engine": "dot", "direction": "TB",
 "nodes": [{"id": "s", "label": "Start", "role": "start"},
           {"id": "p", "label": "Payment OK?", "role": "decision"},
           {"id": "db", "label": "Orders", "role": "datastore"}],
 "edges": [{"from": "s", "to": "p"}, {"from": "p", "to": "ship", "label": "yes"}],
 "clusters": [{"id": "sw", "label": "Customer", "members": ["s"]}]}
```
`role` picks the shape (start=ellipse, process=rounded box, decision=diamond,
datastore=cylinder…); ERD uses `"type":"entity"` + `attributes[]`, class uses `"type":"class"`
+ `fields[]`/`methods[]`; `edge.kind` (`async`/`inheritance`/`composition`…) picks the arrow;
one level of `clusters` nesting via `parent`.
Render: `python scripts/build_graph.py --spec <slug>.spec.json --out project_dir/output/diagrams/<slug>.png`
→ PNG + SVG + native `.drawio`.

**3. UML sequence diagrams → `scripts/build_sequence.py`** — spec keys `participants[]`,
`messages[]` (sync / async / return / self), `fragments[]` (alt / opt / loop), `title`
(PNG only; sequence shapes don't round-trip to `.drawio`).
Render: `python scripts/build_sequence.py --spec <slug>.spec.json --out project_dir/output/diagrams/<slug>.png`

> **RENDER IN THE CLOUD CHOSEN IN PHASE 2 — never default to AWS.** Use the icon provider
> matching Phase-2's stack (`aws/*`, `azure/*`, `gcp/*`, or `container/*`+`network/*` for
> on-prem K8s). Using AWS icons for an Azure / GCP decision is a REJECT.

These renderers already apply the nesting + legend + colour-hierarchy + `wrap_label` + ortho /
skip-edge routing + arrow anti-overlap + aspect + DPI rules described in the rest of this section
and the SA Charter below — so you do NOT re-implement them; you author a faithful `spec.json`,
render, then run the self-check. The `.drawio` + `.svg` come out automatically. Only reach for the
mingrammer fallback below if a diagram genuinely does not fit any of the three renderers above.

### Renderer gotchas that cost a re-render — apply while AUTHORING the spec

These are defects the renderers do NOT prevent for you. Each one was found by looking at a rendered
PNG, not by a check, so build the spec so they cannot happen:

1. **`build_cloud`: never draw an edge between two nodes in the SAME column.** A node's label is
   drawn BELOW its icon, and a same-column edge is anchored on the icon edge and runs vertically at
   the node's centre x, so it ploughs straight through the source node's own label text and through
   every node stacked between the two endpoints. Give the two ends of the relationship their own
   columns (a 6th column costs ~700 px of width and reads fine), or drop the edge: in `build_cloud`
   the COLUMN BOUNDARY is the cluster, so **one** edge into a column visually connects every node
   inside it and the rest are not "floating".
   *This is about SAME-column edges only.* An edge spanning two or more columns is safe: see item 12.
2. **`build_cloud`: aim the cross-column edge at a node near the source's own y.** The single node in
   a short column sits at the vertical centre, so an edge from it to the FIRST node of a 6-node
   column travels far vertically and clips the icons it passes. Target a node whose row is near the
   source's row, or balance the columns by giving the short one 2-3 nodes.
3. **`build_cloud`: a same-column edge label lands in the right-hand gutter** at
   `node_centre_x + CELL_W/2 + COL_PAD + 10*S`. On the right-most column that runs off the canvas and
   the label is clipped. Keep such labels to one short word, or restructure per rule 1.
4. **`build_sequence`: the fragment tag chip collides with the first message label.** The chip is
   drawn at the fragment box's top-left, in the same y band as the label of the fragment's first
   message. Before rendering, check `MARGIN*0.6 + textwidth(f"{TYPE}  [{label}]", 26px bold) + 2*22`
   against `midpoint(first message) - textwidth(first message label, 28px)/2`. If it does not clear,
   SHORTEN the fragment label (put the nuance in the explanation bullets) or start the fragment on a
   message whose span sits further right. Participant labels are not wrapped either: keep them under
   ~20 characters or they clip at `COL_W - 60`.
5. **Icon packs are not interchangeable in intent.** `assets/icons/ai/` is a VENDOR-LOGO pack
   (`ai/pay` is Amazon Pay, `ai/openai` is OpenAI). Never reach into it for a GENERIC role such as
   "partner banks" or "payment provider" — a vendor logo for a product that is not in the chosen
   stack is an SA-charter anti-pattern and a reviewer reads it as copy-paste. Use a neutral
   provider-family icon instead (`azure/cost-management-and-billing`, `azure/software-as-a-service`,
   `azure/compliance`, `azure/marketplace` all read as institution / money / regulator / merchant),
   and preview an unfamiliar icon by opening the PNG before you trust its name.
6. **The "no RFP section-number references" rule applies to DIAGRAM TEXT too**, not just body prose.
   Requirement codes and section numbers (`CC-02`, `SEC-03`, `Section 7.1`) baked into a boundary
   label or a shared-band caption are exactly the machine-assembled tell the client rejects. Say what
   the requirement IS ("built once, priced once", "PDPL, residency and secure delivery"), not where it
   is numbered.
7. **`build_cloud`: anchor the shared band to the BOTTOM-most node of its column.**
   `_shared_anchor` drops a vertical line from the source node's centre x straight down to the band,
   so if the source is the FIRST node of a 3-node column the line ploughs through the icons AND the
   labels of every node stacked below it. Because a node's label is drawn directly under its icon,
   *some* label is always crossed; picking the bottom node limits the damage to the source's own
   label, which is the acceptable case. `shared.anchor.from` must therefore name the last entry in
   that column's `nodes[]`. Same failure mode as rule 1, different code path — rule 1 will not save
   you here.
8. **`build_sequence`: never put a self-call on the right-most participant.** The self-loop label is
   drawn unwrapped at `cx + 150 + 18` and the canvas ends at `MARGIN*2 + COL_W*n`, so a self-message
   on the last lifeline runs off the edge and is silently truncated ("three way reconciliati"). Check
   `cx(from) + 168 + textwidth(label, 28px) <= canvas_w`; if it fails, reorder the participants so the
   self-calling one is not last. Reordering is free and usually improves the reading order anyway.
9. **Check the ON-PAGE text size, not just the height.** `diagram_check.py` verifies rendered HEIGHT
   and embed DPI, and a very wide diagram passes both while being unreadable: at a 6.5in embed the
   on-page size of a label is `font_pt * 6.5 * 300 / 72 / width_px`. A `build_graph` diagram with more
   than ~10 cards fans out horizontally and can hit 14,000px wide, which puts 13pt body text at under
   2pt on the page. Compute it before you accept the render; below ~2.5pt, re-author the diagram for
   `build_cloud`'s manual grid (same content, roughly a third of the width) rather than shrinking the
   content. Corollary: on `build_graph` cards, keep `subtitle` under ~30 chars — an unwrapped subtitle
   sets the card width and is the usual cause of the blow-out. `wrap_label` also collapses overflow
   into the LAST line (`max_lines=3`), so a >66-char node label renders as two short lines plus one
   enormous one; keep card labels short and push detail into the explanation bullets.
10. **Two cheap pre-render checks pay for themselves** (write them into the run's own `specs/` folder,
   never into the skill): one that measures every sequence fragment chip and self-call label against
   the canvas before rendering (rules 4 and 8), and one that re-renders a `build_cloud` spec to a
   throwaway path and prints the actual colliding rectangles from `build_cloud._LINT["boxes"]`. The
   renderer's own `label_overlap` message says only "an edge label overlaps a icon label" — it never
   names WHICH, so without the probe you are guessing at which of a dozen labels to shorten.
   `_LINT["boxes"]` stores `(kind, bbox)` with no text, so to get the offending STRING, monkeypatch
   `PIL.ImageDraw.ImageDraw.text` to log every drawn string with its measured box, render to a
   throwaway path, then intersect. Note that `label_overlap` is frequently edge-label-versus-ICON,
   not text-versus-text, so a text-only probe can come back empty on a spec that genuinely fails.

11. **`build_cloud`: an adjacent-column edge label gets only HALF the gutter, so keep it under ~26
   characters.** `_edge` routes a same-row adjacent edge as `[sp -> (mx, y) -> (mx, y) -> ep]`, which
   makes the two horizontal runs equal length, and `_longest_mid` returns the midpoint of the FIRST
   one. The label is therefore centred a **quarter** of the way across the gap, not half, so its left
   edge runs back onto the source icon long before it reaches the target. The usable width is
   `(COL_GAP + 2*COL_PAD + CELL_W - ICON) / 2`, about **318 px** at `S = 3`. Measure it statically
   before rendering: build the edge font with `build_cloud._font(8 * build_cloud.S)` (`BC.FT` is only
   populated inside `render()`), measure every adjacent-column edge label with `textlength`, and
   shorten anything over ~300 px. Judging by the raw `COL_GAP` alone over-reports by roughly 2.5x, so
   use the formula, and put the nuance in the explanation bullet rather than in the edge label.

12. **`build_cloud`: an edge spanning two or more columns is SAFE, but it costs height.** `_plan_edges`
   marks it as a `skip` and `_route_skip` sends it out through the source-side gutter, along a clear
   bus lane BELOW the boxes, and back up the target-side gutter, staggering the channel per edge, so
   it never crosses the icons of the columns it spans. Do not restructure a diagram to avoid one.
   What it does cost is a bus lane each: four skip edges on a reuse map added a visible dead band
   between the columns and the shared band and pushed the render from about 3in to 5.6in tall at the
   6.5in embed. So budget skip edges against the HEIGHT cap in rule 4, and if a diagram needs many of
   them, prefer routing from a single representative node per column (the column boundary is the
   cluster, so one edge still reads as connecting everything inside it).
   **But a LABELLED skip is not safe: the label does not follow the line into the clear bus lane.**
   `_longest_mid` puts the label on the longest RUN of the route, and that is usually the vertical
   riser up to the target row rather than the horizontal bus lane, so the label lands in a column
   gutter and can sit on top of an icon. This is a real `label_overlap` blocker, not a cosmetic
   risk (a 469 px skip label landed on a token-accounting icon). Either leave the skip unlabelled
   and put the mechanism in the explanation bullet, or source it from the column's LAST node and
   keep the label to two short words. Height is also legibility, not just page fit: re-authoring a
   reuse map to ZERO skip edges took it from 5.6in to 4.8in at the 6.5in embed and lifted on-page
   node text from 3.5 pt to 4.2 pt, so treat "how few skips can this diagram carry" as a design
   question, not an afterthought.

13. **`build_graph` in `TB`: the width is set by the SUM of the EDGE-LABEL widths in the busiest rank
   gap, not only by the card count.** Every labelled edge becomes a virtual label node in an
   intermediate rank, so ten labelled edges crossing one gap lay their labels out side by side and
   that row, not the cards, becomes the widest thing in the graph. On a context diagram, shortening
   five labels (`OpenID Connect` to `OIDC` on three edges, two connector labels to two words) took
   16.82in to 15.14in of predicted width and lifted on-page text from 4.68 pt to 5.24 pt, with the
   full term kept once on the federation edge and in the bullets. The counter-intuitive corollary:
   **deleting edges can make the graph WIDER** (dropping three edges cost 2.5in, because `mincross`
   reordered the ranks), so shorten labels and merge cards, do not thin the graph out. Card overhead
   is fixed at roughly 1.45in each (node margin both sides, cell padding, `nodesep`), so about 5
   cards per rank is the practical ceiling before gotcha 9 bites. Measure the prediction from the
   spec BEFORE rendering; a re-authored context view came in at 4842 px wide against the previous
   version's 5754 px, which is where the legibility gain actually came from.

14. **A lint-clean `build_cloud` gutter can still read as ONE wrong line.** Two edges that terminate
   at nearly the same y from opposite directions, in the same column gutter, draw what a reader sees
   as a single continuous line joining the wrong two nodes (an image registry to a manifest repo, on
   one run). `_lint_layout` cannot see it because nothing overlaps: the boxes are metres apart in
   pixel terms and each line is individually correct. The same near-colinearity also produces
   near-parallel double runs 16 px apart when row *n* of one column and row *n* of the next are
   almost level. Both are found only by opening the PNG and looking at each gutter, and both are
   fixed by reordering `nodes[]` inside one column or re-sourcing the edge from a different node, not
   by shortening anything. So after the lint passes, budget one pass per figure that looks ONLY at
   the gutters. Related, and worth knowing before you go hunting for a file that is not there:
   `build_cloud` writes `<slug>.lint.json` **only when there are defects**, and deletes a stale one,
   so a missing sidecar is the clean result, not a failed run.

### VERSIONED RE-RUN — reuse the CONTENT, never the RENDERER (MANDATORY)

When you are regenerating a proposal that already has a previous output (a web-app
`output/versions/<N-1>/`, or any prior run of the same project), separate the two halves:

| Reuse verbatim — this is CONTENT | Re-derive every time — this is RENDERING |
|---|---|
| `plan.json` (the confirmed stack + diagram set) | which renderer draws each diagram |
| `replacements.json` (the written proposal prose) | the `spec.json` you feed the renderer |
| each diagram's `caption`, `intro_paragraph`, `explanation_bullets` | the PNG / SVG / `.drawio` themselves |
| the diagram set, slugs and `target_heading`s | the `.docx` assembly (`build_docx.py`) |

**NEVER copy a prior version's build script, renderer choice, or rendered images forward.**
Always re-select the renderer from the PRIMARY list above and re-render from a freshly authored
`spec.json`. A prior version was produced by whatever the skill could do on that date; the skill
improves through exactly this prompt, so a run that replays the old build script silently opts out
of every subsequent improvement — the output stops getting better no matter how much the skill learns.

Reusing the content keeps the proposal stable across iterations (the user already accepted that
analysis and that prose). Re-deriving the render is what lets a regenerate pick up the current
renderers, the current DPI rules and the current SA-grade structure. If a re-render genuinely
regresses against the previous version, say so in the Phase 6 report rather than silently
reinstating the old images.

**Reused prose AGES, because the reviewer gains checks between runs. Re-validate it before you
assemble.** This is the second half of the seam rule and it is not optional. `format_reviewer.py`
grows new checks out of exactly this self-learning loop, so prose that shipped clean from the
previous version can be a DEFECT this run without a single word of it changing. It has already
happened twice: the optional-section word ceilings and the `team_roles` table shape were both
added by one run's Phase 6 and both broke the next run's reused content (seven sections over
ceiling, one blocker). Before you reuse a value, run the current rules over it:

- Count words for every capped prose section and every list ENTRY, in the generator, and fail
  your own build on a breach rather than discovering it in the format review.
- Re-check the required SHAPE of every value, not just its text: `team_roles` and every
  `techstack_*` must be an array of `{name, description}` objects; a list of strings that used to
  render as bullets is now a blocker.
- `git diff` the skill since the previous version's date, or just read the newest
  `LESSONS_LEARNED.md` entries, and treat anything the reviewer gained as a rule that applies to
  the OLD prose too.
- Diff `plan.json` against any `.bak_*` file beside it. A re-confirmed plan can silently retire a
  whole recommendation, and the retired wording survives in the reused prose: one run had to
  scrub a second-hyperscaler alternative out of two technology rows and an assumption entry after
  the plan became single-cloud.

Cutting an over-long section without losing substance follows the order in "How to cut without
losing substance", with one addition that does the most work on a re-run: **de-duplicate across
sections.** Two optional sections written months apart often state the same commitment twice (a
monthly service report described in both Support Model and Service Level Targets), and deleting
the second copy costs nothing.

**Content reuse is not a byte copy: relabel every bullet against the NEW render.** This is the trap
on the seam between the two halves. An `explanation_bullets` entry is `**<node name>**: <substance>`,
and the node name came from the PREVIOUS version's diagram. Re-authoring the spec renames, merges and
splits nodes ("UAE PASS" becomes "National digital identity", nine service groups become eight, a
vendor product becomes a neutral capability), so replaying the old bullet list verbatim ships bullets
naming boxes the reader cannot find, which is exactly the "one bullet per visible element" rule
broken in the least visible way. Do it per diagram: keep each bullet's SUBSTANCE (it was accepted)
and re-point its bold label at a node that exists in the new PNG, merging two bullets when you merged
two nodes so the count stays inside 7 to 17. Do not lean on `diagram_check`'s `explanation_orphan` to
find these: it is a warning, and it only fires when NO word of the bold label appears anywhere in the
`.drawio`, so it misses a rename that keeps any word in common. Also re-check every FIGURE in the
prose against the re-read inputs: a regenerate whose `plan.json` was re-confirmed can carry new
effort, task or count figures, and those numbers appear in the bullets, the intro paragraphs and a
boundary label as well as in `replacements.json`.

**Keep scratch images out of `output/diagrams/`.** `diagram_check.py --dir` treats every PNG in the
folder as a diagram, so a crop you saved while eyeballing a dense cluster is reported as an extra
diagram with a missing `.drawio`. Write crops and probe output to a sibling `specs/` or `_scratch/`
folder. And note what each renderer actually emits: `build_graph` writes PNG + SVG + `.drawio`,
`build_cloud` writes PNG + `.drawio` (no SVG), `build_sequence` writes PNG only. Do not promise an
SVG twin per figure in the Phase 6 report unless `build_graph` drew it.

### Fallback — mingrammer `diagrams` DSL (only if a diagram doesn't fit the primary renderers above)

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
from scripts.diagrams_runtime import wrap_label   # the SAME wrapper used for the PNG

# Same node + edge + cluster structure you fed to the diagrams DSL, as plain
# dicts. Wrap labels with wrap_label() — the SAME text you gave the PNG nodes —
# so the .drawio reads identically. You do NOT pass x/y: export_drawio lays the
# graph out with Graphviz (the same engine as the PNG) so the .drawio MATCHES
# the PNG's structure, flow direction and grouping.
nodes = [
    {"id": "alb",     "label": wrap_label("ALB (TLS ingress)"), "shape": "aws-alb"},
    {"id": "eks",     "label": wrap_label("EKS Cluster"),       "shape": "aws-eks"},
    {"id": "aurora",  "label": wrap_label("Aurora PG 16"),      "shape": "aws-aurora"},
]
edges = [
    {"from": "alb",  "to": "eks",    "label": "HTTPS"},
    {"from": "eks",  "to": "aurora", "label": "SQL"},
    # add "dashed": True for an async / event edge
]
clusters = [
    # MIRROR the PNG's nesting: a cluster can carry "parent": <cluster id> so the
    # .drawio shows the SAME VPC->subnet->pool trust boundaries as the PNG (not
    # flat sibling boxes). A parent cluster's own "members" are only the nodes
    # directly in it; child subnets nest via "parent".
    {"id": "vpc",  "label": wrap_label("VPC 10.0.0.0/16"), "members": []},
    {"id": "pub",  "label": wrap_label("Public Subnet"),   "members": ["alb"],    "parent": "vpc"},
    {"id": "priv", "label": wrap_label("Private Subnets"),  "members": ["eks"],    "parent": "vpc"},
    {"id": "data", "label": wrap_label("Data Tier"),        "members": ["aurora"], "parent": "vpc"},
]
export_drawio(nodes, edges, clusters,
              out_path=f"project_dir/output/diagrams/{slug}.drawio",
              title="Container Diagram",
              direction="TB")   # MUST equal the PNG's Diagram(direction=...)
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
`shape` for a plain labelled rounded rectangle. You do NOT supply
coordinates — `export_drawio` runs Graphviz to position the boxes and
clusters just like the PNG, so the editable source opens looking the
SAME as the figure (this is what fixes "the .drawio doesn't look like
the image"). Always pass `direction=` matching the PNG so they can't
diverge.

Both `.png` and `.drawio` are listed in the Phase 6 report.

Every diagram script starts with:

```python
from scripts.diagrams_runtime import bootstrap, wrap_label
bootstrap()  # ensures `diagrams` + its bundled icons + Graphviz portable are ready

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
        "splines": "ortho",    # orthogonal edges — never diagonal cuts through nodes.
                               # NOTE: some Graphviz builds DROP edge labels with
                               # "ortho" — if your edges carry labels and they
                               # vanish, switch to "spline" or "polyline".
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

### NO LONG-SPAN EDGES — the "bent, ugly arrows" defect, and how to design it away

A reader rejected a figure as having crooked, ugly arrows. The cause was not the renderer:
five async edges each connected a node in one column to a node four or five columns away.
The layout engine has nowhere to put those, so it drops them into routing lanes BELOW every
boundary box, and each one travels down, across the full width of the page, and back up.
Five of them stacked is a tangle of dashed lines under the diagram, and it reads as sloppy
however crisp each individual line is.

**Rules, in the order to apply them:**

1. **An edge should span at most TWO columns.** Before drawing one that spans more, reorder
   the columns so the two nodes are neighbours. Column order is free; edge length is not.
2. **When many nodes talk to the SAME hub, draw a bus, not N long lines.** An event
   backbone, a service mesh, an identity provider or a telemetry sink that every component
   touches becomes ONE horizontal band with short stubs into it. That is also how a
   principal architect would draw it on a whiteboard: five lines crossing the page say
   "five relationships", one labelled band says "this is shared infrastructure", which is
   the actual meaning.
3. **A cross-cutting concern belongs in a band, not in edges.** Security, keys, policy and
   telemetry touch everything. One band along the bottom with a single labelled connector
   beats one edge per consumer.
4. **If a relationship still needs a long edge after 1 to 3, delete the edge and put the
   relationship in an explanation bullet.** A diagram is not obliged to draw every true
   statement, and a line nobody can follow communicates less than a sentence.
5. **Count before rendering.** If any edge spans more than two columns, or more than two
   edges route below the boundary boxes, the layout is wrong and re-rendering will not fix
   it. Change the composition.

Keep `splines="ortho"`: right angles are correct. The defect is edge LENGTH and edge COUNT,
which no spline setting can repair.

### SA-GRADE STRUCTURE — MANDATORY (this is what makes it look senior, not tool-generated)

Flat sibling clusters laid out by auto-layout read as "generated by a tool".
A senior-SA diagram has three things the flat version lacks — **NEST**, a
**LEGEND**, and a **COLOUR HIERARCHY**. Apply ALL THREE to every architecture /
reference diagram. A flat-sibling-cluster reference architecture is a REJECT.

> **RENDER IN THE CLOUD CHOSEN IN PHASE 2 — never default to AWS.** The examples
> below happen to use AWS services, but the cloud was an impartial Phase-2
> decision; if Phase 2 chose Azure / GCP / on-prem, draw THAT. The nesting,
> legend and colour rules are identical across clouds — only the icons/imports
> change:
> - **AWS:** `diagrams.aws.*`, shape hints `aws-*`; VPC → Subnet → EKS pool.
> - **Azure:** `diagrams.azure.*`, hints `azure-*`; **VNet → Subnet → AKS** node pool, Front Door/App Gateway ingress, Cosmos/Azure DB, Service Bus/Event Hub.
> - **GCP:** `diagrams.gcp.*`, hints `gcp-*`; **VPC → Subnet → GKE**, Cloud LB, Cloud SQL/Spanner, Pub/Sub.
> - **On-prem / vendor-neutral:** `diagrams.k8s.*` / `diagrams.onprem.*`, hints `k8s-*`; Cluster → Namespace → workloads.
> Using AWS shapes for an Azure/GCP decision is a REJECT — it contradicts the
> Phase-2 stack and reads as a copy-paste.

**1. NEST the trust boundaries.** The network boundary (AWS VPC / Azure VNet /
GCP VPC) is an OUTER cluster that CONTAINS the subnets; subnets contain their
nodes; node pools nest again. NEVER draw "Public Subnet" / "Private Subnet" /
"Data Tier" as flat siblings — put them INSIDE the network boundary. Put the
CIDR on the boundary box, not jammed into a subnet label.

```python
# AWS shown; for Azure use diagrams.azure.* (VNet/AKS), for GCP diagrams.gcp.* (VPC/GKE)
from diagrams.aws.network import InternetGateway, NATGateway, ELB
from diagrams.aws.compute import EKS
from diagrams.aws.database import Aurora
with Cluster("VPC  10.0.0.0/16", graph_attr={"bgcolor": "#E8F1FB",
             "pencolor": "#1E88E5", "style": "rounded,dashed", "fontsize": "15"}):
    with Cluster("Public Subnet", graph_attr={"bgcolor": "#FBF3E0"}):
        igw = InternetGateway("Internet Gateway"); alb = ELB(wrap_label("ALB (TLS ingress)"))
        igw >> alb
    with Cluster("Private Subnets — EKS", graph_attr={"bgcolor": "#FBE9E7"}):
        with Cluster("Realtime pool", graph_attr={"bgcolor": "#FFFFFF"}):
            eks_rt = EKS(wrap_label("WS gateway + dispatch"))
        with Cluster("Transactional pool", graph_attr={"bgcolor": "#FFFFFF"}):
            eks_tx = EKS(wrap_label("payment / ordering + BFF"))
    with Cluster("Data Tier", graph_attr={"bgcolor": "#E7F0FA"}):
        aur = Aurora(wrap_label("Aurora PG + PostGIS [SoR]"))
    alb >> Edge(label="HTTP / WSS") >> eks_rt
```

**2. LEGEND mandatory** on every reference/architecture diagram — a small
`Cluster("Legend")` near a corner with one solid + one dashed sample edge so the
reader never guesses what solid vs dashed means:

```python
with Cluster("Legend"):
    a = Users("sync (req/resp)"); b = Users("async (event)")
    a >> Edge(label="solid") >> b
    a >> Edge(label="dashed", style="dashed") >> b
```

**3. COLOUR HIERARCHY + NO floating boxes.** Give each tier its own pale
`bgcolor` (VPC light-blue, public amber, private pink, data blue, messaging
purple, shared red) so the eye reads the layers. EVERY cluster must connect to
the flow OR be a clearly-labelled cross-cutting sidebar (e.g. "Shared Identity /
Audit / Ops" linked by a dashed "secrets / metrics" edge). A cluster with NO
edges floating in whitespace reads as amateur — connect it or remove it.

**4. FLOW discipline.** Western reading order: clients top/left → edge → public
subnet → private compute → data/messaging at the bottom/right. `direction="TB"`
for layered stacks; `"LR"` only when TB overflows the 9in page cap.
`splines="ortho"` for crisp right-angle routing.

This nested-boundary + legend + colour-hierarchy structure is the difference
between "drew it in 5 minutes with a tool" and "a Solution Architect designed
this". When you finish a diagram, look at it (open the PNG) and ask: *would a
principal SA put this in front of a client?* If the boundaries are flat or a
cluster floats unconnected, redo it.

### MANDATORY layout-quality rules (in addition to the SA Charter below)

The user has flagged these defects with zero tolerance. Apply BEFORE
rendering, then verify after render:

1. **Label NEVER touches its icon.** Use `node_attr["margin"] >= "0.6,0.5"`.
   In the `diagrams` package the icon is the node "shape" and the label
   sits below it; the margin pads the label inside the cell. Insufficient
   margin = "chữ với ảnh icon dính nhau" (the user's literal complaint).
2. **Label NEVER overflows the cluster frame, and NEVER orphans a "(".**
   Wrap EVERY label — node AND cluster — with the canonical helper
   `wrap_label()` from `scripts.diagrams_runtime`. Do NOT hand-insert
   `\n`, and do NOT break at "(": breaking AFTER "(" is exactly what
   produced the "Amazon MSK (" / "Kafka)" defect. `wrap_label` breaks at
   spaces, keeps a short "(...)" group whole on its own line, and never
   ends a line on "(", "/", "+" or "-". A single long line also punches
   through the cluster border (the cluster sizes to its members, not to a
   node's own wide label), so wrapping fixes both. Use it for the cluster
   name too — an unwrapped 32-char `Cluster(name=...)` overflows its own
   header.

   ```python
   from scripts.diagrams_runtime import wrap_label
   EKS(wrap_label("WS gateway + dispatch / location / trip"))
   Cluster(wrap_label("Shared identity / audit / ops"))
   ```
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
5. **Sharpness (must be crisp in Word, never blurry).** `graph_attr["dpi"] = "300"`.
   Because `build_docx.py` embeds every figure at width = 6.5in, the PNG must be
   **≥ 1950 px wide** (= 300 DPI at 6.5in) — not merely ≥ 1500 px on the long side —
   or Word upscales it and it looks soft. Save the PNG with `dpi=(300, 300)` metadata.
   The PRIMARY renderers (`build_cloud` / `build_graph` / `build_sequence`) already
   guarantee this; on this fallback path, raise `dpi` and re-render (or up-render) until
   the width clears 1950 px, then verify via PIL. The self-check blocks `png_soft_for_embed`.

6. **Mandatory self-check — run after rendering ALL diagrams.** This is the
   per-diagram verification gate the user asked for:

   ```bash
   python scripts/diagram_check.py --dir project_dir/output/diagrams \
       --json project_dir/output/diagrams/diagram_check.json
   ```

   For EVERY diagram it checks the PNG (exists, non-empty, long side
   >= 1500px, renders <= 9.0in tall at 6.5in wide) and the `.drawio`
   (well-formed XML, has nodes/edges, no blank boxes, **no label line
   ending on "("**, no over-long single-line label, line breaks preserved
   as `&#10;`). It also promotes `build_cloud`'s layout lint —
   `header_overflow` and `label_overlap` (read from `<slug>.lint.json`) — to
   **blockers**, and warns on a VPC/subnet diagram whose boundaries are flat
   (`flat_boundaries`), a missing/ill-formed caption or intro, and any
   `explanation_bullets` term that names a component absent from the diagram
   (`explanation_orphan`). **Fix every blocker and re-render until it reports
   0 blockers.** Do NOT hand off to Phase 5 with blockers outstanding; treat
   warnings as a strong nudge to shorten/wrap a label.

The agent ALSO re-opens each PNG with PIL to eyeball the densest cluster.
Re-render until the self-check is clean and the crop looks right.

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
- Caption text: write `<Type>: <Scope>` only, for example `Container Diagram: Booking Service`. `build_docx.py` wraps it as `Figure {SEQ}: <Type>: <Scope>` at assemble time so the number stays in sync as more diagrams are added. Use a colon, never a dash.

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
  "techstack_backend":        [ {"name": "...", "logo": "pack/icon", "description": "..."}, ... ],
  "techstack_frontend":       [ {"name": "...", "logo": "pack/icon", "description": "..."}, ... ],
  "techstack_database":       [ {"name": "...", "logo": "pack/icon", "description": "..."}, ... ],
  "techstack_server_hosting": [ {"name": "...", "logo": "pack/icon", "description": "..."}, ... ],
  "techstack_data":           [ {"name": "...", "logo": "pack/icon", "description": "..."}, ... ]  | null,
  "techstack_ai":             [ {"name": "...", "logo": "pack/icon", "description": "..."}, ... ]  | null,
  "mobile_app_strategy": "... | null",
  "case_study_title": "title of a REAL, relevant Saigon Technology case study comparable to this project's domain (a multi-stakeholder platform of similar shape) — sits in body prose, so never null. If no suitable STS reference is known, the user supplies one before sending (the reviewer flags the placeholder if left unfilled).",
  "case_study_url": "public URL of that STS case study, for example 'https://saigontechnology.com/case-studies/<slug>'. Fills the case-study hyperlink target, so never null.",
  "references": "... | null",

  // ---- RFP-driven optional sections (all default to null; see the block below) ----
  // Every one of these has a HARD WORD CEILING. See "OPTIONAL SECTIONS ARE SHORT".
  "security_data_protection": "... | null",
  "team_structure": "... | null",
  "team_roles":     [ {"name": "Role (<count>, <seniority>, <onshore|offshore>)", "description": "one sentence of accountability"}, ... ]  | null,
  "team_engagement_model": "... | null",
  "delivery_roadmap": "... | null",
  "delivery_milestones": "... | null",
  "delivery_governance": "... | null",
  "support_model": "... | null",
  "service_levels": "... | null",
  "assumptions_dependencies": "... | null",
  "risk_register": "... | null",
  "contractual_exceptions": "... | null",

  "summary_body": "..."
}
```

> **TECHSTACK FORMAT — MANDATORY (2-col tables).** Every
> `techstack_*` value MUST be a **JSON array of `{"name", "description"}`
> objects — NOT a prose paragraph.** `build_docx.py` renders each array as a
> styled 2-column **`Technology | Advantages`** table (shaded bold header,
> bordered, ~33%/67% columns) — a clean, professional two-column layout. One row per
> **concrete technology / framework / library / managed service** (e.g.
> "Go 1.23", "ASP.NET Core", "Amazon Aurora PostgreSQL 16", "Amazon EKS",
> "Amazon MSK (Kafka)", "Terraform"), with the `description` giving that
> item's advantage / role in 1-2 sentences. Aim for roughly 5-12 rows per
> sub-section (Back-end is usually the longest). A prose string here is a
> FORMAT DEFECT the reviewer rejects (`techstack_not_table`). Use `null`
> only for `techstack_data` / `techstack_ai` when that tier is out of scope.
>
> **LOGO PER ROW — put a logo on EVERY row.** Each row
> SHOULD carry `"logo": "pack/icon"`; `build_docx` embeds that PNG above the
> bold name in column 1. It resolves to `assets/icons/<pack>/png/<icon>.png`.
> Packs: `aws/` (AWS service icons — e.g. `aws/aurora-instance`,
> `aws/elastic-kubernetes-service-rounded`, `aws/elasticache-for-redis`,
> `aws/managed-streaming-for-kafka`, `aws/simple-queue-service-sqs-message`,
> `aws/simple-storage-service-s3-bucket-with-objects`, `aws/secrets-manager`,
> `aws/cloudwatch-alarm`, `aws/elastic-load-balancing`,
> `aws/cloudfront-download-distribution`, `aws/ec2-container-registry-rounded`);
> `azure/` and `gcp/` (their cloud service icons); `data/` (languages /
> frameworks / libraries / dev tools — e.g. `data/go`, `data/nodejs`,
> `data/nestjs`, `data/react`, `data/flutter`, `data/dart`, `data/typescript`,
> `data/vite`, `data/antdesign`, `data/i18next`, `data/playwright`,
> `data/vitest`, `data/opentelemetry`, `data/postgresql`, `data/redis`,
> `data/apachekafka`, `data/terraform`, `data/githubactions`, `data/docker`,
> `data/kubernetes`, `data/prometheus`, `data/grafana`, `data/dotnetcore`,
> `data/java`, `data/spring`, `data/python`, `data/rust`, `data/vuejs`,
> `data/angular`, `data/svelte`, `data/kotlin`, `data/nginx`, `data/rabbitmq`,
> `data/graphql`, `data/mysql`, `data/mongodb`, `data/swift`, `data/helm`,
> `data/elasticsearch`); `generic/` fallbacks (`generic/mobile-app`,
> `generic/server`). Rules: (1) pick the icon whose name best matches the
> row's primary product; (2) for a library row with no own logo, reuse its
> **ecosystem** logo (e.g. put the .NET logo on every .NET row — likewise
> `data/go` for Go libraries, `data/react` for React-ecosystem rows);
> (3) **confirm the PNG exists in the pack before referencing it** — if a
> needed language/tool logo is missing, run `tools/fetch_tech_logos.mjs`
> (devicon / simpleicons source) to add it BEFORE assembling. Omit `logo`
> only when no sensible icon exists.
>
> **Head-less / web-app runs cannot fetch a missing logo.** An unattended run is
> forbidden from writing into the skill folder, and `tools/fetch_tech_logos.mjs`
> writes into `assets/icons/data/png/`. So in that mode do NOT try to fetch: fall
> back to rule (2) and give the row its ECOSYSTEM logo (FastAPI → `data/python`,
> Next.js → `data/react`, JUnit / Flyway → `data/java`, OpenAPI → the gateway
> icon), then LIST the gap in the Phase 6 report so a human can run the fetch tool
> once and every later run gets the real logo. Never leave `logo` off a row just
> because the exact product has no icon — a row with no logo is the visible defect;
> an ecosystem logo is not.

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

- **Separate paragraphs inside a prose value with ONE newline, never a blank line.**
  `build_docx._expand_paragraph_with_value` does `value.split("\n")`, so a `\n\n` separator yields
  an empty middle element and therefore an **empty `Normal` paragraph** in the document, carrying
  the full space-before and space-after. That is the visible "chỗ thì trống nhiều chỗ thì gần"
  uneven-whitespace defect the user has flagged, and it is invisible in the JSON. One run shipped
  52 of them before anyone traced the cause. The paragraph's own space-after already supplies the
  separation, so `"para one\npara two"` is what you want. On a re-run, normalise `\n{2,}` to `\n`
  across every reused string value.
- No RFP section-number references.
- No phase plans / sprint plans.
- No specific region names unless client stated one.
- Justify alignment for body text.
- **NO em-dashes (` — `) ANYWHERE in the delivered content.** Not in body prose,
  not in bullets, not in captions, not in table cells. A spaced em-dash is one of
  the strongest signals a reader uses to spot machine-written text, and the client
  has rejected it on sight. There is no carve-out: earlier versions of this rule
  allowed em-dashes inside `problems_and_solutions` and `explanation_bullets`, and
  that exception is now withdrawn.
  - Where it separated a bold label from its description, use a colon:
    `**Component**: description`, not `**Component** — description`.
  - Mid-sentence, use a comma or a semicolon, put the aside in parentheses, or
    split it into two sentences. Two shorter sentences almost always read better
    than one sentence hinged on a dash.
- **NO Latin abbreviations: `e.g.`, `i.e.`, `etc.`, `viz.`, `cf.`** These read as
  machine-assembled filler in a client-facing bid. Write the English instead:
  `for example`, `such as`, `that is`, `in other words`. For `etc.`, either finish
  the list or name the category: "and the remaining authority interfaces", not
  "authority interfaces, etc.". If a list is genuinely open-ended, say "including"
  at the start and stop when the list is complete enough.
- Both rules are ENFORCED by `format_reviewer.py` (`em_dash_in_prose`,
  `latin_abbreviation_in_content`) and normalised defensively by `build_docx.py`,
  so a slip is caught rather than shipped. Do not rely on that: write it correctly.
- **Problems & Solutions** — render as bullets following the Phase 2 brief's `1b` section verbatim (don't summarise it down). Each bullet is two sentences: the bold problem name + root-cause + quantified pain; then the solution named by architectural pattern + trade-off + measurable acceptance criterion. Reject vague consultant-speak ("leverage", "best-in-class", "world-class", "robust solution", "seamlessly integrate", "modernise"). The bullet count follows the brief, not a fixed quota.
- Mobile App Strategy: short and decision-only. If mobile is not in scope, set `mobile_app_strategy` to `null` and the build script will skip the section. The same null-drop applies to `techstack_data` and `techstack_ai` — only fill them when the project actually needs a data pipeline / AI layer.
- **`summary_body`** — final wrap-up of the proposal: 3–8 short paragraphs that restate the headline architectural choice, the four commitments (tech depth, delivery confidence, IP / portability, post-go-live ownership), and the service-level targets. Per-project; do not recycle wording from prior bids.
- **`case_study_title`** — the CASE STUDY section body itself is kept verbatim from the template (a single intro paragraph plus a hyperlink to a relevant STS case study). Only the title is per-project — set this to the name of the comparable client / engagement you want referenced. If the template's existing reference is not the best fit for this bid, flag it in the Phase 6 caveats so the user can swap the hyperlink target manually.
### RFP-driven optional sections — fill only what the client actually asked for

The template carries these sections with a `{{KEY}}` slot each. **Every one defaults to
`null` and is REMOVED at build time when null or absent**, so a bid that does not need
a section shows no trace of it. Read the RFP's "required proposal contents" list (an
Appendix C, a submission-format clause, or the evaluation criteria) and fill exactly
the ones it asks for. Filling a section the client never requested is padding.

| Key | Section | Fill it when the RFP asks for |
|---|---|---|
| `security_data_protection` | SECURITY & DATA PROTECTION | a security / data-protection approach as its own narrative (residency, encryption, access control, consent and data-subject rights, secure SDLC) |
| `team_structure` | PROJECT TEAM › Team Structure | the shape of the delivery organisation: squads, how many, what each owns. Opens with the headcount arithmetic |
| `team_roles` | › Roles & Responsibilities | the positions, **how many people in each**, seniority and location. An ARRAY rendered as a `Role \| Accountability` table |
| `team_engagement_model` | › Engagement Model | onshore/offshore split, working hours overlap, how the client interacts with the team |
| `delivery_roadmap` | DELIVERY PLAN & GOVERNANCE › Delivery Roadmap | a phased roadmap or a sequencing proposal |
| `delivery_milestones` | › Milestones & Acceptance | milestones and what acceptance means at each |
| `delivery_governance` | › Governance & Reporting | steering, escalation, change control, reporting cadence |
| `support_model` | SUPPORT & SERVICE LEVELS › Support Model | a run / managed-service phase: coverage, tiers, tooling |
| `service_levels` | › Service Level Targets | availability and severity-based response and resolution targets |
| `assumptions_dependencies` | ASSUMPTIONS, DEPENDENCIES & RISKS › Assumptions & Dependencies | assumptions and what the client must provide |
| `risk_register` | › Key Risks & Mitigations | a risk view; each entry states the risk, its impact and the mitigation already built into the approach |
| `references` | CASE STUDY › References | client references |
| `contractual_exceptions` | CONTRACTUAL EXCEPTIONS | exceptions to the client's contract terms |

### THE CLOUD CHOICE MUST BE JUSTIFIED IN THE DOCUMENT, IN THREE PLACES

A bid names exactly ONE cloud, and it has to say why, where a reader will actually see it.
A rationale that exists only in `plan.json` is invisible to the client, and a stack table
that names a platform without a reason reads as a vendor habit rather than a decision.
State it in all three of these, each time from the requirement rather than from preference:

1. **The hosting row of the technology stack.** The `description` for the cloud and region
   row must name the requirement that forced the choice, the property of this platform that
   satisfies it, and what was rejected. Two or three sentences.
2. **One sentence in the Executive Summary.** An evaluator who reads nothing else must
   still learn which platform and why.
3. **The assumptions register**, stating whether this is a recommendation or a client
   instruction, and what would change if the client has already chosen.

Justify on requirements, never on familiarity. Acceptable reasons are the ones a client can
check: a mandatory residency or sovereignty clause and how the platform satisfies it; the
number of in-country regions and therefore whether recovery can stay inside the border;
whether the required managed services and model inference exist in that region at all;
certification or accreditation the requirements name. **Unacceptable: our team knows it,
we have a partnership, it is the market leader, it is what we usually use.**

If a candidate is rejected, say what it failed rather than that it lost. "No region in
country, so the residency clause cannot be met at all" is a reason; "less suitable" is not.

**Never present a second cloud as an equal alternative.** If a genuine fallback matters to
the client, say what would trigger reconsidering, not that two options are equally good.
Naming two clouds costs the reader confidence and, when the cost model prices only one,
produces a bid that quotes something other than what it recommends.

### THE WHOLE DOCUMENT HAS A LENGTH BUDGET — and the figures are where it is lost

A technical proposal is read by people deciding whether to shortlist you. A document
nobody finishes cannot win, so total length is a quality attribute, not a side effect.

**Budget: 8,000 words of body text.** Measured on the delivered `.docx`. A bid that needs
more must earn it, section by section, in the Phase 6 report.

**Where it actually goes wrong, measured on a real 14,285-word delivery:**

| Block | Words | Share | Verdict |
|---|---:|---:|---|
| Ten figure sections, 19 paragraphs each | 5,662 | **40%** | **the whole problem** |
| Risks, assumptions, contractual exceptions | 1,741 | 12% | keep, this is requirement coverage |
| Technology stack tables | 1,837 | 13% | keep, this is the technical depth |
| Template-verbatim management block | 1,404 | 10% | template, not ours to cut |
| Problems and solutions, team, optional | 1,900 | 13% | already capped |

**So the rule that matters is NOT the bullet COUNT. It is the words per bullet and the
length of the intro.** A measured comparison against a delivered proposal the reader rates
highly settles this:

| | the well-rated delivery | the over-long one | what actually differs |
|---|---:|---:|---|
| figures | 8 | 10 | +2 |
| bullets per figure | 12.6 | 17 | +4 |
| **words per bullet** | **22** | **28** | **+6, and this is the bloat** |
| **intro paragraph** | **56 w** | **78 w** | **+22, and so is this** |
| per figure | 336 w | 554 w | |

Cutting the COUNT was tried and it was the wrong lever: at six bullets a reader can no
longer name the components, and the requirement that the figure be re-drawable from the
bullets alone is lost. **Keep 7 to 17 bullets. Cut the words inside each one, and cut the
intro.** Twelve tight bullets beat six loose ones at the same word budget and say far more.


Cutting length must never cut requirement coverage. If a real requirement can only be
answered at length, answer it and say in the Phase 6 report which budget it broke and why.

### BULLETS, NOT PARAGRAPHS — the fix for "it still reads long"

A section can sit inside its word ceiling and still read as a wall of text. That happened:
sections at 107, 129 and 160 words, with sentences averaging 17 to 23 words, were still
rejected as rambling. **Length was never the problem. The absence of a visual entry point
was.** A reader skimming a bid needs somewhere for the eye to land on every section.

So these sections are **ARRAYS of labelled bullets, not prose strings**:

| Key | Bullets | Words per bullet |
|---|---:|---:|
| `executive_summary` | 1 lead line + 5 to 6 | 30 |
| `security_data_protection` | 5 to 7 | 30 |
| `team_structure` | 4 to 5 | 26 |
| `team_engagement_model` | 3 to 4 | 26 |
| `delivery_roadmap` | 4 to 6 | 28 |
| `delivery_milestones` | 4 to 6 | 28 |
| `delivery_governance` | 4 to 5 | 26 |
| `support_model` | 4 to 6 | 28 |
| `summary_body` | 4 to 5 | 28 |

**Every bullet is `**Label**: one sentence.`** The label is 1 to 4 words naming the thing
decided, and it carries the meaning on its own so a reader who reads only the labels still
learns the answer. `**Residency**: enforced by subscription policy that blocks
provisioning outside the region` works. `**Overview**: this section describes our
approach` is padding and gets deleted.

`executive_summary` is the ONE exception to bullets-only: element 1 is a single plain
sentence stating what the client is buying, then the rest are labelled bullets.

**`purpose` and `mobile_app_strategy` stay prose**, at 2 to 3 sentences each. A three
sentence section does not need bullets.

Rejected constructions, in any of these: a sentence that only announces the section's
topic; a bullet that continues the previous bullet's sentence; two bullets with the same
label; a label longer than four words; a bullet with two sentences where the second only
restates the first.

### THE CLOUD DECISION GOES NEAR THE TOP, AS ITS OWN BULLET

"Why this platform" must be a **labelled bullet inside `executive_summary`**, in the first
three bullets, not a sentence buried in a paragraph. It was buried once: the rationale was
present in paragraph three of five and a reader reported it missing, which for a bid means
it WAS missing. One bullet, the requirement first and the platform second:

`**Cloud**: residency is mandatory and only this platform has two regions in country, so
recovery and model inference never leave it`

The fuller argument still belongs in the hosting row of the technology stack and in the
assumptions register, as set out above. This bullet exists so nobody has to find it.

### WRITE TIGHT — the whole document, with the technical content protected

A bid is read by people deciding whether you understand their problem. Length does not
demonstrate understanding; precision does. Two ceilings apply to the narrative sections,
and a **protected list** says exactly what must NOT be compressed, because cutting
technical substance to hit a word count is the failure this rule exists to prevent.

**Narrative ceilings (hard):**

| Key | Ceiling | Note |
|---|---:|---|
| `problems_and_solutions` | **55 words per pair** | The prompt already said "two sentences" per bullet. Measured, the last run averaged 143 words, so the rule existed and was ignored. 55 words is two real sentences |
| `executive_summary` | 260 | An evaluator reads this and decides whether to keep reading |
| `summary_body` | 200 | It restates; it does not re-argue |
| `purpose` | 150 | Why this engagement exists, not what is in it |
| `mobile_app_strategy` | 160 | The decision and its consequence, nothing else |
| `system_overview_intro` | 300 | Technical, so generous, but still bounded |
| diagram `explanation_bullets` | 30 words per bullet | Keep EVERY bullet; shorten each one |

**Count the words the way the REVIEWER counts them, or you will pass your own check and fail its.**
`format_reviewer` splits on whitespace (`str.split()`) over the text as RENDERED, which differs from
the JSON you authored in three ways that have each cost a run:

1. **A ceiling stated per logical entry can render as more than one paragraph.**
   `build_docx._stringify_value` turns each `problems_and_solutions` pair into TWO paragraphs,
   `● <problem>` and `**Solution:** <solution>`, and `check_narrative_length` measures the LONGEST
   paragraph under the heading. So the reviewer's ceiling is effectively per half while the rule here
   is per PAIR, and the two readings differ by about 2x. Satisfy the strict one: **the pair, both
   halves added together, at most 55 words**, with neither half over about 30. Ten pairs written that
   way came in at 46 to 50 words each and kept the quantified pain and the acceptance criterion in
   every one.
2. **The rendered prefixes are words.** `●` and `Solution:` each count, as does the `● ` the renderer
   prepends to every entry of a list-valued section. Author to about 50 for a 55 ceiling and about 48
   for a 50, rather than measuring to the last word and losing on the glyph.
3. **Nothing enforces the 30-word bullet ceiling, so your own gate has to.** No check in
   `format_reviewer.py` or `diagram_check.py` measures `explanation_bullets`. On one run all four
   diagram agents self-reported "max 30 words" while seven bullets were actually 31 or 32, because
   each had counted with its own rule. Do the counting in the step that MERGES the per-diagram blocks
   into `diagrams.json`, with `len(s.split())`, and refuse to write the file on a breach. Never take
   an agent's self-reported count as the measurement.

**PROTECTED — never compress these to save words:**
- **`techstack_*` table rows.** One row per real technology with its advantage in one or
  two sentences. This is where technical depth is demonstrated, and the table format
  already makes it scannable. Do not merge rows, do not drop rows, do not shorten a
  description to a fragment that no longer says why the choice was made.
- **`system_overview_intro` and every diagram's `intro_paragraph` and
  `explanation_bullets`.** The figures plus their explanation are the architecture
  argument. Shorten individual sentences, never remove a component's bullet.
- **The technical substance of `security_data_protection`.** The residency mechanism, the
  encryption and key-custody model, the access model and the secure development lifecycle
  each have to remain identifiable. Cut the sentences that restate the requirement, not
  the ones that state the control.
- **`risk_register`, `assumptions_dependencies`, `service_levels`,
  `contractual_exceptions`.** These are per-entry capped at 50 words and the LIST may be
  as long as the requirements demand. Never drop an entry to shorten a section.

**Sentence discipline, applied everywhere including the protected sections:**
1. One idea per sentence. Average under 25 words. A sentence over 40 words is two
   sentences that have not been separated yet.
2. Lead with the decision, then the reason. "The estate runs in one region, because
   residency is mandatory" beats "Because residency is mandatory, and after considering
   the alternatives, we propose that the estate should run in one region".
3. Delete every sentence that restates the requirement before answering it. The client
   wrote the requirement.
4. Delete adjectives that carry no decision: robust, comprehensive, world-class, seamless,
   best-practice, cutting-edge, holistic, leverage, synergy.
5. Prefer the concrete noun over the description of it. "Subscription-level policy that
   blocks out-of-region provisioning" beats "a mechanism that prevents resources from
   being created outside the approved region".
6. No sentence whose only content is that a later section exists.

**Never pad to reach a ceiling.** A section at half its ceiling that answers the question
is better than one at the ceiling that also answers it.

### OPTIONAL SECTIONS ARE SHORT — hard word ceilings

A bid reader skims these sections looking for a number, a name or a commitment. Long
prose hides all three. Every optional section has a **hard word ceiling**, and going
over it is a defect the reviewer rejects (`optional_section_too_long`), not a style
preference. Answer the question, state the commitment, stop.

| Key | Ceiling | What earns the words |
|---|---:|---|
| `security_data_protection` | 260 | the residency mechanism, encryption and key custody, access model, data-subject rights, secure SDLC. One short paragraph each, no restating the requirement back |
| `team_structure` | 150 | the squad shape and the headcount arithmetic (see below) |
| `team_roles` | table | an array, one row per position, no prose |
| `team_engagement_model` | 110 | onshore/offshore split, hours overlap, how the client interacts |
| `delivery_roadmap` | 180 | the sequence and what gates each transition |
| `delivery_milestones` | 160 | the milestone set and what acceptance means |
| `delivery_governance` | 130 | forums, cadence, escalation, change control |
| `support_model` | 160 | coverage, tiers, tooling, reporting |

List-valued sections (`service_levels`, `assumptions_dependencies`, `risk_register`,
`contractual_exceptions`, `references`) are capped per ENTRY at **50 words**, not in
total, so the list can be as long as the RFP requires while each line stays scannable.
(Fifty, not forty-five: at forty-five the gate fired on entries one word over, and a
check that cries wolf gets ignored, which is worse than not having it.)

**How to cut without losing substance**, in the order to try:
1. Delete every sentence that restates the requirement before answering it. The client
   wrote the requirement; they do not need it read back.
2. Delete adjectives that carry no decision. "robust", "comprehensive", "world-class",
   "seamless", "best-practice" never survive.
3. Replace a sentence of explanation with the concrete noun. "a mechanism that prevents
   resources being created outside the approved region" becomes "subscription-level
   policy that blocks out-of-region provisioning".
4. Merge two sentences that share a subject.
5. Only then drop content, and if you drop something the RFP asked for, say so in the
   Phase 6 caveats.

**Never pad to reach a ceiling.** A 90-word section that answers the question is better
than a 180-word one that also answers it.

### Team section: name the positions and the headcount

**`team_roles` MUST be a JSON array of `{"name", "description"}` objects**, which
`build_docx.py` renders as a `Role | Accountability` table (same borders and shaded
header as the technology tables, wider first column). A prose string here is a format
defect. The `name` field carries the **position, the number of people, the seniority and
the location** in this exact shape:

```
"Backend Engineer (6, 2 senior + 4 mid, offshore)"
"Solution Architect (1, principal, offshore)"
"Engagement Lead (1, director, onshore)"
```

`description` is **one sentence** of what that role is accountable for. One row per
position, not per person.

**`team_structure` opens with the headcount arithmetic, in numbers.** State the peak
and average team size and show how it follows from the estimate, so the number is
defensible instead of asserted:

> total estimated effort ÷ proposed delivery months ÷ productive hours per person-month
> (use 130 productive hours, which allows for leave, ceremonies and context switching)
> = average concurrent engineers, then state the peak and when it occurs.

If an effort estimate is available in the inputs (a work breakdown, an hours total),
you MUST derive the headcount from it and say which figure you used. If none is
available, say the team shape is sized at kickoff against the agreed estimate and give
the squad structure without inventing a number.

**Hard rule: describe positions, never invent people.** Headcount, seniority band and
location are a staffing proposal and belong here. A person's **name, CV, years of
experience, certification or photograph** is a fact about a real human and must never be
invented. Named personnel come from the bid owner's staff records, and the RFP usually
wants them as an annex rather than in the technical narrative. If the RFP demands named
CVs, give the position table here and flag in the Phase 6 caveats that the named CVs
must be attached before sending.

The same restraint applies to `references` (never invent a client name or a contact) and
to `contractual_exceptions` (a legal position is the bid owner's to state, not yours: if
you have no instruction, leave it null rather than inventing a stance). For
`delivery_milestones` and `delivery_roadmap`, do not invent dates or durations that no
input supports; describe the SEQUENCE and what gates each transition, and say that the
calendar is set at kickoff.

- **`diagram_captions`**: write each value as the FIGURE TITLE ONLY, for example `"Container Diagram: Booking Service"` (no `"Figure 3: "` prefix). `build_docx.py` wraps it with a Word SEQ field so the figure number is computed by Word automatically when the file opens. This keeps Section 2 diagrams (Figures 1–N, per project) and Section 3's verbatim diagrams (Figures N+1 onwards) renumbered correctly no matter how many diagrams a given project has. Match the diagram slugs you set in `diagrams.json` for `target_heading` so the caption attaches to the right image.

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

## Before the long build: check the stack against the architecture

```
python scripts/check_consistency.py --plan spec/plan.json
```

A cloud mismatch between the stack and the figures costs a whole regeneration if it
is found afterwards, and this finds it in a second. Run it once the plan is settled
and again with `--diagrams` as soon as the figure specs exist, rather than waiting
for the format review.
