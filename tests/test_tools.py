"""
Tools test suite for mcp-memento.

This module tests tool models, definitions, registry, and validation.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path to import memento
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError as PydanticValidationError

from memento.advanced_tools import ADVANCED_RELATIONSHIP_TOOLS
from memento.config import (
    _ADVANCED_TOOLS,
    _CORE_TOOLS,
    _EXTENDED_EXTRA_TOOLS,
)
from memento.models import (
    Memory,
    MemoryContext,
    MemoryType,
    RelationshipType,
    ValidationError,
)
from memento.tools.definitions import (
    get_all_tools,
)

# Define public constants expected by tests
CORE_TOOLS = _CORE_TOOLS
EXTENDED_TOOLS = _CORE_TOOLS + _EXTENDED_EXTRA_TOOLS
ADVANCED_TOOLS = _CORE_TOOLS + _EXTENDED_EXTRA_TOOLS + _ADVANCED_TOOLS
from memento.tools.error_handling import (
    NotFoundError,
    ToolError,
    format_error_response,
    handle_tool_error,
)
from memento.tools.registry import (
    ToolHandler,
    clear_handlers,
    get_handler,
    register_handler,
)


def get_tool_definitions_for_profile(profile: str):
    """
    Get tool definitions for a specific profile.

    Args:
        profile: Tool profile name ("core", "extended", or "advanced")

    Returns:
        List of Tool objects for the specified profile
    """
    # Combine all available tool definitions
    all_tool_defs = get_all_tools() + ADVANCED_RELATIONSHIP_TOOLS

    # Get enabled tool names for the profile
    if profile == "core":
        enabled_names = set(CORE_TOOLS)
    elif profile == "extended":
        enabled_names = set(EXTENDED_TOOLS)
    elif profile == "advanced":
        enabled_names = set(ADVANCED_TOOLS)
    else:
        raise ValueError(f"Unknown tool profile: {profile}")

    # Filter tool definitions by name
    return [tool for tool in all_tool_defs if tool.name in enabled_names]


class TestToolModels:
    """Test tool-related models and validation."""

    def test_memory_model_validation_basic(self):
        """Test basic memory model validation."""
        memory = Memory(
            type=MemoryType.SOLUTION,
            title="Test solution for authentication issue",
            content="Implemented JWT token validation with proper error handling.",
            tags=["authentication", "jwt", "security"],
            importance=0.8,
            confidence=0.9,
        )

        assert memory.type == MemoryType.SOLUTION
        assert memory.title == "Test solution for authentication issue"
        assert memory.content.startswith("Implemented JWT token")
        assert memory.tags == ["authentication", "jwt", "security"]
        assert memory.importance == 0.8
        assert memory.confidence == 0.9
        assert memory.created_at is not None

    def test_memory_model_validation_edge_cases(self):
        """Test memory model validation with edge cases."""
        # Test with minimal required fields
        memory = Memory(
            type=MemoryType.TASK,
            title="Minimal task",
            content="Minimal content",
        )

        assert memory.title == "Minimal task"
        assert memory.content == "Minimal content"
        assert memory.tags == []
        assert memory.importance == 0.5
        assert memory.confidence == 0.8

        # Test tag normalization
        memory_with_tags = Memory(
            type=MemoryType.GENERAL,
            title="Tag normalization test",
            content="Testing tag cleaning",
            tags=["  UPPERCASE  ", "  spaced  ", "lowercase", "MixedCase"],
        )

        assert memory_with_tags.tags == [
            "uppercase",
            "spaced",
            "lowercase",
            "mixedcase",
        ]

        # Test text field trimming
        memory_trimmed = Memory(
            type=MemoryType.GENERAL,
            title="  Title with spaces  ",
            content="  Content with spaces  ",
        )

        assert memory_trimmed.title == "Title with spaces"
        assert memory_trimmed.content == "Content with spaces"

    def test_memory_model_validation_errors(self):
        """Test memory model validation errors."""
        # Empty title should raise PydanticValidationError
        with pytest.raises(PydanticValidationError) as exc_info:
            Memory(
                type=MemoryType.TASK,
                title="",
                content="Valid content",
            )
        assert "title" in str(exc_info.value).lower()

        # Empty content should raise PydanticValidationError
        with pytest.raises(PydanticValidationError) as exc_info:
            Memory(
                type=MemoryType.TASK,
                title="Valid title",
                content="",
            )
        assert "content" in str(exc_info.value).lower()

        # Importance out of range should raise PydanticValidationError
        with pytest.raises(PydanticValidationError) as exc_info:
            Memory(
                type=MemoryType.TASK,
                title="Valid title",
                content="Valid content",
                importance=1.5,
            )
        assert "importance" in str(exc_info.value).lower()

        # Confidence out of range should raise PydanticValidationError
        with pytest.raises(PydanticValidationError) as exc_info:
            Memory(
                type=MemoryType.TASK,
                title="Valid title",
                content="Valid content",
                confidence=-0.1,
            )
        assert "confidence" in str(exc_info.value).lower()

    def test_memory_type_enumeration_complete(self):
        """Test complete MemoryType enumeration."""
        expected_types = [
            ("task", "TASK"),
            ("code_pattern", "CODE_PATTERN"),
            ("problem", "PROBLEM"),
            ("solution", "SOLUTION"),
            ("project", "PROJECT"),
            ("technology", "TECHNOLOGY"),
            ("error", "ERROR"),
            ("fix", "FIX"),
            ("command", "COMMAND"),
            ("file_context", "FILE_CONTEXT"),
            ("workflow", "WORKFLOW"),
            ("general", "GENERAL"),
            ("conversation", "CONVERSATION"),
        ]

        for value, name in expected_types:
            mem_type = MemoryType(value)
            assert mem_type.name == name
            assert mem_type.value == value

        # Test invalid type
        with pytest.raises(ValueError):
            MemoryType("invalid_type")

    def test_relationship_type_enumeration_complete(self):
        """Test complete RelationshipType enumeration."""
        expected_types = [
            ("CAUSES", "CAUSES"),
            ("TRIGGERS", "TRIGGERS"),
            ("LEADS_TO", "LEADS_TO"),
            ("PREVENTS", "PREVENTS"),
            ("BREAKS", "BREAKS"),
            ("SOLVES", "SOLVES"),
            ("ADDRESSES", "ADDRESSES"),
            ("ALTERNATIVE_TO", "ALTERNATIVE_TO"),
            ("IMPROVES", "IMPROVES"),
            ("REPLACES", "REPLACES"),
            ("OCCURS_IN", "OCCURS_IN"),
            ("APPLIES_TO", "APPLIES_TO"),
            ("WORKS_WITH", "WORKS_WITH"),
            ("REQUIRES", "REQUIRES"),
        ]

        for value, name in expected_types:
            rel_type = RelationshipType(value)
            assert rel_type.name == name
            assert rel_type.value == value

        # Test invalid type
        with pytest.raises(ValueError):
            RelationshipType("invalid_relationship")

    def test_memory_context_model(self):
        """Test MemoryContext model creation and validation."""
        context = MemoryContext(
            project_path="/test/project/path",
            files_involved=["main.py", "utils.py", "tests.py"],
            languages=["python", "javascript"],
            frameworks=["fastapi", "react"],
            technologies=["postgresql", "redis", "docker"],
            git_commit="abc123def456",
            git_branch="feature/test-branch",
            working_directory="/home/user/projects/test",
            timestamp="2024-01-15T10:30:00Z",
            session_id="session-123456",
            user_id="user-789",
        )

        assert context.project_path == "/test/project/path"
        assert context.files_involved == ["main.py", "utils.py", "tests.py"]
        assert context.languages == ["python", "javascript"]
        assert context.frameworks == ["fastapi", "react"]
        assert context.technologies == ["postgresql", "redis", "docker"]
        assert context.git_commit == "abc123def456"
        assert context.git_branch == "feature/test-branch"
        assert context.working_directory == "/home/user/projects/test"
        from datetime import datetime, timezone

        assert context.timestamp == datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
        assert context.session_id == "session-123456"
        assert context.user_id == "user-789"

        # Test with minimal context
        minimal_context = MemoryContext(
            project_path="/minimal/project",
            files_involved=["app.py"],
        )

        assert minimal_context.project_path == "/minimal/project"
        assert minimal_context.files_involved == ["app.py"]
        assert minimal_context.languages == []
        assert minimal_context.frameworks == []
        assert minimal_context.technologies == []

    def test_memory_json_serialization(self):
        """Test memory serialization to and from JSON."""
        memory = Memory(
            type=MemoryType.SOLUTION,
            title="JSON serialization test",
            content="Testing JSON round-trip serialization",
            tags=["json", "serialization", "test"],
            importance=0.7,
            confidence=0.8,
        )

        # Serialize using model_dump with json mode
        memory_dict = memory.model_dump(mode="json")

        assert memory_dict["type"] == "solution"
        assert memory_dict["title"] == "JSON serialization test"
        assert memory_dict["content"] == "Testing JSON round-trip serialization"
        assert memory_dict["tags"] == ["json", "serialization", "test"]
        assert memory_dict["importance"] == 0.7
        assert memory_dict["confidence"] == 0.8

        # Convert to JSON string
        memory_json = json.dumps(memory_dict)

        # Parse back
        loaded_dict = json.loads(memory_json)
        assert loaded_dict["title"] == "JSON serialization test"
        assert loaded_dict["type"] == "solution"

        # Test deserialization with model_validate
        restored_memory = Memory.model_validate(loaded_dict)
        assert restored_memory.title == "JSON serialization test"
        assert restored_memory.type == MemoryType.SOLUTION


class TestToolDefinitions:
    """Test tool definitions and profiles."""

    def test_get_all_tools(self):
        """Test that get_all_tools returns a comprehensive list."""
        all_tools = get_all_tools()

        assert isinstance(all_tools, list)
        assert len(all_tools) > 0

        # Check that all tools have required attributes
        for tool in all_tools:
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "inputSchema")

            # Check tool name is not empty
            assert isinstance(tool.name, str)
            assert len(tool.name) > 0

            # Check description is not empty
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0

            # Check inputSchema is a dict
            assert isinstance(tool.inputSchema, dict)
            assert "type" in tool.inputSchema
            assert tool.inputSchema["type"] == "object"

    def test_core_tools_exist(self):
        """Test that core tools are defined."""
        all_tools = get_all_tools()
        tool_names = [tool.name for tool in all_tools]

        # Check for essential core tools
        essential_core_tools = [
            "store_persistent_memory",
            "get_persistent_memory",
            "search_persistent_memories",
            "update_persistent_memory",
            "delete_persistent_memory",
            "create_persistent_relationship",
            "get_related_persistent_memories",
        ]

        for tool_name in essential_core_tools:
            assert tool_name in tool_names, f"Core tool '{tool_name}' not found"

    def test_tool_definitions_for_profile(self):
        """Test getting tool definitions for specific profiles."""
        # Test core profile
        core_tools = get_tool_definitions_for_profile("core")
        assert isinstance(core_tools, list)

        # Test extended profile (should include core tools)
        extended_tools = get_tool_definitions_for_profile("extended")
        assert isinstance(extended_tools, list)
        assert len(extended_tools) >= len(core_tools)

        # Test advanced profile (should include extended tools)
        advanced_tools = get_tool_definitions_for_profile("advanced")
        assert isinstance(advanced_tools, list)
        assert len(advanced_tools) >= len(extended_tools)

    def test_tool_schema_structure(self):
        """Test that tool schemas have proper structure."""
        all_tools = get_all_tools()

        for tool in all_tools:
            schema = tool.inputSchema

            # Check required schema structure
            assert schema["type"] == "object"
            assert "properties" in schema

            # Check properties is a dict
            properties = schema["properties"]
            assert isinstance(properties, dict)

            # Check optional fields
            if "required" in schema:
                assert isinstance(schema["required"], list)

            if "additionalProperties" in schema:
                assert isinstance(schema["additionalProperties"], bool)


class TestToolRegistry:
    """Test tool handler registry functionality."""

    def setup_method(self):
        """Clear handlers before each test."""
        clear_handlers()

    def test_register_and_get_handler(self):
        """Test registering and retrieving a handler."""
        # Create a mock handler
        mock_handler = AsyncMock()
        mock_handler.return_value = {"success": True}

        # Register the handler
        register_handler("test_tool", mock_handler)

        # Retrieve the handler
        retrieved_handler = get_handler("test_tool")

        assert retrieved_handler is mock_handler

        # Test calling the handler
        result = retrieved_handler(None, {"param": "value"})
        assert result is not None

    def test_get_nonexistent_handler(self):
        """Test getting a handler that doesn't exist."""
        handler = get_handler("nonexistent_tool")
        assert handler is None

    def test_multiple_handler_registration(self):
        """Test registering multiple handlers."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        handler3 = AsyncMock()

        register_handler("tool1", handler1)
        register_handler("tool2", handler2)
        register_handler("tool3", handler3)

        assert get_handler("tool1") is handler1
        assert get_handler("tool2") is handler2
        assert get_handler("tool3") is handler3

        # Verify handler3 is not handler1
        assert get_handler("tool3") is not handler1

    def test_handler_overwrite(self):
        """Test that registering a handler with existing name overwrites it."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        register_handler("overwrite_tool", handler1)
        assert get_handler("overwrite_tool") is handler1

        register_handler("overwrite_tool", handler2)
        assert get_handler("overwrite_tool") is handler2
        assert get_handler("overwrite_tool") is not handler1

    def test_clear_handlers(self):
        """Test clearing all handlers."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()

        register_handler("tool1", handler1)
        register_handler("tool2", handler2)

        assert get_handler("tool1") is handler1
        assert get_handler("tool2") is handler2

        clear_handlers()

        assert get_handler("tool1") is None
        assert get_handler("tool2") is None


class TestErrorHandling:
    """Test tool error handling classes and functions."""

    def test_tool_error_creation(self):
        """Test ToolError creation with message and details."""
        error = ToolError(
            message="Test error message", details={"param": "value", "code": 123}
        )

        assert error.message == "Test error message"
        assert error.details == {"param": "value", "code": 123}

        # Test with only message
        simple_error = ToolError("Simple error")
        assert str(simple_error) == "Simple error"
        assert simple_error.details == {}

    def test_validation_error(self):
        """Test ValidationError creation."""
        error = ValidationError(
            message="Validation failed",
            field="title",
            value="",
            details={"constraint": "non-empty"},
        )

        assert error.message == "Validation failed"
        assert error.field == "title"
        assert error.value == ""
        assert error.details == {"constraint": "non-empty"}

    def test_not_found_error(self):
        """Test NotFoundError creation."""
        error = NotFoundError(
            resource_type="memory",
            resource_id="mem_123",
            details={"searched_in": "database"},
        )

        assert error.message == "memory not found: mem_123"
        assert error.resource_type == "memory"
        assert error.resource_id == "mem_123"
        assert error.details == {"searched_in": "database"}

    def test_format_error_response(self):
        """Test formatting error response for MCP."""
        error = ToolError("Test error", {"code": 500})

        response = format_error_response(error)

        assert response["isError"] is True
        assert len(response["content"]) == 1

        content = response["content"][0]
        assert content["type"] == "text"
        assert "Test error" in content["text"]
        assert "code" in content["text"]

    def test_handle_tool_error_generic(self):
        """Test handle_tool_error with generic exception."""
        exception = Exception("Generic exception message")

        response = handle_tool_error(exception)

        assert response["isError"] is True
        assert len(response["content"]) == 1
        assert "Generic exception message" in response["content"][0]["text"]

    def test_handle_tool_error_tool_error(self):
        """Test handle_tool_error with ToolError."""
        error = ToolError("Tool-specific error", {"action": "create"})

        response = handle_tool_error(error)

        assert response["isError"] is True
        assert "Tool-specific error" in response["content"][0]["text"]


class TestToolHandlerPatterns:
    """Test common tool handler patterns and utilities."""

    @pytest.mark.asyncio
    async def test_async_tool_handler_pattern(self):
        """Test async tool handler pattern with database interaction."""
        # Create mock database
        mock_db = AsyncMock()
        mock_db.store_memory = AsyncMock(return_value="mem_test_123")

        # Create a simple handler
        async def test_handler(database, arguments):
            """Test handler that stores a memory."""
            # Validate required parameters
            if "title" not in arguments or "content" not in arguments:
                raise ValidationError("Missing required parameters")

            # Create memory object
            memory = Memory(
                type=MemoryType.GENERAL,
                title=arguments["title"],
                content=arguments["content"],
                tags=arguments.get("tags", []),
            )

            # Store in database
            memory_id = await database.store_memory(memory)

            return {
                "content": [
                    {"type": "text", "text": f"Memory stored with ID: {memory_id}"}
                ]
            }

        # Register and test the handler
        register_handler("test_store", test_handler)

        # Prepare arguments
        arguments = {
            "title": "Test memory title",
            "content": "Test memory content",
            "tags": ["test", "handler"],
        }

        # Execute handler
        result = await test_handler(mock_db, arguments)

        # Verify results
        assert result is not None
        assert "content" in result
        assert len(result["content"]) == 1
        assert "Memory stored with ID:" in result["content"][0]["text"]

        # Verify database was called
        mock_db.store_memory.assert_called_once()
        stored_memory = mock_db.store_memory.call_args[0][0]
        assert isinstance(stored_memory, Memory)
        assert stored_memory.title == "Test memory title"
        assert stored_memory.content == "Test memory content"

    @pytest.mark.asyncio
    async def test_tool_handler_error_pattern(self):
        """Test tool handler error handling pattern."""

        # Create a handler that raises an error
        async def error_handler(database, arguments):
            """Handler that raises ValidationError."""
            if "required_param" not in arguments:
                raise ValidationError(
                    "Missing required parameter", field="required_param", value=None
                )

            return {"content": [{"type": "text", "text": "Success"}]}

        # Test with missing parameter
        with pytest.raises(ValidationError) as exc_info:
            await error_handler(None, {})

        assert "Missing required parameter" in str(exc_info.value)
        assert exc_info.value.field == "required_param"

        # Test with parameter present
        result = await error_handler(None, {"required_param": "value"})
        assert result["content"][0]["text"] == "Success"

    def test_tool_input_validation_pattern(self):
        """Test common input validation patterns."""

        def validate_string_param(value, param_name, min_length=1, max_length=500):
            """Validate string parameter."""
            if not isinstance(value, str):
                raise ValidationError(
                    f"Parameter '{param_name}' must be a string",
                    field=param_name,
                    value=value,
                )

            if len(value) < min_length:
                raise ValidationError(
                    f"Parameter '{param_name}' must be at least {min_length} characters",
                    field=param_name,
                    value=value,
                )

            if len(value) > max_length:
                raise ValidationError(
                    f"Parameter '{param_name}' must be at most {max_length} characters",
                    field=param_name,
                    value=value,
                )

            return value.strip()

        # Test valid input
        valid_result = validate_string_param("Valid title", "title", min_length=3)
        assert valid_result == "Valid title"

        # Test invalid type
        with pytest.raises(ValidationError) as exc_info:
            validate_string_param(123, "title")
        assert "must be a string" in str(exc_info.value)

        # Test too short
        with pytest.raises(ValidationError) as exc_info:
            validate_string_param("a", "title", min_length=3)
        assert "at least 3 characters" in str(exc_info.value)

        # Test too long
        long_string = "a" * 600
        with pytest.raises(ValidationError) as exc_info:
            validate_string_param(long_string, "description", max_length=500)
        assert "at most 500 characters" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
