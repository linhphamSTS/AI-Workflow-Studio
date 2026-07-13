#!/usr/bin/env bash
# Start the shared web app (macOS/Linux). Runs install-on-first-use, then opens the browser.
cd "$(dirname "$0")" || exit 1
exec bash webapp/run.sh "$@"
