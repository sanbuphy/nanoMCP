import json
import os
import sys
from typing import Any

from openai import OpenAI

from nanomcp import build_default_registry


client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL"),
)

registry = build_default_registry()
registry.initialize_all()


tools = [
    {
        "type": "function",
        "function": {
            "name": "list_mcp_tools",
            "description": "List all tools across registered MCP servers",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "call_mcp_tool",
            "description": "Call one MCP tool by qualified name: server.tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "qualified_name": {"type": "string"},
                    "arguments": {"type": "object"},
                },
                "required": ["qualified_name"],
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


def list_mcp_tools() -> str:
    return json.dumps(registry.list_tools(), ensure_ascii=False)


def call_mcp_tool(qualified_name: str, arguments: dict[str, Any] | None = None) -> str:
    return json.dumps(
        registry.call_tool(qualified_name=qualified_name, arguments=arguments or {}),
        ensure_ascii=False,
    )


available_functions = {
    "list_mcp_tools": list_mcp_tools,
    "call_mcp_tool": call_mcp_tool,
}


def run_agent(user_message: str, max_iterations: int = 6) -> str:
    messages: list[Any] = [
        {
            "role": "system",
            "content": "You are a helpful assistant. Use MCP tools when needed. Be concise.",
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
        else "请先列出 MCP 工具，再调用 math.add 计算 7 + 5"
    )
    print(run_agent(task))
