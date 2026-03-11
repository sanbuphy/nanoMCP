"""
MCP Server: 通过 Streamable HTTP 暴露工具
用法: python streamable_http/mcp_streamable_http_server.py
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOOLS = {
    "add": {
        "description": "两数相加",
        "inputSchema": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]},
        "handler": lambda a, b: a + b,
    },
    "multiply": {
        "description": "两数相乘",
        "inputSchema": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]},
        "handler": lambda a, b: a * b,
    },
    "weather": {
        "description": "查询城市天气",
        "inputSchema": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
        "handler": lambda city: f"{city}: 晴 152°C",
    },
}

def handle(method, params):
    if method == "initialize":
        return {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}
    if method == "tools/list":
        return {"tools": [
            {"name": n, "description": t["description"], "inputSchema": t["inputSchema"]}
            for n, t in TOOLS.items()
        ]}
    if method == "tools/call":
        name, args = params["name"], params.get("arguments", {})
        result = TOOLS[name]["handler"](**args)
        return {"content": [{"type": "text", "text": str(result)}]}

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/mcp":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        msg = json.loads(body)
        payload = json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": handle(msg["method"], msg.get("params", {}))}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8766), Handler).serve_forever()
