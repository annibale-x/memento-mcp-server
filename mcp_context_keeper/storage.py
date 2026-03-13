"""Storage backends for MCP Context Keeper."""

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from .models import Memory


class BaseStorage:
    """Base storage interface."""
    
    async def initialize(self) -> None:
        """Initialize the storage backend."""
        raise NotImplementedError
    
    async def store_memory(self, memory: Memory) -> None:
        """Store a memory."""
        raise NotImplementedError
    
    async def get_memory(self, memory_id: UUID) -> Optional[Memory]:
        """Get a memory by ID."""
        raise NotImplementedError
    
    async def search_memories(
        self, 
        query: str, 
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Memory]:
        """Search memories by content."""
        raise NotImplementedError


class SQLiteStorage(BaseStorage):
    """SQLite storage backend."""
    
    def __init__(self, db_path: str = "context_keeper.db"):
        self.db_path = Path(db_path)
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize SQLite database."""
        async with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # Create memories table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS memories (
                        id TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        type TEXT NOT NULL,
                        title TEXT,
                        tags TEXT,
                        metadata TEXT,
                        project_id TEXT,
                        user_id TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                conn.commit()
            finally:
                conn.close()
    
    async def store_memory(self, memory: Memory) -> None:
        """Store a memory in SQLite."""
        async with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO memories 
                    (id, content, type, title, tags, metadata, project_id, user_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(memory.id),
                    memory.content,
                    memory.type.value,
                    memory.title,
                    json.dumps(memory.tags),
                    json.dumps(memory.metadata),
                    memory.project_id,
                    memory.user_id,
                    memory.created_at.isoformat(),
                    memory.updated_at.isoformat(),
                ))
                conn.commit()
            finally:
                conn.close()
    
    async def get_memory(self, memory_id: UUID) -> Optional[Memory]:
        """Get a memory by ID from SQLite."""
        async with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM memories WHERE id = ?", (str(memory_id),))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return Memory(
                    id=UUID(row[0]),
                    content=row[1],
                    type=row[2],
                    title=row[3],
                    tags=json.loads(row[4]) if row[4] else [],
                    metadata=json.loads(row[5]) if row[5] else {},
                    project_id=row[6],
                    user_id=row[7],
                    created_at=datetime.fromisoformat(row[8]),
                    updated_at=datetime.fromisoformat(row[9]),
                )
            finally:
                conn.close()
    
    async def search_memories(
        self, 
        query: str, 
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Memory]:
        """Search memories in SQLite."""
        async with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                if memory_type:
                    cursor.execute("""
                        SELECT * FROM memories 
                        WHERE content LIKE ? AND type = ?
                        ORDER BY updated_at DESC
                        LIMIT ?
                    """, (f"%{query}%", memory_type, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM memories 
                        WHERE content LIKE ?
                        ORDER BY updated_at DESC
                        LIMIT ?
                    """, (f"%{query}%", limit))
                
                memories = []
                for row in cursor.fetchall():
                    memories.append(Memory(
                        id=UUID(row[0]),
                        content=row[1],
                        type=row[2],
                        title=row[3],
                        tags=json.loads(row[4]) if row[4] else [],
                        metadata=json.loads(row[5]) if row[5] else {},
                        project_id=row[6],
                        user_id=row[7],
                        created_at=datetime.fromisoformat(row[8]),
                        updated_at=datetime.fromisoformat(row[9]),
                    ))
                
                return memories
            finally:
                conn.close()


def get_storage(backend: str = "sqlite", **kwargs) -> BaseStorage:
    """Get storage backend instance."""
    if backend == "sqlite":
        return SQLiteStorage(**kwargs)
    elif backend == "networkx":
        # Simple NetworkX implementation for now
        class SimpleNetworkXStorage(BaseStorage):
            def __init__(self):
                self.memories = {}
                self._lock = asyncio.Lock()
            
            async def initialize(self) -> None:
                async with self._lock:
                    self.memories.clear()
            
            async def store_memory(self, memory: Memory) -> None:
                async with self._lock:
                    self.memories[memory.id] = memory
            
            async def get_memory(self, memory_id: UUID) -> Optional[Memory]:
                async with self._lock:
                    return self.memories.get(memory_id)
            
            async def search_memories(self, query: str, memory_type: Optional[str] = None, limit: int = 10) -> List[Memory]:
                async with self._lock:
                    results = []
                    query_lower = query.lower()
                    
                    for memory in self.memories.values():
                        if query_lower in memory.content.lower():
                            if memory_type and memory.type != memory_type:
                                continue
                            results.append(memory)
                    
                    results.sort(key=lambda m: m.updated_at, reverse=True)
                    return results[:limit]
        
        return SimpleNetworkXStorage()
    else:
        raise ValueError(f"Unknown storage backend: {backend}")
