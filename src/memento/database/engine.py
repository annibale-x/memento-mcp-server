"""
SQLite backend implementation for Memento.

This module provides a zero-dependency backend using SQLite for persistence.
This enables the Memento to work without requiring external database
servers or NetworkX.
"""

import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Optional

import aiosqlite

from ..config import Config
from ..models import DatabaseConnectionError, SchemaError
from .base import GraphBackend

logger = logging.getLogger(__name__)


class SQLiteBackend(GraphBackend):
    """SQLite implementation of the GraphBackend interface."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize SQLite backend.

        Args:
            db_path: Path to SQLite database file (defaults to ~/.mcp-memento/context.db)

        Raises:
            DatabaseConnectionError: If SQLite connection fails
        """
        db_path = db_path if db_path is not None else Config.DB_PATH
        # Expand tilde (~) to home directory
        self.db_path: str = os.path.expanduser(db_path)
        self.conn: Optional[aiosqlite.Connection] = None
        self._connected = False
        self._supports_fts = False

        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    async def connect(self) -> bool:
        """
        Establish connection to SQLite database and initialize graph.

        Returns:
            True if connection successful

        Raises:
            DatabaseConnectionError: If connection fails
        """
        try:
            self.conn = await aiosqlite.connect(self.db_path)
            self.conn.row_factory = aiosqlite.Row  # Enable column access by name
            self._connected = True

            # Enable WAL mode for concurrent access and better performance
            await self.conn.execute("PRAGMA journal_mode=WAL")
            await self.conn.execute("PRAGMA synchronous=NORMAL")
            await self.conn.execute("PRAGMA busy_timeout=5000")
            # Enable foreign key constraint enforcement (OFF by default in SQLite)
            await self.conn.execute("PRAGMA foreign_keys=ON")

            # Check FTS support once
            await self._check_fts_support()

            logger.info(f"Successfully connected to SQLite database at {self.db_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to SQLite: {e}")
            raise DatabaseConnectionError(f"Failed to connect to SQLite: {e}")

    async def disconnect(self) -> None:
        """Close the database connection."""
        if self.conn:
            await self.conn.close()
            self.conn = None
            self._connected = False
            logger.info("SQLite connection closed")

    async def refresh_fts_support(self) -> None:
        """
        Refresh FTS support detection.

        This should be called after recreating or modifying the FTS table
        to ensure the backend correctly detects FTS availability.
        """
        if not self._connected or not self.conn:
            raise DatabaseConnectionError("Cannot refresh FTS support: not connected")

        await self._check_fts_support()
        logger.info(f"FTS support refreshed: {self._supports_fts}")

    async def _check_fts_support(self) -> None:
        """Check if FTS table exists and is accessible."""
        try:
            async with self.conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='nodes_fts'"
            ) as cursor:
                result = await cursor.fetchone()
                table_exists = bool(result[0] > 0) if result else False

            # If table exists, try to query it to ensure it's not corrupted
            if table_exists:
                try:
                    async with self.conn.execute(
                        "SELECT COUNT(*) FROM nodes_fts"
                    ) as cursor:
                        await cursor.fetchone()
                    self._supports_fts = True
                except Exception as e:
                    if "no such column: T.title" in str(e):
                        logger.warning(
                            "FTS table exists but is corrupted (T.title error)"
                        )
                        self._supports_fts = False
                    else:
                        logger.warning(f"FTS table exists but query failed: {e}")
                        self._supports_fts = False
            else:
                self._supports_fts = False

        except Exception as e:
            logger.warning(f"Failed to check FTS support: {e}")
            self._supports_fts = False

    async def initialize_schema(self) -> None:
        """
        Initialize database schema including indexes.

        Raises:
            SchemaError: If schema initialization fails
        """
        logger.info("Initializing SQLite schema for MCP Memento...")

        if not self.conn:
            raise SchemaError("Schema operation failed: not connected to database")

        try:
            # Create nodes table
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    properties TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create relationships table (with confidence system fields)
            await self.conn.execute("""
                CREATE TABLE IF NOT EXISTS relationships (
                    id TEXT PRIMARY KEY,
                    from_id TEXT NOT NULL,
                    to_id TEXT NOT NULL,
                    rel_type TEXT NOT NULL,
                    properties TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,


                    -- Confidence system fields
                    confidence FLOAT DEFAULT 0.8,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    decay_factor FLOAT DEFAULT 0.95,

                    FOREIGN KEY (from_id) REFERENCES nodes(id) ON DELETE CASCADE,
                    FOREIGN KEY (to_id) REFERENCES nodes(id) ON DELETE CASCADE
                )
            """)

            # Create indexes
            await self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_nodes_label ON nodes(label)"
            )
            await self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_nodes_created ON nodes(created_at)"
            )
            await self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rel_from ON relationships(from_id)"
            )
            await self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rel_to ON relationships(to_id)"
            )
            await self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(rel_type)"
            )

            # Create FTS5 virtual table for full-text search
            try:
                await self.conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
                        id,
                        title,
                        content,
                        summary
                    )
                """)
                logger.debug("Created FTS5 table for full-text search")
            except Exception as e:
                logger.warning(
                    f"Could not create FTS5 table (may not be available): {e}"
                )

            # Version index for optimistic locking
            await self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_version
                ON nodes(json_extract(properties, '$.version'))
                WHERE label = 'Memory'
            """)

            await self.conn.commit()
            logger.info("Schema initialization completed")

        except Exception as e:
            await self.conn.rollback()
            raise SchemaError(f"Failed to initialize schema: {e}")

    async def health_check(self) -> dict[str, Any]:
        """
        Check backend health and return status information.

        Returns:
            Dictionary with health check results
        """
        health_info = {
            "connected": self._connected,
            "backend_type": "sqlite",
            "db_path": self.db_path,
        }

        if self._connected and self.conn:
            try:
                async with self.conn.execute(
                    "SELECT COUNT(*) FROM nodes WHERE label = 'Memory'"
                ) as cursor:
                    row = await cursor.fetchone()
                    count = row[0] if row else 0

                health_info["statistics"] = {"memory_count": count}

                # Get SQLite version
                async with self.conn.execute("SELECT sqlite_version()") as cursor:
                    row = await cursor.fetchone()
                    health_info["version"] = row[0] if row else "unknown"

                # Get database size
                db_size = (
                    os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                )
                health_info["database_size_bytes"] = db_size

            except Exception as e:
                logger.warning(f"Could not get detailed health info: {e}")
                health_info["warning"] = str(e)

        return health_info

    def backend_name(self) -> str:
        """Return the name of this backend implementation."""
        return "sqlite"

    def supports_fulltext_search(self) -> bool:
        """
        Check if this backend supports full-text search.

        Returns:
            True if FTS5 is available in SQLite
        """
        return self._supports_fts

    def supports_transactions(self) -> bool:
        """Check if this backend supports ACID transactions."""
        return True  # SQLite supports transactions

    @classmethod
    async def create(cls, db_path: Optional[str] = None) -> "SQLiteBackend":
        """
        Factory method to create and connect to a SQLite backend.

        Args:
            db_path: Path to SQLite database file

        Returns:
            Connected SQLiteBackend instance

        Raises:
            DatabaseConnectionError: If connection fails
        """
        backend = cls(db_path)
        await backend.connect()
        return backend
