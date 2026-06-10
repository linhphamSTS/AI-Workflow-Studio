#!/usr/bin/env python3
"""Fetch and stage icon packs into skill/.../assets/icons/<pack>/.

Strategy (in order, first to succeed wins per pack):

  1. **Bundled icons from the `diagrams` PyPI package** — preferred, because
     mingrammer/diagrams bundles 525 AWS / 808 Azure / 123 GCP / etc. PNG
     icons that work offline and never 404 when a corporate CDN URL rotates.
     We copy directly into `<pack>/png/` (skipping the SVG → PNG render step).

  2. **Pip install `diagrams` if missing**, then retry step 1.

  3. **Fall back to URL download of source_zip** (legacy path) — copies SVG
     into `<pack>/svg/` so `prerender_icons.py` can render PNGs from them.

If everything fails for a pack, `build_diagram.py`'s `resolve_icon` falls
back to a placeholder shape — the workflow still completes.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve


REPO_ROOT = Path(__file__).resolve().parent.parent
ICONS_ROOT = REPO_ROOT / "skill" / "linhpham-technicalproposal" / "assets" / "icons"
CACHE = REPO_ROOT / ".cache" / "icon_zips"

# Map our pack name -> `diagrams` package provider name
DIAGRAMS_PROVIDER_FOR_PACK = {
    "aws": "aws",
    "azure": "azure",
    "gcp": "gcp",
    "container": "k8s",
    "generic": "generic",
    "network": "onprem",
    "data": "onprem",
    "ai": "saas",
}


def _diagrams_resources_root() -> Path | None:
    """Locate the `resources/` folder bundled with the `diagrams` package."""
    try:
        import diagrams  # type: ignore
    except ImportError:
        return None
    pkg_dir = Path(diagrams.__file__).resolve().parent
    # `resources` lives as a sibling of the diagrams package directory.
    cand = pkg_dir.parent / "resources"
    return cand if cand.exists() else None


def _ensure_diagrams_installed() -> bool:
    """Try to import `diagrams`; if missing, pip-install it and retry."""
    if _diagrams_resources_root() is not None:
        return True
    print("  diagrams package not installed — pip installing...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "--user", "diagrams"],
            check=True, capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"  ! pip install diagrams failed: {e.stderr.decode(errors='replace')[:200]}")
        return False
    return _diagrams_resources_root() is not None


def stage_from_diagrams_package(pack: str, cfg: dict) -> bool:
    """Copy PNGs from the bundled `diagrams` package into <pack>/png/.

    Stages every bundled icon under its normalised name (so any sensible
    `pack/name` reference in a diagram spec resolves), and ALSO writes
    must_have aliases when a bundled icon name contains a must_have token
    (so `aws/alb` works even though the upstream file is named
    `ApplicationLoadBalancer.png`).

    Returns True if at least one icon was staged.
    """
    resources = _diagrams_resources_root()
    if resources is None:
        return False
    provider = DIAGRAMS_PROVIDER_FOR_PACK.get(pack)
    if not provider:
        return False
    src_root = resources / provider
    if not src_root.exists():
        return False
    out_png = ICONS_ROOT / pack / "png"
    out_png.mkdir(parents=True, exist_ok=True)
    wanted = {normalize(n) for n in cfg.get("must_have", [])}

    staged_total = 0
    aliased = 0
    # Walk every PNG in this provider's category subfolders.
    for png in src_root.rglob("*.png"):
        norm = normalize(png.stem)
        if not norm:
            continue
        # 1. Stage under the bundled icon's own normalised name.
        primary = out_png / f"{norm}.png"
        if not primary.exists():
            shutil.copyfile(png, primary)
        staged_total += 1
        # 2. Also write aliases for any must_have token that matches.
        for want in wanted:
            if not want:
                continue
            if want == norm or want in norm or norm in want:
                alias = out_png / f"{want}.png"
                if not alias.exists():
                    shutil.copyfile(png, alias)
                    aliased += 1
                break
    # How many must_have tokens are now resolvable?
    resolved = sum(1 for w in wanted if w and (out_png / f"{w}.png").exists())
    print(f"  staged from diagrams package: {staged_total} PNG icons "
          f"({resolved}/{len(wanted)} must_have resolved, {aliased} aliases)")
    return staged_total > 0


def fetch_zip(url: str, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size > 0:
        print(f"  cached: {dst.name}")
        return True
    print(f"  downloading: {url}")
    try:
        urlretrieve(url, dst)
        return True
    except Exception as e:
        print(f"  ! download failed: {e}")
        return False


def normalize(name: str) -> str:
    return (
        name.lower()
        .replace("_", "-")
        .replace(" ", "-")
        .replace("amazon-", "")
        .replace("aws-", "")
        .replace("azure-", "")
        .replace("microsoft-", "")
        .replace("google-cloud-", "")
        .replace("cloud-", "cloud-")
    )


def stage_pack(pack: str, cfg: dict) -> None:
    print(f"\n== {pack} ==")

    # 1) Preferred: copy from the bundled `diagrams` package (offline, stable).
    if _ensure_diagrams_installed() and stage_from_diagrams_package(pack, cfg):
        return

    # 2) Fall back to downloading the upstream source_zip.
    out_svg = ICONS_ROOT / pack / "svg"
    out_svg.mkdir(parents=True, exist_ok=True)
    src_zip_url = cfg.get("source_zip")
    if not src_zip_url:
        print(f"  no source_zip in manifest — pack {pack} must be populated manually")
        return

    cache_path = CACHE / f"{pack}.zip"
    if not fetch_zip(src_zip_url, cache_path):
        return

    wanted = {normalize(n) for n in cfg.get("must_have", [])}
    found = set()

    try:
        with zipfile.ZipFile(cache_path) as z:
            for name in z.namelist():
                if not name.lower().endswith(".svg"):
                    continue
                base = Path(name).stem
                norm = normalize(base)
                # Match any wanted token contained in the icon name.
                for want in wanted:
                    if want in norm:
                        data = z.read(name)
                        (out_svg / f"{want}.svg").write_bytes(data)
                        found.add(want)
                        break
    except zipfile.BadZipFile:
        print(f"  ! bad zip: {cache_path}")
        return

    missing = wanted - found
    print(f"  staged: {len(found)} / wanted: {len(wanted)}")
    if missing:
        print(f"  missing: {', '.join(sorted(missing))}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", action="append",
                    help="Limit to specific pack(s); default = all packs in manifest")
    args = ap.parse_args()

    manifest = json.loads((ICONS_ROOT / "manifest.json").read_text(encoding="utf-8"))
    packs = manifest["packs"]
    selected = args.pack or list(packs.keys())

    for p in selected:
        if p not in packs:
            print(f"! unknown pack: {p}")
            continue
        stage_pack(p, packs[p])

    print("\nDone. Next step: python tools/prerender_icons.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
