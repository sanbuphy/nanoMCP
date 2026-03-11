# 官方 MCP (Model Context Protocol) 介绍

> English version: [official-mcp-introduction.en.md](./official-mcp-introduction.en.md)
>
> 本文档基于 [MCP 官方文档](https://modelcontextprotocol.io/docs/getting-started/intro) 编写，结合了实际项目案例进行说明。

一句话说清楚（分点）：
- **针对的问题**：AI 客户端对接外部系统时协议/参数/返回/传输各自为政，导致每接一个客户端就要重写一套插件，生态碎片化且难复用
- **MCP 定义了什么**：
  - **（1）消息与握手**：基于 JSON-RPC 2.0 的统一消息格式 + 生命周期初始化（initialize/initialized）+ capabilities 能力协商
  - **（2）标准能力对象**：Tools / Resources / Prompts 三类原语，以及配套的 list/read/get/call 方法与数据结构
  - **（3）传输与通知约定**：stdio、Streamable HTTP/SSE 等 transport 抽象，以及 list_changed/updated 等通知模式
- **实现的效果**：Server 一次实现，多 Host/Client 互通；能力可发现、可调用、可订阅，集成成本显著下降且更易做权限、安全与审计

为什么需要它 / 做了什么 / 达成什么效果：
- **问题**：没有统一标准时，每个 AI 客户端与每个外部系统都要单独适配（工具名、参数结构、返回格式、鉴权、传输、错误语义都不一致），生态碎片化且难复用
- **做法**：用 JSON-RPC 2.0 定义统一消息外壳与方法集合，并通过初始化阶段协商 capabilities，让“能提供什么/能处理什么”变成可声明、可验证的契约
- **效果**：Server 一次实现，多个 Host/Client 可复用；工具/资源/提示模板可发现、可调用、可订阅，工程上更容易做权限、审计、UI 呈现与安全确认

**相关文档**：
- [Kimi CLI MCP 实现分析](./kimi-cli-mcp-implementation-analysis.md) - 基于 fastmcp (Python) 的实现
- [Gemini CLI MCP 实现分析](./gemini-cli-mcp-implementation-analysis.md) - 基于 @modelcontextprotocol/sdk (TypeScript) 的实现

**本文目标**：
- 把 “MCP 是什么” 讲清楚
- 把 “MCP 协议里到底传什么 JSON” 讲清楚（数据结构 + 示例）
- 把 “怎么写 MCP Server / Client” 讲清楚（从最小可用到可扩展）

---

## 什么是 MCP?

MCP (Model Context Protocol，模型上下文协议) 是一个开源标准，用于将 AI 应用程序连接到外部系统。通过 MCP，AI 应用程序（如 Claude 或 ChatGPT）可以连接到：

- **数据源**（如本地文件、数据库）
- **工具**（如搜索引擎、计算器）
- **工作流**（如专门的提示词）

这使得 AI 能够访问关键信息并执行任务。

### 类比：USB-C 接口

将 MCP 想象成 AI 应用程序的 USB-C 接口。就像 USB-C 提供了连接电子设备的标准化方式一样，MCP 提供了将 AI 应用程序连接到外部系统的标准化方式。

## MCP 能实现什么?

1. **个性化 AI 助手**：AI 代理可以访问你的 Google Calendar 和 Notion，充当更个性化的 AI 助手。

2. **跨平台开发**：Claude Code 可以使用 Figma 设计生成完整的 Web 应用程序。

3. **企业数据分析**：企业聊天机器人可以连接组织内的多个数据库，使用户能够通过聊天分析数据。

4. **创意设计与制造**：AI 模型可以在 Blender 上创建 3D 设计，并使用 3D 打印机打印出来。

## 为什么 MCP 重要?

MCP 为生态系统中的不同角色带来各种好处：

### 对开发者

- 减少构建 AI 应用程序或代理时的开发时间和复杂性
- 简化与现有系统的集成

### 对 AI 应用程序或代理

- 访问数据源、工具和应用程序的生态系统
- 增强能力并改善最终用户体验
- 一次构建，到处集成

### 对最终用户

- 更强大的 AI 应用程序或代理
- AI 可以访问你的数据并在必要时代表你采取行动

## 广泛的生态系统支持

MCP 是一个开放协议，在广泛的客户端和服务器中得到支持。支持 MCP 的工具包括：

- **AI 助手**：Claude、ChatGPT
- **开发工具**：Visual Studio Code、Cursor、MCPJam 等

这种广泛的支持使得"一次构建，随处集成"成为可能。

## 开始构建

MCP 提供三条主要的构建路径：

### 1. 构建服务器 (Build Servers)
创建 MCP 服务器以暴露你的数据和工具给 AI 应用程序使用。

### 2. 构建客户端 (Build Clients)
开发连接到 MCP 服务器的应用程序。

### 3. 构建 MCP 应用 (Build MCP Apps)
构建在 AI 客户端内运行的交互式应用程序。

## 核心概念

### 架构组件

MCP 的核心架构包括三个主要组件：

1. **Host（主机）**：运行 AI 模型的应用程序（如 IDE、聊天界面）
2. **Client（客户端）**：实现 MCP 协议的库
3. **Server（服务器）**：提供工具、资源和提示词的应用程序

### 连接方式

MCP 支持多种连接方式：

- **本地进程**：通过 stdio 连接本地运行的 MCP 服务器
- **HTTP/SSE**：通过网络连接远程 MCP 服务器
- **直接集成**：服务器作为库直接嵌入到应用程序中

### 数据交换

MCP 使用标准化的消息格式进行数据交换：

- **工具 (Tools)**：可以调用的函数
- **资源 (Resources)**：可以读取的数据
- **提示词 (Prompts)**：可重用的模板

## 协议与数据结构（重点）

MCP 的“数据层”协议本质上是 **JSON-RPC 2.0** 的一套约定：用统一的消息封装（request/response/notification），再定义一组标准 `method`（如 `tools/list`、`resources/read` 等）以及这些方法对应的 `params/result` 数据结构。

下面从最底层的 JSON 外壳开始，一层层把 MCP 的数据结构讲清楚。

### 1) JSON-RPC 外壳：Request / Response / Notification

**Request（有 id，必须回复）**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

**Response（同 id，二选一：result 或 error）**

成功：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": { "tools": [] }
}
```

失败（协议级错误，典型是参数不合法 / 方法不存在）：

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": { "code": -32602, "message": "Invalid params" }
}
```

