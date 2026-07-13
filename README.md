# STS Claude Code Workflows

A monorepo of reusable Claude Code skills + a shared web app. Each skill lives in its
own folder and deploys independently (a junction/symlink from every local Claude profile
to the skill source, so editing in the repo updates every profile immediately).

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

### `webapp/` — the shared web app
A local browser UI over the skills: workspaces, a refine gate, generate, version
history/compare, and export. Today it drives the **diagram** skill; it is placed at
the top level (beside both skills) so it can also drive the **technical-proposal**
workflow from the same UI.

Run: `python webapp/launch.py` (or `webapp/run.bat` / `webapp/run.sh`) → http://127.0.0.1:8000

## Layout

```
.
├─ technical-proposal/   # /linhpham-technicalproposal skill + tools + templates
├─ diagram/              # /linhpham-diagram skill + tools
└─ webapp/               # shared local web app over the skills (diagram now, proposal next)
```

Each skill folder keeps its own `deploy.*`, `.gitignore`, and `LESSONS_LEARNED.md`,
so the two skills stay fully independent inside one repository.
