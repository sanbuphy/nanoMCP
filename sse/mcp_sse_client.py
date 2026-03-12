"""
MCP Client + OpenAI Agent
Usage: python sse/mcp_sse_client.py "What's the weather in Beijing?"
"""
import os, sys, json, time, subprocess
from urllib import request
from openai import OpenAI

class MCPClient:
    def __init__(self, cmd, url):
        self.proc = subprocess.Popen(cmd)
        self.url = url
        self._id = 0
        self._wait_server_ready()

    def _wait_server_ready(self, timeout=5):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                self.send("initialize", {"protocolVersion": "2024-11-05"})
                return
            except Exception:
                time.sleep(0.1)
        raise RuntimeError("SSE server not ready")

    def send(self, method, params={}):
        self._id += 1
        body = json.dumps({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}, ensure_ascii=False).encode("utf-8")
        req = request.Request(self.url, data=body, headers={"Content-Type": "application/json", "Accept": "text/event-stream"}, method="POST")
        with request.urlopen(req) as resp:
            sse_text = resp.read().decode("utf-8")
        data_lines = [line[6:] for line in sse_text.splitlines() if line.startswith("data: ")]
        return json.loads("\n".join(data_lines))["result"]

    def initialize(self):
        self.send("initialize", {"protocolVersion": "2024-11-05"})

    def list_tools(self):
        return self.send("tools/list")["tools"]

    def call_tool(self, name, arguments={}):
        return self.send("tools/call", {"name": name, "arguments": arguments})["content"][0]["text"]

    def close(self):
        self.proc.terminate()


def run_agent(user_message, max_iterations=5):
    mcp = MCPClient([sys.executable, os.path.join(os.path.dirname(__file__), "mcp_sse_server.py")], "http://127.0.0.1:8765/mcp")
    mcp.initialize()
    openai_tools = [
        {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["inputSchema"]}}
        for t in mcp.list_tools()
    ]
    llm = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), base_url=os.environ.get("OPENAI_BASE_URL"))
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Be concise."},
        {"role": "user", "content": user_message},
    ]
    for _ in range(max_iterations):
        resp = llm.chat.completions.create(model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"), messages=messages, tools=openai_tools)
        msg = resp.choices[0].message
        messages.append(msg)
        if not msg.tool_calls:
            mcp.close()
            return msg.content
        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            print(f"[MCP] {name}({args})")
            result = mcp.call_tool(name, args)
            print(f"  → {result}")
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    mcp.close()
    return "Max iterations reached"


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What's the weather in Beijing?"
    print(run_agent(task))
