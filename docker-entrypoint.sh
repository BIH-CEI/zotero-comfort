#!/bin/bash
set -e

# Load secrets from Docker Secrets mount point if available
# Docker Secrets are mounted at /run/secrets/
# Supports both single-library and dual-library configurations

# Group Library Secrets
if [ -f "/run/secrets/zotero_group_library_id" ]; then
    export ZOTERO_GROUP_LIBRARY_ID=$(cat /run/secrets/zotero_group_library_id)
    echo "Loaded ZOTERO_GROUP_LIBRARY_ID from Docker Secret"
fi

if [ -f "/run/secrets/zotero_group_api_key" ]; then
    export ZOTERO_GROUP_API_KEY=$(cat /run/secrets/zotero_group_api_key)
    echo "Loaded ZOTERO_GROUP_API_KEY from Docker Secret"
fi

# Personal Library Secrets
if [ -f "/run/secrets/zotero_personal_library_id" ]; then
    export ZOTERO_PERSONAL_LIBRARY_ID=$(cat /run/secrets/zotero_personal_library_id)
    echo "Loaded ZOTERO_PERSONAL_LIBRARY_ID from Docker Secret"
fi

if [ -f "/run/secrets/zotero_personal_api_key" ]; then
    export ZOTERO_PERSONAL_API_KEY=$(cat /run/secrets/zotero_personal_api_key)
    echo "Loaded ZOTERO_PERSONAL_API_KEY from Docker Secret"
fi

# Legacy single-library secrets (backwards compatibility)
if [ -f "/run/secrets/zotero_library_id" ] && [ -z "$ZOTERO_GROUP_LIBRARY_ID" ]; then
    export ZOTERO_GROUP_LIBRARY_ID=$(cat /run/secrets/zotero_library_id)
    echo "Loaded ZOTERO_GROUP_LIBRARY_ID from legacy secret"
fi

if [ -f "/run/secrets/zotero_api_key" ] && [ -z "$ZOTERO_GROUP_API_KEY" ]; then
    export ZOTERO_GROUP_API_KEY=$(cat /run/secrets/zotero_api_key)
    echo "Loaded ZOTERO_GROUP_API_KEY from legacy secret"
fi

# Validate required environment variables
# At minimum need group library for CEI_Publications
if [ -z "$ZOTERO_GROUP_LIBRARY_ID" ] && [ -z "$ZOTERO_LIBRARY_ID" ]; then
    echo "ERROR: ZOTERO_GROUP_LIBRARY_ID not set (via env var or Docker Secret)"
    exit 1
fi

if [ -z "$ZOTERO_GROUP_API_KEY" ] && [ -z "$ZOTERO_API_KEY" ]; then
    echo "ERROR: ZOTERO_GROUP_API_KEY not set (via env var or Docker Secret)"
    exit 1
fi

# Personal library is optional (enables user's personal library access)
if [ -n "$ZOTERO_PERSONAL_LIBRARY_ID" ] || [ -n "$ZOTERO_PERSONAL_API_KEY" ]; then
    if [ -z "$ZOTERO_PERSONAL_LIBRARY_ID" ] || [ -z "$ZOTERO_PERSONAL_API_KEY" ]; then
        echo "WARNING: Both ZOTERO_PERSONAL_LIBRARY_ID and ZOTERO_PERSONAL_API_KEY must be set together"
    fi
fi

# Run tests if TEST_MODE=1
if [ "$TEST_MODE" = "1" ]; then
    echo "Running test suite..."
    pytest tests/ -v
    if [ $? -ne 0 ]; then
        echo "Tests failed!"
        exit 1
    fi
fi

# Start MCP server
exec "$@"
