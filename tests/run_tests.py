#!/usr/bin/env python3
"""
Test runner for mcp-memento project using pytest.

This script runs the complete test suite with clean, professional output.
All output is in English without emojis or colors.

Usage:
    python run_tests.py [options] [test_files...]

Examples:
    python run_tests.py                     # Run all tests
    python run_tests.py -v                  # Run all tests with verbose output
    python run_tests.py test_server_startup.py  # Run specific test file
    python run_tests.py --list              # List all test files
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Add parent directory to path to import memento for any direct imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pytest

    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False
    print("ERROR: pytest is not installed. Install with: pip install pytest")
    sys.exit(1)


def list_test_files(test_dir: Path) -> list[str]:
    """List all test files in the tests directory."""
    test_files = []
    for test_file in test_dir.glob("test_*.py"):
        if test_file.name != "run_tests.py":
            test_files.append(str(test_file.relative_to(test_dir)))

    return sorted(test_files)


def print_test_summary(start_time: float, exit_code: int) -> None:
    """Print test execution summary."""
    duration = time.time() - start_time

    print("\n" + "=" * 60)
    print("TEST EXECUTION SUMMARY")
    print("=" * 60)

    if exit_code == 0:
        print("RESULT: ALL TESTS PASSED")
    elif exit_code == 1:
        print("RESULT: SOME TESTS FAILED")
    elif exit_code == 2:
        print("RESULT: TEST EXECUTION WAS INTERRUPTED")
    elif exit_code == 3:
        print("RESULT: INTERNAL ERROR IN TEST EXECUTION")
    elif exit_code == 4:
        print("RESULT: USAGE ERROR")
    else:
        print(f"RESULT: UNKNOWN EXIT CODE ({exit_code})")

    print(f"DURATION: {duration:.2f} seconds")
    print("=" * 60)


def main() -> int:
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="Run mcp-memento test suite using pytest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Categories:
  1. Server Startup     - test_server_startup.py
  2. Relationships      - test_relationships.py
  3. Tools              - test_tools.py
  4. CLI                - test_cli.py
  5. Standard Pytest    - test_standard_pytest.py

Examples:
  Run all tests:              python run_tests.py
  Run with verbose output:    python run_tests.py -v
  Run specific test file:     python run_tests.py test_server_startup.py
  Run tests matching pattern: python run_tests.py -k "test_config"
  List all test files:        python run_tests.py --list
  Run with minimal output:    python run_tests.py -q
        """,
    )

    parser.add_argument(
        "test_files",
        nargs="*",
        help="Specific test files to run (default: run all tests)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Increase verbosity of test output",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Reduce verbosity of test output",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available test files and exit",
    )

    parser.add_argument(
        "-k",
        "--keyword",
        type=str,
        help="Only run tests matching the given substring expression",
    )

    parser.add_argument(
        "-x",
        "--exitfirst",
        action="store_true",
        help="Exit instantly on first error or failed test",
    )

    parser.add_argument(
        "--tb",
        choices=["short", "long", "line", "no"],
        default="short",
        help="Set the traceback style for test failures (default: short)",
    )

    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Suppress header and summary output from this script",
    )

    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report (requires pytest-cov)",
    )

    args = parser.parse_args()

    test_dir = Path(__file__).parent

    # List test files if requested
    if args.list:
        test_files = list_test_files(test_dir)
        print(f"Available test files in {test_dir}:")
        for i, test_file in enumerate(test_files, 1):
            print(f"  {i:2}. {test_file}")
        print(f"\nTotal: {len(test_files)} test files")
        return 0

    # Build pytest arguments
    pytest_args = []

    # Set verbosity
    if args.quiet:
        pytest_args.append("-q")
    elif args.verbose:
        pytest_args.append("-v")
    else:
        # Default: moderate verbosity
        pytest_args.append("-v")

    # Set traceback style
    pytest_args.append(f"--tb={args.tb}")

    # Exit first if requested
    if args.exitfirst:
        pytest_args.append("-x")

    # Keyword expression
    if args.keyword:
        pytest_args.append(f"-k={args.keyword}")

    # Coverage if requested
    if args.coverage:
        pytest_args.extend(["--cov=memento", "--cov-report=term-missing"])

    # Add test files or directory
    if args.test_files:
        # Convert relative paths to absolute
        test_paths = []
        for test_file in args.test_files:
            test_path = test_dir / test_file
            if test_path.exists():
                test_paths.append(str(test_path))
            else:
                print(f"ERROR: Test file not found: {test_file}")
                return 1
        pytest_args.extend(test_paths)
    else:
        # Run all tests in the test directory
        pytest_args.append(str(test_dir))

    # Print header
    if not args.no_header:
        print("=" * 60)
        print("MCP CONTEXT KEEPER - TEST SUITE")
        print("=" * 60)
        print(f"Python: {sys.version.split()[0]}")
        print(f"Test directory: {test_dir}")
        print(f"Pytest arguments: {' '.join(pytest_args)}")
        print("-" * 60)

    # Run pytest
    start_time = time.time()

    try:
        exit_code = pytest.main(pytest_args)
    except KeyboardInterrupt:
        print("\n\nTEST EXECUTION INTERRUPTED BY USER")
        exit_code = 2
    except Exception as e:
        print(f"\nERROR: Failed to execute tests: {e}")
        exit_code = 3

    # Print summary
    if not args.no_header:
        print_test_summary(start_time, exit_code)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
