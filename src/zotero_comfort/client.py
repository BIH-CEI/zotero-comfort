"""
MCP client for Zotero integration via 54yyyu/zotero-mcp.

Provides a synchronous Python interface to the community Zotero MCP server.
Supports dual-library architecture for group and personal libraries.
"""

import asyncio
import json
import os
import logging
from typing import Any, Dict, List, Optional, Literal

logger = logging.getLogger(__name__)

LibraryType = Literal["group", "personal"]

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP SDK not installed. Install with: pip install mcp")


class ZoteroMCPClient:
    """
    Client for Zotero MCP server (54yyyu/zotero-mcp).

    Wraps the community MCP server with a synchronous Python interface.
    Handles connection lifecycle and JSON serialization.
    """

    def __init__(
        self,
        library_id: Optional[str] = None,
        library_type: Optional[str] = None,
        api_key: Optional[str] = None,
        mcp_command: str = "zotero-mcp",
    ):
        """Initialize Zotero MCP client.

        Args:
            library_id: Zotero library ID (from env ZOTERO_LIBRARY_ID)
            library_type: 'user' or 'group' (default from env or 'group')
            api_key: Zotero API key (from env ZOTERO_API_KEY)
            mcp_command: Command to run the MCP server
        """
        self.library_id = library_id or os.getenv("ZOTERO_LIBRARY_ID")
        self.library_type = library_type or os.getenv("ZOTERO_LIBRARY_TYPE", "group")
        self.api_key = api_key or os.getenv("ZOTERO_API_KEY")
        self.mcp_command = mcp_command

        self._env = os.environ.copy()
        if self.library_id:
            self._env["ZOTERO_LIBRARY_ID"] = str(self.library_id)
        if self.library_type:
            self._env["ZOTERO_LIBRARY_TYPE"] = self.library_type
        if self.api_key:
            self._env["ZOTERO_API_KEY"] = self.api_key

        logger.info(f"ZoteroMCPClient: {self.library_type} library {self.library_id}")

    def _get_server_params(self) -> "StdioServerParameters":
        """Get MCP server parameters."""
        if not MCP_AVAILABLE:
            raise RuntimeError("MCP SDK not installed. Run: pip install mcp")

        return StdioServerParameters(
            command=self.mcp_command,
            args=[],
            env=self._env,
        )

    async def _call_tool_async(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call an MCP tool asynchronously.

        Args:
            tool_name: Name of the tool (e.g., 'zotero_search_items')
            arguments: Tool arguments

        Returns:
            Tool result as dict
        """
        if not MCP_AVAILABLE:
            return {"error": "MCP SDK not installed", "tool": tool_name}

        server_params = self._get_server_params()

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    result = await session.call_tool(tool_name, arguments=arguments)

                    if hasattr(result, "content") and result.content:
                        for content_item in result.content:
                            if hasattr(content_item, "text"):
                                try:
                                    return json.loads(content_item.text)
                                except json.JSONDecodeError:
                                    return {"text": content_item.text}

                    return {"result": str(result)}

        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            return {"error": str(e), "tool": tool_name}

    def call_tool(self, tool_name: str, **arguments) -> Dict[str, Any]:
        """Call an MCP tool synchronously.

        Args:
            tool_name: Name of the tool
            **arguments: Tool arguments

        Returns:
            Tool result as dict
        """
        logger.debug(f"Calling MCP tool: {tool_name} with args: {arguments}")
        return asyncio.run(self._call_tool_async(tool_name, arguments))

    # Convenience methods mapping to zotero-mcp tools

    def search_items(self, query: str, limit: int = 50) -> List[Dict]:
        """Search for papers in the library."""
        result = self.call_tool("zotero_search_items", query=query, limit=limit)
        if "error" in result:
            logger.error(f"Search error: {result['error']}")
            return []
        return result.get("items", result.get("results", []))[:limit]

    def get_item(self, item_key: str) -> Dict[str, Any]:
        """Get metadata for a specific item."""
        result = self.call_tool("zotero_get_item_metadata", item_key=item_key)
        if "error" in result:
            logger.error(f"Item fetch error: {result['error']}")
        return result

    def list_collections(self) -> List[Dict]:
        """List all collections in the library."""
        result = self.call_tool("zotero_get_collections")
        if "error" in result:
            logger.error(f"Collection fetch error: {result['error']}")
            return []
        return result.get("collections", [])

    def get_collection_items(self, collection_key: str) -> List[Dict]:
        """Get items in a specific collection."""
        result = self.call_tool("zotero_get_collection_items", collection_key=collection_key)
        if "error" in result:
            logger.error(f"Collection items error: {result['error']}")
            return []
        return result.get("items", [])

    def get_item_fulltext(self, item_key: str) -> str:
        """Get full text content of an item."""
        result = self.call_tool("zotero_get_item_fulltext", item_key=item_key)
        if "error" in result:
            logger.error(f"Fulltext error: {result['error']}")
            return ""
        return result.get("fulltext", result.get("text", ""))

    def get_annotations(self, item_key: str) -> List[Dict]:
        """Get annotations for an item."""
        result = self.call_tool("zotero_get_annotations", item_key=item_key)
        if "error" in result:
            logger.error(f"Annotations error: {result['error']}")
            return []
        return result.get("annotations", [])

    def semantic_search(self, query: str, limit: int = 10) -> List[Dict]:
        """AI-powered semantic search."""
        result = self.call_tool("zotero_semantic_search", query=query, limit=limit)
        if "error" in result:
            logger.error(f"Semantic search error: {result['error']}")
            return []
        return result.get("results", result.get("items", []))

    def advanced_search(
        self,
        title: Optional[str] = None,
        creator: Optional[str] = None,
        tag: Optional[str] = None,
        item_type: Optional[str] = None,
        year: Optional[str] = None,
    ) -> List[Dict]:
        """Advanced search with multiple criteria."""
        criteria = {}
        if title:
            criteria["title"] = title
        if creator:
            criteria["creator"] = creator
        if tag:
            criteria["tag"] = tag
        if item_type:
            criteria["itemType"] = item_type
        if year:
            criteria["year"] = year

        result = self.call_tool("zotero_advanced_search", **criteria)
        if "error" in result:
            logger.error(f"Advanced search error: {result['error']}")
            return []
        return result.get("items", result.get("results", []))

    def get_recent(self, limit: int = 20) -> List[Dict]:
        """Get recently added items."""
        result = self.call_tool("zotero_get_recent", limit=limit)
        if "error" in result:
            logger.error(f"Recent items error: {result['error']}")
            return []
        return result.get("items", [])

    def get_tags(self) -> List[str]:
        """Get all tags in the library."""
        result = self.call_tool("zotero_get_tags")
        if "error" in result:
            logger.error(f"Tags error: {result['error']}")
            return []
        return result.get("tags", [])

    def search_by_tag(self, tag: str) -> List[Dict]:
        """Search items by tag."""
        result = self.call_tool("zotero_search_by_tag", tag=tag)
        if "error" in result:
            logger.error(f"Tag search error: {result['error']}")
            return []
        return result.get("items", [])


class DualLibraryClient:
    """
    Client that manages both group and personal Zotero libraries.

    Provides unified access to both libraries with explicit library selection
    for operations that support it.
    """

    def __init__(
        self,
        group_library_id: Optional[str] = None,
        group_api_key: Optional[str] = None,
        personal_library_id: Optional[str] = None,
        personal_api_key: Optional[str] = None,
        mcp_command: str = "zotero-mcp",
    ):
        """Initialize dual library client.

        Args:
            group_library_id: Group library ID (from env ZOTERO_GROUP_LIBRARY_ID)
            group_api_key: Group library API key (from env ZOTERO_GROUP_API_KEY)
            personal_library_id: Personal library ID (from env ZOTERO_PERSONAL_LIBRARY_ID)
            personal_api_key: Personal library API key (from env ZOTERO_PERSONAL_API_KEY)
            mcp_command: Command to run the MCP server
        """
        # Group library configuration
        self.group_library_id = group_library_id or os.getenv("ZOTERO_GROUP_LIBRARY_ID")
        self.group_api_key = group_api_key or os.getenv("ZOTERO_GROUP_API_KEY")

        # Personal library configuration
        self.personal_library_id = personal_library_id or os.getenv("ZOTERO_PERSONAL_LIBRARY_ID")
        self.personal_api_key = personal_api_key or os.getenv("ZOTERO_PERSONAL_API_KEY")

        # Fallback to single library env vars for backwards compatibility
        if not self.group_library_id:
            self.group_library_id = os.getenv("ZOTERO_LIBRARY_ID")
            self.group_api_key = self.group_api_key or os.getenv("ZOTERO_API_KEY")

        self.mcp_command = mcp_command

        # Initialize clients (lazy - only if credentials provided)
        self._group_client: Optional[ZoteroMCPClient] = None
        self._personal_client: Optional[ZoteroMCPClient] = None

        # Default library for operations
        self._default_library: LibraryType = "group"

        logger.info(
            f"DualLibraryClient: group={self.group_library_id}, "
            f"personal={self.personal_library_id}"
        )

    @property
    def group_client(self) -> Optional[ZoteroMCPClient]:
        """Get group library client (lazy initialization)."""
        if self._group_client is None and self.group_library_id and self.group_api_key:
            self._group_client = ZoteroMCPClient(
                library_id=self.group_library_id,
                library_type="group",
                api_key=self.group_api_key,
                mcp_command=self.mcp_command,
            )
        return self._group_client

    @property
    def personal_client(self) -> Optional[ZoteroMCPClient]:
        """Get personal library client (lazy initialization)."""
        if self._personal_client is None and self.personal_library_id and self.personal_api_key:
            self._personal_client = ZoteroMCPClient(
                library_id=self.personal_library_id,
                library_type="user",
                api_key=self.personal_api_key,
                mcp_command=self.mcp_command,
            )
        return self._personal_client

    def get_client(self, library: Optional[LibraryType] = None) -> ZoteroMCPClient:
        """Get client for specified library.

        Args:
            library: 'group' or 'personal', defaults to default library

        Returns:
            ZoteroMCPClient for the specified library

        Raises:
            ValueError: If specified library is not configured
        """
        library = library or self._default_library

        if library == "group":
            if not self.group_client:
                raise ValueError("Group library not configured")
            return self.group_client
        elif library == "personal":
            if not self.personal_client:
                raise ValueError("Personal library not configured")
            return self.personal_client
        else:
            raise ValueError(f"Unknown library type: {library}")

    def set_default_library(self, library: LibraryType) -> None:
        """Set the default library for operations."""
        if library not in ("group", "personal"):
            raise ValueError(f"Invalid library type: {library}")
        self._default_library = library
        logger.info(f"Default library set to: {library}")

    def get_library_status(self) -> Dict[str, Any]:
        """Get status of both libraries.

        Returns:
            {
                'group': {'configured': bool, 'library_id': str},
                'personal': {'configured': bool, 'library_id': str},
                'default': str
            }
        """
        return {
            "group": {
                "configured": bool(self.group_library_id and self.group_api_key),
                "library_id": self.group_library_id or "",
            },
            "personal": {
                "configured": bool(self.personal_library_id and self.personal_api_key),
                "library_id": self.personal_library_id or "",
            },
            "default": self._default_library,
        }

    # Convenience methods that delegate to appropriate client

    def search_items(
        self, query: str, limit: int = 50, library: Optional[LibraryType] = None
    ) -> List[Dict]:
        """Search for papers in specified library."""
        return self.get_client(library).search_items(query, limit=limit)

    def get_item(
        self, item_key: str, library: Optional[LibraryType] = None
    ) -> Dict[str, Any]:
        """Get metadata for a specific item."""
        return self.get_client(library).get_item(item_key)

    def list_collections(
        self, library: Optional[LibraryType] = None
    ) -> List[Dict]:
        """List all collections in specified library."""
        return self.get_client(library).list_collections()

    def get_collection_items(
        self, collection_key: str, library: Optional[LibraryType] = None
    ) -> List[Dict]:
        """Get items in a specific collection."""
        return self.get_client(library).get_collection_items(collection_key)

    def semantic_search(
        self, query: str, limit: int = 10, library: Optional[LibraryType] = None
    ) -> List[Dict]:
        """AI-powered semantic search in specified library."""
        return self.get_client(library).semantic_search(query, limit=limit)
