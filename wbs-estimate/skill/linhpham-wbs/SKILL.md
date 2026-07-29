---
name: linhpham-wbs
description: |
  Turn a folder of bid documents into a delivered Work Breakdown Structure with man-hour
  estimates: an Excel workbook a client can price from. Handles the two situations that
  actually occur and tells them apart on its own. FILL MODE, when the client supplies a WBS
  and wants hours in it, keeps their structure untouched and fills only the effort columns.
  AUTHOR MODE, when there is only an RFP, designs the breakdown first and then estimates it.
  It ingests .pdf/.docx/.xlsx/.md, analyses scope, proposes the module structure and the
  factor stack, confirms both with the user at a gate, estimates every leaf task, builds the
  workbook, and gates the result on a verifier that checks requirement coverage, ratios,
  whole-hour discipline and SharePoint rendering before delivering. An estimation knowledge
  base with per-task-type effort ranges, AI-assisted and risk factors, and reference figures
  from past projects lives in `reference/`.
  Trigger when the user types: /linhpham-wbs <project folder>
---

# WBS Estimate

Produce `WBS_<Project>.xlsx`: a work breakdown with man-hour estimates, per-task assumptions,
a technical risk register, an out-of-scope boundary, and a verifier report proving the numbers
hang together.

## Why this exists

An estimate loses a bid two ways. Too high and a cheaper vendor takes it. Too low and you win
work you deliver at a loss, which costs more than losing. The job is not "produce a number", it
is "produce a number you can defend line by line and still deliver against".

Three things separate a defensible estimate from a plausible one, and this skill enforces all
three rather than hoping for them:

1. **Coverage is proven, not assumed.** Every requirement reference in the source documents is
   traced to at least one task, by a script, and the coverage figure is reported.
2. **Factors are explicit and auditable.** The downward AI-assisted factor and the upward risk
   factors both appear in a table showing base, final, and the rule that moved it. An estimate
   where the reasoning is invisible cannot be challenged, so it cannot be trusted.
3. **The workbook is checked before it is delivered.** Whole hours, ratio sanity, no orphan
   rows, correct roll-up formulas, and row heights that render on SharePoint.

## Two modes, detected not asked

| | The client supplied a WBS | There is only an RFP |
|---|---|---|
| Mode | **FILL** | **AUTHOR** |
| Structure | theirs, untouched | you design it |
| You write | the effort columns only | the whole workbook |
| Main risk | mis-reading their column layout | missing a requirement |

Phase 1 decides by looking for a spreadsheet with a task-ID column. Say which mode you are in
and why, and let the user override at the gate. **In FILL mode never add, remove, renumber or
reword a row.** A client who sent a WBS is comparing bids line by line; a changed structure
makes the comparison impossible and reads as carelessness.

## Workflow

```
0 Intake    read reference/ + LESSONS_LEARNED, load the enforced rules
1 Ingest    read every file in the folder, detect the mode
2 Analyze   scope, modules, frontend targets, heavy and risky areas
3 Confirm   GATE: structure, columns, factor stack, what is zeroed
4 Estimate  every leaf task, then the explicit factor layer
5 Build     the workbook  (one command: scripts/build_all.py -> both workbooks + both gates)
6 Verify    the verifier must pass before anything is shown as done
7 Report    summary, ratios, caveats, and the self-learning entry
```

## Hard rules

- **Estimate at leaf level only.** A number on a module row hides the tasks it is made of.
- **Whole hours everywhere.** No 2.5, no 0.25. Round half up. Fractional hours read as false
  precision and are awkward to price.
- **Every estimate covers development, developer unit testing and code-review fixes.** Say so.
  If a dedicated QA function, project management or business analysis is not in the number,
  say that too, with the uplift the reader should apply.
- **Separate the disciplines.** Back-end, front-end, mobile and AI are different people and
  different rates; one blended column cannot be resourced from.
- **A row that bundles N integrations costs N times one integration.** This is the single most
  expensive mistake in the reference log and it has happened more than once.
- **Never invent a requirement.** If the documents do not say it, it is an assumption, and it
  belongs in the assumptions column where the client can strike it.

## Deploy

Developed in this repo. Run `python tools/deploy.py` from `wbs-estimate/` to link the skill
into every Claude profile on the machine. Editing a file in the repo takes effect immediately;
there is no build step.
