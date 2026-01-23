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

    def test_add_items_to_collection(self):
        """Test adding items to collection proxy."""
        proxy = ZoteroProxy.__new__(ZoteroProxy)
        proxy.client = MagicMock()
        proxy.client.add_items_to_collection.return_value = {
            "status": "success",
            "added": 2,
            "failed": 0,
            "details": [
                {"item_key": "ITEM1", "status": "added"},
                {"item_key": "ITEM2", "status": "added"},
            ],
        }

        result = proxy.add_items_to_collection("COLL1", ["ITEM1", "ITEM2"])

        proxy.client.add_items_to_collection.assert_called_once_with("COLL1", ["ITEM1", "ITEM2"])
        assert result["status"] == "success"
        assert result["added"] == 2
        assert len(result["details"]) == 2

    def test_remove_item_from_collection(self):
        """Test removing item from collection proxy."""
        proxy = ZoteroProxy.__new__(ZoteroProxy)
        proxy.client = MagicMock()
        proxy.client.remove_item_from_collection.return_value = {
            "status": "success",
            "item_key": "ITEM1",
            "collection_key": "COLL1",
        }

        result = proxy.remove_item_from_collection("COLL1", "ITEM1")

        proxy.client.remove_item_from_collection.assert_called_once_with("COLL1", "ITEM1")
        assert result["status"] == "success"
        assert result["item_key"] == "ITEM1"
