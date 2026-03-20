# Usage Rules and Best Practices

This document outlines the rules, conventions, and best practices for using Memento effectively. For ready-to-use configuration snippets for AI agents, see [AGENT_CONFIGURATION.md](./AGENT_CONFIGURATION.md).

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

### 4. Memory Types Guide
Choosing the right memory type improves search filtering and organization. The complete list of supported types is:

| Type | Use For | Example |
|------|---------|---------|
| **`solution`** | Working fixes, architectural implementations | "Fixed N+1 query with eager loading" |
| **`problem`** | Issues encountered that need tracking | "Database deadlock under high concurrency" |
| **`code_pattern`** | Reusable templates or patterns | "Repository pattern for database access" |
| **`task`** | Completed milestones or session summaries | "Implemented user authentication" |
| **`technology`** | Framework knowledge, configs | "FastAPI dependency injection best practices" |
| **`error`** | Specific error strings | "ImportError: module not found" |
| **`fix`** | Direct resolutions to specific errors | "Added missing import statement for models" |
| **`workflow`** | Multi-step processes, procedures | "CI/CD pipeline deployment steps" |
| **`general`** | Architecture choices, decisions, miscellaneous | "Chose PostgreSQL over MongoDB for transactions" |
| **`project`** | Project-level context and metadata | "Project X uses a monorepo structure" |
| **`command`** | CLI commands, shell scripts, one-liners | "Command to reset local dev database" |
| **`file_context`** | Key files, their purpose and structure | "auth/middleware.py handles JWT validation" |
| **`conversation`** | Session summaries, AI interaction notes | "Summary of onboarding session 2024-01-15" |

> **Note**: The type `decision` is not a standalone enum value — use `type="general"` with a `decision` tag instead (e.g., `tags=["decision", "architecture"]`). This is the recommended convention throughout the codebase.

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

*Note: While tags are technically optional in the API, they are strongly recommended for effective search and organization. Memories without tags may be difficult to find later.*

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
Memento supports 35 relationship types organized into 7 semantic categories. For a complete reference with all relationship types, examples, and usage guidelines, see [RELATIONSHIPS.md](./RELATIONSHIPS.md).

**Always use the most specific relationship type available.** Here are the most commonly used types:

| Type | Category | When to Use | Example |
|------|----------|-------------|---------|
| **`SOLVES`** | Solution | Solution completely fixes a problem | Fix `SOLVES` bug |
| **`CAUSES`** | Causal | A directly causes B | Error `CAUSES` crash |
| **`APPLIES_TO`** | Context | Pattern applies to specific context | Pattern `APPLIES_TO` project |
| **`IMPROVES`** | Solution | Improved version of something | v2 `IMPROVES` v1 |
| **`DEPENDS_ON`** | Workflow | A requires B to function | Feature `DEPENDS_ON` API |
| **`RELATED_TO`** | Similarity | General connection (use when unsure) | Topic A `RELATED_TO` Topic B |
| **`BUILDS_ON`** | Learning | Advanced concept builds on basic | Advanced `BUILDS_ON` Basic |
| **`REQUIRES`** | Context | Component requires another | Module `REQUIRES` library |
| **`ALTERNATIVE_TO`** | Solution | Alternative approach (bidirectional) | Method A `ALTERNATIVE_TO` Method B |
| **`CONFIRMS`** | Learning | Evidence confirms hypothesis | Test `CONFIRMS` implementation |

For the complete list of all 35 relationship types with detailed examples, see the [complete relationship documentation](./RELATIONSHIPS.md).

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

> **📌 Note**: Code examples below are **MCP tool call pseudocode** — they illustrate
> which tools to invoke and with what arguments. They are not importable Python
> functions. See [PYTHON.md](integrations/PYTHON.md) for the MCP client pattern.

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

For team usage, the core rules above apply globally. Personal tagging prefixes, shared database workflows,
and review conventions should follow your team's agreed standards. For a complete reference of team-specific
tagging conventions, collaboration workflows, and ready-to-use configuration snippets, see
[AGENT_CONFIGURATION.md](./AGENT_CONFIGURATION.md#advanced-team-collaboration).

## Example Workflows

Integrating Memento into your daily development cycle is key. If you don't prompt the AI or configure rules, nothing gets stored. Here are some workflow habits to build:

### 1. The Debugging Lifecycle
When you encounter a stubborn issue:
1. **Identify the Issue:** You hit an error. Tell the AI to store it (Type: `error`).
2. **Find the Root Cause:** You trace the bug. Have the AI store the root cause (Type: `problem`) and link it (`error` CAUSES `problem`).
3. **Implement the Fix:** You write the patch. Tell the AI to save the implementation (Type: `solution`) and link it (`solution` SOLVES `problem`).
4. *Result:* You now have a complete, traceable chain of how an error maps to a root cause and its solution.

### 2. Feature Development
When building something new:
1. **Context Gathering:** Start your session by asking the AI, *"Recall any patterns we use for user authentication."*
2. **Implementation:** Write the code with the AI's help, leveraging the retrieved context.
3. **Knowledge Capture:** Once the feature works, tell the AI, *"Store this new JWT authentication approach"* (Type: `code_pattern`).
4. **Link to Context:** Instruct the AI to link the pattern to the current project (`pattern` APPLIES_TO `project`).

### 3. Optimization & Architecture
When making high-level choices:
1. **Identify the Bottleneck:** Store the performance issue or limitation (Type: `problem`).
2. **Explore Options:** Test a few approaches and store the viable ones (Type: `solution`).
3. **Compare & Decide:** Link the chosen approach as an improvement (`best_solution` IMPROVES `old_solution`).
4. **Document the Rationale:** Save the final architecture choice so future developers understand the *why* behind your choices.

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
- **Export backup**: `memento export --format json --output memento-backup.json`
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
````markdown
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
````

### Pattern Template
````markdown
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
````

### Decision Record Template
````markdown
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
````

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

> **⚠️ Note**: Memento uses a plain SQLite file with no built-in authentication, roles, or ACL.
> Access control is entirely at the OS filesystem level.

- **Personal database**: Store in user home directory (`~/.mcp-memento/context.db`)
- **Team database**: Use OS filesystem permissions on the shared `.db` file
- **Backup encryption**: Encrypt backup files that may contain sensitive content
- **Access logs**: SQLite does not log access — use OS-level auditing if required

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
- Run `apply_memento_confidence_decay` to clean up low-confidence relationships (Extended profile or above)
- Delete obsolete memories identified by `get_low_confidence_mementos`
- Check database file size with `memento --health`
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
