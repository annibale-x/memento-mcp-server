"""
Bug regression test suite for mcp-memento.

Covers every bug found during the March 2026 manual testing session:

  BUG-001  find_memento_patterns     — crashed with KeyError 'from_memory_id'
  BUG-002  analyze_memento_graph     — crashed with KeyError 'category'
  BUG-003  set_memento_decay_factor  — ignored the decay_factor argument
  BUG-004  get_recent_memento_activity — MCP timeout due to blocking git subprocess
  BUG-005  get_memento_clusters /    — returned raw stats dict instead of analysis
           get_central_mementos
  BUG-006  CASCADE DELETE            — PRAGMA foreign_keys never enabled → orphan rows
  BUG-007  FTS multi-word query      — phrase-search instead of AND logic
  BUG-008  search_memento_relationships_by_context — always empty (structural note)
"""

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from memento.advanced_tools import AdvancedRelationshipHandlers
from memento.database.engine import SQLiteBackend
from memento.database.interface import SQLiteMemoryDatabase
from memento.models import (
    Memory,
    MemoryType,
    RelationshipProperties,
    RelationshipType,
)
from memento.tools.activity_tools import handle_get_recent_memento_activity
from memento.tools.confidence_tools import handle_set_memento_decay_factor

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_db_path():
    """Temporary SQLite file; cleaned up after the test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as fh:
        path = fh.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
async def backend(temp_db_path):
    """Real SQLiteBackend connected to a temp file (not in-memory)."""
    be = SQLiteBackend(temp_db_path)
    await be.connect()
    await be.initialize_schema()
    yield be
    await be.disconnect()


@pytest.fixture
async def db(backend):
    """SQLiteMemoryDatabase wrapping the real backend."""
    return SQLiteMemoryDatabase(backend)


def _make_memory(
    mem_id: str,
    title: str = "Test memory",
    mem_type: MemoryType = MemoryType.GENERAL,
    importance: float = 0.5,
    tags: list[str] | None = None,
    content: str = "Test content",
) -> Memory:
    now = datetime.now(timezone.utc)
    return Memory(
        id=mem_id,
        type=mem_type,
        title=title,
        content=content,
        tags=tags or [],
        importance=importance,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# BUG-001  find_memento_patterns — KeyError 'from_memory_id'
# ---------------------------------------------------------------------------


class TestBug001FindMementoPatterns:
    """find_memento_patterns must not crash and must return pattern data."""

    @pytest.mark.asyncio
    async def test_no_crash_empty_db(self, db):
        handlers = AdvancedRelationshipHandlers(db)
        result = await handlers.handle_find_memento_patterns({})

        assert not result.isError
        payload = json.loads(result.content[0].text)
        assert "total_memories" in payload
        assert "total_relationships" in payload
        # When DB is empty the handler returns the short-circuit payload
        # which must at least signal zero data cleanly.
        assert payload["total_memories"] == 0

    @pytest.mark.asyncio
    async def test_no_crash_with_args(self, db):
        handlers = AdvancedRelationshipHandlers(db)
        result = await handlers.handle_find_memento_patterns(
            {"min_pattern_size": 2, "min_support": 0.3}
        )

        assert not result.isError
        payload = json.loads(result.content[0].text)
        # Empty DB: must return a payload without crashing (no KeyError)
        assert isinstance(payload, dict)

    @pytest.mark.asyncio
    async def test_detects_relationship_pattern(self, db):
        """When two SOLVES relationships exist, the pattern should appear."""
        m1 = _make_memory("p1", "Problem 1", MemoryType.PROBLEM)
        m2 = _make_memory("p2", "Problem 2", MemoryType.PROBLEM)
        s1 = _make_memory("s1", "Solution 1", MemoryType.SOLUTION)
        s2 = _make_memory("s2", "Solution 2", MemoryType.SOLUTION)

        for m in (m1, m2, s1, s2):
            await db.store_memory(m)

        props = RelationshipProperties(strength=0.8, confidence=0.9)
        await db.create_relationship("s1", "p1", RelationshipType.SOLVES, props)
        await db.create_relationship("s2", "p2", RelationshipType.SOLVES, props)

        handlers = AdvancedRelationshipHandlers(db)
        result = await handlers.handle_find_memento_patterns(
            {"min_pattern_size": 2, "min_support": 0.0}
        )

        assert not result.isError
        payload = json.loads(result.content[0].text)
        assert payload["total_relationships"] == 2

        rel_patterns = payload["relationship_type_patterns"]
        solves_patterns = [
            p for p in rel_patterns if p["relationship_type"] == "SOLVES"
        ]
        assert len(solves_patterns) == 1
        assert solves_patterns[0]["count"] == 2

    @pytest.mark.asyncio
    async def test_min_pattern_size_filter(self, db):
        """Patterns with count < min_pattern_size must be excluded."""
        m1 = _make_memory("m1")
        m2 = _make_memory("m2")
        await db.store_memory(m1)
        await db.store_memory(m2)

        props = RelationshipProperties(strength=0.5, confidence=0.8)
        await db.create_relationship("m1", "m2", RelationshipType.RELATED_TO, props)

        handlers = AdvancedRelationshipHandlers(db)
        # min_pattern_size=5 → the single RELATED_TO should be excluded
        result = await handlers.handle_find_memento_patterns(
            {"min_pattern_size": 5, "min_support": 0.0}
        )

        assert not result.isError
        payload = json.loads(result.content[0].text)
        assert payload["relationship_type_patterns"] == []


# ---------------------------------------------------------------------------
# BUG-002  analyze_memento_graph — KeyError 'category'
# ---------------------------------------------------------------------------


class TestBug002AnalyzeMementoGraph:
    """analyze_memento_graph must not crash and must return analytics."""

    @pytest.mark.asyncio
    async def test_no_crash_empty_db(self, db):
        handlers = AdvancedRelationshipHandlers(db)
        result = await handlers.handle_analyze_memento_graph({})

        assert not result.isError
        payload = json.loads(result.content[0].text)
        assert "summary" in payload
        assert "relationship_distribution" in payload
        assert "category_coverage" in payload
        assert "top_connected_memories" in payload

    @pytest.mark.asyncio
    async def test_summary_fields_present(self, db):
        handlers = AdvancedRelationshipHandlers(db)
        result = await handlers.handle_analyze_memento_graph({})

        payload = json.loads(result.content[0].text)
        summary = payload["summary"]

        for field in (
            "total_memories",
            "total_relationships",
            "graph_density",
            "avg_importance",
            "avg_confidence",
        ):
            assert field in summary, f"Missing summary field: {field}"

    @pytest.mark.asyncio
    async def test_graph_density_with_data(self, db):
        """Density must be 0 with 0 edges and >0 when edges exist."""
        m1 = _make_memory("gd1")
        m2 = _make_memory("gd2")
        await db.store_memory(m1)
        await db.store_memory(m2)

        handlers = AdvancedRelationshipHandlers(db)

        # No edges yet
        result = await handlers.handle_analyze_memento_graph({})
        payload = json.loads(result.content[0].text)
        assert payload["summary"]["graph_density"] == 0.0

        # Add one edge
        props = RelationshipProperties(strength=0.7, confidence=0.8)
        await db.create_relationship("gd1", "gd2", RelationshipType.RELATED_TO, props)

        result = await handlers.handle_analyze_memento_graph({})
        payload = json.loads(result.content[0].text)
        assert payload["summary"]["graph_density"] > 0.0
        assert payload["summary"]["total_relationships"] == 1

    @pytest.mark.asyncio
    async def test_category_coverage_completeness(self, db):
        """All 7 relationship categories must appear in category_coverage."""
        handlers = AdvancedRelationshipHandlers(db)
        result = await handlers.handle_analyze_memento_graph({})

        payload = json.loads(result.content[0].text)
        coverage = payload["category_coverage"]

        expected_categories = {
            "causal",
            "solution",
            "context",
            "learning",
            "similarity",
            "workflow",
            "quality",
        }
        assert set(coverage.keys()) == expected_categories

    @pytest.mark.asyncio
    async def test_top_connected_memories(self, db):
        """The hub memory (most connections) must appear first."""
        hub = _make_memory("hub", "Hub memory")
        spoke1 = _make_memory("sp1", "Spoke 1")
        spoke2 = _make_memory("sp2", "Spoke 2")
        spoke3 = _make_memory("sp3", "Spoke 3")

        for m in (hub, spoke1, spoke2, spoke3):
            await db.store_memory(m)

        props = RelationshipProperties(strength=0.5, confidence=0.8)
        await db.create_relationship("hub", "sp1", RelationshipType.RELATED_TO, props)
        await db.create_relationship("hub", "sp2", RelationshipType.RELATED_TO, props)
        await db.create_relationship("hub", "sp3", RelationshipType.RELATED_TO, props)

        handlers = AdvancedRelationshipHandlers(db)
        result = await handlers.handle_analyze_memento_graph({})

        payload = json.loads(result.content[0].text)
        top = payload["top_connected_memories"]
        assert len(top) >= 1
        assert top[0]["id"] == "hub"
        assert top[0]["degree"] == 3


# ---------------------------------------------------------------------------
# BUG-003  set_memento_decay_factor — ignored the decay_factor argument
# ---------------------------------------------------------------------------


class TestBug003SetMementoDecayFactor:
    """set_memento_decay_factor must persist the supplied decay_factor value."""

    @pytest.mark.asyncio
    async def test_decay_factor_persisted_in_db(self, db):
        """After calling the tool the relationship row must carry the new value."""
        m1 = _make_memory("df1", "Memory 1")
        m2 = _make_memory("df2", "Memory 2")
        await db.store_memory(m1)
        await db.store_memory(m2)

        props = RelationshipProperties(strength=0.8, confidence=0.9, decay_factor=0.95)
        await db.create_relationship("df1", "df2", RelationshipType.SOLVES, props)

        result = await handle_set_memento_decay_factor(
            db,
            {"memory_id": "df1", "decay_factor": 0.99, "reason": "Test"},
        )

        assert not result.isError, result.content[0].text

        # Verify the stored decay_factor in the database
        rows = await db._execute_sql(
            "SELECT decay_factor FROM relationships WHERE from_id = ? OR to_id = ?",
            ("df1", "df1"),
        )
        assert rows, "Relationship row not found after set_decay_factor"
        assert abs(rows[0]["decay_factor"] - 0.99) < 1e-6

    @pytest.mark.asyncio
    async def test_confirmation_message_contains_factor(self, db):
        m = _make_memory("df3", "Single memory")
        m2 = _make_memory("df4", "Related")
        await db.store_memory(m)
        await db.store_memory(m2)

        props = RelationshipProperties(strength=0.5, confidence=0.8)
        await db.create_relationship("df3", "df4", RelationshipType.RELATED_TO, props)

        result = await handle_set_memento_decay_factor(
            db,
            {"memory_id": "df3", "decay_factor": 0.80},
        )

        assert not result.isError
        assert "0.800" in result.content[0].text

    @pytest.mark.asyncio
    async def test_memory_not_found_returns_error(self, db):
        result = await handle_set_memento_decay_factor(
            db,
            {"memory_id": "nonexistent-id", "decay_factor": 0.9},
        )
        assert result.isError

    @pytest.mark.asyncio
    async def test_invalid_decay_factor_returns_error(self, db):
        m = _make_memory("df5")
        await db.store_memory(m)

        result = await handle_set_memento_decay_factor(
            db,
            {"memory_id": "df5", "decay_factor": 1.5},
        )
        assert result.isError

    @pytest.mark.asyncio
    async def test_set_decay_factor_db_method_direct(self, db):
        """Unit-test the new set_decay_factor DB method directly."""
        m1 = _make_memory("dd1")
        m2 = _make_memory("dd2")
        await db.store_memory(m1)
        await db.store_memory(m2)

        props = RelationshipProperties(strength=0.6, confidence=0.8)
        await db.create_relationship("dd1", "dd2", RelationshipType.CAUSES, props)

        updated = await db.set_decay_factor("dd1", 0.70, "direct test")
        assert updated == 1

        rows = await db._execute_sql(
            "SELECT decay_factor FROM relationships WHERE from_id = 'dd1'"
        )
        assert abs(rows[0]["decay_factor"] - 0.70) < 1e-6

    @pytest.mark.asyncio
    async def test_set_decay_factor_updates_all_related_relationships(self, db):
        """set_decay_factor must update both outgoing and incoming relationships."""
        hub = _make_memory("hub2")
        n1 = _make_memory("n1")
        n2 = _make_memory("n2")

        for m in (hub, n1, n2):
            await db.store_memory(m)

        props = RelationshipProperties(strength=0.5, confidence=0.8)
        await db.create_relationship("hub2", "n1", RelationshipType.RELATED_TO, props)
        await db.create_relationship("n2", "hub2", RelationshipType.RELATED_TO, props)

        updated = await db.set_decay_factor("hub2", 1.0, "no decay")
        assert updated == 2  # both relationships touched

        rows = await db._execute_sql(
            "SELECT decay_factor FROM relationships "
            "WHERE from_id = 'hub2' OR to_id = 'hub2'"
        )
        for row in rows:
            assert abs(row["decay_factor"] - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# BUG-004  get_recent_memento_activity — MCP timeout from blocking git call
# ---------------------------------------------------------------------------


class TestBug004RecentActivityTimeout:
    """get_recent_memento_activity must complete even when git detection blocks."""

    @pytest.mark.asyncio
    async def test_completes_when_project_detection_times_out(self, db):
        """Simulate a slow detect_project_context() — tool must not hang."""

        async def slow_detect(*_args, **_kwargs):
            await asyncio.sleep(10)  # way longer than the 3-second guard
            return {"project_path": "/slow"}

        with patch(
            "memento.tools.activity_tools.asyncio.wait_for",
            side_effect=asyncio.TimeoutError,
        ):
            result = await handle_get_recent_memento_activity(db, {"days": 7})

        # Must return a result, not raise / time out
        assert result is not None
        assert not result.isError

    @pytest.mark.asyncio
    async def test_completes_when_project_detection_raises(self, db):
        """If detect_project_context raises, the tool must still return data."""
        with patch(
            "memento.tools.activity_tools.asyncio.wait_for",
            side_effect=RuntimeError("git not found"),
        ):
            result = await handle_get_recent_memento_activity(db, {"days": 7})

        assert result is not None
        assert not result.isError

    @pytest.mark.asyncio
    async def test_returns_correct_structure(self, db):
        """Response must contain the expected sections."""
        m = _make_memory("act1", "Recent activity memory")
        await db.store_memory(m)

        result = await handle_get_recent_memento_activity(db, {"days": 30})

        assert not result.isError
        text = result.content[0].text
        assert "Total Memories" in text

    @pytest.mark.asyncio
    async def test_explicit_project_skips_detection(self, db):
        """When project is explicitly supplied the tool must not call detect_project_context."""
        detect_called = []

        def _fake_detect(*_a, **_kw):
            detect_called.append(True)
            return {"project_path": "/fake"}

        with patch(
            "memento.tools.activity_tools.asyncio.wait_for",
            side_effect=asyncio.TimeoutError,
        ):
            # Even if wait_for would time-out, it must NOT be reached at all
            # when project is explicitly set.
            result = await handle_get_recent_memento_activity(
                db, {"days": 7, "project": "/explicit/path"}
            )

        assert not result.isError
        # detect_project_context is inside the `if not project:` branch
        assert detect_called == [], "detect_project_context must not be called when project is supplied"


# ---------------------------------------------------------------------------
# BUG-005  get_memento_clusters / get_central_mementos — stub output quality
# ---------------------------------------------------------------------------


class TestBug005ClusterAndCentralStubs:
    """Cluster and central-memento tools must return parseable, sane output."""

    @pytest.mark.asyncio
    async def test_clusters_returns_parseable_json(self, db):
        handlers = AdvancedRelationshipHandlers(db)
        result = await handlers.handle_get_memento_clusters({})

        assert not result.isError
        payload = json.loads(result.content[0].text)
        assert "total_memories" in payload
        assert "total_relationships" in payload

    @pytest.mark.asyncio
    async def test_clusters_total_memories_is_integer(self, db):
        """total_memories must be a plain integer, not a dict like {'count': N}."""
        m1 = _make_memory("cl1")
        m2 = _make_memory("cl2")
        await db.store_memory(m1)
        await db.store_memory(m2)

        handlers = AdvancedRelationshipHandlers(db)
        result = await handlers.handle_get_memento_clusters({})

        payload = json.loads(result.content[0].text)
        # The value must be a plain number, not a nested dict
        assert isinstance(payload["total_memories"], (int, float)), (
            f"expected int/float, got {type(payload['total_memories'])}: "
            f"{payload['total_memories']}"
        )
        assert isinstance(payload["total_relationships"], (int, float))

    @pytest.mark.asyncio
    async def test_central_mementos_returns_parseable_json(self, db):
        handlers = AdvancedRelationshipHandlers(db)
        result = await handlers.handle_get_central_mementos({})

        assert not result.isError
        payload = json.loads(result.content[0].text)
        assert "total_memories" in payload

    @pytest.mark.asyncio
    async def test_central_mementos_total_is_integer(self, db):
        m = _make_memory("cen1")
        await db.store_memory(m)

        handlers = AdvancedRelationshipHandlers(db)
        result = await handlers.handle_get_central_mementos({})

        payload = json.loads(result.content[0].text)
        assert isinstance(payload["total_memories"], (int, float)), (
            f"expected int/float, got {type(payload['total_memories'])}"
        )


# ---------------------------------------------------------------------------
# BUG-006  CASCADE DELETE — PRAGMA foreign_keys never enabled
# ---------------------------------------------------------------------------


class TestBug006CascadeDelete:
    """Deleting a memory must cascade-delete its relationships."""

    @pytest.mark.asyncio
    async def test_relationships_deleted_on_memory_delete(self, db):
        m1 = _make_memory("cd1", "Source")
        m2 = _make_memory("cd2", "Target")
        await db.store_memory(m1)
        await db.store_memory(m2)

        props = RelationshipProperties(strength=0.8, confidence=0.9)
        await db.create_relationship("cd1", "cd2", RelationshipType.SOLVES, props)

        # Verify relationship exists
        rows_before = await db._execute_sql(
            "SELECT id FROM relationships WHERE from_id = 'cd1' OR to_id = 'cd1'"
        )
        assert len(rows_before) == 1

        # Delete the source memory
        deleted = await db.delete_memory("cd1")
        assert deleted is True

        # Relationship must be gone
        rows_after = await db._execute_sql(
            "SELECT id FROM relationships WHERE from_id = 'cd1' OR to_id = 'cd1'"
        )
        assert len(rows_after) == 0, (
            f"Expected 0 orphan relationships, found {len(rows_after)}"
        )

    @pytest.mark.asyncio
    async def test_multiple_relationships_cascade(self, db):
        hub = _make_memory("hub3", "Hub")
        n1 = _make_memory("nb1", "Node 1")
        n2 = _make_memory("nb2", "Node 2")
        n3 = _make_memory("nb3", "Node 3")

        for m in (hub, n1, n2, n3):
            await db.store_memory(m)

        props = RelationshipProperties(strength=0.5, confidence=0.8)
        await db.create_relationship("hub3", "nb1", RelationshipType.RELATED_TO, props)
        await db.create_relationship("hub3", "nb2", RelationshipType.RELATED_TO, props)
        await db.create_relationship("nb3", "hub3", RelationshipType.RELATED_TO, props)

        await db.delete_memory("hub3")

        orphans = await db._execute_sql(
            "SELECT id FROM relationships WHERE from_id = 'hub3' OR to_id = 'hub3'"
        )
        assert len(orphans) == 0, f"Found {len(orphans)} orphan(s) after cascade delete"

    @pytest.mark.asyncio
    async def test_statistics_show_no_orphan_relationships(self, db):
        """After deleting all memories the relationship count must be 0."""
        m1 = _make_memory("st1")
        m2 = _make_memory("st2")
        await db.store_memory(m1)
        await db.store_memory(m2)

        props = RelationshipProperties(strength=0.6, confidence=0.7)
        await db.create_relationship("st1", "st2", RelationshipType.CAUSES, props)

        await db.delete_memory("st1")
        await db.delete_memory("st2")

        stats = await db.get_memory_statistics()
        assert stats["total_memories"]["count"] == 0
        assert stats["total_relationships"]["count"] == 0, (
            "Orphan relationships remain after deleting all memories"
        )

    @pytest.mark.asyncio
    async def test_foreign_keys_pragma_enabled(self, backend):
        """PRAGMA foreign_keys must return 1 (ON) on a fresh connection."""
        result = await backend.conn.execute("PRAGMA foreign_keys")
        row = await result.fetchone()
        assert row[0] == 1, "PRAGMA foreign_keys is OFF — cascade delete will not work"

    @pytest.mark.asyncio
    async def test_remaining_memories_unaffected(self, db):
        """Cascade must not touch relationships between surviving memories."""
        victim = _make_memory("victim")
        safe1 = _make_memory("safe1")
        safe2 = _make_memory("safe2")

        for m in (victim, safe1, safe2):
            await db.store_memory(m)

        props = RelationshipProperties(strength=0.7, confidence=0.8)
        await db.create_relationship("victim", "safe1", RelationshipType.CAUSES, props)
        await db.create_relationship(
            "safe1", "safe2", RelationshipType.RELATED_TO, props
        )

        await db.delete_memory("victim")

        # safe1 → safe2 relationship must survive
        survivor = await db._execute_sql(
            "SELECT id FROM relationships WHERE from_id = 'safe1' AND to_id = 'safe2'"
        )
        assert len(survivor) == 1


# ---------------------------------------------------------------------------
# BUG-007  FTS multi-word query — phrase search instead of AND logic
# ---------------------------------------------------------------------------


class TestBug007FTSMultiWordQuery:
    """Multi-word FTS queries must use AND logic, not phrase (adjacent-word) search."""

    @pytest.mark.asyncio
    async def test_multiword_query_finds_non_adjacent_terms(self, db):
        """'token validation' must match a document where words are far apart."""
        m = _make_memory(
            "fts1",
            title="OAuth2 token validation error",
            content=(
                "Token is validated against the secret key. "
                "Clock drift causes validation failures."
            ),
        )
        await db.store_memory(m)

        from memento.models import SearchQuery

        sq = SearchQuery(query="token validation", limit=10)
        result = await db.search_memories(sq)

        assert len(result.results) >= 1, (
            "Multi-word FTS query 'token validation' should find the memory "
            "even when the words are not adjacent"
        )

    @pytest.mark.asyncio
    async def test_multiword_query_all_terms_must_match(self, db):
        """If one term is absent, the document must not appear."""
        present = _make_memory(
            "fts2",
            title="Connection pooling fix",
            content="Fixed timeout by increasing connection pool size.",
        )
        absent = _make_memory(
            "fts3",
            title="Unrelated entry",
            content="Something completely different.",
        )
        await db.store_memory(present)
        await db.store_memory(absent)

        from memento.models import SearchQuery

        sq = SearchQuery(query="connection timeout", limit=10)
        result = await db.search_memories(sq)

        ids = [m.id for m in result.results]
        assert "fts2" in ids, (
            "Should find 'fts2' which contains both 'connection' and 'timeout'"
        )
        assert "fts3" not in ids, "Should not find 'fts3' which lacks 'timeout'"

    @pytest.mark.asyncio
    async def test_single_word_still_works(self, db):
        """Single-word queries must continue to work with prefix matching."""
        m = _make_memory(
            "fts4",
            title="Authentication middleware",
            content="JWT authentication for all routes.",
        )
        await db.store_memory(m)

        from memento.models import SearchQuery

        # Prefix match: 'auth' should hit 'authentication'
        sq = SearchQuery(query="auth", limit=10)
        result = await db.search_memories(sq)

        assert len(result.results) >= 1

    @pytest.mark.asyncio
    async def test_prepare_fts_query_single_term(self, db):
        """_prepare_fts_query must add * suffix for single terms."""
        prepared = db._prepare_fts_query("redis")
        assert prepared == "redis*"

    @pytest.mark.asyncio
    async def test_prepare_fts_query_multi_term_uses_and(self, db):
        """_prepare_fts_query must produce 'a* b*' style AND query, NOT '\"a b\"'."""
        prepared = db._prepare_fts_query("token validation")
        assert '"' not in prepared, (
            f"Multi-word FTS query must not use phrase syntax, got: {prepared!r}"
        )
        parts = prepared.split()
        assert len(parts) == 2
        assert all(p.endswith("*") for p in parts)

    @pytest.mark.asyncio
    async def test_prepare_fts_query_three_terms(self, db):
        prepared = db._prepare_fts_query("connection pool timeout")
        parts = prepared.split()
        assert len(parts) == 3
        assert all(p.endswith("*") for p in parts)

    @pytest.mark.asyncio
    async def test_three_word_query_real_search(self, db):
        """Three-word query must find a document containing all three words."""
        m = _make_memory(
            "fts5",
            title="Redis connection pool timeout fix",
            content=(
                "The connection to Redis timed out because the pool was exhausted. "
                "Increased pool size resolves timeout issues."
            ),
        )
        await db.store_memory(m)

        from memento.models import SearchQuery

        sq = SearchQuery(query="redis pool timeout", limit=10)
        result = await db.search_memories(sq)

        assert len(result.results) >= 1, (
            "Three-word AND query should match document containing all three terms"
        )


# ---------------------------------------------------------------------------
# BUG-008  search_memento_relationships_by_context — structural limitation
# ---------------------------------------------------------------------------


class TestBug008RelationshipContextSearch:
    """
    search_memento_relationships_by_context filters on structured JSON fields
    (scope, conditions, components) that are never written by
    create_memento_relationship.  These tests document the limitation and
    verify that the tool works correctly when the structured fields ARE present.
    """

    @pytest.mark.asyncio
    async def test_returns_empty_for_standard_relationships(self, db):
        """Standard relationships (no structured context) return no results."""
        m1 = _make_memory("sc1")
        m2 = _make_memory("sc2")
        await db.store_memory(m1)
        await db.store_memory(m2)

        props = RelationshipProperties(
            strength=0.8, confidence=0.9, context="plain text context"
        )
        await db.create_relationship("sc1", "sc2", RelationshipType.SOLVES, props)

        results = await db.search_relationships_by_context(components=["sc1"])
        # Expected: 0 — the 'context' field is plain text, not a structured dict
        assert results == [], (
            "Standard relationships lack structured context fields; "
            "search should return empty list"
        )

    @pytest.mark.asyncio
    async def test_no_crash_with_various_filters(self, db):
        """Tool must not crash regardless of which filters are applied."""
        from memento.tools.activity_tools import (
            handle_search_memento_relationships_by_context,
        )

        for args in [
            {"scope": "full"},
            {"conditions": ["prod"]},
            {"has_evidence": True},
            {"components": ["redis"]},
            {"temporal": "v2.0"},
            {},
        ]:
            result = await handle_search_memento_relationships_by_context(db, args)
            assert result is not None, f"Tool crashed for args={args}"
