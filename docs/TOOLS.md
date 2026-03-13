# MCP Tools Reference - mcp-context-server

## Overview

This document provides a comprehensive reference for all MCP (Model Context Protocol) tools available in the mcp-context-server server. This is a simplified version of MemoryGraph focused on SQLite-only backend for Zed editor integration.

## Core Tools (9 Tools)

### Memory Management Tools

#### 1. `store_memory`
**Description**: Store a new memory in the graph database.

**Parameters**:
- `content` (string, required): The content of the memory
- `memory_type` (string, optional): Type of memory (default: "note")
- `context` (string, optional): Context information
- `tags` (array of strings, optional): Tags for categorization
- `metadata` (object, optional): Additional metadata

**Returns**: Memory ID and creation timestamp

**Example**:
```json
{
  "tool": "store_memory",
  "content": "Fixed authentication bug in login controller",
  "memory_type": "bug_fix",
  "tags": ["authentication", "bug", "backend"],
  "context": "Working on user authentication system"
}
```

#### 2. `recall_memories`
**Description**: Recall memories based on a query.

**Parameters**:
- `query` (string, required): Search query
- `limit` (number, optional): Maximum number of results (default: 10)
- `memory_types` (array of strings, optional): Filter by memory types

**Returns**: List of matching memories with relevance scores

**Example**:
```json
{
  "tool": "recall_memories",
  "query": "authentication bug",
  "limit": 5,
  "memory_types": ["bug_fix", "issue"]
}
```

#### 3. `search_memories`
**Description**: Advanced search with semantic matching.

**Parameters**:
- `query` (string, required): Search query
- `search_tolerance` (number, optional): Search tolerance (0.0-1.0, default: 0.7)
- `limit` (number, optional): Maximum number of results (default: 10)
- `include_context` (boolean, optional): Include context in search (default: true)

**Returns**: List of memories with similarity scores

**Example**:
```json
{
  "tool": "search_memories",
  "query": "user login authentication",
  "search_tolerance": 0.8,
  "limit": 10
}
```

#### 4. `get_memory`
**Description**: Retrieve a specific memory by ID.

**Parameters**:
- `memory_id` (string, required): ID of the memory to retrieve

**Returns**: Complete memory object with all properties

**Example**:
```json
{
  "tool": "get_memory",
  "memory_id": "mem_123456"
}
```

#### 5. `update_memory`
**Description**: Update an existing memory.

**Parameters**:
- `memory_id` (string, required): ID of the memory to update
- `content` (string, optional): Updated content
- `tags` (array of strings, optional): Updated tags
- `context` (string, optional): Updated context
- `metadata` (object, optional): Updated metadata

**Returns**: Updated memory object

**Example**:
```json
{
  "tool": "update_memory",
  "memory_id": "mem_123456",
  "content": "Fixed authentication bug and added rate limiting",
  "tags": ["authentication", "bug", "backend", "security"]
}
```

#### 6. `delete_memory`
**Description**: Delete a memory from the graph.

**Parameters**:
- `memory_id` (string, required): ID of the memory to delete

**Returns**: Confirmation of deletion

**Example**:
```json
{
  "tool": "delete_memory",
  "memory_id": "mem_123456"
}
```

### Relationship Tools

#### 7. `create_relationship`
**Description**: Create a relationship between two memories.

**Parameters**:
- `from_memory_id` (string, required): Source memory ID
- `to_memory_id` (string, required): Target memory ID
- `relationship_type` (string, required): Type of relationship
- `context` (string, optional): Context for the relationship
- `strength` (number, optional): Relationship strength (0.0-1.0)

**Returns**: Relationship ID and details

**Example**:
```json
{
  "tool": "create_relationship",
  "from_memory_id": "mem_123456",
  "to_memory_id": "mem_789012",
  "relationship_type": "caused_by",
  "context": "Authentication bug caused login failure"
}
```

#### 8. `get_relationships`
**Description**: Get relationships for a memory.

**Parameters**:
- `memory_id` (string, required): Memory ID to get relationships for
- `direction` (string, optional): Relationship direction ("incoming", "outgoing", "both", default: "both")
- `relationship_types` (array of strings, optional): Filter by relationship types

**Returns**: List of relationships

**Example**:
```json
{
  "tool": "get_relationships",
  "memory_id": "mem_123456",
  "direction": "outgoing",
  "relationship_types": ["caused_by", "related_to"]
}
```

