# MCP 深度解析：从原理到实践

> English version: [mcp-deep-dive-guide.en.md](./mcp-deep-dive-guide.en.md)
>
> 本文详细解释 Model Context Protocol (MCP) 的工作原理，包括 JSON Schema 基础、MCP 与 Function Calling 的区别、如何解决 NxM 集成复杂度问题，以及完整的代码示例。

---

## 目录

- [1. MCP 核心概念](#1-mcp-核心概念)
- [2. JSON Schema 基础](#2-json-schema-基础)
- [3. MCP vs Function Calling](#3-mcp-vs-function-calling)
- [4. MCP 解决的 NxM 问题](#4-mcp-解决的-nxm-问题)
- [5. MCP 工作原理详解](#5-mcp-工作原理详解)
- [6. 配置文件如何工作](#6-配置文件如何工作)
- [7. 为什么只需写一次](#7-为什么只需写一次)
- [8. 完整代码示例](#8-完整代码示例)
- [9. 总结](#9-总结)

---

## 1. MCP 核心概念

### 什么是 MCP？

**Model Context Protocol (MCP)** 是一个开放协议，用于在 LLM（大语言模型）应用和外部数据源/工具之间建立标准化连接。

#### 类比：MCP 就像 AI 界的 USB 标准

```
┌─────────────────────────────────────────────────────────┐
│ USB 生态系统                                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  鼠标厂商 ──[遵循 USB 协议]──> USB 标准                 │
│                                ↓                        │
│  Windows ──[实现 USB 驱动]──> 识别并使用鼠标            │
│  Mac     ──[实现 USB 驱动]──> 识别并使用鼠标            │
│  Linux   ──[实现 USB 驱动]──> 识别并使用鼠标            │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ MCP 生态系统                                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Tavily ──[遵循 MCP 协议]──> MCP 标准                   │
│                            ↓                            │
│  Claude Desktop ──[实现 MCP 客户端]──> 使用 Tavily      │
│  Cursor IDE     ──[实现 MCP 客户端]──> 使用 Tavily      │
│  自定义应用     ──[实现 MCP 客户端]──> 使用 Tavily      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### MCP 的核心组件

```
┌──────────────────────────────────────────────────────────┐
│                    MCP 架构                              │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────┐         ┌─────────────┐                │
│  │ MCP 服务器  │         │ MCP 客户端  │                │
│  │             │         │             │                │
│  │ • 暴露工具  │<------->│ • 连接服务器│                │
│  │ • 暴露资源  │ JSON-RPC│ • 获取工具  │                │
│  │ • 暴露提示  │         │ • 调用工具  │                │
│  │             │         │ • 格式转换  │                │
│  └─────────────┘         └─────────────┘                │
│       ↓                        ↓                         │
│  Tavily/GitHub/Slack    Claude/Cursor/自定义应用         │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## 2. JSON Schema 基础

### 什么是 JSON Schema？

**JSON Schema** 是一种用于描述 JSON 数据结构的格式。它定义了：
- 数据的类型（string, number, object, array 等）
- 必需字段
- 字段的约束条件（最小值、最大值、枚举值等）

### 基本示例

#### 简单的 JSON Schema

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "用户姓名"
    },
    "age": {
      "type": "integer",
      "description": "用户年龄",
      "minimum": 0,
      "maximum": 150
    },
    "email": {
      "type": "string",
      "format": "email",
      "description": "用户邮箱"
    }
  },
  "required": ["name", "email"]
}
```

#### 对应的有效 JSON 数据

```json
{
  "name": "张三",
  "age": 25,
  "email": "zhangsan@example.com"
}
```

#### 无效的 JSON 数据

```json
{
  "age": 25,
  "email": "zhangsan@example.com"
  // ❌ 缺少必需的 "name" 字段
}
```

### 在 MCP 中的应用

MCP 使用 JSON Schema 来描述工具的输入参数：

```python
# MCP 服务器定义工具

@mcp.tool()
def search_web(
    query: str,                    # string 类型
    max_results: int = 10,         # integer 类型，默认值 10
    search_depth: str = "basic"    # string 类型，默认值 "basic"
) -> str:
    """
    搜索网络获取最新信息

    这个函数会被自动转换为以下 JSON Schema：
    """
    pass

# 自动转换为：
{
  "name": "search_web",
  "description": "搜索网络获取最新信息",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "搜索关键词"
      },
      "max_results": {
        "type": "integer",
        "description": "最大结果数",
        "default": 10
      },
      "search_depth": {
        "type": "string",
        "description": "搜索深度",
        "default": "basic",
        "enum": ["basic", "advanced"]
      }
    },
    "required": ["query"]
  }
}
```

### 为什么 JSON Schema 重要？

1. **统一性**：各大 LLM 都使用 JSON Schema 描述工具
2. **可验证**：可以验证参数是否符合要求
3. **自描述**：包含类型和描述信息，LLM 能理解
4. **互操作性**：不同系统之间可以交换工具定义

---

## 3. MCP vs Function Calling

### 核心区别

```
┌─────────────────────────────────────────────────────────┐
│ MCP vs Function Calling                                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  MCP（协议标准）                                        │
│  ────────────────────                                  │
│  • 定义如何暴露工具                                     │
│  • 定义通信协议（JSON-RPC）                             │
│  • 定义工具描述格式（JSON Schema）                      │
│  • 类似 USB 接口标准                                    │
│                                                         │
│  Function Calling（执行机制）                           │
│  ─────────────────────────────                         │
│  • LLM 如何调用工具                                     │
│  • 如何传递参数                                         │
│  • 如何接收返回结果                                     │
│  • 类似设备驱动程序                                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 详细对比

| 方面 | MCP | Function Calling |
|------|-----|------------------|
| **本质** | 协议标准 | 执行机制 |
| **定义者** | MCP 官方规范 | 各 LLM 提供商 |
| **作用** | 统一工具暴露方式 | LLM 调用工具的方式 |
| **协议** | JSON-RPC 2.0 | 各不相同（HTTP/WebSocket） |
| **工具格式** | 统一的 `inputSchema` | Claude: `input_schema`<br>OpenAI: `parameters`<br>Gemini: `parameters` |
| **关系** | MCP 使用 Function Calling 作为底层执行机制 | Function Calling 可以调用 MCP 工具 |

### MCP 与 Function Calling 的协作

```
┌─────────────────────────────────────────────────────────┐
│ MCP 如何使用 Function Calling                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. MCP 服务器暴露工具                                  │
│     ↓                                                   │
│  2. MCP 客户端获取工具列表                              │
│     ↓                                                   │
│  3. 客户端将 MCP 工具转换为 LLM 格式                    │
│     ↓                                                   │
│  4. LLM 使用 Function Calling 决定调用哪个工具          │
│     ↓                                                   │
│  5. 客户端拦截工具调用，转发给 MCP 服务器               │
│     ↓                                                   │
│  6. MCP 服务器执行并返回结果                            │
│     ↓                                                   │
│  7. 客户端将结果转给 LLM                                │
│     ↓                                                   │
│  8. LLM 生成最终答案                                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 4. MCP 解决的 NxM 问题

### 问题描述：传统方式的集成复杂度

假设你有 3 个 LLM 应用和 3 个工具需要集成：

#### ❌ 传统方式（无 MCP）

```
要做的集成：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Claude Desktop  →  Tavily API  (需要写 1 次集成代码)
Claude Desktop  →  GitHub API  (需要写 1 次集成代码)
Claude Desktop  →  Slack API   (需要写 1 次集成代码)

Cursor IDE     →  Tavily API  (需要写 1 次集成代码)
Cursor IDE     →  GitHub API  (需要写 1 次集成代码)
Cursor IDE     →  Slack API   (需要写 1 次集成代码)

自定义应用     →  Tavily API  (需要写 1 次集成代码)
自定义应用     →  GitHub API  (需要写 1 次集成代码)
自定义应用     →  Slack API   (需要写 1 次集成代码)

总计：3 × 3 = 9 次集成 🫠
```

#### 问题详情

**1. 工具定义格式不统一**

```typescript
// Claude 格式
const claudeTool = {
  name: 'search',
  description: '搜索网络',
  input_schema: {              // ← 注意：input_schema
    type: 'object',
    properties: {
      query: { type: 'string' }
    }
  }
};

// OpenAI 格式
const openaiTool = {
  type: 'function',
  function: {
    name: 'search',
    description: '搜索网络',
    parameters: {                // ← 注意：parameters
      type: 'object',
      properties: {
        query: { type: 'string' }
      }
    }
  }
};

// Gemini 格式
const geminiTool = {
  name: 'search',
  description: '搜索网络',
  parameters: {                  // ← 注意：parameters
    type: 'object',
    properties: {
      query: { type: 'string' },
      maxResults: { type: 'integer' }  // ← 注意：camelCase
    }
  }
};
```

**2. API 调用方式不同**

```typescript
// Claude API 调用
const response = await anthropic.messages.create({
  model: 'claude-3-5-sonnet-20241022',
  tools: [claudeTool],
  messages: [...]
});

// OpenAI API 调用
const response = await openai.chat.completions.create({
  model: 'gpt-4-turbo',
  tools: [openaiTool],
  messages: [...]
});

// Gemini API 调用
const model = genAI.getGenerativeModel({ model: 'gemini-pro' });
const response = await model.generateContent(prompt);
```

**3. 工具调用结构不同**

```typescript
// Claude 的工具调用
{
  type: 'tool_use',
  id: 'toolu_xxx',
  name: 'search',
  input: { query: 'test' }
}

// OpenAI 的工具调用
{
  id: 'call_xxx',
  type: 'function',
  function: {
    name: 'search',
    arguments: '{"query":"test"}'  // ← JSON 字符串！
  }
}

// Gemini 的工具调用
{
  name: 'search',
  args: { query: 'test' }  // ← 直接是对象
}
```

#### ✅ MCP 方式

```
工具提供者只需写 1 次 MCP 服务器：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tavily MCP Server  (写 1 次，支持 stdio/HTTP)
GitHub MCP Server  (写 1 次，支持 stdio/HTTP)
Slack MCP Server   (写 1 次，支持 stdio/HTTP)

任何支持 MCP 的客户端都能用：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Claude Desktop  →  配置 .mcp.json  →  自动连接所有服务器
Cursor IDE     →  配置 .mcp.json  →  自动连接所有服务器
自定义应用     →  配置 .mcp.json  →  自动连接所有服务器

总计：3 个服务器 + N 个客户端配置 = 3 + N 🎉
```

### 复杂度对比

```
┌─────────────────────────────────────────────────────────┐
│ 传统方式：双向适配（NxM 复杂度）                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   工具提供者              LLM 客户端                     │
│      ↓                      ↓                           │
│  Tavily 团队            Claude Desktop                  │
│  ├─ Claude 适配         ├─ 实现 Claude 工具系统         │
│  ├─ OpenAI 适配         ├─ 为 Tavily 写适配            │
│  └─ Gemini 适配         ├─ 为 GitHub 写适配            │
│                         └─ 为 Slack 写适配              │
│                                                          │
│  GitHub 团队            Cursor IDE                       │
│  ├─ Claude 适配         ├─ 实现 OpenAI 工具系统         │
│  ├─ OpenAI 适配         ├─ 为 Tavily 写适配            │
│  └─ Gemini 适配         ├─ 为 GitHub 写适配            │
│                         └─ 为 Slack 写适配              │
│                                                          │
│  Slack 团队              自定义应用                      │
│  ├─ Claude 适配         ├─ 实现 Gemini 工具系统         │
│  ├─ OpenAI 适配         ├─ 为 Tavily 写适配            │
│  └─ Gemini 适配         ├─ 为 GitHub 写适配            │
│                         └─ 为 Slack 写适配              │
│                                                          │
│  结果：混乱、重复、难以维护                              │
│  总代码量：~450 行 × 3 = 1350+ 行                        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ MCP 方式：单向责任（N+M 复杂度）                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   工具提供者              LLM 客户端                     │
│      ↓                      ↓                           │
│  Tavily 团队            Claude Desktop                  │
│  └─ MCP 服务器          └─ MCP 客户端适配器             │
│     (50 行代码)             (200 行代码)                 │
│                             ↓                           │
│  GitHub 团队              自动能用所有                   │
│  └─ MCP 服务器          MCP 服务器！                    │
│     (100 行代码)                                        │
│                             ↓                           │
│  Slack 团队             Cursor IDE                       │
│  └─ MCP 服务器          └─ MCP 客户端适配器             │
│     (80 行代码)             (200 行代码)                 │
│                             ↓                           │
│                         自动能用所有                    │
│                         MCP 服务器！                     │
│                                                          │
│  结果：清晰、可复用、易维护                               │
│  总代码量：~230 行（服务器）+ 600 行（客户端）= 830 行   │
└─────────────────────────────────────────────────────────┘
```

---

## 5. MCP 工作原理详解

### 完整工作流程

```
┌─────────────────────────────────────────────────────────────┐
│ 步骤 1: Claude Desktop 启动                                  │
│ - 读取 ~/.claude/config.json 或项目的 .mcp.json             │
│ - 解析出要启动的 MCP 服务器列表                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤 2: 启动 MCP 服务器                                     │
│ - 执行: npx -y tavily-mcp                                   │
│ - 通过 stdio（标准输入/输出）建立通信管道                    │
│ - 服务器进程启动，等待 JSON-RPC 请求                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤 3: 初始化握手 (JSON-RPC)                               │
│                                                              │
│ Claude → Tavily:                                             │
│ {                                                            │
│   "jsonrpc": "2.0",                                         │
│   "id": 1,                                                  │
│   "method": "initialize",                                   │
│   "params": {                                               │
│     "protocolVersion": "2025-06-18",                        │
│     "capabilities": {                                       │
│       "roots": { "listChanged": true }                      │
│     },                                                      │
│     "clientInfo": {                                         │
│       "name": "claude-desktop",                             │
│       "version": "1.0.0"                                    │
│     }                                                       │
│   }                                                         │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Tavily → Claude:                                             │
│ {                                                            │
│   "jsonrpc": "2.0",                                         │
│   "id": 1,                                                  │
│   "result": {                                               │
│     "protocolVersion": "2025-06-18",                        │
│     "capabilities": {                                       │
│       "tools": {}    // ← 声明支持 tools                    │
│     },                                                      │
│     "serverInfo": {                                         │
│       "name": "tavily-mcp",                                 │
│       "version": "1.0.0"                                    │
│     }                                                       │
│   }                                                         │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤 4: 获取工具列表                                         │
│                                                              │
│ Claude → Tavily:                                             │
│ {                                                            │
│   "jsonrpc": "2.0",                                         │
│   "id": 2,                                                  │
│   "method": "tools/list"    // ← MCP 标准方法                │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Tavily → Claude:                                             │
│ {                                                            │
│   "jsonrpc": "2.0",                                         │
│   "id": 2,                                                  │
│   "result": {                                               │
│     "tools": [                                               │
│       {                                                      │
│         "name": "tavily_search",        // ← 工具名          │
│         "description": "搜索网络获取最新信息",               │
│         "inputSchema": {                                     │
│           "type": "object",                                  │
│           "properties": {                                    │
│             "query": {                                       │
│               "type": "string",                              │
│               "description": "搜索关键词"                    │
│             },                                               │
│             "max_results": {                                 │
│               "type": "integer",                             │
│               "description": "最大结果数",                   │
│               "default": 10                                  │
│             }                                                │
│           },                                                  │
│           "required": ["query"]                              │
│         }                                                     │
│       },                                                      │
│       {                                                      │
│         "name": "tavily_extract",                            │
│         "description": "提取网页内容",                        │
│         "inputSchema": { ... }                               │
│       },                                                      │
│       {                                                      │
│         "name": "tavily_research",                           │
│         "description": "深度研究",                            │
│         "inputSchema": { ... }                               │
│       }                                                      │
│     ]                                                        │
│   }                                                          │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤 5: Claude 把工具定义转换为自己的函数定义                │
│                                                              │
│ MCP 工具格式 → Claude 函数格式：                              │
│                                                              │
│ {                                                            │
│   "name": "tavily_search",                                   │
│   "description": "搜索网络获取最新信息",                      │
│   "input_schema": { ... }                                    │
│ }                                                            │
│                        ↓ 转换                                │
│                                                              │
│ 这个定义被添加到 Claude 的系统提示词中！                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤 6: 用户提问                                             │
│                                                              │
│ 用户: "搜索 MCP 相关信息"                                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤 7: Claude 决定调用工具                                   │
│                                                              │
│ Claude 的系统提示词包含：                                     │
│                                                              │
│ 你可以使用以下工具：                                          │
│ - mcp__tavily__tavily_search: 搜索网络获取最新信息           │
│ - mcp__tavily__tavily_extract: 提取网页内容                  │
│ - ...                                                       │
│                                                              │
│ Claude 分析用户意图 → 决定调用 tavily_search                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤 8: Function Calling (Claude API 调用)                   │
│                                                              │
│ Claude 生成:                                                 │
│ {                                                            │
│   "type": "tool_use",                                       │
│   "id": "toolu_xxx",                                        │
│   "name": "mcp__tavily__tavily_search",  // ← mcp__服务器名__工具名 │
│   "input": {                                                │
│     "query": "MCP",                                         │
│     "max_results": 5                                        │
│   }                                                         │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤 9: Claude Desktop 拦截工具调用                          │
│                                                              │
│ Claude Desktop 看到 "mcp__tavily__tavily_search":            │
│ 1. 解析出: 服务器 = tavily, 工具 = tavily_search             │
│ 2. 通过 stdio 向 Tavily MCP 发送 JSON-RPC:                   │
│                                                              │
│ {                                                            │
│   "jsonrpc": "2.0",                                         │
│   "id": 3,                                                  │
│   "method": "tools/call",    // ← MCP 标准方法                │
│   "params": {                                               │
│     "name": "tavily_search",                                │
│     "arguments": {                                          │
│       "query": "MCP",                                       │
│       "max_results": 5                                      │
│     }                                                       │
│   }                                                         │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤 10: Tavily MCP 执行搜索                                 │
│                                                              │
│ - Tavily MCP 调用 Tavily API                                 │
│ - 获取搜索结果                                               │
│ - 通过 stdio 返回:                                           │
│                                                              │
│ {                                                            │
│   "jsonrpc": "2.0",                                         │
│   "id": 3,                                                  │
│   "result": {                                               │
│     "content": [                                            │
│       {                                                      │
│         "type": "text",                                     │
│         "text": "搜索结果..."                                │
│       }                                                      │
│     ],                                                      │
│     "isError": false                                        │
│   }                                                          │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤 11: Claude Desktop 把结果转给 Claude                     │
│                                                              │
│ Claude Desktop 把 MCP 结果转换为 Claude API 格式:             │
│                                                              │
│ {                                                            │
│   "type": "tool_result",                                    │
│   "tool_use_id": "toolu_xxx",                               │
│   "content": "搜索结果..."                                    │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤 12: Claude 基于工具结果生成最终答案                      │
└─────────────────────────────────────────────────────────────┘
```

### 关键协议：JSON-RPC 2.0

MCP 使用 JSON-RPC 2.0 作为通信协议。JSON-RPC 是一个轻量级的远程过程调用协议。

#### 基本结构

```json
{
  "jsonrpc": "2.0",
  "method": "方法名",
  "params": { /* 参数 */ },
  "id": 1
}
```

#### MCP 定义的标准方法

```javascript
// 1. 初始化
{ "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {...} }

// 2. 列出工具
{ "jsonrpc": "2.0", "id": 2, "method": "tools/list" }

// 3. 调用工具
{ "jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {...} }

// 4. 列出资源
{ "jsonrpc": "2.0", "id": 4, "method": "resources/list" }

// 5. 读取资源
{ "jsonrpc": "2.0", "id": 5, "method": "resources/read", "params": {...} }
```

---

## 6. 配置文件如何工作

### 配置文件结构

```json
{
  "mcpServers": {
    "tavily": {                           // 服务器名称（自定义）
      "command": "npx",                   // 启动命令
      "args": ["-y", "tavily-mcp"],       // 命令参数
      "env": {                            // 环境变量
        "TAVILY_API_KEY": "tvly-..."
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "ghp_..."
      }
    }
  }
}
```

### 配置文件位置

| 应用 | 配置文件位置 |
|------|------------|
| Claude Desktop | `~/.claude/config.json` |
| Cursor | `~/.cursor/mcp.json` |
| 项目特定 | `.mcp.json`（项目根目录） |

### 配置文件解析流程

```typescript
// 伪代码：Claude Desktop 如何读取配置

async function loadMCPServers() {
  // 1. 读取全局配置
  const globalConfig = await readFile('~/.claude/config.json');

  // 2. 读取项目配置（如果存在）
  const projectConfig = await readFile('.mcp.json');

  // 3. 合并配置
  const allServers = {
    ...globalConfig.mcpServers,
    ...projectConfig.mcpServers
  };

  // 4. 启动所有服务器
  for (const [name, config] of Object.entries(allServers)) {
    await startMCPServer(name, config);
  }
}

async function startMCPServer(name, config) {
  // 1. 创建子进程
  const process = spawn(config.command, config.args, {
    env: { ...process.env, ...config.env }
  });

  // 2. 创建 MCP 客户端
  const client = new Client({
    name: "claude-desktop",
    version: "1.0.0"
  });

  // 3. 连接到服务器的 stdio
  const transport = new StdioClientTransport({
    stdout: process.stdout,
    stdin: process.stdin
  });

  // 4. 连接并初始化
  await client.connect(transport);
  await client.initialize();

  // 5. 获取工具列表
  const tools = await client.listTools();

  // 6. 注册工具
  registerTools(name, tools.tools);
}
```

---

## 7. 为什么只需写一次

### 核心原理：协议标准化 + 客户端适配层

#### Tavily 只需实现 MCP 标准

```python
# tavily_mcp_server.py
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("Tavily Search Server")

@mcp.tool()
def tavily_search(
    query: str,
    max_results: int = 10
) -> str:
    """
    使用 Tavily API 搜索网络获取最新信息
    """
    response = httpx.post(
        "https://api.tavily.com/search",
        json={
            "api_key": os.environ["TAVILY_API_KEY"],
            "query": query,
            "max_results": max_results
        }
    )
    return response.json()

# 启动服务器
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

**就这样！Tavily 的工作结束了。**

#### 客户端负责协议转换

```typescript
// Claude Desktop 内部的 MCP 适配器

class ClaudeMCPAdapter {
  async connectToMCP(serverConfig: any) {
    // 1. 连接到 MCP 服务器
    const mcpClient = new Client({
      name: "claude-desktop",
      version: "1.0.0"
    });

    const transport = new StdioClientTransport({
      command: serverConfig.command,
      args: serverConfig.args,
      env: serverConfig.env
    });

    await mcpClient.connect(transport);

    // 2. 获取 MCP 工具列表
    const toolsResult = await mcpClient.listTools();

    // 3. 【关键】转换 MCP 格式 → Claude 格式
    const claudeTools = toolsResult.tools.map(tool => ({
      name: `mcp__${serverName}__${tool.name}`,
      description: tool.description,
      input_schema: tool.inputSchema  // ← MCP 的 inputSchema 直接兼容！
    }));

    return claudeTools;
  }

  async callTool(toolName: string, args: any) {
    const [prefix, serverName, toolName] = toolName.split('__');

    // 调用 MCP 服务器
    const result = await this.mcpClient.callTool({
      name: toolName,
      arguments: args
    });

    // 转换结果格式
    return {
      type: 'tool_result',
      tool_use_id: this.generateId(),
      content: result.content.map(item => ({
        type: 'text',
        text: item.text
      }))
    };
  }
}
```

### 为什么 MCP 格式能自动兼容？

```typescript
// MCP 的 inputSchema 设计得非常好

{
  "type": "object",
  "properties": {
    "query": { "type": "string" },
    "max_results": { "type": "integer" }
  },
  "required": ["query"]
}

// Claude 格式
input_schema: { ... }        // ← 直接使用

// OpenAI 格式
parameters: { ... }           // ← 直接使用（只改字段名）

// Gemini 格式
parameters: { ... }           // ← 直接使用
```

**这就是为什么 MCP 能成功：它的 JSON Schema 设计与各大 LLM 的工具定义格式高度兼容！**

---

## 8. 完整代码示例

### 传统方式 vs MCP 方式对比

#### ❌ 传统方式：每个客户端都要写适配

**Claude Desktop 适配代码**

```typescript
// claude-tavily-integration.ts

import Anthropic from '@anthropic-ai/sdk';

const tavilySearchTool = {
  name: 'tavily_search',
  description: '搜索网络获取最新信息',
  input_schema: {  // ← Claude 格式
    type: 'object',
    properties: {
      query: { type: 'string' },
      max_results: { type: 'integer', default: 10 }
    },
    required: ['query']
  }
};

async function callTavilyAPI(params: any) {
  const response = await fetch('https://api.tavily.com/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      api_key: process.env.TAVILY_API_KEY,
      query: params.query,
      max_results: params.max_results || 10
    })
  });
  return await response.json();
}

async function handleClaudeResponse(userMessage: string) {
  const anthropic = new Anthropic({
    apiKey: process.env.ANTHROPIC_API_KEY
  });

  const message = await anthropic.messages.create({
    model: 'claude-3-5-sonnet-20241022',
    max_tokens: 1024,
    tools: [tavilySearchTool],
    messages: [{ role: 'user', content: userMessage }]
  });

  for (const block of message.content) {
    if (block.type === 'tool_use' && block.name === 'tavily_search') {
      const toolResult = await callTavilyAPI(block.input);

      const finalMessage = await anthropic.messages.create({
        model: 'claude-3-5-sonnet-20241022',
        max_tokens: 1024,
        tools: [tavilySearchTool],
        messages: [
          { role: 'user', content: userMessage },
          { role: 'assistant', content: message.content },
          {
            role: 'user',
            content: [{
              type: 'tool_result',
              tool_use_id: block.id,
              content: JSON.stringify(toolResult)
            }]
          }
        ]
      });

      return finalMessage.content;
    }
  }

  return message.content;
}
```

**Cursor IDE 适配代码**

```typescript
// cursor-tavily-integration.ts

import OpenAI from 'openai';

const tavilySearchTool = {
  type: 'function' as const,
  function: {
    name: 'tavily_search',
    description: '搜索网络获取最新信息',
    parameters: {  // ← OpenAI 格式（不同！）
      type: 'object',
      properties: {
        query: { type: 'string' },
        max_results: { type: 'integer' }
      },
      required: ['query']
    }
  }
};

async function callTavilyAPI(params: any) {  // ← 重复实现
  const response = await fetch('https://api.tavily.com/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      api_key: process.env.TAVILY_API_KEY,
      query: params.query,
      max_results: params.max_results || 10
    })
  });
  return await response.json();
}

async function handleOpenAIResponse(userMessage: string) {
  const openai = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY
  });

  const response = await openai.chat.completions.create({
    model: 'gpt-4-turbo',
    messages: [{ role: 'user', content: userMessage }],
    tools: [tavilySearchTool],
    tool_choice: 'auto'
  });

  const assistantMessage = response.choices[0].message;

  if (assistantMessage.tool_calls) {
    for (const toolCall of assistantMessage.tool_calls) {
      if (toolCall.function.name === 'tavily_search') {
        const args = JSON.parse(toolCall.function.arguments);
        const toolResult = await callTavilyAPI(args);

        const finalResponse = await openai.chat.completions.create({
          model: 'gpt-4-turbo',
          messages: [
            { role: 'user', content: userMessage },
            assistantMessage,
            {
              role: 'tool',
              tool_call_id: toolCall.id,
              content: JSON.stringify(toolResult)
            }
          ]
        });

        return finalResponse.choices[0].message.content;
      }
    }
  }

  return assistantMessage.content;
}
```

#### ✅ MCP 方式：只写一次

**Tavily MCP 服务器**

```python
# tavily_mcp_server.py
from mcp.server.fastmcp import FastMCP
import httpx
import os

mcp = FastMCP("Tavily Search Server")

@mcp.tool()
def tavily_search(
    query: str,
    max_results: int = 10,
    search_depth: str = "basic"
) -> str:
    """
    使用 Tavily API 搜索网络获取最新信息

    Args:
        query: 搜索关键词
        max_results: 最大结果数 (1-20)
        search_depth: 搜索深度 (basic/advanced)

    Returns:
        搜索结果的 JSON 字符串
    """
    response = httpx.post(
        "https://api.tavily.com/search",
        json={
            "api_key": os.environ["TAVILY_API_KEY"],
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth
        },
        timeout=30.0
    )
    return response.json()

@mcp.tool()
def tavily_extract(urls: list[str]) -> str:
    """
    从指定 URL 提取内容

    Args:
        urls: 要提取的 URL 列表

    Returns:
        提取的内容
    """
    response = httpx.post(
        "https://api.tavily.com/extract",
        json={
            "api_key": os.environ["TAVILY_API_KEY"],
            "urls": urls
        },
        timeout=30.0
    )
    return response.json()

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

**各客户端配置**

```json
// Claude Desktop: ~/.claude/config.json
{
  "mcpServers": {
    "tavily": {
      "command": "uvx",
      "args": ["tavily-mcp"],
      "env": {
        "TAVILY_API_KEY": "tvly-your-api-key"
      }
    }
  }
}
```

```json
// Cursor IDE: ~/.cursor/mcp.json
{
  "mcpServers": {
    "tavily": {
      "command": "uvx",
      "args": ["tavily-mcp"],
      "env": {
        "TAVILY_API_KEY": "tvly-your-api-key"
      }
    }
  }
}
```

```typescript
// 自定义应用: custom-mcp-client.ts
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

async function connectToTavilyMCP() {
  const client = new Client({
    name: "my-custom-app",
    version: "1.0.0"
  });

  const transport = new StdioClientTransport({
    command: "uvx",
    args: ["tavily-mcp"],
    env: {
      TAVILY_API_KEY: process.env.TAVILY_API_KEY!
    }
  });

  await client.connect(transport);

  // 获取可用工具列表
  const toolsResult = await client.listTools();

  console.log("可用工具:", toolsResult.tools);

  return client;
}
```

### 代码量对比

| 方式 | 代码量 | 维护成本 |
|------|-------|---------|
| **传统方式** | 450 行 × 3 个客户端 = 1350+ 行 | API 变更要改 3 个地方 |
| **MCP 方式** | 50 行（服务器）+ 3 个配置文件 | API 变了只改 1 个服务器 |

---

## 9. 总结

### 核心要点

1. **MCP 是协议标准，不是实现**
   - MCP 定义了统一的工具暴露方式
   - MCP 定义了标准的通信协议（JSON-RPC 2.0）
   - MCP 定义了统一的工具描述格式（JSON Schema）

2. **MCP ≠ Function Calling**
   - MCP 是协议标准（如何暴露工具）
   - Function Calling 是执行机制（LLM 如何调用工具）
   - MCP 使用 Function Calling 作为底层执行机制

3. **MCP 解决了 NxM 复杂度问题**
   - 传统方式：每个工具要为每个客户端写适配（N×M）
   - MCP 方式：工具写一次 MCP 服务器，客户端写一次 MCP 适配器（N+M）

4. **为什么只需写一次？**
   - 工具提供者只需实现 MCP 标准（统一的 JSON Schema + JSON-RPC）
   - 各 LLM 客户端内部实现 MCP 适配器（MCP 格式 → 自己的格式）
   - 责任清晰：工具方负责实现 MCP，客户端负责适配 MCP

5. **JSON Schema 是关键**
   - JSON Schema 是描述 JSON 数据结构的标准格式
   - 各大 LLM 都使用 JSON Schema 描述工具
   - MCP 的 inputSchema 设计与各大 LLM 高度兼容

### 最佳实践建议

#### 对于工具提供者

```python
# 1. 使用 MCP SDK 定义工具
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My Tool Server")

@mcp.tool()
def my_tool(param1: str, param2: int = 10) -> str:
    """
    清晰的工具描述

    Args:
        param1: 参数说明
        param2: 参数说明

    Returns:
        返回值说明
    """
    return "result"

# 2. 启动服务器
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

#### 对于客户端开发者

```typescript
// 1. 实现 MCP 适配器
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

class MyMCPAdapter {
  async connect(serverConfig: any) {
    const client = new Client({
      name: "my-app",
      version: "1.0.0"
    });

    const transport = new StdioClientTransport({
      command: serverConfig.command,
      args: serverConfig.args,
      env: serverConfig.env
    });

    await client.connect(transport);

    // 2. 转换 MCP 格式为自己的 LLM 格式
    const toolsResult = await client.listTools();
    const myFormatTools = toolsResult.tools.map(tool => ({
      // 转换逻辑
    }));

    return { client, tools: myFormatTools };
  }
}
```

#### 对于用户

```json
// 1. 配置 MCP 服务器
{
  "mcpServers": {
    "tool-name": {
      "command": "启动命令",
      "args": ["参数"],
      "env": {
        "API_KEY": "your-api-key"
      }
    }
  }
}

// 2. 重启 LLM 应用
// 3. 直接使用工具！
```

### 延伸阅读

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [MCP 规范](https://modelcontextprotocol.io/specification/)
- [JSON Schema 官方规范](https://json-schema.org/)
- [MCP 服务器开发指南](https://modelcontextprotocol.io/docs/develop/build-server)
- [MCP 客户端开发指南](https://modelcontextprotocol.io/docs/develop/build-client)

---

**一句话总结：**

> **传统方式**：每个工具提供者需要为每个 LLM 客户端写不同的适配代码，导致 N×M 复杂度。
>
> **MCP 方式**：MCP 定义了统一的工具注册格式（基于 JSON Schema），工具提供者只需实现一次 MCP 服务器，各 LLM 客户端只需实现一次 MCP 适配器，就能实现工具的通用接入。

---

*本文档由 AI 辅助生成，基于 MCP 官方文档和最佳实践整理。*
