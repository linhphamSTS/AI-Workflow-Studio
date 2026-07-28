# WBS Estimate — `/linhpham-wbs`

Turn a folder of bid documents into a Work Breakdown Structure with man-hour estimates: an
Excel workbook a client can price from, plus a cloud cost estimation workbook when
infrastructure is in scope.

```
/linhpham-wbs <project folder>
```

## Two modes, detected not asked

**FILL** — the client sent a WBS and wants hours in it. Their structure is kept exactly:
no row is added, removed, renumbered or reworded, because a client who sends a WBS is
comparing bids line by line.

**AUTHOR** — there is only an RFP. The breakdown is designed first, then estimated.

Phase 1 decides by looking for a spreadsheet with a task-ID column, states the mode and the
evidence, and the user can override at the gate.

## What makes the estimate defensible

Three things, each enforced rather than hoped for:

1. **Coverage is proven.** Every requirement identifier in the source documents is traced to
   a task by a script, and the verifier reports the mandatory requirements with the fewest
   hours behind them. Counting tags proves a reference was mentioned, not that the work is
   there.
2. **Factors are visible.** The downward AI-assisted factor and the upward risk factors both
   appear in a table showing base, final and the rule. The recorded failure is an estimate
   that applied only the downward one and looked entirely plausible.
3. **The workbook is gated.** Whole hours, ratio sanity, no orphan or double-counting rows,
   and row heights that render on SharePoint, which never auto-fits.

## Workflow

```
0 Intake    load reference/ and LESSONS_LEARNED
1 Ingest    read every file, detect the mode, enumerate the requirements
2 Analyze   scope, modules, front-end targets, money paths, integration counts
3 Confirm   GATE: structure, columns, mobile approach, factors, deliberate zeros
4 Estimate  every leaf task, then the explicit factor layer -> wbs.json
5 Build     the workbook, and the cost workbook where asked
6 Verify    the gate must pass before anything is called finished
7 Report    summary, ratios, caveats, and the self-learning entry
```

## Layout

```
skill/linhpham-wbs/
  SKILL.md
  LESSONS_LEARNED.md      the skill's self-learning diary; Phase 0 reads, Phase 7 appends
  prompts/00..07
  reference/
    estimation_rules.md   effort ranges, factors, sanity bands, deliberate-zero policy
    lessons_learned.md    real figures from delivered estimates
  scripts/
    wbs_schema.py         the contract between the estimating and building phases
    build_wbs.py          renders wbs.json into the workbook
    verify_wbs.py         the gate
    xlsx_style.py         shared styling and the row-height code
    cloud_prices.py       pulls real regional list prices, deterministically
    build_cost.py         the cost estimation workbook, one sheet per environment
tools/deploy.py
```

The estimate lives in `wbs.json` and the rendering lives in Python. A re-run of the same
spec produces the same workbook, and a challenged number is changed in one place.

## Deploy

```
python tools/deploy.py          # or deploy.bat / deploy.sh / deploy.command
```

Links the skill into every Claude profile on the machine. Editing a file in the repo takes
effect immediately; there is no build step.

## Requirements

Python 3.10+, `openpyxl`. `Pillow` is optional but recommended: without it the row-height
measurement falls back to a character estimate, which is less accurate for wrapped text.
