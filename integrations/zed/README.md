# Memento Zed Extension — Development Guide

## 1. Overview

This is the [Zed](https://zed.dev/) editor extension for **Memento MCP Server**.
It provides a zero-config runtime that discovers Python, installs `mcp-memento` if
needed, and launches the MCP server.

The extension lives in `integrations/zed/` inside the main `mcp-memento` repository.

---

## 2. Architecture

### WASM Sandbox Constraints

Zed extensions compile to WebAssembly (`wasm32-wasip1`) and run in a sandbox:

- `std::env::temp_dir()` **panics** — no arbitrary filesystem access.
- The sandbox `PATH` is not the user shell `PATH`.
- There is no Zed API for spawning Python directly.
- The **WASM working directory** is `<data>/extensions/work/<ext-id>/` — a Zed-managed
  directory that is **separate** from the extension source files. Zed does **not** copy
  source files there automatically.

### Two Rust Components

```
integrations/zed/
├── src/lib.rs          # WASM extension — finds stub, returns Command to Zed
└── stub/src/main.rs    # Native binary stub — finds Python, launches mcp-memento
```

#### 1. WASM extension (`src/lib.rs`)

Runs inside the Zed sandbox. Its only job is to locate the stub binary and return
a `Command` to Zed. It uses a **download-first with local cache** strategy:

| Priority | Location | When present |
|----------|----------|--------------|
| 1 | `stub/bin/<asset>` relative to WASM CWD | Placed there by `deploy.py dev-stub` (dev) or by Zed from the extension package (marketplace) |
| 2 | `<download-name>` in WASM CWD | Cached from a previous download |
| 3 | GitHub Release `vX.Y.Z` | Downloaded on first run, cached for future runs |

The WASM CWD is `%LOCALAPPDATA%\Zed\extensions\work\mcp-memento\` on Windows.

#### 2. Native stub (`stub/src/main.rs`)

A small native binary (~160 lines). It does **not** proxy MCP traffic.

Flow:
1. Reads `PYTHON_COMMAND` env var (or auto-discovers: `py.exe` → `python.exe` → `%LOCALAPPDATA%`)
2. Checks if `mcp-memento` is installed (`python -m memento --version`)
3. If not installed: runs `pip install --upgrade mcp-memento`
4. Spawns `python -u -m memento` with **inherited stdio**
5. Exits immediately — Python inherits Zed's file descriptors directly

**Why inherited stdio instead of a proxy?**
On Windows, Zed (ShellBuilder) closes stdin after `initialize`. With inherited stdio,
Python gets the actual file descriptors opened by Zed — no proxy pipe, no broken pipe.

Debug log: `%TEMP%\memento_stub_debug.log` (Windows)

---

## 3. Repository Structure

```
integrations/zed/
├── src/
│   └── lib.rs                              # WASM extension
├── stub/
│   ├── src/
│   │   └── main.rs                         # Native stub source
│   ├── bin/
│   │   ├── memento-stub-x86_64-pc-windows-msvc.exe
│   │   ├── memento-stub-x86_64-apple-darwin
│   │   ├── memento-stub-aarch64-apple-darwin
│   │   ├── memento-stub-x86_64-unknown-linux-gnu
│   │   └── memento-stub-aarch64-unknown-linux-gnu
│   └── Cargo.toml
├── Cargo.toml                              # Workspace root
├── extension.toml                          # Extension manifest
├── extension.wasm                          # Compiled WASM (git-ignored, built by Zed)
└── README.md                               # This file (developer guide)
```

`stub/bin/` contains pre-built binaries committed to the repository.
They are used by the marketplace install path (Zed copies them into the work dir).

---

## 4. Prerequisites

- **Rust** with the WASM target:
  ```
  rustup target add wasm32-wasip1
  ```
- **Zed Editor** installed.
- **Python 3.8+** on the host system.

---

## 5. Local Development Workflow

### First-time setup

After cloning, run:

```
python scripts/deploy.py dev-stub
```

This command:
1. Builds the stub binary for the current platform (`cargo build --release`)
2. Copies it into `integrations/zed/stub/bin/<asset>` (repo)
3. Copies it into the Zed extension work directory:
   - Windows: `%LOCALAPPDATA%\Zed\extensions\work\mcp-memento\stub\bin\`
   - macOS:   `~/Library/Application Support/Zed/extensions/work/mcp-memento/stub/bin/`
   - Linux:   `~/.local/share/zed/extensions/work/mcp-memento/stub/bin/`
4. Commits and pushes the updated binary to `dev`

Step 3 is what makes "Install Dev Extension" work without a GitHub Release —
Zed uses that work directory as the WASM sandbox CWD, so the stub is found at
`stub/bin/<asset>` exactly as `lib.rs` expects.

### Loading the extension in Zed

1. Open Zed.
2. Open the Command Palette (`Ctrl+Shift+P`).
3. Run `zed: extensions`.
4. Click **Install Dev Extension** and select `integrations/zed/`.

Zed compiles the WASM and loads the extension. No rebuild needed after editing
`lib.rs` — Zed recompiles automatically on reload.

### After modifying `stub/src/main.rs`

```
python scripts/deploy.py dev-stub
```

Rebuild, copy to both locations, commit, push.

### Building the WASM manually

```
cargo build --target wasm32-wasip1 --release
cp target/wasm32-wasip1/release/memento_mcp_server.wasm extension.wasm
```

`extension.wasm` is git-ignored; Zed rebuilds it from source when loading a dev
extension.

---

## 6. Version Constants in `lib.rs`

```rust
const STUB_EXT_RELEASE: &str = "v0.2.9";   // GitHub Release tag for fallback download
const REPO: &str = "annibale-x/mcp-memento";
const BUNDLED_BIN_DIR: &str = "stub/bin";   // Relative to WASM CWD
```

`STUB_EXT_RELEASE` is updated automatically by `scripts/deploy.py` on every version bump.

---

## 7. Release Workflow

The full release is handled by `scripts/deploy.py`. See `scripts/README.md` for details.

```
# Official release (triggers CI cross-compile for all 5 platforms):
python scripts/deploy.py bump X.Y.Z --yes

# Dev bump (local tag only, no CI, no PyPI):
python scripts/deploy.py bump X.Y.Z --dev --yes
```

On an official release:
- GitHub Actions (`.github/workflows/zed-stub-release.yml`) cross-compiles stub
  binaries for all 5 targets and uploads them as assets to the release.
- `deploy.py` uploads the binaries from `stub/bin/` to the GitHub Release as well.

---

## 8. Settings Reference

| Setting | Default | Description |
|---|---|---|
| `MEMENTO_DB_PATH` | `default` | Path to the SQLite database. `default` = OS native path (`%USERPROFILE%\.mcp-memento\context.db` on Windows, `~/.mcp-memento/context.db` on macOS/Linux). Set to an absolute path to override. |
| `MEMENTO_PROFILE` | `core` | Tool profile: `core`, `extended`, or `advanced`. |
| `PYTHON_COMMAND` | `default` | Python executable. `default` = automatic discovery (`py.exe` → `python.exe` on Windows, `python3` → `python` on Unix). Set to an absolute path to override. |

> User-facing documentation: [docs/extensions/ZED.md](../../docs/extensions/ZED.md)

---

## 9. Cargo Workspace Layout

The workspace root is `integrations/zed/Cargo.toml` with two members:

- `.` — the WASM extension crate (`memento-mcp-server`)
- `stub` — the native stub crate (`memento-stub`)

Both share the same `target/` directory at `integrations/zed/target/`.

Build commands:

```
# WASM extension
cargo build --target wasm32-wasip1 --release

# Native stub (host platform)
cargo build --release --manifest-path integrations/zed/stub/Cargo.toml
```

---

## 10. Coding Standards

- **Airy Code Style**: 1 empty line before `if`/`else`/`match`, 2 empty lines before `fn`/`struct`/`impl`.
- **Conventional Commits**: `type(scope): description` — e.g. `fix(zed): correct stub path on Windows`.
- **Versioning**: read-only. Never bump `version` in `extension.toml` or `Cargo.toml` unless explicitly instructed.
- Ephemeral files go in `.agent/` (git-ignored).