#!/usr/bin/env python3
"""Assemble a project's High-Level Technical Proposal .docx.

Inputs:
  --template       path to proposal_template.docx (the reusable template)
  --replacements   JSON dict: keys -> values to substitute in the template
  --diagrams       JSON list: each entry {slug, png, caption, target_heading}
  --out            output .docx path

Behaviour:
  1. Copy template to output path.
  2. Substitute every {{KEY}} token in body / header / footer / tables with
     the matching value from replacements.json, preserving run formatting
     where practical. (Cover-page client / project / version live in the
     template as {{KEY}} placeholders, so step 2 handles them too.)
  3. Inject the per-project H6 sub-headings under "System Overview" — one
     for each entry in diagrams.json, in order, placed after "2.1.1 System
     Context".
  4. For each diagram: find the heading whose text matches target_heading
     (case-insensitive contains match) and insert the PNG immediately after,
     followed by a Caption-styled paragraph.
  5. Drop empty optional sections (Mobile App Strategy if mobile_strategy is
     null; tech-stack Data/AI placeholders if those values are null).
  6. Justify body paragraphs and bullet text.
  7. Enable autoHyphenation + updateFields in word/settings.xml so the TOC
     refreshes the first time the user opens the file.
  8. Save.

The script is intentionally generic — no customer-, vendor-, or project-
specific strings live in this file.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_][A-Z0-9_]*)\}\}")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")

# Anchor heading the dynamic H6 inject step (step 3) targets.
SUBHEADING_ANCHOR = "2.1.1 System Context"


def _render_inline_markdown_into(p_el, text: str) -> None:
    """Replace runs in p_el with new runs that interpret **bold** markdown.
    Existing runs are cleared first; the resulting paragraph keeps its
    paragraph properties (style, alignment, spacing) intact."""
    from docx.oxml import OxmlElement
    # Snapshot the first run's rPr (if any) so the new runs inherit base font.
    first_r = p_el.find(qn("w:r"))
    base_rPr = first_r.find(qn("w:rPr")) if first_r is not None else None
    # Drop all existing runs.
    for r in p_el.findall(qn("w:r")):
        p_el.remove(r)

    def add_run(segment: str, bold: bool) -> None:
        if segment == "":
            return
        r = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        # Inherit base font properties (size, font family) from the cleared run.
        if base_rPr is not None:
            for child in base_rPr:
                tag = child.tag.rsplit("}", 1)[-1]
                if tag in ("b", "i"):
                    continue  # we set bold explicitly
                import copy as _copy
                rPr.append(_copy.deepcopy(child))
        if bold:
            rPr.append(OxmlElement("w:b"))
        if len(rPr):
            r.append(rPr)
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = segment
        r.append(t)
        p_el.append(r)

    # Split text on **...** markers.
    pos = 0
    for m in BOLD_RE.finditer(text):
        if m.start() > pos:
            add_run(text[pos:m.start()], bold=False)
        add_run(m.group(1), bold=True)
        pos = m.end()
    if pos < len(text):
        add_run(text[pos:], bold=False)


def _expand_paragraph_with_value(p_el, value: str) -> None:
    """Render `value` into the document at p_el's position, splitting on
    newlines so each line becomes its own paragraph, and interpreting
    `**bold**` markdown inside each line. Cloned paragraphs inherit the
    style + spacing of p_el so the visual rhythm stays consistent."""
    import copy as _copy
    lines = value.split("\n")
    if not lines:
        lines = [""]
    _render_inline_markdown_into(p_el, lines[0])
    cursor = p_el
    for line in lines[1:]:
        new_p = _copy.deepcopy(p_el)
        # Strip any sectPr from the clone so we don't duplicate section breaks.
        for sp in new_p.findall(".//" + qn("w:sectPr")):
            sp.getparent().remove(sp)
        _render_inline_markdown_into(new_p, line)
        cursor.addnext(new_p)
        cursor = new_p


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def style_id_to_name(doc) -> dict:
    return {s.style_id: s.name for s in doc.styles if getattr(s, "style_id", None)}


def is_heading(paragraph, name_map: dict) -> int | None:
    style = paragraph.style.name if paragraph.style else None
    if style and style.startswith("Heading"):
        try:
            return int(style.split()[-1])
        except ValueError:
            return None
    return None


def _stringify_value(val):
    """Render a replacement value (str / list / dict) into the multi-line
    markdown string that `_expand_paragraph_with_value` can lay out.

    - str           → as-is
    - list[dict] with problem/solution keys → 2 lines per entry
                                              ("● <problem>" / "**Solution:** <s>")
    - list[str]     → "● <item>" lines
    - list[other]   → "● <repr>" lines
    - dict          → "**key:** value" lines
    - None          → None (caller handles drop)
    """
    if val is None:
        return None
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        if not val:
            return ""
        if all(isinstance(it, dict) and "problem" in it and "solution" in it for it in val):
            chunks = []
            for it in val:
                # Replace "**Bold Title** — body" with "**Bold Title**: body"
                # User feedback: em-dash after bold title in P&S bullets reads
                # AI-generated; colon is the preferred separator.
                prob = re.sub(r'(\*\*[^*]+\*\*)\s*—\s*', r'\1: ', it['problem'], count=1)
                sol  = re.sub(r'(\*\*[^*]+\*\*)\s*—\s*', r'\1: ', it['solution'], count=1)
                chunks.append(f"●	{prob}")
                chunks.append(f"**Solution:** {sol}")
            return "\n".join(chunks)
        lines = []
        for it in val:
            if isinstance(it, str):
                lines.append(f"●	{it}")
            elif isinstance(it, dict):
                lines.append("●	" + "; ".join(f"**{k}:** {v}" for k, v in it.items()))
            else:
                lines.append(f"●	{it}")
        return "\n".join(lines)
    if isinstance(val, dict):
        return "\n".join(f"**{k}:** {v}" for k, v in val.items())
    return str(val)


def replace_in_paragraph(paragraph, mapping: dict[str, str]) -> int:
    """Replace {{KEY}} tokens in a paragraph's runs. Returns count replaced.

    We work on the joined text first, then write the result back into the
    first run and clear the others. This loses per-token formatting inside
    the affected runs but preserves the paragraph style. For the proposal
    template this is acceptable — placeholders sit inside Normal text.
    """
    joined = "".join(r.text or "" for r in paragraph.runs)
    if not joined:
        return 0

    count = 0

    def sub(m):
        nonlocal count
        key = m.group(1).lower()
        if key in mapping:
            val = mapping[key]
            if val is None:
                # Leave the placeholder so drop_section_if_empty can remove the
                # surrounding heading + body cleanly. str(None) would silently
                # litter the document with the word "None".
                return m.group(0)
            count += 1
            return _stringify_value(val)
        return m.group(0)

    new = PLACEHOLDER_RE.sub(sub, joined)

    if new == joined:
        return 0

    runs = paragraph.runs
    if not runs:
        return 0
    # If the replaced text carries multi-paragraph content (\n) or bold
    # markdown (**...**), render it properly into the document instead of
    # collapsing into one runs[0].text. Otherwise fall back to the simple
    # path — keeps run formatting for plain substitutions.
    if "\n" in new or "**" in new:
        _expand_paragraph_with_value(paragraph._p, new)
        return count
    runs[0].text = new
    for r in runs[1:]:
        r.text = ""
    return count


def replace_in_table(table, mapping: dict[str, str]) -> int:
    total = 0
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                total += replace_in_paragraph(p, mapping)
            for nested in cell.tables:
                total += replace_in_table(nested, mapping)
    return total


def replace_in_section_parts(section, mapping: dict[str, str]) -> int:
    """Replace in header / footer (default + first-page + even)."""
    total = 0
    for part in (section.header, section.footer, section.first_page_header,
                 section.first_page_footer, section.even_page_header, section.even_page_footer):
        try:
            for p in part.paragraphs:
                total += replace_in_paragraph(p, mapping)
            for t in part.tables:
                total += replace_in_table(t, mapping)
        except Exception:
            # Section may not have all part types; ignore.
            pass
    return total


def clone_paragraph_after(anchor_p, new_text: str):
    """Clone the anchor paragraph (style + format preserved), set its text, and
    insert it immediately after the anchor. Returns the new paragraph element."""
    import copy as _copy
    new_el = _copy.deepcopy(anchor_p._p)
    runs = new_el.findall(qn("w:r"))
    set_once = False
    for r in runs:
        for t in r.findall(qn("w:t")):
            if not set_once:
                t.text = new_text
                set_once = True
            else:
                t.text = ""
    if not set_once and runs:
        from docx.oxml import OxmlElement
        t = OxmlElement("w:t")
        t.text = new_text
        runs[0].append(t)
    anchor_p._p.addnext(new_el)
    return new_el


def inject_subheadings_after_anchor(doc, anchor_text: str, subheadings: list[str]) -> int:
    """Insert one H6 paragraph per item in `subheadings` after the anchor heading.

    Auto-renumbers each injected sub-heading sequentially starting from the
    anchor's number + 1, so there are no gaps even if upstream content
    skipped or reordered entries. Stripped from each input string:
    any existing 'N.N.N' prefix.
    """
    anchor = find_heading_paragraph(doc, anchor_text)
    if anchor is None or not subheadings:
        return 0

    # Parse anchor's numbering ("2.1.1 System Context" -> prefix "2.1.", next 2)
    m = re.match(r"\s*(\d+(?:\.\d+)*)\.(\d+)\s+", anchor_text)
    if m:
        prefix = m.group(1) + "."
        start = int(m.group(2)) + 1
    else:
        prefix = ""
        start = 1

    renumbered = []
    for i, text in enumerate(subheadings):
        clean = re.sub(r"^\s*\d+(\.\d+)*\s*[.:)-]?\s*", "", text).strip()
        renumbered.append(f"{prefix}{start + i} {clean}" if prefix else clean)

    # Insert in reverse so document order matches input order.
    for text in reversed(renumbered):
        clone_paragraph_after(anchor, text)
    return len(renumbered)


def find_heading_paragraph(doc, target: str):
    """Find the first heading paragraph whose text contains `target` (case-insensitive)."""
    target_norm = target.lower().strip()
    for p in doc.paragraphs:
        if p.style and p.style.name and p.style.name.startswith("Heading"):
            if target_norm in p.text.lower():
                return p
    return None


def insert_after_paragraph(paragraph, new_element) -> None:
    """Insert raw XML element immediately after `paragraph` in the body."""
    paragraph._p.addnext(new_element)


def _build_seq_caption_table(doc, title: str):
    """Clone an existing 1x1 caption table from the document and put
    'Figure <SEQ Figure>: <title>' inside its single cell. Returns the new
    table element ready to be inserted into the body.

    Cloning preserves the template's bordered/shaded cell style so every
    figure in the document — verbatim Section 3 plus Phase-4-inserted
    Section 2 diagrams — looks identical."""
    import copy as _copy
    from docx.oxml import OxmlElement

    # Find a sample 1x1 caption table in the doc to clone.
    sample = None
    for t in doc.tables:
        if len(t.rows) == 1 and len(t.columns) == 1:
            txt = t.rows[0].cells[0].text.strip()
            if txt:
                sample = t
                break
    if sample is None:
        return None

    new_tbl = _copy.deepcopy(sample._tbl)
    # Wipe existing text in the clone.
    for tn in new_tbl.iter(qn("w:t")):
        tn.text = ""
    # Find the target paragraph inside the single cell.
    cell_p = next(iter(new_tbl.iter(qn("w:p"))), None)
    if cell_p is None:
        return new_tbl
    # Take the first existing run's rPr as the formatting template for SEQ runs.
    first_r = cell_p.find(qn("w:r"))
    rpr_tmpl = first_r.find(qn("w:rPr")) if first_r is not None else None

    def text_run(text: str):
        r = OxmlElement("w:r")
        if rpr_tmpl is not None:
            r.append(_copy.deepcopy(rpr_tmpl))
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = text
        r.append(t)
        return r

    def fld_run(ftype: str):
        r = OxmlElement("w:r")
        fc = OxmlElement("w:fldChar")
        fc.set(qn("w:fldCharType"), ftype)
        if ftype == "begin":
            fc.set(qn("w:dirty"), "true")
        r.append(fc)
        return r

    def instr_run(text: str):
        r = OxmlElement("w:r")
        it = OxmlElement("w:instrText")
        it.set(qn("xml:space"), "preserve")
        it.text = text
        r.append(it)
        return r

    # Remove any leftover runs so the cell paragraph starts empty.
    for r in cell_p.findall(qn("w:r")):
        cell_p.remove(r)
    cell_p.append(text_run("Figure "))
    cell_p.append(fld_run("begin"))
    cell_p.append(instr_run(r" SEQ Figure \* ARABIC "))
    cell_p.append(fld_run("separate"))
    cell_p.append(text_run("1"))
    cell_p.append(fld_run("end"))
    cell_p.append(text_run(f": {title}"))
    return new_tbl


# Patterns the content-writer agent emits at the start of bullet items
# that we MUST strip so the rendered bullet doesn't read "●  1. text" or
# "●  Step 1 — text" (the user-flagged duplicate-numbering bug).
#
# Critically, we must NOT destroy the bold component label. Inputs like
#   "1. **Step 1 — Bank API POST** — body"
# should become
#   "**Bank API POST** — body"
# — i.e. strip ONLY the manual numbering, including the "Step 1 — " prefix
# inside the bold span. The bold-wrapped title text must survive.

# Plain manual numbering at the start of the string (no surrounding emphasis).
_PLAIN_NUMBER_RE = re.compile(
    r"^\s*(?:"
    r"\(?\d{1,3}\)?\s*[.)\-:]\s+"              # "1. "  "(1) "  "1) "  "1 - "
    r"|step\s+\d{1,3}[a-z]?\s*[.)\-:—]\s+"     # "Step 1 — "  "Step 2a — "
    r")",
    re.IGNORECASE,
)

# Manual numbering INSIDE a leading bold/italic span. We match the opening
# emphasis marker + the numbering, then re-emit the opening marker so the
# title text immediately following stays bold. Example:
#   "**Step 1 — Bank API**"
# becomes (after re.sub):
#   "**Bank API**"
_INSIDE_EMPH_NUMBER_RE = re.compile(
    r"^(\s*)(\*\*|__|\*|_)\s*"
    r"(?:"
    r"\(?\d{1,3}\)?\s*[.)\-:]\s+"
    r"|step\s+\d{1,3}[a-z]?\s*[.)\-:—]\s+"
    r")",
    re.IGNORECASE,
)


def _strip_manual_numbering(text: str) -> str:
    """Remove ALL leading manual numbering from a bullet item while
    preserving the bold component label.

    Two patterns per pass:
      1. "1. " / "Step 1 — " at the very start → strip outright
      2. "**Step 1 — title**" / "**1. title**" → strip ONLY the numbering
         from inside the bold span, leaving "**title**" intact

    Loops because the content-writer agent stacks (e.g. "1. **Step 1 — title**")
    — one pass strips the leading "1. ", the next strips the "Step 1 — "
    from inside the bold span.
    """
    if not text:
        return text
    stripped = text.lstrip()
    while stripped.startswith("●"):
        stripped = stripped[1:].lstrip()
    for _ in range(4):
        # Strip "**Step 1 — " → "**" first so the title stays bold-wrapped.
        m = _INSIDE_EMPH_NUMBER_RE.match(stripped)
        if m:
            stripped = m.group(1) + m.group(2) + stripped[m.end():]
            stripped = stripped.lstrip()
            continue
        m = _PLAIN_NUMBER_RE.match(stripped)
        if m:
            stripped = stripped[m.end():].lstrip()
            continue
        break
    return _label_dash_to_colon(stripped.strip())


def _label_dash_to_colon(text: str) -> str:
    """Turn a `**Label** — description` bullet into `**Label**: description`.

    A spaced em-dash is one of the clearest tells of machine-written prose and the
    client rejects it on sight, so 04_generate.md forbids it outright. This is the
    defensive net: it only rewrites the STRUCTURAL separator after a bold label,
    which is a mechanical substitution with one right answer. A mid-sentence dash
    needs a judgement call between a comma, a semicolon and two sentences, so that
    one is left to the writer and caught by `format_reviewer.check_em_dash_in_prose`.
    """
    if not text:
        return text
    return re.sub(r'(\*\*[^*]+\*\*)\s*[—–]\s*', r'\1: ', text, count=1)


def _build_bullet_paragraph(text: str, *, is_first: bool = False):
    """Construct a justified body paragraph for a diagram explanation bullet.
    Strips any manual numbering the agent prefixed (avoids "● 1. text"
    duplication), prepends "●  ", then renders `**bold**` inline markdown.

    is_first=True: this is the bullet immediately after a Figure caption
    table. The table cannot carry `space_after`, so the first bullet must
    declare a larger `space_before` to create the breathing gap between
    caption and first bullet that the user has flagged as missing.
    """
    from docx.oxml import OxmlElement
    p = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")
    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:before"), "240" if is_first else "0")  # 12pt before first
    spacing.set(qn("w:after"), "120")
    spacing.set(qn("w:line"), "276")
    spacing.set(qn("w:lineRule"), "auto")
    pPr.append(spacing)
    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), "both")
    pPr.append(jc)
    ind = OxmlElement("w:ind")
    ind.set(qn("w:left"), "280")     # tighter left indent (was 360)
    ind.set(qn("w:hanging"), "200")  # bullet sits at 80 twips, text wraps at 280
    pPr.append(ind)
    p.append(pPr)
    # Single space between bullet glyph and text (was 2) — user flagged
    # the gap between the glyph and its text read as too wide.
    body_text = "●	" + _strip_manual_numbering(text)
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = ""
    r.append(t)
    p.append(r)
    _render_inline_markdown_into(p, body_text)
    return p


def _build_intro_paragraph(text: str):
    """Justified body paragraph (intro sentence between H6 and image).
    Renders `**bold**` markdown inside the text."""
    from docx.oxml import OxmlElement
    p = OxmlElement("w:p")
    pPr = OxmlElement("w:pPr")
    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:before"), "0")
    spacing.set(qn("w:after"), "120")
    spacing.set(qn("w:line"), "276")
    spacing.set(qn("w:lineRule"), "auto")
    pPr.append(spacing)
    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), "both")
    pPr.append(jc)
    p.append(pPr)
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = ""
    r.append(t)
    p.append(r)
    _render_inline_markdown_into(p, text)
    return p


def insert_image_after_heading(doc, heading_text: str, png_path: Path,
                                caption: str, width_inches: float = 6.5,
                                intro_paragraph: str | None = None,
                                explanation_bullets: list[str] | None = None) -> bool:
    """Insert (in document order):

        heading
        → intro_paragraph        (optional context sentence)
        → image                  (centered)
        → SEQ-numbered Figure caption table
        → explanation bullet 1
        → explanation bullet 2
        → …

    This matches the standard STS proposal convention: every diagram has
    an intro sentence above it and 7–17 explanation bullets below it.
    """
    heading = find_heading_paragraph(doc, heading_text)
    if heading is None:
        return False

    body = doc.element.body
    placeholder_p = doc.add_paragraph()
    placeholder_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # Add breathing room above + below the figure. Without this the image
    # touches the intro sentence above and the bullets below — a complaint
    # the user has flagged as a quality issue. 12pt ≈ one body line.
    placeholder_p.paragraph_format.space_before = Pt(12)
    placeholder_p.paragraph_format.space_after = Pt(6)  # caption sits below; small gap to it
    placeholder_run = placeholder_p.add_run()
    placeholder_run.add_picture(str(png_path), width=Inches(width_inches))

    title = re.sub(r"^\s*Figure\s+\d+\s*[:.]?\s*", "", caption).strip() or caption
    caption_el = _build_seq_caption_table(doc, title)

    body.remove(placeholder_p._p)
    # Insert in REVERSE so document order ends up: heading → intro → image
    # → caption → bullets (in list order). The LAST item we insert (which
    # appears FIRST in document order, immediately after the caption table)
    # carries is_first=True so it owns the space-before gap that the caption
    # table can't provide itself.
    bullets = list(explanation_bullets or [])
    non_empty = [b for b in bullets if b and str(b).strip()]
    for idx, bullet_text in enumerate(reversed(non_empty)):
        is_first_in_list = (idx == len(non_empty) - 1)
        insert_after_paragraph(heading,
                               _build_bullet_paragraph(str(bullet_text),
                                                       is_first=is_first_in_list))
    if caption_el is not None:
        insert_after_paragraph(heading, caption_el)
    insert_after_paragraph(heading, placeholder_p._p)
    if intro_paragraph and intro_paragraph.strip():
        insert_after_paragraph(heading, _build_intro_paragraph(intro_paragraph.strip()))
    return True


# The bid sections an RFP normally asks for beyond the technical solution itself
# (Appendix-C style: team, delivery plan, support and SLAs, risks, references,
# contractual exceptions). Every one is OPTIONAL: the template carries the heading
# and a {{KEY}} slot, and anything left null or absent is removed at build time, so
# a project that does not need a section sees no trace of it. This is what lets a
# PM fill in only the sections a given client actually asked for.
#   (H3 heading, [(H5 subheading or None, content key), ...])
OPTIONAL_SECTION_GROUPS = [
    ("SECURITY & DATA PROTECTION", [
        (None, "security_data_protection"),
    ]),
    ("PROJECT TEAM", [
        ("Team Structure", "team_structure"),
        ("Roles & Responsibilities", "team_roles"),
        ("Engagement Model", "team_engagement_model"),
    ]),
    ("DELIVERY PLAN & GOVERNANCE", [
        ("Delivery Roadmap", "delivery_roadmap"),
        ("Milestones & Acceptance", "delivery_milestones"),
        ("Governance & Reporting", "delivery_governance"),
    ]),
    ("SUPPORT & SERVICE LEVELS", [
        ("Support Model", "support_model"),
        ("Service Level Targets", "service_levels"),
    ]),
    ("ASSUMPTIONS, DEPENDENCIES & RISKS", [
        ("Assumptions & Dependencies", "assumptions_dependencies"),
        ("Key Risks & Mitigations", "risk_register"),
    ]),
    ("CONTRACTUAL EXCEPTIONS", [
        (None, "contractual_exceptions"),
    ]),
]
# "References" lives inside the existing CASE STUDY section, so it is dropped on its
# own rather than as part of a group.
OPTIONAL_SUBSECTIONS = [("References", "references")]


def drop_section_if_empty(doc, heading_text: str, mapping: dict, content_key: str | None = None) -> bool:
    """If the value for the section's content key is null/empty, remove the heading
    and any following paragraphs up to the next heading at same-or-higher level.
    Returns True if section was dropped.

    `content_key`, when given, is the exact mapping key to test (use this when the
    heading TEXT no longer equals the key, e.g. a "Data" heading whose content key
    is "techstack_data"). When omitted, the key is derived from the heading text:
    lowercased, spaces/dashes/braces stripped ("Mobile App Strategy" ->
    "mobile_app_strategy").
    """
    heading = find_heading_paragraph(doc, heading_text)
    if heading is None:
        return False

    if content_key is not None:
        key = content_key
    else:
        key = heading_text.lower()
        key = re.sub(r"[{}]", "", key)
        key = re.sub(r"[\s\-]+", "_", key).strip("_")
    # Empty == None / "" / "null" / [] (an empty techstack array is also "no section").
    if mapping.get(key) not in (None, "", "null", []):
        return False

    own_level = int(heading.style.name.split()[-1])
    to_remove = [heading._p]
    cursor = heading._p
    while True:
        nxt = cursor.getnext()
        if nxt is None:
            break
        tag = nxt.tag.rsplit("}", 1)[-1]
        if tag == "p":
            # Check if this is another heading at same-or-higher level
            pPr = nxt.find(qn("w:pPr"))
            if pPr is not None:
                pStyle = pPr.find(qn("w:pStyle"))
                if pStyle is not None:
                    val = pStyle.get(qn("w:val"), "")
                    # Need style name from styles part. Approximate: heading style ids
                    # in this template are numeric — bail out conservatively at any heading.
                    # (Caller responsibility: design templates so optional sections are leaf headings.)
                    name = doc.styles.element.findall(qn("w:style"))
                    # Quick check: if val matches a heading style by name, stop.
                    style_name = next((s.get(qn("w:styleId")) for s in name if s.get(qn("w:styleId")) == val), None)
                    # Fallback: stop at the next paragraph that python-docx reports as a heading.
                    for p in doc.paragraphs:
                        if p._p is nxt and p.style and p.style.name.startswith("Heading"):
                            lvl = int(p.style.name.split()[-1])
                            if lvl <= own_level:
                                # Stop before this paragraph
                                for el in to_remove:
                                    el.getparent().remove(el)
                                return True
                            break
            to_remove.append(nxt)
        elif tag == "tbl":
            to_remove.append(nxt)
        else:
            # sectPr etc — stop
            break
        cursor = nxt

    for el in to_remove:
        el.getparent().remove(el)
    return True


# Professional, Word-standard heading spacing (points). The heading hugs the
# block it introduces (SMALL space-after) and is separated from the content
# ABOVE by space-before. Values are clamped into [floor, ceiling] — far tighter
# than the old 24pt floor, which made "1." and "1.1" sit a full blank line apart
# (the defect the user flagged). Floors MUST match the reviewer's
# heading_section_spacing floors so a post-auto_fix rebuild can't regress.
_HEADING_MIN_SPACE_BEFORE = {1: 18, 2: 12, 3: 10, 4: 8, 5: 8, 6: 6}
_HEADING_MIN_SPACE_AFTER  = {1:  6, 2:  4, 3:  4, 4:  3, 5:  3, 6:  3}
_HEADING_MAX_SPACE_BEFORE = {1: 24, 2: 16, 3: 12, 4: 10, 5: 10, 6: 8}
_HEADING_MAX_SPACE_AFTER  = {1: 10, 2:  8, 3:  6, 4:  6, 5:  6, 6:  6}
# A heading IMMEDIATELY under another heading (e.g. "1. INTRODUCTION" then
# "1.1 Executive Summary") must NOT add a section-size gap — the two group as a
# unit. Force a small space-before in that case regardless of the floor.
_HEADING_STACKED_SPACE_BEFORE = {1: 6, 2: 4, 3: 4, 4: 4, 5: 4, 6: 4}


def _heading_style_ids(doc) -> set:
    """Style IDs whose name is a Heading. The template references styles by
    numeric ID (`w:pStyle w:val="4"`) in the XML, while python-docx exposes the
    resolved name ("Heading 3"); raw-XML checks must map ID -> name or they
    silently miss every heading."""
    ids = set()
    for s in doc.styles:
        try:
            if s.style_id and (s.name or "").startswith("Heading"):
                ids.add(s.style_id)
        except Exception:
            continue
    return ids


def _pstyle_val(p_el) -> str:
    pPr = p_el.find(qn("w:pPr"))
    if pPr is None:
        return ""
    ps = pPr.find(qn("w:pStyle"))
    return (ps.get(qn("w:val")) if ps is not None else "") or ""


def _el_is_heading(p_el, heading_ids: set) -> bool:
    if p_el is None or p_el.tag != qn("w:p"):
        return False
    val = _pstyle_val(p_el)
    return val in heading_ids or val.startswith("Heading")


def _prev_block_is_heading(p_el, heading_ids: set) -> bool:
    """True if the block immediately before `p_el` is a heading paragraph
    (skipping empty spacer paragraphs). Used so a heading stacked directly under
    another heading hugs it instead of leaving a blank-line gap."""
    prev = p_el.getprevious()
    while prev is not None:
        if prev.tag != qn("w:p"):
            return False  # a table or other block — not a stacked heading
        text = "".join(t.text or "" for t in prev.iter(qn("w:t")))
        if not text.strip() and not _el_is_heading(prev, heading_ids):
            prev = prev.getprevious()  # skip an empty spacer paragraph
            continue
        return _el_is_heading(prev, heading_ids)
    return False


def remove_heading_adjacent_blank_paragraphs(doc) -> int:
    """Delete empty 'spacer' paragraphs that sit directly next to a heading.

    The template peppers blank paragraphs around headings; combined with the
    headings' own space-before/after they read as an extra blank line, for
    example between "1. INTRODUCTION" and "1.1 Executive Summary".
    Heading space-before/after alone gives the correct, consistent rhythm, so
    these spacers are pure noise. Keeps image paragraphs and the section-final
    paragraph."""
    heading_ids = _heading_style_ids(doc)
    body = doc.element.body
    removed = 0
    for el in list(body):
        if el.tag != qn("w:p"):
            continue
        if "".join(t.text or "" for t in el.iter(qn("w:t"))).strip():
            continue
        if el.find(".//" + qn("w:drawing")) is not None:
            continue  # holds an image — not a blank spacer
        pPr = el.find(qn("w:pPr"))
        if pPr is not None and pPr.find(qn("w:sectPr")) is not None:
            continue  # section-carrying paragraph — keep
        if _el_is_heading(el.getprevious(), heading_ids) or _el_is_heading(el.getnext(), heading_ids):
            body.remove(el)
            removed += 1
    return removed


def boost_heading_spacing(doc) -> int:
    """Clamp heading space-before/after into the professional ranges above.

    A heading directly under another heading gets a small forced space-before
    (no blank-line gap between "1." and "1.1"); otherwise space-before is
    clamped into [floor, ceiling]. space-after is always kept small so the
    heading hugs the block it introduces.
    """
    touched = 0
    heading_ids = _heading_style_ids(doc)
    for p in doc.paragraphs:
        sname = p.style.name if p.style else ""
        if not sname.startswith("Heading"):
            continue
        try:
            lvl = int(sname.split()[-1])
        except ValueError:
            continue
        sb_floor = _HEADING_MIN_SPACE_BEFORE.get(lvl)
        sa_floor = _HEADING_MIN_SPACE_AFTER.get(lvl)
        sb_ceil = _HEADING_MAX_SPACE_BEFORE.get(lvl)
        sa_ceil = _HEADING_MAX_SPACE_AFTER.get(lvl)
        if sb_floor is None:
            continue
        pf = p.paragraph_format
        if _prev_block_is_heading(p._p, heading_ids):
            # stacked heading — force the small "grouped" gap
            pf.space_before = Pt(_HEADING_STACKED_SPACE_BEFORE.get(lvl, 4))
            touched += 1
        else:
            cur_sb = pf.space_before.pt if pf.space_before else 0
            if cur_sb < sb_floor:
                pf.space_before = Pt(sb_floor); touched += 1
            elif sb_ceil and cur_sb > sb_ceil:
                pf.space_before = Pt(sb_ceil); touched += 1
        cur_sa = pf.space_after.pt if pf.space_after else 0
        if cur_sa < sa_floor:
            pf.space_after = Pt(sa_floor); touched += 1
        elif sa_ceil and cur_sa > sa_ceil:
            pf.space_after = Pt(sa_ceil); touched += 1
    return touched


_HEADING_TEXT_RE = re.compile(r"^\s*\d+(\.\d+){0,4}\.?\s+\S")


def _looks_like_heading_text(text: str) -> bool:
    """Heuristic: a paragraph whose visible text starts with `1.`, `1.1`,
    `2.1.3.`, etc. followed by a real word is structurally a heading even
    if the template forgot to apply the Heading 1/2/3 style. The proposal
    template carries these as plain paragraphs with hard-coded left_indent
    (480 / 960 / 1200 twentieths), so `pStyle.startswith("Heading")` misses
    them, which is the root cause of a sub-heading sitting further left than
    defect."""
    return bool(_HEADING_TEXT_RE.match(text or ""))


def normalize_heading_indents(doc) -> int:
    """Pull every heading paragraph back to flush-left so that:
      - the auto-number / typed number anchor sits at column 0 (the page
        margin), and
      - no heading sticks out to the left of the body text,
        and
      - all headings line up consistently rather than stair-stepping
        deeper for each level.

    We catch headings via TWO signals (either is sufficient):
      1. Paragraph style starts with "Heading" (the python-docx-native way), OR
      2. The visible text matches `^\\d+(\\.\\d+)*\\.?\\s+\\S` — i.e. starts
         with `1.`, `1.1`, `2.1.3.`, etc. This catches the template's
         numbered-paragraph-without-Heading-style case.

    For every match we set BOTH left_indent and first_line_indent to 0 —
    leaving a hanging gutter would push the number off the left margin.
    """
    from docx.oxml import OxmlElement
    touched = 0
    for p in doc.paragraphs:
        sname = p.style.name if p.style else ""
        text = p.text or ""
        is_heading_style = sname.startswith("Heading")
        is_heading_text = _looks_like_heading_text(text)
        if not (is_heading_style or is_heading_text):
            continue
        pf = p.paragraph_format
        # ALWAYS force left_indent and first_line_indent to 0 on a heading.
        # Setting to None (the python-docx "inherit from style") is NOT
        # enough — the style or numbering definition still pushes the
        # number off-margin. We need a HARD zero at the paragraph level.
        pf.left_indent = Pt(0)
        pf.first_line_indent = Pt(0)
        touched += 1
        # Also write a direct XML w:ind override so the numbering
        # definition's indent attributes do not win over the paragraph's
        # explicit value. We FORCE-INSERT an <w:ind/> element with all
        # four ind attrs zeroed; this overrides the numId-derived indent.
        pPr = p._p.find(qn("w:pPr"))
        if pPr is None:
            pPr = OxmlElement("w:pPr")
            p._p.insert(0, pPr)
        ind = pPr.find(qn("w:ind"))
        if ind is None:
            ind = OxmlElement("w:ind")
            # Insert ind in correct schema position (after numPr if present)
            numPr = pPr.find(qn("w:numPr"))
            if numPr is not None:
                numPr.addnext(ind)
            else:
                pPr.append(ind)
        ind.set(qn("w:left"), "0")
        ind.set(qn("w:start"), "0")
        ind.set(qn("w:firstLine"), "0")
        ind.set(qn("w:hanging"), "0")
    return touched


def ensure_caption_followed_by_gap(doc, min_pt: int = 12) -> int:
    """For every 1x1 caption table in the document, make sure the paragraph
    immediately after has space-before >= min_pt. A caption table cannot
    carry trailing whitespace itself, so the next paragraph must own the
    gap — otherwise body text sits flush against the caption, which the
    reader has flagged as a layout defect: the body text sits too close to the
    figure and its caption.
    """
    from docx.oxml import OxmlElement
    touched = 0
    body = doc.element.body
    for tbl in list(doc.tables):
        rows = tbl.rows
        if len(rows) != 1 or len(rows[0].cells) != 1:
            continue
        cell_text = "".join(p.text for p in rows[0].cells[0].paragraphs).strip()
        if not cell_text:
            continue  # not a caption (empty)
        # Skip if this isn't really a caption (heuristic: caption text contains
        # 'Figure' or starts with a number reference). Otherwise we'd push
        # body table-cell content around.
        if "Figure" not in cell_text and "figure" not in cell_text and "Bảng" not in cell_text:
            continue
        nxt = tbl._element.getnext()
        if nxt is None or nxt.tag.rsplit("}", 1)[-1] != "p":
            continue
        # Read current space-before
        pPr = nxt.find(qn("w:pPr"))
        if pPr is None:
            pPr = OxmlElement("w:pPr")
            nxt.insert(0, pPr)
        spacing = pPr.find(qn("w:spacing"))
        if spacing is None:
            spacing = OxmlElement("w:spacing")
            pPr.append(spacing)
        cur_before = spacing.get(qn("w:before"))
        cur_pt = int(cur_before) / 20 if cur_before else 0
        if cur_pt < min_pt:
            spacing.set(qn("w:before"), str(min_pt * 20))  # twentieths of a point
            touched += 1
    return touched


def justify_body(doc) -> int:
    """Set every Normal / List* paragraph to JUSTIFY. Return count touched.

    SKIPS paragraphs that contain an inline image (`<w:drawing>`) — those
    are already centered by `center_image_paragraphs` and overriding to
    JUSTIFY would un-center the image (the previous bug 3.5.3 surfaced).
    """
    touched = 0
    for p in doc.paragraphs:
        sname = p.style.name if p.style else ""
        if sname.startswith("Heading") or sname in ("Title", "Subtitle", "Caption"):
            continue
        # Skip image-bearing paragraphs — keep their CENTER alignment.
        if p._p.find(".//" + qn("w:drawing")) is not None:
            continue
        if p.alignment != WD_ALIGN_PARAGRAPH.JUSTIFY:
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            touched += 1
    return touched


def replace_remaining_placeholders_xml(out_path: Path, mapping: dict) -> int:
    """Final XML-level pass to catch {{KEY}} placeholders that python-docx
    iteration misses — notably TOC field cached text, comments XML, and any
    other parts that aren't standard body paragraphs/tables/headers.

    Only substitutes when the mapping value is not None; None values mean
    the surrounding section was supposed to be dropped, so leaving the
    placeholder is intentional and the format reviewer will flag it for the
    user to fix the upstream replacements file.
    """
    tmp = out_path.with_suffix(".tmp.docx")
    pattern = re.compile(r"\{\{([A-Z_][A-Z0-9_]*)\}\}")
    total = 0
    with zipfile.ZipFile(out_path, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.endswith(".xml"):
                txt = data.decode("utf-8", errors="replace")
                def repl(m):
                    nonlocal total
                    key = m.group(1).lower()
                    if key in mapping and mapping[key] is not None:
                        total += 1
                        rendered = _stringify_value(mapping[key])
                        return rendered if rendered is not None else m.group(0)
                    return m.group(0)
                new_txt = pattern.sub(repl, txt)
                if new_txt != txt:
                    data = new_txt.encode("utf-8")
            zout.writestr(item, data)
    tmp.replace(out_path)
    return total


def patch_numbering_xml(out_path: Path) -> int:
    """Force every heading-numbering level to left-align (`lvlJc="left"`).

    The proposal_template's numbering definition uses `lvlJc="right"` so the
    auto-numbers (1., 1.1., 1.1.1.) are right-aligned within their hanging
    gutter. Because "1.1." is wider than "1.", a right-aligned 1.1. starts
    LEFT of where a right-aligned 1. starts, so a child heading renders further
    out than its parent (seen on page 4 of the rendered docx).
    Left-aligning the numbers anchors them at the same left column.
    """
    tmp = out_path.with_suffix(".tmp.docx")
    touched = 0
    with zipfile.ZipFile(out_path, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/numbering.xml":
                txt = data.decode("utf-8")
                # Replace every "lvlJc" right-align inside any heading <w:lvl>
                new = re.sub(r'<w:lvlJc w:val="right"/>',
                             '<w:lvlJc w:val="left"/>', txt)
                touched += txt.count('<w:lvlJc w:val="right"/>')
                if new != txt:
                    data = new.encode("utf-8")
            zout.writestr(item, data)
    tmp.replace(out_path)
    return touched


def renumber_figure_sequence_cache(out_path: Path) -> int:
    """Walk word/document.xml and renumber every SEQ Figure field's cached
    text run with an incrementing integer 1, 2, 3, ... in document order.

    Why: viewers that DON'T evaluate Word field codes (LibreOffice PDF
    export, PyMuPDF, SharePoint preview) display the CACHED text between
    `<w:fldChar w:fldCharType="separate"/>` and `<w:fldChar w:fldCharType="end"/>`
    instead of evaluating `SEQ Figure`. If every caption ships with the same
    cached "1", every preview shows "Figure 1: ..." regardless of position.
    Renumbering the cache makes captions correct in EVERY viewer, before
    the user even presses F9.
    """
    tmp = out_path.with_suffix(".tmp.docx")
    seq_count = 0
    with zipfile.ZipFile(out_path, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                txt = data.decode("utf-8")
                # Pattern: <w:instrText ...>...SEQ Figure...</w:instrText>
                # followed by <w:fldChar w:fldCharType="separate"/>
                # followed by one or more runs until <w:fldChar w:fldCharType="end"/>
                # We rewrite the FIRST <w:t>...</w:t> inside that span.
                counter = {"n": 0}
                def renum_match(m):
                    counter["n"] += 1
                    seq_block = m.group(0)
                    # Find the cached text run between separate and end
                    new_block = re.sub(
                        r'(<w:fldChar w:fldCharType="separate"/></w:r>.*?<w:t[^>]*>)([^<]*)(</w:t>)',
                        lambda mm: mm.group(1) + str(counter["n"]) + mm.group(3),
                        seq_block,
                        count=1,
                        flags=re.DOTALL,
                    )
                    return new_block
                pattern = re.compile(
                    r'<w:instrText[^>]*>\s*SEQ\s+Figure[^<]*</w:instrText>.*?<w:fldChar w:fldCharType="end"/>',
                    re.DOTALL,
                )
                new_txt = pattern.sub(renum_match, txt)
                seq_count = counter["n"]
                if new_txt != txt:
                    data = new_txt.encode("utf-8")
            zout.writestr(item, data)
    tmp.replace(out_path)
    return seq_count


def patch_settings_xml(out_path: Path) -> None:
    """Edit word/settings.xml to add the document-level flags that keep our
    output looking clean. We add (only if missing):

      - autoHyphenation=true       — lets Word break long words across lines
                                     instead of leaving giant trailing gaps
                                     in justified paragraphs.
      - consecutiveHyphenLimit=2   — prevents more than 2 consecutive hyphens
                                     (Word default = unlimited, which can produce
                                     ugly hyphen ladders).
      - hyphenationZone=288        — 0.2" (in twentieths-of-a-point: 288);
                                     narrower zone → more hyphenation, fewer gaps.
      - doNotExpandShiftReturn=true — soft line breaks (Shift+Enter) do NOT
                                     trigger full justify expansion on the line
                                     that ends with one. This is the single
                                     most effective fix for the "huge white
                                     channels in middle of paragraph" symptom
                                     the user has reported.
      - characterSpacingControl=compressPunctuation — lets Word squeeze inter-
                                     character whitespace around punctuation
                                     instead of widening word gaps.
      - updateFields=true          — refreshes the TOC the first time the
                                     document is opened.
    """
    tmp = out_path.with_suffix(".tmp.docx")
    desired = {
        "autoHyphenation":            '<w:autoHyphenation w:val="true"/>',
        "consecutiveHyphenLimit":     '<w:consecutiveHyphenLimit w:val="2"/>',
        "hyphenationZone":            '<w:hyphenationZone w:val="288"/>',
        "doNotExpandShiftReturn":     '<w:doNotExpandShiftReturn/>',
        "characterSpacingControl":    '<w:characterSpacingControl w:val="compressPunctuation"/>',
        "updateFields":               '<w:updateFields w:val="true"/>',
    }
    with zipfile.ZipFile(out_path, "r") as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/settings.xml":
                txt = data.decode("utf-8")
                inserts = [xml for tag, xml in desired.items() if tag not in txt]
                if inserts:
                    txt = txt.replace(
                        "</w:settings>",
                        "".join(inserts) + "</w:settings>",
                    )
                data = txt.encode("utf-8")
            zout.writestr(item, data)
    tmp.replace(out_path)


SKILL_ROOT = Path(__file__).resolve().parent.parent
ICONS_ROOT = SKILL_ROOT / "assets" / "icons"


def _resolve_logo_path(logo_ref: str | None) -> Path | None:
    """Resolve a logo reference like 'azure/aks' or 'aws/lambda' to a real PNG."""
    if not logo_ref:
        return None
    try:
        pack, name = logo_ref.split("/", 1)
    except ValueError:
        return None
    candidates = [
        ICONS_ROOT / pack / "png" / f"{name}.png",
        ICONS_ROOT / pack / "png" / f"{name}@300.png",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _set_cell_fill(cell, hex_color: str) -> None:
    from docx.oxml import OxmlElement
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _set_table_borders(table, color: str = "B7B7B7", size: int = 8) -> None:
    from docx.oxml import OxmlElement
    tblPr = table._element.find(qn("w:tblPr"))
    if tblPr is None:
        return
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{edge}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:color"), color)
        b.set(qn("w:sz"), str(size))
        b.set(qn("w:space"), "0")
        borders.append(b)
    # Remove existing borders if any
    existing = tblPr.find(qn("w:tblBorders"))
    if existing is not None:
        tblPr.remove(existing)
    tblPr.append(borders)


def _build_techstack_table(doc, items: list[dict], header_fill: str = "595959",
                           headers: tuple = ("Technology", "Advantages"),
                           col0_inches: float = 1.75):
    """Build a 2-col shaded-header table (professional layout).

    Each item: {"name": str, "logo": "pack/name" | None, "description": str}.
    Logo (if resolvable) is embedded above the bold name in column 1.

    `headers` and `col0_inches` exist because this renderer serves more than the
    technology stack. The team section uses it as `Role | Accountability` with a
    wider first column, since a role cell carries the position, the headcount and
    the location rather than a one-word product name. Reusing this function keeps
    every table in the document identical in border, fill and spacing: a second
    hand-rolled table renderer is how a document ends up with two table styles.
    """
    from docx.shared import Inches as _Inches, RGBColor
    from docx.enum.table import WD_ALIGN_VERTICAL
    n_rows = 1 + len(items)
    tbl = doc.add_table(rows=n_rows, cols=2)
    tbl.autofit = False
    # Column widths — Technology col carries only logo + short name, keep narrow.
    # We MUST set both tblGrid (authoritative for Word layout) AND per-row cell
    # widths — python-docx only does the latter, leaving tblGrid stale.
    # Body width of this template's main section is 7.27" (10466 twips,
    # margins 0.5" + 0.5"). Table fills body margin-to-margin.
    # Total must stay 10466 twips (the 7.27" body width) whatever col0 is, or the
    # table stops ending at the right margin.
    _TOTAL_TWIPS = 10466
    col0_twips = int(round(col0_inches * 1440))
    col1_twips = _TOTAL_TWIPS - col0_twips
    col0_w = _Inches(col0_inches)
    col1_w = _Inches(col1_twips / 1440.0)
    from docx.oxml import OxmlElement
    tblGrid = tbl._element.find(qn("w:tblGrid"))
    if tblGrid is not None:
        for child in list(tblGrid):
            tblGrid.remove(child)
        for w in (col0_twips, col1_twips):
            gc = OxmlElement("w:gridCol")
            gc.set(qn("w:w"), str(w))
            tblGrid.append(gc)
    # Force table width = full page body (9360 twips) and fixed layout
    # so column widths take effect immediately. Also zero the table indent
    # so the table starts at the left page margin, ends at right margin.
    tblPr = tbl._element.find(qn("w:tblPr"))
    if tblPr is not None:
        # Width
        tblW = tblPr.find(qn("w:tblW"))
        if tblW is None:
            tblW = OxmlElement("w:tblW")
            tblPr.append(tblW)
        tblW.set(qn("w:w"), "10466")
        tblW.set(qn("w:type"), "dxa")
        # Indent (zero — flush with body left margin)
        tblInd = tblPr.find(qn("w:tblInd"))
        if tblInd is None:
            tblInd = OxmlElement("w:tblInd")
            tblPr.append(tblInd)
        tblInd.set(qn("w:w"), "0")
        tblInd.set(qn("w:type"), "dxa")
        # Fixed layout — column widths honored exactly, not autofit
        tblLayout = tblPr.find(qn("w:tblLayout"))
        if tblLayout is None:
            tblLayout = OxmlElement("w:tblLayout")
            tblPr.append(tblLayout)
        tblLayout.set(qn("w:type"), "fixed")
    for row in tbl.rows:
        row.cells[0].width = col0_w
        row.cells[1].width = col1_w
        # Vertical-center every cell so the logo and the name sit centred together.
        for c in row.cells:
            c.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    # Header
    hdr = tbl.rows[0]
    for col_idx, label in enumerate(headers):
        cell = hdr.cells[col_idx]
        cell.text = ""
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = para.add_run(label)
        run.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        run.font.size = Pt(11)
        _set_cell_fill(cell, header_fill)

    # Data rows
    for i, item in enumerate(items):
        row = tbl.rows[i + 1]
        # Col 1: optional logo + bold name, both centered horizontally
        name_cell = row.cells[0]
        name_cell.text = ""  # clear default empty paragraph
        # Logo paragraph (centered)
        logo_path = _resolve_logo_path(item.get("logo"))
        if logo_path:
            logo_para = name_cell.paragraphs[0]
            logo_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            logo_run = logo_para.add_run()
            try:
                logo_run.add_picture(str(logo_path), height=_Inches(0.35))
            except Exception:
                pass
            # Name paragraph below logo (centered)
            name_para = name_cell.add_paragraph()
        else:
            name_para = name_cell.paragraphs[0]
        name_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        name_run = name_para.add_run(item.get("name", ""))
        name_run.bold = True
        name_run.font.size = Pt(11)

        # Col 2: description
        desc_cell = row.cells[1]
        desc_cell.text = ""
        desc_para = desc_cell.paragraphs[0]
        _render_inline_markdown_into(desc_para._p, item.get("description", ""))
        desc_para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    _set_table_borders(tbl, color="B7B7B7", size=8)
    return tbl


#: Content keys that render as a 2-col table when given a list of {name, description}
#: dicts, mapped to their header labels and first-column width in inches. Anything
#: named `techstack_*` is included automatically with the technology defaults.
#: A key listed here still renders as bullets if its value is a list of plain
#: strings, so turning a section into a table is opt-in per project.
_EXTRA_TABLE_KEYS = {
    "team_roles": (("Role", "Accountability"), 2.60),
}


def render_techstack_tables(doc, replacements: dict) -> set:
    """For every table-eligible key whose value is a list of {name, [logo,] description}
    dicts, find its {{KEY}} placeholder paragraph and replace it with a styled 2-col table.
    Returns the set of keys that were rendered as tables (so the caller skips the
    optional-section drop for them — their placeholder paragraph is already gone and
    a table now sits under the heading)."""
    rendered = set()
    for key, val in list(replacements.items()):
        eligible = key.startswith("techstack_") or key in _EXTRA_TABLE_KEYS
        if not eligible or not isinstance(val, list) or not val:
            continue
        if not all(isinstance(it, dict) and "name" in it and "description" in it for it in val):
            continue
        headers, col0 = _EXTRA_TABLE_KEYS.get(key, (("Technology", "Advantages"), 1.75))
        placeholder = "{{" + key.upper() + "}}"
        target = None
        for p in doc.paragraphs:
            if placeholder in (p.text or ""):
                target = p
                break
        if target is None:
            continue
        # Build the table at the end of the document, then move it into position
        tbl = _build_techstack_table(doc, val, headers=headers, col0_inches=col0)
        # Move table to just after the target paragraph
        target._p.addnext(tbl._element)
        # Remove the placeholder paragraph (its content is now in the table)
        target._p.getparent().remove(target._p)
        # Mark replacement so the text-replacement step doesn't try to fill it
        replacements[key] = ""
        rendered.add(key)
    return rendered


def normalize_bullet_indent(doc) -> int:
    """Give every glyph bullet a hanging indent so a wrapped line aligns under the text.

    Bullets reach the document by two routes. Diagram explanation bullets are built by
    `_build_bullet_paragraph`, which sets ind left=280 hanging=200. Content lists (risks,
    assumptions, service levels, contractual exceptions, and every optional section written
    as bullets) arrive through the generic list-to-text path as plain paragraphs beginning
    with the glyph, with no indent at all.

    The result was 54 bullets indented correctly and 140 not, which is worse than none of
    them being indented: a 25-word bullet always wraps, and without a hanging indent the
    second line returns to the left margin and sits under the glyph instead of under the
    text. Inconsistent ragged bullets read as carelessness, in Word and in SharePoint alike.

    Applied as a pass rather than at each call site because there are several call sites and
    a future one would silently miss it again.
    """
    from docx.oxml import OxmlElement

    def every_paragraph(d):
        """Body paragraphs AND paragraphs inside table cells.

        `doc.paragraphs` skips table cells, so a first attempt left 20 bulleted lines
        inside the technology-stack and role tables un-indented while fixing 174 elsewhere.
        Same trap as every other pass that walks only the top level of the body.
        """
        yield from d.paragraphs
        for tbl in d.tables:
            for row in tbl.rows:
                for cell in row.cells:
                    yield from cell.paragraphs

    def set_ind(para, left, hanging):
        pPr = para._p.get_or_add_pPr()
        if pPr.find(qn("w:numPr")) is not None:
            return False                  # a real Word list handles its own indent
        ind = pPr.find(qn("w:ind"))
        if ind is None:
            ind = OxmlElement("w:ind")
            pPr.append(ind)
        if ind.get(qn("w:left")) == left and ind.get(qn("w:hanging")) == hanging:
            return False
        ind.set(qn("w:left"), left)
        if hanging is None:
            if ind.get(qn("w:hanging")) is not None:
                ind.attrib.pop(qn("w:hanging"))
        else:
            ind.set(qn("w:hanging"), hanging)
        return True

    def opens_with_bold_label(para):
        """A continuation paragraph such as "**Solution:** ..." — a bold run ending in a colon."""
        for run in para.runs:
            t = (run.text or "").strip()
            if not t:
                continue
            return bool(run.bold) and t.endswith(":")
        return False

    touched = 0
    prev_was_bullet = False
    for para in every_paragraph(doc):
        text = (para.text or "").strip()
        style = para.style.name if para.style else ""
        if not text or style.lower().startswith("heading"):
            prev_was_bullet = False
            continue
        if text.startswith(("●", "•")):
            if set_ind(para, "280", "200"):
                touched += 1
            # Declare the tab stop the glyph tabs to, so the text column is identical on
            # every bullet instead of being wherever justification stretched a space to.
            pPr = para._p.get_or_add_pPr()
            if pPr.find(qn("w:tabs")) is None:
                tabs = OxmlElement("w:tabs")
                tab = OxmlElement("w:tab")
                tab.set(qn("w:val"), "left")
                tab.set(qn("w:pos"), "280")
                tabs.append(tab)
                pPr.append(tabs)
            prev_was_bullet = True
            continue
        # A paragraph that CONTINUES the bullet above it, such as the "Solution:" half of a
        # problem and solution pair, is emitted as plain text with no glyph. Left at the
        # margin it is wider than the bullet it belongs to, so the pair reads as an indented
        # bullet followed by an unrelated flush-left block and the reader cannot see which
        # solution answers which problem. Indent it to the bullet's TEXT, with no hanging,
        # so the two halves read as one unit.
        if prev_was_bullet and opens_with_bold_label(para):
            if set_ind(para, "280", None):
                touched += 1
            continue
        prev_was_bullet = False
    return touched


def normalize_body_spacing(doc) -> int:
    """Clamp every BODY paragraph (non-heading, non-caption, non-image) to a
    consistent rhythm: SB=0pt, SA=6pt. The template carries a grab-bag of
    paragraph styles inherited from PMO34129 — some sit at SA=20pt, others
    at SA=0, so the vertical gap varies from one part of the page to another.

    PRESERVES:
      - The first bullet after a Figure caption (it explicitly carries
        SB=12pt as breathing room between caption table and bullet text).
      - Any paragraph with an intentionally-set SB ≥ 8pt (likely a
        first-after-something marker we put there on purpose).
    """
    touched = 0
    BODY_SB = Pt(0)
    BODY_SA = Pt(6)
    for p in doc.paragraphs:
        sname = p.style.name if p.style else ""
        if sname.startswith("Heading") or sname in ("Title", "Subtitle", "Caption"):
            continue
        # Skip image-bearing paragraphs (they own SB=12pt SA=6pt for the figure rhythm)
        if p._p.find(".//" + qn("w:drawing")) is not None:
            continue
        # Skip empty paragraphs (used as page-break or layout spacers)
        if not (p.text or "").strip():
            continue
        pf = p.paragraph_format
        sb = pf.space_before.pt if pf.space_before else 0
        sa = pf.space_after.pt if pf.space_after else 0
        # Preserve intentional larger SB (we explicitly set 12pt for the first
        # bullet after a Figure caption — see _build_bullet_paragraph).
        if sb >= 8:
            # Only clamp SA if it's wildly different from 6pt
            if abs(sa - 6) > 0.1:
                pf.space_after = BODY_SA
                touched += 1
            continue
        if abs(sb - 0) > 0.1:
            pf.space_before = BODY_SB
            touched += 1
        if abs(sa - 6) > 0.1:
            pf.space_after = BODY_SA
            touched += 1
    return touched


def center_image_paragraphs(doc) -> int:
    """Every paragraph that contains a w:drawing (an inline image) gets
    centered. The proposal template ships several diagrams (3.5.3 Testing
    Process, Branch Model, etc.) at left alignment by default — user wants
    every image visually centered on the page so the captions sit cleanly
    beneath."""
    touched = 0
    for p in doc.paragraphs:
        if p._p.find(".//" + qn("w:drawing")) is not None:
            if p.alignment != WD_ALIGN_PARAGRAPH.CENTER:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                touched += 1
    return touched


def remove_empty_caption_tables(doc) -> int:
    """Remove 1x1 caption tables left over from the template (legacy artifact)."""
    removed = 0
    for tbl in list(doc.tables):
        rows = tbl.rows
        if len(rows) == 1 and len(rows[0].cells) == 1:
            cell = rows[0].cells[0]
            text = "".join(p.text for p in cell.paragraphs).strip()
            if not text:
                tbl._element.getparent().remove(tbl._element)
                removed += 1
    return removed


def remove_trailing_empty_paragraphs(doc) -> int:
    """Delete empty paragraphs at the very END of the body so SharePoint / Word /
    Office-365-online do not render a blank page at the end of the document.

    Keeps the body's final `sectPr`, any paragraph that carries a section break
    in its `pPr`, and any paragraph holding an image or an explicit break. Only
    the trailing RUN of truly empty paragraphs is removed.
    """
    body = doc.element.body
    removed = 0
    for el in reversed(list(body)):
        tag = el.tag
        if tag == qn("w:sectPr"):
            continue  # the document-final section properties — keep, keep scanning
        if tag != qn("w:p"):
            break  # a table or other content block — stop
        text = "".join(t.text or "" for t in el.iter(qn("w:t")))
        has_img = el.find(".//" + qn("w:drawing")) is not None
        has_break = el.find(".//" + qn("w:br")) is not None
        pPr = el.find(qn("w:pPr"))
        holds_sectpr = pPr is not None and pPr.find(qn("w:sectPr")) is not None
        if text.strip() or has_img or has_break or holds_sectpr:
            break  # real content (or a section-carrying para) — stop here
        body.remove(el)
        removed += 1
    return removed


def _normalise_subheading(text: str) -> str:
    """Strip leading section numbers and normalise for comparison."""
    t = re.sub(r"^\s*\d+(\.\d+)*\s*[.:)-]?\s*", "", text or "")
    return t.strip().lower()


def _collect_subheadings(diagrams: list, existing_anchor_text: str = "") -> list[str]:
    """Build the H6 sub-heading list from the diagram inventory, skipping any
    diagram whose title matches the existing anchor heading (e.g. the
    template already carries '2.1.1 System Context' as the anchor, so a
    Phase 2 inventory that also includes 'System Context' should not inject
    a duplicate H6 — the image just attaches to 2.1.1)."""
    anchor_norm = _normalise_subheading(existing_anchor_text)
    out: list[str] = []
    for d in diagrams:
        title = d.get("subheading") or d.get("target_heading") or d.get("slug")
        if not title or not str(title).strip():
            continue
        title = str(title).strip()
        if anchor_norm:
            t_norm = _normalise_subheading(title)
            if t_norm == anchor_norm or t_norm in anchor_norm or anchor_norm in t_norm:
                continue  # already covered by the existing anchor heading
        out.append(title)
    return out


_BULLET_GLYPHS = "●•▪◦‣⁃"     # ● • ▪ ◦ ‣ ⁃


def _all_paragraphs(doc):
    """Body paragraphs AND paragraphs inside table cells.

    `doc.paragraphs` skips table cells. Every pass in this file that forgot that
    has shipped a defect, so it is one helper now.
    """
    yield from doc.paragraphs
    for tbl in doc.tables:
        for row in tbl.rows:
            for cell in row.cells:
                yield from cell.paragraphs


def _is_glyph_bullet(para) -> bool:
    """A paragraph that OPENS with a bullet character and is not already a list item."""
    pPr = para._p.find(qn("w:pPr"))
    if pPr is not None and pPr.find(qn("w:numPr")) is not None:
        return False
    text = (para.text or "").lstrip()
    return bool(text) and text[0] in _BULLET_GLYPHS


def ensure_bullet_numbering(doc) -> int:
    """Define a real bullet list in numbering.xml and return its numId.

    WHY THIS EXISTS. The template ships a `numbering.xml` with exactly one definition,
    `numId=1`, and that one drives the HEADING numbering (the "4.2.1" on Heading 6). There
    is no bullet list defined anywhere in it. So every bullet this skill produced was a
    `●` character typed into an ordinary paragraph with a manual hanging indent faked by
    `w:ind`. It looks close enough in Word on a desktop and it is wrong everywhere else:
    Word Online and SharePoint lay a fake hanging indent out differently, so the reader
    had to select each list, remove the bullets and re-apply them, at which point Word
    attached the list definition that was missing all along and the spacing came right.
    That report is the whole reason for this function.

    Reuses an existing bullet definition if the template ever gains one, so running this
    twice cannot stack duplicates.
    """
    from docx.oxml import OxmlElement

    numbering = doc.part.numbering_part.element

    # Already have a bullet abstract definition? Reuse the num that points at it.
    for abstract in numbering.findall(qn("w:abstractNum")):
        lvl = abstract.find(qn("w:lvl"))
        if lvl is None:
            continue
        fmt = lvl.find(qn("w:numFmt"))
        if fmt is not None and fmt.get(qn("w:val")) == "bullet":
            aid = abstract.get(qn("w:abstractNumId"))
            for num in numbering.findall(qn("w:num")):
                ref = num.find(qn("w:abstractNumId"))
                if ref is not None and ref.get(qn("w:val")) == aid:
                    return int(num.get(qn("w:numId")))

    used_abstract = [int(a.get(qn("w:abstractNumId"))) for a in numbering.findall(qn("w:abstractNum"))]
    used_num = [int(n.get(qn("w:numId"))) for n in numbering.findall(qn("w:num"))]
    abstract_id = (max(used_abstract) + 1) if used_abstract else 0
    num_id = (max(used_num) + 1) if used_num else 1

    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_id))
    # Three levels is enough: the content never nests deeper, and defining the levels we
    # do not use would only give Word somewhere to drift to.
    for ilvl, (glyph, font, left, hanging) in enumerate([
        ("", "Symbol",      280, 200),   # matches the indent the fake bullets used,
        ("o",      "Courier New", 560, 200),   # so no line moves when the glyph becomes real
        ("", "Wingdings",   840, 200),
    ]):
        lvl = OxmlElement("w:lvl")
        lvl.set(qn("w:ilvl"), str(ilvl))
        for tag, attr, val in [
            ("w:start", "w:val", "1"),
            ("w:numFmt", "w:val", "bullet"),
            ("w:lvlText", "w:val", glyph),
            ("w:lvlJc", "w:val", "left"),
        ]:
            el = OxmlElement(tag)
            el.set(qn(attr), val)
            lvl.append(el)
        pPr = OxmlElement("w:pPr")
        ind = OxmlElement("w:ind")
        ind.set(qn("w:left"), str(left))
        ind.set(qn("w:hanging"), str(hanging))
        pPr.append(ind)
        lvl.append(pPr)
        rPr = OxmlElement("w:rPr")
        rfonts = OxmlElement("w:rFonts")
        rfonts.set(qn("w:ascii"), font)
        rfonts.set(qn("w:hAnsi"), font)
        rfonts.set(qn("w:hint"), "default")
        rPr.append(rfonts)
        lvl.append(rPr)
        abstract.append(lvl)

    # Schema order: every w:abstractNum precedes every w:num.
    existing_nums = numbering.findall(qn("w:num"))
    if existing_nums:
        existing_nums[0].addprevious(abstract)
    else:
        numbering.append(abstract)

    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    ref = OxmlElement("w:abstractNumId")
    ref.set(qn("w:val"), str(abstract_id))
    num.append(ref)
    numbering.append(num)
    return num_id


def convert_glyph_bullets_to_real_lists(doc, num_id: int) -> int:
    """Strip the typed glyph and make the paragraph a genuine Word list item.

    The glyph is removed from the text because the list definition draws it now; leaving
    both renders two bullets. The manual `w:ind` is removed as well, so indentation comes
    from the numbering definition and is identical on every platform, which is the fix for
    the SharePoint report.

    A continuation paragraph (`**Solution:** ...` under a problem bullet) never opens with
    a glyph, so it is untouched here and keeps the indent `normalize_bullet_indent` gave it.
    """
    from docx.oxml import OxmlElement

    converted = 0
    for para in _all_paragraphs(doc):
        if not _is_glyph_bullet(para):
            continue

        # Remove the leading glyph plus the tab or spaces that follow it, from whichever
        # run carries it. Editing run text keeps the run's formatting intact.
        for run in para.runs:
            if not (run.text or "").strip():
                continue
            stripped = run.text.lstrip()
            if stripped and stripped[0] in _BULLET_GLYPHS:
                lead = run.text[: len(run.text) - len(stripped)]
                run.text = lead + stripped[1:].lstrip("\t ")
            break
        # A tab can also live in its own run; drop a now-leading one.
        for run in para.runs:
            if run.text == "\t":
                run.text = ""
                break
            if (run.text or "").strip():
                break

        pPr = para._p.get_or_add_pPr()
        ind = pPr.find(qn("w:ind"))
        if ind is not None:
            pPr.remove(ind)
        numPr = OxmlElement("w:numPr")
        ilvl = OxmlElement("w:ilvl"); ilvl.set(qn("w:val"), "0")
        nid = OxmlElement("w:numId"); nid.set(qn("w:val"), str(num_id))
        numPr.append(ilvl); numPr.append(nid)
        # numPr belongs immediately after pStyle in the pPr schema order.
        style = pPr.find(qn("w:pStyle"))
        if style is not None:
            style.addnext(numPr)
        else:
            pPr.insert(0, numPr)
        converted += 1
    return converted


def normalize_bullet_spacing(doc, before_pt: float = 0, after_pt: float = 6) -> int:
    """One space-before and one space-after for every list item in the document.

    A delivered file carried SIX different spacing pairs across its bullets, including
    eleven with none set at all: (0,6) on 117, (6,8) on 14, (2,4) on 13, nothing on 11,
    (12,6) on 8 and (4,4) on 5. A bullet with 12pt before sitting next to one with 0
    is twice the gap for no reason, and the gap visibly changes down the page. Each pass
    that touches paragraphs had stamped its own value and none of them ran last.

    Deliberately NARROW: list items only. The broad body-paragraph sweep that used to live
    in `build()` was disabled because it regressed the caption-to-bullet gap, and that
    lesson stands. Caption gaps, image paragraphs and headings are not touched here.
    """
    changed = 0
    for para in _all_paragraphs(doc):
        pPr = para._p.find(qn("w:pPr"))
        if pPr is None or pPr.find(qn("w:numPr")) is None:
            continue
        if para.style.name.lower().startswith("heading"):
            continue                      # the numbered headings are list items too
        fmt = para.paragraph_format
        want_before, want_after = Pt(before_pt), Pt(after_pt)
        if fmt.space_before != want_before or fmt.space_after != want_after:
            fmt.space_before = want_before
            fmt.space_after = want_after
            changed += 1
    return changed


def strip_typed_numbers_from_autonumbered_headings(doc) -> int:
    """Remove a hand-typed section number from a heading that Word already numbers.

    THE DEFECT THIS FIXES, reported on a v2 delivery. The template's `Testing Workflow`,
    `Testing Scope`, `Testing Process` and `User Acceptance Testing` headings carry BOTH
    `numPr(numId=1, ilvl=2)`, whose level format is `%1.%2.%3.`, AND a number typed into
    the text. Word prints its own number and then the text, so the heading renders as
    `3.5.1. 4.5.1 Testing Workflow`.

    It hid for a long time because the two numbers agreed: while a SECURITY & DATA
    PROTECTION section sat at 3, development management was 4 and both read `4.5.1`. Turn
    that optional section off and development management becomes 3, the automatic number
    becomes `3.5.1` and the typed one still says `4.5.1`. So the duplication was always
    there and the section drop only made it visible, which is the recurring shape of a
    hand-typed number going stale.

    **Only strips where `numPr` is present.** `2.1.1 System Context` and the other injected
    System Overview sub-headings have NO numbering of their own and their number IS the
    typed text, so they must keep it. That distinction is the whole safety of this pass.
    """
    stripped = 0
    for para in _all_paragraphs(doc):
        if not (para.style.name or "").lower().startswith("heading"):
            continue
        pPr = para._p.find(qn("w:pPr"))
        if pPr is None or pPr.find(qn("w:numPr")) is None:
            continue                      # numbers itself by typing; leave it alone
        text = (para.text or "").lstrip()
        m = re.match(r"^\d+(?:\.\d+)*\.?\s+", text)
        if not m:
            continue
        lead = m.group(0)
        for run in para.runs:
            if not (run.text or "").strip():
                continue
            body = run.text.lstrip()
            if body.startswith(lead):
                keep = run.text[: len(run.text) - len(body)] + body[len(lead):]
                run.text = keep
                stripped += 1
            break
    return stripped


def apply_keep_with_next(doc) -> int:
    """Prevent the #1 cause of ugly whitespace / unnecessary page breaks: a
    heading (or a diagram intro / image) stranded at the bottom of a page while
    its content flows to the next. Word's keep-with-next pulls a heading down
    to start on the same page as the block it introduces, and keep-together
    stops a paragraph splitting across pages. Applied to every heading, every
    image paragraph, and the diagram intro paragraph. Durable style rule — runs
    on every build so no project regresses.
    """
    touched = 0
    paras = doc.paragraphs
    for idx, p in enumerate(paras):
        sname = p.style.name if p.style else ""
        is_heading = sname.startswith("Heading")
        has_image = bool(p._p.findall(".//" + qn("w:drawing")))
        if is_heading:
            pf = p.paragraph_format
            pf.keep_with_next = True
            pf.keep_together = True
            touched += 1
        elif has_image:
            # image should stay with the caption/bullets that follow it
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.keep_together = True
            touched += 1
    return touched


# Replacement keys consumed by dedicated logic rather than a {{KEY}} placeholder
# in the template (so they are exempt from the missing-placeholder guard below).
_NON_PLACEHOLDER_KEYS = {"diagram_captions"}


def validate_template_placeholders(template: Path, replacements: dict) -> None:
    """Fail loudly if a content key carries data but the template has no slot for it.

    Root cause of the "Mobile App Strategy heading present but body empty" bug:
    the template was missing the ``{{MOBILE_APP_STRATEGY}}`` placeholder, so the
    non-null value in replacements.json had nowhere to render and the section
    shipped empty (drop_section_if_empty also kept the heading because the data
    was non-empty). A content key with data but no placeholder = guaranteed lost
    content, so we stop the build instead of silently producing an empty section.
    """
    present: set[str] = set()
    with zipfile.ZipFile(template) as zf:
        for name in zf.namelist():
            if name.startswith("word/") and name.endswith(".xml"):
                xml = zf.read(name).decode("utf-8", "ignore")
                present.update(re.findall(r"\{\{([A-Z0-9_]+)\}\}", xml))
    missing = []
    for key, val in replacements.items():
        if key in _NON_PLACEHOLDER_KEYS:
            continue
        truthy = val not in (None, "", "null", [])
        if truthy and key.upper() not in present:
            missing.append(key)
    if missing:
        raise SystemExit(
            "! Template is missing a placeholder for content key(s): "
            + ", ".join(sorted(missing))
            + ".\n  Each non-empty content key needs a matching {{KEY}} slot in "
            "the template (e.g. mobile_app_strategy -> {{MOBILE_APP_STRATEGY}}).\n"
            "  Add the placeholder paragraph under its heading, or set the value "
            "to null if the section should be dropped."
        )


def validate_template_image_headings(template: Path) -> None:
    """Fail loudly if the template embeds an image inside a Heading-styled (or
    outline-levelled) body paragraph.

    Root cause of the "template images leak into the Table of Contents on
    SharePoint" bug (see LESSONS_LEARNED 2026-07-13): the template's TOC field
    collects entries BY STYLE NAME (``TOC \\t "Heading 1,1,...,Heading 6,6,"``)
    and by applied outline level (``\\u``). An image sitting in a Heading-styled
    paragraph — even an empty one — therefore becomes a TOC entry, so the image
    gets pulled into the table of contents when Word/SharePoint updates fields. Figure and
    decorative images must live in Normal (non-Heading) paragraphs with direct
    centering/spacing; skill-inserted diagrams already do, which is why only
    template-embedded images were ever affected.

    Only ``word/document.xml`` is scanned (headers/footers are not collected by a
    TOC). This runs on the TEMPLATE, before skill diagrams are inserted, so it
    never false-positives on generated figures.
    """
    import xml.etree.ElementTree as ET
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(template) as zf:
        try:
            sroot = ET.fromstring(zf.read("word/styles.xml").decode("utf-8", "ignore"))
            sid_name = {}
            for st in sroot.iter(W + "style"):
                nm = st.find(W + "name")
                sid_name[st.get(W + "styleId")] = (nm.get(W + "val").lower() if nm is not None else "")
        except (KeyError, ET.ParseError):
            sid_name = {}
        try:
            droot = ET.fromstring(zf.read("word/document.xml").decode("utf-8", "ignore"))
        except (KeyError, ET.ParseError):
            return
    offenders = 0
    for p in droot.iter(W + "p"):
        if p.find(".//" + W + "drawing") is None and p.find(".//" + W + "pict") is None:
            continue
        ppr = p.find(W + "pPr")
        if ppr is None:
            continue
        ps = ppr.find(W + "pStyle")
        style_name = sid_name.get(ps.get(W + "val"), "") if ps is not None else ""
        ol = ppr.find(W + "outlineLvl")
        ol_val = int(ol.get(W + "val")) if ol is not None else None
        if style_name.startswith("heading") or (ol_val is not None and ol_val < 9):
            offenders += 1
    if offenders:
        raise SystemExit(
            f"! Template has {offenders} image paragraph(s) in a Heading style / "
            "outline level.\n  The TOC field collects by style name "
            '(\\t "Heading 1,1,...,Heading 6,6,"), so those images leak into the Table '
            "of Contents when SharePoint/Word updates fields.\n  Demote each image "
            "paragraph to Normal (keep its direct centering/spacing so the image stays "
            "put but is excluded from the TOC). See LESSONS_LEARNED 2026-07-13."
        )


def build(template: Path, replacements: dict, diagrams: list, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    # Guard: every non-empty content key must have a {{KEY}} slot in the template.
    validate_template_placeholders(template, replacements)
    # Guard: no template image may sit in a Heading paragraph (it would leak into the TOC).
    validate_template_image_headings(template)
    shutil.copyfile(template, out)

    doc = Document(str(out))

    # 1. Text replacements across body, tables, and headers/footers.
    # Pre-pass: any techstack_* value that's a list of {name, description} dicts
    # is converted to a styled 2-col table at the placeholder position.
    rendered_tech = render_techstack_tables(doc, replacements)
    if rendered_tech:
        print(f"Techstack tables rendered: {len(rendered_tech)} ({', '.join(sorted(rendered_tech))})")

    total = 0
    for p in doc.paragraphs:
        total += replace_in_paragraph(p, replacements)
    for t in doc.tables:
        total += replace_in_table(t, replacements)
    for section in doc.sections:
        total += replace_in_section_parts(section, replacements)
    print(f"Text replacements: {total}")

    # 2. Inject per-project H6 sub-headings under System Overview.
    #    Skip any diagram whose title already matches the existing anchor
    #    (avoids "2.1.1 System Context" / "2.1.2 System Context" duplicates).
    subs = _collect_subheadings(diagrams, existing_anchor_text=SUBHEADING_ANCHOR)
    injected = inject_subheadings_after_anchor(doc, SUBHEADING_ANCHOR, subs)
    print(f"Sub-headings injected after '{SUBHEADING_ANCHOR}': {injected}")

    # 3. Drop optional empty sections (template defines them; we strip if data is null).
    # The replacements key used for each is derived from heading text by
    # lowercasing + underscoring (see drop_section_if_empty). The headings
    # below have been chosen so the derived key matches the documented
    # Phase 4 schema (mobile_app_strategy, techstack_data, techstack_ai).
    # Heading text -> explicit content key. The Data/AI sub-headings now carry a
    # fixed label ("Data" / "AI") with the {{TECHSTACK_*}} placeholder in the body
    # paragraph beneath, so the content key must be passed explicitly. Skip the
    # drop for any techstack section already rendered as a table (its placeholder
    # is gone and a table sits under the heading — dropping would delete the table).
    drop_specs = [("Mobile App Strategy", None)]
    if "techstack_data" not in rendered_tech:
        drop_specs.append(("Data", "techstack_data"))
    if "techstack_ai" not in rendered_tech:
        drop_specs.append(("AI", "techstack_ai"))
    dropped = 0

    # The RFP-driven sections (team, delivery plan, support, risks, references,
    # contractual exceptions) are all OPTIONAL. Drop the whole H3 when every one of
    # its subsections is empty; otherwise keep the H3 and drop only the empty
    # subsections. Order matters: the H3 pass must run first, because dropping an
    # H3 also removes its children and a later child drop would then find nothing.
    # A section rendered as a TABLE has had its value blanked by
    # render_techstack_tables, so that the text pass does not refill the placeholder it
    # already consumed. To the emptiness test below that blank looks like "no content",
    # and the heading gets dropped while its table sits underneath it, orphaned. That is
    # how the Roles & Responsibilities heading disappeared from a delivery whose roles
    # table had rendered perfectly. Treat a rendered table as content.
    def is_empty(key):
        if key in rendered_tech:
            return False
        return replacements.get(key) in (None, "", "null", [])

    for h3_heading, children in OPTIONAL_SECTION_GROUPS:
        keys = [key for _sub, key in children]
        if all(is_empty(k) for k in keys):
            if drop_section_if_empty(doc, h3_heading, replacements, keys[0]):
                dropped += 1
            continue
        for sub, key in children:
            if sub and not is_empty(key):
                continue
            if sub and drop_section_if_empty(doc, sub, replacements, key):
                dropped += 1
    for sub, key in OPTIONAL_SUBSECTIONS:
        if is_empty(key) and drop_section_if_empty(doc, sub, replacements, key):
            dropped += 1

    for heading_text, ckey in drop_specs:
        if drop_section_if_empty(doc, heading_text, replacements, ckey):
            dropped += 1
    print(f"Optional sections dropped: {dropped}")

    # 4. Diagram insertions.
    inserted = 0
    for d in diagrams:
        png = Path(d["png"])
        if not png.exists():
            print(f"  ! diagram PNG missing: {png}")
            continue
        ok = insert_image_after_heading(
            doc,
            d["target_heading"],
            png,
            d.get("caption", ""),
            width_inches=d.get("width_inches", 6.5),
            intro_paragraph=d.get("intro_paragraph"),
            explanation_bullets=d.get("explanation_bullets"),
        )
        marker = "ok" if ok else "skipped (heading not found)"
        n_bullets = len(d.get("explanation_bullets") or [])
        print(f"  [{marker}] {d['slug']} -> {d['target_heading']} ({n_bullets} bullets)")
        if ok:
            inserted += 1
    print(f"Diagrams inserted: {inserted}/{len(diagrams)}")

    # 5. Cleanup empty 1x1 caption tables.
    removed_tables = remove_empty_caption_tables(doc)
    print(f"Empty caption tables removed: {removed_tables}")

    # 6a. Pull heading text back to flush-left (template inherits L=36 which
    #     makes headings appear deeper-indented than their body content).
    n_norm = normalize_heading_indents(doc)
    print(f"Heading indents normalized: {n_norm}")

    # 6a-ii. Remove blank 'spacer' paragraphs adjacent to headings so the
    #        headings' own space-before/after controls the rhythm — kills the
    #        extra blank-line gap between, for example, '1.' and '1.1'.
    n_blank = remove_heading_adjacent_blank_paragraphs(doc)
    print(f"Heading-adjacent blank paragraphs removed: {n_blank}")

    # 6a-iii. A heading that Word numbers must not ALSO carry a typed number.
    n_dup = strip_typed_numbers_from_autonumbered_headings(doc)
    if n_dup:
        print(f"Duplicate typed heading numbers stripped: {n_dup}")

    # 6b. Bump heading space-before/after so section transitions are visible.
    n_sp = boost_heading_spacing(doc)
    print(f"Heading spacing boosted: {n_sp}")

    # 6b-ii. Keep headings/images with the block they introduce — stops a
    #        heading orphaned at a page bottom, the main cause of an unwanted
    #        page break and the white space it leaves behind.
    n_kwn = apply_keep_with_next(doc)
    print(f"Keep-with-next applied: {n_kwn}")

    # 6c. Every Figure caption table needs whitespace after it — body text
    #     touching the caption is a layout defect the user has flagged.
    n_cap = ensure_caption_followed_by_gap(doc, min_pt=12)
    print(f"Paragraphs given gap-after-caption: {n_cap}")

    # 6d. Center every inline image (template-inherited diagrams default to left).
    n_img = center_image_paragraphs(doc)
    if n_img:
        print(f"Image paragraphs centered: {n_img}")

    # 6e. (Disabled) Body paragraph spacing normalization — removed
    #     because the broad sweep regressed the caption-to-bullet gap.
    #     Per [[feedback-dont-touch-fixed]], only touch what's broken.

    # 6f. Justify body.
    justified = justify_body(doc)
    print(f"Paragraphs justified: {justified}")

    # 6g. Strip trailing empty paragraphs so no blank page renders at the end
    #     (SharePoint / Office-365-online are strict about this).
    n_tail = remove_trailing_empty_paragraphs(doc)
    if n_tail:
        print(f"Trailing empty paragraphs removed: {n_tail}")

    # 7. Save.
    bullets = normalize_bullet_indent(doc)
    print(f"Bullet indents normalized: {bullets}")

    # 7a. Turn the typed glyph bullets into REAL Word list items, and give every
    #     one of them the same spacing. See the two functions for why.
    num_id = ensure_bullet_numbering(doc)
    n_real = convert_glyph_bullets_to_real_lists(doc, num_id)
    print(f"Glyph bullets converted to Word list items: {n_real} (numId={num_id})")
    n_bsp = normalize_bullet_spacing(doc)
    print(f"Bullet spacing normalized: {n_bsp}")

    # 7b. The bullet pass above runs AFTER 6c and overwrites the 12pt gap that 6c put on
    #     the first paragraph under a Figure caption, whenever that paragraph is a bullet.
    #     That is precisely the caption-to-bullet regression which got the old broad
    #     spacing sweep disabled at 6e, and it came straight back the first time this pass
    #     ran: eight captions reported `caption_text_crush`. Re-assert the caption gap last
    #     rather than teach the bullet pass about captions, so the rule lives in one place.
    n_cap2 = ensure_caption_followed_by_gap(doc, min_pt=12)
    if n_cap2:
        print(f"Caption gap re-asserted after bullet spacing: {n_cap2}")

    doc.save(str(out))

    # 8. Final XML-level placeholder sweep — catches TOC cache, comments etc.
    n_xml = replace_remaining_placeholders_xml(out, replacements)
    if n_xml:
        print(f"XML-level placeholder fills: {n_xml}")

    # 9. autoHyphenation + updateFields patch on the saved file.
    n_num = patch_numbering_xml(out)
    if n_num:
        print(f"Heading numbering left-aligned: {n_num} level(s)")
    n_fig = renumber_figure_sequence_cache(out)
    if n_fig:
        print(f"Figure SEQ cache renumbered: {n_fig}")
    patch_settings_xml(out)

    print(f"\nOutput: {out}  ({out.stat().st_size:,} bytes)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", type=Path, required=True)
    ap.add_argument("--replacements", type=Path, required=True)
    ap.add_argument("--diagrams", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    if not args.template.exists():
        print(f"! template missing: {args.template}", file=sys.stderr); return 1
    if not args.replacements.exists():
        print(f"! replacements missing: {args.replacements}", file=sys.stderr); return 1
    if not args.diagrams.exists():
        print(f"! diagrams missing: {args.diagrams}", file=sys.stderr); return 1

    replacements = load_json(args.replacements)
    diagrams = load_json(args.diagrams)
    build(args.template, replacements, diagrams, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
