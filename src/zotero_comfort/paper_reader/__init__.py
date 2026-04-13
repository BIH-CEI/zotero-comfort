"""
Paper Reader module for zotero-comfort.

Provides three access layers for academic paper management:
1. Local Connector (port 23119) — Zotero Desktop integration with auto PDF
2. Web API utilities — notes, collections, DOI import via Crossref
3. Direct PDF download — Unpaywall, PMC, DOI direct, Playwright fallback
"""

from .download import download, batch_download
from .local_connector import ping, save_by_doi, batch_save_dois, get_selected_collection
from .utils import get_pdf_path, post_note, list_collection, import_doi, create_collection

__all__ = [
    "download",
    "batch_download",
    "ping",
    "save_by_doi",
    "batch_save_dois",
    "get_selected_collection",
    "get_pdf_path",
    "post_note",
    "list_collection",
    "import_doi",
    "create_collection",
]
