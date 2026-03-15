# MCP Tools Reference - mcp-context-keeper

## Overview

This document provides a comprehensive reference for all MCP (Model Context Protocol) tools available in the mcp-context-keeper server. This is a simplified version of Context Keeper focused on SQLite-only backend for Zed editor integration.

**IMPORTANT NAMING CONVENTION**: All tools use the `_persistent` suffix to distinguish them from session-based memory tools (like Serena Context Server). Use these tools for long-term knowledge that survives across sessions.

## Tool Profiles

### Core Profile (9 Tools)
Default profile with essential memory management tools for persistent storage.

### Extended Profile (12 Tools)
Core tools + 3 additional tools for advanced search and statistics.

### Advanced Profile (19 Tools)
Extended tools + 7 advanced tools for graph analysis and pattern detection.

## Core Tools (10 Tools)

### Guide Tool

#### 1. `help_memory_tools_usage`
**Description**: Get comprehensive guidance on using persistent memory tools and distinguishing them from session memory tools. Critical for avoiding confusion between persistent (cross-session) and session (project-specific) memory tools.

**Parameters**:
- `topic` (string, optional): Specific topic to get guidance on: "distinction", "examples", "best_practices", or "all" (default)

**Returns**: Comprehensive guide with examples, decision matrices, and best practices

**Example**:
```json
{
  "tool": "help_memory_tools_usage",
  "topic": "distinction"
}
```

### Memory Management Tools

#### 2. `store_persistent_memory`
**Description**: Store a new persistent memory in the graph database. Use for long-term knowledge that should survive across ALL sessions.

**Parameters**:
- `type` (string, required): Type of memory (solution, problem, error, fix, pattern, decision, task, code_pattern, technology, command, workflow, general)
- `title` (string, required): Short descriptive title for the memory (max 500 chars)
- `content` (string, required): Detailed content of the memory (max 50KB)
- `tags` (array of strings, optional): Tags for categorization (max 50 tags, 100 chars each)
- `importance` (number, optional): Importance score (0.0-1.0)
- `context` (object, optional): Context information for the memory

**Returns**: Memory ID and creation timestamp

**Example**:
```json
{
  "tool": "store_persistent_memory",
  "type": "solution",
  "title": "Fixed Redis timeout",
  "content": "Increased timeout to 30s and added connection pooling...",
  "tags": ["redis", "database", "performance"],
  "importance": 0.8
}
```

#### 3. `recall_persistent_memories`

**Description**: Recall persistent memories using natural language queries with fuzzy matching. Optimized for conceptual queries and general exploration.

**Parameters**:
- `query` (string, required): Natural language query
- `memory_types` (array of strings, optional): Filter by memory types
- `project_path` (string, optional): Filter by project path
- `limit` (integer, optional): Maximum results per page (default: 20)
- `offset` (integer, optional): Results to skip for pagination

**Returns**: List of matching memories with relevance scores

**Example**:
```json
{
  "tool": "recall_persistent_memories",
  "query": "how to fix timeout issues",
  "memory_types": ["solution", "fix"],
  "limit": 5
}
```

#### 4. `search_persistent_memories`
**Description**: Advanced search with fine-grained filters for precise retrieval of persistent memories. Use for acronyms, proper nouns, known tags, and exact technical terms.

**Parameters**:
- `query` (string, optional): Text to search in memory content
- `terms` (array of strings, optional): Multiple search terms
- `tags` (array of strings, optional): Filter by exact tag match
- `memory_types` (array of strings, optional): Filter by memory types
- `min_importance` (number, optional): Minimum importance score
- `search_tolerance` (string, optional): "strict", "normal", or "fuzzy"
- `match_mode` (string, optional): "any" or "all"

**Returns**: List of memories with similarity scores

**Example**:
```json
{
  "tool": "search_persistent_memories",
  "tags": ["jwt", "auth"],
  "memory_types": ["solution", "pattern"],
  "min_importance": 0.7
}
```

#### 5. `get_persistent_memory`
**Description**: Retrieve a specific persistent memory by ID.

**Parameters**:
- `memory_id` (string, required): ID of the memory to retrieve
- `include_relationships` (boolean, optional): Include related memories

**Returns**: Complete memory object with all properties

**Example**:
```json
{
  "tool": "get_persistent_memory",
  "memory_id": "mem_abc123",
  "include_relationships": true
}
```

