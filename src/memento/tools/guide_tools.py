"""
Guide tools for memento onboarding protocol and usage optimization.

This module provides tools for Memento onboarding including comprehensive
protocols for tool usage, retrieval flow optimization, and best practices.
"""

from typing import Any, Dict

from mcp.types import CallToolResult, TextContent


async def handle_memento_onboarding(
    context: Any, arguments: Dict[str, Any]
) -> CallToolResult:
    """
    Handle memento_onboarding tool call.

    Provides comprehensive onboarding protocol for Memento including
    tool usage guidance, retrieval flow optimization, and best practices.

    Args:
        context: Tool context with database and configuration
        arguments: Tool arguments including optional topic

    Returns:
        CallToolResult with onboarding content
    """
    topic = arguments.get("topic", "onboarding")

    onboarding_content = _generate_onboarding_content(topic)

    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=onboarding_content,
            )
        ]
    )


def _generate_onboarding_content(topic: str) -> str:
    """
    Generate onboarding content based on requested topic.

    Args:
        topic: Specific topic to generate onboarding for

    Returns:
        Formatted onboarding content
    """
    if topic == "distinction":
        return _generate_distinction_guide()
    elif topic == "examples":
        return _generate_examples_guide()
    elif topic == "best_practices":
        return _generate_best_practices_guide()
    elif topic == "protocol":
        return _generate_onboarding_protocol()
    elif topic == "retrieval_flow":
        return _generate_retrieval_flow_guide()
    else:  # "onboarding" or any other value
        return _generate_comprehensive_onboarding()


def _generate_distinction_guide() -> str:
    """Generate guide focusing on the distinction between memento and session memory."""
    return """# MEMENTO vs SESSION MEMORY - CRITICAL DISTINCTION

## MEMENTO (mcp-memento tools with '_persistent' suffix)
- Scope: Global - accessible from ANY project or session
- Persistence: Long-term - survives across ALL sessions
- Purpose: Store reusable knowledge, solutions, patterns
- Tool Examples:
  - store_memento - Store long-term solutions
  - get_memento - Retrieve cross-session knowledge
  - search_mementos - Search global patterns

## SESSION MEMORY (Serena Context Server tools WITHOUT suffix)
- Scope: Project-specific - only accessible within current project
- Persistence: Temporary - lasts only for current session
- Purpose: Store ephemeral context, temporary variables
- Tool Examples:
  - store_memory - Store session context
  - get_memory - Retrieve session variables
  - search_memories - Search within session

## WHEN TO USE WHICH - DECISION MATRIX
- Bug fix solution: Use Memento ALWAYS
- Architecture decision: Use Memento ALWAYS
- Reusable code pattern: Use Memento ALWAYS
- Technology evaluation: Use Memento ALWAYS
- Current file context: Use Session ALWAYS
- Temporary calculation: Use Session ALWAYS
- Project-specific variable: Use Session ALWAYS
- Session undo history: Use Session ALWAYS

## COMMON CONFUSIONS TO AVOID
1. Using store_memory (Serena) for long-term solutions
   Use store_memento instead

2. Using get_memory (Serena) for cross-session knowledge
   Use get_memento instead

3. Using search_memories (Serena) for global patterns
   Use search_mementos instead

## KEY TAKEAWAY
ALWAYS CHECK FOR '_persistent' SUFFIX when you need knowledge to survive across sessions.
No suffix = session-only, temporary storage."""


def _generate_examples_guide() -> str:
    """Generate guide with practical examples."""
    return """# PRACTICAL EXAMPLES - MEMENTO vs SESSION MEMORY

## CORRECT USAGE EXAMPLES

### Example 1: Storing a bug fix solution
Use store_memento for long-term solution

### Example 2: Storing current file context
Use store_memory for session-specific context

### Example 3: Searching for authentication patterns
Use search_mementos for global knowledge search

## INCORRECT USAGE EXAMPLES

### Example 1: WRONG - Using session memory for solution
Using store_memory for database optimization solution
PROBLEM: This solution will be lost when session ends

### Example 2: WRONG - Using memento for temporary context
Using store_memento for temporary calculation
PROBLEM: Pollutes memento storage with ephemeral data

## SCENARIO-BASED EXAMPLES

### Scenario: Learning a new framework
- Memento: Store framework patterns, best practices, gotchas
- Session: Store current file you're working on, temporary test code

### Scenario: Debugging a complex issue
- Memento: Store the root cause and solution
- Session: Store current stack trace, temporary variables

### Scenario: Refactoring code
- Memento: Store refactoring patterns, before/after examples
- Session: Store current method being refactored, temporary imports

## QUICK REFERENCE
- Need it tomorrow? -> Use _persistent suffix
- Only need it now? -> No suffix (session memory)
- Sharing across projects? -> Use _persistent suffix
- Project-specific only? -> No suffix (session memory)"""


