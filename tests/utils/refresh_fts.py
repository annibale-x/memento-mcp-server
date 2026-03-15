"""
Script to refresh FTS support in the Context Keeper database.

This script forces the SQLite backend to refresh its FTS support detection
after fixing the FTS schema issue.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def refresh_fts_support(db_path: Path) -> bool:
    """
    Refresh FTS support in the database.

    Args:
        db_path: Path to SQLite database file

    Returns:
        True if FTS support was successfully refreshed
    """
    try:
        from context_keeper.database.engine import SQLiteBackend

        logger.info(f"Refreshing FTS support for database: {db_path}")

        # Create and connect to backend
        backend = SQLiteBackend(str(db_path))
        await backend.connect()

        # Get current FTS support status
        old_status = backend.supports_fulltext_search()
        logger.info(f"Current FTS support status: {old_status}")

        # Refresh FTS support
        await backend.refresh_fts_support()

        # Get new FTS support status
        new_status = backend.supports_fulltext_search()
        logger.info(f"New FTS support status: {new_status}")

        # Test FTS functionality
        if new_status:
            logger.info("Testing FTS functionality...")
            try:
                # Simple test query
                async with backend.conn.execute(
                    "SELECT COUNT(*) FROM nodes_fts"
                ) as cursor:
                    result = await cursor.fetchone()
                    count = result[0] if result else 0
                    logger.info(f"FTS table contains {count} records")

                # Test search query
                async with backend.conn.execute(
                    "SELECT id, title FROM nodes_fts LIMIT 3"
                ) as cursor:
                    rows = await cursor.fetchall()
                    if rows:
                        logger.info("Sample FTS records:")
                        for row in rows:
                            logger.info(f"  - {row['id']}: {row['title']}")
                    else:
                        logger.info("FTS table is empty")

            except Exception as e:
                logger.warning(f"FTS test query failed: {e}")
                new_status = False

        # Clean up
        await backend.disconnect()

        if new_status and not old_status:
            logger.info("✅ Successfully enabled FTS support")
        elif new_status and old_status:
            logger.info("✅ FTS support was already enabled")
        elif not new_status and old_status:
            logger.warning("⚠️ FTS support was disabled")
        else:
            logger.warning("⚠️ FTS support is not available")

        return new_status

    except ImportError as e:
        logger.error(f"Failed to import backend modules: {e}")
        logger.info("Make sure you're running from the project root directory")
        return False
    except Exception as e:
        logger.error(f"Failed to refresh FTS support: {e}")
        return False


async def test_search_functionality(db_path: Path) -> bool:
    """
    Test search functionality after refreshing FTS support.

    Args:
        db_path: Path to SQLite database file

    Returns:
        True if search functionality works correctly
    """
    try:
        from context_keeper.database.engine import SQLiteBackend
        from context_keeper.database.interface import SQLiteMemoryDatabase
        from context_keeper.models import SearchQuery

        logger.info("Testing search functionality...")

        # Create backend and database
        backend = SQLiteBackend(str(db_path))
        await backend.connect()
        memory_db = SQLiteMemoryDatabase(backend)

        # Test 1: Search with query
        logger.info("Test 1: Search with query 'hannibal'")
        search_query = SearchQuery(query="hannibal", limit=5)

        try:
            result = await memory_db.search_memories(search_query)
            logger.info(f"Found {len(result.results)} memories")
            for i, memory in enumerate(result.results, 1):
                logger.info(f"  {i}. {memory.title} (ID: {memory.id})")

            if len(result.results) > 0:
                logger.info("✅ Search with query successful")
            else:
                logger.warning("⚠️ Search returned no results (might be expected)")

        except Exception as e:
            logger.error(f"❌ Search with query failed: {e}")
            await backend.disconnect()
            return False

        # Test 2: Search with tags
        logger.info("\nTest 2: Search with tags ['hannibal']")
        search_query = SearchQuery(tags=["hannibal"], limit=5)

        try:
            result = await memory_db.search_memories(search_query)
            logger.info(f"Found {len(result.results)} memories with tag 'hannibal'")
            for i, memory in enumerate(result.results, 1):
                logger.info(f"  {i}. {memory.title} (Tags: {memory.tags})")

            if len(result.results) > 0:
                logger.info("✅ Search with tags successful")
            else:
                logger.warning("⚠️ Search with tags returned no results")

        except Exception as e:
            logger.error(f"❌ Search with tags failed: {e}")
            await backend.disconnect()
            return False

        # Test 3: Simple search (no FTS)
        logger.info("\nTest 3: Simple search (no query)")
        search_query = SearchQuery(limit=5)

        try:
            result = await memory_db.search_memories(search_query)
            logger.info(f"Found {len(result.results)} memories total")
            logger.info("✅ Simple search successful")

        except Exception as e:
            logger.error(f"❌ Simple search failed: {e}")
            await backend.disconnect()
            return False

        await backend.disconnect()
        logger.info("\n✅ All search tests passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Search functionality test failed: {e}")
        return False


def get_database_path() -> Path:
    """Get the path to the SQLite database."""
    # Check in .data directory (current project)
    project_path = Path(".") / ".data" / "db"
    if project_path.exists():
        return project_path

    # Default path used by Context Keeper
    default_path = Path.home() / ".mcp-context-keeper" / "context.db"
    if default_path.exists():
        return default_path

    # Check in data directory
    data_path = Path(".") / "data" / "context.db"
    if data_path.exists():
        return data_path

    raise FileNotFoundError("Could not find SQLite database file")


async def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Refresh FTS support in Context Keeper database"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        help="Path to SQLite database file (default: auto-detect)",
    )
    parser.add_argument(
        "--test-search",
        action="store_true",
        help="Test search functionality after refreshing FTS",
    )
    parser.add_argument(
        "--skip-refresh",
        action="store_true",
        help="Skip FTS refresh and only run tests",
    )

    args = parser.parse_args()

    try:
        # Get database path
        if args.db_path:
            db_path = Path(args.db_path)
        else:
            db_path = get_database_path()

        logger.info(f"Using database: {db_path}")

        # Refresh FTS support if not skipped
        fts_enabled = False
        if not args.skip_refresh:
            fts_enabled = await refresh_fts_support(db_path)
        else:
            logger.info("Skipping FTS refresh as requested")
            fts_enabled = True  # Assume it's enabled for testing

        # Test search functionality if requested
        if args.test_search and fts_enabled:
            search_ok = await test_search_functionality(db_path)
            if not search_ok:
                logger.error("❌ Search functionality tests failed")
                sys.exit(1)

        logger.info("\n" + "=" * 60)
        if fts_enabled:
            logger.info("✅ FTS support is ENABLED and ready for use")
            logger.info("Note: You may need to restart the MCP server or client")
            logger.info("for the changes to take effect.")
        else:
            logger.info("❌ FTS support is NOT available")
            logger.info("Check the logs above for details on what went wrong.")
        logger.info("=" * 60)

    except FileNotFoundError as e:
        logger.error(f"Database not found: {e}")
        logger.info("Please specify the database path with --db-path")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
