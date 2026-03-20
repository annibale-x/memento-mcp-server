# Memento Tools Reference

## Table of Contents

- [Overview](#overview)
- [Tool Categories](#tool-categories)
  - [1. Core Memory Tools](#1-core-memory-tools-essential-operations)
  - [1b. Extended-Only Memory Tools](#1b-extended-only-memory-tools)
  - [2. Confidence System Tools](#2-confidence-system-tools-knowledge-quality)
  - [3. Advanced Relationship Tools](#3-advanced-relationship-tools-graph-analytics)
- [Tool Profiles](#tool-profiles)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)
- [Performance Considerations](#performance-considerations)
- [Error Handling](#error-handling)
- [Integration Patterns](#integration-patterns)
- [Parameter Requirements](#parameter-requirements)

---

> **📌 Note**: All code snippets in this document are **MCP tool call pseudocode** — they
> illustrate which tools an AI agent should invoke and with what arguments. They are
> **not** importable Python functions. For programmatic Python access, use the MCP
> client pattern described in [PYTHON.md](integrations/PYTHON.md).

---

## Overview

Memento provides a comprehensive set of tools for persistent memory management in MCP clients. These tools enable AI assistants to store, retrieve, and analyze knowledge across sessions, building a personal knowledge base that grows smarter over time.

## Tool Categories

### 1. Core Memory Tools (Essential Operations)
These tools are available in **all profiles** and provide the fundamental memory operations:

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `store_memento` | Store a new memento with context and metadata | `type`, `title`, `content`, `tags`, `importance` |
| `get_memento` | Retrieve a specific memento by ID | `memory_id`, `include_relationships` |
| `update_memento` | Update an existing memento | `memory_id`, `title`, `content`, `tags`, `importance` |
| `delete_memento` | Delete a memento and all its relationships | `memory_id` |
| `search_mementos` | Advanced search with fine-grained filters | `query`, `tags`, `memory_types`, `min_importance` |
| `recall_mementos` | Natural language search for conceptual queries | `query`, `memory_types`, `project_path` |
| `create_memento_relationship` | Link two mementos with a typed relationship | `from_memory_id`, `to_memory_id`, `relationship_type` |
| `get_related_mementos` | Find mementos connected to a specific memento | `memory_id`, `relationship_types`, `max_depth` |
| `get_recent_memento_activity` | Get summary of recent memento activity | `days`, `project` |
| `memento_onboarding` | Get comprehensive onboarding protocol for Memento | `topic` (optional) |

### 1b. Extended-Only Memory Tools
These tools are available from the **Extended profile** onwards:

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `get_memento_statistics` | Get statistics about the memento database | (no parameters) |
| `contextual_memento_search` | Search only within related mementos | `memory_id`, `query`, `max_depth` |
| `search_memento_relationships_by_context` | Search relationships by structured context fields | `scope`, `conditions`, `evidence`, `components` |

### 2. Confidence System Tools (Knowledge Quality)
These tools manage confidence scores and decay for relationship quality maintenance:

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `adjust_memento_confidence` | Manually adjust confidence of a relationship | `relationship_id`, `new_confidence`, `reason` |
| `get_low_confidence_mementos` | Find mementos with low confidence scores | `threshold`, `limit` |
| `apply_memento_confidence_decay` | Apply automatic confidence decay based on last access | (no parameters) |
| `boost_memento_confidence` | Boost confidence when a memento is successfully used | `memory_id`, `boost_amount`, `reason` |
| `set_memento_decay_factor` | Set custom decay factor for specific mementos | `memory_id`, `decay_factor`, `reason` |

### 3. Advanced Relationship Tools (Graph Analytics)
These tools provide advanced graph analysis and pattern detection:

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `find_path_between_mementos` | Find shortest path between two mementos | `from_memory_id`, `to_memory_id`, `max_depth` |
| `get_memento_clusters` | Detect clusters of densely connected mementos | `min_cluster_size`, `min_density` |
| `get_central_mementos` | Find mementos that connect different clusters | (no parameters) |
| `suggest_memento_relationships` | Get intelligent relationship type suggestions | `from_memory_id`, `to_memory_id` |
| `find_memento_patterns` | Find patterns in mementos and relationships | `min_pattern_size`, `min_support` |
| `analyze_memento_graph` | Get comprehensive analytics for the memento graph | (no parameters) |
| `get_memento_network` | Get complete network structure of mementos | (no parameters) |

## Tool Profiles

Memento offers three tool profiles with increasing capabilities:

### Core Profile (13 tools)
- All Core Memory Tools (section 1 above)
- Basic confidence tools: `adjust_memento_confidence`, `get_low_confidence_mementos`, `boost_memento_confidence`

### Extended Profile (17 tools)
- All Core Profile tools
- Extended-Only Memory Tools (section 1b above): `get_memento_statistics`, `contextual_memento_search`, `search_memento_relationships_by_context`
- Additional confidence tool: `apply_memento_confidence_decay`

### Advanced Profile (25 tools)
- All Extended Profile tools
- All Advanced Relationship Tools
- Advanced confidence tool: `set_memento_decay_factor`

## Usage Examples

### Basic Memory Operations
```python
# Store a solution
solution_id = store_memento(
    type="solution",
    title="Fixed Redis timeout with connection pooling",
    content="Increased connection timeout to 30s and added connection pooling...",
    tags=["redis", "timeout", "production_fix"],
    importance=0.8
)

# Find related knowledge
results = recall_mementos(query="Redis timeout solutions", limit=5)

# Create relationships
create_memento_relationship(
    from_memory_id=solution_id,
    to_memory_id=related_solution_id,
    relationship_type="RELATED_TO"  # See [RELATIONSHIPS.md](./RELATIONSHIPS.md) for all 35 relationship types
)
```

### Confidence Management
```python
# Find obsolete knowledge
low_confidence = get_low_confidence_mementos(threshold=0.3)

# Boost confidence after verification
boost_memento_confidence(
    memory_id=verified_solution_id,
    boost_amount=0.15,
    reason="Verified in production deployment"
)

# Apply monthly decay
apply_memento_confidence_decay()
```

### Advanced Analysis
```python
# Find knowledge clusters
clusters = get_memento_clusters(min_cluster_size=3, min_density=0.3)

# Analyze relationship patterns
patterns = find_memento_patterns(min_pattern_size=2, min_support=0.5)

# Get graph analytics
analytics = analyze_memento_graph()
```

## Best Practices

### 1. Tagging Strategy
- Always include acronyms as tags: `tags=["jwt", "auth", "api"]`
- Use consistent tag naming: lowercase, hyphenated for multi-word
- Tag by technology, problem domain, and solution type

### 2. Memory Organization
- Use `type` field consistently: `solution`, `problem`, `code_pattern`, `general`
- Set appropriate `importance` (0.0-1.0) for prioritization
- Include relevant `context` for better searchability

### 3. Relationship Management
- Use meaningful `relationship_type`: Choose from 35 available types (see [RELATIONSHIPS.md](./RELATIONSHIPS.md) for complete list)
- Set initial `confidence` based on verification level
- Regularly review and adjust confidence scores

### 4. Search Optimization
- Use `recall_mementos` for natural language/conceptual queries
- Use `search_mementos` for exact matches and tag-based filtering
- Combine with `get_related_mementos` for context exploration

## Performance Considerations

### Memory Limits
- Title: max 500 characters
- Content: max 50KB (50,000 characters)
- Tags: max 50 tags, 100 characters each
- Relationships: unlimited, but consider graph complexity

### Search Performance
- `recall_mementos`: Optimized for fuzzy matching, handles 1000+ mementos
- `search_mementos`: Best for exact matches, supports complex filtering
- `get_related_mementos`: Efficient BFS traversal up to depth 5

### Database Optimization
- SQLite with FTS5 for full-text search
- Automatic indexing on frequently queried fields
- Connection pooling for high-concurrency environments

## Error Handling

All tools return structured error responses with:
- Error type and message
- Suggested remediation
- Context about the failed operation

Common error scenarios:
- Invalid memory ID format
- Database connection issues
- Validation errors for input parameters
- Permission/access restrictions

## Integration Patterns

### With AI Assistants
```python
async def process_with_context(query: str):
    # Search for relevant mementos
    mementos = await recall_mementos(query=query, limit=5)
    
    # Use mementos to inform response
    context = build_context(mementos)
    response = generate_response(query, context)
    
    # Store successful interaction
    await store_memento(
        type="interaction",
        title=f"Query: {query[:50]}",
        content=f"Q: {query}\n\nA: {response}",
        tags=["auto-stored", "interaction"]
    )
    
    return response
```

### With CI/CD Pipelines
```python
async def store_test_results(test_name: str, results: dict):
    memento_id = await store_memento(
        type="test_result",
        title=f"Test: {test_name}",
        content=json.dumps(results, indent=2),
        tags=["ci-cd", "testing", "automation"],
        importance=0.7
    )
    
    # Link to related code changes
    await create_memento_relationship(
        from_memory_id=code_change_id,
        to_memory_id=memento_id,
        relationship_type="VALIDATED_BY",  # One of 35 relationship types - see [RELATIONSHIPS.md](./RELATIONSHIPS.md)
        confidence=0.9
    )
```

---

## Parameter Requirements

### Core Memory Tools Required Parameters

| Tool | Required Parameters | Optional Parameters |
|------|---------------------|---------------------|
| `store_memento` | `type`, `title`, `content` | `tags`, `importance`, `id` |
| `get_memento` | `memory_id` | `include_relationships` |
| `update_memento` | `memory_id` | `title`, `content`, `tags`, `importance` |
| `delete_memento` | `memory_id` | (none) |
| `search_mementos` | (none) - at least one of `query`, `tags`, or `memory_types` recommended | `query`, `tags`, `memory_types`, `min_importance`, `limit`, `offset` |
| `recall_mementos` | `query` | `memory_types`, `project_path`, `limit`, `offset` |
| `create_memento_relationship` | `from_memory_id`, `to_memory_id`, `relationship_type` | `strength`, `confidence`, `context` |
| `get_related_mementos` | `memory_id` | `relationship_types`, `max_depth` |

### Confidence System Tools Required Parameters

| Tool | Required Parameters | Optional Parameters |
|------|---------------------|---------------------|
| `adjust_memento_confidence` | `relationship_id`, `new_confidence` | `reason` |
| `get_low_confidence_mementos` | (none) | `threshold`, `limit` |
| `apply_memento_confidence_decay` | (none) | (none) |
| `boost_memento_confidence` | `memory_id` | `boost_amount`, `reason` |
| `set_memento_decay_factor` | `memory_id` | `decay_factor`, `reason` |

### Advanced Relationship Tools Required Parameters

| Tool | Required Parameters | Optional Parameters |
|------|---------------------|---------------------|
| `find_path_between_mementos` | `from_memory_id`, `to_memory_id` | `max_depth` |
| `get_memento_clusters` | (none) | `min_cluster_size`, `min_density` |
| `get_central_mementos` | (none) | (none) |
| `suggest_memento_relationships` | `from_memory_id`, `to_memory_id` | (none) |
| `find_memento_patterns` | (none) | `min_pattern_size`, `min_support` |
| `analyze_memento_graph` | (none) | (none) |
| `get_memento_network` | (none) | (none) |

**Note**: Parameters marked as required must be provided for the tool to function. Optional parameters have default values or can be omitted.

---
