"""
Test file for relationship functionality in mcp-context-keeper
Tests relationship models and types without requiring server initialization.
"""

import json
import os
import sys

import pytest

# Add parent directory to path to import context_keeper
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from context_keeper.models import (
    Memory,
    MemoryType,
    Relationship,
    RelationshipProperties,
    RelationshipType,
)


def test_relationship_models():
    """Test relationship model functionality"""
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

    assert relationship.type == RelationshipType.RELATED_TO
    assert relationship.properties.strength == 0.8
    assert relationship.properties.confidence == 0.9

    # Test serialization using model_dump with json mode for datetime serialization
    relationship_dict = relationship.model_dump(mode="json")

    # Test deserialization
    relationship_json = json.dumps(relationship_dict)
    loaded_dict = json.loads(relationship_json)
    assert loaded_dict["type"] == "RELATED_TO"

    # Test Memory model creation
    memory = Memory(
        type=MemoryType.SOLUTION,
        title="Test memory title",
        content="Test memory content",
        tags=["test", "relationship"],
    )

    assert memory.type == MemoryType.SOLUTION
    assert memory.title == "Test memory title"


def test_relationship_types():
    """Test relationship type enumeration"""
    # Test value access
    assert RelationshipType.CAUSES.value == "CAUSES"
    assert RelationshipType.RELATED_TO.value == "RELATED_TO"
    assert RelationshipType.SOLVES.value == "SOLVES"
    assert RelationshipType.ADDRESSES.value == "ADDRESSES"
    assert RelationshipType.DEPENDS_ON.value == "DEPENDS_ON"

    # Test string to enum conversion
    assert RelationshipType("CAUSES") == RelationshipType.CAUSES
    assert RelationshipType("RELATED_TO") == RelationshipType.RELATED_TO
    assert RelationshipType("SOLVES") == RelationshipType.SOLVES


def test_memory_types():
    """Test memory type enumeration"""
    # Test value access
    assert MemoryType.TASK.value == "task"
    assert MemoryType.SOLUTION.value == "solution"
    assert MemoryType.PROBLEM.value == "problem"
    assert MemoryType.FIX.value == "fix"
    assert MemoryType.ERROR.value == "error"

    # Test string to enum conversion
    assert MemoryType("task") == MemoryType.TASK
    assert MemoryType("solution") == MemoryType.SOLUTION
    assert MemoryType("problem") == MemoryType.PROBLEM


def test_relationship_properties():
    """Test relationship properties model"""
    # Test RelationshipProperties creation
    properties = RelationshipProperties(
        strength=0.7,
        confidence=0.8,
        context="Test context for relationship",
        evidence_count=3,
        success_rate=0.9,
    )

    assert properties.strength == 0.7
    assert properties.confidence == 0.8
    assert properties.context == "Test context for relationship"
    assert properties.evidence_count == 3
    assert properties.success_rate == 0.9

    # Test validation
    # Strength should be between 0.0 and 1.0
    with pytest.raises(ValueError):
        RelationshipProperties(strength=1.5)

    # Confidence should be between 0.0 and 1.0
    with pytest.raises(ValueError):
        RelationshipProperties(confidence=-0.1)
