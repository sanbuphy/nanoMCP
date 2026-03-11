from nanomcp.client import NanoMCPClient
from nanomcp.protocol import JsonDict
from nanomcp.transport import TransportMCPClient


class MCPRegistry:
    def __init__(self) -> None:
        self._clients: dict[str, object] = {}

    def register(self, server_name: str, client: object) -> None:
        self._clients[server_name] = client

    def register_server(self, server_name: str, server: object, transport: str = "inmemory") -> None:
        if transport == "inmemory":
            client = NanoMCPClient(server_name, server)
        elif transport in {"stdio", "sse", "streamable_http"}:
            client = TransportMCPClient(server_name, server, transport=transport)
        else:
            raise ValueError(f"Unsupported transport: {transport}")
        self.register(server_name, client)

    def server_names(self) -> list[str]:
        return sorted(self._clients.keys())

    def initialize_all(self) -> dict[str, JsonDict]:
        initialized: dict[str, JsonDict] = {}
        for server_name, client in self._clients.items():
            initialized[server_name] = client.initialize()
        return initialized

    def list_tools(self) -> list[JsonDict]:
        merged_tools: list[JsonDict] = []
        for server_name, client in self._clients.items():
            for tool in client.list_tools():
                merged_tools.append(
                    {
                        "server": server_name,
                        "name": tool.get("name", ""),
                        "qualified_name": f"{server_name}.{tool.get('name', '')}",
                        "description": tool.get("description", ""),
                        "inputSchema": tool.get("inputSchema", {}),
                    }
                )
        return merged_tools

    def call_tool(self, qualified_name: str, arguments: JsonDict | None = None) -> JsonDict:
        arguments = arguments or {}
        if "." not in qualified_name:
            return {"ok": False, "error": "Tool name must be 'server.tool'"}

        server_name, tool_name = qualified_name.split(".", 1)
        client = self._clients.get(server_name)
        if client is None:
            return {"ok": False, "error": f"Unknown server: {server_name}"}

        response = client.call_tool(tool_name, arguments)
        if "error" in response:
            return {"ok": False, "error": response["error"]["message"]}
        return {"ok": True, "result": response["result"]}
