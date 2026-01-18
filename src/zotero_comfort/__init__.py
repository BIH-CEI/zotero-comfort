"""
Zotero Comfort - High-level Zotero MCP integration.

Provides two layers:
A) Proxy Layer - Direct re-exposure of 54yyyu/zotero-mcp tools
B) Smart Workflows - High-level research automation
"""

from .client import ZoteroMCPClient
from .proxy import ZoteroProxy
from .workflows import ZoteroWorkflows

__version__ = "0.1.0"
__all__ = ["ZoteroMCPClient", "ZoteroProxy", "ZoteroWorkflows"]
