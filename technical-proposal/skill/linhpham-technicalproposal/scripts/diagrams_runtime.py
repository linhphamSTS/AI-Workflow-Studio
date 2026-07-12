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
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Label wrapping — the single canonical helper for EVERY node and cluster
# label (and the drawio export). Use it instead of hand-inserting "\n".
# ---------------------------------------------------------------------------

def wrap_label(text: str, limit: int = 16, max_lines: int = 3) -> str:
    """Wrap a diagram label into <= max_lines short lines without ugly breaks.

    Fixes the defects seen in prior renders:
      * NEVER orphans an opening parenthesis — "Amazon MSK (Kafka)" wraps to
        "Amazon MSK" / "(Kafka)", never "Amazon MSK (" / "Kafka)".
        (The old rule "break at '(' as a boundary" is what produced the
        dangling "(" — we break BEFORE "(", keeping "(...)" together.)
      * NEVER ends a line on a "/", "+", "-" or "(" connector.
      * Keeps short slash groups ("10.0.0.0/16", "client/server") intact and
        only splits them when a single token is itself longer than the limit.

    Returns the text with embedded "\\n" line breaks. Graphviz and draw.io both
    honour "\\n", and because the breaks are explicit neither engine re-wraps
    (re-wrapping by pixel width is what orphaned the "(").
    """
    text = " ".join((text or "").split())  # normalise whitespace
    if not text:
        return ""
    if len(text) <= limit:
        return text
    # A break before "(" so the parenthetical starts a fresh line cleanly.
    norm = re.sub(r"\s*\(", " (", text).strip()
    # Protect a "(...)" group that fits on one line: keep it as a single token
    # so it is never split mid-parenthetical ("(PG family)" stays whole).
    NBSP = "\x00"
    def _protect(m: "re.Match") -> str:
        g = m.group(0)
        return g.replace(" ", NBSP) if len(g) <= limit else g
    norm = re.sub(r"\([^()]*\)", _protect, norm)
    words = [w.replace(NBSP, " ") for w in norm.split(" ") if w]

    def hard_split(tok: str) -> list[str]:
        """Split a single over-long token at /, +, - (keeping the separator on
        the left part) so we never emit a line wider than the cell."""
        if len(tok) <= limit:
            return [tok]
        parts, buf = [], ""
        for ch in tok:
            buf += ch
            if ch in "/+-" and len(buf) >= limit:
                parts.append(buf)
                buf = ""
        if buf:
            parts.append(buf)
        return parts or [tok]

    lines: list[str] = []
    cur = ""
    for w in words:
        for piece in hard_split(w):
            cand = (cur + " " + piece).strip()
            if not cur or len(cand) <= limit:
                cur = cand
            else:
                lines.append(cur)
                cur = piece
    if cur:
        lines.append(cur)

    # Collapse to max_lines by merging the overflow into the last allowed line.
    if len(lines) > max_lines:
        head = lines[: max_lines - 1]
        head.append(" ".join(lines[max_lines - 1:]))
        lines = head

    # Safety net: a line must NEVER end on a lone opening "(" (the headline
    # defect). Parenthetical protection above normally prevents this; this
    # catches an unbalanced "(" with no closing ")".
    for i in range(len(lines) - 1):
        if lines[i].endswith("("):
            lines[i] = lines[i][:-1].rstrip()
            lines[i + 1] = "(" + lines[i + 1]
    return "\n".join(ln for ln in lines if ln)


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


def _icon_resources_present() -> bool:
    """True if the `diagrams` package's bundled icon PNGs are on disk.

    A pip wheel can install the `diagrams` *code* without its `resources/`
    icon tree (seen in the wild), which makes every rendered node a blank box
    with no vendor glyph. We detect that so bootstrap() can repair it."""
    try:
        import diagrams
    except ImportError:
        return False
    # mingrammer resolves an icon as `<dir-of-diagrams-pkg>/../<_icon_dir>` where
    # `_icon_dir` starts with "resources/", i.e. `site-packages/resources/...`.
    # The wheel lays them at the site-packages root, NOT inside the package dir,
    # so check the parent first (the location mingrammer actually reads).
    base = Path(diagrams.__file__).parent
    for res in (base.parent / "resources", base / "resources"):
        if res.exists():
            for _ in res.rglob("*.png"):  # returns on the first icon — fast
                return True
    return False


def _ensure_icon_resources() -> None:
    """Repair a `diagrams` install whose bundled icon `resources/` are missing
    by force-reinstalling the package. Warns (does not hard-fail) if offline so
    the run still produces diagrams — just without vendor glyphs."""
    if _icon_resources_present():
        return
    print("[diagrams_runtime] `diagrams` icon resources MISSING — "
          "force-reinstalling to restore bundled vendor icons...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user",
             "--force-reinstall", "--no-deps", "diagrams"],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"[diagrams_runtime] ! reinstall failed: {e}", file=sys.stderr)
    if not _icon_resources_present():
        print("[diagrams_runtime] ! WARNING: diagrams icons still missing — PNG "
              "nodes will render without vendor glyphs. Fix manually: "
              "pip install --force-reinstall diagrams", file=sys.stderr)


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
    _ensure_icon_resources()
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
