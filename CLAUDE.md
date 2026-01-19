# Arena PLM MCP Server

## Project Overview
MCP server that wraps Arena PLM's REST API, enabling Claude to search and retrieve part information via natural language.

## Architecture

```
Claude Code / Slackbot → MCP Server (stdio) → Arena PLM API
```

### Current Phase: Phase 1 (Native Search)
- Direct API wrapper exposing Arena's search as MCP tools
- Claude handles query interpretation, MCP handles API calls

### Future: Phase 2 (Semantic Search)
- Add vector DB (Chroma/pgvector) for embedding-based search
- Sync job to index parts from Arena
- New tool: `search_items_semantic(query: string)`

## Project Structure

```
arena-mcp-server/
├── src/
│   └── arena_mcp_server/
│       ├── __init__.py
│       ├── server.py          # MCP server + tool definitions
│       └── arena_client.py    # Arena API wrapper (auth, search)
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── CLAUDE.md
```

## Arena API Details

- **Base URL**: `https://api.arenasolutions.com/v1`
- **Auth**: POST `/login` with email/password → returns `arena_session_id`
- **Session Header**: `arena_session_id`
- **Wildcards**: `*` required for partial matches (automatically added by client)
- **Pagination**: `limit` (max 400), `offset`

## MCP Tools

### `search_items`
Search Arena parts by name, number, or description. Wildcards are added automatically for partial matching.

**Parameters:**
- `name` (string, optional): Part name filter
- `description` (string, optional): Description filter
- `number` (string, optional): Part number filter
- `category_guid` (string, optional): Category GUID filter (use `get_categories` to find GUIDs)
- `limit` (int, optional): Max results (default 20, max 400)

**Returns:** List of matching items with number, name, revision, lifecyclePhase, GUID, URL

---

### `get_item`
Get full details for a specific item by GUID.

**Parameters:**
- `guid` (string, required): Item GUID (obtain from `search_items`)

**Returns:** Complete item details including custom attributes

---

### `get_item_bom`
Get bill of materials (BOM) for an assembly item.

**Parameters:**
- `guid` (string, required): Item GUID of the assembly

**Returns:** List of child components with quantities, line numbers, and reference designators

---

### `get_item_where_used`
Find all assemblies where a given item is used as a component. Useful for impact analysis.

**Parameters:**
- `guid` (string, required): Item GUID to find usage of

**Returns:** List of parent assemblies with line numbers and quantities

---

### `get_item_revisions`
Get all revisions of an item including working, effective, and superseded revisions.

**Parameters:**
- `guid` (string, required): Item GUID

**Returns:** List of revisions with status (Working/Effective/Superseded), lifecycle phase, and change order info

---

### `get_item_files`
Get all files associated with an item (drawings, datasheets, etc.).

**Parameters:**
- `guid` (string, required): Item GUID

**Returns:** List of file associations with name, format, edition, and primary flag

---

### `get_item_sourcing`
Get supplier/sourcing information for an item including approved manufacturers and vendors.

**Parameters:**
- `guid` (string, required): Item GUID
- `limit` (int, optional): Max results (default 20, max 400)

**Returns:** List of source relationships with approval status and production/prototype flags

---

### `get_categories`
Get available item categories. Use category GUIDs to filter `search_items` results.

**Parameters:**
- `path` (string, optional): Filter by category path prefix (e.g., `item\Assembly`)

**Returns:** List of categories with path, GUID, and assignable flag

---

## Recommended Workflows

### Finding a part by description
1. `search_items(description="...")` → get matching items with GUIDs
2. `get_item(guid)` → get full details for the best match
3. `get_item_where_used(guid)` → verify it's used in expected assemblies

### Finding components in an assembly
1. `search_items(name="assembly name")` → find the assembly
2. `get_item_bom(guid)` → list all components
3. `get_item(component_guid)` → get details on specific components

### Impact analysis (what uses this part?)
1. `search_items(number="part-number")` → find the part
2. `get_item_where_used(guid)` → find all parent assemblies
3. Optionally: `get_item_where_used(parent_guid)` → trace up the hierarchy

### Finding parts by category
1. `get_categories(path="item\\...")` → find category GUIDs
2. `search_items(category_guid="...", description="...")` → narrow search to category

### Checking part history
1. `search_items(number="...")` → find the part
2. `get_item_revisions(guid)` → see all revisions and change orders
3. `get_item_files(guid)` → find associated documentation

---

## Running Locally

```bash
# Build
docker build -t arena-mcp-server .

# Run (stdio mode for MCP)
docker run -i --rm \
  -e ARENA_EMAIL=your-email \
  -e ARENA_PASSWORD=your-pass \
  -e ARENA_WORKSPACE_ID=your-workspace \
  arena-mcp-server
```

## Claude Code Config

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "arena-plm": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "ARENA_EMAIL", "-e", "ARENA_PASSWORD", "-e", "ARENA_WORKSPACE_ID", "arena-mcp-server"],
      "env": {
        "ARENA_EMAIL": "...",
        "ARENA_PASSWORD": "...",
        "ARENA_WORKSPACE_ID": "..."
      }
    }
  }
}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ARENA_EMAIL` | Yes | Arena login email |
| `ARENA_PASSWORD` | Yes | Arena login password |
| `ARENA_WORKSPACE_ID` | No | Arena workspace ID (uses default workspace if not set) |

> Note: API base URL is currently hardcoded to `https://api.arenasolutions.com/v1` in `arena_client.py`

## Development Notes

- Server uses **stdio** transport for MCP communication
- Authentication is lazy — client authenticates on first tool call
- Global client instance is reused across tool calls
- Wildcards (`*value*`) are automatically wrapped around search terms

### Known Limitations
- Session expiration handling not implemented — currently errors on expired session
- No retry logic for rate limiting

## Testing

```bash
# Test MCP connection
claude --mcp-debug

# In Claude Code
/mcp  # Should list arena-plm

# Test search
"Search for parts with 'bezel' in the name"
```

## Future Enhancements (Phase 2)

1. Add `vector_store.py` — Chroma/pgvector integration
2. Add `sync_job.py` — periodic Arena → vector DB sync
3. New tool: `search_items_semantic(query)` — embedding-based search
4. Keep `arena_client.py` decoupled for reuse
