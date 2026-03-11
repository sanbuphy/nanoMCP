import json
import os
import sys
from typing import Any

from openai import OpenAI


client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL"),
)


REAL_MCP_SERVERS = {
    "context7": {
        "command": "npx",
        "args": ["-y", "@upstash/context7-mcp"],
        "env": {"CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}"},
        "transport": "stdio",
        "sample_tool": "context7.search_docs",
    },
    "tavily": {
        "command": "npx",
        "args": ["-y", "tavily-mcp@latest"],
        "env": {"TAVILY_API_KEY": "${TAVILY_API_KEY}"},
        "transport": "stdio",
        "sample_tool": "tavily.search",
    },
}


tools = [
    {
        "type": "function",
        "function": {
            "name": "list_real_mcp_servers",
            "description": "List real MCP server templates for official MCP setup",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_mcp_install_examples",
            "description": "Get npx installation and config examples for real MCP servers",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "call_real_mcp_example",
            "description": "Run a real MCP call example payload for tavily/context7",
            "parameters": {
                "type": "object",
                "properties": {
                    "server": {"type": "string"},
                    "query": {"type": "string"},
                },
                "required": ["server", "query"],
            },
        },
    },
]


def parse_tool_arguments(raw_arguments: str) -> dict[str, Any]:
    if not raw_arguments:
        return {}
    try:
        parsed = json.loads(raw_arguments)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError as error:
        return {"_argument_error": f"Invalid JSON arguments: {error}"}


def list_real_mcp_servers() -> str:
    payload = [{"name": name, **config} for name, config in REAL_MCP_SERVERS.items()]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def get_mcp_install_examples() -> str:
    config_json = {
        "mcpServers": {
            "context7": {
                "command": "npx",
                "args": ["-y", "@upstash/context7-mcp"],
                "env": {"CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}"},
            },
            "tavily": {
                "command": "npx",
                "args": ["-y", "tavily-mcp@latest"],
                "env": {"TAVILY_API_KEY": "${TAVILY_API_KEY}"},
            },
        }
    }
    payload = {
        "install_commands": [
            "npm i -g @modelcontextprotocol/inspector",
            "npx -y @upstash/context7-mcp --help",
            "npx -y tavily-mcp@latest --help",
        ],
        "config_example_json": config_json,
        "usage_examples": [
            "claude mcp add context7 --transport stdio -- npx -y @upstash/context7-mcp",
            "claude mcp add tavily --transport stdio -- npx -y tavily-mcp@latest",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def call_real_mcp_example(server: str, query: str) -> str:
    key = server.strip().lower()
    if key not in REAL_MCP_SERVERS:
        return json.dumps({"ok": False, "error": f"Unsupported server: {server}"}, ensure_ascii=False)
    payload = {
        "ok": True,
        "server": key,
        "tool": REAL_MCP_SERVERS[key]["sample_tool"],
        "query": query,
        "jsonrpc_example": {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": REAL_MCP_SERVERS[key]["sample_tool"], "arguments": {"query": query}},
        },
        "note": "This file is an official MCP real integration template. Use the install examples to connect actual servers in your MCP host.",
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


available_functions = {
    "list_real_mcp_servers": list_real_mcp_servers,
    "get_mcp_install_examples": get_mcp_install_examples,
    "call_real_mcp_example": call_real_mcp_example,
}


def run_agent(user_message: str, max_iterations: int = 6) -> str:
    messages: list[Any] = [
        {
            "role": "system",
            "content": "You are a helpful assistant. Use official MCP real examples for tavily/context7 when needed. Be concise.",
        },
        {"role": "user", "content": user_message},
    ]

    for _ in range(max_iterations):
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            tools=tools,
        )
        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            return str(message.content)

        for tool_call in message.tool_calls:
            function_payload = getattr(tool_call, "function", None)
            if function_payload is None:
                continue
            function_name = str(getattr(function_payload, "name", ""))
            raw_arguments = str(getattr(function_payload, "arguments", ""))
            function_args = parse_tool_arguments(raw_arguments)
            print(f"[Tool] {function_name}({function_args})")
            function_impl = available_functions.get(function_name)
            if function_impl is None:
                function_response = f"Error: Unknown tool '{function_name}'"
            elif "_argument_error" in function_args:
                function_response = f"Error: {function_args['_argument_error']}"
            else:
                try:
                    function_response = function_impl(**function_args)
                except TypeError as error:
                    function_response = f"Error: Invalid tool arguments: {error}"
            messages.append(
                {"role": "tool", "tool_call_id": tool_call.id, "content": function_response}
            )

    return "Max iterations reached"


if __name__ == "__main__":
    task = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "先给我 context7 和 tavily 的 mcp 安装配置示例，再给出一次 tavily 查询示例"
    )
    print(run_agent(task))
