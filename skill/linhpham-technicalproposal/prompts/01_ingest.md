# Phase 1 — Ingest input files

Read every supported file in `project_dir` and produce a structured
requirements summary for Phase 2.

## File handlers

| Extension | Tool / handler |
|---|---|
| `.pdf` | `Read` tool (built-in PDF reader). For PDFs > 10 pages, paginate via the `pages` argument. |
| `.docx` | `python scripts/readers/docx_reader.py <path>` |
| `.doc` (Word 97-2003) | `python scripts/readers/doc_reader.py <path>` — converts via LibreOffice headless then reads |
| `.xlsx` / `.xls` | `python scripts/readers/xlsx_reader.py <path>` — emits one markdown table per sheet (auto-installs `openpyxl` if missing) |
| `.pptx` | `python scripts/readers/pptx_reader.py <path>` — title + bullets + speaker notes per slide (auto-installs `python-pptx`) |
| `.csv` | `Read` tool (small files), or `python -c "import pandas; print(pandas.read_csv('...').to_markdown())"` for large |
| `.txt` / `.md` | `Read` tool |
| `.png` / `.jpg` / `.jpeg` / `.webp` | `Read` tool (multimodal vision) — captures screenshots of legacy UI, architecture sketches, hand-drawn whiteboards. Caption the image's content in the extract. |
| `.zip` | extract into a tmp folder first, then ingest each contained file with its appropriate handler |

**Skip these artefacts** even if present in the folder: Word lock files
(`~$*.docx`), macOS `.DS_Store`, Windows `Thumbs.db` / `desktop.ini`,
hidden files (`.*`), any file inside an `output/` sub-folder (those are
the skill's own previous-run artefacts, not inputs).

**File priority for §2 conflict resolution** (used by the merge step
below): RFP-named files first (`*RFP*`, `*requirement*`), then any other
`.docx` / `.pdf` / `.md`, then `.xlsx` / `.pptx` / images, then `.txt`
notes. The most-recent modification time wins ties.

## Parallelisation

Spawn one general-purpose subagent per file (in parallel, single message)
when there are 2+ files. Each subagent's job: read its assigned file and
return a structured extract:

```yaml
file: <path>
type: <RFP | brief | reference | constraints | other>
summary: <2-3 sentences>
business_context:
  industry: <e.g. airline, healthcare>
  client: <client name if stated>
  scale: <users / volume hints>
functional_requirements:
  - <bullet>
non_functional:
  performance: <text or null>
  security: <text or null>
  compliance: <text or null>
  availability: <text or null>
constraints:
  tech_stack_forced: <list or null>
  budget: <text or null>
  timeline: <text or null>
  deployment_target: <on-prem | cloud | hybrid | null>
must_haves: [<list>]
nice_to_haves: [<list>]
open_questions: [<list>]  # things the RFP is silent on
```

## Merge step

After all subagents return, the main thread merges into a single
`requirements.json` in memory. Conflicts between sources: prefer the
RFP / most-recent-file. Note conflicts in `open_questions`.

## Do NOT

- Do not propose a tech stack here. Phase 2 does that.
- Do not write any file to disk — keep `requirements.json` in conversation context.
- Do not skip files; if a file is unreadable, report it and continue.
