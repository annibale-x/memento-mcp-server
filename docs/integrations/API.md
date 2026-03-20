# Programmatic Access & API Reference

Memento is a **stdio MCP server**. It has no HTTP REST API, no WebSocket interface,
and no SDK. This document explains how to access Memento programmatically using the
real interfaces that exist.

## Table of Contents

- [What Memento Is (and Is Not)](#what-memento-is-and-is-not)
- [Python Programmatic Access via MCP Client](#python-programmatic-access-via-mcp-client)
- [Docker Deployment](#docker-deployment)
- [CLI Export / Import](#cli-export--import)
- [Troubleshooting](#troubleshooting)

---

## What Memento Is (and Is Not)

| | |
|---|---|
| ✅ **Is** | A Model Context Protocol (MCP) server communicating over **stdio** (JSON-RPC) |
| ✅ **Is** | A process launched by an MCP host (IDE, agent, or your own code) |
| ✅ **Is** | Scriptable via CLI for export/import automation |
| ❌ **Is NOT** | An HTTP REST server |
| ❌ **Is NOT** | A WebSocket server |
| ❌ **Is NOT** | A gRPC service |
| ❌ **Is NOT** | A Python library with direct method calls for tool invocation |

The transport is always stdio. Clients communicate with Memento by spawning it as a
subprocess and exchanging MCP JSON-RPC messages over stdin/stdout. This is the same
mechanism used by Zed, Cursor, Claude Desktop, and every other MCP-capable host.

```
Your code / IDE / agent
        │
        │  MCP JSON-RPC over stdio
        ▼
  Memento process  (python -m memento)
        │
        ▼
  SQLite database  (~/.mcp-memento/context.db)
```

---

## Python Programmatic Access via MCP Client

The official `mcp` Python library lets you connect to Memento as a client, spawning
it as a subprocess and calling its tools programmatically.

### Install

```bash
pip install mcp
# Memento must also be installed and on PATH
pip install mcp-memento
```

### Connect and Call Tools

```python
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server_params = StdioServerParameters(
        command="memento",
        args=["--profile", "extended"],
        env=None,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Store a memory
            result = await session.call_tool(
                "store_memento",
                arguments={
                    "type": "solution",
                    "title": "Fixed Redis connection timeout",
                    "content": "Increased timeout to 30s, enabled keepalive.",
                    "tags": ["redis", "timeout", "production"],
                    "importance": 0.8,
                },
            )
            response = json.loads(result.content[0].text)
            memory_id = response["id"]

            # Recall memories by semantic query
            result = await session.call_tool(
                "recall_mementos",
                arguments={"query": "Redis connection issues", "limit": 5},
            )
            memories = json.loads(result.content[0].text)

            for m in memories.get("results", []):
                print(f"  - {m['title']} (importance: {m['importance']})")

            # Get a specific memory with relationships
            result = await session.call_tool(
                "get_memento",
                arguments={"memory_id": memory_id, "include_relationships": True},
            )
            memory = json.loads(result.content[0].text)
            print(f"Retrieved: {memory['title']}")

            # Search with filters
            await session.call_tool(
                "search_mementos",
                arguments={
                    "tags": ["redis"],
                    "min_importance": 0.5,
                    "memory_types": ["solution"],
                    "limit": 20,
                },
            )


if __name__ == "__main__":
    asyncio.run(main())
```

### Error Handling

Always check `result.isError` before parsing the response:

```python
result = await session.call_tool("get_memento", arguments={"memory_id": "bad-id"})

if result.isError:
    print(f"Tool error: {result.content[0].text}")
else:
    data = json.loads(result.content[0].text)
```

### Tool Profiles

Launch Memento with the appropriate profile for the tools you need:

| Profile | Tool count | Notable additions |
|---|---|---|
| `core` | 13 | `store_memento`, `get_memento`, `recall_mementos`, `search_mementos`, `create_memento_relationship`, ... |
| `extended` | 17 | + `get_memento_statistics`, `contextual_memento_search`, `apply_memento_confidence_decay` |
| `advanced` | 25 | + graph analytics, `set_memento_decay_factor`, ... |

For the full tool reference see [TOOLS.md](../TOOLS.md).

---

## Docker Deployment

The repository ships a `Dockerfile` and `docker-compose.yml` for running Memento
inside a container. Because the transport is stdio, the container must be run with
`stdin_open: true` and `tty: true`.

### docker-compose (recommended)

```yaml
# docker-compose.yml (already present in the repository root)
version: "3.8"

services:
  memorygraph:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mcp-memento
    stdin_open: true   # Required for MCP stdio
    tty: true          # Required for MCP stdio
    environment:
      - MEMENTO_PROFILE=core
      - MEMENTO_DB_PATH=/data/memory.db
      - MEMENTO_LOG_LEVEL=INFO
    volumes:
      - memory_data:/data
    restart: unless-stopped

volumes:
  memory_data:
    driver: local
```

```bash
# Build and start
docker compose up --build -d

# View logs
docker compose logs -f memorygraph

# Stop
docker compose down
```

### Manual docker run

```bash
docker build -t mcp-memento .

docker run -it \
  -e MEMENTO_PROFILE=extended \
  -e MEMENTO_DB_PATH=/data/memory.db \
  -v memento_data:/data \
  mcp-memento
```

The `-it` flags (`--interactive --tty`) are mandatory — without them the stdio
transport has no stdin to read from and the process exits immediately.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MEMENTO_DB_PATH` | `/data/memory.db` (in container) | SQLite database path |
| `MEMENTO_PROFILE` | `core` | Tool profile: `core`, `extended`, `advanced` |
| `MEMENTO_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Connecting an MCP Client to the Container

Point your MCP client at the container instead of a local process:

```python
server_params = StdioServerParameters(
    command="docker",
    args=["exec", "-i", "mcp-memento", "python", "-m", "memento"],
    env=None,
)
```

---

## CLI Export / Import

Memento provides `export` and `import` subcommands for backups, migrations, and
automation scripts. These operate directly on the SQLite database without going
through the MCP protocol.

```bash
# Export all memories to JSON
memento export --format json --output memories-backup.json

# Export to Markdown (one file per memory, written to a directory)
memento export --format markdown --output ./memories-export/

# Import from a JSON export
memento import --format json --input memories-backup.json

# Import and skip memories whose IDs already exist
memento import --format json --input memories-backup.json --skip-duplicates
```

### Scripting Example — Daily Backup

```bash
#!/bin/bash
DB_PATH="${MEMENTO_DB_PATH:-$HOME/.mcp-memento/context.db}"
BACKUP_DIR="$HOME/.mcp-memento/backups"
DATE=$(date +%Y-%m-%d)

mkdir -p "$BACKUP_DIR"
memento export --format json --output "$BACKUP_DIR/memento-$DATE.json"
echo "Backup saved: $BACKUP_DIR/memento-$DATE.json"

# Retain only the last 30 backups
ls -t "$BACKUP_DIR"/memento-*.json | tail -n +31 | xargs -r rm
```

---

## Troubleshooting

**The MCP client hangs on `session.initialize()`**
The Memento process is not starting. Verify that `memento` is on PATH:
```bash
memento --version
memento --health
```

**`FileNotFoundError: memento` when using `StdioServerParameters`**
The command must resolve in the Python subprocess environment. Use the full path if
needed:
```python
import shutil
StdioServerParameters(command=shutil.which("memento"), args=[])
```

**Docker container exits immediately**
Missing `-it` / `stdin_open + tty`. The MCP stdio transport requires an open stdin.
Always run the container interactively or with `stdin_open: true` + `tty: true`.

**Database not persisting between container restarts**
Ensure the volume mount is correct. The default path inside the container is
`/data/memory.db`. Map a named volume or host directory to `/data`.

**Tool not found (`unknown tool: ...`)**
The tool may belong to a higher profile. Start Memento with `--profile extended` or
`--profile advanced`, or check [TOOLS.md](../TOOLS.md) for the profile each tool
belongs to.

---

## See Also

- **[TOOLS.md](../TOOLS.md)** — Complete MCP tool reference
- **[PYTHON.md](./PYTHON.md)** — Full Python integration guide (embedding, config, error handling)
- **[IDE.md](./IDE.md)** — Configure Memento in Zed, Cursor, Windsurf, VSCode
- **[AGENT.md](./AGENT.md)** — Use Memento with Gemini CLI, Claude CLI