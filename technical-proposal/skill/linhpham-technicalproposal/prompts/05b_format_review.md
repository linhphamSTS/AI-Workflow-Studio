# Phase 5b — Format review (strict)

## First, do the stack and the architecture agree?

```
python scripts/check_consistency.py --plan spec/plan.json        --diagrams output/diagrams/diagrams.json        --docx "output/<Project>.docx"
```

**Run this before reading anything else, and exit 0 before shipping.** The stack, the
architecture prose and the figures come from different steps and nothing else compares them,
so they can disagree while every artefact looks correct on its own. Two failures it exists
for, both of which have reached a client:

* **two clouds in one bid.** The stack chooses one provider and a figure is drawn from
  another's template. No single document contains the contradiction, so a page-by-page read
  never finds it, and a reader who does find it concludes the bidder does not know what they
  are proposing.
* **a figure promising what the stack cannot deliver.** A box reading `Kafka protocol stream`
  and `Schema registry` beside a stack row naming a plain message queue commits to a
  replayable log and schema governance that nothing in the build provides. The figure is what
  an evaluator believes, so the stack has to be able to honour it.

Run it again after any edit to the stack, the architecture or a diagram. Changing one of the
three is exactly when they stop agreeing.


A dedicated subagent ("format-reviewer", general-purpose) audits the
assembled .docx and either signs it off, applies auto-fixes, or surfaces
manual-only issues.

## DOCX FORMAT GATE — what "the format is correct" actually means

`format_reviewer.py` must end with **0 blockers**, and these named checks must appear in
`checks_passed`. A run that skips one has not verified the format, it has only not looked:

| Check | What it prevents |
|---|---|
| `zip_integrity`, `not_encrypted`, `no_macros` | a file SharePoint refuses or flags |
| `placeholders_filled` | a literal `{{KEY}}` reaching the client |
| `images_all_embedded` | a figure that renders for us and not for them |
| `bullet_hanging_indent` | a wrapped bullet whose second line falls back to the left margin. 54 bullets had the indent and 140 did not on one delivery, which reads worse than none of them having it |
| `no_bullet_number_duplicates` | "● 1. text", a glyph bullet inside a Word list |
| `techstack_is_table`, `team_roles_is_table` | a section that should be a table shipping as prose |
| `heading_section_spacing_ok`, `heading_indent_consistent` | a heading gap that reads as a blank line, or a heading indented deeper than its body |
| `image_spacing_ok`, `caption_gap_ok` | text crushed against a figure or its caption |
| `body_justified`, `justify_whitespace_neutralised` | rivers of white space down a justified column |
| `em_dash_prose_ok`, `latin_abbreviation_ok` | the two constructions that read as machine-written |
| `optional_section_length`, `narrative_length` | a section past its word ceiling |

**Two things the reviewer cannot see, so check them by hand:**
1. **Every row needs a stamped height.** python-docx writes none, and Word Online and
   SharePoint do not auto-fit, so a wrapped cell renders clipped. This bites any generated
   `.docx`, not only this one.
2. **A heading with an empty body.** A populated content key with no `{{KEY}}` slot leaves a
   bare heading; `validate_template_placeholders()` in `build_docx.py` fails the build for
   that reason, so do not bypass it.

**`image_low_resolution` on template art and in-table logos is NOT a defect.** Those assets
are not produced by the run and cannot be changed from here. Judge only the figures this run
generated: each must be at least 300 DPI at the 6.5in embed and must fit one page.

Run order matters and is not idempotent: `build_docx.py`, then any post-assembly patch, then
`auto_fix.py`, then review. **Do not rebuild after `auto_fix`** or the fixes are undone.


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
   - **Do NOT re-run Phase 5a for spacing/formatting auto-fixes** (`image_text_crush`,
     `heading_section_spacing_tight`, and any patch that only adjusts paragraph
     spacing). `build_docx.py` regenerates image-paragraph spacing from the template
     on every build, so re-running 5a *re-introduces* the exact defect `auto_fix.py`
     just cleared. Instead, apply the patch to the ALREADY-ASSEMBLED docx and go
     straight to re-rendering + re-review (step 1-3). Only re-run Phase 5a when the
     fix requires regenerating content/structure (e.g. `techstack_not_table` needs a
     new `replacements.json` value, or a diagram must be re-rendered) — a content
     change, not a spacing patch.
   - Re-run steps 1-3 (render pages, run the reviewer, inspect visually).
   - If after 2 iterations issues remain -> escalate to the user with a
     prioritised list.

> **Ordering rule for a post-assembly repair.** When Phase 5a leaves a defect that can only be fixed
> in the DELIVERED file (the CASE STUDY sentence and its hyperlink is the standing example: the
> template ships `...{{CASE_STUDY_TITLE}}.this link` and `build_docx.py` flattens the HYPERLINK field
> into plain text), the repair script runs **after `build_docx.py` and before `auto_fix.py`**, then
> render and review as normal. Such a patch is NOT idempotent against a rebuild, so re-running Phase
> 5a silently reinstates the defect — the same trap as the spacing auto-fix rule above, different
> patch. Keep the script in the run's own `specs/` folder, never in the skill, and list it in the
> Phase 6 report so the fix is visible rather than mysterious. Prefer binding a real `w:hyperlink` to
> a new external relationship in `word/_rels/document.xml.rels` over rebuilding a HYPERLINK field: a
> relationship-backed link renders as a link the moment the file opens, and a field is what the
> run-merge destroyed in the first place.

