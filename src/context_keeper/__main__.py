"""
Entry point for running MCP Context Keeper as a module.

Usage:
    python -m context_keeper [options]

This module entry point delegates to the CLI interface for proper
argument parsing and command handling.
"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
