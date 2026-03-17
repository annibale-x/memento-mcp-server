#!/usr/bin/env bash
# Build script wrapper for MCP Memento package (Unix)
# This simply calls the main Python build script to ensure consistent behavior
# across platforms and to avoid duplicating build logic.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/build_memento.py" "$@"