**Notification（没有 id，不允许回复）**

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/tools/list_changed"
}
```

**通用约定**
- `jsonrpc` 必须是 `"2.0"`
- `id` 必须是 string/number，且不能为 null
- `method` 是字符串，MCP 约定形如 `tools/list`、`resources/read` 这种“命名空间/动作”格式
- `params` / `result` 通常是 JSON Object
- `params._meta` 是保留字段：协议允许双方携带元信息（例如进度 token），不要把业务字段塞进 `_meta` 里

### 2) 生命周期：initialize → notifications/initialized

在任何 `tools/list` / `resources/list` 之前，必须先做一次初始化握手：**协商协议版本 + 能力（capabilities）**。

**initialize（Client → Server）**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-11-25",
    "capabilities": {
      "roots": { "listChanged": true },
      "sampling": {}
    },
    "clientInfo": { "name": "ExampleClient", "version": "1.0.0" }
  }
}
```

**initialize result（Server → Client）**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-11-25",
    "capabilities": {
      "tools": { "listChanged": true },
      "resources": { "subscribe": true, "listChanged": true },
      "prompts": { "listChanged": true },
      "logging": {}
    },
    "serverInfo": { "name": "ExampleServer", "version": "1.0.0" }
  }
}
```

**notifications/initialized（Client → Server）**

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

能力协商的关键点：
- Client 在 initialize 的 `capabilities` 里声明“我能处理什么服务器侧请求/通知”（例如能否处理 roots、sampling 等 client features）
- Server 在 initialize result 里声明“我提供什么能力”（tools/resources/prompts/logging…）
- 后续只能使用双方协商成功的能力：例如 server 没声明 `resources.subscribe=true`，client 就不该发 `resources/subscribe`

### 3) MCP 三大原语（Primitives）：Tools / Resources / Prompts

可以把 MCP Server 理解为“暴露三类对象”：
- Tools：可执行动作（函数调用）
- Resources：可读取的上下文数据（按 URI 定位）
- Prompts：可复用的提示模板（按 name 定位）

这三类对象都有一致的模式：**list 用于发现**，**get/read 用于获取内容**，**call 用于执行（只对 tools）**。

#### 3.1 Tools（工具）

**Tool 定义结构（server 在 tools/list 里返回）**

```json
{
  "name": "get_weather",
  "title": "Weather Information Provider",
  "description": "Get current weather information for a location",
  "inputSchema": {
    "type": "object",
    "properties": {
      "location": { "type": "string", "description": "City name or zip code" }
    },
    "required": ["location"]
  }
}
```

字段理解：
- `name`：工具唯一标识（建议只用字母/数字/下划线/点/横线）
- `title` / `description`：给 UI/人看的说明
- `inputSchema`：JSON Schema（定义 `tools/call` 的 `arguments` 形状）
-（可选）`outputSchema`：约束结构化返回
-（可选）`icons` / `annotations` / `execution`：用于 UI 呈现、优先级、任务化执行等

**列出工具：tools/list**

请求：

```json
{ "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {} }
```

响应：

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": { "tools": [ { "name": "get_weather", "description": "...", "inputSchema": { "type": "object" } } ] }
}
```

**调用工具：tools/call**

请求：

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "get_weather",
    "arguments": { "location": "New York" }
  }
}
```

响应（注意：这是“工具执行结果”，不是 JSON-RPC error）：

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      { "type": "text", "text": "Current weather in New York: 72°F" }
    ],
    "isError": false
  }
}
```

