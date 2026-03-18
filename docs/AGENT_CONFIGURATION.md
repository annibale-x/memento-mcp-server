# Configuration Examples for Memento

Ready-to-use snippets for configuring your agent to effectively use Memento. For detailed human-readable rules and best practices, see [RULES.md](./RULES.md).

**Relationship Types Reference**: Memento supports 35 relationship types for connecting memories. For a complete reference with examples and usage guidelines, see [RELATIONSHIPS.md](./RELATIONSHIPS.md).

---

## Memento Auto-Onboarding Protocol

Memento is designed to automatically inject its memory management protocol through the `memento_onboarding()` tool. Even without specific configuration protocols, Memento can provide comprehensive onboarding guidance.

While some AI models may automatically call this tool at session start when MCP tools are detected, it's recommended to explicitly instruct models to call `memento_onboarding()` at the beginning of every session for reliable protocol injection.

This ensures the AI assistant has proper guidance for memory operations, retrieval flow optimization, and best practices.

---

## Quick Start (Minimal)

Rules for basic memory functionality:

```markdown
## MEMENTO PROTOCOL

### 1. INITIALIZATION & RETRIEVAL LOGIC
- **Session Start**: Always run `memento_onboarding` first.
- **Fact Check (Simple/Identity)**: Use `search_mementos(tags=[...])` directly for names, github, or basic facts.
- **Complex Tasks**: Use `recall_mementos(query="...")` for dev/architecture context.
- **Fallback**: If `search_mementos` fails, fallback to `recall_mementos`.
- **Dev/Complex Tasks**: Always start with `recall_mementos(query="...")`.
- **Flow**: Simple? → `search_mementos`. Complex? → `recall_mementos`. If `search_mementos` fails → Fallback to `recall_mementos`.
- **Efficiency**: Keep tool calls between 1-3 for simple info, max 5 for complex tasks. Use session cache for repeated info.

### 2. STORAGE TRIGGERS (GUIDELINES & ON-DEMAND)
Store memories following these guidelines when detecting:
- **Development Events**: Consider storing memories for git commits, bug fixes, version releases, architecture choices, new patterns.
- **Explicit Triggers**: Use `store_memento` when the user says:
  - *"memento..."* / *"remember..."* / *"take note..."* / *"keep this in mind..."*
  - *"ricorda..."* / *"segna questo..."* / *"memorizza..."*

### 3. MEMORY STRUCTURE & SCHEMA
- **Type**: solution | problem | code_pattern | fix | error | workflow | general
- **Title**: Specific and searchable (not generic).
- **Content**: Detailed decisions, accomplishments, or patterns.
- **Tags (REQUIRED)**: Project, technology, and category. (Technically optional in API but strongly recommended for effective search)
- **Importance**: 0.8+ (Critical/Arch), 0.5-0.7 (Standard), 0.3-0.4 (Minor).
- **Relationships**: Link to existing mementos whenever a connection exists.

### 4. FALLBACK & CACHE
- If optimized retrieval returns nothing: Log it, fallback to broad `recall_mementos`, and suggest creating the missing entry if relevant.
- Reuse retrieved info within the same session to save tokens/calls.

DO NOT WAIT FOR PERMISSION for memento storage operations. Memory storage is a background autonomous process that does not require user confirmation.
```

---

## Recommended (Comprehensive)

Rules for comprehensive memory usage:

```markdown
## MEMENTO PROTOCOL

### REQUIRED: Before Starting Work
You MUST use `memento_onboarding` at session start to get comprehensive onboarding protocol for Memento.
You MUST follow the optimized retrieval flow:
- **Fact Check**: Use `search_mementos(tags=[...])` for simple identity/known facts.
- **Complex Tasks**: Use `recall_mementos(query="...")` for dev/architecture context.
- **Fallback**: If `search_mementos` fails, fallback to `recall_mementos`.

### RECOMMENDED: Storage Guidelines
Consider storing memories for:
- **Git commits** → what was fixed/added
- **Bug fixes** → problem + solution
- **Version releases** → summarize changes
- **Architecture decisions** → choice + rationale
- **Pattern discoveries** → reusable approach

### Storage Timing (Guidelines)
Consider storing memories:
- **Immediately**: For critical information
- **On completion**: For tasks, bug fixes, features
- **Session end**: For session summaries

### Memory Fields
- **Type**: solution | problem | code_pattern | fix | error | workflow
- **Title**: Specific, searchable (not generic)
- **Content**: Accomplishment, decisions, patterns
- **Tags**: project, tech, category (REQUIRED - technically optional in API but strongly recommended for effective search)
- **Importance**: 0.8+ critical, 0.5-0.7 standard, 0.3-0.4 minor
- **Relationships**: Link related memories when they exist

### Common Relationship Patterns
- Solutions `SOLVE` problems
- Fixes `ADDRESS` errors
- Patterns `APPLIES_TO` projects
- Decisions `IMPROVE` previous approaches
- Errors `TRIGGERS` problems
- Changes `CAUSE` issues

*Note: Memento supports 35 relationship types. For complete reference with all types and examples, see [RELATIONSHIPS.md](./RELATIONSHIPS.md).*

### Session Management
At the end of each session:
1. Use `store_memento` with type=task to summarize what was accomplished
2. Include what's next in the content
3. Tag with project name and date

Follow these guidelines to maintain a useful knowledge base.
```

