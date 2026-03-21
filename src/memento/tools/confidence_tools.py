"""
Confidence system tool handlers for the MCP server.

This module contains handlers for confidence system operations:
- adjust_confidence: Manually adjust confidence of a relationship
- get_low_confidence_memories: Find memories with low confidence
- apply_confidence_decay: Apply decay to relationships based on last access
- boost_confidence: Boost confidence when a memory is used successfully
"""

import logging
from typing import Any, Dict, List

from mcp.types import CallToolResult, TextContent

from ..database.interface import SQLiteMemoryDatabase
from ..models import Memory, Relationship
from .error_handling import handle_tool_errors

logger = logging.getLogger(__name__)


@handle_tool_errors("adjust confidence")
async def handle_adjust_memento_confidence(
    memory_db: SQLiteMemoryDatabase, arguments: Dict[str, Any]
) -> CallToolResult:
    """Handle adjust_confidence tool call.

    Args:
        memory_db: Database instance for memory operations
        arguments: Tool arguments from MCP call containing:
            - relationship_id: ID of the relationship to adjust
            - new_confidence: New confidence value (0.0-1.0)
            - reason: Reason for the adjustment

    Returns:
        CallToolResult with confirmation or error message
    """
    relationship_id = arguments["relationship_id"]
    new_confidence = float(arguments["new_confidence"])
    reason = arguments.get("reason", "Manual adjustment")

    await memory_db.adjust_confidence(relationship_id, new_confidence, reason)

    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=f"Adjusted confidence for relationship {relationship_id} to {new_confidence:.2f}",
            )
        ]
    )


@handle_tool_errors("get low confidence memories")
async def handle_get_low_confidence_mementos(
    memory_db: SQLiteMemoryDatabase, arguments: Dict[str, Any]
) -> CallToolResult:
    """Handle get_low_confidence_memories tool call.

    Args:
        memory_db: Database instance for memory operations
        arguments: Tool arguments from MCP call containing:
            - threshold: Confidence threshold (default: 0.3)
            - limit: Maximum number of results to return (default: 20)

    Returns:
        CallToolResult with list of low confidence memories or error message
    """
    threshold = float(arguments.get("threshold", 0.3))
    limit = int(arguments.get("limit", 20))

    # Get low confidence relationships
    relationships = await memory_db.get_low_confidence_relationships(
        threshold=threshold, limit=limit
    )

    if not relationships:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"No relationships found with confidence below {threshold}",
                )
            ]
        )

    # Get unique memory IDs from relationships
    memory_ids = set()

    for rel in relationships:
        memory_ids.add(rel.from_memory_id)
        memory_ids.add(rel.to_memory_id)

    # Fetch memory details
    memories: List[Memory] = []

    for memory_id in list(memory_ids)[:limit]:
        try:
            memory = await memory_db.get_memory_by_id(memory_id)

            if memory:
                memories.append(memory)
        except Exception as e:
            logger.warning(f"Failed to fetch memory {memory_id}: {e}")

    if not memories:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Found {len(relationships)} low confidence relationships but could not fetch memory details",
                )
            ]
        )

    # Format results
    result_text = f"**Low Confidence Memories (threshold: confidence < {threshold})**\n\n"
    result_text += (
        f"Found {len(memories)} memories with low confidence relationships:\n\n"
    )

    for i, memory in enumerate(memories, 1):
        # Find relationships for this memory
        mem_relationships = [
            rel
            for rel in relationships
            if rel.from_memory_id == memory.id or rel.to_memory_id == memory.id
        ]

        result_text += f"**{i}. {memory.title}** (ID: {memory.id})\n"
        result_text += f"Type: {memory.type.value} | Importance: {memory.importance:.2f}\n"

        if memory.summary:
            result_text += f"Summary: {memory.summary[:150]}...\n"

        if mem_relationships:
            result_text += "Low confidence relationships:\n"

            for rel in mem_relationships[:3]:
                other_id = (
                    rel.to_memory_id
                    if rel.from_memory_id == memory.id
                    else rel.from_memory_id
                )
                # "Last accessed" refers to the relationship, not the memory
                last_acc = rel.properties.last_accessed
                last_acc_str = (
                    last_acc.strftime("%Y-%m-%d")
                    if last_acc
                    else "never accessed via search"
                )
                result_text += (
                    f"  - {rel.type.value} → {other_id[:8]}... "
                    f"(relationship confidence: {rel.properties.confidence:.2f}, "
                    f"last accessed: {last_acc_str})\n"
                )

        result_text += "\n"

    result_text += "**💡 Suggestions:**\n"
    result_text += "- Review these memories for accuracy\n"
    result_text += "- Use `adjust_memento_confidence` to update if still valid\n"
    result_text += "- Consider deleting if obsolete\n"
    result_text += "- Use `boost_memento_confidence` if recently validated\n"
    result_text += "\n"
    result_text += "ℹ️ **Note:** 'relationship confidence' is the decay-tracked score on each "
    result_text += "edge — it decreases automatically when the relationship is not accessed. "
    result_text += "'last accessed' tracks when the relationship was last retrieved by a search, "
    result_text += "not when the memory was created.\n"

    return CallToolResult(content=[TextContent(type="text", text=result_text)])


