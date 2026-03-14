"""
SQLite database implementation for Context Keeper.

This module provides a simplified SQLiteMemoryDatabase class that handles
all memory and relationship operations directly with SQLite.
"""

import json
import logging
import re
import sqlite3
import aiosqlite
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

    async def _execute_sql(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
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
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
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

        Args:
            memory: Memory object to store

        Returns:
            Stored memory with updated metadata

        Raises:
            ValidationError: If memory validation fails
            BackendError: If database operation fails
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
                "context": memory.context.model_dump() if memory.context else {},
                "version": 1,
                "created_at": memory.created_at.isoformat()
                if memory.created_at
                else datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Insert into nodes table
            query = """
                INSERT INTO nodes (id, label, properties)
                VALUES (?, ?, ?)
            """
            await self._execute_write(query, (memory.id, "Memory", json.dumps(properties)))

            # Update FTS table if available
            if self.backend.supports_fulltext_search():
                try:
                    fts_query = """
                        INSERT INTO nodes_fts (rowid, id, title, content, summary)
                        VALUES (?, ?, ?, ?, ?)
                    """
                    async with self.conn.execute("SELECT last_insert_rowid()") as cursor:
                        row = await cursor.fetchone()
                        rowid = row[0]
                    await self._execute_write(
                        fts_query,
                        (
                            rowid,
                            memory.id,
                            memory.title or "",
                            memory.content or "",
                            memory.summary or "",
                        ),
                    )
                except aiosqlite.Error as e:
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

    async def get_memory_by_id(self, memory_id: str) -> Optional[Memory]:
        """
        Retrieve a memory by its ID.

        Args:
            memory_id: Memory ID

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
            return self._properties_to_memory(memory_id, properties)

        except aiosqlite.Error as e:
            raise BackendError(f"Failed to get memory: {e}")
        except Exception as e:
            raise BackendError(f"Failed to get memory: {str(e)}")

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
            current_properties = json.loads(
                await self._execute_sql(
                    "SELECT properties FROM nodes WHERE id = ? AND label = 'Memory'",
                    (memory.id,),
                )[0]["properties"]
            )
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
            await self._execute_write(query, (json.dumps(properties), memory.id))

            # Update FTS table if available
            if self.backend.supports_fulltext_search():
                try:
                    fts_query = """
                        UPDATE nodes_fts
                        SET title = ?, content = ?, summary = ?
                        WHERE id = ?
                    """
                    await self._execute_write(
                        fts_query,
                        (
                            memory.title or "",
                            memory.content or "",
                            memory.summary or "",
                            memory.id,
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
            ORDER BY rank
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
            # Simple pattern matching on title and content
            where_clauses.append("""
                (json_extract(properties, '$.title') LIKE ?
                 OR json_extract(properties, '$.content') LIKE ?
                 OR json_extract(properties, '$.summary') LIKE ?)
            """)
            pattern = f"%{query.query}%"
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
            ORDER BY json_extract(properties, '$.updated_at') DESC
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

        Args:
            query: Raw search query

        Returns:
            FTS5-compatible query string
        """
        # Remove special characters and split into terms
        terms = re.findall(r"\b\w+\b", query.lower())

        # Join with AND operator for FTS5
        if not terms:
            return "*"  # Match all

        # Use phrase search for multi-word queries
        if len(terms) > 1:
            return f'"{query}"'

        # Single term with prefix matching
        return f"{terms[0]}*"

    # Relationship operations

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
            if not Config.ALLOW_CYCLES:
                await self._check_for_cycles(relationship)

            # Prepare properties JSON (exclude temporal fields, keep them only as columns)
            # Prepare properties dict
            props_dict = relationship.properties.model_dump()

            # Handle temporal fields
            valid_from = relationship.properties.valid_from.isoformat() if relationship.properties.valid_from else datetime.now(timezone.utc).isoformat()
            valid_until = relationship.properties.valid_until.isoformat() if relationship.properties.valid_until else None
            recorded_at = relationship.properties.recorded_at.isoformat() if relationship.properties.recorded_at else datetime.now(timezone.utc).isoformat()
            created_at = relationship.properties.created_at.isoformat() if relationship.properties.created_at else datetime.now(timezone.utc).isoformat()
            invalidated_by = relationship.properties.invalidated_by

            # Insert into relationships table
            query = """
                INSERT INTO relationships (
                    id, from_id, to_id, rel_type, properties, created_at,
                    valid_from, valid_until, recorded_at, invalidated_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            # Serialize props with correct datetimes
            for k, v in props_dict.items():
                if isinstance(v, datetime):
                    props_dict[k] = v.isoformat()
            
            await self._execute_write(
                query,
                (
                    relationship.id,
                    relationship.from_memory_id,
                    relationship.to_memory_id,
                    relationship.type.value,
                    json.dumps(props_dict),
                    created_at,
                    valid_from,
                    valid_until,
                    recorded_at,
                    invalidated_by,
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
                       created_at, valid_from, valid_until, recorded_at, invalidated_by
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

                    created_at = parse_date(row["created_at"]) or datetime.now(timezone.utc)
                    valid_from = parse_date(row["valid_from"]) or datetime.now(timezone.utc)
                    valid_until = parse_date(row["valid_until"])
                    recorded_at = parse_date(row["recorded_at"]) or datetime.now(timezone.utc)

                    relationship = Relationship(
                        id=row["id"],
                        from_memory_id=row["from_id"],
                        to_memory_id=row["to_id"],
                        type=rel_type,
                        properties=RelationshipProperties(
                            strength=properties.get("strength", 0.5),
                            confidence=properties.get("confidence", 0.8),
                            context=properties.get("context", ""),
                            evidence_count=properties.get("evidence_count", 1),
                            success_rate=properties.get("success_rate", None),
                            validation_count=properties.get("validation_count", 0),
                            counter_evidence_count=properties.get("counter_evidence_count", 0),
                            created_at=created_at,
                            valid_from=valid_from,
                            valid_until=valid_until,
                            recorded_at=recorded_at,
                            last_validated=parse_date(properties.get("last_validated")) or datetime.now(timezone.utc),
                            invalidated_by=row["invalidated_by"],
                        ),
                    )
                    relationships.append(relationship)
                except Exception as e:
                    logger.warning(f"Failed to parse relationship {row['id']}: {e}")

            return relationships

        except aiosqlite.Error as e:
            raise BackendError(f"Failed to get relationships: {e}")
        except Exception as e:
            raise BackendError(f"Failed to get relationships: {str(e)}")

    async def delete_relationship(self, relationship_id: str) -> bool:
        """
        Delete a relationship by its ID.

        Args:
            relationship_id: Relationship ID

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

    async def invalidate_relationship(self, relationship_id: str, invalidated_by: str = None) -> None:
        """
        Invalidate a relationship by setting valid_until to now.

        Args:
            relationship_id: ID of the relationship to invalidate
            invalidated_by: Optional ID of relationship that supersedes this one

        Raises:
            BackendError: If database operation fails
        """
        try:
            # Check if relationship exists
            query = "SELECT id FROM relationships WHERE id = ?"
            result = await self._execute_sql(query, (relationship_id,))

            if not result:
                raise BackendError(f"Relationship not found: {relationship_id}")

            # Set valid_until to now
            now = datetime.now(timezone.utc).isoformat()
            update_query = """
                UPDATE relationships
                SET valid_until = ?, invalidated_by = ?
                WHERE id = ?
            """
            await self._execute_write(update_query, (now, invalidated_by, relationship_id))

            await self.conn.commit()
            logger.info(f"Invalidated relationship: {relationship_id}")

        except aiosqlite.Error as e:
            await self.conn.rollback()
            raise BackendError(f"Failed to invalidate relationship: {e}")
        except Exception as e:
            await self.conn.rollback()
            if isinstance(e, BackendError):
                raise
            raise BackendError(f"Failed to invalidate relationship: {str(e)}")

    async def get_relationship_history(
        self,
        memory_id: str,
        relationship_types: List[RelationshipType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Relationship]:
        """
        Get full history of relationships for a memory, including invalidated ones.

        Args:
            memory_id: ID of the memory to get history for
            relationship_types: Optional filter by relationship types
            limit: Maximum number of results to return (default: 100)
            offset: Number of results to skip for pagination (default: 0)

        Returns:
            List of Relationship objects, ordered chronologically by valid_from

        Raises:
            BackendError: If database operation fails
        """
        try:
            # Build query
            where_conditions = ["(from_id = ? OR to_id = ?)"]
            params = [memory_id, memory_id]

            if relationship_types:
                type_placeholders = ",".join("?" * len(relationship_types))
                where_conditions.append(f"rel_type IN ({type_placeholders})")
                params.extend([rt.value for rt in relationship_types])

            where_clause = " AND ".join(where_conditions)

            query = f"""
                SELECT
                    id, from_id, to_id, rel_type, properties,
                    created_at, valid_from, valid_until, recorded_at, invalidated_by
                FROM relationships
                WHERE {where_clause}
                ORDER BY valid_from ASC
                LIMIT ? OFFSET ?
            """

            params.extend([limit, offset])
            results = await self._execute_sql(query, tuple(params))

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
                    
                    created_at = parse_date(row["created_at"]) or datetime.now(timezone.utc)
                    valid_from = parse_date(row["valid_from"]) or datetime.now(timezone.utc)
                    valid_until = parse_date(row["valid_until"])
                    recorded_at = parse_date(row["recorded_at"]) or datetime.now(timezone.utc)

                    relationship = Relationship(
                        id=row["id"],
                        from_memory_id=row["from_id"],
                        to_memory_id=row["to_id"],
                        type=rel_type,
                        properties=RelationshipProperties(
                            strength=properties.get("strength", 0.5),
                            confidence=properties.get("confidence", 0.8),
                            context=properties.get("context", ""),
                            evidence_count=properties.get("evidence_count", 1),
                            success_rate=properties.get("success_rate", None),
                            validation_count=properties.get("validation_count", 0),
                            counter_evidence_count=properties.get("counter_evidence_count", 0),
                            created_at=created_at,
                            valid_from=valid_from,
                            valid_until=valid_until,
                            recorded_at=recorded_at,
                            last_validated=parse_date(properties.get("last_validated")) or datetime.now(timezone.utc),
                            invalidated_by=row["invalidated_by"],
                        ),
                    )
                    relationships.append(relationship)
                except Exception as e:
                    logger.warning(f"Failed to parse relationship {row['id']}: {e}")

            logger.info(f"Found {len(relationships)} relationships in history for {memory_id}")
            return relationships

        except aiosqlite.Error as e:
            raise BackendError(f"Failed to get relationship history: {e}")
        except Exception as e:
            raise BackendError(f"Failed to get relationship history: {str(e)}")

    async def what_changed(self, since: datetime) -> Dict[str, List[Relationship]]:
        """
        Get all relationship changes since a given time.

        Args:
            since: DateTime to query changes from

        Returns:
            Dictionary with "new_relationships" and "invalidated_relationships" lists

        Raises:
            BackendError: If database operation fails
        """
        try:
            since_str = since.isoformat()

            # Query for new relationships (recorded_at >= since)
            new_query = """
                SELECT
                    id, from_id, to_id, rel_type, properties,
                    created_at, valid_from, valid_until, recorded_at, invalidated_by
                FROM relationships
                WHERE recorded_at >= ?
                ORDER BY recorded_at DESC
            """
            new_results = await self._execute_sql(new_query, (since_str,))

            # Query for invalidated relationships (valid_until set since)
            invalidated_query = """
                SELECT
                    id, from_id, to_id, rel_type, properties,
                    created_at, valid_from, valid_until, recorded_at, invalidated_by
                FROM relationships
                WHERE valid_until IS NOT NULL AND valid_until >= ?
                ORDER BY valid_until DESC
            """
            invalidated_results = await self._execute_sql(invalidated_query, (since_str,))

            def _parse_relationships(results):
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
                        
                        created_at = parse_date(row["created_at"]) or datetime.now(timezone.utc)
                        valid_from = parse_date(row["valid_from"]) or datetime.now(timezone.utc)
                        valid_until = parse_date(row["valid_until"])
                        recorded_at = parse_date(row["recorded_at"]) or datetime.now(timezone.utc)

                        relationship = Relationship(
                            id=row["id"],
                            from_memory_id=row["from_id"],
                            to_memory_id=row["to_id"],
                            type=rel_type,
                            strength=properties.get("strength", 0.5),
                            confidence=properties.get("confidence", 0.8),
                            context=properties.get("context", ""),
                            created_at=created_at,
                            valid_from=valid_from,
                            valid_until=valid_until,
                            recorded_at=recorded_at,
                            invalidated_by=row["invalidated_by"],
                        )
                        relationships.append(relationship)
                    except Exception as e:
                        logger.warning(f"Failed to parse relationship {row['id']}: {e}")
                return relationships

            new_relationships = _parse_relationships(new_results)
            invalidated_relationships = _parse_relationships(invalidated_results)

            logger.info(
                f"Found {len(new_relationships)} new and {len(invalidated_relationships)} invalidated relationships since {since}"
            )
            return {
                "new_relationships": new_relationships,
                "invalidated_relationships": invalidated_relationships,
            }

        except aiosqlite.Error as e:
            raise BackendError(f"Failed to get changes: {e}")
        except Exception as e:
            raise BackendError(f"Failed to get changes: {str(e)}")

    async def get_recent_activity(self, days: int = 7, project: Optional[str] = None) -> Dict[str, Any]:
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
                where_conditions.append("json_extract(properties, '$.context_project_path') = ?")
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
            memories_by_type = {row["type"]: row["count"] for row in type_result} if type_result else {}

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
                            AND (r.valid_until IS NULL OR r.valid_until > CURRENT_TIMESTAMP)
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
