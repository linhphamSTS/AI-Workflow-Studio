# Technical Proposal — ANALYZE (head-less, stop at the confirm gate)

You drive the **`/linhpham-technicalproposal`** skill head-less for the web app. Run its
**Phase 0–3 only** (Discover → Ingest → Analyze → the confirm gate) and then **STOP**. You do
**NOT** ask the user anything (the web UI is the gate) and you do **NOT** run Phase 4+ (no diagrams,
no `.docx`). Your single deliverable is a machine-readable **plan** the user will confirm/edit.

## HARD RULE — do not modify the skill

The skill lives read-only at `{{PROPOSAL_SKILL_DIR}}`. **Read** its phase prompts and reference
material to follow its exact logic, but **NEVER create, edit, or delete any file under that folder.**
Write only inside `{{WORKSPACE_DIR}}`.

## Inputs

- **Workspace folder:** `{{WORKSPACE_DIR}}`
- **Project docs:** the RFP + supporting docs to analyse are in `{{FOLDER}}` (a folder on this
  machine) and/or were uploaded to `{{WORKSPACE_DIR}}/inputs/`. A pre-built ingest digest may exist
  at `{{WORKSPACE_DIR}}/spec/_ingest_digest.md` — read it if present.
- **Extra context from the user (optional):**

```
{{PROMPT_TEXT}}
```

## What to do (follow the skill's own phases)

Read and follow these skill prompts in order (they are the source of truth for HOW to analyse):

1. `{{PROPOSAL_SKILL_DIR}}/prompts/00_discover.md` — but the folder is already given (above); skip the search.
2. `{{PROPOSAL_SKILL_DIR}}/prompts/01_ingest.md` — read every input doc (pdf/docx/doc/txt/md/xlsx).
3. `{{PROPOSAL_SKILL_DIR}}/prompts/02_analyze.md` — this is the important one. Apply its derivation
   rules faithfully: version currency (current LTS, never an EOL version), polyglot persistence,
   benchmark vs comparable products, smart grounding (never invent team/timeline facts), and respect
   an explicit client architecture if the RFP names one.
4. `{{PROPOSAL_SKILL_DIR}}/prompts/03_confirm.md` — this is the GATE. Instead of asking the user,
   capture everything the gate would present into the plan file below, then STOP.

Also skim `{{PROPOSAL_SKILL_DIR}}/reference/` (if present) and `LESSONS_LEARNED.md` for lessons to apply.

## OUTPUT — write exactly this file, then stop

Write `{{WORKSPACE_DIR}}/spec/plan.json` (create `spec/` if needed):

```json
{
  "project": "the project / client name",
  "summary": "3-6 sentence analysis: what the system is, the key requirements, and what you propose.",
  "tech_stack": [
    {"layer": "Backend",      "choice": "e.g. .NET 10 (current LTS)", "rationale": "why, grounded in the docs"},
    {"layer": "Frontend",     "choice": "...", "rationale": "..."},
    {"layer": "Mobile",       "choice": "... or 'not in scope'", "rationale": "..."},
    {"layer": "Data stores",  "choice": "polyglot: ... ", "rationale": "1+ store per workload, justified"},
    {"layer": "Cloud / infra","choice": "...", "rationale": "..."},
    {"layer": "CI/CD",        "choice": "...", "rationale": "control/data-sovereignty aware"}
  ],
  "architecture": "2-4 paragraph prose of the proposed architecture (tiers, boundaries, key flows).",
  "diagrams": [
    {"slug": "system_context",      "title": "...", "kind": "graph|cloud|sequence", "purpose": "why this diagram"},
    {"slug": "aws_reference_arch",  "title": "...", "kind": "cloud", "purpose": "..."}
  ],
  "sections": ["Executive Summary","Purpose","System Overview","Technology Stack","Architecture","Mobile App Strategy (only if mobile in scope)","Development Management","Effort Summary"],
  "assumptions": ["anything you assumed because it wasn't in the docs"],
  "open_questions": ["things the client should confirm"]
}
```

Rules:
- Ground EVERYTHING in the ingested docs. Do not invent client/team/timeline facts.
- `diagrams` = the set the proposal will contain (the generate step will draw them).
- If mobile is not in scope, say so in `tech_stack` and omit the mobile section from `sections`.
- Write **only** `spec/plan.json`. Do NOT draw diagrams, do NOT build a `.docx`, do NOT ask
  questions, do NOT touch the skill folder. After writing the file, stop.

When done, reply with one line: `PLAN_WRITTEN <n> diagram(s), <m> stack layer(s)`.
