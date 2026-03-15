# MCP Context Keeper (mcp-context-keeper)

## Overview

MCP Context Keeper is a context-aware memory management system for MCP (Model Context Protocol) clients like Zed Editor. It provides intelligent memory storage, retrieval, and relationship management with contextual awareness for development workflows.

## Features

- **Persistent Memory**: Long-term knowledge storage with `_persistent` suffix tools (distinct from session memory)
- **Context-Aware Memory**: Store memories with project, file, language, and framework context
- **Graph Relationships**: 35+ relationship types for connecting related memories
- **Fuzzy Search**: Natural language querying with stemming and fuzzy matching
- **SQLite Backend**: Simple, file-based storage with no external dependencies
- **MCP Protocol**: Full compatibility with MCP clients including Zed Editor
- **Bi-temporal Tracking**: Relationship validity with temporal metadata
- **Usage Guidance**: Built-in guide tool to distinguish persistent vs session memory usage

## Quick Start

### Installation

```bash
# Install from local source
pip install -e .

# Or install directly
pip install mcp-context-keeper
```

### Basic Usage

```bash
# Start the server
python -m context_keeper

# Start with extended tool profile
python -m context_keeper --profile extended

# Show configuration
python -m context_keeper --show-config

# Health check
python -m context_keeper --health
```

### Getting Help with Tool Usage

When using with other MCP context servers (like Serena Context Server), use the built-in guide tool to avoid confusion:

```bash
# Get comprehensive guidance on persistent vs session memory
python -m context_keeper --profile extended

# Then call from your MCP client:
{
  "tool": "help_memory_tools_usage",
  "topic": "distinction"
}
```

### Important: Persistent Memory Convention

All MCP tools in this server use the `_persistent` suffix to distinguish them from session memory tools (like those in Serena Context Server):

- **Persistent Memory Tools** (`_persistent` suffix): Long-term, cross-session, global knowledge
  - `store_persistent_memory`, `get_persistent_memory`, `search_persistent_memories`
  - Use for: solutions, patterns, architecture decisions, reusable code

- **Session Memory Tools** (no suffix): Temporary, project-specific, session-only context
  - `store_memory`, `get_memory`, `search_memories` (in Serena Context Server)
  - Use for: current file context, temporary variables, undo history

**Always use `help_memory_tools_usage` when unsure which tool to use!**

### Configuration

Create `context-keeper.yaml` in your project root:

```yaml
# Backend configuration
backend: "sqlite"
sqlite_path: "~/.mcp-context-keeper/context.db"

# Tool configuration
tool_profile: "extended"
enable_advanced_tools: true

# Logging configuration
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Feature configuration
features:
  auto_extract_entities: true
  session_briefing: true
  briefing_verbosity: "standard"
  briefing_recency_days: 7
  allow_relationship_cycles: false
```

## Memory Types

The server supports 13 memory types for different development scenarios:

| Type | Description | Use Case |
|------|-------------|----------|
| `task` | Development tasks | Project management |
| `code_pattern` | Code patterns and idioms | Best practices |
| `problem` | Problems and issues | Bug tracking |
| `solution` | Solutions to problems | Knowledge base |
| `project` | Project information | Project documentation |
| `technology` | Technologies and frameworks | Tech stack tracking |
| `error` | Error messages and stack traces | Debugging history |
| `fix` | Fixes and workarounds | Solution repository |
| `command` | Commands and scripts | Automation recipes |
| `file_context` | File-specific context | File understanding |
| `workflow` | Workflows and processes | Process documentation |
| `general` | General information | Miscellaneous notes |
| `conversation` | Conversation summaries | Meeting notes |

## Tool Profiles

The server supports three tool profiles:

### Core Profile (10 tools)
Essential tools including the guide tool for distinguishing persistent vs session memory:
- `help_memory_tools_usage` - Usage guidance and distinction help
- `store_persistent_memory` - Store long-term solutions
- `get_persistent_memory` - Retrieve cross-session knowledge
- `search_persistent_memories` - Search global patterns
- Plus 6 more core tools

### Extended Profile (13 tools)
Core tools + advanced search and statistics tools

### Advanced Profile (20 tools)
Extended tools + graph analysis and pattern detection tools

## Avoiding Tool Confusion

When using multiple MCP context servers, follow these rules:

1. **Check for `_persistent` suffix** for long-term storage
2. **Use the guide tool** when unsure: `help_memory_tools_usage`
3. **Session memory** (no suffix) is for temporary, project-specific context
4. **Persistent memory** (`_persistent` suffix) is for reusable, cross-session knowledge

Common mistakes to avoid:
- ❌ Using `store_memory` (Serena) for bug fix solutions
- ✅ Use `store_persistent_memory` instead
- ❌ Using `get_memory` (Serena) for cross-session patterns
- ✅ Use `get_persistent_memory` instead

## Relationship Types

The system supports 35+ relationship types including:

