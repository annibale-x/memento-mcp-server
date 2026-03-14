"""
Test file for MCP tools functionality in mcp-context-keeper
Tests tool-related models and validation without requiring server initialization.
"""

import json
import os
import sys

import pytest

# Add parent directory to path to import context_keeper
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from context_keeper.models import Memory, MemoryContext, MemoryType, RelationshipType


def test_memory_model_validation():
    """Test memory model validation and constraints"""

    # Test valid memory creation
    memory = Memory(
        type=MemoryType.SOLUTION,
        title="Fixed authentication bug with JWT",
        content="Increased JWT token expiration to 30 minutes and added refresh token support.",
        tags=["authentication", "jwt", "security", "backend"],
        importance=0.8,
        confidence=0.9,
    )

    assert memory.type == MemoryType.SOLUTION
    assert memory.title == "Fixed authentication bug with JWT"
    assert memory.tags == ["authentication", "jwt", "security", "backend"]
    assert memory.importance == 0.8
    assert memory.confidence == 0.9

    # Test with context
    context = MemoryContext(
        project_path="/apps/api",
        files_involved=["auth.py", "middleware.py"],
        languages=["python"],
        frameworks=["fastapi"],
        git_branch="main",
        working_directory="/home/user/projects/api",
    )

    memory_with_context = Memory(
        type=MemoryType.FIX,
        title="Fixed CORS configuration",
        content="Updated CORS settings to allow frontend origin",
        tags=["cors", "configuration", "frontend"],
        context=context,
    )

    assert memory_with_context.context is not None
    assert memory_with_context.context.project_path == "/apps/api"
    assert "auth.py" in memory_with_context.context.files_involved

    # Test serialization using model_dump with json mode for datetime serialization
    memory_dict = memory.model_dump(mode="json")
    assert memory_dict["title"] == "Fixed authentication bug with JWT"

    # Test deserialization
    memory_json = json.dumps(memory_dict)
    loaded_dict = json.loads(memory_json)
    assert loaded_dict["title"] == "Fixed authentication bug with JWT"

    # Test validation errors
    # Test empty title
    with pytest.raises(ValueError):
        Memory(type=MemoryType.TASK, title="", content="Some content")

    # Test empty content
    with pytest.raises(ValueError):
        Memory(type=MemoryType.TASK, title="Valid title", content="")

    # Test importance out of range
    with pytest.raises(ValueError):
        Memory(
            type=MemoryType.TASK,
            title="Valid title",
            content="Valid content",
            importance=1.5,
        )

    # Test confidence out of range
    with pytest.raises(ValueError):
        Memory(
            type=MemoryType.TASK,
            title="Valid title",
            content="Valid content",
            confidence=-0.1,
        )


def test_memory_type_enumeration():
    """Test memory type enumeration"""
    # Verify all expected types exist
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

    # Test string to enum conversion
    assert MemoryType("task") == MemoryType.TASK
    assert MemoryType("solution") == MemoryType.SOLUTION
    assert MemoryType("problem") == MemoryType.PROBLEM

    # Test invalid type
    with pytest.raises(ValueError):
        MemoryType("invalid_type")


def test_relationship_type_enumeration():
    """Test relationship type enumeration"""
    # Verify some key types exist
    key_types = [
        ("CAUSES", "CAUSES"),
        ("SOLVES", "SOLVES"),
        ("ADDRESSES", "ADDRESSES"),
        ("RELATED_TO", "RELATED_TO"),
        ("DEPENDS_ON", "DEPENDS_ON"),
        ("REQUIRES", "REQUIRES"),
        ("IMPROVES", "IMPROVES"),
        ("BREAKS", "BREAKS"),
    ]

    for value, name in key_types:
        rel_type = RelationshipType(value)
        assert rel_type.name == name
        assert rel_type.value == value

    # Test string to enum conversion
    assert RelationshipType("CAUSES") == RelationshipType.CAUSES
    assert RelationshipType("SOLVES") == RelationshipType.SOLVES
    assert RelationshipType("RELATED_TO") == RelationshipType.RELATED_TO

    # Test invalid type
    with pytest.raises(ValueError):
        RelationshipType("invalid_relationship")


def test_memory_context_model():
    """Test memory context model"""
    # Test basic context creation
    context = MemoryContext(
        project_path="/my/project",
        files_involved=["main.py", "utils.py"],
        languages=["python", "javascript"],
        frameworks=["django", "react"],
        technologies=["postgresql", "redis"],
        git_commit="abc123",
        git_branch="feature/auth",
        working_directory="/home/user/projects/myproject",
        timestamp="2024-01-15T10:30:00Z",
        session_id="session-123",
        user_id="user-456",
    )

    assert context.project_path == "/my/project"
    assert context.files_involved == ["main.py", "utils.py"]
    assert context.languages == ["python", "javascript"]

    # Test serialization
    context_dict = context.model_dump(mode="json")
    assert context_dict["project_path"] == "/my/project"
    assert context_dict["session_id"] == "session-123"

    # Test with minimal context
    minimal_context = MemoryContext(
        project_path="/simple/project",
        files_involved=["app.py"],
    )

    assert minimal_context.project_path == "/simple/project"
    assert minimal_context.files_involved == ["app.py"]

    # Test context in memory
    memory_with_context = Memory(
        type=MemoryType.CODE_PATTERN,
        title="Authentication middleware pattern",
        content="Pattern for JWT authentication in FastAPI",
        tags=["pattern", "authentication", "fastapi"],
        context=context,
    )

    assert memory_with_context.context is not None
    assert memory_with_context.context.project_path == "/my/project"


def test_tool_parameter_validation():
    """Test tool parameter validation constraints"""
    # Test tag normalization
    memory = Memory(
        type=MemoryType.GENERAL,
        title="Test memory with tags",
        content="Content with various tags",
        tags=["  UPPERCASE  ", "MixedCase", "lowercase", "  spaced  "],
    )

    assert memory.tags == ["uppercase", "mixedcase", "lowercase", "spaced"]

    # Test text field trimming
    memory = Memory(
        type=MemoryType.GENERAL,
        title="  Title with spaces  ",
        content="  Content with spaces  ",
    )

    assert memory.title == "Title with spaces"
    assert memory.content == "Content with spaces"
