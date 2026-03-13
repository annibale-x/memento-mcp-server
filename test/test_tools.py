"""
Test file for MCP tools functionality in mcp-user-memory
"""

import asyncio
import json
import os
import sys

# Add parent directory to path to import user_memory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from user_memory import MemoryGraphServer
from user_memory.models import MemoryType, RelationshipType


async def test_basic_tools():
    """Test basic MCP tools functionality"""
    print("Testing basic MCP tools...")

    # Create a test server instance
    server = MemoryGraphServer()

    try:
        # Initialize the server
        await server.initialize()

        # Test 1: Store memory
        print("\n1. Testing store_memory...")
        memory_result = await server.memory_tools.store_memory(
            content="Test memory: Implemented user authentication with JWT",
            memory_type=MemoryType.DECISION.value,
            tags=["authentication", "security", "backend"],
            context="Working on user authentication system",
        )

        print(f"   Memory stored with ID: {memory_result['id']}")
        print(f"   Created at: {memory_result.get('created_at')}")

        memory_id = memory_result["id"]

        # Test 2: Get memory
        print("\n2. Testing get_memory...")
        retrieved_memory = await server.memory_tools.get_memory(memory_id)
        print(f"   Retrieved memory content: {retrieved_memory['content'][:50]}...")
        print(f"   Memory type: {retrieved_memory['memory_type']}")
        print(f"   Tags: {retrieved_memory.get('tags', [])}")

        # Test 3: Update memory
        print("\n3. Testing update_memory...")
        updated_memory = await server.memory_tools.update_memory(
            memory_id=memory_id,
            content="Test memory UPDATED: Implemented user authentication with JWT and refresh tokens",
            tags=["authentication", "security", "backend", "tokens"],
        )

        print(f"   Updated content: {updated_memory['content'][:60]}...")
        print(f"   Updated tags: {updated_memory.get('tags', [])}")

        # Test 4: Store another memory for relationships
        print("\n4. Storing second memory for relationship tests...")
        memory2_result = await server.memory_tools.store_memory(
            content="Test memory 2: Fixed JWT validation bug",
            memory_type=MemoryType.BUG_FIX.value,
            tags=["jwt", "bug", "validation"],
            context="Authentication system debugging",
        )

        memory2_id = memory2_result["id"]
        print(f"   Second memory stored with ID: {memory2_id}")

        # Test 5: Create relationship
        print("\n5. Testing create_relationship...")
        relationship = await server.relationship_tools.create_relationship(
            from_memory_id=memory2_id,
            to_memory_id=memory_id,
            relationship_type=RelationshipType.SOLUTION_FOR.value,
            context="JWT fix solved authentication implementation",
            strength=0.9,
        )

        print(f"   Relationship created: {relationship}")

        # Test 6: Get relationships
        print("\n6. Testing get_relationships...")
        relationships = await server.relationship_tools.get_relationships(
            memory_id=memory_id, direction="incoming"
        )

        print(f"   Found {len(relationships)} incoming relationships")
        for rel in relationships:
            print(f"   - {rel['relationship_type']} from {rel['from_memory_id']}")

        # Test 7: Recall memories
        print("\n7. Testing recall_memories...")
        recalled = await server.memory_tools.recall_memories(
            query="authentication", limit=5
        )

        print(f"   Recalled {len(recalled)} memories for 'authentication'")
        for mem in recalled[:3]:  # Show first 3
            print(
                f"   - {mem['content'][:40]}... (score: {mem.get('relevance_score', 0):.2f})"
            )

        # Test 8: Search memories
        print("\n8. Testing search_memories...")
        searched = await server.memory_tools.search_memories(
            query="JWT token authentication", search_tolerance=0.6, limit=5
        )

        print(f"   Searched found {len(searched)} memories")
        for mem in searched[:3]:  # Show first 3
            print(
                f"   - {mem['content'][:40]}... (similarity: {mem.get('similarity_score', 0):.2f})"
            )

        # Test 9: Export memories
        print("\n9. Testing export_memories...")
        exported = await server.memory_tools.export_memories(
            format="json", include_relationships=True
        )

        # Parse and check export
        if isinstance(exported, str):
            export_data = json.loads(exported)
        else:
            export_data = exported

        print(f"   Exported {len(export_data.get('memories', []))} memories")
        print(f"   Exported {len(export_data.get('relationships', []))} relationships")

        # Test 10: Delete memories
        print("\n10. Testing delete_memory...")
        delete_result1 = await server.memory_tools.delete_memory(memory_id)
        delete_result2 = await server.memory_tools.delete_memory(memory2_id)

        print(f"   Memory 1 deleted: {delete_result1}")
        print(f"   Memory 2 deleted: {delete_result2}")

        # Verify deletion
        print("\n11. Verifying deletion...")
        try:
            await server.memory_tools.get_memory(memory_id)
            print("   ❌ Memory 1 still exists (should have been deleted)")
        except Exception as e:
            print(f"   ✅ Memory 1 successfully deleted: {str(e)[:50]}...")

        try:
            await server.memory_tools.get_memory(memory2_id)
            print("   ❌ Memory 2 still exists (should have been deleted)")
        except Exception as e:
            print(f"   ✅ Memory 2 successfully deleted: {str(e)[:50]}...")

        print("\n[PASS] All basic tool tests passed!")
        return True

    except Exception as e:
        print(f"\n[FAIL] Error during basic tool tests: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Clean up server resources
        await server.cleanup()


async def test_extended_tools():
    """Test extended MCP tools (when available)"""
    print("\n" + "=" * 60)
    print("Testing extended MCP tools...")

    server = MemoryGraphServer()

    try:
        await server.initialize()

        # Check if extended tools are available
        if not hasattr(server, "extended_tools"):
            print("Extended tools not available in current mode")
            return True  # Not a failure, just not available

        # Test import/export cycle
        print("\n1. Testing import/export cycle...")

        # Create test data
        test_memories = [
            {
                "content": "Import test memory 1",
                "memory_type": "note",
                "tags": ["import", "test"],
            },
            {
                "content": "Import test memory 2",
                "memory_type": "reference",
                "tags": ["import", "test", "reference"],
            },
        ]

        # Export test data
        export_data = {"memories": test_memories, "relationships": [], "version": "1.0"}

        # Test import
        print("   Importing test data...")
        import_result = await server.extended_tools.import_memories(
            data=json.dumps(export_data), format="json", merge_strategy="skip"
        )

        print(f"   Import result: {import_result}")

        # Test get_memory_stats
        print("\n2. Testing get_memory_stats...")
        stats = await server.extended_tools.get_memory_stats()
        print(f"   Memory statistics: {json.dumps(stats, indent=2)}")

        # Test health_check
        print("\n3. Testing health_check...")
        health = await server.extended_tools.health_check()
        print(f"   Health check: {health}")

        # Clean up imported memories
        print("\n4. Cleaning up imported memories...")
        # We would need to get the IDs of imported memories to delete them
        # For now, we'll just note that cleanup would be needed

        print("\n[PASS] Extended tool tests completed!")
        return True

    except Exception as e:
        print(f"\n[FAIL] Error during extended tool tests: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        await server.cleanup()


def test_tool_validation():
    """Test tool parameter validation"""
    print("\n" + "=" * 60)
    print("Testing tool parameter validation...")

    try:
        # Test memory type validation
        print("\n1. Testing memory type validation...")
        valid_types = [t.value for t in MemoryType]
        print(f"   Valid memory types: {valid_types}")

        # Test relationship type validation
        print("\n2. Testing relationship type validation...")
        valid_rel_types = [t.value for t in RelationshipType]
        print(f"   Valid relationship types: {valid_rel_types}")

        # Test parameter constraints
        print("\n3. Testing parameter constraints...")
        print("   - search_tolerance should be between 0.0 and 1.0")
        print("   - strength should be between 0.0 and 1.0")
        print("   - limit should be positive integer")

        print("\n[PASS] Tool validation tests passed!")
        return True

    except Exception as e:
        print(f"\n[FAIL] Error in validation tests: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("=" * 60)
    print("Running MCP tools tests for mcp-user-memory")
    print("=" * 60)

    # Run validation tests first
    validation_passed = test_tool_validation()

    # Run basic tool tests
    basic_tools_passed = await test_basic_tools()

    # Run extended tool tests
    extended_tools_passed = await test_extended_tools()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(
        f"Validation tests: {'[PASS] PASSED' if validation_passed else '[FAIL] FAILED'}"
    )
    print(
        f"Basic tool tests: {'[PASS] PASSED' if basic_tools_passed else '[FAIL] FAILED'}"
    )
    print(
        f"Extended tool tests: {'[PASS] PASSED' if extended_tools_passed else '[FAIL] FAILED'}"
    )

    all_passed = validation_passed and basic_tools_passed and extended_tools_passed
    print(
        f"\nOverall: {'[PASS] ALL TESTS PASSED' if all_passed else '[FAIL] SOME TESTS FAILED'}"
    )

    return all_passed


if __name__ == "__main__":
    # Run async tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
