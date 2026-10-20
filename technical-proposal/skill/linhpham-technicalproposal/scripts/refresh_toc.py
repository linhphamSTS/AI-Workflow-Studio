# -*- coding: utf-8 -*-
"""Rebuild the proposal's cached table of contents, without paying Word's picture tax.

Why it is needed: the TOC is a field whose CACHED result is what SharePoint and every preview
pane render. The template ships a cache from another bid (English titles, sections this proposal
does not have, page numbers "?"), so the contents page is wrong until Word recomputes it.

Why it is delicate, and this is a defect this project has already paid for once: a Word COM
open-and-SAVE re-encodes every embedded picture at Word's default compression and strips
settings flags. Updating the TOC requires a save, so the two are in direct conflict.

The sequence here removes the conflict rather than repairing after it:
  1. inject <w:doNotAutoCompressPictures/> into settings.xml BEFORE Word ever opens the file,
     so the save has nothing to compress;
  2. snapshot every media part;
  3. Word COM: update the TOC and all fields, save, close;
  4. compare the MULTISET of image dimensions (Word renumbers media parts, so a name-by-name
     comparison reports false differences and "repairing" them corrupts the document);
  5. verify the TOC actually grew and that no figure lost pixels.

Needed for EVERY proposal, whatever its language: the stale cache ships in the template.
Windows only (Word COM, pywin32). Run after translate_vi.py when the proposal is Vietnamese.

Run: python refresh_toc.py --docx <proposal.docx>
     A byte-identical backup is kept next to it as <name>.docx.pretoc.
"""
import argparse
import io
import pathlib
import shutil
import sys
import zipfile

from PIL import Image

_ap = argparse.ArgumentParser()
_ap.add_argument("--docx", required=True)
DOCX = pathlib.Path(_ap.parse_args().docx).resolve()
BAK = DOCX.with_suffix(".docx.pretoc")

SETTINGS = "word/settings.xml"
FLAG = "<w:doNotAutoCompressPictures/>"


