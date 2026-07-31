#!/usr/bin/env python3
"""
One-time installer for the whole monorepo. Run this ONCE per machine (or after moving
the repo). It sets up EVERYTHING:

  1. Deploys EVERY Claude Code skill in this repo into every local Claude profile
     (a junction on Windows / symlink on macOS-Linux, so editing in the repo updates
      every profile live). Currently:
        - /linhpham-technicalproposal   (technical-proposal/)
        - /linhpham-diagram             (diagram/)
        - /linhpham-wbs                 (wbs-estimate/)
  2. Sets up the shared web app (creates webapp/.venv, installs its dependencies, and
     ensures Graphviz) WITHOUT launching it.

Prerequisite: Python 3.10+.  (The `claude` CLI is needed at run time for the Refine /
Analyze / Generate steps — the web-app setup reports whether it's installed + signed in.)

    python install.py          # or:  install.bat  (Windows)  /  ./install.sh  (macOS/Linux)

Afterwards:
    - Skills work in any Claude Code session:  /linhpham-diagram, /linhpham-technicalproposal
      and /linhpham-wbs
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


def discover_skills() -> list[tuple[str, str]]:
    """Find every skill folder: returns (folder name, slash-command name) pairs.

    A skill folder is any top-level folder that ships BOTH tools/deploy.py and a
    skill/<command-name>/ source dir. Discovering them beats listing them: a list
    goes stale the moment a skill is added, and the failure is silent - the new
    skill simply never reaches the user's machine.
    """
    found: list[tuple[str, str]] = []
    for deploy in sorted(HERE.glob("*/tools/deploy.py")):
        folder = deploy.parent.parent
        commands = [p.name for p in sorted((folder / "skill").glob("*")) if p.is_dir()]
        if commands:
            found.append((folder.name, commands[0]))
    return found


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

    skills = discover_skills()
    if not skills:
        print("[!] No skill folders found (expected <folder>/tools/deploy.py). "
              "Is install.py still at the repo root?", file=sys.stderr)
        return 1

    # 1) deploy every skill (idempotent - re-links every local Claude profile)
    for folder, _command in skills:
        if _step(f"Deploy skill: {folder}", [py, str(HERE / folder / "tools" / "deploy.py")]) != 0:
            failures.append(f"deploy:{folder}")

    # 2) set up the shared web app (venv + deps + Graphviz), do NOT launch
    if _step("Set up the web app (venv + dependencies + Graphviz)",
             [py, str(HERE / "webapp" / "launch.py"), "--setup-only"]) != 0:
        failures.append("webapp")

    print("\n" + "=" * 66)
    if failures:
        print("  Install finished WITH WARNINGS: " + ", ".join(failures))
        print("  (Re-run install.py, or run the failing step by hand - see messages above.)")
    else:
        print(f"  INSTALL COMPLETE - {len(skills)} skill(s) deployed, web app ready.")
    print("=" * 66)
    commands = "   ".join(f"/{c}" for _f, c in skills)
    print(f"\n  Skills (any Claude Code session):  {commands}")
    print("  Start the web app:                 python webapp/launch.py   (or run.bat / run.sh)")
    print("  Web app URL:                       http://127.0.0.1:8000\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
