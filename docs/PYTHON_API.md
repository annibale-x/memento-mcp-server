# Python API Usage Guide

## Overview

The Memento Python API provides programmatic access to all MCP tool functionality, allowing you to integrate persistent memory management directly into your Python applications, scripts, or custom AI agents.

## Installation

```bash
pip install mcp-memento
```

## Basic Usage

### Import and Initialize

```python
from memento import Memento
import asyncio

async def main():
    # Create a Memento instance
    keeper = Memento()
    
    # Initialize the server (creates database connection)
    await keeper.initialize()
    
    # Access the database directly
    db = keeper.memory_db
    
    # Your code here...
    
    # Cleanup when done
    await keeper.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

### Configuration

```python
from memento import Memento
from memento.config import Config

async def main():
    # Create custom configuration
    config = Config(
        sqlite_path="~/custom_path/context.db",
        tool_profile="extended",
        enable_advanced_tools=True,
        log_level="INFO"
    )
    
    # Initialize with custom config
    keeper = Memento(config=config)
    await keeper.initialize()
    
    # Your code...
```

## Core Operations

### Storing Memories

```python
async def store_solution(keeper: Memento):
    tools = keeper.tools
    
    # Store a new memory
    memory_id = await tools["store_memento"](
        type="solution",
        title="Fixed Redis timeout with connection pooling",
        content="Increased connection timeout to 30s and added connection pooling...",
        tags=["redis", "timeout", "production_fix"],
        importance=0.8
    )
    
    print(f"Stored memory with ID: {memory_id}")
    return memory_id
```

### Retrieving Memories

```python
async def retrieve_memory(keeper: Memento, memory_id: str):
    tools = keeper.tools
    
    # Get a specific memory
    memory = await tools["get_memento"](
        memory_id=memory_id,
        include_relationships=True
    )
    
    print(f"Memory: {memory['title']}")
    print(f"Content: {memory['content'][:100]}...")
    
    if memory.get("relationships"):
        print(f"Related memories: {len(memory['relationships'])}")
    
    return memory
```

### Searching Memories

```python
async def search_memories(keeper: Memento, query: str):
    tools = keeper.tools
    
    # Natural language search
    results = await tools["recall_mementos"](
        query=query,
        limit=10,
        memory_types=["solution", "pattern"]
    )
    
    print(f"Found {len(results)} memories:")
    for memory in results:
        print(f"  - {memory['title']} (confidence: {memory.get('confidence', 'N/A')})")
    
    return results
```

### Advanced Search

```python
async def advanced_search(keeper: Memento):
    tools = keeper.tools
    
    # Tag-based search
    results = await tools["search_mementos"](
        tags=["redis", "performance"],
        min_importance=0.5,
        search_tolerance="strict",
        limit=20
    )
    
    # Contextual search within related memories
    contextual_results = await tools["contextual_memento_search"](
        memory_id="existing_memory_id",
        query="connection timeout",
        max_depth=2
    )
    
    return results, contextual_results
```

## Relationship Management

### Creating Relationships

```python
async def create_relationships(keeper: Memento):
    tools = keeper.tools
    
    # Link two memories
    relationship_id = await tools["create_memento_relationship"](
        from_memory_id="solution_123",
        to_memory_id="problem_456",
        relationship_type="SOLVES",
        strength=0.9,
        confidence=0.8,
        context="Production deployment confirmed fix"
    )
    
    print(f"Created relationship: {relationship_id}")
    return relationship_id
```

### Exploring Relationships

```python
async def explore_relationships(keeper: Memento, memory_id: str):
    tools = keeper.tools
    
    # Get related memories
    related = await tools["get_related_mementos"](
        memory_id=memory_id,
        relationship_types=["SOLVES", "CAUSES"],
        max_depth=3
    )
    
    print(f"Found {len(related)} related memories:")
    for memory, rel_type in related:
        print(f"  - {memory['title']} ({rel_type})")
    
    return related
