# Integration Guide

## Table of Contents

- Integration Categories (IDE, Python, Agent)
- Quick Start Examples
- Choosing the Right Integration
- Configuration Hierarchy
- Common Integration Patterns
- Concurrency and Locking
- Getting Help & Next Steps

This guide provides an overview of Memento integration options. For detailed instructions, please refer to the specific integration guides.

## Integration Categories

Memento supports three main integration categories:

### 1. IDE Integrations
For code editors and development environments that support MCP (Model Context Protocol).

**Supported IDEs:**
- **Zed Editor** - Native MCP support
- **Cursor** - AI-powered code editor
- **Windsurf** - Modern code editor with AI
- **VSCode** - Via MCP extension
- **Claude Desktop** - Desktop application for Claude AI

**📖 Detailed Guide:** [IDE Integration Guide](./integrations/IDE.md)

### 2. Python Integrations
For programmatic access and custom agent development.

**Use Cases:**
- Custom AI agents with memory
- Automated knowledge management
- Batch processing of memories
- Integration with existing Python applications
- Advanced analytics and reporting

**📖 Detailed Guide:** [Python Integration Guide](./integrations/PYTHON.md)

### 3. Agent Integrations
For CLI tools and custom applications.

**Supported Agents:**
- **Gemini CLI** - Google's Gemini command-line interface
- **Claude CLI** - Anthropic's Claude command-line interface
- **Custom CLI Agents** - Your own command-line tools

**API & Programmatic Access:**
- **HTTP REST API** - RESTful API for remote access
- **Node.js SDK** - JavaScript/TypeScript integration
- **Docker Deployment** - Containerized deployment
- **Python API** - Programmatic Python integration

**📖 Detailed Guides:**
- [Agent Integration Guide](./integrations/AGENT.md) - CLI agents
- [API & Programmatic Integration Guide](./integrations/API.md) - REST API, Node.js, Docker

## Quick Start Examples

