"""
Tool registry for MCP Memento server.

This module maps MCP tool names to their handler functions. The registry
pattern allows for clean separation between tool definitions and implementations.

To add a new tool:
1. Create the handler function in the appropriate module under tools/
2. Add the mapping to TOOL_HANDLERS dictionary
3. Add the tool definition to the server's tool collection

Tool handlers receive a ToolContext and kwargs from the tool call,
and return the result to be sent back to the MCP client.
"""

from typing import Any, Awaitable, Callable, Dict

from mcp.types import CallToolResult

from .activity_tools import (
    handle_get_memento_statistics,
    handle_get_recent_memento_activity,
    handle_search_memento_relationships_by_context,
)
from .confidence_tools import (
    handle_adjust_memento_confidence,
    handle_apply_memento_confidence_decay,
    handle_boost_memento_confidence,
    handle_get_low_confidence_mementos,
    handle_set_memento_decay_factor,
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

# Type alias for tool handlers
ToolHandler = Callable[[Any, Dict[str, Any]], Awaitable[CallToolResult]]

# Registry mapping tool names to handlers
TOOL_HANDLERS: Dict[str, ToolHandler] = {
    "store_memento": handle_store_memento,
    "get_memento": handle_get_memento,
    "update_memento": handle_update_memento,
    "delete_memento": handle_delete_memento,
    "search_mementos": handle_search_mementos,
    "recall_mementos": handle_recall_mementos,
    "contextual_memento_search": handle_contextual_memento_search,
    "create_memento_relationship": handle_create_memento_relationship,
    "get_related_mementos": handle_get_related_mementos,
    "get_memento_statistics": handle_get_memento_statistics,
    "memento_onboarding": handle_memento_onboarding,
    "get_recent_memento_activity": handle_get_recent_memento_activity,
    "search_memento_relationships_by_context": handle_search_memento_relationships_by_context,
    # Confidence system tools
    "adjust_memento_confidence": handle_adjust_memento_confidence,
    "get_low_confidence_mementos": handle_get_low_confidence_mementos,
    "apply_memento_confidence_decay": handle_apply_memento_confidence_decay,
    "boost_memento_confidence": handle_boost_memento_confidence,
    "set_memento_decay_factor": handle_set_memento_decay_factor,
}


def get_handler(tool_name: str) -> ToolHandler | None:
    """
    Get handler function for a tool by name.

    Args:
        tool_name: Name of the MCP tool to get handler for

    Returns:
        Handler function if found, None otherwise

    Example:
        handler = get_handler("store_memory")
        if handler:
            result = await handler(context, kwargs)
    """
    return TOOL_HANDLERS.get(tool_name)


def register_handler(tool_name: str, handler: ToolHandler) -> None:
    """
    Register a handler function for a tool name.

    Args:
        tool_name: Name of the MCP tool
        handler: Handler function to register
    """
    TOOL_HANDLERS[tool_name] = handler


def clear_handlers() -> None:
    """
    Clear all registered tool handlers.
    """
    TOOL_HANDLERS.clear()
