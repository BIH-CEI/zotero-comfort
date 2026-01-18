"""Tests for proxy layer."""

import pytest
from unittest.mock import MagicMock

from zotero_comfort.proxy import ZoteroProxy


class TestZoteroProxy:
    """Test proxy layer methods."""

    def test_search_papers(self):
        """Test paper search proxy."""
        proxy = ZoteroProxy.__new__(ZoteroProxy)
        proxy.client = MagicMock()
        proxy.client.search_items.return_value = [
            {"key": "A1", "title": "Paper 1"},
            {"key": "A2", "title": "Paper 2"},
        ]

        result = proxy.search_papers("test query", limit=10)

        proxy.client.search_items.assert_called_once_with("test query", limit=10)
        assert len(result) == 2
        assert result[0]["title"] == "Paper 1"

    def test_get_metadata(self):
        """Test metadata retrieval proxy."""
        proxy = ZoteroProxy.__new__(ZoteroProxy)
        proxy.client = MagicMock()
        proxy.client.get_item.return_value = {
            "key": "ABC",
            "title": "Test Paper",
            "DOI": "10.1234/test",
        }

        result = proxy.get_metadata("ABC")

        proxy.client.get_item.assert_called_once_with("ABC")
        assert result["title"] == "Test Paper"

    def test_list_collections(self):
        """Test collection listing proxy."""
        proxy = ZoteroProxy.__new__(ZoteroProxy)
        proxy.client = MagicMock()
        proxy.client.list_collections.return_value = [
            {"key": "C1", "name": "Collection 1"},
            {"key": "C2", "name": "Collection 2"},
        ]

        result = proxy.list_collections()

        assert len(result) == 2
        assert result[0]["name"] == "Collection 1"

    def test_semantic_search(self):
        """Test semantic search proxy."""
        proxy = ZoteroProxy.__new__(ZoteroProxy)
        proxy.client = MagicMock()
        proxy.client.semantic_search.return_value = [
            {"key": "S1", "title": "Similar Paper 1"},
        ]

        result = proxy.semantic_search("clinical NLP", limit=5)

        proxy.client.semantic_search.assert_called_once_with("clinical NLP", limit=5)
        assert len(result) == 1
