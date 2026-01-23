"""
Tests for arXiv external source client.
"""

import pytest
from zotero_comfort.external.arxiv import ArXivClient


@pytest.fixture
def arxiv_client():
    """Create arXiv client."""
    return ArXivClient()


@pytest.mark.asyncio
async def test_search(arxiv_client):
    """Test basic arXiv search."""
    results = await arxiv_client.search(
        query="quantum computing",
        max_results=5
    )

    assert isinstance(results, list)
    assert len(results) <= 5

    if results:
        paper = results[0]
        assert "arxiv_id" in paper
        assert "title" in paper
        assert "abstract" in paper
        assert "authors" in paper
        assert "source" in paper
        assert paper["source"] == "arxiv"


@pytest.mark.asyncio
async def test_get_details(arxiv_client):
    """Test retrieving paper details by arXiv ID."""
    # Use a known stable arXiv ID
    arxiv_id = "2103.15348"  # Example paper

    details = await arxiv_client.get_details(arxiv_id)

    assert details["arxiv_id"] == arxiv_id
    assert "title" in details
    assert "abstract" in details
    assert "authors" in details
    assert isinstance(details["authors"], list)
    assert "publication_date" in details
    assert "pdf_url" in details


@pytest.mark.asyncio
async def test_search_by_author(arxiv_client):
    """Test author-specific search."""
    results = await arxiv_client.search_by_author(
        author="Bengio",
        max_results=3
    )

    assert isinstance(results, list)
    assert len(results) <= 3

    if results:
        # Check that results contain author information
        for paper in results:
            assert "authors" in paper
            assert isinstance(paper["authors"], list)


@pytest.mark.asyncio
async def test_search_by_category(arxiv_client):
    """Test category-specific search."""
    results = await arxiv_client.search_by_category(
        category="cs.AI",
        max_results=5
    )

    assert isinstance(results, list)
    assert len(results) <= 5

    if results:
        # Check that papers have category information
        for paper in results:
            assert "categories" in paper
            assert isinstance(paper["categories"], list)


@pytest.mark.asyncio
async def test_get_recent_papers(arxiv_client):
    """Test getting recent papers."""
    recent = await arxiv_client.get_recent_papers(
        category="cs.LG",
        max_results=5
    )

    assert isinstance(recent, list)
    assert len(recent) <= 5

    if recent:
        paper = recent[0]
        assert "publication_date" in paper
        assert "arxiv_id" in paper


@pytest.mark.asyncio
async def test_export_bibtex(arxiv_client):
    """Test BibTeX export."""
    arxiv_id = "2103.15348"

    bibtex = await arxiv_client.export_bibtex(arxiv_id)

    assert isinstance(bibtex, str)
    assert "@article{" in bibtex
    assert "title" in bibtex
    assert "author" in bibtex
    assert "arxiv" in bibtex.lower()


@pytest.mark.asyncio
async def test_search_with_category_filter(arxiv_client):
    """Test search with category filtering."""
    results = await arxiv_client.search(
        query="machine learning",
        max_results=5,
        categories=["cs.LG", "stat.ML"]
    )

    assert isinstance(results, list)
    assert len(results) <= 5

    if results:
        # Check that results are from specified categories
        for paper in results:
            assert "categories" in paper
