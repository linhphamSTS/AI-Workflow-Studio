# Phase 6 — Verify

```
python scripts/verify_wbs.py --spec wbs.json --xlsx "WBS_<Project>.xlsx" | tee _verify.txt
```

And when a cost workbook was produced, it gets its own gate. **Re-fetch the prices
first**, into a file separate from the one the sizing was built against, so the gate is
comparing the estimate to the vendor and not to itself:

```
python scripts/cloud_prices.py --provider <aws|azure> --region <region> \n       --out prices_recheck.json
python scripts/verify_cost.py --sizing sizing.json \n       --xlsx "Cost Estimation - <Project>.xlsx" \n       --prices prices_recheck.json | tee _verify_cost.txt
python scripts/calibrate_cost.py --sizing sizing.json \n       --xlsx "Cost Estimation - <Project>.xlsx" --prices prices_recheck.json
```

Omitting `--prices` does not skip the freshness checks, it FAILS them. A list price
carried forward under today’s date is the one defect a reader cannot possibly spot,
and a freshness check that quietly does nothing reads as evidence the prices were
confirmed. The workbook itself proves nothing either: openpyxl writes formulas with no
cached results, so `verify_cost.py` evaluates every one of them the way Excel will.

**The estimate is not finished until these exit 0.** Do not report the hours, do not
summarise the modules, do not tell the user it is ready while a check is failing.

## What it proves, and what it cannot

It proves: every mandatory requirement reaches a task; no task claims a requirement that
does not exist; whole hours throughout; every section row totals its
DIRECT children and no effort cell sums a vertical range, so no figure can count the
same hours twice; the cover reads single cells and never a range; deliberate zeros are actually zero and their rows are still there;
every row has a stamped height; every column header fits.

It cannot prove the hours are right. That is what the analysis, the reference figures and
the review are for.

## Read the thinnest-coverage table

The verifier lists the mandatory requirements with the fewest hours behind them. **Read
it.** A requirement covered by one task, in passing, is exactly what a tag count cannot
distinguish from a requirement properly built.

On a delivered estimate this table exposed a requirement for financial clearing between two
partners sitting at sixteen hours, a security requirement whose leakage tests had never been
priced, and a penetration-test task sized for one go-live when the documents demanded three.
None of those was a missing tag.

## When something fails

Fix the cause, not the check. The recorded temptations:

- **Loosening a check because it fired.** If it fired on something legitimate, the check is
  mis-calibrated and should be narrowed precisely — then confirm it still catches a real
  case. A checker that cries wolf is worse than none, because the next real finding is
  waved through with it.
- **Making a check read the spec instead of the workbook.** Two checks once passed on the
  input data while the rendered file was wrong. Verify the thing that ships.
- **Leaving a check at a severity the gate does not count.** A rule enforced at a level
  nothing acts on is a rule in name only.

## Read the sanity block

It reports rather than fails, because an outlier is a question, not a verdict. Answer each
one in the Phase 7 report:

- **Average per row high, average per cell normal** — expected when a leaf spans several
  disciplines. Quote both; quoting only the first invites a correction that is not needed.
- **Back-end share above the band** — legitimate for an engine-heavy platform shared by
  several products. Say so. Never pad the front end to make the ratio look right.
- **Infrastructure below the band** — legitimate with a strong infrastructure-as-code factor
  or when platform work sits in a shared-services module. Say which.
- **Non-functional at zero** — only if that was a deliberate decision at the gate, and the
  cover says why.

Re-run until clean, then Phase 7.
