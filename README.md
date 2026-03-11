# nanoMCP

[中文](./README_CN.md) | English

> *"The question is not what you look at, but what you see."* — Henry David Thoreau

The simplest way to understand MCP and run one minimal multi-MCP agent flow.

A minimal implementation of:
- the core MCP JSON-RPC shape (`initialize`, `tools/list`, `tools/call`)
- fake MCP server registration in both custom and official MCP paths
- three nanoAgent-style tool-calling agents (custom MCP / official MCP / official real MCP examples)

## version

v0.1.0

## install

```bash
pip install -r requirements.txt
```

Set your environment variables:

**macOS/Linux:**
```bash
export OPENAI_API_KEY='your-key-here'
export OPENAI_BASE_URL='https://api.openai.com/v1'  # optional
export OPENAI_MODEL='gpt-4o-mini'  # optional
```

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY='your-key-here'
$env:OPENAI_BASE_URL='https://api.openai.com/v1'  # optional
$env:OPENAI_MODEL='gpt-4o-mini'  # optional
```

## quick start

```bash
python agent.py "list tools and call math.add for 7 + 5"
python agent-official.py "list tools and call math.add for 7 + 5"
python agent_official_mcp.py "show tavily/context7 install config and one call example"
```

## project structure

This repo now has two folders:
- `nanomcp`: self-implemented MCP protocol + multiple transport support + multi-server registry
- `officialmcp`: direct wrapper over official MCP Python SDK (`mcp.server.fastmcp.FastMCP`) for registration

`nanomcp` keeps a nanoAgent-style approach: one minimal loop and one minimal transport abstraction.

## how it works

`nanomcp` provides a tiny MCP data-layer simulation:
1. Host sends JSON-RPC `initialize` to each registered server
2. Host requests `tools/list` and merges tools from all servers
3. Agent invokes `call_mcp_tool`
4. Registry routes to target server with `tools/call`
5. Tool result is returned back to the model loop

The core is still one simple loop:
model call → tool call → tool result → model call.

## minimal mcp shape in this repo

This project implements the minimum practical subset:
- JSON-RPC 2.0 message envelope
- lifecycle handshake (`initialize`)
- tool discovery (`tools/list`)
- tool invocation (`tools/call`)
- capability field for `tools`

## built-in fake mcp servers

- `math` server
  - `math.add`
  - `math.multiply`
- `utility` server
  - `utility.echo`
  - `utility.search` (fake results)
- `meta` server
  - `meta.version`

These fake servers are registerable in:
- `nanomcp` custom registry (`build_default_registry`)
- `officialmcp` official SDK registry (`build_official_fake_registry`)

## built-in transports in nanomcp

- `inmemory`: direct JSON-RPC calls in process
- `stdio`: newline-delimited JSON messages
- `sse`: HTTP post + SSE event stream response
- `streamable_http`: HTTP JSON request/response style

## file map

- `nanomcp/protocol.py`: JSON-RPC envelope and MCP request builders
- `nanomcp/server.py`: minimal MCP server (`initialize`, `tools/list`, `tools/call`)
- `nanomcp/client.py`: in-memory MCP client
- `nanomcp/transport.py`: unified client for `stdio` / `sse` / `streamable_http`
- `nanomcp/registry.py`: multi-MCP registration and call routing
- `nanomcp/builtin.py`: built-in fake servers and tool handlers
- `officialmcp/registry.py`: official MCP SDK registration wrapper
- `agent.py`: agent for custom nanomcp fake registry
- `agent-official.py`: agent for officialmcp fake registry
- `agent_official_mcp.py`: official MCP real integration template for tavily/context7
- `smoke_test.py`: python-runnable smoke checks

## officialmcp quick usage

```python
from officialmcp import build_official_fake_registry

registry = build_official_fake_registry()
registry.run(transport="stdio")
```

## run checks

```bash
python smoke_test.py
```

## mcp references

- MCP architecture overview: https://modelcontextprotocol.io/docs/learn/architecture
- MCP specification overview: https://modelcontextprotocol.io/specification/2025-11-25
- MCP tools section: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- MCP transports (stdio / streamable http): https://modelcontextprotocol.io/specification/2025-06-18/basic/transports

---

## license

MIT

────────────────────────────────────────

⏺ *Like a single seed that grows into a forest, one file becomes infinite possibilities.*
