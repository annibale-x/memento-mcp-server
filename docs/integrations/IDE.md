# IDE Integration Guide

This guide covers how to integrate Memento with various Integrated Development Environments (IDEs) and code editors that support the Model Context Protocol (MCP).

## Table of Contents
- [Quick Start](#quick-start)
- [Zed Editor](#zed-editor)
- [Cursor](#cursor)
- [Windsurf](#windsurf)
- [VSCode](#vscode)
- [Claude Desktop](#claude-desktop)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Quick Start

### Prerequisites
1. Install Memento:
   ```bash
   pipx install mcp-memento
   ```

2. Choose your IDE from the list below
3. Configure using the provided examples
4. Restart your IDE to apply changes

### Configuration Hierarchy
Memento supports multiple configuration sources (in order of precedence):
1. **Environment Variables** (highest priority)
2. **IDE-specific configuration files**
3. **Project-local configuration files**
4. **Global configuration files**
5. **Default values** (lowest priority)

## Zed Editor

### Overview
Zed is a high-performance, multiplayer code editor with native MCP support. Memento integrates seamlessly to provide contextual memory across your coding sessions.

### Configuration
Add to `~/.config/zed/settings.json`:

```json
{
  "context_servers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "extended"],
      "env": {
        "MEMENTO_SQLITE_PATH": "~/.mcp-memento/context.db",
        "MEMENTO_TOOL_PROFILE": "extended"
      }
    }
  }
}
```

### Features in Zed
- **Inline Context**: Get relevant past solutions while coding
- **Command Palette**: Access Memento tools via `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)
- **Project Memory**: Maintain context across different projects
- **Real-time Search**: Find patterns and solutions without leaving the editor

### Usage Examples

#### 1. Store a Solution
While fixing a bug, ask your AI assistant:
```
Store this Redis timeout fix in Memento with tags "redis", "timeout", "production"
```

#### 2. Search for Patterns
When implementing a new feature:
```
Search Memento for authentication patterns using JWT
```

#### 3. Get Project History
When returning to a project:
```
What have we previously implemented for database migrations in this project?
```

### Advanced Configuration
```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "advanced", "--log-level", "INFO"],
      "env": {
        "MEMENTO_SQLITE_PATH": "~/projects/.memento/team.db",
        "MEMENTO_TOOL_PROFILE": "advanced",
        "MEMENTO_ENABLE_ADVANCED_TOOLS": "true",
        "MEMENTO_LOG_LEVEL": "INFO"
      },
      "cwd": "~/projects/current-project"
    }
  }
}
```

### Project-Specific Configuration
Create `.zed/settings.json` in your project root for team-specific settings:

```json
{
  "context_servers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "extended"],
      "env": {
        "MEMENTO_SQLITE_PATH": "./.memento/project.db",
        "MEMENTO_TOOL_PROFILE": "extended"
      }
    }
  }
}
```

## Cursor

### Overview
Cursor is an AI-powered code editor that deeply integrates with MCP. Memento enhances Cursor's capabilities by providing persistent memory across sessions.

### Configuration
Create or edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "core"]
    }
  }
}
```

### Features in Cursor
- **Session Persistence**: Cursor remembers solutions across restarts
- **Pattern Suggestions**: Get code suggestions based on past successful patterns
- **Team Knowledge Base**: Share solutions across team members
- **Context-Aware Completions**: Better completions based on project history

### Usage Tips

#### 1. Store Solutions as You Work
After fixing a bug or implementing a feature:
```
@cursor Please store this solution in Memento as a memory with type "solution"
```

#### 2. Search Before Implementing
When starting a new task:
```
@cursor Search Memento for how we've handled file uploads in the past
```

#### 3. Connect Related Concepts
When working on related features:
```
@cursor Connect this API rate limiting solution to our authentication system in Memento
```

### Project-Specific Configuration
Create `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "extended"],
      "env": {
        "MEMENTO_SQLITE_PATH": "./.cursor/memento.db",
        "MEMENTO_TOOL_PROFILE": "extended"
      }
    }
  }
}
```

### Advanced Features
```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "advanced"],
      "env": {
        "MEMENTO_SQLITE_PATH": "~/.cursor/memento/context.db",
        "MEMENTO_TOOL_PROFILE": "advanced",
        "MEMENTO_ENABLE_ADVANCED_TOOLS": "true"
      }
    },
    "other-server": {
      "command": "other-mcp-server"
    }
  }
}
```

