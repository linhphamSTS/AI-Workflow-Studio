# AI Workflow Studio

A monorepo of reusable Claude Code skills plus a shared local web app ("AI Workflow
Studio") that drives them. Each skill lives in its own folder and deploys independently
(a junction/symlink from every local Claude profile to the skill source, so editing in
the repo updates every profile immediately).

![AI Workflow Studio — the shared web app driving the skills](webapp/static/sample.png)

*AI Workflow Studio — the shared web app: pick a workspace type (diagram or technical proposal), refine, confirm at a gate, generate, keep version history, and export.*

## Install (once per machine)

One command sets up **everything** — deploys both skills into every Claude profile and
prepares the web app (venv + dependencies + Graphviz):

- **Windows:** double-click **`install.bat`** (or `py -3 install.py`)
- **macOS / Linux:** `./install.sh` (or `python3 install.py`)

Only prerequisite: **Python 3.10+**. (The `claude` CLI is needed at run time for the
Refine / Analyze / Generate steps; the installer reports whether it's signed in.)

Then start the web app anytime:

- **Windows:** **`run.bat`**   ·   **macOS / Linux:** `./run.sh`   (→ http://127.0.0.1:8000)

Skills also work directly in any Claude Code session: `/linhpham-diagram` and
`/linhpham-technicalproposal`.

## Skills

### `technical-proposal/` — `/linhpham-technicalproposal`
Turns a project folder (RFP + supporting docs) into a SharePoint-compatible
High-Level Technical Proposal `.docx` with senior-SA-grade architecture diagrams:
ingest → analyze → confirm gate → generate (parallel agents) → assemble →
strict format review → report.

Deploy: `cd technical-proposal && python tools/deploy.py`

### `diagram/` — `/linhpham-diagram`
Turns a plain-language description (or a folder of project docs) into a
senior-SA-grade diagram (sharp PNG + editable `.drawio` + `.docx`).

Deploy: `cd diagram && python tools/deploy.py`

### `wbs-estimate/` — `/linhpham-wbs`
Turns a folder of bid documents into a Work Breakdown Structure with man-hour
estimates, plus a cloud cost estimation workbook where infrastructure is in scope.
Fills a client-supplied WBS without touching its structure, or authors the breakdown
from an RFP, detecting which on its own: ingest → analyze → confirm gate → estimate
with an explicit factor layer → build → verify → report. The gate proves requirement
coverage and refuses a workbook that would render clipped on SharePoint.

Deploy: `cd wbs-estimate && python tools/deploy.py`

### `webapp/` — the shared web app ("AI Workflow Studio")
A local browser UI over the skills. When you create a workspace you pick its type
(**diagram** or **technical proposal**), then: refine/analyze → confirm at a gate →
generate → version history/compare → export. It drives **both** skills head-less via
the `claude` CLI, and sits at the top level (beside both skills) so future skills can
plug into the same UI.

Run: `python webapp/launch.py` (or `webapp/run.bat` / `webapp/run.sh`) → http://127.0.0.1:8000

## How it learns (gets smarter over time)

Both skills **self-improve after every run** — not by swapping in a bigger model, but by
turning each mistake into a rule that is enforced automatically the next time.

**The mechanism (each skill owns it):**

1. **Diary.** Every skill keeps a `LESSONS_LEARNED.md` — a running log of what went wrong,
   what a client flagged, or a non-obvious gotcha, each with its concrete fix.
2. **Promote, don't just log.** A lesson only makes the skill smarter if it is *applied* next
   time, so every reusable lesson is **promoted** into the place that actually runs — a prompt,
   a knowledge-base note, a renderer script, or a build-time guard. Once promoted, the correct
   behaviour happens on its own and the skill physically cannot repeat that mistake.
3. **Read at the start.** Each run loads those enforced rules (they apply automatically) and
   skims the diary for anything relevant to the current job.

**Where the learning runs**

- **Technical proposal** — the skill's final phase appends a lesson and promotes the rule.
- **Diagram** — after a render, a short self-check reviews the output against the skill's own
  senior-SA quality rubric and records/promotes anything reusable.
- **Web app** — it never writes lessons itself; it only lets each skill run its *own*
  self-learning. Learning always happens **through the skill**, so the skill (not some separate
  store) is what gets smarter — on every machine the repo is deployed to.

**Why the log never slows it down.** `LESSONS_LEARNED.md` is a *diary*: it may grow freely. The
skill's real memory is the promoted rules living in its prompts/scripts, which cost nothing extra
to apply. So the archive of lessons can keep growing without ever making a run slower or less
accurate — the intelligence is in the enforced rules, not in re-reading the log.

**Real examples of promoted lessons** (each now enforced, so it can't recur):

- template images placed in a *Heading* paragraph leaked into the SharePoint Table of Contents →
  a build-time guard now fails the build if any template image sits in a heading;
- a full-page cover image overflowed onto a blank extra page on SharePoint → full-page images are
  now floating (behind text) instead of inline;
- diagrams could embed soft/blurry in Word → the renderers now guarantee ≥ 300 DPI at the
  6.5-inch Word embed width.

## Layout

```
.
├─ technical-proposal/   # /linhpham-technicalproposal skill + tools + templates
├─ diagram/              # /linhpham-diagram skill + tools
├─ wbs-estimate/         # /linhpham-wbs skill + tools
└─ webapp/               # "AI Workflow Studio" — shared local web app over the skills
```

Each skill folder keeps its own `deploy.*`, `.gitignore`, and `LESSONS_LEARNED.md`,
so the skills stay fully independent inside one repository.

The web app currently drives the technical-proposal and diagram skills; `wbs-estimate`
runs from Claude Code and is wired into the UI next.
