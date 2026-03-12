# nanoMCP

[English](./README.md) | 中文

> *"问题不在于你看到了什么，而在于你看见了什么。"* — 梭罗

用最小的 Python 代码跑通 MCP（Model Context Protocol）端到端示例：
- 一个极简 MCP Server，暴露少量玩具工具（`add` / `multiply` / `weather`）
- 三种传输的 MCP Client：**stdio** / **SSE** / **Streamable HTTP**
- 基于 OpenAI function calling 的 agent 循环（模型决定何时调用 MCP 工具）
- Tavily MCP 集成示例（本地 `npx` stdio、以及远程 Streamable HTTP/SSE）

本仓库刻意保持“每个传输一个最小闭环示例”，方便对照阅读与上手。

## 版本

v0.1.0

## docs 文档集

仓库内还提供了 `docs/` 文档集（MCP 协议笔记 + 典型项目实现分析）：
- [docs/README.md](./docs/README.md)
- [docs/README.en.md](./docs/README.en.md)

## 安装

```bash
pip install -r requirements.txt
```

## 环境变量

这些示例通过 OpenAI Python SDK 调用模型。

**macOS/Linux:**
```bash
export OPENAI_API_KEY='your-key-here'
export OPENAI_BASE_URL='https://api.openai.com/v1'  # 可选
export OPENAI_MODEL='gpt-4o-mini'  # 可选
```

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY='your-key-here'
$env:OPENAI_BASE_URL='https://api.openai.com/v1'  # 可选
$env:OPENAI_MODEL='gpt-4o-mini'  # 可选
```

Tavily 示例还需要：
```bash
export TAVILY_API_KEY='your-tavily-key'
```

部分脚本支持 StepFun 兼容的环境变量（作为兜底）：
- `STEP_API_KEY`（未设置 `OPENAI_API_KEY` 时使用）
- `DEFAULT_BASE_URL`（默认 `https://api.stepfun.com/v1`）
- `DEFAULT_MODEL`（默认 `step-3.5-flash`）

## 快速开始（本地 demo MCP server）

如果你是 MCP 新手，推荐先从 `stdio/` 开始跑通和理解：它是最简单的传输，也最容易调试。
- 先读 `stdio/mcp_stdio_server.py`，理解最小的 `initialize` / `tools/list` / `tools/call` 是怎么实现的。
- 再读 `stdio/mcp_stdio_client.py`，理解 client 如何启动 server、把 MCP tools 映射成 OpenAI tools，并跑通循环。

**stdio**
```bash
python stdio/mcp_stdio_client.py "What is 3 + 5?"
```

**SSE（HTTP POST + SSE 响应）**
```bash
python sse/mcp_sse_client.py "What's the weather in Beijing?"
```

**Streamable HTTP（HTTP JSON 请求/响应）**
```bash
python streamable_http/mcp_streamable_http_client.py "Compute 7 * 6, then add 5."
```

这些 client 会自动启动对应的 server 子进程。

## Tavily MCP 示例

### 1）stdio 连接 Tavily（本地 `npx` 进程）

需要本机安装 Node.js（保证 `npx` 可用）。

```bash
export TAVILY_API_KEY='your-tavily-key'
python stdio_tavily/mcp_stdio_tavily_client.py "Use Tavily search 2 times and give me 5 links about: MCP Streamable HTTP transport"
```

### 2）Streamable HTTP 连接 Tavily（远程 SSE URL）

该示例连接到一个采用 Streamable HTTP 模式的远程 MCP 服务（SSE 长连接 + POST 消息端点）。

```bash
export TAVILY_REMOTE_SSE_URL='https://.../sse'  # 可选，脚本内置了一个默认值
python streamable_http_tavily/mcp_streamable_http_tavily_client.py "Use Tavily search 3 times and give me 3 links about: MCP tools/list"
```

## 本仓库实现的最小 MCP 形态

- JSON-RPC 2.0 报文外壳
- 生命周期握手：`initialize`
- 工具发现：`tools/list`
- 工具调用：`tools/call`
-（仅远程 Streamable HTTP client）`notifications/initialized`

示例中使用的协议版本：`2024-11-05`。

## 目录结构

- `stdio/`
  - `mcp_stdio_server.py`：stdio 传输的 MCP Server
  - `mcp_stdio_client.py`：stdio Client + LLM 循环（会启动 server）
- `sse/`
  - `mcp_sse_server.py`：HTTP + SSE 的 MCP Server
  - `mcp_sse_client.py`：SSE Client + LLM 循环（会启动 server）
- `streamable_http/`
  - `mcp_streamable_http_server.py`：HTTP JSON 的 MCP Server
  - `mcp_streamable_http_client.py`：Streamable HTTP Client + LLM 循环（会启动 server）
- `stdio_tavily/`
  - `mcp_stdio_tavily_client.py`：通过 stdio 连接 `tavily-mcp`（`npx`）
- `streamable_http_tavily/`
  - `mcp_streamable_http_tavily_client.py`：通过远程 Streamable HTTP（SSE）连接 Tavily
- `docs/`：MCP 协议笔记与实现分析文档集

## 备注

- 默认端口：SSE server 使用 `127.0.0.1:8765`，Streamable HTTP server 使用 `127.0.0.1:8766`。
- 如果模型持续调用工具，client 会在达到最大轮数后返回 `Max iterations reached`。

## MCP 参考

- MCP 架构总览: https://modelcontextprotocol.io/docs/learn/architecture
- MCP 规范总览: https://modelcontextprotocol.io/specification/2025-11-25
- MCP tools 规范: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- MCP 传输规范（stdio / streamable http）: https://modelcontextprotocol.io/specification/2025-06-18/basic/transports

---

## 许可证

MIT

────────────────────────────────────────

⏺ *如同一粒种子长成森林，一个文件化作无限可能。*
