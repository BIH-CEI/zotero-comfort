FROM python:3.11-slim

# Build arguments (injected by GitHub Actions via secrets)
ARG ZOTERO_GROUP=""
ARG ZOTERO_GROUP_API=""

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

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

# Environment variables for Zotero API
# Injected at build-time from GitHub Secrets via docker build --build-arg
ENV ZOTERO_API_KEY=${ZOTERO_GROUP_API}
ENV ZOTERO_LIBRARY_ID=${ZOTERO_GROUP}
ENV ZOTERO_LIBRARY_TYPE="group"
ENV LOG_LEVEL="info"

# Health check (simple Python check to verify server is importable)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import zotero_comfort.server; print('healthy')" || exit 1

# MCP server runs over stdio
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["zotero-comfort"]
