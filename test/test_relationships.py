"""
Test file for relationship functionality in mcp-context-server
Tests relationship models and types without requiring server initialization.
"""

import json
import os
import sys

# Add parent directory to path to import user_memory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from context_server.models import (
    Memory,
    MemoryType,
    Relationship,
    RelationshipProperties,
    RelationshipType,
)


def test_relationship_models():
    """Test relationship model functionality"""
    print("Testing relationship models...")

    try:
        # Test Relationship model creation
        relationship = Relationship(
            from_memory_id="mem_test_1",
            to_memory_id="mem_test_2",
            type=RelationshipType.RELATED_TO,
            properties=RelationshipProperties(
                context="Test relationship context",
                strength=0.8,
                confidence=0.9,
            ),
        )

        print(f"Created relationship: {relationship}")
        print(f"Relationship type: {relationship.type}")
        print(f"Relationship strength: {relationship.properties.strength}")
        print(f"Relationship confidence: {relationship.properties.confidence}")

        # Test serialization using model_dump with json mode for datetime serialization
        relationship_dict = relationship.model_dump(mode="json")
        print(f"Serialized relationship: {json.dumps(relationship_dict, indent=2)}")

        # Test deserialization
        relationship_json = json.dumps(relationship_dict)
        loaded_dict = json.loads(relationship_json)
        print(f"Deserialized relationship dict: {loaded_dict}")

        # Test Memory model creation
        memory = Memory(
            type=MemoryType.SOLUTION,
            title="Test memory title",
            content="Test memory content",
            tags=["test", "relationship"],
        )

        print(f"\nCreated memory: {memory}")
        print(f"Memory type: {memory.type}")
        print(f"Memory title: {memory.title}")

        print("[PASS] Relationship model tests passed!")
        return True

    except Exception as e:
        print(f"[FAIL] Error in relationship model tests: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_relationship_types():
    """Test relationship type enumeration"""
    print("\nTesting relationship types...")

    try:
        # Test all relationship types
        print("Available relationship types:")
        for rel_type in RelationshipType:
            print(f"  - {rel_type.value}: {rel_type.name}")

        # Test value access
        assert RelationshipType.CAUSES.value == "CAUSES"
        assert RelationshipType.RELATED_TO.value == "RELATED_TO"
        assert RelationshipType.SOLVES.value == "SOLVES"
        assert RelationshipType.ADDRESSES.value == "ADDRESSES"
        assert RelationshipType.DEPENDS_ON.value == "DEPENDS_ON"

        # Test string to enum conversion
        causes = RelationshipType("CAUSES")
        assert causes == RelationshipType.CAUSES

        related_to = RelationshipType("RELATED_TO")
        assert related_to == RelationshipType.RELATED_TO

        solves = RelationshipType("SOLVES")
        assert solves == RelationshipType.SOLVES

        print("[PASS] Relationship type tests passed!")
        return True

    except Exception as e:
        print(f"[FAIL] Error in relationship type tests: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_memory_types():
    """Test memory type enumeration"""
    print("\nTesting memory types...")

    try:
        # Test all memory types
        print("Available memory types:")
        for mem_type in MemoryType:
            print(f"  - {mem_type.value}: {mem_type.name}")

        # Test value access
        assert MemoryType.TASK.value == "task"
        assert MemoryType.SOLUTION.value == "solution"
        assert MemoryType.PROBLEM.value == "problem"
        assert MemoryType.FIX.value == "fix"
        assert MemoryType.ERROR.value == "error"

        # Test string to enum conversion
        task = MemoryType("task")
        assert task == MemoryType.TASK

        solution = MemoryType("solution")
        assert solution == MemoryType.SOLUTION

        problem = MemoryType("problem")
        assert problem == MemoryType.PROBLEM

        print("[PASS] Memory type tests passed!")
        return True

    except Exception as e:
        print(f"[FAIL] Error in memory type tests: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_relationship_properties():
    """Test relationship properties model"""
    print("\nTesting relationship properties...")

    try:
        # Test RelationshipProperties creation
        properties = RelationshipProperties(
            strength=0.7,
            confidence=0.8,
            context="Test context for relationship",
            evidence_count=3,
            success_rate=0.9,
        )

        print(f"Created properties: {properties}")
        print(f"Strength: {properties.strength}")
        print(f"Confidence: {properties.confidence}")
        print(f"Context: {properties.context}")
        print(f"Evidence count: {properties.evidence_count}")
        print(f"Success rate: {properties.success_rate}")

        # Test validation
        # Strength should be between 0.0 and 1.0
        try:
            RelationshipProperties(strength=1.5)
            print("[FAIL] Should have raised validation error for strength > 1.0")
            return False
        except ValueError:
            print("[PASS] Correctly rejected strength > 1.0")

        # Confidence should be between 0.0 and 1.0
        try:
            RelationshipProperties(confidence=-0.1)
            print("[FAIL] Should have raised validation error for confidence < 0.0")
            return False
        except ValueError:
            print("[PASS] Correctly rejected confidence < 0.0")

        print("[PASS] Relationship properties tests passed!")
        return True

    except Exception as e:
        print(f"[FAIL] Error in relationship properties tests: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("=" * 60)
    print("Running relationship model tests for mcp-context-server")
    print("=" * 60)

    # Run all tests
    model_tests_passed = test_relationship_models()
    type_tests_passed = test_relationship_types()
    memory_tests_passed = test_memory_types()
    properties_tests_passed = test_relationship_properties()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Model tests: {'[PASS] PASSED' if model_tests_passed else '[FAIL] FAILED'}")
    print(f"Type tests: {'[PASS] PASSED' if type_tests_passed else '[FAIL] FAILED'}")
    print(
        f"Memory tests: {'[PASS] PASSED' if memory_tests_passed else '[FAIL] FAILED'}"
    )
    print(
        f"Properties tests: {'[PASS] PASSED' if properties_tests_passed else '[FAIL] FAILED'}"
    )

    all_passed = (
        model_tests_passed
        and type_tests_passed
        and memory_tests_passed
        and properties_tests_passed
    )
    print(
        f"\nOverall: {'[PASS] ALL TESTS PASSED' if all_passed else '[FAIL] SOME TESTS FAILED'}"
    )

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
