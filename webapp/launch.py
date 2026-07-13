#!/usr/bin/env python3
"""
One-command launcher for the AI Workflow Studio web app.

Move the repo to any machine and just run this (or `run.bat` / `run.sh`). On the
first run it is fully self-installing:

  1. creates a self-contained virtual-env at  webapp/.venv
  2. pip-installs everything in  requirements.txt  into it
  3. ensures Graphviz (the skill downloads a portable copy on first render if missing)
  4. starts the server and opens your browser

Later runs skip straight to step 4. Nothing to set up by hand.

The only thing this cannot install for you is the `claude` CLI itself (it needs a
one-time interactive login). If it is missing, the app still runs - Generate /
Preview / Export work; only the Refine step needs `claude` and will say so.

Usage:
    python launch.py                 # set up (if needed) + run + open browser
    python launch.py --setup-only    # set up only, do not start the server
    DIAGRAM_NO_VENV=1 python launch.py   # install into the current interpreter, no venv
    DIAGRAM_PORT=8080 python launch.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

# Windows consoles default to cp1252 and crash on non-Latin-1 glyphs - force UTF-8
# for our own prints and keep the messages themselves ASCII to be safe everywhere.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

HERE = Path(__file__).resolve().parent
VENV = HERE / ".venv"
REQ = HERE / "requirements.txt"
IS_WIN = os.name == "nt"
VENV_PY = VENV / ("Scripts" if IS_WIN else "bin") / ("python.exe" if IS_WIN else "python")
SETUP_ONLY = "--setup-only" in sys.argv


def _in_our_venv() -> bool:
    try:
        return VENV_PY.exists() and Path(sys.executable).resolve() == VENV_PY.resolve()
    except OSError:
        return False


def _pip_install(py_exe: str) -> int:
    """pip-install requirements.txt using the given interpreter. Returns 0 on success."""
    print("- installing dependencies (first run may take a minute) ...", flush=True)
    subprocess.run([py_exe, "-m", "pip", "install", "--quiet", "--upgrade", "pip"], check=False)
    r = subprocess.run([py_exe, "-m", "pip", "install", "-r", str(REQ)])
    if r.returncode != 0:
        print("\n[!] Dependency install failed. Check your internet connection and re-run.", file=sys.stderr)
    return r.returncode


def _deps_present() -> bool:
    """Are the runtime deps importable by the current interpreter? (used for --no-venv)."""
    try:
        import importlib.util
        return all(importlib.util.find_spec(m) is not None for m in ("fastapi", "uvicorn", "multipart"))
    except Exception:  # noqa: BLE001
        return False


def _ensure_env_then_reexec() -> int:
    """Create .venv (if missing/broken), install deps, then re-run this script inside it."""
    if not VENV_PY.exists():   # missing OR a half-created venv -> (re)build it
        print("- creating virtual environment (.venv) ...", flush=True)
        venv.EnvBuilder(with_pip=True, clear=VENV.exists()).create(VENV)

    marker = VENV / ".deps_ok"
    need = (not marker.exists()) or (REQ.exists() and REQ.stat().st_mtime > marker.stat().st_mtime)
    if need:
        rc = _pip_install(str(VENV_PY))
        if rc != 0:
            return rc
        marker.write_text("ok", encoding="utf-8")
    else:
        print("- dependencies already installed", flush=True)

    # hand off to the venv interpreter (subprocess is more reliable than execv on Windows).
    # DIAGRAM_REEXEC guards against an infinite re-exec loop if venv detection ever mismatches.
    env = {**os.environ, "DIAGRAM_REEXEC": "1"}
    return subprocess.run([str(VENV_PY), str(HERE / "launch.py"), *sys.argv[1:]], env=env).returncode


def _check_claude() -> None:
    """Verify the claude CLI is installed AND signed in (Refine needs both)."""
    exe = shutil.which("claude")
    if not exe:
        print("\n  " + "!" * 3 + " 'claude' CLI not found on PATH.")
        print("      The Refine step calls it. Install Claude Code:")
        print("      https://docs.claude.com/claude-code")
        print("      (Generate / Preview / Export still work; only Refine needs it.)\n", flush=True)
        return
    # installed -> check login state via `claude auth status --json`
    info = {}
    try:
        r = subprocess.run([exe, "auth", "status", "--json"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=30,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        info = json.loads(r.stdout or "{}")
    except Exception:  # noqa: BLE001
        info = {}
    if info.get("loggedIn"):
        who = info.get("email") or info.get("orgName") or ""
        print(f"- claude CLI: signed in{(' as ' + who) if who else ''}", flush=True)
    else:
        print("\n  " + "!" * 3 + " 'claude' is installed but NOT signed in.")
        print("      The Refine step will fail until you log in. Run this in a terminal:")
        print("        claude auth login")
        print("      then start the app again. (Generate / Preview / Export work without it.)\n", flush=True)


def _prewarm_graphviz() -> None:
    """Trigger the skill's own bootstrap so Graphviz is ready before the first render."""
    try:
        sys.path.insert(0, str(HERE.parent / "diagram" / "skill" / "linhpham-diagram" / "scripts"))
        import diagrams_runtime  # noqa: E402
        print("- ensuring Graphviz (downloads a portable copy on first run if missing) ...", flush=True)
        diagrams_runtime.bootstrap()
        print("- Graphviz: ready", flush=True)
    except Exception as e:  # noqa: BLE001
        print(f"  (Graphviz pre-warm skipped: {e}; renderers will bootstrap on first use)", flush=True)


def main() -> int:
    # Phase 1: make sure the interpreter that will run the server has the deps.
    novenv = os.environ.get("DIAGRAM_NO_VENV") == "1"
    reexeced = os.environ.get("DIAGRAM_REEXEC") == "1"
    if novenv:
        # use the current interpreter; install into it if the deps aren't there yet
        if not _deps_present():
            rc = _pip_install(sys.executable)
            if rc != 0:
                return rc
    elif not _in_our_venv() and not reexeced:
        return _ensure_env_then_reexec()

    # Phase 2 (inside the venv / current interpreter): verify tooling, then run.
    print("- python:", sys.executable, flush=True)
    _check_claude()
    _prewarm_graphviz()

    if SETUP_ONLY:
        print("\nOK - Setup complete. Run again without --setup-only to start the app.")
        return 0

    host = os.environ.get("DIAGRAM_HOST", "127.0.0.1")
    port = os.environ.get("DIAGRAM_PORT", "8000")
    url = f"http://{host}:{port}"
    try:
        import threading, webbrowser
        threading.Timer(2.0, lambda: webbrowser.open(url)).start()
    except Exception:  # noqa: BLE001
        pass
    print(f"\n  >  AI Workflow Studio  ->  {url}   (press Ctrl+C to stop)\n", flush=True)

    import runpy
    try:
        runpy.run_path(str(HERE / "server.py"), run_name="__main__")
    except KeyboardInterrupt:
        print("\n- stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
