from typing import Any, Callable

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    class FastMCP:
        def __init__(self, name: str, json_response: bool = True) -> None:
            self.name = name
            self.json_response = json_response
            self.tools: dict[str, Callable[..., Any]] = {}

        def tool(self, name: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
                tool_name = name or handler.__name__
                self.tools[tool_name] = handler
                return handler

            return decorator

        def run(self, transport: str = "stdio") -> None:
            _ = transport


ToolCallable = Callable[..., Any]
FakeToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


def make_wrapped_tool(handler: FakeToolHandler) -> ToolCallable:
    def wrapped_tool(**kwargs: Any) -> Any:
        return handler(kwargs)

    return wrapped_tool


class OfficialMCPRegistry:
    def __init__(self, name: str = "nano-official-mcp") -> None:
        self.server = FastMCP(name, json_response=True)
        self._tools: dict[str, FakeToolHandler] = {}
        self._tool_specs: dict[str, dict[str, Any]] = {}

    def register_tool(self, handler: ToolCallable, name: str | None = None) -> ToolCallable:
        decorator = self.server.tool(name=name) if name else self.server.tool()
        return decorator(handler)

    def register_fake_server(self, server_name: str, tools: list[dict[str, Any]]) -> None:
        for tool in tools:
            tool_name = str(tool.get("name", ""))
            description = str(tool.get("description", ""))
            input_schema = tool.get("inputSchema", {})
            handler = tool.get("handler")
            if not callable(handler):
                raise ValueError(f"Invalid handler for {server_name}.{tool_name}")
            qualified_name = f"{server_name}.{tool_name}"

            wrapped_tool = make_wrapped_tool(handler)
            wrapped_tool.__name__ = qualified_name.replace(".", "_")
            self.register_tool(wrapped_tool, name=qualified_name)

            self._tools[qualified_name] = handler
            self._tool_specs[qualified_name] = {
                "server": server_name,
                "name": tool_name,
                "qualified_name": qualified_name,
                "description": description,
                "inputSchema": input_schema,
            }

    def list_tools(self) -> list[dict[str, Any]]:
        return [self._tool_specs[key] for key in sorted(self._tool_specs.keys())]

    def call_tool(self, qualified_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        arguments = arguments or {}
        handler = self._tools.get(qualified_name)
        if handler is None:
            return {"ok": False, "error": f"Unknown tool: {qualified_name}"}
        try:
            result = handler(arguments)
            return {"ok": True, "result": {"content": [result], "isError": False}}
        except Exception as error:
            return {
                "ok": False,
                "error": str(error),
                "result": {"content": [{"type": "text", "text": f"Tool error: {error}"}], "isError": True},
            }

    def run(self, transport: str = "stdio") -> None:
        self.server.run(transport=transport)


def build_official_demo_registry() -> OfficialMCPRegistry:
    return build_official_fake_registry()


def build_official_fake_registry() -> OfficialMCPRegistry:
    registry = OfficialMCPRegistry("nano-official-demo")
    registry.register_fake_server(
        "math",
        [
            {
                "name": "add",
                "description": "Add two numbers",
                "inputSchema": {
                    "type": "object",
                    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                    "required": ["a", "b"],
                },
                "handler": lambda args: {
                    "type": "text",
                    "text": str(float(args.get("a", 0)) + float(args.get("b", 0))),
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
                "handler": lambda args: {
                    "type": "text",
                    "text": str(float(args.get("a", 1)) * float(args.get("b", 1))),
                },
            },
        ],
    )
    registry.register_fake_server(
        "utility",
        [
            {
                "name": "echo",
                "description": "Echo input text",
                "inputSchema": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
                "handler": lambda args: {"type": "text", "text": str(args.get("text", ""))},
            },
            {
                "name": "search",
                "description": "Return fake search results",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                "handler": lambda args: {
                    "type": "text",
                    "text": str(
                        {
                            "query": str(args.get("query", "")),
                            "top_results": [
                                {"title": "Official fake result A", "url": "https://example.com/a"},
                                {"title": "Official fake result B", "url": "https://example.com/b"},
                            ],
                        }
                    ),
                },
            },
        ],
    )
    registry.register_fake_server(
        "meta",
        [
            {
                "name": "version",
                "description": "Return version info",
                "inputSchema": {
                    "type": "object",
                    "properties": {"target": {"type": "string"}},
                    "required": [],
                },
                "handler": lambda args: {
                    "type": "text",
                    "text": f"{str(args.get('target', 'officialmcp'))}:0.1.0",
                },
            }
        ],
    )
    return registry
