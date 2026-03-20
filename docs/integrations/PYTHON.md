# Python Integration Guide

This guide covers how to integrate Memento with Python applications and custom agents
using the Model Context Protocol (MCP).

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Installation](#installation)
- [Running as MCP Server](#running-as-mcp-server)
- [Programmatic Embedding](#programmatic-embedding)
- [Using via MCP Client](#using-via-mcp-client)
- [CLI Export / Import](#cli-export--import)
- [Error Handling](#error-handling)
- [Configuration Reference](#configuration-reference)

---

## Architecture Overview

Memento is a **MCP (Model Context Protocol) server**. Its primary interface is the
MCP JSON-RPC protocol — the same protocol used by Zed, Cursor, Claude Desktop, and
any other MCP-capable client.

The `Memento` Python class is a **server runtime**, not a Python library with direct
method calls. When you import it and call `initialize()`, you start the MCP server
engine that listens on stdio for JSON-RPC requests.

```
Your application / IDE / agent
        │
        │  MCP JSON-RPC (stdio or socket)
        ▼
  Memento MCP Server  (memento.server.Memento)
        │
        ▼
  SQLite database (~/.mcp-memento/context.db)
```

There are three ways to use Memento from Python:

| Approach | When to use |
|---|---|
| [CLI command](#running-as-mcp-server) | IDE integration, agent config, process-based MCP |
| [Programmatic embedding](#programmatic-embedding) | Embed the server lifecycle in your own async app |
| [MCP client](#using-via-mcp-client) | Call Memento tools from Python as an MCP client |

---

## Installation

```bash
# Recommended: install with pipx (isolated environment)
pipx install mcp-memento

# Or with pip
pip install mcp-memento

# Verify
memento --version
memento --health
```

The package installs one CLI entry point:

| Command | Description |
|---|---|
| `memento` | Primary entry point |

---

## Running as MCP Server

The simplest and most common approach: run Memento as a subprocess and connect to it
via MCP. This is how all IDE integrations work.

```bash
# Start with default settings (core profile, default DB path)
memento

# Extended profile (17 tools)
memento --profile extended

# Advanced profile (25 tools)
memento --profile advanced

# Custom database path
memento --db ~/projects/my-project/memento.db --profile extended

# Show current configuration without starting
memento --show-config

# Run health check and exit
memento --health
memento --health --health-json   # machine-readable JSON output
```

### Environment Variables

All CLI flags can also be set via environment variables:

| Variable | Default | Description |
|---|---|---|
| `MEMENTO_DB_PATH` | `~/.mcp-memento/context.db` | SQLite database path |
| `MEMENTO_PROFILE` | `core` | Tool profile (`core`, `extended`, `advanced`) |
| `MEMENTO_LOG_LEVEL` | `INFO` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `MEMENTO_ALLOW_CYCLES` | `false` | Allow cycles in the relationship graph |

### Configuration Precedence

From highest to lowest priority:

1. **CLI arguments** (`--db`, `--profile`, `--log-level`) — always win
2. **Environment variables** (`MEMENTO_DB_PATH`, `MEMENTO_PROFILE`, ...)
3. **YAML config file** (`memento.yaml` in CWD or `~/.mcp-memento/config.yaml`)
4. **Built-in defaults**

---

## Programmatic Embedding

Use this approach when you want to embed the Memento server lifecycle inside your own
Python application — for example, to run it alongside other async tasks without
spawning a separate process.

```python
import asyncio
from memento import Memento


async def main():
    server = Memento()

    # Connects to SQLite, initializes schema, registers MCP handlers
    await server.initialize()

    try:
        # At this point the MCP server engine is running.
        # It reads JSON-RPC requests from stdin and writes responses to stdout.
        # You can now drive it from an MCP client in a separate coroutine/process.
        #
        # Example: run the server until interrupted
        await server.server.run_forever()

    finally:
        # Always clean up: closes DB connection
        await server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
```

### Memento Class Reference

```python
from memento import Memento

class Memento:
    def __init__(self) -> None:
        """
        Create a new Memento MCP server instance.

        Reads configuration from environment variables and YAML files.
        Does NOT open any connections yet — call initialize() for that.
        """

    async def initialize(self) -> None:
        """
        Open the SQLite database, initialize the schema, and register
        all MCP tool handlers.

        Must be called before the server can handle any requests.
        Raises on connection or schema errors.
        """

    async def cleanup(self) -> None:
        """
        Close the database connection and release resources.

        Safe to call even if initialize() was never called.
        """
```

### Available Exports

The `memento` package also exports the Pydantic models used internally:

```python
from memento import (
    Memento,           # MCP server class
    Memory,            # Memory node model
    MemoryType,        # Enum of memory types
    Relationship,      # Relationship edge model
    RelationshipType,  # Enum of relationship types
    MemoryContext,     # Context model
    # Exception classes:
    MemoryError,
    MemoryNotFoundError,
    RelationshipError,
    ValidationError,
    DatabaseConnectionError,
    SchemaError,
    NotFoundError,
    BackendError,
    ConfigurationError,
    ToolError,
)
```

---

## Using via MCP Client

To call Memento **tools** (store, search, recall, etc.) programmatically from Python,
use the official `mcp` library to connect to a running Memento server as a client.

### Install the MCP client library

```bash
pip install mcp
```

### Connect and call tools

```python
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    # Define the server to connect to
    server_params = StdioServerParameters(
        command="memento",
        args=["--profile", "extended"],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the MCP connection
            await session.initialize()

            # --- Store a memory ---
            result = await session.call_tool(
                "store_memento",
                arguments={
                    "type": "solution",
                    "title": "Fixed Redis connection timeout",
                    "content": "Increased timeout to 30s, enabled keepalive...",
                    "tags": ["redis", "timeout", "production"],
                    "importance": 0.8,
                },
            )
            response = json.loads(result.content[0].text)
            memory_id = response["id"]
            print(f"Stored memory: {memory_id}")

            # --- Recall memories ---
            result = await session.call_tool(
                "recall_mementos",
                arguments={
                    "query": "Redis connection issues",
                    "limit": 5,
                },
            )
            memories = json.loads(result.content[0].text)
            for m in memories.get("results", []):
                print(f"  - {m['title']} (importance: {m['importance']})")

            # --- Get a specific memory ---
            result = await session.call_tool(
                "get_memento",
                arguments={
                    "memory_id": memory_id,
                    "include_relationships": True,
                },
            )
            memory = json.loads(result.content[0].text)
            print(f"Retrieved: {memory['title']}")

            # --- Search with filters ---
            result = await session.call_tool(
                "search_mementos",
                arguments={
                    "tags": ["redis"],
                    "min_importance": 0.5,
                    "memory_types": ["solution"],
                    "limit": 20,
                },
            )

            # --- Create a relationship ---
            await session.call_tool(
                "create_memento_relationship",
                arguments={
                    "from_memory_id": memory_id,
                    "to_memory_id": "another-memory-id",
                    "relationship_type": "RELATED_TO",
                    "strength": 0.8,
                    "confidence": 0.9,
                },
            )


if __name__ == "__main__":
    asyncio.run(main())
```

### Available MCP Tools

For the complete list of tools and their parameters, see [TOOLS.md](../TOOLS.md).
Quick reference by profile:

| Profile | Tools | Key additions |
|---|---|---|
| `core` | 13 | `store_memento`, `get_memento`, `update_memento`, `delete_memento`, `recall_mementos`, `search_mementos`, `create_memento_relationship`, `get_related_mementos`, ... |
| `extended` | 17 | + `get_memento_statistics`, `search_memento_relationships_by_context`, `contextual_memento_search`, `apply_memento_confidence_decay` |
| `advanced` | 25 | + graph analytics, `set_memento_decay_factor`, ... |

---

## CLI Export / Import

Memento includes CLI subcommands for exporting and importing memories without
going through the MCP protocol. Useful for backups, migrations, and scripting.

```bash
# Export all memories to JSON
memento export --format json --output memories-backup.json

# Export to Markdown (one file per memory, written to a directory)
memento export --format markdown --output ./memories-export/

# Import from a JSON export
memento import --format json --input memories-backup.json

# Import and skip memories whose IDs already exist in the DB
memento import --format json --input memories-backup.json --skip-duplicates
```

### Scripting example

```bash
#!/bin/bash
# Daily backup script

DB_PATH="${MEMENTO_DB_PATH:-$HOME/.mcp-memento/context.db}"
BACKUP_DIR="$HOME/.mcp-memento/backups"
DATE=$(date +%Y-%m-%d)

mkdir -p "$BACKUP_DIR"
memento export --format json --output "$BACKUP_DIR/memento-$DATE.json"
echo "Backup saved: $BACKUP_DIR/memento-$DATE.json"

# Keep only the last 30 backups
ls -t "$BACKUP_DIR"/memento-*.json | tail -n +31 | xargs -r rm
```

---

## Error Handling

When calling tools via the MCP client, errors are returned as structured responses.
Always check `result.isError` before parsing the content.

```python
result = await session.call_tool("get_memento", arguments={"memory_id": "bad-id"})

if result.isError:
    error_text = result.content[0].text
    print(f"Tool error: {error_text}")
else:
    data = json.loads(result.content[0].text)
    # process data...
```

When embedding the server, catch exceptions from `initialize()`:

```python
from memento import Memento, DatabaseConnectionError, SchemaError

server = Memento()

try:
    await server.initialize()
except DatabaseConnectionError as e:
    print(f"Cannot open database: {e}")
    raise
except SchemaError as e:
    print(f"Schema initialization failed: {e}")
    raise
```

---

## Configuration Reference

### YAML Configuration File

Create `memento.yaml` in the current working directory or at
`~/.mcp-memento/config.yaml`:

```yaml
# memento.yaml — actively read keys only
db_path: ~/.mcp-memento/context.db
profile: extended           # core | extended | advanced
logging:
  level: INFO               # DEBUG | INFO | WARNING | ERROR
features:
  allow_relationship_cycles: false
```

> **Note**: Only the four keys above are read by the configuration loader.
> `log_level` as a flat top-level key is **not** supported — use `logging.level` (nested).
> Additional sections present in the project's `memento.yaml` template (`confidence`,
> `search`, `performance`, `memory`, `fts`, `project`) are reserved for future use
> and are silently ignored by the current version.

### Checking the Active Configuration

```bash
memento --show-config
```

### Health Check

```bash
# Human-readable output (to stderr)
memento --health

# Machine-readable JSON (to stdout)
memento --health --health-json
```

Example JSON output:

```json
{
  "status": "healthy",
  "version": "X.Y.Z",
  "backend_type": "sqlite",
  "connected": true,
  "db_path": "/home/user/.mcp-memento/context.db",
  "statistics": {
    "memory_count": 142
  },
  "timestamp": "2026-03-18T12:00:00Z"
}
```

---

## Next Steps

- **[TOOLS.md](../TOOLS.md)** — Complete MCP tool reference (parameters, examples)
- **[IDE.md](./IDE.md)** — Configure Memento in Zed, Cursor, Windsurf, VSCode
- **[AGENT.md](./AGENT.md)** — Use Memento with Gemini CLI, Claude CLI
- **[DECAY_SYSTEM.md](../DECAY_SYSTEM.md)** — Confidence & decay system details
- **[RULES.md](../RULES.md)** — Best practices for memory management