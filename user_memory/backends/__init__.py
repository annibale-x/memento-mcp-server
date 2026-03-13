"""
Backend abstraction layer for MemoryGraph MCP Server.

This package provides a unified interface for SQLite backend,
enabling the memory server to work with SQLite for persistence
and NetworkX for graph operations.
"""

from .base import GraphBackend
from .factory import BackendFactory
from .sqlite_fallback import SQLiteFallbackBackend

# Backend classes are imported explicitly for SQLite backend
# Import them explicitly when needed:
#   from memorygraph.backends.sqlite_fallback import SQLiteFallbackBackend

__all__ = [
    "GraphBackend",
    "BackendFactory",
    "SQLiteFallbackBackend",
]
