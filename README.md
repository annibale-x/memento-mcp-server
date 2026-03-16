# MCP Memento

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-blueviolet)](https://spec.modelcontextprotocol.io/)

Intelligent memory management for MCP clients with confidence tracking, relationship mapping, and knowledge quality maintenance.

Memento is an MCP server that provides persistent memory capabilities across multiple platforms:
- **IDEs**: Zed, Cursor, Windsurf, VSCode, Claude Desktop
- **CLI Agents**: Gemini CLI, Claude CLI, custom agents
- **Programmatic Usage**: Python API, REST API, custom integrations
- **Applications**: Any MCP-compatible application

Build a personal or team knowledge base that grows smarter over time, accessible from all your development tools.

## ✨ Key Features

### 🧠 Intelligent Confidence System
- **Automatic decay**: Unused knowledge loses confidence over time (5% monthly)
- **Critical protection**: Security/auth/API key memories never decay
- **Boost on validation**: Confidence increases when knowledge is successfully used
- **Smart ordering**: Search results ranked by `confidence × importance`

### 🔗 Relationship Mapping
- **35+ relationship types**: SOLVES, CAUSES, IMPROVES, USED_IN, etc. (see [Relationship Types Reference](docs/RELATIONSHIPS.md))
- **Graph navigation**: Find connections between concepts
- **Pattern detection**: Identify recurring solution patterns

### 📊 Three Profile System
| Profile | Tools | Best For |
|---------|-------|----------|
| **Core** | 13 tools | All users - Essential operations |
| **Extended** | 17 tools | Power users - Analytics + contextual search |
| **Advanced** | 25 tools | Administrators - Graph analysis |

### 🗃️ Cross-Platform Storage
- **SQLite backend**: Zero dependencies, local storage
- **Full-text search**: Fast, fuzzy matching across all memories
- **Automatic maintenance**: Confidence decay, relationship integrity
- **Shared database**: Same database works across all integrations

## 🔄 MCP Operational Protocols (Auto-Onboarding)

When MCP tools are available, AI assistants should apply the following logic based on the active server:

- **Memento Module**: If Memento tools are available, you MUST execute `memento_onboarding()` at the start of every session to inject the memory management protocol.

This ensures proper guidance for memory operations, optimized retrieval flow (1-3 tool calls for simple info, max 5 for complex tasks), and adherence to best practices.

## 🚀 Quick Start

### 1. Installation

```bash
# Install with pipx (recommended for MCP servers)
pipx install mcp-memento

# Or with pip
pip install mcp-memento
```

### 2. Basic Configuration

**IDEs** (Example for Cursor Editor):
```json
{
  "mcpServers": {
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

**CLI Agents** (Gemini CLI):
```bash
gemini --mcp-servers memento
```

### 3. First Steps

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
```

**💬 Natural Language**: You can also interact with Memento through natural conversation. Just tell your AI assistant things like "Remember that..." or "Store this..." - no code required.

## 📖 Core Concepts

### Confidence System
Memento automatically tracks the reliability of knowledge over time. Unused memories gradually lose confidence, while validated solutions gain confidence. Critical information (security/auth/API keys) is protected from decay.

**Learn more**: [Confidence System Documentation](docs/DECAY_SYSTEM.md)

### Relationship Types
Memories can be connected using semantic relationships like `SOLVES`, `CAUSES`, `APPLIES_TO`, and 32 others. These relationships create a knowledge graph that enables intelligent navigation and pattern discovery.

**Complete reference**: [Relationship Types Documentation](docs/RELATIONSHIPS.md)

### Tool Profiles
Three profiles provide different capabilities:
- **Core**: Essential operations for all users
- **Extended**: Additional analytics and contextual search
- **Advanced**: Full graph analysis and pattern detection

## 🔗 Integrations

Memento works with all major development tools:

| Platform | Configuration Guide | Notes |
|----------|---------------------|-------|
| **Zed Editor** | [IDE Integration](docs/integrations/IDE.md#zed-editor) | Native MCP support |
| **Cursor** | [IDE Integration](docs/integrations/IDE.md#cursor) | AI-powered editor |
| **Windsurf** | [IDE Integration](docs/integrations/IDE.md#windsurf) | Modern code editor |
| **VSCode** | [IDE Integration](docs/integrations/IDE.md#vscode) | Via MCP extension |
| **Claude Desktop** | [IDE Integration](docs/integrations/IDE.md#claude-desktop) | Desktop application |
| **Gemini CLI** | [Agent Integration](docs/integrations/AGENT.md#gemini-cli) | Google's CLI agent |
| **Claude CLI** | [Agent Integration](docs/integrations/AGENT.md#claude-cli) | Anthropic's CLI agent |
| **Python API** | [Python Integration](docs/integrations/PYTHON.md) | Programmatic access |
| **REST API** | [API Integration](docs/integrations/API.md) | HTTP access |

**See also**: [Integration Overview](docs/INTEGRATION.md) for guidance on choosing the right integration.

## 🛠️ Basic Usage Examples

### Store and Retrieve Knowledge

```python
# Store a solution
solution_id = store_memento(
    type="solution",
    title="Fixed memory leak in WebSocket handler",
    content="Added proper cleanup in on_close()...",
    tags=["websocket", "memory", "python"],
    importance=0.9
)

# Natural language search
results = recall_mementos(query="WebSocket memory leak", limit=5)

# Tag-based search
redis_solutions = search_mementos(tags=["redis"], memory_types=["solution"])
```

### Manage Confidence

```python
# Find potentially obsolete knowledge
low_confidence = get_low_confidence_mementos(threshold=0.3)

# Boost confidence after verification
boost_memento_confidence(
    memory_id=verified_solution_id,
    boost_amount=0.15,
    reason="Verified in production deployment"
)
```

### Create Relationships

```python
# Link solution to problem
create_memento_relationship(
    from_memory_id=solution_id,
    to_memory_id=problem_id,
    relationship_type="SOLVES",  # See all 35 types in docs/RELATIONSHIPS.md
    strength=0.9,
    context="Connection pooling resolved the timeout issue"
)

# Explore connected knowledge
related = get_related_mementos(
    memory_id=solution_id,
    relationship_types=["RELATED_TO", "USED_IN"],
    max_depth=2
)
```

### Natural Language Interaction (Chat-Based)

Memento is designed to work seamlessly through natural language conversations with your AI assistant. You can interact with memories using everyday language:

**Store personal information:**
```
User: Remember that my name is Hannibal
AI: ✅ Memento stored - "Your name is Hannibal"

User: Remember that I love programming in Rust
AI: ✅ Memento stored and relationship created: "Hannibal loves Rust programming"
```

**Store work-related knowledge:**
```
User: Remember that we solved Redis timeout with connection pooling
AI: ✅ Memento stored and linked to previous problem - "Redis timeout solution with connection pooling"

User: Store this fix: increased database timeout to 30 seconds
AI: ✅ Memento stored - "Database timeout fix: 30 seconds"
```

**Retrieve knowledge naturally:**
```
User: What do you remember about Redis timeout?
AI: Found 2 solutions: 1) Connection pooling... 2) Query optimization...

User: What do we know about WebSocket memory leaks?
AI: Found 3 solutions: 1) Proper cleanup in on_close()... 2) Buffer management... 3) Connection limits...
```

**Create relationships automatically:**
```
User: Remember that the connection pooling solution solves the Redis timeout
AI: ✅ Memento stored and relationship created: solution SOLVES problem

User: Remember that the WebSocket fix addresses the memory leak issue
AI: ✅ Memento stored and relationship created: fix ADDRESSES error
```

**Using the "Memento" keyword:**
You can also start any sentence with "Memento" to store or retrieve information:
```
User: Memento I love coffee
AI: ✅ Memento stored - "Hannibal loves coffee"

User: Memento what is the Gemini API key for the project?
AI: Found API key: "AIzaSyD...". Would you like me to store this information securely?

User: Memento the deployment script is in /scripts/deploy.sh
AI: ✅ Memento stored - "Deployment script location: /scripts/deploy.sh"

User: Memento how do we handle authentication?
AI: Found 3 authentication patterns: 1) JWT with refresh tokens... 2) OAuth2 integration... 3) API key middleware...
```

**Automatic storage**
The AI assistant automatically stores important information without explicit commands when configured with proper guidelines

**Multi-language support:**
Memento understands trigger phrases in multiple languages; this natural language interface makes Memento accessible to everyone, not just developers, while maintaining all the advanced features like confidence tracking and relationship mapping in the background.

## ⚙️ Configuration

Memento supports multiple configuration sources (in order of precedence):

1. **Environment Variables** (highest priority)
   ```bash
   export MEMENTO_SQLITE_PATH="~/custom/path/memento.db"
   export MEMENTO_TOOL_PROFILE="advanced"
   export MEMENTO_LOG_LEVEL="DEBUG"
   ```

2. **YAML Configuration Files**
   - Project config: `./memento.yaml` in current directory
   - Global config: `~/.mcp-memento/config.yaml`

3. **Command-Line Arguments**
   ```bash
   memento --profile extended --sqlite-path ~/my-context.db
   ```

4. **Default Values** (lowest priority)

### Example Configuration Files

**Project configuration** (`./memento.yaml`):
```yaml
sqlite_path: ~/.mcp-memento/context.db
tool_profile: extended
log_level: INFO
```

**Global configuration** (`~/.mcp-memento/config.yaml`):
```yaml
sqlite_path: ~/.mcp-memento/global.db
tool_profile: extended
log_level: INFO
```

## 📚 Documentation Structure

### Essential Guides
- **[Tools Reference](docs/TOOLS.md)** - Complete guide to all MCP tools
- **[Confidence System](docs/DECAY_SYSTEM.md)** - How confidence tracking works
- **[Relationship Types](docs/RELATIONSHIPS.md)** - All 35 relationship types with examples
- **[Usage Rules](docs/RULES.md)** - Best practices and conventions
- **[Agent Configuration](docs/AGENT_CONFIGURATION.md)** - Templates for AI agents

### Integration Guides
- **[Integration Overview](docs/INTEGRATION.md)** - Choosing the right integration
- **[IDE Integration](docs/integrations/IDE.md)** - Zed, Cursor, Windsurf, VSCode, Claude Desktop
- **[Python Integration](docs/integrations/PYTHON.md)** - Programmatic usage and API reference
- **[Agent Integration](docs/integrations/AGENT.md)** - CLI agents and custom applications
- **[API & Programmatic Integration](docs/integrations/API.md)** - HTTP REST API, Node.js SDK, Docker

### Development & Advanced Topics
- **[Database Schema](docs/dev/SCHEMA.md)** - Technical database structure
- **[Contributing Guidelines](CONTRIBUTING.md)** - Development setup and workflow

## 🏗️ Architecture Overview

### Database Schema
Memento uses a unified SQLite schema accessible from all integrations:
- **Core tables**: `nodes` (memory storage), `relationships` (directed graph)
- **Full-text search**: FTS5 virtual table for fast searching
- **Confidence tracking**: Automatic decay with protection for critical memories

### Consistent Behavior
The system works identically across all platforms:
1. **Same database**: All tools access the same SQLite file
2. **Same confidence tracking**: Updates from one tool reflected everywhere
3. **Same search ranking**: Results ordered by `confidence × importance`
4. **Same relationship types**: 35 semantic relationship types available everywhere

## 📜 Background

Memento is a simplified, lightweight fork of the original [MemoryGraph](https://github.com/memory-graph/memory-graph) project by Gregory Dickson. The goal of this fork is to create a focused, portable memory management system specifically optimized for MCP (Model Context Protocol) integration across all major IDEs and CLI agents.

### Why a Simplified Fork?
MemoryGraph is a powerful, feature-rich memory system with extensive capabilities. However, for MCP integration and broad IDE compatibility, we needed a more focused approach:

- **Lightweight & Portable**: Removed heavy dependencies like NetworkX and complex backend systems
- **Token-Efficient**: Simplified architecture reduces token consumption in AI interactions
- **Cross-Platform Focus**: Optimized for seamless integration with Zed, Cursor, Windsurf, VSCode, Claude Desktop, and CLI agents
- **Core Features Only**: Focused on essential memory operations, confidence tracking, and relationship mapping
- **Simplified Storage**: SQLite-only backend removes complexity of multi-backend support

### What Was Simplified?
- **Removed**: Bi-temporal tracking system (replaced with simpler confidence-based decay)
- **Removed**: Proactive memory features (now uses guideline-based storage)
- **Removed**: Multi-tenant architecture (focused on single-user local storage)
- **Removed**: Heavy dependencies (NetworkX, complex database backends)
- **Removed**: Tens of thousands of lines of backend-specific code

### Team Collaboration & Remote Deployment
While Memento has removed formal multi-tenant architecture, it still supports team collaboration through **shared database access**:

- **Team Collaboration**: Multiple users can share the same SQLite database file (e.g., on network storage). The [Team Collaboration guidelines](docs/AGENT_CONFIGURATION.md#advanced-team-collaboration) provide tagging conventions (`team:[team-name]`, `author:[name]`) for organized shared usage.
- **Remote MCP Server**: Memento can run as a remote MCP server accessible by multiple clients. However, all clients share the same database without built-in tenant isolation.
- **Shared Memory Guidelines**: The included team collaboration templates are valid and functional for teams willing to share a common knowledge base with tagging-based organization.

For true multi-tenancy with isolated databases per team/user, consider using the original MemoryGraph project which includes built-in tenant isolation and advanced access controls.

### When to Choose MemoryGraph vs Memento?
- **Use Memento**: For lightweight, cross-platform memory management in IDEs and CLI tools
- **Use MemoryGraph**: For complex enterprise use cases requiring multi-tenancy, bi-temporal tracking, advanced analytics, or custom backend systems

## 🙏 Acknowledgments

Memento is built upon the solid foundation of Gregory Dickson's [MemoryGraph](https://github.com/memory-graph/memory-graph) project. We're grateful for his pioneering work in memory management systems.

This fork maintains compatibility with MemoryGraph's core concepts while adapting them for the specific needs of MCP integration and modern development tooling. For users requiring the full power of MemoryGraph's advanced features, we recommend exploring the original project.

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on:
- Development setup and workflow
- Code style and conventions
- Testing requirements
- Documentation standards
- Pull request process

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🔗 Links

- **[GitHub Repository](https://github.com/annibale-x/memento-mcp-server)** - Source code and issues
- **[MCP Protocol](https://spec.modelcontextprotocol.io/)** - Model Context Protocol specification
- **[PyPI Package](https://pypi.org/project/mcp-memento/)** - Python Package Index

---

**Need help?** Check the [documentation](docs/) or open an [issue](https://github.com/annibale-x/memento-mcp-server/issues) on GitHub.