## Windsurf

### Overview
Windsurf is a modern code editor with AI integration. Memento provides persistent memory capabilities to enhance Windsurf's AI features.

### Configuration
Create or edit `~/.windsurf/mcp.json`:

```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "extended"]
    }
  }
}
```

### Features in Windsurf
- **Conversation Memory**: Maintain context across chat sessions
- **Solution Recall**: Remember how you solved similar problems
- **Decision Tracking**: Document architecture decisions
- **Cross-Project Insights**: Share knowledge across different projects

### Best Practices

#### 1. Use Descriptive Titles
When storing memories:
```
Store this with title "Authentication: JWT implementation with refresh tokens"
```

#### 2. Consistent Tagging
Use consistent tags for better search:
- `authentication`, `jwt`, `security`, `api`
- `database`, `postgres`, `migrations`, `optimization`
- `frontend`, `react`, `components`, `state-management`

#### 3. Set Appropriate Importance
- `0.9+`: Critical security fixes, production issues
- `0.7-0.8`: Important patterns, architecture decisions
- `0.5-0.6`: Useful tips, common patterns
- `0.3-0.4`: General knowledge, references

#### 4. Create Relationships
Connect related memories:
```
Connect this database optimization to our caching strategy
```

### Project Configuration
Create `.windsurf/mcp.json` in project root:

```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "extended"],
      "env": {
        "MEMENTO_SQLITE_PATH": "${workspaceFolder}/.windsurf/memento.db",
        "MEMENTO_TOOL_PROFILE": "extended"
      }
    }
  }
}
```

## VSCode

### Overview
Visual Studio Code can integrate with Memento through the MCP extension, providing memory capabilities within the popular editor.

