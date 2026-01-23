"""
External Literature Workflows - High-level orchestration for external sources.

Combines external literature search (PubMed, arXiv) with Zotero integration:
- search_pubmed_to_collection: Search PubMed → Add to Zotero collection
- search_arxiv_to_collection: Search arXiv → Add to Zotero collection
- search_multi_source_to_collection: Multi-source search → Unified collection
"""

import logging
from typing import Any, Dict, List, Optional, Literal

from .client import ZoteroMCPClient
from .external import PubMedClient, ArXivClient

logger = logging.getLogger(__name__)


class ExternalWorkflows:
    """
    Orchestrates external literature search with Zotero integration.

    Provides high-level workflows that search external sources (PubMed, arXiv)
    and automatically add results to organized Zotero collections.
    """

    def __init__(
        self,
        zotero_client: Optional[ZoteroMCPClient] = None,
        pubmed_email: Optional[str] = None
    ):
        """Initialize external workflows.

        Args:
            zotero_client: ZoteroMCPClient instance (created with defaults if not provided)
            pubmed_email: Email for PubMed API (required by NCBI)
        """
        self.zotero = zotero_client or ZoteroMCPClient()
        self.pubmed = PubMedClient(email=pubmed_email or "user@example.com")
        self.arxiv = ArXivClient()

    def _paper_to_zotero_item(
        self,
        paper: Dict[str, Any],
        source: Literal["pubmed", "arxiv"]
    ) -> Dict[str, Any]:
        """
        Convert external paper dict to Zotero item format.

        Args:
            paper: Paper dict from PubMed or arXiv
            source: Source identifier

        Returns:
            Zotero-compatible item dict
        """
        item = {
            "itemType": "journalArticle",
            "title": paper.get("title", ""),
            "abstractNote": paper.get("abstract", ""),
            "date": paper.get("publication_date", ""),
            "url": paper.get("url", ""),
            "extra": f"Source: {source}\nID: {paper.get('id', '')}",
        }

        # Add DOI if available
        if paper.get("doi"):
            item["DOI"] = paper["doi"]

        # Convert authors to Zotero creator format
        authors = paper.get("authors", [])
        item["creators"] = []
        for author in authors:
            # Handle different author formats
            if isinstance(author, str):
                # Split "Last First" or "Last, First" format
                if "," in author:
                    last, first = author.split(",", 1)
                    item["creators"].append({
                        "creatorType": "author",
                        "firstName": first.strip(),
                        "lastName": last.strip()
                    })
                else:
                    # Simple format - use as-is
                    item["creators"].append({
                        "creatorType": "author",
                        "name": author
                    })

        # Source-specific fields
        if source == "pubmed":
            item["extra"] += f"\nPMID: {paper.get('pmid', '')}"
            if paper.get("journal"):
                item["publicationTitle"] = paper["journal"]
            if paper.get("volume"):
                item["volume"] = paper["volume"]
            if paper.get("issue"):
                item["issue"] = paper["issue"]
            if paper.get("pages"):
                item["pages"] = paper["pages"]

        elif source == "arxiv":
            item["extra"] += f"\narXiv: {paper.get('arxiv_id', '')}"
            item["publicationTitle"] = "arXiv preprint"
            if paper.get("primary_category"):
                item["extra"] += f"\nCategory: {paper['primary_category']}"
            if paper.get("pdf_url"):
                item["extra"] += f"\nPDF: {paper['pdf_url']}"

        return item

    async def search_pubmed_to_collection(
        self,
        query: str,
        collection_name: str,
        max_results: int = 50,
        create_collection: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search PubMed and add results to a Zotero collection.

        Args:
            query: PubMed search query
            collection_name: Target Zotero collection name
            max_results: Maximum papers to add
            create_collection: Create collection if it doesn't exist
            **kwargs: Additional PubMed search parameters (min_date, max_date, etc.)

        Returns:
            Summary dict with:
                - papers_found: Number of papers from PubMed
                - papers_added: Number successfully added to Zotero
                - collection_key: Zotero collection key
                - items_added: List of added item keys

        Example:
            result = await workflows.search_pubmed_to_collection(
                query="PROMIS quality of life",
                collection_name="PROMs",
                max_results=30
            )
        """
        logger.info(f"Searching PubMed for '{query}' → collection '{collection_name}'")

        # Search PubMed
        papers = await self.pubmed.search_articles(query, max_results=max_results, **kwargs)
        logger.info(f"Found {len(papers)} papers from PubMed")

        # Find or create collection
        collections = self.zotero.list_collections()
        collection_key = None

        for coll in collections:
            if coll.get("name") == collection_name:
                collection_key = coll["key"]
                logger.info(f"Using existing collection: {collection_name} ({collection_key})")
                break

        if not collection_key and create_collection:
            result = self.zotero.create_collection(collection_name)
            collection_key = result.get("key")
            logger.info(f"Created new collection: {collection_name} ({collection_key})")

        if not collection_key:
            return {
                "status": "error",
                "error": f"Collection '{collection_name}' not found and create_collection=False",
                "papers_found": len(papers),
                "papers_added": 0
            }

        # Add papers to Zotero
        items_added = []
        for paper in papers:
            zotero_item = self._paper_to_zotero_item(paper, source="pubmed")

            # Add to Zotero
            result = self.zotero.add_item(zotero_item)
            if result.get("status") == "success":
                item_key = result["key"]
                items_added.append(item_key)
                logger.debug(f"Added item: {item_key} - {paper['title'][:50]}...")
            else:
                logger.warning(f"Failed to add paper: {paper.get('title', 'Unknown')}")

        # Add all items to collection
        if items_added and collection_key:
            self.zotero.add_items_to_collection(collection_key, items_added)
            logger.info(f"Added {len(items_added)} items to collection")

        return {
            "status": "success",
            "papers_found": len(papers),
            "papers_added": len(items_added),
            "collection_name": collection_name,
            "collection_key": collection_key,
            "items_added": items_added
        }

    async def search_arxiv_to_collection(
        self,
        query: str,
        collection_name: str,
        max_results: int = 50,
        create_collection: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search arXiv and add results to a Zotero collection.

        Args:
            query: arXiv search query (supports ti:, au:, cat: prefixes)
            collection_name: Target Zotero collection name
            max_results: Maximum papers to add
            create_collection: Create collection if it doesn't exist
            **kwargs: Additional arXiv search parameters (categories, sort_by, etc.)

        Returns:
            Summary dict with papers_found, papers_added, collection_key, items_added

        Example:
            result = await workflows.search_arxiv_to_collection(
                query="machine learning healthcare",
                collection_name="ML in Healthcare",
                max_results=20,
                categories=["cs.LG", "cs.AI"]
            )
        """
        logger.info(f"Searching arXiv for '{query}' → collection '{collection_name}'")

        # Search arXiv
        papers = await self.arxiv.search(query, max_results=max_results, **kwargs)
        logger.info(f"Found {len(papers)} papers from arXiv")

        # Find or create collection
        collections = self.zotero.list_collections()
        collection_key = None

        for coll in collections:
            if coll.get("name") == collection_name:
                collection_key = coll["key"]
                logger.info(f"Using existing collection: {collection_name} ({collection_key})")
                break

        if not collection_key and create_collection:
            result = self.zotero.create_collection(collection_name)
            collection_key = result.get("key")
            logger.info(f"Created new collection: {collection_name} ({collection_key})")

        if not collection_key:
            return {
                "status": "error",
                "error": f"Collection '{collection_name}' not found and create_collection=False",
                "papers_found": len(papers),
                "papers_added": 0
            }

        # Add papers to Zotero
        items_added = []
        for paper in papers:
            zotero_item = self._paper_to_zotero_item(paper, source="arxiv")

            # Add to Zotero
            result = self.zotero.add_item(zotero_item)
            if result.get("status") == "success":
                item_key = result["key"]
                items_added.append(item_key)
                logger.debug(f"Added item: {item_key} - {paper['title'][:50]}...")
            else:
                logger.warning(f"Failed to add paper: {paper.get('title', 'Unknown')}")

        # Add all items to collection
        if items_added and collection_key:
            self.zotero.add_items_to_collection(collection_key, items_added)
            logger.info(f"Added {len(items_added)} items to collection")

        return {
            "status": "success",
            "papers_found": len(papers),
            "papers_added": len(items_added),
            "collection_name": collection_name,
            "collection_key": collection_key,
            "items_added": items_added
        }

    async def search_multi_source_to_collection(
        self,
        query: str,
        collection_name: str,
        sources: List[Literal["pubmed", "arxiv"]] = ["pubmed", "arxiv"],
        max_results_per_source: int = 25,
        create_collection: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search multiple sources and combine results in a single Zotero collection.

        Args:
            query: Search query
            collection_name: Target Zotero collection name
            sources: List of sources to search (["pubmed", "arxiv"])
            max_results_per_source: Max results from each source
            create_collection: Create collection if it doesn't exist
            **kwargs: Source-specific parameters

        Returns:
            Summary dict with results from all sources

        Example:
            result = await workflows.search_multi_source_to_collection(
                query="patient reported outcomes",
                collection_name="PROMs Literature",
                sources=["pubmed", "arxiv"],
                max_results_per_source=30
            )
        """
        logger.info(f"Multi-source search for '{query}' → collection '{collection_name}'")
        logger.info(f"Sources: {sources}")

        all_papers = []
        source_counts = {}

        # Search each source
        for source in sources:
            if source == "pubmed":
                papers = await self.pubmed.search_articles(query, max_results=max_results_per_source)
                source_counts["pubmed"] = len(papers)
                all_papers.extend([(paper, "pubmed") for paper in papers])

            elif source == "arxiv":
                papers = await self.arxiv.search(query, max_results=max_results_per_source)
                source_counts["arxiv"] = len(papers)
                all_papers.extend([(paper, "arxiv") for paper in papers])

        logger.info(f"Found total {len(all_papers)} papers: {source_counts}")

        # Find or create collection
        collections = self.zotero.list_collections()
        collection_key = None

        for coll in collections:
            if coll.get("name") == collection_name:
                collection_key = coll["key"]
                logger.info(f"Using existing collection: {collection_name} ({collection_key})")
                break

        if not collection_key and create_collection:
            result = self.zotero.create_collection(collection_name)
            collection_key = result.get("key")
            logger.info(f"Created new collection: {collection_name} ({collection_key})")

        if not collection_key:
            return {
                "status": "error",
                "error": f"Collection '{collection_name}' not found and create_collection=False",
                "papers_found": len(all_papers),
                "papers_added": 0,
                "source_counts": source_counts
            }

        # Add papers to Zotero
        items_added = []
        items_by_source = {source: [] for source in sources}

        for paper, source in all_papers:
            zotero_item = self._paper_to_zotero_item(paper, source=source)

            # Add to Zotero
            result = self.zotero.add_item(zotero_item)
            if result.get("status") == "success":
                item_key = result["key"]
                items_added.append(item_key)
                items_by_source[source].append(item_key)
                logger.debug(f"Added item from {source}: {item_key} - {paper['title'][:50]}...")
            else:
                logger.warning(f"Failed to add paper from {source}: {paper.get('title', 'Unknown')}")

        # Add all items to collection
        if items_added and collection_key:
            self.zotero.add_items_to_collection(collection_key, items_added)
            logger.info(f"Added {len(items_added)} items to collection")

        return {
            "status": "success",
            "papers_found": len(all_papers),
            "papers_added": len(items_added),
            "collection_name": collection_name,
            "collection_key": collection_key,
            "source_counts": source_counts,
            "items_added_by_source": items_by_source,
            "items_added": items_added
        }
