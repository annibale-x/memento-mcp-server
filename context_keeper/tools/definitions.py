"""
Tool definitions for Context Keeper MCP server.

This module defines all the MCP tools available to the client.
"""

from typing import List

from mcp.types import Tool

from ..models import MemoryType


def get_all_tools() -> List[Tool]:
    """Collect all tool definitions from all modules."""
    return [
        Tool(
            name="help_memory_tools_usage",
            description="""Get comprehensive guidance on using persistent memory tools and distinguishing them from session memory tools.

CRITICAL DISTINCTION: Persistent memory vs Session memory

PERSISTENT MEMORY (mcp-context-keeper tools with '_persistent' suffix):
- Long-term knowledge that survives across ALL sessions
- Global scope: accessible from any project or session
- Use for: solutions, patterns, architecture decisions, reusable code snippets
- Examples: store_persistent_memory, get_persistent_memory, search_persistent_memories

SESSION MEMORY (Serena Context Server tools without suffix):
- Temporary context for current project/session
- Project-scoped: only accessible within current project
- Use for: current file context, temporary variables, undo/redo history
- Examples: store_memory, get_memory, search_memories (NO '_persistent' suffix)

WHEN TO USE WHICH:
─────────────────────────────────────────────────────────────
| Scenario                     | Use Persistent | Use Session |
|──────────────────────────────|────────────────|─────────────|
| Bug fix solution             | ✅ store_persistent_memory | ❌ |
| Current file context         | ❌ | ✅ store_memory |
| Architecture decision        | ✅ store_persistent_memory | ❌ |
| Temporary calculation        | ❌ | ✅ store_memory |
| Reusable code pattern        | ✅ store_persistent_memory | ❌ |
| Project-specific variable    | ❌ | ✅ store_memory |

Note: You can always use search_persistent_memories or recall_persistent_memories to find past knowledge.""",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="recall_persistent_memories",
            description="""Primary tool for finding persistent memories using natural language queries.

Optimized for fuzzy matching - handles plurals, tenses, and case variations automatically.

BEST FOR:
- Conceptual queries ("how does X work")
- General exploration ("what do we know about authentication")
- Fuzzy/approximate matching

USE FOR: Long-term knowledge that survives across sessions.
DO NOT USE FOR: Temporary session context or project-specific state.

LESS EFFECTIVE FOR:
- Acronyms (DCAD, JWT, API) - use search_persistent_memories with tags instead
- Proper nouns (company names, services)
- Exact technical terms

EXAMPLES:
- recall_persistent_memories(query="timeout fix") - find timeout-related solutions
- recall_persistent_memories(query="how does auth work") - conceptual query
- recall_persistent_memories(project_path="/app") - memories from specific project

FALLBACK: If recall returns no relevant results, try search_persistent_memories with tags filter.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query for what you're looking for",
                    },
                    "memory_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [t.value for t in MemoryType],
                        },
                        "description": "Optional: Filter by memory types for more precision",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Optional: Filter by project path to scope results",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1000,
                        "description": "Maximum number of results per page (default: 20)",
                    },
                    "offset": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Number of results to skip for pagination (default: 0)",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="store_persistent_memory",
            description="""Store a new persistent memory with context and metadata.

Required: type, title, content. Optional: tags, importance (0-1), context.

USE FOR: Long-term knowledge that should survive across ALL sessions.
DO NOT USE FOR: Temporary session state or project-specific context.

LIMITS:
- title: max 500 characters
- content: max 50KB (50,000 characters)
- tags: max 50 tags, 100 chars each

TAGGING BEST PRACTICE:
- Always include acronyms AS TAGS (e.g., tags=["jwt", "auth"])
- Fuzzy search struggles with acronyms in content
- Tags provide exact match fallback for reliable retrieval

Types: solution, problem, error, fix, pattern, decision, task, code_pattern, technology, command, workflow, general

EXAMPLES:
- store_persistent_memory(type="solution", title="Fixed Redis timeout", content="Increased timeout to 30s...", tags=["redis"], importance=0.8)
- store_persistent_memory(type="error", title="OAuth2 auth failure", content="Error details...", tags=["auth", "oauth2"])

Returns memory_id. Use create_persistent_relationship to link related memories.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": [t.value for t in MemoryType],
                        "description": "Type of memory to store",
                    },
                    "title": {
                        "type": "string",
                        "description": "Short descriptive title for the memory",
                    },
                    "content": {
                        "type": "string",
                        "description": "Detailed content of the memory",
                    },
                    "summary": {
                        "type": "string",
                        "description": "Optional brief summary of the memory",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags to categorize the memory",
                    },
                    "importance": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Importance score (0.0-1.0)",
                    },
                    "context": {
                        "type": "object",
                        "description": "Context information for the memory",
                    },
                },
                "required": ["type", "title", "content"],
            },
        ),
        Tool(
            name="get_persistent_memory",
            description="""Retrieve a specific persistent memory by ID.

Use when you have a memory_id from search results or store_persistent_memory.
Set include_relationships=true (default) to see connected memories.

EXAMPLE: get_persistent_memory(memory_id="abc-123")""",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "ID of the memory to retrieve",
                    },
                    "include_relationships": {
                        "type": "boolean",
                        "description": "Whether to include related memories",
                    },
                },
                "required": ["memory_id"],
            },
        ),
        Tool(
            name="update_persistent_memory",
            description="Update an existing persistent memory",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "ID of the memory to update",
                    },
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "summary": {"type": "string"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "importance": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
                "required": ["memory_id"],
            },
        ),
        Tool(
            name="delete_persistent_memory",
            description="Delete a persistent memory and all its relationships",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "ID of the memory to delete",
                    },
                },
                "required": ["memory_id"],
            },
        ),
        Tool(
            name="search_persistent_memories",
            description="""Advanced search with fine-grained filters for precise retrieval of persistent memories.

USE THIS TOOL FIRST (not recall) when searching for:
- Acronyms: DCAD, JWT, MCR2, API, etc.
- Proper nouns: Company names, service names, project names
- Known tags: When you know the tag from previous memories
- Technical terms: Exact matches needed

PARAMETERS:
- tags: Filter by exact tag match (most reliable for acronyms)
- memory_types: Filter by type (solution, problem, etc.)
- min_importance: Filter by importance threshold
- search_tolerance: strict/normal/fuzzy
- match_mode: any/all for multiple terms

NOTE: Tags are automatically normalized to lowercase for case-insensitive matching.

EXAMPLES:
- search_persistent_memories(tags=["jwt", "auth"]) - find JWT-related memories
- search_persistent_memories(tags=["dcad"]) - find DCAD memories by tag
- search_persistent_memories(query="timeout", memory_types=["solution"]) - timeout solutions
- search_persistent_memories(tags=["redis"], min_importance=0.7) - important Redis memories

For conceptual/natural language queries, use recall_persistent_memories instead.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Text to search for in memory content",
                    },
                    "terms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Multiple search terms for complex queries (alternative to query)",
                    },
                    "match_mode": {
                        "type": "string",
                        "enum": ["any", "all"],
                        "description": "Match mode for terms: 'any' returns results matching ANY term (OR), 'all' requires ALL terms (AND)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tags",
                    },
                    "memory_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [t.value for t in MemoryType],
                        },
                        "description": "Filter by memory types",
                    },
                    "relationship_filter": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter results to only include memories with these relationship types",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "Filter by project path",
                    },
                    "min_importance": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Minimum importance score",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1000,
                        "description": "Maximum number of results per page (default: 50)",
                    },
                    "offset": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Number of results to skip for pagination (default: 0)",
                    },
                    "search_tolerance": {
                        "type": "string",
                        "enum": ["strict", "normal", "fuzzy"],
                        "description": "Search tolerance mode: 'strict' for exact matches, 'normal' for stemming (default), 'fuzzy' for typo tolerance",
                    },
                },
            },
        ),
        Tool(
            name="persistent_contextual_search",
            description="""Search only within the context of a given persistent memory (scoped search).

Two-phase process: (1) Find related memories, (2) Search only within that set.
Provides semantic scoping without embeddings.

WHEN TO USE:
- Searching within a specific problem context
- Finding solutions in related knowledge
- Scoped discovery

HOW TO USE:
- Specify memory_id (context root)
- Provide query (search term)
- Optional: max_depth (default: 2)

RETURNS:
- Matches found only within related memories
- Context information
- No leakage outside context""",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "Memory ID to use as context root (required)",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query within context (required)",
                    },
                    "max_depth": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "description": "Maximum relationship traversal depth (default: 2)",
                    },
                },
                "required": ["memory_id", "query"],
            },
        ),
        Tool(
            name="create_persistent_relationship",
            description="""Link two persistent memories with a typed relationship.

Common types: SOLVES (solution→problem), CAUSES (cause→effect), ADDRESSES (fix→error), REQUIRES (dependent→dependency), RELATED_TO (general)

EXAMPLES:
- create_persistent_relationship(from_memory_id="sol-1", to_memory_id="prob-1", relationship_type="SOLVES")
- create_persistent_relationship(from_memory_id="err-1", to_memory_id="fix-1", relationship_type="CAUSES", context="Config error caused timeout")

Optional: strength (0-1), confidence (0-1), context (description)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "from_memory_id": {
                        "type": "string",
                        "description": "ID of the source memory",
                    },
                    "to_memory_id": {
                        "type": "string",
                        "description": "ID of the target memory",
                    },
                    "relationship_type": {
                        "type": "string",
                        "description": "Type of relationship to create",
                    },
                    "strength": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Strength of the relationship (0.0-1.0)",
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Confidence in the relationship (0.0-1.0)",
                    },
                    "context": {
                        "type": "string",
                        "description": "Context or description of the relationship",
                    },
                },
                "required": ["from_memory_id", "to_memory_id", "relationship_type"],
            },
        ),
        Tool(
            name="get_related_persistent_memories",
            description="""Find persistent memories connected to a specific memory via relationships.

Filter by relationship_types (e.g., ["SOLVES"], ["CAUSES"]) and max_depth (default 1).

EXAMPLES:
- get_related_persistent_memories(memory_id="prob-1", relationship_types=["SOLVES"]) - find solutions
- get_related_persistent_memories(memory_id="err-1", relationship_types=["CAUSES"], max_depth=2) - find root causes""",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "ID of the memory to find relations for",
                    },
                    "relationship_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by relationship types",
                    },
                    "max_depth": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "description": "Maximum relationship depth to traverse",
                    },
                },
                "required": ["memory_id"],
            },
        ),
        Tool(
            name="get_persistent_memory_statistics",
            description="Get statistics about the persistent memory database",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_persistent_recent_activity",
            description="""Get summary of recent persistent memory activity for session context.

Returns: memory counts by type, recent memories (up to 20), unresolved problems.

EXAMPLES:
- get_persistent_recent_activity(days=7) - last week's activity
- get_persistent_recent_activity(days=30, project="/app") - last month for specific project""",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 365,
                        "description": "Number of days to look back (default: 7)",
                    },
                    "project": {
                        "type": "string",
                        "description": "Optional: Filter by project path",
                    },
                },
            },
        ),
        Tool(
            name="search_persistent_relationships_by_context",
            description="Search persistent relationships by their structured context fields (scope, conditions, evidence, components)",
            inputSchema={
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "enum": ["partial", "full", "conditional"],
                        "description": "Filter by scope (partial, full, or conditional implementation)",
                    },
                    "conditions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by conditions (e.g., ['production', 'Redis enabled']). Matches any.",
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by specific evidence types (e.g., ['integration tests', 'unit tests']). Matches any.",
                    },
                    "components": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by components mentioned (e.g., ['auth', 'Redis']). Matches any.",
                    },
                    "has_evidence": {
                        "type": "boolean",
                        "description": "Filter by presence/absence of evidence (verified by tests, etc.)",
                    },
                    "temporal": {
                        "type": "string",
                        "description": "Filter by temporal information (e.g., 'v2.1.0', 'since 2024')",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "description": "Maximum number of results (default: 20)",
                    },
                },
            },
        ),
    ]
