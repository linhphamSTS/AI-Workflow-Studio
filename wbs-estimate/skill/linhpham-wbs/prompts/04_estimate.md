# Phase 4 — Estimate

Write `wbs.json` against the contract in `scripts/wbs_schema.py`. The judgement goes in the
JSON; the rendering is Python's job. That way a re-run produces the same workbook, and a
challenged number is changed in one place.

## Every leaf task needs

- **`feature`** — what it is, in the client's vocabulary where they have one.
- **`desc`** — two to four bullets of what the work actually involves. Enough that a
  developer could scope it and a reviewer could challenge it.
- **`assum`** — starts with `Assumption:` and states what you assumed because the documents
  did not say. **Including the assumed COUNT of any external integration.** An unstated
  assumption is an unpriced risk.
- **hours per discipline**, whole numbers.
- **`refs`** — the requirement ids this task satisfies.
- **`risk`** — where the task carries real technical risk: the risk, its level, and the
  mitigation already built into the approach. A risk without a mitigation is a worry, not a
  plan.

## Estimating

Classify each task against the ranges in `reference/estimation_rules.md` section 3, then
move within the range on evidence: number of entities and relations, whether the third
party has a sandbox, what compliance applies, whether it is real-time.

Check the module against `reference/lessons_learned.md`. If a comparable module came in at
230 hours and yours says 60, one of you is wrong.

**Flag technical risk while you estimate, not afterwards.** The moment you notice a task
depends on something outside the team's control, or has to be right about money, or makes
an automated decision with legal consequence, that is the risk entry. Written later it
becomes a formality.

Roughly a fifth to a quarter of tasks carrying a risk entry is normal for a complex bid.
Flagging everything is the same as flagging nothing.

## Then the factor layer, explicitly

Put the uplifts in `factors`, not in the task numbers, so the build prints base → final →
rule. Work through all of these; the recorded failure is applying only the downward one:

1. **Bundled integrations.** Search your own assumptions for "two", "three", "multiple".
   Every hit must be N × a unit price.
2. **No public sandbox** — ×1.3. Authority gateways, national identity, banks, acquirers.
3. **Legacy protocols** — ×1.3-1.5. SOAP, file transfer, anything undocumented until access
   is granted.
4. **Integration buffer** — +10-15% on every task that talks to something external.
5. **Requirements unclear** — ×1.15-1.5, **selectively**. Apply it where one line of
   requirement hides a whole multi-step journey, not across the board: a bottom-up estimate
   already accounts for the work each feature needs, so a blanket multiplier double-counts.
   If the engagement funds a discovery phase, use the low end and say so.
6. **AI-assisted factor** by task type, per section 4 of the rules. This one is already
   inside your base numbers if you estimated with it in mind; say which way you did it.
7. **Competitive factor**, or leave it at 1.0.

Every entry records `base`, `final`, the `rule` and a one-line `note`. The build fails if a
`base` no longer matches the row, so the audit trail cannot quietly become fiction.

## Deliberate zeros

If the gate agreed UI/UX or the non-functional module is absorbed, set `zero_columns` and
`zero_modules` and write the `zero_note` that will appear on the cover. Do not delete the
rows and do not edit hundreds of tasks by hand.

## Out of scope

Fill `out_of_scope` with everything deliberately excluded and the reason. Discovery, a
dedicated QA function, project management, licences, cloud consumption, a managed-service
period, deferred features, anything the client's contract covers rather than the build.

On a fixed-price bid this sheet is as important as the estimate. It is the boundary.

## Self-check before Phase 5

- Every leaf has an assumption
- Whole hours everywhere
- No task is all zeros unless it is deliberately zeroed
- Every requirement id appears in some task's `refs`
- Every "two" or "three" in an assumption has a matching factor entry
