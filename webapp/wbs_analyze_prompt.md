# WBS Estimate — ANALYZE (head-less, stop at the gate)

{{WBS_MODE}}


You drive the **`/linhpham-wbs`** skill head-less for the web app. Run its **Phase 0 to 3**:
read the bid folder, work out whether this is FILL mode (the client supplied a WBS and wants
hours in it) or AUTHOR mode (there is only an RFP, so the breakdown has to be designed),
analyse the scope, and write the plan the user will confirm at the gate.

**Then STOP.** Do not estimate a single hour, do not build a workbook. The user reviews the
plan first, because a wrong module structure or a wrong factor stack is cheap to fix now and
expensive after 250 rows carry numbers.

## HARD RULE — do not modify the skill (except its self-learning memory)

The skill lives at `{{WBS_SKILL_DIR}}`. **Read** its phase prompts and reference material and
run its scripts; put all new output under `{{WORKSPACE_DIR}}/`. You may write to the skill
folder ONLY for self-learning at the end of a full run (`LESSONS_LEARNED.md`, and promoting a
general lesson into `prompts/*.md`). **Never edit the skill's `scripts/*.py`, its `reference/`
files, or anything else.**

## Inputs

- **Bid folder:** `{{FOLDER}}` and/or uploads in `{{WORKSPACE_DIR}}/inputs/`
- **Extra context from the user:** `{{PROMPT_TEXT}}`
- **Skill prompts to follow, in order:** `{{WBS_SKILL_DIR}}/prompts/00_intake.md`,
  `01_ingest.md`, `02_analyze.md`, `03_confirm.md`
- **Estimation knowledge base (read it, it carries the reference ranges and the factors):**
  `{{WBS_SKILL_DIR}}/reference/`
- **Schema the plan must satisfy:** `{{WBS_SKILL_DIR}}/scripts/wbs_schema.py`

## What to produce

Write **`{{WORKSPACE_DIR}}/spec/wbs_plan.json`**. This is the gate artefact the UI renders,
so the shape matters:

```json
{
  "project": "<name>",
  "mode": "fill" | "author",
  "mode_reason": "<what in the folder decided it>",
  "summary": "<3-5 sentences: what is being built, for whom, and the shape of the estimate>",
  "modules": [
    {"id": "1", "title": "...", "purpose": "...", "leaf_estimate": 12,
     "notes": "why this module exists as its own line"}
  ],
  "columns": ["UI/UX", "BE", "FE", "Mobile", "AI", "DevOps"],
  "columns_reason": "<why these, and why any are deliberately zero>",
  "factors": [
    {"name": "AI-assisted development", "value": "x0.8 per task type",
     "direction": "down", "reason": "...", "applies_to": "..."},
    {"name": "Integration buffer", "value": "+10-15%", "direction": "up",
     "reason": "...", "applies_to": "..."}
  ],
  "cloud": {
    "provider": "aws" | "azure" | "undecided",
    "region": "<region id>",
    "reason": "<the requirement signal that decided it, and what each rejected candidate FAILED>",
    "rejected": [{"candidate": "...", "failed": "..."}]
  },
  "cost_scope": "<which environments and which services the cost sheet will price>",
  "assumptions": ["..."],
  "open_questions": ["..."],
  "out_of_scope": ["..."]
}
```

## Rules that decide whether this analysis is any good

- **Read every file in the folder before writing anything.** Requirement documents, any WBS,
  sample data, Q&A, an out-of-scope list. Sample data reveals the real field count; an
  out-of-scope sheet decides whether a whole column is zero.
- **Detect the mode from the folder, and say what decided it.** A client workbook with empty
  effort columns is FILL. Only an RFP is AUTHOR. Guessing wrong wastes the whole run.
- **The cloud is DERIVED, never defaulted.** Follow the rule in `02_analyze.md`: eligibility
  first (does a region exist in the required country at all), then in-country region count,
  then whether the needed services and model inference exist in that region, then any named
  certification. Run `cloud_prices.py --probe` for each candidate rather than assuming.
  Never decide on familiarity, a partnership, or what the last project used. If nothing in
  the inputs settles it, set `provider` to `undecided`, name the recommendation and its
  reason, and put the choice in `open_questions`.
- **Count the integrations explicitly.** A single line hiding N external systems is the
  classic under-count. Write down how many banks, authorities, gateways and partner systems
  the documents actually describe.
- **Both directions of the factor stack.** Downward factors are easy to remember and upward
  ones get forgotten: an integration buffer, no public sandbox, legacy protocols, a row that
  bundles N integrations, genuinely unclear requirements. List each with what it applies to.
- **No hours in this phase.** If you catch yourself writing a number per task, stop.

## When you are done

Reply with one line: `WBS_PLAN_WRITTEN <n> module(s) | <mode> mode | cloud <provider>/<region>`
