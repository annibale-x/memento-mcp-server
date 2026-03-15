#!/usr/bin/env python3
"""
Wrapper script for MCP Context Keeper.

This script provides a proper entry point for running the MCP Context Keeper
as a standalone process, compatible with Zed Editor's MCP configuration.

Usage:
    python context_keeper.py

Environment Variables:
    CONTEXT_SQLITE_PATH: Path to SQLite database file
    CONTEXT_TOOL_PROFILE: Tool profile (core|extended)
    CONTEXT_LOG_LEVEL: Logging level (DEBUG|INFO|WARNING|ERROR)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


try:
    from context_keeper.cli import main as cli_main
    from context_keeper.config import Config
    from context_keeper.server import main as server_main
except ImportError as e:
    print(f"Error importing context_keeper modules: {e}")
    print(
        "Make sure you are in the project root directory and dependencies are installed."
    )
    sys.exit(1)


def run_server():
    """
    Run the MCP Context Keeper.

    This function starts the MCP server with configuration from environment variables.
    """
    # Map environment variables to config
    env_config = {}

    # SQLite database path
    if sqlite_path := os.getenv("CONTEXT_SQLITE_PATH"):
        env_config["sqlite_path"] = sqlite_path
        # Also set environment variable directly to ensure Config reads it
        os.environ["CONTEXT_SQLITE_PATH"] = sqlite_path

    # Tool profile
    if tool_profile := os.getenv("CONTEXT_TOOL_PROFILE"):
        env_config["tool_profile"] = tool_profile
        os.environ["CONTEXT_TOOL_PROFILE"] = tool_profile

    # Log level
    if log_level := os.getenv("CONTEXT_LOG_LEVEL"):
        env_config["log_level"] = log_level
        os.environ["CONTEXT_LOG_LEVEL"] = log_level

    # Apply environment configuration
    if env_config:
        config = Config()
        for key, value in env_config.items():
            if hasattr(config, key):
                setattr(config, key, value)
                print(f"Config: {key} = {value}")

    print("Starting MCP Context Keeper...")
    print(f"Project root: {project_root}")

    # Run the server
    asyncio.run(server_main())


def show_help():
    """Show help information."""
    print("MCP Context Keeper Wrapper")
    print("=" * 40)
    print()
    print("Usage:")
    print("  python context_keeper.py          - Start the MCP server")
    print("  python context_keeper.py --health - Run health check")
    print("  python context_keeper.py --help   - Show this help")
    print()
    print("Environment Variables:")
    print("  CONTEXT_SQLITE_PATH    - Path to SQLite database file")
    print("  CONTEXT_TOOL_PROFILE   - Tool profile (core|extended)")
    print("  CONTEXT_LOG_LEVEL      - Logging level (DEBUG|INFO|WARNING|ERROR)")
    print()
    print("For more CLI options, use the context_keeper module directly:")
    print("  python -m context_keeper.cli --help")


if __name__ == "__main__":
    # Check for command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg in ["-h", "--help"]:
            show_help()
            sys.exit(0)
        elif arg == "--health":
            # Run health check via CLI
            sys.argv = ["context_keeper.cli", "--health"]
            cli_main()
        else:
            print(f"Unknown argument: {arg}")
            show_help()
            sys.exit(1)
    else:
        # No arguments, run the server
        run_server()
