"""
MCP Client: 通过 Remote SSE URL 连接 tavily-mcp
用法: python streamable_http_tavily/mcp_streamable_http_tavily_client.py
"""
import json
import os
import sys
from urllib import parse, request
from openai import OpenAI


class MCPClient:
    def __init__(self, url):
        self.url = url.strip().strip("`").strip()
        self._id = 0
        self._sse_resp = None
        self._message_url = None
        self._pending = {}
        self._connect_sse()

    def _connect_sse(self):
        req = request.Request(self.url, headers={"Accept": "text/event-stream"}, method="GET")
        self._sse_resp = request.urlopen(req, timeout=120)
        self._wait_for_endpoint()

    def _wait_for_endpoint(self):
        while not self._message_url:
            event, data = self._read_event()
            if event == "endpoint" and data:
                self._message_url = parse.urljoin(self.url, data)

    def _read_event(self):
        event = "message"
        data_lines = []
        while True:
            raw = self._sse_resp.readline()
            if not raw:
                raise RuntimeError("Remote SSE stream closed")
            line = raw.decode("utf-8", errors="ignore").rstrip("\r\n")
            if line == "":
                if data_lines:
                    return event, "\n".join(data_lines)
                event = "message"
                data_lines = []
                continue
            if line.startswith(":"):
                continue
            if line.startswith("event:"):
                event = line[6:].strip()
                continue
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
                continue

    def send(self, method, params={}):
        if not self._message_url:
            self._wait_for_endpoint()
        self._id += 1
        req_id = self._id
        body = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            self._message_url,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
            method="POST",
        )
        with request.urlopen(req, timeout=60) as resp:
            if resp.status not in (200, 202):
                raise RuntimeError(f"Unexpected HTTP status: {resp.status}")
        if req_id in self._pending:
            msg = self._pending.pop(req_id)
        else:
            while True:
                event, data = self._read_event()
                if event == "endpoint" and data:
                    self._message_url = parse.urljoin(self.url, data)
                    continue
                if not data:
                    continue
                try:
                    msg = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if msg.get("id") == req_id:
                    break
                if "id" in msg:
                    self._pending[msg["id"]] = msg
        if "error" in msg:
            raise RuntimeError(msg["error"]["message"])
        return msg["result"]

    def initialize(self):
        self.send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "nanomcp-remote-sse-tavily-client", "version": "0.1.0"},
        })
        self.notify("notifications/initialized", {})

    def list_tools(self):
        return self.send("tools/list")["tools"]

    def call_tool(self, name, arguments={}):
        return self.send("tools/call", {"name": name, "arguments": arguments})["content"][0]["text"]

    def notify(self, method, params={}):
        if not self._message_url:
            self._wait_for_endpoint()
        body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params}, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            self._message_url,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
            method="POST",
        )
        with request.urlopen(req, timeout=60) as resp:
            if resp.status not in (200, 202):
                raise RuntimeError(f"Unexpected HTTP status for notification: {resp.status}")

def run_agent(user_message, max_iterations=8):
    url = os.environ.get("TAVILY_REMOTE_SSE_URL", "https://mcp.api-inference.modelscope.net/833945cc3b2848/sse")
    mcp = MCPClient(url)
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("STEP_API_KEY")
    base_url = (os.environ.get("OPENAI_BASE_URL") or os.environ.get("DEFAULT_BASE_URL") or "https://api.stepfun.com/v1").strip().strip("`").strip()
    model = os.environ.get("OPENAI_MODEL") or os.environ.get("DEFAULT_MODEL") or "step-3.5-flash"
    llm = OpenAI(api_key=api_key, base_url=base_url)
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


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Use Tavily search and give me 5 links answering: What is currently the best large language model in the world?"
    print(run_agent(query))
