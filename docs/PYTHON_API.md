# Python API Usage Guide

This guide covers how to use Context Keeper as a Python library for programmatic access to persistent memory management.

## Table of Contents
- [Installation](#installation)
- [Basic Usage](#basic-usage)
- [Core Classes](#core-classes)
- [Memory Operations](#memory-operations)
- [Relationship Management](#relationship-management)
- [Search and Retrieval](#search-and-retrieval)
- [Confidence System](#confidence-system)
- [Advanced Features](#advanced-features)
- [Examples](#examples)

## Installation

```bash
# Install the package
pip install mcp-context-keeper

# Or install in development mode
pip install -e .
```

## Basic Usage

### Import and Initialize

```python
from context_keeper import ContextKeeper
import asyncio

async def main():
    # Create a ContextKeeper instance
    keeper = ContextKeeper()
    
    # Initialize the server (creates database connection)
    await keeper.initialize()
    
    # Access the database directly
    db = keeper.memory_db
    
    # Your code here...
    
    # Cleanup
    await keeper.cleanup()

# Run the async function
asyncio.run(main())
```

### Configuration

```python
from context_keeper import ContextKeeper
from context_keeper.config import Config

async def main():
    # Create custom configuration
    config = Config(
        sqlite_path="~/custom_path/context.db",
        tool_profile="extended",
        enable_advanced_tools=True,
        log_level="INFO"
    )
    
    # Initialize with custom config
    keeper = ContextKeeper(config=config)
    await keeper.initialize()
    
    # Use the keeper...
    await keeper.cleanup()
```

## Core Classes

### ContextKeeper

The main class that provides access to all functionality.

```python
class ContextKeeper:
    def __init__(self, config: Optional[Config] = None):
        """Initialize ContextKeeper with optional configuration."""
    
    async def initialize(self) -> None:
        """Initialize database connection and setup."""
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
    
    @property
    def memory_db(self) -> MemoryDatabase:
        """Access the database interface directly."""
    
    @property
    def tools(self) -> Dict[str, Callable]:
        """Get available MCP tools as callable functions."""
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
```

### MemoryDatabase

Direct database access for advanced operations.

```python
class MemoryDatabase:
    async def store_memory(
        self,
        type: str,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a new memory and return its ID."""
    
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a memory by ID."""
    
    async def update_memory(
        self,
        memory_id: str,
        **updates: Any
    ) -> bool:
        """Update an existing memory."""
    
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
    
    async def search_memories(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        memory_types: Optional[List[str]] = None,
        min_importance: float = 0.0,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search memories with various filters."""
```

## Memory Operations

### Creating Memories

```python
async def create_example_memories(keeper: ContextKeeper):
    db = keeper.memory_db
    
    # Store a solution
    solution_id = await db.store_memory(
        type="solution",
        title="Fixed database connection timeout",
        content="Increased connection timeout to 30s and added retry logic...",
        tags=["database", "postgresql", "timeout", "fix"],
        importance=0.8,
        context={
            "project": "backend-api",
            "language": "python",
            "framework": "fastapi"
        }
    )
    
    # Store a pattern
    pattern_id = await db.store_memory(
        type="pattern",
        title="Database connection pooling pattern",
        content="Always use connection pooling for database connections...",
        tags=["database", "pattern", "best-practice"],
        importance=0.7
    )
    
    return solution_id, pattern_id
```

### Reading and Updating

```python
async def manage_memory(keeper: ContextKeeper, memory_id: str):
    db = keeper.memory_db
    
    # Get memory details
    memory = await db.get_memory(memory_id)
    if memory:
        print(f"Title: {memory['title']}")
        print(f"Type: {memory['type']}")
        print(f"Tags: {memory['tags']}")
        
        # Update the memory
        success = await db.update_memory(
            memory_id,
            importance=0.9,  # Increase importance
            tags=memory['tags'] + ["verified"]  # Add a tag
        )
        
        if success:
            print("Memory updated successfully")
    
    # Delete a memory
    deleted = await db.delete_memory(memory_id)
    if deleted:
        print("Memory deleted")
```

## Relationship Management

### Creating Relationships

```python
async def create_relationships(keeper: ContextKeeper, solution_id: str, pattern_id: str):
    db = keeper.memory_db
    
    # Create a relationship
    relationship_id = await db.create_relationship(
        from_memory_id=solution_id,
        to_memory_id=pattern_id,
        relationship_type="EXEMPLIFIES",
        confidence=0.8,
        context={
            "reason": "Solution demonstrates the pattern",
            "verified": True
        }
    )
    
    # Get related memories
    related = await db.get_related_memories(
        memory_id=solution_id,
        relationship_types=["EXEMPLIFIES", "USES"],
        max_depth=2
    )
    
    return relationship_id, related
```

### Relationship Types

Common relationship types:
- `SOLVES`: Solution → Problem
- `CAUSES`: Cause → Effect
- `IMPROVES`: Improvement → Original
- `RELATED_TO`: General relationship
- `USES`: Component → Dependency
- `EXEMPLIFIES`: Example → Pattern
- `DEPENDS_ON`: Dependency relationship
- `ALTERNATIVE_TO`: Alternative solutions

## Search and Retrieval

### Basic Search

```python
async def search_examples(keeper: ContextKeeper):
    db = keeper.memory_db
    
    # Search by query
    results = await db.search_memories(
        query="database connection timeout",
        limit=10
    )
    
    # Search by tags
    tagged_results = await db.search_memories(
        tags=["database", "python"],
        memory_types=["solution", "pattern"],
        min_importance=0.6,
        limit=20
    )
    
    # Full-text search with filters
    filtered_results = await db.search_memories(
        query="authentication",
        tags=["jwt", "oauth2"],
        memory_types=["solution"],
        limit=15
    )
    
    return results, tagged_results, filtered_results
```

### Advanced Search

```python
async def advanced_search(keeper: ContextKeeper):
    # Use the MCP tools interface for advanced features
    tools = keeper.tools
    
    # Natural language search (fuzzy matching)
    recall_results = await tools["recall_persistent_memories"](
        query="how to handle rate limiting in APIs",
        memory_types=["solution", "pattern"],
        limit=10
    )
    
    # Contextual search
    contextual_results = await tools["persistent_contextual_search"](
        query="authentication",
        context_tags=["web", "api"],
        similarity_threshold=0.7,
        limit=15
    )
    
    return recall_results, contextual_results
```

## Confidence System

### Managing Confidence

```python
async def confidence_management(keeper: ContextKeeper):
    tools = keeper.tools
    
    # Find low-confidence memories
    low_confidence = await tools["get_persistent_low_confidence_memories"](
        threshold=0.3,
        limit=50
    )
    
    # Boost confidence for validated knowledge
    for memory in low_confidence:
        if validate_memory(memory):
            await tools["boost_persistent_confidence"](
                memory_id=memory["id"],
                boost_amount=0.2,
                reason="Monthly verification passed"
            )
    
    # Manual confidence adjustment
    await tools["adjust_persistent_confidence"](
        relationship_id="rel-123",
        new_confidence=0.9,
        reason="Verified in production environment"
    )
    
    # Apply automatic decay
    decay_stats = await tools["apply_persistent_confidence_decay"]()
    print(f"Decay applied to {decay_stats['affected_memories']} memories")
```

### Confidence Configuration

```python
async def configure_confidence(keeper: ContextKeeper):
    tools = keeper.tools
    
    # Set custom decay factors (Advanced profile only)
    await tools["set_persistent_decay_factor"](
        memory_type="solution",
        decay_factor=0.97,  # 3% monthly decay instead of 5%
        reason="Solutions should decay slower"
    )
    
    # Get confidence statistics
    stats = await tools["get_persistent_memory_statistics"]()
    print(f"Average confidence: {stats['average_confidence']:.2f}")
    print(f"High confidence memories: {stats['high_confidence_count']}")
```

## Advanced Features

### Graph Analysis

```python
async def graph_analysis(keeper: ContextKeeper):
    tools = keeper.tools
    
    # Find memory clusters
    clusters = await tools["find_persistent_memory_clusters"](
        min_cluster_size=3,
        similarity_threshold=0.6
    )
    
    # Analyze relationship patterns
    patterns = await tools["analyze_persistent_relationship_patterns"](
        min_support=2,
        min_confidence=0.7
    )
    
    # Get graph statistics
    graph_stats = await tools["get_persistent_memory_graph_statistics"]()
    
    return clusters, patterns, graph_stats
```

### Export and Import

```python
async def backup_restore(keeper: ContextKeeper):
    tools = keeper.tools
    
    # Export to JSON
    export_data = await tools["export_persistent_memories"](
        format="json",
        include_relationships=True,
        include_confidence=True
    )
    
    # Save to file
    import json
    with open("backup.json", "w") as f:
        json.dump(export_data, f, indent=2)
    
    # Import from JSON
    with open("backup.json", "r") as f:
        import_data = json.load(f)
    
    import_stats = await tools["import_persistent_memories"](
        data=import_data,
        skip_duplicates=True,
        preserve_confidence=True
    )
    
    return import_stats
```

## Examples

### Complete Example: Knowledge Base Manager

```python
import asyncio
from context_keeper import ContextKeeper
from datetime import datetime

class KnowledgeBaseManager:
    def __init__(self, db_path: str = "~/.mcp-context-keeper/context.db"):
        self.config = Config(sqlite_path=db_path, tool_profile="extended")
        self.keeper = None
    
    async def __aenter__(self):
        self.keeper = ContextKeeper(config=self.config)
        await self.keeper.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.keeper:
            await self.keeper.cleanup()
    
    async def store_solution(self, title: str, content: str, tags: list, context: dict = None):
        """Store a solution with automatic tagging."""
        db = self.keeper.memory_db
        
        memory_id = await db.store_memory(
            type="solution",
            title=title,
            content=content,
            tags=tags + ["solution", "auto-stored"],
            importance=0.8,
            context={
                "stored_at": datetime.now().isoformat(),
                "source": "python_api",
                **(context or {})
            }
        )
        
        return memory_id
    
    async def find_solutions(self, query: str, project: str = None):
        """Find solutions, optionally filtered by project."""
        db = self.keeper.memory_db
        
        filters = {
            "query": query,
            "memory_types": ["solution"],
            "min_importance": 0.5,
            "limit": 20
        }
        
        if project:
            # This would require custom search logic
            # For simplicity, we'll filter after search
            pass
        
        results = await db.search_memories(**filters)
        
        # Sort by confidence × importance
        results.sort(key=lambda x: x.get('confidence', 0.5) * x.get('importance', 0.5), reverse=True)
        
        return results
    
    async def monthly_maintenance(self):
        """Perform monthly confidence maintenance."""
        tools = self.keeper.tools
        
        # Apply decay
        decay_stats = await tools["apply_persistent_confidence_decay"]()
        
        # Find obsolete knowledge
        low_conf = await tools["get_persistent_low_confidence_memories"](
            threshold=0.2,
            limit=100
        )
        
        # Archive very low confidence memories
        archived = 0
        for memory in low_conf:
            if memory['confidence'] < 0.1:
                await self.keeper.memory_db.delete_memory(memory['id'])
                archived += 1
        
        return {
            "decay_applied": decay_stats['affected_memories'],
            "low_confidence_found": len(low_conf),
            "archived": archived
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
        solutions = await manager.find_solutions("memory leak")
        for sol in solutions[:5]:
            print(f"- {sol['title']} (confidence: {sol.get('confidence', 0.5):.2f})")
        
        # Run maintenance
        if datetime.now().day == 1:  # First day of month
            stats = await manager.monthly_maintenance()
            print(f"Monthly maintenance: {stats}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Example: Integration with Existing Codebase

```python
import asyncio
from context_keeper import ContextKeeper
from typing import List, Dict, Any

class CodebaseAnalyzer:
    def __init__(self, keeper: ContextKeeper):
        self.keeper = keeper
    
    async def analyze_and_store_patterns(self, codebase_path: str):
        """Analyze codebase and store discovered patterns."""
        # This is a simplified example
        patterns = await self.discover_patterns(codebase_path)
        
        for pattern in patterns:
            await self.store_pattern(
                title=pattern["name"],
                content=pattern["description"],
                examples=pattern["examples"],
                tags=pattern["tags"]
            )
    
    async def discover_patterns(self, path: str) -> List[Dict[str, Any]]:
        """Discover patterns in codebase (simplified)."""
        # Implement actual pattern discovery
        return [
            {
                "name": "Repository Pattern Implementation",
                "description": "Consistent use of repository pattern with async/await...",
                "examples": ["user_repository.py", "product_repository.py"],
                "tags": ["design-pattern", "repository", "python", "async"]
            }
        ]
    
    async def store_pattern(self, title: str, content: str, examples: list, tags: list):
        """Store a discovered pattern."""
        db = self.keeper.memory_db
        
        full_content = f"{content}\n\nExamples:\n" + "\n".join(f"- {ex}" for ex in examples)
        
        pattern_id = await db.store_memory(
            type="pattern",
            title=title,
            content=full_content,
            tags=tags + ["auto-discovered"],
            importance=0.7
        )
        
        # Connect to related patterns
        related = await db.search_memories(
            tags=tags[:2],  # First two tags
            memory_types=["pattern"],
            limit=5
        )
        
        for related_memory in related:
            await db.create_relationship(
                from_memory_id=pattern_id,
                to_memory_id=related_memory["id"],
                relationship_type="RELATED_TO",
                confidence=0.6
            )
        
        return pattern_id

async def main():
    keeper = ContextKeeper()
    await keeper.initialize()
    
    analyzer = CodebaseAnalyzer(keeper)
    await analyzer.analyze_and_store_patterns("./src")
    
    await keeper.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

## Best Practices

### 1. Use Async Context Managers

```python
async with ContextKeeper() as keeper:
    # Your code here
    # Automatic cleanup on exit
```

### 2. Batch Operations

```python
async def batch_store(keeper: ContextKeeper, memories: list):
    """Store multiple memories efficiently."""
    db = keeper.memory_db
    
    # Use transactions for batch operations
    async with db.transaction():
        for memory in memories:
            await db.store_memory(**memory)
```

### 3. Error Handling

```python
async def safe_operation(keeper: ContextKeeper):
    try:
        db = keeper.memory_db
        result = await db.get_memory("non-existent-id")
        if not result:
            print("Memory not found")
    except Exception as e:
        print(f"Error: {e}")
        # Log error, retry, or handle gracefully
```

### 4. Resource Management

```python
async def process_with_timeout(keeper: ContextKeeper):
    try:
        # Set timeout for long operations
        async with as