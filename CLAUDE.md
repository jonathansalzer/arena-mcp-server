# Arena MCP Server

MCP server wrapping Arena PLM's REST API.

## Commands

```bash
docker compose up          # Run server
docker compose up --build  # Rebuild and run
```

## Structure

- `server.py` - MCP tools and auth (`APIKeyVerifier` subclasses `TokenVerifier`)
- `arena_client.py` - Arena REST client (httpx, session-based auth)

## Environment

Required in `.env`:
- `ARENA_EMAIL`, `ARENA_PASSWORD`
- `MCP_API_KEY` (min 32 chars, server denies all access if unset)

Optional: `ARENA_WORKSPACE_ID`, `MCP_HOST`, `MCP_PORT`

## Gotchas

- Arena API requires `*wildcards*` for partial matches - `arena_client.py` adds them automatically
- No session refresh on expiry - will error, needs re-auth
- No rate limit retry logic
- Auth is lazy (first tool call), not at startup
