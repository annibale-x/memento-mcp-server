"""
Advanced MCP tool handlers for relationship management and graph analytics.

This module provides tool definitions and handlers for Phase 4's
advanced relationship functionality.
"""

import json
import logging
from typing import Any, Dict

from mcp.types import CallToolResult, TextContent, Tool

from .models import (
    RelationshipType,
)
from .relationships import RelationshipCategory, relationship_manager

logger = logging.getLogger(__name__)


# Tool definitions for advanced relationship features
ADVANCED_RELATIONSHIP_TOOLS = [
    Tool(
        name="find_path_between_mementos",
        description="Find the shortest path between two mementos through relationships",
        inputSchema={
            "type": "object",
            "properties": {
                "from_memory_id": {
                    "type": "string",
                    "description": "Starting memento ID",
                },
                "to_memory_id": {
                    "type": "string",
                    "description": "Target memento ID",
                },
                "max_depth": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "default": 5,
                    "description": "Maximum path length to search",
                },
                "relationship_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [t.value for t in RelationshipType],
                    },
                    "description": "Filter by specific relationship types",
                },
            },
            "required": ["from_memory_id", "to_memory_id"],
        },
    ),
    Tool(
        name="get_memento_clusters",
        description="Detect clusters of densely connected mementos",
        inputSchema={
            "type": "object",
            "properties": {
                "min_cluster_size": {
                    "type": "integer",
                    "minimum": 2,
                    "default": 3,
                    "description": "Minimum mementos per cluster",
                },
                "min_density": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.3,
                    "description": "Minimum cluster density (0.0-1.0)",
                },
            },
        },
    ),
    Tool(
        name="get_central_mementos",
        description="Find mementos that connect different clusters (knowledge bridges)",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="suggest_memento_relationships",
        description="Get intelligent suggestions for relationship types between two mementos",
        inputSchema={
            "type": "object",
            "properties": {
                "from_memory_id": {
                    "type": "string",
                    "description": "Source memento ID",
                },
                "to_memory_id": {
                    "type": "string",
                    "description": "Target memento ID",
                },
            },
            "required": ["from_memory_id", "to_memory_id"],
        },
    ),
    Tool(
        name="find_memento_patterns",
        description="""Find patterns in mementos and relationships

Analyzes the relationship graph to detect recurring structural patterns:
- Most frequent relationship types
- Common memory-type pairs connected by relationships

Note: patterns require multiple occurrences of the same relationship type.
With small datasets (< 10 relationships), lower the thresholds:
  min_pattern_size=1, min_support=0.0  → show all types, even singletons.
When no patterns meet the thresholds the tool still reports all available
relationship types with their counts so the result is always informative.""",
        inputSchema={
            "type": "object",
            "properties": {
                "min_pattern_size": {
                    "type": "integer",
                    "minimum": 2,
                    "default": 3,
                    "description": "Minimum pattern size to detect",
                },
                "min_support": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.5,
                    "description": "Minimum support threshold (0.0-1.0)",
                },
            },
        },
    ),
    Tool(
        name="analyze_memento_graph",
        description="Get comprehensive analytics and metrics for the memento graph",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_memento_network",
        description="Get the complete network structure of mementos and relationships",
        inputSchema={"type": "object", "properties": {}},
    ),
]


