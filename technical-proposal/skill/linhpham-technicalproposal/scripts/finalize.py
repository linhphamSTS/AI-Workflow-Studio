# -*- coding: utf-8 -*-
"""Assemble, repair, review and finish a proposal in the only order that works, in one command.

Each step undoes something if run out of order (build_docx reinstates the defects the repairs
remove, a Word save strips settings flags, two review checks read English), so the order lives
here and not in anyone's memory:

  0. project-specific steps, if any          --pre <script.py> (repeatable), e.g. a custom render
  1. assemble                                 build_docx.py           (skipped with --skip-build)
  2. repairs only the built file can take     post_assembly.py        (case study link, prose
                                                                       spacing, template tables,
                                                                       page header length), then
                                              --post <script.py> ...   (a project's own repair)
  3. image spacing                            auto_fix.py --issue image_text_crush
  4. strict format review                     format_reviewer.py --strict  -> must be 0 issues
     a copy of the reviewed file is kept as  _work/<name>.reviewed.docx
  5. Vietnamese only: translate               translate_vi.py --client <name>
  6. contents rebuilt by Word                 refresh_toc.py           (both languages: the
                                                                       template ships a stale cache)
  7. stack / figure consistency               check_consistency.py
  8. proposal against the WBS                 check_crossdoc.py        (when --wbs is given)

The review runs BEFORE translation on purpose. The proposal's language is decided at the
Phase 3 gate (plan.json "language": "en" | "vi") and passed here as --language.

Usage:
  python finalize.py --docx <out.docx> --language en|vi --replacements <replacements.json>
      --diagrams <diagrams.json> --plan <plan.json> [--client "<name>"] [--wbs <WBS.xlsx>]
      [--pages <render dir>] [--skip-build] [--pre <script.py> ...] [--post <script.py> ...]
After it prints READY, render the pages and look at every one (05b step 3): no script sees a
figure printed over the footer or a word left alone on a line.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "templates" / "proposal_template.docx"
PY = sys.executable


def run(script, *args, allow_fail=False):
    cmd = [PY, str(script), *map(str, args)]
    print("\n$ " + " ".join(Path(c).name if i < 2 else str(c) for i, c in enumerate(cmd)))
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    for line in out.splitlines()[-12:]:
        print("  " + line)
    if r.returncode and not allow_fail:
        sys.exit("STOPPED at %s (exit %d)" % (Path(script).name, r.returncode))
    return r.returncode, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", required=True)
    ap.add_argument("--language", choices=("en", "vi"), required=True)
    ap.add_argument("--replacements", required=True)
    ap.add_argument("--diagrams", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--client", help="client name as written in the proposal (required for vi)")
    ap.add_argument("--wbs", help="the WBS workbook that ships with this proposal")
    ap.add_argument("--pages", help="rendered page PNGs, for the heading-orphan check")
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--pre", action="append", default=[],
                    help="project-specific script run before the build, e.g. a custom render")
    ap.add_argument("--post", action="append", default=[],
                    help="project-specific repair of the built file, run after post_assembly; "
                         "called with the docx path")
    a = ap.parse_args()
    docx = Path(a.docx).resolve()
    if a.language == "vi" and not a.client:
        sys.exit("--client is required for a Vietnamese proposal")
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    planned = str(plan.get("language") or "").strip().lower()
    planned = "vi" if planned.startswith(("vi", "tiếng việt")) else ("en" if planned.startswith("en") else "")
    if planned and planned != a.language:
        sys.exit("plan.json says language=%r but --language is %s" % (plan["language"], a.language))

    for pre in a.pre:
        run(pre)
    if not a.skip_build:
        run(HERE / "build_docx.py", "--template", TEMPLATE, "--replacements", a.replacements,
            "--diagrams", a.diagrams, "--out", docx)
    run(HERE / "post_assembly.py", "--docx", docx, "--replacements", a.replacements,
        "--language", a.language)
    for post in a.post:
        run(post, docx)
    run(HERE / "auto_fix.py", "--docx", docx, "--issue", "image_text_crush")

    work = docx.parent / "_work"          # every working copy lives here, so the output folder
    work.mkdir(exist_ok=True)             # holds exactly one .docx: the deliverable
    review_json = work / (docx.stem + ".format_review.json")
    args = ["--docx", docx, "--strict", "--json", review_json]
    if a.pages:
        args += ["--pages", a.pages]
    run(HERE / "format_reviewer.py", *args, allow_fail=True)
    rep = json.loads(review_json.read_text(encoding="utf-8"))
    if rep.get("issues"):
        ids = sorted({i["id"] for i in rep["issues"]})
        sys.exit("format review is not clean (%d issue(s): %s). Fix per 05b, then re-run with "
                 "--skip-build if the fix was applied to the assembled file." % (len(rep["issues"]), ids))
    shutil.copy2(docx, work / (docx.stem + ".reviewed.docx"))

    if a.language == "vi":
        run(HERE / "translate_vi.py", "--docx", docx, "--client", a.client)
    if sys.platform == "win32":
        run(HERE / "refresh_toc.py", "--docx", docx)
        bak = docx.with_suffix(".docx.pretoc")
        if bak.exists():
            shutil.move(str(bak), str(work / bak.name))
    else:
        print("\n!! contents NOT refreshed: refresh_toc.py needs Word on Windows. The contents page "
              "still shows the template's cached entries; refresh it before sending.")

    _, out = run(HERE / "check_consistency.py", "--plan", a.plan, "--docx", docx,
                 "--diagrams", a.diagrams)
    if "RESULT: CONSISTENT" not in out:
        sys.exit("consistency gate failed")
    if a.wbs:
        run(HERE / "check_crossdoc.py", "--docx", docx, "--wbs", a.wbs)
    else:
        print("\n(no --wbs: proposal-vs-WBS cross-check skipped; pass it whenever a WBS ships too)")
    print("\nREADY  %s  (%s)" % (docx.name, a.language))


if __name__ == "__main__":
    main()
