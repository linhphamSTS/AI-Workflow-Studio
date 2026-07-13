# Technical Proposal — GENERATE (head-less, produce the .docx)

You drive the **`/linhpham-technicalproposal`** skill head-less for the web app. The analysis is
already confirmed by the user (in `plan.json`). Run the skill's **Phase 4 → 6** to produce the final
proposal: draw the diagrams, assemble the `.docx`, run the strict format review + auto-fix, and
deliver. No user questions (everything needed is in `plan.json`).

## HARD RULE — do not modify the skill

The skill lives read-only at `{{PROPOSAL_SKILL_DIR}}`. **Read** its phase prompts + run its scripts,
but **NEVER create, edit, or delete any file under that folder.** All new files go under
`{{OUTPUT_DIR}}/`.

## Inputs

- **Workspace folder:** `{{WORKSPACE_DIR}}`
- **Confirmed plan:** `{{WORKSPACE_DIR}}/spec/plan.json` (tech stack, architecture, diagram set, sections).
- **Source docs:** `{{FOLDER}}` and/or `{{WORKSPACE_DIR}}/inputs/`, plus the digest at
  `{{WORKSPACE_DIR}}/spec/_ingest_digest.md` if present.
- **Skill scripts (run, do not edit):** `{{PROPOSAL_SKILL_DIR}}/scripts/` —
  `build_diagram.py`, `build_docx.py`, `format_reviewer.py`, `auto_fix.py`, `diagram_check.py`,
  `drawio_export.py`, `diagrams_runtime.py`, `render_pages.py`.
- **Template (copy, do not edit in place):** `{{PROPOSAL_SKILL_DIR}}/templates/proposal_template.docx`.

## What to do (follow the skill's own phases, output into the workspace)

Follow these skill prompts, honouring every quality rule in them (SA-grade diagrams >= 300 DPI,
strict format review, SharePoint-Online compatibility, heading spacing, no leftover placeholders):

1. `{{PROPOSAL_SKILL_DIR}}/prompts/04_generate.md` — generate the content + the diagrams named in
   `plan.json`. You MAY spawn parallel subagents exactly as that prompt describes (diagram-builder,
   content-writer, template-setup). Diagrams (PNG + optional .drawio) go to
   `{{OUTPUT_DIR}}/diagrams/` with a `diagrams.json` describing them.
2. `{{PROPOSAL_SKILL_DIR}}/prompts/05a_assemble.md` — assemble the `.docx` by running the skill's
   `build_docx.py` against a COPY of the template, the content `replacements.json`, and the
   diagrams. Write the result to `{{OUTPUT_DIR}}/`.
3. `{{PROPOSAL_SKILL_DIR}}/prompts/05b_format_review.md` — run `format_reviewer.py` + the `auto_fix.py`
   loop (max 2 iterations) until 0 blockers, as that prompt specifies.
4. `{{PROPOSAL_SKILL_DIR}}/prompts/06_report.md` — run the report step INCLUDING the skill's own
   **self-learning**: append a lesson entry to `{{PROPOSAL_SKILL_DIR}}/LESSONS_LEARNED.md` exactly
   as that phase and the file's own rules describe. This is the skill's BUILT-IN mechanism — use it,
   do not invent a separate lessons store. Add an entry only if this run surfaced something reusable
   (a real fix, a gotcha, a good decision); if nothing new, don't pad it. Also write a short run
   summary to `{{OUTPUT_DIR}}/_report.md`.

## OUTPUT (all under `{{OUTPUT_DIR}}/`)

- **`<Project> - High Level Technical Proposal.docx`** — the final proposal (0 format blockers).
- **`diagrams/`** — the generated diagram PNGs (+ `.drawio` where produced) + `diagrams.json`.
- **`replacements.json`** — the content that filled the template (so the run is reproducible).
- **`_report.md`** — a short summary: sections, diagrams, format-review result, any caveats.

Rules:
- Everything grounded in the ingested docs + `plan.json`. No invented client/team/timeline facts.
- Verify the final `.docx` has 0 leftover `{{...}}` placeholders and 0 format-review blockers before
  finishing (the skill's `format_reviewer.py` is the gate).
- NEVER write anything under `{{PROPOSAL_SKILL_DIR}}`.

When done, reply with one line: `PROPOSAL_WRITTEN <docx filename> | <n> diagram(s) | <k> blocker(s)`.
