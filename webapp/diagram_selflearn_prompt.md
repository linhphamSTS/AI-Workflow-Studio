# Diagram — SELF-LEARN (run the skill's own Phase 4-5 on a finished render)

The web app just rendered a diagram with the deterministic Python renderers (fast path, no LLM).
Your job is to run the **`linhpham-diagram` skill's own self-check + self-learning** over that
finished output, so the skill genuinely improves over time **through its own mechanism**. You do
**NOT** re-render anything and you do **NOT** invent a separate lessons store.

## Inputs (read-only except the skill's LESSONS file)

- **Skill folder:** `{{SKILL_DIR}}` (read its prompts + LESSONS).
- **This run's output:** `{{OUTPUT_DIR}}` — the rendered `*.png` (+ `*.svg`/`*.drawio`), the specs
  `*.spec.json`, `diagrams.json`, and the self-check report `_check.json`.
- **The spec that produced it:** `{{WORKSPACE_DIR}}/spec/manifest.json`.

## What to do (follow the skill's own phases)

1. Read `{{SKILL_DIR}}/LESSONS_LEARNED.md` and `{{SKILL_DIR}}/prompts/04_selfcheck.md` +
   `05_deliver.md` — these define the skill's self-check rubric and its self-learning rule.
2. Apply the Phase-4 self-check judgement to the produced diagram(s) using `_check.json` + the PNGs:
   did anything go wrong or reveal a reusable insight (a layout/label issue, a spec pattern that
   worked well, a gotcha for this diagram type)?
3. Run the skill's Phase-5 **self-learning** exactly as `05_deliver.md` + the top rule of
   `LESSONS_LEARNED.md` prescribe: **append a concise lesson entry to
   `{{SKILL_DIR}}/LESSONS_LEARNED.md`** in the file's existing format.
   - Append an entry ONLY if this run surfaced something genuinely reusable. If there is nothing new
     to learn (a clean, ordinary render), do NOTHING and leave the file untouched — do not pad it.

## HARD limits

- Modify NOTHING except (optionally) appending ONE entry to `{{SKILL_DIR}}/LESSONS_LEARNED.md`.
- Do not re-render, do not touch the workspace output, do not edit any other skill file.

Reply with one short line: `SELFLEARN <appended|nothing-new>`.
