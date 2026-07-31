# AI Workflow Studio — Web App

A local browser UI over the Claude Code skills in this repo — **diagram**,
**technical proposal**, and **WBS + cost**. One **workspace** per project; each holds its
own inputs and its own generated output, and you pick the workspace type when you create
it. Choosing WBS asks one more question: fill a client-supplied WBS, or author the
breakdown from an RFP.

![AI Workflow Studio web app](static/sample.png)

```
inputs (a prompt, uploaded docs, or a folder)
  → REFINE / ANALYZE   the real skill runs head-less via the `claude` CLI → spec / plan   ⟵ gate
  → confirm / edit the spec or plan in the browser
  → GENERATE   diagram  = fast local Python renderers → PNG · .svg · .drawio · .docx
               proposal = the skill's full Phase 4-6 → a SharePoint-ready .docx + diagrams
               wbs      = the skill's Phase 4-7 → the WBS workbook + the cost workbook
  → PREVIEW    view the output; iterate (edit inputs/plan, re-run) until happy
  → EXPORT     download a zip of the output folder (or just the .docx / .xlsx)
```

**Refine / Analyze** is the LLM step — it shells out to the installed `claude` CLI (no API key
needed), so the actual skill logic does the classification / analysis, then stops at a confirmation
gate. **Generate** for a *diagram* is pure Python (fast, no LLM) using the skill's `build_cloud` /
`build_graph` / `build_sequence` / `build_diagram_doc` / `diagram_check` scripts; for a *technical
proposal* it runs the skill's full generate → assemble → strict format-review pipeline (a longer
`claude` run) and produces the `.docx`; for a *WBS* it estimates every leaf task, builds both
workbooks and refuses to finish until the verifier passes.

The web app never writes the skills' lessons itself. It only lets each skill run its own
self-learning, so what improves is the skill, on every machine it is deployed to.

## Run — one command, self-installing

On a machine that has nothing at all, use the repo-level installer described in the
[root README](../README.md#install--one-command-nothing-else-needed): it also fetches
Python, deploys the skills and puts a Desktop icon in place.

If the repo is already here, just launch it. The first run creates its own virtual-env,
installs every dependency, downloads a portable Graphviz if needed, starts the server, and
opens your browser. Nothing to set up by hand.

- **Windows:** double-click **`webapp/run.bat`** (or `py -3 webapp/launch.py`)
- **macOS / Linux:** `./webapp/run.sh` (or `python3 webapp/launch.py`)

Only prerequisite: **Python 3.10+** on the machine. The `claude` CLI has to be installed and
signed in for anything to be analysed or generated; if it is not, the app says so on arrival
with the exact command for your platform, and re-checks without a reload.

Works on **Windows, macOS and Linux** — the launcher builds a per-OS venv and the
skill auto-installs Graphviz (portable zip on Windows; `brew`/`apt` on macOS/Linux,
so those may prompt for a package install on first render). On a headless Linux box
the native "Browse…" folder dialog needs a display; type the path instead.

```bash
python webapp/launch.py               # set up (if needed) + run + open browser
python webapp/launch.py --setup-only  # install everything but don't start
DIAGRAM_NO_VENV=1 python webapp/launch.py   # use the current interpreter, no venv
```

Advanced: run the bare server directly (assumes deps already present):

```bash
python webapp/server.py            # → http://127.0.0.1:8000
```

Optional environment overrides:

| var | default | meaning |
|-----|---------|---------|
| `DIAGRAM_HOST` / `DIAGRAM_PORT` | `127.0.0.1` / `8000` | bind address |
| `DIAGRAM_WORKSPACES_DIR` | `webapp/workspaces` | where your workspaces (inputs + output) are stored; set it to keep data outside the repo |
| `DIAGRAM_REFINE_MODEL` | (CLI default) | model passed to `claude -p`, for example `sonnet` |
| `INGEST_MAX_CHARS` | `250000` | per-file cap when reading source documents. It used to be 20,000 and silently dropped 85% of a large WBS before the analysis ever saw it |
| `DIAGRAM_NO_VENV` | unset | set to `1` to install into the current interpreter instead of building `webapp/.venv` |
| `DIAGRAM_HIDDEN_CONSOLE` | `1` | Windows: run `claude` in a hidden console so its child processes do not each pop a window. Set to `0` to see them |
| `DIAGRAM_SELFLEARN` | `1` | run the diagram skill's own self-check and self-learning after a render |

Timeouts, all in seconds. Raise one if a large job is being killed mid-run rather than failing:

| var | default | covers |
|-----|---------|--------|
| `DIAGRAM_REFINE_TIMEOUT` | `900` | a text-mode refine |
| `DIAGRAM_FOLDER_REFINE_TIMEOUT` | `1800` | a folder-mode refine. A real 8-diagram bid folder needed 1,016s, which is why the text-mode budget was not enough |
| `DIAGRAM_RENDER_TIMEOUT` | `180` | one diagram render |
| `DIAGRAM_SELFLEARN_TIMEOUT` | `600` | the post-render self-learning pass |
| `PROPOSAL_ANALYZE_TIMEOUT` | `1200` | proposal analyze |
| `PROPOSAL_GENERATE_TIMEOUT` | `3600` | proposal generate, the heaviest job here |
| `WBS_ANALYZE_TIMEOUT` | `1200` | WBS analyze |
| `WBS_GENERATE_TIMEOUT` | `4200` | WBS generate, which builds and verifies two workbooks |

Dependencies are installed for you by `launch.py` into `webapp/.venv` (see `requirements.txt`):
`fastapi`, `uvicorn`, `python-multipart`, `Pillow`, `python-docx`, `openpyxl`, `PyMuPDF` and
`diagrams`. Graphviz is fetched by the skill's own bootstrap. The only thing you install yourself
is the `claude` CLI, because signing in needs a browser.

## Layout

```
webapp/
  launch.py                    self-installing launcher (venv + deps + Graphviz, then serve)
  server.py                    FastAPI backend + background jobs
  requirements.txt
  refine_prompt.md             head-less refine template for a diagram workspace
  diagram_selflearn_prompt.md  runs the diagram skill's own self-learning after a render
  proposal_analyze_prompt.md   proposal phases 0-3, stop at the gate
  proposal_generate_prompt.md  proposal phases 4-6
  wbs_analyze_prompt.md        WBS phases 0-3, stop at the gate
  wbs_generate_prompt.md       WBS phases 4-7
  static/                      index.html · style.css · app.js  (vanilla-JS SPA, no build)
  workspaces/<id>/             inputs/ · spec/ · output/versions/<n>/   (git-ignored: yours only)
```

Every prompt file is a wrapper that drives the **real skill** head-less and read-only. The web app
holds no copy of the skill logic, so a skill that improves in the repo improves in the UI with no
change here.
