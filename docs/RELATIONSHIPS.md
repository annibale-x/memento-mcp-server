# Relationship Types Reference - MCP Memento

## Introduction to Relationships in Memento

Relationships are the core of the Memento system. They allow connecting memories together to create a structured knowledge network. Each relationship has:
- **A type** (e.g., `SOLVES`, `CAUSES`, `APPLIES_TO`)
- **A direction** (from memory A to memory B)
- **A strength** (0.0-1.0, default 0.5)
- **A confidence** (0.0-1.0, default 0.8)
- **Optional context** (textual description)

### Why Relationships are Important

1. **Intelligent search**: Find solutions linked to problems
2. **Contextual navigation**: Explore related knowledge
3. **Intelligent decay**: Unused relationships lose confidence
4. **Graph analysis**: Discover hidden patterns and connections

### How to Use Relationships

> **📌 Note**: Code examples in this document are **MCP tool call pseudocode** — they
> show the tool name and arguments to pass to your AI assistant or MCP client.
> They are **not** importable Python functions. See [PYTHON.md](integrations/PYTHON.md)
> for the MCP client pattern.

```python
# Example: linking a solution to a problem
await create_memento_relationship(
    from_memory_id="sol-123",      # Solution ID
    to_memory_id="prob-456",       # Problem ID
    relationship_type="SOLVES",    # Relationship type
    strength=0.9,                  # Relationship strength
    confidence=0.8,                # Initial confidence
    context="This solution solves the database timeout issue"
)
```

---

## Relationship Categories

Memento organizes relationships into 7 semantic categories:

### 1. Causal Relationships
Cause-effect, activation, prevention

### 2. Solution Relationships
Problem resolution, improvements, alternatives

### 3. Context Relationships
Applicability, dependencies, environments

### 4. Learning Relationships
Knowledge building, confirmations, contradictions

### 5. Similarity Relationships
Analogies, variants, oppositions

### 6. Workflow Relationships
Sequences, dependencies, parallelism

### 7. Quality Relationships
Effectiveness, preferences, validations

---

## Complete List of Relationship Types

### 1. Causal Relationships (5 types)

| Type | Direction | When to Use | Example |
|------|-----------|-------------|---------|
| **`CAUSES`** | Cause → Effect | A directly causes B | "Configuration error → Timeout" |
| **`TRIGGERS`** | Activator → Activated | A initiates or activates B | "Click event → Modal opening" |
| **`LEADS_TO`** | Start → Result | A eventually leads to B | "Refactor → Better performance" |
| **`PREVENTS`** | Preventive → Event | A prevents B from happening | "Backup → Data loss prevention" |
| **`BREAKS`** | Breaker → System | A breaks or disrupts B | "Library update → Broken build" |

### 2. Solution Relationships (5 types)

| Type | Direction | When to Use | Example |
|------|-----------|-------------|---------|
| **`SOLVES`** | Solution → Problem | A completely solves B | "Connection pooling → Database timeout" |
| **`ADDRESSES`** | Approach → Problem | A partially addresses B | "Partial cache → API slowness" |
| **`ALTERNATIVE_TO`** | Alternative → Original | A is an alternative to B (bidirectional) | "Redis → Memcached" |
| **`IMPROVES`** | Improved → Original | A improves upon B | "v2.0 → v1.0" |
| **`REPLACES`** | Replacement → Original | A replaces or supersedes B | "New API → Legacy API" |

### 3. Context Relationships (5 types)

| Type | Direction | When to Use | Example |
|------|-----------|-------------|---------|
| **`OCCURS_IN`** | Event → Context | A occurs within context B | "Bug → Production environment" |
| **`APPLIES_TO`** | Pattern → Context | A applies to or is relevant in context B | "Error handling pattern → Web API project" |
| **`WORKS_WITH`** | Component → Component | A works together with B (bidirectional) | "Frontend → Backend" |
| **`REQUIRES`** | Dependent → Dependency | A requires B to function | "Feature → Database migration" |
| **`USED_IN`** | Component → System | A is used within system B | "Authentication module → Web application" |

### 4. Learning Relationships (5 types)

| Type | Direction | When to Use | Example |
|------|-----------|-------------|---------|
| **`BUILDS_ON`** | Advanced → Foundation | A builds upon knowledge from B | "Advanced pattern → Basic pattern" |
| **`CONTRADICTS`** | Contradiction → Statement | A contradicts information in B (bidirectional) | "New finding → Previous assumption" |
| **`CONFIRMS`** | Evidence → Hypothesis | A confirms or validates B | "Test results → Implementation hypothesis" |
| **`GENERALIZES`** | General → Specific | A is a generalization of B | "Design pattern → Specific implementation" |
| **`SPECIALIZES`** | Specific → General | A is a specialization of B | "Specific algorithm → General algorithm category" |

