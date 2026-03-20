# Memento MCP Server — Zed Extension

Persistent memory for AI agents, integrated natively in [Zed](https://zed.dev/) via the
Model Context Protocol (MCP).

---

## How it works

The extension includes a small native launcher (**memento-stub**) that:

1. Discovers a Python executable on your system automatically
2. Installs `mcp-memento` via pip if not already present
3. Spawns the MCP server with inherited stdio — no proxy, no buffering issues

This means **zero manual setup**: install the extension, open Zed, done.

---

## Installation

### From the Zed Marketplace (recommended)

1. Open Zed
2. Command Palette → `zed: extensions`
3. Search for **Memento MCP Server**
4. Click **Install**

### Dev / manual install

1. Clone the repository
2. Command Palette → `zed: extensions` → **Install Dev Extension**
3. Select the `integrations/zed/` folder

---

## Requirements

- **Python 3.10+** installed on your system
- Internet access on first run (to download `mcp-memento` via pip if not installed)

Python is discovered automatically in this order:

| Platform | Candidates tried |
|---|---|
| Windows | `py.exe` → `python.exe` → `%LOCALAPPDATA%\Programs\Python\*\python.exe` |
| macOS / Linux | `python3` → `python` → `/usr/local/bin`, `/opt/homebrew/bin`, `/opt/local/bin` |

---

## Configuration

After installing the extension, open the configuration dialog:

Command Palette → `zed: extensions` → **Memento MCP Server** → **Configure Server**

### Settings

| Setting | Default | Description |
|---|---|---|
| `MEMENTO_DB_PATH` | `default` | Path to the SQLite database file. `default` uses the OS-native path (see below). Set an absolute path to override. |
| `MEMENTO_PROFILE` | `core` | Tool profile exposed to the AI agent (see below). |
| `PYTHON_COMMAND` | `default` | Python executable. `default` enables automatic discovery. Set an absolute path if your Python is not on the system PATH. |

### Default database path

| Platform | Path |
|---|---|
| Windows | `%USERPROFILE%\.mcp-memento\context.db` |
| macOS / Linux | `~/.mcp-memento/context.db` |

The directory is created automatically on first run.

### Tool profiles

| Profile | Tools included |
|---|---|
| `core` | Basic memory operations (store, recall, search, relationships) |
| `extended` | `core` + statistics, confidence decay, contextual search |
| `advanced` | `extended` + graph analytics, activity summaries |

### Custom Python executable

If your Python is not discovered automatically, set `PYTHON_COMMAND` to the full path:

```
# Windows example
C:/Users/you/AppData/Local/Programs/Python/Python312/python.exe

# macOS / Linux example
/opt/homebrew/bin/python3
```

### Custom database path

Set `MEMENTO_DB_PATH` to any absolute path:

```
# Windows
C:/Users/you/my-projects/.memento/context.db

# macOS / Linux
/home/you/my-projects/.memento/context.db
```

---

## Manual configuration (without the extension)

If you prefer to configure Zed manually via `settings.json` (macOS/Linux recommended),
add the following to `~/.config/zed/settings.json`:

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

To use a custom Python that is not on the PATH, bypass the extension entirely and
invoke Python directly:

```json
{
  "context_servers": {
    "memento": {
      "command": "/path/to/your/python",
      "args": ["-m", "memento"]
    }
  }
}
```

> **Windows note**: The manual configuration approach may cause stdin buffering issues
> on Windows due to how Zed's ShellBuilder manages pipes. The Zed extension (memento-stub)
> solves this transparently and is the recommended approach on Windows.

---

## Troubleshooting

### Extension fails to start — stub not found

If you see a `404 Not Found` error when downloading the stub:

- If using a **dev install**: run `python scripts/deploy.py build-zed-stub` from the repo root
  (see `scripts/README.md` for the full command reference).
  This builds the stub for the current platform and copies it to the Zed work directory.
- If using the **marketplace install**: the stub is downloaded automatically from the
  GitHub release. Check your internet connection.

Check the Zed log for details: Command Palette → `zed: open log`, search for `memento`.

### Python not found

Set `PYTHON_COMMAND` in the extension settings to the full path of your Python executable.

On Windows, you can find it with:

```
where python
where py
```

On macOS / Linux:

```
which python3
```

### `mcp-memento` installation fails

The stub runs `pip install --upgrade mcp-memento` automatically. If it fails:

1. Check that pip is available: `python -m pip --version`
2. Install manually: `pip install mcp-memento`
3. Verify: `python -m memento --version`

### Debug log

The stub writes a debug log to:

| Platform | Path |
|---|---|
| Windows | `%TEMP%\memento_stub_debug.log` |
| macOS / Linux | `/tmp/memento_stub_debug.log` |

---

## Links

- [GitHub Repository](https://github.com/annibale-x/mcp-memento)
- [PyPI Package](https://pypi.org/project/mcp-memento/)
- [Full IDE Integration Guide](../integrations/IDE.md)
- [Developer Guide](../../integrations/zed/README.md) *(path works from the repo root `docs/extensions/` tree)*