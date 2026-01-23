# Arena MCP Server

MCP server wrapping Arena PLM's REST API.

## Structure

```
src/arena_mcp_server/
├── server.py        # MCP server, tools, auth (APIKeyVerifier)
└── arena_client.py  # Arena API client (httpx, session auth)
```

## Run

```bash
docker compose up
```

## Config

Environment variables in `.env`:
- `ARENA_EMAIL`, `ARENA_PASSWORD` - Arena credentials (required)
- `ARENA_WORKSPACE_ID` - Workspace ID (optional)
- `MCP_API_KEY` - API key for MCP auth (required, min 32 chars)
- `MCP_HOST`, `MCP_PORT` - Server binding (default: `0.0.0.0:8080`)

## Arena API Notes

- Base URL: `https://api.arenasolutions.com/v1`
- Auth: POST `/login` returns `arena_session_id` header
- Wildcards (`*`) required for partial matches (client adds automatically)
- Pagination: `limit` (max 400), `offset`
