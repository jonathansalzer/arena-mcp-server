# Arena MCP Server

MCP server wrapping Arena PLM's REST API.

## Commands

```bash
docker compose up          # Run server
docker compose up --build  # Rebuild and run
```

## Structure

- `server.py` - MCP tools and Google OAuth 2.0 authentication
- `auth.py` - Custom authentication providers with domain restrictions
- `arena_client.py` - Arena REST client (httpx, session-based auth)

## Environment

Required in `.env`:
- `ARENA_EMAIL`, `ARENA_PASSWORD` - Arena PLM credentials

Google OAuth 2.0 (required for production):
- `FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID` - Google OAuth client ID (e.g., `123456789.apps.googleusercontent.com`)
- `FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET` - Google OAuth client secret (e.g., `GOCSPX-abc123...`)
- `FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL` - Public URL where this MCP server is accessible (for OAuth callbacks)

Optional:
- `ARENA_WORKSPACE_ID` (uses default workspace if not set)
- `MCP_TRANSPORT` (http or sse, defaults to http)
- `MCP_HOST` (defaults to 0.0.0.0)
- `MCP_PORT` (defaults to 8080)
- `DISABLE_AUTH=true` (disables auth for local development - use only locally)

## Authentication

The server uses **Google OAuth 2.0** for MCP client authentication, restricted to `@carbonrobotics.com` email addresses via `RestrictedGoogleProvider` (defined in `auth.py`).

**Domain Restriction:**
- Only users with `@carbonrobotics.com` email addresses can authenticate
- Enforcement happens at the token verification layer (server-side validation)
- The OAuth login UI hints to use Google Workspace domain (`hd=carbonrobotics.com`)
- Rejected authentication attempts are logged for security monitoring

**Google Cloud Console Setup:**
1. Create a project in [Google Cloud Console](https://console.cloud.google.com)
2. Enable Google+ API (for user info)
3. Create OAuth 2.0 credentials (Web application type)
4. Add authorized redirect URI: `{FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL}/auth/callback`
5. Configure OAuth consent screen to restrict to carbonrobotics.com Google Workspace domain (recommended)

**Local development:**
- Set `DISABLE_AUTH=true` to bypass authentication entirely
- This should NEVER be used in production

## Gotchas

- Arena API requires `*wildcards*` for partial matches - `arena_client.py` adds them automatically
- No session refresh on expiry - will error, needs re-auth
- No rate limit retry logic
- Arena auth is lazy (first tool call), not at startup
- OAuth requires publicly accessible URL (use ngrok/cloudflare tunnel for local dev)
