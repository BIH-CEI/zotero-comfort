"""
External literature sources for zotero-comfort.

Provides direct API access to:
- PubMed (via NCBI E-utilities / Biopython)
- arXiv (via arXiv API)
- Charité Forschungsdatenbank (via Playwright headless browser)

These sources can be orchestrated with Zotero for complete research workflows.
"""

from .arxiv import ARXIV_CATEGORIES, ArXivClient
from .base import ExternalSource
from .charite import CEIR_TEAM, ChariteClient, TeamMember
from .pubmed import PubMedClient

__all__ = [
    "ExternalSource",
    "PubMedClient",
    "ArXivClient",
    "ARXIV_CATEGORIES",
    "ChariteClient",
    "CEIR_TEAM",
    "TeamMember",
]
