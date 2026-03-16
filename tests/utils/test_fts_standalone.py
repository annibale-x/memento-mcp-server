"""
Test script for FTS functionality in Context Keeper database.

This script tests the full-text search functionality after fixing the schema issue.
"""

import asyncio
import json
import sqlite3
from pathlib import Path


def test_fts_directly(db_path: Path) -> None:
    """Test FTS functionality directly using SQLite."""
    print(f"Testing FTS in database: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        # Check if FTS table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='nodes_fts'"
        )
        if not cursor.fetchone():
            print("ERROR: FTS table does not exist")
            return

        # Test basic query
        print("\n1. Testing basic SELECT from FTS table:")
        cursor = conn.execute("SELECT COUNT(*) as count FROM nodes_fts")
        row = cursor.fetchone()
        print(f"   FTS table has {row['count']} records")

        # Test selecting specific columns
        print("\n2. Testing column selection:")
        cursor = conn.execute("SELECT id, title FROM nodes_fts LIMIT 3")
        rows = cursor.fetchall()
        for i, row in enumerate(rows, 1):
            print(f"   {i}. ID: {row['id']}, Title: {row['title']}")

        # Test FTS search
        print("\n3. Testing FTS search:")

        # Search for "hannibal"
        cursor = conn.execute("""
            SELECT id, title
            FROM nodes_fts
            WHERE nodes_fts MATCH 'hannibal*'
            ORDER BY rank
            LIMIT 5
        """)
        rows = cursor.fetchall()
        print(f"   Found {len(rows)} records matching 'hannibal*':")
        for i, row in enumerate(rows, 1):
            print(f"   {i}. ID: {row['id']}, Title: {row['title']}")

        # Test JOIN with nodes table
        print("\n4. Testing JOIN with nodes table:")
        cursor = conn.execute("""
            SELECT n.id, n.label, fts.title
            FROM nodes n
            JOIN nodes_fts fts ON n.id = fts.id
            WHERE n.label = 'Memory'
            LIMIT 3
        """)
        rows = cursor.fetchall()
        print(f"   Found {len(rows)} memory nodes with FTS data:")
        for i, row in enumerate(rows, 1):
            print(
                f"   {i}. ID: {row['id']}, Label: {row['label']}, Title: {row['title']}"
            )

        # Test FTS with snippet
        print("\n5. Testing FTS snippet (advanced feature):")
        try:
            cursor = conn.execute("""
                SELECT snippet(nodes_fts, 0, '<b>', '</b>', '...', 10) as snippet
                FROM nodes_fts
                WHERE nodes_fts MATCH 'hannibal'
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row and row["snippet"]:
                print(f"   Snippet: {row['snippet']}")
            else:
                print("   No snippet available")
        except Exception as e:
            print(f"   Snippet not supported: {e}")

        print("\n✅ All FTS tests passed!")

    except Exception as e:
        print(f"\n❌ FTS test failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        conn.close()


async def test_fts_with_backend(db_path: Path) -> None:
    """Test FTS using the actual backend code."""
    print(f"\n\nTesting FTS with backend code: {db_path}")

    try:
        from memento.database.engine import SQLiteBackend
        from memento.database.interface import SQLiteMemoryDatabase

        # Create backend
        backend = SQLiteBackend(str(db_path))
        await backend.connect()

        print(f"1. Backend supports FTS: {backend.supports_fulltext_search()}")

        # Create memory database
        memory_db = SQLiteMemoryDatabase(backend)

        # Test search with query
        from memento.models import MemoryType, SearchQuery

        print("\n2. Testing search_memories with FTS:")

        # Search for "hannibal"
        search_query = SearchQuery(query="hannibal", limit=5)

        try:
            result = await memory_db.search_memories(search_query)
            print(f"   Found {len(result.results)} memories")
            for i, memory in enumerate(result.results, 1):
                print(f"   {i}. {memory.title} (Type: {memory.type.value})")
        except Exception as e:
            print(f"   Search failed: {e}")
            import traceback

            traceback.print_exc()

        await backend.disconnect()

    except ImportError as e:
        print(f"   Could not import backend modules: {e}")
    except Exception as e:
        print(f"   Backend test failed: {e}")
        import traceback

        traceback.print_exc()


def check_database_schema(db_path: Path) -> None:
    """Check the database schema for potential issues."""
    print(f"\n\nChecking database schema: {db_path}")

    conn = sqlite3.connect(str(db_path))

    try:
        # Get FTS table schema
        cursor = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='nodes_fts'"
        )
        row = cursor.fetchone()
        if row:
            print("FTS table schema:")
            print(row["sql"])

            # Check for problematic options
            sql = row["sql"].lower()
            if "content='nodes'" in sql:
                print("⚠️  WARNING: FTS table uses content='nodes' option")
            if "content_rowid='rowid'" in sql:
                print("⚠️  WARNING: FTS table uses content_rowid='rowid' option")

        # Check nodes table schema
        cursor = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='nodes'"
        )
        row = cursor.fetchone()
        if row:
            print("\nNodes table schema:")
            print(row["sql"])

            # Check if nodes table has rowid
            sql = row["sql"].lower()
            if "without rowid" in sql:
                print("⚠️  WARNING: nodes table created WITHOUT ROWID")

        # Check data consistency
        print("\nData consistency check:")

        # Count memories in nodes table
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM nodes WHERE label = 'Memory'"
        )
        nodes_count = cursor.fetchone()["count"]
        print(f"   Memories in nodes table: {nodes_count}")

        # Count memories in FTS table
        try:
            cursor = conn.execute("SELECT COUNT(*) as count FROM nodes_fts")
            fts_count = cursor.fetchone()["count"]
            print(f"   Memories in FTS table: {fts_count}")

            if nodes_count != fts_count:
                print(
                    f"⚠️  WARNING: Data mismatch! {nodes_count} nodes vs {fts_count} FTS records"
                )
        except Exception as e:
            print(f"   Could not count FTS records: {e}")

    finally:
        conn.close()


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test FTS functionality")
    parser.add_argument(
        "--db-path",
        type=str,
        default=".data/db",
        help="Path to SQLite database file (default: .data/db)",
    )
    parser.add_argument(
        "--all", action="store_true", help="Run all tests including backend tests"
    )

    args = parser.parse_args()

    db_path = Path(args.db_path)

    if not db_path.exists():
        print(f"ERROR: Database file not found: {db_path}")
        return

    print("=" * 80)
    print("FTS FUNCTIONALITY TEST")
    print("=" * 80)

    # Run direct SQLite tests
    test_fts_directly(db_path)

    # Check schema
    check_database_schema(db_path)

    # Run backend tests if requested
    if args.all:
        asyncio.run(test_fts_with_backend(db_path))

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
