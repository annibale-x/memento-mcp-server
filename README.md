# MCP Memento

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-blueviolet)](https://spec.modelcontextprotocol.io/)

**Universal intelligent memory management for MCP clients** with automatic confidence tracking, relationship mapping, and knowledge quality maintenance across all platforms.

Memento is a universal MCP server that provides persistent memory capabilities across all major platforms:
- **IDEs**: Zed, Cursor, Windsurf, VSCode, Claude Desktop
- **CLI Agents**: Gemini CLI, Claude CLI, custom agents
- **Programmatic Usage**: Python API, REST API, custom integrations
- **Applications**: Any MCP-compatible application



Build a personal or team knowledge base that grows smarter over time, accessible from all your development tools.

## 🚀 Quick Start

### 1. Installation

```bash
# Install with pipx (recommended for MCP servers)
pipx install mcp-memento

# Or with pip
pip install mcp-memento
```

### 2. Choose Your Integration

**IDEs** (Zed, Cursor, Windsurf, VSCode, Claude Desktop):
```json
{
  "context_servers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "extended"],
      "env": {
        "MEMENTO_SQLITE_PATH": "~/.mcp-memento/context.db"
      }
    }
  }
}
```

**CLI Agents** (Gemini CLI, Claude CLI):
```bash
gemini --mcp-servers memento
# or
claude --mcp-servers memento
```

**Python API**:
```python
import memento
server = memento.Memento()
```

### 3. Start Using It

Once configured, your AI assistant can now:

```python
# Store solutions and knowledge
store_memento(
    type="solution",
    title="Fixed Redis timeout with connection pooling",
    content="Increased connection timeout to 30s and added connection pooling...",
    tags=["redis", "timeout", "production_fix"],
    importance=0.8
)

# Find knowledge later
recall_mementos(query="Redis timeout solutions")

# Connect related concepts
create_memento_relationship(
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

### 📊 Three Profile System
| Profile | Tools | Best For |
|---------|-------|----------|
| **Core** | 13 tools | All users - Essential operations |
| **Extended** | 17 tools | Power users - Analytics + contextual search |
| **Advanced** | 25 tools | Administrators - Graph analysis |

### 🗃️ Universal Memento Storage
- **SQLite backend**: Zero dependencies, local storage
- **Full-text search**: Fast, fuzzy matching across all memories
- **Automatic maintenance**: Confidence decay, relationship integrity
- **Cross-platform**: Same database works across all integrations

## 📖 What Can I Do With It?

### For Developers & Teams
- **Remember solutions**: Store fixes for recurring bugs across all tools
- **Track decisions**: Document architecture choices accessible from any IDE
- **Build knowledge base**: Create personal or team documentation
- **Connect concepts**: See relationships between technologies
- **Share knowledge**: Build team memory accessible to all members
- **Onboard faster**: New members can search past solutions from day one
- **Reduce repetition**: Stop solving the same problems across different tools
- **Pattern recognition**: Identify recurring issues across projects

### For AI Assistants & Tools
- **Context persistence**: Remember conversations across sessions and tools
- **Intelligent recall**: Find relevant knowledge regardless of which tool you're using
- **Relationship awareness**: Understand how concepts connect across your entire workflow
- **Quality maintenance**: Automatically deprecate outdated information
- **Universal access**: Same knowledge base from CLI, IDE, or API

## 🛠️ Quick Examples

### Store and Search (Works Everywhere)
```python
# Store a solution - same API across all integrations
memory_id = store_memento(
    type="solution",
    title="Fixed memory leak in WebSocket handler",
    content="Added proper cleanup in on_close()...",
    tags=["websocket", "memory", "python"],
    importance=0.9
)

# Search for solutions - accessible from any tool
results = recall_mementos(query="WebSocket memory leak")
```

### Confidence Management (Universal)
```python
# Find low-confidence memories - system works across all platforms
low_confidence = get_low_confidence_mementos(threshold=0.3)

# Boost confidence when validated - updates reflected everywhere
boost_memento_confidence(memory_id="abc-123", reason="Verified in production")
```

### Cross-Tool Workflow
```bash
# Store from CLI agent
gemini --mcp-servers memento "Store this Redis fix: $(cat redis-fix.txt)"

# Access from IDE later
# (Same memory appears in Zed, Cursor, VSCode, etc.)

# Query from Python API
import memento
# Access the same memory stored from CLI
```

## ⚙️ Universal Configuration

### Single Configuration, Multiple Integrations
Configure once, use everywhere. Memento's configuration system works identically across all integrations.

### Environment Variables (Universal)
```bash
# Database location - same for all tools
export MEMENTO_SQLITE_PATH="~/.mcp-memento/context.db"

# Tool profile - consistent across IDE, CLI, and API
export MEMENTO_TOOL_PROFILE="extended"

# Logging level - unified logging system
export MEMENTO_LOG_LEVEL="INFO"
```

### YAML Configuration (Shared Across Tools)
Memento supports YAML configuration files with the following hierarchy (highest priority last):

1. **Default values** - Hardcoded in code
2. **Global config** - `~/.mcp-memento/config.yaml` (user home directory)
3. **Project config** - `./memento.yaml` (current project directory)
4. **Environment variables** - Highest priority

**Project configuration** (`./memento.yaml` in your project root):
```yaml
sqlite_path: ~/.mcp-memento/context.db
tool_profile: extended
log_level: INFO
```

**Global configuration** (`~/.mcp-memento/config.yaml`):
```yaml
# Global settings for all projects and tools
sqlite_path: ~/.mcp-memento/global.db
tool_profile: extended
log_level: INFO
```

**Configuration works identically for:**
- IDE integrations (Zed, Cursor, Windsurf, VSCode, Claude Desktop)
- CLI agents (Gemini CLI, Claude CLI)
- Python API and custom applications
- REST API and HTTP integrations

## 🔄 Universal Execution

### As an MCP Server (All Integrations)
```bash
# Start server - same binary works for all integrations
memento

# Extended profile - consistent across tools
memento --profile extended

# Health check - verify server works for all clients
memento --health

# Show configuration - see unified settings
memento --show-config
```

### Multiple Entry Points (Same Functionality)
- `memento` - Main executable (used by IDEs and CLI agents)
- `python -m memento` - Python module (for Python API)
- `python -m memento.server` - Direct server (custom integrations)
- `python run_mcp_memento.py` - Wrapper script (flexible deployment)

### Integration-Specific Examples
```bash
# IDE: Configure in IDE settings, then use normally
# CLI: gemini --mcp-servers memento
# Python: import memento; server = memento.Memento()
# All access the same memories with the same configuration
```

## 📚 Universal Documentation

### Essential Guides (Apply to All Integrations)
- **[Tools Reference](docs/TOOLS.md)** - Complete guide to all MCP tools (same tools everywhere)
- **[Confidence System](docs/DECAY_SYSTEM.md)** - How confidence tracking works (unified system)
- **[Python API](docs/integrations/PYTHON.md)** - Using Memento as a Python library
- **[Usage Rules](docs/RULES.md)** - Best practices and conventions (cross-platform)
- **[Agent Configuration](docs/AGENT_CONFIGURATION.md)** - Templates for AI agents

### Integration-Specific Guides
- **[IDE Integration](docs/integrations/IDE.md)** - Zed, Cursor, Windsurf, VSCode, Claude Desktop
- **[Python Integration](docs/integrations/PYTHON.md)** - Programmatic usage and custom agents
- **[Agent Integration](docs/integrations/AGENT.md)** - Gemini CLI, Claude CLI, custom agents
- **[API & Programmatic Integration](docs/integrations/API.md)** - HTTP REST API, Node.js SDK, Docker deployment

### Advanced Topics (Universal Architecture)
- **[Database Schema](docs/dev/SCHEMA.md)** - Technical database structure (shared storage)
- **[API & Programmatic Integration](docs/integrations/API.md)** - HTTP REST API, Node.js SDK, Docker deployment

## 🔗 Universal Integrations

### IDE Integration (All Major IDEs)
```json
{
  "context_servers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "extended"],
      "env": {
        "MEMENTO_SQLITE_PATH": "~/.mcp-memento/context.db"
      }
    }
  }
}
```

### Agent Integration Example (Gemini CLI)
```bash
# Start Gemini with Memento (using default configuration)
gemini --mcp-servers memento

