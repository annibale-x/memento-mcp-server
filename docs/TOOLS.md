# ContextKeeper Tools Reference

Complete guide to all MCP tools in ContextKeeper, including usage patterns and configuration.

---

## Quick Start: Tool Selection

Follow this decision tree when working with memories:

```
User Request
│
├─ Recall/Search Query? → START WITH recall_persistent_memories
│  ├─ Results found? → Use get_persistent_memory or get_related_persistent_memories for details
│  └─ No results? → Try search_persistent_memories with different parameters
│
├─ Store New Information? → START WITH store_persistent_memory
│  └─ After storing? → Use create_persistent_relationship to link related memories
│
├─ Explore Connections? → START WITH get_related_persistent_memories
│
├─ Update/Delete? → get_persistent_memory first, then update_persistent_memory or delete_persistent_memory
│
├─ Confidence Management? → Use confidence system tools for knowledge quality
│  ├─ Find obsolete memories? → get_persistent_low_confidence_memories
│  ├─ Boost valid memory? → boost_persistent_confidence
│  └─ Manual adjustment? → adjust_persistent_confidence
│
└─ Overview/Stats? → get_persistent_memory_statistics
```

---

## Profile Overview

| Profile | Tool Count | Description | Use Case |
|---------|------------|-------------|----------|
| **core** | 13 | Essential memory operations + confidence basics | Default for 95% of users |
| **extended** | 17 | Core + analytics + contextual search + confidence maintenance | Power users |
| **advanced** | 25 | Extended + graph analysis + advanced confidence configuration | Administrators |

### Quick Comparison

| Feature | Core (Default) | Extended | Advanced |
|---------|----------------|----------|----------|
| Memory CRUD | ✅ 5 tools | ✅ 5 tools | ✅ 5 tools |
| Relationships | ✅ 2 tools | ✅ 2 tools | ✅ 2 tools |
| Discovery | ✅ 2 tools | ✅ 2 tools | ✅ 2 tools |
| Confidence Basics | ✅ 3 tools | ✅ 3 tools | ✅ 3 tools |
| Database Stats | ❌ | ✅ 1 tool | ✅ 1 tool |
| Complex Queries | ❌ | ✅ 1 tool | ✅ 1 tool |
| Contextual Search | ❌ | ✅ 1 tool | ✅ 1 tool |
| Confidence Maintenance | ❌ | ✅ 1 tool | ✅ 1 tool |
| Graph Analysis | ❌ | ❌ | ✅ 7 tools |
| Advanced Confidence | ❌ | ❌ | ✅ 1 tool |

---

## Core Profile (13 tools) - DEFAULT

### Primary Tools (Use First)

#### 1. recall_persistent_memories 🎯 RECOMMENDED FIRST CHOICE

**Use for**:
- Any recall or search query from user
- "What did we learn about X?"
- "Show me solutions for Y"
- "Catch me up on this project"

**Why first**:
- Optimized defaults (fuzzy matching, relationships included)
- Simpler interface for natural language queries
- Best results for common use cases
- **Automatic confidence sorting**: Results ordered by confidence score

**When to skip**:
- Need exact match only → use `search_persistent_memories` with `search_tolerance="strict"`
- Need advanced boolean queries → use `search_persistent_memories`

#### 2. store_persistent_memory

**Use for**:
- Capturing new solutions, problems, errors, decisions
- Recording patterns or learnings
- Documenting technology choices

**Always follow with**:
- `create_persistent_relationship` to link to related memories

#### 3. create_persistent_relationship

**Use for**:
- After storing a solution → link to problem it solves
- After documenting an error → link to its fix
- Connecting decisions to what they improve

**Common patterns**:
- solution SOLVES problem
- fix ADDRESSES error
- decision IMPROVES previous_approach
- pattern APPLIES_TO project

**35+ relationship types** across categories: Causation, Solution, Context, Dependency, Knowledge, Comparison, Workflow.

### Secondary Tools (Drill-Down)

#### 4. search_persistent_memories

