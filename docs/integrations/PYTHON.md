# Python Integration Guide

This guide covers how to integrate and use Memento as a Python library for programmatic access, custom agents, and advanced automation scenarios.

## Table of Contents
- [Quick Start](#quick-start)
- [Basic Usage](#basic-usage)
- [API Reference](#api-reference)
- [Custom Agents](#custom-agents)
- [Advanced Patterns](#advanced-patterns)
- [Error Handling](#error-handling)
- [Performance Tips](#performance-tips)
- [Examples](#examples)

## Quick Start

### Installation
```bash
# Install Memento
pip install mcp-memento

# Or install with development dependencies
pip install mcp-memento[dev]
```

### Basic Example
```python
import asyncio
from memento import Memento

async def main():
    # Initialize Memento
    server = Memento()
    await server.initialize()
    
    # Store a memory
    memory_id = await server.store_memory(
        type="solution",
        title="Fixed database connection timeout",
        content="Increased timeout to 30s and added connection pooling...",
        tags=["database", "timeout", "production"],
        importance=0.8
    )
    
    print(f"Stored memory with ID: {memory_id}")
    
    # Search for memories
    results = await server.recall_mementos(
        query="database timeout solutions",
        limit=5
    )
    
    for result in results:
        print(f"Found: {result['title']} (confidence: {result['confidence']:.2f})")
    
    # Cleanup
    await server.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

## Basic Usage

### Initialization
```python
import asyncio
from memento import Memento, Config

async def initialize_memento():
    # Method 1: Default initialization
    server1 = Memento()
    await server1.initialize()
    
    # Method 2: With custom configuration
    config = Config(
        sqlite_path="~/custom/path/memento.db",
        tool_profile="extended",
        log_level="INFO"
    )
    server2 = Memento(config=config)
    await server2.initialize()
    
    # Method 3: With environment variables
    import os
    os.environ["MEMENTO_SQLITE_PATH"] = "~/env/path/memento.db"
    os.environ["MEMENTO_TOOL_PROFILE"] = "advanced"
    
    server3 = Memento()
    await server3.initialize()
    
    return server1, server2, server3
```

### Memory Operations

#### Store Memories
```python
async def store_examples(server):
    # Basic memory storage
    memory_id = await server.store_memory(
        type="solution",
        title="API rate limiting implementation",
        content="Implemented token bucket algorithm with Redis...",
        tags=["api", "rate-limiting", "redis"],
        importance=0.7
    )
    
    # With custom ID
    custom_id = await server.store_memory(
        id="custom-auth-pattern-001",
        type="pattern",
        title="JWT authentication pattern",
        content="Standard JWT implementation with refresh tokens...",
        tags=["auth", "jwt", "security"],
        importance=0.9
    )
    
    # Error memory
    error_id = await server.store_memory(
        type="error",
        title="Database deadlock in transaction",
        content="Occurs when multiple transactions access same rows...",
        tags=["database", "postgres", "deadlock", "error"],
        importance=0.6
    )
    
    return memory_id, custom_id, error_id
```

#### Retrieve Memories
```python
async def retrieve_examples(server):
    # Get specific memory
    memory = await server.get_memory("memory-id-here")
    print(f"Title: {memory.title}")
    print(f"Content: {memory.content[:100]}...")
    
    # Search with natural language
    results = await server.recall_mementos(
        query="how to handle authentication in microservices",
        limit=10,
        memory_types=["solution", "pattern"]
    )
    
    # Advanced search with filters
    filtered_results = await server.search_mementos(
        tags=["redis", "cache"],
        min_importance=0.5,
        memory_types=["solution"],
        limit=20
    )
    
    return results, filtered_results
```

#### Update and Delete
```python
async def update_examples(server, memory_id):
    # Update memory
    await server.update_memory(
        memory_id=memory_id,
        title="Updated: API rate limiting with distributed Redis",
        content="Enhanced implementation with cluster support...",
        tags=["api", "rate-limiting", "redis", "distributed"],
        importance=0.8
    )
    
    # Delete memory
    await server.delete_memory(memory_id)
    
    # Batch operations
    memories_to_delete = ["id1", "id2", "id3"]
    for memory_id in memories_to_delete:
        await server.delete_memory(memory_id)
```

### Relationship Management
```python
async def relationship_examples(server):
    # Create relationships
    relationship_id = await server.create_relationship(
        from_memory_id="auth-solution-001",
        to_memory_id="security-pattern-002",
        relationship_type="USES",
        strength=0.9,
        context="Authentication solution uses security pattern"
    )
    
    # Get related memories
    related = await server.get_related_memories(
        memory_id="auth-solution-001",
        relationship_types=["USES", "RELATED_TO"],
        max_depth=2
    )
    
    # Find connections between memories
    path = await server.find_path_between_memories(
        start_memory_id="problem-001",
        end_memory_id="solution-005",
        max_depth=3
    )
    
    return relationship_id, related, path
```

## API Reference

### Memento Class

#### Initialization
```python
class Memento:
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize Memento server.
        
        Args:
            config: Optional configuration object. If None, loads from
                   environment variables and configuration files.
        """
    
    async def initialize(self) -> None:
        """Initialize the server and database connection."""
    
    async def cleanup(self) -> None:
        """Clean up resources and close connections."""
```

#### Memory Operations
```python
async def store_memory(
    self,
    type: str,
    title: str,
    content: str,
    tags: Optional[List[str]] = None,
    importance: float = 0.5,
    id: Optional[str] = None
) -> str:
    """
    Store a new memory.
    
    Args:
        type: Memory type (solution, pattern, problem, error, fix, general)
        title: Descriptive title
        content: Detailed content
        tags: Optional list of tags
        importance: Importance score (0.0-1.0)
        id: Optional custom ID (auto-generated if not provided)
    
    Returns:
        Memory ID
    """

async def get_memory(self, memory_id: str) -> Memory:
    """
    Retrieve a specific memory.
    
    Args:
        memory_id: ID of the memory to retrieve
    
    Returns:
        Memory object
    """

async def update_memory(
    self,
    memory_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    tags: Optional[List[str]] = None,
    importance: Optional[float] = None
) -> None:
    """
    Update an existing memory.
    
    Args:
        memory_id: ID of memory to update
        title: New title (optional)
        content: New content (optional)
        tags: New tags (optional)
        importance: New importance (optional)
    """

async def delete_memory(self, memory_id: str) -> None:
    """
    Delete a memory.
    
    Args:
        memory_id: ID of memory to delete
    """
```

#### Search Operations
```python
async def recall_mementos(
    self,
    query: str,
    memory_types: Optional[List[str]] = None,
    limit: int = 20,
    offset: int = 0
) -> List[Dict]:
    """
    Search memories using natural language query.
    
    Args:
        query: Natural language search query
        memory_types: Filter by memory types
        limit: Maximum number of results
        offset: Pagination offset
    
    Returns:
        List of memory results with relevance scores
    """

async def search_mementos(
    self,
    tags: Optional[List[str]] = None,
    query: Optional[str] = None,
    memory_types: Optional[List[str]] = None,
    min_importance: float = 0.0,
    limit: int = 50,
    offset: int = 0
) -> List[Dict]:
    """
    Advanced search with filters.
    
    Args:
        tags: Filter by tags
        query: Text search query
        memory_types: Filter by memory types
        min_importance: Minimum importance score
        limit: Maximum number of results
        offset: Pagination offset
    
    Returns:
        List of memory results
    """
```

#### Relationship Operations
```python
async def create_relationship(
    self,
    from_memory_id: str,
    to_memory_id: str,
    relationship_type: str,
    strength: float = 1.0,
    context: Optional[str] = None
) -> str:
    """
    Create relationship between memories.
    
    Args:
        from_memory_id: Source memory ID
        to_memory_id: Target memory ID
        relationship_type: Type of relationship
        strength: Relationship strength (0.0-1.0)
        context: Optional context description
    
    Returns:
        Relationship ID
    """

async def get_related_memories(
    self,
    memory_id: str,
    relationship_types: Optional[List[str]] = None,
    max_depth: int = 1
) -> List[Dict]:
    """
    Get memories related to a specific memory.
    
    Args:
        memory_id: Source memory ID
        relationship_types: Filter by relationship types
        max_depth: Maximum relationship depth to traverse
    
    Returns:
        List of related memories with relationship info
    """
```

#### Statistics and Analytics
```python
async def get_statistics(self) -> Dict:
    """
    Get database statistics.
    
    Returns:
        Dictionary with memory counts, relationship counts, etc.
    """

async def get_recent_activity(self, days: int = 7) -> Dict:
    """
    Get recent activity summary.
    
    Args:
        days: Number of days to look back
    
    Returns:
        Activity summary
    """

async def get_low_confidence_memories(
    self,
    threshold: float = 0.3,
    limit: int = 20
) -> List[Dict]:
    """
    Get memories with low confidence scores.
    
    Args:
        threshold: Confidence threshold (default: < 0.3)
        limit: Maximum number of results
    
    Returns:
        List of low confidence memories
    """
```

### Models

#### Memory Model
```python
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class Memory(BaseModel):
    """Memory model."""
    
    id: str
    type: str
    title: str
    content: str
    tags: List[str]
    importance: float
    confidence: float
    created_at: datetime
    updated_at: datetime
    accessed_at: Optional[datetime]
    
    class Config:
        from_attributes = True
```

#### Relationship Model
```python
class Relationship(BaseModel):
    """Relationship model."""
    
    id: str
    from_memory_id: str
    to_memory_id: str
    type: str
    strength: float
    confidence: float
    context: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True
```

#### Configuration Model
```python
class Config(BaseModel):
    """Configuration model."""
    
    sqlite_path: str = "~/.mcp-memento/context.db"
    tool_profile: str = "core"
    enable_advanced_tools: bool = False
    log_level: str = "INFO"
    allow_relationship_cycles: bool = False
    
    class Config:
        env_prefix = "MEMENTO_"
```

## Custom Agents

### Basic Agent Example
```python
import asyncio
from typing import List, Dict
from memento import Memento

class MementoAgent:
    """Custom agent with Memento integration."""
    
    def __init__(self, profile: str = "extended"):
        self.server = None
        self.profile = profile
    
    async def start(self):
        """Initialize the agent."""
        self.server = Memento()
        await self.server.initialize()
        print(f"Memento agent started with {self.profile} profile")
    
    async def process_query(self, query: str) -> Dict:
        """Process a user query with context from Memento."""
        # Search for relevant memories
        context = await self._gather_context(query)
        
        # Generate response using context
        response = await self._generate_response(query, context)
        
        # Store the interaction
        await self._store_interaction(query, response, context)
        
        return {
            "response": response,
            "context_memories": context,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _gather_context(self, query: str) -> List[Dict]:
        """Gather relevant context from Memento."""
        # First, try natural language search
        memories = await self.server.recall_mementos(
            query=query,
            limit=5,
            memory_types=["solution", "pattern"]
        )
        
        # If no results, try broader search
        if not memories:
            memories = await self.server.search_mementos(
                tags=self._extract_tags(query),
                limit=5
            )
        
        return memories
    
    async def _generate_response(self, query: str, context: List[Dict]) -> str:
        """Generate response using query and context."""
        # This is where you'd integrate with your LLM or logic
        # For example, using OpenAI API:
        # import openai
        # response = await openai.ChatCompletion.create(...)
        
        # Simplified example:
        if context:
            context_summary = "\n".join([
                f"- {m['title']} (confidence: {m['confidence']:.2f})"
                for m in context[:3]
            ])
            return f"Based on {len(context)} relevant memories:\n{context_summary}\n\nResponse to: {query}"
        else:
            return f"No relevant memories found. Response to: {query}"
    
    async def _store_interaction(self, query: str, response: str, context: List[Dict]):
        """Store the interaction in Memento."""
        interaction_id = await self.server.store_memory(
            type="conversation",
            title=f"Query: {query[:50]}...",
            content=f"Q: {query}\n\nA: {response}",
            tags=["interaction", "agent", "auto-stored"],
            importance=0.3
        )
        
        # Link to relevant context memories
        for memory in context[:3]:
            await self.server.create_relationship(
                from_memory_id=interaction_id,
                to_memory_id=memory["id"],
                relationship_type="REFERENCES",
                strength=0.7
            )
    
    async def stop(self):
        """Cleanup the agent."""
        if self.server:
            await self.server.cleanup()
        print("Memento agent stopped")

# Usage
async def main():
    agent = MementoAgent(profile="extended")
    await agent.start()
    
    response = await agent.process_query(
        "How should we handle database connection pooling?"
    )
    print(response["response"])
    
    await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### Advanced Agent with Confidence Management
```python
class ConfidenceAwareAgent(MementoAgent):
    """Agent that manages memory confidence."""
    
    async def process_query(self, query: str) -> Dict:
        """Process query with confidence-aware context gathering."""
        # Get context
        context = await self._gather_context(query)
        
        # Filter by confidence
        high_confidence = [m for m in context if m["confidence"] > 0.7]
        medium_confidence = [m for m in context if 0.4 <= m["confidence"] <= 0.7]
        
        # Generate response prioritizing high confidence memories
        response = await self._generate_confidence_aware_response(
            query, high_confidence, medium_confidence
        )
        
        # Boost confidence of used memories
        await self._boost_used_memories(high_confidence + medium_confidence)
        
        # Check for low confidence memories that might need review
        low_confidence = await self.server.get_low_confidence_memories(
            threshold=0.3,
            limit=5
        )
        
        if low_confidence:
            print(f"Warning: {len(low_confidence)} low confidence memories need review")
        
        return {
            "response": response,
            "high_confidence_context": high_confidence,
            "medium_confidence_context": medium_confidence,
            "low_confidence_warning": bool(low_confidence)
        }
    
    async def _boost_used_memories(self, memories: List[Dict]):
        """Boost confidence of memories that were used."""
        for memory in memories:
            try:
                await self.server.boost_memory_confidence(
                    memory_id=memory["id"],
                    boost_amount=0.05,
                    reason="Used in agent response"
                )
            except Exception as e:
                print(f"Failed to boost memory {memory['id']}: {e}")
```

## Advanced Patterns

### Batch Processing
```python
async def batch_operations(server):
    """Example of batch memory operations."""
    
    # Batch store
    memories_to_store = [
        {
            "type": "solution",
            "title": f"Solution {i}",
            "content": f"Content for solution {i}",
            "tags": ["batch", "test"],
            "importance": 0.5
        }
        for i in range(100)
    ]
    
    stored_ids = []
    for memory_data in memories_to_store:
        memory_id = await server.store_memory(**memory_data)
        stored_ids.append(memory_id)
    
    # Batch search with pagination
    all_results = []
    offset = 0
    limit = 20
    
    while True:
        results = await server.search_mementos(
            tags=["batch"],
            limit=limit,
            offset=offset
        )
            
        if not results:
            break
                
        all_results.extend(results)
        offset += limit
            
        if len(results) < limit:
            break
    
# Batch relationship creation
for i in range(len(stored_ids) - 1):
    await server.create_relationship(
        from_memory_id=stored_ids[i],
        to_memory_id=stored_ids[i + 1],
        relationship_type="RELATED_TO",
        strength=0.5
    )
    
return all_results
