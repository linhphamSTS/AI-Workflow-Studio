# Diagram — `/linhpham-diagram`

A reusable Claude Code skill that turns a plain-language description of a diagram into a
professional, senior-SA-grade diagram: a sharp (>= 300 DPI) PNG, an editable `.drawio` that matches
it, and a per-diagram `.docx` in the proposal figure-block format. The user describes what they want
in ordinary words (often vague); the skill **reviews and rewrites** that into a rigorous,
standards-based spec — classifying the diagram type, suggesting the best-fitting options for the
user to choose, and filling in the correct notation — before drawing.

This skill lives inside the [AI Workflow Studio](../README.md) monorepo, alongside sibling skills
such as `/linhpham-technicalproposal` and `/linhpham-wbs`, and a shared web app that drives them.

**Two input modes**, detected from what you pass:

```
/linhpham-diagram <free-text description>    # TEXT MODE   -> one diagram
/linhpham-diagram <path to a docs folder>    # FOLDER MODE -> a fitting SET of diagrams
```

FOLDER MODE ingests the folder (`.docx` / `.xlsx` / `.pdf` / `.md` / text) into one digest, analyses
it, and proposes the diagram set the documents actually call for — system context, cloud
architecture, microservices, ERD, sequences, CI/CD, security — each justified from the source, for
the user to pick from before anything is drawn.

## Why

Users don't think in "diagram types" — they say "show how an order flows through payment" or "our
AWS setup". This skill's value is the **prompt-refinement layer**: it maps loose language to the
right diagram type + notation (flowchart / sequence / ERD / C4 / microservices / cloud reference
architecture / K8s / DevOps / BPMN / state / class / org chart / mind map / data pipeline / …),
confirms with the user, then renders it to the STS house style.

## Workflow

```
0 Intake → 1 Refine (classify + suggest + rewrite to spec) → 2 Confirm gate
        → 3 Generate (right engine) → 4 Self-check → 5 Deliver + self-learn
```

Phase prompts live in `skill/linhpham-diagram/prompts/00..05`.

## Renderers

| Family | Engine | Script |
|---|---|---|
| Cloud/infra reference architecture, K8s, Docker, on-prem, deployment | **manual-grid PIL renderer** with real vendor icons, driven by a JSON spec | `scripts/build_cloud.py` (specs in `scripts/cloud_specs.py`) |
| Structural / process / hierarchy / data / DevOps (flowchart, C4, microservices, ERD, DFD, state, class, org chart, mind map, network, CI-CD, business context, …) | Graphviz `dot`/`twopi`/`neato`/`circo` from a JSON spec | `scripts/build_graph.py` |
| Sequence / interaction | PIL lifeline renderer from a JSON spec | `scripts/build_sequence.py` |

**Why the cloud family is hand-laid rather than auto-laid.** Auto-layout produced curvy-spaghetti
edges, spider-web shared services and half-empty boundary boxes, so `build_cloud` places tiers as
columns, spans boundary boxes across them, and routes connectors orthogonally by hand. Tier-crossing
edges route around the columns through a clear bus lane instead of straight through the middle, and
a render-time layout lint measures every label, header and icon box with the real fonts and fails
the render on an overlap, a clipped label or a truncated one. `scripts/diagram_templates.py` keeps
canonical specs per cloud slug, all of which call `build_cloud.render`.

All output is >= 300 DPI PNG at the 6.5in Word embed width, plus an editable `.drawio` that matches
the PNG structurally (native stencils, real edges — never a flat screenshot), a `.svg` twin where
the engine emits one, a per-diagram `.docx`, and a `diagrams.json` sidecar (caption + intro +
explanation bullets).

## Knowledge base (`skill/linhpham-diagram/reference/`)

Built from web research of authoritative sources (AWS/Azure/GCP architecture centres, Kubernetes,
Docker, C4, microservices.io, UML, ISO 5807, BPMN) and from the diagrams STS has already shipped:

- `diagram_types.md` — master taxonomy + classification hints (what the Refine phase reads first).
- `kb_cloud_refarch.md` — AWS/Azure/GCP reference-architecture conventions + verified mingrammer paths.
- `kb_infra_container_onprem.md` — Kubernetes, Docker, on-prem/hybrid, CI/CD & GitOps.
- `kb_architecture_software.md` — C4, microservices, event-driven, UML, layered/hexagonal/clean.
- `kb_data_process.md` — ERD, DFD, pipeline/lineage, flowchart, BPMN, swimlane, state, sequence, org chart, mind map.
- `kb_house_style_catalog.md` — STS house style + a suggestion catalog of the diagram types STS ships.

## Self-learning

`skill/linhpham-diagram/LESSONS_LEARNED.md` is read at Phase 0 and appended at Phase 5 after **every**
run. General lessons are promoted into the KB / scripts / prompts so mistakes can't recur — the skill
improves each run.

## Deploy

```
deploy.bat          # Windows
./deploy.command    # macOS
./deploy.sh         # Linux
```

Creates a junction/symlink from every Claude profile's `skills/linhpham-diagram/` to this repo's
`skill/linhpham-diagram/`. Edit in the repo → reflected in every profile immediately (no re-deploy).

## Requirements

Python 3.10+ with Pillow. `bootstrap()` auto-installs the `diagrams` package + a portable Graphviz on
first use (Windows auto-download; macOS/Linux prints the one-line `brew`/`apt` command). FOLDER MODE
additionally reads `.docx` with `python-docx`, `.xlsx` with `openpyxl` and `.pdf` with PyMuPDF; a
legacy `.doc` is not supported.

Node is needed only to **re-fetch icons**, not to render: `skill/linhpham-diagram/tools/fetch_ai_logos.mjs`
pulls the AI/LLM logo pack. The PNGs it produces are committed, so a fresh clone renders without Node.
