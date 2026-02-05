#!/usr/bin/env node
/**
 * Zotero MCP Server - Direct Web API integration
 *
 * Simple MCP server that calls Zotero Web API directly.
 * No complex dependencies, just works.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

// Configuration from environment
const ZOTERO_API_KEY = process.env.ZOTERO_API_KEY;
const ZOTERO_LIBRARY_ID = process.env.ZOTERO_LIBRARY_ID;
const ZOTERO_LIBRARY_TYPE = process.env.ZOTERO_LIBRARY_TYPE || 'group';
const ZOTERO_API_BASE = 'https://api.zotero.org';

function getApiPrefix() {
  if (ZOTERO_LIBRARY_TYPE === 'group') {
    return `${ZOTERO_API_BASE}/groups/${ZOTERO_LIBRARY_ID}`;
  }
  return `${ZOTERO_API_BASE}/users/${ZOTERO_LIBRARY_ID}`;
}

async function zoteroRequest(endpoint, params = {}) {
  const url = new URL(`${getApiPrefix()}${endpoint}`);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined) url.searchParams.set(k, v);
  });

  const response = await fetch(url, {
    headers: {
      'Zotero-API-Key': ZOTERO_API_KEY,
      'Zotero-API-Version': '3',
    },
  });

  if (!response.ok) {
    throw new Error(`Zotero API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// Tool definitions
const TOOLS = [
  {
    name: 'search_papers',
    description: 'Search for papers in Zotero library by keyword',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Search query (e.g., "FHIR terminology")' },
        limit: { type: 'integer', description: 'Maximum results to return (default: 50)', default: 50 },
      },
      required: ['query'],
    },
  },
  {
    name: 'get_paper_metadata',
    description: 'Get detailed metadata for a specific paper',
    inputSchema: {
      type: 'object',
      properties: {
        item_key: { type: 'string', description: 'Zotero item key' },
      },
      required: ['item_key'],
    },
  },
  {
    name: 'list_collections',
    description: 'List all collections in the Zotero library',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'get_collection_items',
    description: 'Get all items in a specific collection',
    inputSchema: {
      type: 'object',
      properties: {
        collection_key: { type: 'string', description: 'Collection key' },
      },
      required: ['collection_key'],
    },
  },
  {
    name: 'export_collection_bibtex',
    description: 'Export a collection as BibTeX for citations',
    inputSchema: {
      type: 'object',
      properties: {
        collection_key: { type: 'string', description: 'Collection key to export' },
      },
      required: ['collection_key'],
    },
  },
];

// Tool handlers
async function handleSearchPapers(args) {
  const { query, limit = 50 } = args;
  const items = await zoteroRequest('/items', { q: query, limit, format: 'json' });

  const papers = items.map(item => ({
    key: item.key,
    title: item.data.title || 'Untitled',
    creators: (item.data.creators || []).map(c =>
      c.name || `${c.firstName || ''} ${c.lastName || ''}`.trim()
    ).join(', '),
    date: item.data.date || '',
    itemType: item.data.itemType,
    DOI: item.data.DOI || '',
  }));

  return `Found ${papers.length} papers matching "${query}":\n\n` +
    papers.map(p => `- **${p.title}** (${p.date})\n  ${p.creators}\n  Key: ${p.key}`).join('\n\n');
}

async function handleGetPaperMetadata(args) {
  const { item_key } = args;
  const item = await zoteroRequest(`/items/${item_key}`);

  return JSON.stringify(item.data, null, 2);
}

async function handleListCollections() {
  const collections = await zoteroRequest('/collections');

  if (collections.length === 0) {
    return 'No collections found in the library.';
  }

  const result = collections.map(c => ({
    key: c.key,
    name: c.data.name,
    parentCollection: c.data.parentCollection || null,
  }));

  return `Found ${result.length} collections:\n\n` +
    result.map(c => `- **${c.name}** (key: ${c.key})`).join('\n');
}

async function handleGetCollectionItems(args) {
  const { collection_key } = args;
  const items = await zoteroRequest(`/collections/${collection_key}/items`);

  const papers = items.map(item => ({
    key: item.key,
    title: item.data.title || 'Untitled',
    itemType: item.data.itemType,
  }));

  return `Found ${papers.length} items in collection:\n\n` +
    papers.map(p => `- ${p.title} (${p.itemType}, key: ${p.key})`).join('\n');
}

async function handleExportBibtex(args) {
  const { collection_key } = args;
  const url = new URL(`${getApiPrefix()}/collections/${collection_key}/items`);
  url.searchParams.set('format', 'bibtex');

  const response = await fetch(url, {
    headers: {
      'Zotero-API-Key': ZOTERO_API_KEY,
      'Zotero-API-Version': '3',
    },
  });

  if (!response.ok) {
    throw new Error(`Zotero API error: ${response.status}`);
  }

  return await response.text();
}

// Main server setup
class ZoteroMCPServer {
  constructor() {
    this.server = new Server(
      { name: 'zotero-mcp', version: '1.0.0' },
      { capabilities: { tools: {} } }
    );

    this.setupHandlers();
  }

  setupHandlers() {
    // List tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: TOOLS,
    }));

    // Call tool
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        let result;
        switch (name) {
          case 'search_papers':
            result = await handleSearchPapers(args);
            break;
          case 'get_paper_metadata':
            result = await handleGetPaperMetadata(args);
            break;
          case 'list_collections':
            result = await handleListCollections();
            break;
          case 'get_collection_items':
            result = await handleGetCollectionItems(args);
            break;
          case 'export_collection_bibtex':
            result = await handleExportBibtex(args);
            break;
          default:
            throw new Error(`Unknown tool: ${name}`);
        }

        return { content: [{ type: 'text', text: result }] };
      } catch (error) {
        return { content: [{ type: 'text', text: `Error: ${error.message}` }], isError: true };
      }
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Zotero MCP Server running on stdio');
  }
}

// Validate configuration
if (!ZOTERO_API_KEY || !ZOTERO_LIBRARY_ID) {
  console.error('Error: ZOTERO_API_KEY and ZOTERO_LIBRARY_ID must be set');
  process.exit(1);
}

const server = new ZoteroMCPServer();
server.run().catch(console.error);