def read_parts(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


def write_parts(path, parts, order):
    tmp = path.with_suffix(".docx.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for n in order:
            z.writestr(n, parts[n])
    tmp.replace(path)


def media_dims(parts):
    """Dimensions of the pictures the document actually DISPLAYS, one entry per use.

    Counting every part under word/media is wrong for this template: build_docx leaves about 35
    orphan parts behind (logos and art of removed sections, still related but never drawn), and
    Word drops them on save, which a part count reads as 35 lost images."""
    import re as _re
    out = {}
    for n, b in parts.items():
        if not (n.startswith("word/") and n.endswith(".xml")) or "/_rels/" in n:
            continue
        rels_name = "word/_rels/" + n[len("word/"):] + ".rels"
        if rels_name not in parts:
            continue
        rels = parts[rels_name].decode("utf-8")
        target = {}
        for tag in _re.findall(r"<Relationship\b[^>]*>", rels):
            i, t = _re.search(r'Id="([^"]+)"', tag), _re.search(r'Target="([^"]+)"', tag)
            if i and t and "media/" in t.group(1):
                target[i.group(1)] = "word/" + t.group(1).replace("../", "")
        xml = b.decode("utf-8", "ignore")
        for k, rid in enumerate(_re.findall(r'r:(?:embed|id)="([^"]+)"', xml)):
            part = target.get(rid)
            if part in parts:
                try:
                    out["%s#%d" % (n, k)] = Image.open(io.BytesIO(parts[part])).size
                except Exception:
                    out["%s#%d" % (n, k)] = None
    return out


def toc_entries(path):
    """Count cached TOC entries. They live inside a structured-document-tag block, which is why
    doc.paragraphs does not see them; count the PAGEREF fields instead."""
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8").count("PAGEREF")


def keep_cover_out_of_toc():
    r"""The template styles the cover title and 'Mục lục' as Heading 1 and the two party names
    in the cover table as Heading 6, so the TOC field (\\t "Heading 1,1,...") lists them as
    entries on page 0 and 1. Move each onto a standalone copy of that heading style: identical
    look, no outline level, so neither \t nor \u picks it up."""
    from docx import Document
    from docx.oxml.ns import qn
    d = Document(str(DOCX))

    def derived(name, base):
        r"""A standalone copy of the heading style. A style BASED ON a built-in heading does not
        work: Word locks its outline level to the heading's, so the TOC's \u switch still pulls
        the paragraph in. Copy the heading's own formatting instead and drop its outline level."""
        import copy
        styles = d.styles.element
        for el in styles.findall(qn("w:style")):
            nm = el.find(qn("w:name"))
            if nm is not None and nm.get(qn("w:val")) == name:
                styles.remove(el)
        el = copy.deepcopy(d.styles[base].element)
        el.set(qn("w:styleId"), name.replace(" ", ""))
        el.set(qn("w:customStyle"), "1")
        for attr in (qn("w:default"),):
            el.attrib.pop(attr, None)
        el.find(qn("w:name")).set(qn("w:val"), name)
        for tag in ("w:link", "w:aliases"):
            for x in el.findall(qn(tag)):
                el.remove(x)
        ppr = el.find(qn("w:pPr"))
        if ppr is not None:
            for tag in ("w:outlineLvl", "w:numPr"):
                for x in ppr.findall(qn(tag)):
                    ppr.remove(x)
        styles.append(el)
        return d.styles[name]

    # collect first: re-creating a style mid-loop would orphan the paragraphs that still point
    # at the old copy, and they would then read back as Normal and be skipped
    titles = [p for p in d.paragraphs[:8]
              if p.style.name in ("Heading 1", "Cover Heading 1") and p.text.strip()]
    parties = [p for row in d.tables[0].rows for cell in row.cells for p in cell.paragraphs
               if p.style.name in ("Heading 6", "Cover Heading 6")]
    h1, h6 = derived("Cover Heading 1", "Heading 1"), derived("Cover Heading 6", "Heading 6")
    for p in titles:
        p.style = h1
    for p in parties:
        p.style = h6
    moved = len(titles) + len(parties)
    d.save(str(DOCX))
    print("  cover paragraphs moved off the TOC styles: %d" % moved)


def main():
    if not DOCX.exists():
        sys.exit("proposal not found: %s" % DOCX)
    shutil.copy2(DOCX, BAK)
    keep_cover_out_of_toc()

    before_entries = toc_entries(DOCX)
    parts = read_parts(DOCX)
    order = list(parts.keys())
    before_media = media_dims(parts)

    # 1. stop Word compressing on save, before it is ever opened
    s = parts[SETTINGS].decode("utf-8")
    if FLAG not in s:
        i = s.rfind("</w:settings>")
        if i < 0:
            sys.exit("settings.xml has no </w:settings>")
        parts[SETTINGS] = (s[:i] + FLAG + s[i:]).encode("utf-8")
        write_parts(DOCX, parts, order)
        print("  injected doNotAutoCompressPictures")
    else:
        print("  doNotAutoCompressPictures already set")

    # 2-3. update the fields
    import win32com.client as win32
    word = win32.Dispatch("Word.Application")
    word.Visible = False
    doc = word.Documents.Open(str(DOCX), ReadOnly=False, AddToRecentFiles=False)
    try:
        # 38 entries at Normal's inherited 1.15 line spacing run onto a second page. Set the
        # built-in TOC 1-6 styles to single spacing through Word itself (wdStyleTOC1 = -20 ...
        # TOC6 = -25), which keeps Word's own per-level indents. Space after stays 0: the template
        # has none, and adding even 2 pt made the overflow worse.
        for lvl in range(6):
            pf = doc.Styles(-20 - lvl).ParagraphFormat
            pf.SpaceBefore = 0
            pf.SpaceAfter = 0
            pf.LineSpacingRule = 0  # wdLineSpaceSingle
        for toc in doc.TablesOfContents:
            toc.Update()
        doc.Fields.Update()

        # One page. A proposal with the optional sections on has about 50 entries, which ran
        # onto a second contents page at the template's size. Measure the pages the contents
        # occupy (wdActiveEndPageNumber = 3) and step the TOC 1-6 type down until it fits,
        # never below 8.5pt; the structure (every heading level) stays as it is.
        def toc_pages():
            if doc.TablesOfContents.Count == 0:
                return 1
            r = doc.TablesOfContents(1).Range
            first = doc.Range(r.Start, r.Start).Information(3)
            last = doc.Range(max(r.Start, r.End - 1), max(r.Start, r.End - 1)).Information(3)
            return last - first + 1

        pages = toc_pages()
        for size in (10, 9.5, 9, 8.5):
            if pages <= 1:
                break
            for lvl in range(6):
                doc.Styles(-20 - lvl).Font.Size = size
            for toc in doc.TablesOfContents:
                toc.Update()
            pages = toc_pages()
            print("  contents on %d page(s) at %.1fpt" % (pages, size))
        if pages > 1:
            print("  ! contents still runs onto %d pages at 8.5pt" % pages)
        doc.Fields.Update()
        doc.Save()
    finally:
        doc.Close(SaveChanges=0)
        try:
            word.Quit()
        except Exception:
            pass
    print("  Word updated the TOC and all fields")

    # 4. verify, WITHOUT restoring by name.
    #
    # Word RENUMBERS media parts when it rewrites the package: after the save, image31.png can
    # hold what used to be image32.png, and Word has already re-pointed the relationships to
    # match, so the document is correct. Comparing bytes part-by-part NAME therefore reports a
    # difference for almost every figure, and "restoring" them writes the wrong picture into
    # each slot and breaks the document. The first version of this script did exactly that.
    #
    # The question that actually matters is whether any RESOLUTION was lost, and that is a
    # question about the multiset of image dimensions, not about any individual name.
    from collections import Counter
    after = read_parts(DOCX)
    after_media = media_dims(after)

    # 4a. Word's save also STRIPS settings flags. Re-add every flag that was there before and
    # is not there now, rather than naming a fixed list: the list is whatever this template
    # was built with, and hardcoding it here would go stale the moment the template changes.
    s_before = parts[SETTINGS].decode("utf-8")
    s_after = after[SETTINGS].decode("utf-8")
    import re as _re
    flags_before = set(_re.findall(r"<w:(doNot\w+|updateFields)\b", s_before))
    flags_after = set(_re.findall(r"<w:(doNot\w+|updateFields)\b", s_after))
    missing = sorted(flags_before - flags_after)
    if missing:
        j = s_after.rfind("</w:settings>")
        add = "".join("<w:%s/>" % f for f in missing)
        after[SETTINGS] = (s_after[:j] + add + s_after[j:]).encode("utf-8")
        write_parts(DOCX, after, list(after.keys()))
        after = read_parts(DOCX)
        after_media = media_dims(after)
        print("  restored settings flags stripped by the save: %s" % ", ".join(missing))
    was = Counter(d for d in before_media.values() if d)
    now = Counter(d for d in after_media.values() if d)
    lost = was - now
    after_entries = toc_entries(DOCX)
    print("  TOC entries: %d -> %d" % (before_entries, after_entries))
    print("  displayed pictures: %d -> %d" % (len(before_media), len(after_media)))
    if lost:
        # Only now is a repair warranted, and it must be done by matching dimensions, not names.
        sys.exit("Word re-encoded %d image(s): %s | "
                 "Restore from %s and investigate; do NOT restore by part name."
                 % (sum(lost.values()), sorted(lost), BAK.name))
    assert after_entries > 0, "TOC is empty"
    # Every contents entry must name a heading this document really has; anything else is the
    # template's cached entry from another bid surviving the update.
    # Word puts the updated contents inside a content control (w:sdt), which python-docx's
    # doc.paragraphs never yields, so walk every w:p in the body. Reading doc.paragraphs here
    # found zero entries and passed without checking anything.
    from docx import Document
    from docx.oxml.ns import qn
    d = Document(str(DOCX))
    styles = {s.style_id: (s.name or "") for s in d.styles}

    def all_paras():
        for p in d.element.body.iter(qn("w:p")):
            ps = p.find(qn("w:pPr") + "/" + qn("w:pStyle"))
            name = styles.get(ps.get(qn("w:val")), "") if ps is not None else ""
            # The page number sits after a <w:tab/> run element, not a "\t" in the text;
            # tab STOPS in pPr are formatting and are skipped by reading runs only.
            text = "".join("\t" if el.tag == qn("w:tab") else (el.text or "")
                           for r in p.iter(qn("w:r")) for el in r
                           if el.tag in (qn("w:t"), qn("w:tab")))
            yield name, text

    number = lambda s: _re.sub(r"^\d+(\.\d+)*\.?\s*", "", s.strip())
    paras = list(all_paras())
    headings = {number(t) for n, t in paras if n.startswith("Heading") and t.strip()}
    # The page number follows a tab; never strip trailing digits from the title itself
    # ("... under Decree 13" is a heading, not "... under Decree" on page 13).
    entries = [number(t.split("\t")[0]) for n, t in paras
               if n.lower().startswith("toc") and t.strip()]
    stale = [e for e in entries if e and e not in headings]
    print("  contents entries read back: %d" % len(entries))
    assert entries, "no contents entry could be read back"
    if stale:
        sys.exit("contents entries that match no heading (stale cache?): %s" % stale[:6])
    assert FLAG in after[SETTINGS].decode("utf-8"), "compression flag was stripped by the save"
    print("OK  TOC refreshed, every figure kept its resolution")


if __name__ == "__main__":
    main()
