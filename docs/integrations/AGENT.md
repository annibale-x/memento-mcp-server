# Agent Integration Guide

This guide covers how to integrate Memento with various AI agents and CLI tools that support the Model Context Protocol (MCP). Memento provides persistent memory capabilities to enhance your AI workflows across different platforms.

## Table of Contents

- [Installation](#installation)
- [Gemini CLI](#gemini-cli)
- [Claude CLI](#claude-cli)
- [Custom CLI Agents](#custom-cli-agents)
  - [Python-based Agent](#python-based-agent)
  - [Shell Script Agent](#shell-script-agent)
- [Troubleshooting Common Issues](#troubleshooting-common-issues)
- [Best Practices](#best-practices)

> **Claude Desktop** is an IDE-class integration and is documented in the
> [IDE Integration Guide](./IDE.md).

---

## Installation

Before configuring any agent, install Memento:

```bash
# Install with pipx (recommended)
pipx install mcp-memento

# Or with pip
pip install mcp-memento

# Verify installation
memento --version
```

Memento uses SQLite for local storage by default. The database is automatically created at `~/.mcp-memento/context.db` unless configured otherwise.

## Supported Agents

- [Gemini CLI](#gemini-cli) - Google's command-line interface for Gemini AI
- [Claude CLI](#claude-cli) - Anthropic's command-line interface for Claude AI


## Gemini CLI

### Prerequisites
- **Gemini CLI** installed ([Installation Guide](https://github.com/google-gemini/gemini-cli))
- Gemini CLI version with MCP support

### Configuration

Gemini CLI configuration is stored in `~/.gemini/config.json`:

**Basic configuration:**
```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": []
    }
  }
}
```

### Configuration Options
Memento supports multiple configuration methods that can be used individually or combined:

**Method 1: CLI Arguments Only** (recommended for clarity)
```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "extended", "--db", "~/.gemini-memento/context.db", "--log-level", "INFO"]
    }
  }
}
```

**Method 2: Environment Variables Only**
```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": [],
      "env": {
        "MEMENTO_PROFILE": "extended",
        "MEMENTO_DB_PATH": "~/.gemini-memento/context.db",
        "MEMENTO_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Method 3: Mixed Approach** (use with caution - can be confusing)
```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "extended"],
      "env": {
        "MEMENTO_DB_PATH": "~/.gemini-memento/context.db",
        "MEMENTO_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Configuration Priority
When using mixed approaches, remember the priority order (highest to lowest):
1. **CLI Arguments** (`--profile`, `--db`, `--log-level`)
2. **Environment Variables** (`MEMENTO_PROFILE`, `MEMENTO_DB_PATH`, `MEMENTO_LOG_LEVEL`)
3. **YAML Configuration Files** (`~/.mcp-memento/config.yaml`, `./memento.yaml`)
4. **Default Values**

**Recommendation**: For clarity and maintainability, choose **one method consistently** across your configuration.

### Where to Save Configuration
- **User-level**: `~/.gemini/config.json` (affects all Gemini CLI sessions)
- Gemini CLI will automatically load this configuration on startup

### Usage Examples

```bash
# Start Gemini CLI with Memento
gemini --mcp-servers memento

# Or let Gemini load from config automatically
gemini
```

Once started, you can use Memento through natural language:

```
Store this for later: The database uses PostgreSQL on port 5432
```

```
What do you remember about the database configuration?
```

### Troubleshooting

**MCP server not loading:**
1. Check Gemini CLI version supports MCP
2. Verify `~/.gemini/config.json` has valid JSON syntax
3. Test Memento manually: `memento --health`

**Command not found:**
```bash
# Find Memento installation path
which memento

# Use full path in config
{
  "command": "/Users/yourname/.local/bin/memento"
}
```

## Claude CLI

### Prerequisites
- **Claude CLI** installed ([Installation Guide](https://github.com/anthropics/claude-cli))
- Claude CLI version with MCP support

### Configuration

Claude CLI typically accepts MCP servers via command-line arguments. Create a shell script or alias for convenience:

**Option 1: Direct command-line arguments**
```bash
claude --mcp-servers memento
```

**Option 2: Create a wrapper script (`~/bin/claude-memento`)**
```bash
#!/bin/bash
# claude-memento - Claude CLI with Memento integration

# Configuration
export MEMENTO_DB_PATH="${MEMENTO_DB_PATH:-~/.claude-memento/context.db}"
export MEMENTO_PROFILE="${MEMENTO_PROFILE:-extended}"

# Ensure directory exists
mkdir -p "$(dirname "$MEMENTO_DB_PATH")"

# Start Claude with Memento
exec claude --mcp-servers memento "$@"
```

Make it executable:
```bash
chmod +x ~/bin/claude-memento
```

**Option 3: Environment variables in shell profile**
Add to `~/.bashrc`, `~/.zshrc`, or equivalent:
```bash
export MEMENTO_DB_PATH="~/.claude-memento/context.db"
alias claude-memento='claude --mcp-servers memento'
```

### Config File Locations

Claude CLI does not have a persistent MCP config file; configuration is passed via
CLI flags or environment variables. Persist them in your shell profile:

| Platform | File |
|---|---|
| macOS / Linux (bash) | `~/.bashrc` or `~/.bash_profile` |
| macOS / Linux (zsh) | `~/.zshrc` |
| Windows (PowerShell) | `$PROFILE` (`~\Documents\PowerShell\Microsoft.PowerShell_profile.ps1`) |
| Windows (cmd) | Set via System → Environment Variables |

### Usage Examples

```bash
# Using wrapper script
claude-memento "What do you remember about our authentication system?"

# Or directly
claude --mcp-servers memento "Store this solution for later..."
```

### Troubleshooting

**Claude CLI doesn't recognize --mcp-servers:**
1. Update to latest Claude CLI version
2. Check documentation for correct flag (may be `--mcp` or similar)

**Permission issues:**
```bash
# Ensure script is executable
chmod +x ~/bin/claude-memento

# Ensure ~/bin is in PATH
export PATH="$HOME/bin:$PATH"
```

## Custom CLI Agents

### Python-based Agent

> **Architecture note**: Memento is an MCP server — its tools (`store_memento`,
> `recall_mementos`, etc.) are **not** callable as direct Python methods. All
> programmatic access happens through an MCP client session using the `mcp` library.
> See the full explanation in the [Python Integration Guide](./PYTHON.md).

Create a minimal Python agent using the MCP client pattern (see [PYTHON.md](./PYTHON.md) for the full reference):

```python
#!/usr/bin/env python3
"""agent.py - Minimal Memento agent via MCP client. Requires: pip install mcp"""

import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server_params = StdioServerParameters(command="memento", args=["--profile", "extended"])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Store a memory
            result = await session.call_tool(
                "store_memento",
                arguments={"type": "solution", "title": "API timeout fix",
                           "content": "Increased timeout to 30 s and added retry logic.",
                           "tags": ["api", "timeout"], "importance": 0.8},
            )
            print(json.loads(result.content[0].text))

            # Recall memories
            result = await session.call_tool(
                "recall_mementos",
                arguments={"query": "API timeout", "limit": 5},
            )
            for m in json.loads(result.content[0].text):
                print(f"- {m['title']}: {m.get('content', '')[:80]}")


if __name__ == "__main__":
    asyncio.run(main())
```

For a more complete implementation (interactive REPL, error handling, multiple commands)
see the [Python Integration Guide](./PYTHON.md).

### Shell Script Agent

> **⚠️ Note**: Memento is an MCP server that requires a proper MCP initialization
> handshake before accepting tool calls. Raw JSON-RPC piping without that handshake
> will not work. For shell-based automation use the Python MCP client pattern
> (see [Python Integration Guide](./PYTHON.md)) or the CLI export/import commands
> which bypass MCP entirely.

For simple backup/search automation without MCP, use the CLI directly:

```bash
#!/usr/bin/env bash
# memento-agent.sh - Shell helper using Memento CLI (no MCP handshake needed)

export_memories() {
    memento export --format json --output "${1:-memories.json}"
    echo "Exported to ${1:-memories.json}"
}

import_memories() {
    memento import --format json --input "$1" ${2:+--skip-duplicates}
    echo "Imported from $1"
}

case "$1" in
    export) export_memories "$2" ;;
    import) import_memories "$2" "--skip-duplicates" ;;
    *)
        echo "Usage: $0 export [output.json]"
        echo "       $0 import <input.json>"
        echo ""
        echo "For MCP tool calls (store/search) from a shell script, use the"
        echo "Python MCP client pattern instead (see docs/integrations/PYTHON.md)."
        ;;
esac
```

```bash
chmod +x memento-agent.sh
./memento-agent.sh export memories-backup.json
./memento-agent.sh import memories-backup.json
```

## Troubleshooting Common Issues

### MCP Server Not Starting
1. **Verify Memento installation**:
   ```bash
   memento --version
   which memento
   ```

2. **Test MCP communication**:
   ```bash
   echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | memento
   ```

3. **Check permissions**:
   ```bash
   ls -la ~/.mcp-memento/
   chmod 755 ~/.mcp-memento/
   ```

### Configuration File Issues
1. **JSON syntax errors**:
   ```bash
   # Validate JSON
   python3 -m json.tool < config.json
   ```

2. **File location incorrect**:
   - Gemini CLI: `~/.gemini/config.json`
   - Claude Desktop: see [IDE Integration Guide](./IDE.md)
   - Verify file exists and is readable

### Path Issues
1. **Use full paths** in configuration files:
   ```json
   {
     "command": "/Users/yourname/.local/bin/memento"
   }
   ```

2. **Add to PATH**:
   ```bash
   # Add pipx bin to PATH
   export PATH="$HOME/.local/bin:$PATH"
   ```

### Database Issues
1. **Corrupted database**:
   ```bash
   # Backup and recreate
   cp ~/.mcp-memento/context.db ~/.mcp-memento/context.db.backup
   rm ~/.mcp-memento/context.db
   ```

2. **Disk space**:
   ```bash
   # Check database size
   du -h ~/.mcp-memento/context.db
   ```

## Best Practices

### Configuration Management
1. **Use environment variables** for sensitive paths
2. **Version control** your custom scripts
3. **Document** configurations for team members
4. **Test** configurations before relying on them

### Memory Management
1. **Regular backup**:
   ```bash
   # Export memories (--format is required)
   memento export --format json --output memories-backup.json
   ```

2. **Review low-confidence memories** periodically via your AI assistant:
   ```
   memento: get_low_confidence_mementos
   ```

3. **Clean up old memories** periodically

### Performance Optimization
1. **Use appropriate profile**:
   - `core`: Basic operations
   - `extended`: Most users
   - `advanced`: Power users with large memory databases

2. **Monitor database growth**:
   ```bash
   # Check size monthly
   du -h ~/.mcp-memento/context.db
   ```

3. **Archive inactive projects**:
   ```bash
   # Export all memories (filtering by tag is not supported by the CLI;
   # use get_low_confidence_mementos or delete_memento via MCP to clean up)
   memento export --format json --output project-archive.json
   ```

## Next Steps

- Explore [IDE Integration Guide](./IDE.md) for editor setups
- Review [Python Integration Guide](./PYTHON.md) for programmatic MCP client access
- Check [Tools Reference](../TOOLS.md) for complete tool documentation
- See [Usage Rules](../RULES.md) for best practices and conventions

Need help? Check the [Memento documentation](../README.md) or open an issue on GitHub.