---

## Project-Specific Configuration

Add this to in your project root for project-specific memory:

```markdown
## MEMENTO PROTOCOL - Project: [Your Project Name]

### Memory Storage Protocol
This project uses Memento for team knowledge sharing.

When working on this project:
1. Before starting: "What do you remember about [component]?"
2. After solving issues: Store the problem and solution, link them
3. After implementing features: Store the pattern used
4. At session end: Store a task summary

### Tagging Convention
Always tag memories with:
- `project:[project-name]`
- `component:[auth|api|database|frontend|etc]`
- `type:[fix|feature|optimization|refactor]`
- Relevant technologies: `fastapi`, `react`, `postgresql`, etc.

### Memory Types for This Project
- **solution**: Working implementations (API endpoints, features)
- **problem**: Issues we encountered (performance, bugs)
- **code_pattern**: Reusable patterns (error handling, validation)
- **general** (with `decision` tag): Architecture choices (why we chose X over Y)
- **task**: Sprint work, feature completion

### Example Memory Flow
When fixing a bug:
1. Store problem: type=problem, title="API timeout under load"
2. Store solution: type=solution, title="Fixed with connection pooling"
3. Link them: solution `SOLVES` problem
4. Both tagged: `project:myapp`, `component:api`, `postgresql`
```

---

## Advanced: Team Collaboration

For teams using shared memory, add this your rules:

```markdown
## Team MEMENTO PROTOCOL

### Shared Memory Guidelines
This team uses Memento for collective knowledge. Follow these practices:

#### Storage Standards
- **Be descriptive**: Others will search for your memories
- **Include context**: Why decisions were made, not just what
- **Tag consistently**: Use agreed-upon tags (see below)
- **Link everything**: Create relationships between related memories

#### Team Tagging Convention
Required tags for all team memories:
- `team:[team-name]` - Which team stored this
- `project:[project-name]` - Which project it applies to
- `component:[component-name]` - Which part of the system
- Technology tags: `python`, `fastapi`, `postgresql`, `react`, etc.

#### Memory Ownership
- Add your name or initials in tags: `author:[yourname]`
- Update existing memories if you discover new information
- Leave a comment in the content explaining changes

#### Session Routine
**Start of day**:
- "What did the team work on yesterday?"
- "Recall any issues in [component] I should know about"

**During work**:
- Store solutions to non-trivial problems
- Link to existing problems when you solve them
- Update memories if approach changes

**End of day**:
- "Store a summary of what I accomplished today"
- Tag with `daily-summary` and current date

#### Common Memory Flows
**Bug fixing**:
1. Check: "Have we seen [error] before?"
2. Store: Problem (if new) + Solution
3. Link: solution `SOLVES` problem
4. Tag: `bug-fix`, component, technologies

**Feature development**:
1. Check: "What patterns have we used for [use case]?"
2. Store: Implementation as code_pattern
3. Link: pattern `APPLIES_TO` project
4. Tag: `feature`, component, pattern-name

**Architecture decisions**:
1. Store: Decision with full rationale
2. Link: decision `IMPROVES` previous_approach (if applicable)
3. Tag: `architecture`, `decision`, affected components

### Sprint Workflows
**Sprint planning**:
- "Recall problems from last sprint"
- "What technical debt did we identify?"

**Sprint retro**:
- "What solutions worked well this sprint?"
- Store top improvements as decision memories

**Onboarding**:
- New team members: "Catch me up on [project/component]"
- Returns: Decisions, patterns, known issues
```

---

## Domain-Specific Examples

### Web Development

