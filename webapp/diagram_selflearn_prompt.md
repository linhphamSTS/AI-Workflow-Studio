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
4. **Promote the rule — this is the part that actually makes the skill smarter** (per `05_deliver.md`
   §3). Appending to the diary is not enough; a general lesson must become an ENFORCED rule so the log
   size never matters:
   - A convention / notation / classification rule → fold it into the matching Markdown file under
     `{{SKILL_DIR}}`: `reference/kb_*.md`, `reference/diagram_types.md`, or
     `prompts/01_refine.md` / `prompts/03_generate.md`. Editing these Markdown rule files is SAFE and
     expected — do it, and note where in the entry (`Promoted to: ...`).
   - A lesson that needs a **code change** to a `scripts/*.py` file → **DO NOT edit the script** in
     this unattended run. Record it in the entry clearly marked
     `⚠ NEEDS CODE PROMOTION: <file> — <what to change>` so a human applies and verifies it. Never
     guess at code here.

## HARD limits

- You MAY: append ONE entry to `{{SKILL_DIR}}/LESSONS_LEARNED.md`, and — for a general lesson — edit a
  Markdown rule file under `{{SKILL_DIR}}` (`reference/kb_*.md`, `reference/diagram_types.md`,
  `prompts/*.md`) to promote it.
- You MUST NOT: edit any `scripts/*.py` (flag code changes per step 4 instead), re-render, touch the
  workspace output, or change anything else.

Reply with one short line: `SELFLEARN <appended+promoted|appended|nothing-new>`.
