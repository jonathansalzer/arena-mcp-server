"""MCP server for Arena PLM API."""

import os

from dotenv import load_dotenv
import warnings

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import Response

from .arena_client import ArenaClient
from .auth import RestrictedGoogleProvider

load_dotenv()


# Configure host/port from environment
HOST = os.environ.get("MCP_HOST", "0.0.0.0")
PORT = int(os.environ.get("MCP_PORT", "8080"))
TRANSPORT = os.environ.get("MCP_TRANSPORT", "http")  # http or sse
DISABLE_AUTH = os.environ.get("DISABLE_AUTH", "").lower() in ("true", "1", "yes")

# Configure authentication
# When DISABLE_AUTH is true, skip auth entirely
if DISABLE_AUTH:
    warnings.warn(
        "Authentication is DISABLED - this should only be used for local development",
        stacklevel=1,
    )
    auth = None
else:
    # Configure Google OAuth 2.0 authentication (restricted to @carbonrobotics.com)
    auth = RestrictedGoogleProvider(
        client_id=os.environ.get("FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID", ""),
        client_secret=os.environ.get("FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET", ""),
        base_url=os.environ.get("FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL", ""),
        extra_authorize_params={"hd": "carbonrobotics.com"},
    )

mcp = FastMCP("arena-mcp-server", auth=auth)

client: ArenaClient | None = None


def get_client() -> ArenaClient:
    """Get or create authenticated Arena client."""
    global client

    if client is None or not client.is_authenticated:
        client = ArenaClient()
        email = os.environ.get("ARENA_EMAIL")
        password = os.environ.get("ARENA_PASSWORD")
        workspace_id = os.environ.get("ARENA_WORKSPACE_ID")

        if not email or not password:
            raise RuntimeError(
                "ARENA_EMAIL and ARENA_PASSWORD environment variables required"
            )

        client.login(
            email=email,
            password=password,
            workspace_id=int(workspace_id) if workspace_id else None,
        )

    return client


def _format_item_summary(item: dict) -> str:
    """Format a single item as a summary line."""
    line = f"- {item.get('number', 'N/A')}: {item.get('name', 'N/A')}"
    if item.get("revisionNumber"):
        line += f" (Rev {item['revisionNumber']})"
    if item.get("lifecyclePhase", {}).get("name"):
        line += f" [{item['lifecyclePhase']['name']}]"
    if item.get("guid"):
        line += f"\n  GUID: {item['guid']}"
    if item.get("url", {}).get("app"):
        line += f"\n  URL: {item['url']['app']}"
    return line


@mcp.tool()
def search_items(
    name: str | None = None,
    number: str | None = None,
    description: str | None = None,
    category_guid: str | None = None,
    limit: int = 20,
) -> str:
    """Search for items in Arena PLM by name, number, or description.

    Wildcards are added automatically for partial matching.
    Returns item GUIDs which can be used with other tools:
    use get_item for full details, get_item_bom to see components of an assembly,
    or get_item_where_used to find which assemblies contain a part.

    Args:
        name: Filter by item name (partial match)
        number: Filter by item number (partial match)
        description: Filter by description (partial match)
        category_guid: Filter by category GUID (use get_categories to find GUIDs)
        limit: Max results to return (default 20, max 400)
    """
    arena = get_client()
    results = arena.search_items(
        name=name,
        number=number,
        description=description,
        category_guid=category_guid,
        limit=limit,
    )

    count = results.get("count", 0)
    items = results.get("results", [])

    if count == 0:
        return "No items found."

    lines = [f"Found {count} item(s):\n"]
    for item in items:
        lines.append(_format_item_summary(item))

    lines.append("\n---")
    lines.append("Next steps: Use a GUID above with:")
    lines.append("- get_item(guid) for full details")
    lines.append("- get_item_bom(guid) to see assembly components")
    lines.append("- get_item_where_used(guid) to find parent assemblies")

    return "\n".join(lines)


