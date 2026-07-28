#!/usr/bin/env bash
# Deploy the linhpham-wbs skill into every Claude profile on this machine (macOS double-click).
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$DIR/tools/deploy.py" "$@"