class AdvancedRelationshipHandlers:
    """Handlers for advanced relationship tools."""

    def __init__(self, memory_db):
        """Initialize handlers with database reference."""
        self.memory_db = memory_db

    async def handle_find_path_between_mementos(
        self, arguments: Dict[str, Any]
    ) -> CallToolResult:
        """Find shortest path between two mementos using BFS."""
        try:
            from_id = arguments["from_memory_id"]
            to_id = arguments["to_memory_id"]
            max_depth = arguments.get("max_depth", 5)
            rel_types = arguments.get("relationship_types")

            relationship_types = None
            if rel_types:
                relationship_types = [RelationshipType(t) for t in rel_types]

            # BFS: predecessor map stores {node_id: (parent_id, relationship_type)}
            visited = {from_id}
            predecessor: dict = {from_id: None}
            queue = [from_id]
            found = False

            for _depth in range(max_depth):
                if not queue:
                    break

                next_queue = []

                for current_id in queue:
                    neighbors = await self.memory_db.get_related_memories(
                        current_id,
                        relationship_types=relationship_types,
                        max_depth=1,
                    )

                    for neighbor_memory, relationship in neighbors:
                        nid = neighbor_memory.id

                        if nid in visited:
                            continue

                        visited.add(nid)
                        rel_label = relationship.type.value if relationship and hasattr(relationship, "type") else "RELATED_TO"
                        predecessor[nid] = (current_id, rel_label, neighbor_memory.title)

                        if nid == to_id:
                            found = True
                            break

                        next_queue.append(nid)

                    if found:
                        break

                if found:
                    break

                queue = next_queue

            if not found:
                path_info = {
                    "found": False,
                    "from_memory_id": from_id,
                    "to_memory_id": to_id,
                    "searched_depth": max_depth,
                    "visited_count": len(visited),
                }
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(path_info, indent=2))]
                )

            # Reconstruct path by walking back through predecessor map
            path_nodes = []
            current = to_id

            while current is not None:
                entry = predecessor[current]

                if entry is None:
                    path_nodes.append({"id": current, "via_relationship": None})
                else:
                    parent_id, rel_label, node_title = entry
                    path_nodes.append(
                        {"id": current, "title": node_title, "via_relationship": rel_label}
                    )
                    current = parent_id
                    continue

                break

            path_nodes.reverse()

            # Fetch start node title
            start_memory = await self.memory_db.get_memory_by_id(from_id)
            if path_nodes and path_nodes[0].get("id") == from_id:
                path_nodes[0]["title"] = start_memory.title if start_memory else from_id

            path_info = {
                "found": True,
                "from_memory_id": from_id,
                "to_memory_id": to_id,
                "hops": len(path_nodes) - 1,
                "path": path_nodes,
            }

            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(path_info, indent=2))]
            )

        except Exception as e:
            logger.error(f"Error finding memory path: {e}")
            return CallToolResult(
                content=[
                    TextContent(type="text", text=f"Error finding path: {str(e)}")
                ],
                isError=True,
            )

    async def handle_get_memento_clusters(
        self, arguments: Dict[str, Any]
    ) -> CallToolResult:
        """Detect clusters of densely connected mementos.

        Uses degree-based community detection: memories sharing many common
        neighbours are grouped together.  Returns clusters that meet the
        min_cluster_size and min_density thresholds.
        """
        try:
            min_cluster_size = arguments.get("min_cluster_size", 3)
            min_density = arguments.get("min_density", 0.3)

            stats = await self.memory_db.get_memory_statistics()
            total_memories = stats.get("total_memories", {}).get("count", 0)
            total_relationships = stats.get("total_relationships", {}).get("count", 0)

            # Build adjacency map from the relationships table
            rel_rows = await self.memory_db._execute_sql(
                "SELECT from_id, to_id FROM relationships"
            )
            adj: dict[str, set[str]] = {}

            for row in rel_rows:
                adj.setdefault(row["from_id"], set()).add(row["to_id"])
                adj.setdefault(row["to_id"], set()).add(row["from_id"])

            # Simple greedy cluster detection: group nodes by shared neighbours
            visited: set[str] = set()
            clusters: list[dict] = []

            for node in list(adj.keys()):
                if node in visited:
                    continue

                # BFS / greedy expansion: include neighbours with ≥1 common link
                group = {node}
                frontier = list(adj.get(node, []))

                for candidate in frontier:
                    if candidate in visited or candidate in group:
                        continue
                    shared = adj.get(node, set()) & adj.get(candidate, set())
                    if shared or candidate in adj.get(node, set()):
                        group.add(candidate)

                if len(group) < min_cluster_size:
                    continue

                # Density = actual internal edges / max possible edges
                internal = sum(
                    1
                    for n in group
                    for nbr in adj.get(n, set())
                    if nbr in group
                ) // 2  # each edge counted twice
                max_internal = len(group) * (len(group) - 1) // 2
                density = internal / max_internal if max_internal > 0 else 0.0

                if density < min_density:
                    continue

                visited.update(group)
                clusters.append(
                    {
                        "size": len(group),
                        "density": round(density, 4),
                        "members": list(group),
                    }
                )

            result = {
                "analysis_type": "cluster_detection",
                "total_memories": total_memories,
                "total_relationships": total_relationships,
                "min_cluster_size": min_cluster_size,
                "min_density": min_density,
                "clusters_found": len(clusters),
                "clusters": clusters,
            }

            return CallToolResult(
                content=[
                    TextContent(type="text", text=json.dumps(result, indent=2))
                ]
            )

        except Exception as e:
            logger.error(f"Error analyzing clusters: {e}")
            return CallToolResult(
                content=[
                    TextContent(type="text", text=f"Error analyzing clusters: {str(e)}")
                ],
                isError=True,
            )

    async def handle_get_central_mementos(
        self, arguments: Dict[str, Any]
    ) -> CallToolResult:
        """Find mementos that act as bridges between different knowledge clusters.

        A memory is considered central if it has a high degree (many connections)
        relative to the graph average, making it a hub connecting otherwise
        separate parts of the knowledge network.
        """
        try:
            stats = await self.memory_db.get_memory_statistics()
            total_memories = stats.get("total_memories", {}).get("count", 0)
            total_relationships = stats.get("total_relationships", {}).get("count", 0)

            if total_memories == 0:
                result = {
                    "analysis_type": "bridge_detection",
                    "total_memories": 0,
                    "central_mementos": [],
                }
                return CallToolResult(
                    content=[
                        TextContent(type="text", text=json.dumps(result, indent=2))
                    ]
                )

            # Degree of each node
            degree_rows = await self.memory_db._execute_sql(
                """
                SELECT node_id, COUNT(*) as degree FROM (
                    SELECT from_id AS node_id FROM relationships
                    UNION ALL
                    SELECT to_id AS node_id FROM relationships
                )
                GROUP BY node_id
                ORDER BY degree DESC
                """
            )

            avg_degree = (
                (2 * total_relationships / total_memories) if total_memories else 0.0
            )

            # Central = degree > average
            central = []

            for row in degree_rows:
                if row["degree"] <= avg_degree and len(central) > 0:
                    break  # sorted DESC, no point continuing

                mem = await self.memory_db.get_memory_by_id(row["node_id"])

                if mem:
                    central.append(
                        {
                            "id": mem.id,
                            "title": mem.title,
                            "type": mem.type.value,
                            "degree": row["degree"],
                            "centrality_score": round(
                                row["degree"] / max(avg_degree, 1), 3
                            ),
                        }
                    )

            result = {
                "analysis_type": "bridge_detection",
                "total_memories": total_memories,
                "total_relationships": total_relationships,
                "avg_degree": round(avg_degree, 2),
                "central_mementos": central,
            }

            return CallToolResult(
                content=[
                    TextContent(type="text", text=json.dumps(result, indent=2))
                ]
            )

        except Exception as e:
            logger.error(f"Error finding central mementos: {e}")
            return CallToolResult(
                content=[
                    TextContent(type="text", text=f"Error finding bridges: {str(e)}")
                ],
                isError=True,
            )

    async def handle_suggest_memento_relationships(
        self, arguments: Dict[str, Any]
    ) -> CallToolResult:
        """Suggest relationship types between mementos."""
        try:
            from_id = arguments["from_memory_id"]
            to_id = arguments["to_memory_id"]

            # Get the memories
            from_memory = await self.memory_db.get_memory(
                from_id, include_relationships=False
            )
            to_memory = await self.memory_db.get_memory(
                to_id, include_relationships=False
            )

            if not from_memory or not to_memory:
                return CallToolResult(
                    content=[
                        TextContent(type="text", text="One or both memories not found")
                    ],
                    isError=True,
                )

            # Get suggestions
            suggestions = relationship_manager.suggest_relationship_type(
                from_memory, to_memory
            )

            suggestion_list = [
                {
                    "type": rel_type.value,
                    "confidence": confidence,
                    "category": relationship_manager.get_relationship_category(
                        rel_type
                    ).value,
                    "description": relationship_manager.get_relationship_metadata(
                        rel_type
                    ).description,
                }
                for rel_type, confidence in suggestions
            ]

            result = {
                "from_memory": {
                    "id": from_memory.id,
                    "type": from_memory.type.value,
                    "title": from_memory.title,
                },
                "to_memory": {
                    "id": to_memory.id,
                    "type": to_memory.type.value,
                    "title": to_memory.title,
                },
                "suggestions": suggestion_list,
            }

            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, indent=2))]
            )

        except Exception as e:
            logger.error(f"Error suggesting relationship: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {str(e)}")],
                isError=True,
            )

    async def handle_find_memento_patterns(
        self, arguments: Dict[str, Any]
    ) -> CallToolResult:
        """Find recurring patterns in mementos and relationships.

        Analyzes the relationship graph to detect common structural patterns:
        - Most frequent relationship types
        - Common memory type pairs connected by relationships
        - Hub memories (high degree nodes)
        """
        try:
            min_pattern_size = arguments.get("min_pattern_size", 3)
            min_support = arguments.get("min_support", 0.5)

            stats = await self.memory_db.get_memory_statistics()
            total_memories = stats.get("total_memories", {}).get("count", 0)
            total_relationships = stats.get("total_relationships", {}).get("count", 0)

            if total_memories == 0:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "patterns": [],
                                    "total_memories": 0,
                                    "total_relationships": 0,
                                    "note": "No memories found to analyze.",
                                },
                                indent=2,
                            ),
                        )
                    ]
                )

            # Count relationship type frequencies
            rel_type_query = """
                SELECT rel_type, COUNT(*) as count
                FROM relationships
                GROUP BY rel_type
                ORDER BY count DESC
            """
            rel_counts = await self.memory_db._execute_sql(rel_type_query)

            # Count memory type pair patterns
            pair_query = """
                SELECT
                    json_extract(n1.properties, '$.type') as from_type,
                    r.rel_type,
                    json_extract(n2.properties, '$.type') as to_type,
                    COUNT(*) as count
                FROM relationships r
                JOIN nodes n1 ON r.from_id = n1.id
                JOIN nodes n2 ON r.to_id = n2.id
                WHERE n1.label = 'Memory' AND n2.label = 'Memory'
                GROUP BY from_type, r.rel_type, to_type
                ORDER BY count DESC
                LIMIT 20
            """
            pair_counts = await self.memory_db._execute_sql(pair_query)

            # Build relationship type frequency list
            rel_patterns = []
            for row in rel_counts:
                freq = row["count"] / max(total_relationships, 1)

                if row["count"] >= min_pattern_size and freq >= min_support:
                    rel_patterns.append(
                        {
                            "relationship_type": row["rel_type"],
                            "count": row["count"],
                            "frequency": round(freq, 3),
                        }
                    )

            # Build memory type pair patterns
            pair_patterns = []
            for row in pair_counts:
                if row["count"] >= min_pattern_size:
                    pair_patterns.append(
                        {
                            "from_type": row["from_type"],
                            "relationship": row["rel_type"],
                            "to_type": row["to_type"],
                            "count": row["count"],
                        }
                    )

            # When nothing meets the thresholds, expose all available types
            # so the caller always gets useful information.
            all_rel_types = [
                {
                    "relationship_type": row["rel_type"],
                    "count": row["count"],
                    "frequency": round(row["count"] / max(total_relationships, 1), 3),
                }
                for row in rel_counts
            ]
            below_threshold = not rel_patterns and bool(all_rel_types)

            result = {
                "total_memories": total_memories,
                "total_relationships": total_relationships,
                "min_pattern_size": min_pattern_size,
                "min_support": min_support,
                "relationship_type_patterns": rel_patterns,
                "memory_type_pair_patterns": pair_patterns,
                "analysis_note": (
                    "Patterns show recurring relationship types and memory type "
                    "combinations that appear at least min_pattern_size times."
                ),
            }

            if below_threshold:
                result["available_relationship_types"] = all_rel_types
                result["threshold_note"] = (
                    f"No patterns meet min_pattern_size={min_pattern_size} / "
                    f"min_support={min_support}. "
                    f"Use min_pattern_size=1, min_support=0.0 to see all types."
                )

            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, indent=2))]
            )

        except Exception as e:
            logger.error(f"Error finding memento patterns: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {str(e)}")],
                isError=True,
            )

    async def handle_analyze_memento_graph(
        self, arguments: Dict[str, Any]
    ) -> CallToolResult:
        """Get comprehensive analytics and metrics for the memento graph."""
        try:
            stats = await self.memory_db.get_memory_statistics()
            total_memories = stats.get("total_memories", {}).get("count", 0)
            total_relationships = stats.get("total_relationships", {}).get("count", 0)
            memories_by_type = stats.get("memories_by_type", {})
            avg_importance = stats.get("avg_importance", {}).get("avg_importance", 0.0)
            avg_confidence = stats.get("avg_confidence", {}).get("avg_confidence", 0.0)

            # Compute graph density: actual edges / max possible edges
            max_edges = total_memories * (total_memories - 1) if total_memories > 1 else 0
            density = round(total_relationships / max_edges, 4) if max_edges > 0 else 0.0

            # Relationship type distribution
            rel_dist_query = """
                SELECT rel_type, COUNT(*) as count
                FROM relationships
                GROUP BY rel_type
                ORDER BY count DESC
            """
            rel_dist = await self.memory_db._execute_sql(rel_dist_query)
            relationship_distribution = {
                row["rel_type"]: row["count"] for row in rel_dist
            }

            # Top connected memories (degree centrality)
            degree_query = """
                SELECT node_id, COUNT(*) as degree FROM (
                    SELECT from_id as node_id FROM relationships
                    UNION ALL
                    SELECT to_id as node_id FROM relationships
                )
                GROUP BY node_id
                ORDER BY degree DESC
                LIMIT 5
            """
            degree_rows = await self.memory_db._execute_sql(degree_query)
            top_connected = []

            for row in degree_rows:
                mem = await self.memory_db.get_memory_by_id(row["node_id"])

                if mem:
                    top_connected.append(
                        {
                            "id": mem.id,
                            "title": mem.title,
                            "degree": row["degree"],
                        }
                    )

            # Category coverage
            category_coverage = {}

            for cat in RelationshipCategory:
                types_in_cat = relationship_manager.get_types_by_category(cat)
                used = sum(
                    relationship_distribution.get(t.value, 0) for t in types_in_cat
                )
                category_coverage[cat.value] = {
                    "available_types": len(types_in_cat),
                    "used_count": used,
                }

            result = {
                "summary": {
                    "total_memories": total_memories,
                    "total_relationships": total_relationships,
                    "graph_density": density,
                    "avg_importance": round(avg_importance, 3),
                    "avg_confidence": round(avg_confidence, 3),
                },
                "memories_by_type": memories_by_type,
                "relationship_distribution": relationship_distribution,
                "category_coverage": category_coverage,
                "top_connected_memories": top_connected,
                "database_file_size_bytes": stats.get("database_file_size"),
                "timestamp": stats.get("timestamp"),
            }

            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, indent=2))]
            )

        except Exception as e:
            logger.error(f"Error analyzing memento graph: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {str(e)}")],
                isError=True,
            )

    async def handle_get_memento_network(
        self, arguments: Dict[str, Any]
    ) -> CallToolResult:
        """Get the complete memento network: nodes, edges and system metadata."""
        try:
            # Database statistics (same as get_memento_statistics)
            stats = await self.memory_db.get_memory_statistics()

            # Fetch all nodes (memories) — capped at 200
            node_rows = await self.memory_db._execute_sql(
                """
                SELECT id,
                       json_extract(properties, '$.title')      AS title,
                       json_extract(properties, '$.type')       AS type,
                       json_extract(properties, '$.importance') AS importance
                FROM nodes
                WHERE label = 'Memory'
                LIMIT 200
                """
            )
            nodes = [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "type": r["type"],
                    "importance": r["importance"],
                }
                for r in node_rows
            ]

            # Fetch all edges (relationships) — capped at 200
            edge_rows = await self.memory_db._execute_sql(
                """
                SELECT id, from_id, to_id, rel_type, confidence
                FROM relationships
                LIMIT 200
                """
            )
            edges = [
                {
                    "id": r["id"],
                    "from": r["from_id"],
                    "to": r["to_id"],
                    "type": r["rel_type"],
                    "confidence": r["confidence"],
                }
                for r in edge_rows
            ]

            result = {
                "nodes": nodes,
                "edges": edges,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "truncated": len(nodes) == 200 or len(edges) == 200,
                "database_statistics": stats,
                "relationship_system": {
                    "total_relationship_types": 35,
                    "categories": [
                        {
                            "name": cat.value,
                            "types_count": len(
                                relationship_manager.get_types_by_category(cat)
                            ),
                        }
                        for cat in RelationshipCategory
                    ],
                },
            }

            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(result, indent=2))]
            )

        except Exception as e:
            logger.error(f"Error getting memento network: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {str(e)}")],
                isError=True,
            )
