#!/usr/bin/env python3
"""
Build script for MCP Memento package.

This script automates the build, test, and packaging process for the MCP Memento
package. It provides a consistent way to build the package for distribution.

Usage:
    python build/build_memento.py [command]

Commands:
    clean       - Clean build artifacts
    build       - Build package (sdist + wheel)
    test        - Run tests
    check       - Check package with twine
    all         - Run clean, build, test, check
    install     - Install package locally
    version     - Show current version
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
EGG_INFO_DIR = PROJECT_ROOT / "src" / "mcp_memento.egg-info"


def run_command(cmd, cwd=None, capture_output=False):
    """Run a shell command and return the result."""
    if cwd is None:
        cwd = PROJECT_ROOT

    print(f"🚀 Running: {cmd}")
    try:
        if capture_output:
            result = subprocess.run(
                cmd, shell=True, cwd=cwd, capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=True, cwd=cwd, check=True)
            return None
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {cmd}")
        if capture_output and e.stderr:
            print(f"Error output:\n{e.stderr}")
        sys.exit(1)


def clean():
    """Clean build artifacts."""
    print("🧹 Cleaning build artifacts...")

    # Remove distribution directories
    for dir_path in [DIST_DIR, BUILD_DIR]:
        if dir_path.exists():
            print(f"  Removing {dir_path}")
            shutil.rmtree(dir_path)

    # Remove egg-info directory
    if EGG_INFO_DIR.exists():
        print(f"  Removing {EGG_INFO_DIR}")
        shutil.rmtree(EGG_INFO_DIR)

    # Remove Python cache files
    print("  Removing Python cache files...")
    run_command(
        "python -c \"import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]\""
    )
    run_command(
        "python -c \"import pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]\""
    )

    # Remove coverage files
    coverage_files = list(PROJECT_ROOT.glob(".coverage*"))
    for cf in coverage_files:
        print(f"  Removing {cf}")
        cf.unlink()

    print("✅ Clean completed")


def build():
    """Build the package (sdist + wheel)."""
    print("🔨 Building package...")

    # Ensure dist directory exists
    DIST_DIR.mkdir(exist_ok=True)

    # Build package
    run_command("python -m build")

    # List generated files
    dist_files = list(DIST_DIR.glob("*"))
    print(f"📦 Generated {len(dist_files)} distribution file(s):")
    for df in dist_files:
        print(f"  - {df.name} ({df.stat().st_size / 1024:.1f} KB)")

    print("✅ Build completed")


def test():
    """Run tests."""
    print("🧪 Running tests...")

    # Run pytest with coverage
    run_command("python -m pytest tests/ -v --tb=short")

    print("✅ Tests completed")


def check():
    """Check package with twine."""
    print("🔍 Checking package with twine...")

    if not DIST_DIR.exists() or not any(DIST_DIR.iterdir()):
        print("❌ No distribution files found. Run 'build' first.")
        sys.exit(1)

    # Check package
    run_command("twine check dist/*")

    print("✅ Package check completed")


def install():
    """Install package locally."""
    print("📦 Installing package locally...")

    # Find the latest wheel
    wheels = list(DIST_DIR.glob("*.whl"))
    if not wheels:
        print("❌ No wheel files found. Run 'build' first.")
        sys.exit(1)

    latest_wheel = max(wheels, key=lambda p: p.stat().st_mtime)
    print(f"  Installing: {latest_wheel.name}")

    run_command(f"pip install --force-reinstall {latest_wheel}")

    # Verify installation
    version_output = run_command("memento --version", capture_output=True)
    print(f"  Installed version: {version_output}")

    print("✅ Installation completed")


def show_version():
    """Show current version."""
    try:
        # Read version from pyproject.toml
        import tomllib

        with open(PROJECT_ROOT / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        version = data.get("project", {}).get("version", "Unknown")
        print(f"📋 MCP Memento version: {version}")

        # Also show version from __init__.py
        init_file = PROJECT_ROOT / "src" / "memento" / "__init__.py"
        with open(init_file, "r") as f:
            for line in f:
                if "__version__" in line:
                    print(f"  (from __init__.py: {line.strip()})")
                    break
    except Exception as e:
        print(f"❌ Error reading version: {e}")


def run_all():
    """Run clean, build, test, check."""
    clean()
    build()
    test()
    check()
    print("🎉 All tasks completed successfully!")


def main():
    parser = argparse.ArgumentParser(
        description="Build script for MCP Memento package",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "command",
        choices=["clean", "build", "test", "check", "all", "install", "version"],
        help="Command to execute",
    )

    args = parser.parse_args()

    # Execute command
    if args.command == "clean":
        clean()
    elif args.command == "build":
        build()
    elif args.command == "test":
        test()
    elif args.command == "check":
        check()
    elif args.command == "all":
        run_all()
    elif args.command == "install":
        install()
    elif args.command == "version":
        show_version()


if __name__ == "__main__":
    main()
