# Test Suite Documentation - mcp-memento

## Overview

This test suite validates the functionality, reliability, and integration capabilities of the **mcp-memento** project. The suite ensures that the MCP Context Keeper server operates correctly with SQLite backend and integrates seamlessly with Zed editor.

## Test Architecture

### Test Files Structure

```
tests/
├── test_relationships.py          # Memory relationship functionality tests
├── test_tools.py                  # MCP tools and protocol tests
├── test_server_startup.py         # Server initialization and CLI tests
├── test_import.json               # Sample data for import/export testing
├── run_tests.py                   # Main test runner with reporting
├── README.md                      # This documentation
└── test_data/                     # Test databases (gitignored)
```

### Test Categories

| Category | File | Coverage |
|----------|------|----------|
| **Core Functionality** | `test_relationships.py` | Memory relationships, relationship types, bidirectional queries, filtering |
| **MCP Protocol** | `test_tools.py` | All MCP tools, parameter validation, error handling, search functionality |
| **Server Operations** | `test_server_startup.py` | Server initialization, CLI commands, health checks, configuration |
| **Data Operations** | All files | Import/export, data integrity, JSON validation |

## Running Tests

### Quick Start Commands

```bash
# From project root directory
cd tests
python run_tests.py

# With verbose output
python run_tests.py -v

# Save results to JSON file
python run_tests.py -o results.json

# Run specific test file
python test_relationships.py
python test_tools.py
```

### Platform-Specific Scripts

#### Windows
```batch
run_tests.bat              # Basic test run
run_tests.bat -v           # Verbose output
run_tests.bat -o results.json  # Save results
```

#### Unix/Linux/MacOS
```bash
chmod +x run_tests.sh      # Make executable (first time)
./run_tests.sh             # Basic test run
./run_tests.sh -v          # Verbose output
./run_tests.sh -o results.json  # Save results
```

### Test Runner Options

| Option | Description | Example |
|--------|-------------|---------|
| `-v`, `--verbose` | Enable verbose output | `python run_tests.py -v` |
| `-o`, `--output` | Save results to JSON file | `python run_tests.py -o results.json` |
| `--list` | List available test files | `python run_tests.py --list` |
| `--help` | Show help message | `python run_tests.py --help` |

## Test Coverage

### 1. Memory Relationship Tests (`test_relationships.py`)
- **Relationship Creation**: Valid relationship type creation and validation
- **Bidirectional Queries**: Forward and backward relationship traversal
- **Type Filtering**: Filtering relationships by specific types
- **Error Handling**: Invalid relationship type handling
- **Memory Connectivity**: Graph connectivity and path finding

### 2. MCP Tools Tests (`test_tools.py`)
- **Basic Operations**: `store_memento`, `get_memento`, `update_memento`, `delete_memento`
- **Search Operations**: `search_mementos`, `contextual_memento_search`
- **Relationship Tools**: `create_memento_relationship`, `get_related_mementos`
- **Analytics Tools**: `get_memento_statistics`, `get_recent_memento_activity`
- **Advanced Tools**: `find_path_between_mementos`, `analyze_memento_graph`

### 3. Server Startup Tests (`test_server_startup.py`)
- **CLI Commands**: `--show-config`, `--health`, `--profile` options
- **Server Initialization**: Proper MCP server startup and stdio communication
- **Configuration**: Environment variable and YAML configuration handling
- **Error Handling**: Graceful error recovery and cleanup

### 4. Integration Tests
- **Zed MCP Protocol**: Proper JSON-RPC communication
- **Environment Variables**: `MEMENTO_SQLITE_PATH`, `MEMENTO_TOOL_PROFILE` handling
- **Database Operations**: SQLite connection and transaction management
- **Unicode Support**: UTF-8 encoding for tool descriptions and memory content

## Test Data

### Sample Data (`test_import.json`)
Contains comprehensive test data with:
- **6 sample memories** covering different types (configuration, decision, reference, issue, bug_fix, learning)
- **6 relationships** with various types (depends_on, related_to, caused_by, solution_for, learned_from, context_for)
- **Complete metadata** for testing import/export functionality

### Test Database
- **Location**: `tests/test_data/test_memory.db`
- **Format**: SQLite with optimized schema for mcp-memento
- **Management**: Automatically created/cleaned during tests
- **Git Ignored**: Excluded from version control via `.gitignore`

## Writing New Tests

### Test Template
```python
#!/usr/bin/env python3
"""
Test module description.
"""

import asyncio
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memento import Memento
from memento.models import Memory, MemoryType, RelationshipType

async def main() -> bool:
    """
    Main test function - REQUIRED for test runner compatibility.
    
    Returns:
        bool: True if all tests pass, False otherwise
    """
    print("[INFO] Starting test: Your Test Name")
    
    try:
        # Initialize server
        server = Memento()
        await server.initialize()
        
        # Test 1: Basic functionality
        print("  [TEST] Testing basic operation...")
        # Your test code here
        
        # Test 2: Error handling
        print("  [TEST] Testing error handling...")
        # Your test code here
        
        # Cleanup
        await server.cleanup()
        
        print("[PASS] All tests completed successfully")
        return True
        
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
```

