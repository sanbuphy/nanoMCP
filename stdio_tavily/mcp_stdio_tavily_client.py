"""
MCP Client: 通过 stdio 连接 tavily-mcp
用法: python stdio_tavily/mcp_stdio_tavily_client.py
"""
import json
import os
import subprocess
import sys
from openai import OpenAI


class MCPClient:
    def __init__(self):
        env = os.environ.copy()
        if not env.get("TAVILY_API_KEY"):
            raise RuntimeError("Missing environment variable: TAVILY_API_KEY")
        self.proc = subprocess.Popen(
            ["npx", "-y", "tavily-mcp@0.1.4"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            env=env,
        )
        self._id = 0

    def send(self, method, params={}):
        self._id += 1
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("MCP stdio process ended unexpectedly")
            try:
                msg = json.loads(line)
                if isinstance(msg, dict) and "jsonrpc" in msg:
                    break
            except json.JSONDecodeError:
                continue
        if "error" in msg:
            raise RuntimeError(msg["error"]["message"])
        return msg["result"]

    def initialize(self):
        self.send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "nanomcp-stdio-tavily-client", "version": "0.1.0"},
        })

    def list_tools(self):
        return self.send("tools/list")["tools"]

    def call_tool(self, name, arguments={}):
        return self.send("tools/call", {"name": name, "arguments": arguments})["content"][0]["text"]

    def close(self):
        self.proc.terminate()


def run_agent(user_message, max_iterations=8):
    mcp = MCPClient()
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("STEP_API_KEY")
    base_url = (os.environ.get("OPENAI_BASE_URL") or os.environ.get("DEFAULT_BASE_URL") or "https://api.stepfun.com/v1").strip().strip("`").strip()
    model = os.environ.get("OPENAI_MODEL") or os.environ.get("DEFAULT_MODEL") or "step-3.5-flash"
    llm = OpenAI(api_key=api_key, base_url=base_url)
    try:
        mcp.initialize()
        tools = mcp.list_tools()
        openai_tools = [
            {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["inputSchema"]}}
            for t in tools
        ]
        messages = [
            {"role": "system", "content": "你是搜索助手。你可以多次调用 MCP 工具。若用户要求 N 条结果，你必须调用足够多轮并最终返回不少于 N 条可点击 URL。"},
            {"role": "user", "content": user_message},
        ]
        for _ in range(max_iterations):
            resp = llm.chat.completions.create(
                model=model,
                messages=messages,
                tools=openai_tools,
            )
            msg = resp.choices[0].message
            messages.append(msg)
            if not msg.tool_calls:
                return msg.content or ""
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                print(f"[MCP] {tc.function.name}({args})")
                result = mcp.call_tool(tc.function.name, args)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)})
        return "Max iterations reached"
    finally:
        mcp.close()


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Use Tavily search and give me 5 links answering: What is currently the best large language model in the world?"
    print(run_agent(query))