# With custom profile via CLI arguments
gemini --mcp-servers 'memento --profile extended'

# Or use wrapper script with environment variables
MEMENTO_TOOL_PROFILE="advanced" gemini --mcp-servers memento

# Or use wrapper script
gemini-with-memory "Search for Redis timeout solutions"
```

**Configuration methods for agents:**
1. **Environment variables** (highest priority):
   ```bash
   export MEMENTO_SQLITE_PATH="~/.gemini-memento/context.db"
   export MEMENTO_TOOL_PROFILE="extended"
   export MEMENTO_LOG_LEVEL="INFO"
   ```

2. **YAML configuration files** (automatic detection):
   - Project config: `./memento.yaml` in current directory
   - Global config: `~/.mcp-memento/config.yaml`

3. **CLI arguments** (passed to MCP server):
   ```bash
   gemini --mcp-servers 'memento --profile advanced --log-level DEBUG'
   ```

### Detailed Integration Guides
For complete integration instructions, see:
- **[IDE Integration](docs/integrations/IDE.md)** - Detailed setup for all supported IDEs
- **[Python Integration](docs/integrations/PYTHON.md)** - Programmatic usage and API reference
- **[Agent Integration](docs/integrations/AGENT.md)** - CLI agents and custom applications

## 🏗️ Universal Architecture

### Universal Database Schema
Memento uses a unified SQLite schema accessible from all integrations:
- **Core tables** (shared across all platforms):
  - `nodes`: Memory storage with properties and metadata
  - `relationships`: Directed graph with bi-temporal tracking and confidence system
- **Virtual table** (conditional creation):
  - `nodes_fts`: FTS5 virtual table for full-text search
- **Indexes**: Optimized for temporal queries, confidence filtering, and relationship lookups

The schema includes automatic confidence tracking with 5% monthly decay for unused knowledge, ensuring consistent behavior across all integration points.

### Universal Confidence System
The confidence system works identically across all platforms:
1. **Tracks usage**: Each memory access boosts confidence (from any tool)
2. **Applies decay**: Unused memories lose 5% confidence monthly (consistent timing)
3. **Protects critical**: Security/auth memories never decay (global protection)
4. **Optimizes search**: Results ordered by `confidence × importance` (same ranking everywhere)
5. **Cross-platform sync**: Confidence updates from one tool immediately reflected in all others

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
- **Start with recall**: Use `recall_mementos()` for natural language
- **Use tags for acronyms**: Tag `jwt`, `api`, `oauth2` for reliable retrieval
- **Filter by type**: Search `solution` or `pattern` when looking for specific formats
- **Leverage relationships**: Use `get_related_mementos()` to explore connections

## 🚨 Troubleshooting

### Common Issues

**Server won't start:**
```bash
# Check installation
which memento

