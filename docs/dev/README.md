# MCP Memento — Developer Guide

> Complete reference for contributors and maintainers of the `mcp-memento` project.

---

## Table of Contents

1. [Project Architecture](#1-project-architecture)
2. [Repository Structure](#2-repository-structure)
3. [Development Setup](#3-development-setup)
4. [Running Tests](#4-running-tests)
5. [Release Workflow](#5-release-workflow)
6. [Deploy Script Reference](#6-deploy-script-reference)
7. [Extension Architecture](#7-extension-architecture-zed--vscode-)
8. [Extension Stub Binary — Build & Release](#8-extension-stub-binary--build--release)
9. [GitHub Actions CI](#9-github-actions-ci)
10. [Version Convention](#10-version-convention)
11. [Tag Convention](#11-tag-convention)
12. [Changelog & README Badges](#12-changelog--readme-badges)

---

## 1. Project Architecture

```
mcp-memento/
│
├── Python package (PyPI: mcp-memento)
│   └── src/memento/              ← MCP server logic, tools, DB engine
│
└── IDE extensions (Zed, VSCode, …)
    └── integrations/zed/
        ├── src/lib.rs            ← WASM extension (compiled to .wasm)
        └── stub/src/main.rs     ← native Rust binary (launcher/proxy)
```

The project has **two independent release tracks**:

| Track | Language | Artifact | Published to |
|---|---|---|---|
| Python MCP server | Python 3.10+ | `.whl` + `.tar.gz` | PyPI |
| IDE extensions | Rust (WASM + native stub) | `.wasm` + stub `.exe`/ELF | IDE marketplaces (Zed, VSCode, …) |

The two tracks are **versioned together**: the extension version always mirrors the Python package version it ships with. They are released independently only when fixing extension-only bugs (ext counter `N` increments without a Python version bump).

> **Current state**: Only the Zed extension is implemented. The VSCode extension and
> others will follow the same Rust stub pattern and use the same `vX.Y.Z-ext.N` tag
> convention and CI workflow.

---

## 2. Repository Structure

```
mcp-memento/
├── src/
│   └── memento/                  ← Python package root
│       ├── __init__.py           ← __version__ lives here
│       ├── cli.py                ← CLI entry point (memento / mcp-memento)
│       ├── server.py             ← MCP server, tool dispatcher
│       ├── config.py             ← Configuration loader (YAML + env vars)
│       ├── models.py             ← Pydantic data models
│       ├── relationships.py      ← Relationship type registry
│       ├── advanced_tools.py     ← Advanced tool implementations
│       ├── database/             ← SQLite backend (engine, queries, migrations)
│       └── tools/                ← Tool implementations (core, extended, advanced)
│
├── integrations/
│   └── zed/                      ← Zed extension workspace (Rust)
│       ├── Cargo.toml            ← Workspace root + WASM crate [package]
│       ├── extension.toml        ← Zed extension manifest
│       ├── src/
│       │   └── lib.rs            ← WASM extension: downloads stub, returns Command
│       └── stub/                 ← Native Rust binary (non-WASM)
│           ├── Cargo.toml
│           ├── src/main.rs       ← MCP handshake stub + Python proxy
│           └── bin/              ← Pre-built binaries for all platforms (committed)
│               ├── memento-stub-x86_64-pc-windows-msvc.exe
│               ├── memento-stub-x86_64-apple-darwin
│               ├── memento-stub-aarch64-apple-darwin
│               ├── memento-stub-x86_64-unknown-linux-gnu
│               └── memento-stub-aarch64-unknown-linux-gnu
│
├── tests/                        ← pytest test suite (167+ tests)
├── docs/
│   ├── dev/
│   │   ├── DEV.md               ← this file
│   │   └── SCHEMA.md            ← SQLite schema reference
│   ├── integrations/            ← IDE/agent integration guides
│   ├── TOOLS.md                 ← Complete MCP tool reference
│   ├── DECAY_SYSTEM.md          ← Confidence decay documentation
│   └── RULES.md                 ← Agent rules and prompts
│
├── scripts/
│   ├── deploy.py                ← Unified release & deploy script (PRIMARY)
│   └── README.md                ← Scripts documentation
│
├── .github/
│   └── workflows/
│       └── zed-stub-release.yml ← CI: cross-compile stub for all platforms
│
├── pyproject.toml               ← Python package manifest + build config
├── CHANGELOG.md                 ← Human-readable release notes
└── README.md                    ← Public-facing documentation (badges here)
```

---

## 3. Development Setup

### Prerequisites

| Tool | Required for | Install |
|---|---|---|
| Python 3.10+ | MCP server development | [python.org](https://python.org) |
| Rust (via rustup) | Zed extension development | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| `wasm32-wasip1` target | Building the WASM extension | `rustup target add wasm32-wasip1` |
| `cross` | Cross-compiling Linux ARM stub (CI only) | `cargo install cross` (requires Docker) |
| `gh` CLI | Release management, CI monitoring | [cli.github.com](https://cli.github.com) |
| `twine` | Publishing to PyPI | `pip install twine` |
| `build` | Building wheel/sdist | `pip install build` |

> **Windows note**: `gh` may not be in the system PATH. If so, set the full path
> in your shell profile or use `winget install GitHub.cli`.

### Python Environment

```bash
# Clone
git clone https://github.com/annibale-x/mcp-memento.git
cd mcp-memento

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Rust / Zed Extension Environment

```bash
# Add the WASM target (one-time setup)
rustup target add wasm32-wasip1

# Verify Rust edition 2024 is supported (requires Rust >= 1.85)
rustc --version   # should be >= 1.85.0
```

---

## 4. Running Tests

```bash
# Full test suite (all 167+ tests)
pytest

# Short output
pytest --tb=short -q

# Specific test file
pytest tests/test_server_startup.py -v

# With coverage
pytest --cov=src tests/

# Skip slow integration tests
pytest -m "not slow"
```

The test suite is fully self-contained. No network access or external services
are required. All async tests use `pytest-asyncio` in auto mode.

---

## 5. Release Workflow

The canonical release workflow is driven by `scripts/deploy.py`.
Every step below is automated by the script — manual steps are documented
here for reference only.

### Full release (Python + Zed extension)

```bash
# 1. Dry run — preview everything without side effects
python scripts/deploy.py bump 0.3.0 --ext 2 --dry-run

# 2. Execute the full bump
python scripts/deploy.py bump 0.3.0 --ext 2 --yes

# What 'bump' does, in order:
#   a) Runs pytest
#   b) Bumps version in: pyproject.toml, src/memento/__init__.py,
#      integrations/zed/Cargo.toml, integrations/zed/extension.toml,
#      README.md badges, integrations/zed/src/lib.rs (STUB_EXT_RELEASE)
#   c) Prepends entry to CHANGELOG.md
#   d) Builds sdist + wheel
#   e) git add -A && git commit "chore(release): bump version to X.Y.Z"
#   f) git push origin dev
#   g) git tag vX.Y.Z && git push origin vX.Y.Z
#   h) git merge dev → main, git push origin main, checkout dev
#   i) git tag vX.Y.Z-ext.N && git push origin vX.Y.Z-ext.N
#      → triggers GitHub Actions to cross-compile stub for all platforms

# 3. Monitor CI
gh run list --repo annibale-x/mcp-memento
gh run watch <run-id> --repo annibale-x/mcp-memento

# 4. When CI succeeds — download binaries and commit to repo
python scripts/deploy.py ext-binaries --ext 2

# 5. Publish to TestPyPI first (optional but recommended)
python scripts/deploy.py publish --target testpypi

# 6. Publish to PyPI
python scripts/deploy.py publish --target pypi
```

### Python-only release (no Zed changes)

```bash
python scripts/deploy.py bump 0.3.1 --skip-merge --yes
python scripts/deploy.py publish --target pypi
```

### Zed extension-only release (no Python version bump)

```bash
# Only push a new ext tag, no version change
python scripts/deploy.py ext-release --ext 3

# Wait for CI, then download and commit binaries
python scripts/deploy.py ext-binaries --ext 3
```

### Build wheel only (no git operations)

```bash
python scripts/deploy.py build
```

### Check current version state

```bash
python scripts/deploy.py status
```

---

## 6. Deploy Script Reference

**File**: `scripts/deploy.py`

### Commands

| Command | Description |
|---|---|
| `bump X.Y.Z [--ext N]` | Full release cycle |
| `build` | Build sdist + wheel |
| `publish --target {testpypi\|pypi}` | Upload dist/* with twine |
| `ext-release --ext N` | Push IDE extension stub CI tag only |
| `ext-binaries --ext N` | Download CI artifacts + commit |
| `status` | Print all version strings |

### Options

| Option | Applies to | Description |
|---|---|---|
| `--ext N` | `bump`, `ext-release`, `ext-binaries` | Extension release counter (integer) |
| `--dry-run` | all | Preview without executing |
| `--skip-tests` | `bump` | Skip pytest |
| `--skip-merge` | `bump` | Skip dev→main merge |
| `--yes` / `-y` | `bump`, `ext-binaries` | Auto-confirm all prompts |
| `--version X.Y.Z` | `ext-release`, `ext-binaries` | Override Python version |

### Files modified by `bump`

| File | What changes |
|---|---|
| `pyproject.toml` | `version` field |
| `src/memento/__init__.py` | `__version__` |
| `integrations/zed/Cargo.toml` | `[package] version` |
| `integrations/zed/extension.toml` | `version` |
| `integrations/zed/src/lib.rs` | `STUB_EXT_RELEASE` constant |
| `README.md` | Version badge |
| `CHANGELOG.md` | New entry prepended |

---

## 7. Extension Architecture (Zed / VSCode / …)

The Zed extension consists of **two Rust components** with distinct roles:

### Component 1: WASM Extension (`integrations/zed/src/lib.rs`)

> This section documents the Zed extension, the first IDE extension implemented.
> Future extensions (VSCode, etc.) will follow the same stub architecture.

- Compiled to `wasm32-wasip1` (WebAssembly)
- Runs inside Zed's sandboxed extension host
- **Single responsibility**: return the `Command` to launch the MCP server
- Uses **bundle-first strategy** to locate the stub binary:
  1. Checks `stub/bin/{asset_name}` (file committed to repo — no download needed)
  2. Checks for a previously downloaded file in the working directory
  3. Downloads from GitHub Release as fallback
- Reads user settings (`PYTHON_COMMAND`, `MEMENTO_DB_PATH`, `MEMENTO_PROFILE`)
- Passes settings as environment variables to the stub

```
Zed → WASM extension → returns Command{stub_path, args:[], env:[...]}
                                         ↓
                                   stub process starts
```

### Component 2: Native Stub (`integrations/zed/stub/src/main.rs`)

- Compiled as a **native binary** for each platform (not WASM)
- Runs directly as a child process of Zed
- **Responsibilities**:
  1. **Immediate MCP handshake**: responds to `initialize` within milliseconds,
     preventing Zed's 60-second timeout
  2. **Python discovery**: finds Python on the host system (platform-specific)
  3. **Real server launch**: spawns `python -u -m memento` as a subprocess
  4. **Stdin/stdout proxy**: forwards all subsequent JSON-RPC traffic between
     Zed and the Python server

### Why the stub is necessary (Windows)

Zed on Windows launches context server processes via `ShellBuilder` (a
PowerShell non-interactive wrapper). When the direct Python bootstrap approach
was used, the process never received stdin data — the PowerShell wrapper
buffered it indefinitely. The native stub solves this by:

- Reading stdin on a **separate thread** with a `2-second timeout`
- If no data arrives within 2 seconds, it sends a **proactive** `initialize`
  response with `id=1` (the value Zed always uses)
- This response unblocks Zed regardless of buffering behavior

### Python discovery order (Windows)

1. `PYTHON_COMMAND` environment variable (set by user in Zed settings)
2. `py.exe` (Python Launcher — most reliable on Windows)
3. `python.exe` / `python3.exe` in PATH
4. `%LOCALAPPDATA%\Programs\Python\Python3*\python.exe`
5. `%APPDATA%\Python\Python3*\python.exe`

### Python discovery order (macOS / Linux)

1. `PYTHON_COMMAND` environment variable
2. `python3` / `python` in PATH
3. `/usr/local/bin/python3`, `/opt/homebrew/bin/python3`, `/usr/bin/python3`

---

## 8. Extension Stub Binary — Build & Release

### Build locally (Windows only, for testing)

```bash
# From repo root
cd integrations/zed/stub
cargo build --release --target x86_64-pc-windows-msvc

# Output lands in the workspace target directory
cp integrations/zed/target/x86_64-pc-windows-msvc/release/memento-stub.exe \
   integrations/zed/stub/bin/memento-stub-x86_64-pc-windows-msvc.exe
```

### Cross-compile all platforms via CI (recommended)

Push a Zed release tag — GitHub Actions handles everything:

```bash
git tag v0.3.0-ext.2
git push origin v0.3.0-ext.2
# or via deploy script:
python scripts/deploy.py ext-release --ext 2
```

CI compiles all 5 targets in parallel (~1 minute total):

| Target | Runner | Method |
|---|---|---|
| `x86_64-pc-windows-msvc` | `windows-latest` | native |
| `x86_64-apple-darwin` | `macos-latest` | cross-compile from ARM runner |
| `aarch64-apple-darwin` | `macos-latest` | native |
| `x86_64-unknown-linux-gnu` | `ubuntu-latest` | native |
| `aarch64-unknown-linux-gnu` | `ubuntu-latest` | `cross` tool (Docker) |

> **Note**: `macos-13` (Intel runner) was removed from GitHub Actions in 2025.
> Intel macOS binaries are cross-compiled from the `macos-latest` (Apple Silicon)
> runner by adding `x86_64-apple-darwin` as a Rust target. This works natively
> because Apple's Clang toolchain supports cross-compilation out of the box.

### Download CI artifacts into the repo

After CI completes, download and commit the binaries so future extension
installs require zero network access:

```bash
python scripts/deploy.py ext-binaries --ext 2
# Equivalent manual command:
gh release download v0.3.0-ext.2 --repo annibale-x/mcp-memento \
  --dir integrations/zed/stub/bin/ --clobber
git add integrations/zed/stub/bin/
git commit -m "chore(ext): bundle stub binaries from v0.3.0-ext.2"
git push origin dev
```

### Build the WASM extension

```bash
cd integrations/zed
cargo build --target wasm32-wasip1 --release
# Output: integrations/zed/target/wasm32-wasip1/release/memento_mcp_server.wasm
# Zed picks this up automatically when installed as a dev extension.
```

---

## 9. GitHub Actions CI

### Workflow: `zed-stub-release.yml`

**Trigger**: push of a tag matching `v*-ext.*`

**Jobs**:
- `build` (matrix, 5 jobs in parallel): compiles `memento-stub` for each platform
- `release` (sequential, after all builds): creates GitHub Release with all binaries

**Release naming**: the workflow automatically derives the title from the tag:
- Tag `v0.3.0-ext.2` → Release title `Zed Extension ext.2  (mcp-memento v0.3.0)`

**Monitor**:
```bash
gh run list --repo annibale-x/mcp-memento --limit 5
gh run watch <run-id> --repo annibale-x/mcp-memento
```

---

## 10. Version Convention

All version strings follow **Semantic Versioning** (`MAJOR.MINOR.PATCH`).

The same `X.Y.Z` version is kept in sync across:

| File | Field |
|---|---|
| `pyproject.toml` | `[project] version` |
| `src/memento/__init__.py` | `__version__` |
| `integrations/zed/Cargo.toml` | `[package] version` |
| `integrations/zed/extension.toml` | `version` |

The Zed extension is intentionally versioned to match the Python package.
This makes it unambiguous which Python version the extension was built against.

---

## 11. Tag Convention

| Tag format | Meaning | Triggers |
|---|---|---|
| `vX.Y.Z` | Python package release | (manual) PyPI publish |
| `vX.Y.Z-ext.N` | IDE extension release | GitHub Actions stub CI build |

**Examples**:
```
v0.2.6          ← Python package version
v0.2.6-ext.1   ← First IDE extension release for Python 0.2.6 (Zed)
v0.2.6-ext.2   ← Bugfix to extension only, same Python version
v0.3.0          ← Next Python package version
v0.3.0-ext.1   ← First IDE extension release for Python 0.3.0 (Zed)
```

`N` is a monotonically increasing integer, reset to `1` when `X.Y.Z` changes.

**Never delete and recreate a production tag** unless CI failed before any
release assets were uploaded. Use `git tag -d` + `git push origin :refs/tags/…`
only in that case.

---

## 12. Changelog & README Badges

### CHANGELOG.md format

```
* YYYY-MM-DD: vX.Y.Z - <Title> (Hannibal)
  * Change description one
  * Change description two
```

The `deploy.py bump` command prepends a skeleton entry. **Edit it manually**
to add meaningful release notes before pushing.

### README.md badges

The version badge is updated automatically by `deploy.py bump`:

```markdown
[![Latest Release](https://img.shields.io/badge/release-v0.2.6-purple.svg)](...)
```

The `pyproject.toml` URL under `[project.urls]` should also point to the
correct GitHub repository. Check after major restructuring.

### PyPI README patching

PyPI does not render relative Markdown links. The build script automatically
converts relative links to absolute GitHub URLs **at build time only** and
restores the original `README.md` afterwards. No manual intervention needed.

---

## Appendix A: Manual Operations Reference

### Force-update a Zed dev extension in Zed

1. Open Zed → `Extensions`
2. Scroll to `Memento MCP Server` → `Uninstall`
3.  → select the  directory inside your local clone
4. Open a project, configure the server
5. `zed: open log` → search `[MEMENTO-STUB]` for stub output

### Read stub log on Windows

```powershell
Get-Content "$env:TEMP\memento_stub.log"
```

The stub writes a marker file at startup. If this file is absent after
attempting to connect, the process was never launched.

### Manual stub test (bypassing Zed)

```bash
# Simulate empty stdin (the problematic Windows case)
./integrations/zed/stub/bin/memento-stub-x86_64-pc-windows-msvc.exe </dev/null

# Expected: proactive initialize response after ~2s, then Python server starts
```

### Publish to Zed Marketplace (future)

When ready to publish publicly:

1. Fork `zed-industries/extensions`
2. Add as Git submodule: `git submodule add https://github.com/annibale-x/mcp-memento.git extensions/mcp-memento`
3. Add entry to `extensions.toml`:
   ```toml
   [mcp-memento]
   submodule = "extensions/mcp-memento"
   path = "integrations/zed"
   version = "0.2.6"
   ```
4. Run `pnpm sort-extensions`
5. Open PR to `zed-industries/extensions`

> Test on Windows and Linux before opening the marketplace PR.
> macOS support is assumed working (CI compiles successfully).

---

*Last updated: 2026-03-18 — Hannibal*