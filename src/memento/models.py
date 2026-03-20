"""
Data models and schemas for Claude Code Memory Server.

This module defines the core data structures used throughout the memory system,
including memory types, relationships, and validation schemas.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MemoryType(str, Enum):
    """Types of memories that can be stored in the system."""

    TASK = "task"
    CODE_PATTERN = "code_pattern"
    PROBLEM = "problem"
    SOLUTION = "solution"
    PROJECT = "project"
    TECHNOLOGY = "technology"
    ERROR = "error"
    FIX = "fix"
    COMMAND = "command"
    FILE_CONTEXT = "file_context"
    WORKFLOW = "workflow"
    GENERAL = "general"
    CONVERSATION = "conversation"


class RelationshipType(str, Enum):
    """Types of relationships between memories."""

    # Causal relationships
    CAUSES = "CAUSES"
    TRIGGERS = "TRIGGERS"
    LEADS_TO = "LEADS_TO"
    PREVENTS = "PREVENTS"
    BREAKS = "BREAKS"

    # Solution relationships
    SOLVES = "SOLVES"
    ADDRESSES = "ADDRESSES"
    ALTERNATIVE_TO = "ALTERNATIVE_TO"
    IMPROVES = "IMPROVES"
    REPLACES = "REPLACES"

    # Context relationships
    OCCURS_IN = "OCCURS_IN"
    APPLIES_TO = "APPLIES_TO"
    WORKS_WITH = "WORKS_WITH"
    REQUIRES = "REQUIRES"
    USED_IN = "USED_IN"

    # Learning relationships
    BUILDS_ON = "BUILDS_ON"
    CONTRADICTS = "CONTRADICTS"
    CONFIRMS = "CONFIRMS"
    GENERALIZES = "GENERALIZES"
    SPECIALIZES = "SPECIALIZES"

    # Similarity relationships
    SIMILAR_TO = "SIMILAR_TO"
    VARIANT_OF = "VARIANT_OF"
    RELATED_TO = "RELATED_TO"
    ANALOGY_TO = "ANALOGY_TO"
    OPPOSITE_OF = "OPPOSITE_OF"

    # Workflow relationships
    FOLLOWS = "FOLLOWS"
    DEPENDS_ON = "DEPENDS_ON"
    ENABLES = "ENABLES"
    BLOCKS = "BLOCKS"
    PARALLEL_TO = "PARALLEL_TO"

    # Quality relationships
    EFFECTIVE_FOR = "EFFECTIVE_FOR"
    INEFFECTIVE_FOR = "INEFFECTIVE_FOR"
    PREFERRED_OVER = "PREFERRED_OVER"
    DEPRECATED_BY = "DEPRECATED_BY"
    VALIDATED_BY = "VALIDATED_BY"


class MemoryContext(BaseModel):
    """Context information for a memory.

    Provides scoping and metadata for memories, primarily through project_path.
    All fields are optional to support various usage patterns.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "project_path": "/my/project",
                    "session_id": "session-123",
                    "files_involved": ["main.py", "utils.py"],
                    "languages": ["python"],
                    "frameworks": ["fastapi"],
                },
                {
                    "project_path": "/apps/api",
                    "git_branch": "main",
                    "working_directory": "/home/user/projects/api",
                    "user_id": "alice",
                },
                {
                    "project_path": "/personal/notes",
                    "session_id": "notes-456",
                    "user_id": "bob",
                },
            ]
        }
    )

    # === Context fields ===
    project_path: Optional[str] = None
    files_involved: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    working_directory: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    additional_metadata: Dict[str, Any] = Field(default_factory=dict)


class Memory(BaseModel):
    """Core memory data structure.

    Represents a single memory entry in the system with metadata,
    content, relationships, and tracking information.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "mem_abc123",
                    "type": "solution",
                    "title": "Fixed Redis timeout issue",
                    "content": "Increased Redis connection timeout to 30 seconds...",
                    "summary": "Redis timeout fix",
                    "tags": ["redis", "timeout", "connection"],
                    "importance": 0.8,
                    "confidence": 0.9,
                    "usage_count": 5,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "context": {"project_path": "/my/app", "git_branch": "main"},
                },
                {
                    "id": "mem_def456",
                    "type": "error",
                    "title": "Database connection failed",
                    "content": "Error: could not connect to PostgreSQL...",
                    "tags": ["postgresql", "database", "error"],
                    "importance": 0.9,
                    "confidence": 0.8,
                    "usage_count": 3,
                    "created_at": "2024-01-14T14:20:00Z",
                    "updated_at": "2024-01-14T14:20:00Z",
                    "context": {
                        "project_path": "/backend/api",
                        "files_involved": ["database.py"],
                    },
                },
            ]
        }
    )

    # Core fields
    id: Optional[str] = None
    type: MemoryType
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    summary: Optional[str] = Field(None, max_length=200)
    tags: List[str] = Field(default_factory=list)
    context: Optional[MemoryContext] = None

    # Scoring and metrics
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    effectiveness: Optional[float] = Field(None, ge=0.0, le=1.0)
    usage_count: int = Field(default=0, ge=0)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: Optional[datetime] = None

    # Concurrency control
    version: int = Field(
        default=1, ge=1, description="Version number for optimistic concurrency control"
    )
    updated_by: Optional[str] = Field(
        None, description="User ID who last updated this memory"
    )

    # Enriched search result fields (populated by search operations)
    relationships: Optional[Dict[str, List[str]]] = None
    match_info: Optional[Dict[str, Any]] = None
    context_summary: Optional[str] = None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Ensure tags are lowercase and non-empty."""
        return [tag.lower().strip() for tag in v if tag.strip()]

    @field_validator("title", "content")
    @classmethod
    def validate_text_fields(cls, v: str) -> str:
        """Ensure text fields are properly formatted."""
        return v.strip()


