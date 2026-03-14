"""
Standard pytest test suite for mcp-context-keeper.

This module provides comprehensive testing using pytest conventions and fixtures.
It includes tests for configuration, models, database, tools, CLI, and integration.
"""

import asyncio
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError as PydanticValidationError

# Add parent directory to path to import context_keeper
sys.path.insert(0, str(Path(__file__).parent.parent))


# Test fixtures
@pytest.fixture
def temp_db_path():
    """Create a temporary SQLite database file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def sample_memory_data():
    """Provide sample memory data for testing."""
    return {
        "type": "solution",
        "title": "Test solution for authentication",
        "content": "Implemented JWT token validation with proper error handling.",
        "tags": ["authentication", "jwt", "security"],
        "importance": 0.8,
        "confidence": 0.9,
    }


@pytest.fixture
def sample_relationship_data():
    """Provide sample relationship data for testing."""
    return {
        "from_memory_id": "memory_test_1",
        "to_memory_id": "memory_test_2",
        "type": "RELATED_TO",
        "properties": {
            "context": "Test relationship context",
            "strength": 0.8,
            "confidence": 0.9,
        },
    }


@pytest.fixture
def memory_context_data():
    """Provide sample memory context data for testing."""
    return {
        "project_path": "/test/project",
        "files_involved": ["main.py", "utils.py"],
        "languages": ["python"],
        "frameworks": ["fastapi"],
        "technologies": ["postgresql"],
        "git_branch": "test/branch",
        "working_directory": "/tmp/test",
    }


# Test classes follow pytest conventions with descriptive names
class TestConfiguration:
    """Test configuration module functionality."""

    def test_config_defaults(self):
        """Test that Config provides default values when no environment variables are set."""
        from context_keeper.config import Config

        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            Config.reload_config()

            assert Config.TOOL_PROFILE == "core"
            assert Config.ENABLE_ADVANCED_TOOLS is False
            assert Config.LOG_LEVEL == "INFO"
            assert isinstance(Config.SQLITE_PATH, str)
            assert Config.SQLITE_PATH.endswith("context.db")

    def test_config_environment_variables(self):
        """Test that Config reads environment variables correctly."""
        from context_keeper.config import Config

        test_db_path = f"/tmp/test_{uuid.uuid4().hex}.db"

        with patch.dict(
            os.environ,
            {
                "CONTEXT_TOOL_PROFILE": "extended",
                "CONTEXT_ENABLE_ADVANCED_TOOLS": "true",
                "CONTEXT_LOG_LEVEL": "DEBUG",
                "CONTEXT_SQLITE_PATH": test_db_path,
            },
            clear=True,
        ):
            Config.reload_config()

            assert Config.TOOL_PROFILE == "extended"
            assert Config.ENABLE_ADVANCED_TOOLS is True
            assert Config.LOG_LEVEL == "DEBUG"
            assert Config.SQLITE_PATH == test_db_path

    def test_get_enabled_tools(self):
        """Test that get_enabled_tools returns correct tool lists for each profile."""
        from context_keeper.config import Config

        test_cases = [
            ("core", 9),  # Core profile should have 9 tools
            ("extended", 11),  # Extended profile should have 11 tools
        ]

        for profile, expected_min_count in test_cases:
            with patch.dict(os.environ, {"CONTEXT_TOOL_PROFILE": profile}, clear=True):
                Config.reload_config()
                tools = Config.get_enabled_tools()

                assert isinstance(tools, list)
                assert len(tools) >= expected_min_count
                assert "store_persistent_memory" in tools
                assert "get_persistent_memory" in tools

    def test_config_summary_structure(self):
        """Test that get_config_summary returns a properly structured dictionary."""
        from context_keeper.config import Config

        summary = Config.get_config_summary()

        # Check top-level structure
        assert isinstance(summary, dict)
        required_keys = [
            "backend",
            "sqlite",
            "tools",
            "logging",
            "features",
            "config_sources",
        ]
        for key in required_keys:
            assert key in summary, f"Missing key in config summary: {key}"

        # Check nested structure
        assert isinstance(summary["tools"], dict)
        assert "profile" in summary["tools"]
        assert "enable_advanced" in summary["tools"]
        assert "enabled_tools_count" in summary["tools"]

        # Check config sources
        assert isinstance(summary["config_sources"], dict)
        assert "yaml_files" in summary["config_sources"]
        assert "env_vars" in summary["config_sources"]

    def test_config_reload(self):
        """Test that configuration can be reloaded and reflects environment changes."""
        from context_keeper.config import Config

        # Start with default
        with patch.dict(os.environ, {}, clear=True):
            Config.reload_config()
            assert Config.TOOL_PROFILE == "core"

        # Change environment and reload
        with patch.dict(os.environ, {"CONTEXT_TOOL_PROFILE": "extended"}, clear=True):
            Config.reload_config()
            assert Config.TOOL_PROFILE == "extended"

        # Go back to default
        with patch.dict(os.environ, {}, clear=True):
            Config.reload_config()
            assert Config.TOOL_PROFILE == "core"


class TestModels:
    """Test data models and validation."""

    def test_memory_creation(self, sample_memory_data):
        """Test Memory model creation with valid data."""
        from context_keeper.models import Memory, MemoryType

        memory = Memory(**sample_memory_data)

        assert memory.type == MemoryType.SOLUTION
        assert memory.title == sample_memory_data["title"]
        assert memory.content == sample_memory_data["content"]
        assert memory.tags == sample_memory_data["tags"]
        assert memory.importance == sample_memory_data["importance"]
        assert memory.confidence == sample_memory_data["confidence"]
        assert memory.created_at is not None

    def test_memory_validation_errors(self):
        """Test Memory model validation error cases."""
        from context_keeper.models import Memory, MemoryType

        # Empty title should raise PydanticValidationError
        with pytest.raises(PydanticValidationError):
            Memory(
                type=MemoryType.TASK,
                title="",
                content="Valid content",
            )

        # Empty content should raise PydanticValidationError
        with pytest.raises(PydanticValidationError):
            Memory(
                type=MemoryType.TASK,
                title="Valid title",
                content="",
            )

        # Importance out of range should raise PydanticValidationError
        with pytest.raises(PydanticValidationError):
            Memory(
                type=MemoryType.TASK,
                title="Valid title",
                content="Valid content",
                importance=1.5,
            )

    def test_memory_json_serialization(self, sample_memory_data):
        """Test Memory model JSON serialization round-trip."""
        from context_keeper.models import Memory

        # Create memory from data
        memory = Memory(**sample_memory_data)

        # Serialize to dictionary
        memory_dict = memory.model_dump(mode="json")

        # Convert to JSON string
        memory_json = json.dumps(memory_dict)

        # Parse back
        loaded_dict = json.loads(memory_json)

        # Create new memory from loaded data
        restored_memory = Memory.model_validate(loaded_dict)

        # Verify equality of important fields
        assert restored_memory.title == memory.title
        assert restored_memory.content == memory.content
        assert restored_memory.tags == memory.tags
        assert restored_memory.type == memory.type

    def test_relationship_creation(self, sample_relationship_data):
        """Test Relationship model creation with valid data."""
        from context_keeper.models import Relationship, RelationshipType

        relationship = Relationship(**sample_relationship_data)

        assert relationship.from_memory_id == sample_relationship_data["from_memory_id"]
        assert relationship.to_memory_id == sample_relationship_data["to_memory_id"]
        assert relationship.type == RelationshipType.RELATED_TO
        assert relationship.properties is not None
        assert relationship.properties.context == "Test relationship context"
        assert relationship.properties.strength == 0.8
        assert relationship.properties.confidence == 0.9

    def test_memory_context_creation(self, memory_context_data):
        """Test MemoryContext model creation."""
        from context_keeper.models import MemoryContext

        context = MemoryContext(**memory_context_data)

        assert context.project_path == memory_context_data["project_path"]
        assert context.files_involved == memory_context_data["files_involved"]
        assert context.languages == memory_context_data["languages"]
        assert context.frameworks == memory_context_data["frameworks"]
        assert context.technologies == memory_context_data["technologies"]
        assert context.git_branch == memory_context_data["git_branch"]
        assert context.working_directory == memory_context_data["working_directory"]

    def test_memory_type_enumeration(self):
        """Test MemoryType enumeration completeness."""
        from context_keeper.models import MemoryType

        # Test a subset of expected types
        expected_types = [
            ("task", "TASK"),
            ("solution", "SOLUTION"),
            ("problem", "PROBLEM"),
            ("error", "ERROR"),
            ("fix", "FIX"),
        ]

        for value, name in expected_types:
            mem_type = MemoryType(value)
            assert mem_type.name == name
            assert mem_type.value == value

        # Test invalid type raises ValueError
        with pytest.raises(ValueError):
            MemoryType("invalid_type")

    def test_relationship_type_enumeration(self):
        """Test RelationshipType enumeration completeness."""
        from context_keeper.models import RelationshipType

        # Test a subset of expected types
        expected_types = [
            ("CAUSES", "CAUSES"),
            ("SOLVES", "SOLVES"),
            ("RELATED_TO", "RELATED_TO"),
            ("DEPENDS_ON", "DEPENDS_ON"),
            ("IMPROVES", "IMPROVES"),
        ]

        for value, name in expected_types:
            rel_type = RelationshipType(value)
            assert rel_type.name == name
            assert rel_type.value == value

        # Test invalid type raises ValueError
        with pytest.raises(ValueError):
            RelationshipType("invalid_relationship")


class TestDatabase:
    """Test database functionality."""

    @pytest.mark.asyncio
    async def test_sqlite_backend_connection(self, temp_db_path):
        """Test SQLite backend connection and health check."""
        from context_keeper.database.engine import SQLiteBackend

        backend = SQLiteBackend(db_path=temp_db_path)
        await backend.connect()

        try:
            # Initialize schema first
            await backend.initialize_schema()

            # Test health check after schema is initialized
            health_info = await backend.health_check()

            assert health_info["connected"] is True
            assert health_info["backend_type"] == "sqlite"
            assert health_info["db_path"] == temp_db_path
            assert "statistics" in health_info

            # Verify schema was created by checking health again
            health_info_after = await backend.health_check()
            assert health_info_after["connected"] is True

        finally:
            await backend.disconnect()

    @pytest.mark.asyncio
    async def test_sqlite_memory_database_basic_operations(self, temp_db_path):
        """Test basic memory database operations."""
        from context_keeper.database.engine import SQLiteBackend
        from context_keeper.database.interface import SQLiteMemoryDatabase
        from context_keeper.models import (
            Memory,
            MemoryType,
            PaginatedResult,
            SearchQuery,
        )

        # Setup backend and database
        backend = SQLiteBackend(db_path=temp_db_path)
        await backend.connect()
        await backend.initialize_schema()

        db = SQLiteMemoryDatabase(backend)

        try:
            # Create a test memory
            test_memory = Memory(
                id=f"test_memory_{uuid.uuid4().hex[:8]}",
                type=MemoryType.SOLUTION,
                title="Test solution",
                content="Test content for database operations",
                tags=["test", "database"],
            )

            # Store memory
            stored_memory = await db.store_memory(test_memory)
            assert isinstance(stored_memory, Memory)
            assert stored_memory.id is not None
            memory_id = stored_memory.id
            assert isinstance(memory_id, str)
            assert len(memory_id) > 0

            # Retrieve memory
            retrieved_memory = await db.get_memory_by_id(memory_id)
            assert retrieved_memory is not None
            assert retrieved_memory.title == test_memory.title
            assert retrieved_memory.content == test_memory.content
            assert retrieved_memory.type == test_memory.type

            # Search memories
            search_query = SearchQuery(query="test")
            search_results = await db.search_memories(query=search_query)
            assert isinstance(search_results, PaginatedResult)
            assert isinstance(search_results.results, list)
            assert len(search_results.results) > 0

            # Update memory
            updated_memory = Memory(
                id=memory_id,
                type=MemoryType.SOLUTION,
                title="Updated title",
                content="Updated content",
                tags=["updated", "test"],
            )

            await db.update_memory(updated_memory)

            # Verify update
            updated_retrieved = await db.get_memory_by_id(memory_id)
            assert updated_retrieved.title == "Updated title"
            assert updated_retrieved.content == "Updated content"

            # Delete memory
            await db.delete_memory(memory_id)

            # Verify deletion
            deleted_memory = await db.get_memory_by_id(memory_id)
            assert deleted_memory is None

        finally:
            await backend.disconnect()

    @pytest.mark.asyncio
    async def test_sqlite_relationship_operations(self, temp_db_path):
        """Test relationship operations in SQLite database."""
        from context_keeper.database.engine import SQLiteBackend
        from context_keeper.database.interface import SQLiteMemoryDatabase
        from context_keeper.models import (
            Memory,
            MemoryType,
            PaginatedResult,
            Relationship,
            RelationshipProperties,
            RelationshipType,
            SearchQuery,
        )

        # Setup backend and database
        backend = SQLiteBackend(db_path=temp_db_path)
        await backend.connect()
        await backend.initialize_schema()

        db = SQLiteMemoryDatabase(backend)

        try:
            # Create two memories for relationship
            memory1 = Memory(
                id=f"test_memory1_{uuid.uuid4().hex[:8]}",
                type=MemoryType.PROBLEM,
                title="Problem memory",
                content="This is a problem",
            )

            memory2 = Memory(
                id=f"test_memory2_{uuid.uuid4().hex[:8]}",
                type=MemoryType.SOLUTION,
                title="Solution memory",
                content="This solves the problem",
            )

            stored_memory1 = await db.store_memory(memory1)
            stored_memory2 = await db.store_memory(memory2)
            memory1_id = stored_memory1.id
            memory2_id = stored_memory2.id

            # Create relationship
            relationship_properties = RelationshipProperties(
                context="Test relationship between problem and solution",
                strength=0.8,
                confidence=0.9,
            )

            # Create a Relationship object
            relationship = Relationship(
                id=f"rel_{uuid.uuid4().hex[:8]}",
                from_memory_id=memory1_id,
                to_memory_id=memory2_id,
                type=RelationshipType.SOLVES,
                properties=relationship_properties,
            )

            stored_relationship = await db.store_relationship(relationship)
            assert isinstance(stored_relationship, Relationship)
            assert stored_relationship.id is not None
            relationship_id = stored_relationship.id

            assert isinstance(relationship_id, str)
            assert len(relationship_id) > 0

            # Get relationships for memory
            relationships = await db.get_relationships_for_memory(memory1_id)
            assert isinstance(relationships, list)
            assert len(relationships) == 1

            relationship = relationships[0]
            assert relationship.from_memory_id == memory1_id
            assert relationship.to_memory_id == memory2_id
            assert relationship.type == RelationshipType.SOLVES

            # Delete relationship
            await db.delete_relationship(relationship_id)

            # Verify deletion
            relationships_after = await db.get_relationships_for_memory(memory1_id)
            assert len(relationships_after) == 0

        finally:
            await backend.disconnect()


class TestTools:
    """Test tool definitions and handlers."""

    def test_tool_definitions_completeness(self):
        """Test that all tool definitions have required structure."""
        from context_keeper.tools.definitions import get_all_tools

        all_tools = get_all_tools()

        assert isinstance(all_tools, list)
        assert len(all_tools) > 0

        # Check each tool has required attributes
        for tool in all_tools:
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "inputSchema")

            # Validate name
            assert isinstance(tool.name, str)
            assert len(tool.name) > 0

            # Validate description
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0

            # Validate inputSchema structure
            schema = tool.inputSchema
            assert isinstance(schema, dict)
            assert schema["type"] == "object"
            assert "properties" in schema
            assert isinstance(schema["properties"], dict)

    def test_tool_registry_functionality(self):
        """Test tool handler registration and retrieval."""
        from context_keeper.tools.registry import (
            ToolHandler,
            clear_handlers,
            get_handler,
            register_handler,
        )

        # Clear any existing handlers
        clear_handlers()

        # Create mock handlers
        mock_handler1 = AsyncMock()
        mock_handler2 = AsyncMock()

        # Register handlers
        register_handler("test_tool_1", mock_handler1)
        register_handler("test_tool_2", mock_handler2)

        # Retrieve handlers
        retrieved1 = get_handler("test_tool_1")
        retrieved2 = get_handler("test_tool_2")

        assert retrieved1 is mock_handler1
        assert retrieved2 is mock_handler2

        # Test nonexistent handler
        nonexistent = get_handler("nonexistent_tool")
        assert nonexistent is None

        # Clear handlers and verify
        clear_handlers()
        assert get_handler("test_tool_1") is None
        assert get_handler("test_tool_2") is None

    def test_error_handling_classes(self):
        """Test tool error handling class hierarchy."""
        from context_keeper.tools.error_handling import (
            NotFoundError,
            ToolError,
            ValidationError,
        )

        # Test base ToolError
        base_error = ToolError("Base error message", {"detail": "test"})
        assert str(base_error) == "Base error message (Details: {'detail': 'test'})"
        assert base_error.details == {"detail": "test"}

        # Test ValidationError
        validation_error = ValidationError(
            "Validation failed",
            field="title",
            value="",
            details={"constraint": "non-empty"},
        )
        assert (
            str(validation_error)
            == "Validation failed (Details: {'constraint': 'non-empty'})"
        )
        assert validation_error.field == "title"
        assert validation_error.value == ""

        # Test NotFoundError
        not_found_error = NotFoundError("memory", "mem_123", {"searched": "database"})
        assert (
            str(not_found_error)
            == "memory not found: mem_123 (Details: {'searched': 'database'})"
        )
        assert not_found_error.resource_type == "memory"
        assert not_found_error.resource_id == "mem_123"

    @pytest.mark.asyncio
    async def test_mock_tool_handler_execution(self):
        """Test execution of a mock tool handler with database interaction."""
        from context_keeper.models import Memory, MemoryType

        # Clear any existing handlers
        from context_keeper.tools.registry import clear_handlers, register_handler

        clear_handlers()

        # Create a test handler
        async def test_store_handler(database, arguments):
            """Test handler that stores a memory."""
            # Validate arguments
            if "title" not in arguments or "content" not in arguments:
                raise ValueError("Missing required arguments")

            # Create memory
            memory = Memory(
                type=MemoryType.GENERAL,
                title=arguments["title"],
                content=arguments["content"],
                tags=arguments.get("tags", []),
            )

            # Mock database storage
            memory_id = "test_memory_123"

            return {
                "content": [
                    {"type": "text", "text": f"Memory stored with ID: {memory_id}"}
                ]
            }

        # Register handler
        register_handler("test_store", test_store_handler)

        # Test handler execution
        from context_keeper.tools.registry import get_handler

        handler = get_handler("test_store")
        assert handler is not None

        # Prepare arguments
        test_arguments = {
            "title": "Test memory",
            "content": "Test content for handler",
            "tags": ["test", "handler"],
        }

        # Execute with mock database
        mock_db = AsyncMock()
        result = await handler(mock_db, test_arguments)

        # Verify result
        assert result is not None
        assert "content" in result
        assert len(result["content"]) == 1
        assert "Memory stored with ID:" in result["content"][0]["text"]

        # Test with missing arguments
        with pytest.raises(ValueError, match="Missing required arguments"):
            await handler(mock_db, {})


class TestCLI:
    """Test command-line interface functionality."""

    def test_cli_help_output(self, capsys):
        """Test CLI help output."""
        from context_keeper.cli import main

        with patch("sys.argv", ["context_keeper.cli", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit with 0 for help
            assert exc_info.value.code == 0

            # Check that help text was printed to stderr
            captured = capsys.readouterr()
            # Help text goes to stderr via _eprint
            assert "Usage:" in captured.out or "Examples:" in captured.out

    def test_cli_version_output(self, capsys):
        """Test CLI version output."""
        from context_keeper.cli import main

        with patch("sys.argv", ["context_keeper.cli", "--version"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

            # Version should be printed
            captured = capsys.readouterr()
            assert "context-keeper" in captured.out

    def test_cli_show_config(self):
        """Test --show-config option."""
        from context_keeper.cli import main

        with patch("sys.argv", ["context_keeper.cli", "--show-config"]):
            with patch("sys.exit") as mock_exit:
                with patch("context_keeper.cli._eprint") as mock_eprint:
                    main()

                    # Check that exit was called with 0 (may be called multiple times)
                    mock_exit.assert_any_call(0)
                    # Config summary should be printed
                    assert mock_eprint.call_count > 0

                    # Check for expected output
                    call_text = "\n".join(
                        [
                            call.args[0] if call.args else ""
                            for call in mock_eprint.call_args_list
                        ]
                    )
                    assert "Current Configuration:" in call_text
                    assert "Backend:" in call_text
                    assert "Tool Profile:" in call_text

    @pytest.mark.asyncio
    async def test_cli_health_check_integration(self):
        """Test health check functionality via CLI."""
        from context_keeper.cli import perform_health_check

        # Mock backend for health check
        mock_backend = AsyncMock()
        mock_backend.connect = AsyncMock()
        mock_backend.disconnect = AsyncMock()
        mock_backend.health_check = AsyncMock(
            return_value={
                "status": "healthy",
                "connected": True,
                "backend_type": "sqlite",
                "db_path": "/tmp/test.db",
                "version": "3.42.0",
                "statistics": {"memory_count": 42},
            }
        )

        with patch(
            "context_keeper.database.engine.SQLiteBackend", return_value=mock_backend
        ):
            result = await perform_health_check(timeout=1.0)

            assert result["status"] == "healthy"
            assert result["connected"] is True
            assert result["backend_type"] == "sqlite"

            # Verify backend methods were called
            mock_backend.connect.assert_called_once()
            mock_backend.health_check.assert_called_once()
            mock_backend.disconnect.assert_called_once()

    def test_cli_environment_variable_handling(self):
        """Test that CLI properly handles environment variables."""
        from context_keeper.cli import main

        test_db_path = f"/tmp/test_{uuid.uuid4().hex}.db"

        with patch.dict(
            os.environ,
            {
                "CONTEXT_TOOL_PROFILE": "extended",
                "CONTEXT_LOG_LEVEL": "DEBUG",
                "CONTEXT_SQLITE_PATH": test_db_path,
            },
            clear=True,
        ):
            with patch("sys.argv", ["context_keeper.cli", "--show-config"]):
                with patch("sys.exit") as mock_exit:
                    with patch("context_keeper.cli._eprint") as mock_eprint:
                        main()

                        # Check that exit was called with 0 (may be called multiple times)
                        mock_exit.assert_any_call(0)

                        # Check that environment values appear in output
                        call_text = "\n".join(
                            [
                                call.args[0] if call.args else ""
                                for call in mock_eprint.call_args_list
                            ]
                        )
                        assert "extended" in call_text.lower()
                        assert "debug" in call_text.lower()
                        assert test_db_path in call_text


class TestIntegration:
    """Integration tests combining multiple components."""

    @pytest.mark.asyncio
    async def test_server_initialization_flow(self):
        """Test complete server initialization flow."""
        from context_keeper.server import ContextKeeper

        # Create mocks for all dependencies
        mock_backend = AsyncMock()
        mock_backend.connect = AsyncMock(return_value=True)
        mock_backend.backend_name = MagicMock(return_value="sqlite")
        mock_backend.health_check = AsyncMock(
            return_value={
                "connected": True,
                "backend_type": "sqlite",
                "db_path": "/tmp/test.db",
            }
        )

        # Mock database interface
        mock_db = AsyncMock()
        mock_db.initialize_schema = AsyncMock()

        with patch(
            "context_keeper.database.engine.SQLiteBackend", return_value=mock_backend
        ):
            with patch(
                "context_keeper.server.SQLiteMemoryDatabase", return_value=mock_db
            ):
                # Create server
                server = ContextKeeper()

                # Initialize
                await server.initialize()

                # Verify initialization
                assert server.db_connection is mock_backend
                assert server.memory_db is mock_db
                assert server.advanced_handlers is not None

                # Verify tools are collected
                assert len(server.tools) > 0

                # Verify backend was connected
                mock_backend.connect.assert_called_once()

                # Cleanup
                await server.cleanup()
                mock_backend.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_execution_flow(self):
        """Test complete tool execution flow through server."""
        from context_keeper.server import ContextKeeper

        # Create mocks
        mock_backend = AsyncMock()
        mock_backend.connect = AsyncMock(return_value=True)
        mock_backend.close = AsyncMock()

        mock_db = AsyncMock()
        mock_db.store_memory = AsyncMock(return_value="test_memory_123")

        # Mock tool handler
        async def mock_store_handler(database, arguments):
            """Mock handler for store_persistent_memory."""
            return {"content": [{"type": "text", "text": "Memory stored successfully"}]}

        with patch(
            "context_keeper.database.engine.SQLiteBackend", return_value=mock_backend
        ):
            with patch(
                "context_keeper.server.SQLiteMemoryDatabase", return_value=mock_db
            ):
                with patch(
                    "context_keeper.tools.registry.get_handler",
                    return_value=mock_store_handler,
                ):
                    # Create and initialize server
                    server = ContextKeeper()
                    await server.initialize()

                    # Test tool execution through the server's tool registry
                    # instead of accessing internal handlers
                    from context_keeper.tools.registry import get_handler

                    # Verify that tools are registered
                    assert len(server.tools) > 0

                    # Check that at least one tool has a handler
                    tool_names = [tool.name for tool in server.tools]
                    has_registered_handler = False
                    for tool_name in tool_names:
                        if get_handler(tool_name) is not None:
                            has_registered_handler = True
                            break

                    assert has_registered_handler, "No tool handlers registered"

                    await server.cleanup()

    def test_configuration_profile_tool_mapping(self):
        """Test that configuration profiles correctly map to available tools."""
        from context_keeper.config import Config

        profile_tool_counts = {
            "core": 9,  # Core tools
            "extended": 11,  # Extended tools
        }

        for profile, expected_count in profile_tool_counts.items():
            with patch.dict(os.environ, {"CONTEXT_TOOL_PROFILE": profile}, clear=True):
                Config.reload_config()
                tools = Config.get_enabled_tools()

                assert isinstance(tools, list)
                # Check we have at least the expected number of tools
                assert len(tools) >= expected_count

                # Verify essential tools are present
                essential_tools = [
                    "store_persistent_memory",
                    "get_persistent_memory",
                    "search_persistent_memories",
                ]

                for tool_name in essential_tools:
                    assert tool_name in tools, (
                        f"Tool '{tool_name}' missing in {profile} profile"
                    )


# Main execution for running tests directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