> **Configuration Methods**: Memento supports CLI arguments, environment variables, and YAML config files.
> See the full reference in [IDE Integration Guide — Configuration Methods](./integrations/IDE.md#configuration-methods)
> or [README — Configuration](../README.md#configuration).

### IDE Example (Zed Editor)
Minimal config using CLI arguments (recommended):
```json
{
  "context_servers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "extended", "--db", "~/.mcp-memento/context.db"]
    }
  }
}
```

### Agent Example (Gemini CLI)
```bash
# Start Gemini with Memento
gemini --mcp-servers memento

# Or use wrapper script
gemini-with-memory "Search for Redis timeout solutions"
```

### Python Example

Memento is a **MCP server** — tools are called via the MCP JSON-RPC protocol,
not as direct Python method calls. Use the `mcp` library to connect as a client:

```python
import asyncio, json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="memento", args=["--profile", "extended"]
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "store_memento",
                arguments={
                    "type": "solution",
                    "title": "Database optimization",
                    "content": "Optimized queries and added indexes...",
                    "tags": ["database", "optimization"],
                    "importance": 0.8,
                },
            )
            print(json.loads(result.content[0].text))

asyncio.run(main())
```

For full details see [Python Integration Guide](./integrations/PYTHON.md).

## Choosing the Right Integration

### For Developers
- **Primary Use**: IDE integration (Zed, Cursor, Windsurf)
- **Secondary Use**: Python API for automation
- **Best Profile**: Extended (17 tools)

### For Teams
- **Primary Use**: Shared database with IDE integration
- **Secondary Use**: Python API for team tools
- **Best Profile**: Extended or Advanced

### For AI Agent Developers
- **Primary Use**: MCP client (Python `mcp` library) for custom agents
- **Secondary Use**: HTTP REST API for multi-language support
- **Best Profile**: Advanced (25 tools)

### For System Administrators
- **Primary Use**: CLI tools and automation
- **Secondary Use**: HTTP REST API for monitoring
- **Best Profile**: Advanced with custom configuration

## Configuration Hierarchy

Memento supports multiple configuration sources. Order of precedence (highest first):

1. **CLI arguments** (highest priority — always win)
   ```bash
   memento --profile extended --db ~/my-context.db
   ```

2. **Environment variables**
   ```bash
   export MEMENTO_DB_PATH="~/custom/path/memento.db"
   export MEMENTO_PROFILE="advanced"
   ```

3. **YAML configuration files** (lowest explicit priority)
   ```yaml
   # memento.yaml
   db_path: ~/.mcp-memento/context.db
   profile: extended
   log_level: INFO
   ```

   The `memento.yaml` file is searched in this order (first found wins):
   - Current working directory (`./memento.yaml`)
   - User home directory (`~/.mcp-memento/config.yaml`)

4. **Built-in defaults** (lowest priority)

## Common Integration Patterns

### Pattern 1: Project-Specific Memory
Use different databases for different projects:
```bash
# Project A
cd ~/projects/project-a
export MEMENTO_DB_PATH="./.memento/project-a.db"
memento --profile extended

# Project B  
cd ~/projects/project-b
export MEMENTO_DB_PATH="./.memento/project-b.db"
memento --profile extended
```

### Pattern 2: Team Shared Memory
Share a database across team members:
```bash
# Linux/macOS: use a shared network mount
export MEMENTO_DB_PATH="/mnt/shared/team-memory.db"

# Windows: use a UNC path or mapped drive
# set MEMENTO_DB_PATH=\\server\share\team-memory.db
# set MEMENTO_DB_PATH=Z:\team-memory.db

memento --profile extended
```
> **Note (Windows)**: `/mnt/shared/...` is a Unix-style path. Use a UNC path or mapped drive letter instead.

### Pattern 3: Development vs Production
Different profiles for different environments:
```bash
# Development - full toolset
export MEMENTO_PROFILE="advanced"
memento

# Production - minimal tools
export MEMENTO_PROFILE="core"
memento
```

## Concurrency and Locking

Memento uses SQLite with Write-Ahead Logging (WAL) mode enabled by default to support concurrent read and write operations from multiple clients. This allows multiple IDE instances or AI agents to access the same memory database simultaneously.

### Key Features:
- **WAL Mode**: Enables concurrent reads and writes without locking conflicts
- **Optimistic Locking**: Memory version tracking prevents overwrite conflicts
- **Automatic Retry**: Built-in retry logic for transient lock conflicts
- **Connection Pooling**: Efficient handling of multiple concurrent connections

### Best Practices for Team Usage:
1. **Shared Network Storage**: When using a shared database on network storage, ensure filesystem supports locking
2. **Regular Backups**: Export memories periodically with `memento export --format json --output backup.json`
3. **Backup Strategy**: Implement regular backups for shared databases
4. **Monitoring**: Monitor database size and lock contention if experiencing performance issues

### Common Scenarios:
- **Multiple IDEs**: Different team members can use Memento simultaneously from different IDEs
- **CI/CD Pipelines**: Automated scripts can access memories while developers work
- **Cross-Platform**: Windows, macOS, and Linux clients can share the same database file

### Troubleshooting Lock Conflicts:
If you encounter "database is locked" errors:
1. Check if multiple processes are writing simultaneously
2. Verify filesystem permissions support SQLite locking
3. Consider using separate database files for high-concurrency scenarios
4. Ensure adequate disk space and I/O performance

## Getting Help

### Documentation Links
- **[Main Documentation](../README.md)** - Overview and quick start
- **[Tools Reference](../TOOLS.md)** - Complete MCP tool reference
- **[Confidence System](../DECAY_SYSTEM.md)** - Confidence tracking details
- **[Usage Rules](../RULES.md)** - Best practices and conventions
- **[Agent Configuration](../AGENT_CONFIGURATION.md)** - Templates for AI agents

### Integration-Specific Help
- **IDE Issues**: Check [IDE.md](./integrations/IDE.md#troubleshooting)
- **Python Issues**: Check [PYTHON.md](./integrations/PYTHON.md#error-handling)
- **Agent Issues**: Check [AGENT.md](./integrations/AGENT.md#troubleshooting)

### Community Support
- **GitHub Issues**: [Report bugs or request features](https://github.com/annibale-x/mcp-memento/issues)
- **Documentation**: Check the `docs/` directory for complete guides

## Next Steps

1. **Choose your integration type** from the categories above
2. **Read the specific guide** for detailed instructions
3. **Configure your environment** following the examples
4. **Test the integration** with simple operations
5. **Explore advanced features** as needed

Remember: Memento is designed to be flexible. Start simple with the Core profile and expand to Extended or Advanced as your needs grow.

---

**Need more help?** Each integration guide contains detailed troubleshooting sections, examples, and best practices for that specific integration type.