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

## Roll-up on section rows, and lever eligibility (ported from the AEGI bid, 2026-07-29)

### The workbook must roll up the way a reader expects
The builder used to leave every section row empty and sum a vertical range for each total.
That is correct only while nobody adds a subtotal. On a delivered bid the client's PM added
sums to the module rows, which is a completely reasonable thing to do, and every range then
contained the same hours at task, group and module level: the cover reported **three times**
the real number.

The fix is not to ask users not to do that. It is:

* a section row totals its **direct children**, naming each cell (`=G5+G6+G7`)
* the sheet TOTAL adds the **module rows** only
* the cover reads a **section row** for a module and the **TOTAL row** for a sheet
* nothing anywhere sums a vertical range in an effort column

**"Direct child" is decided by the dot depth of the identifier, never by row colour or row
kind.** A module can carry its tasks one level up with no group rows at all (`6.1`, `6.2`
directly under `6`), and a colour-based rule leaves that module's section row empty while
reporting success.

`verify_wbs.py` now asserts the roll-up formula matches the direct-children list exactly, and
separately bans any vertical-range SUM in an effort cell, which gates the whole bug class
rather than the one instance.

### The cover had no check at all, and the cover is where it shows
Three checks covered the WBS sheets and none covered the cover, which is precisely the sheet
where a double count becomes visible to the client. Added: every cover figure must read a
single cell or add named cells, never a range. **Scan every formula column.** The first
version of the equivalent check on the bid looked at one column, so a range restored into a
different column passed silently. There is also an assert that the check found some formulas,
because a check that inspects nothing must never report success.

### A lever must declare what it can apply TO
Every saving lever used to take its basis from "all hourly rows". On the bid that meant
reserved pricing was claimed on the Kubernetes control plane, the load balancer and the NAT
gateway, none of which the vendor sells reserved, and a nightly shutdown was claimed on
managed cache, search and streaming, none of which have a stopped state. The savings were
overstated by roughly a fifth and **the finished workbook looked entirely correct**.

Lines now carry `reservable` and `stoppable` (defaulting to true), and the scopes
`prod reservable`, `all reservable` and `non-prod stoppable` resolve to only the eligible
rows. Every lever has to answer "does the vendor actually sell this for this line?".

**Reservability and stoppability are independent facts. Never derive one list from the
other.** A managed database can typically be stopped on a burstable tier that cannot be
reserved, so treating "not reservable" as implying "not stoppable" produces a false positive.

### Still open
There is no `verify_cost.py` in this skill. The bid it was ported from ended with 42 checks
over the cost workbook, including formula evaluation (openpyxl writes no cached values, so a
saved file proves nothing about its own totals) and reverse calibration. Until that exists,
the cost workbook is generated but not gated.

### The cost workbook now has a gate, and it enforces price freshness

There was no `verify_cost.py` at all: the workbook was generated and never checked. It now
has one, with reverse calibration in `calibrate_cost.py` (9 injected faults, all caught).

**openpyxl writes formulas but no cached results, so a saved workbook proves nothing about
its own totals.** Excel computes them when the client opens it. The gate evaluates every
formula the same way and fails when the file a client would see disagrees with the model.

**Fetching prices was a step; keeping them fresh was not.** `priced_on` was a string the
author typed, so a run could ship prices extracted weeks earlier under today's date, and the
"re-extract before sending" warning lived only in prose on the sheet. Phase 6 now re-fetches
into a *separate* file and the gate re-resolves every unit price against it, failing on any
drift. **Omitting `--prices` fails the freshness checks rather than skipping them**, because a
check that quietly does nothing reads as evidence the prices were confirmed.

Two of my own checks were wrong on first run and calibration is what exposed both:

* the instrument a lever uses was guessed from the row's label, and a reservation row is
  labelled with its term, "1 year", which contains neither "reserved" nor "commitment", so it
  was mistaken for a shutdown schedule and complained about the wrong property. Read the
  scope the sheet already prints, never infer it from a label.