##### ToolResult.content：ContentBlock（统一内容块）

MCP 用 `content: ContentBlock[]` 表达“给模型/用户的返回内容”。常见类型：

**TextContent**

```json
{ "type": "text", "text": "hello" }
```

**ImageContent / AudioContent（base64）**

```json
{ "type": "image", "mimeType": "image/png", "data": "..." }
```

**ResourceLink（返回一个可被读取/订阅的资源链接）**

```json
{
  "type": "resource_link",
  "name": "readme",
  "uri": "file:///project/README.md",
  "mimeType": "text/markdown"
}
```

**EmbeddedResource（把资源内容直接嵌进返回）**

```json
{
  "type": "resource",
  "resource": {
    "uri": "file:///project/README.md",
    "mimeType": "text/markdown",
    "text": "# Project"
  }
}
```

#### 3.2 Resources（资源）

Resource 的核心是：**用 URI 做定位**，通过 `resources/read` 读取内容。

**Resource 定义结构（server 在 resources/list 里返回）**

```json
{
  "uri": "file:///project/src/main.rs",
  "name": "main.rs",
  "title": "Rust Software Application Main File",
  "description": "Primary application entry point",
  "mimeType": "text/x-rust"
}
```

**列出资源：resources/list**

```json
{ "jsonrpc": "2.0", "id": 10, "method": "resources/list", "params": {} }
```

响应：

```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "result": { "resources": [ { "uri": "file:///project/src/main.rs", "name": "main.rs" } ] }
}
```

**读取资源：resources/read**

```json
{
  "jsonrpc": "2.0",
  "id": 11,
  "method": "resources/read",
  "params": { "uri": "file:///project/src/main.rs" }
}
```

响应（注意 `contents` 是数组，允许同一 uri 有多份分片内容）：

```json
{
  "jsonrpc": "2.0",
  "id": 11,
  "result": {
    "contents": [
      {
        "uri": "file:///project/src/main.rs",
        "mimeType": "text/x-rust",
        "text": "fn main() { println!(\"Hello world!\"); }"
      }
    ]
  }
}
```

**（可选）订阅资源变更：resources/subscribe**

```json
{ "jsonrpc": "2.0", "id": 12, "method": "resources/subscribe", "params": { "uri": "file:///project/src/main.rs" } }
```

资源更新通知（server → client）：

```json
{ "jsonrpc": "2.0", "method": "notifications/resources/updated", "params": { "uri": "file:///project/src/main.rs" } }
```

#### 3.3 Prompts（提示词模板）

Prompt 的核心是：**让 server 提供可复用的消息模板**，由用户/应用选择使用，必要时传入参数。

**Prompt 定义结构（server 在 prompts/list 里返回）**

```json
{
  "name": "code_review",
  "title": "Request Code Review",
  "description": "Asks the LLM to analyze code quality and suggest improvements",
  "arguments": [
    { "name": "code", "description": "The code to review", "required": true }
  ]
}
```

**列出 prompts：prompts/list**

```json
{ "jsonrpc": "2.0", "id": 20, "method": "prompts/list", "params": {} }
```

**获取 prompt：prompts/get**

