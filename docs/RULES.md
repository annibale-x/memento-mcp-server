# Usage Rules and Best Practices

This document outlines the rules, conventions, and best practices for using Memento effectively.

## Table of Contents
- [Memory Creation Rules](#memory-creation-rules)
- [Tagging Conventions](#tagging-conventions)
- [Importance Scoring](#importance-scoring)
- [Relationship Guidelines](#relationship-guidelines)
- [Confidence Management](#confidence-management)
- [Search Optimization](#search-optimization)
- [Team Collaboration](#team-collaboration)
- [Configuration Templates](#configuration-templates)
- [Maintenance Schedule](#maintenance-schedule)

## Memory Creation Rules

### 1. What to Store
**DO store:**
- Solutions to recurring problems
- Architecture decisions and trade-offs
- Code patterns and best practices
- Configuration examples that work
- Debugging procedures
- Team conventions and standards
- Learning resources and references

**AVOID storing:**
- Temporary work in progress
- Personal notes unrelated to work
- Highly specific one-time fixes
- Sensitive information (passwords, keys)
- Duplicate information

### 2. Title Guidelines
- **Be descriptive**: "Fixed Redis connection timeout with connection pooling" not "Bug fix"
- **Include key terms**: Mention technologies and problem types
- **Keep it concise**: 5-10 words maximum
- **Use present tense**: "Handles" not "Handled"

### 3. Content Structure
```markdown
# Problem/Context
Brief description of the situation

# Solution/Pattern
Detailed explanation of the solution

# Implementation
Code examples or configuration

# Notes
Additional context, alternatives considered, trade-offs
```

## Tagging Conventions

### 1. Tag Categories
Use consistent tag categories:

| Category | Examples | Purpose |
|----------|----------|---------|
| **Technology** | `python`, `react`, `postgresql`, `docker` | Primary technology |
| **Problem Type** | `bug`, `performance`, `security`, `scaling` | Type of issue |
| **Solution Type** | `fix`, `pattern`, `optimization`, `refactor` | Nature of solution |
| **Domain** | `auth`, `database`, `api`, `ui`, `devops` | Functional area |
| **Status** | `verified`, `production`, `deprecated` | Current state |

### 2. Tag Format
- **Lowercase only**: `python` not `Python`
- **Hyphens for multi-word**: `web-socket` not `websocket` or `web_socket`
- **No spaces**: Use `database-migration` not `database migration`
- **Singular form**: Prefer `library` over `libraries`

### 3. Required Tags
Every memory should have at least:
- One technology tag
- One domain tag
- One solution type tag

### 4. Special Tags
- `no_decay`: Prevents confidence decay (use sparingly)
- `critical`: High importance, appears in critical searches
- `security`, `auth`, `api_key`: Protected from decay
- `deprecated`: Mark as obsolete
- `team-*`: Team-specific tags (e.g., `team-backend`)

## Importance Scoring

### 1. Scoring Guidelines
| Score | When to Use | Examples |
|-------|-------------|----------|
| **0.9-1.0** | Critical solutions, security fixes, core patterns | Authentication bypass fix, Production outage solution |
| **0.7-0.8** | Important patterns, architecture decisions | Database schema pattern, API design decision |
| **0.5-0.6** | Useful tips, common patterns, best practices | Logging configuration, Error handling pattern |
| **0.3-0.4** | General knowledge, references, learning resources | Library overview, Tutorial summary |
| **0.1-0.2** | Minor tips, personal preferences, experimental | Code style preference, Experimental approach |

### 2. Scoring Factors
Consider these factors when assigning importance:
- **Impact**: How many users/features are affected?
- **Frequency**: How often does this problem occur?
- **Complexity**: How difficult was the solution?
- **Novelty**: Is this a unique or innovative approach?
- **Verification**: Has this been proven in production?

## Relationship Guidelines

### 1. Relationship Types
Use the most specific relationship type available:

| Type | Direction | When to Use |
|------|-----------|-------------|
| **SOLVES** | Solution → Problem | A solution fixes a specific problem |
| **CAUSES** | Cause → Effect | One thing causes another |
| **IMPROVES** | Improved → Original | Better version of something |
| **USES** | Component → Dependency | One thing uses another |
| **DEPENDS_ON** | Dependent → Dependency | Requires another component |
| **RELATED_TO** | Any → Any | General relationship |
| **ALTERNATIVE_TO** | Alternative → Original | Different approach to same problem |
| **EXEMPLIFIES** | Example → Pattern | Concrete example of a pattern |
| **PRECEDES** | Earlier → Later | Temporal sequence |
| **CONTRADICTS** | Contradiction → Statement | Contradictory information |

### 2. Relationship Strength
Set appropriate confidence for relationships:
- **0.9-1.0**: Strong, verified relationships
- **0.7-0.8**: Good evidence, likely correct
- **0.5-0.6**: Moderate evidence, needs verification
- **0.3-0.4**: Weak connection, speculative
- **0.1-0.2**: Very weak, needs validation

### 3. Relationship Creation Rules
1. **Create immediately**: Link memories when you create them
2. **Be specific**: Use the most precise relationship type
3. **Add context**: Include why the relationship exists
4. **Review periodically**: Verify relationships are still valid
5. **Avoid cycles**: Be careful with circular relationships

## Confidence Management

### 1. Automatic Decay Rules
- **Base decay**: 5% monthly for unused memories
- **No decay**: Memories with `no_decay`, `security`, `auth`, `api_key`, `critical` tags
- **Reduced decay**: High importance (0.8+) memories decay 2.5% monthly
- **Accelerated decay**: Low importance (0.3-) memories decay 7.5% monthly

### 2. Confidence Boosting
Boost confidence when:
- **Solution is reused** successfully (+0.01 per use)
- **Memory is verified** in production (+0.05 to +0.20)
- **Multiple team members** confirm (+0.10)
- **Time-based validation** (quarterly review, +0.05)

### 3. Low Confidence Handling
When confidence drops below 0.3:
1. **Review**: Check if memory is still valid
2. **Update**: Refresh content if needed
3. **Boost**: Increase confidence if still relevant
4. **Archive**: Delete or deprecate if obsolete

### 4. Critical Memory Protection
Memories with these tags never decay:
- `security`
- `auth`
- `api_key`
- `password`
- `critical`
- `no_decay`

## Search Optimization

### 1. Search Strategy
```python
# 1. Start with natural language search
results = recall_mementos(
    query="how to handle database migrations",
    limit=10
)

# 2. If no results, try advanced search
if not results:
    results = search_mementos(
        query="database migration",
        tags=["postgresql", "migration"],
        memory_types=["solution", "pattern"],
        limit=15
    )

# 3. Explore relationships
if results:
    related = get_related_mementos(
        memory_id=results[0]["id"],
        relationship_types=["RELATED_TO", "USES"],
        max_depth=2
    )
```

### 2. Query Optimization
- **Use natural language**: "how to fix memory leaks" not "memory leak fix"
- **Include context**: Add technology and domain terms
- **Be specific**: "Python async memory leak" not just "memory leak"
- **Try variations**: Different phrasings may yield different results

### 3. Filter Usage
Use filters to narrow results:
- `memory_types`: Filter by solution, pattern, problem, etc.
- `tags`: Filter by specific tags
- `min_importance`: Exclude low-importance memories
- `min_confidence`: Exclude low-confidence memories

## Team Collaboration

### 1. Shared Database Rules
When using a shared database:
1. **Prefix personal tags**: `user:john/` for personal memories
2. **Review team memories**: Weekly review of team contributions
3. **Resolve conflicts**: Discuss and merge duplicate memories
4. **Maintain quality**: Peer review important memories

### 2. Team Tag Conventions
- `team-{name}`: Team-specific memories
- `project-{name}`: Project-specific memories
- `sprint-{number}`: Sprint-related memories
- `review-needed`: Needs team review
- `approved`: Team-approved memory

### 3. Collaboration Workflow
```
1. Individual creates memory
2. Adds `review-needed` tag
3. Team reviews weekly
4. If approved, add `approved` tag
5. If needs work, provide feedback
6. Archive or delete rejected memories
```

## Maintenance Schedule

### 1. Daily
- **Store new memories** as you work
- **Create relationships** between related memories
- **Boost confidence** for validated solutions

### 2. Weekly
- **Review low-confidence** memories (< 0.3)
- **Check for duplicates** and merge if found
- **Update outdated** information
- **Team review** of shared memories

### 3. Monthly
- **Apply confidence decay**: `apply_memento_confidence_decay()`
- **Export backup**: `export_mementos()`
- **Database maintenance**: `memento --maintenance`
- **Review tags**: Clean up unused or inconsistent tags

### 4. Quarterly
- **Comprehensive review**: All memories below 0.5 confidence
- **Archive obsolete**: Memories not used in 6+ months
- **Update patterns**: Refresh established patterns
- **Team retrospective**: Review what's working/not working

### 5. Yearly
- **Major cleanup**: Archive memories older than 2 years
- **Schema review**: Check if database schema needs updates
- **Process review**: Update rules and conventions
- **Training**: Refresh team on best practices

## Template Examples

### Solution Template
```markdown
# Problem
[Brief description of the problem]

# Context
- **Technology**: [Python, React, etc.]
- **Environment**: [Production, Development, Testing]
- **Symptoms**: [Error messages, performance issues]
- **Impact**: [Users affected, business impact]

# Solution
[Detailed explanation of the solution]

# Implementation
```language
[Code or configuration example]
```

# Verification
- **Tested**: [Yes/No]
- **Production**: [Yes/No]
- **Duration**: [How long it's been running]

# Alternatives Considered
1. [Alternative 1] - [Why rejected]
2. [Alternative 2] - [Why rejected]

# Notes
[Additional context, lessons learned, references]
```

### Pattern Template
```markdown
# Pattern Name
[Descriptive name]

# Intent
[What problem this pattern solves]

# Context
- **When to use**: [Appropriate situations]
- **When not to use**: [Inappropriate situations]
- **Related patterns**: [Other patterns to consider]

# Structure
[Diagram or description of structure]

# Implementation
```language
[Example implementation]
```

# Consequences
**Benefits:**
- [Benefit 1]
- [Benefit 2]

**Drawbacks:**
- [Drawback 1]
- [Drawback 2]

# Known Uses
- [Project/Component 1]
- [Project/Component 2]

# See Also
- [Related documentation]
- [Reference implementations]
```

### Decision Record Template
```markdown
# Decision Record: [Decision Title]

## Status
[Proposed | Accepted | Deprecated | Superseded]

## Context
[What led to this decision? What problem are we solving?]

## Decision
[What are we deciding to do?]

## Rationale
[Why did we make this decision?]

## Alternatives Considered
1. [Alternative 1] - [Pros/Cons]
2. [Alternative 2] - [Pros/Cons]

## Implications
- **Technical**: [Technical implications]
- **Team**: [Team implications]
- **Timeline**: [Timeline implications]

## Related Decisions
- [Decision 1]
- [Decision 2]

## Notes
[Additional context, references, follow-up actions]
```

## Compliance and Security

### 1. Sensitive Information
**NEVER store:**
- Passwords or secrets
- API keys or tokens
- Personal identifiable information
- Proprietary business logic
- Security vulnerability details

### 2. Compliance Tags
Use these tags for compliance:
- `pii`: Contains personally identifiable information
- `confidential`: Company confidential information
- `ndaprotected`: Protected by NDA
- `exportcontrolled`: Export-controlled information

### 3. Access Control
- **Personal database**: Store in user home directory
- **Team database**: Use appropriate file permissions
- **Backup encryption**: Encrypt backups containing sensitive info
- **Access logs**: Consider logging access to sensitive memories

## Troubleshooting Common Issues

### 1. Memory Not Found
**Problem**: Can't find a memory you know exists
**Solutions**:
- Try different search terms
- Use `recall_mementos()` for fuzzy matching
- Check if memory has appropriate tags
- Verify memory wasn't deleted or archived

### 2. Slow Performance
**Problem**: Searches or operations are slow
**Solutions**:
- Run `memento --maintenance`
- Archive old, low-confidence memories
- Check database file size
- Ensure adequate disk space

### 3. Duplicate Memories
**Problem**: Multiple memories with similar content
**Solutions**:
- Merge duplicates using `update_memento()`
- Add relationships between similar memories
- Establish clearer creation guidelines
- Regular duplicate detection and cleanup

### 4. Low Search Relevance
**Problem**: Search results aren't relevant
**Solutions**:
- Improve memory titles and content
- Use consistent tagging
- Set appropriate importance scores
- Create meaningful relationships

---

*Last updated: [Date]*
*Version: 1.0*