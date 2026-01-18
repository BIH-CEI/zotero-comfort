FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install zotero-mcp (the underlying MCP server)
RUN pip install --no-cache-dir zotero-mcp

# Copy and install zotero-comfort
COPY pyproject.toml .
COPY src/ src/

# Install mcp dependency first (required for editable install)
RUN pip install --no-cache-dir mcp>=1.0.0

RUN pip install --no-cache-dir -e .

# Environment variables (override at runtime)
# Group library (default for shared team library)
ENV ZOTERO_GROUP_LIBRARY_ID=""
ENV ZOTERO_GROUP_API_KEY=""
# Personal library (user's own library)
ENV ZOTERO_PERSONAL_LIBRARY_ID=""
ENV ZOTERO_PERSONAL_API_KEY=""
# Backwards compatibility (fallback for group library)
ENV ZOTERO_LIBRARY_ID=""
ENV ZOTERO_API_KEY=""

# Run the MCP server
ENTRYPOINT ["zotero-comfort"]
