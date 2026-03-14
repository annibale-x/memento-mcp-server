# Test Suite - mcp-context-keeper

## Overview

This directory contains the complete test suite for the `mcp-context-keeper` project. The test suite is designed to validate the functionality of the MCP Context Keeper with SQLite backend, ensuring reliability and correctness for Zed editor integration.

## Test Structure

### Test Files

| File | Description | Purpose |
|------|-------------|---------|
| `test_relationships.py` | Relationship functionality tests | Tests memory relationships, relationship types, and relationship management |
| `test_tools.py` | MCP tools functionality tests | Tests all MCP tools (store, recall, search, relationships, etc.) |
| `test_import.json` | Test data for import/export | Sample data for testing import/export functionality |
| `run_tests.py` | Main test runner | Orchestrates all tests and provides comprehensive reporting |

### Test Data

| Directory/File | Description |
|----------------|-------------|
| `test_data/` | Test database files (excluded from git via `.gitignore`) |
| `test_import.json` | Pre-configured test memories and relationships |

## Running Tests

### Quick Start

```bash
# From project root
cd test
python run_tests.py

# Or using the provided scripts
./run_tests.sh          # Unix/Linux
run_tests.bat           # Windows
```

### Test Runner Options

```bash
# List available test files
python run_tests.py --list

# Run with verbose output
python run_tests.py -v

# Save results to JSON file
python run_tests.py -o test_results.json

# Run with verbose output and save results
python run_tests.py -v -o test_results.json
```

### Platform-Specific Scripts

#### Windows
```batch
# Basic test run
run_tests.bat

# With options
run_tests.bat -v
run_tests.bat -o results.json
```

#### Unix/Linux/MacOS
```bash
# Make script executable (first time only)
chmod +x run_tests.sh

# Basic test run
./run_tests.sh

# With options
./run_tests.sh -v
./run_tests.sh -o results.json
```

## Test Categories

### 1. Import Tests
- Validates that all required modules can be imported
- Checks ContextKeeper instantiation
- Verifies MemoryType and RelationshipType enumerations

### 2. JSON Validation Tests
- Validates structure of test data files
- Checks required fields in memories and relationships
- Ensures data integrity for import/export operations

### 3. Relationship Tests (`test_relationships.py`)
- Memory relationship creation and management
- Relationship type validation
- Bidirectional relationship queries
- Relationship filtering by type

### 4. MCP Tools Tests (`test_tools.py`)
- Basic tool operations (store, get, update, delete)
- Memory search and recall functionality
- Relationship management tools
- Import/export operations
- Parameter validation and error handling

## Test Output

All test output is in English. The test runner provides:

- **Timestamped logs**: Each log entry includes timestamp and log level
- **Status indicators**: 
  - `[PASS]` or `✅` - Test passed
  - `[FAIL]` or `❌` - Test failed  
  - `[WARN]` or `⚠️` - Test skipped or warning
  - `[UNKN]` or `❓` - Unknown status
- **Detailed reporting**: Test duration, errors, warnings
- **Summary statistics**: Total tests, passed/failed/skipped counts

### Sample Output
```
[14:30:25] [INFO] ============================================================
[14:30:25] [INFO] Starting test suite for mcp-context-keeper
[14:30:25] [INFO] ============================================================
[14:30:25] [INFO] Running import test...
[14:30:25] [INFO]   [PASS] Import test: PASSED
...
[14:30:26] [INFO] ============================================================
[14:30:26] [INFO] TEST SUMMARY
[14:30:26] [INFO] ============================================================
[14:30:26] [INFO] Total tests: 4
[14:30:26] [INFO] Passed:      3 [PASS]
[14:30:26] [INFO] Failed:      1 [FAIL]
[14:30:26] [INFO] Skipped:     0 [WARN]
[14:30:26] [INFO] Total time:  1.23 seconds
[14:30:26] [INFO] [FAIL] 1 TEST(S) FAILED
[14:30:26] [INFO] ============================================================
```

## Test Data

### `test_import.json`
Contains 6 sample memories with 6 relationships, covering:
- Multiple memory types (configuration, decision, reference, issue, bug_fix, learning)
- Various relationship types (depends_on, related_to, caused_by, solution_for, learned_from, context_for)
- Complete metadata for testing import/export functionality

### Test Database
- Location: `test_data/test_memory.db`
- SQLite database with schema compatible with mcp-context-keeper
- Automatically created if it doesn't exist
- Excluded from git via `.gitignore` pattern `*.db`

## Writing New Tests

### Test File Structure
```python
#!/usr/bin/env python3
"""
Test description here.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from context_keeper import ContextKeeper
from context_keeper.models import MemoryType, RelationshipType

async def main():
    """Main test function - REQUIRED for test runner"""
    print("Running tests...")
    
    try:
        # Test code here
        server = ContextKeeper()
        await server.initialize()
        
        # Your tests...
        
        await server.cleanup()
        print("[PASS] All tests passed!")
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

### Requirements for Test Runner Compatibility
1. **Must have a `main()` function** - This is how the test runner identifies executable tests
2. **`main()` should return `True`/`False`** - Indicates test success/failure
3. **Use `[PASS]`/`[FAIL]` prefixes** - For consistent output on all platforms
4. **Clean up resources** - Always clean up server instances and database connections

## Continuous Integration

The test suite is designed to work in CI environments:

- **No interactive prompts** - Fully automated
- **Exit codes** - Returns 0 on success, non-zero on failure
- **JSON output** - Results can be saved for CI reporting
- **Platform independent** - Works on Windows, Linux, and macOS

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure you're running from the `test` directory or have added the parent directory to Python path
2. **Database errors**: Check that SQLite database path is accessible and writable
3. **Unicode errors**: On Windows, all output uses ASCII characters for compatibility
4. **Async errors**: Ensure `main()` is async and uses `asyncio.run()` when executed directly

### Debugging Tests
```bash
# Run single test file directly
python test_relationships.py

# With debug output
python -m pdb test_tools.py
```

## Version Control

- Test files are versioned in git
- Test data (databases) are excluded via `.gitignore`
- Test results/output files should be excluded from version control

## Dependencies

- Python 3.10+
- mcp-context-keeper package (from parent directory)
- SQLite3 (included with Python)

## License

Same as main project - MIT License.

## Acknowledgments

Test suite developed as part of the mcp-context-keeper simplification project for Zed editor integration.