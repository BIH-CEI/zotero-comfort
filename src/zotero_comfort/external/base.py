"""
Abstract base class for external literature sources.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class ExternalSource(ABC):
    """
    Abstract interface for external literature sources.

    All sources (PubMed, arXiv, etc.) implement this interface
    for consistent orchestration.
    """

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 100,
        **kwargs
    ) -> List[Dict]:
        """
        Search for papers.

        Args:
            query: Search query string
            max_results: Maximum papers to return
            **kwargs: Source-specific parameters

        Returns:
            List of paper dicts with standardized fields:
            - id: Source-specific ID (PMID, arXiv ID, etc.)
            - title: Paper title
            - abstract: Abstract text
            - authors: List of author names
            - publication_date: Date string
            - doi: DOI if available
            - url: Link to paper
            - source: Source name ("pubmed", "arxiv")
        """
        pass

    @abstractmethod
    async def get_details(self, paper_id: str) -> Dict:
        """
        Get full details for a specific paper.

        Args:
            paper_id: Source-specific paper ID

        Returns:
            Paper dict with full metadata
        """
        pass

    def normalize_paper(self, raw_paper: Dict) -> Dict:
        """
        Normalize source-specific paper format to standard format.

        This is a helper method that subclasses can override
        to transform their native format to the standard format.
        """
        return raw_paper
