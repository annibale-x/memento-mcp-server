# Changelog

* 2026-03-14: v0.1.12 - Zed MCP integration fix and character encoding issues (Hannibal)
  * Fixed Zed MCP server integration by resolving hidden character issues in configuration
  * Identified and resolved copy-paste invisible character problems in environment variables
  * Enhanced Windows compatibility with proper UTF-8 encoding for tool descriptions
  * Improved error handling for MCP protocol communication with Zed editor
  * Added comprehensive debugging tools for Zed MCP integration testing

* 2026-03-14: v0.1.11 - Complete test suite reconstruction and bug fixes (Hannibal)
  * Fixed 18 failing tests in the test suite (from 18 to 0 failures)
  * Resolved event loop issues in CLI health check and export/import tests
  * Fixed database test failures with proper ID handling and SearchQuery usage
  * Corrected sys.exit assertion problems in CLI show-config tests
  * Fixed string matching issues in health check timeout tests
  * Resolved error handling class string representation assertions
  * Fixed server test issues with mock handlers and cleanup expectations
  * Added missing Config.ALLOW_RELATIONSHIP_CYCLES attribute
  * Fixed await syntax bug in SQLiteMemoryDatabase.update_memory()
  * Added missing RelationshipProperties import to database interface

* 2026-03-14: v0.1.10 - Path resolution and Windows compatibility fixes (Hannibal)
  * Fixed SQLite database path issues on Windows systems
  * Changed default database path from `.db` to `context.db` in configuration
  * Fixed indentation error in `context_keeper.py` wrapper script
  * Improved environment variable handling for configuration overrides
  * Enhanced Windows compatibility for database file operations

* 2026-03-14: v0.1.9 - Code quality analysis and dead code removal (Hannibal)
  * Removed unused `SimpleGraph` and graph algorithms classes
  * Removed unused `MemoryNode` and graph-related models
  * Removed unused utilities like `datetime_utils.py` and `error_handling.py`
  * Migrated inline tools definitions from `server.py` to `tools/definitions.py`
  * Fixed test suite by using explicit asserts instead of return values
  * Cleaned up leftover testing artifacts and databases

All notable changes to the mcp-context-keeper project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.8] - 2026-03-14

### Changed
- Renamed database files for better clarity:
  - `sqlite_backend.py` → `engine.py` (database engine/connection management)
  - `sqlite_database.py` → `interface.py` (domain interface for memories and relationships)
- Renamed `backends` directory to `database` for accurate representation
- Updated all imports to reflect new file structure
- Improved code organization and separation of concerns

### Fixed
- Removed unused work files (`simple_sqlite_db.py`)
- Cleaned up import paths after file reorganization
- Ensured all tests pass with new file structure

## [0.1.7] - 2026-03-15

### Added
- `help_memory_tools_usage` tool for comprehensive guidance on persistent vs session memory usage
- Clear distinction guidance to prevent confusion with Serena Context Server tools
- Decision matrices and practical examples for tool selection
- Renamed guide tool from `get_persistent_memory_guide` to `help_memory_tools_usage` for better LLM discoverability
- Best practices documentation for persistent memory usage

### Changed
- Updated tool count: Core profile now has 10 tools (including guide tool)
- Enhanced documentation with persistent vs session memory distinction
- Improved README.md with usage guidance and common mistakes to avoid

### Fixed
- Potential confusion between persistent memory tools (`_persistent` suffix) and session memory tools (no suffix)
- Documentation inconsistencies regarding tool naming conventions
- Integration guidance for using multiple MCP context servers together


## [0.1.6] - 2026-03-14

### Added
- Persistent tool naming convention to avoid conflicts with Serena Context Server
- Clear distinction between persistent (cross-session) and session memory storage