@mcp.tool()
def get_item(guid: str) -> str:
    """Get full details for a specific item by its GUID.

    Returns all item attributes including custom attributes, description, owner, and lifecycle phase.
    Use after search_items to get complete information about a specific part.

    Args:
        guid: Item GUID (obtain from search_items)
    """
    arena = get_client()
    item = arena.get_item(guid)

    lines = [
        f"Item: {item.get('number', 'N/A')} - {item.get('name', 'N/A')}",
        f"GUID: {item.get('guid', 'N/A')}",
        f"Revision: {item.get('revisionNumber', 'N/A')}",
        f"Lifecycle Phase: {item.get('lifecyclePhase', {}).get('name', 'N/A')}",
        f"Category: {item.get('category', {}).get('name', 'N/A')}",
        f"Description: {item.get('description', 'N/A')}",
        f"Owner: {item.get('owner', {}).get('fullName', 'N/A')}",
        f"Created: {item.get('creationDateTime', 'N/A')}",
        f"Effective: {item.get('effectiveDateTime', 'N/A')}",
    ]

    if item.get("url", {}).get("app"):
        lines.append(f"URL: {item['url']['app']}")

    if item.get("additionalAttributes"):
        lines.append("\nCustom Attributes:")
        for attr in item["additionalAttributes"]:
            lines.append(f"  {attr.get('name', 'N/A')}: {attr.get('value', 'N/A')}")

    return "\n".join(lines)


@mcp.tool()
def get_item_bom(guid: str) -> str:
    """Get the bill of materials (BOM) for an assembly item.

    Returns all child components with quantities and reference designators.
    Use this to see what parts make up an assembly.
    If looking for a specific component, search for the assembly first, then get its BOM.

    Args:
        guid: Item GUID of the assembly
    """
    arena = get_client()
    results = arena.get_item_bom(guid)

    count = results.get("count", 0)
    bom_lines = results.get("results", [])

    if count == 0:
        return "No BOM lines found (item may not be an assembly)."

    lines = [f"BOM has {count} line(s):\n"]
    for bom_line in bom_lines:
        item = bom_line.get("item", {})
        line_num = bom_line.get("lineNumber", "N/A")
        qty = bom_line.get("quantity", "N/A")
        ref_des = bom_line.get("refDes", "")

        lines.append(
            f"[{line_num}] {item.get('number', 'N/A')}: {item.get('name', 'N/A')} "
            f"(Qty: {qty})"
        )
        if ref_des:
            lines[-1] += f" RefDes: {ref_des}"
        lines.append(f"     GUID: {item.get('guid', 'N/A')}")

    return "\n".join(lines)


@mcp.tool()
def get_item_where_used(guid: str) -> str:
    """Find all assemblies where a given item is used as a component.

    Essential for impact analysis - shows what products would be affected by a part change.
    Use this to verify a part is used in expected assemblies or to understand part relationships.

    Args:
        guid: Item GUID to find usage of
    """
    arena = get_client()
    results = arena.get_item_where_used(guid)

    count = results.get("count", 0)
    usages = results.get("results", [])

    if count == 0:
        return "Item is not used in any assemblies."

    lines = [f"Used in {count} assembly(ies):\n"]
    for usage in usages:
        item = usage.get("item", {})
        line_num = usage.get("lineNumber", "N/A")
        qty = usage.get("quantity", "N/A")

        lines.append(
            f"- {item.get('number', 'N/A')}: {item.get('name', 'N/A')} "
            f"(Line {line_num}, Qty: {qty})"
        )
        lines.append(f"  GUID: {item.get('guid', 'N/A')}")

    return "\n".join(lines)


@mcp.tool()
def get_item_revisions(guid: str) -> str:
    """Get all revisions of an item including working, effective, and superseded revisions.

    Shows revision history with associated change orders.
    Use to understand how a part has evolved or to find a specific revision.

    Args:
        guid: Item GUID
    """
    arena = get_client()
    results = arena.get_item_revisions(guid)

    count = results.get("count", 0)
    revisions = results.get("results", [])

    if count == 0:
        return "No revisions found."

    status_map = {0: "Working", 1: "Effective", 2: "Superseded"}
    lines = [f"Found {count} revision(s):\n"]
    for rev in revisions:
        status = status_map.get(rev.get("status"), "Unknown")
        rev_num = rev.get("number", "Working")
        phase = rev.get("lifecyclePhase", {}).get("name", "N/A")

        lines.append(f"- Rev {rev_num} [{status}] - {phase}")
        if rev.get("change", {}).get("number"):
            lines[-1] += f" (via {rev['change']['number']})"
        lines.append(f"  GUID: {rev.get('guid', 'N/A')}")

    return "\n".join(lines)