#### 6. `update_persistent_memory`
**Description**: Update an existing persistent memory.

**Parameters**:
- `memory_id` (string, required): ID of the memory to update
- `title` (string, optional): Updated title
- `content` (string, optional): Updated content
- `summary` (string, optional): Updated summary
- `tags` (array of strings, optional): Updated tags
- `importance` (number, optional): Updated importance score

**Returns**: Updated memory object

**Example**:
```json
{
  "tool": "update_persistent_memory",
  "memory_id": "mem_abc123",
  "content": "Fixed authentication bug and added rate limiting",
  "tags": ["authentication", "security", "rate-limiting"]
}
```

#### 7. `delete_persistent_memory`
**Description**: Delete a persistent memory and all its relationships.

**Parameters**:
- `memory_id` (string, required): ID of the memory to delete

**Returns**: Confirmation of deletion

**Example**:
```json
{
  "tool": "delete_persistent_memory",
  "memory_id": "mem_abc123"
}
```

### Relationship Tools

#### 8. `create_persistent_relationship`
**Description**: Create a relationship between two persistent memories.

**Parameters**:
- `from_memory_id` (string, required): Source memory ID
- `to_memory_id` (string, required): Target memory ID
- `relationship_type` (string, required): Type of relationship
- `strength` (number, optional): Relationship strength (0.0-1.0)
- `confidence` (number, optional): Confidence in relationship (0.0-1.0)
- `context` (string, optional): Context description

**Returns**: Relationship ID and details

**Example**:
```json
{
  "tool": "create_persistent_relationship",
  "from_memory_id": "mem_sol_123",
  "to_memory_id": "mem_prob_456",
  "relationship_type": "SOLVES",
  "context": "Redis timeout fix solves connection pool issue"
}
```

#### 9. `get_related_persistent_memories`
**Description**: Get relationships for a persistent memory.

**Parameters**:
- `memory_id` (string, required): Memory ID to get relationships for
- `relationship_types` (array of strings, optional): Filter by relationship types
- `max_depth` (integer, optional): Maximum relationship depth (1-5)

**Returns**: List of related memories and relationships

**Example**:
```json
{
  "tool": "get_related_persistent_memories",
  "memory_id": "mem_prob_456",
  "relationship_types": ["SOLVES", "ADDRESSES"],
  "max_depth": 2
}
```

### Utility Tools

#### 10. `get_persistent_recent_activity`
**Description**: Get summary of recent persistent memory activity.

**Parameters**:
- `days` (integer, optional): Number of days to look back (1-365, default: 7)
- `project` (string, optional): Filter by project path

**Returns**: Memory counts by type, recent memories, unresolved problems

**Example**:
```json
{
  "tool": "get_persistent_recent_activity",
  "days": 7,
  "project": "/apps/api"
}
```

## Extended Tools (3 Additional Tools)

### 11. `get_persistent_memory_statistics`
**Description**: Get statistics about the persistent memory database.

**Parameters**: None

**Returns**: Database statistics including total memories, relationships, memory types distribution

**Example**:
```json
{
  "tool": "get_persistent_memory_statistics"
}
```

### 12. `search_persistent_relationships_by_context`
**Description**: Search persistent relationships by structured context fields.

**Parameters**:
- `scope` (string, optional): "partial", "full", or "conditional"
- `conditions` (array of strings, optional): Filter by conditions
- `has_evidence` (boolean, optional): Filter by evidence presence
- `evidence` (array of strings, optional): Filter by evidence types
- `components` (array of strings, optional): Filter by components
- `temporal` (string, optional): Filter by temporal information

**Returns**: List of relationships matching context criteria

**Example**:
```json
{
  "tool": "search_persistent_relationships_by_context",
  "scope": "full",
  "has_evidence": true,
  "components": ["auth", "database"]
}
```

### 13. `persistent_contextual_search`
**Description**: Search only within the context of a given persistent memory (scoped search).

**Parameters**:
- `memory_id` (string, required): Memory ID to use as context root
- `query` (string, required): Search query within context
- `max_depth` (integer, optional): Maximum relationship depth (1-5, default: 2)

**Returns**: Matches found only within related memories

**Example**:
```json
{
  "tool": "persistent_contextual_search",
  "memory_id": "mem_prob_456",
  "query": "timeout configuration",
  "max_depth": 2
}
```

