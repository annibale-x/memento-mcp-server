"""Pydantic models for MCP Context Keeper."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Types of memories that can be stored."""
    
    TASK = "task"
    SOLUTION = "solution"
    PROBLEM = "problem"
    FIX = "fix"
    ERROR = "error"
    PREFERENCE = "preference"
    DECISION = "decision"
    COMMAND = "command"
    CONFIGURATION = "configuration"
    DOCUMENTATION = "documentation"
    TEST = "test"
    RESEARCH = "research"
    IDEA = "idea"
    NOTE = "note"
    PERSONAL = "personal"


class RelationshipType(str, Enum):
    """Types of relationships between memories."""
    
    CAUSES = "causes"
    SOLVES = "solves"
    ADDRESSES = "addresses"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"
    VERSION_OF = "version_of"
    ALTERNATIVE_TO = "alternative_to"
    IMPROVES = "improves"
    REFERS_TO = "refers_to"
    PART_OF = "part_of"
    CONTAINS = "contains"
    PRECEDES = "precedes"
    FOLLOWS = "follows"
    SIMILAR_TO = "similar_to"
    CONTRASTS_WITH = "contrasts_with"


class Memory(BaseModel):
    """A single memory/context item."""
    
    id: UUID = Field(default_factory=uuid4)
    content: str
    type: MemoryType = MemoryType.NOTE
    title: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class Relationship(BaseModel):
    """A relationship between two memories."""
    
    id: UUID = Field(default_factory=uuid4)
    source_memory_id: UUID
    target_memory_id: UUID
    type: RelationshipType = RelationshipType.RELATED_TO
    strength: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class MemoryContext(BaseModel):
    """Context information for a project or session."""
    
    id: UUID = Field(default_factory=uuid4)
    project_id: str
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    active_memory_ids: List[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class MemorySearchResult(BaseModel):
    """Result of a memory search."""
    
    memory: Memory
    score: float = Field(ge=0.0, le=1.0)
    highlights: List[str] = Field(default_factory=list)


class Statistics(BaseModel):
    """Statistics about the context keeper."""
    
    total_memories: int = 0
    total_relationships: int = 0
    memory_types: Dict[MemoryType, int] = Field(default_factory=dict)
    relationship_types: Dict[RelationshipType, int] = Field(default_factory=dict)
    recent_activity: List[str] = Field(default_factory=list)
