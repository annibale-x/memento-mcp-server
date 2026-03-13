"""Main ContextKeeper class for MCP Context Keeper."""

from typing import List, Optional
from uuid import UUID

from .models import Memory, MemoryType


class ContextKeeper:
    """Main class for managing context and memories."""
    
    def __init__(self, db_path: str = "context_keeper.db"):
        """Initialize the context keeper."""
        self.db_path = db_path
    
    async def store_memory(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.NOTE,
        title: Optional[str] = None,
    ) -> Memory:
        """Store a new memory."""
        return Memory(
            content=content,
            type=memory_type,
            title=title,
        )
    
    async def recall_memories(self, query: str, limit: int = 5) -> List[Memory]:
        """Recall memories relevant to a query."""
        return []
