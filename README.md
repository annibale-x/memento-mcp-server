# MCP Context Server

## Overview

MCP Context Server is a context-aware memory management system for MCP (Model Context Protocol) clients like Zed Editor. It provides intelligent memory storage, retrieval, and relationship management with contextual awareness for development workflows.

## Features

- **Context-Aware Memory**: Store memories with project, file, language, and framework context
- **Graph Relationships**: 35+ relationship types for connecting related memories
- **Fuzzy Search**: Natural language querying with stemming and fuzzy matching
- **SQLite Backend**: Simple, file-based storage with no external dependencies
- **MCP Protocol**: Full compatibility with MCP clients including Zed Editor
- **Bi-temporal Tracking**: Relationship validity with temporal metadata

## Quick Start

### Installation

```bash
# Install from local source
pip install -e .

# Or install directly
pip install mcp-context-server
```

### Basic Usage

```bash
# Start the server
python -m context_server

# Start with extended tool profile
python -m context_server --profile extended

# Show configuration
python -m context_server --show-config

# Health check
python -m context_server --health
```

### Configuration

Create `context-server.yaml` in your project root:

```yaml
# Backend configuration
backend: "sqlite"
sqlite_path: "~/.mcp-context-server/context.db"

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

## Relationship Types

The system supports 35+ relationship types including:

- **Causal**: `CAUSES`, `TRIGGERS`, `PREVENTS`
- **Solution**: `SOLVES`, `ADDRESSES`, `MITIGATES`
- **Context**: `RELATES_TO`, `DEPENDS_ON`, `USES`
- **Learning**: `EXPLAINS`, `CLARIFIES`, `SIMPLIFIES`
- **Temporal**: `PRECEDES`, `FOLLOWS`, `OCCURS_WITH`

## Development

### Project Structure

```
mcp-context-server/
├── context_server/          # Core package
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
black context_server/ test/

# Sort imports
isort context_server/ test/

# Type checking
mypy context_server/

# Linting
flake8 context_server/ test/
```

## Environment Variables

```bash
# Backend configuration
export CONTEXT_BACKEND=sqlite
export CONTEXT_SQLITE_PATH=~/.mcp-context-server/context.db

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
    "context-server": {
      "command": "python",
      "args": ["-m", "context_server"],
      "env": {
        "CONTEXT_SQLITE_PATH": "~/.mcp-context-server/context.db"
      }
    }
  }
}
```

## API Examples

### Storing a Memory

```python
from context_server import Memory, MemoryType

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
from context_server import Relationship, RelationshipType

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
set CONTEXT_LOG_LEVEL=DEBUG && python -m context_server

# Check Python version
python --version

# Check installed packages
pip list | grep mcp-context-server
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
- [GitHub Repository](https://github.com/yourusername/mcp-context-server)