def _generate_best_practices_guide() -> str:
    """Generate guide with best practices."""
    return """# BEST PRACTICES FOR MEMENTO USAGE

## 1. NAMING CONVENTION
ALWAYS use '_persistent' suffix for long-term storage
- store_memento - Correct for solutions
- store_memory - Wrong for solutions (session-only)

## 2. TAGGING STRATEGY
Always tag acronyms in mementos
Tags: ["jwt", "api", "redis", "oauth2"]  # Good tagging
- Why: Fuzzy search struggles with acronyms
- Tags provide exact match fallback
- Enables reliable retrieval via search_mementos(tags=["jwt"])

## 3. IMPORTANCE SCORING
Use importance scores (0.0-1.0) to prioritize
- 0.9-1.0: Critical solutions, security fixes
- 0.7-0.8: Important patterns, architecture decisions
- 0.5-0.6: Useful tips, common patterns
- 0.0-0.4: General knowledge, references

## 4. RELATIONSHIP BUILDING
Connect related mementos
Benefits:
- Creates knowledge graph
- Enables path finding between related concepts
- Improves contextual search results

## 5. MEMORY TYPE SELECTION
Choose appropriate memory types
- solution: For fixes and workarounds
- pattern: For reusable code patterns
- technology: For framework/tool knowledge
- error: For error patterns and solutions
- general: For miscellaneous knowledge

## 6. CONTEXT ENRICHMENT
Add rich context to mementos
Context fields: project, language, framework, timestamp

## 7. REGULAR MAINTENANCE
Use these tools for database health:
- get_memento_statistics: Monitor database size
- get_recent_memento_activity: Track usage patterns
- analyze_memento_graph: Analyze relationship density

## 8. AVOID THESE COMMON MISTAKES
1. Over-persisting: Don't use _persistent for temporary data
2. Under-tagging: Always tag acronyms and key terms
3. Sparse relationships: Connect related memories
4. Vague titles: Use descriptive, specific titles
5. Missing context: Always include relevant context

## 9. INTEGRATION WITH SESSION MEMORY
Use both systems together:
1. Store current work in session memory
2. Extract patterns and solutions to memento
3. Reference memento knowledge during session work
4. Clean up session memory at end of project

## 10. CONFIDENCE SYSTEM MANAGEMENT (Advanced Profile Only)
For comprehensive confidence system documentation, see docs/DECAY_SYSTEM.md

### Quick Reference
- Confidence scores: 0.0-1.0 (higher = more reliable)
- Automatic decay: 5% monthly for unused knowledge
- No decay for: security, auth, api_key, password, critical, no_decay tags
- Search ordering: confidence * importance

### Available Tools
1. adjust_memento_confidence - Manual confidence adjustment
2. get_low_confidence_mementos - Find obsolete knowledge
3. apply_memento_confidence_decay - Apply automatic decay
4. boost_memento_confidence - Boost when validated
5. set_memento_decay_factor - Custom decay rates

## 11. PERFORMANCE OPTIMIZATION
- Use recall_mementos for conceptual queries
- Use search_mementos for exact term matching
- Use contextual_memento_search for scoped exploration
- Set appropriate limit parameters to avoid large result sets"""


