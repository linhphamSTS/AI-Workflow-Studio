#!/usr/bin/env python3
"""The `aiws` command: start the app, and keep it up to date.

    aiws              check for a new version, apply it, then start the app
    aiws stop         stop a server that was started without a window
    aiws update       update now and do not start
    aiws version      print the installed commit and whether a newer one exists
    aiws --no-update  start without checking

The Desktop shortcut runs this under pythonw with --windowless, so no console appears. Output
goes to logs/aiws.log instead, and `aiws stop` is how it is shut down, since there is no window
to press Ctrl+C in.

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
PIDFILE = ROOT / ".aiws-pid"
LOGFILE = ROOT / "logs" / "aiws.log"
IS_WIN = os.name == "nt"
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if IS_WIN else 0


def server_python() -> str:
    """The interpreter the SERVER must run under.

    Deliberately python.exe and never pythonw.exe: launch.py decides whether it is already
    inside the virtual-env by comparing sys.executable against .venv/Scripts/python.exe, so
    handing it pythonw makes it conclude it is outside, re-exec into python.exe, and open the
    console the windowless mode exists to avoid.
    """
    venv = ROOT / "webapp" / (".venv/Scripts/python.exe" if IS_WIN else ".venv/bin/python")
    return str(venv) if venv.exists() else sys.executable


def app_port() -> int:
    try:
        return int(os.environ.get("DIAGRAM_PORT", "8000"))
    except ValueError:
        return 8000


def already_serving(port: int) -> bool:
    """Is something answering on the app's port? Used so a second double-click opens the
    browser instead of starting a second server that then fails to bind."""
    import socket
    with socket.socket() as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def go_windowless() -> None:
    """Send output to a log file, because under pythonw sys.stdout is None and the first
    print() would raise AttributeError before anything started."""
    LOGFILE.parent.mkdir(parents=True, exist_ok=True)
    f = open(LOGFILE, "w", encoding="utf-8", buffering=1)
    sys.stdout = f
    sys.stderr = f


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


def update_verdict() -> tuple[str, str | None]:
    """What the pre-start check decided, without acting on it.

    Split out from check_quietly so the progress window can say which of these is happening
    instead of showing one vague "working" message for a 4-second check and a 65 MB download.
    """
    if os.environ.get("AIWS_NO_UPDATE") == "1":
        return "disabled", None
    if is_git_checkout():
        return "git", None
    have, want = installed_sha(), latest_sha(timeout=4.0)
    if not want:
        return "offline", None
    if have == want:
        return "current", want
    return "behind", want


def check_quietly(post=None) -> None:
    """Auto-update on the way to starting the app. Any failure here is reported and ignored:
    not being able to update is never a reason to stop someone opening the app."""
    say = post or (lambda _m: None)
    verdict, want = update_verdict()
    if verdict != "behind":
        return
    msg = f"a newer version is available ({want[:7]}), updating before start ..."
    print(f"- {msg}", flush=True)
    say("Downloading a new version. This can take a minute.")
    try:
        run_installer()
    except Exception as e:  # noqa: BLE001
        print(f"  (update skipped: {e})", flush=True)
        say("Update skipped, starting the version already installed.")


def start_app(argv: list[str], windowless: bool = False) -> int:
    launch = ROOT / "webapp" / "launch.py"
    if not launch.exists():
        print(f"[!] {launch} is missing. Re-run the installer.")
        return 1

    port = app_port()
    if windowless and already_serving(port):
        # Double-clicking the icon again should show the app, not fail to bind a second server.
        print(f"- already running on port {port}, opening the browser")
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{port}")
        return 0

    cmd = [server_python(), str(launch), *argv]
    if not windowless:
        return subprocess.run(cmd).returncode

    # No console anywhere: this process has none (pythonw) and the child is told not to make
    # one. Its output goes to the same log, so a silent failure is still diagnosable.
    proc = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr,
                            creationflags=_NO_WINDOW)
    try:
        PIDFILE.write_text(json.dumps({"pid": proc.pid, "port": port}), encoding="utf-8")
    except OSError:
        pass
    print(f"- started pid {proc.pid} on port {port}; stop it with: aiws stop")
    rc = proc.wait()
    PIDFILE.unlink(missing_ok=True)
    return rc


def start_windowless(skip_update: bool) -> int:
    """Icon launch: a progress window, then the server, then the browser.

    The window exists because everything here is otherwise invisible. It also decides when the
    app is READY by waiting for the port to answer rather than for a fixed number of seconds,
    so the browser never opens onto a connection error.
    """
    import time
    import webbrowser

    port = app_port()
    if already_serving(port):
        print(f"- already running on port {port}, opening the browser")
        webbrowser.open(f"http://127.0.0.1:{port}")
        return 0

    launch = ROOT / "webapp" / "launch.py"
    if not launch.exists():
        print(f"[!] {launch} is missing. Re-run the installer.")
        return 1

    def work(post) -> int:
        if not skip_update:
            post("Checking for updates ...")
            check_quietly(post)

        post("Starting the server ...")
        proc = subprocess.Popen([server_python(), str(launch)],
                                stdout=sys.stdout, stderr=sys.stderr,
                                creationflags=_NO_WINDOW)
        try:
            PIDFILE.write_text(json.dumps({"pid": proc.pid, "port": port}), encoding="utf-8")
        except OSError:
            pass

        # First launch after an update installs dependencies, so this is generous. Watching the
        # process as well as the port means a crash is noticed at once instead of at the timeout.
        deadline = time.time() + 120
        post("Waiting for it to come up ...")
        while time.time() < deadline:
            if already_serving(port):
                post("Opening your browser ...")
                webbrowser.open(f"http://127.0.0.1:{port}")
                time.sleep(1.2)          # let the window be seen rather than blink out
                return 0
            if proc.poll() is not None:
                post(f"It stopped before serving. See logs/aiws.log")
                time.sleep(5)
                return 1
            time.sleep(0.5)

        post("Gave up waiting. See logs/aiws.log")
        time.sleep(5)
        return 1

    icon = ROOT / "webapp" / "static" / "aiws.png"
    try:
        from splash import Splash                       # sits beside this file
    except ImportError:
        sys.path.insert(0, str(HERE))
        try:
            from splash import Splash
        except Exception:                               # noqa: BLE001
            return work(lambda _m: None)                # no window, same work
    return Splash(icon if icon.exists() else None).run(work)


def _kill(pid: int) -> None:
    if IS_WIN:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                       capture_output=True, creationflags=_NO_WINDOW)
    else:
        try:
            os.kill(pid, 15)
        except OSError:
            pass


def port_owners(port: int) -> list[int]:
    """Every process listening on the port. Needed because killing the recorded pid is not
    enough: launch.py hands off to a child, and a descendant has been observed surviving a
    tree kill and continuing to hold the socket while `stop` reported success."""
    pids: set[int] = set()
    try:
        if IS_WIN:
            out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True,
                                 text=True, creationflags=_NO_WINDOW).stdout
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[3] == "LISTENING" and parts[1].endswith(f":{port}"):
                    pids.add(int(parts[4]))
        else:
            out = subprocess.run(["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"],
                                 capture_output=True, text=True).stdout
            pids.update(int(x) for x in out.split())
    except Exception:  # noqa: BLE001
        pass
    return sorted(pids)


def stop_app() -> int:
    """Stop a windowless server. Without this there is no way to stop one: there is no console
    to press Ctrl+C in, which is the cost of not showing a window.

    The success condition is that the PORT IS FREE, not that a pid was signalled. Reporting
    "stopped" while something still answers is the failure mode this exists to prevent.
    """
    import time
    port = app_port()

    pid = None
    try:
        pid = json.loads(PIDFILE.read_text(encoding="utf-8")).get("pid")
    except Exception:  # noqa: BLE001
        pass

    if not pid and not already_serving(port):
        print("- not running")
        PIDFILE.unlink(missing_ok=True)
        return 0

    if pid:
        _kill(pid)

    # Then make the port the authority, with a couple of passes for anything that outlived
    # the tree kill or was started from a terminal without a pid file.
    for attempt in range(3):
        time.sleep(0.6)
        if not already_serving(port):
            break
        owners = [p for p in port_owners(port) if p != os.getpid()]
        if not owners:
            break
        if attempt == 0 and not pid:
            print(f"- no pid file; stopping whatever holds port {port}: {owners}")
        for p in owners:
            _kill(p)

    PIDFILE.unlink(missing_ok=True)
    if already_serving(port):
        print(f"- something is STILL answering on port {port}. Remaining: {port_owners(port)}")
        print("    If you started it from a terminal, press Ctrl+C there.")
        return 1
    print("- stopped")
    return 0


def main() -> int:
    args = sys.argv[1:]

    # sys.stdout is None under pythonw, which is how the Desktop shortcut runs this.
    windowless = "--windowless" in args or sys.stdout is None
    if windowless:
        go_windowless()
        args = [a for a in args if a != "--windowless"]

    if args and args[0] in ("stop", "--stop"):
        return stop_app()

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

    skip_update = "--no-update" in args
    if windowless:
        # The icon path gets the progress window, which owns the update check too so it can
        # report on it. A terminal launch already shows everything, so it stays as it was.
        return start_windowless(skip_update)

    if not skip_update:
        check_quietly()
    return start_app([a for a in args if a != "--no-update"])


if __name__ == "__main__":
    raise SystemExit(main())