**Use when recall_persistent_memories isn't suitable**:
- Need strict exact matching (`search_tolerance="strict"`)
- Need to search with specific tags
- Need to filter by importance threshold
- Advanced queries requiring fine control
- Need pagination for large result sets

**Pagination**:
```python
# First page (results 0-49)
search_persistent_memories(query="authentication", limit=50, offset=0)

# Second page (results 50-99)
search_persistent_memories(query="authentication", limit=50, offset=50)
```

#### 5. get_persistent_memory

**Use for**:
- Getting full details when you have a specific ID
- Verifying memory before update/delete
- Drilling down from search results

#### 6. get_related_persistent_memories

**Use for**:
- After finding a memory, explore what connects to it
- "What caused this problem?"
- "What solutions exist for this?"
- Following chains of reasoning

**Filter by relationship types**:
- `relationship_types=["SOLVES"]` → Find solutions
- `relationship_types=["CAUSES", "TRIGGERS"]` → Find causes
- `relationship_types=["USED_IN"]` → Find where pattern applies

### Utility Tools

#### 7. update_persistent_memory

**Use for**: Corrections, adding tags, updating importance.
**Always**: Use `get_persistent_memory` first to verify contents.

#### 8. delete_persistent_memory

**Use for**: Removing obsolete or incorrect memories.
**Warning**: Deletes all relationships too (cascade). Irreversible.

#### 9. get_persistent_recent_activity

**Use for**:
- Session briefing and progress tracking
- Summary of recent memories (last N days)
- Unresolved problems highlighted
- "Catch me up" functionality

### 10. help_memory_tools_usage

**Use for**:
- Understanding the difference between persistent and session memory
- Learning best practices for memory storage
- Getting guidance on when to use which tool

### Confidence System Tools (Now in Core)

#### 11. get_persistent_low_confidence_memories

**Use for**:
- Finding memories with low confidence scores
- Identifying potentially obsolete knowledge
- Periodic cleanup and verification
- Quality assurance of the knowledge base

**Features**:
- Filter by confidence threshold (default: < 0.3)
- Shows relationships causing low confidence
- Includes memory details and last access time
- Sorted by confidence (lowest first)

#### 12. boost_persistent_confidence

**Use for**:
- Boosting confidence when a memory is successfully used
- Reinforcing valid knowledge
- Manual confidence increase for verified information

**Usage patterns**:
- After successfully applying a solution → boost its confidence
- When verifying old information is still valid → boost confidence
- When multiple team members confirm a pattern → boost confidence

#### 13. adjust_persistent_confidence

**Use for**:
- Manually adjusting confidence of a relationship
- Correcting confidence scores when you know a memory is valid/invalid
- Setting custom confidence based on verification

**Examples**:
- `adjust_persistent_confidence(relationship_id="rel-123", new_confidence=0.9, reason="Verified in production")`
- `adjust_persistent_confidence(relationship_id="rel-456", new_confidence=0.1, reason="Obsolete after library update")`

---

## Extended Profile (17 tools)

All Core tools plus:

### 14. apply_persistent_confidence_decay

**Use for**:
- Applying automatic confidence decay based on last access time
- System maintenance to keep knowledge base fresh
- Applying intelligent decay rules:
  - Critical memories (security, auth, api_key): No decay
  - High importance memories: Reduced decay
  - General knowledge: Normal decay (5% per month)

**Intelligent decay**:
- API keys, passwords, security info: No decay (decay_factor=1.0)
- Critical solutions (importance > 0.9): Low decay (decay_factor=0.98)
- General knowledge: Normal decay (decay_factor=0.95)
- Temporary context: High decay (decay_factor=0.90)

### 15. get_persistent_memory_statistics

**Use for**:
- Database overview and metrics
- Total memories and relationships
- Breakdown by memory type
- Average importance scores

### 16. search_persistent_relationships_by_context

**Use for**:
- Complex relationship queries
- Search by structured context fields (scope, conditions, evidence)
- Filter by implementation scope (partial/full/conditional)
- Advanced relationship analytics

### 17. persistent_contextual_search

**Use for**:
- Scoped search within related memories
- Two-phase search: find related memories, then search within that set
- Search within a specific problem context
- No leakage outside context boundary

