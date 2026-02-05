FROM python:3.11-slim

WORKDIR /app

# Install system dependencies + Node.js (for upstream zotero-mcp)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install upstream zotero-mcp (54yyyu/zotero-mcp) - Node.js MCP server
# Vendored with node_modules from ceir-zotero-mcp container
COPY vendor/zotero-mcp/ /opt/zotero-mcp/
RUN printf '#!/bin/bash\nnode /opt/zotero-mcp/server.js "$@"\n' > /usr/local/bin/zotero-mcp && \
    chmod +x /usr/local/bin/zotero-mcp

# Copy project files
COPY pyproject.toml uv.lock* ./
COPY src/ src/
COPY tests/ tests/
COPY README.md .

# Install dependencies with pip (uv available but pip is fine for production)
RUN pip install --no-cache-dir . pytest pytest-asyncio

# Copy entrypoint script
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

# Environment variables for Zotero API (set at runtime via docker-compose or docker run)
ENV ZOTERO_API_KEY=""
ENV ZOTERO_LIBRARY_ID=""
ENV ZOTERO_LIBRARY_TYPE="group"
ENV LOG_LEVEL="info"

# Health check (simple Python check to verify server is importable)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import zotero_comfort.server; print('healthy')" || exit 1

# MCP server runs over stdio
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["zotero-comfort"]
