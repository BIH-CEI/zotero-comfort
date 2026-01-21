#!/usr/bin/env python3
"""
HTTP Server for Zotero Comfort.

Exposes the same functionality as the MCP server via REST API.
Uses the existing proxy and workflows layers - NO DUPLICATION.

Usage:
    uvicorn http_server:app --host 0.0.0.0 --port 8000

Or directly:
    python http_server.py
"""

import os
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from contextlib import asynccontextmanager

# Import existing modules - NO DUPLICATION
from src.zotero_comfort.client import DualLibraryClient
from src.zotero_comfort.proxy import ZoteroProxy
from src.zotero_comfort.workflows import ZoteroWorkflows

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

# Global instances (initialized at startup)
dual_client: Optional[DualLibraryClient] = None
proxy: Optional[ZoteroProxy] = None
workflows: Optional[ZoteroWorkflows] = None

# Thread pool for running sync MCP calls (they use asyncio.run internally)
executor = ThreadPoolExecutor(max_workers=4)


async def run_sync(func, *args, **kwargs):
    """Run a sync function in thread pool to avoid asyncio conflicts."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, partial(func, *args, **kwargs))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize shared instances at startup."""
    global dual_client, proxy, workflows

    dual_client = DualLibraryClient()
    proxy = ZoteroProxy(client=dual_client.group_client)
    workflows = ZoteroWorkflows(client=dual_client.group_client)

    logger.info("Zotero Comfort HTTP Server initialized")
    logger.info(f"Library status: {dual_client.get_library_status()}")

    yield

    logger.info("Zotero Comfort HTTP Server shutting down")


app = FastAPI(
    title="Zotero Comfort HTTP API",
    description="REST API for Zotero research library - wraps existing MCP functionality",
    version="0.1.0",
    lifespan=lifespan,
)


# =============================================================================
# Health & Status
# =============================================================================

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "zotero-comfort-http",
    }


@app.get("/api/status")
async def library_status():
    """Get status of configured libraries."""
    return dual_client.get_library_status()


# =============================================================================
# Proxy Layer (A) - Direct operations
# =============================================================================

@app.get("/api/papers/search")
async def search_papers(
    query: str = Query(..., description="Search query"),
    limit: int = Query(50, description="Maximum results"),
):
    """Search for papers in the library."""
    try:
        results = await run_sync(proxy.search_papers, query, limit=limit)
        return {"query": query, "results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/papers/{item_key}")
async def get_paper_metadata(item_key: str):
    """Get detailed metadata for a specific paper."""
    try:
        metadata = await run_sync(proxy.get_metadata, item_key)
        if "error" in metadata:
            raise HTTPException(status_code=404, detail=metadata["error"])
        return {"item_key": item_key, "metadata": metadata}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metadata error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/papers/{item_key}/fulltext")
async def get_paper_fulltext(item_key: str):
    """Get full text content of a paper."""
    try:
        fulltext = await run_sync(proxy.get_fulltext, item_key)
        return {"item_key": item_key, "fulltext": fulltext}
    except Exception as e:
        logger.error(f"Fulltext error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/papers/{item_key}/annotations")
async def get_paper_annotations(item_key: str):
    """Get PDF annotations for a paper."""
    try:
        annotations = await run_sync(proxy.get_annotations, item_key)
        return {"item_key": item_key, "annotations": annotations}
    except Exception as e:
        logger.error(f"Annotations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/collections")
async def list_collections():
    """List all collections in the library."""
    try:
        collections = await run_sync(proxy.list_collections)
        return {"collections": collections, "count": len(collections)}
    except Exception as e:
        logger.error(f"Collections error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/collections/{collection_key}/items")
async def get_collection_items(collection_key: str):
    """Get all items in a specific collection."""
    try:
        items = await run_sync(proxy.get_collection_items, collection_key)
        return {"collection_key": collection_key, "items": items, "count": len(items)}
    except Exception as e:
        logger.error(f"Collection items error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/papers/semantic-search")