### Installation
1. Install the [MCP Extension for VSCode](https://marketplace.visualstudio.com/items?itemName=modelcontextprotocol.vscode-mcp)
2. Configure in your VSCode `settings.json`:

```json
{
  "mcp": {
    "servers": {
      "memento": {
        "command": "memento",
        "args": ["--profile", "core"],
        "env": {
          "MEMENTO_SQLITE_PATH": "${env:HOME}/.vscode/memento.db"
        }
      }
    }
  }
}
```

### Features in VSCode
- **Command Palette Integration**: Access via `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (macOS)
- **Sidebar View**: Browse memories and relationships (if supported by extension)
- **Quick Fixes**: Get suggested solutions for errors
- **Documentation Integration**: Link code to relevant documentation memories

### Configuration Options

#### User Settings
Edit `~/.config/Code/User/settings.json`:

```json
{
  "mcp.servers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "extended", "--log-level", "WARNING"],
      "env": {
        "MEMENTO_SQLITE_PATH": "${env:HOME}/.vscode/memento/context.db",
        "MEMENTO_TOOL_PROFILE": "extended"
      },
      "disabled": false,
      "autoStart": true
    }
  }
}
```

#### Workspace Settings
Create `.vscode/settings.json` in your project:

```json
{
  "mcp.servers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "extended"],
      "env": {
        "MEMENTO_SQLITE_PATH": "${workspaceFolder}/.vscode/memento.db",
        "MEMENTO_TOOL_PROFILE": "extended"
      }
    }
  }
}
```

### Usage Patterns

#### 1. Through AI Extensions
If using GitHub Copilot or other AI extensions:
- The AI will automatically use Memento for context
- Store solutions as you work
- Search for patterns when stuck

#### 2. Direct Tool Usage
Use the command palette:
1. `Ctrl+Shift+P` → "MCP: Call Tool"
2. Select "memento" server
3. Choose tool (e.g., "recall_mementos")
4. Enter parameters

#### 3. Custom Keybindings
Add to `keybindings.json`:
```json
[
  {
    "key": "ctrl+shift+m",
    "command": "mcp.callTool",
    "args": {
      "server": "memento",
      "tool": "recall_mementos",
      "arguments": {
        "query": "current file context"
      }
    }
  }
]
```

## Claude Desktop

### Overview
Claude Desktop is Anthropic's desktop application for Claude AI. Memento integrates to provide persistent memory across conversations.

### Configuration
Add to Claude Desktop configuration:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`  
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "core"]
    }
  }
}
```

### Features with Claude
- **Conversation Memory**: Claude remembers past discussions and decisions
- **Project Context**: Maintain context across different projects and conversations
- **Solution Library**: Build a personal library of solutions and patterns
- **Learning Over Time**: Claude gets better as it learns from your work and decisions

### Usage Patterns

#### 1. Start a Session with Context
```
Load context from our previous discussion about authentication system design
```

#### 2. Store Important Insights
```
Save this authentication flow as a pattern in Memento with type "pattern" and tags "auth", "workflow"
```

#### 3. Search for Historical Solutions
```
What have we learned about database optimization in past projects?
```

#### 4. Connect Related Discussions
```
Connect this conversation about API design to our previous discussion about rate limiting
```

### Advanced Configuration
```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "extended"],
      "env": {
        "MEMENTO_SQLITE_PATH": "~/Claude/memento.db",
        "MEMENTO_TOOL_PROFILE": "extended",
        "MEMENTO_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Project-Specific Memory
For project-focused conversations, specify the project path:

```
Set Memento project path to ~/projects/ecommerce-app
```

This helps scope searches and keeps project memories organized.

## Troubleshooting

### Common Issues

#### 1. Server Won't Start
```bash
# Check installation
which memento

# Test basic functionality
memento --health

# Check permissions on database directory
ls -la ~/.mcp-memento/
```

#### 2. IDE Doesn't Recognize Memento
- Restart your IDE after configuration changes
- Check IDE logs for MCP errors
- Verify configuration file syntax (use JSON validator)
- Test with: `memento --list-tools`

#### 3. Slow Performance
```bash
# Run database maintenance
memento --maintenance

# Check database size
ls -lh ~/.mcp-memento/context.db

# Consider archiving old memories
memento export old_memories.json
```

#### 4. Memories Not Found in Search
- Try different search terms
- Use `recall_mementos` for fuzzy matching instead of `search_mementos`
- Check if memories have appropriate tags
- Verify the memory was actually stored (check with `get_memento`)

### Debug Mode
```bash
# Enable verbose logging
MEMENTO_LOG_LEVEL=DEBUG memento --profile core

# Or from IDE configuration
{
  "command": "memento",
  "args": ["--profile", "core", "--log-level", "DEBUG"]
}
```

### Checking MCP Connection
```bash
# Test MCP protocol communication
echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | memento
```

## Best Practices

### Configuration Management
1. **Use Environment Variables** for sensitive paths and settings
2. **Version Control** your configuration files (except sensitive data)
3. **Document** custom configurations for your team
4. **Test** configurations in development before deploying to production

### Performance Optimization
1. **Regular Maintenance**: Run `memento --maintenance` monthly
2. **Archive Old Data**: Export and remove very old, low-confidence memories
3. **Use Appropriate Profiles**: Don't use Advanced profile unless you need those tools
4. **Monitor Disk Usage**: Keep an eye on database size growth

### Team Collaboration
1. **Shared Database Location**: Use a shared location for team knowledge base
2. **Consistent Tagging Conventions**: Agree on tag naming conventions
3. **Regular Knowledge Reviews**: Monthly reviews of important memories
4. **Training Sessions**: Ensure team knows how to use Memento effectively

### Memory Management
1. **Descriptive Titles**: Use clear, searchable titles
2. **Structured Content**: Organize memory content with headers and lists
3. **Regular Cleanup**: Remove obsolete or low-confidence memories
4. **Relationship Building**: Connect related memories for better context

### IDE-Specific Tips
- **Zed**: Use project-specific configurations for team projects
- **Cursor**: Leverage @cursor commands for quick Memento operations
- **Windsurf**: Use consistent tagging for cross-project knowledge sharing
- **VSCode**: Configure workspace settings for project-specific memory
- **Claude Desktop**: Start conversations with context loading for continuity

---

**Need More Help?**
- Check the [Tools Reference](../TOOLS.md) for detailed tool usage
- Review [Python API Guide](../integrations/PYTHON.md) for programmatic access
- See [Agent Integration Guide](./AGENT.md) for CLI agent setups
- Open an issue on GitHub for bugs or feature requests