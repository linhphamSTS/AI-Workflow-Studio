#!/usr/bin/env bash
# Diagram Workflow — one-command launcher (macOS / Linux).
# First run installs everything into webapp/.venv, then starts the app.
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
  exec python3 launch.py "$@"
elif command -v python >/dev/null 2>&1; then
  exec python launch.py "$@"
else
  echo
  echo "[!] Python 3.10+ was not found. Install it from https://www.python.org/downloads/ and re-run."
  echo
  exit 1
fi
