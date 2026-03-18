# Database Schema Documentation

## Overview

This document describes the SQLite database schema used by the MCP Memento application. The database stores mementos and their relationships with a confidence scoring system.

## Tables

### 1. `nodes` Table

Stores individual memory nodes with their properties.

| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | Unique identifier for the memory node |
| `label` | TEXT | NOT NULL | Label/type of the memory node |
| `properties` | TEXT | NOT NULL | JSON-serialized properties of the memory |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Timestamp when the node was created |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Timestamp when the node was last updated |

**Indexes:**
- `idx_nodes_label` ON `nodes`(`label`)
- `idx_nodes_created` ON `nodes`(`created_at`)

### 2. `relationships` Table

Stores relationships between memory nodes with a confidence scoring system.

| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | Unique identifier for the relationship |
| `from_id` | TEXT | NOT NULL | Source memory node ID |
| `to_id` | TEXT | NOT NULL | Target memory node ID |
| `rel_type` | TEXT | NOT NULL | Type of relationship (e.g., SOLVES, CAUSES, ADDRESSES) |
| `properties` | TEXT | NOT NULL | JSON-serialized relationship properties |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Timestamp when relationship was created |
| `confidence` | FLOAT | DEFAULT 0.8 | Confidence score for this relationship (0.0-1.0) |
| `last_accessed` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last time this relationship was accessed |
| `access_count` | INTEGER | DEFAULT 0 | Number of times this relationship has been accessed |
| `decay_factor` | FLOAT | DEFAULT 0.95 | Monthly decay factor for confidence (e.g., 0.95 = 5% monthly decay) |

**Foreign Keys:**
- `FOREIGN KEY (from_id) REFERENCES nodes(id) ON DELETE CASCADE`
- `FOREIGN KEY (to_id) REFERENCES nodes(id) ON DELETE CASCADE`

**Indexes:**
- `idx_rel_from` ON `relationships`(`from_id`)
- `idx_rel_to` ON `relationships`(`to_id`)
- `idx_rel_type` ON `relationships`(`rel_type`)
- `idx_relationships_confidence` ON `relationships`(`confidence`)
- `idx_relationships_last_accessed` ON `relationships`(`last_accessed`)

### 3. `nodes_fts` Virtual Table (FTS5)

Full-text search virtual table for efficient text searching on memory content.

| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| `id` | TEXT | Memory node ID (linked to `nodes.id`) |
| `title` | TEXT | Memory title for full-text search |
| `content` | TEXT | Memory content for full-text search |
| `summary` | TEXT | Memory summary for full-text search |

**Note:** This is a SQLite FTS5 virtual table that enables fast full-text search capabilities. It's created conditionally based on FTS5 availability.

### 4. Additional Indexes

**Memory Version Index:**
- `idx_memory_version` ON `nodes`(`json_extract(properties, '$.version')`) WHERE `label = 'Memory'`

This index supports optimistic locking for memory updates.

## JSON Properties Structure

### Node Properties (`nodes.properties` JSON field):
```json
{
  "type": "solution|problem|error|fix|pattern|technology|...",
  "title": "Descriptive title",
  "content": "Detailed content",
  "summary": "Brief summary",
  "tags": ["tag1", "tag2", ...],
  "importance": 0.0-1.0,
  "context": {
    "project": "project_path",
    "language": "python|javascript|...",
    "framework": "framework_name",
    "timestamp": "ISO timestamp"
  }
}
```

### Relationship Properties (`relationships.properties` JSON field):
```json
{
  "scope": "partial|full|conditional",
  "conditions": ["condition1", "condition2", ...],
  "evidence": ["integration_tests", "unit_tests", ...],
  "components": ["component1", "component2", ...],
  "strength": 0.0-1.0,
  "confidence": 0.0-1.0,
  "context": "Relationship description",
  "success_rate": 0.0-1.0,
  "created_at": "ISO timestamp",
  "last_validated": "ISO timestamp",
  "validation_count": 0,
  "counter_evidence_count": 0,
  "last_accessed": "ISO timestamp",
  "access_count": 0,
  "decay_factor": 0.95
}
```

## Common Query Patterns

### 1. Low Confidence Relationships
```sql
-- Find relationships with low confidence
SELECT * FROM relationships 
WHERE confidence < 0.3 
ORDER BY confidence ASC;

-- Find relationships not accessed recently
SELECT * FROM relationships 
WHERE last_accessed < datetime('now', '-30 days') 
ORDER BY last_accessed ASC;
```

### 2. Confidence System Statistics
```sql
-- Get confidence distribution
SELECT 
  CASE 
    WHEN confidence >= 0.9 THEN 'High (0.9-1.0)'
    WHEN confidence >= 0.7 THEN 'Good (0.7-0.89)'
    WHEN confidence >= 0.5 THEN 'Moderate (0.5-0.69)'
    WHEN confidence >= 0.3 THEN 'Low (0.3-0.49)'
    ELSE 'Very Low (0.0-0.29)'
  END as confidence_level,
  COUNT(*) as count,
  AVG(access_count) as avg_access_count,
  MIN(last_accessed) as oldest_access,
  MAX(last_accessed) as newest_access
FROM relationships 
GROUP BY confidence_level 
ORDER BY confidence_level DESC;
```

## Database Initialization

The schema is initialized by the `SQLiteBackend.initialize_schema()` method, which:
1. Creates the `nodes` table
2. Creates the `relationships` table with confidence system fields
3. Creates all necessary indexes including confidence and access tracking indexes
4. Creates the FTS5 virtual table (if available)
5. Creates the memory version index for optimistic locking

## Notes

1. **FTS5 Availability**: The `nodes_fts` table is created conditionally. If FTS5 is not available in the SQLite build, a warning is logged but the application continues without full-text search.

2. **Confidence System**: The database includes a comprehensive confidence tracking system with:
   - Automatic decay (5% monthly by default)
   - Access tracking (`last_accessed`, `access_count`)
   - Configurable decay factors (`decay_factor`)
   - Indexes for efficient confidence-based queries

3. **JSON Storage**: All properties are stored as JSON strings, which allows flexible schema but requires JSON parsing in queries.

4. **Cascading Deletes**: Relationships are automatically deleted when referenced nodes are deleted due to `ON DELETE CASCADE` constraints.

5. **Performance**: Indexes are optimized for common query patterns including relationship lookups and confidence-based filtering.

6. **Optimistic Locking**: The `idx_memory_version` index supports optimistic locking for concurrent memory updates.