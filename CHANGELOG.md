# Changelog

* 2026-03-16: v0.1.20 - Codebase consistency restoration and documentation enhancement (Hannibal)
  * **Legacy code cleanup**: Removed mcp_context_keeper module, example.py, setup.py, and test_basic.py to restore consistent codebase
  * **Version bump**: Updated to v0.1.20 in __init__.py and pyproject.toml
  * **Project memory updates**: Corrected test count (157 tests) and removed references to legacy code
  * **Complete README restructuring**: Linear, modular structure without redundancies
  * **Removed "Universal" terminology**: Replaced with "Cross-Platform", "Shared", "Consistent Behavior"
  * **Added natural language interaction examples**: Show chat-based memento usage with "Remember that..." patterns
  * **Relationship Types cross-linking**: Added prominent references to RELATIONSHIPS.md documentation
  * **Eliminated duplicate content**: Each piece of information now in one place only
  * **Improved documentation flow**: Clear path from installation to advanced usage
  * **Multi-language trigger phrases**: English, Italian, Spanish support for natural interaction
  * **All examples in English**: Removed Italian code examples from README
  * **Enhanced integration table**: Clear overview of all supported platforms
  * **Configuration hierarchy clarification**: Environment variables → YAML files → CLI args → defaults
  * **Tool profile explanation**: Core (13), Extended (17), Advanced (25) tools
  * **Architecture overview**: Simplified explanation of consistent behavior across platforms

* 2026-03-16: v0.1.19 - Test suite fixes and warning resolution (Hannibal)
  * Fixed 2 failing tests in server startup and initialization flow
  * Corrected server cleanup to call `disconnect()` instead of `close()` on database backend
  * Updated all test mocks to expect `disconnect.assert_called_once()` instead of `close.assert_called_once()`
  * Added proper warning filters for AsyncMock coroutine warnings in test suite
  * Fixed async mock configuration in CLI tests to avoid RuntimeWarning for unawaited coroutines
  * Enhanced test reliability with proper mock specifications for all async methods
  * All 157 tests now passing with 0 warnings
  * Improved test suite stability and maintainability

* 2026-03-16: v0.1.18 - Memento onboarding protocol enhancement and tool renaming (Hannibal)
  * Renamed `help_memento_tools_usage` tool to `memento_onboarding` for clearer onboarding purpose
  * Enhanced tool with comprehensive onboarding protocol including initialization, retrieval flow, and storage triggers
  * Added optimized retrieval flow guide to prevent inefficient tool usage (6+ tool calls)
  * Integrated external Memento protocol with automatic storage triggers and on-demand triggers
  * Added memory schema requirements with mandatory tags (project, tech, category) and importance scoring
  * Added tool selection decision tree for efficient retrieval (1-3 tools for simple info, max 5 for complex tasks)
  * Added practical examples showing inefficient vs optimized tool usage patterns
  * Enhanced topic parameter support: "protocol", "retrieval_flow", "distinction", "examples", "best_practices"
  * Updated all documentation references to reflect new tool name and enhanced functionality
  * Maintained backward compatibility through topic-based access to previous guidance content
  * Updated tool definitions, registry, and imports to reflect new naming convention
  * Enhanced configuration handling for improved onboarding experience
  * Fixed test suite to work with renamed tool and updated functionality

