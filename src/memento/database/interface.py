"""
SQLite database implementation for Memento.

This module provides a simplified SQLiteMemoryDatabase class that handles
all memory and relationship operations directly with SQLite.
"""

import json
import logging
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

from ..config import Config
from ..models import (
    BackendError,
    Memory,
    MemoryContext,
    MemoryError,
    MemoryNotFoundError,
    MemoryType,
    NotFoundError,
    PaginatedResult,
    Relationship,
    RelationshipError,
    RelationshipProperties,
    RelationshipType,
    SearchQuery,
    ValidationError,
)

logger = logging.getLogger(__name__)


class SQLiteMemoryDatabase:
    """SQLite implementation of memory database operations."""

    def __init__(self, backend):
        """
        Initialize with a SQLite backend connection.

        Args:
            backend: SQLiteBackend instance
        """
        self.backend = backend
        self.conn = backend.conn

    # Helper methods for SQLite operations

    async def _execute_sql(
        self, query: str, params: Tuple = ()
    ) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results as dictionaries.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of result rows as dictionaries

        Raises:
            BackendError: If database connection not available
        """
        if not self.conn:
            raise BackendError("Database connection not available")

        async with self.conn.execute(query, params) as cursor:
            # Convert rows to dictionaries
            columns = (
                [desc[0] for desc in cursor.description] if cursor.description else []
            )
            results = []
            rows = await cursor.fetchall()
            for row in rows:
                results.append(dict(zip(columns, row)))

            return results

    async def _execute_write(self, query: str, params: Tuple = ()) -> None:
        """
        Execute a write SQL query.

        Args:
            query: SQL query string
            params: Query parameters
        """
        if not self.conn:
            raise BackendError("Database connection not available")

        await self.conn.execute(query, params)

    def _properties_to_memory(
        self, memory_id: str, properties: Dict[str, Any]
    ) -> Memory:
        """
        Convert properties dictionary to Memory object.

        Args:
            memory_id: Memory ID
            properties: Properties dictionary

        Returns:
            Memory object
        """
        # Parse context if present
        context_dict = properties.get("context", {})
        context = None
        if context_dict:
            try:
                context = MemoryContext(**context_dict)
            except Exception:
                context = None

        # Parse memory type
        memory_type_str = properties.get("type", "general")
        try:
            memory_type = MemoryType(memory_type_str)
        except ValueError:
            memory_type = MemoryType.GENERAL

        # Parse dates
        created_at = None
        if properties.get("created_at"):
            try:
                created_at = datetime.fromisoformat(properties["created_at"])
            except (ValueError, TypeError):
                created_at = datetime.now(timezone.utc)

        updated_at = None
        if properties.get("updated_at"):
            try:
                updated_at = datetime.fromisoformat(properties["updated_at"])
            except (ValueError, TypeError):
                updated_at = datetime.now(timezone.utc)

        return Memory(
            id=memory_id,
            title=properties.get("title", ""),
            content=properties.get("content", ""),
            summary=properties.get("summary", ""),
            type=memory_type,
            importance=properties.get("importance", 0.5),
            tags=properties.get("tags", []),
            context=context,
            created_at=created_at,
            updated_at=updated_at,
        )

    # Memory operations

    async def store_memory(self, memory: Memory) -> Memory:
        """
        Store a memory in SQLite database.

        **Upsert semantics**: if a memory with the same ``id`` already exists,
        this method silently calls ``update_memory()`` instead of raising an
        error.  Pass a freshly-generated ID (or leave ``id=None`` and let the
        caller assign one) when you intend to create a new entry.

        Args:
            memory: Memory object to store.  ``memory.id`` must be set before
                calling this method.

        Returns:
            Stored (or updated) memory with refreshed metadata.

        Raises:
            ValidationError: If memory validation fails (e.g. missing id).
            BackendError: If database operation fails.
        """
        try:
            # Validate memory
            if not memory.id:
                raise ValidationError("Memory ID is required")

            # Check if memory already exists
            existing = await self.get_memory_by_id(memory.id)
            if existing:
                # Update existing memory
                return await self.update_memory(memory)

            # Prepare properties JSON
            properties = {
                "title": memory.title,
                "content": memory.content,
                "summary": memory.summary,
                "type": memory.type.value if memory.type else "general",
                "importance": memory.importance,
                "tags": memory.tags,
                "context": memory.context.model_dump(mode="json")
                if memory.context
                else {},
                "version": 1,
                "created_at": memory.created_at.isoformat()
                if memory.created_at
                else datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "last_accessed": memory.last_accessed.isoformat()
                if memory.last_accessed
                else None,
            }

            # Insert into nodes table
            query = """
                INSERT INTO nodes (id, label, properties)
                VALUES (?, ?, ?)
            """
            await self._execute_write(
                query, (memory.id, "Memory", json.dumps(properties, default=str))
            )

            # Update FTS table if available
            if self.backend.supports_fulltext_search():
                try:
                    fts_query = """
                        INSERT INTO nodes_fts (id, title, content, summary)
                        VALUES (?, ?, ?, ?)
                    """
                    await self._execute_write(
                        fts_query,
                        (
                            memory.id,
                            memory.title or "",
                            memory.content or "",
                            memory.summary or "",
                        ),
                    )
                except Exception as e:
                    logger.warning(f"Could not update FTS table: {e}")

            await self.conn.commit()
            logger.debug(f"Stored memory: {memory.id}")
            return memory

        except aiosqlite.Error as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to store memory: {e}")
        except Exception as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to store memory: {str(e)}")

    async def get_memory(
        self, memory_id: str, include_relationships: bool = True
    ) -> Optional[Memory]:
        """
        Retrieve a memory by its ID, optionally including related memories.

        Args:
            memory_id: Memory ID
            include_relationships: Whether to include related memories (default: True)

        Returns:
            Memory object if found, None otherwise

        Raises:
            BackendError: If database operation fails
        """
        try:
            query = """
                SELECT properties FROM nodes
                WHERE id = ? AND label = 'Memory'
            """
            results = await self._execute_sql(query, (memory_id,))

            if not results:
                return None

            properties = json.loads(results[0]["properties"])
            memory = self._properties_to_memory(memory_id, properties)

            # Get related memories if requested
            if include_relationships:
                related = await self.get_related_memories(memory_id, max_depth=1)
                # Note: The Memory model doesn't have a relationships field,
                # so we can't attach them directly. The relationships are
                # available through separate API calls.

            return memory

        except aiosqlite.Error as e:
            raise BackendError(f"Failed to get memory: {e}")
        except Exception as e:
            raise BackendError(f"Failed to get memory: {str(e)}")

    async def get_memory_by_id(self, memory_id: str) -> Optional[Memory]:
        """
        Retrieve a memory by its ID (legacy method, use get_memory instead).

        Args:
            memory_id: Memory ID

        Returns:
            Memory object if found, None otherwise

        Raises:
            BackendError: If database operation fails
        """
        return await self.get_memory(memory_id, include_relationships=False)

    async def update_memory(self, memory: Memory) -> Memory:
        """
        Update an existing memory.

        Args:
            memory: Memory object with updated data

        Returns:
            Updated memory

        Raises:
            MemoryNotFoundError: If memory doesn't exist
            ValidationError: If memory validation fails
            BackendError: If database operation fails
        """
        try:
            # Check if memory exists
            existing = await self.get_memory_by_id(memory.id)
            if not existing:
                raise MemoryNotFoundError(f"Memory not found: {memory.id}")

            # Get current version for optimistic locking
            result = await self._execute_sql(
                "SELECT properties FROM nodes WHERE id = ? AND label = 'Memory'",
                (memory.id,),
            )
            current_properties = json.loads(result[0]["properties"])
            current_version = current_properties.get("version", 1)

            # Prepare updated properties
            properties = {
                "title": memory.title,
                "content": memory.content,
                "summary": memory.summary,
                "type": memory.type.value if memory.type else "general",
                "importance": memory.importance,
                "tags": memory.tags,
                "context": memory.context.model_dump() if memory.context else {},
                "version": current_version + 1,
                "created_at": current_properties.get(
                    "created_at", datetime.now(timezone.utc).isoformat()
                ),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Update nodes table
            query = """
                UPDATE nodes
                SET properties = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND label = 'Memory'
            """
            await self._execute_write(
                query, (json.dumps(properties, default=str), memory.id)
            )

            # Update FTS table if available
            if self.backend.supports_fulltext_search():
                try:
                    fts_query = """
                        INSERT OR REPLACE INTO nodes_fts (id, title, content, summary)
                        VALUES (?, ?, ?, ?)
                    """
                    await self._execute_write(
                        fts_query,
                        (
                            memory.id,
                            memory.title or "",
                            memory.content or "",
                            memory.summary or "",
                        ),
                    )
                except aiosqlite.Error as e:
                    logger.warning(f"Could not update FTS table: {e}")

            await self.conn.commit()
            logger.debug(f"Updated memory: {memory.id}")
            return memory

        except aiosqlite.Error as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to update memory: {e}")
        except Exception as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to update memory: {str(e)}")

    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory by its ID.

        Args:
            memory_id: Memory ID

        Returns:
            True if memory was deleted, False if not found

        Raises:
            BackendError: If database operation fails
        """
        try:
            # Check if memory exists
            existing = await self.get_memory_by_id(memory_id)
            if not existing:
                return False

            # Delete from nodes table (relationships will be cascade deleted)
            query = "DELETE FROM nodes WHERE id = ? AND label = 'Memory'"
            await self._execute_write(query, (memory_id,))

            # Delete from FTS table if available
            if self.backend.supports_fulltext_search():
                try:
                    fts_query = "DELETE FROM nodes_fts WHERE id = ?"
                    await self._execute_write(fts_query, (memory_id,))
                except aiosqlite.Error as e:
                    logger.warning(f"Could not delete from FTS table: {e}")

            await self.conn.commit()
            logger.debug(f"Deleted memory: {memory_id}")
            return True

        except aiosqlite.Error as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to delete memory: {e}")
        except Exception as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to delete memory: {str(e)}")

    async def search_memories(self, query: SearchQuery) -> PaginatedResult:
        """
        Search memories using SQLite full-text search or simple pattern matching.

        Args:
            query: Search query object

        Returns:
            PaginatedResult with matching memories

        Raises:
            BackendError: If database operation fails
        """
        try:
            memories: List[Memory] = []
            total_count = 0

            # Use FTS if available and query is not empty
            if query.query and self.backend.supports_fulltext_search():
                memories, total_count = await self._search_with_fts(query)
            else:
                memories, total_count = await self._search_with_simple(query)

            # Apply offset and limit
            start = query.offset or 0
            end = start + (query.limit or len(memories))
            paginated_memories = memories[start:end]

            # Calculate next offset
            next_offset = None
            if end < total_count:
                next_offset = end

            return PaginatedResult(
                results=paginated_memories,
                total_count=total_count,
                limit=query.limit or len(paginated_memories),
                offset=query.offset or 0,
                has_more=next_offset is not None,
                next_offset=next_offset,
            )

        except aiosqlite.Error as e:
            raise BackendError(f"Failed to search memories: {e}")
        except Exception as e:
            raise BackendError(f"Failed to search memories: {str(e)}")

    async def _search_with_fts(self, query: SearchQuery) -> Tuple[List[Memory], int]:
        """Search using SQLite FTS5 full-text search."""
        search_terms = self._prepare_fts_query(query.query)

        fts_query = f"""
            SELECT n.id, n.properties
            FROM nodes n
            JOIN nodes_fts fts ON n.id = fts.id
            WHERE n.label = 'Memory'
              AND fts.nodes_fts MATCH ?
            ORDER BY
                (json_extract(n.properties, '$.confidence') * json_extract(n.properties, '$.importance')) DESC,
                rank
            LIMIT ?
        """

        # Get total count
        count_query = f"""
            SELECT COUNT(*)
            FROM nodes n
            JOIN nodes_fts fts ON n.id = fts.id
            WHERE n.label = 'Memory'
              AND fts.nodes_fts MATCH ?
        """

        limit = query.limit or 100

        # Execute queries
        results = await self._execute_sql(fts_query, (search_terms, limit))
        count_result = await self._execute_sql(count_query, (search_terms,))
        total_count = count_result[0]["COUNT(*)"] if count_result else 0

        # Convert to Memory objects
        memories = []
        for row in results:
            try:
                properties = json.loads(row["properties"])
                memory = self._properties_to_memory(row["id"], properties)
                memories.append(memory)
            except Exception as e:
                logger.warning(f"Failed to parse memory {row['id']}: {e}")

        return memories, total_count

    async def _search_with_simple(self, query: SearchQuery) -> Tuple[List[Memory], int]:
        """Search using simple SQL pattern matching."""
        where_clauses = ["label = 'Memory'"]
        params = []

        if query.query:
            # AND-match every whitespace-separated word independently so that
            # "connection timeout" finds documents containing both words even
            # when they are not adjacent (mirrors the FTS AND behaviour).
            words = query.query.split()

            for word in words:
                pattern = f"%{word}%"
                where_clauses.append("""
                    (json_extract(properties, '$.title') LIKE ?
                     OR json_extract(properties, '$.content') LIKE ?
                     OR json_extract(properties, '$.summary') LIKE ?)
                """)
                params.extend([pattern, pattern, pattern])

        # Filter by tags if specified
        if query.tags:
            tag_conditions = []
            for tag in query.tags:
                tag_conditions.append("json_extract(properties, '$.tags') LIKE ?")
                params.append(f'%"{tag}"%')
            where_clauses.append(f"({' OR '.join(tag_conditions)})")

        # Filter by memory type if specified
        if query.memory_types:
            type_conditions = []
            for mem_type in query.memory_types:
                type_conditions.append("json_extract(properties, '$.type') = ?")
                params.append(
                    mem_type.value if hasattr(mem_type, "value") else mem_type
                )
            where_clauses.append(f"({' OR '.join(type_conditions)})")

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Get total count
        count_query = f"SELECT COUNT(*) FROM nodes WHERE {where_sql}"
        count_result = await self._execute_sql(count_query, params)
        total_count = count_result[0]["COUNT(*)"] if count_result else 0

        # Get results with limit
        limit = query.limit or 100
        search_query = f"""
            SELECT id, properties FROM nodes
            WHERE {where_sql}
            ORDER BY
                (json_extract(properties, '$.confidence') * json_extract(properties, '$.importance')) DESC,
                json_extract(properties, '$.updated_at') DESC
            LIMIT ?
        """
        params.append(limit)

        results = await self._execute_sql(search_query, params)

        # Convert to Memory objects
        memories = []
        for row in results:
            try:
                properties = json.loads(row["properties"])
                memory = self._properties_to_memory(row["id"], properties)
                memories.append(memory)
            except Exception as e:
                logger.warning(f"Failed to parse memory {row['id']}: {e}")

        return memories, total_count

    def _prepare_fts_query(self, query: str) -> str:
        """
        Prepare query string for SQLite FTS5.

        Single terms use prefix matching (token*).
        Multi-word queries use AND logic so all terms must appear anywhere
        in the document (not necessarily adjacent), which is far more useful
        than phrase search for exploratory queries.

        Args:
            query: Raw search query

        Returns:
            FTS5-compatible query string
        """
        # Extract word tokens, strip FTS5 special chars
        terms = re.findall(r"\b\w+\b", query.lower())

        if not terms:
            return "*"  # Match all

        if len(terms) == 1:
            # Single term: prefix matching for partial words
            return f"{terms[0]}*"

        # Multi-word: AND of prefix-matched terms so every word must appear
        return " ".join(f"{t}*" for t in terms)

    # Relationship operations

    async def create_relationship(
        self,
        from_memory_id: str,
        to_memory_id: str,
        relationship_type: RelationshipType,
        properties: RelationshipProperties,
    ) -> str:
        """
        Create and store a new relationship between two memories.

        Args:
            from_memory_id: ID of source memory
            to_memory_id: ID of target memory
            relationship_type: Type of relationship
            properties: Relationship properties

        Returns:
            ID of the created relationship

        Raises:
            ValidationError: If relationship validation fails
            BackendError: If database operation fails
        """
        # Generate a unique ID for the relationship
        import uuid

        from ..models import Relationship

        relationship_id = str(uuid.uuid4())

        # Create Relationship object
        relationship = Relationship(
            id=relationship_id,
            from_memory_id=from_memory_id,
            to_memory_id=to_memory_id,
            type=relationship_type,
            properties=properties,
        )

        # Store the relationship
        stored_relationship = await self.store_relationship(relationship)
        return stored_relationship.id

    async def store_relationship(self, relationship: Relationship) -> Relationship:
        """
        Store a relationship in SQLite database.

        Args:
            relationship: Relationship object to store

        Returns:
            Stored relationship

        Raises:
            ValidationError: If relationship validation fails
            BackendError: If database operation fails
        """
        try:
            # Validate relationship
            if not relationship.id:
                raise ValidationError("Relationship ID is required")

            # Check if from_memory exists
            from_memory = await self.get_memory_by_id(relationship.from_memory_id)
            if not from_memory:
                raise ValidationError(
                    f"From memory not found: {relationship.from_memory_id}"
                )

            # Check if to_memory exists
            to_memory = await self.get_memory_by_id(relationship.to_memory_id)
            if not to_memory:
                raise ValidationError(
                    f"To memory not found: {relationship.to_memory_id}"
                )

            # Check for cycles if not allowed
            if not Config.ALLOW_RELATIONSHIP_CYCLES:
                await self._check_for_cycles(relationship)

            # Prepare properties JSON (exclude temporal fields, keep them only as columns)
            # Prepare properties dict
            props_dict = relationship.properties.model_dump()

            created_at = (
                relationship.properties.created_at.isoformat()
                if relationship.properties.created_at
                else datetime.now(timezone.utc).isoformat()
            )

            # Insert into relationships table
            query = """
                INSERT INTO relationships (
                    id, from_id, to_id, rel_type, properties, created_at,
                    
                    confidence, last_accessed, access_count, decay_factor
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            # Serialize props with correct datetimes
            for k, v in props_dict.items():
                if isinstance(v, datetime):
                    props_dict[k] = v.isoformat()

            # Handle confidence system fields
            confidence = relationship.properties.confidence
            last_accessed = (
                relationship.properties.last_accessed.isoformat()
                if relationship.properties.last_accessed
                else datetime.now(timezone.utc).isoformat()
            )
            access_count = relationship.properties.access_count
            decay_factor = relationship.properties.decay_factor

            await self._execute_write(
                query,
                (
                    relationship.id,
                    relationship.from_memory_id,
                    relationship.to_memory_id,
                    relationship.type.value,
                    json.dumps(props_dict),
                    created_at,
                    confidence,
                    last_accessed,
                    access_count,
                    decay_factor,
                ),
            )

            await self.conn.commit()
            logger.debug(f"Stored relationship: {relationship.id}")
            return relationship

        except aiosqlite.Error as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to store relationship: {e}")
        except Exception as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to store relationship: {str(e)}")

    async def _check_for_cycles(self, relationship: Relationship) -> None:
        """
        Check if adding a relationship would create a cycle.

        Args:
            relationship: Relationship to check

        Raises:
            ValidationError: If cycle would be created
        """
        # Simple cycle detection for now
        # In a full implementation, we would traverse the graph
        if relationship.from_memory_id == relationship.to_memory_id:
            raise ValidationError("Self-referential relationships are not allowed")

        # Check for existing reverse relationship
        query = """
            SELECT COUNT(*) FROM relationships
            WHERE from_id = ? AND to_id = ? AND rel_type = ?
        """
        results = await self._execute_sql(
            query,
            (
                relationship.to_memory_id,
                relationship.from_memory_id,
                relationship.type.value,
            ),
        )

        if results and results[0]["COUNT(*)"] > 0:
            raise ValidationError(
                f"Reverse relationship already exists: {relationship.type.value}"
            )

    async def get_relationships_for_memory(self, memory_id: str) -> List[Relationship]:
        """
        Get all relationships for a specific memory.

        Args:
            memory_id: Memory ID

        Returns:
            List of Relationship objects

        Raises:
            BackendError: If database operation fails
        """
        try:
            query = """
                SELECT id, from_id, to_id, rel_type, properties,
                       created_at,
                       confidence, last_accessed, access_count, decay_factor
                FROM relationships
                WHERE from_id = ? OR to_id = ?
            """
            results = await self._execute_sql(query, (memory_id, memory_id))

            relationships = []
            for row in results:
                try:
                    properties = json.loads(row["properties"])
                    rel_type = RelationshipType(row["rel_type"])

                    def parse_date(date_str):
                        if not date_str:
                            return None
                        try:
                            return datetime.fromisoformat(date_str)
                        except (ValueError, TypeError):
                            return None

                    created_at = parse_date(row["created_at"]) or datetime.now(
                        timezone.utc
                    )

                    # Parse confidence system fields
                    confidence = (
                        float(row["confidence"])
                        if row["confidence"] is not None
                        else 0.8
                    )
                    last_accessed = parse_date(row["last_accessed"]) or datetime.now(
                        timezone.utc
                    )
                    access_count = (
                        int(row["access_count"])
                        if row["access_count"] is not None
                        else 0
                    )
                    decay_factor = (
                        float(row["decay_factor"])
                        if row["decay_factor"] is not None
                        else 0.95
                    )

                    # Update properties with confidence system fields
                    properties.update(
                        {
                            "confidence": confidence,
                            "last_accessed": last_accessed,
                            "access_count": access_count,
                            "decay_factor": decay_factor,
                        }
                    )

                    relationship = Relationship(
                        id=row["id"],
                        from_memory_id=row["from_id"],
                        to_memory_id=row["to_id"],
                        type=rel_type,
                        properties=RelationshipProperties(**properties),
                        created_at=created_at,
                    )
                    relationships.append(relationship)
                except (KeyError, ValueError, json.JSONDecodeError) as e:
                    logger.warning(f"Failed to parse relationship row: {e}")
                    continue

            return relationships

        except Exception as e:
            raise BackendError(f"Failed to get relationships: {str(e)}")

    async def get_related_memories(
        self,
        memory_id: str,
        relationship_types: Optional[List[RelationshipType]] = None,
        max_depth: int = 2,
    ) -> List[Tuple[Memory, Relationship]]:
        """
        Get memories related to a specific memory with their relationships.

        Args:
            memory_id: ID of memory to find relations for
            relationship_types: Optional list of relationship types to filter
            max_depth: Maximum traversal depth (default: 2)

        Returns:
            List of tuples (Memory, Relationship) for related memories
            For depth > 1, returns (Memory, incoming_relationship) where
            incoming_relationship is the relationship from the parent in the path

        Raises:
            BackendError: If database operation fails
        """
        try:
            # Special case: depth 0 returns empty list
            if max_depth < 1:
                return []

            # Use BFS to traverse relationships
            visited = set([memory_id])
            results = []

            # Queue stores (current_memory_id, current_depth, path_relationship)
            # path_relationship is the relationship that led to current_memory_id
            queue = []

            # Initialize queue with direct neighbors of the starting memory
            direct_relationships = await self.get_relationships_for_memory(memory_id)

            # Filter by relationship types if specified
            if relationship_types:
                direct_relationships = [
                    rel
                    for rel in direct_relationships
                    if rel.type in relationship_types
                ]

            for relationship in direct_relationships:
                # Determine which memory is the neighbor
                if relationship.from_memory_id == memory_id:
                    neighbor_id = relationship.to_memory_id
                else:
                    neighbor_id = relationship.from_memory_id

                if neighbor_id in visited:
                    continue

                visited.add(neighbor_id)

                # Get the neighbor memory
                neighbor_memory = await self.get_memory_by_id(neighbor_id)
                if not neighbor_memory:
                    continue

                # Add to results with the direct relationship
                results.append((neighbor_memory, relationship))

                # Add to queue for further traversal if depth > 1
                if max_depth > 1:
                    queue.append((neighbor_id, 1, relationship))

            # Process queue for deeper levels
            while queue:
                current_id, current_depth, incoming_relationship = queue.pop(0)

                # Get relationships for current memory
                current_relationships = await self.get_relationships_for_memory(
                    current_id
                )

                # Filter by relationship types if specified
                if relationship_types:
                    current_relationships = [
                        rel
                        for rel in current_relationships
                        if rel.type in relationship_types
                    ]

                for relationship in current_relationships:
                    # Determine which memory is the neighbor
                    if relationship.from_memory_id == current_id:
                        neighbor_id = relationship.to_memory_id
                    else:
                        neighbor_id = relationship.from_memory_id

                    if neighbor_id in visited:
                        continue

                    visited.add(neighbor_id)

                    # Get the neighbor memory
                    neighbor_memory = await self.get_memory_by_id(neighbor_id)
                    if not neighbor_memory:
                        continue

                    # Add to results with the relationship that led to this memory
                    # (the incoming relationship from the path)
                    results.append((neighbor_memory, incoming_relationship))

                    # Add to queue for further traversal if not at max depth
                    if current_depth + 1 < max_depth:
                        queue.append(
                            (neighbor_id, current_depth + 1, incoming_relationship)
                        )

            return results

        except Exception as e:
            raise BackendError(f"Failed to get related memories: {str(e)}")

    async def update_relationship_properties(
        self,
        from_memory_id: str,
        to_memory_id: str,
        relationship_type: RelationshipType,
        new_properties: RelationshipProperties,
    ) -> bool:
        """
        Update properties of an existing relationship.

        Args:
            from_memory_id: ID of source memory
            to_memory_id: ID of target memory
            relationship_type: Type of relationship
            new_properties: New relationship properties

        Returns:
            True if relationship was updated, False if not found

        Raises:
            BackendError: If database operation fails
        """
        try:
            # Find the relationship
            query = """
                SELECT id, properties FROM relationships
                WHERE from_id = ? AND to_id = ? AND rel_type = ?
            """
            results = await self._execute_sql(
                query, (from_memory_id, to_memory_id, relationship_type.value)
            )

            if not results:
                return False

            relationship_id = results[0]["id"]

            # Update properties
            update_query = """
                UPDATE relationships
                SET properties = ?, last_validated = ?
                WHERE id = ?
            """

            # Prepare properties JSON
            properties_dict = new_properties.model_dump(mode="json")
            properties_json = json.dumps(properties_dict)

            # Update last_validated timestamp
            last_validated = datetime.now(timezone.utc).isoformat()

            await self._execute_write(
                update_query, (properties_json, last_validated, relationship_id)
            )

            return True

        except Exception as e:
            raise BackendError(f"Failed to update relationship properties: {str(e)}")

    async def delete_relationship(self, relationship_id: str) -> bool:
        """
        Delete a relationship by its ID.

        Args:
            relationship_id: ID of relationship to delete

        Returns:
            True if relationship was deleted, False if not found

        Raises:
            BackendError: If database operation fails
        """
        try:
            # Check if relationship exists
            query = "SELECT COUNT(*) FROM relationships WHERE id = ?"
            results = await self._execute_sql(query, (relationship_id,))

            if not results or results[0]["COUNT(*)"] == 0:
                return False

            # Delete relationship
            delete_query = "DELETE FROM relationships WHERE id = ?"
            await self._execute_write(delete_query, (relationship_id,))

            await self.conn.commit()
            logger.debug(f"Deleted relationship: {relationship_id}")
            return True

        except aiosqlite.Error as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to delete relationship: {e}")
        except Exception as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to delete relationship: {str(e)}")

    async def initialize_schema(self) -> None:
        """
        Initialize database schema if needed.

        This is a no-op since the SQLiteBackend already creates the schema.
        """
        logger.debug("Schema already initialized by SQLiteBackend")

    async def search_relationships_by_context(
        self,
        scope: Optional[str] = None,
        conditions: Optional[List[str]] = None,
        has_evidence: Optional[bool] = None,
        evidence: Optional[List[str]] = None,
        components: Optional[List[str]] = None,
        temporal: Optional[str] = None,
        limit: int = 20,
    ) -> List[Relationship]:
        """
        Search relationships by their structured context fields.

        Args:
            scope: Filter by scope (partial/full/conditional)
            conditions: Filter by conditions
            has_evidence: Filter by presence/absence of evidence
            evidence: Filter by specific evidence types
            components: Filter by components mentioned
            temporal: Filter by temporal information
            limit: Maximum number of results

        Returns:
            List of matching relationships

        Raises:
            BackendError: If database operation fails
        """
        try:
            # Base query
            query = """
                SELECT id, from_id, to_id, rel_type, properties,
                       created_at,
                       confidence, last_accessed, access_count, decay_factor
                FROM relationships
                WHERE properties IS NOT NULL AND properties != ''
            """
            params = []

            # Build WHERE clauses based on filters
            where_clauses = []

            if scope:
                where_clauses.append("properties LIKE ?")
                params.append(f'%"scope"%:"{scope}"%')

            if conditions:
                for condition in conditions:
                    where_clauses.append("properties LIKE ?")
                    params.append(f'%"conditions"%:"{condition}"%')

            if evidence:
                for ev in evidence:
                    where_clauses.append("properties LIKE ?")
                    params.append(f'%"evidence"%:"{ev}"%')

            if components:
                for component in components:
                    where_clauses.append("properties LIKE ?")
                    params.append(f'%"components"%:"{component}"%')

            if temporal:
                where_clauses.append("properties LIKE ?")
                params.append(f'%"temporal"%:"{temporal}"%')

            if has_evidence is not None:
                if has_evidence:
                    where_clauses.append(
                        "(properties LIKE '%\"evidence\"%' OR properties LIKE '%\"evidence_count\"%')"
                    )
                else:
                    where_clauses.append(
                        "(properties NOT LIKE '%\"evidence\"%' AND properties NOT LIKE '%\"evidence_count\"%')"
                    )

            # Add WHERE clauses if any
            if where_clauses:
                query += " AND " + " AND ".join(where_clauses)

            # Add limit
            query += " LIMIT ?"
            params.append(limit)

            # Execute query
            results = await self._execute_sql(query, tuple(params))

            # Parse results into Relationship objects
            relationships = []
            for row in results:
                try:
                    properties = json.loads(row["properties"])
                    rel_type = RelationshipType(row["rel_type"])

                    def parse_date(date_str):
                        if not date_str:
                            return None
                        try:
                            return datetime.fromisoformat(date_str)
                        except (ValueError, TypeError):
                            return None

                    created_at = parse_date(row["created_at"]) or datetime.now(
                        timezone.utc
                    )

                    # Parse confidence system fields
                    confidence = (
                        float(row["confidence"])
                        if row["confidence"] is not None
                        else 0.8
                    )
                    last_accessed = parse_date(row["last_accessed"]) or datetime.now(
                        timezone.utc
                    )
                    access_count = (
                        int(row["access_count"])
                        if row["access_count"] is not None
                        else 0
                    )
                    decay_factor = (
                        float(row["decay_factor"])
                        if row["decay_factor"] is not None
                        else 0.95
                    )

                    # Update properties with confidence system fields
                    properties.update(
                        {
                            "confidence": confidence,
                            "last_accessed": last_accessed,
                            "access_count": access_count,
                            "decay_factor": decay_factor,
                        }
                    )

                    relationship = Relationship(
                        id=row["id"],
                        from_memory_id=row["from_id"],
                        to_memory_id=row["to_id"],
                        type=rel_type,
                        properties=RelationshipProperties(**properties),
                        created_at=created_at,
                    )
                    relationships.append(relationship)
                except (KeyError, ValueError, json.JSONDecodeError) as e:
                    logger.warning(f"Failed to parse relationship row: {e}")
                    continue

            return relationships

        except Exception as e:
            raise BackendError(f"Failed to search relationships by context: {str(e)}")
        except aiosqlite.Error as e:
            raise BackendError(f"Failed to get relationship history: {e}")
        except Exception as e:
            raise BackendError(f"Failed to get relationship history: {str(e)}")

    async def get_recent_activity(
        self, days: int = 7, project: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get recent activity summary for session briefing.

        Args:
            days: Number of days to look back (default: 7)
            project: Optional project path filter

        Returns:
            Dictionary containing activity details

        Raises:
            BackendError: If database operation fails
        """
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_iso = cutoff_date.isoformat()

            # Build WHERE conditions
            where_conditions = [
                "label = 'Memory'",
                "json_extract(properties, '$.created_at') >= ?",
            ]
            params = [cutoff_iso]

            if project:
                where_conditions.append(
                    "json_extract(properties, '$.context_project_path') = ?"
                )
                params.append(project)

            where_clause = " AND ".join(where_conditions)

            # Get total count
            count_query = f"SELECT COUNT(*) as count FROM nodes WHERE {where_clause}"
            count_result = await self._execute_sql(count_query, tuple(params))
            total_count = count_result[0]["count"] if count_result else 0

            # Get memories by type
            type_query = f"""
                SELECT
                    json_extract(properties, '$.type') as type,
                    COUNT(*) as count
                FROM nodes
                WHERE {where_clause}
                GROUP BY json_extract(properties, '$.type')
            """
            type_result = await self._execute_sql(type_query, tuple(params))
            memories_by_type = (
                {row["type"]: row["count"] for row in type_result}
                if type_result
                else {}
            )

            # Get recent memories
            recent_query = f"""
                SELECT id, properties
                FROM nodes
                WHERE {where_clause}
                ORDER BY json_extract(properties, '$.created_at') DESC
                LIMIT 20
            """
            recent_result = await self._execute_sql(recent_query, tuple(params))

            recent_memories = []
            for row in recent_result:
                try:
                    properties = json.loads(row["properties"])
                    memory = self._properties_to_memory(row["id"], properties)
                    recent_memories.append(memory)
                except Exception:
                    pass

            # Find unresolved problems
            unresolved_query = f"""
                SELECT n.id, n.properties
                FROM nodes n
                WHERE {where_clause}
                    AND json_extract(n.properties, '$.type') IN ('problem', 'error')
                    AND NOT EXISTS (
                        SELECT 1
                        FROM relationships r
                        WHERE r.to_id = n.id
                            AND r.rel_type IN ('SOLVES', 'FIXES', 'ADDRESSES')
                    )
                ORDER BY CAST(json_extract(n.properties, '$.importance') AS REAL) DESC
                LIMIT 10
            """
            unresolved_result = await self._execute_sql(unresolved_query, tuple(params))

            unresolved_problems = []
            for row in unresolved_result:
                try:
                    properties = json.loads(row["properties"])
                    memory = self._properties_to_memory(row["id"], properties)
                    unresolved_problems.append(memory)
                except Exception:
                    pass

            return {
                "total_count": total_count,
                "memories_by_type": memories_by_type,
                "recent_memories": recent_memories,
                "unresolved_problems": unresolved_problems,
                "days": days,
                "project": project,
            }

        except aiosqlite.Error as e:
            raise BackendError(f"Failed to get recent activity: {e}")
        except Exception as e:
            raise BackendError(f"Failed to get recent activity: {str(e)}")

    async def update_confidence_on_access(self, relationship_id: str) -> None:
        """
        Update confidence and access count when a relationship is accessed.

        Args:
            relationship_id: ID of the relationship that was accessed

        Raises:
            BackendError: If database operation fails
        """
        try:
            now = datetime.now(timezone.utc).isoformat()

            # Update access count and last_accessed
            update_query = """
                UPDATE relationships
                SET access_count = access_count + 1,
                    last_accessed = ?
                WHERE id = ?
            """
            await self._execute_write(update_query, (now, relationship_id))

            # Apply confidence boost for usage
            boost_query = """
                UPDATE relationships
                SET confidence = MIN(1.0, confidence + 0.01)
                WHERE id = ? AND confidence < 1.0
            """
            await self._execute_write(boost_query, (relationship_id,))

            await self.conn.commit()
            logger.debug(
                f"Updated confidence on access for relationship: {relationship_id}"
            )

        except aiosqlite.Error as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to update confidence on access: {e}")
        except Exception as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to update confidence on access: {str(e)}")

    async def apply_confidence_decay(self, memory_id: Optional[str] = None) -> int:
        """
        Apply confidence decay to relationships based on last access time.

        Args:
            memory_id: Optional memory ID to apply decay only to its relationships

        Returns:
            Number of relationships updated

        Raises:
            BackendError: If database operation fails
        """
        try:
            # Calculate decay based on months since last access
            # Base decay: 5% per month (decay_factor = 0.95)
            # But apply intelligent decay based on memory importance and tags

            if memory_id:
                # Get memory to check its importance and tags
                memory = await self.get_memory_by_id(memory_id)
                if not memory:
                    return 0

                # Calculate custom decay factor based on memory properties
                base_decay = 0.95  # 5% decay per month

                # Adjust decay based on importance
                importance_factor = 1.0 - (memory.importance * 0.3)
                # importance=0.9 → factor=0.73 (27% less decay)

                # Check for critical tags that should have no decay
                critical_tags = {
                    "security",
                    "auth",
                    "api_key",
                    "password",
                    "critical",
                    "no_decay",
                }
                has_critical_tag = any(tag in critical_tags for tag in memory.tags)

                # Check for temporary tags that should decay faster
                temporary_tags = {"temporary", "session", "debug"}
                has_temporary_tag = any(tag in temporary_tags for tag in memory.tags)

                if has_critical_tag:
                    # No decay for critical memories
                    decay_factor = 1.0
                elif has_temporary_tag:
                    # Faster decay for temporary context: 20% monthly (decay_factor = 0.80)
                    decay_factor = 0.80
                else:
                    decay_factor = base_decay * importance_factor

                # Update decay_factor for all relationships of this memory
                update_decay_query = """
                    UPDATE relationships
                    SET decay_factor = ?
                    WHERE from_id = ? OR to_id = ?
                """
                await self._execute_write(
                    update_decay_query, (decay_factor, memory_id, memory_id)
                )

            # Apply decay based on months since last access
            # For each month without access: confidence = confidence * decay_factor
            decay_query = """
                UPDATE relationships
                SET confidence = confidence * POWER(
                    decay_factor,
                    CAST((julianday('now') - julianday(last_accessed)) / 30.0 AS INTEGER)
                )
                WHERE last_accessed IS NOT NULL
                  AND confidence > 0.1  -- Don't decay below 0.1
            """

            if memory_id:
                decay_query += " AND (from_id = ? OR to_id = ?)"
                result = await self._execute_write(decay_query, (memory_id, memory_id))
            else:
                result = await self._execute_write(decay_query)

            await self.conn.commit()

            # Get count of updated relationships
            count_query = "SELECT changes() as change_count"
            count_result = await self._execute_sql(count_query)
            updated_count = count_result[0]["change_count"] if count_result else 0

            logger.info(f"Applied confidence decay to {updated_count} relationships")
            return updated_count

        except aiosqlite.Error as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to apply confidence decay: {e}")
        except Exception as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to apply confidence decay: {str(e)}")

    async def adjust_confidence(
        self, relationship_id: str, new_confidence: float, reason: str
    ) -> None:
        """
        Manually adjust confidence of a relationship.

        Args:
            relationship_id: ID of the relationship to adjust
            new_confidence: New confidence value (0.0-1.0)
            reason: Reason for the adjustment

        Raises:
            BackendError: If database operation fails
            ValidationError: If new_confidence is out of range
        """
        if new_confidence < 0.0 or new_confidence > 1.0:
            raise ValidationError(
                f"Confidence must be between 0.0 and 1.0, got {new_confidence}"
            )

        try:
            update_query = """
                UPDATE relationships
                SET confidence = ?
                WHERE id = ?
            """
            await self._execute_write(update_query, (new_confidence, relationship_id))

            await self.conn.commit()
            logger.info(
                f"Adjusted confidence for relationship {relationship_id} to {new_confidence}: {reason}"
            )

        except aiosqlite.Error as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to adjust confidence: {e}")
        except Exception as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to adjust confidence: {str(e)}")

    async def set_decay_factor(
        self, memory_id: str, decay_factor: float, reason: str = ""
    ) -> int:
        """
        Set a custom decay factor for all relationships of a memory.

        Unlike apply_confidence_decay(), this method sets the stored
        decay_factor column directly without recalculating it from tags or
        importance.  The new value will be used by future decay runs.

        Args:
            memory_id: ID of the memory whose relationships are updated
            decay_factor: New decay factor (0.0-1.0; 1.0 = no decay)
            reason: Optional reason for audit logging

        Returns:
            Number of relationships updated

        Raises:
            ValidationError: If decay_factor is out of range
            BackendError: If database operation fails
        """
        if decay_factor < 0.0 or decay_factor > 1.0:
            raise ValidationError(
                f"Decay factor must be between 0.0 and 1.0, got {decay_factor}"
            )

        try:
            update_query = """
                UPDATE relationships
                SET decay_factor = ?
                WHERE from_id = ? OR to_id = ?
            """
            await self._execute_write(update_query, (decay_factor, memory_id, memory_id))
            await self.conn.commit()

            count_result = await self._execute_sql("SELECT changes() as n")
            updated = count_result[0]["n"] if count_result else 0
            logger.info(
                f"Set decay_factor={decay_factor} for {updated} relationships "
                f"of memory {memory_id}: {reason}"
            )
            return updated

        except aiosqlite.Error as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to set decay factor: {e}")
        except Exception as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to set decay factor: {str(e)}")


    async def get_low_confidence_relationships(
        self, threshold: float = 0.3, limit: int = 50
    ) -> List[Relationship]:
        """
        Get relationships with confidence below threshold.

        Args:
            threshold: Confidence threshold (default: 0.3)
            limit: Maximum number of results to return

        Returns:
            List of low confidence relationships

        Raises:
            BackendError: If database operation fails
        """
        try:
            query = """
                SELECT id, from_id, to_id, rel_type, properties,
                       created_at,
                       confidence, last_accessed, access_count, decay_factor
                FROM relationships
                WHERE confidence < ?
                ORDER BY confidence ASC, last_accessed ASC
                LIMIT ?
            """

            results = await self._execute_sql(query, (threshold, limit))

            relationships = []
            for row in results:
                try:
                    properties = json.loads(row["properties"])
                    rel_type = RelationshipType(row["rel_type"])

                    def parse_date(date_str):
                        if not date_str:
                            return None
                        try:
                            return datetime.fromisoformat(date_str)
                        except (ValueError, TypeError):
                            return None

                    created_at = parse_date(row["created_at"]) or datetime.now(
                        timezone.utc
                    )

                    # Parse confidence system fields
                    confidence = (
                        float(row["confidence"])
                        if row["confidence"] is not None
                        else 0.8
                    )
                    last_accessed = parse_date(row["last_accessed"]) or datetime.now(
                        timezone.utc
                    )
                    access_count = (
                        int(row["access_count"])
                        if row["access_count"] is not None
                        else 0
                    )
                    decay_factor = (
                        float(row["decay_factor"])
                        if row["decay_factor"] is not None
                        else 0.95
                    )

                    # Update properties with confidence system fields
                    properties.update(
                        {
                            "confidence": confidence,
                            "last_accessed": last_accessed,
                            "access_count": access_count,
                            "decay_factor": decay_factor,
                        }
                    )

                    relationship = Relationship(
                        id=row["id"],
                        from_memory_id=row["from_id"],
                        to_memory_id=row["to_id"],
                        type=rel_type,
                        properties=RelationshipProperties(**properties),
                        created_at=created_at,
                    )
                    relationships.append(relationship)
                except Exception as e:
                    logger.warning(f"Failed to parse relationship {row['id']}: {e}")

            return relationships

        except aiosqlite.Error as e:
            raise BackendError(f"Failed to get low confidence relationships: {e}")
        except Exception as e:
            raise BackendError(f"Failed to get low confidence relationships: {str(e)}")

    async def get_memory_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the memory database.

        Returns:
            Dictionary containing various statistics about the database

        Raises:
            BackendError: If database operation fails
        """
        try:
            # Get total memories count
            total_memories_query = (
                "SELECT COUNT(*) as count FROM nodes WHERE label = 'Memory'"
            )
            total_memories_result = await self._execute_sql(total_memories_query)
            total_memories = (
                total_memories_result[0]["count"] if total_memories_result else 0
            )

            # Get memories by type
            memories_by_type_query = """
                SELECT
                    json_extract(properties, '$.type') as type,
                    COUNT(*) as count
                FROM nodes
                WHERE label = 'Memory'
                GROUP BY json_extract(properties, '$.type')
            """
            memories_by_type_result = await self._execute_sql(memories_by_type_query)
            memories_by_type = (
                {row["type"]: row["count"] for row in memories_by_type_result}
                if memories_by_type_result
                else {}
            )

            # Get total relationships count
            total_relationships_query = "SELECT COUNT(*) as count FROM relationships"
            total_relationships_result = await self._execute_sql(
                total_relationships_query
            )
            total_relationships = (
                total_relationships_result[0]["count"]
                if total_relationships_result
                else 0
            )

            # Get average importance
            avg_importance_query = """
                SELECT AVG(CAST(json_extract(properties, '$.importance') AS REAL)) as avg_importance
                FROM nodes
                WHERE label = 'Memory'
                AND json_extract(properties, '$.importance') IS NOT NULL
            """
            avg_importance_result = await self._execute_sql(avg_importance_query)
            avg_importance = (
                avg_importance_result[0]["avg_importance"]
                if avg_importance_result
                else 0.0
            )

            # Get average confidence from relationships
            avg_confidence_query = """
                SELECT AVG(CAST(json_extract(properties, '$.confidence') AS REAL)) as avg_confidence
                FROM relationships
                WHERE json_extract(properties, '$.confidence') IS NOT NULL
            """
            avg_confidence_result = await self._execute_sql(avg_confidence_query)
            avg_confidence = (
                avg_confidence_result[0]["avg_confidence"]
                if avg_confidence_result
                else 0.0
            )

            # Get database file size if available
            db_file_size = None
            try:
                if hasattr(self.backend, "db_path"):
                    db_path = Path(self.backend.db_path)
                    if db_path.exists():
                        db_file_size = db_path.stat().st_size
            except Exception:
                pass

            return {
                "total_memories": {"count": total_memories},
                "memories_by_type": memories_by_type,
                "total_relationships": {"count": total_relationships},
                "avg_importance": {
                    "avg_importance": float(avg_importance) if avg_importance else 0.0
                },
                "avg_confidence": {
                    "avg_confidence": float(avg_confidence) if avg_confidence else 0.0
                },
                "database_file_size": db_file_size,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except aiosqlite.Error as e:
            raise BackendError(f"Failed to get memory statistics: {e}")
        except Exception as e:
            raise BackendError(f"Failed to get memory statistics: {str(e)}")
