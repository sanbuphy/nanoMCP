# nanoMCP

[中文](./README_CN.md) | English

> *"The question is not what you look at, but what you see."* — Henry David Thoreau

Minimal MCP (Model Context Protocol) demos in Python:
- a tiny MCP server that exposes a few toy tools (`add`, `multiply`, `weather`)
- MCP clients for **stdio**, **SSE**, and **Streamable HTTP**
- an OpenAI function-calling loop that calls MCP tools
- Tavily MCP integration examples (local stdio via `npx`, and remote Streamable HTTP via SSE)

This repository is intentionally small and easy to read: each transport is a self-contained end-to-end example.

If you forget what an “agent loop” is or how OpenAI function calling works, read:
https://github.com/sanbuphy/nanoAgent

## Version

v0.1.0

## Docs

There is also a `docs/` folder with MCP reading notes and deeper implementation analyses:
- [docs/README.en.md](./docs/README.en.md)
- [docs/README.md](./docs/README.md) (Chinese)

## Install

```bash
pip install -r requirements.txt
```

## Environment variables

These examples call an LLM via the OpenAI Python SDK.

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

Tavily examples also require:
```bash
export TAVILY_API_KEY='your-tavily-key'
```

Some scripts support StepFun-compatible env vars (as a fallback):
- `STEP_API_KEY` (used when `OPENAI_API_KEY` is missing)
- `DEFAULT_BASE_URL` (defaults to `https://api.stepfun.com/v1`)
- `DEFAULT_MODEL` (defaults to `step-3.5-flash`)

## Quick start (local demo MCP server)

If you're new to MCP, start with `stdio/` first. It is the simplest transport and the easiest to debug:
- Read `stdio/mcp_stdio_server.py` to see the minimal `initialize` / `tools/list` / `tools/call` implementation.
- Then read `stdio/mcp_stdio_client.py` to see how the client spawns the server, converts MCP tools to OpenAI tools, and runs the loop.

**stdio**
```bash
python stdio/mcp_stdio_client.py "What is 3 + 5?"
```

**SSE (HTTP POST + SSE response)**
```bash
python sse/mcp_sse_client.py "What's the weather in Beijing?"
```

**Streamable HTTP (HTTP JSON request/response)**
```bash
python streamable_http/mcp_streamable_http_client.py "Compute 7 * 6, then add 5."
```

Each client spins up its matching server process automatically.

## Tavily MCP examples

### 1) Tavily over stdio (local `npx` process)

Requires Node.js so `npx` is available.

```bash
export TAVILY_API_KEY='your-tavily-key'
python stdio_tavily/mcp_stdio_tavily_client.py "Use Tavily search 2 times and give me 5 links about: MCP Streamable HTTP transport"
```

### 2) Tavily over Streamable HTTP (remote SSE URL)

This example connects to a remote MCP server that uses the Streamable HTTP pattern (SSE stream + POST message endpoint).

```bash
export TAVILY_REMOTE_SSE_URL='https://.../sse'  # optional, a default is baked into the script
python streamable_http_tavily/mcp_streamable_http_tavily_client.py "Use Tavily search 3 times and give me 3 links about: MCP tools/list"
```

## What is implemented

These examples implement the minimal practical subset of MCP tools:
- JSON-RPC 2.0 envelope
- lifecycle handshake: `initialize`
- tool discovery: `tools/list`
- tool invocation: `tools/call`
- (remote Streamable HTTP client only) `notifications/initialized`

Protocol version used in demos: `2024-11-05`.

## Project layout

- `stdio/`
  - `mcp_stdio_server.py`: MCP server over stdio
  - `mcp_stdio_client.py`: MCP client + LLM loop (spawns the server)
- `sse/`
  - `mcp_sse_server.py`: MCP server over HTTP that replies via SSE
  - `mcp_sse_client.py`: MCP client + LLM loop (spawns the server)
- `streamable_http/`
  - `mcp_streamable_http_server.py`: MCP server over HTTP JSON
  - `mcp_streamable_http_client.py`: MCP client + LLM loop (spawns the server)
- `stdio_tavily/`
  - `mcp_stdio_tavily_client.py`: connect to `tavily-mcp` via stdio (`npx`)
- `streamable_http_tavily/`
  - `mcp_streamable_http_tavily_client.py`: connect to a remote Streamable HTTP (SSE) endpoint
- `docs/`: MCP protocol notes + implementation deep dives

## Notes

- Default ports: SSE server uses `127.0.0.1:8765`, Streamable HTTP server uses `127.0.0.1:8766`.
- If the model keeps calling tools, the clients stop after a maximum number of iterations and return `Max iterations reached`.

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