* 2026-03-15: v0.1.17 - Complete environment variable renaming and configuration file standardization (Hannibal)
  * Renamed all remaining `CONTEXT_` environment variables to `MEMENTO_` prefix:
    - `CONTEXT_SQLITE_PATH` → `MEMENTO_SQLITE_PATH`
    - `CONTEXT_TOOL_PROFILE` → `MEMENTO_TOOL_PROFILE`
    - `CONTEXT_LOG_LEVEL` → `MEMENTO_LOG_LEVEL`
    - `CONTEXT_ENABLE_ADVANCED_TOOLS` → `MEMENTO_ENABLE_ADVANCED_TOOLS`
    - `CONTEXT_ALLOW_CYCLES` → `MEMENTO_ALLOW_CYCLES`
    - `CONTEXT_BACKEND` → `MEMENTO_BACKEND`
    - `CONTEXT_AUTO_EXTRACT_ENTITIES` → `MEMENTO_AUTO_EXTRACT_ENTITIES`
    - `CONTEXT_SESSION_BRIEFING` → `MEMENTO_SESSION_BRIEFING`
    - `CONTEXT_BRIEFING_VERBOSITY` → `MEMENTO_BRIEFING_VERBOSITY`
    - `CONTEXT_BRIEFING_RECENCY_DAYS` → `MEMENTO_BRIEFING_RECENCY_DAYS`
  * Standardized configuration file name from `context-keeper.yaml` to `memento.yaml`
  * Updated all documentation references to use new configuration file name
  * Fixed remaining references in integration guides and examples
  * Updated configuration loading logic to prioritize `memento.yaml` over legacy names
  * Enhanced backward compatibility with deprecation warnings for old variable names
  * All 159 tests passing with new environment variable naming
  * Complete project renaming from Context Keeper to Memento finalized

* 2026-03-15: v0.1.16 - Documentation reorganization and README restructuring (Hannibal)
  * Completely reorganized README.md to focus on user needs (636 → 441 lines)
  * Created clear separation between MCP server usage and Python library usage
  * Added comprehensive documentation structure in docs/ directory:
    - integrations/PYTHON.md - Complete guide to using Memento as a Python library
    - integrations/IDE.md - Detailed IDE integration guides
    - integrations/AGENT.md - Agent and CLI integration guides
    - RULES.md - Usage rules and best practices
    - AGENT_CONFIGURATION.md - Agent configuration templates
    - CONTRIBUTING.md - Contribution guidelines for developers
  * Improved README structure to answer three key user questions:
    1. How to install? - Clear installation instructions
    2. How to run? - IDE configuration and execution modes
    3. What can I do with it? - Use cases for developers, teams, and AI assistants
  * Enhanced documentation navigation with clear links between files
  * Maintained focus on MCP server usage for IDEs (Zed, Cursor, Windsurf, VSCode) and CLI agents
  * Updated GitHub repository URLs to use placeholders for consistency
  * All documentation cross-references verified and functional

* 2026-03-15: v0.1.15 - Confidence system reorganization and tool distribution optimization (Hannibal)
  * Reorganized confidence system tools for better accessibility across profiles
  * Moved 3 essential confidence tools to Core profile (13 tools total):
    - get_low_confidence_mementos - Identify obsolete knowledge
    - boost_memento_confidence - Reinforce valid knowledge  
    - adjust_memento_confidence - Manual confidence correction
  * Moved apply_memento_confidence_decay to Extended profile (17 tools total)
  * Kept set_memento_decay_factor in Advanced profile (25 tools total)
  * Updated tool documentation with new distribution strategy
  * Enhanced TOOLS.md with comprehensive confidence system guidance
  * All confidence system tests passing (13/13)
  * Demo script fully functional with new tool distribution
  * Improved user experience: all users now have basic confidence management
  * Better search result ordering with confidence-based prioritization

* 2026-03-15: v0.1.14 - FTS schema fix and database stability improvements (Hannibal)
  * Fixed critical 'no such column: T.title' error in SQLite FTS table
  * Updated database schema to create FTS tables without problematic content='nodes' option
  * Added refresh_fts_support() method to properly detect FTS availability after schema creation
  * Fixed get_memento tool by adding missing get_memory() method to database interface
  * Enhanced FTS table population with INSERT OR REPLACE for reliable updates
  * Created fix_fts_schema.py script to repair existing corrupted databases
  * Added comprehensive testing for new database creation with correct FTS schema
  * Improved error handling and logging for FTS operations
  * All memento tools now fully functional with proper FTS support

* 2026-03-15: v0.1.13 - ID generation pattern implementation and database schema initialization fix (Hannibal)
  * Implemented functional ID generation pattern with automatic UUID generation and optional override
  * Fixed database schema initialization bug in server startup (missing initialize_schema() call)
  * Added import asyncio to server.py to fix missing dependency
  * Enhanced store_memento tool with automatic ID generation when no ID provided
  * Added support for custom IDs with validation and duplicate detection
  * Updated tool schema to include optional id field in store_memento
  * Improved error handling for ID validation and conflict scenarios
  * All 128 tests passing with comprehensive ID pattern validation