### Test Requirements
1. **Async `main()` function**: Must be async and return boolean
2. **Clear output**: Use `[PASS]`, `[FAIL]`, `[INFO]` prefixes
3. **Resource cleanup**: Always clean up server instances
4. **Error handling**: Catch and report exceptions appropriately
5. **Platform compatibility**: Use ASCII indicators for Windows compatibility

### Best Practices
- **Isolate tests**: Each test should be independent
- **Mock external dependencies**: Use mocks for network/database when appropriate
- **Test edge cases**: Include boundary conditions and error scenarios
- **Document test purpose**: Clear comments explaining what each test validates

## Test Output Format

### Standard Output Format
```
[HH:MM:SS] [LEVEL] Message content
```

### Status Indicators
| Indicator | Meaning | Platform |
|-----------|---------|----------|
| `[PASS]` | Test passed | All platforms |
| `[FAIL]` | Test failed | All platforms |
| `[INFO]` | Informational message | All platforms |
| `[WARN]` | Warning or skipped test | All platforms |
| `[OK]` | Operation successful | All platforms |
| `[ERROR]` | Error occurred | All platforms |

## Continuous Integration

### CI/CD Integration
The test suite is designed for seamless CI/CD integration:

- **Exit codes**: Returns 0 on success, non-zero on failure
- **JSON output**: Machine-readable results for CI reporting
- **No interactive prompts**: Fully automated execution
- **Resource cleanup**: Automatic cleanup of test artifacts

### Environment Variables for CI
```bash
# Database configuration
export MEMENTO_SQLITE_PATH=tests/test_data/ci_test.db

# Tool profile
export MEMENTO_TOOL_PROFILE=extended

# Logging
export MEMENTO_LOG_LEVEL=INFO

# Encoding (important for Windows CI)
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1
```

## Troubleshooting

### Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| **Import errors** | Run from `tests` directory or add project root to Python path |
| **Database errors** | Ensure write permissions to `test_data` directory |
| **Unicode errors** | Set `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1` environment variables |
| **Async errors** | Ensure `main()` is async and uses `asyncio.run()` |
| **Windows path issues** | Use forward slashes in paths and proper escaping |

### Debugging Tests
```bash
# Run single test with debug output
python -m pdb test_relationships.py

# Run with increased verbosity
python test_tools.py 2>&1 | tee debug.log

# Check test database
sqlite3 tests/test_data/test_memory.db ".tables"
```

### Test Database Management
```bash
# Clean test database
rm -f tests/test_data/*.db

# Inspect test database schema
sqlite3 tests/test_data/test_memory.db ".schema"

# Export test data
sqlite3 tests/test_data/test_memory.db ".dump" > backup.sql
```

## Performance Considerations

### Test Optimization
- **Database isolation**: Each test uses isolated database connections
- **Async operations**: All tests use async/await for better performance
- **Resource pooling**: Connection pooling for database operations
- **Cleanup hooks**: Automatic cleanup of test artifacts

### Memory Management
- **Context managers**: Use `async with` for resource management
- **Connection pooling**: Reuse database connections when possible
- **Batch operations**: Group related operations for efficiency
- **Cleanup verification**: Verify resources are properly released

## Version Compatibility

### Python Version Support
- **Primary**: Python 3.10+
- **Tested**: Python 3.11, 3.12
- **Async support**: Full async/await compatibility

### Platform Support
| Platform | Status | Notes |
|----------|--------|-------|
| **Windows** | ✅ Fully supported | ASCII indicators, path handling |
| **Linux** | ✅ Fully supported | UTF-8 native, standard paths |
| **macOS** | ✅ Fully supported | Unix-like, UTF-8 native |

### Dependencies
- **mcp-memento**: Parent package (in development mode)
- **SQLite3**: Included with Python standard library
- **pytest**: Optional for advanced testing patterns
- **asyncio**: Standard library for async operations

## Contributing to Tests

### Adding New Tests
1. **Create test file** in `tests/` directory
2. **Follow template structure** with async `main()` function
3. **Add comprehensive test cases** covering functionality and edge cases
4. **Test locally** before committing
5. **Update documentation** if adding new test categories

### Test Quality Standards
- **Code coverage**: Aim for high coverage of critical paths
- **Readability**: Clear test names and comments
- **Maintainability**: Easy to update when code changes
- **Performance**: Efficient execution without unnecessary delays
- **Reliability**: Consistent results across runs

## License and Attribution

### License
Same as main project - **MIT License**.

### Acknowledgments
Test suite developed as part of the **mcp-memento** project for Zed editor integration. Special focus on Windows compatibility and MCP protocol compliance.

---

*Last Updated: 2026-03-15*  
*Test Suite Version: Compatible with mcp-memento v0.1.14+*
