#!/bin/bash

# Build script for MCP Memento package (Linux/macOS bash version)
#
# Usage:
#   ./build.sh [command]
#
# Commands:
#   clean     - Clean build artifacts
#   build     - Build package (sdist + wheel)
#   test      - Run tests
#   check     - Check package with twine
#   all       - Run clean, build, test, check
#   install   - Install package locally
#   version   - Show current version
#   help      - Show this help

set -e

# Project directories
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_DIR="$PROJECT_ROOT/build"
EGG_INFO_DIR="$PROJECT_ROOT/src/mcp_memento.egg-info"

# Colors for output
if [ -t 1 ]; then
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    RESET='\033[0m'
else
    GREEN=''
    RED=''
    YELLOW=''
    BLUE=''
    RESET=''
fi

# Function to print colored output
print_color() {
    echo -e "${1}${2}${RESET}"
}

# Function to run command and check error
run_command() {
    echo "🚀 Running: $1"
    eval "$1"
    if [ $? -ne 0 ]; then
        print_color "$RED" "❌ Command failed: $1"
        exit 1
    fi
}

# Clean build artifacts
clean() {
    print_color "$BLUE" "🧹 Cleaning build artifacts..."

    # Remove distribution directories
    for dir_path in "$DIST_DIR" "$BUILD_DIR"; do
        if [ -d "$dir_path" ]; then
            echo "  Removing $dir_path"
            rm -rf "$dir_path"
        fi
    done

    # Remove egg-info directory
    if [ -d "$EGG_INFO_DIR" ]; then
        echo "  Removing $EGG_INFO_DIR"
        rm -rf "$EGG_INFO_DIR"
    fi

    # Remove Python cache files
    echo "  Removing Python cache files..."
    find "$PROJECT_ROOT" -type f -name "*.py[co]" -delete
    find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

    # Remove coverage files
    echo "  Removing coverage files..."
    find "$PROJECT_ROOT" -name ".coverage*" -delete

    print_color "$GREEN" "✅ Clean completed"
}

# Build the package
build() {
    print_color "$BLUE" "🔨 Building package..."

    # Ensure dist directory exists
    mkdir -p "$DIST_DIR"

    # Build package
    run_command "python -m build"

    # List generated files
    print_color "$BLUE" "📦 Generated distribution files:"
    for file in "$DIST_DIR"/*; do
        if [ -f "$file" ]; then
            size_kb=$(( $(stat -f%z "$file" 2>/dev/null || stat -c%s "$file") / 1024 ))
            echo "  - $(basename "$file") (${size_kb} KB)"
        fi
    done

    print_color "$GREEN" "✅ Build completed"
}

# Run tests
test() {
    print_color "$BLUE" "🧪 Running tests..."
    run_command "python -m pytest tests/ -v --tb=short"
    print_color "$GREEN" "✅ Tests completed"
}

# Check package with twine
check() {
    print_color "$BLUE" "🔍 Checking package with twine..."

    # Check if distribution files exist
    if [ ! -d "$DIST_DIR" ] || [ -z "$(ls -A "$DIST_DIR" 2>/dev/null)" ]; then
        print_color "$RED" "❌ No distribution files found. Run 'build' first."
        exit 1
    fi

    run_command "twine check $DIST_DIR/*"
    print_color "$GREEN" "✅ Package check completed"
}

# Install package locally
install() {
    print_color "$BLUE" "📦 Installing package locally..."

    # Find the latest wheel
    latest_wheel=""
    latest_time=0

    for wheel in "$DIST_DIR"/*.whl; do
        if [ -f "$wheel" ]; then
            file_time=$(stat -f%m "$wheel" 2>/dev/null || stat -c%Y "$wheel")
            if [ "$file_time" -gt "$latest_time" ]; then
                latest_time=$file_time
                latest_wheel="$wheel"
            fi
        fi
    done

    if [ -z "$latest_wheel" ]; then
        print_color "$RED" "❌ No wheel files found. Run 'build' first."
        exit 1
    fi

    echo "  Installing: $(basename "$latest_wheel")"
    run_command "pip install --force-reinstall \"$latest_wheel\""

    # Verify installation
    version_output=$(memento --version 2>/dev/null || echo "Unknown")
    echo "  Installed version: $version_output"

    print_color "$GREEN" "✅ Installation completed"
}

# Show current version
version() {
    print_color "$BLUE" "📋 MCP Memento version information:"

    # Try to read from pyproject.toml
    if [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
        pyproject_version=$(grep -i "version" "$PROJECT_ROOT/pyproject.toml" | head -1 | cut -d'=' -f2 | tr -d ' "')
        if [ -n "$pyproject_version" ]; then
            echo "  From pyproject.toml: $pyproject_version"
        fi
    fi

    # Try to read from __init__.py
    if [ -f "$PROJECT_ROOT/src/memento/__init__.py" ]; then
        init_version=$(grep "__version__" "$PROJECT_ROOT/src/memento/__init__.py" | head -1 | cut -d'=' -f2 | tr -d ' "')
        if [ -n "$init_version" ]; then
            echo "  From __init__.py: $init_version"
        fi
    fi
}

# Run all tasks
all() {
    clean
    build
    test
    check
    print_color "$GREEN" "🎉 All tasks completed successfully!"
}

# Show help
help() {
    echo "MCP Memento Build Script (Linux/macOS Bash)"
    echo ""
    echo "Usage:"
    echo "  ./build.sh [command]"
    echo ""
    echo "Commands:"
    echo "  clean     - Clean build artifacts"
    echo "  build     - Build package (sdist + wheel)"
    echo "  test      - Run tests"
    echo "  check     - Check package with twine"
    echo "  all       - Run clean, build, test, check"
    echo "  install   - Install package locally"
    echo "  version   - Show current version"
    echo "  help      - Show this help"
    echo ""
    echo "Examples:"
    echo "  ./build.sh all"
    echo "  ./build.sh build && ./build.sh install"
}

# Main execution
if [ $# -eq 0 ]; then
    help
    exit 0
fi

# Execute the requested command
case "$1" in
    clean)
        clean
        ;;
    build)
        build
        ;;
    test)
        test
        ;;
    check)
        check
        ;;
    all)
        all
        ;;
    install)
        install
        ;;
    version)
        version
        ;;
    help)
        help
        ;;
    *)
        print_color "$RED" "❌ Unknown command: $1"
        echo ""
        help
        exit 1
        ;;
esac
