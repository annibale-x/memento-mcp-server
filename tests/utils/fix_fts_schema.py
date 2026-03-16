"""
Script to fix FTS schema issue in SQLite database.

This script fixes the 'no such column: T.title' error by:
1. Dropping the corrupted FTS table
2. Recreating it without content='nodes' option
3. Populating it with existing data from nodes table
"""

import asyncio
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_database_path() -> Path:
    """Get the path to the SQLite database."""
    # Default path used by Memento
    default_path = Path.home() / ".mcp-memento" / "context.db"

    # Check if database exists in default location
    if default_path.exists():
        return default_path

    # Check in .data directory (current project)
    project_path = Path(".") / ".data" / "db"
    if project_path.exists():
        return project_path

    # Check in data directory
    data_path = Path(".") / "data" / "context.db"
    if data_path.exists():
        return data_path

    raise FileNotFoundError("Could not find SQLite database file")


def fix_fts_schema_sync(db_path: Path) -> None:
    """
    Fix FTS schema issue synchronously.

    Args:
        db_path: Path to SQLite database file
    """
    logger.info(f"Fixing FTS schema in database: {db_path}")

    # Connect to database
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        # Check if FTS table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='nodes_fts'"
        )
        fts_exists = cursor.fetchone() is not None

        if not fts_exists:
            logger.info("FTS table does not exist, creating it...")
            create_fts_table(conn)
            return

        # Try to query FTS table to check if it's corrupted
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM nodes_fts")
            count = cursor.fetchone()[0]
            logger.info(
                f"FTS table exists with {count} records, checking for corruption..."
            )

            # Try a simple query to check for 'T.title' error
            cursor = conn.execute("SELECT id FROM nodes_fts LIMIT 1")
            cursor.fetchone()
            logger.info("FTS table appears to be working correctly")
            return

        except sqlite3.OperationalError as e:
            if "no such column: T.title" in str(e):
                logger.warning("FTS table is corrupted with 'T.title' error")
                drop_and_recreate_fts(conn)
            else:
                logger.error(f"Unexpected error with FTS table: {e}")
                raise

    except Exception as e:
        logger.error(f"Failed to fix FTS schema: {e}")
        raise
    finally:
        conn.close()


def drop_and_recreate_fts(conn: sqlite3.Connection) -> None:
    """
    Drop corrupted FTS table and recreate it.

    Args:
        conn: SQLite database connection
    """
    logger.info("Dropping corrupted FTS table...")

    # Drop the corrupted FTS table
    conn.execute("DROP TABLE IF EXISTS nodes_fts")
    conn.commit()

    # Create new FTS table WITHOUT content='nodes' option
    logger.info("Creating new FTS table...")
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
            id,
            title,
            content,
            summary
        )
    """)
    conn.commit()

    # Populate FTS table with existing data
    logger.info("Populating FTS table with existing data...")
    populate_fts_table(conn)

    logger.info("FTS table successfully recreated and populated")


def create_fts_table(conn: sqlite3.Connection) -> None:
    """
    Create FTS table without content='nodes' option.

    Args:
        conn: SQLite database connection
    """
    logger.info("Creating FTS table...")

    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
            id,
            title,
            content,
            summary
        )
    """)
    conn.commit()

    # Populate with existing data
    populate_fts_table(conn)

    logger.info("FTS table created and populated")


def populate_fts_table(conn: sqlite3.Connection) -> None:
    """
    Populate FTS table with data from nodes table.

    Args:
        conn: SQLite database connection
    """
    # Get all memory nodes
    cursor = conn.execute("""
        SELECT id, properties
        FROM nodes
        WHERE label = 'Memory'
    """)

    memory_nodes = cursor.fetchall()
    logger.info(f"Found {len(memory_nodes)} memory nodes to index")

    # Insert into FTS table
    inserted_count = 0
    for node in memory_nodes:
        try:
            node_id = node["id"]
            properties = json.loads(node["properties"])

            # Extract fields for FTS
            title = properties.get("title", "")
            content = properties.get("content", "")
            summary = properties.get("summary", "")

            # Insert into FTS table
            conn.execute(
                """
                INSERT INTO nodes_fts (id, title, content, summary)
                VALUES (?, ?, ?, ?)
            """,
                (node_id, title, content, summary),
            )

            inserted_count += 1

        except Exception as e:
            logger.warning(f"Failed to index memory {node['id']}: {e}")

    conn.commit()
    logger.info(f"Inserted {inserted_count} records into FTS table")


def update_database_code() -> None:
    """
    Update the database engine code to prevent future issues.

    This function prints the changes needed in the codebase.
    """
    logger.info("Suggested code changes to prevent FTS issues:")

    print("\n" + "=" * 80)
    print("CHANGES NEEDED IN: memento/database/engine.py")
    print("=" * 80)
    print("\nReplace the FTS table creation code (around line 210-225):")
    print("\nFROM:")
    print("""```
                    CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
                        id,
                        title,
                        content,
                        summary,
                        content='nodes',
                        content_rowid='rowid'
                    )
```""")
    print("\nTO:")
    print("""```
                    CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
                        id,
                        title,
                        content,
                        summary
                    )
```""")

    print("\n" + "=" * 80)
    print("CHANGES NEEDED IN: memento/database/interface.py")
    print("=" * 80)
    print("\nUpdate the store_memory method to ensure FTS is populated:")
    print("\nEnsure the FTS insertion code is always executed when storing memories.")