## Advanced Tools (7 Additional Tools)

### 14. `analyze_persistent_memory_graph`
**Description**: Get comprehensive analytics and metrics for the persistent memory graph.

**Parameters**: None

**Returns**: Graph metrics, relationship system statistics, database statistics

**Example**:
```json
{
  "tool": "analyze_persistent_memory_graph"
}
```

### 15. `find_persistent_patterns`
**Description**: Find patterns in persistent memories and relationships.

**Parameters**:
- `min_pattern_size` (integer, optional): Minimum pattern size (default: 3)
- `min_support` (number, optional): Minimum support threshold (0.0-1.0, default: 0.5)

**Returns**: Detected patterns and their support scores

**Example**:
```json
{
  "tool": "find_persistent_patterns",
  "min_pattern_size": 3,
  "min_support": 0.6
}
```

### 16. `suggest_persistent_relationships`
**Description**: Get intelligent suggestions for relationship types between two persistent memories.

**Parameters**:
- `from_memory_id` (string, required): Source memory ID
- `to_memory_id` (string, required): Target memory ID

**Returns**: List of suggested relationship types with confidence scores

**Example**:
```json
{
  "tool": "suggest_persistent_relationships",
  "from_memory_id": "mem_sol_123",
  "to_memory_id": "mem_prob_456"
}
```

### 17. `get_persistent_memory_clusters`
**Description**: Detect clusters of densely connected persistent memories.

**Parameters**:
- `min_cluster_size` (integer, optional): Minimum memories per cluster (default: 3)
- `min_density` (number, optional): Minimum cluster density (0.0-1.0, default: 0.3)

**Returns**: Detected clusters with size and density metrics

**Example**:
```json
{
  "tool": "get_persistent_memory_clusters",
  "min_cluster_size": 3,
  "min_density": 0.4
}
```

### 18. `get_persistent_central_memories`
**Description**: Find persistent memories that connect different clusters (knowledge bridges).

**Parameters**: None

**Returns**: Central memories with betweenness centrality scores

**Example**:
```json
{
  "tool": "get_persistent_central_memories"
}
```

### 19. `find_path_between_persistent_memories`
**Description**: Find the shortest path between two persistent memories through relationships.

**Parameters**:
- `from_memory_id` (string, required): Starting memory ID
- `to_memory_id` (string, required): Target memory ID
- `max_depth` (integer, optional): Maximum path length (1-10, default: 5)
- `relationship_types` (array of strings, optional): Filter by relationship types

**Returns**: Path information including found status and hops

**Example**:
```json
{
  "tool": "find_path_between_persistent_memories",
  "from_memory_id": "mem_sol_123",
  "to_memory_id": "mem_root_789",
  "max_depth": 5
}
```

### 20. `get_persistent_memory_network`
**Description**: Get the complete network structure of persistent memories and relationships.

**Parameters**: None

**Returns**: Network structure including nodes, edges, and topological properties

**Example**:
```json
{
  "tool": "get_persistent_memory_network"
}
```

## Tool Count Summary

- **Core Profile**: 10 tools (including guide tool)
- **Extended Profile**: 13 tools (core + 3 extended)
- **Advanced Profile**: 20 tools (extended + 7 advanced)

## Relationship Types

### Core Relationship Types

1. **SOLVES** - A solution solves a problem
2. **CAUSES** - A cause leads to an effect
3. **ADDRESSES** - A fix addresses an error
4. **REQUIRES** - A dependency requires another component
5. **RELATED_TO** - General relationship between memories
6. **DEPENDS_ON** - Technical dependency
7. **IMPLEMENTS** - Implementation of a pattern or design
8. **EXTENDS** - Extension or enhancement
9. **REFINES** - Refinement or improvement
10. **DOCUMENTS** - Documentation relationship

### Extended Relationship Types

11. **LEARNED_FROM** - Knowledge learned from experience
12. **IMPROVES** - Improvement over previous version
13. **REFERENCES** - Reference to external resource
14. **SIMILAR_TO** - Similarity in content or context
15. **CONTRASTS_WITH** - Contrast or difference
16. **PRECEDES** - Temporal precedence
17. **FOLLOWS** - Temporal following
18. **VALIDATES** - Validation or verification
19. **INVALIDATES** - Invalidation or contradiction

