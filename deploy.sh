#!/bin/bash
# Linux deploy wrapper.
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found. Install Python 3.9+ first."
    exit 1
fi

python3 tools/deploy.py "$@"
