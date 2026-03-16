# Integration Guide

This guide covers how to integrate Context Keeper with various IDEs, editors, and AI agents.

## Table of Contents
- [Quick Start](#quick-start)
- [Zed Editor](#zed-editor)
- [Cursor](#cursor)
- [Windsurf](#windsurf)
- [VSCode](#vscode)
- [Claude Desktop](#claude-desktop)
- [Gemini CLI](#gemini-cli)
- [Custom Agents](#custom-agents)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites
1. Install Context Keeper:
   ```bash
   pipx install mcp-memento
   ```

2. Choose your integration method:
   - **IDEs**: Zed, Cursor, Windsurf, VSCode
   - **Desktop Apps**: Claude Desktop
   - **CLI Agents**: Gemini CLI, custom scripts

3. Configure your tool profile:
   - **Core** (13 tools): Recommended for most users
   - **Extended** (17 tools): Power users with analytics needs
   - **Advanced** (25 tools): Administrators and developers

## Zed Editor

### Configuration
Add to `~/.config/zed/settings.json`:

```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "extended"],
      "env": {
        "CONTEXT_SQLITE_PATH": "~/.mcp-memento/context.db",
        "CONTEXT_TOOL_PROFILE": "extended"
      }
    }
  }
}
```

### Features in Zed
- **Inline suggestions**: Get relevant past solutions while coding
- **Command palette**: Access Context Keeper tools via `Cmd+Shift+P`
- **Context awareness**: AI assistant remembers your project history
- **Quick search**: Find patterns and solutions without leaving the editor

### Usage Example
1. Open Zed and start coding
2. When you encounter a problem, ask your AI assistant:
   ```
   Have we solved similar database timeout issues before?
   ```
3. The assistant will search Context Keeper and provide relevant solutions

### Advanced Configuration
```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "advanced", "--log-level", "INFO"],
      "env": {
        "CONTEXT_SQLITE_PATH": "~/projects/.context/team.db",
        "CONTEXT_TOOL_PROFILE": "advanced",
        "CONTEXT_ENABLE_ADVANCED_TOOLS": "true"
      }
    }
  }
}
```

## Cursor

### Configuration
Create or edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "context-keeper": {
      "command": "memento",
      "args": ["--profile", "core"]
    }
  }
}
```

### Features in Cursor
- **Project memory**: Cursor remembers solutions across sessions
- **Pattern recognition**: Suggests established patterns for common tasks
- **Team knowledge**: Share solutions across team members
- **Code generation**: Generate code based on past successful patterns

### Usage Tips
1. **Store solutions as you work**:
   ```python
   # After fixing a bug, ask Cursor:
   "Store this solution in Context Keeper as a memory"
   ```

2. **Search before implementing**:
   ```python
   "Search Context Keeper for authentication patterns"
   ```

3. **Connect related concepts**:
   ```python
   "Connect this database optimization to our caching strategy"
   ```

### Project-Specific Configuration
Create `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "context-keeper": {
      "command": "memento",
      "args": ["--profile", "extended"],
      "env": {
        "CONTEXT_SQLITE_PATH": "./.cursor/context.db"
      }
    }
  }
}
```

## Windsurf

### Configuration
Create or edit `~/.windsurf/mcp.json`:

```json
{
  "mcpServers": {
    "context-keeper": {
      "command": "memento",
      "args": ["--profile", "core"]
    }
  }
}
```

### Features in Windsurf
- **Context persistence**: Maintain conversation context across sessions
- **Solution recall**: Remember how you solved similar problems
- **Decision tracking**: Document architecture decisions
- **Knowledge sharing**: Share insights across different projects

### Best Practices
1. **Use descriptive titles** when storing memories
2. **Tag consistently** for better search results
3. **Set appropriate importance** levels
4. **Create relationships** between related memories

## VSCode

### Installation
1. Install the [MCP Extension](https://marketplace.visualstudio.com/items?itemName=modelcontextprotocol.vscode-mcp) for VSCode
2. Configure in `settings.json`:

```json
{
  "mcp": {
    "servers": {
      "context-keeper": {
        "command": "memento",
        "args": ["--profile", "core"],
        "env": {
          "CONTEXT_SQLITE_PATH": "${env:HOME}/.vscode/context.db"
        }
      }
    }
  }
}
```

### Features in VSCode
- **Command palette integration**: Access via `Ctrl+Shift+P`
- **Sidebar view**: Browse memories and relationships
- **Quick fixes**: Get suggested solutions for errors
- **Documentation integration**: Link code to relevant documentation

### Extension Configuration
For more control, use a dedicated configuration file:

```json
{
  "mcp.servers": {
    "context-keeper": {
      "command": "memento",
      "args": ["--profile", "extended", "--log-level", "WARNING"],
      "env": {
        "CONTEXT_SQLITE_PATH": "${workspaceFolder}/.vscode/context.db",
        "CONTEXT_TOOL_PROFILE": "extended"
      },
      "disabled": false,
      "autoStart": true
    }
  }
}
```

## Claude Desktop

### Configuration
Add to Claude Desktop configuration:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "context-keeper": {
      "command": "memento",
      "args": ["--profile", "core"]
    }
  }
}
```

### Features with Claude
- **Conversation memory**: Claude remembers past discussions
- **Project context**: Maintain context across different projects
- **Solution library**: Build a personal library of solutions
- **Learning over time**: Claude gets better as it learns from your work

### Usage Patterns
1. **Start a session**:
   ```
   "Load context from our previous discussion about authentication"
   ```

2. **Store insights**:
   ```
   "Save this authentication flow as a pattern in Context Keeper"
   ```

3. **Search for help**:
   ```
   "What have we learned about database optimization?"
   ```

## Gemini CLI

### Installation and Setup
1. Install Context Keeper:
   ```bash
   pipx install mcp-memento
   ```

2. Configure Gemini CLI to use MCP servers

### Basic Usage
```bash
# Start Gemini CLI with Context Keeper
gemini --mcp-servers memento

# Or specify custom configuration
gemini --mcp-servers 'memento --profile extended'
```

### Integration Script
Create a wrapper script `gemini-with-context`:

```bash
#!/bin/bash
# ~/bin/gemini-with-context

export CONTEXT_SQLITE_PATH="${CONTEXT_SQLITE_PATH:-~/.gemini-context/context.db}"
export CONTEXT_TOOL_PROFILE="${CONTEXT_TOOL_PROFILE:-extended}"

# Start Context Keeper server in background
memento --profile "$CONTEXT_TOOL_PROFILE" &
CONTEXT_PID=$!

# Wait for server to start
sleep 2

# Start Gemini CLI
gemini --mcp-servers memento "$@"

# Cleanup
kill $CONTEXT_PID
```

### Usage Examples
```bash
# Store a solution from terminal output
gemini "Take this solution and store it in Context Keeper: $(cat solution.txt)"

# Search for patterns
gemini "Search Context Keeper for Redis caching patterns"

# Get project history
gemini "What have we done with this codebase before?"
```

## Custom Agents

### Python Integration
```python
import asyncio
from memento import Memento

class CustomAgent:
    def __init__(self):
        self.keeper = None
    
    async def start(self):
        """Initialize Context Keeper."""
        self.keeper = Memento()
        await self.keeper.initialize()
    
    async def process_query(self, query: str):
        """Process a query using Context Keeper."""
        # Search for relevant memories
        tools = self.keeper.tools
        memories = await tools["recall_persistent_memories"](
            query=query,
            limit=5
        )
        
        # Use memories to inform response
        context = self._build_context(memories)
        response = await self._generate_response(query, context)
        
        # Store the interaction
        await self._store_interaction(query, response, memories)
        
        return response
    
    async def _store_interaction(self, query: str, response: str, memories: list):
        """Store the interaction in Context Keeper."""
        db = self.keeper.memory_db
        
        interaction_id = await db.store_memory(
            type="conversation",
            title=f"Query: {query[:50]}...",
            content=f"Q: {query}\n\nA: {response}",
            tags=["interaction", "auto-stored"],
            importance=0.3
        )
        
        # Link to relevant memories
        for memory in memories[:3]:
            await db.create_relationship(
                from_memory_id=interaction_id,
                to_memory_id=memory["id"],
                relationship_type="REFERENCES",
                confidence=0.7
            )
    
    async def stop(self):
        """Cleanup resources."""
        if self.keeper:
            await self.keeper.cleanup()

# Usage
async def main():
    agent = CustomAgent()
    await agent.start()
    
    response = await agent.process_query("How do we handle database migrations?")
    print(response)
    
    await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### Node.js Integration
```javascript
// Using child_process to run Context Keeper
const { spawn } = require('child_process');
const { Readable } = require('stream');

class MementoClient {
  constructor() {
    this.server = null;
  }

  start() {
    return new Promise((resolve, reject) => {
      this.server = spawn('memento', ['--profile', 'core']);
      
      this.server.stdout.on('data', (data) => {
        console.log(`Context Keeper: ${data}`);
      });
      
      this.server.stderr.on('data', (data) => {
        console.error(`Context Keeper error: ${data}`);
      });
      
      this.server.on('close', (code) => {
        console.log(`Context Keeper exited with code ${code}`);
      });
      
      // Wait for server to be ready
      setTimeout(resolve, 2000);
    });
  }

  stop() {
    if (this.server) {
      this.server.kill();
    }
  }

  async queryMemories(query) {
    // Use MCP client library or HTTP interface
    // This is a simplified example
    const response = await this._sendMCPRequest({
      method: "tools/call",
      params: {
        name: "recall_persistent_memories",
        arguments: {
          query: query,
          limit: 10
        }
      }
    });
    
    return response;
  }
}
```

### HTTP API Integration
Context Keeper can be exposed as an HTTP server for remote access:

```bash
# Start HTTP server (requires custom setup)
memento --http --port 8080 --host 0.0.0.0
```

Then connect from any HTTP client:

```python
import requests
import json

class RemoteMemento:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
    
    def search(self, query, limit=10):
        response = requests.post(
            f"{self.base_url}/search",
            json={"query": query, "limit": limit}
        )
        return response.json()
    
    def store(self, memory_data):
        response = requests.post(
            f"{self.base_url}/memories",
            json=memory_data
        )
        return response.json()
```

## Troubleshooting

### Common Issues

**1. Server won't start**
```bash
# Check installation
which memento

# Test basic functionality
memento --health

# Check permissions
ls -la ~/.mcp-memento/
```

**2. IDE doesn't recognize the server**
- Restart the IDE after configuration changes
- Check IDE logs for MCP errors
- Verify the configuration file syntax
- Test with `memento --list-tools`

**3. Slow performance**
```bash
# Run maintenance
memento --maintenance

# Check database size
ls -lh ~/.mcp-memento/context.db

# Consider archiving old memories
```

**4. Memory not found in search**
- Try different search terms
- Use `recall_persistent_memories` for fuzzy matching
- Check if memories have appropriate tags
- Verify the memory was actually stored

### Debug Mode
```bash
# Enable verbose logging
CONTEXT_LOG_LEVEL=DEBUG memento --profile core

# Or from IDE configuration
{
  "command": "memento",
  "args": ["--profile", "core", "--log-level", "DEBUG"]
}
```

### Getting Help
1. Check the [Tools Reference](TOOLS.md) for tool usage
2. Review [Confidence System](DECAY_SYSTEM.md) documentation
3. Look at [Python API](PYTHON_API.md) for programmatic access
4. Open an issue on GitHub for bugs or feature requests

## Best Practices

### Configuration Management
1. **Use environment variables** for sensitive paths
2. **Version control** your configuration files
3. **Document** custom configurations for your team
4. **Test** configurations in development first

### Performance Optimization
1. **Regular maintenance**: Run `--maintenance` monthly
2. **Archive old data**: Export and remove very old memories
3. **Use appropriate profiles**: Don't use Advanced unless needed
4. **Monitor disk usage**: Keep an eye on database size

### Team Collaboration
1. **Shared database**: Use a shared location for team knowledge
2. **Consistent tagging**: Agree on tag conventions
3. **Regular reviews**: Monthly knowledge base reviews
4. **Training**: Ensure team knows how to use the system

---

**Need more help?** Check the [main documentation](../README.md) or open an issue on GitHub.