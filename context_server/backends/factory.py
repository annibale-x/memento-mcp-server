"""
Backend factory for MemoryGraph MCP server.

This module provides a simplified factory that only supports SQLite backend
for the Zed editor integration.
"""

import logging
from typing import Union

from ..config import Config
from ..models import DatabaseConnectionError
from .base import GraphBackend
from .sqlite_fallback import SQLiteFallbackBackend

logger = logging.getLogger(__name__)


class BackendFactory:
    """
    Factory class for creating SQLite backend instances.

    This simplified factory only supports SQLite backend for use with
    Zed editor integration.
    """

    @staticmethod
    async def create_backend() -> GraphBackend:
        """
        Create and connect to SQLite backend.

        Returns:
            Connected SQLiteFallbackBackend instance

        Raises:
            DatabaseConnectionError: If SQLite backend cannot be connected
        """
        backend_type = Config.BACKEND.lower()

        # Only support sqlite backend
        if backend_type not in ["sqlite", "auto"]:
            logger.warning(
                f"Unsupported backend type: {backend_type}. "
                f"Only 'sqlite' is supported. Falling back to SQLite."
            )

        logger.info("Creating SQLite backend...")
        return await BackendFactory._create_sqlite()

    @staticmethod
    async def _create_sqlite() -> SQLiteFallbackBackend:
        """Create and initialize SQLite backend."""
        try:
            backend = SQLiteFallbackBackend()
            await backend.connect()

            # Initialize schema if needed
            await backend.initialize_schema()

            logger.info(
                f"SQLite backend connected successfully to: {Config.SQLITE_PATH}"
            )
            return backend
        except Exception as e:
            logger.error(f"Failed to connect to SQLite backend: {e}")
            raise DatabaseConnectionError(
                f"Failed to connect to SQLite backend at {Config.SQLITE_PATH}: {str(e)}"
            )

    @staticmethod
    def get_configured_backend_type() -> str:
        """
        Get the configured backend type.

        Returns:
            Always returns "sqlite" since only SQLite is supported
        """
        return "sqlite"

    @staticmethod
    def is_backend_configured(backend_type: str = "sqlite") -> bool:
        """
        Check if a backend is configured.

        Args:
            backend_type: Backend type to check (only "sqlite" is supported)

        Returns:
            True if SQLite is configured (always True for SQLite)
        """
        return backend_type == "sqlite"
