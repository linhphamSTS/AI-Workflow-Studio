# WBS Estimate — GENERATE (head-less, produce both workbooks)

{{WBS_MODE}}


You drive the **`/linhpham-wbs`** skill head-less. The plan is already confirmed by the user
in `wbs_plan.json`. Run the skill's **Phase 4 to 7**: estimate every leaf task, build the
workbooks, gate them on the verifier, and report.

## HARD RULE — do not modify the skill (except its self-learning memory)

The skill lives at `{{WBS_SKILL_DIR}}`. Read its prompts and run its scripts; all new output
goes under `{{OUTPUT_DIR}}/`. You may write to the skill folder ONLY for Phase 7
self-learning: appending to `LESSONS_LEARNED.md` and promoting a general lesson into
`prompts/*.md`. **Never edit `scripts/*.py`, `reference/`, or anything else.** A lesson that
needs a code change is recorded as `⚠ NEEDS CODE PROMOTION: <file> — <what>` for a human.

## Inputs

- **Confirmed plan:** `{{WORKSPACE_DIR}}/spec/wbs_plan.json` — the module structure, the
  column set, the factor stack and the cloud decision are all SETTLED. Honour them.
- **Bid folder:** `{{FOLDER}}` and/or `{{WORKSPACE_DIR}}/inputs/`
- **Skill prompts, in order:** `{{WBS_SKILL_DIR}}/prompts/04_estimate.md`, `05_build.md`,
  `06_verify.md`, `07_report.md`
- **Reference ranges and factors:** `{{WBS_SKILL_DIR}}/reference/`
- **Scripts (run, do not edit):** `{{WBS_SKILL_DIR}}/scripts/` — `wbs_schema.py`,
  `build_wbs.py`, `verify_wbs.py`, `cloud_prices.py`, `build_cost.py`

## TWO deliverables, and both are required

### 1. The work breakdown

`{{OUTPUT_DIR}}/WBS_<Project>.xlsx`, built by `build_wbs.py` from a `wbs.json` you write
against `wbs_schema.py`. In FILL mode do not use the generic builder: open the client's own
workbook with openpyxl and write ONLY into the effort columns, leaving their structure,
wording and formatting untouched.

### 2. The cost estimation

`{{OUTPUT_DIR}}/Cost Estimation - <Project>.xlsx`, built by `build_cost.py`.

**Every unit price must be a REAL current price, fetched, never recalled and never
estimated.** The sequence is not optional:

```
python scripts/cloud_prices.py --provider <from the plan> --region <from the plan> --probe
python scripts/cloud_prices.py --provider <...> --region <...> --out prices.json
python scripts/build_cost.py --prices prices.json --sizing sizing.json --out "Cost Estimation - <Project>.xlsx"
```

Rules that make the cost sheet defensible:

- **Never invent, round from memory, or carry a price from another region.** A regional price
  can differ by more than 20%, and a number nobody can trace is the first thing challenged.
- **Select on ATTRIBUTES, not on a substring.** The same SKU appears many times. Use `--dump`
  to see every variant with the columns that separate them, then choose deliberately. Two
  traps that each produced a wrong figure in practice: the same virtual machine has a
  separate **Windows** row at roughly double the Linux rate, distinguished only by
  `productName`; and an Azure **Reservation** row reports its unit as "1 Hour" while the
  price is the **total for the whole term**, so it must be divided by the hours in the term
  before it is compared with an on-demand rate.
- **A service with no meter in that region is a finding, not a gap to fill.** Put the line on
  the sheet with the reason it carries no price. Confirm the name first: Azure lists Azure
  Cache for Redis as "Redis Cache" and Azure OpenAI as "Foundry Models", so a zero can mean
  the wrong name rather than an absent service.
- **Price the LAUNCH volume, and show the mature figure beside it.** Metered lines bill what
  is consumed, so putting year-three volume in month one answers a different question. Give
  each such row its mature quantity and the signal that triggers the change, so a reader can
  see a re-basing rather than suspect a cut.
- **Put the optimisation INSIDE the sizing**, then list the levers that remain. Sizing
  something generously so a lever can claim it back later is marking your own homework.
- **Every lever declares its ELIGIBILITY, not just a percentage.** For each one, answer "does
  the vendor actually sell this for that line?" A commitment cannot be bought for a managed
  control plane, a gateway or a per-request meter, and a shutdown schedule saves nothing on a
  service with no stopped state. An ineligible line in a lever's basis overstates the saving
  and nothing on the sheet looks wrong.
- **Never add a one-off amount to a per-year amount.** Subtotal per cadence.
- **Anything the client procures directly** (an independent penetration test, for instance)
  sits in its own block, excluded from every total and labelled as excluded.
- Every unit price carries the meter or usageType it came from and the extraction date, and
  the sheet states these are LIST prices to be re-extracted before the number is sent.

## Gate

Both workbooks must pass before you report done:

```
python scripts/verify_wbs.py --spec wbs.json --xlsx "WBS_<Project>.xlsx" | tee _verify.txt
```

Fix what it reports and re-run; do not narrate a failure as acceptable. Read the
thinnest-coverage table and the sanity block, not only the pass count. **Stamp a row height
on every row of both workbooks** (openpyxl writes none and SharePoint does not auto-fit, so a
wrapped cell renders clipped) and confirm no formula-bearing total disagrees with the model.

## OUTPUT (all under `{{OUTPUT_DIR}}/`)

- **`WBS_<Project>.xlsx`** — the work breakdown, verifier clean
- **`Cost Estimation - <Project>.xlsx`** — every price traceable to a fetched meter
- `wbs.json`, `sizing.json`, `prices.json` — so the run is reproducible
- `_verify.txt` — the verifier output
- `_report.md` — modules, total hours, the ratio and average checks, the cloud decision, the
  monthly cost headline, and every caveat a human must resolve before sending

Reply with one line:
`WBS_WRITTEN <wbs filename> | <total>h | <cost filename> | <monthly> USD/mo | <n> check(s)`
