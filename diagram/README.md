# Diagram-WorkFlow

A reusable Claude Code skill — **`/linhpham-diagram`** — that turns a plain-language description of a
diagram into a professional, senior-SA-grade diagram: a sharp (>= 300 DPI) PNG plus an editable
`.drawio`. The user describes what they want in ordinary words (often vague); the skill **reviews and
rewrites** that into a rigorous, standards-based spec — classifying the diagram type, suggesting the
best-fitting options for the user to choose, and filling in the correct notation — before drawing.

```
/linhpham-diagram <free-text description of the diagram you want>
```

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
| Cloud/infra reference architecture, K8s, Docker, on-prem, deployment | mingrammer `diagrams` (vendor icons) + Graphviz | authored Python script |
| Structural / process / hierarchy / data / DevOps (flowchart, C4, microservices, ERD, DFD, state, class, org chart, mind map, network, CI-CD, business context, …) | Graphviz `dot`/`twopi`/`neato`/`circo` from a JSON spec | `scripts/build_graph.py` |
| Sequence / interaction | PIL lifeline renderer from a JSON spec | `scripts/build_sequence.py` |

All output is >= 300 DPI PNG + (where supported) an editable `.drawio` that matches the PNG, plus a
`diagrams.json` sidecar (caption + intro + explanation bullets).

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
first use (Windows auto-download; macOS/Linux prints the one-line `brew`/`apt` command). Node is only
needed if logo-fetch tooling is added later.