def _generate_onboarding_protocol() -> str:
    """Generate Memento onboarding protocol."""
    return """# MEMENTO ONBOARDING PROTOCOL

## 1. INITIALIZATION
- **Session Start**: Always run `memento_onboarding` first to understand the protocol.
- **Tool Discovery**: Verify available Memento tools and their purposes.

## 2. RETRIEVAL FLOW (OPTIMIZED)
### A. FACT CHECK (Simple/Identity Queries)
Use `search_mementos(tags=[...])` for:
- Names, usernames, GitHub handles
- Basic facts and identity information
- Known acronyms and technical terms
- Exact matches needed

### B. COMPLEX TASKS (Development/Architecture)
Use `recall_mementos(query="...")` for:
- Development context and architecture decisions
- Conceptual queries and patterns
- Fuzzy matching and natural language
- General exploration of knowledge

### C. FALLBACK STRATEGY
If `search_mementos` fails or returns no results:
1. Fallback to `recall_mementos` with broader query
2. Check related memories with `get_related_mementos`
3. Use `get_recent_memento_activity` for context

## 3. AUTOMATIC STORAGE TRIGGERS
Store via `store_memento` immediately on:
- Git commits and version releases
- Bug fixes and solutions
- Architecture decisions and patterns
- Technology evaluations
- Important discoveries

## 4. ON-DEMAND TRIGGERS
Trigger `store_memento` INSTANTLY when user says:
- *"memento..."*, *"remember..."*, *"take note..."*
- *"ricorda..."*, *"segna..."*, *"memorizza..."* (Italian)
- Any equivalent in other languages

## 5. MEMORY SCHEMA REQUIREMENTS
### Required Tags (Always include):
- `project`: Project name or identifier
- `tech`: Technology or framework
- `category`: General category (e.g., "auth", "database", "api")

### Importance Scoring:
- **0.8+ (Critical)**: Security fixes, production issues, architecture decisions
- **0.5 (Standard)**: Regular solutions, patterns, best practices
- **0.3 (Reference)**: General knowledge, documentation

### Relationship Building:
Always link related mementos using `create_memento_relationship`:
- SOLVES: solution → problem
- CAUSES: cause → effect
- ADDRESSES: fix → error
- REQUIRES: dependent → dependency
- RELATED_TO: general relationship

## 6. AVOIDING INEFFICIENT TOOL USAGE
### Common Mistake: Using 6 tools before finding the right one
**Solution**: Follow this optimized flow:
1. **Simple facts** → `search_mementos(tags=[...])` (1 tool)
2. **Complex queries** → `recall_mementos(query="...")` (1 tool)
3. **Related context** → `get_related_mementos()` (1 tool)

### Tool Selection Matrix:
| Scenario | Primary Tool | Secondary Tool | Avoid |
|----------|--------------|----------------|-------|
| Simple fact | `search_mementos` | - | `recall_mementos` |
| Conceptual query | `recall_mementos` | `get_related_mementos` | Multiple searches |
| Related knowledge | `get_related_mementos` | `search_mementos` | Manual browsing |
| Recent activity | `get_recent_memento_activity` | - | Full database scan |

## 7. INTEGRATION WITH SESSION MEMORY
### Memento (Long-term):
- Solutions, patterns, architecture
- Cross-project knowledge
- Reusable code snippets

### Session Memory (Temporary):
- Current file context
- Temporary calculations
- Project-specific variables
- Session undo history

## 8. PERFORMANCE OPTIMIZATION
- Set appropriate `limit` parameters (default: 20)
- Use `offset` for pagination
- Filter by `memory_types` when possible
- Use `min_importance` for critical knowledge
- Cache frequently accessed memories"""


