#!/bin/bash
# macOS double-clickable deploy wrapper.
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found. Install Python 3.9+ from https://www.python.org/downloads/macos/"
    read -p "Press Enter to close..."
    exit 1
fi

python3 tools/deploy.py "$@"
RC=$?

echo
if [ "$RC" -eq 0 ]; then
    echo "Deploy succeeded."
else
    echo "Deploy finished with errors. See output above."
fi
read -p "Press Enter to close..."
exit $RC
