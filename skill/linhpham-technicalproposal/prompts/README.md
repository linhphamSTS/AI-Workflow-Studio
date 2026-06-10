# Phase prompts

One file per workflow phase. Each prompt is a self-contained instruction block that the main
Claude conversation reads at the right moment in the pipeline.

| File | Phase |
|---|---|
| `00_discover.md` | Find and confirm the project folder |
| `01_ingest.md` | Read every input file (parallel subagents) |
| `02_analyze.md` | Extract requirements, propose stack + diagrams + outline |
| `03_confirm.md` | Human-in-the-loop gate |
| `04_generate.md` | Diagram + content + template agents in parallel |
| `05a_assemble.md` | Run build_docx.py |
| `05b_format_review.md` | Strict format reviewer + auto-fix loop |
| `06_report.md` | Final report and caveats |

> Scaffold only — implementation pending.
