# Lessons Learned — /linhpham-wbs

> **Self-learning store for this skill.** It travels with the skill through git and the
> profile links, so a lesson recorded on one machine applies to every run everywhere.
>
> - **Phase 0** reads this file and applies every entry as a constraint on the current run.
> - **Phase 7** appends a new entry AND **promotes** any general lesson into the prompt,
>   script or reference file that actually runs. Mandatory: a lesson left only here has
>   not improved the skill, it has only been written down.
>
> This file is a **diary** and may grow freely; it never slows a run. The skill's real
> memory is the **enforced rules** promoted out of here. Do not prune, archive or
> consolidate it — a deleted lesson is a mistake queued up to be repeated.

**Not to be confused with `reference/lessons_learned.md`**, which holds reference FIGURES
from delivered estimates: module hours, ratios, totals. That file answers "how big is this
usually". This file answers "what did we get wrong, and what now stops it".

## How to read this (Phase 0)

Internalise every entry before starting. Where an entry names a concrete fix — a factor to
apply, a check to run, a shape of mistake to look for — apply it up front rather than
rediscovering it.

## How to write an entry (Phase 7)

Newest on top, in this shape:

```
### <what kind of system> — <YYYY-MM-DD>
- **Shape and total:** front-end targets, modules, total hours, mode (fill / author)
- **Factors applied:** the stack, and anything unusual about it
- **What the estimate nearly got wrong:** the specific miss, and how it surfaced
- **Verifier findings:** what the gate caught that a human read had not
- **Reusable figures:** module hours worth adding to reference/lessons_learned.md
- **Promoted to:** the prompt / script / reference file changed, or "nothing general"
```

Add an entry only when a run surfaced something reusable. If a run was clean, say so in one
line rather than padding.

---

## Entries

<!-- Newest entry directly below this line. -->

### Three products on one shared platform, authored from an RFP with no client WBS — 2026-07-28
- **Shape and total:** 3 mobile + 4 web front-end targets, 6 modules, 264 leaf tasks,
  4,108 hours after zeroing UI/UX and the non-functional module. AUTHOR mode: the client
  supplied only an RFP, so the breakdown had to be designed before anything could be
  estimated.
- **Factors applied:** AI-assisted per task type (infrastructure-as-code ×0.45-0.55, CRUD
  and UI ×0.6-0.7, business logic ×0.85-0.95, no-sandbox integration ×0.9-0.95); upward
  buffer and no-sandbox and legacy multipliers on 30 tasks; selective requirement-
  uncertainty ×1.15 on eight modules; competitive left at ×1.0.
- **What the estimate nearly got wrong, three times over:**
  1. **Only the downward factor was applied.** The first pass ran the AI factor and none of
     the upward rules: no integration buffer, no no-sandbox multiplier, no legacy multiplier,
     and no correction for rows bundling several integrations. It came to 4,590 hours and
     looked entirely plausible. Adding the missing rules moved it to 4,864. Nothing but a
     deliberate audit would have caught it.
  2. **Coverage was counted by tag.** A traceability script reported every requirement
     covered. Reading the requirement TEXT against the tasks then found five real problems,
     including a task that did not exist: the RFP described the user journeys but never the
     business-entity account structure those journeys attach to, so nothing created or
     administered the entity.
  3. **A row bundling several integrations was priced as one.** "Two free zone authorities"
     at 16 hours, "two partner banks" at 12. Each needed to be N times a unit price.
- **Verifier findings a human read had missed:** rows with no stamped height, so every
  wrapped cell would have been clipped on SharePoint; a column left at the default width
  that cut the tail off its own header; and, later, two checks that passed while proving
  nothing, because they read the source data rather than the rendered workbook.
- **Reusable figures:** shared platform 1,713h of a 4,108h total, so 42%; partner platform
  with settlement 233h; AI platform 268h; payments and wallet 222h; identity with a national
  digital ID 195h. All added to `reference/lessons_learned.md`.
- **Promoted to:** `estimation_rules.md` section 4 (apply both directions, and apply the
  uncertainty factor selectively rather than across the board); section 7 (report the average
  per populated discipline cell alongside the average per row); section 8 (deliberate zeros
  keep their rows and gain a cover note). `verify_wbs.py` gained the header-fit and
  row-height checks and the thinnest-coverage report. `xlsx_style.py` carries the row-height
  formula.

### Generalisable rules established while building this skill — 2026-07-28
- **A rule with no automated check will be broken.** Every style and content rule that
  existed only as prose in a prompt was eventually violated. The ones that hold are the ones
  a script fails on.
- **Scope of enforcement must equal scope of rule.** A rule can be correct and still fail
  three ways: written but never checked; checked but with an exemption that swallows the
  rule; checked everywhere but at a severity the gate does not count. All three happened on
  one rule in a single day.
- **A check that reads the source instead of the artefact proves nothing.** Two checks
  passed on the input data while the rendered workbook was wrong. Verify the thing that
  ships. *This skill's own verifier shipped with the same bug and the fixture caught it: the
  zeroed-module check read `wbs.json`, which still holds the pre-factor numbers because the
  zeroing happens during the build, so it would have failed on a correct workbook and passed
  on a broken one. It now reads the rendered sheets. Write the fixture before trusting the
  gate.*
- **Calibrate a new check in both directions before trusting it.** A checker that fires on
  something legitimate is worse than no checker, because the next real finding is waved
  through with it.
- **Do not guess a layout constant. Derive it.** Excel's stored row heights solve exactly to
  `n * 15.0 + 0.75` for Calibri 11; a guessed 14.4 under-sized every row by 0.6pt per line,
  which on a twelve-line cell put the last line on the border.
- **Copying a reference workbook does not copy what Excel computed into it.** Row heights
  are stamped by Excel Desktop on save. A faithfully copied file with correct fills, widths,
  merges and borders can still render broken on SharePoint. The reference file also carried
  a header-width defect that had simply never been noticed, so "matches the reference" is
  not the same as "correct".
- **A "reuse what worked last time" instruction must name which artefacts.** If it is
  allowed to cover the build or render layer, the output freezes at the capability of the day
  it was written and every later improvement becomes invisible. Split content, which is safe
  to reuse for stability, from capability, which is the thing being improved.
