# Phase 5a — Assemble, repair, review and finish (one command)

```
python scripts/finalize.py \
    --docx "<project_dir>/output/{Project} - High Level Technical Proposal.docx" \
    --language <en|vi>                       # from spec/plan.json, confirmed at the gate
    --client "<client name>"                 # required for vi
    --replacements <project_dir>/output/replacements.json \
    --diagrams <project_dir>/output/diagrams/diagrams.json \
    --plan <project_dir>/spec/plan.json \
    [--wbs "<project_dir>/<the WBS workbook>.xlsx"]   # whenever a WBS ships with the bid
    [--pre <project_dir>/output/specs/<custom step>.py]  # a project-specific render, if any
    [--post <project_dir>/output/specs/<repair>.py]      # a project-specific repair of the built file
```

`finalize.py` runs the steps in the only order that works, and stops at the first one that fails:

| # | Step | Script | Both / vi only |
|---|---|---|---|
| 0 | project-specific steps (`--pre`) | the run's own `specs/` | both |
| 1 | assemble | `build_docx.py` | both |
| 2 | repairs only the built file can take: case-study sentence + real hyperlink, prose paragraph spacing, template table rows, page-header length | `post_assembly.py` | both |
| 3 | image spacing | `auto_fix.py --issue image_text_crush` | both |
| 4 | strict format review, must be 0 issues; the reviewed file is kept as `_work/<name>.reviewed.docx` (all working copies go to `_work/`, so the output folder holds one `.docx`) | `format_reviewer.py --strict` | both |
| 5 | translate the template prose, headings, cover and header | `translate_vi.py` | vi |
| 6 | rebuild the contents page in Word (the template ships a stale cache from another bid) | `refresh_toc.py` | both, Windows |
| 7 | stack vs architecture vs figures | `check_consistency.py` | both |
| 8 | proposal vs WBS: quoted totals, cloud named, Out of Scope items | `check_crossdoc.py` | when `--wbs` |

It prints `READY` at the end. Then Phase 5b: render the pages and look at every one.

Why the order matters: `build_docx` reinstates every defect step 2 repairs, so nothing runs
between a rebuild and step 2; two review checks read English template phrases, so the review
runs before translation; a Word save strips settings flags and can re-encode pictures, so the
contents rebuild runs last on the file and verifies every displayed picture kept its size.

When a review issue is fixed in the ASSEMBLED file (a spacing auto-fix), re-run with
`--skip-build` so the fix is not undone. When the fix is a content change (replacements or a
diagram), re-run without it.

`build_docx.py` itself is responsible for:

1. **In-place text replacement** for every key in `replacements.json`.
   Tokens follow the form `{{KEY}}` if present in the template, otherwise
   the script falls back to a positional / heading-based insertion strategy
   (see the script's docstring).
2. **Diagram insertion**. For each entry in `diagrams.json`, find the
   matching heading and insert (in this order): the PNG at the configured
   width (default 6.5 inches), the SEQ-numbered Figure caption table, and
   one justified bullet paragraph per item in `explanation_bullets`. The
   bullets are mandatory professional polish — a diagram without prose
   underneath reads as junior work; aim for 7–17 bullets per diagram.
3. **Formatting pass**:
   - Body paragraphs and bullet text -> justify alignment.
   - Enable `<w:autoHyphenation w:val="true"/>` in `word/settings.xml`.
   - Strip any 1×1 legacy caption tables that the template inherited.
4. **Cleanup**:
   - Inject per-project H6 sub-headings under "2.1.1 System Context" (one
     per diagram in `diagrams.json`).
   - Remove any heading whose body section is empty (e.g. drop Mobile App
     Strategy if `mobile_strategy` is null; drop `{{TECHSTACK_DATA}}` /
     `{{TECHSTACK_AI}}` if those values are null).
5. **Save** the assembled .docx to the requested output path.

> **Path note:** Agent A (Phase 4) writes `diagrams.json` INSIDE the
> `output/diagrams/` folder (alongside the PNGs), so `--diagrams` must point
> to `<project_dir>/output/diagrams/diagrams.json` — not `output/diagrams.json`.
> Passing the wrong path fails with "diagrams missing".

## Do NOT

- Do not modify `templates/proposal_template.docx` — always copy it first.
- Do not embed images at lower than their native resolution. Word handles
  display sizing; let the PNG keep its full pixel data.
- Do not run `build_docx.py`, `translate_vi.py` or `refresh_toc.py` by hand in a different
  order. If a step needs changing, change `finalize.py`.
- Do not translate a file that has not passed the review, and do not review the translated
  file instead: review the English template text, then translate.
