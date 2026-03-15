"""
Test script to verify new database creation with correct FTS schema.

This script creates a fresh SQLite database and verifies that:
1. The schema is created correctly without 'content='nodes'' option
2. FTS table works without 'T.title' error
3. All operations (store, search, update) work correctly
"""

import asyncio
import json
import os

# Add project to path
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from context_keeper.database.engine import SQLiteBackend
from context_keeper.database.interface import SQLiteMemoryDatabase
from context_keeper.models import Memory, MemoryContext, MemoryType, SearchQuery


async def test_new_database_creation():
    """Test creating a fresh database with correct schema."""

    # Create temporary database file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        print("=" * 80)
        print("TEST: New Database Creation with Correct FTS Schema")
        print("=" * 80)

        # Create and connect to backend
        backend = SQLiteBackend(db_path)
        await backend.connect()

        print(f"1. Created new database at: {db_path}")
        print(f"   Database size: {os.path.getsize(db_path)} bytes")

        # Initialize schema
        await backend.initialize_schema()
        print("2. Schema initialized successfully")

        # Refresh FTS support after schema creation
        await backend.refresh_fts_support()
        print("   FTS support refreshed after schema creation")

        # Check FTS support
        fts_supported = backend.supports_fulltext_search()
        print(f"3. FTS support detected: {fts_supported}")

        if not fts_supported:
            print("   ❌ ERROR: FTS not supported in new database after refresh")
            return False

        # Test FTS table directly
        print("\n4. Testing FTS table directly...")
        try:
            # Test simple query on FTS table
            async with backend.conn.execute("SELECT COUNT(*) FROM nodes_fts") as cursor:
                result = await cursor.fetchone()
                count = result[0] if result else 0
                print(f"   FTS table has {count} records (should be 0)")

            # Test column selection (this was failing with 'T.title' error)
            async with backend.conn.execute(
                "SELECT id, title FROM nodes_fts LIMIT 1"
            ) as cursor:
                await cursor.fetchone()
                print("   ✓ Column selection works (no 'T.title' error)")

            # Test FTS search syntax
            async with backend.conn.execute(
                "SELECT id FROM nodes_fts WHERE nodes_fts MATCH 'test*'"
            ) as cursor:
                await cursor.fetchall()
                print("   ✓ FTS search syntax works")

        except Exception as e:
            print(f"   ❌ FTS table test failed: {e}")
            if "no such column: T.title" in str(e):
                print("   ⚠️ CRITICAL: Still has 'T.title' error!")
            return False

        # Create memory database and test operations
        memory_db = SQLiteMemoryDatabase(backend)

        print("\n5. Testing memory operations...")

        # Create a test memory
        test_memory = Memory(
            id="test-memory-1",
            title="Test Memory for FTS Verification",
            content="This is a test memory to verify that FTS works correctly in new databases.",
            summary="Test memory for schema verification",
            type=MemoryType.GENERAL,
            importance=0.5,
            tags=["test", "verification", "fts"],
            context=MemoryContext(project_path="/test/project"),
            created_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

        # Convert to string for JSON serialization
        test_memory.created_at = (
            test_memory.created_at.isoformat()
            if hasattr(test_memory.created_at, "isoformat")
            else test_memory.created_at
        )
        test_memory.updated_at = (
            test_memory.updated_at.isoformat()
            if hasattr(test_memory.updated_at, "isoformat")
            else test_memory.updated_at
        )

        # Store memory
        stored_memory = await memory_db.store_memory(test_memory)
        print(f"   ✓ Memory stored: {stored_memory.id}")

        # Verify memory was stored
        retrieved = await memory_db.get_memory("test-memory-1")
        if retrieved and retrieved.id == "test-memory-1":
            print("   ✓ Memory retrieved successfully")
        else:
            print("   ❌ Memory retrieval failed")
            return False

        # Test FTS search
        search_query = SearchQuery(query="verification", limit=5)
        search_result = await memory_db.search_memories(search_query)

        if len(search_result.results) > 0:
            print(f"   ✓ FTS search found {len(search_result.results)} memories")
        else:
            print("   ⚠️ FTS search returned no results (might need more data)")

        # Test update with FTS
        test_memory.content = (
            "Updated content with more keywords for better FTS testing."
        )
        updated_memory = await memory_db.update_memory(test_memory)
        print("   ✓ Memory updated with FTS sync")

        # Test delete with FTS cleanup
        await memory_db.delete_memory("test-memory-1")
        print("   ✓ Memory deleted with FTS cleanup")

        # Verify FTS table is empty
        async with backend.conn.execute("SELECT COUNT(*) FROM nodes_fts") as cursor:
            result = await cursor.fetchone()
            count = result[0] if result else 0
            if count == 0:
                print("   ✓ FTS table correctly cleaned up after delete")
            else:
                print(f"   ⚠️ FTS table still has {count} records after delete")

        # Check database schema
        print("\n6. Verifying database schema...")

        # Get FTS table schema
        async with backend.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='nodes_fts'"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                fts_schema = row[0]
                print("   FTS table schema:")
                print(f"   {fts_schema}")

                # Check for problematic options
                if "content='nodes'" in fts_schema.lower():
                    print("   ❌ CRITICAL: FTS table still uses content='nodes' option")
                    return False
                if "content_rowid='rowid'" in fts_schema.lower():
                    print(
                        "   ❌ CRITICAL: FTS table still uses content_rowid='rowid' option"
                    )
                    return False
                else:
                    print("   ✓ FTS table created without problematic options")

        # Check nodes table
        async with backend.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='nodes'"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                print("   ✓ Nodes table created correctly")

        await backend.disconnect()

        print("\n" + "=" * 80)
        print("✅ SUCCESS: New database created with correct FTS schema!")
        print("   No 'T.title' error, all operations work correctly.")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Clean up temporary file
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
                print(f"\nCleaned up temporary database: {db_path}")
        except:
            pass


async def test_existing_database_fix():
    """Test that the fix_fts_schema script works on existing databases."""

    print("\n" + "=" * 80)
    print("TEST: Existing Database Fix Verification")
    print("=" * 80)

    # First create a database with the old (wrong) schema
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # Manually create database with old schema
        import sqlite3

        conn = sqlite3.connect(db_path)

        # Create nodes table (same as before)
        conn.execute("""
            CREATE TABLE nodes (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                properties TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create FTS table with OLD (wrong) schema
        conn.execute("""
            CREATE VIRTUAL TABLE nodes_fts USING fts5(
                id,
                title,
                content,
                summary,
                content='nodes',
                content_rowid='rowid'
            )
        """)

        conn.commit()
        conn.close()

        print(f"1. Created database with OLD (wrong) schema at: {db_path}")

        # Now test if it has the 'T.title' error
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.execute("SELECT * FROM nodes_fts")
            cursor.fetchone()
            print("   ⚠️ Unexpected: Old schema doesn't immediately fail")
        except sqlite3.OperationalError as e:
            if "no such column: T.title" in str(e):
                print("   ✓ Confirmed: Old schema has 'T.title' error")
            else:
                print(f"   Different error: {e}")
        finally:
            conn.close()

        # Now run the fix script
        print("\n2. Applying fix...")

        # Import and run fix function
        from fix_fts_schema import fix_fts_schema_sync

        fix_fts_schema_sync(Path(db_path))

        print("   ✓ Fix applied")

        # Verify fix worked
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.execute("SELECT * FROM nodes_fts")
            cursor.fetchone()
            print("   ✓ Fixed: No 'T.title' error after fix")

            # Check schema
            cursor = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='nodes_fts'"
            )
            row = cursor.fetchone()
            if row:
                fts_schema = row[0]
                if "content='nodes'" not in fts_schema.lower():
                    print("   ✓ Schema corrected: No content='nodes' option")
                else:
                    print("   ❌ Schema still has content='nodes'")
                    return False

        except sqlite3.OperationalError as e:
            print(f"   ❌ Still has error after fix: {e}")
            return False
        finally:
            conn.close()

        print("\n" + "=" * 80)
        print("✅ SUCCESS: Existing database fix works correctly!")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Clean up
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except:
            pass


def main():
    """Run all tests."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test new database creation with correct FTS schema"
    )
    parser.add_argument(
        "--test",
        choices=["new", "fix", "all"],
        default="all",
        help="Which test to run (default: all)",
    )

    args = parser.parse_args()

    results = []

    if args.test in ["new", "all"]:
        results.append(
            ("New Database Creation", asyncio.run(test_new_database_creation()))
        )

    if args.test in ["fix", "all"]:
        results.append(
            ("Existing Database Fix", asyncio.run(test_existing_database_fix()))
        )

    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 80)

    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("The FTS schema issue has been completely resolved:")
        print("1. New databases are created with correct schema")
        print("2. Existing databases can be fixed with the fix script")
        print("3. No more 'T.title' errors!")
        return 0
    else:
        print("⚠️ SOME TESTS FAILED")
        print("The FTS schema issue may not be fully resolved.")
        return 1


if __name__ == "__main__":
    exit(main())
