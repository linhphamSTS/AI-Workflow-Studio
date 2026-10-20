# Phase 5 — Build

```
python scripts/build_all.py --spec wbs.json --project "<Project>" \
--sizing sizing.json --provider <aws|azure> --region <region>
```

That is the whole delivery in one command: it builds the WBS, re-fetches the list
prices, builds the cost workbook, then runs both gates and prints READY or the reason
it is not. Drop `--sizing`, `--provider` and `--region` when there is no cloud estimate.

Run the steps individually while iterating on one of them:

```
python scripts/build_wbs.py --spec wbs.json --out "WBS_<Project>.xlsx"
```

The build prints the factor table and the totals. **Read them.** This is the first point
where the shape of the estimate is visible, and an obviously wrong module usually shows
here rather than in the verifier.

If the build fails, it is telling you the spec is wrong, not that the script is broken. The
validation refuses a task with no assumption, a factor whose base no longer matches its
row, and a module assigned to no sheet or to two. Section rows are not left empty: the
builder gives each one a total of its DIRECT children, naming every child cell, and the
sheet total adds the module rows. Nothing sums a vertical range, because once a section
row carries a total, a range over the body counts the same hours at task, group and
module level at once. That is not hypothetical: a reader added subtotals to the section
rows of a delivered workbook, entirely reasonably, and every range-based total tripled. Each of those
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
python scripts/cloud_prices.py --provider <aws|azure> --region <region> \
       --out prices.json
python scripts/build_cost.py --sizing sizing.json \
       --out "Cost Estimation - <Project>.xlsx"
```

Fetch the prices on the day you build, and put that date in `priced_on`. Phase 6 re-fetches
and compares every unit price against the vendor, so a figure copied from an earlier run
fails the gate rather than reaching a client.

Each line also declares which saving instruments it can carry: `reservable` when the vendor
sells committed pricing for it, `stoppable` when it has a stopped state. Both default to
true, and both need setting to false on the lines that cannot carry them. A Kubernetes
control plane, a load balancer, a NAT gateway and an API gateway cannot be reserved, while a
managed cache, search or streaming tier cannot be stopped at all, only deleted and rebuilt.
**These are independent properties.** A managed database is commonly stoppable on a burstable
tier that is not reservable, so never derive one list from the other. Getting this wrong
overstated the savings on a live bid by about a fifth, and the workbook looked correct.

Three rules for that workbook, all learned the hard way:

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

### Selecting a meter: what the price list does not say by name

Learned on a live AWS bid (ap-southeast-1, 2026-10). Each of these would have put a wrong
figure on the sheet that nothing downstream catches:

- **usageType is not a unique key.** `APS1-BoxUsage:m7g.xlarge` is shared by Linux, RHEL,
  SUSE and Ubuntu Pro; pin `Operating System` AND `operation=RunInstances`. RDS lists an
  `UnusedBox` row (unused reservation) at the running-instance price; select the
  `InstanceUsage` / `Multi-AZUsage` row. Tiered meters (S3 storage, data transfer out,
  CloudWatch metrics, SQS) repeat the usageType per tier; pin `StartingRange`.
  **Write each price as exact attribute filters and require them to resolve to exactly one
  distinct price**, or the run stops. A filter that matches two prices silently keeps one.
- **Residency lives in the meter name.** On Bedrock, a usageType ending in `cross-region`,
  `global` or `geo` means inference may run outside the region. In ap-southeast-1 the
  Nova 2.0 models had ONLY such meters, while the gate plan said they were in-region. When
  residency is required, price only meters without that suffix and say so on the line.
- **Some services are not in the regional file.** CloudFront edge transfer and requests, and
  Route 53 hosted zones and queries, are priced in the GLOBAL offer
  (`offers/v1.0/aws/<code>/current/index.csv`); the regional CloudFront file holds only
  origin-shield and Lambda@Edge rows. A storage class can be missing too: the Glacier Deep
  Archive storage meter was absent in ap-southeast-1 while its retrieval fees were present.
  Put that on the line as a finding, priced on the nearest published meter.
- **Re-check every availability claim the plan makes against the price list.** The plan's
  probe looks at service codes, not meters. In one run, three claims were wrong: Nova 2.0
  "in-region", Chime SDK "not in the index", SQS "not in the index".
- **The re-check must compare against the vendor's CURRENT offer version.** The cache under
  `scripts/.pricecache` is keyed by service name only. Compare the CSV preamble `Version`
  with the version in the current offer URL before reusing a cached file. `cloud_prices.py --out`
  leaves `prices` empty, so populate both `prices.json` and `prices_recheck.json` with the
  SAME key spec. Then run `build_all.py --skip-price-refetch`, because its own re-fetch
  overwrites a populated recheck file with an empty one.

## Output

Report where the files were written and their headline numbers, then Phase 6. Do not
describe the estimate as finished; nothing is finished until the gate passes.