* the cover's grand total summed a range over the environment rows. Arithmetically fine
  today, and exactly the fragile shape that tripled a delivered WBS cover. Fixed in the
  builder by naming each cell rather than by relaxing the check.

### The most expensive rule in the reference was documented and not enforced

`reference/estimation_rules.md` section 4 splits factors into upward and downward, and
`build_wbs.py` prints the whole stack as a `base -> final -> rule` audit table. Both good.
Nothing checked that the stack actually moved in both directions.

That is the defect that left a live bid 218 hours short. The AI discount is applied per task
type while the base numbers are written, exactly as the estimating phase intends, so the
factor table can be legitimately EMPTY and nothing looks one-sided. Meanwhile the integration
buffer, the no-sandbox multiplier, the legacy-protocol multiplier and the rule that a row
bundling N integrations costs N times one unit price had all been skipped. It surfaced only
because someone asked whether the rules had been applied at all.

Two checks now gate it, and neither can pass vacuously:

* **the factor stack moves in both directions.** An empty factor table does not pass when any
  task integrates with something outside the estate, because rule 5 owes those a 10-15%
  buffer. The demand is made by the presence of such a task, not by a blanket rule, so a
  project with no external interface is not nagged.
* **every row naming a COUNT of external things carries an explicit factor.** This is the
  `"two free zone authorities"` shape priced as one authority. Reading the count out of the
  assumptions column is what catches it, because the hours look perfectly reasonable for one.

Calibrated across three states: no factors plus an integrating task fails, a stack with only
a downward entry fails, and an upward entry on the bundled row passes.

The sanity report also now prints the two shares the reference names, the infrastructure
percentage and the last module's percentage, plus mobile against front-end web where both
columns are populated. Those stay reports rather than gates: an outlier there is a question
to answer, not a defect. **The factor stack is different, because a missing uplift is not a
question, it is money left on the table.**

### How to tell whether a gate in this skill can be trusted

Every gate here has a calibration script that injects the exact fault the gate claims to
catch and asserts it is caught. Run those, not the summary someone gives you:

```
python scripts/calibrate_cost.py --sizing sizing.json --xlsx cost.xlsx --prices prices.json
```

The WBS side is calibrated the same way, including a mutation that hides a restored range in
a *different column* from the one the check was first written to scan, because that is how the
original version of that check passed while the defect was present.

**A gate with no injected-fault test is a hope.** Four ways a gate looks fine and is not:

* it **crashes** instead of failing. A crash exits non-zero, so a calibration that only reads
  the exit code records it as CAUGHT while the check never printed a verdict. Assert on the
  named `[FAIL]` line, not on the exit code.
* it **matches nothing** and reports success. Every check that scans a set must fail when the
  set is empty, or a renamed scope silently disables it.
* it **shares a premise with the thing it checks**. Reading back the same exclusion list the
  builder used only proves the builder is self-consistent. Vendor facts belong in the
  verifier, written out in full.
* it **cries wolf**. A check that fires on well-formed work trains the reader to skip the
  output, which is worse than not having it. The reference-range comparison was written as a
  hard gate, fired on task names that were perfectly reasonable, and was demoted to a report
  on the spot. Only the direction that costs money stayed a gate.

### Verify a claim about content by READING it, not by grepping your own vocabulary

Checking whether the rules from the source document had reached this skill, keyword probes
returned four separate false negatives in one sitting: `full-text` against a file that says
`full text`, `qr` against `camera and scanning flows`, `cart` against `a basket spanning
several vendors`, `whole term` against `the TOTAL for the term`. Every one of them was already
covered, and each near-miss nearly caused a duplicate to be written.

The probe scope was wrong too: `prompts/` was left out of the scan, so two lessons that live
in `05_build.md` were reported missing.

Grep is for locating text. Deciding whether a concept is present is reading work. When the
two disagree, the reading wins.