async def semantic_search(
    query: str = Query(..., description="Natural language search query"),
    limit: int = Query(10, description="Maximum results"),
):
    """AI-powered semantic search across the library."""
    try:
        results = await run_sync(proxy.semantic_search, query, limit=limit)
        return {"query": query, "results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/papers/advanced-search")
async def advanced_search(
    title: Optional[str] = Query(None, description="Filter by title"),
    creator: Optional[str] = Query(None, description="Filter by author"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    item_type: Optional[str] = Query(None, description="Filter by type"),
    year: Optional[str] = Query(None, description="Filter by year"),
):
    """Search with multiple filter criteria."""
    try:
        results = await run_sync(
            proxy.advanced_search, title=title, creator=creator, tag=tag, item_type=item_type, year=year
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Advanced search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/papers/recent")
async def get_recent_papers(limit: int = Query(20, description="Maximum results")):
    """Get recently added papers."""
    try:
        results = await run_sync(proxy.get_recent, limit=limit)
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Recent papers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tags")
async def get_tags():
    """Get all tags in the library."""
    try:
        tags = await run_sync(proxy.get_tags)
        return {"tags": tags, "count": len(tags)}
    except Exception as e:
        logger.error(f"Tags error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tags/{tag}/papers")
async def get_papers_by_tag(tag: str):
    """Get all papers with a specific tag."""
    try:
        results = await run_sync(proxy.search_by_tag, tag)
        return {"tag": tag, "results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Tag search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Workflows Layer (B) - Smart orchestrations
# =============================================================================

@app.get("/api/workflows/reading-list")
async def build_reading_list(
    topic: str = Query(..., description="Research topic"),
    max_papers: int = Query(20, description="Maximum papers to include"),
    min_year: Optional[int] = Query(None, description="Only include papers from this year or later"),
):
    """Build a curated reading list for a research topic."""
    try:
        result = await run_sync(workflows.build_reading_list, topic, max_papers=max_papers, min_year=min_year)
        return result
    except Exception as e:
        logger.error(f"Reading list error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/smart-add")
async def smart_add_paper(
    doi: str = Query(..., description="Paper DOI"),
    check_duplicates: bool = Query(True, description="Check for duplicates"),
):
    """Check DOI for duplicates and suggest collection (read-only preview)."""
    try:
        result = await run_sync(workflows.smart_add_paper, doi, check_duplicates=check_duplicates)
        return result
    except Exception as e:
        logger.error(f"Smart add error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/export-bibliography")
async def export_bibliography(
    collection_name: Optional[str] = Query(None, description="Export from this collection"),
    tag: Optional[str] = Query(None, description="Export papers with this tag"),
):
    """Export papers as BibTeX bibliography."""
    try:
        result = await run_sync(workflows.export_bibliography, collection_name=collection_name, tag=tag)
        return result
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/related-papers/{item_key}")
async def find_related_papers(
    item_key: str,
    limit: int = Query(10, description="Maximum related papers"),
):
    """Find papers related to a given paper using semantic search."""
    try:
        result = await run_sync(workflows.find_related_papers, item_key, limit=limit)
        return result
    except Exception as e:
        logger.error(f"Related papers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Dual Library Support (C)
# =============================================================================

@app.get("/api/group/search")
async def search_group_library(
    query: str = Query(..., description="Search query"),
    limit: int = Query(50, description="Maximum results"),
):
    """Search in the group (shared team) library."""
    try:
        results = await run_sync(dual_client.search_items, query, limit=limit, library="group")
        return {"library": "group", "query": query, "results": results, "count": len(results)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Group search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/personal/search")
async def search_personal_library(
    query: str = Query(..., description="Search query"),
    limit: int = Query(50, description="Maximum results"),
):
    """Search in your personal library."""
    try:
        results = await run_sync(dual_client.search_items, query, limit=limit, library="personal")
        return {"library": "personal", "query": query, "results": results, "count": len(results)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Personal search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
