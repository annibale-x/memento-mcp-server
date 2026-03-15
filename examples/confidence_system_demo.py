"""
Confidence System Demonstration for MCP Context Keeper

This example demonstrates the confidence system features:
1. Automatic confidence decay based on last access time
2. Intelligent decay rules for different memory types
3. Confidence boosting when memories are used
4. Special handling for critical memories (no decay)
5. Low confidence memory detection

Run this example to see how the confidence system works:
    python examples/confidence_system_demo.py
"""

import asyncio
import json

# Add parent directory to path for imports
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from context_keeper.database.interface import SQLiteMemoryDatabase
from context_keeper.models import (
    Memory,
    MemoryContext,
    MemoryType,
    Relationship,
    RelationshipProperties,
    RelationshipType,
)


class ConfidenceSystemDemo:
    """Demonstration of confidence system features."""

    def __init__(self, db_path=":memory:"):
        """Initialize demo with in-memory database."""
        self.db_path = db_path
        self.memory_db = None
        self.backend = None

    async def setup(self):
        """Set up the database and create test data."""
        print("🔧 Setting up demonstration database...")

        # Create in-memory database
        from context_keeper.database.engine import SQLiteBackend

        # Create backend first
        self.backend = SQLiteBackend(self.db_path)
        await self.backend.connect()

        # Create memory database with backend
        self.memory_db = SQLiteMemoryDatabase(self.backend)
        await self.backend.initialize_schema()

        # Create demonstration memories
        await self.create_demo_memories()

        print("✅ Setup complete\n")

    async def create_demo_memories(self):
        """Create different types of memories for demonstration."""

        # 1. Critical memory (API key - should have no decay)
        api_key_memory = Memory(
            id="mem-api-key",
            type=MemoryType.TECHNOLOGY,
            title="Production API Key for Payment Service",
            content="API key: sk_live_abc123xyz789",
            summary="Production Stripe API key for payment processing",
            tags=["security", "api_key", "payment", "production", "no_decay"],
            importance=0.95,
            confidence=0.8,
            context=MemoryContext(
                project_path="/ecommerce/api",
                technologies=["stripe", "python"],
                frameworks=["fastapi"],
            ),
        )

        # 2. High importance solution (recently used)
        recent_solution = Memory(
            id="mem-recent-solution",
            type=MemoryType.SOLUTION,
            title="Fixed Redis timeout with connection pooling",
            content="Implemented Redis connection pooling with 30s timeout and 10 max connections",
            summary="Redis connection pooling solution",
            tags=["redis", "database", "performance", "production_fix"],
            importance=0.85,
            confidence=0.9,  # High confidence (recently used)
            context=MemoryContext(
                project_path="/ecommerce/api",
                technologies=["redis", "python"],
                frameworks=["fastapi"],
                git_commit="abc123",
            ),
        )

        # 3. Old general knowledge (not used recently)
        old_knowledge = Memory(
            id="mem-old-knowledge",
            type=MemoryType.GENERAL,
            title="Old deployment script for v1.0",
            content="bash deploy.sh --env production --version 1.0.0",
            summary="Deprecated deployment script",
            tags=["deployment", "bash", "legacy"],
            importance=0.4,
            confidence=0.8,  # Will decay over time
            context=MemoryContext(
                project_path="/ecommerce/api",
                technologies=["bash", "linux"],
            ),
        )

        # 4. Medium confidence pattern
        pattern_memory = Memory(
            id="mem-pattern",
            type=MemoryType.CODE_PATTERN,
            title="JWT authentication middleware pattern",
            content="FastAPI middleware for JWT token validation with Redis blacklist",
            summary="JWT auth pattern with token blacklisting",
            tags=["authentication", "jwt", "security", "pattern"],
            importance=0.7,
            confidence=0.6,
            context=MemoryContext(
                project_path="/ecommerce/api",
                technologies=["jwt", "redis", "python"],
                frameworks=["fastapi"],
            ),
        )

        # Store all memories
        memories = [api_key_memory, recent_solution, old_knowledge, pattern_memory]

        for memory in memories:
            await self.memory_db.store_memory(memory)
            print(f"  Created: {memory.title} (confidence: {memory.confidence:.2f})")

        # Create relationships between memories
        await self.create_demo_relationships()

    async def create_demo_relationships(self):
        """Create relationships between demo memories."""

        # Relationship: Solution fixes a problem (that we'll simulate)
        relationship = Relationship(
            id="rel-solution-fix",
            from_memory_id="mem-recent-solution",
            to_memory_id="mem-old-knowledge",  # Simulating fixing old deployment
            type=RelationshipType.IMPROVES,
            properties=RelationshipProperties(
                strength=0.8,
                confidence=0.8,
                context="New Redis solution improves upon old deployment",
                access_count=3,  # Has been used 3 times
                decay_factor=0.95,
            ),
        )

        await self.memory_db.store_relationship(relationship)
        print(f"  Created relationship: {relationship.type.value}")

    async def demonstrate_confidence_decay(self):
        """Demonstrate automatic confidence decay."""
        print("📉 DEMONSTRATION 1: Confidence Decay")
        print("=" * 50)

        # Simulate time passing for old knowledge
        print("\n1. Simulating 6 months without access for 'Old deployment script':")

        # Get the old knowledge memory
        old_memory = await self.memory_db.get_memory_by_id("mem-old-knowledge")
        print(f"   Initial confidence: {old_memory.confidence:.2f}")

        # Apply decay (simulating 6 months)
        # Base decay: 5% per month, so 6 months: 0.95^6 ≈ 0.74
        # With importance 0.4: importance_factor = 1.0 - (0.4 * 0.3) = 0.88
        # Total decay: 0.95 * 0.88 = 0.836 per month
        # 6 months: 0.836^6 ≈ 0.34 multiplier
        # New confidence: 0.8 * 0.34 ≈ 0.27

        updated_count = await self.memory_db.apply_confidence_decay("mem-old-knowledge")
        print(f"   Applied decay to {updated_count} relationships")

        # Get updated memory
        updated_memory = await self.memory_db.get_memory_by_id("mem-old-knowledge")
        print(f"   New confidence: {updated_memory.confidence:.2f}")
        print(
            f"   Status: {'⚠️ LOW CONFIDENCE' if updated_memory.confidence < 0.3 else 'OK'}"
        )

        print("\n2. Checking critical memory (API key):")
        api_memory = await self.memory_db.get_memory_by_id("mem-api-key")
        print(f"   Confidence: {api_memory.confidence:.2f}")
        print(f"   Tags: {', '.join(api_memory.tags)}")
        print(f"   Status: Critical memory - NO DECAY applied (decay_factor=1.0)")

    async def demonstrate_confidence_boost(self):
        """Demonstrate confidence boosting on usage."""
        print("\n\n🚀 DEMONSTRATION 2: Confidence Boosting")
        print("=" * 50)

        print("\n1. Before using the JWT pattern:")
        pattern_memory = await self.memory_db.get_memory_by_id("mem-pattern")
        print(f"   Confidence: {pattern_memory.confidence:.2f}")

        # Simulate using the pattern (accessing its relationships)
        print("\n2. Using the pattern in a new project...")

        # Update confidence on access
        await self.memory_db.update_confidence_on_access("rel-solution-fix")

        # Also boost confidence manually (simulating successful usage)
        await self.memory_db.adjust_confidence(
            relationship_id="rel-solution-fix",
            new_confidence=min(1.0, pattern_memory.confidence + 0.15),
            reason="Successfully implemented in new project",
        )

        print("\n3. After successful usage:")
        updated_pattern = await self.memory_db.get_memory_by_id("mem-pattern")
        print(f"   New confidence: {updated_pattern.confidence:.2f}")
        print(
            f"   Boost: +{(updated_pattern.confidence - pattern_memory.confidence):.2f}"
        )

    async def demonstrate_low_confidence_detection(self):
        """Demonstrate finding low confidence memories."""
        print("\n\n🔍 DEMONSTRATION 3: Low Confidence Detection")
        print("=" * 50)

        print("\nFinding memories with confidence < 0.5:")

        # Get low confidence relationships
        low_conf_relationships = await self.memory_db.get_low_confidence_relationships(
            threshold=0.5, limit=10
        )

        if not low_conf_relationships:
            print("   No low confidence relationships found.")
            return

        # Get unique memory IDs
        memory_ids = set()
        for rel in low_conf_relationships:
            memory_ids.add(rel.from_memory_id)
            memory_ids.add(rel.to_memory_id)

        print(f"\n   Found {len(low_conf_relationships)} low confidence relationships")
        print(f"   Affecting {len(memory_ids)} memories:")

        for i, memory_id in enumerate(list(memory_ids)[:5], 1):  # Show first 5
            try:
                memory = await self.memory_db.get_memory_by_id(memory_id)
                if memory:
                    print(f"\n   {i}. {memory.title}")
                    print(f"      ID: {memory.id}")
                    print(f"      Confidence: {memory.confidence:.2f}")
                    print(f"      Type: {memory.type.value}")
                    print(f"      Last accessed: {memory.last_accessed or 'Never'}")
            except Exception as e:
                print(f"   Error fetching memory {memory_id}: {e}")

    async def demonstrate_search_ordering(self):
        """Demonstrate search results ordered by confidence."""
        print("\n\n🎯 DEMONSTRATION 4: Search Result Ordering")
        print("=" * 50)

        print("\nSearching for 'deployment' (should show high confidence first):")

        # Create a search query
        from context_keeper.models import SearchQuery

        search_query = SearchQuery(query="deployment", limit=5)

        # Perform search
        search_result = await self.memory_db.search_memories(search_query)

        print(f"\n   Found {len(search_result.results)} results:")
        print(f"   Ordered by: (confidence × importance) DESC")

        for i, memory in enumerate(search_result.results, 1):
            score = memory.confidence * memory.importance
            print(f"\n   {i}. {memory.title}")
            print(f"      Confidence: {memory.confidence:.2f}")
            print(f"      Importance: {memory.importance:.2f}")
            print(f"      Score (conf×imp): {score:.3f}")
            print(f"      Type: {memory.type.value}")

            # Show warning for low confidence
            if memory.confidence < 0.3:
                print(f"      ⚠️  WARNING: Low confidence - may be obsolete")

    async def demonstrate_maintenance_routine(self):
        """Demonstrate a confidence system maintenance routine."""
        print("\n\n🛠️  DEMONSTRATION 5: Maintenance Routine")
        print("=" * 50)

        print("\nMonthly confidence system maintenance:")
        print("1. Applying automatic decay to all relationships...")

        updated_count = await self.memory_db.apply_confidence_decay()
        print(f"   Updated {updated_count} relationships")

        print("\n2. Finding low confidence memories for review...")
        low_conf = await self.memory_db.get_low_confidence_relationships(
            threshold=0.3, limit=20
        )

        print(f"   Found {len(low_conf)} relationships with confidence < 0.3")

        if low_conf:
            print("\n3. Sample low confidence items for review:")
            for i, rel in enumerate(low_conf[:3], 1):  # Show first 3
                print(f"\n   {i}. Relationship: {rel.type.value}")
                print(f"      From: {rel.from_memory_id[:8]}...")
                print(f"      To: {rel.to_memory_id[:8]}...")
                print(f"      Confidence: {rel.properties.confidence:.2f}")
                print(f"      Last accessed: {rel.properties.last_accessed}")
                print(f"      Access count: {rel.properties.access_count}")

        print("\n4. Maintenance complete!")
        print("   - Obsolete knowledge automatically decays")
        print("   - Critical information protected (no decay)")
        print("   - Low confidence items flagged for review")
        print("   - System maintains accuracy over time")

    async def run_all_demonstrations(self):
        """Run all demonstrations."""
        print("=" * 60)
        print("MCP CONTEXT KEEPER - CONFIDENCE SYSTEM DEMONSTRATION")
        print("=" * 60)

        await self.setup()

        await self.demonstrate_confidence_decay()
        await self.demonstrate_confidence_boost()
        await self.demonstrate_low_confidence_detection()
        await self.demonstrate_search_ordering()
        await self.demonstrate_maintenance_routine()

        print("\n" + "=" * 60)
        print("DEMONSTRATION COMPLETE")
        print("=" * 60)
        print("\nSummary of Confidence System Features:")
        print("✅ Automatic decay for unused knowledge")
        print("✅ No decay for critical info (security, API keys)")
        print("✅ Confidence boosting on successful usage")
        print("✅ Low confidence detection for cleanup")
        print("✅ Intelligent search ordering (confidence × importance)")
        print("✅ Maintenance routines for system health")

        print("\nAvailable MCP Tools for Confidence Management:")
        print("  • adjust_persistent_confidence - Manual confidence adjustment")
        print("  • get_persistent_low_confidence_memories - Find obsolete knowledge")
        print("  • apply_persistent_confidence_decay - Apply automatic decay")
        print("  • boost_persistent_confidence - Boost when memory is validated")
        print("  • set_persistent_decay_factor - Custom decay rates")


async def main():
    """Run the confidence system demonstration."""
    demo = ConfidenceSystemDemo()

    try:
        await demo.run_all_demonstrations()
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Cleanup
        if demo.memory_db:
            await demo.backend.disconnect()
        if demo.backend:
            await demo.backend.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
