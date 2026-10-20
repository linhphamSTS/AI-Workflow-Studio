# -*- coding: utf-8 -*-
"""Repairs that only the DELIVERED file can take, run after build_docx and before auto_fix.

Three defects every run used to repair by hand in its own specs/ folder:

1. The CASE STUDY sentence. The template ships `...comparable to {{CASE_STUDY_TITLE}}.this link`
   and build_docx flattens the HYPERLINK field, so the link is dead text glued to the title.
   The sentence is rewritten in the proposal language and "this link" / "liên kết này" is bound
   to a real relationship-backed w:hyperlink on `case_study_url`.
2. Prose paragraph spacing. A multi-paragraph value clones the template paragraph that held its
   placeholder, and some slots carry no space_after, so a whole section renders with no gap
   between paragraphs. Body paragraphs with none get the document's dominant value.
3. Template tables. build_docx hardens the tables it generates, not the ones the template ships
   (branch model, environments, testing scope), and a split row left "smoke testing." alone at
   the top of a page. cantSplit only where the longest row is short (a 350-character process
   row held whole leaves half-empty pages), and on every real table the header row repeats and
   is kept with the first data row.

Not idempotent against a rebuild: re-running build_docx reinstates all three, so finalize.py
runs this straight after it.

Usage: python post_assembly.py --docx <proposal.docx> --replacements <replacements.json> --language en|vi
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt

HYPERLINK = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
CASE_LEAD = "We are pleased to present a relevant case study"
SENTENCE = {
    "en": ("We are pleased to present a relevant case study that demonstrates our ability to "
           "deliver a high-performance, multi-stakeholder platform comparable to {title}. "
           "The full case study is available at ", "this link"),
    "vi": ("Chúng tôi xin giới thiệu một case study thể hiện năng lực xây dựng nền tảng hiệu năng "
           "cao, nhiều bên tham gia, tương đồng với {title}. Toàn bộ case study xem tại ",
           "liên kết này"),
}
SHORT_ROW = 300   # characters; longer rows may split, or they leave half-empty pages


def fix_case_study(d, url, lang):
    done = ("The full case study is available at", "Toàn bộ case study xem tại")
    if any(any(x in p.text for x in done) for p in d.paragraphs):
        print("[1] case study sentence already repaired")
        return
    for p in d.paragraphs:
        if CASE_LEAD not in p.text:
            continue
        m = re.search(r"comparable to (.+?)\.?this link", p.text)
        title = m.group(1).strip().rstrip(".") if m else ("this project" if lang == "en" else "dự án này")
        if lang == "vi" and title:
            title = title[0].lower() + title[1:]
        lead, anchor = SENTENCE[lang]
        runs = p.runs
        runs[0].text = lead.format(title=title)
        for r in runs[1:]:
            r.text = ""
        r_id = d.part.relate_to(url, HYPERLINK, is_external=True)
        hl = p._p.makeelement(qn("w:hyperlink"), {qn("r:id"): r_id})
        run = p._p.makeelement(qn("w:r"), {})
        rpr = p._p.makeelement(qn("w:rPr"), {})
        for tag, attrs in (("w:color", {qn("w:val"): "0563C1"}), ("w:u", {qn("w:val"): "single"})):
            rpr.append(p._p.makeelement(qn(tag), attrs))
        run.append(rpr)
        t = p._p.makeelement(qn("w:t"), {})
        t.text = anchor
        run.append(t)
        hl.append(run)
        p._p.append(hl)
        run2 = p._p.makeelement(qn("w:r"), {})
        t2 = p._p.makeelement(qn("w:t"), {})
        t2.text = "."
        run2.append(t2)
        p._p.append(run2)
        print("[1] case study sentence rewritten (%s), hyperlink bound -> %s" % (lang, url))
        return
    # Guard on the artefact, not on a phrase: a missing sentence must be loud. A proposal with
    # the case-study section switched off has no such paragraph and no heading either.
    if any(p.text.strip() == "CASE STUDY" for p in d.paragraphs):
        sys.exit("[1] CASE STUDY heading present but its sentence was not found: check by hand")
    print("[1] no CASE STUDY section, nothing to repair")


def fix_prose_spacing(d):
    vals = Counter(p.paragraph_format.space_after for p in d.paragraphs
                   if p.style.name == "Normal" and p.text.strip())
    dominant = next((v for v, _ in vals.most_common() if v is not None), Pt(6))
    in_body, stamped = False, 0
    for p in d.paragraphs:
        if p.style.name.startswith("Heading") and p.text.strip() == "INTRODUCTION":
            in_body = True   # the cover is template art and is left alone
        if in_body and p.style.name == "Normal" and p.text.strip() \
                and p.paragraph_format.space_after is None:
            p.paragraph_format.space_after = dominant
            stamped += 1
    print("[2] stamped space_after=%s on %d body paragraph(s)" % (dominant, stamped))


def fix_template_table_rows(d):
    n = 0
    for tb in d.tables:
        if len(tb.rows) < 2:
            continue  # figure captions are one-row tables
        if max(len(r._tr.xpath("string(.)")) for r in tb.rows) <= SHORT_ROW:
            for row in tb.rows:
                trpr = row._tr.get_or_add_trPr()
                if trpr.find(qn("w:cantSplit")) is None:
                    trpr.append(trpr.makeelement(qn("w:cantSplit"), {}))
                    n += 1
        head = tb.rows[0]
        for p in head._tr.iter(qn("w:p")):
            ppr = p.find(qn("w:pPr"))
            if ppr is None:
                ppr = p.makeelement(qn("w:pPr"), {})
                p.insert(0, ppr)
            if ppr.find(qn("w:keepNext")) is None:
                kn = ppr.makeelement(qn("w:keepNext"), {})
                style = ppr.find(qn("w:pStyle"))
                if style is not None:
                    style.addnext(kn)
                else:
                    ppr.insert(0, kn)
        trpr = head._tr.get_or_add_trPr()
        if trpr.find(qn("w:tblHeader")) is None:
            trpr.append(trpr.makeelement(qn("w:tblHeader"), {}))
    print("[3] cantSplit set on %d table row(s); header rows repeat and stay with the next row" % n)


def fix_cover_duplicates(d):
    """The template types "Project Coordinator" twice in the ISSUED FROM cell of the cover.
    Only the Vietnamese pass used to remove it, so every English proposal shipped the slip."""
    n = 0
    if not d.tables:
        return
    for row in d.tables[0].rows:
        for cell in row.cells:
            seen = set()
            for p in list(cell.paragraphs):
                t = p.text.strip()
                if t in ("Project Sponsor", "Project Coordinator"):
                    if t in seen:
                        p._p.getparent().remove(p._p)
                        n += 1
                    seen.add(t)
    print("[5] duplicate role lines removed from the cover: %d" % n)


def fix_cover_title(d, client):
    """The cover line `for <title> - <client>` wrapped with the hyphen at the start of the second
    line, or with the client's last word alone. Bind the client name with non-breaking spaces,
    glue the hyphen to the title, and centre the line like the title above it."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    if not client:
        return
    nb = client.replace(" ", " ")
    n = 0
    for p in d.paragraphs[:40]:
        t = p.text
        if not t.strip().startswith(("for ", "cho ")) or not t.rstrip().endswith(client):
            continue
        new = re.sub(r"\s+-\s+" + re.escape(client) + r"\s*$", " - " + nb, t)
        runs = [r for r in p.runs if r.text]
        if runs and new != t:
            runs[0].text = new
            for r in runs[1:]:
                r.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            n += 1
    print("[6] cover title line bound and centred: %d" % n)


