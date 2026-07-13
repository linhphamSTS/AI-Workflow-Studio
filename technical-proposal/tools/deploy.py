#!/usr/bin/env python3
"""Cross-platform deploy script for the linhpham-technicalproposal skill.

Detects all Claude Code profile directories on the machine and creates a
junction (Windows) or symlink (macOS/Linux) from each profile's skills/
folder to this repo's skill source.

A folder matching .claude* is treated as a real Claude profile only if it
contains at least MIN_SIGNALS of the known Claude Code signature files.
This prevents accidentally deploying into random folders that happen to
share the prefix (e.g. an unrelated .claude-patcher git repo).
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_NAME = "linhpham-technicalproposal"
REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_SOURCE = REPO_ROOT / "skill" / SKILL_NAME

CLAUDE_PROFILE_SIGNALS = [
    ".credentials.json",
    "history.jsonl",
    ".claude.json",
    "projects",
    "plugins",
]
MIN_SIGNALS = 2


def is_claude_profile(path: Path) -> tuple[bool, int, list[str]]:
    if not path.is_dir():
        return False, 0, []
    found = [s for s in CLAUDE_PROFILE_SIGNALS if (path / s).exists()]
    return len(found) >= MIN_SIGNALS, len(found), found


def find_claude_profiles(verbose: bool = True) -> list[Path]:
    home = Path.home()
    candidates = [p for p in home.glob(".claude*") if p.is_dir()]
    # also honor an explicitly-relocated config dir (may live outside home)
    env_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if env_dir and Path(env_dir).is_dir():
        candidates.append(Path(env_dir))
    # de-duplicate by resolved path (e.g. CLAUDE_CONFIG_DIR that is also a ~/.claude* dir)
    seen, uniq = set(), []
    for c in candidates:
        try:
            rp = c.resolve()
        except OSError:
            continue
        if rp not in seen:
            seen.add(rp); uniq.append(c)
    candidates = sorted(uniq, key=lambda p: str(p))
    profiles: list[Path] = []
    if verbose:
        print(f"Scanning {home} for .claude* directories (+ CLAUDE_CONFIG_DIR if set)...")
    for c in candidates:
        ok, score, found = is_claude_profile(c)
        marker = "OK" if ok else "skip"
        if verbose:
            print(f"  [{marker:4s}] {c.name:30s} score={score}/{MIN_SIGNALS}+ signals={found}")
        if ok:
            profiles.append(c)
    return profiles


def remove_existing(dst: Path) -> bool:
    """Remove an existing file/dir/junction at dst. Returns True if removed or absent."""
    if not dst.exists() and not dst.is_symlink():
        return True
    try:
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        elif platform.system() == "Windows":
            # Junction shows as directory; rmdir removes the link, not the target.
            result = subprocess.run(
                ["cmd", "/c", "rmdir", str(dst)],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                # Fall back to rmtree if it was a real directory
                shutil.rmtree(dst)
        else:
            shutil.rmtree(dst)
        return True
    except Exception as e:
        print(f"    ! could not remove existing {dst}: {e}")
        return False


def already_linked(dst: Path, src: Path) -> bool:
    """Return True if dst already points to src (symlink or junction)."""
    try:
        return dst.resolve() == src.resolve()
    except Exception:
        return False


def create_link(src: Path, dst: Path, mode: str) -> bool:
    """Create dst -> src. mode is 'link' (junction/symlink) or 'copy'."""
    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists() or dst.is_symlink():
        if already_linked(dst, src):
            print(f"    already linked correctly")
            return True
        print(f"    destination exists, replacing")
        if not remove_existing(dst):
            return False

    if mode == "copy":
        shutil.copytree(src, dst)
        print(f"    copied -> {dst}")
        return True

    # mode == link
    if platform.system() == "Windows":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(dst), str(src)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"    ! mklink failed: {result.stderr.strip() or result.stdout.strip()}")
            return False
    else:
        try:
            dst.symlink_to(src, target_is_directory=True)
        except OSError as e:
            print(f"    ! symlink failed: {e}")
            return False

    print(f"    linked -> {dst}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy linhpham-technicalproposal skill to all Claude profiles.")
    parser.add_argument("--mode", choices=["link", "copy"], default="link",
                        help="link = junction/symlink (default, recommended); copy = full file copy")
    parser.add_argument("--dry-run", action="store_true", help="Detect profiles but do not modify anything.")
    parser.add_argument("--profile", action="append",
                        help="Restrict deploy to a specific profile dir name (repeatable). Example: --profile .claude --profile .claude-account2")
    args = parser.parse_args()

    print(f"= linhpham-technicalproposal deploy ({args.mode} mode) =")
    print(f"Repo:   {REPO_ROOT}")
    print(f"Source: {SKILL_SOURCE}")
    print()

    if not SKILL_SOURCE.exists():
        print(f"! Skill source not found at {SKILL_SOURCE}")
        print(f"  (Did you clone the full repo? Or is the skill/ folder missing?)")
        return 1

    profiles = find_claude_profiles()
    if args.profile:
        wanted = set(args.profile)
        profiles = [p for p in profiles if p.name in wanted]

    if not profiles:
        print("\n! No Claude profiles detected. Nothing to do.")
        return 1

    print(f"\nFound {len(profiles)} Claude profile(s).")

    if args.dry_run:
        print("(dry-run; no changes made)")
        return 0

    success = 0
    for p in profiles:
        skills_dir = p / "skills"
        dst = skills_dir / SKILL_NAME
        print(f"\n-> {p.name}")
        if create_link(SKILL_SOURCE, dst, mode=args.mode):
            success += 1

    print(f"\n= Done: {success}/{len(profiles)} profiles deployed =")
    return 0 if success == len(profiles) else 1


if __name__ == "__main__":
    sys.exit(main())
