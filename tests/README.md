# Test Suite — mcp-memento

## Table of Contents

- [Overview](#overview)
- [Test Files](#test-files)
- [Directory Structure](#directory-structure)
- [Running Tests](#running-tests)
- [Configuration](#configuration)
- [Writing New Tests](#writing-new-tests)
- [Troubleshooting](#troubleshooting)

---

## Overview

This directory contains the full pytest-based test suite for mcp-memento. Tests cover core models,
database operations, CLI, MCP tools, FTS search, pagination, relationships, confidence system,
context extraction, and server startup.

---

## Test Files

| File | Description |
|------|-------------|
| `test_standard_pytest.py` | Comprehensive pytest suite covering configuration, models, database, tools, CLI, and integration. Uses fixtures for DB isolation. |
| `test_cli.py` | CLI functionality: argument parsing, `--health`, `--show-config`, `--profile`, import/export handlers. |
| `test_tools.py` | Tool models, definitions, registry, and parameter validation. |
| `test_relationships.py` | Relationship models, types, validation, and serialization. |
| `test_server_startup.py` | Server initialization, database connection, and basic startup behaviour. |
| `test_confidence_system.py` | Confidence decay, intelligent decay rules per memory type, boost-on-access, low-confidence detection, critical-memory exemption. |
| `test_fts_integration.py` | Full-Text Search schema creation, search operations, ranking, and error handling. |
| `test_pagination.py` | `paginate_memories` and `count_memories` utilities with async mocks. |
| `test_context_extractor.py` | `extract_context_structure`, `parse_context`, and all private extractor helpers. |
| `test_project_detection.py` | `detect_project_context` return shape and required keys. |

---

## Directory Structure

```
tests/
├── README.md                   # This file
├── test_standard_pytest.py     # Comprehensive fixture-based suite
├── test_cli.py                 # CLI tests
├── test_tools.py               # Tool model/registry tests
├── test_relationships.py       # Relationship model tests
├── test_server_startup.py      # Server startup tests
├── test_confidence_system.py   # Confidence system tests
├── test_fts_integration.py     # Full-Text Search tests
├── test_pagination.py          # Pagination utility tests
├── test_context_extractor.py   # Context extractor tests
├── test_project_detection.py   # Project detection tests
├── run_tests.py                # Legacy runner (do not use)
├── run_tests.bat               # Legacy Windows script (do not use)
├── run_tests.sh                # Legacy Unix script (do not use)
├── utils/                      # Shared test helpers
└── test_data/                  # Temporary test databases (git-ignored)
```

---

## Running Tests

All tests are executed with **pytest** from the project root.

### Run the full suite

```bash
pytest tests/
```

### Run with verbose output

```bash
pytest tests/ -v
```

### Run a single file

```bash
pytest tests/test_cli.py -v
```

### Run a single test by name

```bash
pytest tests/test_confidence_system.py -k "test_decay"
```

### Run with coverage

```bash
pytest tests/ --cov=memento --cov-report=term-missing
```

### Run only async tests

```bash
pytest tests/ -m asyncio
```

---

## Configuration

pytest behaviour is controlled by `pyproject.toml` (or `pytest.ini`) in the project root.
Key settings:

```
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

Useful environment variables:

```bash
MEMENTO_DB_PATH=tests/test_data/ci_test.db
MEMENTO_PROFILE=extended
MEMENTO_LOG_LEVEL=WARNING
PYTHONIOENCODING=utf-8   # required on Windows CI
PYTHONUTF8=1             # required on Windows CI
```

---

## Writing New Tests

### Sync test (no async)

```python
# tests/test_example.py
import pytest
from memento.models import Memory


def test_memory_title_required():
    with pytest.raises(Exception):
        Memory(title=None)
```

### Async test with pytest-asyncio

```python
# tests/test_example_async.py
import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_store_and_retrieve(temp_db_path):
    # temp_db_path fixture is defined in test_standard_pytest.py
    # or define your own via conftest.py
    db = AsyncMock()
    db.store.return_value = {"id": "abc", "title": "Example"}

    result = await db.store({"title": "Example"})

    assert result["id"] == "abc"
```

### Fixture for isolated DB

```python
import os
import tempfile
import pytest


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        path = tmp.name
    yield path
    if os.path.exists(path):
        os.unlink(path)
```

### Best practices

- One assertion focus per test function.
- Use `pytest.fixture` for setup/teardown — never global state.
- Mock external I/O (`AsyncMock`, `MagicMock`, `patch`).
- Name tests as `test_<what>_<condition>` for clarity.
- Keep test data in `tests/test_data/` (git-ignored).

---

## Troubleshooting

| Symptom | Solution |
|---------|----------|
| `ModuleNotFoundError: memento` | Run pytest from the **project root**, not from `tests/`. |
| `ScopeMismatch` with async fixtures | Ensure `asyncio_mode = "auto"` is set in `pyproject.toml`. |
| Database permission errors | Verify write access to `tests/test_data/`. |
| Unicode decode errors on Windows | Set `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1`. |
| Stale `.pyc` / import cache issues | Run `pytest --cache-clear` or delete `__pycache__` dirs. |

### Inspect a test database manually

```bash
sqlite3 tests/test_data/test_memory.db ".tables"
sqlite3 tests/test_data/test_memory.db ".schema memories"
```

### Clean all test artifacts

```bash
find tests/test_data -name "*.db" -delete
find tests -name "__pycache__" -type d -exec rm -rf {} +
```
