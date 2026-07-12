# STS Claude Code Workflows

A monorepo of reusable Claude Code skills. Each skill lives in its own folder and
deploys independently (a junction/symlink from every local Claude profile to the
skill source, so editing in the repo updates every profile immediately).

## Skills

### `technical-proposal/` — `/linhpham-technicalproposal`
Turns a project folder (RFP + supporting docs) into a SharePoint-compatible
High-Level Technical Proposal `.docx` with senior-SA-grade architecture diagrams:
ingest → analyze → confirm gate → generate (parallel agents) → assemble →
strict format review → report.

Deploy: `cd technical-proposal && python tools/deploy.py`

### `diagram/` — `/linhpham-diagram`
Turns a plain-language description (or a folder of project docs) into a
senior-SA-grade diagram (sharp PNG + editable `.drawio` + `.docx`). Also ships a
local **web app** (`diagram/webapp/`) over the skill: workspaces, a refine gate,
generate, version history/compare, and export.

Deploy: `cd diagram && python tools/deploy.py`
Web app: `cd diagram && python webapp/launch.py` (or `webapp/run.bat` / `run.sh`)

## Layout

```
.
├─ technical-proposal/   # /linhpham-technicalproposal skill + tools + templates
└─ diagram/              # /linhpham-diagram skill + tools + web app
```

Each folder keeps its own `deploy.*`, `.gitignore`, and `LESSONS_LEARNED.md`, so
the two skills stay fully independent inside one repository.
