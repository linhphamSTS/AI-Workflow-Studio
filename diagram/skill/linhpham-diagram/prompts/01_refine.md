# Phase 1 — Refine (the heart of this skill)

Turn the user's loose description into a rigorous, standards-based **diagram spec**. Three steps:
classify → suggest & confirm the TYPE → rewrite to a full spec.

## Step 0 — FOLDER MODE only: propose the SET of diagrams (skip in TEXT MODE)

If Phase 0 ingested a folder (you read `_ingest_digest.md`), the deliverable is usually **several**
diagrams, not one — mirror how the technical-proposal skill derives a diagram set from an RFP:

1. **Analyse the digest** for what the material actually describes: the system + its actors and
   external systems (→ System Context), its cloud/infra and named tech (→ Cloud Reference Architecture
   on the right provider), its services/bounded contexts and datastores (→ Microservices), its data
   model (→ ERD), its key money/latency/auth flows (→ Sequences), its delivery setup (→ CI/CD), and any
   compliance/security emphasis (→ Security view). Use `reference/kb_house_style_catalog.md`'s
   suggestion catalog. Derive everything from THIS folder — never assume a diagram the docs don't
   support, never copy another project's set.
2. **Propose the fitting set** with `AskUserQuestion` (multiSelect): list the 3–7 diagrams the material
   justifies, each with a one-line "why this one, from the docs" reason; recommend a sensible default
   subset. Let the user add/drop. Do NOT silently draw all of them.
3. For **each chosen diagram**, run Steps 1–3 below (classify is usually already known from the
   analysis; still author a rigorous per-diagram spec grounded in the digest). Give each its own slug
   and a `diagrams.json` entry whose `intro_paragraph`/bullets EXPLAIN the design from the documents
   (see Phase 3's rule) — two diagrams from the same folder must read as distinct explanations.

Then proceed through Steps 1–3 per diagram. In TEXT MODE, skip Step 0 and start at Step 1.

## Step 1 — Classify

Using `reference/diagram_types.md` (the "Classification hints" section) plus `LESSONS_LEARNED.md`,
map the request to the 1–3 diagram types that fit best. For each candidate note the category and
renderer. Resolve obvious signals yourself (e.g. "login flow between app and OAuth" → Sequence;
"our AWS backend" → AWS Reference Architecture) — do not ask when a signal is clear.

## Step 2 — Suggest the type and let the user pick (ALWAYS confirm the type)

Per the standing rule, the user's natural description may be unclear, so **suggest the fitting
type(s) and let the user choose** — never silently commit to a type. Use the `AskUserQuestion` tool:

- If **one** type clearly fits: still confirm it, and offer the 1–2 next-best alternatives so the
  user can redirect. Mark the recommended one "(Recommended)".
- If **several** fit: present them as options, each with a one-line "best when ..." reason.
- In the SAME round, also ask any **missing detail that materially changes the drawing**, e.g.:
  - which **cloud** (AWS / Azure / GCP / on-prem) for an architecture diagram,
  - **level of detail** (high-level context vs detailed),
  - **orientation** only if the user cares (otherwise auto: TB layered / LR flow),
  - the **specific scenario** for a sequence (happy path only, or with error/alt branches).

Keep it to ≤4 questions. Do not ask about things you can sensibly default (per the KB).

## Step 3 — Rewrite into a rigorous spec

Now READ the relevant `reference/kb_*.md` for the chosen type and author the spec with the CORRECT
notation for that type. This is where a vague request becomes a professional diagram:

- Expand the user's description into the real elements the diagram needs (nodes, actors, boundaries,
  data stores, edges with labels/protocols), following that type's convention (e.g. flowchart ISO
  shapes; ERD crow's-foot; C4 boundaries; microservices DB-per-service + sync/async; cloud nested
  VPC/VNet + edge-outside + legend + colour hierarchy; sequence lifelines + fragments).
- Apply the house style from `kb_house_style_catalog.md`: caption `<Type> — <Scope>`, legend for
  sync/async, `[PII]`/`[PCI]`/`[SoR]` tags where relevant, `**Component**: description` bullets
  (a colon after the bold label, never a dash: a spaced em-dash reads as machine-written and is
  rejected on sight, and the same applies to `e.g.` / `i.e.` / `etc.` anywhere in delivered text).
- Fill sensible, domain-plausible detail the user omitted, but **do not invent specifics that would
  mislead** (exact instance counts, made-up service names) — keep them generic or labelled as
  assumptions, and list assumptions in the brief.

**Produce two artefacts:**

1. A short human **diagram brief** (for the Phase-2 gate): chosen type + renderer, one-line purpose,
   the element list, orientation, any assumptions, and the planned caption.
2. The **machine spec**, matching the renderer:
   - **graphviz** (`build_graph.py`): a JSON spec — `{slug, title, category, diagram_type, engine,
     direction, nodes:[{id,label,role|type,...}], edges:[{from,to,label,kind}], clusters:[...]}`.
     Roles drive shapes (start/end/process/decision/io/datastore/state/actor/...); `type:"entity"`
     for ERD (with `attributes`), `type:"class"` for UML (with `fields`/`methods`). Edge `kind`
     covers sync/async/inheritance/composition/aggregation/dependency.
   - **sequence** (`build_sequence.py`): `{slug, title, diagram_type:"sequence", participants:
     [{id,label,role}], messages:[{from,to,label,kind}], fragments:[{type,label,from,to}]}`.
     kind = sync|async|return|self.
   - **mingrammer** (cloud/infra): describe the node/edge/cluster structure (which vendor icons,
     the nested boundaries, the legend) — the actual Python is written in Phase 3 per its SA rules.

Save the machine spec to `output/diagrams/<slug>.spec.json` (graphviz/sequence) so Phase 3 can run it.

Proceed to Phase 2 (Confirm).
