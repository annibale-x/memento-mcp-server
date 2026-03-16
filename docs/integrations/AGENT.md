# Agent Integration Guide

This guide covers how to integrate Memento with various AI agents, CLI tools, and custom applications that support the Model Context Protocol (MCP).

## Configuration Methods

Memento supports multiple configuration methods with the following hierarchy (highest priority last):

### 1. Environment Variables (Highest Priority)
```bash
# Database location
export MEMENTO_SQLITE_PATH="~/.mcp-memento/context.db"

# Tool profile (core, extended, advanced)
export MEMENTO_TOOL_PROFILE="extended"

# Logging level
export MEMENTO_LOG_LEVEL="INFO"

# Advanced tools
export MEMENTO_ENABLE_ADVANCED_TOOLS="true"

# Allow relationship cycles
export MEMENTO_ALLOW_CYCLES="false"
```

### 2. YAML Configuration Files (Automatic Detection)
Memento automatically searches for configuration files in this order:

**Project Configuration** (`./memento.yaml` in current directory):
```yaml
sqlite_path: ~/.mcp-memento/context.db
tool_profile: extended
log_level: INFO
enable_advanced_tools: true
features:
  allow_relationship_cycles: false
```

**Global Configuration** (`~/.mcp-memento/config.yaml` in home directory):
```yaml
# Global settings for all projects
sqlite_path: ~/.mcp-memento/global.db
tool_profile: extended
log_level: INFO
```

### 3. CLI Arguments (Passed to MCP Server)
```bash
# Pass arguments directly to Memento server
gemini --mcp-servers 'memento --profile advanced --log-level DEBUG'

# Available CLI arguments:
# --profile core|extended|advanced
# --log-level DEBUG|INFO|WARNING|ERROR
# --sqlite-path /custom/path/db.sqlite
```

### Configuration Priority Summary
1. **Environment variables** - Highest priority, override everything
2. **Project YAML** (`./memento.yaml`) - Project-specific settings
3. **Global YAML** (`~/.mcp-memento/config.yaml`) - User-wide settings
4. **Default values** - Hardcoded in application

