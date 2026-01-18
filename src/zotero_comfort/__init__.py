"""
Zotero Comfort - High-level Zotero MCP integration.

Provides three layers:
A) Proxy Layer - Direct re-exposure of 54yyyu/zotero-mcp tools
B) Smart Workflows - High-level research automation
C) Dual Library - Group and personal library management
"""

from .client import ZoteroMCPClient, DualLibraryClient
from .proxy import ZoteroProxy
from .workflows import ZoteroWorkflows

__version__ = "0.1.0"
__all__ = ["ZoteroMCPClient", "DualLibraryClient", "ZoteroProxy", "ZoteroWorkflows"]
