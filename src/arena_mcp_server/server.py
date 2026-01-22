"""MCP server for Arena PLM API."""

import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .arena_client import ArenaClient


server = Server("arena-mcp-server")
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


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_items",
            description=(
                "Search for items in Arena PLM by name, number, or description. "
                "Wildcards are added automatically for partial matching. "
                "Returns item GUIDs which can be used with other tools: "
                "use get_item for full details, get_item_bom to see components of an assembly, "
                "or get_item_where_used to find which assemblies contain a part."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Filter by item name (partial match)",
                    },
                    "number": {
                        "type": "string",
                        "description": "Filter by item number (partial match)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Filter by description (partial match)",
                    },
                    "category_guid": {
                        "type": "string",
                        "description": "Filter by category GUID (use get_categories to find GUIDs)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default 20, max 400)",
                        "default": 20,
                    },
                },
                "additionalProperties": False,
            },
        ),
        Tool(
            name="get_item",
            description=(
                "Get full details for a specific item by its GUID. "
                "Returns all item attributes including custom attributes, description, owner, and lifecycle phase. "
                "Use after search_items to get complete information about a specific part."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "guid": {
                        "type": "string",
                        "description": "Item GUID (obtain from search_items)",
                    },
                },
                "required": ["guid"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="get_item_bom",
            description=(
                "Get the bill of materials (BOM) for an assembly item. "
                "Returns all child components with quantities and reference designators. "
                "Use this to see what parts make up an assembly. "
                "If looking for a specific component, search for the assembly first, then get its BOM."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "guid": {
                        "type": "string",
                        "description": "Item GUID of the assembly",
                    },
                },
                "required": ["guid"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="get_item_where_used",
            description=(
                "Find all assemblies where a given item is used as a component. "
                "Essential for impact analysis - shows what products would be affected by a part change. "
                "Use this to verify a part is used in expected assemblies or to understand part relationships."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "guid": {
                        "type": "string",
                        "description": "Item GUID to find usage of",
                    },
                },
                "required": ["guid"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="get_item_revisions",
            description=(
                "Get all revisions of an item including working, effective, and superseded revisions. "
                "Shows revision history with associated change orders. "
                "Use to understand how a part has evolved or to find a specific revision."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "guid": {
                        "type": "string",
                        "description": "Item GUID",
                    },
                },
                "required": ["guid"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="get_item_files",
            description=(
                "Get all files associated with an item (drawings, datasheets, CAD files, etc.). "
                "Use to find documentation or design files for a part."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "guid": {
                        "type": "string",
                        "description": "Item GUID",
                    },
                },
                "required": ["guid"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="get_item_sourcing",
            description=(
                "Get supplier/sourcing information for an item including approved manufacturers and vendors. "
                "Shows approval status and whether sources are active for production or prototype. "
                "Use to find approved suppliers for a part."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "guid": {
                        "type": "string",
                        "description": "Item GUID",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default 20, max 400)",
                        "default": 20,
                    },
                },
                "required": ["guid"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="get_categories",
            description=(
                "Get available item categories. Returns category GUIDs that can be used to filter search_items results. "
                "Use when you want to narrow searches to specific part types (e.g., only assemblies, only resistors)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Filter by category path prefix (e.g., 'item\\\\Assembly')",
                    },
                },
                "additionalProperties": False,
            },
        ),
    ]


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


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        arena = get_client()

        if name == "search_items":
            results = arena.search_items(
                name=arguments.get("name"),
                number=arguments.get("number"),
                description=arguments.get("description"),
                category_guid=arguments.get("category_guid"),
                limit=arguments.get("limit", 20),
            )

            count = results.get("count", 0)
            items = results.get("results", [])

            if count == 0:
                return [TextContent(type="text", text="No items found.")]

            lines = [f"Found {count} item(s):\n"]
            for item in items:
                lines.append(_format_item_summary(item))

            # Add hints for follow-up actions
            lines.append("\n---")
            lines.append("Next steps: Use a GUID above with:")
            lines.append("- get_item(guid) for full details")
            lines.append("- get_item_bom(guid) to see assembly components")
            lines.append("- get_item_where_used(guid) to find parent assemblies")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "get_item":
            item = arena.get_item(arguments["guid"])

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

            # Include additional attributes if present
            if item.get("additionalAttributes"):
                lines.append("\nCustom Attributes:")
                for attr in item["additionalAttributes"]:
                    lines.append(f"  {attr.get('name', 'N/A')}: {attr.get('value', 'N/A')}")

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "get_item_bom":
            results = arena.get_item_bom(arguments["guid"])

            count = results.get("count", 0)
            bom_lines = results.get("results", [])

            if count == 0:
                return [TextContent(type="text", text="No BOM lines found (item may not be an assembly).")]

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

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "get_item_where_used":
            results = arena.get_item_where_used(arguments["guid"])

            count = results.get("count", 0)
            usages = results.get("results", [])

            if count == 0:
                return [TextContent(type="text", text="Item is not used in any assemblies.")]

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

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "get_item_revisions":
            results = arena.get_item_revisions(arguments["guid"])

            count = results.get("count", 0)
            revisions = results.get("results", [])

            if count == 0:
                return [TextContent(type="text", text="No revisions found.")]

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

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "get_item_files":
            results = arena.get_item_files(arguments["guid"])

            count = results.get("count", 0)
            files = results.get("results", [])

            if count == 0:
                return [TextContent(type="text", text="No files associated with this item.")]

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

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "get_item_sourcing":
            results = arena.get_item_sourcing(
                arguments["guid"],
                limit=arguments.get("limit", 20),
            )

            count = results.get("count", 0)
            sources = results.get("results", [])

            if count == 0:
                return [TextContent(type="text", text="No sourcing relationships found.")]

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

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "get_categories":
            results = arena.get_categories(path=arguments.get("path"))

            count = results.get("count", 0)
            categories = results.get("results", [])

            if count == 0:
                return [TextContent(type="text", text="No categories found.")]

            lines = [f"Found {count} category(ies):\n"]
            for cat in categories:
                assignable = "assignable" if cat.get("assignable") else "structural"
                lines.append(f"- {cat.get('path', 'N/A')} [{assignable}]")
                lines.append(f"  GUID: {cat.get('guid', 'N/A')}")
                if cat.get("description"):
                    lines.append(f"  Description: {cat['description']}")

            return [TextContent(type="text", text="\n".join(lines))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e}")]


def main() -> None:
    """Run the MCP server."""
    import asyncio

    transport = os.environ.get("MCP_TRANSPORT", "stdio")

    if transport == "http":
        from mcp.server.streamable_http import StreamableHTTPServer

        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("MCP_PORT", "8080"))

        http_server = StreamableHTTPServer(server)
        http_server.run(host=host, port=port)
    else:
        async def run():
            async with stdio_server() as (read_stream, write_stream):
                await server.run(read_stream, write_stream, server.create_initialization_options())

        asyncio.run(run())


if __name__ == "__main__":
    main()
