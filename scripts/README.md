# Scripts Directory

This directory contains the unified release and deployment tooling for MCP Memento.

## 📦 deploy.py — Primary Release Script

Single entry point for all release and deployment operations.

```bash
python scripts/deploy.py <command> [options]
```

---

## Commands

### `bump X.Y.Z`
Full release cycle: run tests, bump versions across all manifests, update
`CHANGELOG.md` and `README.md` badges, build wheel, commit, tag, push,
merge `dev → main`, and upload stub binaries to the GitHub release.

With `--dev`, the merge and GitHub Release upload are skipped, and the stub
binary for the **current platform** is automatically rebuilt and bundled into
`stub/bin/` so that "Install Dev Extension" in Zed always uses an up-to-date binary.

```bash
# Preview without side effects
python scripts/deploy.py bump 0.3.0 --dry-run

# Full release (merges dev → main)
python scripts/deploy.py bump 0.3.0 --yes

# Dev-only release (no merge into main, rebuilds stub for current platform)
python scripts/deploy.py bump 0.3.0 --dev --yes
```

### `build`
Build wheel only, no version bump or git operations.

Temporarily patches `README.md` for PyPI compatibility before building:
- Converts relative markdown links to absolute GitHub URLs.
- Injects a compact "📋 Recent Changes" table (last 4 releases from `CHANGELOG.md`)
  before the License section.

The original `README.md` is restored immediately after the build.

```bash
python scripts/deploy.py build
```

### `publish`
Upload `dist/*` to TestPyPI or PyPI using `twine`.

If the current branch is `dev` and `main` is behind, **automatically merges
`dev → main`** before uploading — so the published release is always reflected
on the main branch.

```bash
python scripts/deploy.py publish --target testpypi
python scripts/deploy.py publish --target pypi
```

### `build-zed-stub`
Build the Rust stub binary for the **current platform** using `cargo build --release`,
copy it into `integrations/zed/stub/bin/`, and commit.

Use this during active Zed extension development when you modify `stub/src/main.rs`
and want the bundled binary updated without doing a full `bump`.

```bash
python scripts/deploy.py build-zed-stub
python scripts/deploy.py build-zed-stub --dry-run   # preview only
```

> **Note**: this only updates the binary for your current OS/arch.
> The other 4 platform binaries are produced by CI on a full release.

---

### `ext-binaries`
Download the CI-built stub binaries from the GitHub release `vX.Y.Z` and
commit them into `integrations/zed/stub/bin/`.

**When to use**: after `bump` has pushed the tag and the GitHub Actions CI
workflow (`.github/workflows/zed-stub-release.yml`) has finished building all
5 platform binaries. The CI produces fresh cross-compiled binaries (e.g. Linux
ARM64 via `cross`, macOS Intel cross-compiled on Apple Silicon) that may differ
from whatever was previously bundled in the repository.

```bash
# Wait for CI to finish, then:
python scripts/deploy.py ext-binaries
python scripts/deploy.py ext-binaries --version 0.3.0   # explicit version
```

### `status`
Print the current version string from every manifest file.

```bash
python scripts/deploy.py status
```

---

## Options

| Option | Applies to | Description |
|---|---|---|
| `--dry-run` | all | Preview all actions without executing |
| `--skip-tests` | `bump` | Skip pytest before release |
| `--dev` | `bump` | Do not merge `dev → main`; rebuild stub for current platform |
| `--yes` / `-y` | `bump`, `ext-binaries` | Auto-confirm all prompts |
| `--version X.Y.Z` | `ext-binaries` | Override Python version |

---

## Typical Release Flow

```bash
# 1. Dry run — verify everything looks correct
python scripts/deploy.py bump 0.3.0 --dry-run

# 2. Full release (bumps, builds, tags, pushes, uploads stub binaries, merges to main)
python scripts/deploy.py bump 0.3.0 --yes

# 3. Publish to PyPI (merge already done by bump)
python scripts/deploy.py publish --target pypi

# --- Optional: refresh stub binaries from CI ---
# Monitor CI (cross-compiles stub for all 5 platforms)
gh run list --repo annibale-x/mcp-memento --limit 5

# Pull fresh CI-built binaries into repo and commit
python scripts/deploy.py ext-binaries
```

### Dev-only release (publish to PyPI later)

```bash
# 1. Release to GitHub only, stay on dev (also rebuilds stub for current platform)
python scripts/deploy.py bump 0.3.0 --dev --yes

# 2. When ready to publish — publish automatically merges dev → main first
python scripts/deploy.py publish --target pypi
```

### Zed extension development loop

```bash
# After modifying stub/src/main.rs only (no version bump needed):
python scripts/deploy.py build-zed-stub

# After any change (Python server, lib.rs, stub) — full dev cycle:
python scripts/deploy.py bump 0.3.0 --dev --yes
# Then reload the extension in Zed via "Install Dev Extension"
```

---

## Files Modified by `bump`

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

## Zed Extension Stub Binaries

The stub binaries in `integrations/zed/stub/bin/` are pre-compiled native
launchers for each platform. They are:

1. Bundled in the repository for zero-download installs (dev extensions).
2. Uploaded as assets to the GitHub release `vX.Y.Z` by `deploy.py bump`.
3. Re-built by GitHub Actions CI (`.github/workflows/zed-stub-release.yml`)
   on every push of a `vX.Y.Z` tag, for all 5 targets:

| Platform | Asset |
|---|---|
| Windows x86-64 | `memento-stub-x86_64-pc-windows-msvc.exe` |
| macOS Intel | `memento-stub-x86_64-apple-darwin` |
| macOS Apple Silicon | `memento-stub-aarch64-apple-darwin` |
| Linux x86-64 | `memento-stub-x86_64-unknown-linux-gnu` |
| Linux ARM64 | `memento-stub-aarch64-unknown-linux-gnu` |

---

## Directory Structure

```
scripts/
├── README.md    ← This file
└── deploy.py    ← Unified release & deploy script
```

---

## Prerequisites

```bash
# Python build tools
pip install build twine

# GitHub CLI (for stub binary upload / download)
gh auth login
```

---

## Related Documentation

- **[docs/dev/README.md](../docs/dev/README.md)** — Full developer guide
- **[CHANGELOG.md](../CHANGELOG.md)** — Release history
- **[Main README](../README.md)** — Project overview and quick start