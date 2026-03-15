"""
Guide tools for persistent memory usage guidance and distinction from session memory.

This module provides tools to help users understand the difference between
persistent memory (cross-session, global) and session memory (project-specific, temporary).
"""

from typing import Any, Dict

from mcp.types import CallToolResult, TextContent


async def handle_help_memory_tools_usage(
    context: Any, arguments: Dict[str, Any]
) -> CallToolResult:
    """
    Handle help_memory_tools_usage tool call.

    Provides comprehensive guidance on using persistent memory tools and
    distinguishing them from session memory tools.

    Args:
        context: Tool context with database and configuration
        arguments: Tool arguments including optional topic

    Returns:
        CallToolResult with guidance content
    """
    topic = arguments.get("topic", "all")

    guide_content = _generate_guide_content(topic)

    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=guide_content,
            )
        ]
    )


def _generate_guide_content(topic: str) -> str:
    """
    Generate guide content based on requested topic.

    Args:
        topic: Specific topic to generate guidance for

    Returns:
        Formatted guide content
    """
    if topic == "distinction":
        return _generate_distinction_guide()
    elif topic == "examples":
        return _generate_examples_guide()
    elif topic == "best_practices":
        return _generate_best_practices_guide()
    else:  # "all" or any other value
        return _generate_comprehensive_guide()


def _generate_distinction_guide() -> str:
    """Generate guide focusing on the distinction between persistent and session memory."""
    return """# PERSISTENT MEMORY vs SESSION MEMORY - CRITICAL DISTINCTION

## PERSISTENT MEMORY (mcp-context-keeper tools with '_persistent' suffix)
- **Scope**: Global - accessible from ANY project or session
- **Persistence**: Long-term - survives across ALL sessions
- **Purpose**: Store reusable knowledge, solutions, patterns
- **Tool Examples**:
  - `store_persistent_memory` - Store long-term solutions
  - `get_persistent_memory` - Retrieve cross-session knowledge
  - `search_persistent_memories` - Search global patterns

## SESSION MEMORY (Serena Context Server tools WITHOUT suffix)
- **Scope**: Project-specific - only accessible within current project
- **Persistence**: Temporary - lasts only for current session
- **Purpose**: Store ephemeral context, temporary variables
- **Tool Examples**:
  - `store_memory` - Store session context
  - `get_memory` - Retrieve session variables
  - `search_memories` - Search within session

## WHEN TO USE WHICH - DECISION MATRIX
┌─────────────────────────────────────────────┬─────────────────┬───────────────┐
│ Scenario                                    │ Use Persistent  │ Use Session   │
├─────────────────────────────────────────────┼─────────────────┼───────────────┤
│ Bug fix solution                            │ ✅ ALWAYS       │ ❌ NEVER      │
│ Architecture decision                       │ ✅ ALWAYS       │ ❌ NEVER      │
│ Reusable code pattern                       │ ✅ ALWAYS       │ ❌ NEVER      │
│ Technology evaluation                       │ ✅ ALWAYS       │ ❌ NEVER      │
│ Current file context                        │ ❌ NEVER        │ ✅ ALWAYS     │
│ Temporary calculation                       │ ❌ NEVER        │ ✅ ALWAYS     │
│ Project-specific variable                   │ ❌ NEVER        │ ✅ ALWAYS     │
│ Session undo history                        │ ❌ NEVER        │ ✅ ALWAYS     │
└─────────────────────────────────────────────┴─────────────────┴───────────────┘

## COMMON CONFUSIONS TO AVOID
1. ❌ Using `store_memory` (Serena) for long-term solutions
   ✅ Use `store_persistent_memory` instead

2. ❌ Using `get_memory` (Serena) for cross-session knowledge
   ✅ Use `get_persistent_memory` instead

3. ❌ Using `search_memories` (Serena) for global patterns
   ✅ Use `search_persistent_memories` instead

## KEY TAKEAWAY
**ALWAYS CHECK FOR '_persistent' SUFFIX** when you need knowledge to survive across sessions.
No suffix = session-only, temporary storage."""


def _generate_examples_guide() -> str:
    """Generate guide with practical examples."""
    return """# PRACTICAL EXAMPLES - PERSISTENT vs SESSION MEMORY

## ✅ CORRECT USAGE EXAMPLES

### Example 1: Storing a bug fix solution
```json
{
  "tool": "store_persistent_memory",
  "type": "solution",
  "title": "Fixed JWT authentication timeout",
  "content": "Increased JWT token expiration to 30 minutes...",
  "tags": ["jwt", "authentication", "security"],
  "importance": 0.8
}
```
✅ **CORRECT**: Uses `_persistent` suffix for long-term solution

### Example 2: Storing current file context
```json
{
  "tool": "store_memory",
  "type": "file_context",
  "title": "Current API endpoint",
  "content": "Working on /api/auth/login endpoint...",
  "project_path": "/projects/api-server"
}
```
✅ **CORRECT**: No suffix for session-specific context

### Example 3: Searching for authentication patterns
```json
{
  "tool": "search_persistent_memories",
  "tags": ["authentication", "jwt"],
  "memory_types": ["solution", "pattern"],
  "limit": 5
}
```
✅ **CORRECT**: Uses `_persistent` suffix for global knowledge search

## ❌ INCORRECT USAGE EXAMPLES

### Example 1: WRONG - Using session memory for solution
```json
{
  "tool": "store_memory",  // ❌ WRONG - NO '_persistent' suffix
  "type": "solution",
  "title": "Database optimization",
  "content": "Added indexes to improve query performance..."
}
```
❌ **PROBLEM**: This solution will be lost when session ends

### Example 2: WRONG - Using persistent memory for temporary context
```json
{
  "tool": "store_persistent_memory",  // ❌ WRONG - UNNECESSARY persistence
  "type": "file_context",
  "title": "Temporary calculation",
  "content": "x = 5, y = 10, result = x + y"
}
```
❌ **PROBLEM**: Pollutes persistent storage with ephemeral data

## SCENARIO-BASED EXAMPLES

### Scenario: Learning a new framework
- ✅ **Persistent**: Store framework patterns, best practices, gotchas
- ✅ **Session**: Store current file you're working on, temporary test code

### Scenario: Debugging a complex issue
- ✅ **Persistent**: Store the root cause and solution
- ✅ **Session**: Store current stack trace, temporary variables

### Scenario: Refactoring code
- ✅ **Persistent**: Store refactoring patterns, before/after examples
- ✅ **Session**: Store current method being refactored, temporary imports

## QUICK REFERENCE
- **Need it tomorrow?** → Use `_persistent` suffix
- **Only need it now?** → No suffix (session memory)
- **Sharing across projects?** → Use `_persistent` suffix
- **Project-specific only?** → No suffix (session memory)"""


