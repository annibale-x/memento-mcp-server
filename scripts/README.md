# Scripts Directory

This directory contains the unified release and deployment tooling for MCP Memento.

## 📦 deploy.py — Primary Release Script

`deploy.py` is the single entry point for all release and deployment operations.
It replaces the legacy `build_memento.py`, `build.sh`, and `build.bat` scripts,
which have been removed.

**Usage:**
```bash
python scripts/deploy.py <command> [options]
```

---

## Commands

### `bump X.Y.Z`
Full release cycle: run tests, bump versions across all manifests, update
`CHANGELOG.md` and `README.md` badges, build wheel, commit, tag, push, merge
`dev → main`, and optionally trigger IDE extension stub CI.

```bash
# Preview without side effects
python scripts/deploy.py bump 0.3.0 --ext 2 --dry-run

# Execute the full release
python scripts/deploy.py bump 0.3.0 --ext 2 --yes
```

### `build`
Build `sdist` + wheel only, with no version bump or git operations.

Before invoking `python -m build`, this command temporarily patches `README.md` for
PyPI compatibility:
- Converts all relative markdown links to absolute GitHub URLs (so tables and
  cross-references render correctly on the PyPI project page).
- Injects a compact **"📋 Recent Changes"** table (last 4 releases from
  `CHANGELOG.md`) just before the License section, giving PyPI visitors a quick
  at-a-glance history without having to leave the page.

The original `README.md` is restored immediately after the wheel is built.

```bash
python scripts/deploy.py build
```

### `publish`
Upload `dist/*` to TestPyPI or PyPI using `twine`.

```bash
python scripts/deploy.py publish --target testpypi
python scripts/deploy.py publish --target pypi
```

### `ext-release`
Push the IDE extension tag `vX.Y.Z-ext.N` to trigger the GitHub Actions CI
workflow that cross-compiles the native stub binary for all 5 platforms.

```bash
python scripts/deploy.py ext-release --ext 2
```

> Alias `zed-release` is kept for backward compatibility.

### `ext-binaries`
Download the CI-built stub binaries from the GitHub Release and commit them
into `integrations/zed/stub/bin/`.

```bash
python scripts/deploy.py ext-binaries --ext 2
```

> Alias `zed-binaries` is kept for backward compatibility.

### `status`
Print the current version string from every manifest file.

```bash
python scripts/deploy.py status
```

---

## Options

| Option | Applies to | Description |
|---|---|---|
| `--ext N` | `bump`, `ext-release`, `ext-binaries` | Extension release counter (integer) |
| `--dry-run` | all | Preview all actions without executing |
| `--skip-tests` | `bump` | Skip pytest before release |
| `--skip-merge` | `bump` | Do not merge `dev → main` |
| `--yes` / `-y` | `bump`, `ext-binaries` | Auto-confirm all prompts |
| `--version X.Y.Z` | `ext-release`, `ext-binaries` | Override Python version |

---

## Typical Release Flow

```bash
# 1. Dry run — verify everything looks correct
python scripts/deploy.py bump 0.3.0 --ext 2 --dry-run

# 2. Full release
python scripts/deploy.py bump 0.3.0 --ext 2 --yes

# 3. Monitor CI
gh run list --repo annibale-x/mcp-memento --limit 5
gh run watch <run-id> --repo annibale-x/mcp-memento

# 4. Download binaries built by CI and commit to repo
python scripts/deploy.py ext-binaries --ext 2

# 5. Publish to PyPI
python scripts/deploy.py publish --target testpypi   # optional
python scripts/deploy.py publish --target pypi
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

# GitHub CLI (for ext-release / ext-binaries)
# https://cli.github.com
gh auth login
```

---

## Related Documentation

- **[docs/dev/DEV.md](../docs/dev/DEV.md)** — Full developer guide with release workflow details
- **[CHANGELOG.md](../CHANGELOG.md)** — Release history
- **[Main README](../README.md)** — Project overview and quick start