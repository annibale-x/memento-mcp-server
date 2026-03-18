"""
Relationship test suite for mcp-memento.

This module tests relationship models, types, validation, and serialization.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path to import memento
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from pydantic import ValidationError as PydanticValidationError

from memento.models import (
    Memory,
    MemoryContext,
    MemoryType,
    Relationship,
    RelationshipProperties,
    RelationshipType,
)


class TestRelationshipModels:
    """Test relationship model classes and functionality."""

    def test_relationship_creation(self):
        """Test basic relationship creation with all fields."""
        relationship = Relationship(
            from_memory_id="memory_test_1",
            to_memory_id="memory_test_2",
            type=RelationshipType.RELATED_TO,
            properties=RelationshipProperties(
                context="Test relationship between two memories",
                strength=0.8,
                confidence=0.9,
                evidence_count=3,
                success_rate=0.95,
            ),
        )

        assert relationship.from_memory_id == "memory_test_1"
        assert relationship.to_memory_id == "memory_test_2"
        assert relationship.type == RelationshipType.RELATED_TO
        assert relationship.properties.strength == 0.8
        assert relationship.properties.confidence == 0.9
        assert (
            relationship.properties.context == "Test relationship between two memories"
        )
        assert relationship.properties.evidence_count == 3
        assert relationship.properties.success_rate == 0.95
        # Note: metadata field was removed from RelationshipProperties

    def test_relationship_creation_minimal(self):
        """Test relationship creation with minimal required fields."""
        relationship = Relationship(
            from_memory_id="memory_min_1",
            to_memory_id="memory_min_2",
            type=RelationshipType.DEPENDS_ON,
        )

        assert relationship.from_memory_id == "memory_min_1"
        assert relationship.to_memory_id == "memory_min_2"
        assert relationship.type == RelationshipType.DEPENDS_ON
        assert relationship.properties is not None
        assert relationship.properties.strength == 0.5  # default value
        assert relationship.properties.confidence == 0.8  # default value

    def test_relationship_with_custom_id(self):
        """Test relationship creation with custom ID."""
        relationship = Relationship(
            id="custom_relationship_123",
            from_memory_id="memory_a",
            to_memory_id="memory_b",
            type=RelationshipType.SOLVES,
        )

        assert relationship.id == "custom_relationship_123"
        assert relationship.from_memory_id == "memory_a"
        assert relationship.to_memory_id == "memory_b"
        assert relationship.type == RelationshipType.SOLVES

    def test_relationship_equality(self):
        """Test relationship equality comparison."""
        # Use a fixed timestamp to avoid flakiness from default_factory=datetime.now()
        fixed_ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        fixed_props = RelationshipProperties(
            context="Test", strength=0.5,
            created_at=fixed_ts, last_validated=fixed_ts,
        )

        relationship1 = Relationship(
            from_memory_id="mem_1",
            to_memory_id="mem_2",
            type=RelationshipType.CAUSES,
            properties=fixed_props.model_copy(),
        )

        relationship2 = Relationship(
            from_memory_id="mem_1",
            to_memory_id="mem_2",
            type=RelationshipType.CAUSES,
            properties=fixed_props.model_copy(),
        )

        relationship3 = Relationship(
            from_memory_id="mem_2",
            to_memory_id="mem_1",
            type=RelationshipType.CAUSES,
            properties=fixed_props.model_copy(),
        )

        # Same IDs and values should be equal
        relationship1.id = "same_id"
        relationship2.id = "same_id"
        assert relationship1 == relationship2

        # Different IDs should not be equal
        relationship3.id = "different_id"
        assert relationship1 != relationship3

    def test_relationship_hash(self):
        """Test relationship hashing for use in sets and dicts."""
        relationship = Relationship(
            id="hash_test_123",
            from_memory_id="mem_a",
            to_memory_id="mem_b",
            type=RelationshipType.IMPROVES,
        )

        # Note: Pydantic v2 models are not hashable by default
        # Instead, test that we can use the ID for hashing purposes
        assert relationship.id == "hash_test_123"

        # Test that we can still work with relationships in collections using IDs
        relationship_dict = {relationship.id: relationship}
        assert relationship_dict["hash_test_123"] == relationship

        # Test equality comparison - for Pydantic v2 with timestamps,
        # we need to compare specific fields since timestamps differ
        relationship2 = Relationship(
            id="hash_test_123",
            from_memory_id="mem_a",
            to_memory_id="mem_b",
            type=RelationshipType.IMPROVES,
        )

        # Compare key fields instead of full object equality
        assert relationship.id == relationship2.id
        assert relationship.from_memory_id == relationship2.from_memory_id
        assert relationship.to_memory_id == relationship2.to_memory_id
        assert relationship.type == relationship2.type

    def test_relationship_string_representation(self):
        """Test relationship string representation for debugging."""
        relationship = Relationship(
            from_memory_id="mem_from",
            to_memory_id="mem_to",
            type=RelationshipType.ADDRESSES,
            properties=RelationshipProperties(context="Debug test", strength=0.7),
        )

        representation = str(relationship)
        assert "mem_from" in representation
        assert "mem_to" in representation
        assert "ADDRESSES" in representation
        assert "Relationship" in representation


class TestRelationshipProperties:
    """Test RelationshipProperties model and validation."""

    def test_relationship_properties_creation(self):
        """Test RelationshipProperties creation with all fields."""
        properties = RelationshipProperties(
            context="Detailed test context for relationship validation",
            strength=0.75,
            confidence=0.85,
            evidence_count=5,
            success_rate=0.92,
        )

        assert properties.context == "Detailed test context for relationship validation"
        assert properties.strength == 0.75
        assert properties.confidence == 0.85
        assert properties.evidence_count == 5
        assert properties.success_rate == 0.92

    def test_relationship_properties_minimal(self):
        """Test RelationshipProperties creation with minimal fields."""
        properties = RelationshipProperties(
            context="Minimal context",
            strength=0.5,
            confidence=0.6,
        )

        assert properties.context == "Minimal context"
        assert properties.strength == 0.5
        assert properties.confidence == 0.6
        assert properties.evidence_count == 1  # default value
        assert properties.success_rate is None

    def test_relationship_properties_default_values(self):
        """Test RelationshipProperties default values."""
        properties = RelationshipProperties()

        assert properties.context is None
        assert properties.strength == 0.5
        assert properties.confidence == 0.8
        assert properties.evidence_count == 1
        assert properties.success_rate is None

    def test_relationship_properties_strength_validation(self):
        """Test strength validation in RelationshipProperties."""
        # Valid values
        properties1 = RelationshipProperties(strength=0.0)
        properties2 = RelationshipProperties(strength=0.5)
        properties3 = RelationshipProperties(strength=1.0)

        assert properties1.strength == 0.0
        assert properties2.strength == 0.5
        assert properties3.strength == 1.0

        # Invalid values should raise ValueError
        with pytest.raises(PydanticValidationError):
            RelationshipProperties(strength=-0.1)

        with pytest.raises(PydanticValidationError):
            RelationshipProperties(strength=1.1)

    def test_relationship_properties_confidence_validation(self):
        """Test confidence validation in RelationshipProperties."""
        # Valid values
        properties1 = RelationshipProperties(confidence=0.0)
        properties2 = RelationshipProperties(confidence=0.7)
        properties3 = RelationshipProperties(confidence=1.0)

        assert properties1.confidence == 0.0
        assert properties2.confidence == 0.7
        assert properties3.confidence == 1.0

        # Invalid values should raise ValueError
        with pytest.raises(PydanticValidationError):
            RelationshipProperties(confidence=-0.1)

        with pytest.raises(PydanticValidationError):
            RelationshipProperties(confidence=1.1)

    def test_relationship_properties_success_rate_validation(self):
        """Test success rate validation in RelationshipProperties."""
        # Valid values
        properties1 = RelationshipProperties(success_rate=0.0)
        properties2 = RelationshipProperties(success_rate=0.8)
        properties3 = RelationshipProperties(success_rate=1.0)

        assert properties1.success_rate == 0.0
        assert properties2.success_rate == 0.8
        assert properties3.success_rate == 1.0

        # Invalid values should raise ValueError
        with pytest.raises(PydanticValidationError):
            RelationshipProperties(success_rate=-0.1)

        with pytest.raises(PydanticValidationError):
            RelationshipProperties(success_rate=1.1)

    def test_relationship_properties_evidence_count_validation(self):
        """Test evidence count validation in RelationshipProperties."""
        # Valid values
        properties1 = RelationshipProperties(evidence_count=0)
        properties2 = RelationshipProperties(evidence_count=10)
        properties3 = RelationshipProperties(evidence_count=1000)

        assert properties1.evidence_count == 0
        assert properties2.evidence_count == 10
        assert properties3.evidence_count == 1000

        # Invalid values should raise ValueError
        with pytest.raises(PydanticValidationError):
            RelationshipProperties(evidence_count=-1)

        with pytest.raises(PydanticValidationError):
            RelationshipProperties(evidence_count=-1000)

    def test_relationship_properties_string_representation(self):
        """Test RelationshipProperties string representation."""
        properties = RelationshipProperties(
            context="Test properties",
            strength=0.8,
            confidence=0.9,
        )

        representation = str(properties)
        assert "Test properties" in representation
        assert "0.8" in representation
        assert "0.9" in representation
        # Pydantic v2 representation doesn't include class name by default
        # Test that key fields are present instead
        assert "strength=0.8" in representation
        assert "confidence=0.9" in representation
        assert "context='Test properties'" in representation


class TestRelationshipTypeEnum:
    """Test RelationshipType enumeration."""

    def test_all_relationship_types_exist(self):
        """Verify all expected relationship types are defined."""
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
            ("USED_IN", "USED_IN"),
            ("BUILDS_ON", "BUILDS_ON"),
            ("CONTRADICTS", "CONTRADICTS"),
            ("CONFIRMS", "CONFIRMS"),
            ("GENERALIZES", "GENERALIZES"),
            ("SPECIALIZES", "SPECIALIZES"),
            ("SIMILAR_TO", "SIMILAR_TO"),
            ("VARIANT_OF", "VARIANT_OF"),
            ("RELATED_TO", "RELATED_TO"),
            ("ANALOGY_TO", "ANALOGY_TO"),
            ("OPPOSITE_OF", "OPPOSITE_OF"),
            ("FOLLOWS", "FOLLOWS"),
            ("DEPENDS_ON", "DEPENDS_ON"),
            ("ENABLES", "ENABLES"),
            ("BLOCKS", "BLOCKS"),
            ("PARALLEL_TO", "PARALLEL_TO"),
            ("EFFECTIVE_FOR", "EFFECTIVE_FOR"),
            ("INEFFECTIVE_FOR", "INEFFECTIVE_FOR"),
            ("PREFERRED_OVER", "PREFERRED_OVER"),
            ("DEPRECATED_BY", "DEPRECATED_BY"),
            ("VALIDATED_BY", "VALIDATED_BY"),
        ]

        for value, name in expected_types:
            rel_type = RelationshipType(value)
            assert rel_type.name == name
            assert rel_type.value == value

    def test_relationship_type_from_string(self):
        """Test creating RelationshipType from string values."""
        assert RelationshipType("CAUSES") == RelationshipType.CAUSES
        assert RelationshipType("SOLVES") == RelationshipType.SOLVES
        assert RelationshipType("RELATED_TO") == RelationshipType.RELATED_TO
        assert RelationshipType("DEPENDS_ON") == RelationshipType.DEPENDS_ON

    def test_relationship_type_case_insensitive(self):
        """Test that relationship type values are case-sensitive as defined."""
        # RelationshipType uses uppercase values
        assert RelationshipType("CAUSES").value == "CAUSES"

        # Lowercase should raise ValueError
        with pytest.raises(ValueError):
            RelationshipType("causes")

    def test_relationship_type_iteration(self):
        """Test iterating over RelationshipType enumeration."""
        all_types = list(RelationshipType)
        assert len(all_types) > 0

        # All should be RelationshipType instances
        for rel_type in all_types:
            assert isinstance(rel_type, RelationshipType)

    def test_invalid_relationship_type(self):
        """Test that invalid relationship type raises ValueError."""
        with pytest.raises(ValueError):
            RelationshipType("INVALID_TYPE_NAME")

        with pytest.raises(ValueError):
            RelationshipType("non_existent")

        with pytest.raises(ValueError):
            RelationshipType("causes")  # lowercase should fail

    def test_relationship_type_comparison(self):
        """Test RelationshipType comparison operations."""
        assert RelationshipType.CAUSES == RelationshipType.CAUSES
        assert RelationshipType.CAUSES != RelationshipType.SOLVES
        assert RelationshipType.RELATED_TO != RelationshipType.DEPENDS_ON

    def test_relationship_type_string_representation(self):
        """Test RelationshipType string representation."""
        assert str(RelationshipType.CAUSES) == "RelationshipType.CAUSES"
        assert str(RelationshipType.SOLVES) == "RelationshipType.SOLVES"
        assert (
            repr(RelationshipType.RELATED_TO)
            == "<RelationshipType.RELATED_TO: 'RELATED_TO'>"
        )


class TestMemoryModelsForRelationships:
    """Test Memory models that are used in relationships."""

    def test_memory_creation_for_relationships(self):
        """Test Memory creation that can be used in relationships."""
        memory = Memory(
            type=MemoryType.SOLUTION,
            title="Test solution for relationship testing",
            content="This memory will be used to test relationship connections.",
            tags=["relationship", "test", "integration"],
            importance=0.8,
            confidence=0.9,
        )

        assert memory.type == MemoryType.SOLUTION
        assert memory.title == "Test solution for relationship testing"
        assert memory.tags == ["relationship", "test", "integration"]
        assert memory.importance == 0.8
        assert memory.confidence == 0.9

    def test_memory_with_context_for_relationships(self):
        """Test Memory with context for relationship testing."""
        context = MemoryContext(
            project_path="/test/project",
            files_involved=["test_relationships.py", "models.py"],
            languages=["python"],
            frameworks=["pytest"],
            git_branch="test/relationships",
            working_directory="/tmp/test",
        )

        memory = Memory(
            type=MemoryType.CODE_PATTERN,
            title="Relationship test pattern",
            content="Pattern for testing memory relationships",
            tags=["pattern", "test"],
            context=context,
        )

        assert memory.context is not None
        assert memory.context.project_path == "/test/project"
        assert "test_relationships.py" in memory.context.files_involved
        assert memory.context.languages == ["python"]

    def test_memory_validation_for_relationships(self):
        """Test memory validation that affects relationship creation."""
        # Valid memory
        memory = Memory(
            type=MemoryType.PROBLEM,
            title="Valid problem title",
            content="Valid content for testing",
        )

        assert memory.title == "Valid problem title"
        assert memory.content == "Valid content for testing"

        # Invalid memory should raise ValueError
        with pytest.raises(ValueError):
            Memory(type=MemoryType.TASK, title="", content="Some content")

        with pytest.raises(ValueError):
            Memory(type=MemoryType.TASK, title="Valid title", content="")

    def test_memory_type_enumeration(self):
        """Test MemoryType enumeration for relationship contexts."""
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

    def test_memory_type_from_string(self):
        """Test creating MemoryType from string values."""
        assert MemoryType("task") == MemoryType.TASK
        assert MemoryType("solution") == MemoryType.SOLUTION
        assert MemoryType("problem") == MemoryType.PROBLEM
        assert MemoryType("error") == MemoryType.ERROR


class TestRelationshipSerialization:
    """Test relationship serialization and deserialization."""

    def test_relationship_json_serialization(self):
        """Test Relationship serialization to JSON."""
        relationship = Relationship(
            from_memory_id="mem_serialize_1",
            to_memory_id="mem_serialize_2",
            type=RelationshipType.IMPROVES,
            properties=RelationshipProperties(
                context="Serialization test",
                strength=0.7,
                confidence=0.8,
            ),
        )

        # Serialize using model_dump with json mode for datetime handling
        relationship_dict = relationship.model_dump(mode="json")

        # Verify dictionary structure
        assert relationship_dict["from_memory_id"] == "mem_serialize_1"
        assert relationship_dict["to_memory_id"] == "mem_serialize_2"
        assert relationship_dict["type"] == "IMPROVES"
        assert relationship_dict["properties"]["context"] == "Serialization test"
        assert relationship_dict["properties"]["strength"] == 0.7
        assert relationship_dict["properties"]["confidence"] == 0.8

        # Convert to JSON string
        relationship_json = json.dumps(relationship_dict)

        # Parse back
        loaded_dict = json.loads(relationship_json)
        assert loaded_dict["from_memory_id"] == "mem_serialize_1"
        assert loaded_dict["type"] == "IMPROVES"

    def test_relationship_json_deserialization(self):
        """Test Relationship deserialization from JSON."""
        relationship_data = {
            "from_memory_id": "mem_deserialize_1",
            "to_memory_id": "mem_deserialize_2",
            "type": "DEPENDS_ON",
            "properties": {
                "context": "Deserialization test",
                "strength": 0.6,
                "confidence": 0.75,
                "evidence_count": 2,
                "success_rate": 0.85,
            },
        }

        # Deserialize using model_validate
        relationship = Relationship.model_validate(relationship_data)

        assert relationship.from_memory_id == "mem_deserialize_1"
        assert relationship.to_memory_id == "mem_deserialize_2"
        assert relationship.type == RelationshipType.DEPENDS_ON
        assert relationship.properties.context == "Deserialization test"
        assert relationship.properties.strength == 0.6
        assert relationship.properties.confidence == 0.75
        # Note: notes field was removed from RelationshipProperties

        # Test with JSON string
        json_data = json.dumps(relationship_data)
        relationship_dict = json.loads(json_data)
        relationship2 = Relationship(**relationship_dict)

        assert relationship2.from_memory_id == "mem_deserialize_1"
        assert relationship2.to_memory_id == "mem_deserialize_2"
        assert relationship2.type == RelationshipType.DEPENDS_ON

    def test_relationship_serialization_without_properties(self):
        """Test relationship serialization with default properties."""
        relationship = Relationship(
            from_memory_id="mem_no_props_1",
            to_memory_id="mem_no_props_2",
            type=RelationshipType.DEPENDS_ON,
        )

        relationship_dict = relationship.model_dump(mode="json")
        assert relationship_dict["from_memory_id"] == "mem_no_props_1"
        assert relationship_dict["to_memory_id"] == "mem_no_props_2"
        assert relationship_dict["type"] == "DEPENDS_ON"
        assert relationship_dict["properties"] is not None
        assert relationship_dict["properties"]["strength"] == 0.5
        assert relationship_dict["properties"]["confidence"] == 0.8

    def test_relationship_properties_json_serialization(self):
        """Test RelationshipProperties serialization to JSON."""
        properties = RelationshipProperties(
            context="Serialization test",
            strength=0.9,
            confidence=0.95,
            evidence_count=4,
            success_rate=0.98,
        )

        properties_dict = properties.model_dump(mode="json")

        assert properties_dict["context"] == "Serialization test"
        assert properties_dict["strength"] == 0.9
        assert properties_dict["confidence"] == 0.95
        assert properties_dict["evidence_count"] == 4
        assert properties_dict["success_rate"] == 0.98
        # Note: metadata field was removed from RelationshipProperties

    def test_relationship_roundtrip_serialization(self):
        """Test complete round-trip serialization and deserialization."""
        original_relationship = Relationship(
            id="roundtrip_123",
            from_memory_id="mem_roundtrip_1",
            to_memory_id="mem_roundtrip_2",
            type=RelationshipType.SOLVES,
            properties=RelationshipProperties(
                context="Roundtrip serialization test",
                strength=0.75,
                confidence=0.85,
                evidence_count=3,
                success_rate=0.92,
            ),
        )

        # Serialize
        relationship_dict = original_relationship.model_dump(mode="json")
        relationship_json = json.dumps(relationship_dict)

        # Deserialize
        loaded_dict = json.loads(relationship_json)
        restored_relationship = Relationship.model_validate(loaded_dict)

        # Verify equality
        assert restored_relationship.id == original_relationship.id
        assert (
            restored_relationship.from_memory_id == original_relationship.from_memory_id
        )
        assert restored_relationship.to_memory_id == original_relationship.to_memory_id
        assert restored_relationship.type == original_relationship.type
        assert (
            restored_relationship.properties.context
            == original_relationship.properties.context
        )
        assert (
            restored_relationship.properties.strength
            == original_relationship.properties.strength
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