> **The second standing repair: `team_roles_not_table` cannot be fixed by fixing the content.**
> `build_docx.py` and `format_reviewer.py` currently contradict each other here, so expect this
> blocker on any bid whose `team_roles` is the required `{name, description}` array.
> `render_techstack_tables` builds the `Role | Accountability` table and then sets
> `replacements["team_roles"] = ""` so the text pass skips it; its own docstring says the caller
> must therefore skip the optional-section drop, but the caller only does that for
> `techstack_data` and `techstack_ai` in `drop_specs`. The `OPTIONAL_SECTION_GROUPS` pass still
> calls `drop_section_if_empty("Roles & Responsibilities", replacements, "team_roles")`, reads the
> blanked value, decides the section is empty and deletes **the heading together with the table it
> just built**. So the section vanishes and the check fires no matter how correct the content is.
> **Do not "fix" it by reverting `team_roles` to bullet strings** — that satisfies the drop pass
> and re-fires the blocker.
>
> Diagnose before repairing: monkeypatch `drop_section_if_empty` to print its heading, key and the
> type of the value it read, and the mechanism names itself in one line
> (`DROPPED: 'Roles & Responsibilities' key='team_roles' value=str`). Guessing from the symptom
> costs a rebuild each time.
>
> Repair it in the delivered file, in the run's own `specs/`, and build the table by calling the
> skill's **own** `build_docx._build_techstack_table` with
> `build_docx._EXTRA_TABLE_KEYS["team_roles"]`, so the borders, shaded header and column widths are
> identical to the technology tables. A second hand-rolled table renderer is how a document ends up
> with two table styles. Clone the sibling H5 paragraph for the heading so style and numbering
> carry over, then set its space-before to the H4/H5 floor of 8pt yourself: the sibling
> ("Team Structure") sits directly under the H3 and therefore carries the reduced 4pt that groups a
> heading with its parent, which would fire `heading_section_spacing_tight` on the clone. Fixing it
> in the repair script rather than leaning on `auto_fix.py` keeps the reproduction recipe to one
> pass. Same ordering as the case-study repair: after `build_docx.py`, before `auto_fix.py`, and
> list it in the Phase 6 report. Record the underlying one-line script fix as
> `⚠ NEEDS CODE PROMOTION` rather than editing the script in an unattended run.

> **`narrative_length_not_measured` is a signal, not noise.** `check_narrative_length` matches a
> section by its heading text, lowercased, against `_NARRATIVE_CEILINGS` and `_PER_BULLET_CEILINGS`.
> When it can match nothing it emits this minor deliberately, because silence would be
> indistinguishable from a clean pass on a document whose headings were renamed, which is how a check
> quietly becomes a no-op. If you see it, the ceilings were not applied to anything: find the renamed
> heading before you accept the review. The same applies to `optional_section_length`, which has no
> such guard, so a renamed optional heading passes it silently.

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

> **Known false positive — `external_image_ref`.** `check_no_external_images` tests
> `'TargetMode="External"' in data and "image" in data.lower()` over the WHOLE `.rels`
> file rather than per relationship, so ANY document that has embedded images (they all
> do) plus ANY external **hyperlink** trips it. Before treating it as a defect, list the
> external relationships and read their `Type`:
> ```
> python -c "import zipfile,re;d=zipfile.ZipFile(DOCX).read('word/_rels/document.xml.rels').decode();print(re.findall(r'<Relationship[^>]*TargetMode=\"External\"[^>]*/>',d))"
> ```
> If every hit is `.../relationships/hyperlink`, the document is clean: say so explicitly
> in the Phase 6 report (with the relationship listed) rather than removing a working link
> to silence the check.

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

> **Known noise — `image_low_resolution` on template assets.** `check_image_sharpness` audits every
> image in `word/media/`, which includes the template's own decorative artwork and the ~150 px to
> 256 px technology logos that `build_docx.py` embeds in the Technology Stack tables. On a normal
> build those account for essentially all of the flagged images, and re-rendering an architecture
> figure will not change the count. Confirm rather than assume, then say so explicitly in the Phase 6
> report instead of listing them as defects:
> ```
> python -c "import zipfile,io;from PIL import Image;z=zipfile.ZipFile(DOCX);print(sorted((Image.open(io.BytesIO(z.read(n))).size[0],n) for n in z.namelist() if n.startswith('word/media/')))"
> ```
> The architecture figures should all be >= 1950 px wide. If one of THEM appears in the flagged set,
> that is a real defect: re-render it, do not waive it.

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
`heading_deeper_than_body`, `heading_section_spacing_tight`,
`settings_flags_missing`, and `techstack_not_table` are all clear in
`format_review.json`.

- [ ] **Every Technology Stack sub-section (Back-end / Front-end / Database /
      Server & Hosting / Data / AI) renders as a 2-column `Technology |
      Advantages` table, not a prose paragraph** (`techstack_not_table`). This
      is the required professional table format. It is NOT auto-fixable — it means the
      content-writer emitted a prose string instead of the required array of
      `{name, description}` rows; the fix is to regenerate that techstack value
      as an array and rebuild. Escalate if it survives.

## Output

- `format_review.json` (machine readable, consumed by auto_fix.py)
- `format_review.md` (human readable, consumed by Phase 6's report)
- An `auto_fixes_applied` log if any patches were applied.
