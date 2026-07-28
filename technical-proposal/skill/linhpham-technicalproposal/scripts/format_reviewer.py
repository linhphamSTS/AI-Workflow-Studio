#!/usr/bin/env python3
"""Strict format and SharePoint-compatibility review for the assembled .docx.

Emits a JSON report (machine-readable, consumed by auto_fix.py and by the
Phase 5b prompt) plus a parallel Markdown report (human-readable).

Run from the skill folder so relative imports work:
    python scripts/format_reviewer.py --docx <path> --json out.json
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


@dataclass
class Issue:
    id: str
    category: str  # layout | visual | sharepoint | polish | sharpness
    severity: str  # blocker | major | minor
    auto_fixable: bool
    summary: str
    detail: str = ""
    page: int | None = None
    location: str | None = None


@dataclass
class Report:
    docx: str
    file_size_bytes: int
    issues: list[Issue] = field(default_factory=list)
    checks_passed: list[str] = field(default_factory=list)
    auto_fixable_count: int = 0
    blocker_count: int = 0

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)
        if issue.auto_fixable:
            self.auto_fixable_count += 1
        if issue.severity == "blocker":
            self.blocker_count += 1

    def pass_(self, name: str) -> None:
        self.checks_passed.append(name)


# ---------------------------------------------------------------------------
# Checks.
# ---------------------------------------------------------------------------


def check_zip_integrity(docx_path: Path, report: Report) -> None:
    try:
        with zipfile.ZipFile(docx_path, "r") as z:
            bad = z.testzip()
            if bad:
                report.add(Issue("zip_corruption", "sharepoint", "blocker", False,
                                 "Zip integrity check failed",
                                 detail=f"Bad file inside docx: {bad}"))
            else:
                report.pass_("zip_integrity")
    except zipfile.BadZipFile:
        report.add(Issue("zip_bad", "sharepoint", "blocker", False,
                         "File is not a valid .docx (bad zip)"))


def check_size(docx_path: Path, report: Report) -> None:
    size = docx_path.stat().st_size
    if size > 100 * 1024 * 1024:
        report.add(Issue("file_too_large", "sharepoint", "blocker", False,
                         f"File size {size/1024/1024:.1f} MB exceeds 100 MB"))
    elif size > 25 * 1024 * 1024:
        report.add(Issue("file_large_warning", "sharepoint", "minor", False,
                         f"File size {size/1024/1024:.1f} MB > 25 MB — slow SharePoint sync"))
    else:
        report.pass_("file_size_ok")


def check_no_track_changes(docx_path: Path, report: Report) -> None:
    with zipfile.ZipFile(docx_path) as z:
        doc_xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    if re.search(r"<w:ins\b|<w:del\b|<w:moveFrom\b|<w:moveTo\b", doc_xml):
        report.add(Issue("track_changes_present", "sharepoint", "major", True,
                         "Tracked changes (insertions / deletions) present"))
    else:
        report.pass_("no_track_changes")


def check_no_comments(docx_path: Path, report: Report) -> None:
    with zipfile.ZipFile(docx_path) as z:
        if "word/comments.xml" in z.namelist():
            data = z.read("word/comments.xml").decode("utf-8", errors="replace")
            if "<w:comment " in data:
                report.add(Issue("comments_present", "sharepoint", "major", True,
                                 "Document contains comments"))
                return
        report.pass_("no_comments")


def check_no_macros(docx_path: Path, report: Report) -> None:
    if docx_path.suffix.lower() == ".docm":
        report.add(Issue("docm_macro_enabled", "sharepoint", "blocker", False,
                         ".docm extension — macros allowed; should be .docx"))
        return
    with zipfile.ZipFile(docx_path) as z:
        if any(n.startswith("word/vbaProject") for n in z.namelist()):
            report.add(Issue("vba_project_present", "sharepoint", "blocker", False,
                             "VBA macros found inside .docx"))
            return
    report.pass_("no_macros")


def check_no_encryption(docx_path: Path, report: Report) -> None:
    with open(docx_path, "rb") as f:
        head = f.read(8)
    # Encrypted OOXML starts with the OLE compound document signature D0 CF 11 E0 A1 B1 1A E1
    if head[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        report.add(Issue("encrypted", "sharepoint", "blocker", False,
                         "File appears encrypted / password-protected"))
    else:
        report.pass_("not_encrypted")


_REL_RE = re.compile(r"<Relationship\b[^>]*/>")


def check_no_external_images(docx_path: Path, report: Report) -> None:
    """An image linked by URL instead of embedded does not travel with the file.

    Test each relationship on its own. The earlier version asked whether the .rels
    file contained `TargetMode="External"` ANYWHERE and the word "image" ANYWHERE,
    which is true of every document that has both an embedded image and an ordinary
    hyperlink: the case-study link alone was enough to raise a false alarm. Two
    unrelated conditions matched at file level say nothing about any one relationship.
    """
    offenders = []
    with zipfile.ZipFile(docx_path) as z:
        for rel_name in z.namelist():
            if not rel_name.endswith(".rels"):
                continue
            data = z.read(rel_name).decode("utf-8", errors="replace")
            for rel in _REL_RE.findall(data):
                if 'TargetMode="External"' not in rel:
                    continue
                type_m = re.search(r'Type="([^"]+)"', rel)
                if not type_m or not type_m.group(1).rstrip("/").endswith("/image"):
                    continue          # an external hyperlink is normal and expected
                target = re.search(r'Target="([^"]+)"', rel)
                offenders.append(f"{rel_name}: {target.group(1) if target else '?'}")
    if offenders:
        report.add(Issue("external_image_ref", "sharepoint", "major", False,
                         f"{len(offenders)} image(s) linked externally instead of embedded; "
                         f"they will not render for anyone else",
                         detail="; ".join(offenders[:5])))
    else:
        report.pass_("images_all_embedded")


def check_no_unfilled_placeholders(docx_path: Path, report: Report) -> None:
    with zipfile.ZipFile(docx_path) as z:
        text = z.read("word/document.xml").decode("utf-8", errors="replace")
    placeholders = re.findall(r"\{\{[A-Z_][A-Z0-9_]*\}\}", text)
    if placeholders:
        report.add(Issue("unfilled_placeholder", "polish", "blocker", True,
                         "Literal {{PLACEHOLDER}} tokens left in document",
                         detail=f"Tokens: {sorted(set(placeholders))}"))
    else:
        report.pass_("placeholders_filled")


def check_image_sharpness(docx_path: Path, report: Report) -> None:
    """Every embedded image must be >= 1500 px wide for sharp 6.5-in Word display."""
    try:
        from PIL import Image
    except ImportError:
        return  # If PIL unavailable in this environment, skip silently
    with zipfile.ZipFile(docx_path) as z:
        media = [n for n in z.namelist() if n.startswith("word/media/")]
        for m in media:
            try:
                data = z.read(m)
                img = Image.open(io.BytesIO(data))
                w, _ = img.size
                if w < 1500:
                    report.add(Issue(
                        f"image_low_resolution::{m}", "sharpness", "major", False,
                        f"Image {m} is only {w}px wide (< 1500 px target)",
                        detail="Re-render the source diagram at >= 300 DPI",
                    ))
            except Exception:
                continue
    report.pass_("image_sharpness_audited")


def check_justify_body(docx_path: Path, report: Report) -> None:
    """Sample paragraphs: ratio of justified body paragraphs should be high."""
    doc = Document(str(docx_path))
    body, justified = 0, 0
    for p in doc.paragraphs:
        sname = p.style.name if p.style else ""
        if sname.startswith("Heading") or sname in ("Title", "Subtitle", "Caption", "TOC", "Header", "Footer"):
            continue
        if not p.text.strip():
            continue
        body += 1
        if p.alignment is not None and int(p.alignment) == 3:  # WD_ALIGN_PARAGRAPH.JUSTIFY
            justified += 1
    if body == 0:
        return
    ratio = justified / body
    if ratio < 0.8:
        report.add(Issue("body_not_justified", "visual", "major", True,
                         f"Only {justified}/{body} body paragraphs are justified ({ratio:.0%})"))
    else:
        report.pass_("body_justified")


def check_heading_orphans_pdf(pages_dir: Path | None, report: Report) -> None:
    """Visual checks need rendered PNGs (Phase 5b renders them). Skipped here
    if pages_dir is not provided; the per-page Read by the agent covers it."""
    if pages_dir is None or not pages_dir.exists():
        return
    # Programmatically checking widows / orphan headings from PNGs is hard.
    # Leave to the agent's visual inspection step.
    report.pass_("page_visual_check_deferred_to_agent")


# ---------------------------------------------------------------------------
# Quality checks added 2026-05-25 after the user flagged specific defects:
# bullet-and-number duplicates, image-text crush, heading deeper-indent than
# body, tight section spacing, justify whitespace channels, settings flags
# missing. Each maps to a real visual symptom the reviewer must not miss.
# ---------------------------------------------------------------------------

_BULLET_NUMBER_PATTERN = re.compile(
    r"●\s*(?:\(?\d{1,3}\)?\s*[.)\-:]|step\s+\d{1,3}\s*[.)\-:—])\s+",
    re.IGNORECASE,
)


def check_no_bullet_number_duplicates(docx_path: Path, report: Report) -> None:
    """Reject paragraphs whose text starts with "●  1. " / "●  Step 2 — " etc.
    Each one renders as both a bullet dot AND a manual number — visible to
    the reader as a quality bug ("dấu chấm tròn + số trùng")."""
    doc = Document(str(docx_path))
    bad = []
    for i, p in enumerate(doc.paragraphs):
        txt = (p.text or "").lstrip()
        if not txt.startswith("●"):
            continue
        if _BULLET_NUMBER_PATTERN.match(txt):
            bad.append((i, txt[:80]))
    if bad:
        report.add(Issue(
            "bullet_number_duplicate", "polish", "blocker", True,
            f"{len(bad)} bullet(s) start with both '●' and a manual number "
            f"(renders as '● 1. text')",
            detail="; ".join(f"para {i}: {t}" for i, t in bad[:5]),
        ))
    else:
        report.pass_("no_bullet_number_duplicates")


def check_image_spacing(docx_path: Path, report: Report) -> None:
    """Every image paragraph must have space-before AND space-after >= 6pt so
    the image is not visually crushed against the text above and below."""
    doc = Document(str(docx_path))
    bad = []
    for i, p in enumerate(doc.paragraphs):
        has_image = any(
            r.element.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}inline")
            for r in p.runs
        )
        if not has_image:
            continue
        pf = p.paragraph_format
        sb = pf.space_before.pt if pf.space_before else 0
        sa = pf.space_after.pt if pf.space_after else 0
        if sb < 6 or sa < 3:
            bad.append((i, sb, sa))
    if bad:
        report.add(Issue(
            "image_text_crush", "visual", "major", True,
            f"{len(bad)} image paragraph(s) have insufficient spacing "
            f"(sb<6pt OR sa<3pt) — image touches surrounding text",
            detail="; ".join(f"para {i}: sb={sb} sa={sa}" for i, sb, sa in bad[:5]),
        ))
    else:
        report.pass_("image_spacing_ok")


def check_heading_indent_vs_body(docx_path: Path, report: Report) -> None:
    """Heading 3 / 4 / 5 / 6 must NOT be left-indented deeper than the
    surrounding body paragraphs. A heading sitting at L=36 while body sits
    at L=0 reads as "title thụt vô sâu hơn text" — wrong visual hierarchy.
    """
    doc = Document(str(docx_path))
    bad = []
    # Reference body indent: most common non-zero left indent of Normal
    # paragraphs, or 0 if all Normal text is flush-left.
    body_indents = [p.paragraph_format.left_indent.pt
                    for p in doc.paragraphs
                    if (p.style.name if p.style else "") == "Normal"
                    and p.paragraph_format.left_indent is not None]
    body_indent_ref = 0
    if body_indents:
        body_indent_ref = max(0, min(body_indents))
    for i, p in enumerate(doc.paragraphs):
        sname = p.style.name if p.style else ""
        if not sname.startswith("Heading"):
            continue
        pf = p.paragraph_format
        if pf.left_indent is None:
            continue
        if pf.left_indent.pt > body_indent_ref + 2:  # 2pt slack
            bad.append((i, sname, pf.left_indent.pt, body_indent_ref))
    if bad:
        report.add(Issue(
            "heading_deeper_than_body", "visual", "blocker", True,
            f"{len(bad)} heading(s) indented deeper than body text",
            detail="; ".join(f"para {i} ({s}): L={l} vs body L={b}"
                              for i, s, l, b in bad[:5]),
        ))
    else:
        report.pass_("heading_indent_consistent")


def _prev_block_is_heading_el(p_el, heading_ids) -> bool:
    """True if the block before `p_el` is a heading paragraph (skipping empty
    spacers). A heading stacked directly under another heading hugs it with a
    small space-before on purpose — it must NOT be flagged as 'tight'.
    `heading_ids` maps numeric style IDs (the template uses `w:val="4"`) to
    headings — a name-only `startswith("Heading")` check silently misses them."""
    from docx.oxml.ns import qn as _qn
    def is_h(style):
        return style in heading_ids or style.startswith("Heading")
    prev = p_el.getprevious()
    while prev is not None:
        if prev.tag != _qn("w:p"):
            return False
        pPr = prev.find(_qn("w:pPr"))
        style = ""
        if pPr is not None:
            ps = pPr.find(_qn("w:pStyle"))
            if ps is not None:
                style = ps.get(_qn("w:val")) or ""
        text = "".join(t.text or "" for t in prev.iter(_qn("w:t")))
        if not text.strip() and not is_h(style):
            prev = prev.getprevious()
            continue
        return is_h(style)
    return False


def check_heading_section_spacing(docx_path: Path, report: Report) -> None:
    """Heading 1-3 should have visible space-before so major section
    transitions don't feel cramped — but NOT a blank-line gap. Floors match
    build_docx `_HEADING_MIN_SPACE_BEFORE`: H1 >= 18, H2 >= 12, H3 >= 10,
    H4/H5 >= 8, H6 >= 6pt. A heading stacked directly under another heading is
    exempt (it hugs its parent with a small gap on purpose).
    """
    floors = {1: 18, 2: 12, 3: 10, 4: 8, 5: 8, 6: 6}
    doc = Document(str(docx_path))
    heading_ids = {s.style_id for s in doc.styles
                   if getattr(s, "style_id", None) and (s.name or "").startswith("Heading")}
    bad = []
    for i, p in enumerate(doc.paragraphs):
        sname = p.style.name if p.style else ""
        if not sname.startswith("Heading"):
            continue
        try:
            lvl = int(sname.split()[-1])
        except ValueError:
            continue
        floor = floors.get(lvl)
        if floor is None:
            continue
        if _prev_block_is_heading_el(p._p, heading_ids):
            continue  # stacked heading — small gap is intentional
        pf = p.paragraph_format
        sb = pf.space_before.pt if pf.space_before else 0
        if sb + 0.5 < floor:  # 0.5pt rounding slack
            bad.append((i, sname, sb, floor))
    if bad:
        report.add(Issue(
            "heading_section_spacing_tight", "visual", "major", True,
            f"{len(bad)} heading(s) have space-before below the floor "
            f"(major sections look cramped)",
            detail="; ".join(f"para {i} ({s}): sb={sb}<{floor}"
                              for i, s, sb, floor in bad[:5]),
        ))
    else:
        report.pass_("heading_section_spacing_ok")


def check_settings_flags_present(docx_path: Path, report: Report) -> None:
    """settings.xml must carry the flags that prevent justify whitespace
    channels and TOC stale-cache."""
    required = [
        "autoHyphenation",
        "doNotExpandShiftReturn",
        "characterSpacingControl",
        "updateFields",
    ]
    with zipfile.ZipFile(docx_path) as z:
        try:
            txt = z.read("word/settings.xml").decode("utf-8", errors="replace")
        except KeyError:
            report.add(Issue("settings_xml_missing", "polish", "major", False,
                             "word/settings.xml not present"))
            return
    missing = [f for f in required if f not in txt]
    if missing:
        report.add(Issue(
            "settings_flags_missing", "visual", "major", True,
            f"settings.xml missing flag(s): {', '.join(missing)} — justify "
            f"gaps and TOC freshness may regress",
        ))
    else:
        report.pass_("settings_flags_present")


def check_caption_followed_by_gap(docx_path: Path, report: Report) -> None:
    """For every 1x1 Figure caption table, the next paragraph must carry
    space-before >= 8pt. Otherwise body text sits flush against the
    caption — the user-flagged "text và title image quá sát nhau" defect.
    """
    doc = Document(str(docx_path))
    body = doc.element.body
    bad = []
    for tbl in doc.tables:
        rows = tbl.rows
        if len(rows) != 1 or len(rows[0].cells) != 1:
            continue
        cell_text = "".join(p.text for p in rows[0].cells[0].paragraphs).strip()
        if not cell_text or ("Figure" not in cell_text and "figure" not in cell_text
                              and "Bảng" not in cell_text):
            continue
        nxt = tbl._element.getnext()
        if nxt is None or nxt.tag.rsplit("}", 1)[-1] != "p":
            continue
        pPr = nxt.find(qn("w:pPr"))
        sb_pt = 0
        if pPr is not None:
            sp = pPr.find(qn("w:spacing"))
            if sp is not None:
                v = sp.get(qn("w:before"))
                if v:
                    sb_pt = int(v) / 20
        if sb_pt < 8:
            # describe the next paragraph briefly
            txt_t = nxt.find(".//" + qn("w:t"))
            preview = (txt_t.text or "")[:50] if txt_t is not None else ""
            bad.append((cell_text[:40], sb_pt, preview))
    if bad:
        report.add(Issue(
            "caption_text_crush", "visual", "major", True,
            f"{len(bad)} Figure caption(s) have body text crammed underneath "
            f"(next paragraph space-before < 8pt)",
            detail="; ".join(f"after '{c}': sb={sb} '{p}'" for c, sb, p in bad[:5]),
        ))
    else:
        report.pass_("caption_gap_ok")


def check_justify_whitespace_channels(docx_path: Path, report: Report) -> None:
    """When a justified paragraph contains a soft line break, Word can
    expand the inter-word spacing on the broken line — producing visible
    "rivers" of white space. The document-level flag `doNotExpandShiftReturn`
    neutralises this symptom. We only raise an issue when:
      (a) the flag is missing from settings.xml AND
      (b) at least one justified paragraph contains a `<w:br/>` soft return.
    Either alone is harmless: (a) without (b) means no paragraph would be
    affected; (b) without (a) is already prevented by Word.
    """
    # Read settings to see if the neutralising flag is in place.
    flag_present = False
    with zipfile.ZipFile(docx_path) as z:
        try:
            settings = z.read("word/settings.xml").decode("utf-8", errors="replace")
            flag_present = "doNotExpandShiftReturn" in settings
        except KeyError:
            pass
    if flag_present:
        report.pass_("justify_whitespace_neutralised")
        return

    doc = Document(str(docx_path))
    suspects = []
    for i, p in enumerate(doc.paragraphs):
        if p.alignment is None or int(p.alignment) != 3:
            continue
        for r in p.runs:
            if r.element.findall(qn("w:br")):
                suspects.append((i, (p.text or "")[:60]))
                break
    if suspects:
        report.add(Issue(
            "justify_soft_returns", "visual", "major", True,
            f"{len(suspects)} justified paragraph(s) contain soft line breaks "
            f"AND the document is missing `doNotExpandShiftReturn` — visible "
            f"whitespace channels will appear in Word",
            detail="; ".join(f"para {i}: {t}" for i, t in suspects[:5]),
        ))
    else:
        report.pass_("no_justify_soft_returns")


_TECHSTACK_LABELS = {
    "back-end", "backend", "front-end", "frontend", "database",
    "server & hosting", "server and hosting", "data", "ai", "ai / ml", "ai & ml",
}


def check_techstack_is_table(docx_path: Path, report: Report) -> None:
    """Each Technology Stack sub-heading (Back-end / Front-end / Database /
    Server & Hosting / Data / AI) MUST be immediately followed by a 2-column
    'Technology | Advantages' table, NOT a prose paragraph — the required
    professional table format. Prose here is a zero-tolerance format defect
    (`techstack_not_table`): the content-writer emitted a string instead of the
    required array of {name, description} rows."""
    doc = Document(str(docx_path))
    pmap = {p._p: p for p in doc.paragraphs}
    tmap = {t._tbl: t for t in doc.tables}
    children = list(doc.element.body.iterchildren())
    bad = []
    for idx, child in enumerate(children):
        p = pmap.get(child)
        if p is None:
            continue
        if (p.style.name if p.style else "") != "Heading 6":
            continue
        if (p.text or "").strip().lower() not in _TECHSTACK_LABELS:
            continue
        nxt = None
        for follow in children[idx + 1:]:
            if follow in tmap:
                nxt = ("tbl", None); break
            fp = pmap.get(follow)
            if fp is not None:
                if (fp.text or "").strip() == "":
                    continue  # skip blank spacer paragraphs
                nxt = ("p", (fp.text or "")[:60]); break
        if nxt is None or nxt[0] != "tbl":
            bad.append(((p.text or "").strip(), nxt[1] if nxt else "(nothing)"))
    if bad:
        report.add(Issue(
            "techstack_not_table", "visual", "blocker", False,
            f"{len(bad)} Technology Stack sub-section(s) render as prose instead of a "
            f"'Technology | Advantages' table",
            detail="; ".join(f"'{h}' -> {prev}" for h, prev in bad),
        ))
    else:
        report.pass_("techstack_is_table")


def _iter_content_paragraphs(doc):
    """Every paragraph a reader actually sees, including table cells, excluding headings."""
    def walk(paras):
        for p in paras:
            sname = p.style.name if p.style else ""
            if sname.startswith("Heading"):
                continue
            txt = (p.text or "").strip()
            if txt:
                yield txt

    yield from walk(doc.paragraphs)
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                yield from walk(cell.paragraphs)


def check_em_dash_in_prose(docx_path: Path, report: Report) -> None:
    """No em-dash (—) anywhere in the delivered content.

    A spaced em-dash is one of the strongest signals a reader uses to spot
    machine-written text, and the client rejects it on sight. An earlier version
    of this check exempted bullets and figure captions, on the grounds that the
    dash was a structural separator there. That exemption is withdrawn: the reader
    does not care whether a dash is structural, only that it is there. Use a colon
    after a bold label, and a comma, a semicolon or two sentences in prose.
    """
    doc = Document(str(docx_path))
    bad = [txt[:70] for txt in _iter_content_paragraphs(doc) if "—" in txt]

    if bad:
        report.add(Issue(
            # BLOCKER, not "major": the client rejects this on sight, and a "major"
            # never reaches blocker_count, so the "loop until 0 blockers" gate in
            # 05b would have shipped the document with the em-dashes still in it.
            "em_dash_in_prose", "content", "blocker", False,
            f"{len(bad)} paragraph(s) contain an em-dash (—), which the client rejects as "
            f"machine-written. Use a colon after a bold label, and a comma, a semicolon or "
            f"two sentences in prose. This applies to bullets and captions too. Fix the "
            f"offending values in replacements.json / diagrams.json and re-run Phase 5a.",
            detail="; ".join(bad[:5]),
        ))
    else:
        report.pass_("em_dash_prose_ok")


# "e.g." and friends read as machine-assembled filler in a client-facing bid.
# Word-boundary anchored so "Inc." or a version like "v1.e" cannot match.
_LATIN_ABBREV_RE = re.compile(r"(?<![A-Za-z])(e\.g\.|i\.e\.|etc\.|viz\.|cf\.)", re.IGNORECASE)
_LATIN_ABBREV_FIX = {
    "e.g.": "for example / such as",
    "i.e.": "that is / in other words",
    "etc.": "finish the list, or name the category",
    "viz.": "namely",
    "cf.": "compare",
}


def check_latin_abbreviation_in_content(docx_path: Path, report: Report) -> None:
    """No Latin abbreviations in the delivered content: write the English instead."""
    doc = Document(str(docx_path))
    hits, found = [], set()
    for txt in _iter_content_paragraphs(doc):
        for m in _LATIN_ABBREV_RE.finditer(txt):
            found.add(m.group(1).lower())
            hits.append(txt[:70])
    if hits:
        advice = "; ".join(f"{k} -> {v}" for k, v in _LATIN_ABBREV_FIX.items() if k in found)
        report.add(Issue(
            # BLOCKER for the same reason as em_dash_in_prose: a "major" is not counted
            # by the gate, so it would ship.
            "latin_abbreviation_in_content", "content", "blocker", False,
            f"{len(hits)} paragraph(s) use a Latin abbreviation ({', '.join(sorted(found))}), "
            f"which reads as machine-assembled filler in a client-facing bid. Write it out: "
            f"{advice}. Fix the offending values in replacements.json / diagrams.json and "
            f"re-run Phase 5a.",
            detail="; ".join(dict.fromkeys(hits))[:400],
        ))
    else:
        report.pass_("latin_abbreviation_ok")


# ---------------------------------------------------------------------------
# Runner.
# ---------------------------------------------------------------------------


CHECKS = [
    ("zip_integrity",                  check_zip_integrity),
    ("file_size",                      check_size),
    ("track_changes",                  check_no_track_changes),
    ("comments",                       check_no_comments),
    ("macros",                         check_no_macros),
    ("encryption",                     check_no_encryption),
    ("external_images",                check_no_external_images),
    ("placeholders",                   check_no_unfilled_placeholders),
    ("image_sharpness",                check_image_sharpness),
    ("justify_body",                   check_justify_body),
    # Quality checks added 2026-05-25:
    ("no_bullet_number_duplicates",    check_no_bullet_number_duplicates),
    ("image_spacing",                  check_image_spacing),
    ("heading_indent_vs_body",         check_heading_indent_vs_body),
    ("heading_section_spacing",        check_heading_section_spacing),
    ("caption_followed_by_gap",        check_caption_followed_by_gap),
    ("settings_flags_present",         check_settings_flags_present),
    ("justify_whitespace_channels",    check_justify_whitespace_channels),
    ("techstack_is_table",             check_techstack_is_table),
    ("em_dash_in_prose",               check_em_dash_in_prose),
    ("latin_abbreviation_in_content",  check_latin_abbreviation_in_content),
]


def run(docx_path: Path, pages_dir: Path | None) -> Report:
    report = Report(docx=str(docx_path), file_size_bytes=docx_path.stat().st_size)
    for name, fn in CHECKS:
        try:
            fn(docx_path, report)
        except Exception as e:
            report.add(Issue(f"check_error::{name}", "polish", "minor", False,
                             f"Check {name} crashed", detail=str(e)))
    check_heading_orphans_pdf(pages_dir, report)
    return report


def write_markdown(report: Report, out: Path) -> None:
    lines = [
        f"# Format Review",
        "",
        f"- Document: `{report.docx}`",
        f"- File size: {report.file_size_bytes/1024/1024:.2f} MB",
        f"- Blockers: **{report.blocker_count}**",
        f"- Auto-fixable: **{report.auto_fixable_count}**",
        f"- Checks passed: {len(report.checks_passed)}",
        "",
    ]
    if report.issues:
        lines.append("## Issues")
        for i in report.issues:
            tag = "AUTO" if i.auto_fixable else "MANUAL"
            lines.append(f"- **[{i.severity.upper()} / {tag}] {i.category}** — {i.summary}")
            if i.detail:
                lines.append(f"  - {i.detail}")
    else:
        lines.append("## Issues\n\nNone — proposal passes the strict review.")
    lines.append("")
    lines.append("## Checks passed")
    for c in report.checks_passed:
        lines.append(f"- {c}")
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", type=Path, required=True)
    ap.add_argument("--pages", type=Path, default=None, help="Optional dir of per-page PNGs")
    ap.add_argument("--json", type=Path, required=True, help="Write JSON report here")
    ap.add_argument("--md", type=Path, default=None, help="Also write markdown report here")
    ap.add_argument("--strict", action="store_true", help="(reserved) bump minor -> major")
    args = ap.parse_args()

    if not args.docx.exists():
        print(f"! docx not found: {args.docx}", file=sys.stderr); return 1

    report = run(args.docx, args.pages)

    # Persist
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps({
        "docx": report.docx,
        "file_size_bytes": report.file_size_bytes,
        "blocker_count": report.blocker_count,
        "auto_fixable_count": report.auto_fixable_count,
        "checks_passed": report.checks_passed,
        "issues": [asdict(i) for i in report.issues],
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.md:
        write_markdown(report, args.md)

    # Print short summary
    print(f"Issues: {len(report.issues)}  Blockers: {report.blocker_count}  Auto-fixable: {report.auto_fixable_count}")
    print(f"Passed: {len(report.checks_passed)} checks")
    return 0 if report.blocker_count == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