def _generate_best_practices_guide() -> str:
    """Generate guide with best practices."""
    return """# BEST PRACTICES FOR PERSISTENT MEMORY USAGE

## 1. NAMING CONVENTION
**ALWAYS use '_persistent' suffix for long-term storage**
- ✅ `store_persistent_memory` - Correct for solutions
- ❌ `store_memory` - Wrong for solutions (session-only)

## 2. TAGGING STRATEGY
**Always tag acronyms in persistent memories**
```json
{
  "tool": "store_persistent_memory",
  "tags": ["jwt", "api", "redis", "oauth2"]  // ✅ Good tagging
}
```
- Why: Fuzzy search struggles with acronyms
- Tags provide exact match fallback
- Enables reliable retrieval via `search_persistent_memories(tags=["jwt"])`

## 3. IMPORTANCE SCORING
**Use importance scores (0.0-1.0) to prioritize**
- 0.9-1.0: Critical solutions, security fixes
- 0.7-0.8: Important patterns, architecture decisions
- 0.5-0.6: Useful tips, common patterns
- 0.0-0.4: General knowledge, references

## 4. RELATIONSHIP BUILDING
**Connect related persistent memories**
```json
{
  "tool": "create_persistent_relationship",
  "from_memory_id": "sol_jwt_fix",
  "to_memory_id": "prob_auth_timeout",
  "relationship_type": "SOLVES",
  "context": "JWT implementation solves authentication timeout"
}
```
Benefits:
- Creates knowledge graph
- Enables path finding between related concepts
- Improves contextual search results

## 5. MEMORY TYPE SELECTION
**Choose appropriate memory types**
- `solution`: For fixes and workarounds
- `pattern`: For reusable code patterns
- `technology`: For framework/tool knowledge
- `error`: For error patterns and solutions
- `general`: For miscellaneous knowledge

## 6. CONTEXT ENRICHMENT
**Add rich context to persistent memories**
```json
{
  "tool": "store_persistent_memory",
  "context": {
    "project": "api-server",
    "language": "python",
    "framework": "fastapi",
    "timestamp": "2024-03-14T10:30:00Z"
  }
}
```

## 7. REGULAR MAINTENANCE
**Use these tools for database health:**
- `get_persistent_memory_statistics`: Monitor database size
- `get_persistent_recent_activity`: Track usage patterns
- `analyze_persistent_memory_graph`: Analyze relationship density

## 8. AVOID THESE COMMON MISTAKES
1. **Over-persisting**: Don't use `_persistent` for temporary data
2. **Under-tagging**: Always tag acronyms and key terms
3. **Sparse relationships**: Connect related memories
4. **Vague titles**: Use descriptive, specific titles
5. **Missing context**: Always include relevant context

## 9. INTEGRATION WITH SESSION MEMORY
**Use both systems together:**
1. Store current work in session memory
2. Extract patterns and solutions to persistent memory
3. Reference persistent knowledge during session work
4. Clean up session memory at end of project

## 10. PERFORMANCE OPTIMIZATION
- Use `recall_persistent_memories` for conceptual queries
- Use `search_persistent_memories` for exact term matching
- Use `persistent_contextual_search` for scoped exploration
- Set appropriate `limit` parameters to avoid large result sets"""


def _generate_comprehensive_guide() -> str:
    """Generate comprehensive guide covering all topics."""
    distinction = _generate_distinction_guide()
    examples = _generate_examples_guide()
    best_practices = _generate_best_practices_guide()

    return f"""{distinction}

---

{examples}

---

{best_practices}

---

# QUICK DECISION FLOWCHART

1. **Is this knowledge reusable across projects?**
   - YES → Use `_persistent` suffix tools
   - NO → Use session memory tools (no suffix)

2. **Will you need this tomorrow/next week?**
   - YES → Use `_persistent` suffix tools
   - NO → Use session memory tools (no suffix)

3. **Is this a solution/pattern/architecture decision?**
   - YES → Use `_persistent` suffix tools
   - NO → Use session memory tools (no suffix)

4. **Is this temporary/current work context?**
   - YES → Use session memory tools (no suffix)
   - NO → Use `_persistent` suffix tools

# NEED HELP?
Use these tools for assistance:
- `get_persistent_memory_guide(topic="distinction")` - Focus on differences
- `get_persistent_memory_guide(topic="examples")` - Practical examples
- `get_persistent_memory_guide(topic="best_practices")` - Usage guidelines
- `get_persistent_memory_statistics()` - Database health check
- `get_persistent_recent_activity()` - Usage patterns"""
