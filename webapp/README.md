# Diagram-WorkFlow — Web App

A local browser UI over the `linhpham-diagram` skill. One **workspace** per project; each holds
its own inputs and its own generated output.

![AI Workflow Studio web app](static/sample.png)

```
inputs (prompt / uploaded docs / a folder)
  → REFINE    the real skill runs head-less via the `claude` CLI → spec/manifest.json   ⟵ gate
  → confirm / edit the spec in the browser
  → GENERATE  deterministic local Python renderers → output/diagrams/*.png .svg .drawio .docx
  → PREVIEW   view PNGs; iterate (edit prompt/spec, re-run) until happy
  → EXPORT    download a zip of the output folder
```

**Refine** is the only LLM step — it shells out to the installed `claude` CLI (no API key needed),
so the actual skill logic does the classification + spec refinement, then stops at the gate.
**Generate** is pure Python (fast, no LLM) using the skill's `build_cloud` / `build_graph` /
`build_sequence` / `build_diagram_doc` / `diagram_check` scripts.

## Run — one command, self-installing

Move the repo to any machine and just launch it. The first run creates its own
virtual-env, installs every dependency, downloads a portable Graphviz if needed,
starts the server, and opens your browser. Nothing to set up by hand.

- **Windows:** double-click **`webapp/run.bat`** (or `py -3 webapp/launch.py`)
- **macOS / Linux:** `./webapp/run.sh` (or `python3 webapp/launch.py`)

Only prerequisite: **Python 3.10+** on the machine. (The `claude` CLI is needed
for the *Refine* step only — install Claude Code and run `claude` once to log in;
Generate / Preview / Export work without it.)

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
| `DIAGRAM_REFINE_MODEL` | (CLI default) | model passed to `claude -p`, e.g. `sonnet` |
| `DIAGRAM_REFINE_TIMEOUT` | `900` | seconds before a refine run is killed |
| `DIAGRAM_WORKSPACES_DIR` | `webapp/workspaces` | where your workspaces (inputs + output) are stored; set it to keep data outside the repo |

Requirements (already present in this environment): `fastapi`, `uvicorn`, `python-multipart`,
the skill's render deps (`Pillow`, `python-docx`, `openpyxl`, `PyMuPDF`), Graphviz portable on
`~/graphviz_portable/bin`, and the `claude` CLI on `PATH`.

## Layout

```
webapp/
  server.py            FastAPI backend + background jobs
  refine_prompt.md     head-less refine instruction template ({{PLACEHOLDERS}})
  static/              index.html · style.css · app.js  (vanilla-JS SPA, no build)
  workspaces/<id>/     inputs/ · spec/manifest.json · output/diagrams/   (git-ignored)
```
