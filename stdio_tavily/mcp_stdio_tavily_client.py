"""
MCP Client: Connect to tavily-mcp via stdio
Usage: python stdio_tavily/mcp_stdio_tavily_client.py
"""
import json
import os
import re
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


def _extract_tool_call_budget(user_message: str):
    patterns = [
        r"(?:search|query|call)\s*(?:for\s*)?(\d{1,2})\s*(?:times|searches|queries|rounds|iterations)\b",
        r"(\d{1,2})\s*(?:times|searches|queries|rounds|iterations)\b",
        r"(\d{1,2})\s*次(?:查询|搜索|工具调用)?",
    ]
    for p in patterns:
        m = re.search(p, user_message, flags=re.IGNORECASE)
        if not m:
            continue
        try:
            n = int(m.group(1))
        except (TypeError, ValueError):
            continue
        if 1 <= n <= 20:
            return n
    return None


def run_agent(user_message, max_iterations=8, default_tool_calls=4):
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
        tool_call_budget = _extract_tool_call_budget(user_message) or default_tool_calls
        messages = [
            {"role": "system", "content": "You are a search assistant. Always respond in English.\n\nYou can call MCP tools multiple times.\n- If the user requests N results, you must call tools enough times and return at least N clickable URLs.\n- If the user specifies how many searches/tool calls to run, follow that number.\n- Otherwise, default to 4 tool calls."},
            {"role": "user", "content": user_message},
        ]
        tool_calls_made = 0
        budget_notice_added = False
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
                if tool_calls_made >= tool_call_budget:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": "Tool call budget exceeded. Do not call any more tools; answer using the information already gathered.",
                    })
                    continue
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                print(f"[MCP] {tc.function.name}({args})")
                result = mcp.call_tool(tc.function.name, args)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)})
                tool_calls_made += 1
            if tool_calls_made >= tool_call_budget and not budget_notice_added:
                messages.append({"role": "system", "content": "Tool call budget reached. Produce the final answer now without calling any tools."})
                budget_notice_added = True
        return "Max iterations reached"
    finally:
        mcp.close()


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Use Tavily search 2 times and give me 5 links answering: What is currently the best large language model in the world?"
    print(run_agent(query))