def fix_page_header(d):
    """The header cell holds about 42 characters per line; a longer "for <title> - <client>"
    wraps onto a third line on every page. Drop any parenthetical gloss from the HEADER copy
    (the cover keeps the full title). format_reviewer reports it if it is still too long."""
    n = 0
    for sec in d.sections:
        for part in (sec.header, sec.first_page_header):
            for tb in part.tables:
                for row in tb.rows:
                    for cell in row.cells:
                        for p in cell.paragraphs:
                            if not p.text.strip().startswith(("for ", "cho ")) or len(p.text.strip()) <= 42:
                                continue
                            # Drop a parenthetical gloss first; if still too long, drop the
                            # trailing " - <client>" (the project name already carries it).
                            new = re.sub(r"\s*\([^)]*\)", "", p.text)
                            if len(new.strip()) > 42 and " - " in new:
                                new = new.rsplit(" - ", 1)[0]
                            runs = [r for r in p.runs if r.text]
                            if runs and new != p.text:
                                runs[0].text = new
                                for r in runs[1:]:
                                    r.text = ""
                                n += 1
    print("[4] page header shortened in %d run(s)" % n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", required=True)
    ap.add_argument("--replacements", required=True)
    ap.add_argument("--language", choices=("en", "vi"), required=True)
    a = ap.parse_args()
    repl = json.loads(Path(a.replacements).read_text(encoding="utf-8"))
    d = Document(a.docx)
    fix_case_study(d, repl.get("case_study_url") or "https://saigontechnology.com/case-studies/",
                   a.language)
    fix_prose_spacing(d)
    fix_template_table_rows(d)
    fix_page_header(d)
    fix_cover_duplicates(d)
    fix_cover_title(d, (repl.get("client_name") or "").strip())
    d.save(a.docx)
    print("saved:", a.docx)


if __name__ == "__main__":
    main()