### Changed
- Updated environment variable prefixes from MEMORY_ to CONTEXT_
- Changed default database path to ~/.mcp-context-keeper/context.db
- Updated configuration file names to context-keeper.yaml
- Fixed module entry point to properly handle CLI arguments
- Improved Zed editor MCP configuration compatibility
- **BREAKING CHANGE**: Renamed all MCP tools with `_persistent` suffix:
  - Core tools: `store_memory` → `store_persistent_memory`, `get_memory` → `get_persistent_memory`, etc.
  - Extended tools: `get_memory_statistics` → `get_persistent_memory_statistics`, etc.
  - Advanced tools: `find_memory_path` → `find_path_between_persistent_memories`, etc.

### Fixed
- Module execution with `python -m context_keeper` now works correctly
- CLI arguments like `--health` and `--show-config` are properly handled
- Environment variable support for Zed editor integration
- Configuration file path references
- Tool registry mapping with new persistent tool names

## [0.1.5] - 2026-03-13

### Added
- SimpleGraph class to replace NetworkX dependency
- Lightweight in-memory graph structure for SQLite backend
- JSON serialization support for SimpleGraph
- Integration tests for SimpleGraph with SQLite backend

### Changed
- Replaced NetworkX dependency with custom SimpleGraph implementation
- Updated SQLite backend to use SimpleGraph instead of NetworkX
- Reduced external dependencies from 6 to 5 packages
- Updated project documentation to reflect NetworkX removal

### Fixed
- JSON serialization issues with edge tuple keys
- Graph loading when tables don't exist yet
- Documentation inconsistencies regarding dependencies

### Removed
- NetworkX dependency (networkx>=3.0.0)
- External graph library dependency

## [0.1.4] - 2026-03-13

### Added
- SQLite-only backend support (removed all other backends)
- Simplified configuration with YAML + env vars
- MemoryNode.to_database_properties() method for SQLite compatibility
- Updated documentation reflecting SQLite-only architecture

### Changed
- Simplified project structure by removing non-SQLite backends
- Updated README.md to reflect SQLite-only support
- Removed references to Neo4j, FalkorDB, Memgraph, Turso, and Cloud backends
- Updated memory_parser.py documentation

### Fixed
- Critical bug preventing memory storage in SQLite backend
- Documentation inconsistencies
- Import/export functionality for SQLite

### Removed
- Multi-tenant support
- All non-SQLite backend implementations
- Admin-only tools and migration tools
- Advanced analytics modules not essential for core functionality

## [0.1.3] - 2026-03-12

### Added
- Initial simplified version for Zed editor integration
- Core MCP tools for memory management
- SQLite backend with zero dependencies
- Basic configuration system

### Changed
- Project renamed to mcp-context-keeper
- Focus on context-aware memory management for MCP servers
- Simplified architecture for Zed editor compatibility

## [0.1.2] - 2026-03-11

### Added
- Export/import functionality for memories
- Health check CLI command
- Basic relationship management

### Fixed
- SQLite schema initialization issues
- Memory parsing utilities

## [0.1.1] - 2026-03-10

### Added
- Initial SQLite backend implementation
- Core memory models (Memory, MemoryContext, Relationship)
- Basic tool handlers for MCP protocol

### Changed
- Ported from original MemoryGraph project
- Simplified for single-backend operation

## [0.1.0] - 2026-03-09

### Added
- Initial project setup
- MCP server foundation
- Basic project structure

---

## Versioning Scheme

- **Major version (0.x.y)**: Breaking changes to API or architecture
- **Minor version (0.x.y)**: New features and enhancements
- **Patch version (0.x.y.z)**: Bug fixes and minor improvements

## Migration Notes

### From v0.1.3 to v0.1.4
- This version removes all non-SQLite backend support
- Configuration is now simplified with only SQLite options
- Multi-tenant features have been removed
- The system is now focused on single-user, local storage for Zed editor

### From original MemoryGraph
- This fork focuses on simplicity and Zed editor integration
- Only SQLite backend is supported
- Advanced features have been removed in favor of core functionality
- The project is now named "mcp-context-keeper" to reflect its purpose

## Acknowledgments

This project is a simplified fork of the original MemoryGraph project by Gregory Dickson, adapted specifically for Zed editor integration with a focus on simplicity and local storage.