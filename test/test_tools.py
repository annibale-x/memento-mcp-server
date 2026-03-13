"""
Test file for MCP tools functionality in mcp-context-server
Tests tool-related models and validation without requiring server initialization.
"""

import json
import os
import sys

# Add parent directory to path to import context_server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from context_server.models import Memory, MemoryContext, MemoryType, RelationshipType


def test_memory_model_validation():
    """Test memory model validation and constraints"""
    print("Testing memory model validation...")

    try:
        # Test valid memory creation
        memory = Memory(
            type=MemoryType.SOLUTION,
            title="Fixed authentication bug with JWT",
            content="Increased JWT token expiration to 30 minutes and added refresh token support.",
            tags=["authentication", "jwt", "security", "backend"],
            importance=0.8,
            confidence=0.9,
        )

        print(f"Created memory: {memory}")
        print(f"Memory type: {memory.type}")
        print(f"Memory title: {memory.title}")
        print(f"Memory tags: {memory.tags}")
        print(f"Memory importance: {memory.importance}")
        print(f"Memory confidence: {memory.confidence}")

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

        print(f"\nMemory with context: {memory_with_context}")
        print(f"Context project path: {memory_with_context.context.project_path}")
        print(f"Context files: {memory_with_context.context.files_involved}")
        print(f"Context languages: {memory_with_context.context.languages}")

        # Test serialization using model_dump with json mode for datetime serialization
        memory_dict = memory.model_dump(mode="json")
        print(f"\nSerialized memory: {json.dumps(memory_dict, indent=2)}")

        # Test deserialization
        memory_json = json.dumps(memory_dict)
        loaded_dict = json.loads(memory_json)
        print(f"Deserialized memory dict: {loaded_dict}")

        # Test validation errors
        print("\nTesting validation constraints...")

        # Test empty title
        try:
            Memory(type=MemoryType.TASK, title="", content="Some content")
            print("[FAIL] Should have raised validation error for empty title")
            return False
        except ValueError:
            print("[PASS] Correctly rejected empty title")

        # Test empty content
        try:
            Memory(type=MemoryType.TASK, title="Valid title", content="")
            print("[FAIL] Should have raised validation error for empty content")
            return False
        except ValueError:
            print("[PASS] Correctly rejected empty content")

        # Test importance out of range
        try:
            Memory(
                type=MemoryType.TASK,
                title="Valid title",
                content="Valid content",
                importance=1.5,
            )
            print("[FAIL] Should have raised validation error for importance > 1.0")
            return False
        except ValueError:
            print("[PASS] Correctly rejected importance > 1.0")

        # Test confidence out of range
        try:
            Memory(
                type=MemoryType.TASK,
                title="Valid title",
                content="Valid content",
                confidence=-0.1,
            )
            print("[FAIL] Should have raised validation error for confidence < 0.0")
            return False
        except ValueError:
            print("[PASS] Correctly rejected confidence < 0.0")

        print("[PASS] Memory model validation tests passed!")
        return True

    except Exception as e:
        print(f"[FAIL] Error in memory model validation tests: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_memory_type_enumeration():
    """Test memory type enumeration"""
    print("\nTesting memory type enumeration...")

    try:
        # List all memory types
        print("Available memory types:")
        for mem_type in MemoryType:
            print(f"  - {mem_type.value}: {mem_type.name}")

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
            print(f"  [OK] {name}: {value}")

        # Test string to enum conversion
        task = MemoryType("task")
        assert task == MemoryType.TASK

        solution = MemoryType("solution")
        assert solution == MemoryType.SOLUTION

        problem = MemoryType("problem")
        assert problem == MemoryType.PROBLEM

        # Test invalid type
        try:
            MemoryType("invalid_type")
            print("[FAIL] Should have raised ValueError for invalid type")
            return False
        except ValueError:
            print("[PASS] Correctly rejected invalid memory type")

        print("[PASS] Memory type enumeration tests passed!")
        return True

    except Exception as e:
        print(f"[FAIL] Error in memory type enumeration tests: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_relationship_type_enumeration():
    """Test relationship type enumeration"""
    print("\nTesting relationship type enumeration...")

    try:
        # List all relationship types
        print("Available relationship types:")
        for rel_type in RelationshipType:
            print(f"  - {rel_type.value}: {rel_type.name}")

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
            print(f"  [OK] {name}: {value}")

        # Test string to enum conversion
        causes = RelationshipType("CAUSES")
        assert causes == RelationshipType.CAUSES

        solves = RelationshipType("SOLVES")
        assert solves == RelationshipType.SOLVES

        related_to = RelationshipType("RELATED_TO")
        assert related_to == RelationshipType.RELATED_TO

        # Test invalid type
        try:
            RelationshipType("invalid_relationship")
            print("[FAIL] Should have raised ValueError for invalid relationship type")
            return False
        except ValueError:
            print("[PASS] Correctly rejected invalid relationship type")

        print("[PASS] Relationship type enumeration tests passed!")
        return True

    except Exception as e:
        print(f"[FAIL] Error in relationship type enumeration tests: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_memory_context_model():
    """Test memory context model"""
    print("\nTesting memory context model...")

    try:
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

        print(f"Created context: {context}")
        print(f"Project path: {context.project_path}")
        print(f"Files involved: {context.files_involved}")
        print(f"Languages: {context.languages}")
        print(f"Frameworks: {context.frameworks}")
        print(f"Technologies: {context.technologies}")
        print(f"Git commit: {context.git_commit}")
        print(f"Git branch: {context.git_branch}")
        print(f"Working directory: {context.working_directory}")
        print(f"Session ID: {context.session_id}")
        print(f"User ID: {context.user_id}")

        # Test serialization using model_dump with json mode for datetime serialization
        context_dict = context.model_dump(mode="json")
        print(f"\nSerialized context: {json.dumps(context_dict, indent=2)}")

        # Test with minimal context
        minimal_context = MemoryContext(
            project_path="/simple/project",
            files_involved=["app.py"],
        )

        print(f"\nMinimal context: {minimal_context}")
        print(f"Project path: {minimal_context.project_path}")
        print(f"Files involved: {minimal_context.files_involved}")

        # Test context in memory
        memory_with_context = Memory(
            type=MemoryType.CODE_PATTERN,
            title="Authentication middleware pattern",
            content="Pattern for JWT authentication in FastAPI",
            tags=["pattern", "authentication", "fastapi"],
            context=context,
        )

        print(f"\nMemory with full context: {memory_with_context}")
        print(
            f"Memory context project: {memory_with_context.context.project_path if memory_with_context.context else 'None'}"
        )

        print("[PASS] Memory context model tests passed!")
        return True

    except Exception as e:
        print(f"[FAIL] Error in memory context model tests: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_tool_parameter_validation():
    """Test tool parameter validation constraints"""
    print("\nTesting tool parameter validation constraints...")

    try:
        # Test memory type validation
        print("1. Testing memory type validation...")
        valid_memory_types = [t.value for t in MemoryType]
        print(f"   Valid memory types: {valid_memory_types}")

        # Test relationship type validation
        print("2. Testing relationship type validation...")
        valid_relationship_types = [t.value for t in RelationshipType]
        print(f"   Valid relationship types: {valid_relationship_types}")

        # Test parameter constraints
        print("3. Testing parameter constraints...")
        print("   - importance: should be between 0.0 and 1.0")
        print("   - confidence: should be between 0.0 and 1.0")
        print("   - strength: should be between 0.0 and 1.0")
        print("   - success_rate: should be between 0.0 and 1.0")
        print("   - limit: should be positive integer")
        print("   - offset: should be non-negative integer")

        # Test tag normalization
        print("4. Testing tag normalization...")
        memory = Memory(
            type=MemoryType.GENERAL,
            title="Test memory with tags",
            content="Content with various tags",
            tags=["  UPPERCASE  ", "MixedCase", "lowercase", "  spaced  "],
        )

        print(
            f"   Original tags: {['  UPPERCASE  ', 'MixedCase', 'lowercase', '  spaced  ']}"
        )
        print(f"   Normalized tags: {memory.tags}")
        assert memory.tags == ["uppercase", "mixedcase", "lowercase", "spaced"]
        print("   [OK] Tags correctly normalized to lowercase and trimmed")

        # Test text field trimming
        print("5. Testing text field trimming...")
        memory = Memory(
            type=MemoryType.GENERAL,
            title="  Title with spaces  ",
            content="  Content with spaces  ",
        )

        print(f"   Original title: '  Title with spaces  '")
        print(f"   Trimmed title: '{memory.title}'")
        assert memory.title == "Title with spaces"

        print(f"   Original content: '  Content with spaces  '")
        print(f"   Trimmed content: '{memory.content}'")
        assert memory.content == "Content with spaces"
        print("   [OK] Text fields correctly trimmed")

        print("[PASS] Tool parameter validation tests passed!")
        return True

    except Exception as e:
        print(f"[FAIL] Error in tool parameter validation tests: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("=" * 60)
    print("Running MCP tool model tests for mcp-user-memory")
    print("=" * 60)

    # Run all tests
    validation_passed = test_memory_model_validation()
    memory_types_passed = test_memory_type_enumeration()
    relationship_types_passed = test_relationship_type_enumeration()
    context_passed = test_memory_context_model()
    param_validation_passed = test_tool_parameter_validation()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(
        f"Memory validation: {'[PASS] PASSED' if validation_passed else '[FAIL] FAILED'}"
    )
    print(
        f"Memory types: {'[PASS] PASSED' if memory_types_passed else '[FAIL] FAILED'}"
    )
    print(
        f"Relationship types: {'[PASS] PASSED' if relationship_types_passed else '[FAIL] FAILED'}"
    )
    print(f"Context model: {'[PASS] PASSED' if context_passed else '[FAIL] FAILED'}")
    print(
        f"Parameter validation: {'[PASS] PASSED' if param_validation_passed else '[FAIL] FAILED'}"
    )

    all_passed = (
        validation_passed
        and memory_types_passed
        and relationship_types_passed
        and context_passed
        and param_validation_passed
    )
    print(
        f"\nOverall: {'[PASS] ALL TESTS PASSED' if all_passed else '[FAIL] SOME TESTS FAILED'}"
    )

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