@mcp.tool()
def get_item_files(guid: str) -> str:
    """Get all files associated with an item (drawings, datasheets, CAD files, etc.).

    Use to find documentation or design files for a part.

    Args:
        guid: Item GUID
    """
    arena = get_client()
    results = arena.get_item_files(guid)

    count = results.get("count", 0)
    files = results.get("results", [])

    if count == 0:
        return "No files associated with this item."

    lines = [f"Found {count} file(s):\n"]
    for file_assoc in files:
        f = file_assoc.get("file", {})
        lines.append(
            f"- {f.get('name', 'N/A')} ({f.get('format', 'N/A')})"
        )
        if f.get("title"):
            lines[-1] += f" - {f['title']}"
        lines.append(f"  Number: {f.get('number', 'N/A')}, Edition: {f.get('edition', 'N/A')}")
        if file_assoc.get("primary"):
            lines[-1] += " [PRIMARY]"

    return "\n".join(lines)


@mcp.tool()
def get_item_sourcing(guid: str, limit: int = 20) -> str:
    """Get supplier/sourcing information for an item including approved manufacturers and vendors.

    Shows approval status and whether sources are active for production or prototype.
    Use to find approved suppliers for a part.

    Args:
        guid: Item GUID
        limit: Max results to return (default 20, max 400)
    """
    arena = get_client()
    results = arena.get_item_sourcing(guid, limit=limit)

    count = results.get("count", 0)
    sources = results.get("results", [])

    if count == 0:
        return "No sourcing relationships found."

    lines = [f"Found {count} source(s):\n"]
    for source in sources:
        approved = "Approved" if source.get("approved") else "Not Approved"
        prod = "Production" if source.get("activeProduction") else ""
        proto = "Prototype" if source.get("activePrototype") else ""
        active = ", ".join(filter(None, [prod, proto])) or "Inactive"

        lines.append(f"- [{approved}] [{active}]")
        if source.get("notes"):
            lines.append(f"  Notes: {source['notes']}")
        lines.append(f"  GUID: {source.get('guid', 'N/A')}")

    return "\n".join(lines)


@mcp.tool()
def get_categories(path: str | None = None) -> str:
    """Get available item categories.

    Returns category GUIDs that can be used to filter search_items results.
    Use when you want to narrow searches to specific part types (e.g., only assemblies, only resistors).

    Args:
        path: Filter by category path prefix (e.g., 'item\\Assembly')
    """
    arena = get_client()
    results = arena.get_categories(path=path)

    count = results.get("count", 0)
    categories = results.get("results", [])

    if count == 0:
        return "No categories found."

    lines = [f"Found {count} category(ies):\n"]
    for cat in categories:
        assignable = "assignable" if cat.get("assignable") else "structural"
        lines.append(f"- {cat.get('path', 'N/A')} [{assignable}]")
        lines.append(f"  GUID: {cat.get('guid', 'N/A')}")
        if cat.get("description"):
            lines.append(f"  Description: {cat['description']}")

    return "\n".join(lines)


@mcp.custom_route("/healthz", methods=["GET"])
def health_check(_request: Request) -> Response:
    """Health check endpoint for load balancers and monitoring."""
    return Response(status_code=200, content="OK")


def main() -> None:
    """Run the MCP server."""
    # Validate required Arena credentials at startup
    arena_email = os.environ.get("ARENA_EMAIL")
    arena_password = os.environ.get("ARENA_PASSWORD")

    if not arena_email or not arena_password:
        print("ERROR: Missing required environment variables")
        print("ARENA_EMAIL and ARENA_PASSWORD must be set")
        print("\nPlease configure these in your .env file or environment")
        raise SystemExit(1)

    auth_status = "DISABLED" if DISABLE_AUTH else "enabled"
    print(f"Starting Arena MCP server on http://{HOST}:{PORT}")
    print(f"Transport: {TRANSPORT}, Auth: {auth_status}")
    print(f"Arena account: {arena_email}")
    mcp.run(transport=TRANSPORT, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
