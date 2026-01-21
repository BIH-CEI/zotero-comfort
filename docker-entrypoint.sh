#!/bin/bash
set -e

# Validate required environment variables
if [ -z "$ZOTERO_API_KEY" ]; then
    echo "ERROR: ZOTERO_API_KEY not set"
    exit 1
fi

if [ -z "$ZOTERO_LIBRARY_ID" ]; then
    echo "ERROR: ZOTERO_LIBRARY_ID not set"
    exit 1
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