* 2026-03-15: v0.1.12 - Zed MCP integration fix and character encoding issues (Hannibal)
  * Fixed Zed MCP server integration by resolving hidden character issues in configuration
  * Identified and resolved copy-paste invisible character problems in environment variables
  * Enhanced Windows compatibility with proper UTF-8 encoding for tool descriptions
  * Improved error handling for MCP protocol communication with Zed editor
  * Added comprehensive debugging tools for Zed MCP integration testing

* 2026-03-15: v0.1.11 - Relationship system bug fixes and API consistency (Hannibal)
  * Fixed critical bug in relationship creation: added missing create_relationship method to SQLiteMemoryDatabase
  * Added get_related_memories method with BFS traversal support for max_depth parameter
  * Added update_relationship_properties method for modifying relationship attributes
  * Added search_relationships_by_context method for structured context-based filtering
  * Fixed API inconsistency between tool handlers and database interface methods
  * Enhanced get_related_memories to properly handle relationship type filtering and depth traversal
  * Improved error handling and validation for relationship operations
  * All relationship tools now functional: create_memento_relationship, get_related_mementos, etc.

* 2026-03-14: v0.1.10 - Complete test suite reconstruction and bug fixes (Hannibal)
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

* 2026-03-14: v0.1.9 - Path resolution and Windows compatibility fixes (Hannibal)
  * Fixed SQLite database path issues on Windows systems
  * Changed default database path from `.db` to `context.db` in configuration
  * Fixed indentation error in `memento.py` wrapper script
  * Improved environment variable handling for configuration overrides
  * Enhanced Windows compatibility for database file operations

* 2026-03-14: v0.1.8 - Code quality analysis and dead code removal (Hannibal)
  * Removed unused `SimpleGraph` and graph algorithms classes
  * Removed unused `MemoryNode` and graph-related models
  * Removed unused utilities like `datetime_utils.py` and `error_handling.py`
  * Migrated inline tools definitions from `server.py` to `tools/definitions.py`
  * Fixed test suite by using explicit asserts instead of return values
  * Cleaned up leftover testing artifacts and databases

* 2026-03-14: v0.1.7 - File reorganization and structure cleanup (Hannibal)
  * Renamed database files for better clarity:
    - `sqlite_backend.py` → `engine.py` (database engine/connection management)
    - `sqlite_database.py` → `interface.py` (domain interface for memories and relationships)
  * Renamed `backends` directory to `database` for accurate representation
  * Updated all imports to reflect new file structure
  * Improved code organization and separation of concerns
  * Removed unused work files (`simple_sqlite_db.py`)
  * Cleaned up import paths after file reorganization
  * Ensured all tests pass with new file structure

* 2026-03-14: v0.1.6 - Memory tools guidance and usage clarification (Hannibal)
  * Added `help_memento_tools_usage` tool for comprehensive guidance on memento vs session memory usage
  * Added clear distinction guidance to prevent confusion with Serena Context Server tools
  * Added decision matrices and practical examples for tool selection
  * Renamed guide tool from `get_memento_guide` to `help_memento_tools_usage` for better LLM discoverability
  * Added best practices documentation for memento usage
  * Updated tool count: Core profile now has 10 tools (including guide tool)
  * Enhanced documentation with memento vs session memory distinction
  * Improved README.md with usage guidance and common mistakes to avoid
  * Fixed potential confusion between memento tools (`_persistent` suffix) and session memory tools (no suffix)
  * Fixed documentation inconsistencies regarding tool naming conventions
  * Fixed integration guidance for using multiple MCP context servers together

