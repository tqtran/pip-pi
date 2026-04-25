#!/usr/bin/env bash
# Launch pip-pi with root privileges while preserving the display environment.
# Usage: ./run.sh [--fullscreen] [other args]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$(command -v python3)"

# Carry the current user's DISPLAY and XAUTHORITY into the sudo environment,
# and keep the current PYTHONPATH so packages from the user venv are visible.
exec sudo \
    DISPLAY="${DISPLAY:-:0}" \
    XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}" \
    PYTHONPATH="${PYTHONPATH}" \
    HOME="${HOME}" \
    "$PYTHON" "$SCRIPT_DIR/main.py" "$@"
