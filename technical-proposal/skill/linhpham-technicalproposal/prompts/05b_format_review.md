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
| `bullets_are_real_lists` | a bullet that is a `●` typed into an ordinary paragraph. The template defines no bullet list, so every bullet was faked until `build_docx.ensure_bullet_numbering` wrote one. Word on a desktop hides it; SharePoint does not, and the reader ends up removing and re-applying every list by hand |
| `bullet_spacing_uniform` | the gap between bullets changing down the page. One delivery carried six different space-before/after pairs because each pass stamped its own and none ran last |
| `heading_number_not_duplicated` | `3.5.1. 4.5.1 Testing Workflow`. A heading that Word numbers must not also carry a typed number; the duplicate stays invisible while the two agree and appears the moment a section is dropped |
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
> patch. The case-study sentence, prose spacing, template table rows and page header are now
> repaired by `scripts/post_assembly.py` inside `finalize.py`; a NEW repair a run discovers goes in
> the run's own `specs/` folder, runs through `finalize.py --post <script>` (it gets the docx path), is listed
> in the Phase 6 report, and is recorded for promotion into `post_assembly.py`. Prefer binding a real `w:hyperlink` to
> a new external relationship in `word/_rels/document.xml.rels` over rebuilding a HYPERLINK field: a
> relationship-backed link renders as a link the moment the file opens, and a field is what the
> run-merge destroyed in the first place.

