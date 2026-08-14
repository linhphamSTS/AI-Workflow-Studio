#!/usr/bin/env python3
"""DEVELOPER tool. Re-assemble a proposal from an existing version and run every format
check, in seconds, without a generate.

NOT part of using the skill. Anyone producing a proposal just runs the skill: Phase 5b
already runs `format_reviewer.py` over the assembled file on every single generate, and
`build_docx.py` prevents these defects while assembling, so there is nothing to remember
and nothing extra to run. This script exists for whoever is CHANGING `build_docx.py`,
`format_reviewer.py` or the template, and needs to know in five seconds whether the change
worked, instead of spending thirty minutes on a generate whose slow half is irrelevant to
the edit.

WHY IT IS POSSIBLE
------------------
A proposal run has two layers, and only the first is slow.

  1. the LLM layer  - analyse, write the content, design the figures. Minutes to tens of
                      minutes, and it produces `replacements.json` + `diagrams/`.
  2. the assembly   - `build_docx.py` turns those into the .docx. About ten seconds.

Every format defect found on 2026-08-11 lived in layer 2: bullets that were a typed glyph
instead of a Word list, six different bullet spacings, a heading numbered twice, a figure
printing over the footer. None of them needed layer 1 to be re-run, yet each round trip
cost a full generate because that is the only button there was.

This script re-runs layer 2 alone against a version directory that already exists, then
runs the full `format_reviewer`. Seconds instead of half an hour, and it exercises exactly
the code where those defects live.

WHAT IT CANNOT TELL YOU
-----------------------
**It rebuilds the ASSEMBLY only, so it does not apply that run's post-assembly repairs.**
A delivered version usually carries `specs/_post_assembly_patches.py` holding fixes that
cannot be made during assembly - the case-study hyperlink that `build_docx.py` flattens,
`cantSplit` on generated table rows, and so on - and they are deliberately not idempotent
against a rebuild. So a CLEAN verdict here means *the assembly is clean*, not *this file is
ready to send*. To produce a deliverable, run the same order Phase 5b uses:
`build_docx.py`, then `specs/_post_assembly_patches.py <docx>`, then
`auto_fix.py --issue image_text_crush`, then the reviewer.

Anything owned by layer 1: whether the Executive Summary reads well, whether a section was
dropped that should not have been, whether a figure says the right thing. Change the
CONTENT and you do have to generate again. Change the SCRIPT or the TEMPLATE and this is
all you need.

USAGE
    python tools/verify_docx.py <version_dir> [--out <path.docx>]
    python tools/verify_docx.py webapp/workspaces/<id>/output/versions/2

The version directory is one holding `replacements.json` and `diagrams/diagrams.json` -
that is, any delivered version. Nothing in it is modified; the rebuild is written to a
temporary file unless --out says otherwise.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "technical-proposal" / "skill" / "linhpham-technicalproposal"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("version_dir", type=Path,
                    help="a versions/<n> directory holding replacements.json and diagrams/")
    ap.add_argument("--out", type=Path, default=None,
                    help="where to write the rebuild (default: a temporary file)")
    ap.add_argument("--template", type=Path,
                    default=SKILL / "templates" / "proposal_template.docx")
    args = ap.parse_args()

    vdir = args.version_dir.resolve()
    repl = vdir / "replacements.json"
    diag = vdir / "diagrams" / "diagrams.json"
    for p in (repl, diag, args.template):
        if not p.exists():
            print(f"! missing: {p}", file=sys.stderr)
            return 2

    out = args.out or Path(tempfile.gettempdir()) / "verify_rebuild.docx"
    print(f"source   : {vdir}")
    print(f"rebuild  : {out}\n")

    build = subprocess.run(
        [sys.executable, "scripts/build_docx.py",
         "--template", str(args.template), "--replacements", str(repl),
         "--diagrams", str(diag), "--out", str(out)],
        cwd=SKILL, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if build.returncode != 0:
        print(build.stdout)
        print(build.stderr, file=sys.stderr)
        print("\nBUILD FAILED", file=sys.stderr)
        return 1
    # Surface only the lines that say what the assembly actually did.
    for line in (build.stdout or "").splitlines():
        low = line.lower()
        if any(k in low for k in ("bullet", "heading", "caption", "dropped",
                                  "inserted", "replacements", "output:")):
            print("  " + line.strip())

    report = out.with_suffix(".review.json")
    rev = subprocess.run(
        [sys.executable, "scripts/format_reviewer.py",
         "--docx", str(out), "--json", str(report)],
        cwd=SKILL, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if not report.exists():
        print(rev.stdout)
        print(rev.stderr, file=sys.stderr)
        return 1

    data = json.loads(report.read_text(encoding="utf-8"))
    issues = data.get("issues", [])
    blockers = [i for i in issues if i.get("severity") == "blocker"]

    print(f"\n{'-' * 66}")
    print(f"checks passed : {len(data.get('checks_passed', []))}")
    print(f"issues        : {len(issues)}   blockers: {len(blockers)}")
    for i in issues:
        fix = " (auto-fixable)" if i.get("auto_fixable") else ""
        print(f"  [{i.get('severity')}] {i.get('id')}{fix}: {str(i.get('summary'))[:96]}")

    # image_text_crush is the documented standing repair that `auto_fix.py` owns after
    # every build, so it is not a reason to call the assembly broken.
    real = [i for i in issues
            if i.get("id") not in ("image_text_crush", "caption_text_crush")]
    print(f"{'-' * 66}")
    if blockers:
        print("RESULT: BLOCKED - fix before generating anything")
        return 1
    if real:
        print("RESULT: OK with warnings above")
        return 0
    print("RESULT: CLEAN (remaining items, if any, are auto_fix's standing repairs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
