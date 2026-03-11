# MCP in-depth analysis: from principle to practice

> English translation generated from `./mcp-deep-dive-guide.md`


> This article explains in detail how Model Context Protocol (MCP) works, including the basics of JSON Schema, the difference between MCP and Function Calling, how to solve the problem of NxM integration complexity, and complete code examples.

---

## Table of contents

- 1. MCP Core Concepts
- 2. JSON Schema Fundamentals
- 3. MCP vs Function Calling
- 4. The NxM Integration Problem
- 5. MCP Runtime Mechanics
- 6. How Configuration Works
- 7. Why "Write Once" Is Possible
- 8. Complete Code Examples
- 9. Summary

---

## 1. MCP core concepts

### What is MCP?

**Model Context Protocol (MCP)** is an open protocol used to establish standardized connections between LLM (Large Language Model) applications and external data sources/tools.

#### Analogy: MCP is like the USB standard in the AI ​​world

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
### Core components of MCP

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

## 2. JSON Schema basics

### What is JSON Schema?

**JSON Schema** is a format used to describe the structure of JSON data. It defines:
- Type of data (string, number, object, array, etc.)
- required fields
- Constraints on fields (minimum value, maximum value, enumeration value, etc.)

### Basic example

#### Simple JSON Schema

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
#### Corresponding valid JSON data

```json
{
  "name": "张三",
  "age": 25,
  "email": "zhangsan@example.com"
}
```
#### Invalid JSON data

```json
{
  "age": 25,
  "email": "zhangsan@example.com"
  // ❌ 缺少必需的 "name" 字段
}
```
### Application in MCP

MCP uses JSON Schema to describe the input parameters of the tool:

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
### Why is JSON Schema important?

1. **Uniformity**: All major LLMs use JSON Schema description tools
2. **Verifiable**: Can verify whether the parameters meet the requirements
3. **Self-describing**: Contains type and description information, LLM can understand
4. **Interoperability**: Tool definitions can be exchanged between different systems

---

## 3. MCP vs Function Calling

### Core differences

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
### Detailed comparison

|aspect| MCP | Function Calling |
|------|-----|------------------|
|**nature**|protocol standards|Execution mechanism|
|**definer**|MCP official specification|Various LLM providers|
|**effect**|Unified tool exposure method|How LLM calls tools|
|**protocol**| JSON-RPC 2.0 |Varies (HTTP/WebSocket)|
|**Tool Format**|Unified `inputSchema`| Claude: `input_schema`<br>OpenAI: `parameters`<br>Gemini: `parameters` |
|**relation**|MCP uses Function Calling as the underlying execution mechanism|Function Calling can call MCP tools|

### Collaboration between MCP and Function Calling

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

## 4. NxM problem solved by MCP

### Problem description: Integration complexity of traditional methods

Let's say you have 3 LLM applications and 3 tools that need to be integrated:

#### ❌ Traditional method (without MCP)

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
#### Problem details

**1. The tool definition format is not uniform**

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
**2. API calling methods are different**

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
**3. The tool calling structure is different**

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
#### ✅ MCP method

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
### Complexity comparison

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

## 5. Detailed explanation of MCP working principle

### Complete workflow

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
### Key protocol: JSON-RPC 2.0

MCP uses JSON-RPC 2.0 as the communication protocol. JSON-RPC is a lightweight remote procedure call protocol.

#### Basic structure

```json
{
  "jsonrpc": "2.0",
  "method": "方法名",
  "params": { /* 参数 */ },
  "id": 1
}
```
#### Standard methods defined by MCP

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

## 6. How configuration files work

### Configuration file structure

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
### Configuration file location

|application|Configuration file location|
|------|------------|
| Claude Desktop | `~/.claude/config.json` |
| Cursor | `~/.cursor/mcp.json` |
|project specific|`.mcp.json` (project root directory)|

### Configuration file parsing process

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

## 7. Why you only need to write it once

### Core principle: protocol standardization + client adaptation layer

#### Tavily only needs to implement the MCP standard

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
**that's all! Tavily's job is over. **

#### The client is responsible for protocol conversion

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
### Why is the MCP format automatically compatible?

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
**This is why MCP is successful: its JSON Schema design is highly compatible with the tool definition formats of major LLMs! **

---

## 8. Complete code example

### Comparison of traditional method vs MCP method

#### ❌ Traditional method: each client must write an adaptation

**Claude Desktop adaptation code**

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
**Cursor IDE adaptation code**

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
#### ✅ MCP method: write only once

**Tavily MCP Server**

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
**Configuration of each client**

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
### Comparison of code size

|Way|Amount of code|Maintenance cost|
|------|-------|---------|
|**Traditional way**|450 rows × 3 clients = 1350+ rows|API changes require 3 changes|
|**MCP method**|50 lines (server) + 3 config files|The API has changed and only 1 server has been changed.|

---

## 9. Summary

### Core Points

1. **MCP is a protocol standard, not an implementation**
   - MCP defines a unified tool exposure method
   - MCP defines a standard communication protocol (JSON-RPC 2.0)
   - MCP defines a unified tool description format (JSON Schema)

2. **MCP ≠ Function Calling**
   - MCP is a protocol standard (how to expose tools)
   - Function Calling is the execution mechanism (how LLM calls tools)
   - MCP uses Function Calling as the underlying execution mechanism

3. **MCP solves the NxM complexity problem**
   - Traditional method: each tool needs to write an adaptation for each client (N×M)
   - MCP method: The tool writes the MCP server once, and the client writes the MCP adapter once (N+M)

4. **Why do you only need to write it once? **
   - Tool providers only need to implement the MCP standard (unified JSON Schema + JSON-RPC)
   - Each LLM client internally implements the MCP adapter (MCP format → own format)
   - Clear responsibilities: the tool side is responsible for implementing MCP, and the client is responsible for adapting MCP

5. **JSON Schema is key**
   - JSON Schema is a standard format for describing JSON data structure
   - All major LLMs use JSON Schema description tools
   - MCP's inputSchema design is highly compatible with major LLMs

### Best Practice Suggestions

#### For tool providers

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
#### For client developers

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
#### For users

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
### Further reading

- [MCP official document](https://modelcontextprotocol.io/)
- [MCP Specification](https://modelcontextprotocol.io/specification/)
- [JSON Schema official specification](https://json-schema.org/)
- [MCP Server Development Guide](https://modelcontextprotocol.io/docs/develop/build-server)
- [MCP Client Development Guide](https://modelcontextprotocol.io/docs/develop/build-client)

---

**Summary in one sentence:**

> **Traditional approach**: Each tool provider needs to write different adaptation code for each LLM client, resulting in N×M complexity.
>
> **MCP method**: MCP defines a unified tool registration format (based on JSON Schema). Tool providers only need to implement the MCP server once, and each LLM client only needs to implement the MCP adapter once to achieve universal access to tools.

---

*This document is generated with AI assistance and is based on MCP official documents and best practices. *