---

## Advanced Profile (25 tools)

All Extended tools plus:

### Confidence System Tools (Advanced)

#### 18. set_persistent_decay_factor

**Use for**:
- Setting custom decay factor for specific memories
- Marking memories as "no decay" (critical information)
- Adjusting decay rates based on importance

**Special tags for no decay**:
- `security`, `auth`, `api_key`, `password`, `critical`, `no_decay`

**Decay factor ranges**:
- 1.0: No decay (critical information)
- 0.98-0.99: Very low decay (high importance)
- 0.95-0.97: Normal decay (general knowledge)
- 0.90-0.94: High decay (temporary context)
- 0.80-0.89: Very high decay (ephemeral data)

### Graph Analysis Tools

#### 19. analyze_persistent_memory_graph

**Use for**:
- Comprehensive analytics and metrics for the persistent memory graph
- Relationship density analysis
- Graph structure visualization

#### 20. find_persistent_patterns

**Use for**:
- Detecting patterns in persistent memories and relationships
- Finding recurring solution patterns
- Identifying common problem-solution pairs

#### 21. suggest_persistent_relationships

**Use for**:
- Getting intelligent suggestions for relationship types between memories
- Discovering potential connections between memories
- Enhancing the knowledge graph

#### 22. get_persistent_memory_clusters

**Use for**:
- Detecting clusters of densely connected persistent memories
- Finding topic groups and related concepts
- Understanding knowledge organization

#### 23. get_persistent_central_memories

**Use for**:
- Finding persistent memories that connect different clusters
- Identifying knowledge bridges and central concepts
- Discovering key memories in the graph

#### 24. find_path_between_persistent_memories

**Use for**:
- Finding the shortest path between two persistent memories
- Discovering connection chains between concepts
- Understanding how memories are related

#### 25. get_persistent_memory_network

**Use for**:
- Getting the complete network structure of persistent memories
- Full graph analysis and visualization
- Understanding the overall knowledge structure

---

## Common Usage Patterns

### Pattern: Confidence System Maintenance

```python
# Monthly maintenance routine:
# 1. Find low confidence memories
low_conf = get_persistent_low_confidence_memories(threshold=0.3, limit=50)

# 2. Apply automatic decay
apply_persistent_confidence_decay()

# 3. Review and adjust
for memory in low_conf:
    if memory_is_still_valid(memory):
        boost_persistent_confidence(memory_id=memory.id, boost_amount=0.2, reason="Monthly verification")
    else:
        # Mark for deletion or adjustment
        adjust_persistent_confidence(relationship_id=..., new_confidence=0.1, reason="Obsolete")
```

### Pattern: Critical Information Protection

```python
# When storing critical information, use special tags:
store_persistent_memory(
    type="technology",
    title="Production API Key for Service X",
    content="key: abc123...",
    tags=["api_key", "security", "production", "no_decay"],  # Critical tags
    importance=0.95  # High importance
)

# These memories will have:
# - No automatic confidence decay
# - Always high in search results
# - Protected from accidental obsolescence
```

### Pattern: "What did we learn about X?"

```
Step 1: recall_persistent_memories(query="X")
Step 2: [Present results - automatically sorted by confidence]
Step 3 (if low confidence warning): Check with get_persistent_low_confidence_memories
Step 4 (if user asks): get_persistent_memory(memory_id="...")
Step 5 (if user wants connections): get_related_persistent_memories(memory_id="...")
```

### Pattern: User Solves a Problem

```python
# Step 1: Store the solution
store_persistent_memory(
    type="solution",
    title="Fixed Redis timeout with 30s connection timeout",
    content="...",
    tags=["redis", "timeout", "production_fix"],
    importance=0.8
)
# → Returns memory_id: "sol-123"

# Step 2: Find related problem
recall_persistent_memories(query="Redis timeout", memory_types=["problem", "error"])
# → Finds memory_id: "prob-456"

# Step 3: Create link
create_persistent_relationship(
    from_memory_id="sol-123",
    to_memory_id="prob-456",
    relationship_type="SOLVES"
)

# Step 4: Boost confidence (optional but recommended)
boost_persistent_confidence(
    memory_id="sol-123",
    boost_amount=0.15,
    reason="Successfully applied in production"
)
```

