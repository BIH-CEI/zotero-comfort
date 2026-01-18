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

RUN pip install --no-cache-dir -e .

# Environment variables (override at runtime)
ENV ZOTERO_LIBRARY_ID=""
ENV ZOTERO_LIBRARY_TYPE="group"
ENV ZOTERO_API_KEY=""

# Run the MCP server
ENTRYPOINT ["zotero-comfort"]
