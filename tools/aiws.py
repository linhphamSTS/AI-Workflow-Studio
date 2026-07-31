#!/usr/bin/env python3
"""The `aiws` command: start the app, and keep it up to date.

    aiws              check for a new version, apply it, then start the app
    aiws update       update now and do not start
    aiws version      print the installed commit and whether a newer one exists
    aiws --no-update  start without checking

The launcher script written by the installer calls this file, so the behaviour lives in one
place for Windows, macOS and Linux instead of being duplicated into a .cmd and a shell script.

Auto-update runs BEFORE the server starts, never while it is running: replacing files under a
live process is how an update turns into a support call. It is also skipped when the install
directory is a git working copy, because that is somebody developing the app, and mirroring
GitHub over their uncommitted work would destroy it.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = "linhphamSTS/AI-Workflow-Studio"
BRANCH = "main"
STAMP = ROOT / ".aiws-version"
IS_WIN = os.name == "nt"


def installed_sha() -> str | None:
    try:
        return json.loads(STAMP.read_text(encoding="utf-8")).get("sha")
    except Exception:  # noqa: BLE001
        return None


def latest_sha(timeout: float = 6.0) -> str | None:
    """The head commit of the branch, or None when offline.

    A short timeout on purpose: a slow or blocked network must delay starting the app by
    seconds, not minutes. Being unable to check is not a reason to refuse to run.
    """
    url = f"https://api.github.com/repos/{REPO}/commits/{BRANCH}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github.sha",       # returns the bare sha, not 100 KB of JSON
        "User-Agent": "ai-workflow-studio-updater",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8").strip() or None
    except (urllib.error.URLError, OSError, TimeoutError):
        return None


def is_git_checkout() -> bool:
    return (ROOT / ".git").exists()


def run_installer(assume_yes: bool = True) -> int:
    """Re-run the platform installer against this directory. It mirrors the new files in and
    leaves .git, webapp/workspaces and webapp/.venv alone."""
    env = dict(os.environ, AIWS_NO_START="1")
    if assume_yes:
        env["AIWS_YES"] = "1"
    if IS_WIN:
        script = ROOT / "get.ps1"
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
               "-File", str(script), "-Dir", str(ROOT), "-NoStart"]
    else:
        script = ROOT / "get.sh"
        cmd = ["bash", str(script), "--dir", str(ROOT), "--no-start"]
    if not script.exists():
        print(f"[!] {script.name} is missing, so this install cannot update itself.")
        print(f"    Re-run the one-line installer to repair it.")
        return 1
    return subprocess.run(cmd, env=env).returncode


def do_update(force: bool = False) -> int:
    if is_git_checkout() and not force:
        print("- this install is a git working copy, so it updates with git, not the installer")
        print("    git pull   (then re-run install.py if a skill was added)")
        return 0
    have, want = installed_sha(), latest_sha()
    if want and have == want:
        print(f"- already up to date ({have[:7]})")
        return 0
    if not want:
        print("- could not reach GitHub; leaving the current version in place")
        return 0
    print(f"- updating {have[:7] if have else 'unknown'} -> {want[:7]}")
    return run_installer()


def check_quietly() -> None:
    """Auto-update on the way to starting the app. Any failure here is reported and ignored:
    not being able to update is never a reason to stop someone opening the app."""
    if os.environ.get("AIWS_NO_UPDATE") == "1" or is_git_checkout():
        return
    have, want = installed_sha(), latest_sha(timeout=4.0)
    if not want or have == want:
        return
    print(f"- a newer version is available ({want[:7]}), updating before start ...", flush=True)
    try:
        run_installer()
    except Exception as e:  # noqa: BLE001
        print(f"  (update skipped: {e})", flush=True)


def start_app(argv: list[str]) -> int:
    launch = ROOT / "webapp" / "launch.py"
    if not launch.exists():
        print(f"[!] {launch} is missing. Re-run the installer.")
        return 1
    return subprocess.run([sys.executable, str(launch), *argv]).returncode


def main() -> int:
    args = sys.argv[1:]

    if args and args[0] in ("update", "--update", "-u"):
        return do_update(force="--force" in args)

    if args and args[0] in ("version", "--version", "-V"):
        have = installed_sha()
        print(f"AI Workflow Studio at {ROOT}")
        print(f"  installed : {have or 'unknown (installed before versions were stamped)'}")
        if is_git_checkout():
            print("  source    : git working copy, managed with git")
        else:
            want = latest_sha()
            if not want:
                print("  latest    : could not reach GitHub")
            elif want == have:
                print("  latest    : same, up to date")
            else:
                print(f"  latest    : {want}  -> run 'aiws update'")
        print(f"  python    : {sys.executable}")
        print(f"  platform  : {platform.platform()}")
        return 0

    if args and args[0] in ("help", "--help", "-h"):
        print(__doc__)
        return 0

    passthrough = [a for a in args if a != "--no-update"]
    if "--no-update" not in args:
        check_quietly()
    return start_app(passthrough)


if __name__ == "__main__":
    raise SystemExit(main())
