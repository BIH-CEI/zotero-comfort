"""
MCP Server for Zotero Comfort.

Exposes both proxy layer and smart workflows as MCP tools.
Implements JSON-RPC 2.0 protocol for Claude integration.
"""

import json
import sys
import logging
from typing import Any, Dict, Optional

from .proxy import ZoteroProxy
from .workflows import ZoteroWorkflows

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


class ZoteroComfortServer:
    """MCP Server exposing Zotero proxy and workflow tools."""

    def __init__(self):
        """Initialize MCP server with proxy and workflows."""
        self.proxy = ZoteroProxy()
        self.workflows = ZoteroWorkflows(client=self.proxy.client)
        logger.info("Zotero Comfort MCP Server initialized")

    def get_tools(self) -> list:
        """Return list of available tools."""
        return [
            # Proxy Layer (A) - Direct MCP tool access
            {
                "name": "zotero_search",
                "description": "Search for papers in Zotero library by keyword",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (e.g., 'FHIR terminology')",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results (default: 50)",
                            "default": 50,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "zotero_get_metadata",
                "description": "Get detailed metadata for a specific paper",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "item_key": {
                            "type": "string",
                            "description": "Zotero item key",
                        }
                    },
                    "required": ["item_key"],
                },
            },
            {
                "name": "zotero_list_collections",
                "description": "List all collections in the Zotero library",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "zotero_get_collection_items",
                "description": "Get all items in a specific collection",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection_key": {
                            "type": "string",
                            "description": "Collection key",
                        }
                    },
                    "required": ["collection_key"],
                },
            },
            {
                "name": "zotero_get_fulltext",
                "description": "Get full text content of a paper",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "item_key": {
                            "type": "string",
                            "description": "Zotero item key",
                        }
                    },
                    "required": ["item_key"],
                },
            },
            {
                "name": "zotero_semantic_search",
                "description": "AI-powered semantic search for similar papers",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language search query",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results (default: 10)",
                            "default": 10,
                        },
                    },
                    "required": ["query"],
                },
            },
            # Smart Workflows (B) - High-level orchestrations
            {
                "name": "build_reading_list",
                "description": "Build a curated reading list for a research topic",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Research topic (e.g., 'FHIR interoperability')",
                        },
                        "max_papers": {
                            "type": "integer",
                            "description": "Maximum papers to include (default: 20)",
                            "default": 20,
                        },
                        "min_year": {
                            "type": "integer",
                            "description": "Only include papers from this year or later",
                        },
                    },
                    "required": ["topic"],
                },
            },
            {
                "name": "smart_add_paper",
                "description": "Add paper from DOI with duplicate checking and collection suggestion",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "doi": {
                            "type": "string",
                            "description": "Paper DOI (e.g., '10.1234/example')",
                        },
                        "check_duplicates": {
                            "type": "boolean",
                            "description": "Check if paper already exists (default: true)",
                            "default": True,
                        },
                    },
                    "required": ["doi"],
                },
            },
            {
                "name": "export_bibliography",
                "description": "Export papers as BibTeX bibliography",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "collection_name": {
                            "type": "string",
                            "description": "Export from this collection",
                        },
                        "tag": {
                            "type": "string",
                            "description": "Export papers with this tag",
                        },
                    },
                },
            },
            {
                "name": "find_related_papers",
                "description": "Find papers related to a given paper using semantic search",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "item_key": {
                            "type": "string",
                            "description": "Zotero key of the source paper",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum related papers (default: 10)",
                            "default": 10,
                        },
                    },
                    "required": ["item_key"],
                },
            },
        ]

    def make_response(
        self,
        request_id: Any,
        result: Optional[dict] = None,
        error: Optional[dict] = None,
    ) -> str:
        """Create JSON-RPC 2.0 response."""
        response = {"jsonrpc": "2.0"}

        if request_id is not None and request_id != "":
            response["id"] = request_id

        if error:
            response["error"] = error
        elif result is not None:
            response["result"] = result

        return json.dumps(response)

    def handle_initialize(self, request_id: Any) -> str:
        """Handle initialize request."""
        return self.make_response(
            request_id,
            result={
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "zotero-comfort", "version": "0.1.0"},
            },
        )

    def handle_tools_list(self, request_id: Any) -> str:
        """Handle tools/list request."""
        return self.make_response(request_id, result={"tools": self.get_tools()})

    def handle_tools_call(
        self, request_id: Any, tool_name: str, arguments: dict
    ) -> str:
        """Handle tools/call request."""
        try:
            result_data = self._dispatch_tool(tool_name, arguments)
            return self.make_response(
                request_id,
                result={"content": [{"type": "text", "text": json.dumps(result_data, indent=2)}]},
            )
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return self.make_response(
                request_id, error={"code": -32603, "message": f"Internal error: {str(e)}"}
            )

    def _dispatch_tool(self, tool_name: str, arguments: dict) -> Any:
        """Dispatch tool call to appropriate handler."""
        # Proxy Layer (A)
        if tool_name == "zotero_search":
            return self.proxy.search_papers(
                arguments.get("query", ""), arguments.get("limit", 50)
            )
        elif tool_name == "zotero_get_metadata":
            return self.proxy.get_metadata(arguments.get("item_key", ""))
        elif tool_name == "zotero_list_collections":
            return self.proxy.list_collections()
        elif tool_name == "zotero_get_collection_items":
            return self.proxy.get_collection_items(arguments.get("collection_key", ""))
        elif tool_name == "zotero_get_fulltext":
            return self.proxy.get_fulltext(arguments.get("item_key", ""))
        elif tool_name == "zotero_semantic_search":
            return self.proxy.semantic_search(
                arguments.get("query", ""), arguments.get("limit", 10)
            )

        # Smart Workflows (B)
        elif tool_name == "build_reading_list":
            return self.workflows.build_reading_list(
                arguments.get("topic", ""),
                arguments.get("max_papers", 20),
                arguments.get("min_year"),
            )
        elif tool_name == "smart_add_paper":
            return self.workflows.smart_add_paper(
                arguments.get("doi", ""),
                arguments.get("check_duplicates", True),
            )
        elif tool_name == "export_bibliography":
            return self.workflows.export_bibliography(
                arguments.get("collection_name"),
                arguments.get("tag"),
            )
        elif tool_name == "find_related_papers":
            return self.workflows.find_related_papers(
                arguments.get("item_key", ""),
                arguments.get("limit", 10),
            )

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def process_request(self, request: dict) -> Optional[str]:
        """Process a JSON-RPC request."""
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        logger.debug(f"Processing: method={method}, id={request_id}")

        # Notifications (no response)
        if request_id is None:
            if method == "notifications/initialized":
                logger.debug("Received initialized notification")
            return None

        if method == "initialize":
            return self.handle_initialize(request_id)
        elif method == "tools/list":
            return self.handle_tools_list(request_id)
        elif method == "tools/call":
            return self.handle_tools_call(
                request_id, params.get("name"), params.get("arguments", {})
            )
        else:
            return self.make_response(
                request_id, error={"code": -32601, "message": f"Method not found: {method}"}
            )


def main():
    """Run MCP server over stdio."""
    server = ZoteroComfortServer()
    logger.info("Starting Zotero Comfort MCP Server")

    try:
        while True:
            line = sys.stdin.readline()
            if not line:
                logger.info("EOF, shutting down")
                break

            try:
                request = json.loads(line)
                response = server.process_request(request)
                if response is not None:
                    print(response)
                    sys.stdout.flush()
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Parse error"},
                }))
                sys.stdout.flush()

    except KeyboardInterrupt:
        logger.info("Shutting down (SIGINT)")
        sys.exit(0)


if __name__ == "__main__":
    main()