# Test basic functionality
memento --health

# Check permissions on database file
ls -la ~/.mcp-memento/
```

**No tools available in IDE:**
- Verify MCP configuration is correct
- Restart your IDE after configuration changes
- Check IDE logs for MCP server errors
- Test with `memento --list-tools` to verify installation

**Slow searches:**
- Database might need vacuuming: `memento --maintenance`
- Consider archiving old, low-confidence memories
- Check disk space on database location

### Debug Mode
```bash
# Enable verbose logging
MEMENTO_LOG_LEVEL=DEBUG memento

# Or use command line
memento --log-level DEBUG --profile core
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
git clone https://github.com/annibale-x/memento-mcp-server.git
cd mcp-memento

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

### Project Structure
```
mcp-memento/
├── src/                          # Source code
│   └── memento/                  # Main package
├── docs/                        # Documentation
├── tests/                       # Test suite
├── pyproject.toml              # Package configuration
├── MANIFEST.in                 # Additional files for distribution
├── CONTRIBUTING.md             # Contribution guidelines
├── LICENSE                     # MIT License
└── README.md                   # This file
```

### Setup
```bash
# Clone repository
git clone https://github.com/annibale-x/memento-mcp-server.git
cd mcp-memento

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
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
- **[Database Schema](docs/dev/SCHEMA.md)** - Database structure and design

## 🔗 Links

- **[GitHub Repository](https://github.com/annibale-x/memento-mcp-server)** - Source code and issues
- **[MCP Protocol](https://spec.modelcontextprotocol.io/)** - Model Context Protocol specification
- **[PyPI Package](https://pypi.org/project/mcp-memento/)** - Python Package Index
- **[Discussions](https://github.com/annibale-x/memento-mcp-server/discussions)** - Community forum

---

**Need help?** Check the [documentation](docs/) or open an [issue](https://github.com/annibale-x/memento-mcp-server/issues) on GitHub.
