#!/bin/bash

# Shell test runner for mcp-memento project
# Usage: ./run_tests.sh [options] [test_files...]
#
# Options:
#   -v, --verbose      Increase verbosity of test output
#   -q, --quiet        Reduce verbosity of test output
#   --list             List all available test files and exit
#   -k EXPRESSION      Only run tests matching the given substring expression
#   -x, --exitfirst    Exit instantly on first error or failed test
#   --tb STYLE         Set traceback style (short, long, line, no)
#   --no-header        Suppress header and summary output
#   --coverage         Generate coverage report (requires pytest-cov)
#   -h, --help         Show this help message

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="$SCRIPT_DIR"
PROJECT_NAME="mcp-memento"

# Function to print error messages
print_error() {
    printf "ERROR: %s\n" "$1" >&2
}

# Function to print usage information
print_usage() {
    cat << EOF
$PROJECT_NAME Test Runner
Usage: $0 [options] [test_files...]

Options:
  -v, --verbose      Increase verbosity of test output
  -q, --quiet        Reduce verbosity of test output
  --list             List all available test files and exit
  -k EXPRESSION      Only run tests matching the given substring expression
  -x, --exitfirst    Exit instantly on first error or failed test
  --tb STYLE         Set traceback style (short, long, line, no) [default: short]
  --no-header        Suppress header and summary output
  --coverage         Generate coverage report (requires pytest-cov)
  -h, --help         Show this help message

Test Categories:
  1. Server Startup     - test_server_startup.py
  2. Relationships      - test_relationships.py
  3. Tools              - test_tools.py
  4. CLI                - test_cli.py
  5. Standard Pytest    - test_standard_pytest.py

Examples:
  $0                           # Run all tests
  $0 -v                       # Run all tests with verbose output
  $0 test_server_startup.py   # Run specific test file
  $0 -k "test_config"         # Run tests matching pattern
  $0 --list                   # List all test files
  $0 -q                       # Run with minimal output
EOF
}

# Function to list test files
list_test_files() {
    printf "Available test files in %s:\n" "$TEST_DIR"
    local count=0
    for test_file in "$TEST_DIR"/test_*.py; do
        if [[ "$(basename "$test_file")" != "run_tests.py" ]]; then
            ((count++)) || true
            printf "  %2d. %s\n" "$count" "$(basename "$test_file")"
        fi
    done
    printf "\nTotal: %d test files\n" "$count"
}

# Function to calculate duration
calculate_duration() {
    local start_time=$1
    local end_time=$2
    local duration=$(echo "$end_time - $start_time" | bc)
    printf "%.2f" "$duration"
}

# Function to print test summary
print_test_summary() {
    local start_time=$1
    local exit_code=$2

    printf "\n"
    printf "============================================================\n"
    printf "TEST EXECUTION SUMMARY\n"
    printf "============================================================\n"

    case $exit_code in
        0)
            printf "RESULT: ALL TESTS PASSED\n"
            ;;
        1)
            printf "RESULT: SOME TESTS FAILED\n"
            ;;
        2)
            printf "RESULT: TEST EXECUTION WAS INTERRUPTED\n"
            ;;
        3)
            printf "RESULT: INTERNAL ERROR IN TEST EXECUTION\n"
            ;;
        4)
            printf "RESULT: USAGE ERROR\n"
            ;;
        *)
            printf "RESULT: UNKNOWN EXIT CODE (%d)\n" "$exit_code"
            ;;
    esac

    local end_time
    end_time=$(date +%s.%N)
    local duration
    duration=$(calculate_duration "$start_time" "$end_time")

    printf "DURATION: %s seconds\n" "$duration"
    printf "============================================================\n"
}

# Main execution
main() {
    # Parse command line arguments
    local verbose=""
    local quiet=""
    local list=""
    local keyword=""
    local exitfirst=""
    local tb_style="short"
    local no_header=""
    local coverage=""
    local test_files=()

    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--verbose)
                verbose="-v"
                shift
                ;;
            -q|--quiet)
                quiet="-q"
                shift
                ;;
            --list)
                list="--list"
                shift
                ;;
            -k)
                if [[ -z "${2:-}" ]]; then
                    print_error "Option -k requires an argument"
                    return 1
                fi
                keyword="-k $2"
                shift 2
                ;;
            -x|--exitfirst)
                exitfirst="-x"
                shift
                ;;
            --tb)
                if [[ -z "${2:-}" ]]; then
                    print_error "Option --tb requires an argument"
                    return 1
                fi
                tb_style="$2"
                shift 2
                ;;
            --no-header)
                no_header="--no-header"
                shift
                ;;
            --coverage)
                coverage="--coverage"
                shift
                ;;
            -h|--help)
                print_usage
                return 0
                ;;
            -*)
                print_error "Unknown option: $1"
                print_usage
                return 1
                ;;
            *)
                test_files+=("$1")
                shift
                ;;
        esac
    done

    # Change to test directory
    cd "$TEST_DIR" || {
        print_error "Cannot change to test directory: $TEST_DIR"
        return 1
    }

    # Check if Python is available
    if ! command -v python >/dev/null 2>&1; then
        print_error "Python is not installed or not in PATH"
        return 1
    fi

    # Check if pytest is available via the test runner
    if ! python -c "import pytest" >/dev/null 2>&1; then
        print_error "pytest is not installed. Install with: pip install pytest"
        return 1
    fi

    # Handle list option
    if [[ -n "$list" ]]; then
        list_test_files
        return 0
    fi

    # Build command
    local cmd="python run_tests.py"

    [[ -n "$verbose" ]] && cmd="$cmd $verbose"
    [[ -n "$quiet" ]] && cmd="$cmd $quiet"
    [[ -n "$keyword" ]] && cmd="$cmd $keyword"
    [[ -n "$exitfirst" ]] && cmd="$cmd $exitfirst"
    [[ "$tb_style" != "short" ]] && cmd="$cmd --tb $tb_style"
    [[ -n "$no_header" ]] && cmd="$cmd $no_header"
    [[ -n "$coverage" ]] && cmd="$cmd $coverage"

    # Add test files if specified
    if [[ ${#test_files[@]} -gt 0 ]]; then
        for file in "${test_files[@]}"; do
            if [[ ! -f "$file" ]]; then
                print_error "Test file not found: $file"
                return 1
            fi
            cmd="$cmd $file"
        done
    fi

    # Print header
    if [[ -z "$no_header" ]]; then
        printf "============================================================\n"
        printf "MCP MEMENTO - TEST SUITE\n"
        printf "============================================================\n"
        printf "Python: %s\n" "$(python --version 2>&1 | cut -d' ' -f2)"
        printf "Test directory: %s\n" "$TEST_DIR"
        printf "Command: %s\n" "$cmd"
        printf "------------------------------------------------------------\n"
    fi

    # Run tests
    local start_time
    start_time=$(date +%s.%N)
    local exit_code=0

    set +e
    eval "$cmd"
    exit_code=$?
    set -e

    # Print summary
    if [[ -z "$no_header" ]]; then
        print_test_summary "$start_time" "$exit_code"
    fi

    return $exit_code
}

# Handle script interruption
trap 'printf "\nTest execution interrupted by user\n"; exit 2' INT

# Run main function
if main "$@"; then
    exit 0
else
    exit $?
fi
