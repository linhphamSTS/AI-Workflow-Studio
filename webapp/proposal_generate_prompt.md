# Technical Proposal — GENERATE (head-less, produce the .docx)

You drive the **`/linhpham-technicalproposal`** skill head-less for the web app. The analysis is
already confirmed by the user (in `plan.json`). Run the skill's **Phase 4 → 6** to produce the final
proposal: draw the diagrams, assemble the `.docx`, run the strict format review + auto-fix, and
deliver. No user questions (everything needed is in `plan.json`).

## HARD RULE — do not modify the skill (except its self-learning memory)

The skill lives at `{{PROPOSAL_SKILL_DIR}}`. **Read** its phase prompts + run its scripts, and put all
new run output under `{{OUTPUT_DIR}}/`. You may write to the skill folder ONLY for self-learning
(Phase 6): appending to `LESSONS_LEARNED.md`, and promoting a general lesson into a Markdown rule file
(`prompts/*.md`). **Never edit the skill's `scripts/*.py`, templates, or any other file** — for a
lesson that needs a code change, record it in the entry as `⚠ NEEDS CODE PROMOTION` for a human. Do
not create or delete anything else under the folder.

## Optional bid sections the user selected

{{SECTIONS}}

## Re-run context (what you may reuse)

{{PRIOR_VERSION}}

## Inputs

- **Workspace folder:** `{{WORKSPACE_DIR}}`
- **Confirmed plan:** `{{WORKSPACE_DIR}}/spec/plan.json` (tech stack, architecture, diagram set, sections).
- **Source docs:** `{{FOLDER}}` and/or `{{WORKSPACE_DIR}}/inputs/`, plus the digest at
  `{{WORKSPACE_DIR}}/spec/_ingest_digest.md` if present.
- **Proposal language:** `plan.json` `"language"` (`en` or `vi`), confirmed by the user at the
  gate. Write every generated value in it (04_generate.md, Agent B, Language). If it is missing,
  stop and say so: do not guess.
- **Skill scripts (run, do not edit):** `{{PROPOSAL_SKILL_DIR}}/scripts/` —
  `build_diagram.py`, `build_docx.py`, `finalize.py` (which runs `post_assembly.py`,
  `auto_fix.py`, `format_reviewer.py`, `translate_vi.py`, `refresh_toc.py`,
  `check_consistency.py`, `check_crossdoc.py`), `diagram_check.py`, `drawio_export.py`,
  `diagrams_runtime.py`, `render_pages.py`.
- **Template (copy, do not edit in place):** `{{PROPOSAL_SKILL_DIR}}/templates/proposal_template.docx`.

## What to do (follow the skill's own phases, output into the workspace)

Follow these skill prompts, honouring every quality rule in them (SA-grade diagrams >= 300 DPI,
strict format review, SharePoint-Online compatibility, heading spacing, no leftover placeholders):

1. `{{PROPOSAL_SKILL_DIR}}/prompts/04_generate.md` — generate the content + the diagrams named in
   `plan.json`. You MAY spawn parallel subagents exactly as that prompt describes (diagram-builder,
   content-writer, template-setup). Diagrams (PNG + optional .drawio) go to
   `{{OUTPUT_DIR}}/diagrams/` with a `diagrams.json` describing them.
2. `{{PROPOSAL_SKILL_DIR}}/prompts/05a_assemble.md` — assemble AND finish with ONE command,
   `finalize.py`, exactly as that prompt specifies: `--docx "{{OUTPUT_DIR}}/<Project> - High Level
   Technical Proposal.docx" --language <plan.language> --client "<plan.client>"
   --replacements {{OUTPUT_DIR}}/replacements.json --diagrams {{OUTPUT_DIR}}/diagrams/diagrams.json
   --plan {{WORKSPACE_DIR}}/spec/plan.json`, plus `--wbs <file>` when a WBS workbook is among the
   source docs. Do not run `build_docx.py`, the review, the translation or the contents rebuild by
   hand in another order. It must print `READY`.
3. `{{PROPOSAL_SKILL_DIR}}/prompts/05b_format_review.md` — when `finalize.py` stops on review
   issues, apply the fixes and the `auto_fix.py` loop (max 2 iterations) as that prompt specifies,
   then re-run `finalize.py` (`--skip-build` when the fix was made on the assembled file). Then
   render the pages (`render_pages.py`) and LOOK at every page: no script sees a figure printed
   over the footer or a word left alone on a line.
4. `{{PROPOSAL_SKILL_DIR}}/prompts/06_report.md` — run the report step INCLUDING the skill's own
   **self-learning**: append a lesson entry to `{{PROPOSAL_SKILL_DIR}}/LESSONS_LEARNED.md`, AND
   **promote** a general lesson into the relevant phase prompt (`04_generate.md` /
   `05b_format_review.md`, Markdown only — promotion is what actually makes the skill smarter), noting
   where you promoted it. This is the skill's BUILT-IN mechanism — use it, do not invent a separate
   lessons store. For a lesson that would need a `scripts/*.py` change, DO NOT edit the script in this
   unattended run — flag it `⚠ NEEDS CODE PROMOTION: <file> — <what>` in the entry for a human. Add an
   entry only if this run surfaced something reusable (a real fix, a gotcha, a good decision); if
   nothing new, don't pad it. Also write a short run summary to `{{OUTPUT_DIR}}/_report.md`.

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

- This run is head-less: when your turn ends, the run ends. If you spawn subagents, WAIT for
  every one of them to report before you assemble, and never end your turn while a subagent or
  a background command is still running.
- The final `.docx` is the ONLY `.docx` directly in `{{OUTPUT_DIR}}/`; `finalize.py` keeps its
  working copies under `{{OUTPUT_DIR}}/_work/`.

When done, reply with one line: `PROPOSAL_WRITTEN <docx filename> | <n> diagram(s) | <k> blocker(s) | <language>`.
