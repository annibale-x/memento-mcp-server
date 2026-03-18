# Contributing to MCP Memento

Thank you for your interest in contributing to MCP Memento! This document provides guidelines and instructions for contributing to the project.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. We aim to foster an inclusive and welcoming community.

## Getting Started

### Finding Issues to Work On
- Check the [GitHub Issues](https://github.com/annibale-x/mcp-memento/issues) for bugs and feature requests
- Look for issues tagged with `good-first-issue` or `help-wanted`
- Discuss proposed changes in an issue before starting work

### Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/annibale-x/mcp-memento.git
   cd mcp-memento
   ```

2. **Install in development mode**:
   ```bash
   pip install -e ".[dev]"
   ```

3. **Run tests to ensure everything works**:
   ```bash
   pytest
   ```

### Project Structure
```
mcp-memento/
├── src/                          # Source code
│   └── memento/          # Main package
├── docs/                        # Documentation
├── tests/                       # Test suite
├── pyproject.toml              # Package configuration
└── README.md                   # Main documentation
```

## Code Style

### Python Code
- Follow [PEP 8](https://pep8.org/) guidelines
- Use type hints for all function signatures
- Write descriptive docstrings using Google style
- Maximum line length: 88 characters (Black formatting)

### Import Order
```python
# Standard library imports
import os
import sys
from typing import Dict, List

# Third-party imports
import sqlite3
from mcp import Client

# Local imports
from .config import Config
from .models import Memory
```

### Naming Conventions
- **Classes**: `CamelCase`
- **Functions/Methods**: `snake_case`
- **Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: `_private` (single underscore)
- **Very Private**: `__very_private` (double underscore)

### Code Formatting
We use:
- **Black** for code formatting
- **isort** for import sorting
- **mypy** for type checking

Format your code before submitting:
```bash
black src/ tests/
isort src/ tests/
mypy src/
```

## Testing

### Test Structure
- Write tests for all new functionality
- Follow the existing test patterns
- Use descriptive test names
- Group related tests in classes

### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_memory_operations.py

# Run with coverage
pytest --cov=src tests/

# Run with verbose output
pytest -v

# Run a specific test
pytest tests/test_memory_operations.py::test_store_memory -v
```

### Test Guidelines
1. **Isolation**: Tests should not depend on each other
2. **Speed**: Keep tests fast
3. **Clarity**: Test names should describe what they test
4. **Coverage**: Aim for high test coverage
5. **Mocking**: Use mocks for external dependencies

### Test Database
- Tests use in-memory SQLite databases
- Each test creates its own database
- Clean up resources in teardown methods

## Documentation

### Documentation Structure
```
docs/
├── TOOLS.md              # MCP tools reference
├── DECAY_SYSTEM.md       # Confidence system documentation
├── RULES.md              # Usage rules and best practices
├── RELATIONSHIPS.md      # Relationship types reference
├── AGENT_CONFIGURATION.md # Agent prompt templates and configuration
├── INTEGRATION.md        # Integration overview
├── integrations/         # Detailed integration guides
│   ├── IDE.md            # IDE integration (Zed, Cursor, Windsurf, etc.)
│   ├── PYTHON.md         # Python MCP client and programmatic usage
│   ├── AGENT.md          # CLI agent integration (Gemini, Claude, etc.)
│   └── API.md            # HTTP REST API, Node.js SDK, Docker deployment
└── dev/                  # Development documentation
    ├── DEV.md            # Development workflow and release process
    └── SCHEMA.md         # Database schema documentation
```

**Note**: This file (`CONTRIBUTING.md`) is located in the project root, following GitHub conventions for contributor guidelines. For detailed technical documentation, see the `docs/` directory.

### Writing Documentation
- Use clear, concise language
- Include code examples
- Update documentation when changing APIs
- Use Markdown formatting
- Include table of contents for long documents

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
        title: Descriptive title for the memento
        content: Detailed content of the memento
        tags: Optional list of tags for categorization
        importance: Importance score 0.0-1.0 (default 0.5)

    Returns:
        The ID of the newly created memento

    Raises:
        ValueError: If required parameters are missing
        DatabaseError: If database operation fails

    Examples:
        >>> memory_id = store_memento(
        ...     type="solution",
        ...     title="Fixed Redis timeout",
        ...     content="Increased timeout to 30s...",
        ...     tags=["redis", "timeout"],
        ...     importance=0.8,
        ... )
    """
```

## Pull Request Process

### Before Submitting
1. **Discuss changes**: Open an issue to discuss major changes
2. **Update documentation**: Ensure docs reflect your changes
3. **Add tests**: Include tests for new functionality
4. **Run tests**: Ensure all tests pass
5. **Format code**: Run Black and isort

### Creating a Pull Request
1. **Fork the repository**
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
4. **Commit with Conventional Commits**:
   ```bash
   git commit -m "feat(memory): add bulk import functionality"
   ```
5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Open a Pull Request**

### Pull Request Guidelines
- **Title**: Use Conventional Commits format
- **Description**: Clearly describe what the PR does and why
- **Linked issues**: Reference related issues
- **Small PRs**: Keep changes focused and manageable
- **Review ready**: Ensure CI passes and code is formatted

### Conventional Commits
Use the following commit message format:
```
<type>(<scope>): <description>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions or changes
- `chore`: Maintenance tasks

**Examples**:
- `feat(confidence): add automatic decay scheduling`
- `fix(search): resolve memory leak in full-text search`
- `docs(api): update Python API examples`
- `test(memory): add tests for relationship validation`

## Release Process

> **Note**: For the complete automated release workflow (tag conventions, deploy script, CI/CD), see [docs/dev/DEV.md](docs/dev/DEV.md).

### Versioning
We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist
1. **Update version** in `pyproject.toml`
2. **Update CHANGELOG.md** with release notes
3. **Run full test suite**
4. **Build distribution packages**:
   ```bash
   python -m build
   ```
5. **Test installation** from built packages
6. **Create GitHub release** with tag
7. **Publish to PyPI** (maintainers only)

### Changelog Format
```markdown
## [Version] - YYYY-MM-DD

### Added
- New feature description

### Changed
- Changes to existing functionality

### Fixed
- Bug fixes

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Security
- Security-related changes
```

## Development Workflow

### Daily Development
```bash
# 1. Sync with upstream
git fetch upstream
git merge upstream/main

# 2. Create feature branch
git checkout -b feature/your-feature

# 3. Make changes and test
# ... make changes ...
pytest

# 4. Format code
black src/ tests/
isort src/ tests/

# 5. Commit changes
git add .
git commit -m "feat: your feature description"

# 6. Push and create PR
git push origin feature/your-feature
```

### Debugging
```bash
# Run with debug logging
MEMENTO_LOG_LEVEL=DEBUG python -m memento

# Use pdb for debugging
import pdb; pdb.set_trace()

# Profile performance
python -m cProfile -o profile.stats run_mcp_memento.py
```

## Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **Discussions**: For questions and general discussion
- **Documentation**: Check the `docs/` directory for detailed guides
- **Development Docs**: See `docs/dev/` for technical development information

## License

By contributing to MCP Memento, you agree that your contributions will be licensed under the project's MIT License.

---

Thank you for contributing to MCP Memento! Your help makes this project better for everyone.