### Utility Tools

#### 9. `export_memories`
**Description**: Export memories to JSON format.

**Parameters**:
- `format` (string, optional): Export format ("json", "ndjson", default: "json")
- `include_relationships` (boolean, optional): Include relationships (default: true)
- `memory_ids` (array of strings, optional): Specific memory IDs to export

**Returns**: Exported data in specified format

**Example**:
```json
{
  "tool": "export_memories",
  "format": "json",
  "include_relationships": true
}
```

## Extended Tools (12 Tools - When enabled)

When running in extended mode, the following additional tools are available:

### 10. `import_memories`
**Description**: Import memories from JSON format.

**Parameters**:
- `data` (string, required): JSON data to import
- `format` (string, optional): Import format ("json", "ndjson", default: "json")
- `merge_strategy` (string, optional): Merge strategy ("skip", "overwrite", "merge", default: "skip")

### 11. `get_memory_stats`
**Description**: Get statistics about memories.

**Parameters**:
- `time_range` (object, optional): Time range filter
- `group_by` (string, optional): Group by field ("type", "day", "week", "month")

### 12. `health_check`
**Description**: Check server health and database status.

**Parameters**: None

## Relationship Types

### Core Relationship Types

1. **caused_by** - A memory was caused by another memory
2. **related_to** - Memories are related but not causally
3. **solution_for** - A memory provides a solution for another memory
4. **context_for** - A memory provides context for another memory
5. **depends_on** - A memory depends on another memory

### Extended Relationship Types

6. **learned_from** - Knowledge was learned from another memory
7. **improves** - A memory improves upon another memory
8. **references** - A memory references another memory
9. **similar_to** - Memories are similar in content or context

## Memory Types

### Standard Types

1. **note** - General note or observation
2. **bug_fix** - Bug fix or solution
3. **issue** - Problem or issue encountered
4. **decision** - Architectural or design decision
5. **learning** - Something learned
6. **todo** - Task to be done
7. **reference** - Reference material or link

### Extended Types

8. **configuration** - Configuration details
9. **command** - Command or script
10. **error** - Error message or stack trace
11. **optimization** - Performance optimization
12. **security** - Security-related information

## Configuration

### Server Modes

1. **Core Mode** (Default): 9 basic tools for essential memory management
2. **Extended Mode**: 12 tools including import/export and statistics

### Configuration File (`memorygraph.yaml`)

```yaml
server:
  mode: "core"  # or "extended"
  host: "localhost"
  port: 8080

database:
  path: "./memory.db"  # SQLite database path
  auto_init: true

logging:
  level: "INFO"
  file: "./memorygraph.log"
```

## Usage Examples

### Basic Memory Storage
```bash
# Store a memory
curl -X POST http://localhost:8080/tools/store_memory \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Implemented user authentication with JWT",
    "memory_type": "decision",
    "tags": ["authentication", "security", "backend"]
  }'
```

### Search and Recall
```bash
# Search for authentication-related memories
curl -X POST http://localhost:8080/tools/search_memories \
  -H "Content-Type: application/json" \
  -d '{
    "query": "authentication JWT implementation",
    "limit": 5
  }'
```

### Creating Relationships
```bash
# Link a bug fix to the original issue
curl -X POST http://localhost:8080/tools/create_relationship \
  -H "Content-Type: application/json" \
  -d '{
    "from_memory_id": "mem_fix_123",
    "to_memory_id": "mem_issue_456",
    "relationship_type": "solution_for",
    "context": "Fixed JWT validation issue"
  }'
```

## Best Practices

1. **Consistent Tagging**: Use consistent tags for similar topics
2. **Clear Context**: Always provide context when storing memories
3. **Relationship Mapping**: Create relationships to connect related memories
4. **Regular Export**: Regularly export memories for backup
5. **Memory Types**: Use appropriate memory types for categorization

## Troubleshooting

### Common Issues

1. **Database Connection**: Ensure SQLite database path is accessible
2. **Memory Not Found**: Verify memory ID exists
3. **Relationship Errors**: Check that both memory IDs exist
4. **Import/Export**: Validate JSON format before import

### Health Check
```bash
curl http://localhost:8080/health
```

## License

MIT License - See LICENSE file for details.

## Acknowledgments

This project is a simplified fork of the original MemoryGraph project by Gregory Dickson, adapted specifically for Zed editor integration with a focus on simplicity and local storage.