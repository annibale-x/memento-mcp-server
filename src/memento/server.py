"""
MCP Memento for Zed Editor.

This module implements the Model Context Protocol server that provides intelligent
memory capabilities for Zed editor using SQLite as the backend storage.
"""

import asyncio
import logging
from typing import List, Optional

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    TextContent,
    Tool,
)

from . import __version__
from .advanced_tools import ADVANCED_RELATIONSHIP_TOOLS, AdvancedRelationshipHandlers
from .config import Config
from .database.interface import SQLiteMemoryDatabase

# Note: Only MemoryType from models is imported at module level.
# Other domain model classes (Memory, RelationshipType, etc.) are passed via tool handlers.
from .models import (
    MemoryType,
)
from .tools.definitions import get_all_tools
from .tools.registry import get_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Memento:
    """MCP Memento for Zed Editor."""

    def __init__(self):
        """Initialize the memento."""
        self.server = Server("memento")
        self.db_connection = None  # GraphBackend instance
        self.memory_db: Optional[SQLiteMemoryDatabase] = None
        self.advanced_handlers: Optional[AdvancedRelationshipHandlers] = None

        # Register MCP handlers
        self._register_handlers()

        # Collect all tools from all modules
        all_tools = self._collect_all_tools()

        # Filter tools based on profile
        enabled_tool_names = Config.get_enabled_tools()
        if enabled_tool_names is None:
            # Full profile: all tools enabled
            self.tools = all_tools
            logger.info(f"Tool profile: FULL - All {len(all_tools)} tools enabled")
        else:
            # Filter tools by name
            self.tools = [tool for tool in all_tools if tool.name in enabled_tool_names]
            logger.info(
                f"Tool profile: {Config.TOOL_PROFILE.upper()} - {len(self.tools)}/{len(all_tools)} tools enabled"
            )

    def _collect_all_tools(self) -> List[Tool]:
        """Collect all tool definitions from all modules."""
        return get_all_tools() + ADVANCED_RELATIONSHIP_TOOLS

    def _register_handlers(self):
        """Register MCP protocol handlers."""

        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """List available tools."""
            return ListToolsResult(tools=self.tools)

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> CallToolResult:
            """Handle tool calls."""
            try:
                if not self.memory_db:
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text="Error: Memory database not initialized",
                            )
                        ],
                        isError=True,
                    )

                # Check core tool handlers first using registry
                handler = get_handler(name)
                if handler:
                    return await handler(self.memory_db, arguments)
                # Advanced relationship tools
                elif name in [
                    "find_path_between_mementos",
                    "get_memento_clusters",
                    "get_central_mementos",
                    "suggest_memento_relationships",
                    "find_memento_patterns",
                    "analyze_memento_graph",
                    "get_memento_network",
                ]:
                    # Dispatch to advanced handlers
                    method_name = f"handle_{name}"
                    handler = getattr(self.advanced_handlers, method_name, None)
                    if handler:
                        return await handler(arguments)
                    else:
                        return CallToolResult(
                            content=[
                                TextContent(
                                    type="text", text=f"Handler not found: {name}"
                                )
                            ],
                            isError=True,
                        )

                else:
                    return CallToolResult(
                        content=[
                            TextContent(type="text", text=f"Unknown tool: {name}")
                        ],
                        isError=True,
                    )

            except Exception as e:
                logger.error(f"Error handling tool call {name}: {e}", exc_info=True)
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True,
                )

    async def initialize(self):
        """Initialize the server and establish database connection."""
        try:
            # Initialize backend connection directly
            from .database.engine import SQLiteBackend

            self.db_connection = SQLiteBackend()
            await self.db_connection.connect()

            # Initialize database schema (creates tables if they don't exist)
            await self.db_connection.initialize_schema()

            # Initialize memory database - always use SQLiteMemoryDatabase
            logger.info("Using SQLiteMemoryDatabase for SQLite backend")
            self.memory_db = SQLiteMemoryDatabase(self.db_connection)

            # Initialize advanced relationship handlers
            self.advanced_handlers = AdvancedRelationshipHandlers(self.memory_db)

            backend_name = getattr(
                self.db_connection, "backend_name", lambda: "Unknown"
            )
            if callable(backend_name):
                backend_name = backend_name()
            logger.info("MCP Memento initialized successfully.")
            logger.info(f"Backend: {backend_name}")
            logger.info(
                f"Tool profile: {Config.TOOL_PROFILE.upper()} ({len(self.tools)} tools enabled)"
            )

        except Exception as e:
            logger.error(f"Failed to initialize server: {e}", exc_info=True)
            raise

    async def cleanup(self):
        """Clean up resources."""
        if self.db_connection:
            await self.db_connection.close()
        logger.info("Memento Server cleanup completed")


async def main():
    """Main entry point for the memento."""
    server = Memento()

    try:
        # Initialize the context keeper
        await server.initialize()

        # Create notification options and capabilities BEFORE passing to InitializationOptions
        # This ensures proper object instantiation and avoids potential GC or scoping issues
        notification_options = NotificationOptions()
        capabilities = server.server.get_capabilities(
            notification_options=notification_options,
            experimental_capabilities={},
        )

        # Run the stdio server
        async with stdio_server() as (read_stream, write_stream):
            await server.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="memento",
                    server_version=__version__,
                    capabilities=capabilities,
                ),
            )

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise
    finally:
        await server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
