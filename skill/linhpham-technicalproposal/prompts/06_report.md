# Phase 6 — Final report

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
