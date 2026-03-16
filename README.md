# MCP Context Keeper

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-blueviolet)](https://spec.modelcontextprotocol.io/)

**Intelligent persistent memory management for MCP clients** with automatic confidence tracking, relationship mapping, and knowledge quality maintenance.

Context Keeper is an MCP server that provides persistent memory capabilities to AI assistants in your IDE (Zed, VSCode, Cursor, Windsurf) or CLI agents (Gemini CLI, Claude, etc.). It helps you build a personal knowledge base that grows smarter over time.

## 🚀 Quick Start

### 1. Installation

```bash
# Install with pipx (recommended for MCP servers)
pipx install mcp-context-keeper

# Or with pip
pip install mcp-context-keeper
```

### 2. Configure Your IDE

**Zed Editor** (`~/.config/zed/settings.json`):
```json
{
  "mcpServers": {
    "context_keeper": {
      "command": "context_keeper",
      "args": ["--profile", "extended"],
      "env": {
        "CONTEXT_SQLITE_PATH": "~/.mcp-context-keeper/context.db"
      }
    }
  }
}
```

**Cursor / Windsurf** (`~/.cursor/mcp.json` or `~/.windsurf/mcp.json`):
```json
{
  "mcpServers": {
    "context-keeper": {
      "command": "context_keeper",
      "args": ["--profile", "extended"]
    }
  }
}
```

### 3. Start Using It

Once configured, your AI assistant can now:

```python
# Store solutions and knowledge
store_persistent_memory(
    type="solution",
    title="Fixed Redis timeout with connection pooling",
    content="Increased connection timeout to 30s and added connection pooling...",
    tags=["redis", "timeout", "production_fix"],
    importance=0.8
)

# Find knowledge later
recall_persistent_memories(query="Redis timeout solutions")

# Connect related concepts
create_persistent_relationship(
    from_memory_id="redis-fix-123",
    to_memory_id="database-optimization-456",
    relationship_type="RELATED_TO"
)
```

## ✨ Key Features

### 🧠 Intelligent Confidence System
- **Automatic decay**: Unused knowledge loses confidence over time (5% monthly)
- **Critical protection**: Security/auth/API key memories never decay
- **Boost on validation**: Confidence increases when knowledge is successfully used
- **Smart ordering**: Search results ranked by `confidence × importance`

### 🔗 Relationship Mapping
- **35+ relationship types**: SOLVES, CAUSES, IMPROVES, USED_IN, etc.
- **Graph navigation**: Find connections between concepts
- **Pattern detection**: Identify recurring solution patterns
- **Knowledge clusters**: Discover topic groups and related concepts

### 📊 Three Profile System
| Profile | Tools | Best For |
|---------|-------|----------|
| **Core** | 13 tools | All users - Essential operations + confidence basics |
| **Extended** | 17 tools | Power users - Analytics + contextual search |
| **Advanced** | 25 tools | Administrators - Graph analysis + advanced configuration |

### 🗃️ Persistent Storage
- **SQLite backend**: Zero dependencies, local storage
- **Full-text search**: Fast, fuzzy matching across all memories
- **Automatic maintenance**: Confidence decay, relationship integrity
- **Export/import**: JSON export for backup and migration

## 📖 What Can I Do With It?

### For Developers
- **Remember solutions**: Store fixes for recurring bugs
- **Track decisions**: Document architecture choices and trade-offs
- **Build knowledge base**: Create personal documentation that improves over time
- **Connect concepts**: See relationships between different technologies

### For Teams
- **Share knowledge**: Build team memory that survives member changes
- **Onboard faster**: New members can search past solutions
- **Reduce repetition**: Stop solving the same problems multiple times
- **Pattern recognition**: Identify recurring issues across projects

### For AI Assistants
- **Context persistence**: Remember conversations and decisions across sessions
- **Intelligent recall**: Find relevant knowledge based on confidence and importance
- **Relationship awareness**: Understand how concepts connect
- **Quality maintenance**: Automatically deprecate outdated information

## 🛠️ Usage Examples

### Store and Connect Knowledge
```python
# Store a bug fix
bug_fix_id = store_persistent_memory(
    type="solution",
    title="Fixed memory leak in WebSocket handler",
    content="Added proper cleanup in on_close() and reduced buffer size...",
    tags=["websocket", "memory", "python", "fix"],
    importance=0.9
)

# Store related pattern
pattern_id = store_persistent_memory(
    type="pattern",
    title="WebSocket connection management pattern",
    content="Always implement heartbeat and cleanup in finally block...",
    tags=["websocket", "pattern", "best-practice"],
    importance=0.7
)

# Connect them
create_persistent_relationship(
    from_memory_id=bug_fix_id,
    to_memory_id=pattern_id,
    relationship_type="EXEMPLIFIES"
)
```

### Find Obsolete Knowledge
```python
# Find low-confidence memories (potentially outdated)
low_confidence = get_persistent_low_confidence_memories(threshold=0.3)

for memory in low_confidence:
    print(f"Review: {memory['title']} (confidence: {memory['confidence']:.2f})")
    # Optionally boost or delete
```

### Natural Language Search
```python
# Find relevant knowledge using natural language
results = recall_persistent_memories(
    query="how to handle database connection timeouts",
    limit=5
)

for result in results:
    print(f"📚 {result['title']}")
    print(f"   Confidence: {result['confidence']:.2f}")
    print(f"   Relevance: {result['relevance']:.2f}")
```

## ⚙️ Configuration

### Environment Variables
```bash
# Database location
export CONTEXT_SQLITE_PATH="~/.mcp-context-keeper/context.db"

# Tool profile (core, extended, advanced)
export CONTEXT_TOOL_PROFILE="extended"

# Enable advanced tools
export CONTEXT_ENABLE_ADVANCED_TOOLS="true"

# Logging level
export CONTEXT_LOG_LEVEL="INFO"
```

### YAML Configuration File (`context-keeper.yaml`)
```yaml
backend: sqlite
sqlite_path: ~/.mcp-context-keeper/context.db
tool_profile: extended
enable_advanced_tools: false

logging:
  level: INFO
  format: "[{asctime}] {levelname}: {message}"

features:
  allow_relationship_cycles: false
```

## 🔄 Execution Modes

### As an MCP Server (Recommended)
```bash
# Default profile (core)
context_keeper

# Extended profile
context_keeper --profile extended

# Custom database location
context_keeper --sqlite-path ~/my-context.db

# Debug mode
context_keeper --log-level DEBUG
```

### With Command-Line Options
```bash
# Show help
context_keeper --help

# Health check
context_keeper --health

# List all tools
context_keeper --list-tools

# Export memories to JSON
context_keeper --export ~/backup.json

# Import from JSON
context_keeper --import ~/backup.json
```

### Available Entry Points
After installation, you have multiple ways to run Context Keeper:

| Command | Description |
|---------|-------------|
| `context_keeper` | Main executable (created by pip) |
| `python -m context_keeper` | Run as Python module |
| `python -m context_keeper.server` | Direct server access |
| `python run_mcp_context_keeper.py` | Development script |

## 📚 Documentation

### Essential Guides
- **[Tools Reference](docs/TOOLS.md)** - Complete guide to all 25 MCP tools
- **[Confidence System](docs/DECAY_SYSTEM.md)** - How confidence tracking works
- **[Python API Usage](docs/PYTHON_API.md)** - Using Context Keeper as a Python library
- **[Usage Rules](docs/RULES.md)** - Best practices and templates

### Advanced Topics
- **[Database Schema](docs/dev/SCHEMA.md)** - Technical database structure
- **[Development Guide](docs/dev/DEV.md)** - Contributing and development setup
- **[Integration Examples](docs/INTEGRATION.md)** - Detailed setup for different IDEs

## 🏗️ Architecture

### Database Schema
Context Keeper uses SQLite with three main tables:
- `memories`: Core memory storage with full-text search
- `relationships`: Directed graph of memory connections
- `confidence_scores`: Time-decaying confidence values

### Confidence System
The confidence system automatically:
1. **Tracks usage**: Each memory access boosts confidence
2. **Applies decay**: Unused memories lose 5% confidence monthly
3. **Protects critical**: Security/auth memories never decay
4. **Optimizes search**: Results ordered by `confidence × importance`

## 🔗 Integration Examples

### Zed Editor
Add to `~/.config/zed/settings.json`:
```json
{
  "context_servers": {
    "context_keeper": {
      "command": "context_keeper",
      "args": ["--profile", "extended"],
      "env": {
        "CONTEXT_SQLITE_PATH": "~/.mcp-context-keeper/context.db",
        "CONTEXT_TOOL_PROFILE": "extended"
      }
    }
  }
}
```

### Custom Script with Python API
```python
# See docs/PYTHON_API.md for complete examples
from context_keeper import ContextKeeper
import asyncio

async def analyze_knowledge():
    server = ContextKeeper()
    await server.initialize()
    
    stats = await server.get_statistics()
    print(f"Total memories: {stats['memory_count']}")
    print(f"Total relationships: {stats['relationship_count']}")
```

## 📈 Best Practices

### Memory Creation
- **Be specific**: Use descriptive titles and clear content
- **Tag consistently**: Use lowercase tags without spaces (e.g., `redis`, `web-socket`)
- **Set importance**: Use 0.9+ for critical solutions, 0.5-0.7 for general knowledge
- **Add relationships**: Connect related memories immediately

### Confidence Management
- **Review quarterly**: Check low-confidence memories every 3 months
- **Boost validated**: Increase confidence when solutions are confirmed
- **Archive obsolete**: Delete or deprecate outdated information
- **Protect critical**: Tag security/auth memories with `no_decay`

### Search Optimization
- **Start with recall**: Use `recall_persistent_memories()` for natural language
- **Use tags for acronyms**: Tag `jwt`, `api`, `oauth2` for reliable retrieval
- **Filter by type**: Search `solution` or `pattern` when looking for specific formats
- **Leverage relationships**: Use `get_related_persistent_memories()` to explore connections

## 🚨 Troubleshooting

### Common Issues

**Server won't start:**
```bash
# Check installation
which context_keeper

# Test basic functionality
context_keeper --health

# Check permissions on database file
ls -la ~/.mcp-context-keeper/
```

**No tools available in IDE:**
- Verify MCP configuration is correct
- Restart your IDE after configuration changes
- Check IDE logs for MCP server errors
- Test with `context_keeper --list-tools` to verify installation

**Slow searches:**
- Database might need vacuuming: `context_keeper --maintenance`
- Consider archiving old, low-confidence memories
- Check disk space on database location

### Debug Mode
```bash
# Enable verbose logging
CONTEXT_LOG_LEVEL=DEBUG context_keeper

# Or use command line
context_keeper --log-level DEBUG --profile core
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test categories
pytest tests/test_memory_operations.py
pytest tests/test_confidence_system.py
pytest tests/test_relationships.py

# With coverage
pytest --cov=src tests/
```

## 📦 Development

### Setup
```bash
# Clone repository
git clone https://github.com/your-username/mcp-context-keeper.git
cd mcp-context-keeper

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

### Project Structure
```
mcp-context-keeper/
├── src/                          # Source code
│   └── context_keeper/          # Main package
├── docs/                        # Documentation
├── tests/                       # Test suite
├── pyproject.toml              # Package configuration
├── MANIFEST.in                 # Additional files for distribution
├── CONTRIBUTING.md             # Contribution guidelines
├── LICENSE                     # MIT License
└── README.md                   # This file
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on:
- Development setup and workflow
- Code style and conventions
- Testing requirements
- Documentation standards
- Pull request process

### Development Guidelines
- Follow existing code style and conventions
- Add tests for new functionality
- Update documentation for API changes
- Use type hints and docstrings
- Keep the confidence system backward compatible

For complete development documentation, see:
- **[Development Guide](docs/dev/DEV.md)** - Technical development setup
- **[Database Schema](docs/dev/SCHEMA.md)** - Database structure and design

## 🔗 Links

- **[GitHub Repository](https://github.com/your-username/mcp-context-keeper)** - Source code and issues
- **[MCP Protocol](https://spec.modelcontextprotocol.io/)** - Model Context Protocol specification
- **[PyPI Package](https://pypi.org/project/mcp-context-keeper/)** - Python Package Index
- **[Discussions](https://github.com/your-username/mcp-context-keeper/discussions)** - Community forum

---

**Need help?** Check the [documentation](docs/) or open an [issue](https://github.com/your-username/mcp-context-keeper/issues) on GitHub.