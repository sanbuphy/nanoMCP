# In-depth dismantling of Kimi CLI’s MCP (Model Context Protocol) implementation mechanism

> English translation generated from `./kimi-cli-mcp-implementation-analysis.md`


> **Project address**: [https://github.com/MoonshotAI/kimi-cli](https://github.com/MoonshotAI/kimi-cli)
>
> **Analysis version**: v1.3
>
> **Analysis time**: 2026-03-11

**Related Documents**:
- [Official MCP Introduction](./official-mcp-introduction.en.md) - Basic concepts and principles of MCP protocol
- [Gemini CLI MCP Implementation](./gemini-cli-mcp-implementation-analysis.en.md) - Implementation comparison based on TypeScript SDK

## Table of contents

- 1. Project Overview
- 2. MCP Architecture Overview
- 3. Core Component Breakdown
- 4. End-to-End Workflow
- 5. Key Technical Implementations
- 6. Security Mechanisms
- 7. Usage Examples
- 8. Summary and Takeaways

---

## 1. Project Overview

### 1.1 What is Kimi CLI?

Kimi Code CLI is a terminal AI assistant developed by Moonshot AI. It not only helps you complete software development tasks, but also serves as a powerful shell environment. Kimi CLI supports functions such as reading and editing code, executing shell commands, searching web pages, and more.

### 1.2 What is MCP?

**MCP (Model Context Protocol)** is an open protocol that allows AI models to safely interact with external tools and data sources. Through MCP, Kimi CLI can:

- Access a specific API or database
- Control browsers or other applications
- Integrate with third-party services (GitHub, Linear, Notion, etc.)
- Expand the boundaries of AI capabilities

### 1.3 Technology stack

- **Language**: Python 3.12+
- **MCP client**: `fastmcp==2.12.5`
- **Configuration Management**: Pydantic
- **Asynchronous Framework**: asyncio
- **CLI Framework**: Typer

---

## 2. MCP architecture overview

### 2.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户交互层                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  CLI 命令    │  │  ACP 协议    │  │  Web UI      │          │
│  │  kimi mcp    │  │  IDE 集成    │  │  界面        │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         配置管理层                               │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  ~/.kimi/mcp.json (默认配置)                           │     │
│  │  --mcp-config-file (自定义配置)                        │     │
│  │  --mcp-config (内联配置)                               │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         核心处理层                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ KimiToolset  │  │  MCPTool     │  │ MCPServerInfo│          │
│  │ 工具集管理   │  │  工具封装    │  │ 连接状态     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         MCP 客户端层                             │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  fastmcp.Client                                         │     │
│  │  - stdio 传输 (本地进程)                                │     │
│  │  - http 传输 (远程服务器)                               │     │
│  │  - OAuth 认证                                            │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      外部 MCP 服务器层                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │context7  │  │ Linear   │  │Notion    │  │自定义... │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
```
### 2.2 Core code structure

```
src/kimi_cli/
├── cli/
│   └── mcp.py                    # MCP CLI 命令实现
├── soul/
│   └── toolset.py                # 工具集核心逻辑
├── acp/
│   └── mcp.py                    # ACP 协议的 MCP 适配
├── config.py                     # 配置定义
└── exception.py                  # 异常定义

主要文件职责：
- cli/mcp.py: 提供 kimi mcp 命令行工具
- soul/toolset.py: 工具加载、管理、调用核心逻辑
- acp/mcp.py: ACP 协议与 MCP 的桥接
```

---

## 3. Disassembly of core components

### 3.1 Configuration management (`cli/mcp.py`)

#### Configuration file structure

MCP configuration is stored in `~/.kimi/mcp.json` and supports two transmission modes:

```json
{
  "mcpServers": {
    "context7": {
      "url": "https://mcp.context7.com/mcp",
      "transport": "http",
      "headers": {
        "CONTEXT7_API_KEY": "your-key"
      },
      "auth": "oauth"
    },
    "chrome-devtools": {
      "command": "npx",
      "args": ["chrome-devtools-mcp@latest"],
      "env": {
        "NODE_ENV": "production"
      },
      "transport": "stdio"
    }
  }
}
```
#### Configuration loading process

```python
# cli/mcp.py: _load_mcp_config()

def _load_mcp_config() -> dict[str, Any]:
    """从全局配置文件加载 MCP 配置"""
    mcp_file = get_global_mcp_config_file()  # ~/.kimi/mcp.json

    if not mcp_file.exists():
        return {"mcpServers": {}}

    # 1. 读取并解析 JSON
    config = json.loads(mcp_file.read_text(encoding="utf-8"))

    # 2. 使用 Pydantic 验证配置格式
    try:
        MCPConfig.model_validate(config)
    except ValidationError as e:
        raise typer.BadParameter(f"Invalid MCP config: {e}")

    return config
```
#### CLI command implementation

```bash
# 添加 HTTP 服务器
kimi mcp add --transport http context7 https://mcp.context7.com/mcp \
  --header "CONTEXT7_API_KEY: your-key"

# 添加 OAuth 认证的服务器
kimi mcp add --transport http --auth oauth linear https://mcp.linear.app/mcp

# 添加 stdio 服务器
kimi mcp add --transport stdio chrome-devtools -- npx chrome-devtools-mcp@latest

# 列出所有服务器
kimi mcp list

# 测试连接
kimi mcp test context7

# OAuth 授权
kimi mcp auth linear

# 移除服务器
kimi mcp remove context7
```
**Code implementation** (`cli/mcp.py:83-193`):

```python
@cli.command("add")
def mcp_add(
    name: str,
    server_args: list[str] | None,
    transport: Literal["stdio", "http"] = "stdio",
    env: list[str] | None = None,
    header: list[str] | None = None,
    auth: str | None = None,
):
    """添加 MCP 服务器"""
    config = _load_mcp_config()

    if transport == "stdio":
        # stdio 模式：命令行工具
        command, *command_args = server_args
        server_config = {
            "command": command,
            "args": command_args,
            "env": _parse_key_value_pairs(env, "env")
        }
    else:
        # http 模式：远程服务器
        server_config = {
            "url": server_args[0],
            "transport": "http",
            "headers": _parse_key_value_pairs(header, "header", separator=":"),
        }
        if auth:
            server_config["auth"] = auth

    config["mcpServers"][name] = server_config
    _save_mcp_config(config)
```

---

### 3.2 Toolset management (`soul/toolset.py`)

#### KimiToolset Class

**Responsibilities**: Manage all tools (built-in tools + MCP tools)

```python
class KimiToolset:
    def __init__(self) -> None:
        self._tool_dict: dict[str, ToolType] = {}      # 所有工具字典
        self._mcp_servers: dict[str, MCPServerInfo] = {}  # MCP 服务器
        self._mcp_loading_task: asyncio.Task[None] | None = None

    def add(self, tool: ToolType) -> None:
        """添加工具到工具集"""
        self._tool_dict[tool.name] = tool

    def find(self, tool_name: str) -> ToolType | None:
        """查找工具"""
        return self._tool_dict.get(tool_name)

    def handle(self, tool_call: ToolCall) -> HandleResult:
        """处理工具调用"""
        tool = self._tool_dict.get(tool_call.function.name)
        if not tool:
            return ToolResult(return_value=ToolNotFoundError(tool_name))

        # 异步调用工具
        async def _call():
            ret = await tool.call(arguments)
            return ToolResult(tool_call_id=tool_call.id, return_value=ret)

        return asyncio.create_task(_call())
```
#### MCP server information

```python
@dataclass
class MCPServerInfo:
    """MCP 服务器连接信息"""
    status: Literal["pending", "connecting", "connected", "failed", "unauthorized"]
    client: fastmcp.Client[Any]  # fastmcp 客户端
    tools: list[MCPTool[Any]]    # 该服务器提供的工具列表
```
**State Machine**:

```
pending (初始状态)
   ↓
connecting (开始连接)
   ↓
   ├─→ connected (连接成功，工具已加载)
   ├─→ failed (连接失败)
   └─→ unauthorized (OAuth 未授权)
```

---

### 3.3 MCP tool package (`soul/toolset.py`)

#### MCPTool class

**Responsibility**: Encapsulate MCP tools into tools callable by Kimi CLI

```python
class MCPTool[T: ClientTransport](CallableTool):
    def __init__(
        self,
        server_name: str,      # 服务器名称
        mcp_tool: mcp.Tool,    # MCP 原始工具
        client: fastmcp.Client[T],  # fastmcp 客户端
        *,
        runtime: Runtime,      # 运行时上下文
        **kwargs: Any,
    ):
        # 调用父类初始化
        super().__init__(
            name=mcp_tool.name,
            description=(
                f"This is an MCP (Model Context Protocol) tool "
                f"from MCP server `{server_name}`.\n\n"
                f"{mcp_tool.description or 'No description provided.'}"
            ),
            parameters=mcp_tool.inputSchema,  # JSON Schema
        )
        self._mcp_tool = mcp_tool
        self._client = client
        self._runtime = runtime
        self._timeout = timedelta(
            milliseconds=runtime.config.mcp.client.tool_call_timeout_ms
        )
        self._action_name = f"mcp:{mcp_tool.name}"
```
#### Tool calling process

```python
async def __call__(self, **kwargs) -> ToolReturnValue:
    # 1. 用户审批
    description = f"Call MCP tool `{self._mcp_tool.name}`."
    if not await self._runtime.approval.request(
        self.name, self._action_name, description
    ):
        return ToolRejectedError()

    # 2. 调用 MCP 服务器
    try:
        async with self._client as client:
            result = await client.call_tool(
                self._mcp_tool.name,
                kwargs,
                timeout=self._timeout,
                raise_on_error=False
            )
            return convert_mcp_tool_result(result)
    except Exception as e:
        # 3. 错误处理
        if "timeout" in str(e).lower():
            return ToolError(
                message=f"Timeout while calling MCP tool `{self._mcp_tool.name}`",
                brief="Timeout"
            )
        raise
```

---

### 3.4 Configuration definition (`config.py`)

```python
class MCPClientConfig(BaseModel):
    """MCP 客户端配置"""
    tool_call_timeout_ms: int = 60000  # 工具调用超时（毫秒）

class MCPConfig(BaseModel):
    """MCP 配置"""
    client: MCPClientConfig = Field(
        default_factory=MCPClientConfig
    )

class Config(BaseModel):
    """主配置"""
    mcp: MCPConfig = Field(
        default_factory=MCPConfig,
        description="MCP configuration"
    )
```

---

## 4. Complete workflow

### 4.1 Startup flow chart

```
┌─────────────────────────────────────────────────────────────────┐
│                      1. 用户启动 kimi                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│               2. 加载配置 (app.py: KimiCLI.create)              │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 加载源：                                               │     │
│  │  • ~/.kimi/mcp.json (默认)                            │     │
│  │  • --mcp-config-file <path> (指定文件)                 │     │
│  │  • --mcp-config <json> (内联配置)                     │     │
│  └────────────────────────────────────────────────────────┘     │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 验证配置：                                             │     │
│  │  MCPConfig.model_validate(config)                      │     │
│  │  解析服务器配置（stdio/http）                          │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│           3. 创建 Runtime 和 KimiToolset                         │
│  runtime = await Runtime.create(config, ...)                    │
│  toolset = runtime.toolset                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│        4. 加载 MCP 工具 (toolset.load_mcp_tools)                │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ for each mcp_config:                                  │     │
│  │   for server_name, server_config in mcpServers:        │     │
│  │     1. 创建 MCPServerInfo (status: pending)            │     │
│  │     2. 创建 fastmcp.Client                             │     │
│  │     3. 检查 OAuth 授权状态                             │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              5. 异步连接所有服务器                                │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ asyncio.gather(*tasks)                                │     │
│  │   for each server:                                    │     │
│  │     status: pending → connecting                      │     │
│  │     ├─ 未授权 → unauthorized                          │     │
│  │     └─ 已授权 → 连接并获取工具列表                    │     │
│  │         ├─ 成功 → 创建 MCPTool → 添加到 toolset       │     │
│  │         │         → status: connected                 │     │
│  │         └─ 失败 → status: failed                      │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   6. 显示连接结果                                │
│  • "mcp servers connected" (成功)                               │
│  • "mcp authorization needed" (需要授权)                        │
│  • "mcp connection failed" (连接失败)                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   7. 等待用户输入                                │
└─────────────────────────────────────────────────────────────────┘
```
### 4.2 Tool calling flow chart

```
┌─────────────────────────────────────────────────────────────────┐
│                    用户输入问题                                  │
│  "使用 context7 搜索 Python MCP 教程"                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  AI 分析并决定调用工具                           │
│  识别需要使用 context7_search 工具                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    生成 ToolCall                                 │
│  {                                                              │
│    "id": "call_abc123",                                         │
│    "function": {                                                │
│      "name": "context7_search",                                 │
│      "arguments": {                                             │
│        "query": "Python MCP tutorial",                          │
│        "limit": 10                                              │
│      }                                                           │
│    }                                                             │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│            toolset.handle(tool_call)                            │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 1. 查找工具：                                          │     │
│  │    tool = toolset._tool_dict["context7_search"]        │     │
│  │                                                        │     │
│  │ 2. 解析参数：                                          │     │
│  │    kwargs = json.loads(arguments)                     │     │
│  │                                                        │     │
│  │ 3. 异步调用：                                          │     │
│  │    result = await tool.call(kwargs)                   │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              MCPTool.__call__(**kwargs)                         │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 1. 用户审批：                                          │     │
│  │    await runtime.approval.request(                     │     │
│  │      "context7_search",                                │     │
│  │      "mcp:context7_search",                            │     │
│  │      "Call MCP tool `context7_search`"                 │     │
│  │    )                                                    │     │
│  │                                                        │     │
│  │  ┌────────────────────────────────────────────┐        │     │
│  │  │ 弹出确认对话框：                         │        │     │
│  │  │ ┌──────────────────────────────────┐     │        │     │
│  │  │  │ 即将执行 MCP 工具调用           │     │        │     │
│  │  │  │ 工具: context7_search           │     │        │     │
│  │  │  │ 描述: Search the web...         │     │        │     │
│  │  │  │ [允许] [拒绝]                   │     │        │     │
│  │  │  └──────────────────────────────────┘     │        │     │
│  │  └────────────────────────────────────────────┘        │     │
│  │                                                        │     │
│  │ 2. 调用 MCP 服务器：                                   │     │
│  │    async with client as client:                       │     │
│  │      result = await client.call_tool(                 │     │
│  │        "context7_search",                             │     │
│  │        kwargs,                                        │     │
│  │        timeout=60s                                    │     │
│  │      )                                                 │     │
│  │                                                        │     │
│  │ 3. 转换结果：                                          │     │
│  │    return convert_mcp_tool_result(result)             │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│          convert_mcp_tool_result(result)                        │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ for part in result.content:                            │     │
│  │   if part.type == "text":                              │     │
│  │     content.append(ContentPart(text=part.text))        │     │
│  │   elif part.type == "image":                           │     │
│  │     content.append(ContentPart(image=part.data))       │     │
│  │   elif part.type == "resource":                        │     │
│  │     content.append(ContentPart(resource=...))          │     │
│  │                                                        │     │
│  │ if result.is_error:                                    │     │
│  │   return ToolError(output=content)                     │     │
│  │ else:                                                  │     │
│  │   return ToolOk(output=content)                        │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              AI 处理结果并返回给用户                              │
└─────────────────────────────────────────────────────────────────┘
```
### 4.3 OAuth authorization flow chart

```
┌─────────────────────────────────────────────────────────────────┐
│              1. 添加 OAuth 服务器                                │
│  kimi mcp add --transport http --auth oauth linear \           │
│    https://mcp.linear.app/mcp                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              2. 配置保存到 ~/.kimi/mcp.json                      │
│  {                                                              │
│    "mcpServers": {                                              │
│      "linear": {                                                │
│        "url": "https://mcp.linear.app/mcp",                    │
│        "transport": "http",                                     │
│        "auth": "oauth"                                          │
│      }                                                           │
│    }                                                             │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              3. 执行授权                                        │
│  kimi mcp auth linear                                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              4. 打开浏览器授权                                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 1. 创建 fastmcp.Client                                 │     │
│  │ 2. async with client as client:                       │     │
│  │ 3. await client.list_tools()                          │     │
│  │    → 触发 OAuth 流程                                   │     │
│  │    → 打开浏览器                                        │     │
│  │    → 用户登录并授权                                    │     │
│  │    → Token 保存到文件系统                              │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              5. 授权成功                                        │
│  ✓ Token 已保存，后续使用无需重新授权                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Key technology implementation

### 5.1 Asynchronous concurrent loading

**Question**: How to efficiently load multiple MCP servers?

**Solution**: Use `asyncio.gather` to connect to all servers concurrently

```python
# soul/toolset.py: load_mcp_tools()

async def load_mcp_tools(self, mcp_configs, runtime, in_background=True):
    # 1. 为每个服务器创建连接任务
    tasks = [
        asyncio.create_task(_connect_server(server_name, server_info))
        for server_name, server_info in self._mcp_servers.items()
        if server_info.status == "pending"
    ]

    # 2. 并发执行所有连接
    results = await asyncio.gather(*tasks) if tasks else []

    # 3. 收集失败的服务器
    failed_servers = {name: error for name, error in results if error is not None}

    if failed_servers:
        raise MCPRuntimeError(f"Failed to connect MCP servers: {failed_servers}")
```
**Advantages**:
- Multiple servers are connected at the same time without blocking startup
- Failure of a single server does not affect other servers
- Quick feedback on connection status

---

### 5.2 Background loading strategy

**Question**: The MCP server connection may be slow, how to avoid blocking user startup?

**Solution**: Support background loading

```python
# soul/toolset.py: load_mcp_tools()

async def load_mcp_tools(self, mcp_configs, runtime, in_background=True):
    async def _connect():
        # 连接所有服务器
        ...

    if in_background:
        # 后台加载，不阻塞启动
        self._mcp_loading_task = asyncio.create_task(_connect())
    else:
        # 同步等待加载完成
        await _connect()

# 在需要使用 MCP 工具时等待加载完成
async def wait_for_mcp_tools(self) -> None:
    task = self._mcp_loading_task
    if task:
        await task
```
**User Experience**:
- Fast startup
- Show loading progress notification
- Completed silently in the background

---

### 5.3 Content type conversion

**Issue**: The content type returned by MCP is inconsistent with the Kimi CLI internal format

**Solution**: Unify conversion functions

```python
# soul/toolset.py: convert_mcp_tool_result()

def convert_mcp_tool_result(result: CallToolResult) -> ToolReturnValue:
    """将 MCP 工具结果转换为 Kimi 工具返回值"""
    content: list[ContentPart] = []

    # 遍历 MCP 返回的内容
    for part in result.content:
        content.append(convert_mcp_content(part))

    # 根据是否错误返回不同类型
    if result.is_error:
        return ToolError(
            output=content,
            message="Tool returned an error. The output may be error message",
            brief=""
        )
    else:
        return ToolOk(output=content)


# kosong/tooling/mcp.py: convert_mcp_content()

def convert_mcp_content(content) -> ContentPart:
    """转换单个 MCP 内容"""
    if isinstance(content, mcp.TextContent):
        return ContentPart(text=content.text)
    elif isinstance(content, mcp.ImageContent):
        return ContentPart(image=content.data)
    elif isinstance(content, mcp.ResourceContents):
        return ContentPart(resource=...)
    else:
        raise ValueError(f"Unsupported content type: {type(content)}")
```

---

### 5.4 Timeout control

**Issue**: MCP server may be slow or unresponsive

**Solution**: Configure timeout + exception catching

```python
# soul/toolset.py: MCPTool.__call__()

async def __call__(self, **kwargs) -> ToolReturnValue:
    # 从配置读取超时时间（默认 60 秒）
    self._timeout = timedelta(
        milliseconds=runtime.config.mcp.client.tool_call_timeout_ms
    )

    try:
        async with self._client as client:
            result = await client.call_tool(
                self._mcp_tool.name,
                kwargs,
                timeout=self._timeout,  # 设置超时
                raise_on_error=False
            )
            return convert_mcp_tool_result(result)
    except Exception as e:
        # 捕获超时异常
        exc_msg = str(e).lower()
        if "timeout" in exc_msg or "timed out" in exc_msg:
            return ToolError(
                message=(
                    f"Timeout while calling MCP tool `{self._mcp_tool.name}`. "
                    "You may explain to the user that the timeout config is set too low."
                ),
                brief="Timeout"
            )
        raise
```
**Configuration** (`~/.kimi/config.yaml`):

```yaml
mcp:
  client:
    tool_call_timeout_ms: 60000  # 60 秒
```

---

### 5.5 Error isolation

**Issue**: Failure of one MCP server should not affect other servers

**Solution**: Independent connection task + state management

```python
# soul/toolset.py: _connect_server()

async def _connect_server(
    server_name: str, server_info: MCPServerInfo
) -> tuple[str, Exception | None]:
    """连接单个服务器，不影响其他服务器"""
    if server_info.status != "pending":
        return server_name, None

    server_info.status = "connecting"

    try:
        async with server_info.client as client:
            # 获取工具列表
            for tool in await client.list_tools():
                server_info.tools.append(
                    MCPTool(server_name, tool, client, runtime=runtime)
                )

            # 添加到工具集
            for tool in server_info.tools:
                self.add(tool)

            server_info.status = "connected"
            logger.info(f"Connected MCP server: {server_name}")
            return server_name, None

    except Exception as e:
        # 记录错误，但不抛出异常
        logger.error(f"Failed to connect MCP server: {server_name}, error: {e}")
        server_info.status = "failed"
        return server_name, e
```

---

## 6. Security mechanism

### 6.1 User approval mechanism

**All MCP tool calls require user confirmation**

```python
# soul/toolset.py: MCPTool.__call__()

async def __call__(self, **kwargs) -> ToolReturnValue:
    description = f"Call MCP tool `{self._mcp_tool.name}`."

    # 请求用户批准
    if not await self._runtime.approval.request(
        self.name,              # 工具名称
        self._action_name,      # 动作名称 (mcp:xxx)
        description             # 描述
    ):
        return ToolRejectedError()

    # 用户批准后才执行
    ...
```
**Approval Interface**:

```
┌─────────────────────────────────────────┐
│ 即将执行 MCP 工具调用                   │
├─────────────────────────────────────────┤
│ 工具: context7_search                   │
│ 类型: MCP 工具                          │
│                                         │
│ 描述:                                   │
│ Search the web using Context7 API...    │
│                                         │
│ 参数:                                   │
│ {                                       │
│   "query": "Python MCP tutorial",       │
│   "limit": 10                           │
│ }                                       │
│                                         │
│ [允许] [拒绝] [总是允许]                │
└─────────────────────────────────────────┘
```
### 6.2 YOLO mode

**Note**: Even in YOLO mode, MCP tools require approval

```python
# YOLO 模式只影响内置工具，不影响 MCP 工具
# 文档明确说明：
# "In YOLO mode, MCP tool operations will also be auto-approved.
#  It is recommended to use YOLO mode only when you fully trust the MCP server."
```
### 6.3 OAuth Token secure storage

```python
# fastmcp 使用 keyring 安全存储 OAuth token
from fastmcp.client.auth.oauth import FileTokenStorage

storage = FileTokenStorage(server_url=server_url)
tokens = await storage.get_tokens()  # 从安全存储读取
```
### 6.4 Prompt word injection protection

Content returned by MCP tools is tagged to help the AI ​​differentiate between tool output and user instructions:

```python
# 工具返回内容会被标记为 "tool output"
# AI 可以识别这不是用户指令
```
**Documentation Warning**:

> Content returned by MCP tools may contain malicious instructions that attempt to induce the AI ​​to perform dangerous operations.
> Kimi Code CLI tags tool return content to help AI distinguish tool output from user instructions.

**Suggestion**:
- Only use MCP servers from trusted sources
- Check whether the actions proposed by the AI are reasonable
- Maintain manual approvals for high-risk operations

---

## 7. Usage examples

### 7.1 Add Context7 search tool

```bash
# 1. 添加 Context7 HTTP 服务器
kimi mcp add --transport http context7 https://mcp.context7.com/mcp \
  --header "CONTEXT7_API_KEY: your-api-key"

# 2. 测试连接
kimi mcp test context7

# 3. 列出所有服务器
kimi mcp list

# 4. 启动 kimi
kimi

# 5. 使用 Context7 搜索
> 使用 context7 搜索 Python MCP 教程

# AI 会调用 context7_search 工具，并请求你的批准
# 批准后，AI 会显示搜索结果
```
### 7.2 Add Linear integration

```bash
# 1. 添加 Linear OAuth 服务器
kimi mcp add --transport http --auth oauth linear https://mcp.linear.app/mcp

# 2. 执行 OAuth 授权
kimi mcp auth linear
# 浏览器会打开，登录并授权

# 3. 测试连接
kimi mcp test linear

# 4. 使用 Linear 工具
kimi

> 列出我的 Linear issues
> 创建一个新的 Linear issue：修复 MCP 连接超时问题
```
### 7.3 Add local Chrome DevTools

```bash
# 1. 添加 stdio 服务器
kimi mcp add --transport stdio chrome-devtools -- npx chrome-devtools-mcp@latest

# 2. 测试连接
kimi mcp test chrome-devtools

# 3. 使用 Chrome DevTools
kimi

> 打开浏览器并访问 https://github.com/MoonshotAI/kimi-cli
> 截图当前页面
```
### 7.4 Temporarily load configuration

```bash
# 从文件加载
kimi --mcp-config-file /path/to/custom-mcp.json

# 内联配置
kimi --mcp-config '{
  "mcpServers": {
    "test": {
      "url": "https://test.mcp.server",
      "transport": "http"
    }
  }
}'
```

---

## 8. Summary and reflections

### 8.1 Architecture Highlights

1. **Standardized Design**
   - Fully compliant with MCP protocol specifications
   - Integrates with any MCP server
   - Configuration format compatible with other clients such as Claude Desktop

2. **Asynchronous Concurrency**
   - Multiple server concurrent connections
   - Background loading does not block startup
   - Efficient resource utilization

3. **Safety first**
   - All tool calls require approval
   - OAuth Token secure storage
   - Prompt word injection protection

4. **User Experience**
   - Clear command line interface
   - Real-time status notifications
   - Detailed error message

5. **Fault Tolerance**
   - Failure of a single server does not affect others
   - Perfect error handling
   - Timeout protection

### 8.2 Designs that can be learned from

1. **分层架构**
   - CLI 层、配置层、核心层、客户端层清晰分离
   - 每层职责明确，易于维护

2. **状态管理**
   - MCPServerInfo 的状态机设计
   - 清晰的状态转换逻辑

3. **Tool Encapsulation**
   - MCPTool unified encapsulation MCP tool
   - Hide underlying communication details

4. **Configuration Verification**
   - Verify configuration using Pydantic
   - Early detection of configuration errors

### 8.3 Room for improvement

1. **Tool Discovery**
   - Can add tool recommendation function
   - Recommend relevant MCP servers based on user behavior

2. **Performance Monitoring**
   - Record the response time of each server
   - Automatically adjust timeout configuration

3. **Caching mechanism**
   - Cache the call results of commonly used tools
   - Reduce duplicate requests

4. **Batch operation**
   -Support adding/removing servers in batches
   - Batch test connections

### 8.4 Applicable scenarios

Kimi CLI's MCP implementation is particularly suitable for the following scenarios:

1. **Development tool chain integration**
   - Integrates with GitHub, GitLab, Jira and more
   - Automated development process

2. **Data Analysis**
   - Connect to database MCP server
   - Perform SQL queries and analysis

3. **Content Creation**
   - Integrated search, translation and summarization tools
   - Improve creative efficiency

4. **Operation and Maintenance Automation**
   - Connect to monitoring and alarm systems
   - Automated operation and maintenance operations

---

## 9. The complete code flow of LLM calling MCP tool

This section shows in detail the complete code link of how LLM calls the MCP tool in Kimi CLI, from the LLM generation tool call to the final execution of the MCP server call.

### 9.1 Core call link

#### kosong.step - The core engine called by LLM tools

**Location**: `packages/kosong/src/kosong/__init__.py:104-180`

```python
async def step(
    chat_provider: ChatProvider,      # LLM 提供商（如 Kimi API）
    system_prompt: str,                # 系统提示词
    toolset: Toolset,                 # 工具集（包含 MCP 工具）
    history: Sequence[Message],       # 对话历史
    *,
    on_message_part: Callback[[StreamedMessagePart], None] | None = None,  # 流式回调
    on_tool_result: Callable[[ToolResult], None] | None = None,          # 工具结果回调
) -> "StepResult":
    """
    运行一个 agent "step"

    核心流程：
    1. 调用 LLM 生成响应（可能包含工具调用）
    2. 处理工具调用（通过 toolset.handle）
    3. 返回结果（包含工具结果的 Future）
    """
    tool_calls: list[ToolCall] = []
    tool_result_futures: dict[str, ToolResultFuture] = {}

    # 工具调用回调
    async def on_tool_call(tool_call: ToolCall):
        """
        当 LLM 生成工具调用时触发

        Args:
            tool_call: LLM 生成的工具调用
                {
                    "id": "call_123",
                    "function": {
                        "name": "mcp_context7_search",
                        "arguments": '{"query": "..."}'
                    }
                }
        """
        tool_calls.append(tool_call)

        # 核心：将工具调用分发给 toolset
        # toolset.handle() 会：
        # 1. 查找工具（包括 MCP 工具）
        # 2. 解析参数
        # 3. 异步执行工具
        result = toolset.handle(tool_call)

        if isinstance(result, ToolResult):
            # 同步返回的结果（如工具未找到、参数解析失败）
            future = ToolResultFuture()
            future.add_done_callback(future_done_callback)
            future.set_result(result)
            tool_result_futures[tool_call.id] = future
        else:
            # 异步执行的任务（实际工具调用）
            result.add_done_callback(future_done_callback)
            tool_result_futures[tool_call.id] = result

    try:
        # 调用 generate，传入工具定义和工具调用回调
        result = await generate(
            chat_provider,           # LLM 提供商
            system_prompt,           # 系统提示词
            toolset.tools,          # 工具定义（包括 MCP 工具）
            history,                 # 对话历史
            on_message_part=on_message_part,   # 流式输出回调
            on_tool_call=on_tool_call,          # 工具调用回调
        )
    except (ChatProviderError, asyncio.CancelledError):
        # 清理：取消所有未完成的工具调用
        for future in tool_result_futures.values():
            future.remove_done_callback(future_done_callback)
            future.cancel()
        await asyncio.gather(*tool_result_futures.values(), return_exceptions=True)
        raise

    return StepResult(
        result.id,                    # 消息 ID
        result.message,              # LLM 生成的消息
        result.usage,                # Token 使用量
        tool_calls,                  # 工具调用列表
        tool_result_futures,        # 工具结果 Future
    )
```
**Key Points**:
- The `step()` function is the core bridge between LLM and tools.
- It calls the LLM API, passing in the definitions of all available tools
- When LLM decides to call a tool, it is handled through the `on_tool_call` callback
- Dispatching tool calls to `toolset.handle()` which will route to the correct tool (including MCP tools)

#### KimiToolset.handle - Tool call dispatcher

**Location**: `src/kimi_cli/soul/toolset.py:97-124`

```python
def handle(self, tool_call: ToolCall) -> HandleResult:
    """
    处理工具调用的入口

    输入：LLM 生成的 ToolCall
    输出：HandleResult（同步或异步结果）
    """
    # 设置当前工具调用上下文（用于审批时获取信息）
    token = current_tool_call.set(tool_call)

    try:
        # 1. 查找工具
        if tool_call.function.name not in self._tool_dict:
            # 工具未找到
            return ToolResult(
                tool_call_id=tool_call.id,
                return_value=ToolNotFoundError(tool_call.function.name),
            )

        # 2. 获取工具实例（可能是 MCPTool）
        tool = self._tool_dict[tool_call.function.name]

        # 3. 解析参数
        try:
            arguments: JsonType = json.loads(
                tool_call.function.arguments or "{}"
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                tool_call_id=tool_call.id,
                return_value=ToolParseError(str(e))
            )

        # 4. 异步调用工具
        # 这里的 tool 可能是 MCPTool，它会：
        # - 请求用户审批
        # - 调用 MCP 服务器
        # - 转换结果格式
        async def _call():
            try:
                ret = await tool.call(arguments)
                return ToolResult(
                    tool_call_id=tool_call.id,
                    return_value=ret
                )
            except Exception as e:
                return ToolResult(
                    tool_call_id=tool_call.id,
                    return_value=ToolRuntimeError(str(e))
                )

        # 返回异步任务
        return asyncio.create_task(_call())

    finally:
        # 清理上下文
        current_tool_call.reset(token)
```
**Key Points**:
- `handle()` is the central dispatcher of tool calls
- It finds tools, parses parameters, and creates asynchronous tasks
- Supports all types of tools (built-in tools, MCP tools, user-defined tools)

#### MCPTool.call - MCP tool executor

**Location**: `src/kimi_cli/soul/toolset.py:380-405`

```python
async def __call__(self, **kwargs) -> ToolReturnValue:
    """
    执行 MCP 工具调用

    调用链：
    LLM → kosong.step → KimiToolset.handle → MCPTool.__call__
                                                            ↓
                                                    调用 MCP 服务器
    """
    # 1. 用户审批（关键安全机制）
    description = f"Call MCP tool `{self._mcp_tool.name}`."
    if not await self._runtime.approval.request(
        self.name,              # 工具名称
        self._action_name,      # 动作名称
        description             # 描述
    ):
        return ToolRejectedError()  # 用户拒绝

    # 2. 调用 fastmcp 客户端
    try:
        async with self._client as client:
            result = await client.call_tool(
                self._mcp_tool.name,    # MCP 工具名称
                kwargs,                # 参数
                timeout=self._timeout,   # 超时控制
                raise_on_error=False    # 不抛出错误，返回错误响应
            )
            # 3. 转换 MCP 结果为 Kimi 格式
            return convert_mcp_tool_result(result)
    except Exception as e:
        # 4. 处理超时和错误
        exc_msg = str(e).lower()
        if "timeout" in exc_msg or "timed out" in exc_msg:
            return ToolError(
                message=(
                    f"Timeout while calling MCP tool `{self._mcp_tool.name}`. "
                    "You may explain to the user that the timeout config is set too low."
                ),
                brief="Timeout"
            )
        raise
```
**Key Points**:
- **User Approval**: The MCP tool must be confirmed by the user before being called.
- **fastmcp client**: Use the fastmcp library to communicate with the MCP server
- **Timeout Control**: Prevent long-running tools from blocking
- **Error Handling**: Capture and convert various error conditions

#### kimisoul._step - Complete Step execution process

**Location**: `src/kimi_cli/soul/kimisoul.py:383-456`

```python
async def _step(self) -> StepOutcome | None:
    """
    执行单个推理步骤

    返回：StepOutcome 或 None（继续）
    """
    assert self._runtime.llm is not None
    chat_provider = self._runtime.llm.chat_provider

    # 1. 调用 kosong.step（包含 LLM 调用和工具分发）
    result = await kosong.step(
        chat_provider,
        self._agent.system_prompt,    # 系统提示词
        self._agent.toolset,           # 工具集（包含 MCP 工具）
        self._context.history,         # 对话历史
        on_message_part=wire_send,     # 流式输出回调
        on_tool_result=wire_send,      # 工具结果回调
    )

    # 2. 等待所有工具调用完成
    results = await result.tool_results()

    # 3. 将结果添加到上下文
    await self._grow_context(result, results)

    # 4. 检查是否有工具调用
    if result.tool_calls:
        return None  # 有工具调用，继续循环

    # 5. 没有工具调用，停止
    return StepOutcome(
        stop_reason="no_tool_calls",
        assistant_message=result.message
    )
```
### 9.2 Process of tool registration to LLM

#### Tool definition conversion

```python
# kosong 从 Toolset 提取工具定义
# 位置：packages/kosong/src/kosong/_generate.py

async def generate(
    chat_provider: ChatProvider,
    system_prompt: str,
    tools: Sequence[Tool],  # 这里传入所有工具定义
    history: Sequence[Message],
    ...
) -> "GenerateResult":

    # 将工具转换为 LLM API 格式
    tool_declarations = [
        {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters  # JSON Schema
        }
        for tool in tools
    ]

    # 调用 LLM API
    response = await chat_provider.generate_content({
        "system_instruction": system_prompt,
        "contents": history,
        "tools": tool_declarations,  # 告诉 LLM 有哪些工具可用
        "tool_config": {
            "function_calling_config": {
                "mode": "ANY"  # 允许 LLM 自动调用工具
            }
        }
    })

    # 处理流式响应和工具调用
    ...
```
**Key Points**:
- MCP tools are converted to standard LLM Function Calling format
- Tool parameters are described using JSON Schema
- LLM can call MCP tools just like built-in tools

#### How to register the MCP tool

```python
# 1. MCP 工具创建（mcp-client.py）
async def discover_tools() -> list[DiscoveredMCPTool]:
    tools = []
    for mcp_tool in await client.list_tools():
        tool = MCPTool(
            server_name,
            mcp_tool,
            client,
            runtime=runtime
        )
        tools.append(tool)
    return tools

# 2. 工具注册到 Toolset（toolset.py:230-233）
for tool in tools:
    self.add(tool)  # 添加到 _tool_dict

# 3. LLM 可以看到这些工具
# toolset.tools 返回所有工具的 Tool 定义
```
### 9.3 Complete call sequence diagram

```
用户输入 "使用 context7 搜索 Python MCP 教程"
    ↓
kimisoul._turn()
    ↓
kimisoul._agent_loop()
    ↓
kosong.step(
    chat_provider=KimiChatProvider,
    system_prompt=...,
    toolset=KimiToolset{
        _tool_dict={
            "context7_search": MCPTool(...),
            "read_file": ReadFile(...),
            ...
        }
    },
    history=[...]
)
    ↓
generate()
    ↓
Kimi API 调用
    POST /chat/completions
{
    "messages": [...],
    "tools": [
        {
            "name": "context7_search",
            "description": "This is an MCP (Model Context Protocol) tool...",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"}
                }
            }
        },
        ...
    ]
}
    ↓
Kimi API 返回流式响应
    ├── Content: "好的，我来帮你搜索..."
    └── FunctionCall: {
            "id": "call_abc123",
            "function": {
                "name": "context7_search",
                "arguments": '{"query": "Python MCP 教程", "limit": 10}'
            }
         }
    ↓
on_tool_call(tool_call)
    ↓
toolset.handle(tool_call)
    ↓
找到 MCPTool("context7_search")
    ↓
MCPTool.__call__(**{"query": "Python MCP 教程", "limit": 10})
    ↓
runtime.approval.request(...)
    ↓
[用户审批界面]
    ↓
用户点击"允许"
    ↓
client.call_tool("search", {"query": "Python MCP 教程", "limit": 10})
    ↓
MCP 服务器返回结果
    ↓
convert_mcp_tool_result(result)
    ↓
ToolResult(return_value=ToolOk(output=[...]))
    ↓
返回给 kosong.step
    ↓
_kimisoul._grow_context(result, results)
    ↓
添加到对话历史
    ↓
继续下一轮 LLM 调用（包含工具结果）
```
### 9.4 Key data structure conversion

#### LLM FunctionCall → Kimi ToolCall

```python
# LLM 返回的格式
function_call = {
    "id": "call_abc123",
    "function": {
        "name": "context7_search",  # LLM 看到的工具名称
        "arguments": '{"query": "...", "limit": 10}'
    }
}

# 转换为 Kimi ToolCall
tool_call = ToolCall(
    id=function_call["id"],
    function=FunctionCall(
        name=function_call["function"]["name"],
        arguments=function_call["function"]["arguments"]
    )
)
```

#### Tool Result → LLM Context

```python
# MCP 工具返回的原始结果
mcp_result = {
    "content": [
        {"type": "text", "text": "找到 10 个相关结果..."},
        {"type": "image", "data": "base64...", "mimeType": "image/png"}
    ]
}

# 转换为 Kimi ContentPart
content_parts = [
    ContentPart(text="找到 10 个相关结果..."),
    ContentPart(image="base64...")
]

# 转换为 LLM FunctionResponse
tool_result_message = Message(
    role="tool",
    content=[
        FunctionResponse(
            name="context7_search",
            response=content_parts
        )
    ]
)

# 添加到对话历史
history.append(tool_result_message)
```
### 9.5 Comparison with Gemini CLI

|characteristic| Kimi CLI | Gemini CLI |
|------|----------|------------|
|**Tool name format**|Original tool name (e.g. `context7_search`)|`mcp_{server}_{tool}` (such as `mcp_context7_search`)|
|**LLM Integration Layer**|kosong frame| Google GenAI SDK |
|**Tool Registration**|via Toolset.add()|By ToolRegistry|
|**User Approval**|In MCPTool.call()|In DiscoveredMCPToolInvocation|
|**Result Conversion**| convert_mcp_tool_result() | transformMcpContentToParts() |
|**Error handling**| ToolError | ToolErrorType |

---

## Reference resources

- **GitHub repository**: [https://github.com/MoonshotAI/kimi-cli](https://github.com/MoonshotAI/kimi-cli)
- **Official Document**: [https://moonshotai.github.io/kimi-cli/](https://moonshotai.github.io/kimi-cli/)
- **MCP protocol**: [https://modelcontextprotocol.io/](https://modelcontextprotocol.io/)
- **fastmcp library**: [https://github.com/jlowin/fastmcp](https://github.com/jlowin/fastmcp)

---

## Appendix

### A. Core code file list

```
src/kimi_cli/
├── cli/mcp.py                    # MCP CLI 命令 (350 行)
├── soul/toolset.py               # 工具集核心 (467 行)
├── acp/mcp.py                    # ACP 协议适配 (47 行)
├── config.py                     # 配置定义 (200+ 行)
└── exception.py                  # 异常定义

关键类：
- KimiToolset: 工具集管理
- MCPTool: MCP 工具封装
- MCPServerInfo: 服务器连接信息
- MCPConfig: 配置定义
```
### B. Configuration file example

**~/.kimi/mcp.json**:```json
{
  "mcpServers": {
    "context7": {
      "url": "https://mcp.context7.com/mcp",
      "transport": "http",
      "headers": {
        "CONTEXT7_API_KEY": "your-key"
      }
    },
    "linear": {
      "url": "https://mcp.linear.app/mcp",
      "transport": "http",
      "auth": "oauth"
    }
  }
}
```

**~/.kimi/config.yaml**:```yaml
mcp:
  client:
    tool_call_timeout_ms: 60000
```
### C. Related dependencies

```toml
[dependencies]
fastmcp = "2.12.5"
agent-client-protocol = "0.7.0"
pydantic = "2.12.5"
```

---

**Documentation version**: 1.0
**Last updated**: 2026-03-11
**Author**: AI Assistant
**License**: MIT License