class RelationshipProperties(BaseModel):
    """Properties for relationships between memories."""

    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    context: Optional[str] = None
    evidence_count: int = Field(default=1, ge=0)
    success_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_validated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    validation_count: int = Field(default=0, ge=0)
    counter_evidence_count: int = Field(default=0, ge=0)

    # Confidence system fields
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    last_accessed: Optional[datetime] = Field(
        None, description="When this relationship was last accessed/used"
    )
    access_count: int = Field(default=0, ge=0)
    decay_factor: float = Field(default=0.95, ge=0.0, le=1.0)


class Relationship(BaseModel):
    """Relationship between two memories."""

    id: Optional[str] = None
    from_memory_id: str
    to_memory_id: str
    type: RelationshipType
    properties: RelationshipProperties = Field(default_factory=RelationshipProperties)
    description: Optional[str] = None
    bidirectional: bool = Field(default=False)

    @field_validator("from_memory_id", "to_memory_id")
    @classmethod
    def validate_memory_ids(cls, v: str) -> str:
        """Ensure memory IDs are non-empty."""
        if not v or not v.strip():
            raise ValueError("Memory ID cannot be empty")
        return v.strip()


class SearchQuery(BaseModel):
    """Search query parameters for memory retrieval."""

    query: Optional[str] = None
    terms: List[str] = Field(
        default_factory=list, description="Multiple search terms for multi-term queries"
    )
    memory_types: List[MemoryType] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    project_path: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    min_importance: Optional[float] = Field(None, ge=0.0, le=1.0)
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    min_effectiveness: Optional[float] = Field(None, ge=0.0, le=1.0)
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    include_relationships: bool = Field(default=True)
    search_tolerance: Optional[str] = Field(default="normal")
    match_mode: Optional[str] = Field(
        default="any", description="Match mode for terms: 'any' (OR) or 'all' (AND)"
    )
    relationship_filter: Optional[List[str]] = Field(
        default=None, description="Filter results by relationship types"
    )

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v):
        """Ensure tags are lowercase and non-empty."""
        if v is None:
            return []
        return [tag.lower().strip() for tag in v if tag and tag.strip()]

    @field_validator("search_tolerance")
    @classmethod
    def validate_search_tolerance(cls, v: Optional[str]) -> str:
        """Validate search_tolerance parameter."""
        if v is None:
            return "normal"
        valid_values = ["strict", "normal", "fuzzy"]
        if v not in valid_values:
            raise ValueError(
                f"search_tolerance must be one of {valid_values}, got '{v}'"
            )
        return v

    @field_validator("match_mode")
    @classmethod
    def validate_match_mode(cls, v: Optional[str]) -> str:
        """Validate match_mode parameter."""
        if v is None:
            return "any"
        valid_values = ["any", "all"]
        if v not in valid_values:
            raise ValueError(f"match_mode must be one of {valid_values}, got '{v}'")
        return v


class PaginatedResult(BaseModel):
    """Paginated result wrapper for memory search operations."""

    results: List[Memory]
    total_count: int = Field(ge=0)
    limit: int = Field(ge=1, le=1000)
    offset: int = Field(ge=0)
    has_more: bool
    next_offset: Optional[int] = None


# Custom Exception Hierarchy
class MemoryError(Exception):
    """Base exception for all memory-related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class ToolError(MemoryError):
    """Raised when there's a tool-specific error."""

    pass


class MemoryNotFoundError(MemoryError):
    """Raised when a requested memory does not exist."""

    def __init__(self, memory_id: str, details: Optional[Dict[str, Any]] = None):
        self.memory_id = memory_id
        message = f"Memory not found: {memory_id}"
        super().__init__(message, details)


class RelationshipError(MemoryError):
    """Raised when there's an issue with relationship operations."""

    pass


class ValidationError(MemoryError):
    """Raised when data validation fails."""

    def __init__(
        self,
        message: str,
        field: str = None,
        value: Any = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.field = field
        self.value = value
        super().__init__(message, details)


class DatabaseConnectionError(MemoryError):
    """Raised when there's a database connection issue."""

    pass


class SchemaError(MemoryError):
    """Raised when there's a schema-related issue."""

    pass


class NotFoundError(MemoryError):
    """Alias for MemoryNotFoundError for consistency with workplan naming."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.resource_type = resource_type
        self.resource_id = resource_id
        message = f"{resource_type} not found: {resource_id}"
        super().__init__(message, details)


class BackendError(MemoryError):
    """Raised when there's a backend operation issue."""

    pass


class ConfigurationError(MemoryError):
    """Raised when there's a configuration issue."""

    pass
