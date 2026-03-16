"""
Tool handlers for the MCP server.

This package contains modular tool handlers organized by functionality:
- memory_tools: CRUD operations for memories
- relationship_tools: Create and query relationships
- search_tools: Search, recall, and contextual search for memories
- activity_tools: Activity summaries and statistics
- guide_tools: Guidance and best practices for memento usage
"""

from .activity_tools import (
    handle_get_memento_statistics,
    handle_get_recent_memento_activity,
    handle_search_memento_relationships_by_context,
)
from .guide_tools import (
    handle_memento_onboarding,
)
from .memory_tools import (
    handle_delete_memento,
    handle_get_memento,
    handle_store_memento,
    handle_update_memento,
)
from .relationship_tools import (
    handle_create_memento_relationship,
    handle_get_related_mementos,
)
from .search_tools import (
    handle_contextual_memento_search,
    handle_recall_mementos,
    handle_search_mementos,
)

__all__ = [
    # Memory CRUD operations
    "handle_store_memento",
    "handle_get_memento",
    "handle_update_memento",
    "handle_delete_memento",
    # Relationship operations
    "handle_create_memento_relationship",
    "handle_get_related_mementos",
    # Search operations
    "handle_search_mementos",
    "handle_recall_mementos",
    "handle_contextual_memento_search",
    # Activity and statistics
    "handle_get_memento_statistics",
    "handle_get_recent_memento_activity",
    "handle_search_memento_relationships_by_context",
    # Guide tools
    "handle_memento_onboarding",
]
