# Phase 0 — Intake

Before reading a single project document, load what the skill already knows.

## Read, in this order

1. **`reference/estimation_rules.md`** — the effort ranges, the factor tables, the sanity
   bands, the deliberate-zero policy. These are the rules the estimate is built from. Do
   not re-derive them from intuition; the whole point is that they came from delivered work.
2. **`reference/lessons_learned.md`** — real figures from bids that were priced and
   submitted. When a module you are about to estimate matches a shape in there and your
   number is far off, find out which of you is wrong before the bid goes out.
3. **`LESSONS_LEARNED.md`** — the skill's own diary. Apply every entry as a constraint on
   this run. Where an entry names a concrete fix, apply it up front.

## What "loaded" means

Not "skimmed". By the end of this phase you should be able to answer, without looking
again:

- What the AI-assisted factor is for infrastructure-as-code, and why it differs from the
  factor for business logic.
- What happens to a WBS row that reads "two payment gateways".
- Which direction of factor gets forgotten, and what stops it now.
- Why a section priced at zero keeps its rows.

If you cannot, read again. Every one of those is in the reference because getting it wrong
cost a real estimate real accuracy.

## Set up the run

```
<project>/
  wbs.json          the spec you will write in Phase 4
  WBS_<Project>.xlsx        built in Phase 5
  Cost Estimation - <Project>.xlsx   built in Phase 5 when infrastructure is in scope
  _verify.txt       the gate output from Phase 6
  _report.md        the summary from Phase 7
```

Announce which reference documents you loaded and how many prior lessons you are carrying.
Then go to Phase 1.
