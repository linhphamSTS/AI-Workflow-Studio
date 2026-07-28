# Phase 7 — Report and self-learn

## The report

Write `_report.md` and summarise it for the user. Lead with the number and the shape, not
with the process.

1. **The total**, and the per-sheet breakdown.
2. **What the number covers**, and what it does not. If a dedicated QA function, project
   management or discovery sits outside it, give the uplift the reader should apply. A
   number the client thinks is all-in when it is not causes more damage than a high number.
3. **The factor stack**: what was applied, in which direction, and what the competitive
   factor is set to.
4. **Coverage**: mandatory requirements covered, out of how many.
5. **The sanity metrics**, with an answer for anything outside its band. An unexplained
   outlier will be the first thing a reviewer asks about.
6. **Assumptions that carry money**, especially the assumed count of every external
   integration, stated as "beyond this count is a change request at the same unit effort".
7. **The risk register**: how many tasks carry one, and the handful most likely to move the
   number.
8. **What the client must still decide**, and what only they can supply.

Be plain about what is weak. An estimate presented as more certain than it is gets found
out in the first review, and everything else you said loses credibility with it.

## Then self-learn — mandatory

Append an entry to `LESSONS_LEARNED.md` in the documented shape, and **promote** anything
general into the place that actually runs:

| The lesson is about | Promote it into |
|---|---|
| How much a kind of work costs | `reference/estimation_rules.md` section 3 |
| A factor, or when to apply one | `reference/estimation_rules.md` section 4 |
| A module's real figures | `reference/lessons_learned.md` |
| Something the gate should have caught | `scripts/verify_wbs.py` |
| How the workbook renders | `scripts/xlsx_style.py` or `build_wbs.py` |
| How a phase should be run | the phase prompt |

**A lesson left only in the diary has not improved the skill.** Name the promotion in the
entry. If a lesson needs a code change you should not make unattended, write
`NEEDS CODE PROMOTION: <file> — <what>` so a human can.

Add an entry only when the run surfaced something reusable: a real miss, a gotcha, a
decision worth repeating. If it was clean, say so in one line. Padding the diary makes the
next Phase 0 slower and teaches nothing.

Never prune, archive or consolidate the diary. A deleted lesson is a mistake queued up to
be repeated.

## Deliverables

- `WBS_<Project>.xlsx`
- `Cost Estimation - <Project>.xlsx`, where infrastructure was in scope
- `wbs.json`, so the estimate can be re-run and diffed
- `_verify.txt`, the passing gate
- `_report.md`
