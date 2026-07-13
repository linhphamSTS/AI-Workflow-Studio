#!/usr/bin/env python3
"""
One-time installer for the whole monorepo. Run this ONCE per machine (or after moving
the repo). It sets up EVERYTHING:

  1. Deploys BOTH Claude Code skills into every local Claude profile
     (a junction on Windows / symlink on macOS-Linux, so editing in the repo updates
      every profile live):
        - /linhpham-technicalproposal   (technical-proposal/)
        - /linhpham-diagram             (diagram/)
  2. Sets up the shared web app (creates webapp/.venv, installs its dependencies, and
     ensures Graphviz) WITHOUT launching it.

Prerequisite: Python 3.10+.  (The `claude` CLI is needed at run time for the Refine /
Analyze / Generate steps — the web-app setup reports whether it's installed + signed in.)

    python install.py          # or:  install.bat  (Windows)  /  ./install.sh  (macOS/Linux)

Afterwards:
    - Skills work in any Claude Code session:  /linhpham-diagram  and  /linhpham-technicalproposal
    - Start the web app:  python webapp/launch.py   (or run.bat / run.sh)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

HERE = Path(__file__).resolve().parent
SKILLS = ["technical-proposal", "diagram"]


def _step(title: str, cmd: list[str]) -> int:
    print("\n" + "=" * 66)
    print("  " + title)
    print("=" * 66, flush=True)
    try:
        return subprocess.run(cmd).returncode
    except FileNotFoundError as e:
        print(f"[!] {e}", file=sys.stderr)
        return 1


def main() -> int:
    py = sys.executable
    failures = []

    # 1) deploy both skills (idempotent — re-links every local Claude profile)
    for skill in SKILLS:
        deploy = HERE / skill / "tools" / "deploy.py"
        if not deploy.exists():
            print(f"[!] missing {deploy}", file=sys.stderr); failures.append(skill); continue
        if _step(f"Deploy skill: {skill}", [py, str(deploy)]) != 0:
            failures.append(f"deploy:{skill}")

    # 2) set up the shared web app (venv + deps + Graphviz), do NOT launch
    if _step("Set up the web app (venv + dependencies + Graphviz)",
             [py, str(HERE / "webapp" / "launch.py"), "--setup-only"]) != 0:
        failures.append("webapp")

    print("\n" + "=" * 66)
    if failures:
        print("  Install finished WITH WARNINGS: " + ", ".join(failures))
        print("  (Re-run install.py, or run the failing step by hand — see messages above.)")
    else:
        print("  INSTALL COMPLETE - both skills deployed, web app ready.")
    print("=" * 66)
    print("\n  Skills (any Claude Code session):  /linhpham-diagram   /linhpham-technicalproposal")
    print("  Start the web app:                 python webapp/launch.py   (or run.bat / run.sh)")
    print("  Web app URL:                       http://127.0.0.1:8000\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
