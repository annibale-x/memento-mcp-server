"""
MCP Context Keeper - Model Context Protocol server for managing and persisting context across conversations.

A powerful MCP server that provides persistent memory and context management for AI assistants,
enabling them to remember information across conversations and sessions.
"""

__version__ = "0.1.0"
__author__ = "Hannibal"
__email__ = ""
__license__ = "MIT"

from .context_keeper import ContextKeeper
from .exceptions import (
    ContextKeeperError,
    MemoryNotFoundError,
    RelationshipNotFoundError,
)
from .models import Memory, MemoryContext, Relationship

__all__ = [
    "ContextKeeper",
    "Memory",
    "Relationship",
    "MemoryContext",
    "ContextKeeperError",
    "MemoryNotFoundError",
    "RelationshipNotFoundError",
]
