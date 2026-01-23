# Arena MCP Server

MCP server that wraps Arena PLM's REST API, enabling Claude to search and retrieve part information.

## Quick Start

```bash
docker compose up
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ARENA_EMAIL` | Yes | Arena login email |
| `ARENA_PASSWORD` | Yes | Arena login password |
| `ARENA_WORKSPACE_ID` | No | Workspace ID (uses default if not set) |
| `MCP_API_KEY` | Yes | API key for authentication (min 32 chars) |
| `MCP_HOST` | No | Host to bind (default: `0.0.0.0`) |
| `MCP_PORT` | No | Port to bind (default: `8080`) |

## Available Tools

- `search_items` - Search parts by name, number, or description
- `get_item` - Get full details for an item by GUID
- `get_item_bom` - Get bill of materials for an assembly
- `get_item_where_used` - Find assemblies containing a part
- `get_item_revisions` - Get revision history
- `get_item_files` - Get associated files
- `get_item_sourcing` - Get supplier information
- `get_categories` - List item categories
