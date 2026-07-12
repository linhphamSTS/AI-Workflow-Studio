# scripts/

Rendering engine for the `linhpham-diagram` skill. All produce sharp (>= 300 DPI) output.

| Script | Role |
|---|---|
| `diagrams_runtime.py` | `bootstrap()` — ensures the `diagrams` (mingrammer) package + its bundled vendor icons + a portable Graphviz are installed (self-healing, no manual steps). `wrap_label()` — the canonical label wrapper (breaks BEFORE `(`, never orphans `(`/`/`/`+`/`-`). Use in EVERY renderer path. |
| `build_graph.py` | **General-purpose Graphviz renderer** from a JSON spec → PNG + `.drawio`. Covers flowchart, workflow, BPMN-lite, state machine, decision tree, ERD, DFD, data pipeline, C4, microservices, class/component/package, org chart, mind map, network, business context, DevOps/CI-CD. Node `role`/`type` → shape; edge `kind` → line/arrow style; engines dot/twopi/neato/circo. |
| `build_sequence.py` | **UML sequence renderer** (PIL lifelines) from a JSON spec → PNG. Participants, dashed lifelines, sync/async/return/self messages, alt/opt/loop fragments. No `.drawio`. |
| `drawio_export.py` | Emits an editable `.drawio` laid out with Graphviz so it MATCHES the PNG. Carries AWS/Azure/GCP/K8s vendor stencils via `SHAPE_STYLES`. Used by `build_graph.py` and the mingrammer path. |
| `diagram_check.py` | Per-diagram self-check gate: PNG sharpness/aspect (fits one Word page), `.drawio` well-formed, no blank boxes, no dangling `(`, line breaks preserved, nested boundaries for VPC/subnet diagrams, stale-caption detection, diagrams.json block completeness. Exit 0 = clean. |
| `svg_util.py` | `inline_images()` — base64-inlines external icon references into a Graphviz/mingrammer SVG so it is self-contained (portable + opens with icons intact in draw.io). `png_to_drawio()` — wraps any PNG as an editable draw.io image cell (so icon/sequence diagrams also ship a `.drawio`). `build_graph.py` emits an SVG automatically; the mingrammer path calls both. |
| `build_cloud.py` | **Pixel-perfect MANUAL-GRID cloud/infra renderer (PIL).** Places tiers as columns, wraps them in VPC/VNet boundaries, draws orthogonal connectors + a bottom shared band by hand — brochure-grade, beyond what Graphviz auto-layout can do. Composites clean vendor icons from the mingrammer bundled PNGs (`provider/stem`). Driven by a spec (`build_cloud.render(spec, out)`). **Also emits a NATIVE, fully editable `.drawio`** (every icon a draggable image cell, every boundary a rectangle, every edge an orthogonal connector — not an image capture). |
| `cloud_specs.py` | The 6 canonical cloud/infra SPECS (AWS/Azure/GCP/on-prem/K8s/Docker) for `build_cloud`. Phase 3 copies the closest and adapts labels/tech. `SPECS` = slug→spec. |
| `diagram_templates.py` | **The canonical CLEAN-LAYOUT builders for cloud/infra/tech diagrams** (aws/azure/gcp ref-arch, k8s, docker, on-prem hybrid, CI/CD, GitOps, data pipeline, microservices, C4 container, deployment, AI-RAG). Each encodes the anti-spaghetti rules from `reference/kb_diagram_layout.md` (splines=ortho, one spine, shared-services as an edgeless band + one anchor edge, nested shrink-wrapped boundaries, real icons). Phase 3 COPIES the closest builder and adapts labels — it does NOT freehand. `TEMPLATES` = slug→builder; runnable standalone (`--name aws_ref --out DIR`). The samples are rendered from these, so samples == skill output. |
| `build_diagram.py` | PIL JSON-spec renderer — offline fallback when Graphviz can't be installed. Less polished. |
| `readers/` | Kept from the parent engine (unused by this skill's core paths). |

Icons live in `../assets/icons/` (aws, azure, gcp, k8s/container, network, data, generic, ai).
