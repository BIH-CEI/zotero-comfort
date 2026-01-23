"""
External literature sources for zotero-comfort.

Provides direct API access to:
- PubMed (via NCBI E-utilities / Biopython)
- arXiv (via arXiv API)

These sources can be orchestrated with Zotero for complete research workflows.
"""

from .base import ExternalSource
from .pubmed import PubMedClient
from .arxiv import ArXivClient, ARXIV_CATEGORIES

__all__ = ["ExternalSource", "PubMedClient", "ArXivClient", "ARXIV_CATEGORIES"]
