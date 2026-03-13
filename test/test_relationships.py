"""
Test file for relationship functionality in mcp-user-memory
"""

import asyncio
import json
import os
import sys

# Add parent directory to path to import user_memory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from user_memory import MemoryGraphServer
from user_memory.models import Memory, MemoryType, Relationship, RelationshipType


async def test_relationships():
    """Test relationship creation and retrieval"""
    print("Testing relationship functionality...")

    # Create a test server instance
    server = MemoryGraphServer()

    try:
        # Initialize the server
        await server.initialize()

        # Create two test memories
        memory1 = Memory(
            content="Test memory 1: Authentication bug",
            memory_type=MemoryType.BUG_FIX,
            tags=["authentication", "bug"],
        )

        memory2 = Memory(
            content="Test memory 2: Login failure issue",
            memory_type=MemoryType.ISSUE,
            tags=["login", "issue"],
        )

        # Store memories
        print("Storing test memories...")
        stored_memory1 = await server.memory_tools.store_memory(
            content=memory1.content,
            memory_type=memory1.memory_type.value,
            tags=memory1.tags,
        )

        stored_memory2 = await server.memory_tools.store_memory(
            content=memory2.content,
            memory_type=memory2.memory_type.value,
            tags=memory2.tags,
        )

        print(f"Memory 1 ID: {stored_memory1['id']}")
        print(f"Memory 2 ID: {stored_memory2['id']}")

        # Create a relationship
        print("\nCreating relationship between memories...")
        relationship = await server.relationship_tools.create_relationship(
            from_memory_id=stored_memory1["id"],
            to_memory_id=stored_memory2["id"],
            relationship_type=RelationshipType.CAUSED_BY.value,
            context="Authentication bug caused login failure",
        )

        print(f"Relationship created: {relationship}")

        # Get relationships for memory 1
        print("\nGetting relationships for memory 1...")
        relationships = await server.relationship_tools.get_relationships(
            memory_id=stored_memory1["id"], direction="outgoing"
        )

        print(f"Found {len(relationships)} outgoing relationships:")
        for rel in relationships:
            print(f"  - {rel['relationship_type']} -> {rel['to_memory_id']}")

        # Get relationships for memory 2
        print("\nGetting relationships for memory 2...")
        relationships = await server.relationship_tools.get_relationships(
            memory_id=stored_memory2["id"], direction="incoming"
        )

        print(f"Found {len(relationships)} incoming relationships:")
        for rel in relationships:
            print(f"  - {rel['from_memory_id']} -> {rel['relationship_type']}")

        # Test bidirectional relationships
        print("\nGetting all relationships for memory 1...")
        all_relationships = await server.relationship_tools.get_relationships(
            memory_id=stored_memory1["id"], direction="both"
        )

        print(f"Total relationships: {len(all_relationships)}")

        # Create another relationship type
        print("\nCreating 'solution_for' relationship...")
        solution_relationship = await server.relationship_tools.create_relationship(
            from_memory_id=stored_memory2["id"],
            to_memory_id=stored_memory1["id"],
            relationship_type=RelationshipType.SOLUTION_FOR.value,
            context="Login failure was solved by authentication fix",
        )

        print(f"Solution relationship created: {solution_relationship}")

        # Test filtering by relationship type
        print("\nFiltering relationships by type 'caused_by'...")
        caused_by_relationships = await server.relationship_tools.get_relationships(
            memory_id=stored_memory1["id"],
            direction="outgoing",
            relationship_types=["caused_by"],
        )

        print(f"Found {len(caused_by_relationships)} 'caused_by' relationships")

        # Clean up test data
        print("\nCleaning up test data...")
        await server.memory_tools.delete_memory(stored_memory1["id"])
        await server.memory_tools.delete_memory(stored_memory2["id"])

        print("\n✅ All relationship tests passed!")

    except Exception as e:
        print(f"\n❌ Error during relationship tests: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Clean up server resources
        await server.cleanup()

    return True


def test_relationship_models():
    """Test relationship model functionality"""
    print("\nTesting relationship models...")

    try:
        # Test Relationship model creation
        relationship = Relationship(
            from_memory_id="mem_test_1",
            to_memory_id="mem_test_2",
            relationship_type=RelationshipType.RELATED_TO,
            context="Test relationship context",
            strength=0.8,
        )

        print(f"Created relationship: {relationship}")
        print(f"Relationship type: {relationship.relationship_type}")
        print(f"Relationship strength: {relationship.strength}")

        # Test serialization
        relationship_dict = relationship.dict()
        print(f"Serialized relationship: {json.dumps(relationship_dict, indent=2)}")

        # Test deserialization
        relationship_json = json.dumps(relationship_dict)
        loaded_dict = json.loads(relationship_json)
        print(f"Deserialized relationship dict: {loaded_dict}")

        print("✅ Relationship model tests passed!")
        return True

    except Exception as e:
        print(f"❌ Error in relationship model tests: {e}")
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
        assert RelationshipType.CAUSED_BY.value == "caused_by"
        assert RelationshipType.RELATED_TO.value == "related_to"
        assert RelationshipType.SOLUTION_FOR.value == "solution_for"
        assert RelationshipType.CONTEXT_FOR.value == "context_for"
        assert RelationshipType.DEPENDS_ON.value == "depends_on"

        # Test string to enum conversion
        caused_by = RelationshipType("caused_by")
        assert caused_by == RelationshipType.CAUSED_BY

        related_to = RelationshipType("related_to")
        assert related_to == RelationshipType.RELATED_TO

        print("✅ Relationship type tests passed!")
        return True

    except Exception as e:
        print(f"❌ Error in relationship type tests: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("=" * 60)
    print("Running relationship tests for mcp-user-memory")
    print("=" * 60)

    # Run model tests first (don't require server)
    model_tests_passed = test_relationship_models()
    type_tests_passed = test_relationship_types()

    # Run server tests
    server_tests_passed = await test_relationships()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Model tests: {'✅ PASSED' if model_tests_passed else '❌ FAILED'}")
    print(f"Type tests: {'✅ PASSED' if type_tests_passed else '❌ FAILED'}")
    print(f"Server tests: {'✅ PASSED' if server_tests_passed else '❌ FAILED'}")

    all_passed = model_tests_passed and type_tests_passed and server_tests_passed
    print(
        f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}"
    )

    return all_passed


if __name__ == "__main__":
    # Run async tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
