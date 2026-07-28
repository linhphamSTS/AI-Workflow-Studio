# Phase 5 — Build

```
python scripts/build_wbs.py --spec wbs.json --out "WBS_<Project>.xlsx"
```

The build prints the factor table and the totals. **Read them.** This is the first point
where the shape of the estimate is visible, and an obviously wrong module usually shows
here rather than in the verifier.

If the build fails, it is telling you the spec is wrong, not that the script is broken. The
validation refuses a section row carrying hours, a task with no assumption, a factor whose
base no longer matches its row, and a module assigned to no sheet or to two. Each of those
would otherwise produce a workbook that is confidently wrong.

## FILL mode

Do not use the generic builder. Open the client's workbook with `openpyxl`, write only into
the effort columns you identified in Phase 1, and save. Keep every other cell, every style
and every formula exactly as it was.

Then still run the verifier against it. Their structure does not exempt the numbers from
the ratio and whole-hour checks, and their workbook may well have no stamped row heights
either.

## Cost estimation workbook

When infrastructure is in scope and the gate asked for it:

```
python scripts/cloud_prices.py --provider aws --region <region> --out prices.json
python scripts/build_cost.py --prices prices.json --sizing sizing.json \
       --out "Cost Estimation - <Project>.xlsx"
```

Two rules for that workbook, both learned the hard way:

**Never read a large price file through a summarising model.** Two reads of the same AWS
pricing JSON returned two different prices for the same instance, and both were wrong.
`cloud_prices.py` streams the vendor's own CSV and parses it deterministically. Every price
lands in the workbook with the usageType it came from.

**Optimise the sizing, not just the list of levers underneath it.** Listing savings beneath
a generous sizing is scoring points by having inflated first. Put the decisions that cost
nothing into the design — the cheaper cache engine, the infrequent-access log class,
burstable classes for non-production, in-cluster services for development — and say in each
line why it is small. Keep as levers only the choices that cost something: a shutdown
schedule, a multi-year commitment, spot capacity.

Then separate the two on the sheet: what is already applied and cannot be taken again, and
what is still available. Otherwise a reader banks the same saving twice.

## Output

Report where the files were written and their headline numbers, then Phase 6. Do not
describe the estimate as finished; nothing is finished until the gate passes.