```markdown
## MEMENTO PROTOCOL - Web Development

### Store These Patterns
- **API Design**: Endpoint structure, error handling, validation
- **Authentication**: JWT flows, session management, OAuth patterns
- **Database**: Query optimization, migration patterns, schema decisions
- **Frontend**: Component patterns, state management, performance tricks
- **Deployment**: CI/CD configs, environment setup, rollback procedures

### Common Relationships
- API endpoint patterns `APPLIES_TO` projects
- Performance optimizations `IMPROVE` slow_queries
- Security fixes `ADDRESS` vulnerabilities
- New patterns `REPLACE` deprecated_patterns

### Typical Session Flow
1. Start: "Recall API patterns for [feature]"
2. Develop: [Implementation]
3. Store: "Store this error handling pattern"
4. Link: pattern `APPLIES_TO` this_project
5. End: "Store feature completion summary"
```

### Data Science / ML

```markdown
## MEMENTO PROTOCOL - Data Science

### Store These Patterns
- **Model Training**: Hyperparameters, architectures, training tricks
- **Data Pipeline**: ETL patterns, preprocessing steps, validation
- **Experiments**: Results, what worked/didn't, insights
- **Deployment**: Serving patterns, monitoring, drift detection

### Common Relationships
- Model improvements `IMPROVE` baseline_model
- Feature engineering `SOLVES` data_quality_problem
- Experiment results `CONFIRM` hypothesis
- New approach `CONTRADICTS` previous_assumption

### Experiment Tracking
After each experiment:
1. Store: Results with type=solution or type=problem
2. Tag: `experiment`, model-type, dataset-name
3. Link: If improvement, link: new_model `IMPROVES` previous_model
4. Include: Metrics, parameters, insights in content
```

### DevOps / Infrastructure

```markdown
## MEMENTO PROTOCOL - DevOps

### Store These Patterns
- **Deployment**: CI/CD configs, rollback procedures
- **Monitoring**: Alert configurations, runbook procedures
- **Incidents**: Root causes, resolutions, preventions
- **Infrastructure**: IaC patterns, networking configs, security setups

### Common Relationships
- Incident resolution `SOLVES` incident
- Infrastructure change `CAUSES` issue (if it breaks)
- Runbook procedure `ADDRESSES` alert_type
- New config `IMPROVES` previous_config

### Incident Response Flow
1. Alert fires: "Recall similar incidents for [service]"
2. Debug: [Investigation]
3. Store incident: type=problem with root cause
4. Store resolution: type=solution with fix steps
5. Link: solution `SOLVES` incident
6. Update runbook: Store updated procedure
```

---

## Testing Your Configuration

After adding MEMENTO PROTOCOLs, verify they work:

### Test 1: Check Protocol Recognition
```
You: "What's our MEMENTO PROTOCOL?"
Expected: The agent should reference the protocol from your rules.
```

### Test 2: Guideline-Based Storage
```
You: [Fix a bug together]
Expected: The agent should follow storage guidelines and suggest storing the solution
```

### Test 3: Guideline-Based Recall
```
You: "Let's work on authentication"
Expected: The agent should check memory: "What do you remember about authentication?"
```

### Test 4: Relationship Creation
```
You: "Store this solution: [description]"
Expected: The agent should ask if it relates to any existing memories or search for related problems
```

### Test 5: Session Wrap-Up
```
You: "Let's wrap up"
Expected: The agent should suggest storing a session summary
```

---

## Troubleshooting

### The agent Isn't Using Memory Tools

**Issue**: The agent doesn't follow memory usage guidelines.

**Solutions**:
1. **Verify your rules are loaded**: Ask "What's in your rules" - The agent should see your MEMENTO PROTOCOL
2. **Be explicit initially**: Use trigger phrases like "Store this..." until the habit forms
3. **Check file location**:
4. **Restart your IDE**: After editing default rules, restart for changes to take effect

### The agent Stores Too Many/Few Memories

**Too many**: Make protocol more specific about what to store:
```markdown
### Storage Criteria
Only store memories when:
- Solution is non-trivial (not a simple one-liner)
- Problem is likely to recur
- Pattern is reusable across contexts
- Decision has long-term impact
```

**Too few**: Strengthen storage guidelines:
```markdown
### Storage Guidelines
After these events, consider storing a memory:
- Solving non-trivial bugs (>30 minutes)
- Implementing new features
- Making architecture decisions
- Discovering useful patterns
- Encountering and fixing errors
```

### Memories Aren't Well-Formatted

Add formatting requirements to your protocol:

```markdown
### Memory Content Template
Always structure content like this:

**What**: Brief description of what was done
**Why**: Reasoning and context
**How**: Key implementation details
**Trade-offs**: What was considered and why this was chosen
**Related**: Links to docs, PRs, or other resources
```