```

## Confidence System

### Managing Confidence

```python
async def manage_confidence(keeper: Memento):
    tools = keeper.tools
    
    # Find low confidence memories
    low_conf = await tools["get_low_confidence_mementos"](
        threshold=0.3,
        limit=20
    )
    
    print(f"Found {len(low_conf)} low confidence memories")
    
    # Boost confidence for validated memories
    for memory in low_conf[:5]:  # First 5
        if validate_memory(memory):
            await tools["boost_memento_confidence"](
                memory_id=memory["id"],
                boost_amount=0.2,
                reason="Monthly verification passed"
            )
    
    # Apply automatic decay
    decay_results = await tools["apply_memento_confidence_decay"]()
    print(f"Applied decay to {decay_results['updated_count']} relationships")
    
    # Set custom decay factor for critical memories
    await tools["set_memento_decay_factor"](
        memory_id="critical_memory_123",
        decay_factor=1.0,  # No decay
        reason="Security-critical information"
    )
```

### Manual Confidence Adjustment

```python
async def adjust_confidence(keeper: Memento):
    tools = keeper.tools
    
    # Manual adjustment
    await tools["adjust_memento_confidence"](
        relationship_id="relationship_123",
        new_confidence=0.9,
        reason="Verified in production environment"
    )
```

## Analytics and Statistics

### Database Statistics

```python
async def get_statistics(keeper: Memento):
    tools = keeper.tools
    
    # Get overall statistics
    stats = await tools["get_memento_statistics"]()
    
    print(f"Total memories: {stats['memory_count']}")
    print(f"Total relationships: {stats['relationship_count']}")
    print(f"Memory types: {stats['memory_types']}")
    
    # Get recent activity
    recent = await tools["get_recent_memento_activity"](
        days=7,
        project="/current/project"
    )
    
    print(f"Recent memories: {recent['recent_memory_count']}")
    print(f"Unresolved problems: {len(recent['unresolved_problems'])}")
    
    return stats, recent
```

### Relationship Context Search

```python
async def search_relationship_context(keeper: Memento):
    tools = keeper.tools
    
    # Search by structured context
    results = await tools["search_memento_relationships_by_context"](
        scope="full",
        conditions=["production", "high-traffic"],
        evidence=["integration_tests", "load_tests"],
        components=["auth", "database"],
        has_evidence=True,
        limit=10
    )
    
    return results
```

## Advanced Features

### Graph Analysis

```python
async def graph_analysis(keeper: Memento):
    tools = keeper.tools
    
    # Find memory clusters
    clusters = await tools["find_memento_clusters"](
        min_cluster_size=3,
        similarity_threshold=0.6
    )
    
    # Analyze relationship patterns
    patterns = await tools["find_memento_patterns"](
        min_pattern_size=2,
        min_support=0.5
    )
    
    # Get graph analytics
    analytics = await tools["analyze_memento_graph"]()
    
    # Find central memories
    central = await tools["get_central_mementos"]()
    
    # Get complete network
    network = await tools["get_memento_network"]()
    
    return {
        "clusters": clusters,
        "patterns": patterns,
        "analytics": analytics,
        "central_memories": central,
        "network": network
    }
```

### Path Finding

```python
async def find_paths(keeper: Memento):
    tools = keeper.tools
    
    # Find shortest path between memories
    path = await tools["find_path_between_mementos"](
        from_memory_id="problem_123",
        to_memory_id="solution_456",
        max_depth=5,
        relationship_types=["SOLVES", "RELATED_TO"]
    )
    
    if path["found"]:
        print(f"Path found with {path['hops']} hops")
    else:
        print("No path found within max depth")
    
    return path
