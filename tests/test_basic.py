"""Basic tests for MCP Context Keeper."""

import pytest
from mcp_context_keeper import ContextKeeper, MemoryType


@pytest.mark.asyncio
async def test_store_memory():
    """Test storing a memory."""
    keeper = ContextKeeper()
    memory = await keeper.store_memory(
        content="Test memory content",
        memory_type=MemoryType.NOTE,
        title="Test Memory",
    )
    
    assert memory.content == "Test memory content"
    assert memory.type == MemoryType.NOTE
    assert memory.title == "Test Memory"


@pytest.mark.asyncio
async def test_recall_memories():
    """Test recalling memories."""
    keeper = ContextKeeper()
    memories = await keeper.recall_memories("test query")
    
    assert isinstance(memories, list)
    assert len(memories) == 0  # Empty for now
