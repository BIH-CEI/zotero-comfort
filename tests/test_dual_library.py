"""Tests for dual library client."""

import pytest
from unittest.mock import MagicMock, patch
import os

from zotero_comfort.client import DualLibraryClient, ZoteroMCPClient


class TestDualLibraryClient:
    """Test dual library client functionality."""

    def test_library_status_both_configured(self):
        """Test library status when both libraries are configured."""
        with patch.dict(os.environ, {
            "ZOTERO_GROUP_LIBRARY_ID": "12345",
            "ZOTERO_GROUP_API_KEY": "group_key",
            "ZOTERO_PERSONAL_LIBRARY_ID": "67890",
            "ZOTERO_PERSONAL_API_KEY": "personal_key",
        }, clear=False):
            client = DualLibraryClient()
            status = client.get_library_status()

            assert status["group"]["configured"] is True
            assert status["group"]["library_id"] == "12345"
            assert status["personal"]["configured"] is True
            assert status["personal"]["library_id"] == "67890"
            assert status["default"] == "group"

    def test_library_status_only_group(self):
        """Test library status when only group library is configured."""
        with patch.dict(os.environ, {
            "ZOTERO_GROUP_LIBRARY_ID": "12345",
            "ZOTERO_GROUP_API_KEY": "group_key",
        }, clear=True):
            client = DualLibraryClient()
            status = client.get_library_status()

            assert status["group"]["configured"] is True
            assert status["personal"]["configured"] is False

    def test_backwards_compatibility(self):
        """Test that old env vars work as fallback for group library."""
        with patch.dict(os.environ, {
            "ZOTERO_LIBRARY_ID": "legacy_id",
            "ZOTERO_API_KEY": "legacy_key",
        }, clear=True):
            client = DualLibraryClient()
            status = client.get_library_status()

            assert status["group"]["configured"] is True
            assert status["group"]["library_id"] == "legacy_id"

    def test_set_default_library(self):
        """Test setting default library."""
        with patch.dict(os.environ, {
            "ZOTERO_GROUP_LIBRARY_ID": "12345",
            "ZOTERO_GROUP_API_KEY": "group_key",
            "ZOTERO_PERSONAL_LIBRARY_ID": "67890",
            "ZOTERO_PERSONAL_API_KEY": "personal_key",
        }, clear=False):
            client = DualLibraryClient()

            assert client._default_library == "group"
            client.set_default_library("personal")
            assert client._default_library == "personal"

    def test_set_invalid_library_raises(self):
        """Test that setting invalid library raises ValueError."""
        client = DualLibraryClient.__new__(DualLibraryClient)

        with pytest.raises(ValueError):
            client.set_default_library("invalid")

    def test_get_client_raises_when_not_configured(self):
        """Test that getting unconfigured library raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            client = DualLibraryClient()

            with pytest.raises(ValueError, match="Group library not configured"):
                client.get_client("group")

            with pytest.raises(ValueError, match="Personal library not configured"):
                client.get_client("personal")
