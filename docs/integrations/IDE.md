# IDE Integration Guide

This guide covers how to integrate Memento with various Integrated Development Environments (IDEs) and code editors that support the Model Context Protocol (MCP). Memento provides persistent memory capabilities to enhance your AI-assisted coding experience.

## Installation

Before configuring any IDE, install Memento:

```bash
# Install with pipx (recommended)
pipx install mcp-memento

# Or with pip
pip install mcp-memento

# Verify installation
memento --version
```

Memento uses SQLite for local storage by default. The database is automatically created at `~/.mcp-memento/context.db` unless configured otherwise.

## Supported IDEs

- [Zed Editor](#zed-editor) - High-performance, multiplayer code editor
- [Cursor](#cursor) - AI-powered code editor
- [Windsurf](#windsurf) - Modern code editor with AI integration
- [VSCode](#vscode) - Popular code editor via MCP extension
- [Claude Desktop](#claude-desktop) - Anthropic's desktop application

## Zed Editor

### Overview
Zed is a high-performance, multiplayer code editor with native MCP support. Memento integrates seamlessly to provide contextual memory across your coding sessions.

### Two Integration Modes

Memento supports two distinct integration modes for Zed:

| Mode | How | Best for |
|---|---|---|
| **Manual config** (PyPI) | Add `memento` command to `settings.json` | macOS / Linux — `memento` is in PATH |
| **Zed Extension** | Install "Memento MCP Server" from Zed marketplace | Windows (avoids stdin buffering issue) or any platform where you prefer a managed install |

> **Windows note**: Zed on Windows launches context server processes via PowerShell's
> `ShellBuilder`, which can cause stdin buffering issues when using the manual config
> approach. The dedicated Zed extension (a native Rust stub + WASM component) solves
> this transparently. If the manual configuration does not work on Windows, use the
> Zed extension instead.

### Configuration (Manual / PyPI install)

Add to `~/.config/zed/settings.json`:

```json
{
  "context_servers": {
    "memento": {
      "command": "memento",
      "args": []
    }
  }
}
```

### Configuration Methods
Memento supports multiple configuration approaches. For clarity, we recommend choosing **one method consistently**:

**Method A: CLI Arguments** (recommended - most explicit)
```json
{
  "context_servers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "extended", "--db", "~/.zed-memento/context.db", "--log-level", "INFO"]
    }
  }
}
```

**Method B: Environment Variables**
```json
{
  "context_servers": {
    "memento": {
      "command": "memento",
      "args": [],
      "env": {
        "MEMENTO_PROFILE": "extended",
        "MEMENTO_DB_PATH": "~/.zed-memento/context.db",
        "MEMENTO_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Method C: YAML Configuration File**
Create `~/.mcp-memento/config.yaml`:
```yaml
profile: extended
db_path: ~/.zed-memento/context.db
logging:
  level: INFO
```
Then use minimal JSON config:
```json
{
  "context_servers": {
    "memento": {
      "command": "memento",
      "args": []
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
- **User-level**: `~/.config/zed/settings.json` (affects all projects)
- Zed will automatically load this configuration on startup

### Usage Examples

Once configured, restart Zed. In the chat interface:

```
What memory tools do you have available?
```

```
Store this pattern for later: API endpoints should follow RESTful conventions
```

```
What do you remember about RESTful API design?
```

### Troubleshooting

**Server not appearing:**
1. Check Zed version supports MCP
2. Verify `~/.config/zed/settings.json` has valid JSON syntax
3. Test Memento manually: `memento --health`

**Permission issues:**
```bash
# Ensure database directory exists
mkdir -p ~/.mcp-memento
chmod 755 ~/.mcp-memento
```

## Cursor

### Overview
Cursor is an AI-powered code editor that deeply integrates with MCP. Memento enhances Cursor's capabilities by providing persistent memory across sessions.

### Prerequisites
- Cursor version with MCP support
- **Important**: MCP tools require **Agent mode** in Cursor

### Configuration

Create or edit `.cursor/mcp.json` in your project root:

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

For global configuration (all projects), create `~/.cursor/mcp.json`.

### Where to Save Configuration
- **Project-specific**: `.cursor/mcp.json` in project root (recommended for teams)
- **Global**: `~/.cursor/mcp.json` (affects all projects)

### Usage with Agent Mode

MCP tools only work in **Agent mode**:

1. Open Cursor Chat
2. Click the mode selector at bottom of chat panel
3. Select **Agent** mode
4. Now you can use Memento tools:

```
@cursor Search Memento for authentication patterns we've used before
```

```
@cursor Store this solution in Memento: Fixed memory leak in WebSocket handler
```

### Advanced Configuration

```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "extended", "--db", "./.cursor/memento.db", "--log-level", "WARNING"],
      "env": {}
    }
  }
}
```

### Troubleshooting

**Tools not appearing:**
1. Ensure you're in **Agent mode** (not Chat or Composer mode)
2. Restart Cursor after configuration changes
3. Check `.cursor/mcp.json` JSON syntax

**Agent mode not available:**
- Some Cursor versions require specific settings for Agent mode
- Check Cursor documentation for current requirements

## Windsurf

### Overview
Windsurf is a modern code editor with AI integration. Memento provides persistent memory capabilities to enhance Windsurf's AI features.

### Configuration

Windsurf configuration varies by operating system:

**macOS**: `~/Library/Application Support/Windsurf/mcp.json`
**Linux**: `~/.config/Windsurf/mcp.json`
**Windows**: `%APPDATA%\Windsurf\mcp.json`

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

### Project-Specific Configuration

Create `.windsurf/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": ["--db", "./.windsurf/memento.db"],
      "env": {}
    }
  }
}
```

### Where to Save Configuration
- **User-level**: OS-specific location (see above)
- **Project-specific**: `.windsurf/mcp.json` in project root

### Usage Examples

Once configured, restart Windsurf. In the AI chat:

```
What memory capabilities do you have?
```

```
Remember that this project uses TypeScript with strict mode enabled
```

```
What coding standards should I follow for this project?
```

### Advanced Features

```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "extended", "--db", "~/.windsurf-memento/context.db"],
      "env": {}
    }
  }
}
```

### Troubleshooting

**Configuration not loading:**
1. Verify file exists at correct OS location
2. Check JSON syntax
3. Restart Windsurf completely (not just reload window)

**Path issues:**
```json
{
  "command": "/Users/yourname/.local/bin/memento"
}
```

## VSCode

### Overview
Visual Studio Code can integrate with Memento through the MCP extension, providing memory capabilities within the popular editor.

### Prerequisites
- **VS Code 1.99+** (MCP support added in this release; use `1.100+` for the stable GA build)
- **MCP Extension for VSCode** installed

### Configuration

Create `.vscode/mcp.json` in your workspace root:

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

For user-level configuration (all workspaces), create at:
- **macOS/Linux**: `~/.vscode/mcp.json`
- **Windows**: `%USERPROFILE%\.vscode\mcp.json`

### Starting the MCP Server

1. Open VS Code
2. Open Command Palette (`Cmd/Ctrl + Shift + P`)
3. Run: **MCP: List Servers**
4. Find `memento` and click **Start**

### Where to Save Configuration
- **Workspace-specific**: `.vscode/mcp.json` in project root (recommended)
- **User-level**: `~/.vscode/mcp.json` (all workspaces)

### Usage with GitHub Copilot

MCP tools work with GitHub Copilot in **Agent mode**:

1. Open Copilot Chat (`Cmd/Ctrl + Shift + I`)
2. Use `@workspace` prefix or switch to **Agent** mode
3. Now you can use Memento:

```
@workspace Store this API endpoint pattern in Memento
```

```
@workspace What authentication patterns have we used before?
```

### Advanced Configuration

```json
{
  "mcpServers": {
    "memento": {
      "command": "memento",
      "args": ["--profile", "extended", "--db", "${workspaceFolder}/.vscode/memento.db"],
      "env": {}
    }
  }
}
```

### Troubleshooting

**MCP servers not available:**
1. Check VS Code version is 1.99+ (1.100+ recommended)
2. Verify MCP extension is installed and enabled
3. Command Palette > **MCP: List Servers** to check status

**Server won't start:**
1. Test Memento manually: `memento --version`
2. Use full path in configuration:
   ```json
   {
     "command": "/Users/yourname/.local/bin/memento"
   }
   ```

**Tools not appearing in chat:**
1. Must use Agent mode or `@workspace` prefix
2. Restart MCP server: Command Palette > **MCP: Restart Server**

## Claude Desktop

### Overview
Claude Desktop is Anthropic's desktop application for Claude AI. Memento integrates to provide persistent memory across conversations.

### Configuration

Claude Desktop configuration varies by operating system:

**macOS:**
```bash
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

### Important: Path Restriction
Claude Desktop has a restricted PATH. You may need to use the full path to Memento:

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

After configuration, **completely quit and restart Claude Desktop** (not just close window). Then in a new conversation:

```
What memory tools do you have available?
```

```
Store this for later: Our deployment process requires approval from two team members
```

```
What's our deployment approval process?
```

### Advanced Configuration

```json
{
  "mcpServers": {
    "memento": {
      "command": "/Users/yourname/.local/bin/memento",
      "args": ["--profile", "extended", "--db", "~/Claude/memento.db", "--log-level", "INFO"],
      "env": {}
    }
  }
}
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

## Troubleshooting Common Issues

### Memento Not Found

**Issue**: IDE reports "command not found" or similar error.

**Solutions**:
1. Verify installation:
   ```bash
   which memento
   memento --version
   ```

2. Use full path in configuration:
   ```json
   {
     "command": "/Users/yourname/.local/bin/memento"
   }
   ```

3. Ensure pipx bin is in PATH:
   ```bash
   # Add to shell profile (.bashrc, .zshrc, etc.)
   export PATH="$HOME/.local/bin:$PATH"
   ```

### Configuration File Issues

**Issue**: Configuration not loading or syntax errors.

**Solutions**:
1. Validate JSON syntax:
   ```bash
   python3 -m json.tool < config.json
   ```

2. Check file location:
   - Zed: `~/.config/zed/settings.json`
   - Cursor: `.cursor/mcp.json` or `~/.cursor/mcp.json`
   - Windsurf: OS-specific (see above)
   - VSCode: `.vscode/mcp.json` or `~/.vscode/mcp.json`
   - Claude Desktop: OS-specific (see above)

### Server Not Starting

**Issue**: MCP server fails to start or immediately crashes.

**Solutions**:
1. Test Memento standalone:
   ```bash
   memento --health
   ```

2. Check database permissions:
   ```bash
   mkdir -p ~/.mcp-memento
   chmod 755 ~/.mcp-memento
   ```

3. Test MCP communication:
   ```bash
   echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | memento
   ```

### Tools Not Appearing

**Issue**: Memento tools don't appear in AI chat.

**Solutions**:
1. **Cursor/Windsurf**: Ensure you're in **Agent mode**
2. **VSCode**: Use `@workspace` prefix or Agent mode
3. Restart the MCP server
4. Reload IDE window
5. Check IDE logs for MCP errors

### Database Issues

**Issue**: Slow performance or corruption.

**Solutions**:
1. Check database size:
   ```bash
   du -h ~/.mcp-memento/context.db
   ```

2. Backup and recreate if corrupted:
   ```bash
   cp ~/.mcp-memento/context.db ~/.mcp-memento/context.db.backup
   rm ~/.mcp-memento/context.db
   ```

## Best Practices

### Configuration Management

1. **Use project-specific configurations** for team projects
2. **Version control** your `.cursor/mcp.json` or `.vscode/mcp.json` files
3. **Document** configurations for team members
4. **Test** configurations before sharing with team

### Memory Management

1. **Backup important memories**:
   ```bash
   # Export memories to JSON (use --format, required)
   memento export --format json --output memories-backup.json
   ```

3. **Use appropriate profiles**:
   - `core`: Basic memory operations
   - `extended`: Most users (adds analytics)
   - `advanced`: Power users with large databases

### IDE-Specific Tips

**Zed**:
- Use project-specific configurations for different codebases
- Leverage Zed's multiplayer features for team knowledge sharing

**Cursor**:
- Always use Agent mode for memory operations
- Store patterns as you discover them
- Query before implementing new features

**Windsurf**:
- Use consistent tagging for cross-project knowledge
- Store architectural decisions as you make them

**VSCode**:
- Configure at workspace level for project-specific memory
- Combine with GitHub Copilot for enhanced AI assistance

**Claude Desktop**:
- Use full paths in configuration
- Store context between different conversation topics
- Build up project knowledge over multiple sessions

### Performance Optimization

1. **Monitor database growth**:
   ```bash
   # Check size periodically
   du -h ~/.mcp-memento/context.db
   ```

2. **Archive inactive projects**:
   ```bash
   # Export old project memories (--format is required)
   memento export --format json --output old-project.json
   ```

3. **Use appropriate profile** for your needs

## Next Steps

- Explore [Agent Integration Guide](./AGENT.md) for CLI tool setups
- Review [Python Integration Guide](./PYTHON.md) for programmatic access
- Check [Tools Reference](../TOOLS.md) for complete tool documentation
- See [Usage Rules](../RULES.md) for best practices and conventions

For additional help, check the [Memento documentation](../README.md) or open an issue on GitHub.
