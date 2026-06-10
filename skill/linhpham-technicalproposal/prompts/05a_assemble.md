# Phase 5a — Assemble the final .docx

Run `build_docx.py` with the outputs from Phase 4.

```
python scripts/build_docx.py \
    --template templates/proposal_template.docx \
    --replacements <project_dir>/output/replacements.json \
    --diagrams <project_dir>/output/diagrams.json \
    --out "<project_dir>/output/{Project} - High Level Technical Proposal.docx"
```

`build_docx.py` is responsible for:

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

The script reports paragraphs touched, images embedded, and final file size.

## Do NOT

- Do not modify `templates/proposal_template.docx` — always copy it first.
- Do not embed images at lower than their native resolution. Word handles
  display sizing; let the PNG keep its full pixel data.
- Do not skip the formatting pass — missing justification is the most
  common regression.
