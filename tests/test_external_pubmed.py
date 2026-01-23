"""
Tests for PubMed external source client.
"""

import pytest
from zotero_comfort.external.pubmed import PubMedClient


@pytest.fixture
def pubmed_client():
    """Create PubMed client with test email."""
    return PubMedClient(email="test@example.com")


@pytest.mark.asyncio
async def test_search_articles(pubmed_client):
    """Test basic article search."""
    results = await pubmed_client.search_articles(
        query="PROMIS quality of life",
        max_results=5
    )

    assert isinstance(results, list)
    assert len(results) <= 5

    if results:
        article = results[0]
        assert "pmid" in article
        assert "title" in article
        assert "source" in article
        assert article["source"] == "pubmed"


@pytest.mark.asyncio
async def test_get_article_details(pubmed_client):
    """Test retrieving article details by PMID."""
    # Use known PMID for reproducibility
    pmid = "32191689"  # Example PROMIS-29 paper

    details = await pubmed_client.get_article_details(pmid)

    assert details["pmid"] == pmid
    assert "title" in details
    assert "abstract" in details
    assert "authors" in details
    assert isinstance(details["authors"], list)
    assert "publication_date" in details


@pytest.mark.asyncio
async def test_validate_pmid(pubmed_client):
    """Test PMID validation."""
    # Valid PMID
    result = await pubmed_client.validate_pmid("32191689")
    assert result["valid_format"] is True
    assert result["exists"] is True

    # Invalid format
    result = await pubmed_client.validate_pmid("invalid")
    assert result["valid_format"] is False


@pytest.mark.asyncio
async def test_search_by_author(pubmed_client):
    """Test author-specific search."""
    results = await pubmed_client.search_by_author(
        author="Smith J",
        max_results=3
    )

    assert isinstance(results, list)
    assert len(results) <= 3


@pytest.mark.asyncio
async def test_export_citation(pubmed_client):
    """Test citation export in different formats."""
    pmid = "32191689"

    # Test BibTeX format
    bibtex = await pubmed_client.export_citation(pmid, format="bibtex")
    assert "@article{" in bibtex

    # Test APA format
    apa = await pubmed_client.export_citation(pmid, format="apa")
    assert isinstance(apa, str)
    assert len(apa) > 0


@pytest.mark.asyncio
async def test_batch_article_lookup(pubmed_client):
    """Test batch retrieval of multiple articles."""
    pmids = ["32191689", "30726282", "28129794"]

    results = await pubmed_client.batch_article_lookup(pmids)

    assert isinstance(results, list)
    assert len(results) == len(pmids)

    for article in results:
        assert "pmid" in article
        assert article["pmid"] in pmids


@pytest.mark.asyncio
async def test_get_similar_articles(pubmed_client):
    """Test finding similar articles."""
    pmid = "32191689"

    similar = await pubmed_client.get_similar_articles(pmid, max_results=5)

    assert isinstance(similar, list)
    assert len(similar) <= 5

    # Original article shouldn't be in similar results
    for article in similar:
        assert article["pmid"] != pmid
