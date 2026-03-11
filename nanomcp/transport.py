import json

from nanomcp.protocol import JsonDict


class TransportMCPClient:
    def __init__(self, server_name: str, server: object, transport: str) -> None:
        self.server_name = server_name
        self._server = server
        self._transport = transport
        self._request_id = 0

    def initialize(self) -> JsonDict:
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {"roots": {"listChanged": False}, "sampling": {}},
                "clientInfo": {"name": f"nanoagent-host-{self._transport}", "version": "0.1.0"},
            },
        }
        return self._send_request(request)

    def list_tools(self) -> list[JsonDict]:
        response = self._send_request(
            {"jsonrpc": "2.0", "id": self._next_request_id(), "method": "tools/list", "params": {}}
        )
        return response.get("result", {}).get("tools", [])

    def call_tool(self, tool_name: str, arguments: JsonDict | None = None) -> JsonDict:
        return self._send_request(
            {
                "jsonrpc": "2.0",
                "id": self._next_request_id(),
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments or {}},
            }
        )

    def _send_request(self, request: JsonDict) -> JsonDict:
        if self._transport == "stdio":
            payload = json.dumps(request, ensure_ascii=False)
            response = self._server.handle_request(json.loads(payload))
            return json.loads(json.dumps(response, ensure_ascii=False))

        if self._transport == "sse":
            body = json.dumps(request, ensure_ascii=False)
            response = self._server.handle_request(json.loads(body))
            sse_data = f"event: message\ndata: {json.dumps(response, ensure_ascii=False)}\n\n"
            data_line = [line[6:] for line in sse_data.strip().splitlines() if line.startswith("data: ")]
            if not data_line:
                raise ValueError("Invalid SSE response")
            return json.loads("\n".join(data_line))

        if self._transport == "streamable_http":
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }
            _ = headers
            body = json.dumps(request, ensure_ascii=False)
            response = self._server.handle_request(json.loads(body))
            return json.loads(json.dumps(response, ensure_ascii=False))

        raise ValueError(f"Unsupported transport: {self._transport}")

    def _next_request_id(self) -> int:
        self._request_id += 1
        return self._request_id
