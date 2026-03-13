"""
Command-line interface for MemoryGraph MCP Server.

Provides easy server startup with configuration options for AI coding agents.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Tuple

from . import __version__
from .config import TOOL_PROFILES, BackendType, Config
from .server import main as server_main

logger = logging.getLogger(__name__)


def _eprint(*args, **kwargs):
    """Print to stderr to avoid polluting MCP stdio transport on stdout."""
    kwargs.setdefault("file", sys.stderr)
    print(*args, **kwargs)


async def _create_backend_and_db() -> Tuple:
    """Create a backend and the appropriate database wrapper.

    Returns a (backend, backend_name, db) tuple. The caller is responsible
    for calling ``await backend.disconnect()`` when finished.
    """
    from .backends.factory import BackendFactory
    from .backends.sqlite_fallback import SQLiteFallbackBackend
    from .sqlite_database import SQLiteMemoryDatabase

    backend = await BackendFactory.create_backend()
    backend_name = backend.backend_name()

    # Always use SQLiteMemoryDatabase since we only support SQLite backend
    db = SQLiteMemoryDatabase(backend)

    return backend, backend_name, db


async def handle_export(args: argparse.Namespace) -> None:
    """Handle export command - works with all backends."""
    from .utils.export_import import export_to_json, export_to_markdown

    try:
        backend, backend_name, db = await _create_backend_and_db()
        _eprint(f"\nExporting memories from {backend_name} backend...")

        start_time = time.time()

        if args.format == "json":
            result = await export_to_json(db, args.output)
            duration = time.time() - start_time

            _eprint("\nExport complete!")
            _eprint(f"   Backend: {result.get('backend_type', backend_name)}")
            _eprint(f"   Output: {args.output}")
            _eprint(f"   Memories: {result['memory_count']}")
            _eprint(f"   Relationships: {result['relationship_count']}")
            _eprint(f"   Duration: {duration:.1f} seconds")

        elif args.format == "markdown":
            await export_to_markdown(db, args.output)
            duration = time.time() - start_time

            _eprint("\nExport complete!")
            _eprint(f"   Backend: {backend_name}")
            _eprint(f"   Output: {args.output}/")
            _eprint(f"   Duration: {duration:.1f} seconds")

        await backend.disconnect()

    except Exception as e:
        _eprint(f"Export failed: {e}")
        logger.error(f"Export failed: {e}", exc_info=True)
        sys.exit(1)


async def handle_import(args: argparse.Namespace) -> None:
    """Handle import command - works with all backends."""
    from .utils.export_import import import_from_json

    try:
        backend, backend_name, db = await _create_backend_and_db()
        _eprint(f"\nImporting memories to {backend_name} backend...")

        await db.initialize_schema()

        start_time = time.time()

        if args.format == "json":
            result = await import_from_json(
                db, args.input, skip_duplicates=args.skip_duplicates
            )
            duration = time.time() - start_time

            _eprint("\nImport complete!")
            _eprint(f"   Backend: {backend_name}")
            _eprint(
                f"   Imported: {result['imported_memories']} memories, {result['imported_relationships']} relationships"
            )
            if result["skipped_memories"] > 0 or result["skipped_relationships"] > 0:
                _eprint(
                    f"   Skipped: {result['skipped_memories']} memories, {result['skipped_relationships']} relationships"
                )
            _eprint(f"   Duration: {duration:.1f} seconds")

        await backend.disconnect()

    except Exception as e:
        _eprint(f"Import failed: {e}")
        logger.error(f"Import failed: {e}", exc_info=True)
        sys.exit(1)


async def handle_migrate(args: argparse.Namespace) -> None:
    """Handle migrate command (simplified for SQLite-only version)."""
    _eprint("\nMigration functionality has been simplified for SQLite-only version.")
    _eprint("Only SQLite to SQLite migrations are supported.")

    if args.source_backend and args.source_backend != "sqlite":
        _eprint(f"\nError: Source backend '{args.source_backend}' is not supported.")
        _eprint("Only 'sqlite' backend is supported in this version.")
        sys.exit(1)

    if args.target_backend != "sqlite":
        _eprint(f"\nError: Target backend '{args.target_backend}' is not supported.")
        _eprint("Only 'sqlite' backend is supported in this version.")
        sys.exit(1)

    _eprint("\nNote: For SQLite to SQLite migrations, simply copy the database file.")
    _eprint("Example: cp ~/.memorygraph/memory.db ~/.memorygraph/memory_backup.db")
    _eprint("\nOr use the export/import commands:")
    _eprint("  memorygraph export --format json --output memories.json")
    _eprint("  memorygraph import --format json --input memories.json")
    sys.exit(0)


async def handle_migrate_multitenant(args: argparse.Namespace) -> None:
    """Handle migrate-to-multitenant command (deprecated - multi-tenant removed)."""
    _eprint("\nError: Multi-tenant functionality has been removed from this version.")
    _eprint("The migrate-to-multitenant command is no longer available.")
    _eprint("Please use the standard migrate command for SQLite to SQLite migrations.")
    sys.exit(1)


async def perform_health_check(timeout: float = 5.0) -> dict:
    """
    Perform health check on the backend and return status information.

    Args:
        timeout: Maximum time in seconds to wait for health check (default: 5.0)

    Returns:
        Dictionary containing health check results:
            - status: "healthy" or "unhealthy"
            - connected: bool indicating if backend is connected
            - backend_type: str with backend type (always "sqlite")
            - version: str with backend version if available
            - details: dict with backend-specific details
    """
    from .backends.factory import BackendFactory

    result = {
        "status": "unhealthy",
        "connected": False,
        "backend_type": "unknown",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Create backend with timeout
        backend = await asyncio.wait_for(
            BackendFactory.create_backend(), timeout=timeout
        )

        # Run health check
        health_info = await asyncio.wait_for(backend.health_check(), timeout=timeout)

        result.update(health_info)
        connected = health_info.get("connected", False)
        result["status"] = "healthy" if connected else "unhealthy"
        if not connected and "error" not in result:
            result["error"] = "Backend reports disconnected status"

        await backend.disconnect()

    except asyncio.TimeoutError:
        result["error"] = f"Health check timed out after {timeout} seconds"
        logger.error(f"Health check timeout after {timeout}s")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"Health check failed: {e}", exc_info=True)

    return result


def print_config_summary() -> None:
    """Print current configuration summary to stderr."""
    config = Config.get_config_summary()

    _eprint("\nCurrent Configuration:")
    _eprint(f"  Backend: {config['backend']}")
    _eprint(f"  Tool Profile: {Config.TOOL_PROFILE}")
    _eprint(f"  Enable Advanced Tools: {Config.ENABLE_ADVANCED_TOOLS}")
    _eprint(f"  Log Level: {config['logging']['level']}")
    _eprint(f"\n  SQLite Path: {config['sqlite']['path']}")
    _eprint()

    # Show YAML config sources
    yaml_files = config["config_sources"]["yaml_files"]
    if yaml_files:
        _eprint("YAML Configuration Files:")
        for file in yaml_files:
            _eprint(f"  - {file}")
        _eprint()


def validate_backend(backend: str) -> None:
    """Validate backend choice."""
    valid_backends = ["sqlite", "auto"]
    if backend not in valid_backends:
        _eprint(f"Error: Invalid backend '{backend}'")
        _eprint(f"Valid options: {', '.join(valid_backends)}")
        sys.exit(1)


def validate_profile(profile: str) -> None:
    """Validate tool profile choice."""
    valid_profiles = list(TOOL_PROFILES.keys()) + [
        "lite",
        "standard",
        "full",
    ]  # Include legacy
    if profile not in valid_profiles:
        _eprint(f"Error: Invalid profile '{profile}'")
        _eprint("Valid options: core, extended (or legacy: lite, standard, full)")
        sys.exit(1)

    # Warn about legacy profiles
    legacy_map = {"lite": "core", "standard": "extended", "full": "extended"}
    if profile in legacy_map:
        _eprint(
            f"Warning: Profile '{profile}' is deprecated. Using '{legacy_map[profile]}' instead."
        )
        _eprint(f"   Update your configuration to use: --profile {legacy_map[profile]}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MemoryGraph - MCP memory server for AI coding agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with default settings (SQLite backend, core profile)
  memorygraph

  # Use extended profile (11 tools)
  memorygraph --profile extended

  # Show current configuration
  memorygraph --show-config

  # Run health check
  memorygraph --health

  # Run health check
  memorygraph --health

Environment Variables:
  MEMORY_TOOL_PROFILE    Tool profile (core|extended|advanced) [default: core]
  MEMORY_ENABLE_ADVANCED_TOOLS  Enable advanced tools [default: false]
  MEMORY_SQLITE_PATH     SQLite database path [default: ~/.memorygraph/memory.db]
  MEMORY_LOG_LEVEL       Log level (DEBUG|INFO|WARNING|ERROR) [default: INFO]

  Feature Configuration:
    MEMORY_AUTO_EXTRACT_ENTITIES  Automatically extract entities from memory content [default: true]
    MEMORY_SESSION_BRIEFING       Enable session briefing feature [default: true]
    MEMORY_BRIEFING_VERBOSITY     Briefing verbosity level [default: standard]
    MEMORY_BRIEFING_RECENCY_DAYS  Number of days to consider for briefing [default: 7]
    MEMORY_ALLOW_CYCLES           Allow cycles in relationship graph [default: false]
        """,
    )

    parser.add_argument(
        "--version", action="version", version=f"memorygraph {__version__}"
    )

    parser.add_argument(
        "--backend",
        type=str,
        choices=["sqlite", "auto"],
        help="Database backend to use (overrides MEMORY_BACKEND env var)",
    )

    parser.add_argument(
        "--profile",
        type=str,
        choices=[
            "core",
            "extended",
            "lite",
            "standard",
            "full",
        ],  # Include legacy for compatibility
        help="Tool profile to use: core (default, 9 tools) or extended (11 tools). Legacy profiles lite/standard/full are mapped to core/extended.",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (overrides MEMORY_LOG_LEVEL env var)",
    )

    parser.add_argument(
        "--show-config", action="store_true", help="Show current configuration and exit"
    )

    parser.add_argument(
        "--health", action="store_true", help="Run health check and exit"
    )

    parser.add_argument(
        "--health-json",
        action="store_true",
        help="Output health check as JSON (use with --health)",
    )

    parser.add_argument(
        "--health-timeout",
        type=float,
        default=5.0,
        help="Health check timeout in seconds (default: 5.0)",
    )

    # Export/Import subcommand
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Export command
    export_parser = subparsers.add_parser(
        "export", help="Export memories to file (works with all backends)"
    )
    export_parser.add_argument(
        "--format",
        type=str,
        choices=["json", "markdown"],
        required=True,
        help="Export format (json or markdown)",
    )
    export_parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output path (file for JSON, directory for Markdown)",
    )

    # Import command
    import_parser = subparsers.add_parser(
        "import", help="Import memories from file (works with all backends)"
    )
    import_parser.add_argument(
        "--format",
        type=str,
        choices=["json"],
        required=True,
        help="Import format (currently only JSON supported)",
    )
    import_parser.add_argument(
        "--input", type=str, required=True, help="Input JSON file path"
    )
    import_parser.add_argument(
        "--skip-duplicates",
        action="store_true",
        help="Skip memories with existing IDs instead of overwriting",
    )

    # Migrate command
    migrate_parser = subparsers.add_parser(
        "migrate", help="Migrate memories between backends"
    )
    migrate_parser.add_argument(
        "--from",
        dest="source_backend",
        type=str,
        choices=["sqlite"],
        help="Source backend type (defaults to current MEMORY_BACKEND)",
    )
    migrate_parser.add_argument(
        "--from-path",
        type=str,
        help="Source database path (for sqlite)",
    )
    migrate_parser.add_argument(
        "--from-uri",
        type=str,
        help="Source database URI (not used for SQLite backend)",
    )
    migrate_parser.add_argument(
        "--to",
        dest="target_backend",
        type=str,
        required=True,
        choices=["sqlite"],
        help="Target backend type",
    )
    migrate_parser.add_argument(
        "--to-path",
        type=str,
        help="Target database path (for sqlite)",
    )
    migrate_parser.add_argument(
        "--to-uri",
        type=str,
        help="Target database URI (not used for SQLite backend)",
    )
    migrate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate migration without making changes",
    )
    migrate_parser.add_argument(
        "--verbose", action="store_true", help="Show detailed progress information"
    )
    migrate_parser.add_argument(
        "--skip-duplicates",
        action="store_true",
        default=True,
        help="Skip memories that already exist in target",
    )
    migrate_parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip post-migration verification (faster but less safe)",
    )

    # Migrate to multi-tenant command (deprecated - kept for backward compatibility)
    multitenant_parser = subparsers.add_parser(
        "migrate-to-multitenant",
        help="[DEPRECATED] Multi-tenant functionality has been removed",
    )
    multitenant_parser.add_argument(
        "--tenant-id",
        type=str,
        help="[DEPRECATED] Tenant ID (multi-tenant removed)",
    )
    multitenant_parser.add_argument(
        "--visibility",
        type=str,
        choices=["private", "project", "team", "public"],
        help="[DEPRECATED] Visibility (multi-tenant removed)",
    )
    multitenant_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="[DEPRECATED] Dry run (multi-tenant removed)",
    )
    multitenant_parser.add_argument(
        "--rollback",
        action="store_true",
        help="[DEPRECATED] Rollback (multi-tenant removed)",
    )

    args = parser.parse_args()

    # Apply CLI arguments to environment variables.
    # Config uses _EnvVar descriptors that read os.environ dynamically,
    # so setting env vars is sufficient for the current process.
    if args.backend:
        validate_backend(args.backend)
        os.environ["MEMORY_BACKEND"] = args.backend

    if args.profile:
        validate_profile(args.profile)
        profile = {"lite": "core", "standard": "extended", "full": "extended"}.get(
            args.profile, args.profile
        )
        os.environ["MEMORY_TOOL_PROFILE"] = profile

    if args.log_level:
        os.environ["MEMORY_LOG_LEVEL"] = args.log_level

    # Configure logging to stderr (default) so it doesn't pollute MCP stdout
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    # Handle special commands
    if args.show_config:
        _eprint(f"MemoryGraph MCP Server v{__version__}")
        print_config_summary()
        sys.exit(0)

    if args.health:
        # Perform health check
        result = asyncio.run(perform_health_check(timeout=args.health_timeout))

        # Output in JSON format if requested (stdout is intentional for machine-readable output)
        if args.health_json:
            print(json.dumps(result, indent=2))
        else:
            # Human-readable format goes to stderr
            _eprint(f"MemoryGraph MCP Server v{__version__}")
            _eprint("\nHealth Check Results\n")
            _eprint(
                f"Status: {'Healthy' if result['status'] == 'healthy' else 'Unhealthy'}"
            )
            _eprint(f"Backend: {result.get('backend_type', 'unknown')}")
            _eprint(f"Connected: {'Yes' if result.get('connected') else 'No'}")

            if result.get("version"):
                _eprint(f"Version: {result['version']}")

            if result.get("db_path"):
                _eprint(f"Database: {result['db_path']}")

            if result.get("statistics"):
                stats = result["statistics"]
                _eprint("\nStatistics:")
                if "memory_count" in stats:
                    _eprint(f"  Memories: {stats['memory_count']}")
                for key, value in stats.items():
                    if key != "memory_count":
                        _eprint(f"  {key.replace('_', ' ').title()}: {value}")

            if result.get("database_size_bytes"):
                size_mb = result["database_size_bytes"] / (1024 * 1024)
                _eprint(f"  Database Size: {size_mb:.2f} MB")

            if result.get("error"):
                _eprint(f"\nError: {result['error']}")

            _eprint(f"\nTimestamp: {result['timestamp']}")

        # Exit with appropriate status code
        sys.exit(0 if result["status"] == "healthy" else 1)

    # Handle export/import/migrate commands
    if args.command == "export":
        asyncio.run(handle_export(args))
        sys.exit(0)

    if args.command == "import":
        asyncio.run(handle_import(args))
        sys.exit(0)

    if args.command == "migrate":
        asyncio.run(handle_migrate(args))
        sys.exit(0)

    if args.command == "migrate-to-multitenant":
        _eprint(
            "\nError: Multi-tenant functionality has been removed from this version."
        )
        _eprint("The migrate-to-multitenant command is no longer available.")
        sys.exit(1)

    # Start the server - all diagnostic output to stderr to keep stdout
    # clean for MCP JSON-RPC transport
    _eprint(f"Starting MemoryGraph MCP Server v{__version__}")
    _eprint(f"Backend: {Config.BACKEND}")
    _eprint(f"Profile: {Config.TOOL_PROFILE}")
    _eprint(f"Log Level: {Config.LOG_LEVEL}")
    _eprint("\nPress Ctrl+C to stop the server\n")

    try:
        asyncio.run(server_main())
    except KeyboardInterrupt:
        _eprint("\n\nServer stopped gracefully")
        sys.exit(0)
    except Exception as e:
        _eprint(f"\nServer error: {e}")
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