```

### Relationship Suggestions

```python
async def get_relationship_suggestions(keeper: Memento):
    tools = keeper.tools
    
    # Get intelligent suggestions
    suggestions = await tools["suggest_memento_relationships"](
        from_memory_id="memory_123",
        to_memory_id="memory_456"
    )
    
    print("Suggested relationship types:")
    for suggestion in suggestions:
        print(f"  - {suggestion['type']}: {suggestion['confidence']:.2f} confidence")
    
    return suggestions
```

## Examples

### Complete Example: Knowledge Base Manager

```python
import asyncio
from memento import Memento
from datetime import datetime

class KnowledgeBaseManager:
    def __init__(self, db_path: str = "~/.mcp-memento/context.db"):
        self.config = Config(sqlite_path=db_path, tool_profile="extended")
        self.keeper = None
    
    async def __aenter__(self):
        self.keeper = Memento(config=self.config)
        await self.keeper.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.keeper:
            await self.keeper.cleanup()
    
    async def store_solution(self, title: str, content: str, tags: list, context: dict = None):
        """Store a solution in the knowledge base."""
        tools = self.keeper.tools
        
        memory_id = await tools["store_memento"](
            type="solution",
            title=title,
            content=content,
            tags=tags,
            importance=0.7,
            context=context or {}
        )
        
        print(f"Stored solution: {title}")
        return memory_id
    
    async def find_solutions(self, problem: str, limit: int = 5):
        """Find solutions for a problem."""
        tools = self.keeper.tools
        
        # Search for related problems
        problems = await tools["recall_mementos"](
            query=problem,
            memory_types=["problem", "error"],
            limit=limit
        )
        
        solutions = []
        for problem_memory in problems:
            # Find solutions for each problem
            related = await tools["get_related_mementos"](
                memory_id=problem_memory["id"],
                relationship_types=["SOLVES"],
                max_depth=1
            )
            
            for solution, _ in related:
                solutions.append({
                    "problem": problem_memory["title"],
                    "solution": solution["title"],
                    "confidence": solution.get("confidence", 0.5)
                })
        
        return solutions
    
    async def get_insights(self, days: int = 30):
        """Get insights from recent activity."""
        tools = self.keeper.tools
        
        # Get statistics
        stats = await tools["get_memento_statistics"]()
        
        # Get recent activity
        recent = await tools["get_recent_memento_activity"](days=days)
        
        # Find patterns
        patterns = await tools["find_memento_patterns"](
            min_pattern_size=2,
            min_support=0.3
        )
        
        return {
            "stats": stats,
            "recent_activity": recent,
            "patterns": patterns
        }