### Pattern: "Catch me up"

```
Step 1: get_persistent_recent_activity(days=7, project="/current/project")
Step 2: Check for low confidence memories: get_persistent_low_confidence_memories(threshold=0.4)
Step 3: Present summary with unresolved problems and confidence warnings highlighted
```

### Pattern: Knowledge Base Quality Check

```
Step 1: get_persistent_low_confidence_memories(threshold=0.3, limit=20)
Step 2: Review each memory for validity
Step 3: For valid memories: boost_persistent_confidence
Step 4: For obsolete memories: adjust_persistent_confidence or delete_persistent_memory
```

---

## Profile Configuration

### Environment Variable

```bash
# Core (default)
export CONTEXT_TOOL_PROFILE=core

# Extended
export CONTEXT_TOOL_PROFILE=extended

# Advanced
export CONTEXT_TOOL_PROFILE=advanced
```

### CLI Flag

```bash
# Core (default)
context_keeper

# Extended
context_keeper --profile extended

# Advanced
context_keeper --profile advanced
```

### MCP Configuration

```json
{
  "mcpServers": {
    "context_keeper": {
      "command": "context_keeper",
      "args": ["--profile", "extended"],
      "env": {
        "CONTEXT_SQLITE_PATH": "~/.mcp-context-keeper/context.db",
        "CONTEXT_TOOL_PROFILE": "extended",
      }
    }
  }
}
```

---

## Choosing Your Profile

### Use Core Profile If:
- ✅ You're getting started
- ✅ You need basic memory storage and retrieval
- ✅ You want zero configuration
- ✅ You're a typical user (95% of use cases)
- ✅ You want confidence management basics

### Use Extended Profile If:
- ✅ You need database statistics
- ✅ You want advanced relationship queries
- ✅ You're analyzing patterns across large memory sets
- ✅ You need contextual/scoped search
- ✅ You want automatic confidence decay maintenance

### Use Advanced Profile If:
- ✅ You need graph analysis and clustering
- ✅ You want to find patterns and relationships
- ✅ You need to understand the knowledge graph structure
- ✅ You're doing research or advanced analysis
- ✅ You need custom decay factor configuration

---

## Anti-Patterns to Avoid

**❌ Don't**:
- Use search_persistent_memories when recall_persistent_memories would work
- Call get_persistent_memory without an ID
- Create memory without considering relationships
- Use exact match search as default
- Ignore low confidence warnings

**✅ Do**:
- Start with recall_persistent_memories for all searches
- Use create_persistent_relationship after storing related memories
- Filter by memory_types for precision
- Use get_related_persistent_memories to explore context
- Use help_memory_tools_usage when unsure about tool selection
- Check get_persistent_low_confidence_memories periodically
- Boost confidence for validated solutions

---

## IMPORTANT: Persistent vs Session Memory

All tools in ContextKeeper use the `_persistent` suffix to distinguish them from session memory tools in Serena Context Server:

### Persistent Memory Tools (`_persistent` suffix):
- **Scope**: Global - accessible from ANY project or session
- **Persistence**: Long-term - survives across ALL sessions
- **Purpose**: Store reusable knowledge, solutions, patterns
- **Examples**: `store_persistent_memory`, `get_persistent_memory`, `search_persistent_memories`

### Session Memory Tools (no suffix in Serena):
- **Scope**: Project-specific - only accessible within current project
- **Persistence**: Temporary - lasts only for current session
- **Purpose**: Store ephemeral context, temporary variables
- **Examples**: `store_memory`, `get_memory`, `search_memories` (in Serena Context Server)

### When to Use Which:
- **Need it tomorrow or across projects?** → Use `_persistent` suffix tools
- **Only need it for current session?** → Use session memory tools (no suffix)
- **Storing solutions, patterns, decisions?** → Always use `_persistent` suffix
- **Storing temporary work context?** → Use session memory tools

For detailed guidance, use the `help_memory_tools_usage` tool.