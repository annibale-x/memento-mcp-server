# Scripts Directory

This directory contains the unified release and deployment tooling for MCP Memento.

## deploy.py — Primary Release Script

```bash
python scripts/deploy.py <command> [options]
```

---

## Commands

### `bump [X.Y.Z]`

Dev bump: update versions in all manifests, build stub for current platform,
upload to the `dev-latest` pre-release on GitHub, build the Python wheel,
and install it into the Zed extension venv (via `MEMENTO_LOCAL_WHEEL`).

**Version is optional** — omitting it re-runs the bump on the current version
(useful to rebuild the stub or the wheel without changing the version number).

Tag is local only — CI is **not** triggered. Always non-interactive.

```bash
# Bump to a new version
python scripts/deploy.py bump 0.3.0

# Re-run bump on the current version (rebuild stub + wheel, no version change)
python scripts/deploy.py bump

# Preview without side effects
python scripts/deploy.py bump 0.3.0 --dry-run

# Skip pytest
python scripts/deploy.py bump 0.3.0 --skip-tests
```

After `bump`, the Zed extension venv is automatically configured to use the
freshly built local wheel. You only need to reload the extension in Zed:

```
Ctrl+Shift+P → "zed: extensions" → reload mcp-memento
```

---

### `promote`

Promote the current dev version to an official release:

1. Verify `CHANGELOG.md` has an entry for the current version
2. Merge `dev → main`
3. Push the tag `vX.Y.Z` (triggers CI stub cross-compile)
4. Upload stub binaries to the GitHub Release

Version is read automatically from `pyproject.toml`.

```bash
python scripts/deploy.py promote --yes

# Preview
python scripts/deploy.py promote --dry-run
```

---

### `publish`

Upload `dist/*` to PyPI (or TestPyPI with `-t`).

```bash
python scripts/deploy.py publish

# TestPyPI
python scripts/deploy.py publish -t
```

---

## Typical Development Workflow

```
bump 0.3.0  →  fix / test  →  bump  →  fix / test  →  promote  →  publish
```

1. **Start a new version**
   ```bash
   python scripts/deploy.py bump 0.3.0
   ```
   Reload the mcp-memento extension in Zed, test against the live server.

2. **Iterate** (fix code, rebuild, re-test — no version change needed)
   ```bash
   python scripts/deploy.py bump
   ```
   Reload Zed extension, repeat until satisfied.

3. **Promote to official release**
   ```bash
   python scripts/deploy.py promote --yes
   ```

4. **Publish to PyPI**
   ```bash
   python scripts/deploy.py publish
   ```

---

## Other Commands

### `build`
Build sdist + wheel only. No version bump, no git operations.

```bash
python scripts/deploy.py build
```

### `build-zed-stub`
Build the Rust stub binary for the current platform, copy it into
`integrations/zed/stub/bin/`, copy into the Zed work dir, commit and push.

Use this when you modify `stub/src/main.rs` without doing a full `bump`.

```bash
python scripts/deploy.py build-zed-stub
```

### `dev-install`
Build the local wheel and configure the Zed extension venv to use it
(instead of downloading from PyPI). Prints the `MEMENTO_LOCAL_WHEEL` snippet
to paste into Zed settings if needed.

Already called automatically by `bump` — only run this manually if you built
the wheel separately and want to update the Zed venv without a full bump.

```bash
python scripts/deploy.py dev-install
```

### `ext-binaries [--version X.Y.Z]`
Download CI-built stub binaries from the GitHub Release and commit them
into `integrations/zed/stub/bin/`. Run after CI has finished following a
`promote`.

```bash
python scripts/deploy.py ext-binaries
python scripts/deploy.py ext-binaries --version 0.3.0
```

### `upload-stubs [--version X.Y.Z]`
Create the GitHub Release (if missing) and upload local stub binaries from
`stub/bin/` as release assets. Manual fallback if the CI upload step failed.

```bash
python scripts/deploy.py upload-stubs
```

### `status`
Print the current version from every manifest file.

```bash
python scripts/deploy.py status
```

---

## Options

| Option          | Applies to              | Description                              |
|-----------------|-------------------------|------------------------------------------|
| `--dry-run`     | all                     | Preview all actions without executing    |
| `--skip-tests`  | `bump`                  | Skip pytest before release               |
| `--yes` / `-y`  | `promote`, `ext-binaries` | Auto-confirm all prompts               |
| `--version X.Y.Z` | `ext-binaries`, `upload-stubs` | Override version            |
| `--test` / `-t` | `publish`               | Upload to TestPyPI instead of PyPI       |

---

## Files Modified by `bump`

| File | What changes |
|------|--------------|
| `pyproject.toml` | `version` field |
| `src/memento/__init__.py` | `__version__` |
| `integrations/zed/Cargo.toml` | `[package] version` |
| `integrations/zed/extension.toml` | `version` |
| `integrations/zed/src/lib.rs` | `STUB_EXT_RELEASE` constant |
| `README.md` | Version badge |
| `CHANGELOG.md` | New placeholder entry scaffolded |

---

## Zed Extension Stub Binaries

The stub binaries in `integrations/zed/stub/bin/` are pre-compiled native
launchers. They are:

1. Bundled in the repository for zero-download installs (dev extensions).
2. Uploaded as assets to the GitHub Release `vX.Y.Z` by `promote`.
3. Cross-compiled by CI (`.github/workflows/zed-stub-release.yml`) on every
   `vX.Y.Z` tag push, for all 5 targets:

| Platform | Asset |
|----------|-------|
| Windows x86-64 | `memento-stub-x86_64-pc-windows-msvc.exe` |
| macOS Intel | `memento-stub-x86_64-apple-darwin` |
| macOS Apple Silicon | `memento-stub-aarch64-apple-darwin` |
| Linux x86-64 | `memento-stub-x86_64-unknown-linux-gnu` |
| Linux ARM64 | `memento-stub-aarch64-unknown-linux-gnu` |

---

## Prerequisites

```bash
# Python build + publish tools
pip install build twine

# GitHub CLI (for stub binary upload / download)
gh auth login
```

---

## Related Documentation

- **[docs/dev/README.md](../docs/dev/README.md)** — Full developer guide
- **[CHANGELOG.md](../CHANGELOG.md)** — Release history
- **[README.md](../README.md)** — Project overview and quick start