## Table of Contents
- [Quick Start](#quick-start)
- [Gemini CLI](#gemini-cli)
- [Claude CLI](#claude-cli)
- [Custom CLI Agents](#custom-cli-agents)
- [API & Programmatic Integration](#api--programmatic-integration)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Quick Start

### Prerequisites
1. Install Memento:
   ```bash
   pipx install mcp-memento
   ```

2. Choose your agent from the options below
3. Configure using the provided examples
4. Test the integration

### Basic Agent Test
```bash
# Test Memento standalone
memento --health

# Test MCP communication
echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | memento
```

## Gemini CLI

### Overview
Gemini CLI is Google's command-line interface for interacting with Gemini AI models. Memento provides persistent memory capabilities to enhance Gemini's context awareness.

### Configuration Methods for Gemini

#### Method 1: Environment Variables (Recommended)
```bash
# Set configuration via environment variables
export MEMENTO_SQLITE_PATH="~/.gemini-memento/context.db"
export MEMENTO_TOOL_PROFILE="extended"
export MEMENTO_LOG_LEVEL="INFO"

# Start Gemini with Memento
gemini --mcp-servers memento
```

#### Method 2: YAML Configuration Files
Create `memento.yaml` in your project directory:
```yaml
sqlite_path: ~/.gemini-memento/project.db
tool_profile: advanced
log_level: DEBUG
```

Or create global config at `~/.mcp-memento/config.yaml`:
```yaml
sqlite_path: ~/.mcp-memento/global.db
tool_profile: extended
log_level: INFO
```

Then start Gemini:
```bash
# Memento automatically reads YAML configuration
gemini --mcp-servers memento
```

#### Method 3: CLI Arguments
```bash
# Pass arguments directly to Memento server
gemini --mcp-servers 'memento --profile advanced --log-level DEBUG'

# With custom database path
gemini --mcp-servers 'memento --sqlite-path ~/custom/path/context.db'
```

### Basic Integration Examples
```bash
# Simple integration (uses defaults or YAML config)
gemini --mcp-servers memento

# With custom profile via CLI arguments
gemini --mcp-servers 'memento --profile extended'

# With environment variables for project-specific config
cd ~/projects/my-app
MEMENTO_SQLITE_PATH="./.memento/project.db" gemini --mcp-servers memento
```

### Configuration Script
Create a wrapper script `~/bin/gemini-with-memory`:

```bash
#!/bin/bash
# gemini-with-memory - Gemini CLI with Memento integration

# Set Memento environment variables
export MEMENTO_SQLITE_PATH="${MEMENTO_SQLITE_PATH:-~/.gemini-memento/context.db}"
export MEMENTO_TOOL_PROFILE="${MEMENTO_TOOL_PROFILE:-extended}"
export MEMENTO_LOG_LEVEL="${MEMENTO_LOG_LEVEL:-INFO}"

# Create directory if it doesn't exist
mkdir -p "$(dirname "$MEMENTO_SQLITE_PATH")"

# Start Memento server in background
echo "Starting Memento server..."
memento --profile "$MEMENTO_TOOL_PROFILE" &
MEMENTO_PID=$!

# Wait for server to start
sleep 2

# Check if server started successfully
if ! kill -0 $MEMENTO_PID 2>/dev/null; then
    echo "Error: Memento server failed to start"
    exit 1
fi

echo "Memento server started (PID: $MEMENTO_PID)"

# Start Gemini CLI with MCP server
echo "Starting Gemini CLI with Memento integration..."
gemini --mcp-servers memento "$@"

# Capture exit code
EXIT_CODE=$?

# Cleanup
echo "Stopping Memento server..."
kill $MEMENTO_PID 2>/dev/null || true
wait $MEMENTO_PID 2>/dev/null || true

exit $EXIT_CODE
```

Make it executable:
```bash
chmod +x ~/bin/gemini-with-memory
```

### Usage Examples

#### 1. Store Solutions from Terminal Output
```bash
# Store a command output as a solution
gemini-with-memory "Take this Redis configuration and store it in Memento: $(redis-cli info)"

# Store a script output
gemini-with-memory "Store this database migration script in Memento: $(cat migrate.sql)"
```

#### 2. Search for Patterns
```bash
# Search for authentication patterns
gemini-with-memory "Search Memento for JWT authentication implementations"

# Search for error solutions
gemini-with-memory "What solutions do we have for database connection timeouts?"
```

#### 3. Get Project History
```bash
# Get context for current project
gemini-with-memory "What have we implemented for this API project before?"

# Review past decisions
gemini-with-memory "Show me architecture decisions for microservices"
```

#### 4. Interactive Session
```bash
# Start interactive session
gemini-with-memory

# Then in the Gemini interface:
# "Store this solution: [paste solution]"
# "Find similar solutions to [current problem]"
# "Connect this to our previous work on [related topic]"
```

### Advanced Configuration

#### Configuration Priority in Practice
Memento applies configuration in this order (highest priority last):
1. Default values (hardcoded)
2. Global YAML (`~/.mcp-memento/config.yaml`)
3. Project YAML (`./memento.yaml`)
4. Environment variables
5. CLI arguments

Example with mixed configuration:
```bash
# Project has ./memento.yaml with tool_profile: "extended"
# User sets environment variable: export MEMENTO_TOOL_PROFILE="advanced"
# CLI argument: --profile core

# Result: tool_profile = "core" (CLI arguments win)
gemini --mcp-servers 'memento --profile core'
```

#### Custom Database Location
```bash
# Method 1: Environment variable (recommended for scripts)
MEMENTO_SQLITE_PATH="./.memento/project.db" gemini --mcp-servers memento

# Method 2: Project YAML file (./memento.yaml)
# sqlite_path: ./.memento/project.db
gemini --mcp-servers memento

# Method 3: CLI argument
gemini --mcp-servers 'memento --sqlite-path ./.memento/project.db'
```

#### Profile Selection
```bash
# Advanced profile for development
MEMENTO_TOOL_PROFILE="advanced" gemini --mcp-servers memento

# Core profile for simple tasks
gemini --mcp-servers 'memento --profile core'

# Extended profile with YAML configuration
# In ./memento.yaml: tool_profile: extended
gemini --mcp-servers memento
```

#### Integration with Shell Aliases
Add to `~/.bashrc` or `~/.zshrc`:
```bash
# Basic alias with default configuration
alias gemini-mem='gemini --mcp-servers memento'

# Project-specific alias with environment variables
alias gemini-proj='cd ~/projects/my-app && MEMENTO_SQLITE_PATH="./.memento/project.db" gemini --mcp-servers memento'

# Team shared memory with custom profile
alias gemini-team='MEMENTO_SQLITE_PATH="~/team/shared-memory.db" MEMENTO_TOOL_PROFILE="advanced" gemini --mcp-servers memento'

# Debug mode alias
alias gemini-debug='MEMENTO_LOG_LEVEL="DEBUG" gemini --mcp-servers memento'
```

#### Configuration Script Template
Create `~/bin/gemini-memento-config.sh`:
```bash
#!/bin/bash
# Configuration script for Gemini with Memento

# Load project-specific configuration
if [ -f "./memento.yaml" ]; then
    echo "Using project configuration from ./memento.yaml"
fi

# Set environment variables (override YAML if needed)
export MEMENTO_SQLITE_PATH="${MEMENTO_SQLITE_PATH:-~/.gemini-memento/context.db}"
export MEMENTO_TOOL_PROFILE="${MEMENTO_TOOL_PROFILE:-extended}"
export MEMENTO_LOG_LEVEL="${MEMENTO_LOG_LEVEL:-INFO}"

# Create database directory if needed
mkdir -p "$(dirname "$MEMENTO_SQLITE_PATH")"

# Start Gemini with Memento
exec gemini --mcp-servers memento "$@"
```

## Claude CLI

### Overview
Claude CLI is Anthropic's command-line interface for Claude AI. Memento integration provides persistent memory across Claude sessions.

### Basic Integration
```bash
# Start Claude CLI with Memento
claude --mcp-servers memento

# With custom configuration
claude --mcp-servers 'memento --profile extended --log-level INFO'
```

### Configuration Script
Create `~/bin/claude-with-memory`:

```bash
#!/bin/bash
# claude-with-memory - Claude CLI with Memento integration

# Configuration
export MEMENTO_SQLITE_PATH="${MEMENTO_SQLITE_PATH:-~/.claude-memento/context.db}"
export MEMENTO_TOOL_PROFILE="${MEMENTO_TOOL_PROFILE:-extended}"
export MEMENTO_LOG_LEVEL="${MEMENTO_LOG_LEVEL:-WARNING}"

# Ensure directory exists
mkdir -p "$(dirname "$MEMENTO_SQLITE_PATH")"

# Start Memento
memento --profile "$MEMENTO_TOOL_PROFILE" --log-level "$MEMENTO_LOG_LEVEL" &
MEMENTO_PID=$!
sleep 1

# Start Claude
claude --mcp-servers memento "$@"
CLAUDE_EXIT=$?

# Cleanup
kill $MEMENTO_PID 2>/dev/null || true
exit $CLAUDE_EXIT
```

### Usage Patterns

#### 1. Context Loading
```bash
# Start with project context
claude-with-memory "Load context from our e-commerce project"

# Continue previous discussion
claude-with-memory "Continue our discussion about database sharding"
```

#### 2. Solution Storage
```bash
# Store code solutions
claude-with-memory "Store this Python decorator pattern as a memory"

# Store terminal commands
claude-with-memory "Save these Docker commands for later use"
```

#### 3. Knowledge Retrieval
```bash
# Get implementation patterns
claude-with-memory "Show me how we've implemented rate limiting before"

# Review best practices
claude-with-memory "What are our documented security best practices?"
```

## Custom CLI Agents

### Python-based Agent
Create a custom Python agent with Memento integration:

```python
#!/usr/bin/env python3
"""
custom-agent.py - Custom CLI agent with Memento integration
"""

import asyncio
import sys
import json
from typing import List, Dict, Optional
from memento import Memento

class CustomAgent:
    def __init__(self, profile: str = "extended"):
        self.server = None
        self.profile = profile
    
    async def start(self):
        """Initialize the agent."""
        self.server = Memento()
        await self.server.initialize()
        print(f"Custom agent started with Memento ({self.profile} profile)")
    
    async def process_command(self, command: str, args: List[str]) -> str:
        """Process a CLI command."""
        if command == "store":
            return await self._store_memory(args)
        elif command == "search":
            return await self._search_memories(args)
        elif command == "stats":
            return await self._get_statistics()
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
        content = args[2]
        tags = args[3:] if len(args) > 3 else []
        
        memory_id = await self.server.store_memory(
            type=memory_type,
            title=title,
            content=content,
            tags=tags,
            importance=0.5
        )
        
        return f"Stored memory with ID: {memory_id}"
    
    async def _search_memories(self, args: List[str]) -> str:
        """Search memories from CLI."""
        if not args:
            return "Usage: search <query>"
        
        query = " ".join(args)
        results = await self.server.recall_mementos(
            query=query,
            limit=5
        )
        
        if not results:
            return "No memories found."
        
        output = [f"Found {len(results)} memories:"]
        for i, result in enumerate(results, 1):
            output.append(
                f"{i}. {result['title']} "
                f"(confidence: {result['confidence']:.2f})"
            )
        
        return "\n".join(output)
    
    async def _get_statistics(self) -> str:
        """Get Memento statistics."""
        stats = await self.server.get_statistics()
        return json.dumps(stats, indent=2)
    
    def _show_help(self) -> str:
        """Show help message."""
        return """
Available commands:
  store <type> <title> <content> [tags...] - Store a new memory
  search <query>                          - Search memories
  stats                                   - Show statistics
  help                                    - Show this help
        """
    
    async def stop(self):
        """Cleanup the agent."""
        if self.server:
            await self.server.cleanup()

async def main():
    agent = CustomAgent(profile="extended")
    await agent.start()
    
    try:
        if len(sys.argv) > 1:
            command = sys.argv[1]
            args = sys.argv[2:]
            result = await agent.process_command(command, args)
            print(result)
        else:
            print(agent._show_help())
    finally:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

Make it executable:
```bash
chmod +x custom-agent.py
sudo mv custom-agent.py /usr/local/bin/mem-agent
```

Usage:
```bash
# Store a memory
mem-agent store solution "Fix Redis timeout" "Increased timeout to 30s" redis timeout

# Search memories
mem-agent search "Redis timeout"

# Get statistics
mem-agent stats
```

### Shell Script Agent
Create a simple shell-based agent:

```bash
#!/bin/bash
# mem-agent.sh - Shell-based Memento agent

MEMENTO_DB="${MEMENTO_SQLITE_PATH:-~/.memento/agent.db}"
MEMENTO_PROFILE="${MEMENTO_TOOL_PROFILE:-core}"

case "$1" in
    store)
        if [ $# -lt 4 ]; then
            echo "Usage: $0 store <type> <title> <content> [tags...]"
            exit 1
        fi
        
        TYPE="$2"
        TITLE="$3"
        CONTENT="$4"
        shift 4
        TAGS="$@"
        
        # Store using Python one-liner
        python3 -c "
import asyncio, sys
from memento import Memento

async def store():
    server = Memento()
    await server.initialize()
    memory_id = await server.store_memory(
        type='$TYPE',
        title='$TITLE',
        content='''$CONTENT''',
        tags=[$(
            for tag in $TAGS; do
                echo -n "'$tag',"
            done
        )],
        importance=0.5
    )
    print(f'Stored: {memory_id}')
    await server.cleanup()

asyncio.run(store())
        "
        ;;
    
    search)
        if [ $# -lt 2 ]; then
            echo "Usage: $0 search <query>"
            exit 1
        fi
        
        QUERY="$2"
        
        python3 -c "
import asyncio, sys
from memento import Memento

async def search():
    server = Memento()
    await server.initialize()
    results = await server.recall_mementos(
        query='$QUERY',
        limit=5
    )
    for i, r in enumerate(results, 1):
        print(f'{i}. {r[\"title\"]} (confidence: {r[\"confidence\"]:.2f})')
    await server.cleanup()

asyncio.run(search())
        "
        ;;
    
    *)
        echo "Usage: $0 {store|search}"
        echo "  store <type> <title> <content> [tags...]"
        echo "  search <query>"
        exit 1
        ;;
esac
```

## API & Programmatic Integration

For HTTP REST API, Node.js integration, Docker deployment, and other programmatic access methods, see the dedicated [API & Programmatic Integration Guide](./API.md).

The API guide covers:
- **HTTP REST API** - FastAPI wrapper with full endpoint documentation
- **Node.js SDK** - JavaScript/TypeScript integration
- **Docker Deployment** - Containerized deployment examples
- **Python API Reference** - Programmatic Python usage
- **Cloud Deployment** - AWS, GCP, Kubernetes examples
- **Best Practices** - Security, performance, monitoring

### Quick API Examples

#### HTTP REST API (FastAPI):
```python
# Store memory via HTTP
curl -X POST http://localhost:8000/memories \
  -H "Content-Type: application/json" \
  -d '{
    "type": "solution",
    "title": "API Example",
    "content": "Using Memento HTTP API",
    "tags": ["api", "example"]
  }'
```

#### Node.js Integration:
```javascript
const MementoClient = require('./memento-client');
const client = new MementoClient({ profile: 'extended' });
await client.start();
const memoryId = await client.storeMemory({
  type: 'solution',
  title: 'Node.js Example',
  content: 'Using Memento from Node.js'
});
```

#### Docker Deployment:
```bash
docker run -d \
  --name memento \
  -e MEMENTO_SQLITE_PATH=/data/memento.db \
  -v ./data:/data \
  -p 8000:8000 \
  mcp-memento:latest
```

For complete documentation, examples, and best practices, see the [API & Programmatic Integration Guide](./API.md).
