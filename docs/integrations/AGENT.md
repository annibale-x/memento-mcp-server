# Agent Integration Guide

This guide covers how to integrate Memento with various AI agents and CLI tools that support the Model Context Protocol (MCP). Memento provides persistent memory capabilities to enhance your AI workflows across different platforms.

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
- [Claude Desktop](#claude-desktop) - Anthropic's desktop application (included here as it's agent-based)

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

### Where to Save Configuration
- **Shell profile**: `~/.bashrc`, `~/.zshrc`, etc. for environment variables
- **Custom scripts**: `~/bin/` directory for wrapper scripts
- Claude CLI doesn't have a persistent config file for MCP servers

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

## Claude Desktop

### Prerequisites
- **Claude Desktop** app installed ([Download](https://claude.ai/desktop))
- Latest version with MCP support

### Configuration

Claude Desktop configuration varies by operating system:

**macOS:**
```bash
# Open configuration file
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Linux:**
```bash
nano ~/.config/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**Configuration content:**
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

**Important**: Claude Desktop has a restricted PATH. You may need to use the full path to Memento:

```bash
# Find Memento installation path
which memento
# Returns: /Users/yourname/.local/bin/memento
```

Then use the full path in configuration:
```json
{
  "mcpServers": {
    "memento": {
      "command": "/Users/yourname/.local/bin/memento",
      "args": []
    }
  }
}
```

### Where to Save Configuration
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### Usage Examples

Once configured, restart Claude Desktop completely (not just close the window). Then in a new conversation:

```
What memory tools do you have available?
```

```
Store this for later: Our deployment script is in /scripts/deploy.sh
```

```
What do you remember about deployment scripts?
```

### Troubleshooting

**"spawn memento ENOENT" error:**
This means Claude Desktop can't find the Memento command. Solutions:

1. **Use full path** (recommended):
   ```json
   {
     "command": "/Users/yourname/.local/bin/memento"
   }
   ```

2. **Create symlink** (requires sudo):
   ```bash
   sudo ln -s ~/.local/bin/memento /usr/local/bin/memento
   ```
   Then use `"command": "memento"` in config.

**Configuration not taking effect:**
1. Completely quit Claude Desktop (Cmd+Q on macOS, not just close window)
2. Wait a few seconds
3. Reopen Claude Desktop

**Tools not appearing:**
1. Check Claude Desktop logs for MCP errors
2. Test Memento manually: `memento --health`
3. Verify JSON syntax in configuration file

## Custom CLI Agents

### Python-based Agent

> **Architecture note**: Memento is an MCP server — its tools (`store_memento`,
> `recall_mementos`, etc.) are **not** callable as direct Python methods. All
> programmatic access happens through an MCP client session using the `mcp` library.
> See the full explanation in the [Python Integration Guide](./PYTHON.md).

Create a custom Python agent with Memento integration via the MCP client pattern:

```python
#!/usr/bin/env python3
"""
custom-agent.py - Custom CLI agent with Memento integration via MCP client.

Requires: pip install mcp
"""

import asyncio
import json
import sys
from typing import List

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class CustomAgent:
    def __init__(self, profile: str = "extended"):
        self.profile = profile
        self._session: ClientSession | None = None
        self._stack = None  # contextlib.AsyncExitStack, set in start()

    async def start(self):
        """Initialize the MCP client connection to a Memento server."""
        from contextlib import AsyncExitStack

        server_params = StdioServerParameters(
            command="memento",
            args=["--profile", self.profile],
            env=None,
        )

        self._stack = AsyncExitStack()
        read, write = await self._stack.enter_async_context(stdio_client(server_params))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        print(f"Custom agent started with Memento ({self.profile} profile)")

    async def process_command(self, command: str, args: List[str]) -> str:
        """Process a CLI command."""

        if command == "store":
            return await self._store_memory(args)

        elif command == "search":
            return await self._search_memories(args)

        elif command == "help":
            return self._show_help()

        else:
            return f"Unknown command: {command}"

    async def _store_memory(self, args: List[str]) -> str:
        """Store a memory from CLI arguments."""
        if len(args) < 3:
            return "Usage: store <type> <title> <content> [tags...]"

        memory_type = args[0]
        title = args[1]
        content = " ".join(args[2:])

        try:
            result = await self._session.call_tool(
                "store_memento",
                arguments={
                    "type": memory_type,
                    "title": title,
                    "content": content,
                    "tags": ["cli", "custom-agent"],
                    "importance": 0.7,
                },
            )
            data = json.loads(result.content[0].text)
            return f"Memory stored with ID: {data.get('memory_id', '?')}"

        except Exception as e:
            return f"Error storing memory: {e}"

    async def _search_memories(self, args: List[str]) -> str:
        """Search memories from CLI arguments."""
        if not args:
            return "Usage: search <query>"

        query = " ".join(args)

        try:
            result = await self._session.call_tool(
                "recall_mementos",
                arguments={"query": query, "limit": 5},
            )
            memories = json.loads(result.content[0].text)

            if not memories:
                return "No memories found"

            lines = []

            for i, memory in enumerate(memories, 1):
                lines.append(f"{i}. {memory['title']}")
                lines.append(f"   {memory.get('content', '')[:100]}...")
                lines.append(f"   Tags: {', '.join(memory.get('tags', []))}")
                lines.append("")

            return "\n".join(lines)

        except Exception as e:
            return f"Error searching memories: {e}"

    def _show_help(self) -> str:
        """Show help information."""
        return (
            "Available commands:\n"
            "  store <type> <title> <content>  Store a new memory\n"
            "  search <query>                  Search memories\n"
            "  help                            Show this help\n"
        )

    async def stop(self):
        """Clean up the MCP client connection."""
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
            self._session = None


async def main():
    """Main entry point."""
    agent = CustomAgent(profile="extended")

    try:
        await agent.start()

        if len(sys.argv) > 1:
            command = sys.argv[1]
            args = sys.argv[2:] if len(sys.argv) > 2 else []
            result = await agent.process_command(command, args)
            print(result)

        else:
            print("Custom Memento Agent (type 'exit' to quit)")

            while True:
                try:
                    user_input = input("> ").strip()

                    if not user_input:
                        continue

                    if user_input.lower() in ["exit", "quit", "q"]:
                        break

                    parts = user_input.split()
                    command = parts[0]
                    args = parts[1:] if len(parts) > 1 else []
                    result = await agent.process_command(command, args)
                    print(result)

                except KeyboardInterrupt:
                    print("\nExiting...")
                    break

                except EOFError:
                    print("\nExiting...")
                    break

    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

### Shell Script Agent
For simpler integration, create a shell script wrapper:

```bash
#!/bin/bash
# memento-agent.sh - Shell script agent with Memento integration

set -e

MEMENTO_DB="${MEMENTO_DB_PATH:-~/.mcp-memento/agent.db}"
MEMENTO_PROFILE="${MEMENTO_PROFILE:-extended}"

# Ensure database directory exists
mkdir -p "$(dirname "$MEMENTO_DB")"

# Function to store memory
store_memory() {
    local type="$1"
    local title="$2"
    shift 2
    local content="$*"
    
    echo "Storing memory: $title"
    
        # Use the Memento CLI to store via JSON-RPC
    printf '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"store_memento","arguments":{"type":"%s","title":"%s","content":"%s","tags":["shell-agent"],"importance":0.7}}}' \
        "$type" "$title" "$content" | memento --profile extended | python3 -m json.tool || echo "Error: Make sure memento is installed"
}

# Function to search memories
search_memories() {
    local query="$*"
    
    echo "Searching for: $query"
    
    printf '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"recall_mementos","arguments":{"query":"%s","limit":10}}}' \
        "$query" | memento --profile extended | python3 -c "
import sys, json
data = json.load(sys.stdin)
memories = json.loads(data.get('result', {}).get('content', [{}])[0].get('text', '[]'))
for i, m in enumerate(memories, 1):
    print(f'{i}. {m[\"title\"]}')
    print(f'   {m.get(\"content\",\"\")[:80]}...')
    print()
" || echo "Error: Make sure memento is installed"
}

# Function to show statistics
show_stats() {
    echo "Memory Statistics:"
    echo "Database: $MEMENTO_DB"
    
    if [ -f "$MEMENTO_DB" ]; then
        db_size=$(du -h "$MEMENTO_DB" | cut -f1)
        echo "Size: $db_size"
        
        # Count memories using sqlite3 if available
        if command -v sqlite3 >/dev/null 2>&1; then
            memory_count=$(sqlite3 "$MEMENTO_DB" "SELECT COUNT(*) FROM nodes;" 2>/dev/null || echo "N/A")
            echo "Total memories: $memory_count"
        fi
    else
        echo "Database file not found"
    fi
}

# Main command processing
case "$1" in
    store)
        if [ $# -lt 4 ]; then
            echo "Usage: $0 store <type> <title> <content>"
            exit 1
        fi
        store_memory "$2" "$3" "${@:4}"
        ;;
    search)
        if [ $# -lt 2 ]; then
            echo "Usage: $0 search <query>"
            exit 1
        fi
        search_memories "${@:2}"
        ;;
    stats)
        show_stats
        ;;
    help|--help|-h)
        echo "Memento Shell Agent"
        echo ""
        echo "Usage:"
        echo "  $0 store <type> <title> <content>  Store a new memory"
        echo "  $0 search <query>                  Search memories"
        echo "  $0 stats                           Show statistics"
        echo "  $0 help                            Show this help"
        echo ""
        echo "Environment variables:"
        echo "  MEMENTO_DB_PATH    Database location (default: ~/.mcp-memento/agent.db)"
        echo "  MEMENTO_PROFILE   Tool profile (default: extended)"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
```

Make it executable:
```bash
chmod +x memento-agent.sh
```

Usage:
```bash
# Store a memory
./memento-agent.sh store solution "Fixed API timeout" "Increased timeout to 30 seconds and added retry logic"

# Search memories
./memento-agent.sh search "API timeout"

# Show statistics
./memento-agent.sh stats
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
   - Claude Desktop: OS-specific location (see above)
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
   # Export project memories
   memento export --output project-archive.json --filter-tags "project:old-project"
   ```

## Next Steps

- Explore [IDE Integration Guide](./IDE.md) for editor setups
- Review [Python Integration Guide](./PYTHON.md) for programmatic MCP client access
- Check [Tools Reference](../TOOLS.md) for complete tool documentation
- See [Usage Rules](../RULES.md) for best practices and conventions

Need help? Check the [Memento documentation](../README.md) or open an issue on GitHub.
