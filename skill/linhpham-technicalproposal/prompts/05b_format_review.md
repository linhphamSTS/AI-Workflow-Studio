# Phase 5b — Format review (strict)

A dedicated subagent ("format-reviewer", general-purpose) audits the
assembled .docx and either signs it off, applies auto-fixes, or surfaces
manual-only issues.

## Inputs

- Path to the assembled .docx from Phase 5a.
- `manifest.json` listing the diagrams that should be present.

## Steps the agent runs

1. **Render to PDF then per-page PNG** at 300 DPI:
   ```
   python scripts/render_pages.py --in <docx> --out <project_dir>/output/_review/
   ```
   The script calls LibreOffice headless to make a PDF, then `pdf2image` (Poppler)
   to slice each page into a PNG at 300 DPI.

2. **Run the structural / programmatic checks**:
   ```
   python scripts/format_reviewer.py --docx <docx> --pages <project_dir>/output/_review/ \
       --strict --json <project_dir>/output/format_review.json
   ```
   The strict checklist runs the items in the next section. The script emits a
   JSON report; the agent reads it.

3. **Visually inspect every page PNG with the `Read` tool**. The
   programmatic check catches structural issues; the visual check catches
   layout regressions a programmatic check cannot see (e.g. a chart that
   accidentally sits over a footer).

4. **Auto-fix loop** (max 2 iterations):
   - For each `auto_fixable` issue in the JSON report, apply the patch via
     `python scripts/auto_fix.py --docx <docx> --issue <issue_id>`.
   - Re-run Phase 5a to rebuild.
   - Re-run steps 1-3.
   - If after 2 iterations issues remain -> escalate to the user with a
     prioritised list.

## Strict checklist (the bar is high)

### Layout

- [ ] No heading sits on the last line of a page with its body on the next page (orphan heading).
- [ ] No widow / orphan single lines.
- [ ] No diagram overflows the left / right margin.
- [ ] No diagram is split across two pages.
- [ ] No table extends past the right margin.
- [ ] Each top-level Heading 1 starts on a new page (page-break-before).

### Visual quality

- [ ] Body font and size are consistent (no random Arial in a Calibri document).
- [ ] Heading colours follow the template theme.
- [ ] Paragraph spacing is consistent (no double-blank gaps).
- [ ] Bullet indent is uniform within each list.
- [ ] Body text and multi-line bullets use justify alignment.
- [ ] Every embedded diagram is sharp (no obvious aliasing at 100% page view).
- [ ] Every caption follows `Figure N: Type — Scope`.

### SharePoint Online compatibility

- [ ] File size < 100 MB. Warn if > 25 MB.
- [ ] Zip integrity passes (`zipfile.testzip()`).
- [ ] Track changes: 0 revisions.
- [ ] Zero comments.
- [ ] Not a `.docm` (no macros).
- [ ] No encryption / password.
- [ ] No broken internal references (TOC entries, bookmarks).
- [ ] No externally linked images — every image must be embedded.
- [ ] Custom XML schemas section is clean.

### Professional polish

- [ ] No literal `{{...}}` placeholder remains.
- [ ] No literal `{{KEY}}` placeholder remains (programmatic check `placeholders` covers this).
- [ ] Header / footer has the project name and page numbers.
- [ ] No obvious heading typos.

### Bullets, headings, image-text rhythm (post-2026-05-25 user feedback)

The user has flagged these specific defects with **zero tolerance**. The
reviewer MUST NOT issue a PASS while any of them is present in the JSON
report — auto-fix them first, then re-verify visually.

- [ ] **No "● 1. text" or "● Step 1 — text" bullets** (`bullet_number_duplicate`).
      Bullets carry the `●` glyph from the renderer; the content must not
      add a manual number on top. If the content-writer agent has stacked
      two numberings (e.g. `● 1. Step 1 — text`), auto-fix loops the strip
      pass until neither remains.
- [ ] **Every diagram image has ≥ 12pt space-before and ≥ 6pt space-after**
      (`image_text_crush`). An image touching its intro sentence or its
      bullet list is a presentation defect.
- [ ] **No heading is left-indented deeper than the body text it introduces**
      (`heading_deeper_than_body`). Heading 5 at L=36pt over body at L=0pt
      reads as "title thụt vô sâu hơn text" — wrong visual hierarchy.
- [ ] **Heading space-before respects the floors**: H1-H3 ≥ 24pt, H4-H5 ≥ 18pt,
      H6 ≥ 12pt (`heading_section_spacing_tight`). Cramped section transitions
      make the doc feel like a wall of text.
- [ ] **`settings.xml` contains** `autoHyphenation`, `consecutiveHyphenLimit`,
      `hyphenationZone`, `doNotExpandShiftReturn`, `characterSpacingControl`,
      `updateFields` (`settings_flags_missing`). Missing `doNotExpandShiftReturn`
      is the leading cause of visible whitespace channels in justified
      paragraphs ("chữ chứa khoảng trắng khi canh đều").
- [ ] **No "● Step N —"** even after auto-fix, since the Phase-4 content-writer
      should now follow the updated rule in `04_generate.md` not to manually
      number bullet items. If this regression survives the auto-fix loop,
      escalate to the user — the content-writer prompt may need tightening
      again.

### Sharpness audit (image-specific)

For every embedded image, the format reviewer must:

- Decode it from the docx ZIP under `word/media/`.
- Confirm pixel width >= 1500 px (sharp at 6.5 in Word display).
- If lower -> mark as `image_low_resolution` and flag for re-render.

## Strictness mode

Default = **strict**. Items flagged in strict mode:

- widow / orphan single lines,
- font drift of even 1 pt,
- spacing inconsistencies of >= 1 pt,
- a single un-justified body paragraph in a section that justifies others,
- **ANY bullet+number duplicate, image-text crush, deeper-indented heading,
  cramped heading spacing, or missing settings flag** — these are the
  defects the user has flagged with zero tolerance.

The user has accepted slower iterations for a higher quality bar. Do not
soften the checklist without a direct instruction. **Reviewer agents MUST
NOT report PASS** until `bullet_number_duplicate`, `image_text_crush`,
`heading_deeper_than_body`, `heading_section_spacing_tight`, and
`settings_flags_missing` are all clear in `format_review.json`.

## Output

- `format_review.json` (machine readable, consumed by auto_fix.py)
- `format_review.md` (human readable, consumed by Phase 6's report)
- An `auto_fixes_applied` log if any patches were applied.