### 5. Similarity Relationships (5 types)

| Type | Direction | When to Use | Example |
|------|-----------|-------------|---------|
| **`SIMILAR_TO`** | Item → Item | A is similar to B (bidirectional) | "Python solution → JavaScript solution" |
| **`VARIANT_OF`** | Variant → Original | A is a variant or version of B | "Dark theme → Light theme" |
| **`RELATED_TO`** | Item → Item | A is related to B in some way (bidirectional) | "Authentication → Authorization" |
| **`ANALOGY_TO`** | Analogy → Concept | A serves as an analogy for B | "Car engine → Software architecture" |
| **`OPPOSITE_OF`** | Opposite → Concept | A is the opposite or inverse of B (bidirectional) | "Success case → Failure case" |

### 6. Workflow Relationships (5 types)

| Type | Direction | When to Use | Example |
|------|-----------|-------------|---------|
| **`FOLLOWS`** | Later → Earlier | A follows B in sequence | "Deployment → Testing" |
| **`DEPENDS_ON`** | Dependent → Dependency | A depends on B to proceed | "Feature implementation → API design" |
| **`ENABLES`** | Enabler → Enabled | A enables B to happen | "Infrastructure setup → Application deployment" |
| **`BLOCKS`** | Blocker → Blocked | A blocks B from proceeding | "Missing dependency → Build process" |
| **`PARALLEL_TO`** | Process → Process | A runs parallel to B (bidirectional) | "Frontend development → Backend development" |

### 7. Quality Relationships (5 types)

| Type | Direction | When to Use | Example |
|------|-----------|-------------|---------|
| **`EFFECTIVE_FOR`** | Solution → Use Case | A is effective for use case B | "Redis cache → High-read scenarios" |
| **`INEFFECTIVE_FOR`** | Solution → Use Case | A is ineffective for use case B | "Simple cache → Real-time data" |
| **`PREFERRED_OVER`** | Preferred → Alternative | A is preferred over B | "TypeScript → JavaScript for large projects" |
| **`DEPRECATED_BY`** | Deprecated → Replacement | A is deprecated by B | "Old API → New API" |
| **`VALIDATED_BY`** | Implementation → Validation | A is validated by B | "Code change → Test suite" |

---

## Practical Usage Examples

### Example 1: Bug Fix Workflow

```python
# Store the problem
problem_id = await store_memento(
    type="problem",
    title="Database connection timeout under load",
    content="API fails when concurrent users exceed 100",
    tags=["database", "performance", "api"]
)

# Store the solution
solution_id = await store_memento(
    type="solution",
    title="Implemented connection pooling",
    content="Added connection pool with max 50 connections",
    tags=["database", "optimization"]
)

# Link solution to problem
await create_memento_relationship(
    from_memory_id=solution_id,
    to_memory_id=problem_id,
    relationship_type="SOLVES",
    strength=0.9,
    context="Connection pooling resolved the timeout issue"
)
```

### Example 2: Architecture Decision

```python
# Store the decision
decision_id = await store_memento(
    type="general",
    title="Chose Redis over Memcached for caching",
    content="Redis chosen for persistence and data structures",
    tags=["architecture", "caching", "redis"]
)

# Store the alternative considered
alternative_id = await store_memento(
    type="pattern",
    title="Memcached caching pattern",
    content="Simple key-value caching approach",
    tags=["caching", "memcached"]
)

# Link decision to alternative
await create_memento_relationship(
    from_memory_id=decision_id,
    to_memory_id=alternative_id,
    relationship_type="PREFERRED_OVER",
    strength=0.8,
    context="Redis preferred for persistence features"
)
```

### Example 3: Learning Pattern

```python
# Store basic pattern
basic_id = await store_memento(
    type="code_pattern",
    title="Basic error handling with try-catch",
    content="Simple try-catch block for error handling",
    tags=["python", "error-handling", "beginner"]
)

# Store advanced pattern
advanced_id = await store_memento(
    type="code_pattern",
    title="Structured error handling with custom exceptions",
    content="Custom exception hierarchy and context managers",
    tags=["python", "error-handling", "advanced"]
)

# Link advanced to basic
await create_memento_relationship(
    from_memory_id=advanced_id,
    to_memory_id=basic_id,
    relationship_type="BUILDS_ON",
    strength=0.7,
    context="Advanced pattern builds on basic error handling concepts"
)
```

---

## Best Practices for Relationship Usage

### 1. Choose the Most Specific Type
- Use `SOLVES` instead of `RELATED_TO` when a solution fixes a problem
- Use `CAUSES` instead of `LEADS_TO` when there's direct causation
- Use `APPLIES_TO` instead of `RELATED_TO` for pattern-context relationships