## Memory Types

### Standard Types

1. **solution** - Solution to a problem
2. **problem** - Problem or issue
3. **error** - Error or exception
4. **fix** - Fix or workaround
5. **pattern** - Design or code pattern
6. **decision** - Architectural or design decision
7. **task** - Task or todo item
8. **code_pattern** - Code implementation pattern
9. **technology** - Technology or tool
10. **command** - Command or script
11. **workflow** - Workflow or process
12. **general** - General note or observation

## Configuration

### Server Modes

1. **Core Mode** (Default): 9 basic tools for essential persistent memory management
2. **Extended Mode**: 12 tools including advanced search and statistics
3. **Advanced Mode**: 19 tools including graph analysis and pattern detection

### Environment Variables

```
CONTEXT_TOOL_PROFILE=core|extended|advanced
CONTEXT_ENABLE_ADVANCED_TOOLS=true|false
CONTEXT_SQLITE_PATH=~/.mcp-context-keeper/context.db
CONTEXT_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
```

### Configuration File (`context-keeper.yaml`)

```yaml
backend: "sqlite"
tool_profile: "extended"
enable_advanced_tools: true
sqlite_path: "~/.mcp-context-keeper/context.db"
logging:
  level: "INFO"
features:
  auto_extract_entities: true
  session_briefing: true
  briefing_verbosity: "standard"
  briefing_recency_days: 7
  allow_relationship_cycles: false
```

## Usage Examples

### Basic Persistent Memory Storage
```bash
# Store a persistent memory
python -m context_keeper --profile extended

# Then use MCP client to call:
{
  "tool": "store_persistent_memory",
  "type": "solution",
  "title": "Fixed authentication with JWT",
  "content": "Implemented JWT token validation with 30-minute expiration...",
  "tags": ["authentication", "jwt", "security"]
}
```

### Search and Recall Persistent Memories
```bash
# Search for persistent authentication memories
{
  "tool": "search_persistent_memories",
  "tags": ["authentication", "jwt"],
  "memory_types": ["solution", "pattern"],
  "limit": 5
}
```

### Creating Persistent Relationships
```bash
# Link a persistent solution to a problem
{
  "tool": "create_persistent_relationship",
  "from_memory_id": "mem_sol_jwt",
  "to_memory_id": "mem_prob_auth",
  "relationship_type": "SOLVES",
  "context": "JWT implementation solves authentication issues"
}
```

## Best Practices

1. **Use _persistent Suffix**: Always use tools with `_persistent` suffix for long-term storage
2. **Tag Acronyms**: Include acronyms as tags (e.g., `["jwt", "api", "redis"]`)
3. **Clear Context**: Provide context for relationships and memories
4. **Importance Scoring**: Use importance scores (0.0-1.0) to prioritize memories
5. **Regular Maintenance**: Use statistics tools to monitor database health

## When to Use Persistent vs Session Memory

### Use Persistent Memory Tools (`_persistent` suffix):
- Long-term solutions and patterns
- Reusable code snippets and commands
- Architecture decisions and design patterns
- Important bug fixes and workarounds
- Technology evaluations and comparisons
- Knowledge that should survive across sessions

### Use Session Memory Tools (Serena, no suffix):
- Temporary session state
- Current file context
- Project-specific variables
- Undo/redo history
- Ephemeral calculations
- Short-term context that doesn't need persistence

## Getting Started with Guidance

For new users or when confused about which tool to use:

1. **Start with the guide tool**:
   ```json
   {
     "tool": "help_memory_tools_usage",
     "topic": "distinction"
   }
   ```

2. **Review examples**:
   ```json
   {
     "tool": "help_memory_tools_usage",
     "topic": "examples"
   }
   ```

3. **Learn best practices**:
   ```json
   {
     "tool": "help_memory_tools_usage",
     "topic": "best_practices"
   }
   ```

The guide tool provides decision matrices, common mistakes to avoid, and practical examples to ensure correct usage of persistent memory tools.

## Troubleshooting

### Common Issues

1. **Tool Not Found**: Ensure you're using the correct `_persistent` suffix
2. **Database Connection**: Check SQLite database path permissions
3. **Memory Not Found**: Verify memory ID exists in persistent storage
4. **Relationship Errors**: Ensure both memory IDs exist before creating relationships

### Health Check