def _generate_retrieval_flow_guide() -> str:
    """Generate optimized retrieval flow guide."""
    return """# OPTIMIZED RETRIEVAL FLOW GUIDE

## PROBLEM: Inefficient Tool Usage
Memento agents often use 6+ tools before finding the right information.
This guide provides an optimized flow to reduce tool calls to 1-3.

## SOLUTION: Three-Step Retrieval Flow

### STEP 1: IDENTIFY QUERY TYPE
**Simple/Identity Query** (Use `search_mementos`):
- Known facts, names, acronyms
- Exact matches needed
- Tags are known

**Complex/Conceptual Query** (Use `recall_mementos`):
- Development context
- Architecture decisions
- Natural language queries
- Fuzzy matching needed

### STEP 2: SELECT PRIMARY TOOL
#### For SIMPLE queries:
```python
# GOOD: 1 tool call
search_mementos(tags=["jwt", "auth"], search_tolerance="strict")

# BAD: Multiple unnecessary calls
recall_mementos(query="jwt authentication")
get_memento(memory_id="...")
search_mementos(query="jwt")
```

#### For COMPLEX queries:
```python
# GOOD: 1-2 tool calls
recall_mementos(query="how to handle authentication timeout")
get_related_mementos(memory_id="found-memory-id")

# BAD: Sequential guessing
search_mementos(tags=["auth"])
search_mementos(tags=["timeout"])
recall_mementos(query="auth")
recall_mementos(query="timeout")
```

### STEP 3: APPLY FALLBACK STRATEGY
If primary tool returns no results:
1. **For `search_mementos` failures**:
   - Broaden tags or remove some
   - Change `search_tolerance` to "normal" or "fuzzy"
   - Fallback to `recall_mementos`

2. **For `recall_mementos` failures**:
   - Simplify query language
   - Use more specific terms
   - Try `search_mementos` with key terms as tags

## PRACTICAL EXAMPLES

### Example 1: Finding JWT Authentication Solution
**Inefficient (4+ tools):**
1. `recall_mementos(query="authentication")`
2. `search_mementos(tags=["auth"])`
3. `recall_mementos(query="jwt token")`
4. `search_mementos(tags=["jwt"])`

**Optimized (1 tool):**
```python
search_mementos(tags=["jwt", "auth", "authentication"])
```

### Example 2: Understanding Database Architecture
**Inefficient (5+ tools):**
1. `search_mementos(tags=["database"])`
2. `recall_mementos(query="db")`
3. `search_mementos(tags=["postgres"])`
4. `recall_mementos(query="postgresql architecture")`
5. `get_recent_memento_activity()`

**Optimized (2 tools):**
```python
# Step 1: Conceptual query
recall_mementos(query="database architecture patterns")

# Step 2: Get related context (if needed)
get_related_mementos(memory_id="architecture-memory-id")
```

## TOOL SELECTION DECISION TREE

1. **Do you know EXACT tags/terms?**
   - YES → `search_mementos(tags=[...])`
   - NO → Go to 2

2. **Is this a conceptual/development query?**
   - YES → `recall_mementos(query="...")`
   - NO → Go to 3

3. **Do you have a specific memory ID?**
   - YES → `get_memento(memory_id="...")`
   - NO → `get_recent_memento_activity()` for context

## PERFORMANCE METRICS
- **Target**: 1-3 tool calls for simple info
- **Maximum**: 5 tool calls for complex tasks
- **Avoid**: Sequential guessing with 6+ tools

## COMMON PITFALLS TO AVOID
1. **Tag under-specification**: Always include known acronyms as tags
2. **Query vagueness**: Be specific in `recall_mementos` queries
3. **Tool hopping**: Stick to primary tool before falling back
4. **Over-filtering**: Start broad, then narrow down"""


def _generate_comprehensive_onboarding() -> str:
    """Generate comprehensive onboarding covering all topics."""
    protocol = _generate_onboarding_protocol()
    retrieval_flow = _generate_retrieval_flow_guide()
    distinction = _generate_distinction_guide()
    examples = _generate_examples_guide()
    best_practices = _generate_best_practices_guide()

    return f"""{protocol}

---

{retrieval_flow}

---

{distinction}

---

{examples}

---

{best_practices}

---

# QUICK START CHECKLIST

## Session Start (Mandatory):
1. Run `memento_onboarding()` to understand protocol
2. Review available Memento tools
3. Understand retrieval flow optimization

## During Work:
1. Use optimized retrieval flow (1-3 tools max)
2. Follow automatic storage triggers
3. Apply memory schema requirements
4. Link related memories

## Session End:
1. Store important discoveries
2. Verify memory relationships
3. Clean up session memory

# NEED HELP?
Use these tools for assistance:
- `memento_onboarding(topic="protocol")` - Full onboarding protocol
- `memento_onboarding(topic="retrieval_flow")` - Optimized retrieval guide
- `memento_onboarding(topic="distinction")` - Memento vs Session memory
- `memento_onboarding(topic="examples")` - Practical examples
- `memento_onboarding(topic="best_practices")` - Usage guidelines
- `get_recent_memento_activity()` - Recent usage patterns
- `get_memento_statistics()` - Database health check

# CONFIDENCE SYSTEM QUICK REFERENCE

For complete confidence system documentation, see docs/DECAY_SYSTEM.md

## Quick Tips
- Confidence scores: 0.0-1.0 (higher = more reliable)
- No decay tags: security, auth, api_key, password, critical, no_decay
- Search ordering: confidence * importance
- Monthly maintenance: apply_memento_confidence_decay()
- Use `get_low_confidence_mementos()` to find obsolete knowledge
"""
