# Scripts Directory

This directory contains build scripts and utilities for the MCP Memento package.

## 📦 Build Scripts

### Python Script (`build_memento.py`)
The main build script written in Python. Provides the most comprehensive functionality.

**Usage:**
```bash
python scripts/build_memento.py [command]
```

**Commands:**
- `clean` - Clean build artifacts
- `build` - Build package (sdist + wheel)
- `test` - Run tests
- `check` - Check package with twine
- `all` - Run clean, build, test, check
- `install` - Install package locally
- `version` - Show current version

### Windows Batch Script (`build.bat`)
Windows-compatible build script.

**Usage:**
```batch
scripts\build.bat [command]
```

### Linux/macOS Bash Script (`build.sh`)
Unix-compatible build script.

**Usage:**
```bash
./scripts/build.sh [command]
```

## 🚀 Quick Start

### Complete Build Process
```bash
# Using Python script (recommended)
python scripts/build_memento.py all

# Using platform-specific script
# Windows:
scripts\build.bat all

# Linux/macOS:
./scripts/build.sh all
```

### Build and Install Locally
```bash
python scripts/build_memento.py build
python scripts/build_memento.py install
```

## 📁 Directory Structure

```
scripts/
├── README.md          # This file
├── build_memento.py   # Main Python build script
├── build.bat          # Windows batch script
└── build.sh           # Linux/macOS bash script
```

## 🔧 Build Artifacts

When you run the build process, the following artifacts are generated:

- `dist/` - Distribution files (`.whl` and `.tar.gz`)
- `build/` - Temporary build directory (excluded from git)
- `src/*.egg-info/` - Package metadata (excluded from git)

## 🧹 Cleaning

To remove all build artifacts:
```bash
python scripts/build_memento.py clean
```

## 🧪 Testing

Run the test suite:
```bash
python scripts/build_memento.py test
```

## 🔍 Package Validation

Check the built package with twine:
```bash
python scripts/build_memento.py check
```

## 📋 Version Information

Show current package version:
```bash
python scripts/build_memento.py version
```

## ⚙️ Configuration

The build scripts read configuration from:
- `pyproject.toml` - Package metadata and dependencies
- `MANIFEST.in` - Files to include in distribution
- `README.md` - Package description (used as long_description)

## 🐛 Troubleshooting

### Common Issues

1. **"No distribution files found"**
   - Run `build` command first: `python scripts/build_memento.py build`

2. **"Command not found"** (Windows)
   - Use `build.bat` instead of `build.sh`

3. **Permission denied** (Linux/macOS)
   - Make scripts executable: `chmod +x build/build.sh`

4. **Twine warnings about long_description**
   - Ensure `pyproject.toml` has proper `readme` configuration

### Dependencies

Make sure you have the required build tools installed:
```bash
pip install build twine
```

## 📚 Related Documentation

- [PyPI Packaging Guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
- [setuptools Documentation](https://setuptools.pypa.io/en/latest/)
- [MCP Memento Main README](../README.md)

## 🤝 Contributing

When adding new build features:
1. Update all three scripts (Python, Batch, Bash)
2. Test on your target platform
3. Update this README if necessary

## 📄 License

Same as the main project - MIT License.