async def async_fix_fts_schema(db_path: Path) -> None:
    """
    Async version of fix_fts_schema for use with aiosqlite.

    Args:
        db_path: Path to SQLite database file
    """
    import aiosqlite

    logger.info(f"Fixing FTS schema asynchronously in database: {db_path}")

    async with aiosqlite.connect(str(db_path)) as conn:
        conn.row_factory = aiosqlite.Row

        # Check if FTS table exists
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='nodes_fts'"
        ) as cursor:
            fts_exists = await cursor.fetchone() is not None

        if not fts_exists:
            logger.info("FTS table does not exist, creating it...")
            await async_create_fts_table(conn)
            return

        # Try to query FTS table
        try:
            async with conn.execute("SELECT COUNT(*) FROM nodes_fts") as cursor:
                row = await cursor.fetchone()
                count = row[0] if row else 0
                logger.info(f"FTS table exists with {count} records")

            async with conn.execute("SELECT id FROM nodes_fts LIMIT 1") as cursor:
                await cursor.fetchone()
            logger.info("FTS table appears to be working correctly")

        except Exception as e:
            if "no such column: T.title" in str(e):
                logger.warning("FTS table is corrupted with 'T.title' error")
                await async_drop_and_recreate_fts(conn)
            else:
                logger.error(f"Unexpected error with FTS table: {e}")
                raise


async def async_drop_and_recreate_fts(conn) -> None:
    """Async version of drop_and_recreate_fts."""
    logger.info("Dropping corrupted FTS table...")

    await conn.execute("DROP TABLE IF EXISTS nodes_fts")
    await conn.commit()

    logger.info("Creating new FTS table...")
    await conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
            id,
            title,
            content,
            summary
        )
    """)
    await conn.commit()

    await async_populate_fts_table(conn)
    logger.info("FTS table successfully recreated and populated")


async def async_create_fts_table(conn) -> None:
    """Async version of create_fts_table."""
    logger.info("Creating FTS table...")

    await conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
            id,
            title,
            content,
            summary
        )
    """)
    await conn.commit()

    await async_populate_fts_table(conn)
    logger.info("FTS table created and populated")


async def async_populate_fts_table(conn) -> None:
    """Async version of populate_fts_table."""
    async with conn.execute("""
        SELECT id, properties
        FROM nodes
        WHERE label = 'Memory'
    """) as cursor:
        memory_nodes = await cursor.fetchall()

    logger.info(f"Found {len(memory_nodes)} memory nodes to index")

    inserted_count = 0
    for node in memory_nodes:
        try:
            node_id = node["id"]
            properties = json.loads(node["properties"])

            title = properties.get("title", "")
            content = properties.get("content", "")
            summary = properties.get("summary", "")

            await conn.execute(
                """
                INSERT INTO nodes_fts (id, title, content, summary)
                VALUES (?, ?, ?, ?)
            """,
                (node_id, title, content, summary),
            )

            inserted_count += 1

        except Exception as e:
            logger.warning(f"Failed to index memory {node['id']}: {e}")

    await conn.commit()
    logger.info(f"Inserted {inserted_count} records into FTS table")


def main() -> None:
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fix FTS schema issue in SQLite database"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        help="Path to SQLite database file (default: auto-detect)",
    )
    parser.add_argument(
        "--async",
        dest="use_async",
        action="store_true",
        help="Use async version (requires aiosqlite)",
    )
    parser.add_argument(
        "--update-code",
        action="store_true",
        help="Show code changes needed to prevent future issues",
    )

    args = parser.parse_args()

    try:
        if args.update_code:
            update_database_code()
            return

        # Get database path
        if args.db_path:
            db_path = Path(args.db_path)
        else:
            db_path = get_database_path()

        logger.info(f"Using database: {db_path}")

        if args.use_async:
            # Run async version
            asyncio.run(async_fix_fts_schema(db_path))
        else:
            # Run sync version
            fix_fts_schema_sync(db_path)

        logger.info("FTS schema fix completed successfully!")

        # Test the fix
        logger.info("Testing FTS table...")
        conn = sqlite3.connect(str(db_path))
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM nodes_fts")
            count = cursor.fetchone()[0]
            logger.info(f"FTS table now has {count} records")

            cursor = conn.execute("SELECT id, title FROM nodes_fts LIMIT 3")
            rows = cursor.fetchall()
            logger.info("Sample FTS records:")
            for row in rows:
                logger.info(f"  - {row[0]}: {row[1]}")

        finally:
            conn.close()

    except FileNotFoundError as e:
        logger.error(f"Database not found: {e}")
        logger.info("Please specify the database path with --db-path")
        exit(1)
    except Exception as e:
        logger.error(f"Failed to fix FTS schema: {e}")
        exit(1)


if __name__ == "__main__":
    main()
