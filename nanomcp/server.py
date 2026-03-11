from typing import Any, Callable

from nanomcp.protocol import JsonDict, error_response, result_response


ToolHandler = Callable[[JsonDict], JsonDict]


class FakeMCPServer:
    def __init__(
        self,
        name: str,
        version: str,
        tools: list[dict[str, Any]],
        handlers: dict[str, ToolHandler],
    ) -> None:
        self.name = name
        self.version = version
        self._tools = tools
        self._handlers = handlers

    def handle_request(self, request: JsonDict) -> JsonDict:
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if request.get("jsonrpc") != "2.0":
            return error_response(request_id, -32600, "Invalid Request: jsonrpc must be '2.0'")

        if method == "initialize":
            return result_response(
                request_id,
                {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": self.name, "version": self.version},
                },
            )

        if method == "tools/list":
            return result_response(request_id, {"tools": self._tools})

        if method == "tools/call":
            tool_name = str(params.get("name", ""))
            arguments = params.get("arguments", {})
            handler = self._handlers.get(tool_name)
            if handler is None:
                return error_response(request_id, -32602, f"Unknown tool: {tool_name}")
            if not isinstance(arguments, dict):
                return error_response(request_id, -32602, "Invalid params: arguments must be an object")
            try:
                result = handler(arguments)
                return result_response(request_id, {"content": [result], "isError": False})
            except Exception as error:
                return result_response(
                    request_id,
                    {
                        "content": [{"type": "text", "text": f"Tool error: {error}"}],
                        "isError": True,
                    },
                )

        return error_response(request_id, -32601, f"Method not found: {method}")
