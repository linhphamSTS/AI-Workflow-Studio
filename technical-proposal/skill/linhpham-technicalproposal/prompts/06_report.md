# Phase 6 — Final report

## Step A — Record lessons (MANDATORY, before the hand-off message)

Append a new entry to `LESSONS_LEARNED.md` at the skill root (create the file from
the template shape if it is missing). Capture, concretely and reusably:

- Project + proposal type + date (absolute date).
- Stack/architecture proposed and why.
- Format/layout issues hit this run and their fixes (SharePoint compat, >=300 DPI,
  overflow, template structure, font/spacing drift, widow/orphan).
- Diagram-quality issues and fixes (missing icon, chip/arrow collision, centring,
  label overflow).
- Content gaps or client feedback and how they were corrected.
- A "do better next time" checklist future runs should apply up-front.

**Promotion is MANDATORY, not "if you feel like it".** A lesson only makes the skill
better if it is APPLIED next run, so every lesson that could recur MUST be folded into
the place that actually runs — the relevant phase prompt (`04_generate.md` for
diagram/content rules, `05b_format_review.md` for format checks, or a new enforced check
in `format_reviewer.py` once you have verified it). Note where in the entry (e.g.
"Promoted to: 04_generate.md"). A lesson left only in this log has NOT improved the
skill. Prefer promoting into a PROMPT (a rule in prose, low-risk) over editing a script.
The log is a diary that may grow freely; the skill's real memory is these enforced
rules, so the log's size never slows it. Newest entry goes on top of the Entries section.

This step is not optional: it is how the skill self-improves across runs and machines.

## Step B — Hand-off message

Produce a concise hand-off message to the user.

## Format

```
Generated proposal: <absolute path to .docx>

Diagrams (N):
  - Figure 1: <type> — <scope>     ✓
  - Figure 2: <type> — <scope>     ✓
  ...

Format review: PASS  (or PASS WITH N MANUAL ITEMS  or FAIL)
  Auto-fixed: <list>
  Manual review needed:
    - <issue>
    - <issue>

SharePoint compat: OK
  File size: X.X MB
  Zip integrity: OK
  Track changes / comments / macros / encryption: clean
  No unfilled placeholders detected

Caveats:
  - <thing the model is uncertain about>
  - <thing that needs a human SME to verify>
```

## Style

- Vietnamese if the user's last message was Vietnamese.
- English otherwise.
- One paragraph, no padding.
- End with one explicit next action ("Open the file in Word, upload to
  SharePoint, or run /linhpham-technicalproposal again to refine").

## Do NOT

- Do not narrate the pipeline ("I ran Phase 0, then Phase 1, then..."). The
  user knows what the workflow does. Report results, not process.
- Do not claim "100% ready to submit" — there's always a human review step
  before sending to a client.
