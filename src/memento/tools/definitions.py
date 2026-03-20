"""
Tool definitions for MCP Memento server.

This module defines all the MCP tools available to the client.
"""

from typing import List

from mcp.types import Tool

from ..models import MemoryType


def get_all_tools() -> List[Tool]:
    """Collect all tool definitions from all modules."""
    return [
        Tool(
            name="memento_onboarding",
            description="""Get comprehensive onboarding protocol for Memento including tool usage guidance, retrieval flow optimization, and best practices.

MEMENTO ONBOARDING PROTOCOL:
1. INITIALIZATION: Run memento_onboarding() at session start
2. RETRIEVAL FLOW:
   - Fact Check: Use search_mementos(tags=[...]) for simple identity/known facts
   - Complex Tasks: Use recall_mementos(query="...") for dev/architecture context
   - Fallback: If search fails, fallback to recall
3. AUTOMATIC STORAGE: Store via store_memento on git commits, bug fixes, version releases
4. ON-DEMAND TRIGGERS: Store instantly when user says "memento...", "remember...", etc.
5. MEMORY SCHEMA: Required tags (project, tech, category). Importance: 0.8+ (critical), 0.5 (standard)

OPTIMIZED RETRIEVAL (Avoid 6+ tool calls):
- Target: 1-3 tool calls for simple info
- Maximum: 5 tool calls for complex tasks
- Follow decision tree: Known tags → search_mementos, Conceptual → recall_mementos

CRITICAL DISTINCTION: Memento vs Session memory
- Memento: Long-term, cross-session, global scope
- Session Memory: Temporary, project-specific, session-only

USE memento_onboarding(topic="...") for specific guidance:
- "protocol": Full onboarding protocol
- "retrieval_flow": Optimized retrieval guide
- "distinction": Memento vs Session memory
- "examples": Practical examples
- "best_practices": Usage guidelines""",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Specific topic for onboarding guidance",
                        "enum": [
                            "onboarding",
                            "protocol",
                            "retrieval_flow",
                            "distinction",
                            "examples",
                            "best_practices",
                        ],
                        "default": "onboarding",
                    }
                },
            },
        ),
        Tool(
            name="recall_mementos",
            description="""Primary tool for finding mementos using natural language queries.

Optimized for fuzzy matching - handles plurals, tenses, and case variations automatically.

BEST FOR:
- Conceptual queries ("how does X work")
- General exploration ("what do we know about authentication")
- Fuzzy/approximate matching

USE FOR: Long-term knowledge that survives across sessions.
DO NOT USE FOR: Temporary session context or project-specific state.

LESS EFFECTIVE FOR:
- Acronyms (DCAD, JWT, API) - use search_mementos with tags instead
- Proper nouns (company names, services)
- Exact technical terms

EXAMPLES:
- recall_mementos(query="timeout fix") - find timeout-related solutions
- recall_mementos(query="how does auth work") - conceptual query
- recall_mementos(project_path="/app") - memories from specific project

FALLBACK: If recall returns no relevant results, try search_mementos with tags filter.""",
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
            name="store_memento",
            description="""Store a new memento with context and metadata.

Required: type, title, content. Optional: id, tags, importance (0-1), context.

USE FOR: Long-term knowledge that should survive across ALL sessions.
DO NOT USE FOR: Temporary session state or project-specific context.

LIMITS:
- title: max 500 characters
- content: max 50KB (50,000 characters)
- tags: max 50 tags, 100 chars each
- id: if provided, must be unique string identifier

TAGGING BEST PRACTICE:
- Always include acronyms AS TAGS (e.g., tags=["jwt", "auth"])
- Fuzzy search struggles with acronyms in content
- Tags provide exact match fallback for reliable retrieval

Types: solution, problem, error, fix, task, code_pattern, technology, command, file_context, workflow, project, general, conversation

Note: `decision` is not a standalone type — use type="general" with tags=["decision", "architecture"].
Note: `pattern` is not a standalone type — use type="code_pattern".

EXAMPLES:
- store_memento(type="solution", title="Fixed Redis timeout", content="Increased timeout to 30s...", tags=["redis"], importance=0.8)
- store_memento(type="error", title="OAuth2 auth failure", content="Error details...", tags=["auth", "oauth2"], id="custom-error-123")

Returns memory_id. Use create_memento_relationship to link related memories.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": [t.value for t in MemoryType],
                        "description": "Type of memory to store",
                    },
                    "id": {
                        "type": "string",
                        "description": "Optional memory ID (if not provided, a UUID will be generated automatically)",
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
            name="get_memento",
            description="""Retrieve a specific memento by ID.

Use when you have a memory_id from search results or store_memento.
Set include_relationships=true (default) to see connected memories.

EXAMPLE: get_memento(memory_id="abc-123")""",
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
            name="update_memento",
            description="Update an existing memento",
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
            name="delete_memento",
            description="Delete a memento and all its relationships",
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
            name="search_mementos",
            description="""Advanced search with fine-grained filters for precise retrieval of mementos.

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
- search_mementos(tags=["jwt", "auth"]) - find JWT-related memories
- search_mementos(tags=["dcad"]) - find DCAD memories by tag
- search_mementos(query="timeout", memory_types=["solution"]) - timeout solutions
- search_mementos(tags=["redis"], min_importance=0.7) - important Redis memories

For conceptual/natural language queries, use recall_mementos instead.""",
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
            name="contextual_memento_search",
            description="""Search only within the context of a given memento (scoped search).

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
            name="create_memento_relationship",
            description="""Link two mementos with a typed relationship.

Common types: SOLVES (solution→problem), CAUSES (cause→effect), ADDRESSES (fix→error), REQUIRES (dependent→dependency), RELATED_TO (general)

EXAMPLES:
- create_memento_relationship(from_memory_id="sol-1", to_memory_id="prob-1", relationship_type="SOLVES")
- create_memento_relationship(from_memory_id="err-1", to_memory_id="fix-1", relationship_type="CAUSES", context="Config error caused timeout")

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
            name="get_related_mementos",
            description="""Find mementos connected to a specific memory via relationships.

Filter by relationship_types (e.g., ["SOLVES"], ["CAUSES"]) and max_depth (default 1).

EXAMPLES:
- get_related_mementos(memory_id="prob-1", relationship_types=["SOLVES"]) - find solutions
- get_related_mementos(memory_id="err-1", relationship_types=["CAUSES"], max_depth=2) - find root causes""",
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
            name="get_memento_statistics",
            description="Get statistics about the memento database",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_recent_memento_activity",
            description="""Get summary of recent memento activity for session context.

Returns: memory counts by type, recent memories (up to 20), unresolved problems.

EXAMPLES:
- get_recent_memento_activity(days=7) - last week's activity
- get_recent_memento_activity(days=30, project="/app") - last month for specific project""",
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
            name="search_memento_relationships_by_context",
            description="Search memento relationships by their structured context fields (scope, conditions, evidence, components)",
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
        Tool(
            name="adjust_memento_confidence",
            description="""Manually adjust confidence of a relationship.

Use for:
- Correcting confidence scores when you know a memory is valid/invalid
- Setting custom confidence based on verification
- Overriding automatic decay for specific cases

Examples:
- adjust_memento_confidence(relationship_id="rel-123", new_confidence=0.9, reason="Verified in production")
- adjust_memento_confidence(relationship_id="rel-456", new_confidence=0.1, reason="Obsolete after library update")

Confidence ranges:
- 0.9-1.0: High confidence (recently validated)
- 0.7-0.89: Good confidence (regularly used)
- 0.5-0.69: Moderate confidence (somewhat outdated)
- 0.3-0.49: Low confidence (likely outdated)
- 0.0-0.29: Very low confidence (probably obsolete)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "relationship_id": {
                        "type": "string",
                        "description": "ID of the relationship to adjust",
                    },
                    "new_confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "New confidence value (0.0-1.0)",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for the adjustment",
                    },
                },
                "required": ["relationship_id", "new_confidence"],
            },
        ),
        Tool(
            name="get_low_confidence_mementos",
            description="""Find memories with low confidence scores.

Use for:
- Identifying potentially obsolete knowledge
- Periodic cleanup and verification
- Quality assurance of the knowledge base
- Finding memories that need review

Features:
- Filter by confidence threshold (default: < 0.3)
- Shows relationships causing low confidence
- Includes memory details and last access time
- Sorted by confidence (lowest first)

Returns:
- List of low confidence relationships with associated memories
- Memory details for both ends of each relationship
- Confidence scores and last access times""",
            inputSchema={
                "type": "object",
                "properties": {
                    "threshold": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Confidence threshold (default: 0.3)",
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
        Tool(
            name="apply_memento_confidence_decay",
            description="""Apply automatic confidence decay based on last access time.

Use for:
- System maintenance to keep knowledge base fresh
- Applying intelligent decay rules
- Monthly confidence adjustment routine

Intelligent decay rules:
- Critical memories (security, auth, api_key, password, critical, no_decay tags): NO DECAY
- High importance memories: Reduced decay based on importance score
- General knowledge: Standard 5% monthly decay (decay_factor=0.95)
- Temporary context: Higher decay rate

Decay formula:
monthly_decay = confidence × decay_factor^(months_since_last_access)

Minimum confidence: 0.1 (won't decay below this)

Returns:
- Number of relationships updated
- Summary of decay applied
- Breakdown by memory type""",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": (
                            "Optional memory ID. When provided, applies decay only to "
                            "relationships of that specific memory (and updates their "
                            "decay_factor based on the memory's importance and tags). "
                            "When omitted, applies decay to all relationships system-wide."
                        ),
                    },
                },
            },
        ),
        Tool(
            name="boost_memento_confidence",
            description="""Boost confidence when a memory is successfully used.

Use for:
- Reinforcing valid knowledge
- Manual confidence increase for verified information
- After successfully applying a solution
- When verifying old information is still valid

Usage patterns:
- After successfully applying a solution → boost its confidence
- When verifying old information is still valid → boost confidence
- When multiple team members confirm a pattern → boost confidence

Boost mechanics:
- Base boost: +0.01 per access (capped at 1.0)
- Additional boost for validation: +0.05 to +0.20
- Maximum confidence: 1.0 (cannot exceed)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": (
                            "ID of the memory to boost confidence for. "
                            "When provided, boosts confidence on all relationships of that memory. "
                            "Either memory_id or relationship_id must be specified."
                        ),
                    },
                    "relationship_id": {
                        "type": "string",
                        "description": (
                            "ID of a specific relationship to boost confidence for. "
                            "Use this to target a single relationship instead of all "
                            "relationships of a memory. "
                            "Either memory_id or relationship_id must be specified."
                        ),
                    },
                    "boost_amount": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Amount to boost confidence (default: 0.05)",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for the boost",
                    },
                },
                "required": ["memory_id"],
            },
        ),
        Tool(
            name="set_memento_decay_factor",
            description="""Set custom decay factor for specific memories.

Use for:
- Marking memories as "no decay" (critical information)
- Adjusting decay rates based on importance
- Customizing decay for specific use cases

Special tags for no decay:
- security, auth, api_key, password, critical, no_decay

Decay factor ranges:
- 1.0: No decay (critical information)
- 0.98-0.99: Very low decay (high importance)
- 0.95-0.97: Normal decay (general knowledge)
- 0.90-0.94: High decay (temporary context)
- 0.80-0.89: Very high decay (ephemeral data)

Note: Decay factor is applied monthly:
new_confidence = confidence × decay_factor^(months_since_last_access)""",
            inputSchema={
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "ID of the memory to set decay factor for",
                    },
                    "decay_factor": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Decay factor (0.0-1.0, 1.0 = no decay)",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for setting custom decay factor",
                    },
                },
                "required": ["memory_id", "decay_factor"],
            },
        ),
    ]
