# nanoMCP

[English](./README.md) | 中文

> *"问题不在于你看到了什么，而在于你看见了什么。"* — 梭罗

用最简单的方式理解 MCP，并跑通一个最小多 MCP Agent 流程。

这是一个最小实现，包含：
- MCP 核心 JSON-RPC 形态（`initialize`、`tools/list`、`tools/call`）
- 自研 MCP 与官方 MCP 两条路径下的 fake MCP server 注册
- 三个 nanoAgent 风格 Agent（自研 MCP / 官方 MCP / 官方 real MCP 示例）

## 版本

v0.1.0

## 安装

```bash
pip install -r requirements.txt
```

设置环境变量：

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

## 快速开始

```bash
python agent.py "先列出所有 MCP 工具，再调用 math.add 计算 7 + 5"
python agent-official.py "先列出所有 MCP 工具，再调用 math.add 计算 7 + 5"
python agent_official_mcp.py "给出 tavily/context7 的安装配置与一次调用示例"
```

三种入口分别对应：
- `agent.py`：调用自研 `nanomcp` fake 注册
- `agent-official.py`：调用 `officialmcp` fake 注册
- `agent_official_mcp.py`：官方 MCP real 接入模板（Tavily / Context7）

## 项目结构

当前仓库有两个目录：
- `nanomcp`：自实现 MCP 协议 + 多传输支持 + 多 server 注册中心
- `officialmcp`：官方 MCP Python SDK（`mcp.server.fastmcp.FastMCP`）封装

`nanomcp` 保持 nanoAgent 的极简思路：一个最小循环 + 一个最小传输抽象。

## 工作原理

`nanomcp` 提供最小 MCP 数据层模拟：
1. Host 向每个 server 发送 `initialize`
2. Host 通过 `tools/list` 聚合工具
3. Agent 调用 `call_mcp_tool`
4. Registry 将调用路由到目标 server 的 `tools/call`
5. 工具结果回到模型循环

核心依然是一条简单链路：
模型调用 → 工具调用 → 工具结果 → 模型调用。

## 本仓库实现的最小 MCP 形态

- JSON-RPC 2.0 报文外壳
- 生命周期握手（`initialize`）
- 工具发现（`tools/list`）
- 工具调用（`tools/call`）
- `tools` capability 字段

## 内置 fake MCP servers

- `math` server
  - `math.add`
  - `math.multiply`
- `utility` server
  - `utility.echo`
  - `utility.search`（fake 结果）
- `meta` server
  - `meta.version`

这些 fake servers 支持两种注册方式：
- `nanomcp` 自研注册中心（`build_default_registry`）
- `officialmcp` 官方 SDK 注册中心（`build_official_fake_registry`）

## nanomcp 内置传输

- `inmemory`：进程内直接 JSON-RPC 调用
- `stdio`：按行 JSON 消息
- `sse`：HTTP post + SSE 事件流响应
- `streamable_http`：HTTP JSON 请求/响应风格

## 文件映射

- `nanomcp/protocol.py`：JSON-RPC 报文与请求构造
- `nanomcp/server.py`：最小 MCP server（`initialize`、`tools/list`、`tools/call`）
- `nanomcp/client.py`：in-memory MCP client
- `nanomcp/transport.py`：统一传输 client（`stdio` / `sse` / `streamable_http`）
- `nanomcp/registry.py`：多 MCP 注册与路由
- `nanomcp/builtin.py`：内置 fake servers 与 handlers
- `officialmcp/registry.py`：官方 SDK 注册封装
- `agent.py`：调用自研 nanomcp fake 注册
- `agent-official.py`：调用 officialmcp fake 注册
- `agent_official_mcp.py`：官方 MCP real 接入模板（tavily/context7）
- `smoke_test.py`：可直接 python 运行的冒烟校验

## officialmcp 快速用法

```python
from officialmcp import build_official_fake_registry

registry = build_official_fake_registry()
registry.run(transport="stdio")
```

## 官方 real MCP 示例（Tavily / Context7）

`agent_official_mcp.py` 提供官方 MCP 的真实接入模板，内置：
- `list_real_mcp_servers`：查看 Context7 / Tavily 的 server 模板
- `get_mcp_install_examples`：输出 `npx` 安装命令和 `mcpServers` 配置示例
- `call_real_mcp_example`：给出 `tools/call` 的 JSON-RPC 调用示例

推荐先设置：

```bash
export CONTEXT7_API_KEY='your-context7-key'
export TAVILY_API_KEY='your-tavily-key'
```

然后查看示例：

```bash
python agent_official_mcp.py "先列出 real mcp servers，再给我安装命令和配置"
python agent_official_mcp.py "给我一条 tavily 的 tools/call 示例，query=latest mcp news"
python agent_official_mcp.py "给我一条 context7 的 tools/call 示例，query=fastmcp tool"
```

`agent_official_mcp.py` 内置的 `npx` 配置模板：
- Context7: `npx -y @upstash/context7-mcp`
- Tavily: `npx -y tavily-mcp@latest`

## 运行校验

```bash
python smoke_test.py
```

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