@handle_tool_errors("apply confidence decay")
async def handle_apply_memento_confidence_decay(
    memory_db: SQLiteMemoryDatabase, arguments: Dict[str, Any]
) -> CallToolResult:
    """Handle apply_confidence_decay tool call.

    Args:
        memory_db: Database instance for memory operations
        arguments: Tool arguments from MCP call containing:
            - memory_id: Optional memory ID to apply decay only to its relationships

    Returns:
        CallToolResult with decay results or error message
    """
    memory_id = arguments.get("memory_id")

    # Count total relationships before decay to compute skipped
    if memory_id:
        count_rows = await memory_db._execute_sql(
            "SELECT COUNT(*) as total FROM relationships WHERE from_id = ? OR to_id = ?",
            (memory_id, memory_id),
        )
    else:
        count_rows = await memory_db._execute_sql(
            "SELECT COUNT(*) as total FROM relationships"
        )

    total_rels = count_rows[0]["total"] if count_rows else 0

    updated_count = await memory_db.apply_confidence_decay(memory_id)

    skipped = total_rels - updated_count

    # Build breakdown text
    scope = f"memory {memory_id}" if memory_id else "all memories (system-wide)"
    lines = [
        f"**Confidence decay applied** ({scope})\n",
        f"| | Count |",
        f"|---|---|",
        f"| Relationships updated | {updated_count} |",
        f"| Skipped (no last_accessed or at min confidence 0.1) | {skipped} |",
        f"| Total relationships in scope | {total_rels} |",
    ]

    if updated_count == 0 and total_rels > 0:
        lines.append(
            "\n⚠️ All relationships were skipped — they may already be at minimum "
            "confidence (0.1) or have no `last_accessed` timestamp."
        )

    return CallToolResult(
        content=[TextContent(type="text", text="\n".join(lines))]
    )


