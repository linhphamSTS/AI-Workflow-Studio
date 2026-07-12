---
name: linhpham-diagram
description: |
  Turn a natural-language description of a diagram into a professional, senior-SA-grade
  diagram (sharp >= 300 DPI PNG + an editable .drawio). The user describes what they want in
  plain words (often vague); the skill REVIEWS and REWRITES that into a rigorous, standards-based
  diagram spec — classifying the diagram type, suggesting the most fitting options for the user to
  pick, and filling in the correct notation for that type (flowchart / sequence / ERD / C4 /
  microservices / cloud reference architecture / K8s / DevOps / BPMN / state / class / org chart /
  mind map / network / data pipeline / business context, and more). It confirms the normalized spec
  with the user at a gate, then renders with the right engine (mingrammer `diagrams` for cloud/infra,
  Graphviz for structural/process/hierarchy, a PIL lifeline renderer for sequence), self-checks the
  output, and delivers. A knowledge base of diagram conventions lives in `reference/`.
  Also supports FOLDER MODE: point it at a folder of project docs (.txt/.md/.docx/.pdf/.xlsx/…) and it
  ingests + analyses them, then proposes and generates the fitting SET of diagrams — like the
  technical-proposal skill starting from an RFP.
  Trigger when the user types: /linhpham-diagram <description of the diagram, OR a folder of project docs>
---

# linhpham-diagram

Produce one professional diagram from a plain-language request. The value is the **prompt-refinement
layer**: users describe diagrams loosely — this skill turns that into a correct, standards-based spec
before drawing, so the output looks like a Solution Architect made it, not a tool.

```
0 Intake  ->  1 Refine (classify + suggest + rewrite to spec)  ->  2 Confirm gate
          ->  3 Generate (route to the right renderer)  ->  4 Self-check  ->  5 Deliver
```

## How it is invoked

```
/linhpham-diagram <free-text description>          # TEXT MODE — one diagram
/linhpham-diagram <path to a folder of docs>       # FOLDER MODE — a set of diagrams
```

**TEXT MODE** e.g. `/linhpham-diagram how an order flows from the app through payment to the
warehouse`, `/linhpham-diagram our AWS setup for the ride-hailing backend`,
`/linhpham-diagram the login sequence with the OAuth provider`.

**FOLDER MODE** e.g. `/linhpham-diagram C:\Projects\MyBid` or "phân tích folder tài liệu này rồi vẽ
các diagram phù hợp". Phase 0 runs `scripts/ingest.py` to extract text from every
`.txt/.md/.csv/.json/.yaml/.docx/.xlsx/.pdf` in the folder into one digest; Phase 1 analyses it and
proposes the SET of diagrams the material justifies (System Context, Cloud Architecture, Microservices,
ERD, key Sequences, CI/CD, Security …) for you to pick from — then generates each. Everything is
derived from THIS folder's documents; nothing is templated from another project.

## Phase prompts

| Phase | File | Purpose |
|---|---|---|
| 0 | `prompts/00_intake.md` | Capture the request (text) OR ingest a project folder (`scripts/ingest.py`); load lessons + the KB |
| 1 | `prompts/01_refine.md` | Classify the request, suggest fitting diagram types, rewrite to a rigorous spec |
| 2 | `prompts/02_confirm.md` | Human-in-the-loop gate on the normalized spec |
| 3 | `prompts/03_generate.md` | Render with the right engine (mingrammer / Graphviz / PIL sequence) + emit `.drawio` |
| 4 | `prompts/04_selfcheck.md` | `diagram_check.py` + visual verification + fix loop |
| 5 | `prompts/05_deliver.md` | Deliver files, caveats, and append a lesson |

## Renderer routing (decided in Phase 1, executed in Phase 3)

| Family | Renderer | Script |
|---|---|---|
| Cloud/infra reference architecture, K8s topology, Docker, on-prem/hybrid, deployment | mingrammer `diagrams` (vendor icons) + Graphviz | author a Python script (see `03_generate.md`) |
| System context, C4, microservices, event-driven, class/component/package, ERD, DFD, data pipeline, flowchart, workflow, BPMN-lite, swimlane, state machine, decision tree, org chart, mind map, network, business context, DevOps/CI-CD | Graphviz `dot`/`twopi`/`neato`/`circo` from a JSON spec | `scripts/build_graph.py` |
| Sequence / interaction | PIL lifeline renderer from a JSON spec | `scripts/build_sequence.py` |

## Knowledge base (read in Phase 0/1)

`reference/diagram_types.md` (master taxonomy + when-to-use), `reference/kb_diagram_layout.md`
(clean-layout rulebook — ORTHOGONAL edges, shared-services-as-band not spider-web, tight boxes),
plus per-domain convention files:
`kb_cloud_refarch.md`, `kb_infra_container_onprem.md`, `kb_architecture_software.md`,
`kb_data_process.md`, `kb_house_style_catalog.md` (house style + suggestion catalog).

## Output

`output/diagrams/<slug>.png` (>= 300 DPI), a vector `output/diagrams/<slug>.svg` (same engine →
pixel-faithful to the PNG, sharp, and editable in draw.io), and — where supported —
`output/diagrams/<slug>.drawio`, plus a `diagrams.json` metadata sidecar (caption + intro +
explanation bullets) mirroring a professional proposal convention. Fidelity note: the SVG is the
high-fidelity editable twin; a native `.drawio` is a structural (not pixel) copy of the PNG. By default outputs land in the current working directory's `output/diagrams/`;
the user can name another location.

## Source

Developed in `Diagram-WorkFlow`. Run `deploy.bat` (Windows) / `deploy.command` (macOS) /
`deploy.sh` (Linux) from the repo root to install/update the skill into every Claude profile
on this machine via a junction/symlink (edit in repo -> reflected everywhere, no re-deploy).