### 2. Set Appropriate Strength Values
- **0.9-1.0**: Strong, verified relationships (proven solutions)
- **0.7-0.8**: Good evidence, likely correct (tested patterns)
- **0.5-0.6**: Moderate evidence, needs verification (hypotheses)
- **0.3-0.4**: Weak connection, speculative (ideas to explore)
- **0.1-0.2**: Very weak, needs validation (unverified connections)

### 3. Provide Meaningful Context
Always include context that explains:
- Why the relationship exists
- What evidence supports it
- How it was verified
- Any limitations or conditions

### 4. Create Relationships Immediately
Link memories when you create them, not later. This ensures:
- Fresh context in your mind
- Consistent relationship creation
- No forgotten connections

### 5. Review and Update Periodically
- Use `get_low_confidence_mementos()` to find low-confidence connections and memories needing review
- Update confidence based on new evidence
- Remove obsolete mementos (and their cascading relationships) with `delete_memento()`

---

## Common Relationship Patterns

### Development Workflow
1. Problem → (`CAUSES`) → Symptoms
2. Solution → (`SOLVES`) → Problem
3. Pattern → (`APPLIES_TO`) → Project
4. Decision → (`PREFERRED_OVER`) → Alternative

### Learning Progression
1. Basic → (`BUILDS_ON`) → Foundation
2. Advanced → (`GENERALIZES`) → Concepts
3. Example → (`EXEMPLIFIES`) → Pattern
4. Finding → (`CONFIRMS`/`CONTRADICTS`) → Hypothesis

### System Architecture
1. Component → (`DEPENDS_ON`) → Dependency
2. Service → (`WORKS_WITH`) → Service
3. Update → (`BREAKS`) → Compatibility
4. Migration → (`REPLACES`) → Legacy

---

## Relationship Search Examples

### Find Solutions to a Problem
```python
solutions = await get_related_mementos(
    memory_id=problem_id,
    relationship_types=["SOLVES", "ADDRESSES"],
    max_depth=1
)
```

### Find Root Causes
```python
causes = await get_related_mementos(
    memory_id=symptom_id,
    relationship_types=["CAUSES", "TRIGGERS"],
    max_depth=2  # Go deeper to find root causes
)
```

### Find Related Patterns
```python
patterns = await get_related_mementos(
    memory_id=project_id,
    relationship_types=["APPLIES_TO", "USED_IN"],
    max_depth=1
)
```

### Find Learning Dependencies
```python
prerequisites = await get_related_mementos(
    memory_id=advanced_topic_id,
    relationship_types=["BUILDS_ON", "REQUIRES"],
    max_depth=3
)
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. "No relationships found" when searching
- Check relationship types are spelled correctly (case-sensitive)
- Verify memory IDs exist
- Ensure relationships were created in the correct direction
- Try broader relationship types like `RELATED_TO`

#### 2. Relationships not appearing in search results
- Check confidence thresholds (low confidence relationships may be filtered)
- Verify `last_accessed` timestamps are updating
- Ensure decay hasn't reduced confidence below visible thresholds

#### 3. Choosing the wrong relationship type
- Use `suggest_memento_relationships()` for intelligent suggestions
- Review the relationship categories above
- When in doubt, use `RELATED_TO` with clear context

#### 4. Relationship strength feels arbitrary
- Start with defaults (strength=0.5, confidence=0.8)
- Adjust based on evidence: more evidence = higher values
- Use the strength guidelines above as reference

---

## Quick Reference Cheat Sheet

### Most Frequently Used Types
- `SOLVES`: Solution → Problem
- `CAUSES`: Cause → Effect
- `APPLIES_TO`: Pattern → Context
- `DEPENDS_ON`: Dependent → Dependency
- `RELATED_TO`: General connection (when unsure)

### Bidirectional Relationships
- `ALTERNATIVE_TO`
- `CONTRADICTS`
- `SIMILAR_TO`
- `RELATED_TO`
- `OPPOSITE_OF`
- `WORKS_WITH`
- `PARALLEL_TO`

### Strength Guidelines
- **High (0.9+)**: Proven, tested, verified
- **Medium (0.6-0.8)**: Good evidence, likely correct
- **Low (0.3-0.5)**: Some evidence, needs verification
- **Very Low (0.0-0.2)**: Speculative, unverified

---

## Additional Resources

- [TOOLS.md](./TOOLS.md) - Complete tool reference
- [RULES.md](./RULES.md) - Usage rules and best practices
- [AGENT_CONFIGURATION.md](./AGENT_CONFIGURATION.md) - Agent configuration examples
- [DECAY_SYSTEM.md](./DECAY_SYSTEM.md) - Confidence and decay system

For questions or issues, refer to the Memento documentation or contact the development team.