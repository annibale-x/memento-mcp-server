"""Custom exceptions for MCP Context Keeper."""


class ContextKeeperError(Exception):
    """Base exception for all Context Keeper errors."""
    pass


class MemoryNotFoundError(ContextKeeperError):
    """Raised when a memory is not found."""
    pass


class RelationshipNotFoundError(ContextKeeperError):
    """Raised when a relationship is not found."""
    pass


class StorageError(ContextKeeperError):
    """Raised when there is a storage-related error."""
    pass


class ValidationError(ContextKeeperError):
    """Raised when input validation fails."""
    pass


class DuplicateMemoryError(ContextKeeperError):
    """Raised when trying to create a duplicate memory."""
    pass


class CircularRelationshipError(ContextKeeperError):
    """Raised when a relationship would create a cycle."""
    pass
