#!/usr/bin/env python3
"""Full verification suite: template state + build_docx smoke test + format
review + Python file audit. Run before declaring the workflow ready."""
from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
TEMPLATE = REPO / "skill/linhpham-technicalproposal/templates/proposal_template.docx"
BUILD_DOCX = REPO / "skill/linhpham-technicalproposal/scripts/build_docx.py"
FORMAT_REVIEWER = REPO / "skill/linhpham-technicalproposal/scripts/format_reviewer.py"

CUSTOMER_PATTERNS = [
    "Tay Ho", "TayHo", "tayho", "GSA", "Scoot", "Batik",
    "LionAir", "Lion Air", "Beibu", "West Air", "Vendor Y",
    "B2B Airline", "sponsor@", "@tayho", "Livaro",
]
GHOST_SYMBOLS = [
    "TAYHO_FORBIDDEN", "fix_tayho_leakage", "check_no_tayho_leakage",
    "enable_auto_hyphenation", "proposal_template.config.json",
]


def header(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def section_margins(doc_xml: str) -> list:
    sects = re.findall(r"<w:sectPr[^>]*>.*?</w:sectPr>", doc_xml, re.DOTALL)
    out = []
    for s in sects:
        m = re.search(r"<w:pgMar\s+([^/]+)/>", s)
        if not m:
            out.append(None); continue
        mm = re.search(
            r'w:top="(\d+)"\s+w:right="(\d+)"\s+w:bottom="(\d+)"\s+w:left="(\d+)"',
            m.group(1),
        )
        out.append(tuple(int(g) for g in mm.groups()) if mm else None)
    return out


def count_leaks(text_only: str) -> dict[str, int]:
    return {p: len(re.findall(re.escape(p), text_only, re.IGNORECASE)) for p in CUSTOMER_PATTERNS}


def verify_template() -> bool:
    header("1. TEMPLATE STATE")
    if not TEMPLATE.exists():
        print(f"FAIL: template missing at {TEMPLATE}")
        return False
    with zipfile.ZipFile(TEMPLATE) as z:
        doc_xml = z.read("word/document.xml").decode("utf-8", errors="replace")
        settings_xml = z.read("word/settings.xml").decode("utf-8", errors="replace")
        media = [n for n in z.namelist() if n.startswith("word/media/")]
        all_xml_parts = [n for n in z.namelist() if n.endswith(".xml")]

    margins = section_margins(doc_xml)
    print(f"Sections: {len(margins)} (target 3)")
    for i, m in enumerate(margins):
        print(f"  Sec{i+1} margins: {m}")
    ok_margins = (
        len(margins) == 3
        and margins[0] == (0, 0, 0, 0)
        and margins[1] == (720, 720, 720, 720)
        and margins[2] == (0, 0, 0, 0)
    )
    print(f"Margins layout: {'OK' if ok_margins else 'FAIL'}")
    print(f"Images embedded: {len(media)}")
    print(f"updateFields=true: {'YES' if 'updateFields' in settings_xml else 'NO'}")
    print(f"autoHyphenation=true: {'YES' if 'autoHyphenation' in settings_xml else 'NO'}")
    toc_dirty = len(
        re.findall(
            r'<w:fldChar\b[^/]*w:dirty="true"[^/]*/>(?=.{0,500}?<w:instrText[^>]*>\s*TOC\b)',
            doc_xml, re.DOTALL,
        )
    )
    print(f"TOC dirty fields (force refresh): {toc_dirty}")

    total_leaks = 0
    with zipfile.ZipFile(TEMPLATE) as z:
        for part in all_xml_parts:
            data = z.read(part).decode("utf-8", errors="replace")
            text_only = re.sub(r"<[^>]+>", " ", data)
            part_leaks = sum(count_leaks(text_only).values())
            if part_leaks:
                print(f"  ! leaks in {part}: {part_leaks}")
            total_leaks += part_leaks
    print(f"Total customer leaks across all parts: {total_leaks}")
    return ok_margins and total_leaks == 0 and toc_dirty > 0


def smoke_test() -> bool:
    header("2. SMOKE TEST build_docx")
    replacements = {
        "client_name": "ACME Corp",
        "project_title": "Loyalty Platform Modernization",
        "version": "v1.0",
        "proposal_date": "24 May 2026",
        "client_contact_email": "cto@acme.example",
        "vendor_partner_name": "the upstream provider",
        "executive_summary": "Headline executive summary text.",
        "problems_and_solutions": "● **Problem** — solution.",
        "purpose": "Purpose paragraph for the bid.",
        "system_overview_intro": "High-level system overview intro.",
        "techstack_backend": ".NET 10",
        "techstack_frontend": "React 18 + Vite",
        "techstack_database": "Aurora PostgreSQL 16",
        "techstack_server_hosting": "EKS multi-AZ",
        "techstack_data": None,
        "techstack_ai": None,
        "mobile_app_strategy": None,
        "case_study_title": "FruPro B2B platform delivery",
        "summary_body": "Final summary paragraphs tailored to ACME's loyalty rebuild.",
    }
    diagrams = [
        {"slug": "ctx", "subheading": "2.1.2 Container Diagram",
         "target_heading": "Container Diagram", "png": "x.png"},
        {"slug": "dep", "subheading": "2.1.3 Deployment Topology",
         "target_heading": "Deployment Topology", "png": "x.png"},
        {"slug": "cicd", "subheading": "2.1.4 CI/CD Pipeline",
         "target_heading": "CI/CD Pipeline", "png": "x.png"},
    ]
    td = Path(tempfile.mkdtemp())
    try:
        (td / "r.json").write_text(json.dumps(replacements), encoding="utf-8")
        (td / "d.json").write_text(json.dumps(diagrams), encoding="utf-8")
        out_p = td / "out.docx"
        r = subprocess.run(
            [sys.executable, str(BUILD_DOCX),
             "--template", str(TEMPLATE),
             "--replacements", str(td / "r.json"),
             "--diagrams", str(td / "d.json"),
             "--out", str(out_p)],
            capture_output=True, text=True,
        )
        print(r.stdout)
        if r.returncode != 0:
            print(f"FAIL: build_docx exit {r.returncode}")
            if r.stderr: print(r.stderr)
            return False
        with zipfile.ZipFile(out_p) as z:
            out_doc = z.read("word/document.xml").decode("utf-8", errors="replace")
            out_settings = z.read("word/settings.xml").decode("utf-8", errors="replace")
        margins = section_margins(out_doc)
        print(f"Output sections: {len(margins)}")
        for i, m in enumerate(margins):
            print(f"  Sec{i+1}: {m}")
        text_only = re.sub(r"<[^>]+>", " ", out_doc)
        leftover = set(re.findall(r"\{\{[A-Z_]+\}\}", text_only))
        print(f"Unfilled placeholders: {leftover if leftover else 'NONE'}")
        out_leaks = sum(count_leaks(text_only).values())
        print(f"Customer leaks in output: {out_leaks}")
        print(f"Output updateFields: {'YES' if 'updateFields' in out_settings else 'NO'}")
        ok = (
            len(margins) == 3
            and margins[1] == (720, 720, 720, 720)
            and not leftover
            and out_leaks == 0
            and "updateFields" in out_settings
        )
        return ok, out_p, td
    except Exception:
        shutil.rmtree(td, ignore_errors=True)
        raise


def format_review(out_p: Path, td: Path) -> bool:
    header("3. FORMAT REVIEW on output")
    review_json = td / "review.json"
    r = subprocess.run(
        [sys.executable, str(FORMAT_REVIEWER),
         "--docx", str(out_p), "--json", str(review_json)],
        capture_output=True, text=True,
    )
    print(r.stdout)
    rep = json.loads(review_json.read_text(encoding="utf-8"))
    blockers = [i for i in rep["issues"] if i["severity"] == "blocker"]
    print(f"Blockers: {len(blockers)} | Total issues: {len(rep['issues'])}")
    for i in blockers:
        print(f"  BLOCKER: {i['id']} -- {i['summary']}")
    return not blockers


def python_audit() -> bool:
    header("4. PYTHON AUDIT")
    py_files = sorted(
        p for p in REPO.glob("**/*.py")
        if "__pycache__" not in str(p) and ".git" not in str(p)
    )
    issues = []
    for fp in py_files:
        txt = fp.read_text(encoding="utf-8", errors="replace")
        try:
            ast.parse(txt)
        except SyntaxError as e:
            issues.append(f"SYNTAX {fp.relative_to(REPO)}:{e.lineno} {e.msg}")
        # These tooling files legitimately store the customer patterns and
        # ghost-symbol names as one-shot substitution sources or as audit
        # targets; their file headers document this. Skip them entirely.
        if fp.name in ("finalize_template.py", "verify_all.py", "verify_workflow.py"):
            continue
        for sym in GHOST_SYMBOLS:
            if re.search(r"\b" + re.escape(sym) + r"\b", txt):
                issues.append(f"GHOST {fp.relative_to(REPO)} -- {sym}")
        for pat in CUSTOMER_PATTERNS:
            m = re.search(re.escape(pat), txt, re.IGNORECASE)
            if m:
                ln = txt[: m.start()].count("\n") + 1
                issues.append(f"LEAK {fp.relative_to(REPO)}:{ln} -- {pat}")
    print(f"Files audited: {len(py_files)}")
    print(f"Issues found: {len(issues)}")
    for i in issues[:20]:
        print(f"  {i}")
    return not issues


def main() -> int:
    ok1 = verify_template()
    res2 = smoke_test()
    if isinstance(res2, tuple):
        ok2, out_p, td = res2
    else:
        ok2 = False
        out_p, td = None, None
    ok3 = format_review(out_p, td) if out_p else False
    ok4 = python_audit()
    if td:
        shutil.rmtree(td, ignore_errors=True)

    header("RESULT")
    print(f"  Template state:    {'PASS' if ok1 else 'FAIL'}")
    print(f"  build_docx smoke:  {'PASS' if ok2 else 'FAIL'}")
    print(f"  Format review:     {'PASS' if ok3 else 'FAIL'}")
    print(f"  Python audit:      {'PASS' if ok4 else 'FAIL'}")
    return 0 if (ok1 and ok2 and ok3 and ok4) else 1


if __name__ == "__main__":
    sys.exit(main())