@handle_tool_errors("boost confidence")
async def handle_boost_memento_confidence(
    memory_db: SQLiteMemoryDatabase, arguments: Dict[str, Any]
) -> CallToolResult:
    """Handle boost_confidence tool call.

    Boost confidence when a memory or relationship is used successfully.

    Args:
        memory_db: Database instance for memory operations
        arguments: Tool arguments from MCP call containing:
            - memory_id: ID of memory to boost (optional, requires relationship_id if not provided)
            - relationship_id: ID of relationship to boost (optional, requires memory_id if not provided)
            - boost_amount: Amount to boost confidence (default: 0.1)
            - reason: Reason for the boost

    Returns:
        CallToolResult with confirmation or error message
    """
    memory_id = arguments.get("memory_id")
    relationship_id = arguments.get("relationship_id")
    boost_amount = float(arguments.get("boost_amount", 0.1))
    reason = arguments.get("reason", "Successful usage")

    if not memory_id and not relationship_id:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="Either memory_id or relationship_id must be provided",
                )
            ],
            isError=True,
        )

    if boost_amount < 0.0 or boost_amount > 0.5:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="Boost amount must be between 0.0 and 0.5",
                )
            ],
            isError=True,
        )

    if memory_id:
        # Boost confidence for all relationships of this memory
        try:
            # Get memory to check current confidence
            memory = await memory_db.get_memory_by_id(memory_id)
            if not memory:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Memory not found: {memory_id}",
                        )
                    ],
                    isError=True,
                )

            # Calculate new confidence
            new_confidence = min(1.0, memory.confidence + boost_amount)

            # Update memory confidence
            # Note: This requires adding update_memory_confidence method to database
            # For now, we'll update through relationships
            # Get relationships for this memory
            relationships = await memory_db.get_relationships_for_memory(memory_id)
            for rel in relationships:
                new_rel_confidence = min(1.0, rel.properties.confidence + boost_amount)
                await memory_db.adjust_confidence(
                    rel.id,
                    new_rel_confidence,
                    f"Boosted via memory {memory_id}: {reason}",
                )

            if not relationships:
                message = (
                    f"Memory '{memory_id}' has no relationships — confidence boost requires "
                    f"at least one relationship. "
                    f"Create one first with `create_memento_relationship`."
                )
            else:
                message = f"Boosted confidence for {len(relationships)} relationships of memory {memory_id} by {boost_amount:.2f}"

        except Exception as e:
            logger.error(f"Failed to boost confidence for memory {memory_id}: {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Failed to boost confidence: {str(e)}",
                    )
                ],
                isError=True,
            )

    else:  # relationship_id is provided
        try:
            # Get current relationship confidence
            relationships = await memory_db.get_relationships_for_memory(
                relationship_id
            )
            if not relationships:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Relationship not found: {relationship_id}",
                        )
                    ],
                    isError=True,
                )

            # Find the specific relationship
            rel = next((r for r in relationships if r.id == relationship_id), None)
            if not rel:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Relationship not found: {relationship_id}",
                        )
                    ],
                    isError=True,
                )

            new_confidence = min(1.0, rel.properties.confidence + boost_amount)
            await memory_db.adjust_confidence(relationship_id, new_confidence, reason)

            message = f"Boosted confidence for relationship {relationship_id} from {rel.properties.confidence:.2f} to {new_confidence:.2f}"

        except Exception as e:
            logger.error(
                f"Failed to boost confidence for relationship {relationship_id}: {e}"
            )
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Failed to boost confidence: {str(e)}",
                    )
                ],
                isError=True,
            )

    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=message,
            )
        ]
    )


@handle_tool_errors("set decay factor")
async def handle_set_memento_decay_factor(
    memory_db: SQLiteMemoryDatabase, arguments: Dict[str, Any]
) -> CallToolResult:
    """Handle set_decay_factor tool call.

    Set custom decay factor for a memory's relationships.

    Args:
        memory_db: Database instance for memory operations
        arguments: Tool arguments from MCP call containing:
            - memory_id: ID of memory to set decay factor for
            - decay_factor: New decay factor (0.0-1.0, 1.0 = no decay)
            - reason: Reason for the change

    Returns:
        CallToolResult with confirmation or error message
    """
    memory_id = arguments["memory_id"]
    decay_factor = float(arguments.get("decay_factor", 0.95))
    reason = arguments.get("reason", "Custom decay factor")

    if decay_factor < 0.0 or decay_factor > 1.0:
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="Decay factor must be between 0.0 and 1.0",
                )
            ],
            isError=True,
        )

    # Verify the memory exists
    memory = await memory_db.get_memory_by_id(memory_id)

    if not memory:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Memory not found: {memory_id}")],
            isError=True,
        )

    updated = await memory_db.set_decay_factor(memory_id, decay_factor, reason)

    message = (
        f"Set decay_factor={decay_factor:.3f} for {updated} relationship(s) "
        f"of memory '{memory.title}' (ID: {memory_id}).\n"
        f"Reason: {reason}\n"
        f"Effect: each monthly decay run will multiply confidence × {decay_factor:.3f}."
    )

    return CallToolResult(
        content=[TextContent(type="text", text=message)]
    )
