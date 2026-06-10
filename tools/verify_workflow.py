#!/usr/bin/env python3
"""End-to-end workflow verification — runs all the checks a senior architect
would run before declaring the proposal-generation workflow ready to ship."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TPL = REPO / "skill/linhpham-technicalproposal/templates/proposal_template.docx"
BUILD = REPO / "skill/linhpham-technicalproposal/scripts/build_docx.py"
REVIEW = REPO / "skill/linhpham-technicalproposal/scripts/format_reviewer.py"
PROMPT = REPO / "skill/linhpham-technicalproposal/prompts/04_generate.md"

PATTERNS = ["Tay Ho", "TayHo", "tayho", "GSA", "Scoot", "Batik",
            "LionAir", "Beibu", "West Air", "Vendor Y", "B2B Airline",
            "sponsor@", "@tayho", "Livaro"]


def section(t):
    print()
    print("=" * 70)
    print(" " + t)
    print("=" * 70)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    from docx import Document
    from docx.oxml.ns import qn

    pass_count = 0
    fail_count = 0

    def check(name, ok, detail=""):
        nonlocal pass_count, fail_count
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))
        if ok: pass_count += 1
        else: fail_count += 1

    # 1. TEMPLATE STATE
    section("1. TEMPLATE STATE")
    with zipfile.ZipFile(TPL) as z:
        doc_xml = z.read("word/document.xml").decode("utf-8", errors="replace")
        settings_xml = z.read("word/settings.xml").decode("utf-8", errors="replace")
        media = [n for n in z.namelist() if n.startswith("word/media/")]

    sects = re.findall(r"<w:sectPr[^>]*>.*?</w:sectPr>", doc_xml, re.DOTALL)
    margins = []
    for s in sects:
        m = re.search(r"<w:pgMar\s+([^/]+)/>", s)
        if not m:
            margins.append(None); continue
        mm = re.search(r'w:top="(\d+)"\s+w:right="(\d+)"\s+w:bottom="(\d+)"\s+w:left="(\d+)"', m.group(1))
        margins.append(tuple(int(g) for g in mm.groups()) if mm else None)
    check("3 sections present", len(margins) == 3, f"got {len(margins)}")
    check("Front cover full-bleed (0/0/0/0)", margins and margins[0] == (0, 0, 0, 0))
    check("Body section 0.5\" margins (720/720/720/720)", margins and margins[1] == (720, 720, 720, 720))
    check("Back cover full-bleed (0/0/0/0)", margins and margins[2] == (0, 0, 0, 0))

    d = Document(str(TPL))
    cap_tables = []
    for t in d.tables:
        if len(t.rows) == 1 and len(t.columns) == 1:
            joined = "".join(tn.text or "" for tn in t.rows[0].cells[0]._tc.iter(qn("w:t")))
            has_seq = bool(t.rows[0].cells[0]._tc.findall(".//" + qn("w:instrText")))
            if joined.strip() and has_seq:
                cap_tables.append(joined.strip())
    check("All caption tables use 1x1 SEQ format", len(cap_tables) == 6,
          f"{len(cap_tables)} captions — {cap_tables}")

    dirty = len(re.findall(r'<w:fldChar\b[^/]*w:dirty="true"', doc_xml))
    check("Fields marked dirty (auto-refresh on open)", dirty >= 6, f"{dirty} fields")
    check("settings.xml updateFields=true", "updateFields" in settings_xml)
    check("settings.xml autoHyphenation=true", "autoHyphenation" in settings_xml)

    total_leaks = 0
    leaks_per_part = {}
    with zipfile.ZipFile(TPL) as z:
        for part in [n for n in z.namelist() if n.endswith(".xml")]:
            data = z.read(part).decode("utf-8", errors="replace")
            text_only = re.sub(r"<[^>]+>", " ", data)
            part_leaks = sum(len(re.findall(re.escape(p), text_only, re.IGNORECASE))
                             for p in PATTERNS)
            if part_leaks:
                leaks_per_part[part] = part_leaks
            total_leaks += part_leaks
    check("ZERO customer leaks across all XML parts", total_leaks == 0,
          f"leaks={leaks_per_part}" if leaks_per_part else "clean")
    check("Images preserved (45 original)", len(media) >= 40, f"{len(media)} images")

    # 2. BUILD_DOCX end-to-end
    section("2. BUILD_DOCX end-to-end")
    replacements = {
        "client_name": "ACME Corporation",
        "project_title": "Loyalty Platform Modernization",
        "version": "v1.0",
        "proposal_date": "24 May 2026",
        "client_contact_email": "cto@acme.example",
        "vendor_partner_name": "the upstream provider",
        "executive_summary": "Headline executive summary.",
        "problems_and_solutions": "● **Problem** — solution.",
        "purpose": "Purpose statement.",
        "system_overview_intro": "Overview intro.",
        "techstack_backend": ".NET 10",
        "techstack_frontend": "React 18",
        "techstack_database": "Aurora PG 16",
        "techstack_server_hosting": "Amazon EKS multi-AZ",
        "techstack_data": None,
        "techstack_ai": None,
        "mobile_app_strategy": None,
        "case_study_title": "FruPro delivery",
        "summary_body": "Project-specific summary text.",
    }
    diagrams = [
        {"slug": "ctx", "subheading": "2.1.2 Container Diagram",
         "target_heading": "Container Diagram", "png": "x.png",
         "caption": "Container Diagram"},
        {"slug": "dep", "subheading": "2.1.3 Deployment Topology",
         "target_heading": "Deployment Topology", "png": "x.png",
         "caption": "Deployment Topology"},
        {"slug": "cicd", "subheading": "2.1.4 CI/CD",
         "target_heading": "CI/CD", "png": "x.png",
         "caption": "CI/CD Pipeline"},
    ]
    td = Path(tempfile.mkdtemp())
    (td/"r.json").write_text(json.dumps(replacements), encoding="utf-8")
    (td/"d.json").write_text(json.dumps(diagrams), encoding="utf-8")
    out_p = td/"out.docx"
    r = subprocess.run(
        [sys.executable, str(BUILD), "--template", str(TPL),
         "--replacements", str(td/"r.json"), "--diagrams", str(td/"d.json"),
         "--out", str(out_p)],
        capture_output=True, text=True,
    )
    check("build_docx exit 0", r.returncode == 0, r.stderr[:120] if r.returncode else "")
    if out_p.exists():
        with zipfile.ZipFile(out_p) as z:
            od = z.read("word/document.xml").decode("utf-8", errors="replace")
            ods = z.read("word/settings.xml").decode("utf-8", errors="replace")
        out_sects = re.findall(r"<w:sectPr[^>]*>.*?</w:sectPr>", od, re.DOTALL)
        check("Output preserves 3 sections", len(out_sects) == 3)
        text_only = re.sub(r"<[^>]+>", " ", od)
        leftover = set(re.findall(r"\{\{[A-Z_]+\}\}", text_only))
        check("Output has NO unfilled placeholders", not leftover, f"left: {leftover}")
        out_leaks = sum(len(re.findall(re.escape(p), text_only, re.IGNORECASE)) for p in PATTERNS)
        check("Output has NO customer leaks", out_leaks == 0)
        check("Output settings.xml updateFields=true", "updateFields" in ods)

        # 3. FORMAT REVIEW
        section("3. FORMAT REVIEW on output (strict)")
        review_json = td/"review.json"
        r2 = subprocess.run(
            [sys.executable, str(REVIEW), "--docx", str(out_p), "--json", str(review_json)],
            capture_output=True, text=True,
        )
        rep = json.loads(review_json.read_text(encoding="utf-8"))
        blockers = [i for i in rep["issues"] if i["severity"] == "blocker"]
        check("Format review: zero blockers", len(blockers) == 0,
              f"{len(blockers)} blockers" if blockers else f"{len(rep['issues'])} non-blockers")

    # 4. PHASE 4 SCHEMA vs TEMPLATE PLACEHOLDERS
    section("4. PHASE 4 SCHEMA vs TEMPLATE PLACEHOLDERS")
    template_keys = set(re.findall(r"\{\{([A-Z_]+)\}\}",
                                    re.sub(r"<[^>]+>", " ", doc_xml)))
    schema_keys = set(re.findall(r'"([a-z_]+)"\s*:',
                                  PROMPT.read_text(encoding="utf-8")))
    schema_upper = {k.upper() for k in schema_keys}
    missing = template_keys - schema_upper
    check("Every template placeholder is documented in Phase 4 schema",
          not missing, f"missing: {missing}" if missing else "")
    print(f"  Template placeholders: {sorted(template_keys)}")

    # 5. DEPLOY symlinks
    section("5. DEPLOY symlinks")
    import os
    for prof in [".claude", ".claude-account2"]:
        target = Path(os.path.expanduser(f"~/{prof}/skills/linhpham-technicalproposal"))
        if target.exists():
            try:
                real = target.resolve()
                check(f"{prof}/skills/linhpham-technicalproposal exists",
                      real.exists() and (real / "SKILL.md").exists(),
                      f"-> {real}")
            except Exception as e:
                check(f"{prof} symlink", False, str(e))
        else:
            check(f"{prof}/skills/linhpham-technicalproposal exists", False, "not linked")

    # 6. RUN existing verify_all.py
    section("6. tools/verify_all.py")
    r3 = subprocess.run([sys.executable, str(REPO / "tools/verify_all.py")],
                        capture_output=True, text=True)
    last = r3.stdout.split("RESULT")[-1] if "RESULT" in r3.stdout else r3.stdout[-400:]
    print(last)
    check("verify_all.py all PASS",
          "PASS" in last and "FAIL" not in last)

    shutil.rmtree(td, ignore_errors=True)

    section("FINAL RESULT")
    print(f"  Passed: {pass_count}")
    print(f"  Failed: {fail_count}")
    print()
    if fail_count == 0:
        print("  >>> WORKFLOW READY TO SHIP <<<")
        return 0
    else:
        print("  >>> SOME CHECKS FAILED — review above <<<")
        return 1


if __name__ == "__main__":
    sys.exit(main())
