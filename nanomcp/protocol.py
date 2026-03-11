from typing import Any


JsonDict = dict[str, Any]


def result_response(request_id: Any, result: JsonDict) -> JsonDict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error_response(request_id: Any, code: int, message: str) -> JsonDict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def make_initialize_request(request_id: int) -> JsonDict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {"roots": {"listChanged": False}, "sampling": {}},
            "clientInfo": {"name": "nanoagent-host", "version": "0.1.0"},
        },
    }


def make_tools_list_request(request_id: int) -> JsonDict:
    return {"jsonrpc": "2.0", "id": request_id, "method": "tools/list", "params": {}}


def make_tools_call_request(request_id: int, name: str, arguments: JsonDict) -> JsonDict:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
