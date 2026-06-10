"""Runtime helper for the Phase-4 diagram-builder agent.

Use at the top of any Python script that imports `diagrams` (mingrammer):

    from diagrams_runtime import bootstrap
    bootstrap()  # ensures `diagrams` + Graphviz are available, wires PATH

It will, in this order:
  1. import `diagrams` — pip-install if missing.
  2. Locate the `dot` Graphviz binary in PATH.
  3. If not in PATH, look for the portable build at
     `~/graphviz_portable/Graphviz-*/bin/dot(.exe)`.
  4. If still not found, on Windows download the portable zip from the
     known-good GitLab release URL and extract it under `~/graphviz_portable`.
  5. On macOS / Linux, suggest the right `brew` / `apt` command and exit.

The user never runs anything by hand — Phase 4 just calls bootstrap().
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path


GRAPHVIZ_PORTABLE_ROOT = Path.home() / "graphviz_portable"
GRAPHVIZ_DOWNLOAD_URL = (
    "https://gitlab.com/api/v4/projects/4207231/packages/generic/"
    "graphviz-releases/12.2.1/"
    "windows_10_cmake_Release_Graphviz-12.2.1-win64.zip"
)


def _ensure_diagrams_package() -> None:
    """Import `diagrams`; if missing, pip-install it and re-import."""
    try:
        import diagrams  # noqa: F401
        return
    except ImportError:
        pass
    print("[diagrams_runtime] `diagrams` package missing — pip installing...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "--user", "diagrams"],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"pip install diagrams failed: {e}") from e
    import diagrams  # noqa: F401 — verify install worked


def _find_dot() -> Path | None:
    """Return the path to `dot` (Graphviz layout engine), or None if missing."""
    binname = "dot.exe" if platform.system() == "Windows" else "dot"
    # 1. PATH
    found = shutil.which(binname)
    if found:
        return Path(found)
    # 2. Portable install
    if GRAPHVIZ_PORTABLE_ROOT.exists():
        candidates = sorted(GRAPHVIZ_PORTABLE_ROOT.glob(f"Graphviz-*/bin/{binname}"))
        if candidates:
            return candidates[-1]
    return None


def _install_graphviz_windows() -> Path | None:
    """Download + extract the portable Graphviz zip under ~/graphviz_portable."""
    GRAPHVIZ_PORTABLE_ROOT.mkdir(parents=True, exist_ok=True)
    zip_path = GRAPHVIZ_PORTABLE_ROOT / "graphviz_portable.zip"
    if not zip_path.exists():
        print(f"[diagrams_runtime] downloading Graphviz portable from {GRAPHVIZ_DOWNLOAD_URL}")
        try:
            urllib.request.urlretrieve(GRAPHVIZ_DOWNLOAD_URL, zip_path)
        except Exception as e:
            print(f"[diagrams_runtime] ! download failed: {e}", file=sys.stderr)
            return None
    print("[diagrams_runtime] extracting...")
    try:
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(GRAPHVIZ_PORTABLE_ROOT)
    except zipfile.BadZipFile as e:
        print(f"[diagrams_runtime] ! bad zip: {e}", file=sys.stderr)
        return None
    return _find_dot()


def _install_graphviz_unix() -> None:
    """We don't auto-install on macOS / Linux because it requires sudo; tell
    the user the one-line install command instead."""
    sys_name = platform.system()
    if sys_name == "Darwin":
        msg = "Install Graphviz: `brew install graphviz`"
    else:
        msg = ("Install Graphviz via your package manager, e.g. "
               "`sudo apt install graphviz` or `sudo yum install graphviz`.")
    raise RuntimeError(
        f"Graphviz `dot` binary not found and cannot be auto-installed on {sys_name}. "
        + msg
    )


def bootstrap() -> Path:
    """Ensure `diagrams` + Graphviz are ready. Returns the path to `dot`.
    Adds Graphviz `bin/` to PATH for the rest of this process."""
    _ensure_diagrams_package()
    dot = _find_dot()
    if dot is None:
        print("[diagrams_runtime] Graphviz `dot` not found — installing...")
        if platform.system() == "Windows":
            dot = _install_graphviz_windows()
        else:
            _install_graphviz_unix()
        if dot is None:
            raise RuntimeError("Graphviz install failed — cannot render diagrams.")
    # Wire bin/ onto PATH so subprocess calls find it.
    bin_dir = str(dot.parent)
    if bin_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
    return dot


if __name__ == "__main__":
    dot = bootstrap()
    print(f"OK — Graphviz at: {dot}")
