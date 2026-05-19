#!/usr/bin/env bash
# Portable launcher. The Python CLI owns validation and exit status.
set -eu
if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' 'INCOMPLETE: python3 is required' >&2
    exit 2
fi
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 -B "$SCRIPT_DIR/verify.py" starter "$@"
