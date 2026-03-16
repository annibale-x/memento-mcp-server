"""
Tool handlers for the MCP server.

This package contains modular tool handlers organized by functionality:
- memory_tools: CRUD operations for memories
- relationship_tools: Create and query relationships
- search_tools: Search, recall, and contextual search for memories
- activity_tools: Activity summaries and statistics
- guide_tools: Guidance and best practices for persistent memory usage
"""

from .activity_tools import (
    handle_get_memory_statistics,
    handle_get_recent_activity,
    handle_search_relationships_by_context,
)
from .guide_tools import (
    handle_help_memory_tools_usage,
)
from .memory_tools import (
    handle_delete_memory,
    handle_get_memory,
    handle_store_memory,
    handle_update_memory,
)
from .relationship_tools import (
    handle_create_relationship,
    handle_get_related_memories,
)
from .search_tools import (
    handle_contextual_search,
    handle_recall_memories,
    handle_search_memories,
)

__all__ = [
    # Memory CRUD operations
    "handle_store_memory",
    "handle_get_memory",
    "handle_update_memory",
    "handle_delete_memory",
    # Relationship operations
    "handle_create_relationship",
    "handle_get_related_memories",
    # Search operations
    "handle_search_memories",
    "handle_recall_memories",
    "handle_contextual_search",
    # Activity and statistics
    "handle_get_memory_statistics",
    "handle_get_recent_activity",
    "handle_search_relationships_by_context",
    # Guide tools
    "handle_help_memory_tools_usage",
]
