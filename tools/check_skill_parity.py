#!/usr/bin/env python3
"""Assert the two skills draw with the SAME code.

The diagram skill's render layer was ported into the technical-proposal skill so both would
produce figures of the same standard. Nothing then stopped them drifting apart, and they did:
work on a live bid added column straightening to `build_cloud` and polyline routing to
`build_graph` on the proposal side only, so for over a day the diagram skill drew visibly
worse arrows than its sibling and nothing said so. It was found by chance.

A shared file is one that exists in BOTH skills. Every such file must be byte-identical, so a
fix made while working on one bid reaches the other skill in the same commit. Files that exist
in only one skill are listed, not compared: `ingest.py` and `build_diagram_doc.py` genuinely
belong to the diagram skill alone, and `format_reviewer.py`, `build_docx.py`,
`check_consistency.py`, `auto_fix.py` and `render_pages.py` to the proposal alone.

Exit code 0 when every shared file matches, 1 otherwise. Run it before committing a change to
any renderer.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "diagram" / "skill" / "linhpham-diagram" / "scripts"
B = ROOT / "technical-proposal" / "skill" / "linhpham-technicalproposal" / "scripts"


def main() -> int:
    if not A.is_dir() or not B.is_dir():
        print(f"[FAIL] cannot find both script folders:\n  {A}\n  {B}")
        return 1

    a_files = {p.name for p in A.glob("*.py")}
    b_files = {p.name for p in B.glob("*.py")}
    shared = sorted(a_files & b_files)
    if not shared:
        # A check that inspects nothing must fail: either the layout moved or this script is
        # stale, and both are worse than a mismatch because they pass quietly.
        print("[FAIL] no shared scripts found at all - the layout changed or this check is stale")
        return 1

    drifted = []
    for name in shared:
        if (A / name).read_bytes() != (B / name).read_bytes():
            drifted.append(name)
        else:
            print(f"  ok        {name}")

    for name in drifted:
        print(f"  DRIFTED   {name}")

    only_a = sorted(a_files - b_files)
    only_b = sorted(b_files - a_files)
    print(f"\n  diagram-only : {', '.join(only_a) or '(none)'}")
    print(f"  proposal-only: {', '.join(only_b) or '(none)'}")

    print("-" * 64)
    if drifted:
        print(f"[FAIL] {len(drifted)} of {len(shared)} shared script(s) differ between the skills.")
        print("       Copy the newer version both ways so a renderer fix reaches both, then re-run.")
        print("       Compare with:  diff diagram/skill/linhpham-diagram/scripts/<f> \\")
        print("                           technical-proposal/skill/linhpham-technicalproposal/scripts/<f>")
        return 1
    print(f"[PASS] {len(shared)} shared script(s) identical in both skills.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
