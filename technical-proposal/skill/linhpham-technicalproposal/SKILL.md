---
name: linhpham-technicalproposal
description: |
  Generate a high-level technical proposal (SharePoint-Online-compatible .docx) from a project folder
  that contains an RFP + supporting docs. Auto-scans the local filesystem for the project folder,
  ingests .pdf/.docx/.doc/.txt/.md, analyzes requirements, proposes a tech stack and architecture,
  asks the user to confirm at a gate, then orchestrates parallel agents to draw professional
  architecture diagrams (Senior-SA-grade) and assemble the final document using a reusable
  stripped template. A strict format-review agent verifies layout, sharpness (>= 300 DPI), and
  SharePoint compatibility before delivering the file.
  Trigger when the user types: /linhpham-technicalproposal <projectname>
---

# linhpham-technicalproposal

> **Status:** scaffold. Implementation in progress — see `docs/IMPLEMENTATION_PLAN.md`.

This skill orchestrates a 6-phase workflow to produce a high-level technical proposal:

```
0 Discover  ->  1 Ingest  ->  2 Analyze  ->  3 Confirm gate  ->  4 Generate (parallel)  ->  5a Assemble  ->  5b Format review  ->  6 Report
```

## How it is invoked

```
/linhpham-technicalproposal <projectname>
```

Claude auto-scans the working directory (and a few well-known project roots) for a folder whose
name fuzzy-matches `<projectname>`. The folder must contain at least one of:

- `*RFP*.pdf` / `*requirement*.pdf` / `*.docx` / `*.doc` / `*.txt` / `*.md`

## Phase prompts

| Phase | File | Purpose |
|---|---|---|
| 0 | `prompts/00_discover.md` | Locate and confirm the project folder |
| 1 | `prompts/01_ingest.md` | Read every input file (parallel subagents) |
| 2 | `prompts/02_analyze.md` | Extract requirements, propose stack + diagrams + outline |
| 3 | `prompts/03_confirm.md` | Human-in-the-loop gate |
| 4 | `prompts/04_generate.md` | Diagram + content + template agents in parallel |
| 5a | `prompts/05a_assemble.md` | Run build_docx.py |
| 5b | `prompts/05b_format_review.md` | Strict format reviewer + auto-fix loop |
| 6 | `prompts/06_report.md` | Final report and caveats |

## Source

This skill is developed in [`linhphamSTS/TechnicalProposal-WorkFlow`](https://github.com/linhphamSTS/TechnicalProposal-WorkFlow).
Run `deploy.bat` (Windows) / `deploy.command` (macOS) / `deploy.sh` (Linux) from the repo root
to install or update the skill into every Claude profile on this machine.