```json
{
  "jsonrpc": "2.0",
  "id": 21,
  "method": "prompts/get",
  "params": { "name": "code_review", "arguments": { "code": "print('hi')" } }
}
```

响应（关键是 `messages`，每条消息有 role + content）：

```json
{
  "jsonrpc": "2.0",
  "id": 21,
  "result": {
    "description": "Code review prompt",
    "messages": [
      { "role": "user", "content": { "type": "text", "text": "Please review this code: print('hi')" } }
    ]
  }
}
```

### 4) 错误处理：协议错误 vs 执行错误

很多人第一次实现 MCP 时最容易混淆的点是：**什么时候用 JSON-RPC error，什么时候用 ToolResult.isError**。

- **JSON-RPC error（error 字段）**：协议层面出错（method 不存在、params 结构不合法、资源不存在、权限拒绝等）
- **ToolResult.isError=true**：工具本身执行失败（第三方 API 报错、业务校验失败、运行时异常等），但协议调用是成功完成的

示例：调用了不存在的工具（协议错误）

```json
{
  "jsonrpc": "2.0",
  "id": 30,
  "error": { "code": -32602, "message": "Unknown tool: invalid_tool_name" }
}
```

示例：工具存在，但执行失败（执行错误）

```json
{
  "jsonrpc": "2.0",
  "id": 31,
  "result": {
    "content": [ { "type": "text", "text": "API rate limit exceeded" } ],
    "isError": true
  }
}
```

## 开发指南：怎么写 MCP Server（从最小可用到可扩展）

### 最小可用 Server 要做什么

如果只支持 tools，你至少要实现 3 个方法：
- `initialize`：返回 server capabilities（至少包含 `tools`）
- `tools/list`：返回 tools 定义（含 `inputSchema`）
- `tools/call`：执行工具并返回 `content[]`

同时要满足 3 个工程性要求：
- 参数校验：按照 `inputSchema` 以及业务规则校验 `arguments`
- 输出约束：输出尽量结构化、可读，并避免泄露敏感信息
- 安全设计：让宿主应用能做 “人类确认”（尤其是写入/删除/外部网络请求类工具）

### 用本仓库的 nanoMCP 写一个最小 Server（in-memory）

本仓库提供了一个极简的示例 Server：`FakeMCPServer`，用于演示 MCP 的 JSON-RPC 交互（不依赖真实网络/进程）。

同时也提供了按 transport 分类的可运行示例：
- `stdio/mcp_stdio_server.py`：stdio server
- `sse/mcp_sse_server.py`：SSE server
- `streamable_http/mcp_streamable_http_server.py`：streamable_http server