* 2026-03-14: v0.1.5 - Memento tool naming convention and configuration updates (Hannibal)
  * Added memento tool naming convention to avoid conflicts with Serena Context Server
  * Added clear distinction between memento (cross-session) and session memory storage
  * Updated environment variable prefixes from MEMORY_ to MEMENTO_
  * Changed default database path to ~/.mcp-memento/context.db
  * Updated configuration file names to context-keeper.yaml
  * Fixed module entry point to properly handle CLI arguments
  * Improved Zed editor MCP configuration compatibility
  * **BREAKING CHANGE**: Renamed all MCP tools with `_persistent` suffix:
    - Core tools: `store_memory` → `store_memento`, `get_memory` → `get_memento`, etc.
    - Extended tools: `get_memory_statistics` → `get_memento_statistics`, etc.
    - Advanced tools: `find_memory_path` → `find_path_between_mementos`, etc.
  * Fixed module execution with `python -m memento` now works correctly
  * Fixed CLI arguments like `--health` and `--show-config` are properly handled
  * Fixed environment variable support for Zed editor integration
  * Fixed configuration file path references
  * Fixed tool registry mapping with new memento tool names

* 2026-03-13: v0.1.4 - NetworkX dependency removal and SimpleGraph implementation (Hannibal)
  * Added SimpleGraph class to replace NetworkX dependency
  * Added lightweight in-memory graph structure for SQLite backend
  * Added JSON serialization support for SimpleGraph
  * Added integration tests for SimpleGraph with SQLite backend
  * Replaced NetworkX dependency with custom SimpleGraph implementation
  * Updated SQLite backend to use SimpleGraph instead of NetworkX
  * Reduced external dependencies from 6 to 5 packages
  * Updated project documentation to reflect NetworkX removal
  * Fixed JSON serialization issues with edge tuple keys
  * Fixed graph loading when tables don't exist yet
  * Fixed documentation inconsistencies regarding dependencies
  * Removed NetworkX dependency (networkx>=3.0.0)
  * Removed external graph library dependency

* 2026-03-13: v0.1.3 - SQLite-only backend simplification (Hannibal)
  * Added SQLite-only backend support (removed all other backends)
  * Added simplified configuration with YAML + env vars
  * Added MemoryNode.to_database_properties() method for SQLite compatibility
  * Added updated documentation reflecting SQLite-only architecture
  * Simplified project structure by removing non-SQLite backends
  * Updated README.md to reflect SQLite-only support
  * Removed references to Neo4j, FalkorDB, Memgraph, Turso, and Cloud backends
  * Updated memory_parser.py documentation
  * Fixed critical bug preventing memory storage in SQLite backend
  * Fixed documentation inconsistencies
  * Fixed import/export functionality for SQLite
  * Removed multi-tenant support
  * Removed all non-SQLite backend implementations
  * Removed admin-only tools and migration tools
  * Removed advanced analytics modules not essential for core functionality

* 2026-03-12: v0.1.2 - Initial simplified version for Zed editor (Hannibal)
  * Added initial simplified version for Zed editor integration
  * Added core MCP tools for memory management
  * Added SQLite backend with zero dependencies
  * Added basic configuration system
  * Project renamed to mcp-memento
  * Focus on context-aware memory management for MCP servers
  * Simplified architecture for Zed editor compatibility

* 2026-03-11: v0.1.1 - Export/import and health check functionality (Hannibal)
  * Added export/import functionality for memories
  * Added health check CLI command
  * Added basic relationship management
  * Fixed SQLite schema initialization issues
  * Fixed memory parsing utilities

* 2026-03-10: v0.1.0 - Initial SQLite backend implementation (Hannibal)
  * Added initial SQLite backend implementation
  * Added core memory models (Memory, MemoryContext, Relationship)
  * Added basic tool handlers for MCP protocol
  * Ported from original MemoryGraph project
  * Simplified for single-backend operation

* 2026-03-09: v0.0.1 - Initial project setup (Hannibal)
  * Added initial project setup
  * Added MCP server foundation
  * Added basic project structure

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
- The project is now named "mcp-memento" to reflect its purpose

## Acknowledgments

This project is a simplified fork of the original MemoryGraph project by Gregory Dickson, adapted specifically for Zed editor integration with a focus on simplicity and local storage.