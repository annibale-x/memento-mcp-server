# Database Schema Documentation

## Overview

This document describes the SQLite database schema used by the MCP Context Keeper application. The database stores persistent memories and their relationships with bi-temporal tracking capabilities.

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

Stores relationships between memory nodes with bi-temporal tracking.

| Column Name | Data Type | Constraints | Description |
|-------------|-----------|-------------|-------------|
| `id` | TEXT | PRIMARY KEY | Unique identifier for the relationship |
| `from_id` | TEXT | NOT NULL | Source memory node ID |
| `to_id` | TEXT | NOT NULL | Target memory node ID |
| `rel_type` | TEXT | NOT NULL | Type of relationship (e.g., SOLVES, CAUSES, ADDRESSES) |
| `properties` | TEXT | NOT NULL | JSON-serialized relationship properties |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Timestamp when relationship was created |
| `valid_from` | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | When the fact became true (validity time start) |
| `valid_until` | TIMESTAMP | NULL | When the fact stopped being true (NULL = still valid) |
| `recorded_at` | TIMESTAMP | NOT NULL DEFAULT CURRENT_TIMESTAMP | When we learned this fact (transaction time) |
| `invalidated_by` | TEXT | NULL | ID of relationship that superseded this one |

**Foreign Keys:**
- `FOREIGN KEY (from_id) REFERENCES nodes(id) ON DELETE CASCADE`
- `FOREIGN KEY (to_id) REFERENCES nodes(id) ON DELETE CASCADE`
- `FOREIGN KEY (invalidated_by) REFERENCES relationships(id) ON DELETE SET NULL`

**Indexes:**
- `idx_rel_from` ON `relationships`(`from_id`)
- `idx_rel_to` ON `relationships`(`to_id`)
- `idx_rel_type` ON `relationships`(`rel_type`)
- `idx_relationships_temporal` ON `relationships`(`valid_from`, `valid_until`)
- `idx_relationships_current` ON `relationships`(`valid_until`) WHERE `valid_until` IS NULL
- `idx_relationships_recorded` ON `relationships`(`recorded_at`)

### 3. `nodes_fts` Virtual Table (FTS5)

Full-text search virtual table for efficient text searching on memory content.

| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| `id` | TEXT | Memory node ID (linked to `nodes.id`) |
| `title` | TEXT | Memory title for full-text search |
| `content` | TEXT | Memory content for full-text search |
| `summary` | TEXT | Memory summary for full-text search |

**Note:** This is a SQLite FTS5 virtual table that enables fast full-text search capabilities. It's created conditionally based on FTS5 availability.

## Bi-Temporal Tracking

The database implements bi-temporal tracking for relationships, which means it tracks both:

### 1. Validity Time (`valid_from`, `valid_until`)
- **`valid_from`**: When the relationship/fact became true in the real world
- **`valid_until`**: When the relationship/fact stopped being true (NULL means currently valid)

### 2. Transaction Time (`recorded_at`)
- **`recorded_at`**: When the system learned about or recorded this fact

### Use Cases:
- **Historical Analysis**: Query relationships as they were valid at any point in time
- **Correction Tracking**: Track when facts were corrected or superseded
- **Temporal Queries**: Find currently valid relationships (`valid_until IS NULL`)
- **Change Detection**: Detect what changed since a specific time using `recorded_at`

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
  "counter_evidence_count": 0
}
```

## Common Query Patterns

### 1. Get Currently Valid Relationships
```sql
SELECT * FROM relationships 
WHERE valid_until IS NULL;
```

### 2. Get Relationships Valid at Specific Time
```sql
SELECT * FROM relationships 
WHERE valid_from <= ? AND (valid_until IS NULL OR valid_until > ?);
```

### 3. Find Unresolved Problems
```sql
SELECT n.* FROM nodes n
WHERE json_extract(n.properties, '$.type') IN ('problem', 'error')
  AND NOT EXISTS (
    SELECT 1 FROM relationships r
    WHERE r.to_id = n.id
      AND r.rel_type IN ('SOLVES', 'FIXES', 'ADDRESSES')
      AND (r.valid_until IS NULL OR r.valid_until > CURRENT_TIMESTAMP)
  );
```

### 4. Get Relationship History for a Memory
```sql
SELECT * FROM relationships 
WHERE from_id = ? OR to_id = ?
ORDER BY valid_from ASC;
```

### 5. What Changed Since a Specific Time
```sql
-- New relationships recorded since
SELECT * FROM relationships 
WHERE recorded_at >= ? 
ORDER BY recorded_at DESC;

-- Relationships invalidated since
SELECT * FROM relationships 
WHERE valid_until IS NOT NULL AND valid_until >= ? 
ORDER BY valid_until DESC;
```

## Database Initialization

The schema is initialized by the `SQLiteBackend.initialize_schema()` method, which:
1. Creates the `nodes` table
2. Creates the `relationships` table with bi-temporal fields
3. Creates all necessary indexes
4. Creates the FTS5 virtual table (if available)

## Notes

1. **FTS5 Availability**: The `nodes_fts` table is created conditionally. If FTS5 is not available in the SQLite build, a warning is logged but the application continues without full-text search.

2. **Bi-Temporal Implementation**: The bi-temporal tracking is implemented but may not be fully utilized in all queries. The infrastructure exists for temporal queries.

3. **JSON Storage**: All properties are stored as JSON strings, which allows flexible schema but requires JSON parsing in queries.

4. **Cascading Deletes**: Relationships are automatically deleted when referenced nodes are deleted due to `ON DELETE CASCADE` constraints.

5. **Performance**: Indexes are optimized for common query patterns including temporal queries and relationship lookups.