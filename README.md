# MCP Context Keeper

[![PyPI version](https://img.shields.io/pypi/v/mcp-context-keeper.svg)](https://pypi.org/project/mcp-context-keeper/)
[![Python versions](https://img.shields.io/pypi/pyversions/mcp-context-keeper.svg)](https://pypi.org/project/mcp-context-keeper/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful **Model Context Protocol (MCP)** server for managing and persisting context across conversations. Enables AI assistants to remember information, preferences, and decisions between sessions.

## 🚀 Features

- **Persistent Memory**: Store and retrieve information across conversations
- **Context Management**: Maintain project context, decisions, and architectural choices
- **Relationship Tracking**: Connect memories with semantic relationships (CAUSES, SOLVES, DEPENDS_ON, etc.)
- **MCP Integration**: Seamless integration with Zed Editor and other MCP clients
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Async-First**: Built with async/await for high performance

## 📦 Installation

```bash
pip install mcp-context-keeper
```

For development with server capabilities:
```bash
pip install "mcp-context-keeper[server,dev]"
```

## 🎯 Quick Start

### Basic Usage

```python
from mcp_context_keeper import ContextKeeper

# Initialize the context keeper
keeper = ContextKeeper()

# Store a memory
await keeper.store_memory(
    content="User prefers dark theme and uses Python 3.11",
    memory_type="preference",
    title="User Preferences"
)

# Recall memories
memories = await keeper.recall_memories("theme preferences")
print(memories)
```

### MCP Server Setup

```python
from mcp_context_keeper.server import MCPServer

# Start the MCP server
server = MCPServer()
await server.start()
```

## 🔧 MCP Tools Provided

The server exposes the following MCP tools:

### Memory Management
- `store_memory` - Store new information
- `recall_memories` - Retrieve stored memories
- `search_memories` - Search memories by content
- `update_memory` - Update existing memory
- `delete_memory` - Remove a memory

### Relationship Management
- `create_relationship` - Connect two memories
- `get_related_memories` - Find related memories
- `delete_relationship` - Remove a relationship

### Context Management
- `set_project_context` - Set context for current project
- `get_project_context` - Retrieve project context
- `clear_project_context` - Clear project context

## 🏗️ Architecture

### Memory Types
- **Task**: Development tasks and objectives
- **Solution**: Code solutions and patterns
- **Problem**: Issues and bugs encountered
- **Fix**: Bug fixes and resolutions
- **Error**: Error messages and stack traces
- **Preference**: User preferences and settings
- **Decision**: Architectural decisions
- **Command**: Shell commands and scripts
- **Configuration**: Configuration details
- **Documentation**: Documentation notes
- **Test**: Test cases and results
- **Research**: Research findings
- **Idea**: Ideas and suggestions

### Relationship Types
- **CAUSES**: Memory A causes Memory B
- **SOLVES**: Memory A solves Memory B
- **ADDRESSES**: Memory A addresses Memory B
- **DEPENDS_ON**: Memory A depends on Memory B
- **RELATED_TO**: General relationship
- **VERSION_OF**: Version relationship
- **ALTERNATIVE_TO**: Alternative solution
- **IMPROVES**: Improvement relationship
- **REFERS_TO**: Reference relationship

## 📁 Project Structure

```
mcp_context_keeper/
├── __init__.py              # Package exports
├── context_keeper.py        # Main ContextKeeper class
├── models.py               # Pydantic models
├── storage.py              # Storage backends (SQLite, NetworkX)
├── server.py               # MCP server implementation
├── tools.py                # MCP tool handlers
└── exceptions.py           # Custom exceptions
```

## 🔌 Integration with Zed Editor

Add to your Zed settings:

```json
{
  "mcp_servers": {
    "context-keeper": {
      "command": "python",
      "args": ["-m", "mcp_context_keeper.server"],
      "env": {
        "CONTEXT_KEEPER_DB_PATH": "~/.context_keeper.db"
      }
    }
  }
}
```

## 🧪 Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/annibale-x/context-keeper-mcp-server.git
cd context-keeper-mcp-server

# Install with development dependencies
pip install -e ".[dev,server]"

# Run tests
pytest

# Format code
black .
ruff check --fix
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mcp_context_keeper tests/

# Run specific test file
pytest tests/test_context_keeper.py
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

- Issues: [GitHub Issues](https://github.com/annibale-x/context-keeper-mcp-server/issues)
- Discussions: [GitHub Discussions](https://github.com/annibale-x/context-keeper-mcp-server/discussions)

## 🙏 Acknowledgments

- Built on top of the [Model Context Protocol](https://spec.modelcontextprotocol.io/)
- Inspired by the need for persistent context in AI development workflows
- Thanks to the Zed Editor team for the amazing MCP implementation

---

**MCP Context Keeper** - Remember everything, forget nothing. 🧠
