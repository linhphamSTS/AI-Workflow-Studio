#!/usr/bin/env bash
# One-time installer for the whole monorepo (macOS/Linux): deploys both skills + sets up the web app.
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
  exec python3 install.py "$@"
elif command -v python >/dev/null 2>&1; then
  exec python install.py "$@"
else
  echo
  echo "[!] Python 3.10+ was not found. Install it from https://www.python.org/downloads/ and re-run."
  echo
  exit 1
fi
