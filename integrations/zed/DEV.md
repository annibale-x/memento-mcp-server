# Memento Zed Extension - Development Guide

Welcome to the development documentation for the **Memento Zed Extension**. This guide provides all the necessary context, architectural decisions, and workflows for contributing to this project.

## 1. Project Overview

This project is a [Zed](https://zed.dev/) editor extension written in Rust. Its purpose is to provide a seamless, zero-config runtime environment for the **Memento MCP Server** (`mcp-memento`), which is a Python package available on PyPI.

**Note:** This repository contains only the Zed extension wrapper. The actual MCP server logic lives in the [`mcp-memento`](https://pypi.org/project/mcp-memento/) Python package. The bootstrap script that bridges the two is distributed as a GitHub Release asset.

---

## 2. Architecture

### The WASM Sandbox Constraint

Zed extensions are compiled to WebAssembly (WASM) and run inside a heavily sandboxed environment. The key constraints are:

- `std::env::temp_dir()` causes a **panic** (no direct filesystem access).
- The sandbox's `PATH` is **not** the user's shell `PATH`, so `python` or `python3` may not be found.
- There are **no** Zed APIs for Python analogous to `zed::node_binary_path()`.

### The Solution: `download_file` + Bootstrap Script

The Zed Extension API exposes `zed::download_file()`, which can fetch a file from any URL and save it into the **extension's working directory** — a real directory on the host filesystem that Zed manages on behalf of the extension. Crucially, Zed also sets this directory as the **cwd** of any child process spawned via `zed::Command`, so a bare filename is sufficient to reference the downloaded file.

This gives us the following architecture:

```
Zed (WASM sandbox)
  │
  ├─ context_server_command() [Rust/WASM]
  │    1. Reads user settings (PYTHON_COMMAND, BOOTSTRAP_VERSION, …)
  │    2. Calls zed::download_file() → saves mcp_memento_bootstrap.py
  │       into the extension working directory (only on first run / version change)
  │    3. Returns Command { command: "py" | "python3" | …, args: ["-u", "mcp_memento_bootstrap.py"] }
  │
  └─ Zed spawns the child process (cwd = extension working directory)
       │
       └─ mcp_memento_bootstrap.py [Python, host OS]
            ├─ If mcp-memento already installed → exec() into real server immediately
            └─ If not installed:
                 ├─ Start background thread: pip install --user mcp-memento
                 ├─ Main thread: answer Zed's MCP handshake with stub responses
                 │   (initialize → OK, tools/list → [], tools/call → "installing…")
                 ├─ Installation completes (background thread sets Event)
                 └─ Hand off stdin/stdout to real mcp-memento process (proxy loop)
```

### Why the Stub Response Pattern?

Zed times out the MCP handshake after ~60 seconds. A `pip install` can easily exceed that. The bootstrap script solves this by:

1. Answering `initialize` **immediately** with valid (but minimal) capabilities.
2. Running `pip install --user mcp-memento` in a background thread.
3. Buffering any requests that arrive during installation.
4. Once installed, spawning the real `mcp-memento` process and replaying buffered requests through a transparent proxy.

This approach means the user sees the server as "connected" within milliseconds, and tools become available once installation completes (typically 10–30 seconds).

### Python Discovery

Since `Worktree.which()` is not available in `context_server_command` (which receives a `Project`, not a `Worktree`), we cannot call `which()` at spawn time. Instead:

- On **Windows**: the default candidate is `py` (the Python Launcher, always on PATH if Python is installed).
- On **macOS / Linux**: the default candidate is `python3`.
- The user can override this with an absolute path via the `PYTHON_COMMAND` setting.

---

## 3. Repository Structure

```
zed-memento/
├── src/
│   └── lib.rs                  # Rust extension (WASM) — download + spawn logic
├── bootstrap/
│   └── mcp_memento_bootstrap.py  # Bootstrap script published to GitHub Releases
├── extension.toml              # Extension manifest
├── Cargo.toml                  # Rust workspace
├── DEV.md                      # This file
└── .agent/                     # Ephemeral agent artifacts (git-ignored)
```

---

## 4. GitHub Releases Workflow

The bootstrap script is distributed as a GitHub Release asset, **not** bundled in the WASM extension (which would require rebuilding and republishing the extension on every `mcp-memento` update).

### Release Tag Convention

```
bootstrap-v<BOOTSTRAP_VERSION>
```

Example: `bootstrap-v0.1.0`

### Asset Name

```
mcp_memento_bootstrap.py
```

### How to Publish a New Bootstrap Version

1. Edit `bootstrap/mcp_memento_bootstrap.py` with the desired changes.
2. Create and push a new tag:
   ```bash
   git tag bootstrap-v0.2.0
   git push origin bootstrap-v0.2.0
   ```
3. On GitHub, create a Release for that tag and upload `mcp_memento_bootstrap.py` as a release asset.
4. Update `BOOTSTRAP_VERSION` in `src/lib.rs` to `"0.2.0"`.
5. Rebuild and republish the Zed extension.

> **Note:** The `BOOTSTRAP_VERSION` constant in `src/lib.rs` controls which GitHub Release the extension fetches. Users can also pin a specific version via the `BOOTSTRAP_VERSION` setting in their Zed config.

---

## 5. Local Development Workflow

### Prerequisites

- **Rust** with the `wasm32-wasip1` target:
  ```bash
  rustup target add wasm32-wasip1
  ```
- **Zed Editor** installed on your system.
- **Python 3.8+** on the host system.

### Building

```bash
# Debug build (fast iteration)
cargo build --target wasm32-wasip1

# Release build (for packaging)
cargo build --target wasm32-wasip1 --release
```

### Testing in Zed (Dev Extension)

You do not need to publish the extension to test it:

1. Open Zed.
2. Open the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`).
3. Run `zed: extensions`.
4. Click **Install Dev Extension** and select the root directory of this project.
5. Zed compiles the extension to WASM and loads it automatically.

### Testing the Bootstrap Script Standalone

```bash
# Simulate the Zed MCP handshake from the terminal
python bootstrap/mcp_memento_bootstrap.py < test_zed_handshake.py
```

Or pipe JSON-RPC requests manually:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | python bootstrap/mcp_memento_bootstrap.py
```

### Debugging

- Open the Zed log: `zed: open log` from the Command Palette.
- Search for `[MEMENTO-BOOTSTRAP]` to see bootstrap script output.
- Search for `context_server` or `mcp` to see Zed-side errors.

---

## 6. Settings Reference

| Setting              | Default                      | Description                                                          |
|----------------------|------------------------------|----------------------------------------------------------------------|
| `PYTHON_COMMAND`     | `auto`                       | Python executable. `auto` = OS default (`py` on Windows, `python3` on Unix). Set to an absolute path to override. |
| `MEMENTO_SQLITE_PATH`| `~/.mcp-memento/context.db`  | Path to the Memento SQLite database.                                |
| `MEMENTO_TOOL_PROFILE`| `core`                      | Tool profile: `core`, `extended`, or `advanced`.                    |
| `BOOTSTRAP_VERSION`  | `0.1.0`                      | GitHub Release version of the bootstrap script to download.         |

---

## 7. Coding Standards: Airy Code Style

This project enforces the **Airy Code Style** for maximum readability:

- **EXACTLY 1 empty line** before `if`, `else`, `elif`, `try`, `except`, `for`, `while`.
- **EXACTLY 2 empty lines** before every `class`, `def`, `struct`, `impl`, or `fn`.
- **EXACTLY 1 empty line** after a method/function docstring before the code begins.
- All source code (variables, strings, docstrings) in **English**.
- All user-facing communication in **Italian**.

---

## 8. Git & Commit Guidelines

- **Conventional Commits** format is mandatory: `type(scope): description`
  - Examples:
    - `feat(bootstrap): add background pip install with stub MCP responses`
    - `fix(lib): correct Python candidate order on Windows`
    - `docs(dev): update architecture section`
- **Versioning** is read-only: never bump `version` in `extension.toml` or `Cargo.toml` unless explicitly instructed (`BUMP vX.Y.Z`).
- Ephemeral files and artifacts go in `.agent/` (git-ignored).