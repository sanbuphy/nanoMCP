"""
MCP Server: 通过 stdio 暴露工具
用法: python stdio/mcp_stdio_server.py
"""
import sys, json

# 注册工具: name -> {handler, description, inputSchema}
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

if __name__ == "__main__":
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        msg = json.loads(line)
        result = handle(msg["method"], msg.get("params", {}))
        print(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": result}), flush=True)
