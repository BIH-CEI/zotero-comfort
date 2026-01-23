"""
Proxy Layer (A) - Direct re-exposure of 54yyyu/zotero-mcp tools.

These functions provide a thin wrapper around the underlying MCP tools,
offering a cleaner Python API with type hints and documentation.
"""

import logging
from typing import Any, Dict, List, Optional

from .client import ZoteroMCPClient

logger = logging.getLogger(__name__)


class ZoteroProxy:
    """
    Proxy layer that re-exposes zotero-mcp tools with Pythonic interface.

    Methods map directly to underlying MCP tools:
    - search_papers → zotero_search_items
    - get_metadata → zotero_get_item_metadata
    - list_collections → zotero_get_collections
    - get_collection_items → zotero_get_collection_items
    - get_fulltext → zotero_get_item_fulltext
    - get_annotations → zotero_get_annotations
    - semantic_search → zotero_semantic_search
    - advanced_search → zotero_advanced_search
    - get_recent → zotero_get_recent
    - get_tags → zotero_get_tags
    - search_by_tag → zotero_search_by_tag
    - add_items_to_collection → HTTP API (collection management)
    - remove_item_from_collection → HTTP API (collection management)
    """

    def __init__(self, client: Optional[ZoteroMCPClient] = None):
        """Initialize proxy layer.

        Args:
            client: ZoteroMCPClient instance (created with defaults if not provided)
        """
        self.client = client or ZoteroMCPClient()

    def search_papers(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for papers in the Zotero library.

        Args:
            query: Search query string (searches titles, abstracts, etc.)
            limit: Maximum number of results to return

        Returns:
            List of paper records with keys: key, title, creators, date, itemType
        """
        logger.info(f"Proxy: search_papers(query={query!r}, limit={limit})")
        return self.client.search_items(query, limit=limit)

    def get_metadata(self, item_key: str) -> Dict[str, Any]:
        """Get detailed metadata for a specific paper.

        Args:
            item_key: Zotero item key (e.g., "ABC12345")

        Returns:
            Full item metadata including title, creators, abstract, DOI, etc.
        """
        logger.info(f"Proxy: get_metadata(item_key={item_key!r})")
        return self.client.get_item(item_key)

    def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections in the library.

        Returns:
            List of collections with keys: key, name, parentCollection
        """
        logger.info("Proxy: list_collections()")
        return self.client.list_collections()

    def get_collection_items(self, collection_key: str) -> List[Dict[str, Any]]:
        """Get all items in a specific collection.

        Args:
            collection_key: Collection key

        Returns:
            List of items in the collection
        """
        logger.info(f"Proxy: get_collection_items(collection_key={collection_key!r})")
        return self.client.get_collection_items(collection_key)

    def get_fulltext(self, item_key: str) -> str:
        """Get full text content of a paper (if available).

        Args:
            item_key: Zotero item key

        Returns:
            Full text content as string, or empty string if not available
        """
        logger.info(f"Proxy: get_fulltext(item_key={item_key!r})")
        return self.client.get_item_fulltext(item_key)

    def get_annotations(self, item_key: str) -> List[Dict[str, Any]]:
        """Get PDF annotations (highlights, notes) for an item.

        Args:
            item_key: Zotero item key

        Returns:
            List of annotations with text, comment, color, page info
        """
        logger.info(f"Proxy: get_annotations(item_key={item_key!r})")
        return self.client.get_annotations(item_key)

    def semantic_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """AI-powered semantic search across the library.

        Finds papers semantically similar to the query, not just keyword matches.

        Args:
            query: Natural language search query
            limit: Maximum results to return

        Returns:
            List of semantically similar papers with relevance scores
        """
        logger.info(f"Proxy: semantic_search(query={query!r}, limit={limit})")
        return self.client.semantic_search(query, limit=limit)

    def advanced_search(
        self,
        title: Optional[str] = None,
        creator: Optional[str] = None,
        tag: Optional[str] = None,
        item_type: Optional[str] = None,
        year: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search with multiple filter criteria.

        Args:
            title: Filter by title (substring match)
            creator: Filter by author name
            tag: Filter by tag
            item_type: Filter by type (journalArticle, book, etc.)
            year: Filter by publication year

        Returns:
            List of matching papers
        """
        logger.info(
            f"Proxy: advanced_search(title={title!r}, creator={creator!r}, "
            f"tag={tag!r}, item_type={item_type!r}, year={year!r})"
        )
        return self.client.advanced_search(
            title=title, creator=creator, tag=tag, item_type=item_type, year=year
        )

    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recently added items.

        Args:
            limit: Maximum number of items to return

        Returns:
            List of recently added papers, newest first
        """
        logger.info(f"Proxy: get_recent(limit={limit})")
        return self.client.get_recent(limit=limit)

    def get_tags(self) -> List[str]:
        """Get all tags used in the library.

        Returns:
            List of tag names
        """
        logger.info("Proxy: get_tags()")
        return self.client.get_tags()

    def search_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Find all papers with a specific tag.

        Args:
            tag: Tag name to search for

        Returns:
            List of papers with this tag
        """
        logger.info(f"Proxy: search_by_tag(tag={tag!r})")
        return self.client.search_by_tag(tag)

    def add_items_to_collection(
        self, collection_key: str, item_keys: List[str]
    ) -> Dict[str, Any]:
        """Add one or more items to a collection.

        Items can belong to multiple collections simultaneously.

        Args:
            collection_key: Collection key to add items to
            item_keys: List of item keys to add

        Returns:
            Dictionary with status, counts, and details:
            {
                "status": "success" | "partial" | "error",
                "added": int,
                "failed": int,
                "details": [{"item_key": str, "status": str, ...}, ...]
            }
        """
        logger.info(
            f"Proxy: add_items_to_collection(collection_key={collection_key!r}, "
            f"item_keys={len(item_keys)} items)"
        )
        return self.client.add_items_to_collection(collection_key, item_keys)

    def remove_item_from_collection(
        self, collection_key: str, item_key: str
    ) -> Dict[str, Any]:
        """Remove an item from a collection.

        The item remains in the library, just not in this collection.

        Args:
            collection_key: Collection key to remove item from
            item_key: Item key to remove

        Returns:
            Dictionary with status and details:
            {
                "status": "success" | "error",
                "item_key": str,
                "collection_key": str,
                "message": str (optional),
                "error": str (if error)
            }
        """
        logger.info(
            f"Proxy: remove_item_from_collection(collection_key={collection_key!r}, "
            f"item_key={item_key!r})"
        )
        return self.client.remove_item_from_collection(collection_key, item_key)