参考实现：[server.py](file:///Users/sanbu/Code/2026重要开源项目/nanoMCP/nanomcp/server.py)

```python
from nanomcp.server import FakeMCPServer


def add_handler(args: dict) -> dict:
    a = int(args["a"])
    b = int(args["b"])
    return {"type": "text", "text": str(a + b)}


server = FakeMCPServer(
    name="demo",
    version="0.1.0",
    tools=[
        {
            "name": "add",
            "description": "Add two integers",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"}
                },
                "required": ["a", "b"]
            },
        }
    ],
    handlers={"add": add_handler},
)
```

这个 server 的行为对应 MCP 的关键结构：
- `tools/list` 返回 `tools: [...]`
- `tools/call` 返回 `result: { content: [...], isError: false }`
- 不存在的工具返回 JSON-RPC error（`-32602`）

### 生产级 Server 通常还需要什么

- Resources：用 `resources/list`/`resources/read` 提供上下文数据（比“工具里返回一大段文本”更可控、更可缓存）
- Prompts：用 `prompts/list`/`prompts/get` 提供可复用模板（方便 UI 以命令形式暴露）
- 通知与订阅：例如 `notifications/tools/list_changed`、`resources/subscribe` + `notifications/resources/updated`
- 超时/取消/进度：长任务用 progress + cancelled（否则容易让 host 卡死）
- 认证与权限：远程 HTTP transport 需要认证策略（一般用 OAuth 或 bearer token）

## 开发指南：怎么写 MCP Client / Host（从连接到调用）

这里的 “Client” 指的是 **MCP 客户端组件**：它负责维护与某个 MCP Server 的连接，按协议收发 JSON-RPC 消息（initialize、tools/list、tools/call…），并把返回结果交给 **Host（宿主应用）** 统一调度（例如让 LLM 选择工具、把工具结果写回对话上下文）。简单理解：
- **Host**：你的 AI 应用本体（IDE、聊天应用、Agent 框架），管理模型与多个 Server 的整体工作流
- **Client**：每个 Server 对应一个“协议适配器 + 连接管理器”（一对一维护连接、请求 ID、超时等）
- **Server**：真正实现 Tools/Resources/Prompts 的提供方

Client 的核心职责可以拆成 4 步：
1. 建立连接（stdio / http/sse / 其他 transport）
2. 初始化握手（initialize + notifications/initialized）
3. 发现能力（tools/list / resources/list / prompts/list）
4. 组织调用（tools/call / resources/read / prompts/get），把结果交给宿主应用/模型

### 用本仓库的 nanoMCP 写一个最小 Client

参考实现：[client.py](file:///Users/sanbu/Code/2026重要开源项目/nanoMCP/nanomcp/client.py)

```python
from nanomcp.client import NanoMCPClient


client = NanoMCPClient(server_name="demo", server=server)
client.initialize()
tools = client.list_tools()
result = client.call_tool("add", {"a": 1, "b": 2})
```

### 当你要管理多个 MCP Server：注册表（Registry）

宿主应用通常要同时连接多个 server，并把不同 server 的工具整合成一个 “可用工具池”。

参考实现：[registry.py](file:///Users/sanbu/Code/2026重要开源项目/nanoMCP/nanomcp/registry.py)

```python
from nanomcp.registry import MCPRegistry


registry = MCPRegistry()
registry.register_server("math", server, transport="inmemory")

registry.initialize_all()
all_tools = registry.list_tools()

resp = registry.call_tool("math.add", {"a": 10, "b": 20})
```

### transport 的直觉：stdio vs SSE/HTTP

MCP 规定了“协议长什么样”（JSON-RPC），也规定了常见的 transport：
- **stdio**：本地子进程，最常见于 Claude Desktop / IDE 集成
- **Streamable HTTP（可选 SSE）**：远程服务，适合团队/企业内服务化部署

本仓库提供了一个最小 transport 演示客户端（用序列化/反序列化模拟传输）：
[transport.py](file:///Users/sanbu/Code/2026重要开源项目/nanoMCP/nanomcp/transport.py)

另外也提供了按目录区分的三组端到端示例：
- `stdio/mcp_stdio_client.py` + `stdio/mcp_stdio_server.py`
- `sse/mcp_sse_client.py` + `sse/mcp_sse_server.py`
- `streamable_http/mcp_streamable_http_client.py` + `streamable_http/mcp_streamable_http_server.py`

## 交互时序（把一切串起来）

一个典型会话大概长这样：

1. Client → Server：`initialize`
2. Server → Client：`initialize result`
3. Client → Server：`notifications/initialized`
4. Client → Server：`tools/list`
5. Server → Client：`tools/list result`
6.（模型决定要用哪个工具）Client → Server：`tools/call`
7. Server → Client：`tools/call result`（`content[]`）
8.（可选）Server → Client：`notifications/tools/list_changed`

## 安全性

MCP 将安全作为核心设计原则：

- 用户必须明确授权连接到 MCP 服务器
- 服务器可以被启用/禁用
- 支持访问控制列表（allowlist/excludelist）
- OAuth 认证支持远程服务器

## 规范与生态系统

- **开放规范**：MCP 规范公开可用，任何人都可以实现
- **多语言 SDK**：提供 TypeScript、Python 等多种语言的 SDK
- **服务器注册表**：社区维护的可用 MCP 服务器列表
- **社区提案 (SEPs)**：通过 SEP 流程持续改进协议

## 相关资源

- [MCP 规范](https://modelcontextprotocol.io/specification)
- [架构详解](https://modelcontextprotocol.io/docs/about/architecture)
- [SDK 文档](https://modelcontextprotocol.io/docs/developing-mcp/sdk)
- [服务器注册表](https://github.com/modelcontextprotocol/servers)
- [GitHub 仓库](https://github.com/modelcontextprotocol)

## 总结

MCP 通过提供一个标准化的协议，解决了 AI 应用程序与外部系统集成时的碎片化问题。它使得：

1. **开发者**可以更容易地构建 AI 集成
2. **AI 应用**可以访问丰富的数据和能力
3. **用户**可以获得更强大、更个性化的 AI 体验

就像 USB-C 接口统一了设备连接一样，MCP 正在统一 AI 应用与世界的连接方式。