> **A proposal delivered in another language: review first, translate second, then rebuild the TOC.**
> The skill writes and checks in English, so a run delivered in Vietnamese adds a translation pass
> and a contents rebuild, and the order matters for four reasons, all measured on one run:
> 1. **Run `format_reviewer --strict` BEFORE translating.** `uat_terms_incomplete` and
>    `narrative_length_not_measured` match English phrases; on the translated file they fire as a
>    blocker and a minor while all four UAT terms (14 days, silence means accepted, the 3-week fix
>    window, evidence for a rejection) are present in the translated text. Keep a backup of the
>    reviewed English file next to the output.
> 2. **The template's contents page is a stale cache from another bid** (English titles, sections the
>    proposal does not have, page numbers "?"). SharePoint and every preview show the cache, so it has
>    to be rebuilt by Word (`TablesOfContents.Update` + `Fields.Update` + Save), after translation.
>    Before Word opens the file, inject `<w:doNotAutoCompressPictures/>`; after the save, re-add the
>    settings flags Word stripped. To verify the pictures, compare the dimensions of the pictures the
>    document DISPLAYS (follow each `r:embed` through the part's rels). Do not count `word/media`
>    parts: build_docx leaves about 35 orphaned template pictures behind, Word drops them on save, and
>    a part count reports them as 35 re-encoded images.
> 3. **The rebuilt contents lists the cover.** The template styles the cover title and "Content" as
>    Heading 1 and the two party names in the ISSUED TO / FROM table as Heading 6. A style BASED ON a
>    built-in heading does not help: Word locks its outline level to the heading's and the field's
>    `\u` switch pulls it back in, and a paragraph-level `outlineLvl` is ignored too. What works is a
>    standalone copy of the heading style (same pPr and rPr, no `basedOn` heading, no `outlineLvl`).
>    The same template also types "Project Coordinator" twice in the FROM cell.
> 4. **Set the TOC 1-6 styles to single line spacing through Word** (`doc.Styles(-20 - lvl)`), not
>    from python-docx: they inherit Normal's 1.15, which pushed a 38-entry contents two lines onto a
>    second page. Adding space after made it worse. Word keeps its own per-level indents this way.
>
> **PROMOTED TO CODE 2026-10-20:** `finalize.py` runs this order for both languages (the language
> is a gate decision in `plan.json`); `translate_vi.py` translates, `refresh_toc.py` rebuilds the
> contents for EVERY proposal (the stale cache is in the template, not in the translation), moves
> the cover off the heading styles, sets single spacing and checks every entry names a real
> heading; `format_reviewer` reads the UAT terms and the narrative headings in Vietnamese too.
> Still open: fixing the cover styles in the template itself.
>
> **`translate_vi.py` leaves five optional-section headings in English** (2026-10-20): `Team
> Structure`, `Roles & Responsibilities`, `Milestones & Acceptance`, `Support Model`,
> `References`. Its siblings (`Lộ trình triển khai`, `Mục tiêu mức dịch vụ (SLA)`) are translated,
> so the contents page reads half and half. No check sees it. Repair it in the DELIVERED file, AFTER
> `finalize.py` prints READY, through a run-local script. Then re-run `refresh_toc.py` (the old
> entries are now stale) and `check_consistency.py`. Do NOT rename them through `--post`: that
> runs before the review, and `format_reviewer` finds the optional-section ceilings and the
> Roles table by their ENGLISH heading text, so they would silently go unmeasured. Translations
> used: Cơ cấu đội ngũ · Vai trò và trách nhiệm · Mốc bàn giao và nghiệm thu · Mô hình hỗ trợ ·
> Khách hàng tham chiếu. **⚠ NEEDS CODE PROMOTION: `translate_vi.py` heading dictionary gains these
> five; `format_reviewer._SECTION_WORD_CEILINGS` / `_TABLE_SECTIONS` gain their Vietnamese aliases.**

> **Template tables split their rows; generated tables do not.** `build_docx._harden_table_rows`
> covers the tables it builds, not the branch-model, environment and testing-scope tables the template
> ships, and one of those split a row so that "smoke testing." sat alone at the top of a page. Setting
> `cantSplit` on EVERY row is wrong too: the delivery-process table has 350-character rows with
> bullets, and holding them whole left three half-empty pages in a row. Set `cantSplit` only on tables
> whose longest row is short (300 characters worked), skip one-row caption tables, and on every real
> table mark the first row `tblHeader` with `keepNext` on its paragraphs, so a header never ends a
> page alone and repeats when a long table continues. **Done by `post_assembly.py` (step 2 of
> `finalize.py`) since 2026-10-20.**

> **The page header has room for about 42 characters per line.** It prints `for {PROJECT_TITLE} -
> {CLIENT_NAME}`; a longer title wraps and leaves the last word of the client name alone on a third
> line on every page. `post_assembly.py` drops a parenthetical gloss from the header copy (the cover
> keeps it) and `format_reviewer` reports `page_header_wraps` if the line is still too long; then
> shorten the project title used in the header.

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

> **~~The third standing repair~~ — PROMOTED TO CODE 2026-08-27, no longer a hand repair.**
> A generated table row could break across a page while its cell text stayed perfectly correct.
> `python-docx` writes no row properties, so Word's default let a row split at a page boundary: one
> run shipped "Vitest with React" at the foot of a page and **"Testing Library" alone at the top of
> the next**. Nothing caught it, because `format_reviewer` read the cell TEXT (complete) and the table
> structure (well formed) and never the page. It was hand-repaired in three separate projects' `specs/`
> folders before being fixed at source.
>
> Now `build_docx._harden_table_rows` sets all four properties on every table it generates, so a fresh
> build passes with nothing to do: `w:cantSplit` on every row, `w:tblHeader` on the header so a
> continuation is labelled, `keepNext` on the header row's cell paragraphs so the header cannot sit
> alone at the foot of a page (`tblHeader` alone does NOT prevent that), and a row height stamped as
> **`atLeast`** (never `exact`). The height also closes the SharePoint hand-check above: Word Online
> and SharePoint do not auto-fit, so an unstamped row can render clipped there while it looks right
> locally.
>
> The reviewer check `generated_table_rows` now enforces it, scoped by the generated tables' header
> fill so the template's own tables are never flagged. For a document assembled BEFORE this fix, the
> repair is one command and no longer a bespoke script:
> `python scripts/auto_fix.py --docx <file> --issue generated_table_rows_unhardened`.
> Expect the page count to rise by one or two: a row that would have split now moves whole.
>
> **Look at every figure against the FOOTER, because no check does.** `diagram_check` caps a figure at
> 9.0in and `04_generate.md` said 8.5in, but this template starts the body at 2.12in and puts the
> footer's first line at 10.20in, so the real budget is 7.98in and about 7.6in with the caption. An
> 8.36in flowchart passed the diagram check, passed this review with 0 blockers, and printed over
> "Saigon Technology". Convert the assembled file to PDF and compare every image bbox bottom against
> 10.20in (the probe is in `04_generate.md` gotcha 15); the fix is a smaller `width_inches` on that
> one figure in `diagrams.json`, which is a content change, so it is one of the few cases where
> re-running Phase 5a is correct.
> **Getting the PDF for that probe:** `render_pages.py` keeps only the page PNGs, not the PDF. Call
> its `docx_to_pdf(docx, out_dir)` from a run-local script, and **create `out_dir` first**: with a
> missing folder the Word COM path fails with an opaque `(-2147352567, 'Exception occurred.')` and
> the helper returns `None` (2026-10-20). Contact sheets of eight page PNGs at 600 px wide are
> enough to read every page for layout in a few views; zoom into a page only where a sheet shows
> something odd. **⚠ NEEDS CODE PROMOTION: `render_pages.docx_to_pdf` should `mkdir` its out_dir,
> and `render_pages.py` should keep the PDF.**
> Import it with `sys.dont_write_bytecode = True` so a head-less run does not write `__pycache__`
> into the skill folder. When LibreOffice is absent `docx_to_pdf` falls back to Word COM, which is
> good news: the page PNGs and the PDF are then Word's own layout, the one the client sees.
>
> **Find every word left alone on a line with the same PDF, because the eye misses most of them.**
> A sheet-by-sheet read on one Vietnamese bid spotted three; this probe found twelve in the run's
> own prose (the executive summary's last line "cập.", "cron.", "mobile.", "lịch.", "giờ." in the
> summary, a roles-table cell ending "key)") while every review check passed:
> ```python
> # run-local, on the PDF from docx_to_pdf
> for pno in range(doc.page_count):
>     for b in doc[pno].get_text("dict")["blocks"]:
>         if b.get("type") != 0: continue
>         L = [l for l in ("".join(s["text"] for s in ln["spans"]).strip() for ln in b["lines"]) if l]
>         if len(L) >= 2 and len(L[-1].split()) == 1 and 1.9 < b["bbox"][1] / 72 and b["bbox"][3] / 72 < 10.1:
>             print(pno + 1, L[-2][-40:], "//", L[-1])
> ```
> Fix the hits in content the run wrote by rewording in `make_replacements.py` (shorten the
> sentence by a few characters, or lengthen its tail), then rebuild: it is a content change. Hits in
> the template's verbatim development-management pages and one-word table cells ("QC") are not
> ours to change; list them only if the reader would notice. Expect a rebuild or two, since a
> reworded line can push a different word onto its own line. **⚠ NEEDS CODE PROMOTION:
> `format_reviewer.py --pages` (or `render_pages.py`) should report single-word last lines in
> generated sections as a minor.**
>
> **Read the COVER and the case-study link in the FINAL file, not the reviewed one.** Two things
> change after the review, so `format_review.json` cannot see either:
> 1. The cover line `for {PROJECT_TITLE} - {CLIENT_NAME}` is checked by nothing. On one run it left
>    one word alone on a line. See "`project_title` PRINTS ON EVERY PAGE" in `04_generate.md` for
>    the header and cover repair through `finalize.py --post`.
> 2. `refresh_toc.py`'s Word save rewrites the relationship-backed `w:hyperlink` from
>    `post_assembly.py` into a `HYPERLINK` field. The reviewed copy has one `<w:hyperlink` and the
>    delivered file has none. The link still works in Word, so it is not a defect. But a check
>    that counts `w:hyperlink` or external relationships on the delivered file reports a missing
>    link. Verify it by searching `word/document.xml` for `HYPERLINK "<case_study_url>"`.
>    **⚠ NEEDS CODE PROMOTION: `refresh_toc.py`, either re-bind the relationship after the save
>    or assert the field target.**
>
> **The fourth standing repair: a PROSE section can ship with no paragraph spacing at all, and no
> check measures it.** `build_docx._expand_paragraph_with_value` expands a multi-paragraph value by
> CLONING the template paragraph that held the placeholder, so the section inherits whatever spacing
> that particular slot happens to carry. The SUMMARY slot carries none. On one run the Summary's six
> paragraphs rendered with **zero** gap between them while the other 189 body paragraphs in the same
> document carried 6pt, which is the uneven-whitespace defect the user has flagged, arriving from a
> direction nobody was watching. It only became visible because THE SHAPE FOLLOWS THE CONTENT turned
> that section from bullets into prose, so expect it on any section that changes shape between
> versions. `format_reviewer.py` measures heading spacing, image spacing and caption gaps, never body
> paragraph spacing, so it passed with 0 blockers. Find it by counting:
> ```
> python -c "from docx import Document; from collections import Counter; d=Document(DOCX); \
> print(Counter(p.paragraph_format.space_after for p in d.paragraphs if p.style.name=='Normal'))"
> ```
> One dominant value plus a handful of `None` is the defect, and the `None` group names the section.
> Repair in the delivered file, in the run's own `specs/`: walk from the heading to the next heading
> and set `space_after` to the document's own dominant value on any body paragraph carrying `None`.
> Same ordering as the other three repairs, and list it in the Phase 6 report.
> **⚠ NEEDS CODE PROMOTION: `scripts/build_docx.py::_expand_paragraph_with_value` — when the cloned
> source paragraph carries no explicit `space_after`, stamp the document's body value rather than
> inheriting nothing.**
>
> **`bullet_hanging_indent` can no longer appear in `checks_passed`, and its absence is now the
> PASS.** The gate table above lists it as a check that must be present, and that is no longer
> satisfiable on a normal build: `build_docx.py` gained `convert_glyph_bullets_to_real_lists`, which
> turns every `●` paragraph into a real Word list item, while `check_bullet_hanging_indent` skips any
> paragraph carrying `w:numPr` and only calls `report.pass_` when it measured at least one glyph
> bullet. So a clean build measures zero and reports nothing. Confirm it the right way rather than
> hunting for a check that cannot fire: `build_docx.py` prints `Glyph bullets converted to Word list
> items: N (numId=M)`, and the visual pass shows the hanging indent on a wrapped bullet. Treat the
> check as satisfied when that conversion count is non-zero AND `no_bullet_number_duplicates` passed;
> treat it as a real gap only if glyph bullets survived into the delivered file.
>
> **A footer probe over image bboxes needs one exclusion.** The template's own cover and back-page
> artwork is full-bleed: it starts at the paper edge and is 11.69in tall, so it trips any naive
> "bottom below 10.20in" test and buries the real figures in false positives. Skip an image whose top
> is above about 0.2in AND whose height is over 10in; everything else is a figure this run produced.
>
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
      makes the heading look indented deeper than its own body: wrong visual hierarchy.
- [ ] **Heading space-before respects the floors**: H1-H3 ≥ 24pt, H4-H5 ≥ 18pt,
      H6 ≥ 12pt (`heading_section_spacing_tight`). Cramped section transitions
      make the doc feel like a wall of text.
- [ ] **`settings.xml` contains** `autoHyphenation`, `consecutiveHyphenLimit`,
      `hyphenationZone`, `doNotExpandShiftReturn`, `characterSpacingControl`,
      `updateFields` (`settings_flags_missing`). Missing `doNotExpandShiftReturn`
      is the leading cause of visible whitespace channels in justified
      paragraphs, where justification opens visible channels of white space.
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
