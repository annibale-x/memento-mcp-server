"""
Pytest integration tests for FTS (Full-Text Search) functionality.

This module provides comprehensive testing of FTS features in the
MCP Context Keeper database, including schema creation, search operations,
and error handling.
"""

import asyncio
import json
import os
import sqlite3

# Add parent directory to path to import memento
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from memento.database.engine import SQLiteBackend
from memento.database.interface import SQLiteMemoryDatabase
from memento.models import Memory, MemoryContext, MemoryType, SearchQuery


# Test fixtures
@pytest.fixture
def temp_db_path():
    """Create a temporary SQLite database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
async def backend_with_fts(temp_db_path):
    """Create a SQLite backend with FTS support enabled."""
    backend = SQLiteBackend(temp_db_path)
    await backend.connect()
    await backend.initialize_schema()

    # Refresh FTS support to ensure it's enabled
    await backend.refresh_fts_support()

    yield backend

    await backend.disconnect()


@pytest.fixture
async def memory_db_with_fts(backend_with_fts):
    """Create a memory database with FTS support."""
    return SQLiteMemoryDatabase(backend_with_fts)


@pytest.fixture
def sample_memories():
    """Provide sample memories for FTS testing."""
    base_time = datetime.now(timezone.utc)

    return [
        Memory(
            id=f"test-memory-{i}",
            title=f"Test Memory {i}",
            content=f"This is test memory {i} with specific keywords for FTS testing.",
            summary=f"Summary for memory {i}",
            type=MemoryType.GENERAL,
            importance=0.5 + (i * 0.1),
            tags=["test", "fts", f"category-{i % 3}"],
            context=None,
            created_at=base_time,
            updated_at=base_time,
        )
        for i in range(1, 6)
    ]


@pytest.fixture
def sample_memory_with_keywords():
    """Provide a memory with specific keywords for FTS testing."""
    base_time = datetime.now(timezone.utc)

    return Memory(
        id="keyword-memory-1",
        title="Authentication Implementation",
        content="Implemented JWT token validation with proper error handling and security measures.",
        summary="JWT authentication solution",
        type=MemoryType.SOLUTION,
        importance=0.8,
        tags=["authentication", "jwt", "security", "api"],
        context=None,
        created_at=base_time,
        updated_at=base_time,
    )


# Test classes
class TestFTSSchemaCreation:
    """Test FTS schema creation and detection."""

    @pytest.mark.asyncio
    async def test_fts_support_detection(self, backend_with_fts):
        """Test that FTS support is properly detected."""
        fts_supported = backend_with_fts.supports_fulltext_search()
        assert fts_supported is True, "FTS support should be enabled"

    @pytest.mark.asyncio
    async def test_fts_table_creation(self, temp_db_path):
        """Test that FTS table is created with correct schema."""
        backend = SQLiteBackend(temp_db_path)
        await backend.connect()
        await backend.initialize_schema()

        # Check FTS table exists
        async with backend.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='nodes_fts'"
        ) as cursor:
            result = await cursor.fetchone()
            assert result is not None, "FTS table should exist"

        # Check FTS table schema doesn't have problematic options
        async with backend.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='nodes_fts'"
        ) as cursor:
            result = await cursor.fetchone()
            fts_schema = result[0]

            # Should NOT contain problematic options
            assert "content='nodes'" not in fts_schema.lower(), (
                "FTS table should not use content='nodes' option"
            )
            assert "content_rowid='rowid'" not in fts_schema.lower(), (
                "FTS table should not use content_rowid='rowid' option"
            )

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_fts_table_columns(self, backend_with_fts):
        """Test that FTS table has correct columns."""
        # Test selecting from FTS table (this would fail with 'T.title' error)
        async with backend_with_fts.conn.execute(
            "SELECT id, title, content, summary FROM nodes_fts LIMIT 1"
        ) as cursor:
            # Should not raise 'no such column: T.title' error
            await cursor.fetchone()

        # Verify column names
        async with backend_with_fts.conn.execute(
            "PRAGMA table_info(nodes_fts)"
        ) as cursor:
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]

            expected_columns = ["id", "title", "content", "summary"]
            for col in expected_columns:
                assert col in column_names, f"FTS table should have '{col}' column"


class TestFTSMemoryOperations:
    """Test memory operations with FTS integration."""

    @pytest.mark.asyncio
    async def test_store_memory_with_fts(
        self, memory_db_with_fts, sample_memory_with_keywords
    ):
        """Test storing a memory with FTS indexing."""
        # Store memory
        stored_memory = await memory_db_with_fts.store_memory(
            sample_memory_with_keywords
        )
        assert stored_memory.id == sample_memory_with_keywords.id

        # Verify memory was stored
        retrieved = await memory_db_with_fts.get_memory(sample_memory_with_keywords.id)
        assert retrieved is not None
        assert retrieved.id == sample_memory_with_keywords.id

        # Verify FTS table has the memory
        backend = memory_db_with_fts.backend
        async with backend.conn.execute(
            "SELECT id, title FROM nodes_fts WHERE id = ?",
            (sample_memory_with_keywords.id,),
        ) as cursor:
            result = await cursor.fetchone()
            assert result is not None, "Memory should be in FTS table"
            assert result["title"] == sample_memory_with_keywords.title

    @pytest.mark.asyncio
    async def test_update_memory_with_fts(
        self, memory_db_with_fts, sample_memory_with_keywords
    ):
        """Test updating a memory with FTS sync."""
        # Store initial memory
        await memory_db_with_fts.store_memory(sample_memory_with_keywords)

        # Update memory content
        updated_memory = sample_memory_with_keywords.model_copy()
        updated_memory.content = (
            "Updated content with new keywords for better search results."
        )
        updated_memory.title = "Updated Authentication Implementation"

        # Update memory
        result = await memory_db_with_fts.update_memory(updated_memory)
        assert result.id == updated_memory.id

        # Verify FTS table is updated
        backend = memory_db_with_fts.backend
        async with backend.conn.execute(
            "SELECT content FROM nodes_fts WHERE id = ?", (updated_memory.id,)
        ) as cursor:
            result = await cursor.fetchone()
            assert result is not None
            # FTS table should have updated content

    @pytest.mark.asyncio
    async def test_delete_memory_with_fts(
        self, memory_db_with_fts, sample_memory_with_keywords
    ):
        """Test deleting a memory with FTS cleanup."""
        # Store memory
        await memory_db_with_fts.store_memory(sample_memory_with_keywords)

        # Verify it's in FTS table
        backend = memory_db_with_fts.backend
        async with backend.conn.execute(
            "SELECT COUNT(*) as count FROM nodes_fts WHERE id = ?",
            (sample_memory_with_keywords.id,),
        ) as cursor:
            result = await cursor.fetchone()
            assert result["count"] == 1, "Memory should be in FTS table before delete"

        # Delete memory
        await memory_db_with_fts.delete_memory(sample_memory_with_keywords.id)

        # Verify it's removed from FTS table
        async with backend.conn.execute(
            "SELECT COUNT(*) as count FROM nodes_fts WHERE id = ?",
            (sample_memory_with_keywords.id,),
        ) as cursor:
            result = await cursor.fetchone()
            assert result["count"] == 0, (
                "Memory should be removed from FTS table after delete"
            )


class TestFTSSearchOperations:
    """Test FTS search operations."""

    @pytest.mark.asyncio
    async def test_fts_search_with_query(self, memory_db_with_fts, sample_memories):
        """Test FTS search with text query."""
        # Store multiple memories
        for memory in sample_memories:
            await memory_db_with_fts.store_memory(memory)

        # Search for specific keyword
        search_query = SearchQuery(query="keywords", limit=10)
        result = await memory_db_with_fts.search_memories(search_query)

        # Should find memories containing "keywords" in content
        assert len(result.results) > 0, "Should find memories with 'keywords'"

        # Verify search results contain the query term
        for memory in result.results:
            assert (
                "keywords" in memory.content.lower()
                or "keywords" in memory.title.lower()
            )

    @pytest.mark.asyncio
    async def test_fts_search_with_title(self, memory_db_with_fts, sample_memories):
        """Test FTS search targeting title field."""
        # Store memories
        for memory in sample_memories:
            await memory_db_with_fts.store_memory(memory)

        # Search for "Memory 3" in title
        search_query = SearchQuery(query="Memory 3", limit=10)
        result = await memory_db_with_fts.search_memories(search_query)

        # Should find memory with title "Test Memory 3"
        assert len(result.results) >= 1, "Should find memory with 'Memory 3' in title"

        found = False
        for memory in result.results:
            if "3" in memory.title:
                found = True
                break
        assert found, "Should have found memory with '3' in title"

    @pytest.mark.asyncio
    async def test_fts_search_with_wildcard(
        self, memory_db_with_fts, sample_memory_with_keywords
    ):
        """Test FTS search with wildcard matching."""
        # Store memory with specific keywords
        await memory_db_with_fts.store_memory(sample_memory_with_keywords)

        # Search with wildcard (partial word)
        search_query = SearchQuery(query="authent*", limit=10)
        result = await memory_db_with_fts.search_memories(search_query)

        # Should find memory with "authentication"
        assert len(result.results) >= 1, "Should find memory with 'authent*' wildcard"

        # Search with another wildcard
        search_query = SearchQuery(query="valid*", limit=10)
        result = await memory_db_with_fts.search_memories(search_query)

        # Should find memory with "validation"
        assert len(result.results) >= 1, "Should find memory with 'valid*' wildcard"

    @pytest.mark.asyncio
    async def test_fts_search_combined_with_tags(
        self, memory_db_with_fts, sample_memory_with_keywords
    ):
        """Test FTS search combined with tag filtering."""
        # Store memory
        await memory_db_with_fts.store_memory(sample_memory_with_keywords)

        # Search with query AND tags
        search_query = SearchQuery(
            query="authentication", tags=["security", "api"], limit=10
        )
        result = await memory_db_with_fts.search_memories(search_query)

        # Should find the memory
        assert len(result.results) >= 1, "Should find memory with query and tags"

        # Verify tags match
        memory = result.results[0]
        assert "security" in memory.tags
        assert "api" in memory.tags

    @pytest.mark.asyncio
    async def test_fts_search_empty_query(self, memory_db_with_fts, sample_memories):
        """Test search with empty query (should return all memories)."""
        # Store multiple memories
        for memory in sample_memories:
            await memory_db_with_fts.store_memory(memory)

        # Search with empty query
        search_query = SearchQuery(limit=10)
        result = await memory_db_with_fts.search_memories(search_query)

        # Should return all stored memories
        assert len(result.results) == len(sample_memories), (
            f"Should return all {len(sample_memories)} memories"
        )

    @pytest.mark.asyncio
    async def test_fts_search_limit(self, memory_db_with_fts, sample_memories):
        """Test FTS search with limit parameter."""
        # Store multiple memories
        for memory in sample_memories:
            await memory_db_with_fts.store_memory(memory)

        # Search with limit 2
        search_query = SearchQuery(query="test", limit=2)
        result = await memory_db_with_fts.search_memories(search_query)

        # Should respect limit
        assert len(result.results) <= 2, "Should respect limit parameter"

        # Search with limit 1
        search_query = SearchQuery(query="test", limit=1)
        result = await memory_db_with_fts.search_memories(search_query)

        assert len(result.results) <= 1, "Should respect limit parameter"


class TestFTSErrorHandling:
    """Test FTS error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_fts_search_no_results(self, memory_db_with_fts):
        """Test FTS search when no results match."""
        # Search for non-existent term
        search_query = SearchQuery(query="nonexistenttermxyz", limit=10)
        result = await memory_db_with_fts.search_memories(search_query)

        # Should return empty results, not raise error
        assert len(result.results) == 0, "Should return empty results for no matches"

    @pytest.mark.asyncio
    async def test_fts_with_special_characters(self, memory_db_with_fts):
        """Test FTS search with special characters."""
        # Create memory with special characters
        memory = Memory(
            id="special-chars-memory",
            title="Memory with Special Chars: test@example.com",
            content="Email: test@example.com, URL: https://example.com/path?query=test",
            summary="Test with special characters",
            type=MemoryType.GENERAL,
            importance=0.5,
            tags=["test", "special"],
            context=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        await memory_db_with_fts.store_memory(memory)

        # Search for part of special content
        search_query = SearchQuery(query="example.com", limit=10)
        result = await memory_db_with_fts.search_memories(search_query)

        # Should handle special characters gracefully
        assert len(result.results) >= 1, "Should handle special characters in search"

    @pytest.mark.asyncio
    async def test_fts_case_insensitive(
        self, memory_db_with_fts, sample_memory_with_keywords
    ):
        """Test that FTS search is case-insensitive."""
        await memory_db_with_fts.store_memory(sample_memory_with_keywords)

        # Search with different cases
        test_cases = [
            "AUTHENTICATION",  # All caps
            "Authentication",  # Title case
            "authentication",  # Lower case
            "AuThEnTiCaTiOn",  # Mixed case
        ]

        for query in test_cases:
            search_query = SearchQuery(query=query, limit=10)
            result = await memory_db_with_fts.search_memories(search_query)

            # Should find the memory regardless of case
            assert len(result.results) >= 1, (
                f"Should find memory with case-insensitive query: {query}"
            )


# Integration tests with actual SQLite
class TestFTSDirectSQLite:
    """Test FTS functionality directly with SQLite."""

    def test_fts_table_schema_no_t_title_error(self, temp_db_path):
        """Test that FTS table doesn't have 'T.title' error."""
        # Create database with backend
        conn = sqlite3.connect(temp_db_path)

        try:
            # Create nodes table
            conn.execute("""
                CREATE TABLE nodes (
                    id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    properties TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create FTS table WITHOUT problematic options
            conn.execute("""
                CREATE VIRTUAL TABLE nodes_fts USING fts5(
                    id,
                    title,
                    content,
                    summary
                )
            """)

            conn.commit()

            # Test query that would fail with 'T.title' error
            cursor = conn.execute("SELECT id, title FROM nodes_fts")
            results = cursor.fetchall()

            # Should not raise 'no such column: T.title'
            assert True, "Query should succeed without 'T.title' error"

        finally:
            conn.close()

    def test_fts_content_sync(self, temp_db_path):
        """Test manual FTS content synchronization."""
        conn = sqlite3.connect(temp_db_path)
        conn.row_factory = sqlite3.Row

        try:
            # Create tables
            conn.execute("""
                CREATE TABLE nodes (
                    id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    properties TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE VIRTUAL TABLE nodes_fts USING fts5(
                    id,
                    title,
                    content,
                    summary
                )
            """)

            # Insert test data into nodes
            test_memory = {
                "id": "test-1",
                "title": "Test Memory",
                "content": "Test content for FTS",
                "summary": "Test summary",
            }

            conn.execute(
                """
                INSERT INTO nodes (id, label, properties)
                VALUES (?, ?, ?)
                """,
                (test_memory["id"], "Memory", json.dumps(test_memory)),
            )

            # Manually insert into FTS table
            conn.execute(
                """
                INSERT INTO nodes_fts (id, title, content, summary)
                VALUES (?, ?, ?, ?)
                """,
                (
                    test_memory["id"],
                    test_memory["title"],
                    test_memory["content"],
                    test_memory["summary"],
                ),
            )

            conn.commit()

            # Verify FTS table has the data
            cursor = conn.execute(
                "SELECT * FROM nodes_fts WHERE id = ?", (test_memory["id"],)
            )
            result = cursor.fetchone()
            assert result is not None, "Data should be in FTS table"
            assert result["title"] == test_memory["title"]

            # Test FTS search
            cursor = conn.execute(
                "SELECT id FROM nodes_fts WHERE nodes_fts MATCH ?", ("FTS",)
            )
            results = cursor.fetchall()
            assert len(results) >= 1, "Should find memory with 'FTS' in content"

        finally:
            conn.close()

    def test_fts_fix_schema_script(self, temp_db_path):
        """Test that the FTS schema fix script works correctly."""
        import sys
        from pathlib import Path

        # Add utils to path
        sys.path.insert(0, str(Path(__file__).parent))

        try:
            from utils.fix_fts_schema import fix_fts_schema_sync

            # First create a database with the old (wrong) schema
            conn = sqlite3.connect(temp_db_path)

            # Create nodes table
            conn.execute("""
                CREATE TABLE nodes (
                    id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    properties TEXT NOT NULL
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

            # Add some test data
            test_data = {
                "id": "test-fix-1",
                "title": "Test for schema fix",
                "content": "This memory tests the schema fix script",
                "summary": "Schema fix test",
            }

            conn.execute(
                "INSERT INTO nodes (id, label, properties) VALUES (?, ?, ?)",
                ("test-fix-1", "Memory", json.dumps(test_data)),
            )

            conn.commit()
            conn.close()

            # Apply the fix
            fix_fts_schema_sync(Path(temp_db_path))

            # Verify fix worked
            conn = sqlite3.connect(temp_db_path)
            conn.row_factory = sqlite3.Row

            try:
                # Should be able to query without 'T.title' error
                cursor = conn.execute("SELECT * FROM nodes_fts")
                results = cursor.fetchall()
                assert len(results) >= 0, "Query should succeed"

                # Check schema was fixed
                cursor = conn.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name='nodes_fts'"
                )
                row = cursor.fetchone()
                fts_schema = row[0]

                # Should NOT contain problematic options
                assert "content='nodes'" not in fts_schema.lower(), (
                    "Schema should be fixed: no content='nodes' option"
                )
                assert "content_rowid='rowid'" not in fts_schema.lower(), (
                    "Schema should be fixed: no content_rowid='rowid' option"
                )

            finally:
                conn.close()

        except ImportError:
            pytest.skip("FTS fix script not available for testing")
        except Exception as e:
            pytest.fail(f"FTS fix test failed: {e}")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
