#!/bin/bash

# Test runner shell script for mcp-context-keeper project
# Usage: ./run_tests.sh [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_colored() {
    local color="$1"
    local message="$2"
    echo -e "${color}${message}${NC}"
}

print_header() {
    echo "============================================================"
    print_colored "${BLUE}" "Starting test suite for mcp-context-keeper"
    echo "============================================================"
    echo
}

print_footer() {
    echo
    echo "============================================================"
}

print_success() {
    print_colored "$GREEN" "✅ $1"
}

print_error() {
    print_colored "$RED" "❌ $1"
}

print_warning() {
    print_colored "$YELLOW" "⚠️  $1"
}

print_info() {
    print_colored "$BLUE" "ℹ️  $1"
}

# Check if Python is available
check_python() {
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        print_error "Python is not installed or not in PATH"
        exit 1
    fi

    # Prefer python3 if available
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    else
        PYTHON_CMD="python"
    fi

    echo "Using Python: $($PYTHON_CMD --version 2>&1)"
}

# Parse command line arguments
parse_args() {
    VERBOSE=""
    OUTPUT=""
    LIST=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--verbose)
                VERBOSE="-v"
                shift
                ;;
            -o|--output)
                OUTPUT="-o \"$2\""
                shift 2
                ;;
            --list)
                LIST="--list"
                shift
                ;;
            *)
                print_warning "Unknown option: $1"
                shift
                ;;
        esac
    done
}

# Main function
main() {
    print_header
    check_python

    # Change to script directory
    cd "$(dirname "$0")"

    # Parse arguments
    parse_args "$@"

    # List test files if requested
    if [[ -n "$LIST" ]]; then
        print_info "Listing available test files..."
        echo
        $PYTHON_CMD run_tests.py --list
        print_footer
        exit 0
    fi

    # Run tests
    if [[ -z "$VERBOSE" ]]; then
        print_info "Running tests... (use -v for verbose output)"
        echo
    else
        print_info "Running tests with verbose output..."
        echo
    fi

    # Build command
    CMD="$PYTHON_CMD run_tests.py $VERBOSE $OUTPUT"

    # Execute command
    if eval "$CMD"; then
        TEST_RESULT=0
    else
        TEST_RESULT=$?
    fi

    print_footer

    # Print final result
    if [[ $TEST_RESULT -eq 0 ]]; then
        print_success "All tests passed successfully!"
    else
        print_error "Some tests failed. Exit code: $TEST_RESULT"
    fi

    echo "============================================================"

    exit $TEST_RESULT
}

# Run main function
main "$@"