- **Causal**: `CAUSES`, `TRIGGERS`, `PREVENTS`
- **Solution**: `SOLVES`, `ADDRESSES`, `MITIGATES`
- **Context**: `RELATES_TO`, `DEPENDS_ON`, `USES`
- **Learning**: `EXPLAINS`, `CLARIFIES`, `SIMPLIFIES`
- **Temporal**: `PRECEDES`, `FOLLOWS`, `OCCURS_WITH`

## API Examples

### Using Persistent Memory (Correct)
```json
{
  "tool": "store_persistent_memory",
  "type": "solution",
  "title": "Fixed JWT authentication",
  "content": "Increased token expiration to 30 minutes...",
  "tags": ["jwt", "authentication", "security"],
  "importance": 0.8
}
```

### Getting Usage Guidance
```json
{
  "tool": "help_memory_tools_usage",
  "topic": "distinction"
}
```

### Searching Persistent Knowledge
```json
{
  "tool": "search_persistent_memories",
  "tags": ["redis", "database"],
  "memory_types": ["solution", "pattern"],
  "limit": 5
}
```

## Development

### Project Structure

```
mcp-context-keeper/
├── context_keeper/          # Core package
│   ├── backends/           # Database backends
│   ├── tools/              # MCP tool handlers
│   ├── utils/              # Utility functions
│   ├── models.py           # Data models
│   ├── server.py           # MCP server implementation
│   ├── sqlite_database.py  # SQLite operations
│   └── __init__.py
├── test/                   # Test suite
│   ├── test_data/         # Test data files
│   ├── test_relationships.py
│   ├── test_tools.py
│   └── run_tests.py
├── docs/                   # Documentation
├── pyproject.toml          # Project configuration
├── README.md              # This file
└── CHANGELOG.md           # Version history
```

### Running Tests

```bash
# Run all tests
cd test && python run_tests.py

# Run specific test files
cd test && python test_relationships.py
cd test && python test_tools.py

# Run with verbose output
cd test && python run_tests.py --verbose
```

### Code Quality

```bash
# Format code
black context_keeper/ test/

# Sort imports
isort context_keeper/ test/

# Type checking
mypy context_keeper/

# Linting
flake8 context_keeper/ test/
```

## Environment Variables

```bash
# Backend configuration
export CONTEXT_BACKEND=sqlite
export CONTEXT_SQLITE_PATH=~/.mcp-context-keeper/context.db

# Tool configuration
export CONTEXT_TOOL_PROFILE=extended
export CONTEXT_ENABLE_ADVANCED_TOOLS=true

# Logging
export CONTEXT_LOG_LEVEL=INFO

# Features
export CONTEXT_AUTO_EXTRACT_ENTITIES=true
export CONTEXT_SESSION_BRIEFING=true
export CONTEXT_BRIEFING_VERBOSITY=standard
export CONTEXT_BRIEFING_RECENCY_DAYS=7
export CONTEXT_ALLOW_CYCLES=false
```

## Integration with Zed Editor

Add to your Zed MCP configuration:

```json
{
  "mcpServers": {
    "context-keeper": {
      "command": "python",
      "args": ["-m", "context_keeper"],
      "env": {
        "CONTEXT_SQLITE_PATH": "~/.mcp-context-keeper/context.db"
      }
    }
  }
}
```

## API Examples

### Storing a Memory

```python
from context_keeper import Memory, MemoryType

memory = Memory(
    type=MemoryType.SOLUTION,
    title="Fix for database connection issue",
    content="Use connection pooling with max_connections=10",
    tags=["database", "performance", "fix"],
    context={
        "project": "my-project",
        "language": "python",
        "framework": "django"
    }
)
```

### Creating Relationships

```python
from context_keeper import Relationship, RelationshipType

relationship = Relationship(
    from_memory_id="problem_123",
    to_memory_id="solution_456",
    type=RelationshipType.SOLVES,
    properties={
        "effectiveness": 0.95,
        "implementation_time": "2 hours"
    }
)
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're in the test directory or add parent to sys.path
2. **JSON Serialization Errors**: Use `model_dump(mode='json')` for Pydantic models
3. **Database Connection Issues**: Check `CONTEXT_SQLITE_PATH` environment variable
4. **Test Failures on Windows**: Tests use ASCII indicators (`[PASS]`, `[FAIL]`) for compatibility

### Debugging

```bash
# Run with debug logging
set CONTEXT_LOG_LEVEL=DEBUG && python -m context_keeper

# Check Python version
python --version

# Check installed packages
pip list | grep mcp-context-keeper
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `cd test && python run_tests.py`
5. Submit a pull request

### Commit Message Convention

```
feat: Add new memory type 'conversation'
fix: Resolve JSON serialization error
docs: Update installation instructions
test: Add Windows compatibility tests
refactor: Simplify relationship validation
style: Format code with black
chore: Update dependencies
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built on the MCP (Model Context Protocol) specification
- Inspired by MemoryGraph for graph-based memory management
- Designed for seamless integration with Zed Editor

## Links

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Zed Editor](https://zed.dev/)
- [GitHub Repository](https://github.com/yourusername/mcp-context-keeper)