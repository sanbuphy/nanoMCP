"""
MCP Client + OpenAI Agent
Usage: python stdio/mcp_stdio_client.py "What is 3 + 5?"
"""
import os, sys, json, subprocess
from openai import OpenAI

class MCPClient:
    def __init__(self, cmd):
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self._id = 0

    def send(self, method, params={}):
        self._id += 1
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}) + "\n")
        self.proc.stdin.flush()
        return json.loads(self.proc.stdout.readline())["result"]

    def initialize(self):
        self.send("initialize", {"protocolVersion": "2024-11-05"})

    def list_tools(self):
        return self.send("tools/list")["tools"]

    def call_tool(self, name, arguments={}):
        return self.send("tools/call", {"name": name, "arguments": arguments})["content"][0]["text"]

    def close(self):
        self.proc.terminate()


def run_agent(user_message, max_iterations=5):
    mcp = MCPClient([sys.executable, os.path.join(os.path.dirname(__file__), "mcp_stdio_server.py")])
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
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is 3 + 5?"
    print(run_agent(task))