async def main():
    async with KnowledgeBaseManager() as manager:
        # Store a solution
        solution_id = await manager.store_solution(
            title="Fixed memory leak in async context",
            content="Added proper cleanup in __aexit__ method...",
            tags=["python", "async", "memory", "fix"],
            context={"project": "async-worker"}
        )
        
        # Find solutions
        solutions = await manager.find_solutions("memory leak", limit=3)
        print(f"Found {len(solutions)} solutions")
        
        # Get insights
        insights = await manager.get_insights(days=7)
        print(f"Total memories: {insights['stats']['memory_count']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Example: Integration with Existing Codebase

```python
import asyncio
from memento import Memento
from typing import List, Dict, Any

class CodebaseAnalyzer:
    def __init__(self, keeper: Memento):
        self.keeper = keeper
    
    async def analyze_and_store_patterns(self, codebase_path: str):
        """Analyze codebase and store discovered patterns."""
        # This is a simplified example
        patterns = [
            {
                "type": "pattern",
                "title": "FastAPI dependency injection pattern",
                "content": "Use Depends() for service layer injection...",
                "tags": ["fastapi", "python", "dependency-injection"],
                "importance": 0.8
            },
            {
                "type": "solution",
                "title": "SQLAlchemy session management",
                "content": "Always use context managers for database sessions...",
                "tags": ["sqlalchemy", "database", "python"],
                "importance": 0.9
            }
        ]
        
        tools = self.keeper.tools
        stored_patterns = []
        
        for pattern in patterns:
            pattern_id = await tools["store_memento"](**pattern)
            stored_patterns.append(pattern_id)
        
        # Create relationships between patterns
        if len(stored_patterns) > 1:
            await tools["create_memento_relationship"](
                from_memory_id=stored_patterns[0],
                to_memory_id=stored_patterns[1],
                relationship_type="RELATED_TO",
                context="Both are backend patterns"
            )
        
        return stored_patterns
    
    async def find_relevant_patterns(self, task_description: str):
        """Find patterns relevant to a development task."""
        tools = self.keeper.tools
        
        results = await tools["recall_mementos"](
            query=task_description,
            memory_types=["pattern", "solution"],
            limit=5
        )
        
        return [
            {
                "title": r["title"],
                "content": r["content"][:200] + "..." if len(r["content"]) > 200 else r["content"],
                "confidence": r.get("confidence", 0.5)
            }
            for r in results
        ]

async def main():
    keeper = Memento()
    await keeper.initialize()
    
    analyzer = CodebaseAnalyzer(keeper)
    await analyzer.analyze_and_store_patterns("./src")
    
    # Find patterns for a task
    patterns = await analyzer.find_relevant_patterns("database connection management")
    for pattern in patterns:
        print(f"Pattern: {pattern['title']} (confidence: {pattern['confidence']:.2f})")
    
    await keeper.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

## Error Handling

### Basic Error Handling

```python
from memento.models import MemoryNotFoundError, ValidationError

async def safe_memory_operation(keeper: Memento, memory_id: str):
    tools = keeper.tools
    
    try:
        memory = await tools["get_memento"](memory_id=memory_id)
        return memory
    except MemoryNotFoundError:
        print(f"Memory {memory_id} not found")
        return None
    except ValidationError as e:
        print(f"Validation error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
```

### Tool Error Handling

```python
async def handle_tool_errors(keeper: Memento):
    tools = keeper.tools
    
    try:
        # This will fail if memory doesn't exist
        result = await tools["get_memento"](memory_id="nonexistent")
    except Exception as e:
        error_response = {
            "error": str(e),
            "type": type(e).__name__,
            "suggestion": "Check if memory ID is correct"
        }
        print(f"Tool error: {error_response}")
        return error_response
```

## Performance Tips

### Batch Operations

```python
async def batch_operations(keeper: Memento, memories: List[Dict]):
    """Store multiple memories efficiently."""
    tools = keeper.tools
    
    stored_ids = []
    for memory in memories:
        memory_id = await tools["store_memento"](**memory)
        stored_ids.append(memory_id)
    
    return stored_ids
```

### Caching Frequently Accessed Memories

```python
from functools import lru_cache

class CachedMementoAccess:
    def __init__(self, keeper: Memento):
        self.keeper = keeper
        self._cache = {}
    
    async def get_memory_cached(self, memory_id: str):
        """Get memory with caching."""
        if memory_id in self._cache:
            return self._cache[memory_id]
        
        tools = self.keeper.tools
        memory = await tools["get_memento"](memory_id=memory_id)
        self._cache[memory_id] = memory
        return memory
    
    def invalidate_cache(self, memory_id: str = None):
        """Invalidate cache entries."""
        if memory_id:
            self._cache.pop(memory_id, None)
        else:
            self._cache.clear()
```

## Best Practices

1. **Always initialize and cleanup**: Use context managers or explicit `initialize()`/`cleanup()` calls
2. **Use appropriate tool profiles**: Start with 'core', move to 'extended' or 'advanced' as needed
3. **Handle errors gracefully**: Memento provides specific error types for common failure modes
4. **Tag consistently**: Use consistent tagging conventions across your organization
5. **Manage confidence**: Regularly review and adjust confidence scores for important memories
6. **Use relationships**: Create meaningful relationships between memories for better context
7. **Leverage search**: Use `recall_mementos` for natural language, `search_mementos` for precise