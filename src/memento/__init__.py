"""
MCP Memento - Intelligent Memory Management System

A universal MCP server providing intelligent memory capabilities for AI assistants,
IDEs, CLI agents, and custom applications. Memento enables persistent knowledge
storage, relationship mapping, and confidence-based memory management across
multiple integration points.

Key Features:
- Cross-platform compatibility with major IDEs (Zed, Cursor, Windsurf, VSCode, Claude Desktop)
- CLI agent integration (Gemini CLI, Claude CLI, custom agents)
- Python API for programmatic usage
- REST API for HTTP integration
- SQLite backend for zero-dependency deployment
- Intelligent confidence system with automatic decay
- Relationship graph with 35+ relationship types
- Full-text search with fuzzy matching

Usage Examples:
1. IDE Integration: Configure in your IDE's MCP settings
2. CLI Agents: Use with gemini --mcp-servers memento
3. Python API: import memento; server = memento.Memento()
4. REST API: HTTP wrapper for external applications

For detailed documentation, see:
- README.md for quick start
- docs/integrations/ for specific integration guides
- docs/TOOLS.md for complete tool reference
"""

__version__ = "0.2.14"
__author__ = "Hannibal"
__email__ = "annibale.x@gmail.com"

from .models import (
    BackendError,
    ConfigurationError,
    DatabaseConnectionError,
    Memory,
    MemoryContext,
    MemoryError,
    MemoryNotFoundError,
    MemoryType,
    NotFoundError,
    Relationship,
    RelationshipError,
    RelationshipType,
    SchemaError,
    ToolError,
    ValidationError,
)
from .server import Memento

__all__ = [
    "Memento",
    "Memory",
    "MemoryType",
    "Relationship",
    "RelationshipType",
    "MemoryContext",
    "MemoryError",
    "MemoryNotFoundError",
    "RelationshipError",
    "ValidationError",
    "DatabaseConnectionError",
    "SchemaError",
    "NotFoundError",
    "BackendError",
    "ConfigurationError",
    "ToolError",
]
