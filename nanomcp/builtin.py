import json

from nanomcp.protocol import JsonDict
from nanomcp.registry import MCPRegistry
from nanomcp.server import FakeMCPServer


def _math_add(arguments: JsonDict) -> JsonDict:
    a = float(arguments.get("a", 0))
    b = float(arguments.get("b", 0))
    return {"type": "text", "text": str(a + b)}


def _math_multiply(arguments: JsonDict) -> JsonDict:
    a = float(arguments.get("a", 1))
    b = float(arguments.get("b", 1))
    return {"type": "text", "text": str(a * b)}


def _echo_text(arguments: JsonDict) -> JsonDict:
    text = str(arguments.get("text", ""))
    return {"type": "text", "text": text}


def _fake_search(arguments: JsonDict) -> JsonDict:
    query = str(arguments.get("query", ""))
    return {
        "type": "text",
        "text": json.dumps(
            {
                "query": query,
                "top_results": [
                    {"title": "Fake MCP result A", "url": "https://example.com/a"},
                    {"title": "Fake MCP result B", "url": "https://example.com/b"},
                ],
            },
            ensure_ascii=False,
        ),
    }


def _version(arguments: JsonDict) -> JsonDict:
    target = str(arguments.get("target", "nanomcp"))
    return {"type": "text", "text": f"{target}:0.1.0"}


def build_default_registry() -> MCPRegistry:
    math_server = FakeMCPServer(
        name="math-mcp",
        version="0.1.0",
        tools=[
            {
                "name": "add",
                "description": "Add two numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                    "required": ["a", "b"],
                },
            },
            {
                "name": "multiply",
                "description": "Multiply two numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                    "required": ["a", "b"],
                },
            },
        ],
        handlers={"add": _math_add, "multiply": _math_multiply},
    )

    utility_server = FakeMCPServer(
        name="utility-mcp",
        version="0.1.0",
        tools=[
            {
                "name": "echo",
                "description": "Echo input text",
                "inputSchema": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
            },
            {
                "name": "search",
                "description": "Return fake search results",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        ],
        handlers={"echo": _echo_text, "search": _fake_search},
    )

    meta_server = FakeMCPServer(
        name="meta-mcp",
        version="0.1.0",
        tools=[
            {
                "name": "version",
                "description": "Return version info",
                "inputSchema": {
                    "type": "object",
                    "properties": {"target": {"type": "string"}},
                    "required": [],
                },
            }
        ],
        handlers={"version": _version},
    )

    registry = MCPRegistry()
    registry.register_server("math", math_server, transport="stdio")
    registry.register_server("utility", utility_server, transport="sse")
    registry.register_server("meta", meta_server, transport="streamable_http")
    return registry
