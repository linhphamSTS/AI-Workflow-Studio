# Knowledge Base — Clean LAYOUT for architecture diagrams (avoid the "auto-generated" look)

> The #1 quality problem in generated cloud/infra diagrams is **curvy-arrow spaghetti** + **big empty
> boxes**. Root cause is almost never routing — it is **too many edges** and **loose containers**.
> Cut edges + tighten containers and 80% of the mess disappears. Distilled from AWS/Azure/GCP
> architecture-center conventions, the k8s diagram guide, and SA style guides.

## The 6 non-negotiable layout rules
1. **Orthogonal edges, never curves.** `splines=ortho` (fallback `polyline` if labels drop). Curved/organic splines are the amateur tell. (In this skill's mingrammer samples, `graph_attr splines="ortho"`.)
2. **One dominant flow direction, no backtracking.** LR for request/traffic + pipelines; TB for hierarchy (control-plane over workers, trust zones). Every primary edge goes the same way. Cap **1–2 flows** per diagram — a single clean spine (e.g. `users → edge → LB → compute → data`). If you need more, split the diagram.
3. **Shared / cross-cutting services = a panel, NOT edges.** IAM/KMS/Secrets/monitoring/logging connect to "everything", so draw them with **0–1 edges**: a labelled band/sidebar whose *position* implies scope. NEVER draw a dashed edge from compute to each of IAM/KMS/CloudWatch/Secrets (that IS the spider web). "If it connects to everything, connect it to nothing." Make the band compact with an invisible chain (`a >> Edge(style="invis") >> b >> ...`) so icons line up horizontally instead of a tall column.
4. **Boxes shrink-wrap to contents.** Graphviz clusters auto-shrink; the empty-box look comes from long edges forcing rank separation — fix with fewer edges, `nodesep`/`ranksep` tightened (0.4–0.6 / 0.6–0.9), and `rank=same` to pack a tier onto one row. Drop any boundary that adds no info (a serverless app may need no VPC box).
5. **Containment replaces edges.** A resource inside subnet-inside-AZ-inside-VPC shows the whole network path with ZERO connectors. Nest strictly (`Region > VPC > AZ > Subnet > Resource`); every resource lives inside its correct boundary (a floating resource "tells nothing").
6. **Strict grid / alignment + numbered flow.** Uniform icon size, aligned tiers (bands), even gaps. For >3-step flows use numbered ①②③ markers keyed to a caption list instead of many labelled arrows.

## Multi-AZ / redundancy
Identical **side-by-side lanes** inside the VPC, each with the same duplicated resources; a load balancer above fans to each; Multi-AZ DB = primary in lane 1 + standby/replica in lane 2 with ONE labelled "replication" arrow. Duplicate horizontally, never stack vertically.

## Kubernetes
Control-plane band (apiserver+etcd) above/left of the worker band; nest `Cluster > Namespace > Deployment > Pods`. Fleets = one representative + `×N` badge or a small grid, NOT N boxes with N arrows — connect the **group box**, not each pod. Attached resources (ConfigMap/Secret/HPA/PVC) side-attach with **short dashed** connectors, anchored on a consistent side; HPA is a side-badge with a dashed "scales" arrow, not inline in the request path.

## On-prem
Stacked trust bands top→bottom `Internet → [Perimeter FW] → DMZ → [Internal FW] → App/LAN → Data`; firewalls drawn AS the boundary between bands; all cross-zone traffic passes through the firewall (one trunk per zone transition). Colour by trust level.

## Docker Compose
Group by **network** (one box/band per network); traffic tier top→bottom (reverse proxy → app → data); volumes attach below/beside their service as a distinct stateful shape; label ports/protocol; mark host-exposed ports at the top edge.

## Graphviz settings that reproduce the clean look
`splines=ortho` · `rankdir=LR|TB` (one axis) · `nodesep=0.4–0.6` `ranksep=0.6–0.9` (tight, even) · `newrank=true` + `rank=same` for tier bands · nested `subgraph cluster_*` per boundary (shrink-wrap) · `compound=true` + `lhead`/`ltail` to draw ONE edge to a cluster boundary instead of many to its children · invisible edges (`style=invis`) to align/pack a disconnected panel · **delete edges before rendering** (shared-services → band, multi-step → numbered). Manual grid coords (PIL/fixed pos) only needed for pixel-perfect multi-AZ mirror lanes.

## Tier-crossing (skip) edges — route AROUND, never through
An edge whose endpoints are **≥2 columns apart** (e.g. `eks → msk` over the data tier) must NOT run straight across at node height — its horizontal legs graze the icons of every column it flies over. Route it AROUND: exit through the source-side gutter, drop to a clear **horizontal bus lane** below the column boxes (kept inside the surrounding VPC/VNet wrap), traverse, then rise through the target-side gutter into the target. Give each skip edge its **own lane** (stack them) and a small **gutter stagger** so parallel skips never overlap. This is automatic in the manual-grid renderer (`build_cloud._route_skip`); adjacent/same-column edges keep the direct ortho route. Backward skips (right→left, e.g. Argo CD → config repo) route the same way along the bottom — exactly how real GitOps pull/reconcile is drawn.

## Text fit & label placement — no overflow, no overlap
A boundary/subnet **header must sit inside its box** — never let the title cross the box edge. In the
manual-grid renderer (`build_cloud`) the fix is automatic: the column **widens** to fit its header on
one line (up to a cap), and past the cap the header **wraps** and the header zone grows. An **edge
label must never land on a node label**: a *same-column* (stacked) edge (e.g. Aurora primary →
replica "replication") runs at the node centre, so its label goes in the **clear side gutter** past
the cell + box padding, not on the centred node label. Adjacent/skip edge labels only need a small
nudge off the line (they already sit in a gutter). Both are enforced by the renderer's layout lint
(`header_overflow` / `label_overlap` → `<slug>.lint.json` → a `diagram_check` blocker).

## Auto-generated vs professional — the tells
| Amateur | Professional |
|---|---|
| Curvy/diagonal splines, many crossings | Orthogonal, one flow axis, few crossings |
| Skip edge cuts straight across an intervening tier's icons | Tier-crossing edge routes around via a clear gutter + bus lane |
| Header text spills past the box border | Box widened (or header wrapped) so the title fits inside |
| Edge label printed on top of a node's label | Edge label offset into the clear gutter, clear of all text |
| Dashed edge from compute to every shared service | Shared services = band/badge, 0–1 edges |
| Large boundary box mostly empty | Box shrink-wrapped to contents |
| Icons at irregular positions, uneven gaps | Strict grid, aligned tiers, even gaps |
| Every relationship its own labelled arrow | Few flows; numbered steps carry detail |
| N boxes for N replicas | One representative + ×N |
| Resource floating outside any boundary | Every resource nested in its container |
| Bidirectional `<->` arrows | Single-ended client→server arrows |
