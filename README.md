# Zotero Comfort

High-level Zotero MCP integration with smart research workflows.

## Overview

Zotero Comfort provides two layers of functionality:

**A) Proxy Layer** - Direct re-exposure of [54yyyu/zotero-mcp](https://github.com/54yyyu/zotero-mcp) tools with a clean Python API.

**B) Smart Workflows** - High-level orchestrations for common research tasks.

## Installation

```bash
pip install zotero-comfort
```

Or with Docker:

```bash
docker build -t zotero-comfort .
docker run -e ZOTERO_API_KEY=xxx -e ZOTERO_LIBRARY_ID=123 zotero-comfort
```

## Configuration

Set environment variables:

```bash
export ZOTERO_API_KEY="your-api-key"
export ZOTERO_LIBRARY_ID="your-library-id"
export ZOTERO_LIBRARY_TYPE="group"  # or "user"
```

## Usage

### As Python Library

```python
from zotero_comfort import ZoteroProxy, ZoteroWorkflows

# Proxy layer - direct tool access
proxy = ZoteroProxy()
papers = proxy.search_papers("FHIR interoperability", limit=20)
metadata = proxy.get_metadata("ABC12345")

# Smart workflows - high-level operations
workflows = ZoteroWorkflows()
reading_list = workflows.build_reading_list("clinical NLP", max_papers=15)
result = workflows.smart_add_paper("10.1234/example.2024")
bibtex = workflows.export_bibliography(collection_name="FHIR")
```

### As MCP Server

Add to your Claude configuration:

```json
{
  "mcpServers": {
    "zotero-comfort": {
      "command": "zotero-comfort",
      "env": {
        "ZOTERO_API_KEY": "your-key",
        "ZOTERO_LIBRARY_ID": "your-library-id"
      }
    }
  }
}
```

## Available Tools

### Proxy Layer (A)

| Tool | Description |
|------|-------------|
| `zotero_search` | Search papers by keyword |
| `zotero_get_metadata` | Get paper details |
| `zotero_list_collections` | List all collections |
| `zotero_get_collection_items` | Get items in collection |
| `zotero_get_fulltext` | Get paper full text |
| `zotero_semantic_search` | AI-powered semantic search |

### Smart Workflows (B)

| Tool | Description |
|------|-------------|
| `build_reading_list` | Create curated topic reading list |
| `smart_add_paper` | Add paper with duplicate check |
| `export_bibliography` | Export as BibTeX |
| `find_related_papers` | Find semantically similar papers |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/
```

## License

MIT
