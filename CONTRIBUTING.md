# Contributing to MCP Memento

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Code Style](#code-style)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Conventional Commits](#conventional-commits)
- [Release Process](#release-process)

---

## Development Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/annibale-x/mcp-memento.git
   cd mcp-memento
   ```

2. **Install in development mode**:

   ```bash
   pip install -e ".[dev]"
   ```

3. **Verify the setup**:

   ```bash
   pytest
   ```

4. **Run the server locally**:

   ```bash
   memento
   ```

   > The only valid entry point is `memento`. There is no `mcp-memento` command.

---

## Project Structure

```
mcp-memento/
├── src/
│   └── memento/               # Main Python package
│       ├── server.py          # MCP server (tool handlers)
│       ├── config.py          # TOOL_PROFILES, Config, DB path defaults
│       ├── backend.py         # SQLiteBackend
│       └── ...
├── tests/                     # pytest test suite (~167 tests)
├── docs/
│   ├── TOOLS.md               # MCP tools reference
│   ├── DECAY_SYSTEM.md        # Confidence & decay system
│   ├── RULES.md               # Usage rules and best practices
│   ├── RELATIONSHIPS.md       # Relationship types reference
│   ├── AGENT_CONFIGURATION.md # Agent prompt templates
│   ├── INTEGRATION.md         # Integration overview
│   ├── integrations/
│   │   ├── IDE.md             # Zed, Cursor, Windsurf, VSCode
│   │   ├── PYTHON.md          # Python MCP client
│   │   ├── AGENT.md           # CLI agents (Gemini, Claude, etc.)
│   │   └── API.md             # HTTP REST, Node.js SDK, Docker
│   ├── extensions/
│   │   └── ZED.md             # Zed extension specifics
│   └── dev/
│       ├── README.md          # Development workflow & release process
│       └── SCHEMA.md          # Database schema
├── scripts/
│   ├── deploy.py              # Automated release script
│   └── README.md              # Deploy commands reference
├── integrations/
│   └── zed/                   # Zed WASM extension
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

---

## Code Style

### Python

- Follow [PEP 8](https://pep8.org/).
- Use type hints for all function signatures.
- Write docstrings in Google style.
- Maximum line length: 88 characters.
- Airy formatting rules:
  - 1 empty line before `if`, `else`, `elif`, `try`, `except`.
  - 2 empty lines before every `class` or `def`.
  - 1 empty line after a method docstring before the first line of code.

### Import Order

```python
# Standard library
import os
from typing import Optional, List

# Third-party
from mcp.server import Server

# Local
from .config import Config
from .backend import SQLiteBackend
```

### Naming Conventions

| Kind | Style |
|---|---|
| Classes | `CamelCase` |
| Functions / Methods | `snake_case` |
| Variables | `snake_case` |
| Constants | `UPPER_SNAKE_CASE` |
| Internal | `_single_underscore` |

### Formatting Tools

Black, isort, and mypy are aspirational guidelines — they are not enforced by CI.
Running them before a PR is appreciated but not required:

```bash
black src/ tests/
isort src/ tests/
mypy src/
```

---

## Testing

### Running Tests

```bash
# Run the full test suite
pytest

# Run a specific file
pytest tests/test_tools.py

# Verbose output
pytest -v

# Single test
pytest tests/test_tools.py::test_store_memory -v

# With coverage
pytest --cov=src tests/
```

### Guidelines

- Tests must be isolated — no shared state between tests.
- Each test creates its own in-memory SQLite database.
- Test names must describe what they test.
- Use mocks for external dependencies.

---

## Documentation

Technical documentation lives under `docs/`. The development workflow and release
process are documented in [`docs/dev/README.md`](docs/dev/README.md).

When changing a public tool, API surface, or configuration key, update the relevant
file in `docs/` in the same PR.

### Docstring Format

```python
def store_memento(
    type: str,
    title: str,
    content: str,
    tags: Optional[List[str]] = None,
    importance: float = 0.5,
) -> str:
    """Store a new memento in the database.

    Args:
        type: Memory type (solution, problem, code_pattern, fix, error, etc.)
        title: Descriptive title for the memento.
        content: Detailed content of the memento.
        tags: Optional list of tags for categorization.
        importance: Importance score 0.0–1.0 (default 0.5).

    Returns:
        The ID of the newly created memento.

    Raises:
        ValueError: If required parameters are missing.
    """
```

---

## Pull Request Process

1. Open an issue to discuss any significant change before starting work.
2. Create a feature branch from `dev`:

   ```bash
   git checkout -b feat/your-feature-name
   ```

3. Make changes, add tests, update docs as needed.
4. Ensure the test suite passes:

   ```bash
   pytest
   ```

5. Commit using [Conventional Commits](#conventional-commits).
6. Push and open a PR targeting `dev` (not `main`).

### PR Guidelines

- Title must follow Conventional Commits format.
- Description must explain what changes and why.
- Reference related issues (`Closes #N`).
- Keep PRs focused — one concern per PR.

---

## Conventional Commits

```
<type>(<scope>): <description>
```

**Types**:

| Type | Use for |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no logic change |
| `refactor` | Code restructure, no feature/fix |
| `test` | Tests added or changed |
| `chore` | Maintenance, tooling, dependencies |

**Examples**:

```
feat(confidence): add automatic decay scheduling
fix(search): resolve off-by-one in FTS pagination
docs(tools): update store_memento parameter table
test(relationships): add validation edge cases
chore(deps): bump mcp to 1.3.0
```

---

## Release Process

All releases are managed by `scripts/deploy.py`. The full workflow is documented in:

- [`docs/dev/README.md`](docs/dev/README.md) — process overview, branching strategy, CI/CD
- [`scripts/README.md`](scripts/README.md) — deploy command reference

### Versioning

[Semantic Versioning](https://semver.org/) is used:

| Bump | When |
|---|---|
| `MAJOR` | Breaking changes |
| `MINOR` | New backward-compatible features |
| `PATCH` | Backward-compatible bug fixes |

### Changelog Format

Entries follow this format (Keep-a-Changelog is **not** used):

```
* YYYY-MM-DD: vX.Y.Z - <Title> (Hannibal)
  * Change description one
  * Change description two
  * Fix description
```

The deploy script verifies that a correctly formatted entry exists in `CHANGELOG.md`
before running a production bump. Write the entry manually before invoking the script.

---

## Getting Help

- **Bug reports / feature requests**: [GitHub Issues](https://github.com/annibale-x/mcp-memento/issues)
- **Documentation**: `docs/` directory
- **Development docs**: `docs/dev/README.md`

---

## License

Contributions are licensed under the project's [MIT License](LICENSE).