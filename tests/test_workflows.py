"""Tests for smart workflows."""

import pytest
from unittest.mock import MagicMock, patch

from zotero_comfort.workflows import ZoteroWorkflows


class TestZoteroWorkflows:
    """Test smart workflow orchestrations."""

    def test_suggest_collection_fhir(self):
        """Test collection suggestion for FHIR papers."""
        workflows = ZoteroWorkflows.__new__(ZoteroWorkflows)
        workflows.client = MagicMock()

        assert workflows._suggest_collection("FHIR Implementation Guide") == "FHIR"
        assert workflows._suggest_collection("HL7 Standards") == "FHIR"

    def test_suggest_collection_terminology(self):
        """Test collection suggestion for terminology papers."""
        workflows = ZoteroWorkflows.__new__(ZoteroWorkflows)
        workflows.client = MagicMock()

        assert workflows._suggest_collection("SNOMED CT Mapping") == "Terminology"
        assert workflows._suggest_collection("LOINC Codes") == "Terminology"

    def test_suggest_collection_ml(self):
        """Test collection suggestion for ML papers."""
        workflows = ZoteroWorkflows.__new__(ZoteroWorkflows)
        workflows.client = MagicMock()

        assert workflows._suggest_collection("Deep Learning for NER") == "ML"
        assert workflows._suggest_collection("Machine Learning Approaches") == "ML"

    def test_suggest_collection_default(self):
        """Test default collection for unmatched titles."""
        workflows = ZoteroWorkflows.__new__(ZoteroWorkflows)
        workflows.client = MagicMock()

        assert workflows._suggest_collection("Random Title") == "Uncategorized"

    def test_normalize_doi(self):
        """Test DOI normalization."""
        workflows = ZoteroWorkflows.__new__(ZoteroWorkflows)
        workflows.client = MagicMock()

        assert workflows._normalize_doi("10.1234/test") == "10.1234/test"
        assert workflows._normalize_doi("https://doi.org/10.1234/test") == "10.1234/test"
        assert workflows._normalize_doi("doi:10.1234/test") == "10.1234/test"
        assert workflows._normalize_doi("invalid") is None

    def test_extract_year(self):
        """Test year extraction from date strings."""
        workflows = ZoteroWorkflows.__new__(ZoteroWorkflows)
        workflows.client = MagicMock()

        assert workflows._extract_year("2024-01-15") == 2024
        assert workflows._extract_year("2023") == 2023
        assert workflows._extract_year("January 2022") == 2022
        assert workflows._extract_year("") == 0

    def test_format_creators(self):
        """Test creator formatting."""
        workflows = ZoteroWorkflows.__new__(ZoteroWorkflows)
        workflows.client = MagicMock()

        creators = [
            {"lastName": "Smith"},
            {"lastName": "Jones"},
        ]
        assert workflows._format_creators(creators) == "Smith, Jones"

        many_creators = [
            {"lastName": "A"},
            {"lastName": "B"},
            {"lastName": "C"},
            {"lastName": "D"},
        ]
        assert workflows._format_creators(many_creators) == "A, B, C et al."

        assert workflows._format_creators([]) == ""

    def test_build_reading_list(self):
        """Test reading list building."""
        workflows = ZoteroWorkflows.__new__(ZoteroWorkflows)
        workflows.client = MagicMock()
        workflows.client.search_items.return_value = [
            {"key": "A1", "title": "Paper 1", "date": "2024", "creators": []},
            {"key": "A2", "title": "Paper 2", "date": "2023", "creators": []},
        ]

        result = workflows.build_reading_list("FHIR", max_papers=10)

        assert result["topic"] == "FHIR"
        assert result["papers_found"] == 2
        assert result["papers_included"] == 2
        assert len(result["papers"]) == 2

    def test_smart_add_paper_invalid_doi(self):
        """Test smart add with invalid DOI."""
        workflows = ZoteroWorkflows.__new__(ZoteroWorkflows)
        workflows.client = MagicMock()

        result = workflows.smart_add_paper("invalid-doi")

        assert result["status"] == "error"
        assert "Invalid DOI" in result["message"]

    def test_smart_add_paper_duplicate(self):
        """Test smart add detecting duplicate."""
        workflows = ZoteroWorkflows.__new__(ZoteroWorkflows)
        workflows.client = MagicMock()
        workflows.client.search_items.return_value = [
            {"key": "ABC", "title": "Existing Paper", "DOI": "10.1234/test"}
        ]

        result = workflows.smart_add_paper("10.1234/test")

        assert result["status"] == "duplicate"
        assert result["duplicate_key"] == "ABC"

    def test_to_bibtex(self):
        """Test BibTeX generation."""
        workflows = ZoteroWorkflows.__new__(ZoteroWorkflows)
        workflows.client = MagicMock()

        paper = {
            "key": "TEST123",
            "title": "Test Paper",
            "itemType": "journalArticle",
            "creators": [
                {"firstName": "John", "lastName": "Smith", "creatorType": "author"}
            ],
            "date": "2024",
            "publicationTitle": "Test Journal",
            "DOI": "10.1234/test",
        }

        bibtex = workflows._to_bibtex(paper)

        assert "@article{TEST123," in bibtex
        assert "title = {Test Paper}" in bibtex
        assert "author = {Smith, John}" in bibtex
        assert "year = {2024}" in bibtex
        assert "doi = {10.1234/test}" in bibtex
