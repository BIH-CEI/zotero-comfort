FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
COPY src/ src/
COPY README.md .

RUN pip install --no-cache-dir .

# Environment variables for Zotero API
ENV ZOTERO_API_KEY=""
ENV ZOTERO_LIBRARY_ID=""
ENV ZOTERO_LIBRARY_TYPE="group"

# MCP server runs over stdio
ENTRYPOINT ["zotero-comfort"]
