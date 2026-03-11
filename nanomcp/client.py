from nanomcp.protocol import (
    JsonDict,
    make_initialize_request,
    make_tools_call_request,
    make_tools_list_request,
)


class NanoMCPClient:
    def __init__(self, server_name: str, server: object) -> None:
        self.server_name = server_name
        self._server = server
        self._request_id = 0

    def initialize(self) -> JsonDict:
        request = make_initialize_request(self._next_request_id())
        return self._server.handle_request(request)

    def list_tools(self) -> list[JsonDict]:
        request = make_tools_list_request(self._next_request_id())
        response = self._server.handle_request(request)
        return response.get("result", {}).get("tools", [])

    def call_tool(self, tool_name: str, arguments: JsonDict | None = None) -> JsonDict:
        request = make_tools_call_request(self._next_request_id(), tool_name, arguments or {})
        return self._server.handle_request(request)

    def _next_request_id(self) -> int:
        self._request_id += 1
        return self._request_id
